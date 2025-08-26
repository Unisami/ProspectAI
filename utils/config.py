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
    
    # Multi-Provider AI Configuration
    ai_provider: str = "openai"  # openai, azure-openai, anthropic, google, deepseek
    ai_model: Optional[str] = None
    ai_temperature: float = 0.7
    ai_max_tokens: int = 1000
    
    # OpenAI Configuration
    # openai_api_key already defined above
    
    # Azure OpenAI Configuration
    azure_openai_api_key: Optional[str] = None
    azure_openai_endpoint: Optional[str] = None
    azure_openai_deployment_name: str = "gpt-4"
    azure_openai_api_version: str = "2024-02-15-preview"
    use_azure_openai: bool = False  # Deprecated, use ai_provider instead
    
    # Anthropic Configuration
    anthropic_api_key: Optional[str] = None
    
    # Google Configuration
    google_api_key: Optional[str] = None
    
    # DeepSeek Configuration
    deepseek_api_key: Optional[str] = None
    
    @classmethod
    def _validate_provider_requirements(cls, ai_provider: str) -> None:
        """Validate that required credentials are available for the specified AI provider."""
        if ai_provider == "openai":
            if not os.getenv("OPENAI_API_KEY"):
                raise ValueError("OPENAI_API_KEY environment variable is required for OpenAI provider")
        elif ai_provider == "azure-openai":
            if not os.getenv("AZURE_OPENAI_API_KEY"):
                raise ValueError("AZURE_OPENAI_API_KEY environment variable is required for Azure OpenAI provider")
            if not os.getenv("AZURE_OPENAI_ENDPOINT"):
                raise ValueError("AZURE_OPENAI_ENDPOINT environment variable is required for Azure OpenAI provider")
        elif ai_provider == "anthropic":
            if not os.getenv("ANTHROPIC_API_KEY"):
                raise ValueError("ANTHROPIC_API_KEY environment variable is required for Anthropic provider")
        elif ai_provider == "google":
            if not os.getenv("GOOGLE_API_KEY"):
                raise ValueError("GOOGLE_API_KEY environment variable is required for Google provider")
        elif ai_provider == "deepseek":
            if not os.getenv("DEEPSEEK_API_KEY"):
                raise ValueError("DEEPSEEK_API_KEY environment variable is required for DeepSeek provider")
        else:
            raise ValueError(f"Unsupported AI provider: {ai_provider}. Supported providers: openai, azure-openai, anthropic, google, deepseek")
    
    @classmethod
    def get_supported_providers(cls) -> List[str]:
        """Get list of supported AI providers."""
        return ["openai", "azure-openai", "anthropic", "google", "deepseek"]
    
    def get_provider_config(self) -> Dict[str, Any]:
        """Get configuration for the current AI provider."""
        if self.ai_provider == "openai":
            return {
                "api_key": self.openai_api_key,
                "model": self.ai_model or "gpt-4",
                "temperature": self.ai_temperature,
                "max_tokens": self.ai_max_tokens
            }
        elif self.ai_provider == "azure-openai":
            return {
                "api_key": self.azure_openai_api_key,
                "endpoint": self.azure_openai_endpoint,
                "deployment_name": self.azure_openai_deployment_name,
                "api_version": self.azure_openai_api_version,
                "model": self.ai_model or self.azure_openai_deployment_name,
                "temperature": self.ai_temperature,
                "max_tokens": self.ai_max_tokens
            }
        elif self.ai_provider == "anthropic":
            return {
                "api_key": self.anthropic_api_key,
                "model": self.ai_model or "claude-3-sonnet-20240229",
                "temperature": self.ai_temperature,
                "max_tokens": self.ai_max_tokens
            }
        elif self.ai_provider == "google":
            return {
                "api_key": self.google_api_key,
                "model": self.ai_model or "gemini-2.5-flash",
                "temperature": self.ai_temperature,
                "max_tokens": self.ai_max_tokens
            }
        elif self.ai_provider == "deepseek":
            return {
                "api_key": self.deepseek_api_key,
                "model": self.ai_model or "deepseek-chat",
                "temperature": self.ai_temperature,
                "max_tokens": self.ai_max_tokens
            }
        else:
            raise ValueError(f"Unsupported AI provider: {self.ai_provider}")
    
    def _validate_model_for_provider(self, model: str, model_description: str) -> None:
        """Validate that a model is supported by the current AI provider."""
        if self.ai_provider == "openai":
            valid_models = ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo", "gpt-4o", "gpt-4o-mini"]
            if model not in valid_models:
                raise ValueError(f"{model_description} must be a valid OpenAI model: {', '.join(valid_models)}")
        elif self.ai_provider == "azure-openai":
            # Azure OpenAI uses deployment names, so we can't validate specific models
            # The deployment name should be validated by the Azure OpenAI provider
            pass
        elif self.ai_provider == "anthropic":
            valid_models = ["claude-3-haiku-20240307", "claude-3-sonnet-20240229", "claude-3-opus-20240229", "claude-3-5-sonnet-20241022"]
            if model not in valid_models:
                raise ValueError(f"{model_description} must be a valid Anthropic model: {', '.join(valid_models)}")
        elif self.ai_provider == "google":
            valid_models = ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-1.5-pro", "gemini-1.5-flash"]
            if model not in valid_models:
                raise ValueError(f"{model_description} must be a valid Google model: {', '.join(valid_models)}")
        elif self.ai_provider == "deepseek":
            valid_models = ["deepseek-chat", "deepseek-coder"]
            if model not in valid_models:
                raise ValueError(f"{model_description} must be a valid DeepSeek model: {', '.join(valid_models)}")
    
    def get_available_models(self) -> List[str]:
        """Get list of available models for the current AI provider."""
        if self.ai_provider == "openai":
            return ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo", "gpt-4o", "gpt-4o-mini"]
        elif self.ai_provider == "azure-openai":
            return ["Custom deployment names"]
        elif self.ai_provider == "anthropic":
            return ["claude-3-haiku-20240307", "claude-3-sonnet-20240229", "claude-3-opus-20240229", "claude-3-5-sonnet-20241022"]
        elif self.ai_provider == "google":
            return ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-1.5-pro", "gemini-1.5-flash"]
        elif self.ai_provider == "deepseek":
            return ["deepseek-chat", "deepseek-coder"]
        else:
            return []
    
    # Rate Limiting
    scraping_delay: float = 0.3
    hunter_requests_per_minute: int = 10  # Reduced from 25 to 10 for safer rate limiting
    
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
        
        if not notion_token:
            raise ValueError("NOTION_TOKEN environment variable is required")
        if not hunter_api_key:
            raise ValueError("HUNTER_API_KEY environment variable is required")
        
        # AI Provider Configuration
        ai_provider_env = os.getenv("AI_PROVIDER")
        use_azure_openai = os.getenv("USE_AZURE_OPENAI", "false").lower() in ("true", "1", "yes")
        
        if ai_provider_env:
            ai_provider = ai_provider_env.lower()
        elif use_azure_openai:
            # Backward compatibility: if USE_AZURE_OPENAI is set but AI_PROVIDER is not
            ai_provider = "azure-openai"
        else:
            ai_provider = "openai"
        
        # Validate provider-specific requirements
        cls._validate_provider_requirements(ai_provider)
        
        return cls(
            notion_token=notion_token,
            hunter_api_key=hunter_api_key,
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            # Multi-Provider AI Configuration
            ai_provider=ai_provider,
            ai_model=os.getenv("AI_MODEL"),
            ai_temperature=float(os.getenv("AI_TEMPERATURE", "0.7")),
            ai_max_tokens=int(os.getenv("AI_MAX_TOKENS", "1000")),
            # Provider-specific configurations
            azure_openai_api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            azure_openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            azure_openai_deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4"),
            azure_openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
            use_azure_openai=use_azure_openai,
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            deepseek_api_key=os.getenv("DEEPSEEK_API_KEY"),
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
        
        # Handle AI provider configuration
        ai_provider_value = config_dict.get("ai_provider") or config_dict.get("AI_PROVIDER")
        
        if ai_provider_value:
            ai_provider = ai_provider_value.lower()
        elif use_azure_openai:
            # Backward compatibility: if USE_AZURE_OPENAI is set but AI_PROVIDER is not
            ai_provider = "azure-openai"
        else:
            ai_provider = "openai"
        
        return cls(
            notion_token=config_dict.get("notion_token") or config_dict.get("NOTION_TOKEN", ""),
            hunter_api_key=config_dict.get("hunter_api_key") or config_dict.get("HUNTER_API_KEY", ""),
            openai_api_key=config_dict.get("openai_api_key") or config_dict.get("OPENAI_API_KEY", ""),
            # Multi-Provider AI Configuration
            ai_provider=ai_provider,
            ai_model=config_dict.get("ai_model") or config_dict.get("AI_MODEL"),
            ai_temperature=float(config_dict.get("ai_temperature", config_dict.get("AI_TEMPERATURE", 0.7))),
            ai_max_tokens=int(config_dict.get("ai_max_tokens", config_dict.get("AI_MAX_TOKENS", 1000))),
            # Provider-specific configurations
            azure_openai_api_key=config_dict.get("azure_openai_api_key") or config_dict.get("AZURE_OPENAI_API_KEY"),
            azure_openai_endpoint=config_dict.get("azure_openai_endpoint") or config_dict.get("AZURE_OPENAI_ENDPOINT"),
            azure_openai_deployment_name=config_dict.get("azure_openai_deployment_name", 
                                                        config_dict.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4")),
            azure_openai_api_version=config_dict.get("azure_openai_api_version", 
                                                    config_dict.get("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")),
            use_azure_openai=use_azure_openai,
            anthropic_api_key=config_dict.get("anthropic_api_key") or config_dict.get("ANTHROPIC_API_KEY"),
            google_api_key=config_dict.get("google_api_key") or config_dict.get("GOOGLE_API_KEY"),
            deepseek_api_key=config_dict.get("deepseek_api_key") or config_dict.get("DEEPSEEK_API_KEY"),
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
            # Multi-Provider AI Configuration
            "ai_provider": self.ai_provider,
            "ai_model": self.ai_model,
            "ai_temperature": self.ai_temperature,
            "ai_max_tokens": self.ai_max_tokens,
            # Provider-specific configurations
            "azure_openai_api_key": self.azure_openai_api_key,
            "azure_openai_endpoint": self.azure_openai_endpoint,
            "azure_openai_deployment_name": self.azure_openai_deployment_name,
            "azure_openai_api_version": self.azure_openai_api_version,
            "use_azure_openai": self.use_azure_openai,
            "anthropic_api_key": self.anthropic_api_key,
            "google_api_key": self.google_api_key,
            "deepseek_api_key": self.deepseek_api_key,
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
            if config_data["openai_api_key"]:
                config_data["openai_api_key"] = "***MASKED***"
            if config_data["azure_openai_api_key"]:
                config_data["azure_openai_api_key"] = "***MASKED***"
            if config_data["anthropic_api_key"]:
                config_data["anthropic_api_key"] = "***MASKED***"
            if config_data["google_api_key"]:
                config_data["google_api_key"] = "***MASKED***"
            if config_data["deepseek_api_key"]:
                config_data["deepseek_api_key"] = "***MASKED***"
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
        
        # Validate AI provider configuration
        if self.ai_provider not in self.get_supported_providers():
            raise ValueError(f"Unsupported AI provider: {self.ai_provider}. Supported providers: {', '.join(self.get_supported_providers())}")
        
        if self.ai_temperature < 0 or self.ai_temperature > 2:
            raise ValueError("AI temperature must be between 0 and 2")
        
        if self.ai_max_tokens <= 0:
            raise ValueError("AI max tokens must be positive")
        
        # Validate provider-specific configuration
        if self.ai_provider == "openai":
            if not self.openai_api_key:
                raise ValueError("OpenAI API key is required for OpenAI provider")
        elif self.ai_provider == "azure-openai":
            if not self.azure_openai_api_key:
                raise ValueError("Azure OpenAI API key is required for Azure OpenAI provider")
            if not self.azure_openai_endpoint:
                raise ValueError("Azure OpenAI endpoint is required for Azure OpenAI provider")
            if not self.azure_openai_deployment_name:
                raise ValueError("Azure OpenAI deployment name is required for Azure OpenAI provider")
        elif self.ai_provider == "anthropic":
            if not self.anthropic_api_key:
                raise ValueError("Anthropic API key is required for Anthropic provider")
        elif self.ai_provider == "google":
            if not self.google_api_key:
                raise ValueError("Google API key is required for Google provider")
        elif self.ai_provider == "deepseek":
            if not self.deepseek_api_key:
                raise ValueError("DeepSeek API key is required for DeepSeek provider")
        
        # Validate Azure OpenAI configuration if enabled (backward compatibility)
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
        self._validate_model_for_provider(self.ai_parsing_model, "AI parsing model")
        
        # Validate product analysis configuration
        if self.product_analysis_max_retries < 0:
            raise ValueError("Product analysis max retries must be non-negative")
        self._validate_model_for_provider(self.product_analysis_model, "Product analysis model")
        
        # Validate email generation configuration
        if self.max_email_length <= 0:
            raise ValueError("Max email length must be positive")
        self._validate_model_for_provider(self.email_generation_model, "Email generation model")
            
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
        
        # Validate AI provider-specific keys
        if self.ai_provider == "openai":
            validation_results['openai_api_key'] = bool(self.openai_api_key and len(self.openai_api_key) > 10)
        elif self.ai_provider == "azure-openai":
            validation_results['azure_openai_api_key'] = bool(self.azure_openai_api_key and len(self.azure_openai_api_key) > 10)
            validation_results['azure_openai_endpoint'] = bool(self.azure_openai_endpoint and self.azure_openai_endpoint.startswith('https://'))
        elif self.ai_provider == "anthropic":
            validation_results['anthropic_api_key'] = bool(self.anthropic_api_key and len(self.anthropic_api_key) > 10)
        elif self.ai_provider == "google":
            validation_results['google_api_key'] = bool(self.google_api_key and len(self.google_api_key) > 10)
        elif self.ai_provider == "deepseek":
            validation_results['deepseek_api_key'] = bool(self.deepseek_api_key and len(self.deepseek_api_key) > 10)
        
        # Backward compatibility: Check Azure OpenAI keys if enabled
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
        
        # Check AI provider-specific requirements
        if self.ai_provider == "openai":
            if not self.openai_api_key:
                missing.append("OPENAI_API_KEY")
        elif self.ai_provider == "azure-openai":
            if not self.azure_openai_api_key:
                missing.append("AZURE_OPENAI_API_KEY")
            if not self.azure_openai_endpoint:
                missing.append("AZURE_OPENAI_ENDPOINT")
        elif self.ai_provider == "anthropic":
            if not self.anthropic_api_key:
                missing.append("ANTHROPIC_API_KEY")
        elif self.ai_provider == "google":
            if not self.google_api_key:
                missing.append("GOOGLE_API_KEY")
        elif self.ai_provider == "deepseek":
            if not self.deepseek_api_key:
                missing.append("DEEPSEEK_API_KEY")
        
        # Backward compatibility: Check Azure OpenAI if enabled
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
