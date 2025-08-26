@echo off
setlocal enabledelayedexpansion

echo ========================================
echo   ProspectAI Windows Installer
echo ========================================
echo.
echo Setting up your job automation environment...
echo.

:: Check for Python 3.13
echo [1/4] Checking for Python 3.13...
python --version 2>nul | findstr "3.13" >nul
if %errorlevel% neq 0 (
    echo Python 3.13 not found. Installing via winget...
    echo.
    
    :: Check if winget is available
    winget --version >nul 2>&1
    if !errorlevel! neq 0 (
        echo ERROR: winget is not available on this system.
        echo.
        echo Please install Python 3.13 manually:
        echo 1. Go to: https://www.python.org/downloads/
        echo 2. Download Python 3.13.x for Windows
        echo 3. Run the installer with "Add to PATH" checked
        echo 4. Restart this installer after Python installation
        echo.
        pause
        exit /b 1
    )
    
    :: Install Python using winget
    echo Installing Python 3.13...
    winget install --id Python.Python.3.13 -e --silent
    if !errorlevel! neq 0 (
        echo.
        echo ERROR: Failed to install Python automatically.
        echo.
        echo Please install Python 3.13 manually:
        echo 1. Go to: https://www.python.org/downloads/
        echo 2. Download Python 3.13.x for Windows
        echo 3. Run the installer with "Add to PATH" checked
        echo 4. Restart this installer after Python installation
        echo.
        echo If Python is already installed, make sure it's in your PATH.
        echo You may need to restart your command prompt or computer.
        echo.
        pause
        exit /b 1
    )
    
    echo Python 3.13 installation completed.
    echo Refreshing PATH environment...
    
    :: Refresh environment variables
    call refreshenv 2>nul
    
    :: Wait a moment for installation to complete
    timeout /t 3 /nobreak >nul
    
    :: Test Python again
    echo Testing Python installation...
    python --version 2>nul | findstr "3.13" >nul
    if !errorlevel! neq 0 (
        echo.
        echo WARNING: Python 3.13 installation may not be complete.
        echo Please restart your command prompt and try again.
        echo If the problem persists, install Python manually from python.org
        echo.
        pause
        exit /b 1
    )
) else (
    echo Python 3.13 found and ready.
)

echo.
echo [2/4] Python verification complete.
echo.

:: Check if we're in the correct directory
if not exist "cli.py" (
    echo ERROR: This installer must be run from the ProspectAI project directory.
    echo Please navigate to the project folder and run install.bat again.
    echo.
    pause
    exit /b 1
)

:: Check if interactive_setup.py exists
if not exist "interactive_setup.py" (
    echo ERROR: interactive_setup.py not found in current directory.
    echo Please ensure you have the complete ProspectAI project files.
    echo.
    pause
    exit /b 1
)

echo [3/4] Starting interactive setup...
echo This will create a virtual environment and install dependencies.
echo.

:: Run the interactive setup
python interactive_setup.py
if %errorlevel% neq 0 (
    echo.
    echo ========================================
    echo   Setup Failed
    echo ========================================
    echo.
    echo The interactive setup encountered an error.
    echo Please check the error messages above for details.
    echo.
    echo Common solutions:
    echo 1. Check your internet connection
    echo 2. Ensure Python 3.13 is properly installed
    echo 3. Try running as administrator
    echo 4. Check antivirus software isn't blocking the installation
    echo.
    echo If problems persist, please report the issue with the error messages above.
    echo.
    pause
    exit /b 1
)

echo.
echo [4/4] Installation verification...
echo.

:: Verify installation
if exist "venv\Scripts\python.exe" (
    echo Virtual environment: OK
) else (
    echo Virtual environment: FAILED
    goto :installation_failed
)

if exist ".env" (
    echo Configuration file: OK
) else (
    echo Configuration file: Not created ^(you may have skipped it^)
)

if exist "run.bat" (
    echo Runner script: OK
) else (
    echo Runner script: FAILED
    goto :installation_failed
)

echo.
echo ========================================
echo   Installation Successful!
echo ========================================
echo.
echo ^> ProspectAI is now ready to use!
echo.
echo Quick Start:
echo   1. Double-click run.bat to see available commands
echo   2. Or run: run.bat run-campaign --limit 5
echo.
echo Next Steps:
echo   - run.bat validate-config    ^(check your API keys^)
echo   - run.bat setup-dashboard    ^(create Notion dashboard^)
echo   - run.bat quick-start        ^(guided first campaign^)
echo.
echo Documentation:
echo   - README.md contains detailed usage instructions
echo   - examples/ folder has advanced usage examples
echo.
echo Happy prospecting! 🚀
echo.
pause
exit /b 0

:installation_failed
echo.
echo ========================================
echo   Installation Incomplete
echo ========================================
echo.
echo Some components were not properly installed.
echo Please run install.bat again or check for error messages above.
echo.
echo If you continue to have issues:
echo 1. Check your internet connection
echo 2. Ensure you have administrator privileges
echo 3. Try disabling antivirus temporarily
echo 4. Check Windows defender isn't blocking Python
echo.
pause
exit /b 1