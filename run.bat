@echo off
setlocal enabledelayedexpansion

if not exist "venv\Scripts\python.exe" (
    echo Virtual environment not found. Please run install.bat first.
    pause
    exit /b 1
)

if "%~1"=="" (
    goto :menu
) else (
    venv\Scripts\python.exe cli.py %*
    if %errorlevel% neq 0 (
        echo.
        echo Command failed with exit code %errorlevel%
        pause
    )
    exit /b %errorlevel%
)

:menu
cls
echo.
echo ================================================================================
echo              ProspectAI - Intelligent Job Automation System v2.0
echo ================================================================================
echo.
echo    MAIN MENU
echo.
echo [1] Quick Start         - Complete setup + run first campaign
echo [2] Guided Setup        - Step-by-step configuration wizard
echo [3] Run Campaign        - Full workflow: discovery + emails + analytics
echo [4] Discovery Only      - Find companies and prospects
echo [5] Email Generation    - Create personalized emails for recent prospects
echo [6] Send Emails         - Send the most recent generated emails
echo.
echo [7] Status Dashboard    - Show current workflow status and statistics
echo [8] Validate Config     - Check your API configuration and connections
echo [9] Setup Dashboard     - Create/update Notion dashboard
echo.
echo [A] Advanced Options    - Custom campaigns, specific company processing
echo [M] Maintenance Menu    - System health, repairs, configuration management
echo [H] Help and Info      - Commands, system info, documentation
echo.
echo [0] Exit
echo.
echo ================================================================================
set /p choice="Enter your choice (0-9, A, M, H): "
echo.

if "%choice%"=="1" (
    echo Running Quick Start Campaign...
    echo This will discover 5 companies, find prospects, and generate sample emails
    venv\Scripts\python.exe cli.py quick-start --limit 5
    echo.
    pause
    goto :menu
) else if "%choice%"=="2" (
    echo Starting Guided Setup Wizard...
    echo This will help you configure your API keys and settings
    venv\Scripts\python.exe cli.py validate-config
    if !errorlevel! equ 0 (
        echo Configuration looks good! Setting up dashboard...
        venv\Scripts\python.exe cli.py setup-dashboard
    )
    echo.
    pause
    goto :menu
) else if "%choice%"=="3" (
    echo Running Full Campaign Workflow...
    set /p limit="Enter number of companies to process (default 10): "
    if "!limit!"=="" set limit=10
    echo Processing !limit! companies with full workflow...
    venv\Scripts\python.exe cli.py run-campaign --limit !limit!
    echo.
    pause
    goto :menu
) else if "%choice%"=="4" (
    echo Running Discovery Pipeline...
    set /p limit="Enter number of companies to discover (default 20): "
    if "!limit!"=="" set limit=20
    echo Discovering !limit! companies and extracting team information...
    venv\Scripts\python.exe cli.py discover --limit !limit!
    echo.
    pause
    goto :menu
) else if "%choice%"=="5" (
    echo Generating Personalized Emails...
    set /p limit="Enter number of emails to generate (default 10): "
    if "!limit!"=="" set limit=10
    echo Generating !limit! personalized emails for recent prospects...
    venv\Scripts\python.exe cli.py generate-emails-recent --limit !limit!
    echo.
    pause
    goto :menu
) else if "%choice%"=="6" (
    echo Sending Recent Emails...
    set /p limit="Enter number of emails to send (default 5): "
    if "!limit!"=="" set limit=5
    set /p delay="Enter delay between emails in seconds (default 30): "
    if "!delay!"=="" set delay=30
    echo Sending !limit! emails with !delay! second delay...
    venv\Scripts\python.exe cli.py send-emails-recent --limit !limit! --delay !delay!
    echo.
    pause
    goto :menu
) else if "%choice%"=="7" (
    echo Checking System Status...
    venv\Scripts\python.exe cli.py status
    echo.
    pause
    goto :menu
) else if "%choice%"=="8" (
    echo Validating Configuration...
    echo Checking API keys and connections...
    venv\Scripts\python.exe cli.py validate-config
    echo.
    pause
    goto :menu
) else if "%choice%"=="9" (
    echo Setting up Notion Dashboard...
    echo Creating databases and dashboard structure...
    venv\Scripts\python.exe cli.py setup-dashboard
    echo.
    pause
    goto :menu
) else if /i "%choice%"=="A" (
    call :advanced_menu
    goto :menu
) else if /i "%choice%"=="M" (
    call :maintenance_menu
    goto :menu
) else if /i "%choice%"=="H" (
    call :help_menu
    goto :menu
) else if "%choice%"=="0" (
    echo Goodbye! Thanks for using ProspectAI!
    exit /b 0
) else (
    echo Invalid choice. Please enter a number between 0-9 or A, M, H.
    echo.
    pause
    goto :menu
)

goto :eof

:advanced_menu
cls
echo.
echo ================================================================================
echo                            ADVANCED OPTIONS MENU
echo ================================================================================
echo.
echo [1] Custom Campaign     - Run campaign with custom parameters
echo [2] Process Company     - Process a specific company by name
echo [3] Campaign Progress   - View current campaign progress
echo [4] Analytics Report    - View daily analytics and performance stats
echo [5] Email Queue         - Manage pending emails and delivery status
echo [6] Profile Setup       - Configure sender profile for personalization
echo [7] AI Provider         - Configure AI providers (OpenAI, Anthropic, etc.)
echo.
echo [0] Back to Main Menu
echo.
echo ================================================================================
set /p adv_choice="Enter your choice (0-7): "
echo.

if "%adv_choice%"=="1" (
    call :custom_campaign
    exit /b
) else if "%adv_choice%"=="2" (
    call :process_company
    exit /b
) else if "%adv_choice%"=="3" (
    echo Checking Campaign Progress...
    venv\Scripts\python.exe cli.py campaign-status
    echo.
    pause
    call :advanced_menu
    exit /b
) else if "%adv_choice%"=="4" (
    echo Generating Analytics Report...
    echo [1] Daily Report
    echo [2] Weekly Report
    echo [3] Monthly Report
    set /p period_choice="Select report period (1-3): "
    if "!period_choice!"=="1" set period=daily
    if "!period_choice!"=="2" set period=weekly
    if "!period_choice!"=="3" set period=monthly
    if "!period!"=="" set period=daily
    venv\Scripts\python.exe cli.py analytics-report --period !period!
    echo.
    pause
    call :advanced_menu
    exit /b
) else if "%adv_choice%"=="5" (
    echo Managing Email Queue...
    venv\Scripts\python.exe cli.py email-queue
    echo.
    pause
    call :advanced_menu
    exit /b
) else if "%adv_choice%"=="6" (
    echo Configuring Sender Profile...
    venv\Scripts\python.exe cli.py profile-setup
    echo.
    pause
    call :advanced_menu
    exit /b
) else if "%adv_choice%"=="7" (
    echo Configuring AI Providers...
    venv\Scripts\python.exe cli.py configure-ai
    echo.
    pause
    call :advanced_menu
    exit /b
) else if "%adv_choice%"=="0" (
    exit /b
) else (
    echo Invalid choice. Please enter a number between 0 and 7.
    echo.
    pause
    call :advanced_menu
    exit /b
)

:maintenance_menu
cls
echo.
echo ================================================================================
echo                           MAINTENANCE & RECOVERY MENU
echo ================================================================================
echo.
echo [1] Installation Check  - Comprehensive installation status diagnostics
echo [2] Repair Installation - Automated recovery for common installation issues
echo [3] Config Management   - Backup, restore, and migrate configuration files
echo [4] System Health       - Performance monitoring and resource usage
echo [5] Update Check        - Check for updates and maintenance notifications
echo [6] Debug Mode          - Advanced logging and troubleshooting tools
echo [7] Batch Operations    - Automated batch processing and scheduling
echo.
echo [0] Back to Main Menu
echo.
echo ================================================================================
set /p maint_choice="Enter your choice (0-7): "
echo.

if "%maint_choice%"=="1" (
    call :installation_check
    call :maintenance_menu
    exit /b
) else if "%maint_choice%"=="2" (
    call :repair_installation
    call :maintenance_menu
    exit /b
) else if "%maint_choice%"=="3" (
    call :config_management
    call :maintenance_menu
    exit /b
) else if "%maint_choice%"=="4" (
    call :system_health
    call :maintenance_menu
    exit /b
) else if "%maint_choice%"=="5" (
    call :update_check
    call :maintenance_menu
    exit /b
) else if "%maint_choice%"=="6" (
    call :debug_mode
    call :maintenance_menu
    exit /b
) else if "%maint_choice%"=="7" (
    call :batch_operations
    call :maintenance_menu
    exit /b
) else if "%maint_choice%"=="0" (
    exit /b
) else (
    echo Invalid choice. Please enter a number between 0 and 7.
    echo.
    pause
    call :maintenance_menu
    exit /b
)

:help_menu
cls
echo.
echo ================================================================================
echo                              HELP & INFORMATION MENU
echo ================================================================================
echo.
echo [1] Help & Commands     - Show all available commands and examples
echo [2] System Info         - Show system status and configuration info
echo [3] Getting Started     - Quick start guide and tutorials
echo [4] API Configuration   - Help with setting up API keys
echo [5] Troubleshooting     - Common issues and solutions
echo.
echo [0] Back to Main Menu
echo.
echo ================================================================================
set /p help_choice="Enter your choice (0-5): "
echo.

if "%help_choice%"=="1" (
    call :show_help
    call :help_menu
    exit /b
) else if "%help_choice%"=="2" (
    call :system_info
    call :help_menu
    exit /b
) else if "%help_choice%"=="3" (
    echo.
    echo GETTING STARTED GUIDE:
    echo 1. Run 'Guided Setup' to configure your API keys
    echo 2. Use 'Quick Start' to run your first campaign
    echo 3. Check 'Status Dashboard' to monitor progress
    echo 4. Use 'Validate Config' if you encounter issues
    echo.
    pause
    call :help_menu
    exit /b
) else if "%help_choice%"=="4" (
    echo.
    echo API CONFIGURATION HELP:
    echo - Notion Token: Visit https://developers.notion.com/docs/create-a-notion-integration
    echo - Hunter API Key: Visit https://hunter.io/api
    echo - OpenAI API Key: Visit https://platform.openai.com/api-keys
    echo - Resend API Key: Visit https://resend.com/api-keys (optional)
    echo.
    pause
    call :help_menu
    exit /b
) else if "%help_choice%"=="5" (
    echo.
    echo COMMON TROUBLESHOOTING:
    echo - If virtual environment is missing: Run install.bat
    echo - If API keys are invalid: Use 'Validate Config' to check
    echo - If dashboard setup fails: Check Notion permissions
    echo - For installation issues: Use 'Repair Installation'
    echo.
    pause
    call :help_menu
    exit /b
) else if "%help_choice%"=="0" (
    exit /b
) else (
    echo Invalid choice. Please enter a number between 0 and 5.
    echo.
    pause
    call :help_menu
    exit /b
)

:custom_campaign
cls
echo.
echo ================================================================================
echo                          CUSTOM CAMPAIGN CONFIGURATION
echo ================================================================================
echo.
set /p campaign_name="Enter campaign name (default: Custom Campaign): "
if "%campaign_name%"=="" set campaign_name=Custom Campaign

set /p company_limit="Enter number of companies to process (default: 10): "
if "%company_limit%"=="" set company_limit=10

echo.
echo Campaign Options:
echo [1] Discovery only
echo [2] Discovery + Email Generation
echo [3] Full workflow (Discovery + Emails + Sending)
set /p workflow_choice="Select workflow type (1-3): "

echo.
echo Running Custom Campaign: %campaign_name%
echo Companies to process: %company_limit%

if "%workflow_choice%"=="1" (
    echo Workflow: Discovery only
    venv\Scripts\python.exe cli.py discover --limit %company_limit% --campaign-name "%campaign_name%"
) else if "%workflow_choice%"=="2" (
    echo Workflow: Discovery + Email Generation
    venv\Scripts\python.exe cli.py run-campaign --limit %company_limit% --campaign-name "%campaign_name%" --no-send
) else (
    echo Workflow: Full workflow with email sending
    set /p email_delay="Enter delay between emails (seconds, default: 60): "
    if "!email_delay!"=="" set email_delay=60
    venv\Scripts\python.exe cli.py run-campaign --limit %company_limit% --campaign-name "%campaign_name%" --delay !email_delay!
)

echo.
echo Custom campaign completed!
echo.
set /p return="Press Enter to return to main menu..."
exit /b

:process_company
cls
echo.
echo ================================================================================
echo                            PROCESS SPECIFIC COMPANY
echo ================================================================================
echo.
set /p company_name="Enter company name to process: "
if "%company_name%"=="" (
    echo Company name cannot be empty!
    pause
    exit /b
)

set /p company_domain="Enter company domain (optional): "

echo.
echo Processing company: %company_name%
if not "%company_domain%"=="" (
    echo Domain: %company_domain%
    venv\Scripts\python.exe cli.py process-company "%company_name%" --domain "%company_domain%"
) else (
    venv\Scripts\python.exe cli.py process-company "%company_name%"
)

echo.
echo Company processing completed!
echo.
set /p return="Press Enter to return to main menu..."
exit /b

:installation_check
cls
echo.
echo ================================================================================
echo                          INSTALLATION STATUS DIAGNOSTICS
echo ================================================================================
echo.
echo Running comprehensive installation check...
echo.

echo 1. Python Installation Check
echo ----------------------------------------
if exist "venv\Scripts\python.exe" (
    echo OK - Virtual environment found
    echo Path: %CD%\venv\Scripts\python.exe
    for /f "tokens=*" %%i in ('venv\Scripts\python.exe --version 2^>^&1') do echo Version: %%i
    
    echo.
    echo Checking Python packages...
    venv\Scripts\python.exe -m pip list --local 2>nul | findstr /i "click rich"
    if !errorlevel! equ 0 (
        echo OK - Core packages installed
    ) else (
        echo WARNING - Some core packages may be missing
    )
) else (
    echo FAILED - Virtual environment not found
    echo Expected path: %CD%\venv\Scripts\python.exe
    echo Recovery: Run install.bat to create virtual environment
)

echo.
echo 2. Configuration Check
echo ----------------------------------------
if exist ".env" (
    echo OK - Configuration file found
    echo Path: %CD%\.env
    
    echo.
    echo Checking required API keys...
    findstr /c:"NOTION_TOKEN" .env >nul 2>&1
    if !errorlevel! equ 0 (
        echo OK - Notion token configured
    ) else (
        echo MISSING - Notion token not found
    )
    
    findstr /c:"HUNTER_API_KEY" .env >nul 2>&1
    if !errorlevel! equ 0 (
        echo OK - Hunter API key configured
    ) else (
        echo MISSING - Hunter API key not found
    )
) else (
    echo FAILED - Configuration file not found
    echo Expected path: %CD%\.env
    echo Recovery: Run setup or validate-config command
)

echo.
echo 3. Dependencies ^& CLI Check
echo ----------------------------------------
if exist "requirements.txt" (
    echo OK - Requirements file found
) else (
    echo FAILED - Requirements file not found
)

if exist "venv\Scripts\python.exe" (
    if exist "cli.py" (
        echo OK - CLI script found
        echo.
        echo Testing CLI help command...
        venv\Scripts\python.exe cli.py --help >nul 2>&1
        if !errorlevel! equ 0 (
            echo OK - CLI is functional
        ) else (
            echo FAILED - CLI command failed
        )
    ) else (
        echo FAILED - CLI script not found
    )
) else (
    echo SKIPPED - Cannot test CLI without virtual environment
)

echo.
echo ================================================================================
echo Installation Check Complete
echo.
echo Next Steps:
echo - If any components failed, use Repair Installation from Maintenance Menu
echo - Run validate-config to test API connectivity
echo ================================================================================
echo.
set /p return="Press Enter to return to main menu..."
exit /b

:repair_installation
cls
echo.
echo ================================================================================
echo                        AUTOMATED INSTALLATION REPAIR
echo ================================================================================
echo.
echo This will attempt to fix common installation issues...
echo.

echo Step 1: Checking virtual environment...
if not exist "venv\Scripts\python.exe" (
    echo Virtual environment missing. Attempting to recreate...
    python -m venv venv
    if !errorlevel! equ 0 (
        echo OK - Virtual environment created
    ) else (
        echo FAILED - Could not create virtual environment
        echo Please run install.bat manually
        goto :repair_done
    )
) else (
    echo OK - Virtual environment exists
)

echo.
echo Step 2: Updating pip and installing/upgrading dependencies...
venv\Scripts\python.exe -m pip install --upgrade pip
if exist "requirements.txt" (
    echo Installing requirements...
    venv\Scripts\python.exe -m pip install -r requirements.txt --upgrade
    if !errorlevel! equ 0 (
        echo OK - Dependencies installed/updated
    ) else (
        echo WARNING - Some dependencies may have failed to install
    )
) else (
    echo WARNING - requirements.txt not found
)

echo.
echo Step 3: Checking configuration...
if not exist ".env" (
    echo Configuration file missing. Creating template...
    (
        echo # ProspectAI Configuration File
        echo # Required API Keys:
        echo NOTION_TOKEN=
        echo HUNTER_API_KEY=
        echo OPENAI_API_KEY=
        echo.
        echo # Optional Email Configuration:
        echo RESEND_API_KEY=
        echo SENDER_EMAIL=
        echo SENDER_NAME=
    ) > .env
    echo Created .env template. Please add your API keys.
) else (
    echo OK - Configuration file exists
)

echo.
echo Step 4: Testing CLI functionality...
venv\Scripts\python.exe cli.py --help >nul 2>&1
if !errorlevel! equ 0 (
    echo OK - CLI is working
) else (
    echo WARNING - CLI test failed. May need configuration.
)

:repair_done
echo.
echo ================================================================================
echo Repair Process Complete
echo.
echo Recommended Next Steps:
echo 1. Run Installation Check to verify repairs
echo 2. Configure API keys if .env was recreated
echo 3. Run validate-config to test connections
echo 4. Use setup-dashboard to initialize workspace
echo ================================================================================
echo.
set /p return="Press Enter to return to main menu..."
exit /b

:show_help
cls
echo.
echo ================================================================================
echo                             HELP & COMMANDS REFERENCE
echo ================================================================================
echo.
echo MAIN COMMANDS:
echo   run.bat                    - Show this menu
echo   run.bat [command]          - Run specific CLI command
echo.
echo COMMON CLI COMMANDS:
echo   run-campaign --limit 10    - Run full campaign (10 companies)
echo   discover --limit 20        - Discover companies only
echo   generate-emails-recent     - Generate emails for recent prospects
echo   send-emails-recent         - Send recent generated emails
echo   status                     - Check system status
echo   validate-config            - Validate API configuration
echo   setup-dashboard            - Setup Notion dashboard
echo   campaign-status            - View campaign progress
echo   analytics-report           - Generate analytics reports
echo   email-queue                - Manage email queue
echo.
echo CONFIGURATION COMMANDS:
echo   profile-setup              - Setup sender profile
echo   configure-ai               - Configure AI providers
echo   process-company "Name"      - Process specific company
echo.
echo EXAMPLES:
echo   run.bat run-campaign --limit 5
echo   run.bat discover --limit 15
echo   run.bat generate-emails-recent --limit 10
echo   run.bat send-emails-recent --limit 5 --delay 60
echo.
echo For more detailed help on any command:
echo   run.bat [command] --help
echo.
echo ================================================================================
echo.
set /p return="Press Enter to continue..."
exit /b
echo.
echo ================================================================================
echo [96mRepair Process Complete[0m
echo.
echo [36mRecommended Next Steps:[0m
echo 1. Run Installation Check [19] to verify repairs
echo 2. Configure API keys if .env was recreated
echo 3. Run validate-config to test connections
echo 4. Use setup-dashboard to initialize workspace
echo ================================================================================
echo.
set /p return="Press Enter to return to main menu..."
exit /b

:config_management
cls
echo.
echo ================================================================================
echo                                CONFIGURATION MANAGEMENT
echo ================================================================================
echo.
echo [1] Backup Configuration    - Create backup of current .env file
echo [2] Restore Configuration   - Restore from backup file
echo [3] View Configuration      - Display current configuration (masked)
echo [4] Reset Configuration     - Create fresh .env template
echo [5] Export Configuration    - Export config template for transfer
echo [6] Configuration History   - View backup history
echo.
echo [0] Return to Main Menu
echo.
echo ================================================================================
set /p config_choice="Select configuration option (0-6): "
echo.

if "%config_choice%"=="1" (
    echo Creating configuration backup...
    if exist ".env" (
        set backup_name=.env.backup.%date:~10,4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
        set backup_name=!backup_name: =0!
        copy ".env" "!backup_name!" >nul
        if !errorlevel! equ 0 (
            echo OK - Backup created: !backup_name!
        ) else (
            echo FAILED - Could not create backup
        )
    ) else (
        echo WARNING - No .env file found to backup
    )
) else if "%config_choice%"=="2" (
    echo Available backup files:
    dir /b .env.backup.* 2>nul
    if !errorlevel! neq 0 (
        echo No backup files found
    ) else (
        echo.
        set /p backup_file="Enter backup filename to restore: "
        if exist "!backup_file!" (
            copy "!backup_file!" ".env" >nul
            if !errorlevel! equ 0 (
                echo OK - Configuration restored from !backup_file!
            ) else (
                echo FAILED - Could not restore configuration
            )
        ) else (
            echo FAILED - Backup file not found
        )
    )
) else if "%config_choice%"=="3" (
    echo Current configuration (API keys masked):
    if exist ".env" (
        echo.
        for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
            if "%%b"=="" (
                echo %%a
            ) else (
                echo %%a=***MASKED***
            )
        )
    ) else (
        echo No .env file found
    )
) else if "%config_choice%"=="4" (
    echo Creating fresh configuration template...
    if exist ".env" (
        echo Existing .env file will be overwritten!
        set /p confirm="Continue? (y/N): "
        if /i not "!confirm!"=="y" (
            echo Operation cancelled.
            goto :config_done
        )
    )
    (
        echo # ProspectAI Configuration File
        echo # Generated on %date% at %time%
        echo.
        echo # Required API Keys:
        echo NOTION_TOKEN=
        echo HUNTER_API_KEY=
        echo OPENAI_API_KEY=
        echo.
        echo # Optional Email Configuration:
        echo RESEND_API_KEY=
        echo SENDER_EMAIL=
        echo SENDER_NAME=
        echo.
        echo # Optional AI Provider Configuration:
        echo ANTHROPIC_API_KEY=
        echo GOOGLE_API_KEY=
        echo DEEPSEEK_API_KEY=
    ) > .env
    echo OK - Fresh configuration template created
) else if "%config_choice%"=="5" (
    echo Exporting configuration template...
    if exist ".env" (
        (
            echo # ProspectAI Configuration Template
            echo # Exported on %date% at %time%
            echo.
            for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
                if "%%b"=="" (
                    echo %%a
                ) else (
                    echo %%a=
                )
            )
        ) > .env.template
        echo OK - Configuration template exported to .env.template
    ) else (
        echo No .env file found to export
    )
) else if "%config_choice%"=="6" (
    echo Configuration backup history:
    echo.
    dir /b /o-d .env.backup.* 2>nul
    if !errorlevel! neq 0 (
        echo No backup files found
    )
) else if "%config_choice%"=="0" (
    goto :menu
) else (
    echo Invalid choice. Please select 0-6.
)

:config_done
echo.
set /p return="Press Enter to continue..."
goto :config_management

:system_health
cls
echo.
echo ================================================================================
echo                        SYSTEM HEALTH & PERFORMANCE MONITORING
echo ================================================================================
echo.
echo Checking system health and performance...
echo.

echo 1. Virtual Environment Health
echo ----------------------------------------
if exist "venv\Scripts\python.exe" (
    echo OK - Virtual environment active
    
    echo.
    echo [36mPython environment details:[0m
    venv\Scripts\python.exe -c "import sys; print(f'Python: {sys.version.split()[0]}'); print(f'Platform: {sys.platform}')" 2>nul
    
    echo.
    echo [36mPackage health check:[0m
    venv\Scripts\python.exe -m pip check 2>nul
    if !errorlevel! equ 0 (
        echo [32mOK - No dependency conflicts detected[0m
    ) else (
        echo [33mWARNING - Some dependency conflicts detected[0m
    )
) else (
    echo [31mFAILED - Virtual environment not found[0m
)

echo.
echo [36m2. Disk Space Usage[0m
echo ----------------------------------------
echo Project directory size:
dir /s "%CD%" 2>nul | findstr "File(s)" | for /f "tokens=3" %%a in ('findstr /e "bytes"') do echo Total: %%a bytes

echo.
echo Available disk space:
for /f "tokens=3" %%a in ('dir /-c ^| findstr /e "bytes free"') do echo Free: %%a bytes

echo.
echo [36m3. Network Connectivity[0m
echo ----------------------------------------
echo Testing API endpoints...

echo [36mTesting api.notion.com...[0m
ping -n 1 api.notion.com >nul 2>&1
if !errorlevel! equ 0 (
    echo [32mOK - Notion API reachable[0m
) else (
    echo [33mWARNING - Notion API unreachable[0m
)

echo.
echo [36m4. Configuration Health[0m
echo ----------------------------------------
if exist ".env" (
    echo [32mOK - Configuration file present[0m
    
    echo.
    echo [36mRunning configuration validation...[0m
    if exist "venv\Scripts\python.exe" (
        venv\Scripts\python.exe cli.py validate-config >nul 2>&1
        if !errorlevel! equ 0 (
            echo [32mOK - Configuration validation passed[0m
        ) else (
            echo [33mWARNING - Configuration validation failed[0m
        )
    ) else (
        echo [33mSKIPPED - No virtual environment to test with[0m
    )
) else (
    echo [31mFAILED - Configuration file missing[0m
)

echo.
echo ================================================================================
echo [96mSystem Health Check Complete[0m
echo.
echo [36mRecommendations:[0m
echo - Monitor virtual environment for package conflicts
echo - Ensure adequate disk space for operation
echo - Check network connectivity if API calls fail
echo - Validate configuration regularly
echo ================================================================================
echo.
set /p return="Press Enter to return to main menu..."
goto :menu

:update_check
cls
echo.
echo ================================================================================
echo                                UPDATE CHECK & MAINTENANCE
echo ================================================================================
echo.
echo [96mChecking for updates and maintenance notifications...[0m
echo.

echo [36m1. Python Package Updates[0m
echo ----------------------------------------
if exist "venv\Scripts\python.exe" (
    echo [36mChecking for outdated packages...[0m
    venv\Scripts\python.exe -m pip list --outdated --format=columns 2>nul
    if !errorlevel! equ 0 (
        echo.
        echo [36mTo update packages, use: venv\Scripts\python.exe -m pip install --upgrade [package][0m
    ) else (
        echo [32mAll packages appear to be up to date[0m
    )
) else (
    echo [33mSKIPPED - No virtual environment found[0m
)

echo.
echo [36m2. Configuration Status[0m
echo ----------------------------------------
if exist ".env" (
    echo [32mConfiguration file present[0m
    echo.
    echo [36mChecking configuration validation...[0m
    if exist "venv\Scripts\python.exe" (
        venv\Scripts\python.exe cli.py validate-config >nul 2>&1
        if !errorlevel! equ 0 (
            echo [32mConfiguration validation passed[0m
        ) else (
            echo [33mConfiguration validation failed - may need updates[0m
        )
    )
) else (
    echo [33mNo configuration file found[0m
)

echo.
echo [36m3. Repository Status[0m
echo ----------------------------------------
echo [36mChecking git status...[0m
git status 2>nul
if !errorlevel! equ 0 (
    echo [32mGit repository detected[0m
) else (
    echo [33mNot a git repository or git not available[0m
)

echo.
echo [36m4. Maintenance Recommendations[0m
echo ----------------------------------------
echo [36mBased on system analysis:[0m
echo.
echo - Run installation check [19] monthly
echo - Backup configuration [21] before major changes
echo - Monitor system health [22] regularly
echo - Update dependencies periodically
echo - Review API key rotation schedule

echo.
echo ================================================================================
echo [96mUpdate Check Complete[0m
echo ================================================================================
echo.
set /p return="Press Enter to return to main menu..."
goto :menu

:debug_mode
cls
echo.
echo ================================================================================
echo                                ADVANCED DEBUGGING & LOGGING TOOLS
echo ================================================================================
echo.
echo [1] Enable Debug Logging    - Turn on verbose logging for next operation
echo [2] View Recent Logs        - Display recent application logs
echo [3] Test CLI Commands       - Interactive CLI command testing
echo [4] Environment Dump        - Export complete environment information
echo [5] Network Diagnostics     - Advanced network and API testing
echo [6] Clear Debug Data        - Clean up debug files and logs
echo.
echo [0] Return to Main Menu
echo.
echo ================================================================================
set /p debug_choice="Select debug option (0-6): "
echo.

if "%debug_choice%"=="1" (
    echo [36mEnabling debug logging for next operation...[0m
    set DEBUG_MODE=1
    echo [32mDEBUG MODE ENABLED[0m
    echo.
    echo Debug logging will be active for the next CLI command you run.
    echo To disable, restart the script.
) else if "%debug_choice%"=="2" (
    echo [36mRecent application logs:[0m
    echo.
    if exist "logs" (
        echo [36mLast few lines from recent log files:[0m
        for /f %%f in ('dir /b /o-d logs\*.log 2^>nul') do (
            echo.
            echo [33m--- logs\%%f ---[0m
            echo Showing last 10 lines:
            more +1 "logs\%%f" 2>nul
            goto :first_log_only
        )
        :first_log_only
    ) else (
        echo [33mNo logs directory found[0m
    )
) else if "%debug_choice%"=="3" (
    echo [36mInteractive CLI Command Testing[0m
    echo.
    echo Type CLI commands to test (without 'run.bat' prefix)
    echo Examples: status, validate-config, --help
    echo Type 'exit' to return to debug menu
    echo.
    :cli_test_loop
    set /p test_cmd="CLI> "
    if /i "!test_cmd!"=="exit" goto :debug_done
    if "!test_cmd!"=="" goto :cli_test_loop
    
    echo [36mExecuting: venv\Scripts\python.exe cli.py !test_cmd![0m
    if exist "venv\Scripts\python.exe" (
        venv\Scripts\python.exe cli.py !test_cmd!
        echo.
        echo [36mCommand completed with exit code: !errorlevel![0m
    ) else (
        echo [31mERROR: Virtual environment not found[0m
    )
    echo.
    goto :cli_test_loop
) else if "%debug_choice%"=="4" (
    echo [36mGenerating environment dump...[0m
    set dump_file=debug_environment_%date:~10,4%%date:~4,2%%date:~7,2%.txt
    
    (
        echo ProspectAI Environment Debug Dump
        echo Generated: %date% %time%
        echo ================================
        echo.
        echo PYTHON ENVIRONMENT:
        if exist "venv\Scripts\python.exe" (
            venv\Scripts\python.exe --version
            echo.
            echo INSTALLED PACKAGES:
            venv\Scripts\python.exe -m pip list
        ) else (
            echo Virtual environment not found
        )
        echo.
        echo CONFIGURATION STATUS:
        if exist ".env" (
            echo .env file exists
        ) else (
            echo .env file missing
        )
    ) > "!dump_file!"
    
    echo [32mEnvironment dump saved to: !dump_file![0m
) else if "%debug_choice%"=="5" (
    echo [36mNetwork & API Diagnostics[0m
    echo.
    echo [36mTesting network connectivity...[0m
    ping -n 1 api.notion.com >nul 2>&1
    if !errorlevel! equ 0 (
        echo [32mNotion API reachable[0m
    ) else (
        echo [33mNotion API unreachable[0m
    )
) else if "%debug_choice%"=="6" (
    echo [36mCleaning up debug data...[0m
    if exist "debug_environment_*.txt" (
        del debug_environment_*.txt 2>nul
        echo [32mDebug dump files cleared[0m
    ) else (
        echo [33mNo debug dump files found[0m
    )
) else if "%debug_choice%"=="0" (
    goto :menu
) else (
    echo [31mInvalid choice. Please select 0-6.[0m
)

:debug_done
echo.
set /p return="Press Enter to continue..."
goto :debug_mode

:batch_operations
cls
echo.
echo ================================================================================
echo                                BATCH OPERATIONS & AUTOMATION
echo ================================================================================
echo.
echo [1] Scheduled Campaign     - Set up automated campaign runs
echo [2] Batch Email Generation - Generate emails for multiple campaigns
echo [3] Daily Analytics Report - Schedule daily report generation
echo [4] Maintenance Schedule   - Set up automated maintenance tasks
echo [5] Bulk Configuration     - Apply settings to multiple environments
echo [6] Export All Data        - Comprehensive data export
echo.
echo [0] Return to Main Menu
echo.
echo ================================================================================
set /p batch_choice="Select batch operation (0-6): "
echo.

if "%batch_choice%"=="1" (
    echo [36mScheduled Campaign Setup[0m
    echo.
    echo [33mNote: This feature sets up basic scheduled operations[0m
    echo.
    set /p campaign_interval="Enter hours between campaigns (default: 24): "
    if "!campaign_interval!"=="" set campaign_interval=24
    
    set /p company_limit="Enter companies per campaign (default: 10): "
    if "!company_limit!"=="" set company_limit=10
    
    echo.
    echo [36mScheduled campaign would run every !campaign_interval! hours[0m
    echo [36mProcessing !company_limit! companies per run[0m
    echo.
    echo [33mTo implement: Use Windows Task Scheduler or cron jobs[0m
    echo Command: run.bat run-campaign --limit !company_limit!
) else if "%batch_choice%"=="2" (
    echo [36mBatch Email Generation[0m
    echo.
    set /p email_limit="Enter number of emails to generate (default: 50): "
    if "!email_limit!"=="" set email_limit=50
    
    echo [36mGenerating !email_limit! emails in batch...[0m
    if exist "venv\Scripts\python.exe" (
        venv\Scripts\python.exe cli.py generate-emails-recent --limit !email_limit!
        echo [32mBatch email generation completed[0m
    ) else (
        echo [31mVirtual environment not found[0m
    )
) else if "%batch_choice%"=="3" (
    echo [36mDaily Analytics Report[0m
    echo.
    echo [36mGenerating comprehensive daily analytics...[0m
    if exist "venv\Scripts\python.exe" (
        venv\Scripts\python.exe cli.py analytics-report --period daily
        echo [32mDaily analytics report completed[0m
    ) else (
        echo [31mVirtual environment not found[0m
    )
) else if "%batch_choice%"=="4" (
    echo [36mMaintenance Schedule Setup[0m
    echo.
    echo [33mRecommended maintenance tasks:[0m
    echo - Daily: Analytics report generation
    echo - Weekly: System health check
    echo - Monthly: Installation check and updates
    echo - Quarterly: Configuration backup
    echo.
    echo [33mTo implement: Use system scheduler with these commands:[0m
    echo Daily: run.bat analytics-report --period daily
    echo Weekly: run.bat system-health
    echo Monthly: run.bat installation-check
) else if "%batch_choice%"=="5" (
    echo [36mBulk Configuration[0m
    echo.
    echo [33mThis feature would apply configuration changes across environments[0m
    echo Current configuration can be exported via Config Management [21]
) else if "%batch_choice%"=="6" (
    echo [36mExport All Data[0m
    echo.
    echo [36mStarting comprehensive data export...[0m
    if exist "venv\Scripts\python.exe" (
        venv\Scripts\python.exe cli.py status >nul 2>&1
        if !errorlevel! equ 0 (
            echo [32mSystem accessible - export can proceed[0m
            echo [33mNote: Use Notion export features for complete data backup[0m
        ) else (
            echo [33mSystem check failed - verify configuration first[0m
        )
    ) else (
        echo [31mVirtual environment not found[0m
    )
) else if "%batch_choice%"=="0" (
    goto :menu
) else (
    echo [31mInvalid choice. Please select 0-6.[0m
)

echo.
set /p return="Press Enter to continue..."
goto :batch_operations

:system_info
cls
echo.
echo ================================================================================
echo                                  SYSTEM INFORMATION
echo ================================================================================
echo.
echo [36mProspectAI System Status[0m
echo.
echo Python Environment:
if exist "venv\Scripts\python.exe" (
    echo [32mOK - Virtual environment: Active[0m
    venv\Scripts\python.exe --version
) else (
    echo [31mMISSING - Virtual environment: Not found[0m
)

echo.
echo Configuration Status:
if exist ".env" (
    echo [32mOK - Configuration file: Found[0m
) else (
    echo [31mMISSING - Configuration file: Not found[0m
)

echo.
echo Available CLI Commands:
venv\Scripts\python.exe cli.py --help

echo.
echo [36mQuick Validation:[0m
venv\Scripts\python.exe cli.py validate-config

echo.
set /p return="Press Enter to return to main menu..."
goto :menu

:help
cls
echo.
echo ================================================================================
echo                                PROSPECTAI COMMAND REFERENCE
echo ================================================================================
echo.
echo [32m>> QUICK START COMMANDS[0m
echo   quick-start               - Complete setup + first campaign (5 companies)
echo   validate-config           - Check API configuration and connections
echo   setup-dashboard           - Create/update Notion dashboard
echo.
echo [33m>> MAIN WORKFLOW COMMANDS[0m
echo   run-campaign              - Full workflow: discovery + emails + analytics
echo   discover                  - Discovery only (find companies and prospects)
echo   generate-emails-recent    - Generate emails for recent prospects
echo   send-emails-recent        - Send the most recent generated emails
echo.
echo [36m>> MONITORING COMMANDS[0m
echo   status                    - Show workflow status and statistics
echo   campaign-status           - Show current campaign progress
echo   analytics-report          - View analytics and performance stats
echo   email-queue               - Manage email queue and delivery status
echo.
echo [35m>> CONFIGURATION COMMANDS[0m
echo   configure-ai              - Configure AI providers (OpenAI, Anthropic, etc.)
echo   profile-setup             - Setup sender profile for personalization
echo   init-config               - Initialize configuration file with defaults
echo.
echo [37m>> ADVANCED COMMANDS[0m
echo   process-company           - Process a specific company by name
echo   send-emails               - Send emails to specific prospects
echo   analyze-products          - Run AI analysis on company products
echo   daily-summary             - Create daily analytics summary
echo.
echo [33m>> USAGE EXAMPLES[0m
echo   run.bat                   - Show interactive menu (current mode)
echo   run.bat quick-start       - Run quick start campaign
echo   run.bat run-campaign --limit 5
echo   run.bat discover --limit 20 --campaign-name "My Campaign"
echo   run.bat generate-emails-recent --limit 10
echo   run.bat send-emails-recent --limit 5 --delay 60
echo   run.bat process-company "TechCorp" --domain "techcorp.com"
echo.
echo [36m>> PARAMETER OPTIONS[0m
echo   --limit N                 - Limit number of companies/prospects to process
echo   --campaign-name "Name"    - Set custom campaign name for tracking
echo   --delay N                 - Set delay between email sends (seconds)
echo   --dry-run                 - Run in simulation mode without making changes
echo   --verbose                 - Enable detailed logging output
echo.
echo [33m>> GETTING HELP[0m
echo   run.bat [command] --help  - Get detailed help for specific command
echo   Online Documentation:     - Check GitHub repository for full docs
echo   Configuration Guide:      - See README.md for API key setup
echo.
echo ================================================================================
set /p return="Press Enter to return to main menu..."
goto :menu
