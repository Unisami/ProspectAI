#!/usr/bin/env python3
"""
Interactive setup system for ProspectAI job automation tool.
Handles virtual environment creation, dependency installation, and API configuration.
"""

import os
import sys
import subprocess
import platform
import re
import stat
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class ErrorCategory(Enum):
    SYSTEM_ERROR = "system"
    NETWORK_ERROR = "network"
    CONFIGURATION_ERROR = "configuration"
    PERMISSION_ERROR = "permission"
    VALIDATION_ERROR = "validation"


@dataclass
class APIKeyPrompt:
    key_name: str
    description: str
    obtain_url: str
    required: bool = True
    validation_pattern: Optional[str] = None
    example_format: Optional[str] = None


@dataclass
class InstallationState:
    python_installed: bool = False
    venv_created: bool = False
    dependencies_installed: bool = False
    config_created: bool = False
    config_validated: bool = False
    dashboard_setup: bool = False
    runners_created: bool = False
    
    def get_progress_percentage(self) -> float:
        """Calculate installation progress"""
        completed = sum([
            self.python_installed, self.venv_created, self.dependencies_installed,
            self.config_created, self.config_validated, self.dashboard_setup, self.runners_created
        ])
        return (completed / 7) * 100
    
    def get_current_step(self) -> str:
        """Get human-readable current step"""
        if not self.python_installed:
            return "Python installation"
        elif not self.venv_created:
            return "Virtual environment creation"
        elif not self.dependencies_installed:
            return "Dependency installation"
        elif not self.config_created:
            return "API configuration"
        elif not self.config_validated:
            return "Configuration validation"
        elif not self.dashboard_setup:
            return "Dashboard setup"
        elif not self.runners_created:
            return "Runner script creation"
        else:
            return "Installation complete"


class InteractiveSetup:
    """Core setup orchestration with comprehensive error handling"""
    
    def __init__(self):
        self.project_root = Path.cwd()
        self.venv_path = self.project_root / "venv"
        self.env_file = self.project_root / ".env"
        self.installation_state = InstallationState()
        
        # API configuration prompts
        self.api_prompts = [
            APIKeyPrompt(
                key_name="NOTION_TOKEN",
                description="Notion Integration Token for data storage",
                obtain_url="https://developers.notion.com/docs/create-a-notion-integration",
                required=True,
                validation_pattern=r"^(secret_[a-zA-Z0-9]{43,70}|ntn_[a-zA-Z0-9]{40,60})$",
                example_format="secret_... or ntn_..."
            ),
            APIKeyPrompt(
                key_name="HUNTER_API_KEY",
                description="Hunter.io API Key for email discovery",
                obtain_url="https://hunter.io/api",
                required=True,
                example_format="abc123def456..."
            ),
            APIKeyPrompt(
                key_name="OPENAI_API_KEY",
                description="OpenAI API Key for AI-powered email generation",
                obtain_url="https://platform.openai.com/api-keys",
                required=False,  # Will be conditional based on AI provider
                validation_pattern=r"sk-proj-[a-zA-Z0-9]{20}T3BlbkFJ[a-zA-Z0-9]{20}|sk-[a-zA-Z0-9]{48,64}",
                example_format="sk-proj-... or sk-..."
            ),
            APIKeyPrompt(
                key_name="ANTHROPIC_API_KEY",
                description="Anthropic API Key for Claude AI models",
                obtain_url="https://console.anthropic.com/settings/keys",
                required=False,  # Will be conditional based on AI provider
                validation_pattern=r"sk-ant-[a-zA-Z0-9-]{95,}",
                example_format="sk-ant-api03-..."
            ),
            APIKeyPrompt(
                key_name="GOOGLE_API_KEY",
                description="Google API Key for Gemini AI models",
                obtain_url="https://aistudio.google.com/app/apikey",
                required=False,  # Will be conditional based on AI provider
                validation_pattern=r"[a-zA-Z0-9-_]{39}",
                example_format="AIza...(39 characters)"
            ),
            APIKeyPrompt(
                key_name="DEEPSEEK_API_KEY",
                description="DeepSeek API Key for DeepSeek AI models",
                obtain_url="https://platform.deepseek.com/api_keys",
                required=False,  # Will be conditional based on AI provider
                validation_pattern=r"sk-[a-zA-Z0-9]{48,}",
                example_format="sk-..."
            ),
            APIKeyPrompt(
                key_name="RESEND_API_KEY",
                description="Resend API Key for email sending (optional)",
                obtain_url="https://resend.com/api-keys",
                required=False,
                validation_pattern=r"re_[a-zA-Z0-9_]{25,35}",
                example_format="re_ABC123..."
            ),
            APIKeyPrompt(
                key_name="SENDER_EMAIL",
                description="Your email address for sending emails (optional)",
                obtain_url="Your email provider",
                required=False,
                validation_pattern=r"[^@]+@[^@]+\.[^@]+",
                example_format="your.email@domain.com"
            ),
            APIKeyPrompt(
                key_name="SENDER_NAME",
                description="Your name for email signatures (optional)",
                obtain_url="Your preference",
                required=False,
                example_format="Your Full Name"
            ),
            APIKeyPrompt(
                key_name="AZURE_OPENAI_API_KEY",
                description="Azure OpenAI API Key",
                obtain_url="https://portal.azure.com",
                required=False,  # Will be conditional based on AI provider
                validation_pattern=r"[a-zA-Z0-9]{32}",
                example_format="32-character key"
            ),
            APIKeyPrompt(
                key_name="AZURE_OPENAI_ENDPOINT",
                description="Azure OpenAI Endpoint URL",
                obtain_url="https://portal.azure.com",
                required=False,  # Will be conditional based on AI provider
                validation_pattern=r"https://[a-zA-Z0-9-]+\.openai\.azure\.com/?$",
                example_format="https://your-resource.openai.azure.com/"
            ),
            APIKeyPrompt(
                key_name="AZURE_OPENAI_DEPLOYMENT_NAME",
                description="Azure OpenAI Deployment Name",
                obtain_url="Your Azure OpenAI resource",
                required=False,  # Will be conditional based on AI provider
                example_format="gpt-4"
            )
        ]
    
    def print_header(self):
        """Print setup header"""
        print("=" * 70)
        print("🚀 ProspectAI Interactive Setup")
        print("=" * 70)
        print("Setting up your job automation environment...")
        print()
    
    def print_step(self, step: str, description: str = ""):
        """Print current step with progress"""
        progress = self.installation_state.get_progress_percentage()
        print(f"[{progress:5.1f}%] {step}")
        if description:
            print(f"         {description}")
        print()
    
    def create_virtual_environment(self) -> bool:
        """Create isolated Python environment with validation"""
        self.print_step("Creating virtual environment...", "This ensures clean dependency management")
        
        try:
            # Check if venv already exists
            if self.venv_path.exists():
                response = input(f"Virtual environment already exists at {self.venv_path}. Recreate it? (y/N): ").strip().lower()
                if response in ['y', 'yes']:
                    import shutil
                    shutil.rmtree(self.venv_path)
                else:
                    print("Using existing virtual environment.")
                    self.installation_state.venv_created = True
                    return True
            
            # Create virtual environment
            result = subprocess.run([
                sys.executable, '-m', 'venv', str(self.venv_path)
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"❌ Error creating virtual environment:")
                print(f"   {result.stderr}")
                return False
            
            # Verify virtual environment creation
            python_exe = self.get_venv_python()
            if not python_exe.exists():
                print(f"❌ Virtual environment created but Python executable not found at {python_exe}")
                return False
            
            print("✅ Virtual environment created successfully")
            self.installation_state.venv_created = True
            return True
            
        except Exception as e:
            print(f"❌ Error creating virtual environment: {str(e)}")
            return False
    
    def get_venv_python(self) -> Path:
        """Get path to virtual environment Python executable"""
        if platform.system() == "Windows":
            return self.venv_path / "Scripts" / "python.exe"
        else:
            return self.venv_path / "bin" / "python"
    
    def install_dependencies(self) -> bool:
        """Install requirements.txt with progress tracking"""
        self.print_step("Installing dependencies...", "This may take a few minutes")
        
        try:
            python_exe = self.get_venv_python()
            if not python_exe.exists():
                print(f"❌ Python executable not found at {python_exe}")
                return False
            
            # Upgrade pip first
            print("   Upgrading pip...")
            pip_upgrade = subprocess.run([
                str(python_exe), '-m', 'pip', 'install', '--upgrade', 'pip'
            ], capture_output=True, text=True)
            
            if pip_upgrade.returncode != 0:
                print(f"⚠️  Warning: Could not upgrade pip: {pip_upgrade.stderr}")
            
            # Install requirements
            requirements_file = self.project_root / "requirements.txt"
            if not requirements_file.exists():
                print(f"❌ Requirements file not found at {requirements_file}")
                return False
            
            print("   Installing packages from requirements.txt...")
            result = subprocess.run([
                str(python_exe), '-m', 'pip', 'install', '-r', str(requirements_file)
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"❌ Error installing dependencies:")
                print(f"   {result.stderr}")
                print("\n💡 Troubleshooting tips:")
                print("   • Try running: pip install --upgrade pip")
                print("   • Check your internet connection")
                print("   • Try installing packages individually")
                return False
            
            print("✅ Dependencies installed successfully")
            self.installation_state.dependencies_installed = True
            return True
            
        except Exception as e:
            print(f"❌ Error installing dependencies: {str(e)}")
            return False
    
    def validate_api_key(self, key_name: str, value: str) -> bool:
        """Validate API key format"""
        if not value.strip():
            return False
        
        # Find the prompt configuration
        prompt_config = next((p for p in self.api_prompts if p.key_name == key_name), None)
        if not prompt_config or not prompt_config.validation_pattern:
            return True  # No validation pattern specified
        
        return bool(re.match(prompt_config.validation_pattern, value.strip()))
    
    def select_ai_provider(self) -> str:
        """Interactive AI provider selection"""
        print("🤖 AI Provider Selection")
        print("Choose which AI provider you want to use for email generation:")
        print()
        
        providers = [
            ("openai", "OpenAI (ChatGPT)", "Most popular, proven performance, GPT-4 models"),
            ("anthropic", "Anthropic Claude", "Constitutional AI, safety focus, excellent reasoning"),
            ("google", "Google Gemini", "Multimodal capabilities, competitive pricing"),
            ("deepseek", "DeepSeek", "Code-specialized models, very cost-effective"),
            ("azure-openai", "Azure OpenAI", "Enterprise security, custom deployments")
        ]
        
        for i, (provider_id, name, description) in enumerate(providers, 1):
            print(f"[{i}] {name}")
            print(f"    {description}")
            print()
        
        while True:
            try:
                choice = input("Select AI provider (1-5): ").strip()
                if not choice:
                    continue
                    
                choice_num = int(choice)
                if 1 <= choice_num <= len(providers):
                    selected_provider = providers[choice_num - 1][0]
                    selected_name = providers[choice_num - 1][1]
                    print(f"✅ Selected: {selected_name}")
                    print()
                    return selected_provider
                else:
                    print(f"❌ Please enter a number between 1 and {len(providers)}")
                    print()
            except ValueError:
                print("❌ Please enter a valid number")
                print()
    
    def get_required_api_keys(self, ai_provider: str) -> List[str]:
        """Get list of required API keys based on selected AI provider"""
        # Core APIs always required
        required_keys = ["NOTION_TOKEN", "HUNTER_API_KEY"]
        
        # Add AI provider-specific keys
        if ai_provider == "openai":
            required_keys.append("OPENAI_API_KEY")
        elif ai_provider == "anthropic":
            required_keys.append("ANTHROPIC_API_KEY")
        elif ai_provider == "google":
            required_keys.append("GOOGLE_API_KEY")
        elif ai_provider == "deepseek":
            required_keys.append("DEEPSEEK_API_KEY")
        elif ai_provider == "azure-openai":
            required_keys.extend(["AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOYMENT_NAME"])
        
        return required_keys
    
    def get_optional_api_keys(self) -> List[str]:
        """Get list of optional API keys"""
        return ["RESEND_API_KEY", "SENDER_EMAIL", "SENDER_NAME"]
    
    def collect_api_configuration(self) -> Dict[str, str]:
        """Interactive API key collection with guidance"""
        self.print_step("Collecting API configuration...", "Setting up your API keys and credentials")
        
        config = {}
        
        # Check if .env already exists
        if self.env_file.exists():
            response = input(f"Configuration file {self.env_file} already exists. Overwrite it? (y/N): ").strip().lower()
            if response not in ['y', 'yes']:
                print("Keeping existing configuration.")
                return {}
        
        # Step 1: Select AI Provider
        ai_provider = self.select_ai_provider()
        config["AI_PROVIDER"] = ai_provider
        
        # Step 2: Get required and optional API keys based on provider
        required_keys = self.get_required_api_keys(ai_provider)
        optional_keys = self.get_optional_api_keys()
        
        print("Please provide the following API keys and configuration:")
        print("(Required fields must be provided, optional items can be skipped by pressing Enter)")
        print()
        
        # Collect required API keys
        print("📝 Required Configuration:")
        for key_name in required_keys:
            prompt = next((p for p in self.api_prompts if p.key_name == key_name), None)
            if prompt:
                config[key_name] = self._prompt_for_api_key(prompt, required=True)
        
        print()
        print("📁 Optional Configuration (press Enter to skip):")
        for key_name in optional_keys:
            prompt = next((p for p in self.api_prompts if p.key_name == key_name), None)
            if prompt:
                value = self._prompt_for_api_key(prompt, required=False)
                if value:
                    config[key_name] = value
        
        return config
    
    def _prompt_for_api_key(self, prompt: APIKeyPrompt, required: bool = True) -> Optional[str]:
        """Helper method to prompt for a single API key with validation"""
        while True:
            required_indicator = " (required)" if required else " (optional)"
            print(f"📋 {prompt.key_name}{required_indicator}")
            print(f"   Description: {prompt.description}")
            print(f"   Get it from: {prompt.obtain_url}")
            if prompt.example_format:
                print(f"   Format: {prompt.example_format}")
            print()
            
            value = input(f"Enter {prompt.key_name}: ").strip()
            
            # Handle optional fields
            if not value and not required:
                print("   Skipping optional field.")
                print()
                return None
            
            # Validate required fields
            if not value and required:
                print("   ❌ This field is required. Please provide a value.")
                print()
                continue
            
            # Validate format if pattern exists
            if value and not self.validate_api_key(prompt.key_name, value):
                print(f"   ❌ Invalid format. Expected format: {prompt.example_format}")
                print()
                continue
            
            if value:
                print("   ✅ Value accepted.")
                print()
                return value
            
            break
        
        return None
    
    def create_env_file(self, config: Dict[str, str]) -> bool:
        """Create .env file with secure permissions"""
        try:
            env_content = []
            env_content.append("# ProspectAI Configuration")
            env_content.append("# Generated by interactive setup")
            env_content.append(f"# Created: {platform.system()} - {os.getlogin() if hasattr(os, 'getlogin') else 'Unknown'}")
            env_content.append("")
            
            # Core API keys
            env_content.append("# Core API Configuration")
            for key in ["NOTION_TOKEN", "HUNTER_API_KEY"]:
                if key in config:
                    env_content.append(f"{key}={config[key]}")
                else:
                    env_content.append(f"# {key}=")
            env_content.append("")
            
            # AI Provider Configuration
            env_content.append("# AI Provider Configuration")
            if "AI_PROVIDER" in config:
                env_content.append(f"AI_PROVIDER={config['AI_PROVIDER']}")
            
            # AI Provider-specific keys
            ai_keys = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY", "DEEPSEEK_API_KEY", 
                      "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOYMENT_NAME"]
            for key in ai_keys:
                if key in config:
                    env_content.append(f"{key}={config[key]}")
            env_content.append("")
            
            # Optional configuration
            env_content.append("# Optional Email Configuration")
            for key in ["RESEND_API_KEY", "SENDER_EMAIL", "SENDER_NAME"]:
                if key in config:
                    env_content.append(f"{key}={config[key]}")
                else:
                    env_content.append(f"# {key}=")
            env_content.append("")
            
            # Write file
            with open(self.env_file, 'w') as f:
                f.write('\n'.join(env_content))
            
            # Set secure permissions on Unix systems
            if platform.system() != "Windows":
                os.chmod(self.env_file, stat.S_IRUSR | stat.S_IWUSR)  # 600 permissions
            
            print("✅ Configuration file created successfully")
            self.installation_state.config_created = True
            return True
            
        except Exception as e:
            print(f"❌ Error creating configuration file: {str(e)}")
            return False
    
    def validate_configuration(self) -> bool:
        """Automated validation using existing CLI commands"""
        self.print_step("Validating configuration...", "Testing API connections")
        
        try:
            python_exe = self.get_venv_python()
            cli_path = self.project_root / "cli.py"
            
            if not cli_path.exists():
                print(f"❌ CLI script not found at {cli_path}")
                return False
            
            # Run validation command
            result = subprocess.run([
                str(python_exe), str(cli_path), 'validate-config'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print("✅ Configuration validation successful")
                self.installation_state.config_validated = True
                return True
            else:
                print(f"❌ Configuration validation failed:")
                print(f"   {result.stderr}")
                print("\n💡 Common issues:")
                print("   • Check API key formats")
                print("   • Verify API key permissions")
                print("   • Ensure network connectivity")
                return False
                
        except subprocess.TimeoutExpired:
            print("❌ Configuration validation timed out")
            return False
        except Exception as e:
            print(f"❌ Error validating configuration: {str(e)}")
            return False
    
    def setup_dashboard(self) -> bool:
        """Initialize Notion dashboard infrastructure"""
        self.print_step("Setting up Notion dashboard...", "Creating database structure")
        
        try:
            python_exe = self.get_venv_python()
            setup_script = self.project_root / "scripts" / "setup_dashboard.py"
            
            if not setup_script.exists():
                print(f"❌ Dashboard setup script not found at {setup_script}")
                return False
            
            # Run dashboard setup
            result = subprocess.run([
                str(python_exe), str(setup_script)
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                print("✅ Dashboard setup completed")
                self.installation_state.dashboard_setup = True
                return True
            else:
                print(f"❌ Dashboard setup failed:")
                print(f"   {result.stderr}")
                print("\n💡 Troubleshooting:")
                print("   • Check Notion integration permissions")
                print("   • Verify database access rights")
                print("   • Try running setup-dashboard command manually")
                return False
                
        except subprocess.TimeoutExpired:
            print("❌ Dashboard setup timed out")
            return False
        except Exception as e:
            print(f"❌ Error setting up dashboard: {str(e)}")
            return False
    
    def create_runner_scripts(self) -> bool:
        """Generate platform-specific execution scripts"""
        self.print_step("Creating runner scripts...", "Setting up easy execution commands")
        
        try:
            # Create Windows runner
            if not self.create_windows_runner():
                return False
            
            # Create Unix runner
            if not self.create_unix_runner():
                return False
            
            print("✅ Runner scripts created successfully")
            self.installation_state.runners_created = True
            return True
            
        except Exception as e:
            print(f"❌ Error creating runner scripts: {str(e)}")
            return False
    
    def create_windows_runner(self) -> bool:
        """Create Windows batch runner script"""
        runner_content = '''@echo off
setlocal enabledelayedexpansion

if not exist "venv\\Scripts\\python.exe" (
    echo Virtual environment not found. Please run install.bat first.
    pause
    exit /b 1
)

if "%~1"=="" (
    echo.
    echo ========================================
    echo   ProspectAI Job Automation Tool
    echo ========================================
    echo.
    echo Available commands:
    echo   run-campaign --limit 10    - Run a prospect campaign
    echo   status                     - Check system status
    echo   validate-config            - Validate configuration
    echo   setup-dashboard            - Setup Notion dashboard
    echo   quick-start                - Complete setup + first campaign
    echo.
    echo Usage: run.bat [command] [options]
    echo Example: run.bat run-campaign --limit 5
    echo.
    pause
    exit /b 0
)

venv\\Scripts\\python.exe cli.py %*
if %errorlevel% neq 0 (
    echo.
    echo Command failed with exit code %errorlevel%
    pause
)
'''
        
        try:
            runner_path = self.project_root / "run.bat"
            with open(runner_path, 'w') as f:
                f.write(runner_content)
            return True
        except Exception as e:
            print(f"❌ Error creating Windows runner: {str(e)}")
            return False
    
    def create_unix_runner(self) -> bool:
        """Create Unix shell runner script"""
        runner_content = '''#!/bin/bash

if [ ! -f "venv/bin/python" ]; then
    echo "Virtual environment not found. Please run ./install.sh first."
    exit 1
fi

if [ $# -eq 0 ]; then
    echo ""
    echo "========================================"
    echo "  ProspectAI Job Automation Tool"
    echo "========================================"
    echo ""
    echo "Available commands:"
    echo "  run-campaign --limit 10    - Run a prospect campaign"
    echo "  status                     - Check system status"
    echo "  validate-config            - Validate configuration"
    echo "  setup-dashboard            - Setup Notion dashboard"
    echo "  quick-start                - Complete setup + first campaign"
    echo ""
    echo "Usage: ./run.sh [command] [options]"
    echo "Example: ./run.sh run-campaign --limit 5"
    echo ""
    exit 0
fi

venv/bin/python cli.py "$@"
exit_code=$?

if [ $exit_code -ne 0 ]; then
    echo ""
    echo "Command failed with exit code $exit_code"
fi

exit $exit_code
'''
        
        try:
            runner_path = self.project_root / "run.sh"
            with open(runner_path, 'w') as f:
                f.write(runner_content)
            
            # Make executable on Unix systems
            if platform.system() != "Windows":
                os.chmod(runner_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)  # 755
            
            return True
        except Exception as e:
            print(f"❌ Error creating Unix runner: {str(e)}")
            return False
    
    def run_setup(self) -> bool:
        """Execute the complete setup process"""
        self.print_header()
        
        # Mark Python as installed (we assume this since this script is running)
        self.installation_state.python_installed = True
        
        # Step 1: Create virtual environment
        if not self.create_virtual_environment():
            return False
        
        # Step 2: Install dependencies
        if not self.install_dependencies():
            return False
        
        # Step 3: Collect configuration
        config = self.collect_api_configuration()
        if config and not self.create_env_file(config):
            return False
        elif config:
            pass  # Config created successfully
        else:
            print("Using existing configuration.")
            self.installation_state.config_created = True
        
        # Step 4: Validate configuration
        if not self.validate_configuration():
            print("⚠️  Configuration validation failed, but you can try again later.")
            print("   Run: python cli.py validate-config")
        
        # Step 5: Setup dashboard
        if not self.setup_dashboard():
            print("⚠️  Dashboard setup failed, but you can try again later.")
            print("   Run: python cli.py setup-dashboard")
        
        # Step 6: Create runner scripts
        if not self.create_runner_scripts():
            return False
        
        # Success message
        self.print_success_message()
        return True
    
    def print_success_message(self):
        """Print setup completion message"""
        print("=" * 70)
        print("🎉 Setup Complete!")
        print("=" * 70)
        print()
        print("✅ Virtual environment created")
        print("✅ Dependencies installed")
        print("✅ Configuration files created")
        print("✅ Runner scripts ready")
        print()
        print("🚀 Next Steps:")
        print()
        if platform.system() == "Windows":
            print("   1. Double-click run.bat to see available commands")
            print("   2. Or run: run.bat run-campaign --limit 5")
        else:
            print("   1. Run: ./run.sh (to see available commands)")
            print("   2. Or run: ./run.sh run-campaign --limit 5")
        print()
        print("📚 Documentation:")
        print("   • Check README.md for detailed usage")
        print("   • See examples/ folder for advanced usage")
        print()
        print("🆘 Need help?")
        print("   • Validate config: python cli.py validate-config")
        print("   • Setup dashboard: python cli.py setup-dashboard")
        print("   • Check status: python cli.py status")
        print()


def main():
    """Main entry point for interactive setup"""
    try:
        setup = InteractiveSetup()
        success = setup.run_setup()
        
        if success:
            print("Installation completed successfully!")
            sys.exit(0)
        else:
            print("Installation failed. Please check the error messages above.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\nInstallation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error during setup: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()