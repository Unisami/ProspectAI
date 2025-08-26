"""
API validation system with comprehensive error handling and retry mechanisms.
Provides specific validation for Notion, Hunter, OpenAI, and Resend API keys.
"""

import re
import time
import requests
import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import logging


class APIValidationResult(Enum):
    """API validation result types"""
    VALID = "valid"
    INVALID_FORMAT = "invalid_format"
    INVALID_CREDENTIALS = "invalid_credentials"
    NETWORK_ERROR = "network_error"
    QUOTA_EXCEEDED = "quota_exceeded"
    PERMISSION_ERROR = "permission_error"
    SERVICE_UNAVAILABLE = "service_unavailable"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class ValidationResult:
    """Result of API key validation"""
    api_name: str
    key_name: str
    result: APIValidationResult
    message: str
    details: Optional[str] = None
    retry_suggested: bool = False
    help_url: Optional[str] = None


class APIValidator:
    """Comprehensive API validation with error handling and recovery guidance"""
    
    def __init__(self, timeout: int = 10, max_retries: int = 3):
        self.timeout = timeout
        self.max_retries = max_retries
        self.logger = logging.getLogger("api_validator")
        
       # API-specific validation patterns and URLs
        self.api_configs = {
            "NOTION_TOKEN": {
                "name": "Notion",
                "pattern": r"^(secret_[a-zA-Z0-9]{43,70}|ntn_[a-zA-Z0-9]{40,60})$", # Accepts secret_ and ntn_ formats
                "example": "secret_... or ntn_...",
                "obtain_url": "https://developers.notion.com/docs/create-a-notion-integration",
                "test_endpoint": "https://api.notion.com/v1/users/me",
                "headers": {"Notion-Version": "2022-06-28"},
                "help_text": "Create an integration at https://www.notion.so/my-integrations"
            },
            "HUNTER_API_KEY": {
                "name": "Hunter.io",
                "pattern": r"^[a-f0-9]{40}$",
                "example": "abc123def456...",
                "obtain_url": "https://hunter.io/api",
                "test_endpoint": "https://api.hunter.io/v2/account",
                "headers": {},
                "help_text": "Get your API key from https://hunter.io/api"
            },
            "OPENAI_API_KEY": {
                "name": "OpenAI",
                "pattern": r"^(sk-proj-[a-zA-Z0-9]{20}T3BlbkFJ[a-zA-Z0-9]{20}|sk-[a-zA-Z0-9]{48,64})$",
                "example": "sk-proj-... or sk-ABC123...",
                "obtain_url": "https://platform.openai.com/api-keys",
                "test_endpoint": "https://api.openai.com/v1/models",
                "headers": {},
                "help_text": "Create an API key at https://platform.openai.com/api-keys"
            },
            "RESEND_API_KEY": {
                "name": "Resend",
                "pattern": r"^re_[a-zA-Z0-9_]{25,35}$",
                "example": "re_ABC123...",
                "obtain_url": "https://resend.com/api-keys",
                "test_endpoint": "https://api.resend.com/domains",
                "headers": {},
                "help_text": "Get your API key from https://resend.com/api-keys"
            },
            "ANTHROPIC_API_KEY": {
                "name": "Anthropic",
                "pattern": r"^sk-ant-api03-[a-zA-Z0-9-]{95,}$", # Updated pattern to be more specific
                "example": "sk-ant-api03-...",
                "obtain_url": "https://console.anthropic.com/settings/keys",
                "test_endpoint": "https://api.anthropic.com/v1/messages", # A more reliable test endpoint
                "headers": {"anthropic-version": "2023-06-01"}, # Added required version header
                "help_text": "Create an API key at https://console.anthropic.com/settings/keys"
            },
            "GOOGLE_API_KEY": {
                "name": "Google",
                "pattern": r"^AIza[0-9A-Za-z\\-_]{35}$", # More specific pattern for Google keys
                "example": "AIza...(39 characters)",
                "obtain_url": "https://aistudio.google.com/app/apikey",
                "test_endpoint": "https://generativelanguage.googleapis.com/v1beta/models", # Using v1beta
                "headers": {},
                "help_text": "Get your API key from https://aistudio.google.com/app/apikey"
            },
            "DEEPSEEK_API_KEY": {
                "name": "DeepSeek",
                "pattern": r"^sk-[a-zA-Z0-9]{48,}$",
                "example": "sk-...",
                "obtain_url": "https://platform.deepseek.com/api_keys",
                "test_endpoint": "https://api.deepseek.com/v1/models",
                "headers": {},
                "help_text": "Create an API key at https://platform.deepseek.com/api_keys"
            }
        }

    
    def validate_format(self, key_name: str, api_key: str) -> ValidationResult:
        """Validate API key format"""
        if key_name not in self.api_configs:
            return ValidationResult(
                api_name="Unknown",
                key_name=key_name,
                result=APIValidationResult.UNKNOWN_ERROR,
                message=f"Unknown API key type: {key_name}"
            )
        
        config = self.api_configs[key_name]
        
        if not api_key.strip():
            return ValidationResult(
                api_name=config["name"],
                key_name=key_name,
                result=APIValidationResult.INVALID_FORMAT,
                message="API key is empty",
                help_url=config["obtain_url"]
            )
        
        if not re.match(config["pattern"], api_key.strip()):
            return ValidationResult(
                api_name=config["name"],
                key_name=key_name,
                result=APIValidationResult.INVALID_FORMAT,
                message=f"Invalid format. Expected format: {config['example']}",
                details=f"Pattern: {config['pattern']}",
                help_url=config["obtain_url"]
            )
        
        return ValidationResult(
            api_name=config["name"],
            key_name=key_name,
            result=APIValidationResult.VALID,
            message="Format validation passed"
        )
    
    def validate_api_connection(self, key_name: str, api_key: str) -> ValidationResult:
        """Validate API key by testing actual connection"""
        format_result = self.validate_format(key_name, api_key)
        if format_result.result != APIValidationResult.VALID:
            return format_result
        
        config = self.api_configs[key_name]
        
        for attempt in range(self.max_retries):
            try:
                if key_name == "NOTION_TOKEN":
                    result = self._validate_notion(api_key, config)
                elif key_name == "HUNTER_API_KEY":
                    result = self._validate_hunter(api_key, config)
                elif key_name == "OPENAI_API_KEY":
                    result = self._validate_openai(api_key, config)
                elif key_name == "RESEND_API_KEY":
                    result = self._validate_resend(api_key, config)
                else:
                    return ValidationResult(
                        api_name=config["name"],
                        key_name=key_name,
                        result=APIValidationResult.UNKNOWN_ERROR,
                        message="Validation not implemented for this API"
                    )
                
                if result.result == APIValidationResult.VALID or not result.retry_suggested:
                    return result
                
                # Retry with exponential backoff
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                    self.logger.info(f"Retrying {key_name} validation, attempt {attempt + 2}")
                
            except Exception as e:
                self.logger.error(f"Error validating {key_name}: {str(e)}")
                if attempt == self.max_retries - 1:
                    return ValidationResult(
                        api_name=config["name"],
                        key_name=key_name,
                        result=APIValidationResult.UNKNOWN_ERROR,
                        message=f"Validation failed: {str(e)}",
                        retry_suggested=True
                    )
        
        return ValidationResult(
            api_name=config["name"],
            key_name=key_name,
            result=APIValidationResult.UNKNOWN_ERROR,
            message="Maximum retry attempts exceeded",
            retry_suggested=False
        )
    
    def _validate_notion(self, api_key: str, config: Dict[str, Any]) -> ValidationResult:
        """Validate Notion API key"""
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            **config["headers"]
        }
        
        try:
            response = requests.get(
                config["test_endpoint"],
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                user_type = data.get("type", "unknown")
                return ValidationResult(
                    api_name=config["name"],
                    key_name="NOTION_TOKEN",
                    result=APIValidationResult.VALID,
                    message=f"Valid Notion token (user type: {user_type})",
                    details="Successfully connected to Notion API"
                )
            elif response.status_code == 401:
                return ValidationResult(
                    api_name=config["name"],
                    key_name="NOTION_TOKEN",
                    result=APIValidationResult.INVALID_CREDENTIALS,
                    message="Invalid Notion token or insufficient permissions",
                    details="Check that the integration token is correct and has proper permissions",
                    help_url=config["obtain_url"]
                )
            elif response.status_code == 429:
                return ValidationResult(
                    api_name=config["name"],
                    key_name="NOTION_TOKEN",
                    result=APIValidationResult.QUOTA_EXCEEDED,
                    message="Notion API rate limit exceeded",
                    retry_suggested=True
                )
            else:
                return ValidationResult(
                    api_name=config["name"],
                    key_name="NOTION_TOKEN",
                    result=APIValidationResult.SERVICE_UNAVAILABLE,
                    message=f"Notion API error: HTTP {response.status_code}",
                    details=response.text,
                    retry_suggested=True
                )
        
        except requests.exceptions.Timeout:
            return ValidationResult(
                api_name=config["name"],
                key_name="NOTION_TOKEN",
                result=APIValidationResult.NETWORK_ERROR,
                message="Notion API request timed out",
                retry_suggested=True
            )
        except requests.exceptions.ConnectionError:
            return ValidationResult(
                api_name=config["name"],
                key_name="NOTION_TOKEN",
                result=APIValidationResult.NETWORK_ERROR,
                message="Could not connect to Notion API",
                details="Check your internet connection",
                retry_suggested=True
            )
    
    def _validate_hunter(self, api_key: str, config: Dict[str, Any]) -> ValidationResult:
        """Validate Hunter.io API key"""
        url = f"{config['test_endpoint']}?api_key={api_key}"
        
        try:
            response = requests.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                plan_name = data.get("data", {}).get("plan_name", "Unknown")
                calls_used = data.get("data", {}).get("calls", {}).get("used", 0)
                calls_available = data.get("data", {}).get("calls", {}).get("available", 0)
                
                return ValidationResult(
                    api_name=config["name"],
                    key_name="HUNTER_API_KEY",
                    result=APIValidationResult.VALID,
                    message=f"Valid Hunter.io key (plan: {plan_name})",
                    details=f"API calls: {calls_used}/{calls_available}"
                )
            elif response.status_code == 401:
                return ValidationResult(
                    api_name=config["name"],
                    key_name="HUNTER_API_KEY",
                    result=APIValidationResult.INVALID_CREDENTIALS,
                    message="Invalid Hunter.io API key",
                    help_url=config["obtain_url"]
                )
            elif response.status_code == 429:
                return ValidationResult(
                    api_name=config["name"],
                    key_name="HUNTER_API_KEY",
                    result=APIValidationResult.QUOTA_EXCEEDED,
                    message="Hunter.io API quota exceeded",
                    details="Consider upgrading your plan or wait for quota reset"
                )
            else:
                return ValidationResult(
                    api_name=config["name"],
                    key_name="HUNTER_API_KEY",
                    result=APIValidationResult.SERVICE_UNAVAILABLE,
                    message=f"Hunter.io API error: HTTP {response.status_code}",
                    retry_suggested=True
                )
        
        except requests.exceptions.Timeout:
            return ValidationResult(
                api_name=config["name"],
                key_name="HUNTER_API_KEY",
                result=APIValidationResult.NETWORK_ERROR,
                message="Hunter.io API request timed out",
                retry_suggested=True
            )
        except requests.exceptions.ConnectionError:
            return ValidationResult(
                api_name=config["name"],
                key_name="HUNTER_API_KEY",
                result=APIValidationResult.NETWORK_ERROR,
                message="Could not connect to Hunter.io API",
                retry_suggested=True
            )
    
    def _validate_openai(self, api_key: str, config: Dict[str, Any]) -> ValidationResult:
        """Validate OpenAI API key"""
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.get(
                config["test_endpoint"],
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                model_count = len(data.get("data", []))
                return ValidationResult(
                    api_name=config["name"],
                    key_name="OPENAI_API_KEY",
                    result=APIValidationResult.VALID,
                    message=f"Valid OpenAI API key ({model_count} models available)",
                    details="Successfully connected to OpenAI API"
                )
            elif response.status_code == 401:
                return ValidationResult(
                    api_name=config["name"],
                    key_name="OPENAI_API_KEY",
                    result=APIValidationResult.INVALID_CREDENTIALS,
                    message="Invalid OpenAI API key",
                    help_url=config["obtain_url"]
                )
            elif response.status_code == 429:
                return ValidationResult(
                    api_name=config["name"],
                    key_name="OPENAI_API_KEY",
                    result=APIValidationResult.QUOTA_EXCEEDED,
                    message="OpenAI API quota exceeded",
                    details="Check your usage limits and billing"
                )
            else:
                return ValidationResult(
                    api_name=config["name"],
                    key_name="OPENAI_API_KEY",
                    result=APIValidationResult.SERVICE_UNAVAILABLE,
                    message=f"OpenAI API error: HTTP {response.status_code}",
                    retry_suggested=True
                )
        
        except requests.exceptions.Timeout:
            return ValidationResult(
                api_name=config["name"],
                key_name="OPENAI_API_KEY",
                result=APIValidationResult.NETWORK_ERROR,
                message="OpenAI API request timed out",
                retry_suggested=True
            )
        except requests.exceptions.ConnectionError:
            return ValidationResult(
                api_name=config["name"],
                key_name="OPENAI_API_KEY",
                result=APIValidationResult.NETWORK_ERROR,
                message="Could not connect to OpenAI API",
                retry_suggested=True
            )
    
    def _validate_resend(self, api_key: str, config: Dict[str, Any]) -> ValidationResult:
        """Validate Resend API key"""
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.get(
                config["test_endpoint"],
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                domain_count = len(data.get("data", []))
                return ValidationResult(
                    api_name=config["name"],
                    key_name="RESEND_API_KEY",
                    result=APIValidationResult.VALID,
                    message=f"Valid Resend API key ({domain_count} domains configured)",
                    details="Successfully connected to Resend API"
                )
            elif response.status_code == 401:
                return ValidationResult(
                    api_name=config["name"],
                    key_name="RESEND_API_KEY",
                    result=APIValidationResult.INVALID_CREDENTIALS,
                    message="Invalid Resend API key",
                    help_url=config["obtain_url"]
                )
            elif response.status_code == 429:
                return ValidationResult(
                    api_name=config["name"],
                    key_name="RESEND_API_KEY",
                    result=APIValidationResult.QUOTA_EXCEEDED,
                    message="Resend API rate limit exceeded",
                    retry_suggested=True
                )
            else:
                return ValidationResult(
                    api_name=config["name"],
                    key_name="RESEND_API_KEY",
                    result=APIValidationResult.SERVICE_UNAVAILABLE,
                    message=f"Resend API error: HTTP {response.status_code}",
                    retry_suggested=True
                )
        
        except requests.exceptions.Timeout:
            return ValidationResult(
                api_name=config["name"],
                key_name="RESEND_API_KEY",
                result=APIValidationResult.NETWORK_ERROR,
                message="Resend API request timed out",
                retry_suggested=True
            )
        except requests.exceptions.ConnectionError:
            return ValidationResult(
                api_name=config["name"],
                key_name="RESEND_API_KEY",
                result=APIValidationResult.NETWORK_ERROR,
                message="Could not connect to Resend API",
                retry_suggested=True
            )
    
    def validate_email_format(self, email: str) -> ValidationResult:
        """Validate email address format"""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not email.strip():
            return ValidationResult(
                api_name="Email",
                key_name="SENDER_EMAIL",
                result=APIValidationResult.INVALID_FORMAT,
                message="Email address is empty"
            )
        
        if not re.match(email_pattern, email.strip()):
            return ValidationResult(
                api_name="Email",
                key_name="SENDER_EMAIL",
                result=APIValidationResult.INVALID_FORMAT,
                message="Invalid email address format",
                details="Expected format: user@domain.com"
            )
        
        return ValidationResult(
            api_name="Email",
            key_name="SENDER_EMAIL",
            result=APIValidationResult.VALID,
            message="Valid email format"
        )
    
    def validate_all_apis(self, config: Dict[str, str]) -> Dict[str, ValidationResult]:
        """Validate all provided API keys"""
        results = {}
        
        for key_name, api_key in config.items():
            if key_name in self.api_configs:
                self.logger.info(f"Validating {key_name}...")
                results[key_name] = self.validate_api_connection(key_name, api_key)
            elif key_name == "SENDER_EMAIL":
                results[key_name] = self.validate_email_format(api_key)
            elif key_name == "SENDER_NAME":
                # Just check if name is not empty
                if api_key.strip():
                    results[key_name] = ValidationResult(
                        api_name="Name",
                        key_name="SENDER_NAME",
                        result=APIValidationResult.VALID,
                        message="Valid sender name"
                    )
                else:
                    results[key_name] = ValidationResult(
                        api_name="Name",
                        key_name="SENDER_NAME",
                        result=APIValidationResult.INVALID_FORMAT,
                        message="Sender name is empty"
                    )
        
        return results
    
    def get_validation_summary(self, results: Dict[str, ValidationResult]) -> Tuple[bool, str]:
        """Get overall validation summary"""
        valid_count = sum(1 for r in results.values() if r.result == APIValidationResult.VALID)
        total_count = len(results)
        
        if valid_count == total_count:
            return True, f"✅ All {total_count} API keys validated successfully"
        else:
            failed_count = total_count - valid_count
            return False, f"❌ {failed_count}/{total_count} API keys failed validation"
    
    def print_validation_results(self, results: Dict[str, ValidationResult]):
        """Print detailed validation results"""
        print("\n" + "=" * 60)
        print("API Validation Results")
        print("=" * 60)
        
        for key_name, result in results.items():
            status_icon = "✅" if result.result == APIValidationResult.VALID else "❌"
            print(f"\n{status_icon} {result.api_name} ({key_name})")
            print(f"   Status: {result.message}")
            
            if result.details:
                print(f"   Details: {result.details}")
            
            if result.result != APIValidationResult.VALID:
                self._print_recovery_instructions(result)
        
        # Overall summary
        success, summary = self.get_validation_summary(results)
        print(f"\n{summary}")
        print("=" * 60)
    
    def _print_recovery_instructions(self, result: ValidationResult):
        """Print specific recovery instructions for failed validation"""
        print(f"   💡 Recovery steps:")
        
        if result.result == APIValidationResult.INVALID_FORMAT:
            print(f"      • Check the API key format")
            print(f"      • Ensure you copied the complete key")
            if result.help_url:
                print(f"      • Get a new key from: {result.help_url}")
        
        elif result.result == APIValidationResult.INVALID_CREDENTIALS:
            print(f"      • Verify the API key is correct")
            print(f"      • Check if the key has expired")
            print(f"      • Ensure the key has proper permissions")
            if result.help_url:
                print(f"      • Generate a new key at: {result.help_url}")
        
        elif result.result == APIValidationResult.NETWORK_ERROR:
            print(f"      • Check your internet connection")
            print(f"      • Try again in a few minutes")
            print(f"      • Check if you're behind a firewall")
        
        elif result.result == APIValidationResult.QUOTA_EXCEEDED:
            print(f"      • Check your API usage limits")
            print(f"      • Wait for quota reset or upgrade plan")
            print(f"      • Review your billing settings")
        
        elif result.result == APIValidationResult.SERVICE_UNAVAILABLE:
            print(f"      • Try again later")
            print(f"      • Check service status pages")
            if result.retry_suggested:
                print(f"      • Retry validation with: python cli.py validate-config")


# Global validator instance
_api_validator = None

def get_api_validator() -> APIValidator:
    """Get or create global API validator instance"""
    global _api_validator
    if _api_validator is None:
        _api_validator = APIValidator()
    return _api_validator