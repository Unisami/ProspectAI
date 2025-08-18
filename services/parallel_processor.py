#!/usr/bin/env python3
"""
Enhanced parallel processing service for concurrent company processing.
Provides better resource management, progress tracking, error recovery, and rate limiting.
"""

import time
import logging
import threading
from typing import (
    List,
    Dict,
    Any,
    Optional,
    Callable,
    Union
)
from dataclasses import (
    dataclass,
    field
)
from datetime import datetime
from queue import (
    Queue,
    Empty
)
from contextlib import contextmanager

import asyncio
from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed,
    Future
)
import psutil
from unittest.mock import Mock

from models.data_models import (
    CompanyData,
    Prospect
)
from utils.base_service import BaseService
from utils.rate_limiting import RateLimitingService




@dataclass
class ProcessingResult:
    """Result of processing a single company."""
    company_name: str
    prospects: List[Prospect]
    success: bool
    duration: float
    error_message: Optional[str] = None
    retry_count: int = 0
    worker_id: Optional[str] = None
    memory_usage_mb: float = 0.0
    api_calls_made: int = 0


@dataclass
class ProgressInfo:
    """Progress tracking information."""
    total_items: int
    completed_items: int
    successful_items: int
    failed_items: int
    current_item: Optional[str] = None
    estimated_time_remaining: Optional[float] = None
    throughput_per_minute: float = 0.0
    
    @property
    def completion_percentage(self) -> float:
        """Calculate completion percentage."""
        return (self.completed_items / self.total_items * 100) if self.total_items > 0 else 0.0


@dataclass
class ResourceUsage:
    """Resource usage tracking."""
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    active_threads: int = 0
    queue_size: int = 0
    peak_memory_mb: float = 0.0


@dataclass
class BatchConfig:
    """Configuration for batch processing."""
    batch_size: int = 5
    delay_between_batches: float = 10.0
    max_retries: int = 3
    retry_delay: float = 5.0
    enable_rate_limiting: bool = True
    rate_limit_service: Optional[str] = None
    progress_callback: Optional[Callable[[ProgressInfo], None]] = None
    error_callback: Optional[Callable[[str, Exception], None]] = None


class EnhancedParallelProcessor(BaseService):
    """
    Enhanced service for processing multiple companies in parallel.
    
    Features:
    - Better resource management with monitoring
    - Progress tracking with callbacks
    - Error recovery with retry logic
    - Rate-limited processing for external APIs
    - Memory usage monitoring
    - Graceful shutdown handling
    """
    
    def __init__(self, config, max_workers: int = 4, enable_monitoring: bool = True):  # Increased from 3 to 4
        """
        Initialize enhanced parallel processor.
        
        Args:
            config: Configuration object
            max_workers: Maximum number of concurrent workers
            enable_monitoring: Enable resource monitoring
        """
        self.max_workers = max_workers
        self.enable_monitoring = enable_monitoring
        self._shutdown_event = threading.Event()
        self._active_futures: Dict[str, Future] = {}
        self._resource_monitor_thread: Optional[threading.Thread] = None
        self._progress_lock = threading.RLock()
        
        super().__init__(config)
    
    def _initialize_service(self) -> None:
        """Initialize service-specific components."""
        self.rate_limiter = RateLimitingService(self.config)
        self.processing_stats = {
            'total_companies': 0,
            'successful_companies': 0,
            'failed_companies': 0,
            'total_prospects': 0,
            'total_duration': 0,
            'start_time': None,
            'end_time': None,
            'peak_memory_mb': 0.0,
            'total_retries': 0
        }
        self.resource_usage = ResourceUsage()
        
        if self.enable_monitoring:
            self._start_resource_monitoring()
    
    def process_companies_parallel(
        self, 
        companies: List[CompanyData], 
        process_function: Callable[[CompanyData], List[Prospect]],
        batch_config: Optional[BatchConfig] = None
    ) -> List[ProcessingResult]:
        """
        Process multiple companies in parallel with enhanced features.
        
        Args:
            companies: List of companies to process
            process_function: Function to process each company
            batch_config: Configuration for batch processing
            
        Returns:
            List of processing results
        """
        if not companies:
            return []
        
        config = batch_config or BatchConfig()
        
        self.logger.info(f"Starting enhanced parallel processing of {len(companies)} companies with {self.max_workers} workers")
        self.processing_stats['start_time'] = datetime.now()
        self.processing_stats['total_companies'] = len(companies)
        
        # Initialize progress tracking
        progress = ProgressInfo(
            total_items=len(companies),
            completed_items=0,
            successful_items=0,
            failed_items=0
        )
        
        results = []
        retry_queue = Queue()
        
        # Use ThreadPoolExecutor with context manager for proper cleanup
        with self._create_executor() as executor:
            # Submit all companies for processing
            future_to_company = {}
            for company in companies:
                future = executor.submit(
                    self._process_single_company_enhanced, 
                    company, 
                    process_function,
                    config
                )
                future_to_company[future] = company
                self._active_futures[company.name] = future
            
            # Process completed futures as they finish
            for future in as_completed(future_to_company):
                if self._shutdown_event.is_set():
                    self.logger.warning("Shutdown requested, stopping processing")
                    break
                
                company = future_to_company[future]
                
                try:
                    result = future.result()
                    results.append(result)
                    
                    # Update progress
                    with self._progress_lock:
                        progress.completed_items += 1
                        progress.current_item = company.name
                        
                        if result.success:
                            progress.successful_items += 1
                            self.processing_stats['successful_companies'] += 1
                            self.processing_stats['total_prospects'] += len(result.prospects)
                            self.logger.info(f"✅ Completed {company.name}: {len(result.prospects)} prospects in {result.duration:.1f}s")
                        else:
                            progress.failed_items += 1
                            self.processing_stats['failed_companies'] += 1
                            self.logger.error(f"❌ Failed {company.name}: {result.error_message}")
                            
                            # Call error callback for failed results
                            if config.error_callback and callable(config.error_callback):
                                config.error_callback(company.name, Exception(result.error_message))
                            
                            # Add to retry queue if retries are enabled and not exceeded
                            if config.max_retries > 0 and result.retry_count < config.max_retries:
                                retry_queue.put((company, result.retry_count + 1))
                        
                        # Update throughput calculation
                        elapsed_time = (datetime.now() - self.processing_stats['start_time']).total_seconds()
                        if elapsed_time > 0:
                            progress.throughput_per_minute = (progress.completed_items / elapsed_time) * 60
                            remaining_items = progress.total_items - progress.completed_items
                            if progress.throughput_per_minute > 0:
                                progress.estimated_time_remaining = (remaining_items / progress.throughput_per_minute) * 60
                        
                        # Call progress callback if provided
                        if config.progress_callback and callable(config.progress_callback):
                            config.progress_callback(progress)
                    
                    # Update resource usage
                    if result.memory_usage_mb > self.processing_stats['peak_memory_mb']:
                        self.processing_stats['peak_memory_mb'] = result.memory_usage_mb
                        
                except Exception as e:
                    self.processing_stats['failed_companies'] += 1
                    error_result = ProcessingResult(
                        company_name=company.name,
                        prospects=[],
                        success=False,
                        duration=0,
                        error_message=str(e)
                    )
                    results.append(error_result)
                    self.logger.error(f"❌ Exception processing {company.name}: {str(e)}")
                    
                    if config.error_callback and callable(config.error_callback):
                        config.error_callback(company.name, e)
                
                # Clean up completed future
                if company.name in self._active_futures:
                    del self._active_futures[company.name]
            
            # Process retry queue
            if not retry_queue.empty():
                self.logger.info(f"Processing {retry_queue.qsize()} retry items")
                retry_results = self._process_retries(retry_queue, process_function, config, executor)
                results.extend(retry_results)
        
        self.processing_stats['end_time'] = datetime.now()
        self.processing_stats['total_duration'] = (
            self.processing_stats['end_time'] - self.processing_stats['start_time']
        ).total_seconds()
        
        self._log_processing_summary()
        return results
    
    def _process_single_company_enhanced(
        self, 
        company: CompanyData, 
        process_function: Callable[[CompanyData], List[Prospect]],
        config: BatchConfig,
        retry_count: int = 0
    ) -> ProcessingResult:
        """Process a single company with enhanced monitoring and error handling."""
        start_time = time.time()
        worker_id = threading.current_thread().name
        initial_memory = self._get_memory_usage()
        
        try:
            self.logger.info(f"🔄 Processing {company.name} (worker: {worker_id}, attempt: {retry_count + 1})")
            
            # Apply rate limiting if enabled
            if config.enable_rate_limiting and config.rate_limit_service:
                self.rate_limiter.wait_for_service(config.rate_limit_service)
            
            # Process the company
            prospects = process_function(company)
            duration = time.time() - start_time
            final_memory = self._get_memory_usage()
            
            return ProcessingResult(
                company_name=company.name,
                prospects=prospects,
                success=True,
                duration=duration,
                retry_count=retry_count,
                worker_id=worker_id,
                memory_usage_mb=final_memory - initial_memory,
                api_calls_made=1  # This could be enhanced to track actual API calls
            )
            
        except Exception as e:
            duration = time.time() - start_time
            final_memory = self._get_memory_usage()
            
            self.logger.error(f"Error processing {company.name} (attempt {retry_count + 1}): {str(e)}")
            
            return ProcessingResult(
                company_name=company.name,
                prospects=[],
                success=False,
                duration=duration,
                error_message=str(e),
                retry_count=retry_count,
                worker_id=worker_id,
                memory_usage_mb=final_memory - initial_memory,
                api_calls_made=0
            )
    
    def _process_retries(
        self, 
        retry_queue: Queue, 
        process_function: Callable[[CompanyData], List[Prospect]],
        config: BatchConfig,
        executor: ThreadPoolExecutor
    ) -> List[ProcessingResult]:
        """Process retry queue with exponential backoff."""
        retry_results = []
        
        while not retry_queue.empty():
            try:
                company, retry_count = retry_queue.get_nowait()
                
                # Apply retry delay with exponential backoff
                delay = config.retry_delay * (2 ** (retry_count - 1))
                self.logger.info(f"Retrying {company.name} in {delay}s (attempt {retry_count + 1})")
                time.sleep(delay)
                
                # Submit retry
                future = executor.submit(
                    self._process_single_company_enhanced,
                    company,
                    process_function,
                    config,
                    retry_count
                )
                
                try:
                    result = future.result()
                    retry_results.append(result)
                    
                    if result.success:
                        self.processing_stats['successful_companies'] += 1
                        self.processing_stats['total_prospects'] += len(result.prospects)
                        self.logger.info(f"✅ Retry successful for {company.name}")
                    else:
                        self.processing_stats['failed_companies'] += 1
                        self.logger.error(f"❌ Retry failed for {company.name}: {result.error_message}")
                    
                    self.processing_stats['total_retries'] += 1
                    
                except Exception as e:
                    self.logger.error(f"Exception during retry for {company.name}: {str(e)}")
                    retry_results.append(ProcessingResult(
                        company_name=company.name,
                        prospects=[],
                        success=False,
                        duration=0,
                        error_message=str(e),
                        retry_count=retry_count
                    ))
                    
            except Empty:
                break
        
        return retry_results
    
    @contextmanager
    def _create_executor(self):
        """Create thread pool executor with proper resource management."""
        executor = ThreadPoolExecutor(
            max_workers=self.max_workers,
            thread_name_prefix="parallel-processor"
        )
        try:
            yield executor
        finally:
            # Graceful shutdown
            executor.shutdown(wait=True)
    
    def _start_resource_monitoring(self):
        """Start background resource monitoring thread."""
        if self._resource_monitor_thread is None or not self._resource_monitor_thread.is_alive():
            self._resource_monitor_thread = threading.Thread(
                target=self._monitor_resources,
                name="resource-monitor",
                daemon=True
            )
            self._resource_monitor_thread.start()
    
    def _monitor_resources(self):
        """Monitor system resources in background thread."""
        try:
            import psutil
            # Resource monitoring logic would go here
            pass
        except ImportError:
            self.logger.warning("psutil not available, resource monitoring disabled")
            return
        
        while not self._shutdown_event.is_set():
            try:
                # Update resource usage
                process = psutil.Process()
                self.resource_usage.cpu_percent = process.cpu_percent()
                self.resource_usage.memory_mb = process.memory_info().rss / 1024 / 1024
                self.resource_usage.active_threads = process.num_threads()
                self.resource_usage.queue_size = len(self._active_futures)
                
                # Track peak memory
                if self.resource_usage.memory_mb > self.resource_usage.peak_memory_mb:
                    self.resource_usage.peak_memory_mb = self.resource_usage.memory_mb
                
                # Log warnings for high resource usage
                if self.resource_usage.memory_mb > 1000:  # 1GB
                    self.logger.warning(f"High memory usage: {self.resource_usage.memory_mb:.1f}MB")
                
                if self.resource_usage.cpu_percent > 80:
                    self.logger.warning(f"High CPU usage: {self.resource_usage.cpu_percent:.1f}%")
                
                time.sleep(5)  # Monitor every 5 seconds
                
            except Exception as e:
                self.logger.error(f"Error in resource monitoring: {e}")
                time.sleep(10)  # Wait longer on error
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            return psutil.Process().memory_info().rss / 1024 / 1024
        except (ImportError, Exception):
            return 0.0
    
    def shutdown(self):
        """Gracefully shutdown the processor."""
        self.logger.info("Shutting down parallel processor...")
        self._shutdown_event.set()
        
        # Cancel active futures
        for future in self._active_futures.values():
            future.cancel()
        
        # Wait for resource monitor to stop
        if self._resource_monitor_thread and self._resource_monitor_thread.is_alive():
            self._resource_monitor_thread.join(timeout=5)
        
        self.logger.info("Parallel processor shutdown complete")
    
    def process_companies_with_batching(
        self,
        companies: List[CompanyData],
        process_function: Callable[[CompanyData], List[Prospect]],
        batch_config: Optional[BatchConfig] = None
    ) -> List[ProcessingResult]:
        """
        Process companies in batches with enhanced rate limiting and error recovery.
        
        Args:
            companies: List of companies to process
            process_function: Function to process each company
            batch_config: Configuration for batch processing
            
        Returns:
            List of processing results
        """
        if not companies:
            return []
        
        config = batch_config or BatchConfig()
        
        self.logger.info(f"Processing {len(companies)} companies in batches of {config.batch_size}")
        
        all_results = []
        total_processed = 0
        failed_batches = []
        
        # Process companies in batches
        for i in range(0, len(companies), config.batch_size):
            if self._shutdown_event.is_set():
                self.logger.warning("Shutdown requested, stopping batch processing")
                break
            
            batch = companies[i:i + config.batch_size]
            batch_num = (i // config.batch_size) + 1
            total_batches = (len(companies) + config.batch_size - 1) // config.batch_size
            
            self.logger.info(f"🔄 Processing batch {batch_num}/{total_batches} ({len(batch)} companies)")
            
            try:
                # Create batch-specific progress callback
                def batch_progress_callback(progress: ProgressInfo):
                    # Adjust progress to account for total companies across all batches
                    adjusted_progress = ProgressInfo(
                        total_items=len(companies),
                        completed_items=total_processed + progress.completed_items,
                        successful_items=progress.successful_items,
                        failed_items=progress.failed_items,
                        current_item=progress.current_item,
                        estimated_time_remaining=progress.estimated_time_remaining,
                        throughput_per_minute=progress.throughput_per_minute
                    )
                    if config.progress_callback and callable(config.progress_callback):
                        config.progress_callback(adjusted_progress)
                
                # Create batch-specific config
                batch_specific_config = BatchConfig(
                    batch_size=config.batch_size,
                    delay_between_batches=config.delay_between_batches,
                    max_retries=config.max_retries,
                    retry_delay=config.retry_delay,
                    enable_rate_limiting=config.enable_rate_limiting,
                    rate_limit_service=config.rate_limit_service,
                    progress_callback=batch_progress_callback,
                    error_callback=config.error_callback
                )
                
                # Process current batch in parallel
                batch_results = self.process_companies_parallel(batch, process_function, batch_specific_config)
                all_results.extend(batch_results)
                total_processed += len(batch)
                
                # Check batch success rate
                successful_in_batch = sum(1 for r in batch_results if r.success)
                batch_success_rate = successful_in_batch / len(batch_results) if batch_results else 0
                
                if batch_success_rate < 0.5:  # Less than 50% success
                    self.logger.warning(f"Low success rate in batch {batch_num}: {batch_success_rate:.1%}")
                    failed_batches.append(batch_num)
                
            except Exception as e:
                self.logger.error(f"Error processing batch {batch_num}: {str(e)}")
                failed_batches.append(batch_num)
                
                # Create error results for the batch
                for company in batch:
                    error_result = ProcessingResult(
                        company_name=company.name,
                        prospects=[],
                        success=False,
                        duration=0,
                        error_message=f"Batch processing error: {str(e)}"
                    )
                    all_results.append(error_result)
                
                if config.error_callback and callable(config.error_callback):
                    config.error_callback(f"batch_{batch_num}", e)
            
            # Add delay between batches (except for the last batch)
            if i + config.batch_size < len(companies) and not self._shutdown_event.is_set():
                self.logger.info(f"⏸️  Waiting {config.delay_between_batches}s before next batch...")
                time.sleep(config.delay_between_batches)
        
        # Log batch processing summary
        if failed_batches:
            self.logger.warning(f"Failed batches: {failed_batches}")
        
        return all_results
    
    def process_with_rate_limiting(
        self,
        companies: List[CompanyData],
        process_function: Callable[[CompanyData], List[Prospect]],
        service_name: str,
        max_concurrent: int = 2
    ) -> List[ProcessingResult]:
        """
        Process companies with strict rate limiting for external APIs.
        
        Args:
            companies: List of companies to process
            process_function: Function to process each company
            service_name: Name of the service for rate limiting
            max_concurrent: Maximum concurrent requests
            
        Returns:
            List of processing results
        """
        config = BatchConfig(
            batch_size=max_concurrent,
            delay_between_batches=2.0,  # 2 second delay between batches
            enable_rate_limiting=True,
            rate_limit_service=service_name,
            max_retries=2
        )
        
        return self.process_companies_with_batching(companies, process_function, config)
    
    def get_resource_usage(self) -> ResourceUsage:
        """Get current resource usage statistics."""
        return self.resource_usage
    
    def get_progress_info(self) -> Dict[str, Any]:
        """Get current progress information."""
        return {
            'active_tasks': len(self._active_futures),
            'resource_usage': self.resource_usage,
            'processing_stats': self.processing_stats.copy()
        }
    
    def _log_processing_summary(self):
        """Log comprehensive processing summary with enhanced metrics."""
        stats = self.processing_stats
        
        if stats['total_duration'] > 0:
            companies_per_minute = (stats['successful_companies'] / stats['total_duration']) * 60
            prospects_per_minute = (stats['total_prospects'] / stats['total_duration']) * 60
        else:
            companies_per_minute = 0
            prospects_per_minute = 0
        
        success_rate = (stats['successful_companies'] / stats['total_companies'] * 100) if stats['total_companies'] > 0 else 0
        
        self.logger.info("="*70)
        self.logger.info("🚀 ENHANCED PARALLEL PROCESSING SUMMARY")
        self.logger.info("="*70)
        self.logger.info(f"📊 Companies: {stats['successful_companies']}/{stats['total_companies']} successful ({success_rate:.1f}%)")
        self.logger.info(f"👥 Total Prospects: {stats['total_prospects']}")
        self.logger.info(f"⏱️  Total Duration: {stats['total_duration']:.1f}s ({stats['total_duration']/60:.1f}m)")
        self.logger.info(f"🚄 Processing Rate: {companies_per_minute:.1f} companies/min, {prospects_per_minute:.1f} prospects/min")
        self.logger.info(f"⚡ Workers Used: {self.max_workers}")
        self.logger.info(f"🔄 Total Retries: {stats['total_retries']}")
        self.logger.info(f"💾 Peak Memory: {stats['peak_memory_mb']:.1f}MB")
        
        if self.enable_monitoring:
            self.logger.info(f"📈 Current Memory: {self.resource_usage.memory_mb:.1f}MB")
            self.logger.info(f"🖥️  CPU Usage: {self.resource_usage.cpu_percent:.1f}%")
            self.logger.info(f"🧵 Active Threads: {self.resource_usage.active_threads}")
        
        if stats['failed_companies'] > 0:
            self.logger.warning(f"⚠️  Failed Companies: {stats['failed_companies']}")
        
        self.logger.info("="*70)
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        return self.processing_stats.copy()
    
    def __del__(self):
        """Cleanup on destruction."""
        try:
            self.shutdown()
        except Exception:
            pass  # Ignore errors during cleanup


# Backward compatibility class
class ParallelProcessor(EnhancedParallelProcessor):
    """
    Backward compatibility wrapper for the enhanced parallel processor.
    """
    
    def __init__(self, max_workers: int = 4, respect_rate_limits: bool = True):  # Increased from 3 to 4
        """
        Initialize with backward compatible interface.
        
        Args:
            max_workers: Maximum number of concurrent workers
            respect_rate_limits: Whether to respect API rate limits (deprecated)
        """
        # Create a mock config for backward compatibility
        mock_config = Mock()
        mock_config.openai_delay = 1.0
        mock_config.hunter_delay = 1.0
        mock_config.linkedin_delay = 2.0
        mock_config.scraping_delay = 1.0
        mock_config.openai_requests_per_minute = 60
        mock_config.hunter_requests_per_minute = 100
        mock_config.linkedin_requests_per_minute = 30
        mock_config.scraping_requests_per_minute = 60
        mock_config.resend_requests_per_minute = 100
        
        super().__init__(mock_config, max_workers, enable_monitoring=False)
        self.respect_rate_limits = respect_rate_limits
    
    def process_companies_parallel(
        self, 
        companies: List[CompanyData], 
        process_function: Callable[[CompanyData], List[Prospect]],
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> List[ProcessingResult]:
        """
        Backward compatible method signature.
        """
        # Convert old-style progress callback to new format
        new_progress_callback = None
        if progress_callback:
            def _new_progress_callback(progress: ProgressInfo):
                if progress.current_item:
                    progress_callback(progress.current_item, progress.completed_items, progress.total_items)
            new_progress_callback = _new_progress_callback
        
        config = BatchConfig(
            progress_callback=new_progress_callback,
            enable_rate_limiting=self.respect_rate_limits,
            max_retries=0  # Disable retries for backward compatibility
        )
        
        return super().process_companies_parallel(companies, process_function, config)
    
    def process_companies_with_batching(
        self,
        companies: List[CompanyData],
        process_function: Callable[[CompanyData], List[Prospect]],
        batch_size: int = 5,
        delay_between_batches: float = 10.0,
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> List[ProcessingResult]:
        """
        Backward compatible method signature - simplified implementation.
        """
        if not companies:
            return []
        
        self.logger.info(f"Processing {len(companies)} companies in batches of {batch_size} (backward compatible)")
        
        all_results = []
        total_processed = 0
        
        # Process companies in simple batches
        for i in range(0, len(companies), batch_size):
            batch = companies[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(companies) + batch_size - 1) // batch_size
            
            self.logger.info(f"🔄 Processing batch {batch_num}/{total_batches} ({len(batch)} companies)")
            
            # Process current batch using the simple parallel method
            batch_results = self.process_companies_parallel(batch, process_function, None)
            all_results.extend(batch_results)
            total_processed += len(batch)
            
            # Call progress callback for each completed company
            if progress_callback:
                for result in batch_results:
                    progress_callback(result.company_name, total_processed, len(companies))
            
            # Add delay between batches (except for the last batch)
            if i + batch_size < len(companies):
                self.logger.info(f"⏸️  Waiting {delay_between_batches}s before next batch...")
                time.sleep(delay_between_batches)
        
        return all_results


class AsyncParallelProcessor:
    """Async version for even better performance with async operations."""
    
    def __init__(self, max_concurrent: int = 5):
        self.max_concurrent = max_concurrent
        self.logger = logging.getLogger(__name__)
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_companies_async(
        self,
        companies: List[CompanyData],
        async_process_function: Callable[[CompanyData], List[Prospect]]
    ) -> List[ProcessingResult]:
        """Process companies using async/await for maximum concurrency."""
        self.logger.info(f"Starting async processing of {len(companies)} companies")
        
        # Create tasks for all companies
        tasks = [
            self._process_company_with_semaphore(company, async_process_function)
            for company in companies
        ]
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(ProcessingResult(
                    company_name=companies[i].name,
                    prospects=[],
                    success=False,
                    duration=0,
                    error_message=str(result)
                ))
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def _process_company_with_semaphore(
        self,
        company: CompanyData,
        async_process_function: Callable[[CompanyData], List[Prospect]]
    ) -> ProcessingResult:
        """Process company with semaphore to limit concurrency."""
        async with self.semaphore:
            start_time = time.time()
            try:
                prospects = await async_process_function(company)
                duration = time.time() - start_time
                return ProcessingResult(
                    company_name=company.name,
                    prospects=prospects,
                    success=True,
                    duration=duration
                )
            except Exception as e:
                duration = time.time() - start_time
                return ProcessingResult(
                    company_name=company.name,
                    prospects=[],
                    success=False,
                    duration=duration,
                    error_message=str(e)
                )
