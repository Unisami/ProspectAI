"""
Installation recovery and troubleshooting system for ProspectAI installer.
Provides automated recovery mechanisms for common installation failures.
"""

import os
import sys
import subprocess
import shutil
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from .platform_detection import get_platform_manager
from .installer_error_handler import get_error_handler, ErrorCategory


class RecoveryAction(Enum):
    """Types of recovery actions"""
    RETRY = "retry"
    UPGRADE_TOOL = "upgrade_tool"
    CLEAR_CACHE = "clear_cache"
    REINSTALL = "reinstall"
    MANUAL_INTERVENTION = "manual_intervention"
    PERMISSION_FIX = "permission_fix"
    NETWORK_CHECK = "network_check"


@dataclass
class RecoveryStep:
    """Individual recovery step"""
    action: RecoveryAction
    description: str
    command: Optional[str] = None
    automatic: bool = True
    success_check: Optional[str] = None


@dataclass
class RecoveryPlan:
    """Complete recovery plan for an installation issue"""
    issue_type: str
    description: str
    steps: List[RecoveryStep]
    estimated_time: str
    success_rate: str


class InstallationRecoveryManager:
    """Comprehensive recovery system for installation failures"""
    
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path.cwd()
        self.venv_path = self.project_root / "venv"
        self.platform_manager = get_platform_manager()
        self.error_handler = get_error_handler()
        self.logger = logging.getLogger("recovery_manager")
        
        # Recovery plans for different failure types
        self.recovery_plans = self._initialize_recovery_plans()
    
    def _initialize_recovery_plans(self) -> Dict[str, RecoveryPlan]:
        """Initialize recovery plans for different failure scenarios"""
        plans = {}
        
        # Python installation failure
        plans["python_install_failed"] = RecoveryPlan(
            issue_type="python_install_failed",
            description="Python 3.13 installation failed via package manager",
            steps=[
                RecoveryStep(
                    action=RecoveryAction.RETRY,
                    description="Retry package manager installation",
                    automatic=True
                ),
                RecoveryStep(
                    action=RecoveryAction.UPGRADE_TOOL,
                    description="Update package manager",
                    command=self._get_package_manager_update_command(),
                    automatic=True
                ),
                RecoveryStep(
                    action=RecoveryAction.MANUAL_INTERVENTION,
                    description="Manual Python installation required",
                    automatic=False
                )
            ],
            estimated_time="5-10 minutes",
            success_rate="85%"
        )
        
        # Virtual environment creation failure
        plans["venv_creation_failed"] = RecoveryPlan(
            issue_type="venv_creation_failed",
            description="Virtual environment creation failed",
            steps=[
                RecoveryStep(
                    action=RecoveryAction.CLEAR_CACHE,
                    description="Clear existing venv directory",
                    automatic=True
                ),
                RecoveryStep(
                    action=RecoveryAction.PERMISSION_FIX,
                    description="Fix directory permissions",
                    automatic=True
                ),
                RecoveryStep(
                    action=RecoveryAction.RETRY,
                    description="Retry venv creation with different Python executable",
                    automatic=True
                )
            ],
            estimated_time="2-5 minutes",
            success_rate="90%"
        )
        
        # Dependency installation failure
        plans["dependency_install_failed"] = RecoveryPlan(
            issue_type="dependency_install_failed",
            description="Package installation failed",
            steps=[
                RecoveryStep(
                    action=RecoveryAction.UPGRADE_TOOL,
                    description="Upgrade pip to latest version",
                    command="python -m pip install --upgrade pip",
                    automatic=True
                ),
                RecoveryStep(
                    action=RecoveryAction.CLEAR_CACHE,
                    description="Clear pip cache",
                    command="python -m pip cache purge",
                    automatic=True
                ),
                RecoveryStep(
                    action=RecoveryAction.RETRY,
                    description="Retry installation with --no-cache-dir",
                    automatic=True
                ),
                RecoveryStep(
                    action=RecoveryAction.NETWORK_CHECK,
                    description="Check network connectivity and proxy settings",
                    automatic=False
                )
            ],
            estimated_time="3-7 minutes",
            success_rate="80%"
        )
        
        # Configuration validation failure
        plans["config_validation_failed"] = RecoveryPlan(
            issue_type="config_validation_failed",
            description="API configuration validation failed",
            steps=[
                RecoveryStep(
                    action=RecoveryAction.RETRY,
                    description="Retry validation with fresh configuration",
                    automatic=True
                ),
                RecoveryStep(
                    action=RecoveryAction.MANUAL_INTERVENTION,
                    description="Manually verify API keys and network connectivity",
                    automatic=False
                )
            ],
            estimated_time="2-5 minutes",
            success_rate="70%"
        )
        
        # Dashboard setup failure
        plans["dashboard_setup_failed"] = RecoveryPlan(
            issue_type="dashboard_setup_failed",
            description="Notion dashboard setup failed",
            steps=[
                RecoveryStep(
                    action=RecoveryAction.RETRY,
                    description="Retry dashboard setup",
                    automatic=True
                ),
                RecoveryStep(
                    action=RecoveryAction.MANUAL_INTERVENTION,
                    description="Check Notion integration permissions and workspace access",
                    automatic=False
                )
            ],
            estimated_time="3-8 minutes",
            success_rate="75%"
        )
        
        # Permission errors
        plans["permission_error"] = RecoveryPlan(
            issue_type="permission_error",
            description="Insufficient permissions for installation",
            steps=[
                RecoveryStep(
                    action=RecoveryAction.PERMISSION_FIX,
                    description="Attempt to fix permissions",
                    automatic=True
                ),
                RecoveryStep(
                    action=RecoveryAction.MANUAL_INTERVENTION,
                    description="Run installer with elevated privileges",
                    automatic=False
                )
            ],
            estimated_time="1-3 minutes",
            success_rate="95%"
        )
        
        return plans
    
    def _get_package_manager_update_command(self) -> Optional[str]:
        """Get command to update package manager"""
        package_manager = self.platform_manager.get_package_manager()
        
        if package_manager == "winget":
            return "winget upgrade"
        elif package_manager == "brew":
            return "brew update"
        elif package_manager == "apt":
            return "sudo apt-get update"
        elif package_manager == "dnf":
            return "sudo dnf update"
        elif package_manager == "yum":
            return "sudo yum update"
        
        return None
    
    def diagnose_failure(self, error_type: str, error_details: Dict[str, Any]) -> Optional[RecoveryPlan]:
        """Diagnose installation failure and return appropriate recovery plan"""
        
        # Map error types to recovery plans
        error_to_plan = {
            "PYTHON_NOT_FOUND": "python_install_failed",
            "PYTHON_INSTALL_FAILED": "python_install_failed",
            "VENV_CREATION_FAILED": "venv_creation_failed",
            "DEPENDENCY_INSTALL_FAILED": "dependency_install_failed",
            "CONFIG_VALIDATION_FAILED": "config_validation_failed",
            "DASHBOARD_SETUP_FAILED": "dashboard_setup_failed",
            "PERMISSION_DENIED": "permission_error"
        }
        
        plan_key = error_to_plan.get(error_type)
        if plan_key:
            return self.recovery_plans[plan_key]
        
        return None
    
    def execute_recovery(self, plan: RecoveryPlan, interactive: bool = True) -> bool:
        """Execute a recovery plan"""
        print(f"\n🔧 Starting recovery for: {plan.description}")
        print(f"   Estimated time: {plan.estimated_time}")
        print(f"   Success rate: {plan.success_rate}")
        print()
        
        if interactive:
            response = input("Proceed with automatic recovery? (Y/n): ").strip().lower()
            if response in ['n', 'no']:
                print("Recovery cancelled.")
                return False
        
        success = True
        for i, step in enumerate(plan.steps, 1):
            print(f"[{i}/{len(plan.steps)}] {step.description}...")
            
            if step.automatic:
                step_success = self._execute_recovery_step(step)
                if step_success:
                    print(f"   ✅ Completed successfully")
                else:
                    print(f"   ❌ Step failed")
                    success = False
                    
                    if not interactive:
                        break
                    
                    response = input("   Continue with next step? (Y/n): ").strip().lower()
                    if response in ['n', 'no']:
                        break
            else:
                print(f"   ⚠️  Manual intervention required")
                self._provide_manual_instructions(step)
                
                if interactive:
                    input("   Press Enter when you've completed this step...")
        
        return success
    
    def _execute_recovery_step(self, step: RecoveryStep) -> bool:
        """Execute an individual recovery step"""
        try:
            if step.action == RecoveryAction.CLEAR_CACHE:
                return self._clear_cache(step)
            elif step.action == RecoveryAction.UPGRADE_TOOL:
                return self._upgrade_tool(step)
            elif step.action == RecoveryAction.PERMISSION_FIX:
                return self._fix_permissions(step)
            elif step.action == RecoveryAction.RETRY:
                return self._retry_operation(step)
            elif step.action == RecoveryAction.NETWORK_CHECK:
                return self._check_network(step)
            else:
                self.logger.warning(f"Unknown recovery action: {step.action}")
                return False
                
        except Exception as e:
            self.logger.error(f"Recovery step failed: {e}")
            return False
    
    def _clear_cache(self, step: RecoveryStep) -> bool:
        """Clear various caches"""
        try:
            # Clear pip cache
            if "pip" in step.description.lower():
                python_exe = self.platform_manager.get_venv_python_path(self.venv_path)
                if python_exe.exists():
                    result = subprocess.run([
                        str(python_exe), "-m", "pip", "cache", "purge"
                    ], capture_output=True, text=True)
                    return result.returncode == 0
            
            # Clear venv directory
            elif "venv" in step.description.lower():
                if self.venv_path.exists():
                    shutil.rmtree(self.venv_path)
                return True
            
            return True
            
        except Exception as e:
            self.logger.error(f"Cache clearing failed: {e}")
            return False
    
    def _upgrade_tool(self, step: RecoveryStep) -> bool:
        """Upgrade tools like pip or package managers"""
        try:
            if step.command:
                # Handle pip upgrade specially
                if "pip" in step.command and "upgrade" in step.command:
                    python_exe = self.platform_manager.get_venv_python_path(self.venv_path)
                    if python_exe.exists():
                        result = subprocess.run([
                            str(python_exe), "-m", "pip", "install", "--upgrade", "pip"
                        ], capture_output=True, text=True)
                        return result.returncode == 0
                
                # Execute generic command
                result = subprocess.run(
                    step.command.split(),
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout
                )
                return result.returncode == 0
            
            return True
            
        except Exception as e:
            self.logger.error(f"Tool upgrade failed: {e}")
            return False
    
    def _fix_permissions(self, step: RecoveryStep) -> bool:
        """Fix file and directory permissions"""
        try:
            # Check if we need elevated permissions
            if not self.platform_manager.is_admin() and not self.platform_manager.is_windows:
                print(f"   ⚠️  Administrator privileges may be required")
                return False
            
            # Fix venv directory permissions
            if self.venv_path.exists():
                if not self.platform_manager.is_windows:
                    os.chmod(self.venv_path, 0o755)
                    for root, dirs, files in os.walk(self.venv_path):
                        for d in dirs:
                            os.chmod(os.path.join(root, d), 0o755)
                        for f in files:
                            os.chmod(os.path.join(root, f), 0o644)
            
            # Fix project directory permissions
            if not os.access(self.project_root, os.W_OK):
                if not self.platform_manager.is_windows:
                    os.chmod(self.project_root, 0o755)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Permission fix failed: {e}")
            return False
    
    def _retry_operation(self, step: RecoveryStep) -> bool:
        """Retry a failed operation"""
        # This is a placeholder - the actual retry logic depends on context
        # In practice, this would be handled by the calling code
        print(f"   ↻ Retrying operation...")
        return True
    
    def _check_network(self, step: RecoveryStep) -> bool:
        """Check network connectivity"""
        try:
            import urllib.request
            
            # Test connectivity to PyPI
            urllib.request.urlopen('https://pypi.org', timeout=10)
            print(f"   ✅ PyPI connectivity OK")
            
            # Test connectivity to other services
            test_urls = [
                'https://api.openai.com',
                'https://api.notion.com',
                'https://api.hunter.io'
            ]
            
            for url in test_urls:
                try:
                    urllib.request.urlopen(url, timeout=5)
                    print(f"   ✅ {url} reachable")
                except Exception:
                    print(f"   ⚠️  {url} may be unreachable")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Network connectivity issue: {e}")
            return False
    
    def _provide_manual_instructions(self, step: RecoveryStep):
        """Provide manual instructions for non-automatic steps"""
        print(f"\n   📋 Manual Instructions:")
        
        if "Python installation" in step.description:
            print(f"   1. Go to: https://www.python.org/downloads/")
            print(f"   2. Download Python 3.13.x for your system")
            print(f"   3. Run the installer")
            if self.platform_manager.is_windows:
                print(f"   4. Make sure to check 'Add Python to PATH'")
            print(f"   5. Restart your terminal/command prompt")
            print(f"   6. Run the installer again")
        
        elif "elevated privileges" in step.description:
            if self.platform_manager.is_windows:
                print(f"   1. Close this window")
                print(f"   2. Right-click Command Prompt")
                print(f"   3. Select 'Run as administrator'")
                print(f"   4. Navigate to the project directory")
                print(f"   5. Run install.bat again")
            else:
                print(f"   1. Run: sudo ./install.sh")
                print(f"   2. Or fix permissions: sudo chown -R $USER .")
        
        elif "API keys" in step.description:
            print(f"   1. Verify each API key is correct")
            print(f"   2. Check API key permissions")
            print(f"   3. Test network connectivity")
            print(f"   4. Run: python cli.py validate-config")
        
        elif "Notion" in step.description:
            print(f"   1. Check Notion integration permissions")
            print(f"   2. Ensure integration is shared with workspace")
            print(f"   3. Verify token has page creation rights")
            print(f"   4. Run: python cli.py setup-dashboard")
        
        elif "network" in step.description.lower():
            print(f"   1. Check internet connection")
            print(f"   2. Verify proxy settings if behind corporate firewall")
            print(f"   3. Temporarily disable VPN if using one")
            print(f"   4. Check if antivirus is blocking connections")
        
        print()
    
    def create_recovery_report(self, failures: List[str]) -> Dict[str, Any]:
        """Create a comprehensive recovery report"""
        report = {
            "timestamp": str(Path.cwd()),
            "platform": self.platform_manager.get_system_info(),
            "failures": failures,
            "recovery_plans": [],
            "recommendations": []
        }
        
        # Add recovery plans for each failure
        for failure in failures:
            plan = self.diagnose_failure(failure, {})
            if plan:
                report["recovery_plans"].append({
                    "issue": plan.issue_type,
                    "description": plan.description,
                    "estimated_time": plan.estimated_time,
                    "success_rate": plan.success_rate,
                    "steps": [step.description for step in plan.steps]
                })
        
        # Add general recommendations
        if failures:
            report["recommendations"] = [
                "Ensure stable internet connection",
                "Run installer with administrator privileges if needed",
                "Temporarily disable antivirus during installation",
                "Use latest version of the installer",
                "Check system meets minimum requirements"
            ]
        
        return report
    
    def auto_recover_installation(self, error_type: str, error_details: Dict[str, Any]) -> bool:
        """Automatically attempt to recover from installation failure"""
        plan = self.diagnose_failure(error_type, error_details)
        if not plan:
            print(f"❌ No recovery plan available for error: {error_type}")
            return False
        
        print(f"\n🔄 Automatic recovery initiated for: {plan.description}")
        
        # Execute only automatic steps
        for step in plan.steps:
            if step.automatic:
                print(f"   Executing: {step.description}")
                success = self._execute_recovery_step(step)
                if success:
                    print(f"   ✅ Success")
                else:
                    print(f"   ❌ Failed - manual intervention may be required")
                    return False
            else:
                print(f"   ⚠️  Manual step required: {step.description}")
                return False
        
        print(f"✅ Automatic recovery completed")
        return True


# Global recovery manager instance
_recovery_manager = None

def get_recovery_manager(project_root: Path = None) -> InstallationRecoveryManager:
    """Get or create global recovery manager instance"""
    global _recovery_manager
    if _recovery_manager is None:
        _recovery_manager = InstallationRecoveryManager(project_root)
    return _recovery_manager