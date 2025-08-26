# GUI Runner Documentation

## Overview

The GUI Runner provides a user-friendly graphical interface for the Job Prospect Automation system, allowing users to execute CLI commands without needing to use the command line. It's built using Python's tkinter library for maximum compatibility across Windows, macOS, and Linux platforms.

## Features

### Main Interface
- **Tab-based Navigation**: Easy access to different functionality areas
- **Dashboard**: Quick overview of system status and recent campaigns
- **Real-time Output**: View command output as it runs
- **Configuration Management**: Easy setup of environment and config files
- **Automatic Configuration Detection**: Automatically finds config.yaml and profile files
- **Environment Variable Management**: Set and manage environment variables within the GUI

### Command Tabs

#### 1. Dashboard
- System status overview
- Quick access buttons to other tabs
- Recent campaign history (planned enhancement)

#### 2. Discover Companies
- Run company discovery with customizable parameters:
  - Dry run mode
  - Limit (number of companies to process)
  - Batch size
  - Campaign name (optional)
  - Sender profile selection

#### 3. Run Complete Campaign
- Execute complete campaigns with email generation:
  - Dry run mode
  - Auto setup dashboard
  - Limit (number of companies to process)
  - Campaign name
  - Sender profile selection
  - Generate emails option
  - Send emails option

#### 4. Process Specific Company
- Process a specific company:
  - Dry run mode
  - Company name (required)
  - Domain (optional)
  - Sender profile selection

#### 5. Generate Outreach Emails
- Create personalized emails for prospects:
  - Dry run mode
  - Two generation methods:
    - Specific Prospect IDs (comma-separated)
    - Recent Prospects (with limit parameter)
  - Email template selection
  - Sender profile selection
  - Validate profile option
  - Interactive profile option
  - Send immediately option

#### 6. Settings
- Configuration management:
  - Environment file selection (.env)
  - Config file selection (config.yaml)
  - Default sender profile selection
  - Configuration validation
  - File editing capabilities
  - Environment variable management:
    - Add, edit, and delete environment variables
    - Apply variables to current session
    - Save variables to .env file
  - Automatic configuration file detection:
    - Checks for config.yaml at startup
    - Discovers sender profiles automatically
    - Prompts user to create or browse for files if none found

## Usage

### Running the GUI

```bash
# Using the run script
python run_gui.py

# On Windows
run_gui.bat

# On Linux/macOS
./run_gui.sh
```

### Using the GUI

1. **Select a Command Tab**: Choose the functionality you want to use
2. **Configure Options**: Set the parameters for your command
3. **Run Command**: Click the appropriate "Run" button
4. **View Output**: Watch the command execution in the output area
5. **Cancel if Needed**: Use the Cancel button to stop long-running operations

### Generate Emails Recent

To use the new `generate-emails-recent` functionality:

1. Navigate to the "Generate Emails" tab
2. Select the "Recent Prospects" radio button
3. Enter the number of recent prospects to generate emails for (default: 10)
4. Select an email template if desired
5. Click "Generate Emails"

### Environment Variable Management

To manage environment variables:

1. Navigate to the "Settings" tab
2. Scroll down to the "Environment Variables" section
3. Add new variables by clicking "Add Environment Variable"
4. Edit existing variables directly in the input fields
5. Delete variables using the "X" button
6. Apply variables to the current session with "Apply Environment Variables"
7. Save variables to the .env file with "Save Settings"

### Configuration File Detection

The GUI automatically detects configuration files at startup:

1. Looks for `config.yaml` in common locations
2. Discovers sender profiles in standard directories
3. Prompts user to create or browse for files if none found
4. Sets the most recently modified profile as default

## Data Models

The GUI uses several data models to manage configuration:

### CommandConfiguration
Base configuration class for all commands:
- `dry_run`: Boolean flag for dry run mode
- `config_file`: Path to configuration file
- `env_file`: Path to environment file
- `sender_profile`: Path to sender profile file

### DiscoverConfig
Configuration for the discover command:
- Inherits from CommandConfiguration
- `limit`: Number of companies to process (default: 10)
- `batch_size`: Batch size for processing (default: 5)
- `campaign_name`: Optional campaign name

### RunCampaignConfig
Configuration for the run-campaign command:
- Inherits from CommandConfiguration
- `limit`: Number of companies to process (default: 10)
- `campaign_name`: Campaign name
- `generate_emails`: Flag to generate emails (default: True)
- `send_emails`: Flag to send emails (default: False)
- `auto_setup`: Auto-setup dashboard (default: False)

## Security Considerations

1. **Credential Protection**: API keys are never displayed in the UI
2. **File Access**: Secure handling of configuration files through system dialogs
3. **Process Isolation**: Commands are executed in separate processes
4. **Input Validation**: User inputs are validated before command execution
5. **Required Field Validation**: Required fields are clearly marked and validated before command execution
6. **Environment Variable Security**: Environment variables are managed securely within the application

## Future Enhancements

1. **Advanced Scheduling**: Cron-like scheduling for campaigns
2. **Template Management**: UI for creating and editing email templates
3. **Analytics Dashboard**: Graphical representation of campaign metrics
4. **Multi-User Support**: Shared configurations and campaign history
5. **Plugin Architecture**: Extensibility for custom commands
6. **Preset Management**: Save and load command configurations
7. **Enhanced Dashboard**: Real-time campaign monitoring and statistics
8. **Configuration Backup/Restore**: Backup and restore configuration files
9. **API Key Validation**: Validate API keys before allowing command execution
10. **Profile Preview**: Preview sender profiles before using them

## Troubleshooting

### Common Issues

1. **"Module not found" errors**: Ensure you're running from the project root directory
2. **File not found errors**: Check that configuration files exist and are accessible
3. **Permission errors**: Ensure you have read/write permissions for configuration files
4. **GUI not responding**: Long-running operations may temporarily block the interface
5. **Environment variables not applied**: Make sure to click "Apply Environment Variables" after making changes

### Getting Help

For issues not covered in this documentation:
1. Check the main README.md and documentation in the `docs/` directory
2. Run the CLI with `--help` flag for command-specific help
3. Use the dry-run mode to test commands without making API calls
4. Enable verbose logging in the CLI for detailed output

### Troubleshooting Output Issues

If you're not seeing output in the GUI:
1. Ensure you're using the latest version of gui_runner.py
2. Check that each tab has its own output area
3. Verify that commands are completing successfully
4. Try using the Cancel button to see if the output routing is working correctly

### Configuration Issues

If you're having trouble with configuration files:
1. Check that config.yaml contains all required API keys
2. Verify that the sender profile file is in a supported format (Markdown, JSON, YAML)
3. Ensure file permissions allow reading and writing
4. Use the "Validate Configuration" button to check for issues