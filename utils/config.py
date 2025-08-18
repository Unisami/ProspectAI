"""Configuration management for the job prospect automation system."""


# Load environment variables from .env file

import os
import json
import re
from dataclasses import dataclass
from typing import (
    Optional,
    Dict,
    Any,
    List
)
from pathlib import Path
import os

import yaml
from dotenv import load_dotenv

from services.sender_profile_manager import SenderProfileManager


load_dotenv()


@dataclass
class Config:
    """Configuration class for managing all system settings."""
    
    # API Keys
    notion_token: str
    hunter_api_key: str
    openai_api_key: Optional[str] = None
    
    # Azure OpenAI Configuration
    azure_openai_api_key: Optional[str] = None
    azure_openai_endpoint: Optional[str] = None
    azure_openai_deployment_name: str = "gpt-4"
    azure_openai_api_version: str = "2024-02-15-preview"
    use_azure_openai: bool = False
    
    # Rate Limiting
    scraping_delay: float = 0.3
    hunter_requests_per_minute: int = 10
    
    # Processing Limits
    max_products_per_run: int = 50
    max_prospects_per_company: int = 10
    
    # Notion Configuration
    notion_database_id: Optional[str] = None
    
    # Email Generation
    email_template_type: str = "professional"
    personalization_level: str = "medium"
    
    # Email Sending (Resend)
    resend_api_key: Optional[str] = None
    sender_email: str = ""
    sender_name: str = ""
    reply_to_email: Optional[str] = None
    resend_requests_per_minute: int = 100
    
    # AI Parsing Configuration
    enable_ai_parsing: bool = True
    ai_parsing_model: str = "gpt-4"
    ai_parsing_max_retries: int = 3
    ai_parsing_timeout: int = 30
    
    # Product Analysis Configuration
    enable_product_analysis: bool = True
    product_analysis_model: str = "gpt-4"
    product_analysis_max_retries: int = 3
    
    # Enhanced Email Generation
    enhanced_personalization: bool = True
    email_generation_model: str = "gpt-4"
    max_email_length: int = 500
    
    # Workflow Configuration
    enable_enhanced_workflow: bool = True
    batch_processing_enabled: bool = True
    auto_send_emails: bool = False
    email_review_required: bool = True
    
    # Sender Profile Configuration
    sender_profile_path: Optional[str] = None
    sender_profile_format: str = "markdown"  # markdown, json, yaml
    enable_sender_profile: bool = True
    enable_interactive_profile_setup: bool = True
    require_sender_profile: bool = False
    sender_profile_completeness_threshold: float = 0.7
    
    # Progress Tracking Configuration
    enable_progress_tracking: bool = True
    campaigns_db_id: Optional[str] = None
    logs_db_id: Optional[str] = None
    status_db_id: Optional[str] = None
    analytics_db_id: Optional[str] = None
    email_queue_db_id: Optional[str] = None
    dashboard_id: Optional[str] = None
    
    # Notification Configuration
    enable_notifications: bool = True
    notification_methods: List[str] = None
    
    # Interactive Controls Configuration (deprecated)
    enable_interactive_controls: bool = False
    control_check_interval: int = 30
    
    # User Notification Configuration
    notion_user_id: Optional[str] = None  # User's Notion ID for @mentions
    user_email: Optional[str] = None  # User email for notifications
    
    @classmethod
    def from_env(cls) -> "Config":
        """Create configuration from environment variables."""
        # Required API keys
        notion_token = os.getenv("NOTION_TOKEN")
        hunter_api_key = os.getenv("HUNTER_API_KEY")
        openai_api_key = os.getenv("OPENAI_API_KEY")
        
        if not notion_token:
            raise ValueError("NOTION_TOKEN environment variable is required")
        if not hunter_api_key:
            raise ValueError("HUNTER_API_KEY environment variable is required")
        
        # Check if Azure OpenAI should be used
        use_azure_openai = os.getenv("USE_AZURE_OPENAI", "false").lower() in ("true", "1", "yes")
        
        # Only require OpenAI API key if not using Azure OpenAI
        if not use_azure_openai and not openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        # If using Azure OpenAI, validate Azure-specific requirements
        if use_azure_openai:
            azure_openai_api_key = os.getenv("AZURE_OPENAI_API_KEY")
            azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            
            if not azure_openai_api_key:
                raise ValueError("AZURE_OPENAI_API_KEY environment variable is required when USE_AZURE_OPENAI=true")
            if not azure_openai_endpoint:
                raise ValueError("AZURE_OPENAI_ENDPOINT environment variable is required when USE_AZURE_OPENAI=true")
        
        return cls(
            notion_token=notion_token,
            hunter_api_key=hunter_api_key,
            openai_api_key=openai_api_key or "",
            azure_openai_api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            azure_openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            azure_openai_deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4"),
            azure_openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
            use_azure_openai=use_azure_openai,
            scraping_delay=float(os.getenv("SCRAPING_DELAY", "0.3")),
            hunter_requests_per_minute=int(os.getenv("HUNTER_REQUESTS_PER_MINUTE", "10")),
            max_products_per_run=int(os.getenv("MAX_PRODUCTS_PER_RUN", "50")),
            max_prospects_per_company=int(os.getenv("MAX_PROSPECTS_PER_COMPANY", "10")),
            notion_database_id=os.getenv("NOTION_DATABASE_ID"),
            email_template_type=os.getenv("EMAIL_TEMPLATE_TYPE", "professional"),
            personalization_level=os.getenv("PERSONALIZATION_LEVEL", "medium"),
            resend_api_key=os.getenv("RESEND_API_KEY"),
            sender_email=os.getenv("SENDER_EMAIL", ""),
            sender_name=os.getenv("SENDER_NAME", ""),
            reply_to_email=os.getenv("REPLY_TO_EMAIL"),
            resend_requests_per_minute=int(os.getenv("RESEND_REQUESTS_PER_MINUTE", "100")),
            enable_ai_parsing=os.getenv("ENABLE_AI_PARSING", "true").lower() in ("true", "1", "yes"),
            ai_parsing_model=os.getenv("AI_PARSING_MODEL", "gpt-4"),
            ai_parsing_max_retries=int(os.getenv("AI_PARSING_MAX_RETRIES", "3")),
            ai_parsing_timeout=int(os.getenv("AI_PARSING_TIMEOUT", "30")),
            enable_product_analysis=os.getenv("ENABLE_PRODUCT_ANALYSIS", "true").lower() in ("true", "1", "yes"),
            product_analysis_model=os.getenv("PRODUCT_ANALYSIS_MODEL", "gpt-4"),
            product_analysis_max_retries=int(os.getenv("PRODUCT_ANALYSIS_MAX_RETRIES", "3")),
            enhanced_personalization=os.getenv("ENHANCED_PERSONALIZATION", "true").lower() in ("true", "1", "yes"),
            email_generation_model=os.getenv("EMAIL_GENERATION_MODEL", "gpt-4"),
            max_email_length=int(os.getenv("MAX_EMAIL_LENGTH", "500")),
            enable_enhanced_workflow=os.getenv("ENABLE_ENHANCED_WORKFLOW", "true").lower() in ("true", "1", "yes"),
            batch_processing_enabled=os.getenv("BATCH_PROCESSING_ENABLED", "true").lower() in ("true", "1", "yes"),
            auto_send_emails=os.getenv("AUTO_SEND_EMAILS", "false").lower() in ("true", "1", "yes"),
            email_review_required=os.getenv("EMAIL_REVIEW_REQUIRED", "true").lower() in ("true", "1", "yes"),
            # Sender Profile Configuration
            sender_profile_path=os.getenv("SENDER_PROFILE_PATH"),
            sender_profile_format=os.getenv("SENDER_PROFILE_FORMAT", "markdown"),
            enable_sender_profile=os.getenv("ENABLE_SENDER_PROFILE", "true").lower() in ("true", "1", "yes"),
            enable_interactive_profile_setup=os.getenv("ENABLE_INTERACTIVE_PROFILE_SETUP", "true").lower() in ("true", "1", "yes"),
            require_sender_profile=os.getenv("REQUIRE_SENDER_PROFILE", "false").lower() in ("true", "1", "yes"),
            sender_profile_completeness_threshold=float(os.getenv("SENDER_PROFILE_COMPLETENESS_THRESHOLD", "0.7")),
            # Progress Tracking Configuration
            enable_progress_tracking=os.getenv("ENABLE_PROGRESS_TRACKING", "true").lower() in ("true", "1", "yes"),
            campaigns_db_id=os.getenv("CAMPAIGNS_DB_ID"),
            logs_db_id=os.getenv("LOGS_DB_ID"),
            status_db_id=os.getenv("STATUS_DB_ID"),
            analytics_db_id=os.getenv("ANALYTICS_DB_ID"),
            email_queue_db_id=os.getenv("EMAIL_QUEUE_DB_ID"),
            dashboard_id=os.getenv("DASHBOARD_ID"),
            # Notification Configuration
            enable_notifications=os.getenv("ENABLE_NOTIFICATIONS", "true").lower() in ("true", "1", "yes"),
            notification_methods=os.getenv("NOTIFICATION_METHODS", "notion").split(",") if os.getenv("NOTIFICATION_METHODS") else ["notion"],
            # Interactive Controls Configuration (deprecated)
            enable_interactive_controls=False,
            control_check_interval=int(os.getenv("CONTROL_CHECK_INTERVAL", "30")),
            # User Notification Configuration
            notion_user_id=os.getenv("NOTION_USER_ID"),
            user_email=os.getenv("USER_EMAIL"),
        )
    
    @classmethod
    def from_file(cls, config_path: str) -> "Config":
        """Create configuration from YAML or JSON file."""
        config_file = Path(config_path)
        
        if not config_file.exists():
            raise ValueError(f"Configuration file not found: {config_path}")
        
        # Load configuration data
        with open(config_file, 'r') as f:
            if config_file.suffix.lower() in ['.yaml', '.yml']:
                config_data = yaml.safe_load(f)
            elif config_file.suffix.lower() == '.json':
                config_data = json.load(f)
            else:
                raise ValueError(f"Unsupported configuration file format: {config_file.suffix}")
        
        # Set environment variables from config file (temporary for this process)
        original_env = {}
        for key, value in config_data.items():
            if key.upper() in os.environ:
                original_env[key.upper()] = os.environ[key.upper()]
            os.environ[key.upper()] = str(value)
        
        try:
            # Create config from environment variables
            config = cls.from_env()
            return config
        finally:
            # Restore original environment variables
            for key, value in config_data.items():
                if key.upper() in original_env:
                    os.environ[key.upper()] = original_env[key.upper()]
                else:
                    os.environ.pop(key.upper(), None)
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "Config":
        """Create configuration from dictionary."""
        use_azure_openai = str(config_dict.get("use_azure_openai", config_dict.get("USE_AZURE_OPENAI", "false"))).lower() in ("true", "1", "yes")
        
        return cls(
            notion_token=config_dict.get("notion_token") or config_dict.get("NOTION_TOKEN", ""),
            hunter_api_key=config_dict.get("hunter_api_key") or config_dict.get("HUNTER_API_KEY", ""),
            openai_api_key=config_dict.get("openai_api_key") or config_dict.get("OPENAI_API_KEY", ""),
            azure_openai_api_key=config_dict.get("azure_openai_api_key") or config_dict.get("AZURE_OPENAI_API_KEY"),
            azure_openai_endpoint=config_dict.get("azure_openai_endpoint") or config_dict.get("AZURE_OPENAI_ENDPOINT"),
            azure_openai_deployment_name=config_dict.get("azure_openai_deployment_name", 
                                                        config_dict.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4")),
            azure_openai_api_version=config_dict.get("azure_openai_api_version", 
                                                    config_dict.get("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")),
            use_azure_openai=use_azure_openai,
            scraping_delay=float(config_dict.get("scraping_delay", config_dict.get("SCRAPING_DELAY", 0.3))),
            hunter_requests_per_minute=int(config_dict.get("hunter_requests_per_minute", 
                                                         config_dict.get("HUNTER_REQUESTS_PER_MINUTE", 10))),
            max_products_per_run=int(config_dict.get("max_products_per_run", 
                                                   config_dict.get("MAX_PRODUCTS_PER_RUN", 50))),
            max_prospects_per_company=int(config_dict.get("max_prospects_per_company", 
                                                        config_dict.get("MAX_PROSPECTS_PER_COMPANY", 10))),
            notion_database_id=config_dict.get("notion_database_id") or config_dict.get("NOTION_DATABASE_ID"),
            email_template_type=config_dict.get("email_template_type", 
                                               config_dict.get("EMAIL_TEMPLATE_TYPE", "professional")),
            personalization_level=config_dict.get("personalization_level", 
                                                 config_dict.get("PERSONALIZATION_LEVEL", "medium")),
            resend_api_key=config_dict.get("resend_api_key") or config_dict.get("RESEND_API_KEY"),
            sender_email=config_dict.get("sender_email", config_dict.get("SENDER_EMAIL", "")),
            sender_name=config_dict.get("sender_name", config_dict.get("SENDER_NAME", "")),
            reply_to_email=config_dict.get("reply_to_email") or config_dict.get("REPLY_TO_EMAIL"),
            resend_requests_per_minute=int(config_dict.get("resend_requests_per_minute", 
                                                         config_dict.get("RESEND_REQUESTS_PER_MINUTE", 100))),
            enable_ai_parsing=str(config_dict.get("enable_ai_parsing", 
                                                config_dict.get("ENABLE_AI_PARSING", "true"))).lower() in ("true", "1", "yes"),
            ai_parsing_model=config_dict.get("ai_parsing_model", 
                                           config_dict.get("AI_PARSING_MODEL", "gpt-4")),
            ai_parsing_max_retries=int(config_dict.get("ai_parsing_max_retries", 
                                                     config_dict.get("AI_PARSING_MAX_RETRIES", 3))),
            ai_parsing_timeout=int(config_dict.get("ai_parsing_timeout", 
                                                 config_dict.get("AI_PARSING_TIMEOUT", 30))),
            enable_product_analysis=str(config_dict.get("enable_product_analysis", 
                                                       config_dict.get("ENABLE_PRODUCT_ANALYSIS", "true"))).lower() in ("true", "1", "yes"),
            product_analysis_model=config_dict.get("product_analysis_model", 
                                                  config_dict.get("PRODUCT_ANALYSIS_MODEL", "gpt-4")),
            product_analysis_max_retries=int(config_dict.get("product_analysis_max_retries", 
                                                           config_dict.get("PRODUCT_ANALYSIS_MAX_RETRIES", 3))),
            enhanced_personalization=str(config_dict.get("enhanced_personalization", 
                                                        config_dict.get("ENHANCED_PERSONALIZATION", "true"))).lower() in ("true", "1", "yes"),
            email_generation_model=config_dict.get("email_generation_model", 
                                                  config_dict.get("EMAIL_GENERATION_MODEL", "gpt-4")),
            max_email_length=int(config_dict.get("max_email_length", 
                                               config_dict.get("MAX_EMAIL_LENGTH", 500))),
            enable_enhanced_workflow=str(config_dict.get("enable_enhanced_workflow", 
                                                        config_dict.get("ENABLE_ENHANCED_WORKFLOW", "true"))).lower() in ("true", "1", "yes"),
            batch_processing_enabled=str(config_dict.get("batch_processing_enabled", 
                                                        config_dict.get("BATCH_PROCESSING_ENABLED", "true"))).lower() in ("true", "1", "yes"),
            auto_send_emails=str(config_dict.get("auto_send_emails", 
                                                config_dict.get("AUTO_SEND_EMAILS", "false"))).lower() in ("true", "1", "yes"),
            email_review_required=str(config_dict.get("email_review_required", 
                                                    config_dict.get("EMAIL_REVIEW_REQUIRED", "true"))).lower() in ("true", "1", "yes"),
            # Sender Profile Configuration
            sender_profile_path=config_dict.get("sender_profile_path") or config_dict.get("SENDER_PROFILE_PATH"),
            sender_profile_format=config_dict.get("sender_profile_format", 
                                                config_dict.get("SENDER_PROFILE_FORMAT", "markdown")),
            enable_sender_profile=str(config_dict.get("enable_sender_profile", 
                                                    config_dict.get("ENABLE_SENDER_PROFILE", "true"))).lower() in ("true", "1", "yes"),
            enable_interactive_profile_setup=str(config_dict.get("enable_interactive_profile_setup", 
                                                               config_dict.get("ENABLE_INTERACTIVE_PROFILE_SETUP", "true"))).lower() in ("true", "1", "yes"),
            require_sender_profile=str(config_dict.get("require_sender_profile", 
                                                     config_dict.get("REQUIRE_SENDER_PROFILE", "false"))).lower() in ("true", "1", "yes"),
            sender_profile_completeness_threshold=float(config_dict.get("sender_profile_completeness_threshold", 
                                                                      config_dict.get("SENDER_PROFILE_COMPLETENESS_THRESHOLD", 0.7))),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "notion_token": self.notion_token,
            "hunter_api_key": self.hunter_api_key,
            "openai_api_key": self.openai_api_key,
            "azure_openai_api_key": self.azure_openai_api_key,
            "azure_openai_endpoint": self.azure_openai_endpoint,
            "azure_openai_deployment_name": self.azure_openai_deployment_name,
            "azure_openai_api_version": self.azure_openai_api_version,
            "use_azure_openai": self.use_azure_openai,
            "scraping_delay": self.scraping_delay,
            "hunter_requests_per_minute": self.hunter_requests_per_minute,
            "max_products_per_run": self.max_products_per_run,
            "max_prospects_per_company": self.max_prospects_per_company,
            "notion_database_id": self.notion_database_id,
            "email_template_type": self.email_template_type,
            "personalization_level": self.personalization_level,
            "resend_api_key": self.resend_api_key,
            "sender_email": self.sender_email,
            "sender_name": self.sender_name,
            "reply_to_email": self.reply_to_email,
            "resend_requests_per_minute": self.resend_requests_per_minute,
            "enable_ai_parsing": self.enable_ai_parsing,
            "ai_parsing_model": self.ai_parsing_model,
            "ai_parsing_max_retries": self.ai_parsing_max_retries,
            "ai_parsing_timeout": self.ai_parsing_timeout,
            "enable_product_analysis": self.enable_product_analysis,
            "product_analysis_model": self.product_analysis_model,
            "product_analysis_max_retries": self.product_analysis_max_retries,
            "enhanced_personalization": self.enhanced_personalization,
            "email_generation_model": self.email_generation_model,
            "max_email_length": self.max_email_length,
            "enable_enhanced_workflow": self.enable_enhanced_workflow,
            "batch_processing_enabled": self.batch_processing_enabled,
            "auto_send_emails": self.auto_send_emails,
            "email_review_required": self.email_review_required,
            # Sender Profile Configuration
            "sender_profile_path": self.sender_profile_path,
            "sender_profile_format": self.sender_profile_format,
            "enable_sender_profile": self.enable_sender_profile,
            "enable_interactive_profile_setup": self.enable_interactive_profile_setup,
            "require_sender_profile": self.require_sender_profile,
            "sender_profile_completeness_threshold": self.sender_profile_completeness_threshold,
        }
    
    def save_to_file(self, config_path: str, include_secrets: bool = False) -> None:
        """Save configuration to YAML or JSON file."""
        config_file = Path(config_path)
        config_data = self.to_dict()
        
        # Optionally mask sensitive information
        if not include_secrets:
            config_data["notion_token"] = "***MASKED***"
            config_data["hunter_api_key"] = "***MASKED***"
            config_data["openai_api_key"] = "***MASKED***"
            if config_data["azure_openai_api_key"]:
                config_data["azure_openai_api_key"] = "***MASKED***"
            if config_data["resend_api_key"]:
                config_data["resend_api_key"] = "***MASKED***"
        
        # Save based on file extension
        with open(config_file, 'w') as f:
            if config_file.suffix.lower() in ['.yaml', '.yml']:
                yaml.dump(config_data, f, default_flow_style=False)
            elif config_file.suffix.lower() == '.json':
                json.dump(config_data, f, indent=2)
            else:
                raise ValueError(f"Unsupported configuration file format: {config_file.suffix}")
    
    def validate(self) -> None:
        """Validate configuration values."""
        if self.scraping_delay < 0:
            raise ValueError("Scraping delay must be non-negative")
        if self.hunter_requests_per_minute <= 0:
            raise ValueError("Hunter requests per minute must be positive")
        if self.max_products_per_run <= 0:
            raise ValueError("Max products per run must be positive")
        if self.max_prospects_per_company <= 0:
            raise ValueError("Max prospects per company must be positive")
        if self.email_template_type not in ["professional", "casual", "formal"]:
            raise ValueError("Email template type must be 'professional', 'casual', or 'formal'")
        if self.personalization_level not in ["low", "medium", "high"]:
            raise ValueError("Personalization level must be 'low', 'medium', or 'high'")
        
        # Validate Azure OpenAI configuration if enabled
        if self.use_azure_openai:
            if not self.azure_openai_api_key:
                raise ValueError("Azure OpenAI API key is required when use_azure_openai is True")
            if not self.azure_openai_endpoint:
                raise ValueError("Azure OpenAI endpoint is required when use_azure_openai is True")
            if not self.azure_openai_deployment_name:
                raise ValueError("Azure OpenAI deployment name is required when use_azure_openai is True")
        
        # Validate Resend configuration
        if self.resend_requests_per_minute <= 0:
            raise ValueError("Resend requests per minute must be positive")
        
        # Validate AI parsing configuration
        if self.ai_parsing_max_retries < 0:
            raise ValueError("AI parsing max retries must be non-negative")
        if self.ai_parsing_timeout <= 0:
            raise ValueError("AI parsing timeout must be positive")
        if self.ai_parsing_model not in ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"]:
            raise ValueError("AI parsing model must be a valid OpenAI model")
        
        # Validate product analysis configuration
        if self.product_analysis_max_retries < 0:
            raise ValueError("Product analysis max retries must be non-negative")
        if self.product_analysis_model not in ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"]:
            raise ValueError("Product analysis model must be a valid OpenAI model")
        
        # Validate email generation configuration
        if self.max_email_length <= 0:
            raise ValueError("Max email length must be positive")
        if self.email_generation_model not in ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"]:
            raise ValueError("Email generation model must be a valid OpenAI model")
            
        # Validate sender profile configuration
        if self.sender_profile_format not in ["markdown", "json", "yaml"]:
            raise ValueError("Sender profile format must be 'markdown', 'json', or 'yaml'")
        if self.sender_profile_completeness_threshold < 0 or self.sender_profile_completeness_threshold > 1:
            raise ValueError("Sender profile completeness threshold must be between 0 and 1")
        if self.require_sender_profile and not self.enable_sender_profile:
            raise ValueError("Cannot require sender profile when sender profile is disabled")
        if self.require_sender_profile and not self.sender_profile_path and not self.enable_interactive_profile_setup:
            raise ValueError("When sender profile is required, either a profile path or interactive setup must be enabled")
        
        # Validate email addresses if provided
        if self.sender_email:
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, self.sender_email):
                raise ValueError(f"Invalid sender email format: {self.sender_email}")
        
        if self.reply_to_email:
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, self.reply_to_email):
                raise ValueError(f"Invalid reply-to email format: {self.reply_to_email}")
    
    def validate_api_keys(self) -> Dict[str, bool]:
        """Validate that required API keys are present and properly formatted."""
        validation_results = {}
        
        # Check required API keys
        validation_results['notion_token'] = bool(self.notion_token and len(self.notion_token) > 10)
        validation_results['hunter_api_key'] = bool(self.hunter_api_key and len(self.hunter_api_key) > 10)
        
        # Only validate OpenAI API key if not using Azure OpenAI
        if not self.use_azure_openai:
            validation_results['openai_api_key'] = bool(self.openai_api_key and len(self.openai_api_key) > 10)
        
        # Check Azure OpenAI keys if enabled
        if self.use_azure_openai:
            validation_results['azure_openai_api_key'] = bool(self.azure_openai_api_key and len(self.azure_openai_api_key) > 10)
            validation_results['azure_openai_endpoint'] = bool(self.azure_openai_endpoint and self.azure_openai_endpoint.startswith('https://'))
        
        # Check Resend API key if provided
        if self.resend_api_key:
            validation_results['resend_api_key'] = bool(self.resend_api_key and len(self.resend_api_key) > 10)
        
        return validation_results
    
    def get_missing_config(self) -> List[str]:
        """Get list of missing required configuration values."""
        missing = []
        
        if not self.notion_token:
            missing.append("NOTION_TOKEN")
        if not self.hunter_api_key:
            missing.append("HUNTER_API_KEY")
        if not self.use_azure_openai and not self.openai_api_key:
            missing.append("OPENAI_API_KEY")
        
        if self.use_azure_openai:
            if not self.azure_openai_api_key:
                missing.append("AZURE_OPENAI_API_KEY")
            if not self.azure_openai_endpoint:
                missing.append("AZURE_OPENAI_ENDPOINT")
        
        # Check email configuration if Resend is configured
        if self.resend_api_key and not self.sender_email:
            missing.append("SENDER_EMAIL")
            
        # Check sender profile configuration if required
        if self.require_sender_profile and not self.sender_profile_path:
            missing.append("SENDER_PROFILE_PATH")
        
        return missing
        
    def validate_sender_profile(self, sender_profile_manager=None) -> Dict[str, Any]:
        """
        Validate sender profile configuration and profile completeness.
        
        Args:
            sender_profile_manager: Optional SenderProfileManager instance
            
        Returns:
            Dictionary with validation results
        """
        
        results = {
            "is_valid": False,
            "profile_exists": False,
            "profile_loaded": False,
            "profile_complete": False,
            "completeness_score": 0.0,
            "meets_threshold": False,
            "issues": [],
            "profile": None
        }
        
        # Skip validation if sender profile is disabled
        if not self.enable_sender_profile:
            results["is_valid"] = True
            results["issues"].append("Sender profile is disabled")
            return results
        
        # Check if profile path is provided
        if not self.sender_profile_path:
            if self.require_sender_profile:
                results["issues"].append("Sender profile path is required but not provided")
            elif not self.enable_interactive_profile_setup:
                results["issues"].append("No sender profile path and interactive setup is disabled")
            else:
                results["is_valid"] = True
                results["issues"].append("No profile path provided, but interactive setup is enabled")
            return results
        
        # Check if profile file exists
        if not os.path.exists(self.sender_profile_path):
            results["issues"].append(f"Sender profile file not found: {self.sender_profile_path}")
            return results
        
        results["profile_exists"] = True
        
        # Load and validate profile
        try:
            if sender_profile_manager is None:
                sender_profile_manager = SenderProfileManager()
                
            # Load profile based on format
            if self.sender_profile_format == "markdown":
                profile = sender_profile_manager.load_profile_from_markdown(self.sender_profile_path)
            elif self.sender_profile_format == "json":
                profile = sender_profile_manager.load_profile_from_json(self.sender_profile_path)
            elif self.sender_profile_format == "yaml":
                profile = sender_profile_manager.load_profile_from_yaml(self.sender_profile_path)
            else:
                results["issues"].append(f"Unsupported profile format: {self.sender_profile_format}")
                return results
                
            results["profile_loaded"] = True
            results["profile"] = profile
            
            # Check profile completeness
            is_complete = profile.is_complete()
            completeness_score = profile.get_completeness_score()
            
            results["profile_complete"] = is_complete
            results["completeness_score"] = completeness_score
            results["meets_threshold"] = completeness_score >= self.sender_profile_completeness_threshold
            
            # Get validation results
            is_valid, validation_issues = sender_profile_manager.validate_profile(profile)
            
            if not is_valid:
                results["issues"].extend(validation_issues)
            
            if self.require_sender_profile and not results["meets_threshold"]:
                results["issues"].append(
                    f"Sender profile completeness score ({completeness_score:.1%}) is below the required threshold "
                    f"({self.sender_profile_completeness_threshold:.1%})"
                )
                
            # Set overall validity
            if self.require_sender_profile:
                results["is_valid"] = is_valid and results["meets_threshold"]
            else:
                results["is_valid"] = True  # Profile exists but is not required to meet standards
                
        except Exception as e:
            results["issues"].append(f"Failed to load or validate sender profile: {str(e)}")
            
        return results
