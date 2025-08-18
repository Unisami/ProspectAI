"""
Main controller for orchestrating the job prospect automation workflow.
"""

import logging
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
import time
import json
from dataclasses import dataclass, asdict
from enum import Enum
import threading

from models.data_models import CompanyData, TeamMember, Prospect, ProspectStatus, LinkedInProfile
from services.product_hunt_scraper import ProductHuntScraper, ProductData
from services.notion_manager import NotionDataManager, CampaignProgress, CampaignStatus
from services.email_finder import EmailFinder
from services.linkedin_scraper import LinkedInScraper
from services.email_generator import EmailGenerator, EmailTemplate
from services.email_sender import EmailSender
from services.product_analyzer import ProductAnalyzer, ComprehensiveProductInfo
from services.ai_service import AIService, AIOperationType, AIResult, EmailTemplate as AIEmailTemplate
from services.openai_client_manager import CompletionRequest
from utils.config import Config
from utils.configuration_service import get_configuration_service
from utils.logging_config import get_logger


class ProcessingStatus(Enum):
    """Status enum for batch processing."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


@dataclass
class BatchProgress:
    """Data model for tracking batch processing progress."""
    batch_id: str
    status: ProcessingStatus
    total_companies: int
    processed_companies: int
    successful_companies: int
    failed_companies: int
    total_prospects: int
    start_time: datetime
    last_update_time: datetime
    end_time: Optional[datetime] = None
    current_company: Optional[str] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['status'] = self.status.value
        data['start_time'] = self.start_time.isoformat()
        data['last_update_time'] = self.last_update_time.isoformat()
        if self.end_time:
            data['end_time'] = self.end_time.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BatchProgress':
        """Create from dictionary."""
        data['status'] = ProcessingStatus(data['status'])
        data['start_time'] = datetime.fromisoformat(data['start_time'])
        data['last_update_time'] = datetime.fromisoformat(data['last_update_time'])
        if data.get('end_time'):
            data['end_time'] = datetime.fromisoformat(data['end_time'])
        return cls(**data)


@dataclass
class CompanyProcessingResult:
    """Result of processing a single company."""
    company_name: str
    success: bool
    prospects_found: int
    emails_found: int
    linkedin_profiles_found: int
    error_message: Optional[str] = None
    processing_time: Optional[float] = None


class ProspectAutomationController:
    """
    Main controller class that orchestrates all components of the prospect automation system.
    
    This class manages the complete workflow:
    1. Discovery: Scrape ProductHunt for new companies
    2. Extraction: Extract team member information
    3. Enrichment: Find emails and LinkedIn data
    4. Storage: Store organized data in Notion
    5. Outreach: Generate personalized emails
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the controller with all required services.
        
        Args:
            config: Configuration object (deprecated, use ConfigurationService)
        """
        # Use ConfigurationService for centralized configuration management
        if config:
            # Backward compatibility: if config is provided, use it directly
            self.logger = get_logger(__name__)
            self.logger.warning("Direct config parameter is deprecated. Consider using ConfigurationService.")
            self.config = config
        else:
            # Use centralized configuration service
            config_service = get_configuration_service()
            self.config = config_service.get_config()
            self.logger = get_logger(__name__)
        
        # Initialize all services
        try:
            self.product_hunt_scraper = ProductHuntScraper(self.config)
            self.notion_manager = NotionDataManager(self.config)
            self.email_finder = EmailFinder(self.config)
            self.linkedin_scraper = LinkedInScraper(self.config)
            
            # Initialize email generator with error handling
            try:
                self.email_generator = EmailGenerator(config=self.config)
                self.logger.info("Email generator initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize email generator: {str(e)}")
                raise
            
            self.email_sender = EmailSender(config=self.config, notion_manager=self.notion_manager)
            self.product_analyzer = ProductAnalyzer(self.config)
            
            # Initialize consolidated AI Service for all AI operations
            try:
                self.ai_service = AIService(self.config, "prospect_controller")
                self.use_ai_processing = True
                self.logger.info("AI Service initialized successfully")
            except Exception as e:
                self.logger.warning(f"Failed to initialize AI Service: {str(e)}. Falling back to traditional processing.")
                self.ai_service = None
                self.use_ai_processing = False
            
            # Initialize sender profile if enabled
            self.sender_profile = None
            if self.config.enable_sender_profile:
                try:
                    self.sender_profile = self._load_sender_profile()
                    if self.sender_profile:
                        self.logger.info(f"Sender profile loaded successfully: {self.sender_profile.name}")
                    else:
                        self.logger.warning("No sender profile loaded")
                except Exception as e:
                    self.logger.error(f"Failed to load sender profile: {str(e)}")
                    if config.require_sender_profile:
                        raise ValueError(f"Sender profile is required but could not be loaded: {str(e)}")
            
            self.logger.info("ProspectAutomationController initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize controller: {str(e)}")
            raise
        
        # Enhanced workflow statistics with thread safety
        self.stats_lock = threading.Lock()
        self.stats = {
            'companies_processed': 0,
            'prospects_found': 0,
            'emails_found': 0,
            'linkedin_profiles_extracted': 0,
            'emails_generated': 0,
            'ai_parsing_successes': 0,
            'ai_parsing_failures': 0,
            'product_analyses_completed': 0,
            'ai_structured_data_created': 0,
            'emails_sent': 0,
            'errors': 0,
            'start_time': None,
            'end_time': None
        }
        
        # Batch processing state
        self.current_batch: Optional[BatchProgress] = None
        self.batch_results: List[CompanyProcessingResult] = []
        self.progress_callbacks: List[Callable[[BatchProgress], None]] = []
        
        # Progress tracking configuration
        self.dashboard_config = {
            'campaigns_db_id': getattr(config, 'campaigns_db_id', None),
            'logs_db_id': getattr(config, 'logs_db_id', None),
            'status_db_id': getattr(config, 'status_db_id', None),
            'analytics_db_id': getattr(config, 'analytics_db_id', None),
            'email_queue_db_id': getattr(config, 'email_queue_db_id', None),
            'enable_progress_tracking': getattr(config, 'enable_progress_tracking', True)
        }
        
        # Current campaign tracking
        self.current_campaign: Optional[CampaignProgress] = None
        self.campaign_page_id: Optional[str] = None
        
        # Initialize notification manager
        try:
            from services.notification_manager import NotificationManager
            self.notification_manager = NotificationManager(config, self.notion_manager)
            self.logger.info("Notification manager initialized successfully")
        except Exception as e:
            self.logger.warning(f"Failed to initialize notification manager: {str(e)}")
            self.notification_manager = None
        
        # Interactive controls removed for simplicity
        
        # Cache for processed companies to avoid repeated API calls during a single run
        self._processed_companies_cache = None
        self._processed_domains_cache = None
        self._cache_timestamp = None
        self._cache_ttl = 300  # 5 minutes cache TTL
    
    def _get_cached_processed_companies(self) -> tuple[List[str], List[str]]:
        """
        Get cached processed companies and domains, refreshing if needed.
        
        Returns:
            Tuple of (company_names, domains)
        """
        import time
        current_time = time.time()
        
        # Check if cache is valid
        if (self._cache_timestamp is None or 
            current_time - self._cache_timestamp > self._cache_ttl or
            self._processed_companies_cache is None or
            self._processed_domains_cache is None):
            
            self.logger.info("🔄 Refreshing processed companies cache...")
            
            # Refresh cache
            self._processed_companies_cache = self.notion_manager.get_processed_company_names()
            self._processed_domains_cache = self.notion_manager.get_processed_company_domains()
            self._cache_timestamp = current_time
            
            self.logger.info(f"📊 Cache refreshed: {len(self._processed_companies_cache)} companies, {len(self._processed_domains_cache)} domains")
        
        return self._processed_companies_cache, self._processed_domains_cache
    
    def _clear_processed_companies_cache(self):
        """Clear the processed companies cache to force refresh on next access."""
        self._processed_companies_cache = None
        self._processed_domains_cache = None
        self._cache_timestamp = None
        self.logger.debug("🗑️ Cleared processed companies cache")
    
    def _update_stats_thread_safe(self, **kwargs):
        """Thread-safe method to update stats."""
        with self.stats_lock:
            for key, value in kwargs.items():
                if key in self.stats:
                    if isinstance(value, (int, float)):
                        self.stats[key] += value
                    else:
                        self.stats[key] = value
        
    def _load_sender_profile(self):
        """
        Load sender profile based on configuration.
        
        Returns:
            SenderProfile instance or None if not configured
        """
        from services.sender_profile_manager import SenderProfileManager
        import os
        
        if not self.config.enable_sender_profile:
            return None
            
        profile_manager = SenderProfileManager()
        
        # If profile path is provided, load from file
        if self.config.sender_profile_path:
            try:
                if os.path.exists(self.config.sender_profile_path):
                    self.logger.info(f"Loading sender profile from {self.config.sender_profile_path}")
                    
                    if self.config.sender_profile_format == "markdown":
                        return profile_manager.load_profile_from_markdown(self.config.sender_profile_path)
                    elif self.config.sender_profile_format == "json":
                        return profile_manager.load_profile_from_json(self.config.sender_profile_path)
                    elif self.config.sender_profile_format == "yaml":
                        return profile_manager.load_profile_from_yaml(self.config.sender_profile_path)
                    else:
                        self.logger.error(f"Unsupported profile format: {self.config.sender_profile_format}")
                        return None
                else:
                    self.logger.warning(f"Sender profile file not found: {self.config.sender_profile_path}")
                    
                    # If interactive setup is enabled, create profile interactively
                    if self.config.enable_interactive_profile_setup:
                        self.logger.info("Starting interactive profile setup")
                        profile = profile_manager.create_profile_interactively()
                        
                        # Save the created profile
                        if profile:
                            os.makedirs(os.path.dirname(self.config.sender_profile_path), exist_ok=True)
                            
                            if self.config.sender_profile_format == "markdown":
                                profile_manager.save_profile_to_markdown(profile, self.config.sender_profile_path)
                            elif self.config.sender_profile_format == "json":
                                profile_manager.save_profile_to_json(profile, self.config.sender_profile_path)
                            elif self.config.sender_profile_format == "yaml":
                                profile_manager.save_profile_to_yaml(profile, self.config.sender_profile_path)
                                
                            self.logger.info(f"Saved sender profile to {self.config.sender_profile_path}")
                            return profile
                    
                    return None
            except Exception as e:
                self.logger.error(f"Failed to load sender profile: {str(e)}")
                
                # If interactive setup is enabled, create profile interactively
                if self.config.enable_interactive_profile_setup:
                    self.logger.info("Starting interactive profile setup after load failure")
                    return profile_manager.create_profile_interactively()
                    
                return None
        
        # If no profile path but interactive setup is enabled, create profile interactively
        elif self.config.enable_interactive_profile_setup:
            self.logger.info("Starting interactive profile setup (no path provided)")
            return profile_manager.create_profile_interactively()
            
        return None
    
    def run_discovery_pipeline(self, limit: Optional[int] = None, campaign_name: str = None) -> Dict[str, Any]:
        """
        Run the complete discovery pipeline to find and process prospects with progress tracking.
        
        Args:
            limit: Optional limit on number of companies to process
            campaign_name: Optional campaign name for tracking
            
        Returns:
            Dictionary containing pipeline results and statistics
        """
        self.logger.info("Starting discovery pipeline with progress tracking")
        self.stats['start_time'] = datetime.now()
        
        # Initialize campaign tracking
        campaign_name = campaign_name or f"Discovery Campaign {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        target_limit = limit or self.config.max_products_per_run
        
        try:
            # Initialize campaign progress tracking
            self._start_campaign_tracking(campaign_name, target_limit)
            
            # Step 1: Discover companies from ProductHunt
            self._update_campaign_step("Company Discovery")
            self._log_processing_step(campaign_name, "System", "Discovery", "Started", 
                                    details=f"Discovering up to {target_limit} companies from ProductHunt")
            
            companies = self._discover_companies(target_limit)
            
            if not companies:
                self.logger.warning("No companies discovered from ProductHunt")
                self._complete_campaign_tracking(CampaignStatus.COMPLETED)
                return self._get_pipeline_results()
            
            self.logger.info(f"Discovered {len(companies)} companies from ProductHunt")
            self._log_processing_step(campaign_name, "System", "Discovery", "Completed", 
                                    details=f"Found {len(companies)} companies")
            
            # Update campaign with actual company count
            self._update_campaign_companies_target(len(companies))
            
            # Step 2: Process companies in parallel for better performance
            self._update_campaign_step("Processing Companies in Parallel")
            self.logger.info(f"Processing {len(companies)} companies in parallel")
            
            # Import parallel processor
            from services.parallel_processor import ParallelProcessor
            
            # Initialize parallel processor with optimal settings for I/O-bound operations
            # Optimize for I/O-bound operations (web scraping, API calls)
            # Most time is spent waiting, so we can use more workers safely
            max_workers = min(6, max(2, len(companies)))  # 2-6 workers for optimal I/O parallelism
            parallel_processor = ParallelProcessor(max_workers=max_workers)
            
            # Define progress callback
            def progress_callback(company_name: str, completed: int, total: int):
                self._update_campaign_step(f"Processing Companies ({completed}/{total})")
                self._update_campaign_current_company(company_name)
                self.logger.info(f"Progress: {completed}/{total} companies processed")
            
            # Process companies in parallel
            processing_results = parallel_processor.process_companies_parallel(
                companies=companies,
                process_function=self.process_company,
                progress_callback=progress_callback
            )
            
            # Process results and update stats (thread-safe aggregation)
            total_prospects_found = 0
            total_emails_found = 0
            successful_companies = 0
            
            for result in processing_results:
                if result.success:
                    successful_companies += 1
                    prospects_found = len(result.prospects)
                    emails_found = len([p for p in result.prospects if p.email])
                    
                    # Aggregate totals
                    total_prospects_found += prospects_found
                    total_emails_found += emails_found
                    
                    # Log successful processing
                    self._log_processing_step(
                        campaign_name, result.company_name, "Processing", "Completed",
                        duration=result.duration,
                        details=f"Found {prospects_found} prospects, {emails_found} emails",
                        prospects_found=prospects_found,
                        emails_found=emails_found
                    )
                    
                    # Update campaign progress
                    self._update_campaign_progress()
                    
                    self.logger.info(f"✅ {result.company_name}: {prospects_found} prospects, {emails_found} emails in {result.duration:.1f}s")
                    
                else:
                    self.stats['errors'] += 1
                    
                    # Log failed processing
                    self._log_processing_step(
                        campaign_name, result.company_name, "Processing", "Failed",
                        duration=result.duration,
                        error_message=result.error_message
                    )
                    
                    # Send error notification for critical failures
                    if self.notification_manager and self.stats['errors'] >= 3:
                        error_data = {
                            'component': 'Company Processing',
                            'error_message': result.error_message,
                            'campaign_name': campaign_name,
                            'company_name': result.company_name
                        }
                        self.notification_manager.send_error_alert(error_data)
                    
                    self.logger.error(f"❌ {result.company_name}: {result.error_message}")
            
            # Update final stats (thread-safe) - don't override, just ensure consistency
            with self.stats_lock:
                self.stats['companies_processed'] = successful_companies
                # Don't override prospects_found and emails_found as they're updated by threads
                # Just log the totals for verification
                self.logger.info(f"Stats verification: Thread-safe stats show {self.stats['prospects_found']} prospects, {self.stats['emails_found']} emails")
                self.logger.info(f"Parallel results show: {total_prospects_found} prospects, {total_emails_found} emails")
            
            self.logger.info(f"📊 Parallel processing summary: {successful_companies} companies, {total_prospects_found} prospects, {total_emails_found} emails")
            
            # Log parallel processing summary
            parallel_stats = parallel_processor.get_processing_stats()
            self.logger.info(f"Parallel processing completed: {parallel_stats['successful_companies']}/{parallel_stats['total_companies']} companies successful in {parallel_stats['total_duration']:.1f}s")
            
            # Complete campaign tracking
            self.stats['end_time'] = datetime.now()
            self._complete_campaign_tracking(CampaignStatus.COMPLETED)
            
            results = self._get_pipeline_results()
            
            # Send intelligent completion notification
            if self.notification_manager and self.current_campaign:
                campaign_data = {
                    'name': self.current_campaign.name,
                    'companies_processed': self.current_campaign.companies_processed,
                    'prospects_found': self.current_campaign.prospects_found,
                    'success_rate': self.current_campaign.success_rate,
                    'duration_minutes': (self.stats['end_time'] - self.stats['start_time']).total_seconds() / 60,
                    'status': 'Completed'
                }
                
                # Send notification with appropriate priority based on results
                self.notification_manager.send_campaign_completion_notification(campaign_data)
                
                # Also update daily summary automatically
                if self.dashboard_config.get('analytics_db_id'):
                    self.create_daily_summary(self.dashboard_config['analytics_db_id'])
            
            self.logger.info("Discovery pipeline completed successfully")
            self.logger.info(f"Pipeline summary: {results['summary']}")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Discovery pipeline failed: {str(e)}")
            self.stats['errors'] += 1
            self.stats['end_time'] = datetime.now()
            
            # Mark campaign as failed
            self._complete_campaign_tracking(CampaignStatus.FAILED)
            self._log_processing_step(campaign_name, "System", "Pipeline", "Failed", 
                                    error_message=str(e))
            
            raise
    
    def process_company(self, company_data: CompanyData) -> List[Prospect]:
        """
        Process a single company through the enhanced workflow with AI structuring.
        
        Args:
            company_data: Company information from ProductHunt
            
        Returns:
            List of processed prospects
        """
        self.logger.info(f"Processing company: {company_data.name}")
        prospects = []
        
        try:
            # Step 1: Analyze product comprehensively using AI-enhanced analysis
            self.logger.info(f"Step 1: Analyzing product for {company_data.name}")
            product_analysis = self._analyze_product_with_ai_structuring(company_data)
            if product_analysis:
                self._update_stats_thread_safe(product_analyses_completed=1)
            
            # Step 2: Extract team members with AI-enhanced parsing
            self.logger.info(f"Step 2: Extracting team members for {company_data.name}")
            team_members = self._extract_team_members_with_ai(company_data)
            
            if not team_members:
                self.logger.warning(f"No team members found for {company_data.name}")
                return prospects
            
            self.logger.info(f"Found {len(team_members)} team members for {company_data.name}")
            
            # Step 3: Find emails for team members
            self.logger.info(f"Step 3: Finding emails for team members")
            email_results = self._find_team_emails(team_members, company_data.domain)
            
            # Step 4: Extract LinkedIn profiles with AI-enhanced parsing
            self.logger.info(f"Step 4: Extracting LinkedIn profiles with AI parsing")
            linkedin_profiles = self._extract_linkedin_profiles_with_ai(team_members)
            
            # Step 5: Structure all data with AI and store in Notion
            self.logger.info(f"Step 5: Structuring data with AI and storing prospects")
            for team_member in team_members:
                try:
                    prospect = self._create_prospect_from_team_member(
                        team_member, 
                        company_data,
                        email_results.get(team_member.name),
                        linkedin_profiles.get(team_member.linkedin_url) if team_member.linkedin_url else None
                    )
                    
                    if prospect:
                        # First, store the prospect in Notion to get an ID
                        try:
                            page_id = self.notion_manager.store_prospect(prospect)
                            if page_id:
                                prospect.id = page_id
                                self.logger.info(f"Stored prospect {prospect.name} with ID: {page_id}")
                            else:
                                self.logger.warning(f"Failed to store prospect {prospect.name} - no ID returned")
                                continue
                        except Exception as e:
                            self.logger.error(f"Failed to store prospect {prospect.name}: {str(e)}")
                            continue
                        
                        # Get LinkedIn profile for this team member
                        linkedin_profile = linkedin_profiles.get(team_member.linkedin_url) if team_member.linkedin_url else None
                        
                        # Structure all data with AI for email personalization
                        ai_structured_data = self._structure_prospect_data_with_ai(
                            prospect, linkedin_profile, product_analysis, company_data
                        )
                        
                        # Store AI-structured data now that we have a prospect ID
                        if ai_structured_data and prospect.id:
                            try:
                                self.notion_manager.store_ai_structured_data(
                                    prospect_id=prospect.id,
                                    product_summary=ai_structured_data.get('product_summary'),
                                    business_insights=ai_structured_data.get('business_insights'),
                                    linkedin_summary=ai_structured_data.get('linkedin_summary'),
                                    personalization_data=ai_structured_data.get('personalization_data')
                                )
                                self._update_stats_thread_safe(ai_structured_data_created=1)
                                self.logger.info(f"Stored AI-structured data for {prospect.name}")
                            except Exception as e:
                                self.logger.error(f"Failed to store AI-structured data for {prospect.name}: {str(e)}")
                        
                        # Add to results
                        prospects.append(prospect)
                        
                        # Thread-safe stats updates
                        stats_update = {'prospects_found': 1}
                        if prospect.email:
                            stats_update['emails_found'] = 1
                        if linkedin_profile:
                            stats_update['linkedin_profiles_extracted'] = 1
                        
                        self._update_stats_thread_safe(**stats_update)
                        
                        self.logger.info(f"Successfully processed prospect with AI structuring: {prospect.name}")
                        
                except Exception as e:
                    self.logger.error(f"Failed to process team member {team_member.name}: {str(e)}")
                    continue
            
            self.logger.info(f"Successfully processed {len(prospects)} prospects for {company_data.name} with AI enhancement")
            
            # Clear cache since we've added new prospects for this company
            if prospects:
                self._clear_processed_companies_cache()
            
            return prospects
            
        except Exception as e:
            self.logger.error(f"Failed to process company {company_data.name}: {str(e)}")
            raise
    
    def generate_outreach_emails(self, prospect_ids: List[str], 
                               template_type: EmailTemplate = EmailTemplate.COLD_OUTREACH) -> Dict[str, Any]:
        """
        Generate personalized outreach emails for specified prospects.
        
        Args:
            prospect_ids: List of Notion page IDs for prospects
            template_type: Type of email template to use
            
        Returns:
            Dictionary containing email generation results
        """
        self.logger.info(f"Generating outreach emails for {len(prospect_ids)} prospects")
        
        results = {
            'successful': [],
            'failed': [],
            'emails_generated': 0,
            'errors': 0
        }
        
        # Check if sender profile is required but not available
        if self.config.require_sender_profile and not self.sender_profile:
            error_msg = "Sender profile is required but not available"
            self.logger.error(error_msg)
            results['errors'] += 1
            for prospect_id in prospect_ids:
                results['failed'].append({
                    'prospect_id': prospect_id,
                    'error': error_msg
                })
            return results
        
        try:
            # Get prospect data from Notion
            prospects = self.notion_manager.get_prospects()
            target_prospects = [p for p in prospects if p.id in prospect_ids]
            
            if not target_prospects:
                self.logger.warning("No matching prospects found for email generation")
                return results
            
            for prospect in target_prospects:
                try:
                    self.logger.info(f"Generating email for {prospect.name} at {prospect.company}")
                    
                    # PERFORMANCE OPTIMIZATION: Skip LinkedIn extraction if unlikely to succeed
                    linkedin_profile = None
                    if prospect.linkedin_url and self._should_extract_linkedin_profile_for_prospect(prospect):
                        linkedin_profile = self.linkedin_scraper.extract_profile_data(prospect.linkedin_url)
                    
                    # Get product analysis data from Notion if available
                    product_analysis = self.notion_manager.get_prospect_data_for_email(prospect.id)
                    
                    # Generate email using consolidated AI Service
                    start_time = time.time()
                    if self.use_ai_processing and self.ai_service:
                        # Use consolidated AI Service for email generation
                        ai_result = self.ai_service.generate_email(
                            prospect=prospect,
                            template_type=template_type,
                            linkedin_profile=linkedin_profile,
                            product_analysis=product_analysis,
                            additional_context={
                                'source_mention': 'ProductHunt',
                                'discovery_context': f'I discovered {prospect.company} on ProductHunt'
                            },
                            sender_profile=self.sender_profile
                        )
                        
                        if ai_result.success:
                            email_content = ai_result.data
                        else:
                            raise Exception(f"AI email generation failed: {ai_result.error_message}")
                    else:
                        # Fallback to traditional email generator
                        email_content = self.email_generator.generate_outreach_email(
                            prospect=prospect,
                            template_type=template_type,
                            linkedin_profile=linkedin_profile,
                            product_analysis=product_analysis,
                            additional_context={
                                'source_mention': 'ProductHunt',
                                'discovery_context': f'I discovered {prospect.company} on ProductHunt'
                            },
                            sender_profile=self.sender_profile
                        )
                    generation_time = time.time() - start_time
                    
                    # Prepare generation metadata
                    generation_metadata = {
                        'sender_profile_name': self.sender_profile.name if self.sender_profile else None,
                        'model_used': self.config.email_generation_model,
                        'generation_time': generation_time,
                        'template_type': template_type.value
                    }
                    
                    # Store email content in Notion
                    try:
                        self.notion_manager.store_email_content(
                            prospect_id=prospect.id,
                            email_content=email_content,
                            generation_metadata=generation_metadata
                        )
                        self.logger.info(f"Stored email content in Notion for {prospect.name}")
                    except Exception as e:
                        self.logger.error(f"Failed to store email content in Notion for {prospect.name}: {str(e)}")
                        # Continue with the process even if storage fails
                    
                    results['successful'].append({
                        'prospect_id': prospect.id,
                        'prospect_name': prospect.name,
                        'company': prospect.company,
                        'email_content': email_content.to_dict(),
                        'sender_profile_used': self.sender_profile is not None,
                        'generation_time': generation_time,
                        'stored_in_notion': True
                    })
                    
                    results['emails_generated'] += 1
                    self.stats['emails_generated'] += 1
                    
                    self.logger.info(f"Successfully generated and stored email for {prospect.name}")
                    
                except Exception as e:
                    self.logger.error(f"Failed to generate email for {prospect.name}: {str(e)}")
                    results['failed'].append({
                        'prospect_id': prospect.id,
                        'prospect_name': prospect.name,
                        'error': str(e)
                    })
                    results['errors'] += 1
                    continue
            
            self.logger.info(f"Email generation completed: {results['emails_generated']} successful, {results['errors']} failed")
            return results
            
        except Exception as e:
            self.logger.error(f"Email generation process failed: {str(e)}")
            raise
    
    def generate_and_send_outreach_emails(
        self, 
        prospect_ids: List[str], 
        template_type: EmailTemplate = EmailTemplate.COLD_OUTREACH,
        send_immediately: bool = True,
        delay_between_emails: float = 2.0
    ) -> Dict[str, Any]:
        """
        Generate and send personalized outreach emails using AI-structured data.
        
        Args:
            prospect_ids: List of Notion page IDs for prospects
            template_type: Type of email template to use
            send_immediately: Whether to send emails immediately or just generate them
            delay_between_emails: Delay in seconds between sending emails
            
        Returns:
            Dictionary containing email generation and sending results
        """
        self.logger.info(f"Generating and sending outreach emails for {len(prospect_ids)} prospects")
        
        results = {
            'successful': [],
            'failed': [],
            'emails_generated': 0,
            'emails_sent': 0,
            'errors': 0,
            'send_immediately': send_immediately,
            'sender_profile_used': self.sender_profile is not None
        }
        
        # Check if sender profile is required but not available
        if self.config.require_sender_profile and not self.sender_profile:
            error_msg = "Sender profile is required but not available"
            self.logger.error(error_msg)
            results['errors'] += 1
            for prospect_id in prospect_ids:
                results['failed'].append({
                    'prospect_id': prospect_id,
                    'error': error_msg
                })
            return results
        
        try:
            # Use the enhanced email generation and sending workflow
            if send_immediately:
                # Generate and send emails with rate limiting
                email_results = self.email_generator.generate_and_send_bulk_emails(
                    prospect_ids=prospect_ids,
                    notion_manager=self.notion_manager,
                    email_sender=self.email_sender,
                    template_type=template_type,
                    delay_between_emails=delay_between_emails,
                    additional_context={
                        'source_mention': 'ProductHunt',
                        'discovery_context': 'I discovered your company on ProductHunt'
                    },
                    sender_profile=self.sender_profile
                )
            else:
                # Just generate emails without sending
                email_results = []
                for prospect_id in prospect_ids:
                    try:
                        result = self.email_generator.generate_and_send_email(
                            prospect_id=prospect_id,
                            notion_manager=self.notion_manager,
                            email_sender=self.email_sender,
                            template_type=template_type,
                            send_immediately=False,
                            additional_context={
                                'source_mention': 'ProductHunt',
                                'discovery_context': 'I discovered your company on ProductHunt'
                            },
                            sender_profile=self.sender_profile
                        )
                        email_results.append(result)
                    except Exception as e:
                        self.logger.error(f"Failed to generate email for prospect {prospect_id}: {str(e)}")
                        email_results.append({
                            'prospect_id': prospect_id,
                            'error': str(e),
                            'sent': False,
                            'generated_at': datetime.now().isoformat()
                        })
            
            # Process results
            for result in email_results:
                if result.get('error'):
                    results['failed'].append({
                        'prospect_id': result['prospect_id'],
                        'error': result['error']
                    })
                    results['errors'] += 1
                else:
                    # Get prospect data for result
                    prospect_data = self.notion_manager.get_prospect_data_for_email(result['prospect_id'])
                    
                    success_result = {
                        'prospect_id': result['prospect_id'],
                        'prospect_name': prospect_data.get('name', 'Unknown'),
                        'company': prospect_data.get('company', 'Unknown'),
                        'email_content': {
                            'subject': result['email_content'].subject,
                            'body_preview': result['email_content'].body[:200] + '...' if len(result['email_content'].body) > 200 else result['email_content'].body,
                            'personalization_score': result['email_content'].personalization_score,
                            'template_used': result['email_content'].template_used
                        },
                        'sent': result.get('sent', False),
                        'generated_at': result['generated_at'],
                        'sender_profile_used': self.sender_profile is not None
                    }
                    
                    if result.get('send_result'):
                        success_result['send_result'] = result['send_result']
                    
                    results['successful'].append(success_result)
                    results['emails_generated'] += 1
                    
                    if result.get('sent', False):
                        results['emails_sent'] += 1
                        self.stats['emails_generated'] += 1
            
            self.logger.info(
                f"Email generation and sending completed: "
                f"{results['emails_generated']} generated, "
                f"{results['emails_sent']} sent, "
                f"{results['errors']} failed"
            )
            
            return results
            
        except Exception as e:
            self.logger.error(f"Email generation and sending process failed: {str(e)}")
            raise
    
    def send_single_outreach_email(
        self, 
        prospect_id: str, 
        template_type: EmailTemplate = EmailTemplate.COLD_OUTREACH
    ) -> Dict[str, Any]:
        """
        Generate and send a single outreach email using AI-structured data.
        
        Args:
            prospect_id: Notion page ID for the prospect
            template_type: Type of email template to use
            
        Returns:
            Dictionary containing email generation and sending result
        """
        self.logger.info(f"Generating and sending single outreach email for prospect {prospect_id}")
        
        # Check if sender profile is required but not available
        if self.config.require_sender_profile and not self.sender_profile:
            error_msg = "Sender profile is required but not available"
            self.logger.error(error_msg)
            return {
                'prospect_id': prospect_id,
                'error': error_msg,
                'sent': False,
                'generated_at': datetime.now().isoformat(),
                'sender_profile_used': False
            }
        
        try:
            result = self.email_generator.generate_and_send_email(
                prospect_id=prospect_id,
                notion_manager=self.notion_manager,
                email_sender=self.email_sender,
                template_type=template_type,
                send_immediately=True,
                additional_context={
                    'source_mention': 'ProductHunt',
                    'discovery_context': 'I discovered your company on ProductHunt'
                },
                sender_profile=self.sender_profile
            )
            
            # Get prospect data for enhanced result
            prospect_data = self.notion_manager.get_prospect_data_for_email(prospect_id)
            
            enhanced_result = {
                'prospect_id': prospect_id,
                'prospect_name': prospect_data.get('name', 'Unknown'),
                'company': prospect_data.get('company', 'Unknown'),
                'recipient_email': prospect_data.get('email', 'Unknown'),
                'email_content': {
                    'subject': result['email_content'].subject,
                    'body': result['email_content'].body,
                    'personalization_score': result['email_content'].personalization_score,
                    'template_used': result['email_content'].template_used
                },
                'sent': result.get('sent', False),
                'generated_at': result['generated_at'],
                'error': result.get('error'),
                'sender_profile_used': self.sender_profile is not None
            }
            
            if result.get('send_result'):
                enhanced_result['send_result'] = result['send_result']
            
            if result.get('sent', False):
                self.stats['emails_generated'] += 1
                self.logger.info(f"Successfully generated and sent email to {prospect_data.get('name', 'Unknown')}")
            else:
                self.logger.warning(f"Email generated but not sent for {prospect_data.get('name', 'Unknown')}: {result.get('error', 'Unknown error')}")
            
            return enhanced_result
            
        except Exception as e:
            self.logger.error(f"Failed to generate and send email for prospect {prospect_id}: {str(e)}")
            raise
    
    def send_prospect_emails(self, prospect_ids: List[str], batch_size: int = 5, delay: int = 30) -> Dict[str, Any]:
        """
        Send already generated emails to prospects.
        
        Args:
            prospect_ids: List of prospect IDs to send emails to
            batch_size: Number of emails to send per batch
            delay: Delay between batches in seconds
            
        Returns:
            Dictionary containing sending results
        """
        self.logger.info(f"Sending emails to {len(prospect_ids)} prospects")
        
        results = {
            'successful': [],
            'failed': [],
            'total_sent': 0,
            'total_failed': 0
        }
        
        import time
        
        for i, prospect_id in enumerate(prospect_ids):
            try:
                self.logger.info(f"Sending email to prospect {prospect_id} ({i+1}/{len(prospect_ids)})")
                
                # Get prospect data and generated email content from Notion
                prospect_data = self.notion_manager.get_prospect_data_for_email(prospect_id)
                
                if not prospect_data.get('email'):
                    self.logger.warning(f"No email address found for prospect {prospect_id}")
                    results['failed'].append({
                        'prospect_id': prospect_id,
                        'error': 'No email address found',
                        'prospect_name': prospect_data.get('name', 'Unknown')
                    })
                    results['total_failed'] += 1
                    continue
                
                # Check if email has already been sent (safety check)
                delivery_status = prospect_data.get('email_delivery_status', 'Not Sent')
                if delivery_status in ['Sent', 'Delivered', 'Opened', 'Clicked']:
                    self.logger.info(f"Email already sent to prospect {prospect_id} (status: {delivery_status}), skipping")
                    results['failed'].append({
                        'prospect_id': prospect_id,
                        'error': f'Email already sent (status: {delivery_status})',
                        'prospect_name': prospect_data.get('name', 'Unknown'),
                        'skipped': True
                    })
                    results['total_failed'] += 1
                    continue
                
                # Check if email content exists
                email_subject = prospect_data.get('email_subject')
                email_content = prospect_data.get('email_content')
                
                self.logger.info(f"Email subject: {repr(email_subject)}")
                self.logger.info(f"Email content length: {len(email_content) if email_content else 0}")
                
                if not email_subject or not email_content:
                    self.logger.warning(f"No generated email content found for prospect {prospect_id}")
                    results['failed'].append({
                        'prospect_id': prospect_id,
                        'error': 'No generated email content found',
                        'prospect_name': prospect_data.get('name', 'Unknown')
                    })
                    results['total_failed'] += 1
                    continue
                
                # Clean and validate email content
                email_subject = str(email_subject).strip()
                email_content = str(email_content).strip()
                
                if not email_subject or not email_content:
                    self.logger.warning(f"Empty email content after cleaning for prospect {prospect_id}")
                    results['failed'].append({
                        'prospect_id': prospect_id,
                        'error': 'Empty email content after cleaning',
                        'prospect_name': prospect_data.get('name', 'Unknown')
                    })
                    results['total_failed'] += 1
                    continue
                
                # Debug: Log first 200 chars of content to identify issues
                self.logger.info(f"Email content preview: {repr(email_content[:200])}")
                
                # Clean email content of any problematic characters
                import re
                # Remove any null bytes or other problematic characters
                email_content_clean = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', email_content)
                email_subject_clean = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', email_subject)
                
                # Convert email body to HTML format for better rendering
                html_body = self._convert_to_html(email_content_clean)
                
                # Send the email
                send_result = self.email_sender.send_email(
                    recipient_email=prospect_data['email'],
                    subject=email_subject_clean,
                    html_body=html_body,
                    text_body=email_content_clean,  # Plain text version
                    tags=["job-prospect", "outreach", "batch-send"],
                    prospect_id=prospect_id
                )
                
                if send_result.status == "sent":
                    self.logger.info(f"Successfully sent email to {prospect_data['email']} (ID: {send_result.email_id})")
                    
                    # Update email delivery status in Notion
                    try:
                        self.notion_manager.update_email_delivery_status(
                            prospect_id=prospect_id,
                            delivery_status="Sent",
                            provider_id=send_result.email_id
                        )
                        self.logger.info(f"Updated Notion delivery status for prospect {prospect_id}")
                    except Exception as e:
                        self.logger.error(f"Failed to update Notion delivery status: {str(e)}")
                    
                    # Also update the legacy email status field
                    try:
                        self.notion_manager.update_email_status(
                            prospect_id=prospect_id,
                            email_status="Sent",
                            email_id=send_result.email_id,
                            email_subject=email_subject_clean
                        )
                        self.logger.info(f"Updated Notion email status for prospect {prospect_id}")
                    except Exception as e:
                        self.logger.error(f"Failed to update Notion email status: {str(e)}")
                    
                    results['successful'].append({
                        'prospect_id': prospect_id,
                        'prospect_name': prospect_data.get('name', 'Unknown'),
                        'email': prospect_data['email'],
                        'email_id': send_result.email_id,
                        'subject': email_subject
                    })
                    results['total_sent'] += 1
                else:
                    self.logger.error(f"Failed to send email to {prospect_data['email']}: {send_result.error_message}")
                    results['failed'].append({
                        'prospect_id': prospect_id,
                        'error': send_result.error_message,
                        'prospect_name': prospect_data.get('name', 'Unknown'),
                        'email': prospect_data['email']
                    })
                    results['total_failed'] += 1
                
                # Add delay between emails (except for the last one)
                if i < len(prospect_ids) - 1 and (i + 1) % batch_size == 0:
                    self.logger.info(f"Batch completed. Waiting {delay} seconds before next batch...")
                    time.sleep(delay)
                elif i < len(prospect_ids) - 1:
                    # Small delay between individual emails
                    time.sleep(2)
                
            except Exception as e:
                self.logger.error(f"Failed to send email to prospect {prospect_id}: {str(e)}")
                results['failed'].append({
                    'prospect_id': prospect_id,
                    'error': str(e),
                    'prospect_name': 'Unknown'
                })
                results['total_failed'] += 1
        
        self.logger.info(f"Email sending completed: {results['total_sent']} sent, {results['total_failed']} failed")
        return results
    
    def _convert_to_html(self, text_content: str) -> str:
        """
        Convert plain text email content to HTML format.
        
        Args:
            text_content: Plain text email content
            
        Returns:
            HTML formatted email content
        """
        # Basic HTML conversion
        html_content = text_content.replace('\n\n', '</p><p>')
        html_content = html_content.replace('\n', '<br>')
        
        # Wrap in HTML structure
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <p>{html_content}</p>
        </body>
        </html>
        """
        
        return html_content
    
    def get_email_sending_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive email sending statistics.
        
        Returns:
            Dictionary containing email sending statistics and performance metrics
        """
        try:
            # Get stats from email sender
            sending_stats = self.email_sender.get_sending_stats()
            
            # Get delivery report
            delivery_report = self.email_sender.get_delivery_report()
            
            # Combine with controller stats
            combined_stats = {
                'controller_stats': {
                    'emails_generated': self.stats.get('emails_generated', 0),
                    'total_prospects_found': self.stats.get('prospects_found', 0),
                    'total_companies_processed': self.stats.get('companies_processed', 0)
                },
                'email_sender_stats': {
                    'total_sent': sending_stats.total_sent,
                    'total_delivered': sending_stats.total_delivered,
                    'total_opened': sending_stats.total_opened,
                    'total_clicked': sending_stats.total_clicked,
                    'total_bounced': sending_stats.total_bounced,
                    'total_complained': sending_stats.total_complained,
                    'total_failed': sending_stats.total_failed,
                    'delivery_rate': sending_stats.delivery_rate,
                    'open_rate': sending_stats.open_rate,
                    'click_rate': sending_stats.click_rate,
                    'bounce_rate': sending_stats.bounce_rate
                },
                'delivery_report': delivery_report,
                'report_generated_at': datetime.now().isoformat()
            }
            
            return combined_stats
            
        except Exception as e:
            self.logger.error(f"Failed to get email sending stats: {str(e)}")
            return {'error': str(e)}
    
    def get_prospect_email_performance(self, prospect_id: str) -> Dict[str, Any]:
        """
        Get email performance metrics for a specific prospect.
        
        Args:
            prospect_id: Notion page ID for the prospect
            
        Returns:
            Dictionary containing prospect email performance data
        """
        try:
            return self.email_sender.get_email_performance_by_prospect(prospect_id)
        except Exception as e:
            self.logger.error(f"Failed to get prospect email performance: {str(e)}")
            return {'error': str(e)}
    
    def _discover_companies(self, limit: int) -> List[CompanyData]:
        """
        Discover companies from ProductHunt, ensuring we get the target number of unprocessed companies.
        
        Args:
            limit: Target number of unprocessed companies to discover
            
        Returns:
            List of CompanyData objects (unprocessed companies only)
        """
        try:
            self.logger.info(f"Discovering companies to get {limit} unprocessed companies from ProductHunt")
            
            unprocessed_companies = []
            fetch_limit = limit
            max_attempts = 3
            attempt = 0
            
            while len(unprocessed_companies) < limit and attempt < max_attempts:
                attempt += 1
                
                # Increase fetch limit if we didn't get enough unprocessed companies in previous attempts
                if attempt > 1:
                    # Calculate how many more we need and add buffer for duplicates
                    needed = limit - len(unprocessed_companies)
                    # Add 50% buffer to account for duplicates, but cap at reasonable limit
                    fetch_limit = min(needed + int(needed * 0.5), 100)
                    self.logger.info(f"Attempt {attempt}: Need {needed} more companies, fetching {fetch_limit} with duplicate buffer")
                
                # Get latest products from ProductHunt
                products = self.product_hunt_scraper.get_latest_products(fetch_limit)
                
                if not products:
                    self.logger.warning(f"No products found on ProductHunt (attempt {attempt})")
                    break
                
                # Convert products to companies
                companies = []
                for product in products:
                    try:
                        # Extract domain using our validator
                        from services.domain_validator import extract_valid_domain, is_valid_domain
                        domain = extract_valid_domain(product.company_name, product.website_url)
                        
                        # If no valid domain found, try to extract from product page
                        if not domain:
                            self.logger.info(f"No domain found for {product.company_name}, trying product page extraction")
                            extracted_domain = self.product_hunt_scraper.extract_company_domain(product)
                            if extracted_domain and is_valid_domain(extracted_domain):
                                domain = extracted_domain
                                self.logger.info(f"Found domain from product page: {domain}")
                        
                        # Only include companies with valid domains
                        if not domain:
                            self.logger.warning(f"Skipping {product.company_name} - no valid domain found")
                            continue
                        
                        company = CompanyData(
                            name=product.company_name,
                            domain=domain,
                            product_url=product.product_url,
                            description=product.description,
                            launch_date=product.launch_date
                        )
                        
                        companies.append(company)
                        
                    except Exception as e:
                        self.logger.warning(f"Failed to convert product to company data: {str(e)}")
                        continue
                
                if not companies:
                    self.logger.warning(f"No valid companies found in attempt {attempt}")
                    break
                
                # Filter out already processed companies
                batch_unprocessed = self._filter_unprocessed_companies(companies)
                
                # Add new unprocessed companies, avoiding duplicates from previous attempts
                existing_names = {comp.name.lower() for comp in unprocessed_companies}
                for company in batch_unprocessed:
                    if company.name.lower() not in existing_names and len(unprocessed_companies) < limit:
                        unprocessed_companies.append(company)
                        existing_names.add(company.name.lower())
                
                self.logger.info(f"Attempt {attempt}: Found {len(batch_unprocessed)} new companies, total unprocessed: {len(unprocessed_companies)}/{limit}")
                
                # If we have enough companies, break early
                if len(unprocessed_companies) >= limit:
                    break
                
                # If we got very few new companies, increase the fetch limit more aggressively
                if len(batch_unprocessed) < fetch_limit * 0.2:  # Less than 20% were new
                    fetch_limit = min(fetch_limit * 2, 100)
                    self.logger.info(f"Low new company rate, increasing fetch limit to {fetch_limit} for next attempt")
            
            # Trim to exact limit if we got more than requested
            if len(unprocessed_companies) > limit:
                unprocessed_companies = unprocessed_companies[:limit]
                self.logger.info(f"Trimmed results to exactly {limit} companies")
            
            total_discovered = sum(len(self.product_hunt_scraper.get_latest_products(fetch_limit)) for _ in range(attempt))
            skipped_count = total_discovered - len(unprocessed_companies) if total_discovered > len(unprocessed_companies) else 0
            
            self.logger.info(f"✅ Discovery completed: {len(unprocessed_companies)} unprocessed companies ready for processing")
            if skipped_count > 0:
                self.logger.info(f"⚡ PERFORMANCE: Skipped {skipped_count} already processed companies")
            
            if len(unprocessed_companies) < limit:
                self.logger.warning(f"⚠️ Could only find {len(unprocessed_companies)} unprocessed companies out of {limit} requested")
                self.logger.warning("This might indicate that most recent companies have already been processed")
            
            return unprocessed_companies
            
        except Exception as e:
            self.logger.error(f"Failed to discover companies: {str(e)}")
            raise
    
    def _analyze_product_with_ai_structuring(self, company_data: CompanyData) -> Optional[ComprehensiveProductInfo]:
        """
        Analyze product comprehensively with AI-enhanced structuring for email personalization.
        
        Args:
            company_data: Company information from ProductHunt
            
        Returns:
            ComprehensiveProductInfo object or None if analysis fails
        """
        try:
            self.logger.info(f"Analyzing product with AI structuring for {company_data.name}")
            
            # Try to get company website URL from domain
            company_website = f"https://{company_data.domain}" if company_data.domain else ""
            
            # Perform comprehensive product analysis
            product_analysis = self.product_analyzer.analyze_product(
                product_url=company_data.product_url,
                company_website=company_website
            )
            
            # If AI processing is available, enhance the analysis with structured insights
            if self.use_ai_processing and self.ai_service and product_analysis:
                try:
                    # Create comprehensive content for AI analysis
                    product_content = f"""
                    Product: {getattr(product_analysis.basic_info, 'name', 'Unknown')}
                    Description: {getattr(product_analysis.basic_info, 'description', 'No description')}
                    Features: {', '.join([getattr(f, 'name', str(f)) for f in product_analysis.features])}
                    Pricing: {getattr(product_analysis.pricing, 'model', 'Unknown')}
                    Target Market: {getattr(product_analysis.market_analysis, 'target_market', 'Unknown')}
                    Competitors: {', '.join(getattr(product_analysis.market_analysis, 'competitors', []))}
                    """
                    
                    # Use consolidated AI Service to extract business metrics and insights
                    business_metrics_result = self.ai_service.extract_business_metrics(
                        company_data=product_content,
                        company_name=company_data.name
                    )
                    
                    if business_metrics_result.success and business_metrics_result.data:
                        # Enhance the product analysis with AI insights
                        product_analysis.funding_info = {
                            'funding_amount': business_metrics_result.data.funding_amount,
                            'growth_stage': business_metrics_result.data.growth_stage,
                            'business_model': business_metrics_result.data.business_model,
                            'revenue_model': business_metrics_result.data.revenue_model
                        }
                        product_analysis.team_size = business_metrics_result.data.employee_count
                        
                        self.logger.info(f"Enhanced product analysis with AI insights for {company_data.name}")
                    
                except Exception as e:
                    self.logger.warning(f"AI enhancement failed for product analysis: {str(e)}")
            
            self.logger.info(f"Successfully analyzed product for {company_data.name}")
            return product_analysis
            
        except Exception as e:
            self.logger.warning(f"Failed to analyze product for {company_data.name}: {str(e)}")
            # Return None to continue processing without product analysis
            return None

    def _analyze_product(self, company_data: CompanyData) -> Optional[ComprehensiveProductInfo]:
        """
        Analyze product comprehensively for enhanced email personalization.
        
        Args:
            company_data: Company information from ProductHunt
            
        Returns:
            ComprehensiveProductInfo object or None if analysis fails
        """
        try:
            self.logger.info(f"Analyzing product for {company_data.name}")
            
            # Try to get company website URL from domain
            company_website = f"https://{company_data.domain}" if company_data.domain else ""
            
            # Perform comprehensive product analysis
            product_analysis = self.product_analyzer.analyze_product(
                product_url=company_data.product_url,
                company_website=company_website
            )
            
            self.logger.info(f"Successfully analyzed product for {company_data.name}")
            return product_analysis
            
        except Exception as e:
            self.logger.warning(f"Failed to analyze product for {company_data.name}: {str(e)}")
            # Return None to continue processing without product analysis
            return None
    
    def _extract_team_members_with_ai(self, company_data: CompanyData) -> List[TeamMember]:
        """
        Extract team members with AI-enhanced parsing for better accuracy.
        
        Args:
            company_data: Company information
            
        Returns:
            List of TeamMember objects
        """
        try:
            self.logger.info(f"Extracting team members with AI enhancement for {company_data.name}")
            
            # First, get team members using traditional scraping
            team_members = self.product_hunt_scraper.extract_team_info(company_data.product_url)
            
            # If AI processing is available and we have raw team data, enhance it
            if self.use_ai_processing and self.ai_service and team_members:
                try:
                    # Convert team members to raw content for AI processing
                    raw_team_content = "\n".join([
                        f"Name: {getattr(tm, 'name', 'Unknown')}, Role: {getattr(tm, 'role', 'Unknown')}, Company: {getattr(tm, 'company', 'Unknown')}, LinkedIn: {getattr(tm, 'linkedin_url', None) or 'N/A'}"
                        for tm in team_members
                    ])
                    
                    # Use consolidated AI Service to structure and enhance team data
                    ai_result = self.ai_service.extract_team_data(
                        raw_team_info=raw_team_content,
                        company_name=company_data.name
                    )
                    
                    if ai_result.success and ai_result.data:
                        # Use AI-structured team members if available
                        enhanced_team_members = ai_result.data
                        self.logger.info(f"AI enhanced team data: {len(enhanced_team_members)} members structured")
                        self.stats['ai_parsing_successes'] += 1
                        
                        # Limit number of team members per company
                        if len(enhanced_team_members) > self.config.max_prospects_per_company:
                            enhanced_team_members = enhanced_team_members[:self.config.max_prospects_per_company]
                        
                        return enhanced_team_members
                    else:
                        self.logger.warning(f"AI team structuring failed: {ai_result.error_message}")
                        self.stats['ai_parsing_failures'] += 1
                
                except Exception as e:
                    self.logger.warning(f"AI team enhancement failed: {str(e)}")
                    self.stats['ai_parsing_failures'] += 1
            
            # Fall back to traditional team members
            if len(team_members) > self.config.max_prospects_per_company:
                team_members = team_members[:self.config.max_prospects_per_company]
            
            self.logger.info(f"Extracted {len(team_members)} team members for {company_data.name}")
            return team_members
            
        except Exception as e:
            self.logger.error(f"Failed to extract team members for {company_data.name}: {str(e)}")
            return []

    def _extract_linkedin_profiles_with_ai(self, team_members: List[TeamMember]) -> Dict[str, LinkedInProfile]:
        """
        Extract LinkedIn profiles with AI-enhanced parsing for better data structuring.
        
        Args:
            team_members: List of team members with LinkedIn URLs
            
        Returns:
            Dictionary mapping LinkedIn URLs to LinkedInProfile objects
        """
        profiles = {}
        
        for team_member in team_members:
            if not team_member.linkedin_url:
                continue
            
            try:
                # PERFORMANCE OPTIMIZATION: Skip LinkedIn extraction if likely to fail
                if not self._should_extract_linkedin_profile(team_member):
                    self.logger.info(f"Skipping LinkedIn extraction for {team_member.name} - low success probability")
                    continue
                    
                self.logger.info(f"Extracting LinkedIn profile with AI for {team_member.name}")
                
                # First, get raw LinkedIn data using traditional scraping
                raw_profile_data = self.linkedin_scraper.extract_profile_data(team_member.linkedin_url)
                
                if raw_profile_data and self.use_ai_processing and self.ai_service:
                    try:
                        # Get raw HTML content for AI parsing (if available from scraper)
                        raw_html = getattr(raw_profile_data, 'raw_html', None)
                        
                        if raw_html:
                            # Use consolidated AI Service to enhance LinkedIn profile parsing
                            ai_result = self.ai_service.parse_linkedin_profile(
                                raw_html=raw_html,
                                fallback_data={
                                    'name': raw_profile_data.name,
                                    'current_role': raw_profile_data.current_role,
                                    'experience': raw_profile_data.experience,
                                    'skills': raw_profile_data.skills,
                                    'summary': raw_profile_data.summary
                                }
                            )
                            
                            if ai_result.success and ai_result.data:
                                profiles[team_member.linkedin_url] = ai_result.data
                                self.logger.info(f"AI enhanced LinkedIn profile for {team_member.name}")
                                self.stats['ai_parsing_successes'] += 1
                                continue
                        
                    except Exception as e:
                        self.logger.warning(f"AI LinkedIn enhancement failed for {team_member.name}: {str(e)}")
                        self.stats['ai_parsing_failures'] += 1
                
                # Fall back to traditional LinkedIn profile
                if raw_profile_data:
                    profiles[team_member.linkedin_url] = raw_profile_data
                    self.logger.info(f"Extracted LinkedIn profile for {team_member.name}")
                
                # Add delay to respect LinkedIn rate limits
                time.sleep(self.config.scraping_delay)
                
            except Exception as e:
                self.logger.error(f"Failed to extract LinkedIn profile for {team_member.name}: {str(e)}")
                continue
        
        self.logger.info(f"Successfully extracted {len(profiles)} LinkedIn profiles with AI enhancement")
        return profiles

    def _should_extract_linkedin_profile(self, team_member: TeamMember) -> bool:
        """
        Determine if LinkedIn profile extraction is worth the time investment.
        
        Args:
            team_member: TeamMember object
            
        Returns:
            True if extraction should proceed, False to skip
        """
        # Skip if no LinkedIn URL
        if not team_member.linkedin_url:
            return False
            
        # Skip if URL looks invalid or generic
        url_lower = team_member.linkedin_url.lower()
        if any(skip_pattern in url_lower for skip_pattern in [
            'linkedin.com/company',  # Company page, not person
            'linkedin.com/school',   # School page
            'linkedin.com/showcase', # Showcase page
            '/pub/',                 # Old public profile format (often broken)
        ]):
            self.logger.info(f"Skipping LinkedIn extraction - invalid URL pattern: {team_member.linkedin_url}")
            return False
            
        # Skip if name is too generic or incomplete
        if not team_member.name or len(team_member.name.strip()) < 3:
            self.logger.info(f"Skipping LinkedIn extraction - insufficient name data: {team_member.name}")
            return False
            
        # Skip if name contains generic terms
        name_lower = team_member.name.lower()
        if any(generic in name_lower for generic in [
            'team', 'support', 'admin', 'info', 'contact', 'sales', 'marketing'
        ]):
            self.logger.info(f"Skipping LinkedIn extraction - generic name: {team_member.name}")
            return False
            
        # Only proceed if we have a reasonable chance of success
        return True

    def _filter_unprocessed_companies(self, companies: List[CompanyData]) -> List[CompanyData]:
        """
        Filter out companies that have already been processed to avoid duplicate work.
        Uses cached data for optimal performance during batch processing.
        
        Args:
            companies: List of discovered companies
            
        Returns:
            List of companies that haven't been processed yet
        """
        if not companies:
            return companies
            
        try:
            self.logger.info(f"🔍 Checking {len(companies)} companies for duplicates...")
            
            # Get cached processed companies and domains
            processed_companies, processed_domains = self._get_cached_processed_companies()
            
            # Convert to lowercase sets for efficient lookup
            processed_companies_lower = {name.lower() for name in processed_companies}
            processed_domains_lower = {domain.lower() for domain in processed_domains}
            
            unprocessed = []
            skipped_count = 0
            
            for company in companies:
                # Check by name (case-insensitive)
                if company.name.lower() in processed_companies_lower:
                    self.logger.info(f"⏭️ Skipping {company.name} - already processed by name")
                    skipped_count += 1
                    continue
                    
                # Check by domain (case-insensitive)
                if company.domain and company.domain.lower() in processed_domains_lower:
                    self.logger.info(f"⏭️ Skipping {company.name} - already processed by domain ({company.domain})")
                    skipped_count += 1
                    continue
                    
                # Company is new, add to unprocessed list
                unprocessed.append(company)
                
            if skipped_count > 0:
                self.logger.info(f"⚡ PERFORMANCE: Skipped {skipped_count} already processed companies, processing {len(unprocessed)} new companies")
            else:
                self.logger.info(f"✅ All {len(companies)} companies are new - no duplicates found")
                
            return unprocessed
            
        except Exception as e:
            self.logger.warning(f"Failed to filter processed companies: {str(e)}")
            # If filtering fails, return all companies to avoid breaking the pipeline
            self.logger.warning("Continuing with all companies to avoid pipeline failure")
            return companies

    def _should_extract_linkedin_profile_for_prospect(self, prospect: Prospect) -> bool:
        """
        Determine if LinkedIn profile extraction is worth it for email generation.
        
        Args:
            prospect: Prospect object
            
        Returns:
            True if extraction should proceed, False to skip
        """
        # Create a temporary TeamMember-like object to reuse the logic
        class TempTeamMember:
            def __init__(self, name, linkedin_url):
                self.name = name
                self.linkedin_url = linkedin_url
        
        temp_member = TempTeamMember(prospect.name, prospect.linkedin_url)
        return self._should_extract_linkedin_profile(temp_member)

    def _structure_prospect_data_with_ai(
        self, 
        prospect: Prospect, 
        linkedin_profile: Optional[LinkedInProfile], 
        product_analysis: Optional[ComprehensiveProductInfo],
        company_data: CompanyData
    ) -> Dict[str, str]:
        """
        Structure all prospect data with AI for optimized email personalization.
        
        Args:
            prospect: Prospect information
            linkedin_profile: LinkedIn profile data
            product_analysis: Product analysis data
            company_data: Company information
            
        Returns:
            Dictionary containing AI-structured data for email personalization
        """
        try:
            if not self.use_ai_processing or not self.ai_service:
                return {}
            
            self.logger.info(f"Structuring prospect data with AI for {prospect.name}")
            
            # Prepare comprehensive data for AI structuring
            prospect_context = f"""
            Prospect Information:
            Name: {prospect.name}
            Role: {prospect.role}
            Company: {prospect.company}
            Email: {prospect.email or 'Not available'}
            
            Company Information:
            Company: {company_data.name}
            Domain: {company_data.domain}
            Description: {company_data.description}
            Product URL: {company_data.product_url}
            """
            
            # Add LinkedIn information if available
            if linkedin_profile:
                prospect_context += f"""
                
                LinkedIn Profile:
                Current Role: {linkedin_profile.current_role}
                Experience: {', '.join(linkedin_profile.experience[:3])}
                Skills: {', '.join(linkedin_profile.skills[:10])}
                Summary: {linkedin_profile.summary[:300]}
                """
            
            # Add product analysis if available
            if product_analysis:
                prospect_context += f"""
                
                Product Analysis:
                Product: {product_analysis.basic_info.name}
                Description: {product_analysis.basic_info.description}
                Features: {', '.join([f.name for f in product_analysis.features[:5]])}
                Target Market: {product_analysis.market_analysis.target_market}
                Competitors: {', '.join(product_analysis.market_analysis.competitors[:3])}
                """
                
                if product_analysis.funding_info:
                    prospect_context += f"""
                    Funding: {product_analysis.funding_info.get('funding_amount', 'Unknown')}
                    Growth Stage: {product_analysis.funding_info.get('growth_stage', 'Unknown')}
                    Business Model: {product_analysis.funding_info.get('business_model', 'Unknown')}
                    """
            
            # Use AI to create structured summaries for email personalization
            structured_data = {}
            
            # Generate product summary optimized for emails
            try:
                product_summary_prompt = f"""
                Based on the following information, create a concise 2-3 sentence summary of the company's product 
                that would be useful for personalizing a job outreach email:
                
                {prospect_context}
                
                Focus on what makes the product interesting and relevant for someone seeking opportunities.
                """
                
                # Use consolidated AI Service for product summary generation
                request = CompletionRequest(
                    messages=[
                        {"role": "system", "content": "You are an expert at creating concise, engaging product summaries for professional outreach."},
                        {"role": "user", "content": product_summary_prompt}
                    ],
                    temperature=0.3,
                    max_tokens=600
                )
                response = self.ai_service.client_manager.make_completion(request, self.ai_service.client_id)
                
                if response.success:
                    structured_data['product_summary'] = response.content.strip()
                else:
                    structured_data['product_summary'] = ""
                    self.logger.warning(f"AI product summary generation failed: {response.error_message}")
                
            except Exception as e:
                self.logger.warning(f"Failed to generate product summary: {str(e)}")
                structured_data['product_summary'] = ""
            
            # Generate business insights for outreach context
            try:
                business_insights_prompt = f"""
                Based on the following information, identify 2-3 key business insights or growth indicators 
                that would be relevant for a job seeker reaching out to this company:
                
                {prospect_context}
                
                Focus on growth potential, market position, or interesting business aspects.
                """
                
                # Use consolidated AI Service for business insights generation
                request = CompletionRequest(
                    messages=[
                        {"role": "system", "content": "You are an expert at identifying business insights relevant for job seekers."},
                        {"role": "user", "content": business_insights_prompt}
                    ],
                    temperature=0.3,
                    max_tokens=500
                )
                response = self.ai_service.client_manager.make_completion(request, self.ai_service.client_id)
                
                if response.success:
                    structured_data['business_insights'] = response.content.strip()
                else:
                    structured_data['business_insights'] = ""
                    self.logger.warning(f"AI business insights generation failed: {response.error_message}")
                
            except Exception as e:
                self.logger.warning(f"Failed to generate business insights: {str(e)}")
                structured_data['business_insights'] = ""
            
            # Generate LinkedIn summary for personalization
            if linkedin_profile:
                try:
                    linkedin_summary_prompt = f"""
                    Based on the following LinkedIn profile information, create a brief summary highlighting 
                    the most relevant aspects for personalizing a job outreach email:
                    
                    Name: {linkedin_profile.name}
                    Role: {linkedin_profile.current_role}
                    Experience: {', '.join(linkedin_profile.experience[:3])}
                    Skills: {', '.join(linkedin_profile.skills[:5])}
                    
                    Focus on experience and skills that would be relevant for job opportunities.
                    """
                    
                    # Use consolidated AI Service for LinkedIn summary generation
                    request = CompletionRequest(
                        messages=[
                            {"role": "system", "content": "You are an expert at summarizing LinkedIn profiles for professional outreach."},
                            {"role": "user", "content": linkedin_summary_prompt}
                        ],
                        temperature=0.3,
                        max_tokens=400
                    )
                    response = self.ai_service.client_manager.make_completion(request, self.ai_service.client_id)
                    
                    if response.success:
                        structured_data['linkedin_summary'] = response.content.strip()
                    else:
                        structured_data['linkedin_summary'] = ""
                        self.logger.warning(f"AI LinkedIn summary generation failed: {response.error_message}")
                    
                except Exception as e:
                    self.logger.warning(f"Failed to generate LinkedIn summary: {str(e)}")
                    structured_data['linkedin_summary'] = ""
            
            # Generate personalization key points
            try:
                personalization_prompt = f"""
                Based on all the information provided, identify 3-5 key personalization points that would make 
                a job outreach email more relevant and engaging:
                
                {prospect_context}
                
                Focus on specific details that show research and genuine interest.
                """
                
                # Use consolidated AI Service for personalization data generation
                request = CompletionRequest(
                    messages=[
                        {"role": "system", "content": "You are an expert at identifying personalization opportunities for professional outreach."},
                        {"role": "user", "content": personalization_prompt}
                    ],
                    temperature=0.3,
                    max_tokens=800
                )
                response = self.ai_service.client_manager.make_completion(request, self.ai_service.client_id)
                
                if response.success:
                    structured_data['personalization_data'] = response.content.strip()
                else:
                    structured_data['personalization_data'] = ""
                    self.logger.warning(f"AI personalization data generation failed: {response.error_message}")
                
            except Exception as e:
                self.logger.warning(f"Failed to generate personalization data: {str(e)}")
                structured_data['personalization_data'] = ""
            
            self.logger.info(f"Successfully structured prospect data with AI for {prospect.name}")
            return structured_data
            
        except Exception as e:
            self.logger.error(f"Failed to structure prospect data with AI: {str(e)}")
            return {}

    def _extract_team_members(self, company_data: CompanyData) -> List[TeamMember]:
        """
        Extract team members for a company.
        
        Args:
            company_data: Company information
            
        Returns:
            List of TeamMember objects
        """
        try:
            self.logger.info(f"Extracting team members for {company_data.name}")
            
            team_members = self.product_hunt_scraper.extract_team_info(company_data.product_url)
            
            # Limit number of team members per company
            if len(team_members) > self.config.max_prospects_per_company:
                team_members = team_members[:self.config.max_prospects_per_company]
                self.logger.info(f"Limited team members to {self.config.max_prospects_per_company} for {company_data.name}")
            
            return team_members
            
        except Exception as e:
            self.logger.error(f"Failed to extract team members for {company_data.name}: {str(e)}")
            return []
    
    def _find_team_emails(self, team_members: List[TeamMember], domain: str) -> Dict[str, Dict[str, Any]]:
        """
        Find emails for team members.
        
        Args:
            team_members: List of team members
            domain: Company domain
            
        Returns:
            Dictionary mapping team member names to email results
        """
        try:
            # Validate domain before proceeding
            from services.domain_validator import is_valid_domain
            if not domain or not is_valid_domain(domain):
                self.logger.warning(f"Invalid domain for email finding: {domain}")
                return {}
                
            self.logger.info(f"Finding emails for {len(team_members)} team members at {domain}")
            
            email_results = self.email_finder.find_and_verify_team_emails(team_members, domain)
            
            # Get best emails with minimum confidence
            best_emails = self.email_finder.get_best_emails(email_results, min_confidence=70)
            
            self.logger.info(f"Found {len(best_emails)} verified emails for team members")
            return email_results
            
        except Exception as e:
            self.logger.error(f"Failed to find team emails for domain {domain}: {str(e)}")
            return {}
    
    def _extract_linkedin_profiles(self, team_members: List[TeamMember]) -> Dict[str, LinkedInProfile]:
        """
        Extract LinkedIn profiles for team members.
        
        Args:
            team_members: List of team members with LinkedIn URLs
            
        Returns:
            Dictionary mapping LinkedIn URLs to LinkedInProfile objects
        """
        profiles = {}
        
        try:
            linkedin_urls = [tm.linkedin_url for tm in team_members if tm.linkedin_url]
            
            if not linkedin_urls:
                self.logger.info("No LinkedIn URLs found for team members")
                return profiles
            
            self.logger.info(f"Extracting LinkedIn profiles for {len(linkedin_urls)} team members")
            
            profiles = self.linkedin_scraper.extract_multiple_profiles(linkedin_urls)
            
            # Filter out None results
            profiles = {url: profile for url, profile in profiles.items() if profile is not None}
            
            self.logger.info(f"Successfully extracted {len(profiles)} LinkedIn profiles")
            return profiles
            
        except Exception as e:
            self.logger.error(f"Failed to extract LinkedIn profiles: {str(e)}")
            return profiles
    
    def _create_prospect_from_team_member(self, 
                                        team_member: TeamMember, 
                                        company_data: CompanyData,
                                        email_result: Optional[Dict[str, Any]] = None,
                                        linkedin_profile: Optional[LinkedInProfile] = None) -> Optional[Prospect]:
        """
        Create a Prospect object from team member data.
        
        Args:
            team_member: Team member information
            company_data: Company information
            email_result: Email finding results
            linkedin_profile: LinkedIn profile data
            
        Returns:
            Prospect object or None if creation fails
        """
        try:
            # Extract email if available
            email = None
            if email_result and 'email_data' in email_result:
                email = email_result['email_data'].email
            
            # Create notes with available information
            notes = []
            if linkedin_profile:
                if linkedin_profile.summary:
                    notes.append(f"LinkedIn Summary: {linkedin_profile.summary[:200]}")
                if linkedin_profile.skills:
                    notes.append(f"Skills: {', '.join(linkedin_profile.skills[:5])}")
            
            if email_result and 'verification' in email_result and email_result['verification']:
                verification = email_result['verification']
                notes.append(f"Email verification: {verification.result}")
            
            prospect = Prospect(
                name=team_member.name,
                role=team_member.role,
                company=team_member.company,
                linkedin_url=team_member.linkedin_url,
                email=email,
                contacted=False,
                status=ProspectStatus.NOT_CONTACTED,
                notes='\n'.join(notes),
                source_url=company_data.product_url,
                created_at=datetime.now()
            )
            
            return prospect
            
        except Exception as e:
            self.logger.error(f"Failed to create prospect from team member {team_member.name}: {str(e)}")
            return None
    
    def _get_pipeline_results(self) -> Dict[str, Any]:
        """
        Get pipeline execution results and statistics.
        
        Returns:
            Dictionary containing results and statistics
        """
        duration = None
        if self.stats['start_time'] and self.stats['end_time']:
            duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        
        return {
            'statistics': self.stats.copy(),
            'summary': {
                'companies_processed': self.stats['companies_processed'],
                'prospects_found': self.stats['prospects_found'],
                'emails_found': self.stats['emails_found'],
                'linkedin_profiles_extracted': self.stats['linkedin_profiles_extracted'],
                'emails_generated': self.stats['emails_generated'],
                'errors': self.stats['errors'],
                'duration_seconds': duration,
                'success_rate': (self.stats['companies_processed'] / max(1, self.stats['companies_processed'] + self.stats['errors'])) * 100
            }
        }
    
    def get_workflow_status(self) -> Dict[str, Any]:
        """
        Get current workflow status and statistics.
        
        Returns:
            Dictionary containing current status
        """
        return {
            'is_running': self.stats['start_time'] is not None and self.stats['end_time'] is None,
            'current_stats': self.stats.copy(),
            'services_status': {
                'product_hunt_scraper': 'initialized',
                'notion_manager': 'initialized',
                'email_finder': 'initialized',
                'linkedin_scraper': 'initialized',
                'email_generator': 'initialized'
            }
        }
    
    def run_batch_processing(self, companies: List[CompanyData], 
                           batch_size: int = 5,
                           progress_callback: Optional[Callable[[BatchProgress], None]] = None) -> Dict[str, Any]:
        """
        Process companies in batches with progress tracking and resume functionality.
        
        Args:
            companies: List of companies to process
            batch_size: Number of companies to process in each batch
            progress_callback: Optional callback function for progress updates
            
        Returns:
            Dictionary containing batch processing results
        """
        batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Initialize batch progress
        self.current_batch = BatchProgress(
            batch_id=batch_id,
            status=ProcessingStatus.IN_PROGRESS,
            total_companies=len(companies),
            processed_companies=0,
            successful_companies=0,
            failed_companies=0,
            total_prospects=0,
            start_time=datetime.now(),
            last_update_time=datetime.now()
        )
        
        if progress_callback:
            self.progress_callbacks.append(progress_callback)
        
        self.logger.info(f"Starting batch processing: {batch_id} with {len(companies)} companies")
        
        try:
            # Store initial progress state in Notion
            self._store_batch_progress()
            
            # Process companies in batches
            for i in range(0, len(companies), batch_size):
                batch_companies = companies[i:i + batch_size]
                self.logger.info(f"Processing batch {i//batch_size + 1}: companies {i+1}-{min(i+batch_size, len(companies))}")
                
                # Process each company in the current batch
                for company in batch_companies:
                    if self.current_batch.status == ProcessingStatus.PAUSED:
                        self.logger.info("Batch processing paused")
                        break
                    
                    result = self._process_company_with_tracking(company)
                    self.batch_results.append(result)
                    
                    # Update progress
                    self._update_batch_progress(company.name, result)
                    
                    # Add delay between companies
                    time.sleep(self.config.scraping_delay)
                
                # Check if processing was paused
                if self.current_batch.status == ProcessingStatus.PAUSED:
                    break
                
                # Store progress after each batch
                self._store_batch_progress()
                
                # Add delay between batches
                if i + batch_size < len(companies):
                    time.sleep(self.config.scraping_delay * 2)
            
            # Complete batch processing
            if self.current_batch.status != ProcessingStatus.PAUSED:
                self.current_batch.status = ProcessingStatus.COMPLETED
                self.current_batch.end_time = datetime.now()
                self._store_batch_progress()
            
            results = self._get_batch_results()
            self.logger.info(f"Batch processing completed: {batch_id}")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Batch processing failed: {str(e)}")
            self.current_batch.status = ProcessingStatus.FAILED
            self.current_batch.error_message = str(e)
            self.current_batch.end_time = datetime.now()
            self._store_batch_progress()
            raise
    
    def pause_batch_processing(self) -> bool:
        """
        Pause the current batch processing.
        
        Returns:
            True if successfully paused, False if no batch is running
        """
        if self.current_batch and self.current_batch.status == ProcessingStatus.IN_PROGRESS:
            self.current_batch.status = ProcessingStatus.PAUSED
            self.current_batch.last_update_time = datetime.now()
            self._store_batch_progress()
            self.logger.info(f"Batch processing paused: {self.current_batch.batch_id}")
            return True
        return False
    
    def resume_batch_processing(self, batch_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Resume a paused batch processing session.
        
        Args:
            batch_id: Optional batch ID to resume. If None, resumes current batch.
            
        Returns:
            Dictionary containing batch processing results
        """
        if batch_id:
            # Load batch progress from Notion
            batch_progress = self._load_batch_progress(batch_id)
            if not batch_progress:
                raise ValueError(f"Batch {batch_id} not found")
            self.current_batch = batch_progress
        
        if not self.current_batch or self.current_batch.status != ProcessingStatus.PAUSED:
            raise ValueError("No paused batch found to resume")
        
        self.logger.info(f"Resuming batch processing: {self.current_batch.batch_id}")
        
        # Get remaining companies to process
        remaining_companies = self._get_remaining_companies()
        
        if not remaining_companies:
            self.logger.info("No remaining companies to process")
            self.current_batch.status = ProcessingStatus.COMPLETED
            self.current_batch.end_time = datetime.now()
            self._store_batch_progress()
            return self._get_batch_results()
        
        # Resume processing
        self.current_batch.status = ProcessingStatus.IN_PROGRESS
        self.current_batch.last_update_time = datetime.now()
        
        return self.run_batch_processing(remaining_companies)
    
    def get_batch_progress(self, batch_id: Optional[str] = None) -> Optional[BatchProgress]:
        """
        Get progress information for a batch.
        
        Args:
            batch_id: Optional batch ID. If None, returns current batch progress.
            
        Returns:
            BatchProgress object or None if not found
        """
        if batch_id:
            return self._load_batch_progress(batch_id)
        return self.current_batch
    
    def list_batch_history(self) -> List[Dict[str, Any]]:
        """
        Get list of all batch processing sessions.
        
        Returns:
            List of batch progress summaries
        """
        try:
            # Query Notion for batch progress records
            batch_records = self._get_batch_history_from_notion()
            return batch_records
        except Exception as e:
            self.logger.error(f"Failed to get batch history: {str(e)}")
            return []
    
    def add_progress_callback(self, callback: Callable[[BatchProgress], None]) -> None:
        """
        Add a progress callback function.
        
        Args:
            callback: Function to call with progress updates
        """
        self.progress_callbacks.append(callback)
    
    def remove_progress_callback(self, callback: Callable[[BatchProgress], None]) -> None:
        """
        Remove a progress callback function.
        
        Args:
            callback: Function to remove from callbacks
        """
        if callback in self.progress_callbacks:
            self.progress_callbacks.remove(callback)
    
    def _process_company_with_tracking(self, company_data: CompanyData) -> CompanyProcessingResult:
        """
        Process a single company with detailed tracking.
        
        Args:
            company_data: Company information
            
        Returns:
            CompanyProcessingResult with processing details
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"Processing company with tracking: {company_data.name}")
            
            prospects = self.process_company(company_data)
            
            # Count results
            emails_found = sum(1 for p in prospects if p.email)
            linkedin_profiles_found = sum(1 for p in prospects if p.linkedin_url)
            
            processing_time = time.time() - start_time
            
            result = CompanyProcessingResult(
                company_name=company_data.name,
                success=True,
                prospects_found=len(prospects),
                emails_found=emails_found,
                linkedin_profiles_found=linkedin_profiles_found,
                processing_time=processing_time
            )
            
            self.logger.info(f"Successfully processed {company_data.name}: {len(prospects)} prospects")
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            
            result = CompanyProcessingResult(
                company_name=company_data.name,
                success=False,
                prospects_found=0,
                emails_found=0,
                linkedin_profiles_found=0,
                error_message=str(e),
                processing_time=processing_time
            )
            
            self.logger.error(f"Failed to process {company_data.name}: {str(e)}")
            return result
    
    def _update_batch_progress(self, current_company: str, result: CompanyProcessingResult) -> None:
        """
        Update batch progress with latest results.
        
        Args:
            current_company: Name of currently processed company
            result: Processing result for the company
        """
        if not self.current_batch:
            return
        
        self.current_batch.processed_companies += 1
        self.current_batch.current_company = current_company
        self.current_batch.last_update_time = datetime.now()
        
        if result.success:
            self.current_batch.successful_companies += 1
            self.current_batch.total_prospects += result.prospects_found
        else:
            self.current_batch.failed_companies += 1
        
        # Notify progress callbacks
        for callback in self.progress_callbacks:
            try:
                callback(self.current_batch)
            except Exception as e:
                self.logger.warning(f"Progress callback failed: {str(e)}")
    
    def _store_batch_progress(self) -> None:
        """Store batch progress in Notion for recovery."""
        if not self.current_batch:
            return
        
        try:
            # Create a special page in Notion to store batch progress
            progress_data = self.current_batch.to_dict()
            
            # Store as JSON in notes field of a special prospect record
            batch_prospect = Prospect(
                name=f"BATCH_PROGRESS_{self.current_batch.batch_id}",
                role="System",
                company="Batch Processing",
                notes=json.dumps(progress_data),
                status=ProspectStatus.NOT_CONTACTED,
                created_at=self.current_batch.start_time
            )
            
            # Try to store or update existing batch progress record
            existing_prospects = self.notion_manager.get_prospects({
                'company': 'Batch Processing'
            })
            
            batch_record = None
            for prospect in existing_prospects:
                if prospect.name == f"BATCH_PROGRESS_{self.current_batch.batch_id}":
                    batch_record = prospect
                    break
            
            if batch_record:
                # Update existing record
                self.notion_manager.update_prospect_status(
                    batch_record.id,
                    ProspectStatus.NOT_CONTACTED,
                    notes=json.dumps(progress_data)
                )
            else:
                # Create new record
                self.notion_manager.store_prospect(batch_prospect)
            
            self.logger.debug(f"Stored batch progress for {self.current_batch.batch_id}")
            
        except Exception as e:
            self.logger.warning(f"Failed to store batch progress: {str(e)}")
    
    def _load_batch_progress(self, batch_id: str) -> Optional[BatchProgress]:
        """
        Load batch progress from Notion.
        
        Args:
            batch_id: Batch ID to load
            
        Returns:
            BatchProgress object or None if not found
        """
        try:
            prospects = self.notion_manager.get_prospects({
                'company': 'Batch Processing'
            })
            
            for prospect in prospects:
                if prospect.name == f"BATCH_PROGRESS_{batch_id}":
                    progress_data = json.loads(prospect.notes)
                    return BatchProgress.from_dict(progress_data)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to load batch progress for {batch_id}: {str(e)}")
            return None
    
    def _get_remaining_companies(self) -> List[CompanyData]:
        """
        Get list of companies that still need to be processed.
        
        Returns:
            List of remaining CompanyData objects
        """
        # This is a simplified implementation
        # In a real scenario, you'd need to track which companies were processed
        # For now, return empty list as we don't have the original company list
        return []
    
    def _get_batch_results(self) -> Dict[str, Any]:
        """
        Get comprehensive batch processing results.
        
        Returns:
            Dictionary containing batch results and statistics
        """
        if not self.current_batch:
            return {}
        
        total_processing_time = sum(
            r.processing_time for r in self.batch_results 
            if r.processing_time is not None
        )
        
        return {
            'batch_id': self.current_batch.batch_id,
            'status': self.current_batch.status.value,
            'summary': {
                'total_companies': self.current_batch.total_companies,
                'processed_companies': self.current_batch.processed_companies,
                'successful_companies': self.current_batch.successful_companies,
                'failed_companies': self.current_batch.failed_companies,
                'total_prospects': self.current_batch.total_prospects,
                'success_rate': (self.current_batch.successful_companies / max(1, self.current_batch.processed_companies)) * 100,
                'total_processing_time': total_processing_time,
                'average_processing_time': total_processing_time / max(1, len(self.batch_results))
            },
            'timeline': {
                'start_time': self.current_batch.start_time.isoformat(),
                'end_time': self.current_batch.end_time.isoformat() if self.current_batch.end_time else None,
                'last_update': self.current_batch.last_update_time.isoformat(),
                'duration_seconds': (
                    (self.current_batch.end_time or datetime.now()) - self.current_batch.start_time
                ).total_seconds()
            },
            'detailed_results': [
                {
                    'company_name': r.company_name,
                    'success': r.success,
                    'prospects_found': r.prospects_found,
                    'emails_found': r.emails_found,
                    'linkedin_profiles_found': r.linkedin_profiles_found,
                    'processing_time': r.processing_time,
                    'error_message': r.error_message
                }
                for r in self.batch_results
            ]
        }
    
    def _get_batch_history_from_notion(self) -> List[Dict[str, Any]]:
        """
        Get batch processing history from Notion.
        
        Returns:
            List of batch history records
        """
        try:
            prospects = self.notion_manager.get_prospects({
                'company': 'Batch Processing'
            })
            
            batch_history = []
            for prospect in prospects:
                if prospect.name.startswith('BATCH_PROGRESS_'):
                    try:
                        progress_data = json.loads(prospect.notes)
                        batch_history.append({
                            'batch_id': progress_data['batch_id'],
                            'status': progress_data['status'],
                            'total_companies': progress_data['total_companies'],
                            'processed_companies': progress_data['processed_companies'],
                            'successful_companies': progress_data['successful_companies'],
                            'start_time': progress_data['start_time'],
                            'end_time': progress_data.get('end_time'),
                            'last_update': progress_data['last_update_time']
                        })
                    except (json.JSONDecodeError, KeyError) as e:
                        self.logger.warning(f"Failed to parse batch record: {str(e)}")
                        continue
            
            # Sort by start time, most recent first
            batch_history.sort(key=lambda x: x['start_time'], reverse=True)
            return batch_history
            
        except Exception as e:
            self.logger.error(f"Failed to get batch history: {str(e)}")
            return []    
# ==================== PROGRESS TRACKING METHODS ====================
    
    def _start_campaign_tracking(self, campaign_name: str, target_companies: int) -> None:
        """Initialize campaign progress tracking in Notion."""
        if not self.dashboard_config.get('enable_progress_tracking'):
            return
            
        try:
            # Create campaign progress object
            self.current_campaign = CampaignProgress(
                campaign_id=f"campaign_{int(datetime.now().timestamp())}",
                name=campaign_name,
                status=CampaignStatus.RUNNING,
                start_time=datetime.now(),
                current_step="Initializing",
                companies_target=target_companies,
                companies_processed=0,
                prospects_found=0,
                emails_generated=0,
                success_rate=0.0,
                error_count=0
            )
            
            # Create campaign entry in Notion if database is configured
            if self.dashboard_config.get('campaigns_db_id'):
                self.campaign_page_id = self.notion_manager.create_campaign(
                    self.current_campaign,
                    self.dashboard_config['campaigns_db_id']
                )
                self.logger.info(f"Started campaign tracking: {campaign_name}")
            
        except Exception as e:
            self.logger.warning(f"Failed to start campaign tracking: {str(e)}")
    
    def _update_campaign_step(self, step: str) -> None:
        """Update current campaign step."""
        if not self.current_campaign:
            return
            
        self.current_campaign.current_step = step
        self._update_campaign_in_notion()
    
    def _update_campaign_current_company(self, company_name: str) -> None:
        """Update current company being processed."""
        if not self.current_campaign:
            return
            
        self.current_campaign.current_company = company_name
        self._update_campaign_in_notion()
    
    def _update_campaign_companies_target(self, target: int) -> None:
        """Update target number of companies."""
        if not self.current_campaign:
            return
            
        self.current_campaign.companies_target = target
        self._update_campaign_in_notion()
    
    def _update_campaign_progress(self) -> None:
        """Update campaign progress with current stats."""
        if not self.current_campaign:
            return
            
        self.current_campaign.companies_processed = self.stats['companies_processed']
        self.current_campaign.prospects_found = self.stats['prospects_found']
        self.current_campaign.emails_generated = self.stats['emails_generated']
        self.current_campaign.error_count = self.stats['errors']
        
        # Calculate success rate
        if self.current_campaign.companies_processed > 0:
            successful_companies = self.current_campaign.companies_processed - self.current_campaign.error_count
            self.current_campaign.success_rate = successful_companies / self.current_campaign.companies_processed
        
        self._update_campaign_in_notion()
    
    def _complete_campaign_tracking(self, status: CampaignStatus) -> None:
        """Complete campaign tracking with final status."""
        if not self.current_campaign:
            return
            
        self.current_campaign.status = status
        self.current_campaign.current_step = "Completed" if status == CampaignStatus.COMPLETED else "Failed"
        self._update_campaign_progress()
        self._update_campaign_in_notion()
        
        self.logger.info(f"Campaign completed with status: {status.value}")
    
    def _update_campaign_in_notion(self) -> None:
        """Update campaign progress in Notion."""
        if not self.campaign_page_id or not self.current_campaign:
            return
            
        try:
            self.notion_manager.update_campaign_progress(
                self.campaign_page_id,
                self.current_campaign
            )
        except Exception as e:
            self.logger.warning(f"Failed to update campaign in Notion: {str(e)}")
    
    def _log_processing_step(self, campaign_name: str, company_name: str, step: str, 
                           status: str, duration: float = None, details: str = None,
                           error_message: str = None, prospects_found: int = 0, 
                           emails_found: int = 0) -> None:
        """Log a processing step to Notion."""
        if not self.dashboard_config.get('enable_progress_tracking') or not self.dashboard_config.get('logs_db_id'):
            return
            
        try:
            self.notion_manager.log_processing_step(
                logs_db_id=self.dashboard_config['logs_db_id'],
                campaign_name=campaign_name,
                company_name=company_name,
                step=step,
                status=status,
                duration=duration,
                details=details,
                error_message=error_message,
                prospects_found=prospects_found,
                emails_found=emails_found
            )
        except Exception as e:
            self.logger.warning(f"Failed to log processing step: {str(e)}")
    
    def _update_system_status(self, component: str, status: str, details: str = None) -> None:
        """Update system component status in Notion."""
        if not self.dashboard_config.get('enable_progress_tracking') or not self.dashboard_config.get('status_db_id'):
            return
            
        try:
            self.notion_manager.update_system_status(
                status_db_id=self.dashboard_config['status_db_id'],
                component=component,
                status=status,
                details=details
            )
        except Exception as e:
            self.logger.warning(f"Failed to update system status: {str(e)}")
    
    def get_campaign_progress(self) -> Optional[Dict[str, Any]]:
        """Get current campaign progress information."""
        if not self.current_campaign:
            return None
            
        return {
            'campaign_id': self.current_campaign.campaign_id,
            'name': self.current_campaign.name,
            'status': self.current_campaign.status.value,
            'progress_percentage': (self.current_campaign.companies_processed / max(1, self.current_campaign.companies_target)) * 100,
            'current_step': self.current_campaign.current_step,
            'current_company': self.current_campaign.current_company,
            'companies_target': self.current_campaign.companies_target,
            'companies_processed': self.current_campaign.companies_processed,
            'prospects_found': self.current_campaign.prospects_found,
            'emails_generated': self.current_campaign.emails_generated,
            'success_rate': self.current_campaign.success_rate * 100,
            'error_count': self.current_campaign.error_count,
            'start_time': self.current_campaign.start_time.isoformat(),
            'estimated_completion': self.current_campaign.estimated_completion.isoformat() if self.current_campaign.estimated_completion else None
        }
    
    # ==================== DAILY ANALYTICS METHODS ====================
    
    def create_daily_summary(self, analytics_db_id: str) -> bool:
        """Create or update daily analytics summary."""
        if not self.dashboard_config.get('enable_progress_tracking'):
            return False
            
        try:
            from datetime import date
            today = date.today()
            
            # Get today's campaign data
            daily_stats = self._calculate_daily_stats()
            
            # Check if today's entry already exists
            existing_entry = self._find_daily_analytics_entry(analytics_db_id, today)
            
            # Prepare properties for both create and update
            base_properties = {
                "Campaigns Run": {"number": daily_stats.get('campaigns_run', 0)},
                "Companies Processed": {"number": daily_stats.get('companies_processed', 0)},
                "Prospects Found": {"number": daily_stats.get('prospects_found', 0)},
                "Emails Generated": {"number": daily_stats.get('emails_generated', 0)},
                "Emails Sent": {"number": daily_stats.get('emails_sent', 0)},
                "Success Rate": {"number": daily_stats.get('success_rate', 0.0)},
                "Processing Time (min)": {"number": daily_stats.get('processing_time_minutes', 0)},
                "API Calls Made": {"number": daily_stats.get('api_calls', 0)},
                "Errors Encountered": {"number": daily_stats.get('errors', 0)},
                "Top Performing Campaign": {
                    "rich_text": [{"text": {"content": daily_stats.get('top_campaign', 'N/A')}}]
                }
            }
            
            if existing_entry:
                # Update existing entry (don't update title field)
                self.notion_manager.client.pages.update(
                    page_id=existing_entry,
                    properties=base_properties
                )
            else:
                # Create new entry (include title field)
                create_properties = base_properties.copy()
                create_properties["Date"] = {
                    "title": [{"text": {"content": today.strftime("%Y-%m-%d")}}]
                }
                
                self.notion_manager.client.pages.create(
                    parent={"database_id": analytics_db_id},
                    properties=create_properties
                )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create daily summary: {str(e)}")
            return False
    
    def _calculate_daily_stats(self) -> Dict[str, Any]:
        """Calculate daily statistics from Notion databases for today."""
        try:
            from datetime import date, datetime, timedelta
            today = date.today()
            today_start = datetime.combine(today, datetime.min.time())
            today_end = datetime.combine(today, datetime.max.time())
            
            stats = {
                'campaigns_run': 0,
                'companies_processed': 0,
                'prospects_found': 0,
                'emails_generated': 0,
                'emails_sent': 0,
                'success_rate': 0.0,
                'processing_time_minutes': 0,
                'api_calls': 0,
                'errors': 0,
                'top_campaign': 'N/A'
            }
            
            # Get today's campaigns from Campaign Runs database
            if self.dashboard_config.get('campaigns_db_id'):
                try:
                    campaigns_response = self.notion_manager.client.databases.query(
                        database_id=self.dashboard_config['campaigns_db_id'],
                        filter={
                            "property": "Start Time",
                            "date": {
                                "on_or_after": today_start.isoformat()
                            }
                        }
                    )
                    
                    campaigns_today = campaigns_response['results']
                    stats['campaigns_run'] = len(campaigns_today)
                    
                    # Calculate totals from campaigns
                    total_companies = 0
                    total_prospects = 0
                    total_emails = 0
                    total_errors = 0
                    total_processing_time = 0
                    best_campaign = None
                    best_prospects = 0
                    
                    for campaign in campaigns_today:
                        properties = campaign['properties']
                        
                        companies = self.notion_manager._extract_number(properties.get('Companies Processed', {})) or 0
                        prospects = self.notion_manager._extract_number(properties.get('Prospects Found', {})) or 0
                        emails = self.notion_manager._extract_number(properties.get('Emails Generated', {})) or 0
                        errors = self.notion_manager._extract_number(properties.get('Error Count', {})) or 0
                        
                        total_companies += companies
                        total_prospects += prospects
                        total_emails += emails
                        total_errors += errors
                        
                        # Find best performing campaign
                        if prospects > best_prospects:
                            best_prospects = prospects
                            campaign_name = self.notion_manager._extract_title(properties.get('Campaign Name', {}))
                            best_campaign = campaign_name or 'Unknown Campaign'
                    
                    stats['companies_processed'] = total_companies
                    stats['prospects_found'] = total_prospects
                    stats['emails_generated'] = total_emails
                    stats['errors'] = total_errors
                    stats['top_campaign'] = best_campaign or 'N/A'
                    
                    # Calculate success rate
                    if total_companies > 0:
                        stats['success_rate'] = (total_companies - total_errors) / total_companies
                    
                except Exception as e:
                    self.logger.warning(f"Failed to get campaign stats: {str(e)}")
            
            # Get today's processing logs for more detailed stats
            if self.dashboard_config.get('logs_db_id'):
                try:
                    logs_response = self.notion_manager.client.databases.query(
                        database_id=self.dashboard_config['logs_db_id'],
                        filter={
                            "property": "Timestamp",
                            "date": {
                                "on_or_after": today_start.isoformat()
                            }
                        }
                    )
                    
                    # Calculate total processing time from logs
                    total_duration = 0
                    for log_entry in logs_response['results']:
                        properties = log_entry['properties']
                        duration = self.notion_manager._extract_number(properties.get('Duration (s)', {})) or 0
                        total_duration += duration
                    
                    stats['processing_time_minutes'] = total_duration / 60
                    
                except Exception as e:
                    self.logger.warning(f"Failed to get processing logs: {str(e)}")
            
            # Get email stats from prospect database (emails sent today)
            try:
                prospects = self.notion_manager.get_prospects()
                emails_sent_today = 0
                
                for prospect in prospects:
                    # Check if prospect was contacted today (this is a simplified check)
                    if prospect.contacted:
                        emails_sent_today += 1
                
                stats['emails_sent'] = emails_sent_today
                
            except Exception as e:
                self.logger.warning(f"Failed to get email stats: {str(e)}")
            
            # Estimate API calls based on operations performed
            # This is an approximation based on typical API usage
            estimated_api_calls = 0
            estimated_api_calls += stats['campaigns_run'] * 5  # Campaign setup calls
            estimated_api_calls += stats['companies_processed'] * 15  # ProductHunt + domain extraction + team extraction
            estimated_api_calls += stats['prospects_found'] * 8  # LinkedIn + email finding + AI processing
            estimated_api_calls += stats['emails_generated'] * 3  # Email generation + storage
            estimated_api_calls += len(logs_response.get('results', [])) * 2 if 'logs_response' in locals() else 0  # Logging calls
            
            stats['api_calls'] = estimated_api_calls
            
            self.logger.info(f"Calculated daily stats: {stats}")
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to calculate daily stats: {str(e)}")
            return {
                'campaigns_run': 0,
                'companies_processed': 0,
                'prospects_found': 0,
                'emails_generated': 0,
                'emails_sent': 0,
                'success_rate': 0.0,
                'processing_time_minutes': 0,
                'api_calls': 0,
                'errors': 0,
                'top_campaign': 'N/A'
            }
    
    def _find_daily_analytics_entry(self, analytics_db_id: str, date_obj) -> Optional[str]:
        """Find existing daily analytics entry for a specific date."""
        try:
            response = self.notion_manager.client.databases.query(
                database_id=analytics_db_id,
                filter={
                    "property": "Date",
                    "title": {
                        "equals": date_obj.strftime("%Y-%m-%d")
                    }
                }
            )
            
            if response["results"]:
                return response["results"][0]["id"]
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to find daily analytics entry: {str(e)}")
            return None
    
    # ==================== EMAIL QUEUE METHODS ====================
    
    def add_email_to_queue(self, email_queue_db_id: str, prospect_id: str, 
                          email_content, campaign_name: str, priority: str = "Medium") -> bool:
        """Add generated email to the approval queue."""
        if not self.dashboard_config.get('enable_progress_tracking'):
            return False
            
        try:
            # Get prospect data
            prospect_data = self.notion_manager.get_prospect_data_for_email(prospect_id)
            
            properties = {
                "Email ID": {
                    "title": [{"text": {"content": f"email_{prospect_id}_{int(datetime.now().timestamp())}"}}]
                },
                "Prospect Name": {
                    "rich_text": [{"text": {"content": prospect_data.get('name', 'Unknown')}}]
                },
                "Company": {
                    "rich_text": [{"text": {"content": prospect_data.get('company', 'Unknown')}}]
                },
                "Email Subject": {
                    "rich_text": [{"text": {"content": email_content.subject}}]
                },
                "Status": {
                    "select": {"name": "Pending Review"}
                },
                "Generated Date": {
                    "date": {"start": datetime.now().isoformat()}
                },
                "Campaign": {
                    "rich_text": [{"text": {"content": campaign_name}}]
                },
                "Template Type": {
                    "rich_text": [{"text": {"content": email_content.template_type if hasattr(email_content, 'template_type') else 'Unknown'}}]
                },
                "Personalization Score": {
                    "number": email_content.personalization_score if hasattr(email_content, 'personalization_score') else 0.0
                },
                "Email Content": {
                    "rich_text": [{"text": {"content": email_content.body[:2000]}}]  # Truncate for Notion
                },
                "Priority": {
                    "select": {"name": priority}
                }
            }
            
            self.notion_manager.client.pages.create(
                parent={"database_id": email_queue_db_id},
                properties=properties
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add email to queue: {str(e)}")
            return False
    
    def check_email_approvals(self, email_queue_db_id: str) -> List[Dict[str, Any]]:
        """Check for approved emails ready to send."""
        if not self.dashboard_config.get('enable_progress_tracking'):
            return []
            
        try:
            response = self.notion_manager.client.databases.query(
                database_id=email_queue_db_id,
                filter={
                    "property": "Status",
                    "select": {
                        "equals": "Approved"
                    }
                }
            )
            
            approved_emails = []
            for result in response["results"]:
                properties = result["properties"]
                approved_emails.append({
                    "email_id": self.notion_manager._extract_title(properties.get("Email ID", {})),
                    "prospect_name": self.notion_manager._extract_rich_text(properties.get("Prospect Name", {})),
                    "company": self.notion_manager._extract_rich_text(properties.get("Company", {})),
                    "subject": self.notion_manager._extract_rich_text(properties.get("Email Subject", {})),
                    "content": self.notion_manager._extract_rich_text(properties.get("Email Content", {})),
                    "page_id": result["id"]
                })
            
            return approved_emails
            
        except Exception as e:
            self.logger.error(f"Failed to check email approvals: {str(e)}")
            return []
    
    def update_email_status(self, email_page_id: str, status: str, notes: str = None) -> bool:
        """Update email status in the queue."""
        try:
            properties = {
                "Status": {"select": {"name": status}}
            }
            
            if status == "Approved":
                properties["Approved Date"] = {"date": {"start": datetime.now().isoformat()}}
            elif status == "Sent":
                properties["Sent Date"] = {"date": {"start": datetime.now().isoformat()}}
            
            if notes:
                properties["Approval Notes"] = {
                    "rich_text": [{"text": {"content": notes}}]
                }
            
            self.notion_manager.client.pages.update(
                page_id=email_page_id,
                properties=properties
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update email status: {str(e)}")
            return False
    
    # ==================== INTERACTIVE CAMPAIGN CONTROLS ====================
    
    def check_campaign_controls(self) -> Dict[str, Any]:
        """Check for interactive campaign control commands from Notion."""
        if not self.campaign_page_id or not self.dashboard_config.get('enable_progress_tracking'):
            return {"action": "continue"}
            
        try:
            # Get current campaign page
            response = self.notion_manager.client.pages.retrieve(page_id=self.campaign_page_id)
            properties = response["properties"]
            
            # Check for control commands
            status = self.notion_manager._extract_select(properties.get("Status", {}))
            
            if status == "Paused":
                return {"action": "pause", "message": "Campaign paused by user"}
            elif status == "Failed":
                return {"action": "stop", "message": "Campaign stopped by user"}
            else:
                return {"action": "continue"}
                
        except Exception as e:
            self.logger.error(f"Failed to check campaign controls: {str(e)}")
            return {"action": "continue"}
    
    def pause_campaign(self, reason: str = "User requested") -> bool:
        """Pause the current campaign."""
        if not self.current_campaign:
            return False
            
        try:
            self.current_campaign.status = CampaignStatus.PAUSED
            self.current_campaign.current_step = f"Paused: {reason}"
            self._update_campaign_in_notion()
            
            self.logger.info(f"Campaign paused: {reason}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to pause campaign: {str(e)}")
            return False
    
    def resume_campaign(self) -> bool:
        """Resume a paused campaign."""
        if not self.current_campaign or self.current_campaign.status != CampaignStatus.PAUSED:
            return False
            
        try:
            self.current_campaign.status = CampaignStatus.RUNNING
            self.current_campaign.current_step = "Resumed"
            self._update_campaign_in_notion()
            
            self.logger.info("Campaign resumed")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to resume campaign: {str(e)}")
            return False
    
    def add_priority_companies(self, companies: List[str]) -> bool:
        """Add companies to priority processing queue."""
        try:
            # This could be implemented by creating a priority companies database
            # For now, we'll log the priority companies
            self.logger.info(f"Priority companies added: {', '.join(companies)}")
            
            # Update campaign with priority companies info
            if self.current_campaign:
                priority_info = f"Priority companies: {', '.join(companies)}"
                self.current_campaign.current_step = f"Processing priority companies: {companies[0]}"
                self._update_campaign_in_notion()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add priority companies: {str(e)}")
            return False