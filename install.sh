#!/bin/bash
set -e

echo "========================================"
echo "  ProspectAI Unix Installer"
echo "========================================"
echo ""
echo "Setting up your job automation environment..."
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to detect OS
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macOS"
    elif [[ -f /etc/debian_version ]]; then
        echo "debian"
    elif [[ -f /etc/redhat-release ]]; then
        echo "redhat"
    elif [[ -f /etc/arch-release ]]; then
        echo "arch"
    else
        echo "unknown"
    fi
}

# Check for Python 3.13
echo "[1/4] Checking for Python 3.13..."
if command_exists python3.13; then
    PYTHON_CMD="python3.13"
    echo "Python 3.13 found and ready."
elif command_exists python3 && python3 --version 2>/dev/null | grep -q "3.13"; then
    PYTHON_CMD="python3"
    echo "Python 3.13 found and ready."
elif command_exists python && python --version 2>/dev/null | grep -q "3.13"; then
    PYTHON_CMD="python"
    echo "Python 3.13 found and ready."
else
    echo "Python 3.13 not found. Detecting system..."
    
    OS_TYPE=$(detect_os)
    
    case $OS_TYPE in
        "macOS")
            echo "Detected macOS system."
            if ! command_exists brew; then
                echo ""
                echo "ERROR: Homebrew not found."
                echo "Please install Homebrew first:"
                echo "  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
                echo ""
                echo "After installing Homebrew, run this installer again."
                exit 1
            fi
            
            echo "Installing Python 3.13 via Homebrew..."
            brew install python@3.13
            
            # Update PATH for this session
            export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
            
            if command_exists python3.13; then
                PYTHON_CMD="python3.13"
            else
                echo "ERROR: Python 3.13 installation failed or not found in PATH."
                echo "Please check the Homebrew installation output above."
                exit 1
            fi
            ;;
            
        "debian")
            echo "Detected Debian/Ubuntu system."
            echo "Installing Python 3.13 via APT..."
            
            # Update package lists
            echo "Updating package lists..."
            sudo apt-get update
            
            # Install Python 3.13
            sudo apt-get install -y python3.13 python3.13-venv python3.13-pip
            
            if command_exists python3.13; then
                PYTHON_CMD="python3.13"
            else
                echo "ERROR: Python 3.13 installation failed."
                echo "You may need to add a PPA repository first:"
                echo "  sudo add-apt-repository ppa:deadsnakes/ppa"
                echo "  sudo apt-get update"
                echo "  sudo apt-get install python3.13 python3.13-venv python3.13-pip"
                exit 1
            fi
            ;;
            
        "redhat")
            echo "Detected Red Hat/CentOS/Fedora system."
            echo "Installing Python 3.13..."
            
            if command_exists dnf; then
                sudo dnf install -y python3.13 python3.13-pip python3.13-venv
            elif command_exists yum; then
                sudo yum install -y python3.13 python3.13-pip python3.13-venv
            else
                echo "ERROR: No suitable package manager found (dnf/yum)."
                echo "Please install Python 3.13 manually."
                exit 1
            fi
            
            if command_exists python3.13; then
                PYTHON_CMD="python3.13"
            else
                echo "ERROR: Python 3.13 installation failed."
                echo "You may need to enable additional repositories (EPEL, etc.)."
                exit 1
            fi
            ;;
            
        "arch")
            echo "Detected Arch Linux system."
            echo "Installing Python 3.13..."
            sudo pacman -S python
            
            if command_exists python; then
                PYTHON_CMD="python"
            else
                echo "ERROR: Python installation failed."
                exit 1
            fi
            ;;
            
        *)
            echo "ERROR: Unsupported system detected."
            echo ""
            echo "Please install Python 3.13 manually:"
            echo "1. Go to: https://www.python.org/downloads/"
            echo "2. Download Python 3.13.x for your system"
            echo "3. Follow the installation instructions"
            echo "4. Ensure python3.13 is available in your PATH"
            echo "5. Run this installer again"
            echo ""
            exit 1
            ;;
    esac
    
    echo "Python 3.13 installation completed."
fi

echo ""
echo "[2/4] Python verification complete."
echo "Using Python command: $PYTHON_CMD"
echo ""

# Verify we're in the correct directory
if [ ! -f "cli.py" ]; then
    echo "ERROR: This installer must be run from the ProspectAI project directory."
    echo "Please navigate to the project folder and run ./install.sh again."
    echo ""
    exit 1
fi

# Check if interactive_setup.py exists
if [ ! -f "interactive_setup.py" ]; then
    echo "ERROR: interactive_setup.py not found in current directory."
    echo "Please ensure you have the complete ProspectAI project files."
    echo ""
    exit 1
fi

# Make the installer executable if it isn't already
chmod +x "$0" 2>/dev/null || true

echo "[3/4] Starting interactive setup..."
echo "This will create a virtual environment and install dependencies."
echo ""

# Run the interactive setup
$PYTHON_CMD interactive_setup.py
if [ $? -ne 0 ]; then
    echo ""
    echo "========================================"
    echo "  Setup Failed"
    echo "========================================"
    echo ""
    echo "The interactive setup encountered an error."
    echo "Please check the error messages above for details."
    echo ""
    echo "Common solutions:"
    echo "1. Check your internet connection"
    echo "2. Ensure Python 3.13 is properly installed"
    echo "3. Try running with sudo if permission errors occur"
    echo "4. Check that all required system packages are installed"
    echo ""
    echo "If problems persist, please report the issue with the error messages above."
    echo ""
    exit 1
fi

echo ""
echo "[4/4] Installation verification..."
echo ""

# Verify installation
if [ -f "venv/bin/python" ]; then
    echo "Virtual environment: OK"
else
    echo "Virtual environment: FAILED"
    exit 1
fi

if [ -f ".env" ]; then
    echo "Configuration file: OK"
else
    echo "Configuration file: Not created (you may have skipped it)"
fi

if [ -f "run.sh" ]; then
    echo "Runner script: OK"
    # Make sure runner script is executable
    chmod +x run.sh
else
    echo "Runner script: FAILED"
    exit 1
fi

echo ""
echo "========================================"
echo "  Installation Successful!"
echo "========================================"
echo ""
echo "> ProspectAI is now ready to use!"
echo ""
echo "Quick Start:"
echo "  1. Run: ./run.sh (to see available commands)"
echo "  2. Or run: ./run.sh run-campaign --limit 5"
echo ""
echo "Next Steps:"
echo "  - ./run.sh validate-config    (check your API keys)"
echo "  - ./run.sh setup-dashboard    (create Notion dashboard)"
echo "  - ./run.sh quick-start        (guided first campaign)"
echo ""
echo "Documentation:"
echo "  - README.md contains detailed usage instructions"
echo "  - examples/ folder has advanced usage examples"
echo ""
echo "Happy prospecting! 🚀"
echo ""