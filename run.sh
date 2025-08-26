#!/bin/bash

if [ ! -f "venv/bin/python" ]; then
    echo "Virtual environment not found. Please run ./install.sh first."
    read -p "Press Enter to exit..."
    exit 1
fi

if [ $# -eq 0 ]; then
    show_menu
else
    venv/bin/python cli.py "$@"
    exit_code=$?
    
    if [ $exit_code -ne 0 ]; then
        echo ""
        echo "Command failed with exit code $exit_code"
        read -p "Press Enter to continue..."
    fi
    
    exit $exit_code
fi

show_menu() {
    while true; do
        clear
        echo ""
        echo "================================================================================"
        echo "             ProspectAI - Intelligent Job Automation System v2.0"
        echo "================================================================================"
        echo ""
        echo "    \033[32mMAIN MENU\033[0m"
        echo ""
        echo "[1] Quick Start         - Complete setup + run first campaign"
        echo "[2] Guided Setup        - Step-by-step configuration wizard"
        echo "[3] Run Campaign        - Full workflow: discovery + emails + analytics"
        echo "[4] Discovery Only      - Find companies and prospects (advanced)"
        echo "[5] Email Generation    - Create personalized emails for recent prospects"
        echo "[6] Send Emails         - Send the most recent generated emails"
        echo ""
        echo "[7] Status Dashboard    - Show current workflow status and statistics"
        echo "[8] Validate Config     - Check your API configuration and connections"
        echo "[9] Setup Dashboard     - Create/update Notion dashboard"
        echo ""
        echo "\033[36m[A] Advanced Options\033[0m    - Custom campaigns, specific company processing"
        echo "\033[33m[M] Maintenance Menu\033[0m    - System health, repairs, configuration management"
        echo "\033[35m[H] Help and Info\033[0m       - Commands, system info, documentation"
        echo ""
        echo "\033[31m[0] Exit\033[0m"
        echo ""
        echo "================================================================================"
        read -p "Enter your choice (0-9, A, M, H): " choice
        echo ""
        
        case $choice in
            1)
                echo "\033[32mRunning Quick Start Campaign...\033[0m"
                echo "This will discover 5 companies, find prospects, and generate sample emails"
                venv/bin/python cli.py quick-start --limit 5
                echo ""
                read -p "Press Enter to continue..."
                ;;
            2)
                echo "\033[33mStarting Guided Setup Wizard...\033[0m"
                echo "This will help you configure your API keys and settings"
                venv/bin/python cli.py validate-config
                if [ $? -eq 0 ]; then
                    echo "Configuration looks good! Setting up dashboard..."
                    venv/bin/python cli.py setup-dashboard
                fi
                echo ""
                read -p "Press Enter to continue..."
                ;;
            3)
                echo "\033[33mRunning Full Campaign Workflow...\033[0m"
                read -p "Enter number of companies to process (default 10): " limit
                if [ -z "$limit" ]; then limit=10; fi
                echo "Processing $limit companies with full workflow..."
                venv/bin/python cli.py run-campaign --limit $limit
                echo ""
                read -p "Press Enter to continue..."
                ;;
            4)
                echo "\033[36mRunning Discovery Pipeline...\033[0m"
                read -p "Enter number of companies to discover (default 20): " limit
                if [ -z "$limit" ]; then limit=20; fi
                echo "Discovering $limit companies and extracting team information..."
                venv/bin/python cli.py discover --limit $limit
                echo ""
                read -p "Press Enter to continue..."
                ;;
            5)
                echo "\033[35mGenerating Personalized Emails...\033[0m"
                read -p "Enter number of emails to generate (default 10): " limit
                if [ -z "$limit" ]; then limit=10; fi
                echo "Generating $limit personalized emails for recent prospects..."
                venv/bin/python cli.py generate-emails-recent --limit $limit
                echo ""
                read -p "Press Enter to continue..."
                ;;
            6)
                echo "\033[35mSending Recent Emails...\033[0m"
                read -p "Enter number of emails to send (default 5): " limit
                if [ -z "$limit" ]; then limit=5; fi
                read -p "Enter delay between emails in seconds (default 30): " delay
                if [ -z "$delay" ]; then delay=30; fi
                echo "Sending $limit emails with $delay second delay..."
                venv/bin/python cli.py send-emails-recent --limit $limit --delay $delay
                echo ""
                read -p "Press Enter to continue..."
                ;;
            7)
                echo "\033[36mChecking System Status...\033[0m"
                venv/bin/python cli.py status
                echo ""
                read -p "Press Enter to continue..."
                ;;
            8)
                echo "\033[36mChecking Campaign Progress...\033[0m"
                venv/bin/python cli.py campaign-status
                echo ""
                read -p "Press Enter to continue..."
                ;;
            9)
                echo "\033[36mGenerating Analytics Report...\033[0m"
                echo "[1] Daily Report"
                echo "[2] Weekly Report"
                echo "[3] Monthly Report"
                read -p "Select report period (1-3): " period_choice
                case $period_choice in
                    1) period="daily" ;;
                    2) period="weekly" ;;
                    3) period="monthly" ;;
                    *) period="daily" ;;
                esac
                venv/bin/python cli.py analytics-report --period $period
                echo ""
                read -p "Press Enter to continue..."
                ;;
            10)
                echo "\033[36mManaging Email Queue...\033[0m"
                venv/bin/python cli.py email-queue
                echo ""
                read -p "Press Enter to continue..."
                ;;
            11)
                echo "\033[35mValidating Configuration...\033[0m"
                echo "Checking API keys and connections..."
                venv/bin/python cli.py validate-config
                echo ""
                read -p "Press Enter to continue..."
                ;;
            12)
                echo "\033[35mSetting up Notion Dashboard...\033[0m"
                echo "Creating databases and dashboard structure..."
                venv/bin/python cli.py setup-dashboard
                echo ""
                read -p "Press Enter to continue..."
                ;;
            13)
                echo "\033[35mConfiguring Sender Profile...\033[0m"
                venv/bin/python cli.py profile-setup
                echo ""
                read -p "Press Enter to continue..."
                ;;
            14)
                echo "\033[35mConfiguring AI Providers...\033[0m"
                venv/bin/python cli.py configure-ai
                echo ""
                read -p "Press Enter to continue..."
                ;;
            15)
                custom_campaign
                ;;
            16)
                process_company
                ;;
            17)
                show_help
                ;;
            18)
                system_info
                ;;
            19)
                installation_check
                ;;
            20)
                repair_installation
                ;;
            21)
                config_management
                ;;
            22)
                system_health
                ;;
            23)
                update_check
                ;;
            24)
                debug_mode
                ;;
            25)
                batch_operations
                ;;
            0)
                echo "\033[32mGoodbye! Thanks for using ProspectAI!\033[0m"
                exit 0
                ;;
            *)
                echo "\033[31mInvalid choice. Please enter a number between 0 and 25.\033[0m"
                echo ""
                read -p "Press Enter to continue..."
                ;;
        esac
    done
}

custom_campaign() {
    clear
    echo ""
    echo "================================================================================"
    echo "                          CUSTOM CAMPAIGN CONFIGURATION"
    echo "================================================================================"
    echo ""
    read -p "Enter campaign name (default: Custom Campaign): " campaign_name
    if [ -z "$campaign_name" ]; then campaign_name="Custom Campaign"; fi

    read -p "Enter number of companies to process (default: 10): " company_limit
    if [ -z "$company_limit" ]; then company_limit=10; fi

    echo ""
    echo "Campaign Options:"
    echo "[1] Discovery only"
    echo "[2] Discovery + Email Generation"
    echo "[3] Full workflow (Discovery + Emails + Sending)"
    read -p "Select workflow type (1-3): " workflow_choice

    echo ""
    echo "\033[33mRunning Custom Campaign: $campaign_name\033[0m"
    echo "Companies to process: $company_limit"

    case $workflow_choice in
        1)
            echo "Workflow: Discovery only"
            venv/bin/python cli.py discover --limit $company_limit --campaign-name "$campaign_name"
            ;;
        2)
            echo "Workflow: Discovery + Email Generation"
            venv/bin/python cli.py run-campaign --limit $company_limit --campaign-name "$campaign_name" --no-send
            ;;
        *)
            echo "Workflow: Full workflow with email sending"
            read -p "Enter delay between emails (seconds, default: 60): " email_delay
            if [ -z "$email_delay" ]; then email_delay=60; fi
            venv/bin/python cli.py run-campaign --limit $company_limit --campaign-name "$campaign_name" --delay $email_delay
            ;;
    esac

    echo ""
    echo "\033[32mCustom campaign completed!\033[0m"
    echo ""
    read -p "Press Enter to return to main menu..."
}

process_company() {
    clear
    echo ""
    echo "================================================================================"
    echo "                            PROCESS SPECIFIC COMPANY"
    echo "================================================================================"
    echo ""
    read -p "Enter company name to process: " company_name
    if [ -z "$company_name" ]; then
        echo "\033[31mCompany name cannot be empty!\033[0m"
        read -p "Press Enter to continue..."
        return
    fi

    read -p "Enter company domain (optional): " company_domain

    echo ""
    echo "\033[33mProcessing company: $company_name\033[0m"
    if [ -n "$company_domain" ]; then
        echo "Domain: $company_domain"
        venv/bin/python cli.py process-company "$company_name" --domain "$company_domain"
    else
        venv/bin/python cli.py process-company "$company_name"
    fi

    echo ""
    echo "\033[32mCompany processing completed!\033[0m"
    echo ""
    read -p "Press Enter to return to main menu..."
}

installation_check() {
    clear
    echo ""
    echo "================================================================================"
    echo "                          INSTALLATION STATUS DIAGNOSTICS"
    echo "================================================================================"
    echo ""
    echo "\033[96mRunning comprehensive installation check...\033[0m"
    echo ""

    echo "\033[36m1. Python Installation Check\033[0m"
    echo "----------------------------------------"
    if [ -f "venv/bin/python" ]; then
        echo "\033[32mOK - Virtual environment found\033[0m"
        echo "Path: $(pwd)/venv/bin/python"
        echo "Version: $(venv/bin/python --version)"
        
        echo ""
        echo "\033[36mChecking Python packages...\033[0m"
        if venv/bin/python -m pip list --local 2>/dev/null | grep -i "click\|rich" >/dev/null; then
            echo "\033[32mOK - Core packages installed\033[0m"
        else
            echo "\033[33mWARNING - Some core packages may be missing\033[0m"
        fi
    else
        echo "\033[31mFAILED - Virtual environment not found\033[0m"
        echo "Expected path: $(pwd)/venv/bin/python"
        echo "\033[33mRecovery: Run ./install.sh to create virtual environment\033[0m"
    fi

    echo ""
    echo "\033[36m2. Configuration Check\033[0m"
    echo "----------------------------------------"
    if [ -f ".env" ]; then
        echo "\033[32mOK - Configuration file found\033[0m"
        echo "Path: $(pwd)/.env"
        
        echo ""
        echo "\033[36mChecking required API keys...\033[0m"
        if grep -q "NOTION_TOKEN" .env 2>/dev/null; then
            echo "\033[32mOK - Notion token configured\033[0m"
        else
            echo "\033[31mMISSING - Notion token not found\033[0m"
        fi
        
        if grep -q "HUNTER_API_KEY" .env 2>/dev/null; then
            echo "\033[32mOK - Hunter API key configured\033[0m"
        else
            echo "\033[31mMISSING - Hunter API key not found\033[0m"
        fi
    else
        echo "\033[31mFAILED - Configuration file not found\033[0m"
        echo "Expected path: $(pwd)/.env"
        echo "\033[33mRecovery: Run setup or validate-config command\033[0m"
    fi

    echo ""
    echo "\033[36m3. Dependencies & CLI Check\033[0m"
    echo "----------------------------------------"
    if [ -f "requirements.txt" ]; then
        echo "\033[32mOK - Requirements file found\033[0m"
    else
        echo "\033[31mFAILED - Requirements file not found\033[0m"
    fi

    if [ -f "venv/bin/python" ]; then
        if [ -f "cli.py" ]; then
            echo "\033[32mOK - CLI script found\033[0m"
            echo ""
            echo "\033[36mTesting CLI help command...\033[0m"
            if venv/bin/python cli.py --help >/dev/null 2>&1; then
                echo "\033[32mOK - CLI is functional\033[0m"
            else
                echo "\033[31mFAILED - CLI command failed\033[0m"
            fi
        else
            echo "\033[31mFAILED - CLI script not found\033[0m"
        fi
    else
        echo "\033[33mSKIPPED - Cannot test CLI without virtual environment\033[0m"
    fi

    echo ""
    echo "================================================================================"
    echo "\033[96mInstallation Check Complete\033[0m"
    echo ""
    echo "\033[36mNext Steps:\033[0m"
    echo "- If any components failed, use option [20] Repair Installation"
    echo "- Run validate-config to test API connectivity"
    echo "================================================================================"
    echo ""
    read -p "Press Enter to return to main menu..."
}

repair_installation() {
    clear
    echo ""
    echo "================================================================================"
    echo "                        AUTOMATED INSTALLATION REPAIR"
    echo "================================================================================"
    echo ""
    echo "\033[96mThis will attempt to fix common installation issues...\033[0m"
    echo ""

    echo "\033[36mStep 1: Checking virtual environment...\033[0m"
    if [ ! -f "venv/bin/python" ]; then
        echo "\033[33mVirtual environment missing. Attempting to recreate...\033[0m"
        if python3 -m venv venv; then
            echo "\033[32mOK - Virtual environment created\033[0m"
        else
            echo "\033[31mFAILED - Could not create virtual environment\033[0m"
            echo "Please run ./install.sh manually"
            read -p "Press Enter to return to main menu..."
            return
        fi
    else
        echo "\033[32mOK - Virtual environment exists\033[0m"
    fi

    echo ""
    echo "\033[36mStep 2: Updating pip and installing/upgrading dependencies...\033[0m"
    venv/bin/python -m pip install --upgrade pip
    if [ -f "requirements.txt" ]; then
        echo "Installing requirements..."
        if venv/bin/python -m pip install -r requirements.txt --upgrade; then
            echo "\033[32mOK - Dependencies installed/updated\033[0m"
        else
            echo "\033[33mWARNING - Some dependencies may have failed to install\033[0m"
        fi
    else
        echo "\033[33mWARNING - requirements.txt not found\033[0m"
    fi

    echo ""
    echo "\033[36mStep 3: Checking configuration...\033[0m"
    if [ ! -f ".env" ]; then
        echo "\033[33mConfiguration file missing. Creating template...\033[0m"
        cat > .env << EOF
# ProspectAI Configuration File
# Required API Keys:
NOTION_TOKEN=
HUNTER_API_KEY=
OPENAI_API_KEY=

# Optional Email Configuration:
RESEND_API_KEY=
SENDER_EMAIL=
SENDER_NAME=
EOF
        echo "\033[33mCreated .env template. Please add your API keys.\033[0m"
    else
        echo "\033[32mOK - Configuration file exists\033[0m"
    fi

    echo ""
    echo "\033[36mStep 4: Testing CLI functionality...\033[0m"
    if venv/bin/python cli.py --help >/dev/null 2>&1; then
        echo "\033[32mOK - CLI is working\033[0m"
    else
        echo "\033[33mWARNING - CLI test failed. May need configuration.\033[0m"
    fi

    echo ""
    echo "================================================================================"
    echo "\033[96mRepair Process Complete\033[0m"
    echo ""
    echo "\033[36mRecommended Next Steps:\033[0m"
    echo "1. Run Installation Check [19] to verify repairs"
    echo "2. Configure API keys if .env was recreated"
    echo "3. Run validate-config to test connections"
    echo "4. Use setup-dashboard to initialize workspace"
    echo "================================================================================"
    echo ""
    read -p "Press Enter to return to main menu..."
}

show_help() {
    clear
    echo ""
    echo "================================================================================"
    echo "                            PROSPECTAI COMMAND REFERENCE"
    echo "================================================================================"
    echo ""
    echo "\033[32m>> QUICK START COMMANDS\033[0m"
    echo "   quick-start              - Complete setup + first campaign (5 companies)"
    echo "   validate-config          - Check API configuration and connections"
    echo "   setup-dashboard          - Create/update Notion dashboard"
    echo ""
    echo "\033[33m>> MAIN WORKFLOW COMMANDS\033[0m"
    echo "   run-campaign             - Full workflow: discovery + emails + analytics"
    echo "   discover                 - Discovery only (find companies and prospects)"
    echo "   generate-emails-recent   - Generate emails for recent prospects"
    echo "   send-emails-recent       - Send the most recent generated emails"
    echo ""
    echo "\033[36m>> MONITORING COMMANDS\033[0m"
    echo "   status                   - Show workflow status and statistics"
    echo "   campaign-status          - Show current campaign progress"
    echo "   analytics-report         - View analytics and performance stats"
    echo "   email-queue             - Manage email queue and delivery status"
    echo ""
    echo "\033[35m>> CONFIGURATION COMMANDS\033[0m"
    echo "   configure-ai             - Configure AI providers (OpenAI, Anthropic, etc.)"
    echo "   profile-setup           - Setup sender profile for personalization"
    echo ""
    echo "\033[37m>> ADVANCED COMMANDS\033[0m"
    echo "   process-company          - Process a specific company by name"
    echo "   send-emails             - Send emails to specific prospects"
    echo "   analyze-products         - Run AI analysis on company products"
    echo "   daily-summary           - Create daily analytics summary"
    echo ""
    echo "\033[33m>> USAGE EXAMPLES\033[0m"
    echo "   ./run.sh                  - Show interactive menu (current mode)"
    echo "   ./run.sh quick-start      - Run quick start campaign"
    echo "   ./run.sh run-campaign --limit 5"
    echo "   ./run.sh discover --limit 20 --campaign-name \"My Campaign\""
    echo "   ./run.sh generate-emails-recent --limit 10"
    echo "   ./run.sh send-emails-recent --limit 5 --delay 60"
    echo "   ./run.sh process-company \"TechCorp\" --domain \"techcorp.com\""
    echo ""
    echo "\033[36m>> PARAMETER OPTIONS\033[0m"
    echo "   --limit N                - Limit number of companies/prospects to process"
    echo "   --campaign-name \"Name\"    - Set custom campaign name for tracking"
    echo "   --delay N                - Set delay between email sends (seconds)"
    echo "   --dry-run                - Run in simulation mode without making changes"
    echo "   --verbose                - Enable detailed logging output"
    echo ""
    echo "\033[33m>> GETTING HELP\033[0m"
    echo "   ./run.sh [command] --help - Get detailed help for specific command"
    echo "   Online Documentation:    - Check GitHub repository for full docs"
    echo "   Configuration Guide:     - See README.md for API key setup"
    echo ""
    echo "================================================================================"
    read -p "Press Enter to return to main menu..."
}

system_info() {
    clear
    echo ""
    echo "================================================================================"
    echo "                              SYSTEM INFORMATION"
    echo "================================================================================"
    echo ""
    echo "\033[36mProspectAI System Status\033[0m"
    echo ""
    echo "Python Environment:"
    if [ -f "venv/bin/python" ]; then
        echo "\033[32mOK - Virtual environment: Active\033[0m"
        venv/bin/python --version
    else
        echo "\033[31mMISSING - Virtual environment: Not found\033[0m"
    fi

    echo ""
    echo "Configuration Status:"
    if [ -f ".env" ]; then
        echo "\033[32mOK - Configuration file: Found\033[0m"
    else
        echo "\033[31mMISSING - Configuration file: Not found\033[0m"
    fi

    echo ""
    echo "Available CLI Commands:"
    if [ -f "venv/bin/python" ]; then
        venv/bin/python cli.py --help
    else
        echo "Cannot display commands - virtual environment not found"
    fi

    echo ""
    echo "\033[36mQuick Validation:\033[0m"
    if [ -f "venv/bin/python" ]; then
        venv/bin/python cli.py validate-config
    else
        echo "Cannot validate - virtual environment not found"
    fi

    echo ""
    read -p "Press Enter to return to main menu..."
}

config_management() {
    clear
    echo ""
    echo "================================================================================"
    echo "                           CONFIGURATION MANAGEMENT"
    echo "================================================================================"
    echo ""
    echo "[1] Backup Configuration    - Create backup of current .env file"
    echo "[2] Restore Configuration   - Restore from backup file"
    echo "[3] View Configuration      - Display current configuration (masked)"
    echo "[4] Reset Configuration     - Create fresh .env template"
    echo "[5] Export Configuration    - Export config template for transfer"
    echo "[6] Configuration History   - View backup history"
    echo ""
    echo "[0] Return to Main Menu"
    echo ""
    echo "================================================================================"
    read -p "Select configuration option (0-6): " config_choice
    echo ""

    case $config_choice in
        1)
            echo "\033[36mCreating configuration backup...\033[0m"
            if [ -f ".env" ]; then
                backup_name=".env.backup.$(date +%Y%m%d_%H%M%S)"
                if cp ".env" "$backup_name"; then
                    echo "\033[32mOK - Backup created: $backup_name\033[0m"
                else
                    echo "\033[31mFAILED - Could not create backup\033[0m"
                fi
            else
                echo "\033[33mWARNING - No .env file found to backup\033[0m"
            fi
            ;;
        2)
            echo "\033[36mAvailable backup files:\033[0m"
            ls .env.backup.* 2>/dev/null
            if [ $? -ne 0 ]; then
                echo "\033[33mNo backup files found\033[0m"
            else
                echo ""
                read -p "Enter backup filename to restore: " backup_file
                if [ -f "$backup_file" ]; then
                    if cp "$backup_file" ".env"; then
                        echo "\033[32mOK - Configuration restored from $backup_file\033[0m"
                    else
                        echo "\033[31mFAILED - Could not restore configuration\033[0m"
                    fi
                else
                    echo "\033[31mFAILED - Backup file not found\033[0m"
                fi
            fi
            ;;
        3)
            echo "\033[36mCurrent configuration (API keys masked):\033[0m"
            if [ -f ".env" ]; then
                echo ""
                while IFS='=' read -r key value; do
                    if [ -n "$key" ] && [[ ! "$key" =~ ^# ]]; then
                        if [ -n "$value" ]; then
                            echo "$key=***MASKED***"
                        else
                            echo "$key="
                        fi
                    else
                        echo "$key"
                    fi
                done < .env
            else
                echo "\033[33mNo .env file found\033[0m"
            fi
            ;;
        4)
            echo "\033[36mCreating fresh configuration template...\033[0m"
            if [ -f ".env" ]; then
                echo "\033[33mExisting .env file will be overwritten!\033[0m"
                read -p "Continue? (y/N): " confirm
                if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
                    echo "Operation cancelled."
                    read -p "Press Enter to continue..."
                    return
                fi
            fi
            cat > .env << EOF
# ProspectAI Configuration File
# Generated on $(date)

# Required API Keys:
NOTION_TOKEN=
HUNTER_API_KEY=
OPENAI_API_KEY=

# Optional Email Configuration:
RESEND_API_KEY=
SENDER_EMAIL=
SENDER_NAME=

# Optional AI Provider Configuration:
ANTHROPIC_API_KEY=
GOOGLE_API_KEY=
DEEPSEEK_API_KEY=
EOF
            echo "\033[32mOK - Fresh configuration template created\033[0m"
            ;;
        5)
            echo "\033[36mExporting configuration template...\033[0m"
            if [ -f ".env" ]; then
                {
                    echo "# ProspectAI Configuration Template"
                    echo "# Exported on $(date)"
                    echo ""
                    while IFS='=' read -r key value; do
                        if [ -n "$key" ] && [[ ! "$key" =~ ^# ]]; then
                            echo "$key="
                        else
                            echo "$key"
                        fi
                    done < .env
                } > .env.template
                echo "\033[32mOK - Configuration template exported to .env.template\033[0m"
            else
                echo "\033[33mNo .env file found to export\033[0m"
            fi
            ;;
        6)
            echo "\033[36mConfiguration backup history:\033[0m"
            echo ""
            ls -lt .env.backup.* 2>/dev/null
            if [ $? -ne 0 ]; then
                echo "\033[33mNo backup files found\033[0m"
            fi
            ;;
        0)
            return
            ;;
        *)
            echo "\033[31mInvalid choice. Please select 0-6.\033[0m"
            ;;
    esac

    echo ""
    read -p "Press Enter to continue..."
    config_management
}

system_health() {
    clear
    echo ""
    echo "================================================================================"
    echo "                        SYSTEM HEALTH & PERFORMANCE MONITORING"
    echo "================================================================================"
    echo ""
    echo "\033[96mChecking system health and performance...\033[0m"
    echo ""

    echo "\033[36m1. Virtual Environment Health\033[0m"
    echo "----------------------------------------"
    if [ -f "venv/bin/python" ]; then
        echo "\033[32mOK - Virtual environment active\033[0m"
        
        echo ""
        echo "\033[36mPython environment details:\033[0m"
        venv/bin/python -c "import sys; print(f'Python: {sys.version.split()[0]}'); print(f'Platform: {sys.platform}')"
        
        echo ""
        echo "\033[36mPackage health check:\033[0m"
        if venv/bin/python -m pip check >/dev/null 2>&1; then
            echo "\033[32mOK - No dependency conflicts detected\033[0m"
        else
            echo "\033[33mWARNING - Some dependency conflicts detected\033[0m"
        fi
    else
        echo "\033[31mFAILED - Virtual environment not found\033[0m"
    fi

    echo ""
    echo "\033[36m2. Disk Space Usage\033[0m"
    echo "----------------------------------------"
    echo "Project directory size:"
    du -sh . 2>/dev/null || echo "Could not determine directory size"

    if [ -d "venv" ]; then
        echo ""
        echo "Virtual environment size:"
        du -sh venv 2>/dev/null || echo "Could not determine venv size"
    fi

    echo ""
    echo "Available disk space:"
    df -h . 2>/dev/null || echo "Could not determine disk space"

    echo ""
    echo "\033[36m3. Network Connectivity\033[0m"
    echo "----------------------------------------"
    echo "Testing API endpoints..."

    echo "\033[36mTesting api.notion.com...\033[0m"
    if ping -c 1 api.notion.com >/dev/null 2>&1; then
        echo "\033[32mOK - Notion API reachable\033[0m"
    else
        echo "\033[33mWARNING - Notion API unreachable\033[0m"
    fi

    echo ""
    echo "\033[36m4. Configuration Health\033[0m"
    echo "----------------------------------------"
    if [ -f ".env" ]; then
        echo "\033[32mOK - Configuration file present\033[0m"
        
        echo ""
        echo "\033[36mRunning configuration validation...\033[0m"
        if [ -f "venv/bin/python" ]; then
            if venv/bin/python cli.py validate-config >/dev/null 2>&1; then
                echo "\033[32mOK - Configuration validation passed\033[0m"
            else
                echo "\033[33mWARNING - Configuration validation failed\033[0m"
            fi
        else
            echo "\033[33mSKIPPED - No virtual environment to test with\033[0m"
        fi
    else
        echo "\033[31mFAILED - Configuration file missing\033[0m"
    fi

    echo ""
    echo "================================================================================"
    echo "\033[96mSystem Health Check Complete\033[0m"
    echo ""
    echo "\033[36mRecommendations:\033[0m"
    echo "- Monitor virtual environment for package conflicts"
    echo "- Ensure adequate disk space for operation"
    echo "- Check network connectivity if API calls fail"
    echo "- Validate configuration regularly"
    echo "================================================================================"
    echo ""
    read -p "Press Enter to return to main menu..."
}

update_check() {
    clear
    echo ""
    echo "================================================================================"
    echo "                          UPDATE CHECK & MAINTENANCE"
    echo "================================================================================"
    echo ""
    echo "\033[96mChecking for updates and maintenance notifications...\033[0m"
    echo ""

    echo "\033[36m1. Python Package Updates\033[0m"
    echo "----------------------------------------"
    if [ -f "venv/bin/python" ]; then
        echo "\033[36mChecking for outdated packages...\033[0m"
        venv/bin/python -m pip list --outdated 2>/dev/null
        if [ $? -eq 0 ]; then
            echo ""
            echo "\033[36mTo update packages, use: venv/bin/python -m pip install --upgrade [package]\033[0m"
        else
            echo "\033[32mAll packages appear to be up to date\033[0m"
        fi
    else
        echo "\033[33mSKIPPED - No virtual environment found\033[0m"
    fi

    echo ""
    echo "\033[36m2. Configuration Status\033[0m"
    echo "----------------------------------------"
    if [ -f ".env" ]; then
        echo "\033[32mConfiguration file present\033[0m"
        echo ""
        echo "\033[36mChecking configuration validation...\033[0m"
        if [ -f "venv/bin/python" ]; then
            if venv/bin/python cli.py validate-config >/dev/null 2>&1; then
                echo "\033[32mConfiguration validation passed\033[0m"
            else
                echo "\033[33mConfiguration validation failed - may need updates\033[0m"
            fi
        fi
    else
        echo "\033[33mNo configuration file found\033[0m"
    fi

    echo ""
    echo "\033[36m3. Repository Status\033[0m"
    echo "----------------------------------------"
    echo "\033[36mChecking git status...\033[0m"
    if git status >/dev/null 2>&1; then
        echo "\033[32mGit repository detected\033[0m"
    else
        echo "\033[33mNot a git repository or git not available\033[0m"
    fi

    echo ""
    echo "\033[36m4. Maintenance Recommendations\033[0m"
    echo "----------------------------------------"
    echo "\033[36mBased on system analysis:\033[0m"
    echo ""
    echo "- Run installation check [19] monthly"
    echo "- Backup configuration [21] before major changes"
    echo "- Monitor system health [22] regularly"
    echo "- Update dependencies periodically"
    echo "- Review API key rotation schedule"

    echo ""
    echo "================================================================================"
    echo "\033[96mUpdate Check Complete\033[0m"
    echo "================================================================================"
    echo ""
    read -p "Press Enter to return to main menu..."
}

debug_mode() {
    clear
    echo ""
    echo "================================================================================"
    echo "                        ADVANCED DEBUGGING & LOGGING TOOLS"
    echo "================================================================================"
    echo ""
    echo "[1] Enable Debug Logging    - Turn on verbose logging for next operation"
    echo "[2] View Recent Logs        - Display recent application logs"
    echo "[3] Test CLI Commands       - Interactive CLI command testing"
    echo "[4] Environment Dump        - Export complete environment information"
    echo "[5] Network Diagnostics     - Advanced network and API testing"
    echo "[6] Clear Debug Data        - Clean up debug files and logs"
    echo ""
    echo "[0] Return to Main Menu"
    echo ""
    echo "================================================================================"
    read -p "Select debug option (0-6): " debug_choice
    echo ""

    case $debug_choice in
        1)
            echo "\033[36mEnabling debug logging for next operation...\033[0m"
            export DEBUG_MODE=1
            echo "\033[32mDEBUG MODE ENABLED\033[0m"
            echo ""
            echo "Debug logging will be active for the next CLI command you run."
            echo "To disable, restart the script."
            ;;
        2)
            echo "\033[36mRecent application logs:\033[0m"
            echo ""
            if [ -d "logs" ]; then
                echo "\033[36mLast few lines from recent log files:\033[0m"
                for logfile in $(ls -t logs/*.log 2>/dev/null | head -1); do
                    if [ -f "$logfile" ]; then
                        echo ""
                        echo "\033[33m--- $logfile ---\033[0m"
                        tail -10 "$logfile" 2>/dev/null
                        break
                    fi
                done
            else
                echo "\033[33mNo logs directory found\033[0m"
            fi
            ;;
        3)
            echo "\033[36mInteractive CLI Command Testing\033[0m"
            echo ""
            echo "Type CLI commands to test (without './run.sh' prefix)"
            echo "Examples: status, validate-config, --help"
            echo "Type 'exit' to return to debug menu"
            echo ""
            while true; do
                read -p "CLI> " test_cmd
                if [ "$test_cmd" = "exit" ]; then
                    break
                fi
                if [ -n "$test_cmd" ]; then
                    echo "\033[36mExecuting: venv/bin/python cli.py $test_cmd\033[0m"
                    if [ -f "venv/bin/python" ]; then
                        venv/bin/python cli.py $test_cmd
                        echo ""
                        echo "\033[36mCommand completed with exit code: $?\033[0m"
                    else
                        echo "\033[31mERROR: Virtual environment not found\033[0m"
                    fi
                    echo ""
                fi
            done
            ;;
        4)
            echo "\033[36mGenerating environment dump...\033[0m"
            dump_file="debug_environment_$(date +%Y%m%d_%H%M%S).txt"
            
            {
                echo "ProspectAI Environment Debug Dump"
                echo "Generated: $(date)"
                echo "================================"
                echo ""
                echo "PYTHON ENVIRONMENT:"
                if [ -f "venv/bin/python" ]; then
                    venv/bin/python --version
                    echo ""
                    echo "INSTALLED PACKAGES:"
                    venv/bin/python -m pip list
                else
                    echo "Virtual environment not found"
                fi
                echo ""
                echo "CONFIGURATION STATUS:"
                if [ -f ".env" ]; then
                    echo ".env file exists"
                else
                    echo ".env file missing"
                fi
            } > "$dump_file"
            
            echo "\033[32mEnvironment dump saved to: $dump_file\033[0m"
            ;;
        5)
            echo "\033[36mNetwork & API Diagnostics\033[0m"
            echo ""
            echo "\033[36mTesting network connectivity...\033[0m"
            if ping -c 1 api.notion.com >/dev/null 2>&1; then
                echo "\033[32mNotion API reachable\033[0m"
            else
                echo "\033[33mNotion API unreachable\033[0m"
            fi
            ;;
        6)
            echo "\033[36mCleaning up debug data...\033[0m"
            if ls debug_environment_*.txt >/dev/null 2>&1; then
                rm debug_environment_*.txt
                echo "\033[32mDebug dump files cleared\033[0m"
            else
                echo "\033[33mNo debug dump files found\033[0m"
            fi
            ;;
        0)
            return
            ;;
        *)
            echo "\033[31mInvalid choice. Please select 0-6.\033[0m"
            ;;
    esac

    echo ""
    read -p "Press Enter to continue..."
    debug_mode
}

batch_operations() {
    clear
    echo ""
    echo "================================================================================"
    echo "                        BATCH OPERATIONS & AUTOMATION"
    echo "================================================================================"
    echo ""
    echo "[1] Scheduled Campaign     - Set up automated campaign runs"
    echo "[2] Batch Email Generation - Generate emails for multiple campaigns"
    echo "[3] Daily Analytics Report - Schedule daily report generation"
    echo "[4] Maintenance Schedule   - Set up automated maintenance tasks"
    echo "[5] Bulk Configuration     - Apply settings to multiple environments"
    echo "[6] Export All Data        - Comprehensive data export"
    echo ""
    echo "[0] Return to Main Menu"
    echo ""
    echo "================================================================================"
    read -p "Select batch operation (0-6): " batch_choice
    echo ""

    case $batch_choice in
        1)
            echo "\033[36mScheduled Campaign Setup\033[0m"
            echo ""
            echo "\033[33mNote: This feature sets up basic scheduled operations\033[0m"
            echo ""
            read -p "Enter hours between campaigns (default: 24): " campaign_interval
            if [ -z "$campaign_interval" ]; then campaign_interval=24; fi
            
            read -p "Enter companies per campaign (default: 10): " company_limit
            if [ -z "$company_limit" ]; then company_limit=10; fi
            
            echo ""
            echo "\033[36mScheduled campaign would run every $campaign_interval hours\033[0m"
            echo "\033[36mProcessing $company_limit companies per run\033[0m"
            echo ""
            echo "\033[33mTo implement: Use cron jobs or systemd timers\033[0m"
            echo "Command: ./run.sh run-campaign --limit $company_limit"
            ;;
        2)
            echo "\033[36mBatch Email Generation\033[0m"
            echo ""
            read -p "Enter number of emails to generate (default: 50): " email_limit
            if [ -z "$email_limit" ]; then email_limit=50; fi
            
            echo "\033[36mGenerating $email_limit emails in batch...\033[0m"
            if [ -f "venv/bin/python" ]; then
                venv/bin/python cli.py generate-emails-recent --limit $email_limit
                echo "\033[32mBatch email generation completed\033[0m"
            else
                echo "\033[31mVirtual environment not found\033[0m"
            fi
            ;;
        3)
            echo "\033[36mDaily Analytics Report\033[0m"
            echo ""
            echo "\033[36mGenerating comprehensive daily analytics...\033[0m"
            if [ -f "venv/bin/python" ]; then
                venv/bin/python cli.py analytics-report --period daily
                echo "\033[32mDaily analytics report completed\033[0m"
            else
                echo "\033[31mVirtual environment not found\033[0m"
            fi
            ;;
        4)
            echo "\033[36mMaintenance Schedule Setup\033[0m"
            echo ""
            echo "\033[33mRecommended maintenance tasks:\033[0m"
            echo "- Daily: Analytics report generation"
            echo "- Weekly: System health check"
            echo "- Monthly: Installation check and updates"
            echo "- Quarterly: Configuration backup"
            echo ""
            echo "\033[33mTo implement: Use cron with these commands:\033[0m"
            echo "Daily: ./run.sh analytics-report --period daily"
            echo "Weekly: ./run.sh system-health"
            echo "Monthly: ./run.sh installation-check"
            ;;
        5)
            echo "\033[36mBulk Configuration\033[0m"
            echo ""
            echo "\033[33mThis feature would apply configuration changes across environments\033[0m"
            echo "Current configuration can be exported via Config Management [21]"
            ;;
        6)
            echo "\033[36mExport All Data\033[0m"
            echo ""
            echo "\033[36mStarting comprehensive data export...\033[0m"
            if [ -f "venv/bin/python" ]; then
                if venv/bin/python cli.py status >/dev/null 2>&1; then
                    echo "\033[32mSystem accessible - export can proceed\033[0m"
                    echo "\033[33mNote: Use Notion export features for complete data backup\033[0m"
                else
                    echo "\033[33mSystem check failed - verify configuration first\033[0m"
                fi
            else
                echo "\033[31mVirtual environment not found\033[0m"
            fi
            ;;
        0)
            return
            ;;
        *)
            echo "\033[31mInvalid choice. Please select 0-6.\033[0m"
            ;;
    esac

    echo ""
    read -p "Press Enter to continue..."
    batch_operations
}
