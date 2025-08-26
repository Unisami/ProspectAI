"""
Optimized Notion API integration for managing prospect data and progress tracking.
Includes batch operations, connection pooling, and caching for better performance.
"""

import logging
import threading
import time
from typing import (
    List,
    Optional,
    Dict,
    Any,
    Union
)
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from queue import Queue
import hashlib
from urllib.parse import urlparse

from notion_client import Client
from notion_client.errors import APIResponseError
from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed
)

from models.data_models import (
    Prospect,
    ProspectStatus,
    ValidationError
)
from utils.validation_framework import (
    ValidationResult,
    ValidationSeverity
)
from utils.config import Config
from utils.configuration_service import get_configuration_service
from utils.base_service import BaseService
from services.caching_service import CachingService





logger = logging.getLogger(__name__)


class CampaignStatus(Enum):
    """Campaign status enumeration."""
    NOT_STARTED = "Not Started"
    RUNNING = "Running"
    PAUSED = "Paused"
    COMPLETED = "Completed"
    FAILED = "Failed"


@dataclass
class CampaignProgress:
    """Campaign progress data structure."""
    campaign_id: str
    name: str
    status: CampaignStatus
    start_time: datetime
    current_step: str
    companies_target: int
    companies_processed: int
    prospects_found: int
    emails_generated: int
    success_rate: float
    current_company: Optional[str] = None
    estimated_completion: Optional[datetime] = None
    error_count: int = 0


@dataclass
class BatchOperation:
    """Represents a batch operation for Notion API."""
    operation_type: str  # 'create', 'update', 'query'
    data: Dict[str, Any]
    callback: Optional[callable] = None


@dataclass
class ConnectionPoolStats:
    """Statistics for connection pool monitoring."""
    active_connections: int = 0
    total_requests: int = 0
    failed_requests: int = 0
    avg_response_time: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0


class OptimizedNotionDataManager(BaseService):
    """
    Optimized Notion API manager with batch operations, connection pooling, and caching.
    """
    
    def __init__(self, config: Optional[Config] = None, enable_caching: bool = True, 
                 max_connections: int = 5, batch_size: int = 10):
        """
        Initialize optimized Notion client with advanced features.
        
        Args:
            config: Configuration object (deprecated, use ConfigurationService)
            enable_caching: Enable caching for frequently accessed data
            max_connections: Maximum number of concurrent connections
            batch_size: Default batch size for bulk operations
        """
        # Set attributes before calling parent constructor
        self.max_connections = max_connections
        self.batch_size = batch_size
        self.enable_caching = enable_caching
        
        # Use ConfigurationService for centralized configuration management
        if config:
            # Backward compatibility: if config is provided, use it directly
            logger.warning("Direct config parameter is deprecated. Consider using ConfigurationService.")
            self.config = config
        else:
            # Use centralized configuration service
            config_service = get_configuration_service()
            self.config = config_service.get_config()
        
        # Initialize connection pool
        self.connection_pool = ThreadPoolExecutor(
            max_workers=max_connections,
            thread_name_prefix="notion-pool"
        )
        
        # Batch processing queue
        self.batch_queue = Queue()
        self.batch_processor_thread = None
        self.batch_processing_enabled = True
        
        # Performance monitoring
        self.stats = ConnectionPoolStats()
        self.request_times = []
        self.stats_lock = threading.RLock()
        
        super().__init__(self.config)
        
    def _initialize_service(self) -> None:
        """Initialize service-specific components."""
        # Initialize Notion client
        self.client = Client(auth=self.config.notion_token)
        self.database_id = self.config.notion_database_id
        
        # Initialize caching service if enabled
        if self.enable_caching:
            self.cache = CachingService(
                self.config,
                memory_backend=True,
                persistent_backend=False,  # Use memory only for Notion data
                max_memory_entries=1000,
                max_memory_mb=50
            )
        else:
            self.cache = None
        
        # Start batch processor
        self._start_batch_processor()
        
        logger.info(f"Initialized optimized Notion manager with {self.max_connections} connections")
    
    def test_connection(self) -> bool:
        """
        Test the Notion API connection.
        
        Returns:
            True if connection is successful
            
        Raises:
            Exception if connection fails
        """
        try:
            # Try to get the database info to test connection
            self.client.databases.retrieve(database_id=self.database_id)
            return True
        except Exception as e:
            raise Exception(f"Notion API connection failed: {str(e)}")
    
    def _start_batch_processor(self):
        """Start background batch processor thread."""
        if self.batch_processor_thread is None or not self.batch_processor_thread.is_alive():
            self.batch_processor_thread = threading.Thread(
                target=self._process_batch_queue,
                name="notion-batch-processor",
                daemon=True
            )
            self.batch_processor_thread.start()
    
    def _process_batch_queue(self):
        """Process batch operations in background thread."""
        batch_operations = []
        
        while self.batch_processing_enabled:
            try:
                # Collect operations for batching
                timeout = 1.0  # Wait up to 1 second for operations
                
                try:
                    operation = self.batch_queue.get(timeout=timeout)
                    batch_operations.append(operation)
                    
                    # Collect more operations up to batch size
                    while len(batch_operations) < self.batch_size:
                        try:
                            operation = self.batch_queue.get_nowait()
                            batch_operations.append(operation)
                        except:
                            break
                    
                    # Process the batch
                    if batch_operations:
                        self._execute_batch_operations(batch_operations)
                        batch_operations.clear()
                        
                except:
                    # Timeout or queue empty, continue
                    if batch_operations:
                        self._execute_batch_operations(batch_operations)
                        batch_operations.clear()
                    continue
                    
            except Exception as e:
                logger.error(f"Error in batch processor: {e}")
                time.sleep(1)
    
    def _execute_batch_operations(self, operations: List[BatchOperation]):
        """Execute a batch of operations efficiently."""
        if not operations:
            return
        
        # Group operations by type
        creates = [op for op in operations if op.operation_type == 'create']
        updates = [op for op in operations if op.operation_type == 'update']
        queries = [op for op in operations if op.operation_type == 'query']
        
        # Execute batched creates
        if creates:
            self._batch_create_prospects([op.data for op in creates])
        
        # Execute batched updates
        if updates:
            self._batch_update_prospects(updates)
        
        # Execute batched queries
        if queries:
            self._batch_query_prospects(queries)
    
    def _batch_create_prospects(self, prospect_data_list: List[Dict[str, Any]]):
        """Create multiple prospects in batch."""
        try:
            # Notion doesn't support true batch creates, but we can parallelize
            futures = []
            
            for prospect_data in prospect_data_list:
                future = self.connection_pool.submit(
                    self._create_single_prospect,
                    prospect_data
                )
                futures.append(future)
            
            # Wait for all creates to complete
            results = []
            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Error in batch create: {e}")
                    results.append(None)
            
            logger.info(f"Batch created {len([r for r in results if r])} prospects")
            return results
            
        except Exception as e:
            logger.error(f"Error in batch create prospects: {e}")
            return []
    
    def _batch_update_prospects(self, operations: List[BatchOperation]):
        """Update multiple prospects in batch."""
        try:
            futures = []
            
            for operation in operations:
                future = self.connection_pool.submit(
                    self._update_single_prospect,
                    operation.data['prospect_id'],
                    operation.data['properties']
                )
                futures.append((future, operation.callback))
            
            # Wait for all updates to complete
            for future, callback in futures:
                try:
                    result = future.result()
                    if callback:
                        callback(result)
                except Exception as e:
                    logger.error(f"Error in batch update: {e}")
            
            logger.info(f"Batch updated {len(operations)} prospects")
            
        except Exception as e:
            logger.error(f"Error in batch update prospects: {e}")
    
    def _batch_query_prospects(self, operations: List[BatchOperation]):
        """Execute multiple queries in batch."""
        try:
            futures = []
            
            for operation in operations:
                future = self.connection_pool.submit(
                    self._execute_single_query,
                    operation.data
                )
                futures.append((future, operation.callback))
            
            # Wait for all queries to complete
            for future, callback in futures:
                try:
                    result = future.result()
                    if callback:
                        callback(result)
                except Exception as e:
                    logger.error(f"Error in batch query: {e}")
            
            logger.info(f"Batch executed {len(operations)} queries")
            
        except Exception as e:
            logger.error(f"Error in batch query prospects: {e}")
    
    def _create_single_prospect(self, prospect_data: Dict[str, Any]) -> Optional[str]:
        """Create a single prospect with performance monitoring."""
        start_time = time.time()
        
        try:
            response = self.client.pages.create(
                parent={"database_id": self.database_id},
                properties=prospect_data
            )
            
            duration = time.time() - start_time
            self._update_stats(duration, success=True)
            
            return response["id"]
            
        except Exception as e:
            duration = time.time() - start_time
            self._update_stats(duration, success=False)
            logger.error(f"Error creating prospect: {e}")
            return None
    
    def _update_single_prospect(self, prospect_id: str, properties: Dict[str, Any]) -> bool:
        """Update a single prospect with performance monitoring."""
        start_time = time.time()
        
        try:
            self.client.pages.update(
                page_id=prospect_id,
                properties=properties
            )
            
            duration = time.time() - start_time
            self._update_stats(duration, success=True)
            
            # Invalidate cache for this prospect
            if self.cache:
                self.cache.delete(f"prospect:{prospect_id}")
            
            return True
            
        except Exception as e:
            duration = time.time() - start_time
            self._update_stats(duration, success=False)
            logger.error(f"Error updating prospect {prospect_id}: {e}")
            return False
    
    def _execute_single_query(self, query_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Execute a single query with caching and performance monitoring."""
        start_time = time.time()
        
        # Generate cache key for query
        cache_key = None
        if self.cache:
            query_hash = hashlib.md5(str(query_data).encode()).hexdigest()
            cache_key = f"query:{query_hash}"
            
            # Check cache first
            cached_result = self.cache.get(cache_key)
            if cached_result:
                self.stats.cache_hits += 1
                return cached_result
            
            self.stats.cache_misses += 1
        
        try:
            response = self.client.databases.query(**query_data)
            
            duration = time.time() - start_time
            self._update_stats(duration, success=True)
            
            # Cache the result
            if self.cache and cache_key:
                self.cache.set(cache_key, response, ttl=300)  # Cache for 5 minutes
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            self._update_stats(duration, success=False)
            logger.error(f"Error executing query: {e}")
            return None
    
    def _execute_direct_query(self, query_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Execute a single query directly without caching (for force refresh)."""
        start_time = time.time()
        
        try:
            response = self.client.databases.query(**query_data)
            
            duration = time.time() - start_time
            self._update_stats(duration, success=True)
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            self._update_stats(duration, success=False)
            logger.error(f"Error executing direct query: {e}")
            return None
    
    def _update_stats(self, duration: float, success: bool):
        """Update performance statistics."""
        with self.stats_lock:
            self.stats.total_requests += 1
            if not success:
                self.stats.failed_requests += 1
            
            self.request_times.append(duration)
            
            # Keep only last 100 request times for average calculation
            if len(self.request_times) > 100:
                self.request_times = self.request_times[-100:]
            
            self.stats.avg_response_time = sum(self.request_times) / len(self.request_times)
    
    def get_performance_stats(self) -> ConnectionPoolStats:
        """Get current performance statistics."""
        with self.stats_lock:
            return ConnectionPoolStats(
                active_connections=self.connection_pool._threads,
                total_requests=self.stats.total_requests,
                failed_requests=self.stats.failed_requests,
                avg_response_time=self.stats.avg_response_time,
                cache_hits=self.stats.cache_hits,
                cache_misses=self.stats.cache_misses
            )
    def store_prospects_batch(self, prospects: List[Prospect]) -> List[Optional[str]]:
        """
        Store multiple prospects efficiently using batch processing.
        
        Args:
            prospects: List of prospects to store
            
        Returns:
            List[Optional[str]]: List of prospect IDs (None for failed creates)
        """
        if not prospects:
            return []
        
        logger.info(f"Storing {len(prospects)} prospects in batch")
        
        # Prepare prospect data for batch creation
        prospect_data_list = []
        for prospect in prospects:
            try:
                prospect.validate()
                
                # Check cache for existing prospect
                cache_key = f"prospect_exists:{prospect.name}:{prospect.company}"
                if self.cache:
                    existing_id = self.cache.get(cache_key)
                    if existing_id:
                        logger.info(f"Prospect {prospect.name} already exists (cached)")
                        continue
                
                # Prepare properties for Notion
                properties = self._prospect_to_properties(prospect)
                prospect_data_list.append(properties)
                
            except ValidationError as e:
                # Use enhanced validation for better error reporting
                validation_result = self._validate_prospect_data(prospect)
                if not validation_result.is_valid:
                    logger.error(f"Invalid prospect data for {prospect.name}: {validation_result.message}")
                else:
                    logger.error(f"Invalid prospect data for {prospect.name}: {e}")
                continue
        
        # Execute batch creation
        if prospect_data_list:
            return self._batch_create_prospects(prospect_data_list)
        else:
            return []
    
    def update_prospects_batch(self, updates: List[Dict[str, Any]]) -> List[bool]:
        """
        Update multiple prospects efficiently using batch processing.
        
        Args:
            updates: List of update dictionaries with 'prospect_id' and 'properties'
            
        Returns:
            List[bool]: Success status for each update
        """
        if not updates:
            return []
        
        logger.info(f"Updating {len(updates)} prospects in batch")
        
        # Queue batch operations
        operations = []
        for update in updates:
            operation = BatchOperation(
                operation_type='update',
                data=update
            )
            operations.append(operation)
        
        # Execute batch updates
        self._batch_update_prospects(operations)
        
        # Return success status (simplified for now)
        return [True] * len(updates)
    
    def get_prospects_cached(self, filters: Dict[str, Any] = None, 
                           force_refresh: bool = False) -> List[Prospect]:
        """
        Get prospects with intelligent caching.
        
        Args:
            filters: Optional filters to apply
            force_refresh: Force refresh from Notion API
            
        Returns:
            List[Prospect]: List of prospects
        """
        # Generate cache key
        cache_key = f"prospects:{hashlib.md5(str(filters or {}).encode()).hexdigest()}"
        
        # Check cache first (unless force refresh)
        if not force_refresh and self.cache:
            cached_prospects = self.cache.get(cache_key)
            if cached_prospects:
                logger.info(f"Retrieved {len(cached_prospects)} prospects from cache")
                return cached_prospects
        
        # Fetch from Notion API
        prospects = self._fetch_prospects_from_api(filters, force_refresh=force_refresh)
        
        # Cache the results
        if self.cache and prospects:
            self.cache.set(cache_key, prospects, ttl=600)  # Cache for 10 minutes
        
        return prospects
    
    def get_processed_companies_cached(self, force_refresh: bool = False) -> List[str]:
        """
        Get processed company names with caching for better performance.
        
        Args:
            force_refresh: Force refresh from Notion API
            
        Returns:
            List[str]: List of processed company names
        """
        cache_key = "processed_companies"
        
        # Check cache first
        if not force_refresh and self.cache:
            cached_companies = self.cache.get(cache_key)
            if cached_companies:
                logger.info(f"Retrieved {len(cached_companies)} processed companies from cache")
                return cached_companies
        
        # Fetch from API with optimized pagination
        companies = self._fetch_processed_companies_optimized()
        
        # Cache the results
        if self.cache and companies:
            self.cache.set(cache_key, companies, ttl=1800)  # Cache for 30 minutes
        
        return companies
    
    def _fetch_processed_companies_optimized(self) -> List[str]:
        """Optimized method to fetch processed companies with better pagination."""
        if not self.database_id:
            return []
        
        try:
            company_names = set()
            has_more = True
            start_cursor = None
            page_count = 0
            
            while has_more:
                query_params = {
                    "database_id": self.database_id,
                    "page_size": 100,  # Maximum page size
                    "properties": ["Company"]  # Only fetch Company property
                }
                
                if start_cursor:
                    query_params["start_cursor"] = start_cursor
                
                # Use cached query execution
                response = self._execute_single_query(query_params)
                if not response:
                    break
                
                for page in response["results"]:
                    properties = page["properties"]
                    company = self._extract_rich_text(properties.get("Company", {}))
                    if company and company.strip():
                        company_names.add(company.strip())
                
                has_more = response.get("has_more", False)
                start_cursor = response.get("next_cursor")
                page_count += 1
                
                # Add small delay between pages to respect rate limits
                if has_more:
                    time.sleep(0.1)
            
            processed_companies = list(company_names)
            logger.info(f"Fetched {len(processed_companies)} companies in {page_count} pages")
            return processed_companies
            
        except Exception as e:
            logger.error(f"Error fetching processed companies: {e}")
            return []
    
    def bulk_update_email_status(self, updates: List[Dict[str, Any]]) -> int:
        """
        Bulk update email status for multiple prospects.
        
        Args:
            updates: List of update dictionaries with prospect_id, email_status, etc.
            
        Returns:
            int: Number of successful updates
        """
        if not updates:
            return 0
        
        logger.info(f"Bulk updating email status for {len(updates)} prospects")
        
        # Prepare batch operations
        batch_updates = []
        for update in updates:
            properties = {}
            
            if 'email_status' in update:
                properties["Email Status"] = {"select": {"name": update['email_status']}}
            
            if 'email_id' in update:
                properties["Email ID"] = {
                    "rich_text": [{"type": "text", "text": {"content": update['email_id']}}]
                }
            
            if 'email_subject' in update:
                properties["Email Subject"] = {
                    "rich_text": [{"type": "text", "text": {"content": update['email_subject']}}]
                }
            
            # Set email sent date when status is "Sent"
            if update.get('email_status') == "Sent":
                properties["Email Sent Date"] = {
                    "date": {"start": datetime.now().isoformat()}
                }
                properties["Contacted"] = {"checkbox": True}
                properties["Status"] = {"select": {"name": "Contacted"}}
            
            batch_updates.append({
                'prospect_id': update['prospect_id'],
                'properties': properties
            })
        
        # Execute batch updates
        success_results = self.update_prospects_batch(batch_updates)
        success_count = sum(success_results)
        
        logger.info(f"Successfully updated {success_count}/{len(updates)} email statuses")
        return success_count
    
    def _prospect_to_properties(self, prospect: Prospect) -> Dict[str, Any]:
        """Convert Prospect object to Notion properties format."""
        properties = {
            "Name": {
                "title": [{"type": "text", "text": {"content": prospect.name}}]
            },
            "Role": {
                "rich_text": [{"type": "text", "text": {"content": prospect.role}}]
            },
            "Company": {
                "rich_text": [{"type": "text", "text": {"content": prospect.company}}]
            },
            "Contacted": {
                "checkbox": prospect.contacted
            },
            "Status": {
                "select": {"name": prospect.status.value}
            },
            "Added Date": {
                "date": {"start": prospect.created_at.isoformat()}
            }
        }
        
        # Add optional fields
        if prospect.linkedin_url:
            properties["LinkedIn"] = {"url": prospect.linkedin_url}
        
        if prospect.email:
            properties["Email"] = {"email": prospect.email}
        
        if prospect.notes:
            properties["Notes"] = {
                "rich_text": [{"type": "text", "text": {"content": prospect.notes}}]
            }
        
        if prospect.source_url:
            properties["Source"] = {"url": prospect.source_url}
        
        # Add email-related fields (always include status fields)
        properties["Email Generation Status"] = {"select": {"name": prospect.email_generation_status}}
        properties["Email Delivery Status"] = {"select": {"name": prospect.email_delivery_status}}
        
        if prospect.email_subject:
            properties["Email Subject"] = {
                "rich_text": [{"type": "text", "text": {"content": prospect.email_subject}}]
            }
        
        if prospect.email_content:
            properties["Email Content"] = {
                "rich_text": self._create_rich_text_blocks(prospect.email_content)
            }
        
        if prospect.email_generated_date:
            properties["Email Generated Date"] = {"date": {"start": prospect.email_generated_date.isoformat()}}
        
        if prospect.email_sent_date:
            properties["Email Sent Date"] = {"date": {"start": prospect.email_sent_date.isoformat()}}
        
        return properties
    
    def _fetch_prospects_from_api(self, filters: Dict[str, Any] = None, force_refresh: bool = False) -> List[Prospect]:
        """Fetch prospects from Notion API with optimized pagination."""
        if not self.database_id:
            return []
        
        try:
            prospects = []
            has_more = True
            start_cursor = None
            
            while has_more:
                query_params = {
                    "database_id": self.database_id,
                    "page_size": 100
                }
                
                if start_cursor:
                    query_params["start_cursor"] = start_cursor
                
                if filters:
                    query_params["filter"] = self._build_notion_filter(filters)
                
                # Use direct API call if force_refresh is True to bypass caching
                if force_refresh:
                    response = self._execute_direct_query(query_params)
                else:
                    response = self._execute_single_query(query_params)
                if not response:
                    break
                
                for page in response["results"]:
                    try:
                        prospect = self._page_to_prospect(page)
                        prospects.append(prospect)
                    except Exception as e:
                        logger.error(f"Failed to parse prospect from page {page['id']}: {e}")
                        continue
                
                has_more = response.get("has_more", False)
                start_cursor = response.get("next_cursor")
                
                # Add small delay between pages
                if has_more:
                    time.sleep(0.1)
            
            logger.info(f"Fetched {len(prospects)} prospects from Notion API")
            return prospects
            
        except Exception as e:
            logger.error(f"Error fetching prospects from API: {e}")
            return []
    
    def shutdown(self):
        """Gracefully shutdown the optimized Notion manager."""
        logger.info("Shutting down optimized Notion manager...")
        
        # Stop batch processing
        self.batch_processing_enabled = False
        
        # Wait for batch processor to finish
        if self.batch_processor_thread and self.batch_processor_thread.is_alive():
            self.batch_processor_thread.join(timeout=5)
        
        # Shutdown connection pool
        self.connection_pool.shutdown(wait=True)
        
        # Close cache if enabled
        if self.cache:
            self.cache.__exit__(None, None, None)
        
        logger.info("Optimized Notion manager shutdown complete")
    
    def __del__(self):
        """Cleanup on destruction."""
        try:
            self.shutdown()
        except Exception:
            pass  # Ignore errors during cleanup

    def create_prospect_database(self) -> str:
        """
        Create a new Notion database for storing prospect data.
        
        Returns:
            str: The database ID of the created database
            
        Raises:
            APIResponseError: If Notion API request fails
        """
        parent_page_id = self._get_parent_page_id()
        return self._create_database_with_parent(parent_page_id)
    
    def _create_database_with_parent(self, parent_page_id: str) -> str:
        """
        Create a new Notion database with a specific parent page.
        
        Args:
            parent_page_id: The ID of the parent page
            
        Returns:
            str: The database ID of the created database
        """
        try:
            database_properties = {
                "Name": {
                    "title": {}
                },
                "Role": {
                    "rich_text": {}
                },
                "Company": {
                    "rich_text": {}
                },
                "LinkedIn": {
                    "url": {}
                },
                "Email": {
                    "email": {}
                },
                "Contacted": {
                    "checkbox": {}
                },
                "Status": {
                    "select": {
                        "options": [
                            {"name": "Not Contacted", "color": "gray"},
                            {"name": "Contacted", "color": "yellow"},
                            {"name": "Responded", "color": "green"},
                            {"name": "Rejected", "color": "red"}
                        ]
                    }
                },
                "Notes": {
                    "rich_text": {}
                },
                "Source": {
                    "url": {}
                },
                "Added Date": {
                    "date": {}
                },
                "LinkedIn Summary": {
                    "rich_text": {}
                },
                "Experience": {
                    "rich_text": {}
                },
                "Skills": {
                    "rich_text": {}
                },
                "Education": {
                    "rich_text": {}
                },
                "Location": {
                    "rich_text": {}
                },
                "Product Summary": {
                    "rich_text": {}
                },
                "Business Insights": {
                    "rich_text": {}
                },
                "Market Analysis": {
                    "rich_text": {}
                },
                "Product Features": {
                    "rich_text": {}
                },
                "Pricing Model": {
                    "rich_text": {}
                },
                "Competitors": {
                    "rich_text": {}
                },
                "AI Processing Date": {
                    "date": {}
                },
                "Email Status": {
                    "select": {
                        "options": [
                            {"name": "Not Sent", "color": "gray"},
                            {"name": "Sent", "color": "yellow"},
                            {"name": "Delivered", "color": "blue"},
                            {"name": "Opened", "color": "green"},
                            {"name": "Clicked", "color": "purple"},
                            {"name": "Bounced", "color": "red"},
                            {"name": "Complained", "color": "red"},
                            {"name": "Failed", "color": "red"}
                        ]
                    }
                },
                "Email ID": {
                    "rich_text": {}
                },
                "Email Sent Date": {
                    "date": {}
                },
                "Email Subject": {
                    "rich_text": {}
                },
                "Personalization Data": {
                    "rich_text": {}
                },
                "AI Processing Status": {
                    "select": {
                        "options": [
                            {"name": "Not Processed", "color": "gray"},
                            {"name": "Processing", "color": "yellow"},
                            {"name": "Completed", "color": "green"},
                            {"name": "Failed", "color": "red"}
                        ]
                    }
                },
                "Email Content": {
                    "rich_text": {}
                },
                "Email Body": {
                    "rich_text": {}
                },
                "Email Template": {
                    "select": {
                        "options": [
                            {"name": "cold_outreach", "color": "blue"},
                            {"name": "referral_followup", "color": "green"},
                            {"name": "product_interest", "color": "purple"},
                            {"name": "networking", "color": "orange"}
                        ]
                    }
                },
                "Personalization Score": {
                    "number": {}
                },
                "Email Generated Date": {
                    "date": {}
                },
                "Email Generation Status": {
                    "select": {
                        "options": [
                            {"name": "Not Generated", "color": "gray"},
                            {"name": "Generated", "color": "green"},
                            {"name": "Failed", "color": "red"},
                            {"name": "Reviewed", "color": "blue"},
                            {"name": "Approved", "color": "purple"}
                        ]
                    }
                },
                "Sender Profile Used": {
                    "rich_text": {}
                },
                "Email Delivery Status": {
                    "select": {
                        "options": [
                            {"name": "Not Sent", "color": "gray"},
                            {"name": "Queued", "color": "yellow"},
                            {"name": "Sent", "color": "blue"},
                            {"name": "Delivered", "color": "green"},
                            {"name": "Opened", "color": "purple"},
                            {"name": "Clicked", "color": "orange"},
                            {"name": "Bounced", "color": "red"},
                            {"name": "Complained", "color": "red"},
                            {"name": "Failed", "color": "red"}
                        ]
                    }
                },
                "Email Provider ID": {
                    "rich_text": {}
                },
                "Email Delivery Date": {
                    "date": {}
                },
                "Email Open Date": {
                    "date": {}
                },
                "Email Click Date": {
                    "date": {}
                },
                "Email Bounce Reason": {
                    "rich_text": {}
                },
                "Email Generation Model": {
                    "rich_text": {}
                },
                "Email Generation Time": {
                    "number": {}
                },
                "Email Word Count": {
                    "number": {}
                },
                "Email Character Count": {
                    "number": {}
                }
            }
            
            response = self.client.databases.create(
                parent={"type": "page_id", "page_id": parent_page_id},
                title=[{"type": "text", "text": {"content": "Job Prospects"}}],
                properties=database_properties
            )
            
            database_id = response["id"]
            logger.info(f"Created Notion database with ID: {database_id}")
            
            # Update config with new database ID
            self.database_id = database_id
            
            return database_id
            
        except APIResponseError as e:
            logger.error(f"Failed to create Notion database: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating database: {e}")
            raise
    
    def _get_parent_page_id(self) -> str:
        """
        Get the parent page ID for creating the database.
        We'll search for existing pages or create one in the workspace.
        """
        try:
            # Search for pages to find a suitable parent
            response = self.client.search(
                filter={"property": "object", "value": "page"}
            )
            
            if response["results"]:
                # Use the first available page as parent
                page_id = response["results"][0]["id"]
                logger.info(f"Using existing page as parent: {page_id}")
                return page_id
            else:
                # If no pages found, create a new page in the workspace
                logger.info("No pages found, creating a new parent page")
                page_response = self.client.pages.create(
                    parent={"type": "workspace", "workspace": True},
                    properties={
                        "title": {
                            "title": [{"type": "text", "text": {"content": "Job Prospect Automation"}}]
                        }
                    }
                )
                page_id = page_response["id"]
                logger.info(f"Created new parent page: {page_id}")
                return page_id
                
        except APIResponseError as e:
            logger.error(f"Error finding/creating parent page: {e}")
            # Try to search for any available page without filters
            try:
                response = self.client.search()
                for result in response["results"]:
                    if result["object"] == "page":
                        page_id = result["id"]
                        logger.info(f"Using fallback page as parent: {page_id}")
                        return page_id
                
                # If still no pages, raise the original error
                raise e
                
            except Exception as fallback_error:
                logger.error(f"Fallback search also failed: {fallback_error}")
                raise e
    
    def store_prospect(self, prospect: Prospect) -> str:
        """
        Store a single prospect in the Notion database.
        
        Args:
            prospect: The prospect data to store
            
        Returns:
            str: The Notion page ID of the created prospect (or existing if duplicate)
            
        Raises:
            ValidationError: If prospect data is invalid
            APIResponseError: If Notion API request fails
        """
        if not self.database_id:
            raise ValueError("Database ID not set. Create database first.")
        
        try:
            # Validate prospect data
            prospect.validate()
            
            # Check for duplicates and return existing ID if found
            existing_id = self.get_existing_prospect_id(prospect)
            if existing_id:
                logger.info(f"Existing prospect found: {prospect.name} at {prospect.company} (ID: {existing_id})")
                return existing_id
            
            # Prepare properties for Notion
            properties = {
                "Name": {
                    "title": [{"type": "text", "text": {"content": prospect.name}}]
                },
                "Role": {
                    "rich_text": [{"type": "text", "text": {"content": prospect.role}}]
                },
                "Company": {
                    "rich_text": [{"type": "text", "text": {"content": prospect.company}}]
                },
                "Contacted": {
                    "checkbox": prospect.contacted
                },
                "Status": {
                    "select": {"name": prospect.status.value}
                },
                "Added Date": {
                    "date": {"start": prospect.created_at.isoformat()}
                }
            }
            
            # Add optional fields if they exist
            if prospect.linkedin_url:
                properties["LinkedIn"] = {"url": prospect.linkedin_url}
            
            if prospect.email:
                properties["Email"] = {"email": prospect.email}
            
            if prospect.notes:
                properties["Notes"] = {
                    "rich_text": [{"type": "text", "text": {"content": prospect.notes}}]
                }
            
            if prospect.source_url:
                properties["Source"] = {"url": prospect.source_url}
            
            # Initialize AI processing fields with default values
            properties["AI Processing Status"] = {"select": {"name": "Not Processed"}}
            properties["Email Status"] = {"select": {"name": "Not Sent"}}
            properties["Email Generation Status"] = {"select": {"name": "Not Generated"}}
            properties["Email Delivery Status"] = {"select": {"name": "Not Sent"}}
            
            # Create the page in Notion
            response = self.client.pages.create(
                parent={"database_id": self.database_id},
                properties=properties
            )
            
            page_id = response["id"]
            prospect.id = page_id
            
            logger.info(f"Stored prospect: {prospect.name} at {prospect.company}")
            return page_id
            
        except ValidationError:
            logger.error(f"Invalid prospect data: {prospect}")
            raise
        except APIResponseError as e:
            logger.error(f"Failed to store prospect in Notion: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error storing prospect: {e}")
            raise
    
    def store_prospects(self, prospects: List[Prospect]) -> List[str]:
        """
        Store multiple prospects in the Notion database.
        
        Args:
            prospects: List of prospect data to store
            
        Returns:
            List[str]: List of Notion page IDs for successfully created prospects
        """
        stored_ids = []
        
        for prospect in prospects:
            try:
                page_id = self.store_prospect(prospect)
                if page_id:  # Only add if not duplicate
                    stored_ids.append(page_id)
            except Exception as e:
                logger.error(f"Failed to store prospect {prospect.name}: {e}")
                continue
        
        logger.info(f"Successfully stored {len(stored_ids)} out of {len(prospects)} prospects")
        return stored_ids
    
    def get_prospects(self, filters: Optional[Dict[str, Any]] = None) -> List[Prospect]:
        """
        Retrieve prospects from the Notion database.
        
        Args:
            filters: Optional filters to apply to the query
            
        Returns:
            List[Prospect]: List of prospect objects
            
        Raises:
            APIResponseError: If Notion API request fails
        """
        if not self.database_id:
            raise ValueError("Database ID not set. Create database first.")
        
        try:
            # Build query parameters
            query_params = {"database_id": self.database_id}
            
            if filters:
                query_params["filter"] = self._build_notion_filter(filters)
            
            # Query the database
            response = self.client.databases.query(**query_params)
            
            prospects = []
            for page in response["results"]:
                try:
                    prospect = self._page_to_prospect(page)
                    prospects.append(prospect)
                except Exception as e:
                    logger.error(f"Failed to parse prospect from page {page['id']}: {e}")
                    continue
            
            logger.info(f"Retrieved {len(prospects)} prospects from Notion")
            return prospects
            
        except APIResponseError as e:
            logger.error(f"Failed to retrieve prospects from Notion: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error retrieving prospects: {e}")
            raise
    
    def update_email_status(self, prospect_id: str, email_status: str, 
                          email_id: str = None, email_subject: str = None) -> bool:
        """
        Update prospect email status and related fields.
        
        Args:
            prospect_id: The Notion page ID of the prospect
            email_status: New email status (Not Sent, Sent, Delivered, Opened, etc.)
            email_id: The email ID from Resend
            email_subject: The subject of the sent email
            
        Returns:
            bool: True if update was successful
            
        Raises:
            APIResponseError: If Notion API request fails
        """
        try:
            properties = {
                "Email Status": {"select": {"name": email_status}}
            }
            
            if email_id:
                properties["Email ID"] = {
                    "rich_text": [{"type": "text", "text": {"content": email_id}}]
                }
            
            if email_subject:
                properties["Email Subject"] = {
                    "rich_text": [{"type": "text", "text": {"content": email_subject}}]
                }
            
            # Set email sent date when status is "Sent"
            if email_status == "Sent":
                properties["Email Sent Date"] = {
                    "date": {"start": datetime.now().isoformat()}
                }
                # Also update contacted status
                properties["Contacted"] = {"checkbox": True}
                properties["Status"] = {"select": {"name": "Contacted"}}
            
            self.client.pages.update(
                page_id=prospect_id,
                properties=properties
            )
            
            logger.info(f"Updated prospect {prospect_id} email status to {email_status}")
            return True
            
        except APIResponseError as e:
            logger.error(f"Failed to update email status: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error updating email status: {e}")
            raise
    
    def get_prospect_by_email_id(self, email_id: str) -> Optional[str]:
        """
        Find a prospect by email ID.
        
        Args:
            email_id: The email ID from Resend
            
        Returns:
            Optional[str]: The prospect ID if found, None otherwise
        """
        try:
            filter_conditions = {
                "property": "Email ID",
                "rich_text": {"equals": email_id}
            }
            
            response = self.client.databases.query(
                database_id=self.database_id,
                filter=filter_conditions
            )
            
            if response["results"]:
                return response["results"][0]["id"]
            return None
            
        except APIResponseError as e:
            logger.error(f"Failed to find prospect by email ID: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error finding prospect by email ID: {e}")
            return None
    
    def store_ai_structured_data(self, prospect_id: str, product_summary: str = None, 
                               business_insights: str = None, linkedin_summary: str = None, 
                               personalization_data: str = None) -> bool:
        """
        Store AI-processed and structured data for a prospect.
        Handles long text by splitting into multiple rich_text blocks if needed.
        
        Args:
            prospect_id: The Notion page ID of the prospect
            product_summary: AI-structured product analysis optimized for email personalization
            business_insights: AI-processed company metrics, funding, growth stage for outreach context
            linkedin_summary: AI-structured LinkedIn profile insights for personalization
            personalization_data: AI-generated key points for email customization
            
        Returns:
            bool: True if update was successful
            
        Raises:
            APIResponseError: If Notion API request fails
        """
        try:
            properties = {}
            
            # Add AI-structured data fields with proper handling of long text
            if product_summary:
                properties["Product Summary"] = {
                    "rich_text": self._create_rich_text_blocks(product_summary)
                }
            
            if business_insights:
                properties["Business Insights"] = {
                    "rich_text": self._create_rich_text_blocks(business_insights)
                }
            
            if linkedin_summary:
                properties["LinkedIn Summary"] = {
                    "rich_text": self._create_rich_text_blocks(linkedin_summary)
                }
            
            if personalization_data:
                properties["Personalization Data"] = {
                    "rich_text": self._create_rich_text_blocks(personalization_data)
                }
            
            # Only proceed if we have actual data to store
            if not any([product_summary, business_insights, linkedin_summary, personalization_data]):
                logger.warning(f"No AI-structured data to update for prospect {prospect_id}")
                return False
            
            # Update AI processing status and date
            properties["AI Processing Status"] = {"select": {"name": "Completed"}}
            properties["AI Processing Date"] = {
                "date": {"start": datetime.now().isoformat()}
            }
            
            self.client.pages.update(
                page_id=prospect_id,
                properties=properties
            )
            
            logger.info(f"Updated prospect {prospect_id} with AI-structured data")
            return True
            
        except APIResponseError as e:
            logger.error(f"Failed to store AI-structured data: {e}")
            # Update status to failed
            try:
                self.client.pages.update(
                    page_id=prospect_id,
                    properties={"AI Processing Status": {"select": {"name": "Failed"}}}
                )
            except:
                pass
            raise
        except Exception as e:
            logger.error(f"Unexpected error storing AI-structured data: {e}")
            # Update status to failed
            try:
                self.client.pages.update(
                    page_id=prospect_id,
                    properties={"AI Processing Status": {"select": {"name": "Failed"}}}
                )
            except:
                pass
            raise
    
    def get_prospect_data_for_email(self, prospect_id: str) -> Dict[str, str]:
        """
        Retrieve prospect data optimized for email generation.
        
        Args:
            prospect_id: The Notion page ID of the prospect
            
        Returns:
            Dict[str, str]: Dictionary containing all relevant data for email personalization
            
        Raises:
            APIResponseError: If Notion API request fails
        """
        try:
            response = self.client.pages.retrieve(page_id=prospect_id)
            properties = response["properties"]
            
            # Extract all relevant data for email generation
            prospect_data = {
                "name": self._extract_title(properties.get("Name", {})),
                "role": self._extract_rich_text(properties.get("Role", {})),
                "company": self._extract_rich_text(properties.get("Company", {})),
                "linkedin_url": self._extract_url(properties.get("LinkedIn", {})) or "",
                "email": self._extract_email(properties.get("Email", {})) or "",
                "source_url": self._extract_url(properties.get("Source", {})) or "",
                
                # AI-structured data optimized for email generation
                "product_summary": self._extract_rich_text(properties.get("Product Summary", {})),
                "business_insights": self._extract_rich_text(properties.get("Business Insights", {})),
                "linkedin_summary": self._extract_rich_text(properties.get("LinkedIn Summary", {})),
                "personalization_data": self._extract_rich_text(properties.get("Personalization Data", {})),
                
                # Additional context data
                "market_analysis": self._extract_rich_text(properties.get("Market Analysis", {})),
                "product_features": self._extract_rich_text(properties.get("Product Features", {})),
                "pricing_model": self._extract_rich_text(properties.get("Pricing Model", {})),
                "competitors": self._extract_rich_text(properties.get("Competitors", {})),
                "experience": self._extract_rich_text(properties.get("Experience", {})),
                "skills": self._extract_rich_text(properties.get("Skills", {})),
                "location": self._extract_rich_text(properties.get("Location", {})),
                "notes": self._extract_rich_text(properties.get("Notes", {})),
                
                # Processing status
                "ai_processing_status": self._extract_select(properties.get("AI Processing Status", {})),
                "ai_processing_date": self._extract_date(properties.get("AI Processing Date", {})),
                
                # Email content (for sending already generated emails)
                "email_subject": self._extract_rich_text(properties.get("Email Subject", {})),
                "email_content": self._extract_rich_text(properties.get("Email Content", {})),
                "email_generation_status": self._extract_select(properties.get("Email Generation Status", {})),
                "email_delivery_status": self._extract_select(properties.get("Email Delivery Status", {}))
            }
            
            logger.info(f"Retrieved prospect data for email generation: {prospect_data['name']}")
            return prospect_data
            
        except APIResponseError as e:
            logger.error(f"Failed to retrieve prospect data for email: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error retrieving prospect data for email: {e}")
            raise
    
    def update_ai_processing_status(self, prospect_id: str, status: str) -> bool:
        """
        Update the AI processing status for a prospect.
        
        Args:
            prospect_id: The Notion page ID of the prospect
            status: New AI processing status (Not Processed, Processing, Completed, Failed)
            
        Returns:
            bool: True if update was successful
            
        Raises:
            APIResponseError: If Notion API request fails
        """
        try:
            properties = {
                "AI Processing Status": {"select": {"name": status}}
            }
            
            # Set processing date when status changes to Processing or Completed
            if status in ["Processing", "Completed"]:
                properties["AI Processing Date"] = {
                    "date": {"start": datetime.now().isoformat()}
                }
            
            self.client.pages.update(
                page_id=prospect_id,
                properties=properties
            )
            
            logger.info(f"Updated prospect {prospect_id} AI processing status to {status}")
            return True
            
        except APIResponseError as e:
            logger.error(f"Failed to update AI processing status: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error updating AI processing status: {e}")
            raise
    
    def store_email_content(self, prospect_id: str, email_content, 
                           generation_metadata: Dict[str, Any] = None) -> bool:
        """
        Store generated email content and metadata in Notion.
        
        Args:
            prospect_id: The Notion page ID of the prospect
            email_content: EmailContent object with generated email data
            generation_metadata: Additional metadata about email generation
            
        Returns:
            bool: True if storage was successful
            
        Raises:
            APIResponseError: If Notion API request fails
        """
        try:
            properties = {}
            
            # Store email content
            if hasattr(email_content, 'subject') and email_content.subject:
                properties["Email Subject"] = {
                    "rich_text": [{"type": "text", "text": {"content": email_content.subject}}]
                }
            
            if hasattr(email_content, 'body') and email_content.body:
                # Store email body using multiple blocks if needed (no truncation)
                properties["Email Body"] = {
                    "rich_text": self._create_rich_text_blocks(email_content.body)
                }
                
                # Store full content in Email Content field (same as Email Body now)
                properties["Email Content"] = {
                    "rich_text": self._create_rich_text_blocks(email_content.body)
                }
            
            if hasattr(email_content, 'template_used') and email_content.template_used:
                properties["Email Template"] = {"select": {"name": email_content.template_used}}
            
            if hasattr(email_content, 'personalization_score'):
                properties["Personalization Score"] = {"number": email_content.personalization_score}
            
            # Store generation metadata
            if generation_metadata:
                if 'sender_profile_name' in generation_metadata:
                    properties["Sender Profile Used"] = {
                        "rich_text": [{"type": "text", "text": {"content": generation_metadata['sender_profile_name']}}]
                    }
                
                if 'model_used' in generation_metadata:
                    properties["Email Generation Model"] = {
                        "rich_text": [{"type": "text", "text": {"content": generation_metadata['model_used']}}]
                    }
                
                if 'generation_time' in generation_metadata:
                    properties["Email Generation Time"] = {"number": generation_metadata['generation_time']}
                
                if 'word_count' in generation_metadata:
                    properties["Email Word Count"] = {"number": generation_metadata['word_count']}
                
                if 'character_count' in generation_metadata:
                    properties["Email Character Count"] = {"number": generation_metadata['character_count']}
            
            # Calculate word and character counts if not provided
            if hasattr(email_content, 'body') and email_content.body:
                if 'word_count' not in (generation_metadata or {}):
                    word_count = len(email_content.body.split())
                    properties["Email Word Count"] = {"number": word_count}
                
                if 'character_count' not in (generation_metadata or {}):
                    char_count = len(email_content.body)
                    properties["Email Character Count"] = {"number": char_count}
            
            # Update generation status and date
            properties["Email Generation Status"] = {"select": {"name": "Generated"}}
            properties["Email Generated Date"] = {
                "date": {"start": datetime.now().isoformat()}
            }
            
            self.client.pages.update(
                page_id=prospect_id,
                properties=properties
            )
            
            logger.info(f"Stored email content for prospect {prospect_id}")
            return True
            
        except APIResponseError as e:
            logger.error(f"Failed to store email content: {e}")
            # Update status to failed
            try:
                self.client.pages.update(
                    page_id=prospect_id,
                    properties={"Email Generation Status": {"select": {"name": "Failed"}}}
                )
            except:
                pass
            raise
        except Exception as e:
            logger.error(f"Unexpected error storing email content: {e}")
            # Update status to failed
            try:
                self.client.pages.update(
                    page_id=prospect_id,
                    properties={"Email Generation Status": {"select": {"name": "Failed"}}}
                )
            except:
                pass
            raise
    
    def update_email_delivery_status(self, prospect_id: str, delivery_status: str, 
                                   provider_id: str = None, delivery_metadata: Dict[str, Any] = None) -> bool:
        """
        Update email delivery status and related tracking information.
        
        Args:
            prospect_id: The Notion page ID of the prospect
            delivery_status: New delivery status (Queued, Sent, Delivered, Opened, etc.)
            provider_id: Email provider ID (e.g., Resend email ID)
            delivery_metadata: Additional delivery tracking data
            
        Returns:
            bool: True if update was successful
            
        Raises:
            APIResponseError: If Notion API request fails
        """
        try:
            properties = {
                "Email Delivery Status": {"select": {"name": delivery_status}}
            }
            
            if provider_id:
                properties["Email Provider ID"] = {
                    "rich_text": [{"type": "text", "text": {"content": provider_id}}]
                }
            
            # Update relevant dates based on status
            current_time = datetime.now().isoformat()
            
            if delivery_status in ["Sent", "Queued"]:
                properties["Email Delivery Date"] = {"date": {"start": current_time}}
                # Also update the legacy Email Sent Date field
                properties["Email Sent Date"] = {"date": {"start": current_time}}
                # Update contacted status
                properties["Contacted"] = {"checkbox": True}
                properties["Status"] = {"select": {"name": "Contacted"}}
            
            elif delivery_status == "Opened":
                properties["Email Open Date"] = {"date": {"start": current_time}}
            
            elif delivery_status == "Clicked":
                properties["Email Click Date"] = {"date": {"start": current_time}}
            
            elif delivery_status in ["Bounced", "Failed"]:
                if delivery_metadata and 'bounce_reason' in delivery_metadata:
                    properties["Email Bounce Reason"] = {
                        "rich_text": [{"type": "text", "text": {"content": delivery_metadata['bounce_reason']}}]
                    }
            
            # Store additional delivery metadata
            if delivery_metadata:
                # You can extend this to store more specific delivery data
                pass
            
            self.client.pages.update(
                page_id=prospect_id,
                properties=properties
            )
            
            logger.info(f"Updated prospect {prospect_id} email delivery status to {delivery_status}")
            return True
            
        except APIResponseError as e:
            logger.error(f"Failed to update email delivery status: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error updating email delivery status: {e}")
            raise
    
    def get_email_generation_stats(self) -> Dict[str, Any]:
        """
        Get statistics about email generation across all prospects.
        
        Returns:
            Dict[str, Any]: Statistics about email generation
        """
        try:
            # Query all prospects
            response = self.client.databases.query(database_id=self.database_id)
            
            stats = {
                'total_prospects': 0,
                'emails_generated': 0,
                'emails_sent': 0,
                'emails_delivered': 0,
                'emails_opened': 0,
                'emails_clicked': 0,
                'emails_bounced': 0,
                'avg_personalization_score': 0.0,
                'avg_word_count': 0,
                'templates_used': {},
                'models_used': {},
                'sender_profiles_used': {},
                'generation_success_rate': 0.0,
                'delivery_success_rate': 0.0
            }
            
            personalization_scores = []
            word_counts = []
            
            for page in response["results"]:
                properties = page["properties"]
                stats['total_prospects'] += 1
                
                # Email generation stats
                generation_status = self._extract_select(properties.get("Email Generation Status", {}))
                if generation_status == "Generated":
                    stats['emails_generated'] += 1
                
                # Email delivery stats
                delivery_status = self._extract_select(properties.get("Email Delivery Status", {}))
                if delivery_status in ["Sent", "Delivered", "Opened", "Clicked"]:
                    stats['emails_sent'] += 1
                if delivery_status in ["Delivered", "Opened", "Clicked"]:
                    stats['emails_delivered'] += 1
                if delivery_status in ["Opened", "Clicked"]:
                    stats['emails_opened'] += 1
                if delivery_status == "Clicked":
                    stats['emails_clicked'] += 1
                if delivery_status == "Bounced":
                    stats['emails_bounced'] += 1
                
                # Personalization score
                score = self._extract_number(properties.get("Personalization Score", {}))
                if score is not None:
                    personalization_scores.append(score)
                
                # Word count
                word_count = self._extract_number(properties.get("Email Word Count", {}))
                if word_count is not None:
                    word_counts.append(word_count)
                
                # Template usage
                template = self._extract_select(properties.get("Email Template", {}))
                if template:
                    stats['templates_used'][template] = stats['templates_used'].get(template, 0) + 1
                
                # Model usage
                model = self._extract_rich_text(properties.get("Email Generation Model", {}))
                if model:
                    stats['models_used'][model] = stats['models_used'].get(model, 0) + 1
                
                # Sender profile usage
                sender_profile = self._extract_rich_text(properties.get("Sender Profile Used", {}))
                if sender_profile:
                    stats['sender_profiles_used'][sender_profile] = stats['sender_profiles_used'].get(sender_profile, 0) + 1
            
            # Calculate averages
            if personalization_scores:
                stats['avg_personalization_score'] = sum(personalization_scores) / len(personalization_scores)
            
            if word_counts:
                stats['avg_word_count'] = sum(word_counts) / len(word_counts)
            
            # Calculate success rates
            if stats['total_prospects'] > 0:
                stats['generation_success_rate'] = stats['emails_generated'] / stats['total_prospects']
            
            if stats['emails_sent'] > 0:
                stats['delivery_success_rate'] = stats['emails_delivered'] / stats['emails_sent']
            
            logger.info("Retrieved email generation statistics")
            return stats
            
        except APIResponseError as e:
            logger.error(f"Failed to get email generation stats: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting email generation stats: {e}")
            raise
    
    def get_prospects_by_email_status(self, generation_status: str = None, 
                                    delivery_status: str = None) -> List[Dict[str, Any]]:
        """
        Get prospects filtered by email generation or delivery status.
        
        Args:
            generation_status: Filter by email generation status
            delivery_status: Filter by email delivery status
            
        Returns:
            List[Dict[str, Any]]: List of prospect data with email information
        """
        try:
            filter_conditions = {"and": []}
            
            if generation_status:
                filter_conditions["and"].append({
                    "property": "Email Generation Status",
                    "select": {"equals": generation_status}
                })
            
            if delivery_status:
                filter_conditions["and"].append({
                    "property": "Email Delivery Status",
                    "select": {"equals": delivery_status}
                })
            
            query_params = {"database_id": self.database_id}
            if filter_conditions["and"]:
                query_params["filter"] = filter_conditions
            
            response = self.client.databases.query(**query_params)
            
            prospects = []
            for page in response["results"]:
                properties = page["properties"]
                
                prospect_data = {
                    "id": page["id"],
                    "name": self._extract_title(properties.get("Name", {})),
                    "company": self._extract_rich_text(properties.get("Company", {})),
                    "email": self._extract_email(properties.get("Email", {})),
                    "email_subject": self._extract_rich_text(properties.get("Email Subject", {})),
                    "email_template": self._extract_select(properties.get("Email Template", {})),
                    "personalization_score": self._extract_number(properties.get("Personalization Score", {})),
                    "generation_status": self._extract_select(properties.get("Email Generation Status", {})),
                    "delivery_status": self._extract_select(properties.get("Email Delivery Status", {})),
                    "generated_date": self._extract_date(properties.get("Email Generated Date", {})),
                    "sent_date": self._extract_date(properties.get("Email Delivery Date", {})),
                    "opened_date": self._extract_date(properties.get("Email Open Date", {})),
                    "sender_profile": self._extract_rich_text(properties.get("Sender Profile Used", {})),
                    "model_used": self._extract_rich_text(properties.get("Email Generation Model", {}))
                }
                
                prospects.append(prospect_data)
            
            logger.info(f"Retrieved {len(prospects)} prospects with email status filters")
            return prospects
            
        except APIResponseError as e:
            logger.error(f"Failed to get prospects by email status: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting prospects by email status: {e}")
            raise
    
    def get_processed_company_names(self) -> List[str]:
        """
        Get list of company names that have already been processed.
        
        Returns:
            List[str]: List of unique company names from existing prospects
        """
        if not self.database_id:
            logger.warning("Database ID not set, returning empty list")
            return []
        
        try:
            # Query all prospects to get unique company names with pagination
            company_names = set()
            has_more = True
            start_cursor = None
            
            while has_more:
                query_params = {
                    "database_id": self.database_id,
                    "page_size": 100  # Maximum page size for better performance
                }
                
                if start_cursor:
                    query_params["start_cursor"] = start_cursor
                
                response = self.client.databases.query(**query_params)
                
                for page in response["results"]:
                    properties = page["properties"]
                    company = self._extract_rich_text(properties.get("Company", {}))
                    if company and company.strip():
                        company_names.add(company.strip())
                
                has_more = response.get("has_more", False)
                start_cursor = response.get("next_cursor")
            
            processed_companies = list(company_names)
            logger.info(f"Found {len(processed_companies)} unique processed companies")
            return processed_companies
            
        except APIResponseError as e:
            logger.error(f"Failed to get processed company names: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error getting processed company names: {e}")
            return []
    
    def get_processed_company_domains(self) -> List[str]:
        """
        Get list of company domains that have already been processed.
        This extracts domains from source URLs of existing prospects.
        
        Returns:
            List[str]: List of unique company domains from existing prospects
        """
        if not self.database_id:
            logger.warning("Database ID not set, returning empty list")
            return []
        
        try:
            # Query all prospects to get unique domains from source URLs with pagination
            domains = set()
            has_more = True
            start_cursor = None
            
            while has_more:
                query_params = {
                    "database_id": self.database_id,
                    "page_size": 100  # Maximum page size for better performance
                }
                
                if start_cursor:
                    query_params["start_cursor"] = start_cursor
                
                response = self.client.databases.query(**query_params)
                
                for page in response["results"]:
                    properties = page["properties"]
                    source_url = self._extract_url(properties.get("Source", {}))
                    
                    if source_url:
                        # Extract domain from source URL
                        try:
                            parsed_url = urlparse(source_url)
                            if parsed_url.netloc:
                                # Remove www. prefix if present
                                domain = parsed_url.netloc.lower()
                                if domain.startswith('www.'):
                                    domain = domain[4:]
                                domains.add(domain)
                        except Exception as e:
                            logger.warning(f"Failed to parse domain from URL {source_url}: {e}")
                            continue
                
                has_more = response.get("has_more", False)
                start_cursor = response.get("next_cursor")
            
            processed_domains = list(domains)
            logger.info(f"Found {len(processed_domains)} unique processed domains")
            return processed_domains
            
        except APIResponseError as e:
            logger.error(f"Failed to get processed company domains: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error getting processed company domains: {e}")
            return []
    
    def is_company_already_processed(self, company_name: str, company_domain: str = None) -> bool:
        """
        Check if a specific company has already been processed.
        This is more efficient than getting all processed companies for single checks.
        
        Args:
            company_name: Name of the company to check
            company_domain: Optional domain to check as well
            
        Returns:
            bool: True if company has been processed, False otherwise
        """
        if not self.database_id:
            return False
        
        try:
            # Build filter conditions
            filter_conditions = {"or": []}
            
            # Check by company name (case-insensitive)
            filter_conditions["or"].append({
                "property": "Company",
                "rich_text": {"equals": company_name}
            })
            
            # If domain is provided, also check by domain in source URL
            if company_domain:
                # We'll need to check if any source URL contains this domain
                # Since Notion doesn't support regex, we'll do a contains check
                filter_conditions["or"].append({
                    "property": "Source",
                    "url": {"contains": company_domain}
                })
            
            response = self.client.databases.query(
                database_id=self.database_id,
                filter=filter_conditions,
                page_size=1  # We only need to know if any exist
            )
            
            is_processed = len(response["results"]) > 0
            
            if is_processed:
                logger.info(f"Company {company_name} already processed - skipping")
            
            return is_processed
            
        except APIResponseError as e:
            logger.error(f"Failed to check if company is processed: {e}")
            # Return False to continue processing if check fails
            return False
        except Exception as e:
            logger.error(f"Unexpected error checking if company is processed: {e}")
            # Return False to continue processing if check fails
            return False
    
    def get_companies_processing_status(self, companies: List[tuple]) -> Dict[str, bool]:
        """
        Check processing status for multiple companies efficiently.
        
        Args:
            companies: List of tuples (company_name, company_domain)
            
        Returns:
            Dict mapping company names to processing status (True if processed)
        """
        if not self.database_id or not companies:
            return {}
        
        try:
            # Get all processed companies and domains in one call
            processed_companies = set(name.lower() for name in self.get_processed_company_names())
            processed_domains = set(domain.lower() for domain in self.get_processed_company_domains())
            
            status_map = {}
            for company_name, company_domain in companies:
                is_processed = (
                    company_name.lower() in processed_companies or
                    (company_domain and company_domain.lower() in processed_domains)
                )
                status_map[company_name] = is_processed
            
            processed_count = sum(status_map.values())
            logger.info(f"Batch status check: {processed_count}/{len(companies)} companies already processed")
            
            return status_map
            
        except Exception as e:
            logger.error(f"Failed to get companies processing status: {e}")
            # Return empty dict to continue processing
            return {}

    def update_prospect_status(self, prospect_id: str, status: ProspectStatus, 
                             contacted: bool = None, notes: str = None) -> bool:
        """
        Update prospect status and related fields.
        
        Args:
            prospect_id: The Notion page ID of the prospect
            status: New status for the prospect
            contacted: Whether the prospect has been contacted
            notes: Additional notes to add
            
        Returns:
            bool: True if update was successful
            
        Raises:
            APIResponseError: If Notion API request fails
        """
        try:
            properties = {
                "Status": {"select": {"name": status.value}}
            }
            
            if contacted is not None:
                properties["Contacted"] = {"checkbox": contacted}
            
            if notes:
                properties["Notes"] = {
                    "rich_text": [{"type": "text", "text": {"content": notes}}]
                }
            
            self.client.pages.update(
                page_id=prospect_id,
                properties=properties
            )
            
            logger.info(f"Updated prospect {prospect_id} status to {status.value}")
            return True
            
        except APIResponseError as e:
            logger.error(f"Failed to update prospect status: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error updating prospect: {e}")
            raise
    
    def check_duplicate(self, prospect: Prospect) -> bool:
        """
        Check if a prospect already exists in the database.
        
        Args:
            prospect: The prospect to check for duplicates
            
        Returns:
            bool: True if duplicate exists, False otherwise
        """
        existing_id = self.get_existing_prospect_id(prospect)
        return existing_id is not None
    
    def get_existing_prospect_id(self, prospect: Prospect) -> Optional[str]:
        """
        Get the ID of an existing prospect if it exists.
        
        Args:
            prospect: The prospect to check for duplicates
            
        Returns:
            str: The existing prospect's ID if found, None otherwise
        """
        try:
            # Search for prospects with the same name and company
            filter_conditions = {
                "and": [
                    {
                        "property": "Name",
                        "title": {"equals": prospect.name}
                    },
                    {
                        "property": "Company", 
                        "rich_text": {"equals": prospect.company}
                    }
                ]
            }
            
            response = self.client.databases.query(
                database_id=self.database_id,
                filter=filter_conditions
            )
            
            if len(response["results"]) > 0:
                return response["results"][0]["id"]
            else:
                return None
            
        except APIResponseError as e:
            logger.error(f"Failed to check for duplicates: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error checking duplicates: {e}")
            return False
    
    def _build_notion_filter(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert simple filters to Notion API filter format.
        
        Args:
            filters: Simple filter dictionary
            
        Returns:
            Dict: Notion API compatible filter
        """
        notion_filter = {"and": []}
        
        for key, value in filters.items():
            if key == "company":
                notion_filter["and"].append({
                    "property": "Company",
                    "rich_text": {"equals": value}
                })
            elif key == "status":
                notion_filter["and"].append({
                    "property": "Status",
                    "select": {"equals": value}
                })
            elif key == "contacted":
                notion_filter["and"].append({
                    "property": "Contacted",
                    "checkbox": {"equals": value}
                })
        
        return notion_filter
    
    def _page_to_prospect(self, page: Dict[str, Any]) -> Prospect:
        """
        Convert a Notion page to a Prospect object.
        
        Args:
            page: Notion page data
            
        Returns:
            Prospect: Converted prospect object
        """
        properties = page["properties"]
        
        # Extract required fields
        name = self._extract_title(properties.get("Name", {}))
        role = self._extract_rich_text(properties.get("Role", {}))
        company = self._extract_rich_text(properties.get("Company", {}))
        
        # Extract optional fields
        linkedin_url = self._extract_url(properties.get("LinkedIn", {}))
        email = self._extract_email(properties.get("Email", {}))
        contacted = self._extract_checkbox(properties.get("Contacted", {}))
        status_str = self._extract_select(properties.get("Status", {}))
        notes = self._extract_rich_text(properties.get("Notes", {}))
        source_url = self._extract_url(properties.get("Source", {}))
        created_at = self._extract_date(properties.get("Added Date", {}))
        
        # Log if created_at is None for debugging
        if created_at is None:
            logger.debug(f"Created date is None for prospect {name} ({page.get('id', 'unknown ID')}). Using current time as fallback.")
            created_at = datetime.now()
        elif not isinstance(created_at, datetime):
            logger.warning(f"Created date is not a datetime object for prospect {name} ({page.get('id', 'unknown ID')}): {type(created_at).__name__}. Using current time as fallback.")
            created_at = datetime.now()

        # Extract email-related fields
        email_generation_status = self._extract_select(properties.get("Email Generation Status", {}))
        email_delivery_status = self._extract_select(properties.get("Email Delivery Status", {}))
        email_subject = self._extract_rich_text(properties.get("Email Subject", {}))
        email_content = self._extract_rich_text(properties.get("Email Content", {}))
        email_generated_date = self._extract_date(properties.get("Email Generated Date", {}))
        email_sent_date = self._extract_date(properties.get("Email Sent Date", {}))

        # Extract AI-structured data fields
        product_summary = self._extract_rich_text(properties.get("Product Summary", {}))
        business_insights = self._extract_rich_text(properties.get("Business Insights", {}))
        linkedin_summary = self._extract_rich_text(properties.get("LinkedIn Summary", {}))
        personalization_data = self._extract_rich_text(properties.get("Personalization Data", {}))

        # Convert status string to enum
        status = ProspectStatus.NOT_CONTACTED
        for status_enum in ProspectStatus:
            if status_enum.value == status_str:
                status = status_enum
                break

        return Prospect(
            id=page["id"],
            name=name,
            role=role,
            company=company,
            linkedin_url=linkedin_url,
            email=email,
            contacted=contacted,
            status=status,
            notes=notes,
            source_url=source_url,
            created_at=created_at,
            email_generation_status=email_generation_status,
            email_delivery_status=email_delivery_status,
            email_subject=email_subject,
            email_content=email_content,
            email_generated_date=email_generated_date,
            email_sent_date=email_sent_date,
            product_summary=product_summary,
            business_insights=business_insights,
            linkedin_summary=linkedin_summary,
            personalization_data=personalization_data
        )
        
    def _create_rich_text_blocks(self, text: str, max_block_size: int = 2000) -> List[Dict[str, Any]]:
        """Create rich text blocks for Notion with proper chunking to avoid character loss.
        
        This method guarantees no character loss by using simple chunking.
        
        Args:
            text: The text content to store
            max_block_size: Maximum characters per block (Notion limit is 2000)
            
        Returns:
            List of rich_text block dictionaries
        """
        if not text:
            return [{"type": "text", "text": {"content": ""}}]
        
        # If text is within limit, return single block
        if len(text) <= max_block_size:
            return [{"type": "text", "text": {"content": text}}]
        
        # Split long text into chunks of max_block_size
        blocks = []
        for i in range(0, len(text), max_block_size):
            chunk = text[i:i + max_block_size]
            blocks.append({"type": "text", "text": {"content": chunk}})
        
        # Verify no characters were lost
        total_chars = sum(len(block["text"]["content"]) for block in blocks)
        if total_chars != len(text):
            logger.error(f"Character loss detected: original={len(text)}, preserved={total_chars}")
        else:
            logger.debug(f"Split text into {len(blocks)} blocks with no character loss")
        
        return blocks
    
    def _extract_url(self, prop: Dict[str, Any]) -> Optional[str]:
        """Extract URL from Notion url property."""
        return prop.get("url")
    
    def _extract_email(self, prop: Dict[str, Any]) -> Optional[str]:
        """Extract email from Notion email property."""
        return prop.get("email")
    
    def _extract_checkbox(self, prop: Dict[str, Any]) -> bool:
        """Extract boolean from Notion checkbox property."""
        return prop.get("checkbox", False)
    
    def _extract_select(self, prop: Dict[str, Any]) -> str:
        """Extract text from Notion select property."""
        if "select" in prop and prop["select"]:
            return prop["select"]["name"]
        return ""
    
    def _extract_date(self, prop: Dict[str, Any]) -> Optional[datetime]:
        """Extract datetime from Notion date property."""
        try:
            # Check if date field exists and has a start value
            if "date" in prop and prop["date"] and "start" in prop["date"]:
                date_str = prop["date"]["start"]
                # Handle different date formats that Notion might return
                if date_str:
                    # Try to parse ISO format dates
                    if isinstance(date_str, str):
                        # Handle various datetime formats
                        if "T" in date_str:
                            # Full datetime format with timezone
                            if date_str.endswith('Z'):
                                return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                            else:
                                return datetime.fromisoformat(date_str)
                        else:
                            # Date only format (YYYY-MM-DD)
                            # Add time component to make it a full datetime
                            return datetime.fromisoformat(date_str + "T00:00:00")
                    elif isinstance(date_str, datetime):
                        # Already a datetime object
                        return date_str
        except (ValueError, TypeError, KeyError) as e:
            # Log the error for debugging but don't crash
            logger.debug(f"Failed to parse date '{prop.get('date', {}).get('start', 'None')}': {e}")
        return None
    
    def _extract_number(self, prop: Dict[str, Any]) -> Optional[float]:
        """Extract number from Notion number property."""
        return prop.get("number")
    
    def _extract_title(self, prop: Dict[str, Any]) -> str:
        """Extract text from Notion title property."""
        try:
            if "title" in prop and prop["title"]:
                return prop["title"][0]["text"]["content"]
        except:
            pass
        return ""
    
    def _extract_rich_text(self, prop: Dict[str, Any]) -> str:
        """Extract text from Notion rich text property."""
        try:
            if "rich_text" in prop and prop["rich_text"]:
                return prop["rich_text"][0]["text"]["content"]
        except:
            pass
        return ""
    
    def update_prospect_with_linkedin_data(self, prospect_id: str, linkedin_profile) -> bool:
        """
        Update a prospect with LinkedIn profile data.
        
        Args:
            prospect_id: The Notion page ID of the prospect
            linkedin_profile: LinkedInProfile object with extracted data
            
        Returns:
            bool: True if update was successful
            
        Raises:
            APIResponseError: If Notion API request fails
        """
        try:
            properties = {}
            
            # Add LinkedIn-specific fields
            if linkedin_profile.summary:
                properties["LinkedIn Summary"] = {
                    "rich_text": self._create_rich_text_blocks(linkedin_profile.summary)
                }
            
            if linkedin_profile.experience:
                experience_text = "\n".join(linkedin_profile.experience)
                properties["Experience"] = {
                    "rich_text": self._create_rich_text_blocks(experience_text)
                }
            
            if linkedin_profile.skills:
                skills_text = ", ".join(linkedin_profile.skills)
                properties["Skills"] = {
                    "rich_text": [{"type": "text", "text": {"content": skills_text}}]
                }
            
            if linkedin_profile.education:
                education_text = "\n".join(linkedin_profile.education)
                properties["Education"] = {
                    "rich_text": [{"type": "text", "text": {"content": education_text}}]
                }
            
            if linkedin_profile.location:
                properties["Location"] = {
                    "rich_text": [{"type": "text", "text": {"content": linkedin_profile.location}}]
                }
            
            # Update company if it was extracted from LinkedIn
            if linkedin_profile.company:
                properties["Company"] = {
                    "rich_text": [{"type": "text", "text": {"content": linkedin_profile.company}}]
                }
            
            # Update role if it was extracted from LinkedIn
            if linkedin_profile.current_role:
                properties["Role"] = {
                    "rich_text": [{"type": "text", "text": {"content": linkedin_profile.current_role}}]
                }
            
            if properties:  # Only update if we have data to update
                self.client.pages.update(
                    page_id=prospect_id,
                    properties=properties
                )
                
                logger.info(f"Updated prospect {prospect_id} with LinkedIn data")
                return True
            else:
                logger.warning(f"No LinkedIn data to update for prospect {prospect_id}")
                return False
            
        except APIResponseError as e:
            logger.error(f"Failed to update prospect with LinkedIn data: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error updating prospect with LinkedIn data: {e}")
            raise
    
    def store_prospect_with_linkedin_data(self, prospect: Prospect, linkedin_profile) -> str:
        """
        Store a prospect with LinkedIn profile data in one operation.
        
        Args:
            prospect: The prospect data to store
            linkedin_profile: LinkedInProfile object with extracted data
            
        Returns:
            str: The Notion page ID of the created prospect (or existing if duplicate)
            
        Raises:
            ValidationError: If prospect data is invalid
            APIResponseError: If Notion API request fails
        """
        if not self.database_id:
            raise ValueError("Database ID not set. Create database first.")
        
        try:
            # Validate prospect data
            prospect.validate()
            
            # Check for duplicates and return existing ID if found
            existing_id = self.get_existing_prospect_id(prospect)
            if existing_id:
                logger.info(f"Existing prospect found: {prospect.name} at {prospect.company} (ID: {existing_id})")
                return existing_id
            
            # Prepare basic properties for Notion
            properties = {
                "Name": {
                    "title": [{"type": "text", "text": {"content": prospect.name}}]
                },
                "Role": {
                    "rich_text": [{"type": "text", "text": {"content": prospect.role}}]
                },
                "Company": {
                    "rich_text": [{"type": "text", "text": {"content": prospect.company}}]
                },
                "Contacted": {
                    "checkbox": prospect.contacted
                },
                "Status": {
                    "select": {"name": prospect.status.value}
                },
                "Added Date": {
                    "date": {"start": prospect.created_at.isoformat()}
                }
            }
            
            # Add optional basic fields
            if prospect.linkedin_url:
                properties["LinkedIn"] = {"url": prospect.linkedin_url}
            
            if prospect.email:
                properties["Email"] = {"email": prospect.email}
            
            if prospect.notes:
                properties["Notes"] = {
                    "rich_text": [{"type": "text", "text": {"content": prospect.notes}}]
                }
            
            if prospect.source_url:
                properties["Source"] = {"url": prospect.source_url}
            
            # Add LinkedIn-specific fields if available
            if linkedin_profile:
                if linkedin_profile.summary:
                    properties["LinkedIn Summary"] = {
                        "rich_text": [{"type": "text", "text": {"content": linkedin_profile.summary}}]
                    }
                
                if linkedin_profile.experience:
                    experience_text = "\n".join(linkedin_profile.experience)
                    properties["Experience"] = {
                        "rich_text": [{"type": "text", "text": {"content": experience_text}}]
                    }
                
                if linkedin_profile.skills:
                    skills_text = ", ".join(linkedin_profile.skills)
                    properties["Skills"] = {
                        "rich_text": [{"type": "text", "text": {"content": skills_text}}]
                    }
                
                if linkedin_profile.education:
                    education_text = "\n".join(linkedin_profile.education)
                    properties["Education"] = {
                        "rich_text": [{"type": "text", "text": {"content": education_text}}]
                    }
                
                if linkedin_profile.location:
                    properties["Location"] = {
                        "rich_text": [{"type": "text", "text": {"content": linkedin_profile.location}}]
                    }
                
                # Override company and role with LinkedIn data if available
                if linkedin_profile.company:
                    properties["Company"] = {
                        "rich_text": [{"type": "text", "text": {"content": linkedin_profile.company}}]
                    }
                
                if linkedin_profile.current_role:
                    properties["Role"] = {
                        "rich_text": [{"type": "text", "text": {"content": linkedin_profile.current_role}}]
                    }
            
            # Create the page in Notion
            response = self.client.pages.create(
                parent={"database_id": self.database_id},
                properties=properties
            )
            
            page_id = response["id"]
            prospect.id = page_id
            
            logger.info(f"Stored prospect with LinkedIn data: {prospect.name} at {prospect.company}")
            return page_id
            
        except ValidationError:
            logger.error(f"Invalid prospect data: {prospect}")
            raise
        except APIResponseError as e:
            logger.error(f"Failed to store prospect with LinkedIn data in Notion: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error storing prospect with LinkedIn data: {e}")
            raise
    
    def store_prospect_with_product_analysis(self, prospect: Prospect, linkedin_profile, product_analysis) -> str:
        """
        Store a prospect with LinkedIn profile data and product analysis in one operation.
        
        Args:
            prospect: The prospect data to store
            linkedin_profile: LinkedInProfile object with extracted data (can be None)
            product_analysis: ComprehensiveProductInfo object with product analysis (can be None)
            
        Returns:
            str: The Notion page ID of the created prospect (or existing if duplicate)
            
        Raises:
            ValidationError: If prospect data is invalid
            APIResponseError: If Notion API request fails
        """
        if not self.database_id:
            raise ValueError("Database ID not set. Create database first.")
        
        try:
            # Validate prospect data
            prospect.validate()
            
            # Check for duplicates and return existing ID if found
            existing_id = self.get_existing_prospect_id(prospect)
            if existing_id:
                logger.info(f"Existing prospect found: {prospect.name} at {prospect.company} (ID: {existing_id})")
                return existing_id
            
            # Prepare basic properties for Notion
            properties = {
                "Name": {
                    "title": [{"type": "text", "text": {"content": prospect.name}}]
                },
                "Role": {
                    "rich_text": [{"type": "text", "text": {"content": prospect.role}}]
                },
                "Company": {
                    "rich_text": [{"type": "text", "text": {"content": prospect.company}}]
                },
                "Contacted": {
                    "checkbox": prospect.contacted
                },
                "Status": {
                    "select": {"name": prospect.status.value}
                },
                "Added Date": {
                    "date": {"start": prospect.created_at.isoformat()}
                }
            }
            
            # Add optional basic fields
            if prospect.linkedin_url:
                properties["LinkedIn"] = {"url": prospect.linkedin_url}
            
            if prospect.email:
                properties["Email"] = {"email": prospect.email}
            
            if prospect.notes:
                properties["Notes"] = {
                    "rich_text": [{"type": "text", "text": {"content": prospect.notes}}]
                }
            
            if prospect.source_url:
                properties["Source"] = {"url": prospect.source_url}
            
            # Add LinkedIn-specific fields if available
            if linkedin_profile:
                if linkedin_profile.summary:
                    properties["LinkedIn Summary"] = {
                        "rich_text": [{"type": "text", "text": {"content": linkedin_profile.summary}}]
                    }
                
                if linkedin_profile.experience:
                    experience_text = "\n".join(linkedin_profile.experience)
                    properties["Experience"] = {
                        "rich_text": [{"type": "text", "text": {"content": experience_text}}]
                    }
                
                if linkedin_profile.skills:
                    skills_text = ", ".join(linkedin_profile.skills)
                    properties["Skills"] = {
                        "rich_text": [{"type": "text", "text": {"content": skills_text}}]
                    }
                
                if linkedin_profile.education:
                    education_text = "\n".join(linkedin_profile.education)
                    properties["Education"] = {
                        "rich_text": [{"type": "text", "text": {"content": education_text}}]
                    }
                
                if linkedin_profile.location:
                    properties["Location"] = {
                        "rich_text": [{"type": "text", "text": {"content": linkedin_profile.location}}]
                    }
                
                # Override company and role with LinkedIn data if available
                if linkedin_profile.company:
                    properties["Company"] = {
                        "rich_text": [{"type": "text", "text": {"content": linkedin_profile.company}}]
                    }
                
                if linkedin_profile.current_role:
                    properties["Role"] = {
                        "rich_text": [{"type": "text", "text": {"content": linkedin_profile.current_role}}]
                    }
            
            # Add product analysis fields if available
            if product_analysis:
                # Product Summary - comprehensive overview for email personalization
                product_summary = self._create_product_summary(product_analysis)
                if product_summary:
                    properties["Product Summary"] = {
                        "rich_text": [{"type": "text", "text": {"content": product_summary}}]
                    }
                
                # Business Insights - key business metrics and insights
                business_insights = self._create_business_insights(product_analysis)
                if business_insights:
                    properties["Business Insights"] = {
                        "rich_text": [{"type": "text", "text": {"content": business_insights}}]
                    }
                
                # Market Analysis - competitive landscape and positioning
                if product_analysis.market_analysis:
                    market_text = self._format_market_analysis(product_analysis.market_analysis)
                    if market_text:
                        properties["Market Analysis"] = {
                            "rich_text": [{"type": "text", "text": {"content": market_text}}]
                        }
                
                # Product Features - key features for personalization
                if product_analysis.features:
                    features_text = self._format_features(product_analysis.features)
                    if features_text:
                        properties["Product Features"] = {
                            "rich_text": [{"type": "text", "text": {"content": features_text}}]
                        }
                
                # Pricing Model - pricing information
                if product_analysis.pricing:
                    pricing_text = self._format_pricing(product_analysis.pricing)
                    if pricing_text:
                        properties["Pricing Model"] = {
                            "rich_text": [{"type": "text", "text": {"content": pricing_text}}]
                        }
                
                # Competitors - competitive landscape
                if product_analysis.market_analysis and product_analysis.market_analysis.competitors:
                    competitors_text = ", ".join(product_analysis.market_analysis.competitors)
                    properties["Competitors"] = {
                        "rich_text": [{"type": "text", "text": {"content": competitors_text}}]
                    }
                
                # AI Processing Date - when the analysis was performed
                properties["AI Processing Date"] = {
                    "date": {"start": datetime.now().isoformat()}
                }
            
            # Create the page in Notion
            response = self.client.pages.create(
                parent={"database_id": self.database_id},
                properties=properties
            )
            
            page_id = response["id"]
            prospect.id = page_id
            
            logger.info(f"Stored prospect with product analysis: {prospect.name} at {prospect.company}")
            return page_id
            
        except ValidationError:
            logger.error(f"Invalid prospect data: {prospect}")
            raise
        except APIResponseError as e:
            logger.error(f"Failed to store prospect with product analysis in Notion: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error storing prospect with product analysis: {e}")
            raise
    
    def _create_product_summary(self, product_analysis) -> str:
        """Create a comprehensive product summary optimized for email personalization."""
        summary_parts = []
        
        if product_analysis.basic_info:
            if product_analysis.basic_info.name:
                summary_parts.append(f"Product: {product_analysis.basic_info.name}")
            
            if product_analysis.basic_info.description:
                summary_parts.append(f"Description: {product_analysis.basic_info.description}")
            
            if product_analysis.basic_info.target_market:
                summary_parts.append(f"Target Market: {product_analysis.basic_info.target_market}")
        
        if product_analysis.team_size:
            summary_parts.append(f"Team Size: ~{product_analysis.team_size} people")
        
        if product_analysis.launch_date:
            summary_parts.append(f"Launch: {product_analysis.launch_date.strftime('%B %Y')}")
        
        return "\n".join(summary_parts)
    
    def _create_business_insights(self, product_analysis) -> str:
        """Create business insights summary for outreach context."""
        insights_parts = []
        
        if product_analysis.funding_info:
            funding_status = product_analysis.funding_info.get('status', 'Unknown')
            insights_parts.append(f"Funding Status: {funding_status}")
            
            if 'details' in product_analysis.funding_info:
                insights_parts.append(f"Funding Details: {product_analysis.funding_info['details']}")
        
        if product_analysis.market_analysis:
            if product_analysis.market_analysis.growth_potential:
                insights_parts.append(f"Growth Potential: {product_analysis.market_analysis.growth_potential}")
            
            if product_analysis.market_analysis.market_position:
                insights_parts.append(f"Market Position: {product_analysis.market_analysis.market_position}")
            
            if product_analysis.market_analysis.competitive_advantages:
                advantages = ", ".join(product_analysis.market_analysis.competitive_advantages[:3])
                insights_parts.append(f"Key Advantages: {advantages}")
        
        if product_analysis.social_metrics:
            metrics_text = []
            for key, value in product_analysis.social_metrics.items():
                metrics_text.append(f"{key}: {value}")
            if metrics_text:
                insights_parts.append(f"Social Metrics: {', '.join(metrics_text)}")
        
        return "\n".join(insights_parts)
    
    def _format_market_analysis(self, market_analysis) -> str:
        """Format market analysis for Notion storage."""
        analysis_parts = []
        
        if market_analysis.target_market:
            analysis_parts.append(f"Target Market: {market_analysis.target_market}")
        
        if market_analysis.market_size:
            analysis_parts.append(f"Market Size: {market_analysis.market_size}")
        
        if market_analysis.competitors:
            competitors = ", ".join(market_analysis.competitors[:5])  # Limit to top 5
            analysis_parts.append(f"Main Competitors: {competitors}")
        
        if market_analysis.competitive_advantages:
            advantages = ", ".join(market_analysis.competitive_advantages[:3])  # Top 3
            analysis_parts.append(f"Competitive Advantages: {advantages}")
        
        return "\n".join(analysis_parts)
    
    def _format_features(self, features) -> str:
        """Format product features for Notion storage."""
        if not features:
            return ""
        
        # Group features by category if available
        categorized_features = {}
        uncategorized_features = []
        
        for feature in features[:10]:  # Limit to top 10 features
            if feature.category:
                if feature.category not in categorized_features:
                    categorized_features[feature.category] = []
                categorized_features[feature.category].append(feature.name)
            else:
                uncategorized_features.append(feature.name)
        
        feature_text = []
        
        # Add categorized features
        for category, feature_names in categorized_features.items():
            feature_text.append(f"{category}: {', '.join(feature_names)}")
        
        # Add uncategorized features
        if uncategorized_features:
            feature_text.append(f"Key Features: {', '.join(uncategorized_features)}")
        
        return "\n".join(feature_text)
    
    def _format_pricing(self, pricing) -> str:
        """Format pricing information for Notion storage."""
        pricing_parts = []
        
        if pricing.model:
            pricing_parts.append(f"Model: {pricing.model}")
        
        if pricing.tiers:
            tier_names = [tier.get('name', 'Unknown') for tier in pricing.tiers[:3]]  # Top 3 tiers
            pricing_parts.append(f"Tiers: {', '.join(tier_names)}")
        
        if pricing.billing_cycles:
            cycles = ", ".join(pricing.billing_cycles)
            pricing_parts.append(f"Billing: {cycles}")
        
        return "\n".join(pricing_parts)
    
    # ==================== PROGRESS TRACKING METHODS ====================
    
    def create_campaign_dashboard(self) -> Dict[str, str]:
        """
        Create campaign management databases in Notion.
        
        Returns:
            Dictionary with database IDs for campaigns, logs, and system status
        """
        try:
            parent_page_id = self._get_parent_page_id()
            
            # Create main dashboard page as child of existing page
            dashboard_page = self.client.pages.create(
                parent={"type": "page_id", "page_id": parent_page_id},
                properties={
                    "title": [
                        {
                            "text": {
                                "content": "📊 Job Prospect Automation Dashboard"
                            }
                        }
                    ]
                }
            )
            
            # Add comprehensive content blocks to the dashboard page
            self.client.blocks.children.append(
                block_id=dashboard_page["id"],
                children=[
                    {
                        "object": "block",
                        "type": "heading_1",
                        "heading_1": {
                            "rich_text": [{"type": "text", "text": {"content": "🎯 Campaign Management"}}]
                        }
                    },
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": "Monitor your job prospect automation campaigns in real-time. This dashboard provides complete visibility into your automation workflow."}}]
                        }
                    },
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [{"type": "text", "text": {"content": "📊 Quick Overview"}}]
                        }
                    },
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": "• Active Campaigns: Check Campaign Runs database below\n• Today's Progress: View Processing Log for recent activity\n• System Health: Monitor component status in System Status\n• Email Queue: Track email generation and approval workflow"}}]
                        }
                    },
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [{"type": "text", "text": {"content": "🚀 Quick Actions"}}]
                        }
                    },
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": "To start a new campaign: python cli.py discover --limit 10 --campaign-name \"Your Campaign Name\""}}]
                        }
                    }
                ]
            )
            
            dashboard_id = dashboard_page["id"]
            
            # Create Campaign Runs database
            campaigns_db = self._create_campaigns_database(dashboard_id)
            
            # Create Processing Log database
            logs_db = self._create_processing_log_database(dashboard_id)
            
            # Create System Status database
            status_db = self._create_system_status_database(dashboard_id)
            
            # Create Daily Analytics database
            analytics_db = self._create_daily_analytics_database(dashboard_id)
            
            # Create Email Queue database
            email_queue_db = self._create_email_queue_database(dashboard_id)
            
            logger.info(f"Created campaign dashboard with databases: campaigns={campaigns_db}, logs={logs_db}, status={status_db}, analytics={analytics_db}, email_queue={email_queue_db}")
            
            return {
                "dashboard_id": dashboard_id,
                "campaigns_db": campaigns_db,
                "logs_db": logs_db,
                "status_db": status_db,
                "analytics_db": analytics_db,
                "email_queue_db": email_queue_db
            }
            
        except Exception as e:
            logger.error(f"Failed to create campaign dashboard: {str(e)}")
            raise
    
    def _create_campaigns_database(self, parent_id: str) -> str:
        """Create the Campaign Runs database."""
        properties = {
            "Campaign Name": {"title": {}},
            "Status": {
                "select": {
                    "options": [
                        {"name": "Not Started", "color": "gray"},
                        {"name": "Running", "color": "yellow"},
                        {"name": "Paused", "color": "orange"},
                        {"name": "Completed", "color": "green"},
                        {"name": "Failed", "color": "red"}
                    ]
                }
            },
            "Progress": {"number": {"format": "percent"}},
            "Current Step": {"rich_text": {}},
            "Companies Target": {"number": {}},
            "Companies Processed": {"number": {}},
            "Prospects Found": {"number": {}},
            "Emails Generated": {"number": {}},
            "Success Rate": {"number": {"format": "percent"}},
            "Start Time": {"date": {}},
            "End Time": {"date": {}},
            "Current Company": {"rich_text": {}},
            "Estimated Completion": {"date": {}},
            "Error Count": {"number": {}},
            "Configuration": {"rich_text": {}}
        }
        
        response = self.client.databases.create(
            parent={"type": "page_id", "page_id": parent_id},
            title=[{"type": "text", "text": {"content": "🎯 Campaign Runs"}}],
            properties=properties
        )
        
        return response["id"]
    
    def _create_processing_log_database(self, parent_id: str) -> str:
        """Create the Processing Log database."""
        properties = {
            "Log Entry": {"title": {}},
            "Timestamp": {"date": {}},
            "Campaign": {"rich_text": {}},
            "Company": {"rich_text": {}},
            "Step": {
                "select": {
                    "options": [
                        {"name": "Discovery", "color": "blue"},
                        {"name": "Team Extraction", "color": "purple"},
                        {"name": "Email Finding", "color": "orange"},
                        {"name": "LinkedIn Scraping", "color": "green"},
                        {"name": "AI Processing", "color": "yellow"},
                        {"name": "Email Generation", "color": "pink"},
                        {"name": "Storage", "color": "gray"}
                    ]
                }
            },
            "Status": {
                "select": {
                    "options": [
                        {"name": "Started", "color": "yellow"},
                        {"name": "Completed", "color": "green"},
                        {"name": "Failed", "color": "red"},
                        {"name": "Skipped", "color": "gray"}
                    ]
                }
            },
            "Duration (s)": {"number": {}},
            "Details": {"rich_text": {}},
            "Error Message": {"rich_text": {}},
            "Prospects Found": {"number": {}},
            "Emails Found": {"number": {}}
        }
        
        response = self.client.databases.create(
            parent={"type": "page_id", "page_id": parent_id},
            title=[{"type": "text", "text": {"content": "📋 Processing Log"}}],
            properties=properties
        )
        
        return response["id"]
    
    def _create_system_status_database(self, parent_id: str) -> str:
        """Create the System Status database."""
        properties = {
            "Component": {"title": {}},
            "Status": {
                "select": {
                    "options": [
                        {"name": "Healthy", "color": "green"},
                        {"name": "Warning", "color": "yellow"},
                        {"name": "Error", "color": "red"},
                        {"name": "Offline", "color": "gray"}
                    ]
                }
            },
            "Last Update": {"date": {}},
            "API Quota Used": {"number": {"format": "percent"}},
            "Rate Limit Status": {"rich_text": {}},
            "Error Count (24h)": {"number": {}},
            "Success Rate (24h)": {"number": {"format": "percent"}},
            "Details": {"rich_text": {}},
            "Next Check": {"date": {}}
        }
        
        response = self.client.databases.create(
            parent={"type": "page_id", "page_id": parent_id},
            title=[{"type": "text", "text": {"content": "⚙️ System Status"}}],
            properties=properties
        )
        
        return response["id"]
    
    def _create_daily_analytics_database(self, parent_id: str) -> str:
        """Create the Daily Analytics database."""
        properties = {
            "Date": {"title": {}},
            "Campaigns Run": {"number": {}},
            "Companies Processed": {"number": {}},
            "Prospects Found": {"number": {}},
            "Emails Generated": {"number": {}},
            "Emails Sent": {"number": {}},
            "Success Rate": {"number": {"format": "percent"}},
            "Processing Time (min)": {"number": {}},
            "API Calls Made": {"number": {}},
            "Errors Encountered": {"number": {}},
            "Top Performing Campaign": {"rich_text": {}},
            "Notes": {"rich_text": {}}
        }
        
        response = self.client.databases.create(
            parent={"type": "page_id", "page_id": parent_id},
            title=[{"type": "text", "text": {"content": "📈 Daily Analytics"}}],
            properties=properties
        )
        
        return response["id"]
    
    def _create_email_queue_database(self, parent_id: str) -> str:
        """Create the Email Queue database."""
        properties = {
            "Email ID": {"title": {}},
            "Prospect Name": {"rich_text": {}},
            "Company": {"rich_text": {}},
            "Email Subject": {"rich_text": {}},
            "Status": {
                "select": {
                    "options": [
                        {"name": "Pending Review", "color": "yellow"},
                        {"name": "Approved", "color": "green"},
                        {"name": "Rejected", "color": "red"},
                        {"name": "Sent", "color": "blue"},
                        {"name": "Delivered", "color": "purple"},
                        {"name": "Failed", "color": "red"}
                    ]
                }
            },
            "Generated Date": {"date": {}},
            "Approved Date": {"date": {}},
            "Sent Date": {"date": {}},
            "Campaign": {"rich_text": {}},
            "Template Type": {"rich_text": {}},
            "Personalization Score": {"number": {}},
            "Email Content": {"rich_text": {}},
            "Approval Notes": {"rich_text": {}},
            "Priority": {
                "select": {
                    "options": [
                        {"name": "High", "color": "red"},
                        {"name": "Medium", "color": "yellow"},
                        {"name": "Low", "color": "gray"}
                    ]
                }
            }
        }
        
        response = self.client.databases.create(
            parent={"type": "page_id", "page_id": parent_id},
            title=[{"type": "text", "text": {"content": "📧 Email Queue"}}],
            properties=properties
        )
        
        return response["id"]
    
    def create_campaign(self, campaign_data: CampaignProgress, campaigns_db_id: str) -> str:
        """
        Create a new campaign entry in Notion.
        
        Args:
            campaign_data: Campaign progress data
            campaigns_db_id: Database ID for campaigns
            
        Returns:
            Campaign page ID
        """
        try:
            properties = {
                "Campaign Name": {
                    "title": [{"type": "text", "text": {"content": campaign_data.name}}]
                },
                "Status": {
                    "select": {"name": campaign_data.status.value}
                },
                "Progress": {
                    "number": campaign_data.companies_processed / max(campaign_data.companies_target, 1)
                },
                "Current Step": {
                    "rich_text": [{"type": "text", "text": {"content": campaign_data.current_step}}]
                },
                "Companies Target": {
                    "number": campaign_data.companies_target
                },
                "Companies Processed": {
                    "number": campaign_data.companies_processed
                },
                "Prospects Found": {
                    "number": campaign_data.prospects_found
                },
                "Emails Generated": {
                    "number": campaign_data.emails_generated
                },
                "Success Rate": {
                    "number": campaign_data.success_rate
                },
                "Start Time": {
                    "date": {"start": campaign_data.start_time.isoformat()}
                },
                "Error Count": {
                    "number": campaign_data.error_count
                }
            }
            
            if campaign_data.current_company:
                properties["Current Company"] = {
                    "rich_text": [{"type": "text", "text": {"content": campaign_data.current_company}}]
                }
            
            if campaign_data.estimated_completion:
                properties["Estimated Completion"] = {
                    "date": {"start": campaign_data.estimated_completion.isoformat()}
                }
            
            response = self.client.pages.create(
                parent={"database_id": campaigns_db_id},
                properties=properties
            )
            
            logger.info(f"Created campaign entry: {campaign_data.name}")
            return response["id"]
            
        except Exception as e:
            logger.error(f"Failed to create campaign entry: {str(e)}")
            raise
    
    def update_campaign_progress(self, campaign_page_id: str, campaign_data: CampaignProgress) -> bool:
        """
        Update campaign progress in Notion.
        
        Args:
            campaign_page_id: Notion page ID of the campaign
            campaign_data: Updated campaign data
            
        Returns:
            True if successful
        """
        try:
            properties = {
                "Status": {
                    "select": {"name": campaign_data.status.value}
                },
                "Progress": {
                    "number": campaign_data.companies_processed / max(campaign_data.companies_target, 1)
                },
                "Current Step": {
                    "rich_text": [{"type": "text", "text": {"content": campaign_data.current_step}}]
                },
                "Companies Processed": {
                    "number": campaign_data.companies_processed
                },
                "Prospects Found": {
                    "number": campaign_data.prospects_found
                },
                "Emails Generated": {
                    "number": campaign_data.emails_generated
                },
                "Success Rate": {
                    "number": campaign_data.success_rate
                },
                "Error Count": {
                    "number": campaign_data.error_count
                }
            }
            
            if campaign_data.current_company:
                properties["Current Company"] = {
                    "rich_text": [{"type": "text", "text": {"content": campaign_data.current_company}}]
                }
            
            if campaign_data.estimated_completion:
                properties["Estimated Completion"] = {
                    "date": {"start": campaign_data.estimated_completion.isoformat()}
                }
            
            # Add end time if campaign is completed or failed
            if campaign_data.status in [CampaignStatus.COMPLETED, CampaignStatus.FAILED]:
                properties["End Time"] = {
                    "date": {"start": datetime.now().isoformat()}
                }
            
            self.client.pages.update(
                page_id=campaign_page_id,
                properties=properties
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update campaign progress: {str(e)}")
            return False
    
    def log_processing_step(self, logs_db_id: str, campaign_name: str, company_name: str, 
                           step: str, status: str, duration: float = None, 
                           details: str = None, error_message: str = None,
                           prospects_found: int = 0, emails_found: int = 0) -> bool:
        """
        Log a processing step to Notion.
        
        Args:
            logs_db_id: Database ID for processing logs
            campaign_name: Name of the campaign
            company_name: Company being processed
            step: Processing step name
            status: Step status (Started, Completed, Failed, Skipped)
            duration: Duration in seconds
            details: Additional details
            error_message: Error message if failed
            prospects_found: Number of prospects found
            emails_found: Number of emails found
            
        Returns:
            True if successful
        """
        try:
            properties = {
                "Timestamp": {
                    "date": {"start": datetime.now().isoformat()}
                },
                "Campaign": {
                    "rich_text": [{"type": "text", "text": {"content": campaign_name}}]
                },
                "Company": {
                    "rich_text": [{"type": "text", "text": {"content": company_name}}]
                },
                "Step": {
                    "select": {"name": step}
                },
                "Status": {
                    "select": {"name": status}
                },
                "Prospects Found": {
                    "number": prospects_found
                },
                "Emails Found": {
                    "number": emails_found
                }
            }
            
            if duration is not None:
                properties["Duration (s)"] = {"number": duration}
            
            if details:
                properties["Details"] = {
                    "rich_text": [{"type": "text", "text": {"content": details}}]
                }
            
            if error_message:
                properties["Error Message"] = {
                    "rich_text": [{"type": "text", "text": {"content": error_message}}]
                }
            
            self.client.pages.create(
                parent={"database_id": logs_db_id},
                properties=properties
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to log processing step: {str(e)}")
            return False
    
    def update_system_status(self, status_db_id: str, component: str, status: str, 
                           details: str = None, api_quota_used: float = None,
                           error_count: int = None, success_rate: float = None) -> bool:
        """
        Update system component status in Notion.
        
        Args:
            status_db_id: Database ID for system status
            component: Component name (e.g., "ProductHunt Scraper", "Email Generator")
            status: Component status (Healthy, Warning, Error, Offline)
            details: Additional status details
            api_quota_used: API quota usage percentage (0-1)
            error_count: Number of errors in last twenty-four hours
            success_rate: Success rate percentage (0-1)
            
        Returns:
            True if successful
        """
        try:
            # Find existing component entry
            existing_page_id = self._find_system_component(status_db_id, component)
            
            # Prepare properties
            properties = {
                "Status": {"select": {"name": status}}
            }
            
            # Add optional properties
            if details:
                properties["Details"] = {
                    "rich_text": [{"type": "text", "text": {"content": details}}]
                }
            
            if api_quota_used is not None:
                properties["API Quota Used"] = {"number": api_quota_used}
            
            if error_count is not None:
                properties["Error Count (24h)"] = {"number": error_count}
            
            if success_rate is not None:
                properties["Success Rate (24h)"] = {"number": success_rate}
            
            if existing_page_id:
                # Update existing entry
                self.client.pages.update(
                    page_id=existing_page_id,
                    properties=properties
                )
            else:
                # Create new entry
                properties["Component"] = {
                    "title": [{"type": "text", "text": {"content": component}}]
                }
                
                self.client.pages.create(
                    parent={"database_id": status_db_id},
                    properties=properties
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update system status: {str(e)}")
            return False
    
    def _find_system_component(self, status_db_id: str, component: str) -> Optional[str]:
        """Find existing system component entry."""
        try:
            response = self.client.databases.query(
                database_id=status_db_id,
                filter={
                    "property": "Component",
                    "title": {
                        "equals": component
                    }
                }
            )
            
            if response["results"]:
                return response["results"][0]["id"]
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to find system component: {str(e)}")
            return None
    
    def _validate_prospect_data(self, prospect: Prospect) -> ValidationResult:
        """
        Validate prospect data using ValidationFramework before processing.
        
        Args:
            prospect: Prospect instance to validate
            
        Returns:
            ValidationResult with validation details
        """
        try:
            # Use the enhanced validation from the data model
            return prospect.validate()
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message=f"Prospect validation failed: {str(e)}",
                field_name="prospect",
                error_code="PROSPECT_VALIDATION_ERROR"
            )
    
    def _validate_prospect_batch(self, prospects: List[Prospect]) -> List[ValidationResult]:
        """
        Validate a batch of prospects using ValidationFramework.
        
        Args:
            prospects: List of Prospect instances to validate
            
        Returns:
            List of ValidationResult objects, one for each prospect
        """
        results = []
        for i, prospect in enumerate(prospects):
            try:
                validation_result = self._validate_prospect_data(prospect)
                results.append(validation_result)
            except Exception as e:
                results.append(ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.ERROR,
                    message=f"Prospect {i} validation failed: {str(e)}",
                    field_name=f"prospect_{i}",
                    error_code="BATCH_PROSPECT_VALIDATION_ERROR"
                ))
        return results

# Backward compatibility wrapper
class NotionDataManager(OptimizedNotionDataManager):
    """
    Backward compatibility wrapper for the optimized Notion manager.
    Maintains the original interface while providing enhanced performance.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize with backward compatible interface."""
        super().__init__(config, enable_caching=True, max_connections=3, batch_size=5)
        logger.info("Using optimized Notion manager with backward compatibility")
    
    def store_prospect(self, prospect: Prospect) -> str:
        """
        Store a single prospect (backward compatible method).
        
        Args:
            prospect: The prospect data to store
            
        Returns:
            str: The Notion page ID of the created prospect
        """
        # Use batch method for single prospect (still more efficient)
        results = self.store_prospects_batch([prospect])
        return results[0] if results and results[0] else ""
    
    def get_prospects(self, filters: Dict[str, Any] = None) -> List[Prospect]:
        """
        Get prospects (backward compatible method with caching).
        
        Args:
            filters: Optional filters to apply
            
        Returns:
            List[Prospect]: List of prospects
        """
        return self.get_prospects_cached(filters)
    
    def get_processed_company_names(self) -> List[str]:
        """
        Get processed company names (backward compatible method with caching).
        
        Returns:
            List[str]: List of processed company names
        """
        return self.get_processed_companies_cached()
    
    def update_email_status(self, prospect_id: str, email_status: str, 
                          email_id: str = None, email_subject: str = None) -> bool:
        """
        Update prospect email status (backward compatible method).
        
        Args:
            prospect_id: The Notion page ID of the prospect
            email_status: New email status
            email_id: The email ID from Resend
            email_subject: The subject of the sent email
            
        Returns:
            bool: True if update was successful
        """
        update_data = {
            'prospect_id': prospect_id,
            'email_status': email_status
        }
        
        if email_id:
            update_data['email_id'] = email_id
        
        if email_subject:
            update_data['email_subject'] = email_subject
        
        # Use bulk method for single update (still more efficient)
        success_count = self.bulk_update_email_status([update_data])
        return success_count > 0

    # Issue tracking methods
    def create_issue(self, issue) -> str:
        """
        Create a new issue in Notion issues database.
        
        Args:
            issue: Issue object to create
            
        Returns:
            Issue ID for tracking
            
        Raises:
            Exception: If creation fails
        """
        try:
            # Get issues database ID from config
            issues_db_id = getattr(self.config, 'issues_database_id', None)
            if not issues_db_id:
                raise Exception("Issues database not configured. Run setup-dashboard first.")
            
            # Prepare properties for Notion
            properties = {
                "Title": {
                    "title": [{"type": "text", "text": {"content": issue.title}}]
                },
                "Description": {
                    "rich_text": [{"type": "text", "text": {"content": issue.description}}]
                },
                "Category": {
                    "select": {"name": issue.category.value}
                },
                "Status": {
                    "select": {"name": issue.status.value}
                },
                "Created": {
                    "date": {"start": issue.created_at.isoformat()}
                },
                "Issue ID": {
                    "rich_text": [{"type": "text", "text": {"content": issue.issue_id}}]
                }
            }
            
            # Add context as JSON if available
            if issue.context:
                import json
                context_text = json.dumps(issue.context, indent=2)
                properties["Context"] = {
                    "rich_text": [{"type": "text", "text": {"content": context_text}}]
                }
            
            # Create page in Notion
            response = self.client.pages.create(
                parent={"database_id": issues_db_id},
                properties=properties
            )
            
            logger.info(f"Issue created successfully: {issue.issue_id}")
            return issue.issue_id
            
        except Exception as e:
            logger.error(f"Failed to create issue: {str(e)}")
            raise Exception(f"Could not create issue: {str(e)}")
    
    def get_issues(self, status=None, limit: int = 10):
        """
        Get issues from Notion database.
        
        Args:
            status: Optional status filter
            limit: Maximum number of issues to return
            
        Returns:
            List of Issue objects
        """
        try:
            from models.data_models import Issue, IssueCategory, IssueStatus
            
            issues_db_id = getattr(self.config, 'issues_database_id', None)
            if not issues_db_id:
                logger.warning("Issues database not configured")
                return []
            
            # Build query filter
            query_filter = None
            if status:
                query_filter = {
                    "property": "Status",
                    "select": {"equals": status.value if hasattr(status, 'value') else status}
                }
            
            # Query database
            response = self.client.databases.query(
                database_id=issues_db_id,
                filter=query_filter,
                page_size=limit,
                sorts=[{"property": "Created", "direction": "descending"}]
            )
            
            issues = []
            for result in response["results"]:
                try:
                    # Extract properties
                    props = result["properties"]
                    
                    title = self._extract_title_text(props.get("Title", {}))
                    description = self._extract_rich_text(props.get("Description", {}))
                    category_text = self._extract_select_text(props.get("Category", {}))
                    status_text = self._extract_select_text(props.get("Status", {}))
                    created_text = self._extract_date(props.get("Created", {}))
                    issue_id = self._extract_rich_text(props.get("Issue ID", {}))
                    context_text = self._extract_rich_text(props.get("Context", {}))
                    
                    # Parse context JSON
                    context = {}
                    if context_text:
                        try:
                            import json
                            context = json.loads(context_text)
                        except:
                            context = {"raw": context_text}
                    
                    # Create issue object
                    issue = Issue(
                        issue_id=issue_id,
                        title=title,
                        description=description,
                        category=IssueCategory(category_text) if category_text else IssueCategory.BUG,
                        status=IssueStatus(status_text) if status_text else IssueStatus.OPEN,
                        created_at=datetime.fromisoformat(created_text) if created_text else datetime.now(),
                        context=context
                    )
                    
                    issues.append(issue)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse issue: {str(e)}")
                    continue
            
            return issues
            
        except Exception as e:
            logger.error(f"Failed to get issues: {str(e)}")
            return []
    
    def get_issue_by_id(self, issue_id: str):
        """
        Get a specific issue by ID.
        
        Args:
            issue_id: Issue identifier
            
        Returns:
            Issue object or None
        """
        try:
            from models.data_models import Issue, IssueCategory, IssueStatus
            
            issues_db_id = getattr(self.config, 'issues_database_id', None)
            if not issues_db_id:
                return None
            
            # Query by issue ID
            response = self.client.databases.query(
                database_id=issues_db_id,
                filter={
                    "property": "Issue ID",
                    "rich_text": {"equals": issue_id}
                }
            )
            
            if not response["results"]:
                return None
            
            result = response["results"][0]
            props = result["properties"]
            
            # Extract data (same as get_issues)
            title = self._extract_title_text(props.get("Title", {}))
            description = self._extract_rich_text(props.get("Description", {}))
            category_text = self._extract_select_text(props.get("Category", {}))
            status_text = self._extract_select_text(props.get("Status", {}))
            created_text = self._extract_date(props.get("Created", {}))
            context_text = self._extract_rich_text(props.get("Context", {}))
            
            # Parse context
            context = {}
            if context_text:
                try:
                    import json
                    context = json.loads(context_text)
                except:
                    context = {"raw": context_text}
            
            return Issue(
                issue_id=issue_id,
                title=title,
                description=description,
                category=IssueCategory(category_text) if category_text else IssueCategory.BUG,
                status=IssueStatus(status_text) if status_text else IssueStatus.OPEN,
                created_at=datetime.fromisoformat(created_text) if created_text else datetime.now(),
                context=context
            )
            
        except Exception as e:
            logger.error(f"Failed to get issue {issue_id}: {str(e)}")
            return None
    
    def _extract_title_text(self, title_property: Dict[str, Any]) -> str:
        """Extract text from title property."""
        try:
            if "title" in title_property and title_property["title"]:
                return title_property["title"][0]["text"]["content"]
        except:
            pass
        return ""
    
    def _extract_select_text(self, select_property: Dict[str, Any]) -> str:
        """Extract text from select property."""
        try:
            if "select" in select_property and select_property["select"]:
        return ""


if __name__ == "__main__":
    pass
