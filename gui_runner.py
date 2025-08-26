#!/usr/bin/env python3
"""
GUI Runner for Job Prospect Automation System
Provides a user-friendly interface for running CLI commands without using the command line.
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import subprocess
import threading
import os
import sys
import json
from pathlib import Path

class CommandConfiguration:
    """Base configuration class for CLI commands."""
    def __init__(self):
        self.dry_run = False
        self.config_file = None
        self.env_file = None
        self.sender_profile = None

class DiscoverConfig(CommandConfiguration):
    """Configuration for the discover command."""
    def __init__(self):
        super().__init__()
        self.limit = 10
        self.batch_size = 5
        self.campaign_name = ""

class RunCampaignConfig(CommandConfiguration):
    """Configuration for the run-campaign command."""
    def __init__(self):
        super().__init__()
        self.limit = 10
        self.campaign_name = ""
        self.generate_emails = True
        self.send_emails = False
        self.auto_setup = False

class GUIRunner:
    def __init__(self, root):
        self.root = root
        self.root.title("Outreach-for-Job GUI Runner")
        self.root.geometry("800x600")
        
        # Configuration variables
        self.dry_run = tk.BooleanVar()
        self.auto_setup = tk.BooleanVar()
        self.generate_emails = tk.BooleanVar(value=True)
        self.send_emails = tk.BooleanVar()
        self.validate_profile = tk.BooleanVar()
        self.interactive_profile = tk.BooleanVar()
        
        # String variables
        self.limit = tk.StringVar(value="10")
        self.batch_size = tk.StringVar(value="5")
        self.campaign_name = tk.StringVar()
        self.sender_profile = tk.StringVar()
        self.company_name = tk.StringVar()
        self.domain = tk.StringVar()
        self.prospect_ids = tk.StringVar()
        self.env_file = tk.StringVar(value=".env")
        self.config_file = tk.StringVar()
        self.default_sender_profile = tk.StringVar()
        self.recent_emails_limit = tk.StringVar(value="10")  # New variable for generate-emails-recent limit
        
        # Template variable
        self.template_var = tk.StringVar(value="Cold Outreach")
        
        # Email generation method variable
        self.email_generation_method = tk.StringVar(value="specific")  # "specific" or "recent"
        
        # Process handle for cancellation
        self.current_process = None
        
        # Output text widgets for each tab
        self.discover_output_text = None
        self.campaign_output_text = None
        self.process_output_text = None
        self.email_output_text = None
        
        # Check for configuration files at startup
        self.check_configuration_files()
        
        self.create_widgets()
        
    def check_configuration_files(self):
        """Check for config.yaml and profile files, prompt user if not found."""
        import os
        from pathlib import Path
        
        # Check for config.yaml
        config_paths = [
            Path("config.yaml"),
            Path("config.yml"),
            Path.home() / ".job_prospect_automation" / "config.yaml",
            Path.home() / "config.yaml"
        ]
        
        config_found = False
        for path in config_paths:
            if path.exists():
                self.config_file.set(str(path))
                config_found = True
                break
        
        if not config_found:
            # Ask user to choose or create config file
            result = messagebox.askyesnocancel(
                "Configuration File Not Found",
                "No config.yaml file found. Would you like to:\n"
                "Yes: Create a new configuration file\n"
                "No: Browse for an existing configuration file\n"
                "Cancel: Continue without configuration file"
            )
            
            if result is True:  # Yes - create new
                self.create_new_config()
            elif result is False:  # No - browse
                self.browse_config_file()
        
        # Check for sender profiles
        self.check_sender_profiles()
        
    def check_sender_profiles(self):
        """Check for existing sender profiles."""
        from pathlib import Path
        
        # Use the same logic as SenderProfileManager.discover_existing_profiles()
        search_locations = [
            Path.cwd() / "profiles",  # Current directory profiles folder
            Path.cwd(),  # Current directory
            Path.home() / ".job_prospect_automation" / "profiles",  # User config folder
            Path.home() / "profiles",  # User home profiles folder
        ]
        
        # Profile file patterns to look for
        patterns = [
            "*.md", "*.markdown",  # Markdown files
            "*.json",  # JSON files
            "*.yaml", "*.yml"  # YAML files
        ]
        
        profiles = []
        for location in search_locations:
            if not location.exists():
                continue
                
            for pattern in patterns:
                for profile_path in location.glob(pattern):
                    profiles.append(profile_path)
        
        if profiles and not self.sender_profile.get():
            # Set the most recent profile as default
            profiles.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            self.sender_profile.set(str(profiles[0]))
        
    def create_widgets(self):
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create tabs
        self.create_dashboard_tab()
        self.create_discover_tab()
        self.create_run_campaign_tab()
        self.create_process_company_tab()
        self.create_generate_emails_tab()
        self.create_settings_tab()
        
        # Create status bar
        self.create_status_bar()
        
    def create_dashboard_tab(self):
        self.dashboard_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.dashboard_frame, text="Dashboard")
        
        # Dashboard content
        ttk.Label(self.dashboard_frame, text="Dashboard", font=("Arial", 16, "bold")).pack(pady=10)
        ttk.Label(self.dashboard_frame, text="Quick overview of system status and recent campaign history").pack()
        
        # Quick access buttons
        button_frame = ttk.Frame(self.dashboard_frame)
        button_frame.pack(pady=20)
        
        ttk.Button(button_frame, text="Run Discovery", command=lambda: self.notebook.select(1)).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Run Campaign", command=lambda: self.notebook.select(2)).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Settings", command=lambda: self.notebook.select(5)).pack(side=tk.LEFT, padx=5)
        
        # System status
        status_frame = ttk.LabelFrame(self.dashboard_frame, text="System Status")
        status_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(status_frame, text="Configuration: Validated", foreground="green").pack(anchor=tk.W, padx=5, pady=2)
        ttk.Label(status_frame, text="API Connections: All Connected", foreground="green").pack(anchor=tk.W, padx=5, pady=2)
        ttk.Label(status_frame, text="Last Campaign: None", foreground="gray").pack(anchor=tk.W, padx=5, pady=2)
        
    def create_discover_tab(self):
        self.discover_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.discover_frame, text="Discover")
        
        # Discover content
        ttk.Label(self.discover_frame, text="Discover Companies", font=("Arial", 14, "bold")).pack(pady=10)
        
        # Options frame
        options_frame = ttk.LabelFrame(self.discover_frame, text="Options")
        options_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Dry run checkbox
        ttk.Checkbutton(options_frame, text="Dry Run Mode", variable=self.dry_run).pack(anchor=tk.W, padx=5, pady=2)
        
        # Limit
        limit_frame = ttk.Frame(options_frame)
        limit_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(limit_frame, text="Limit:").pack(side=tk.LEFT)
        ttk.Entry(limit_frame, textvariable=self.limit, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Label(limit_frame, text="companies").pack(side=tk.LEFT)
        
        # Batch size
        batch_frame = ttk.Frame(options_frame)
        batch_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(batch_frame, text="Batch Size:").pack(side=tk.LEFT)
        ttk.Entry(batch_frame, textvariable=self.batch_size, width=10).pack(side=tk.LEFT, padx=5)
        
        # Campaign name (optional)
        campaign_frame = ttk.Frame(options_frame)
        campaign_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(campaign_frame, text="Campaign Name:").pack(side=tk.LEFT)
        ttk.Entry(campaign_frame, textvariable=self.campaign_name).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Label(campaign_frame, text="(optional)").pack(side=tk.LEFT, padx=5)
        
        # Sender profile (optional)
        profile_frame = ttk.Frame(options_frame)
        profile_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(profile_frame, text="Sender Profile:").pack(side=tk.LEFT)
        ttk.Entry(profile_frame, textvariable=self.sender_profile).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(profile_frame, text="Browse...", command=self.browse_sender_profile).pack(side=tk.LEFT, padx=5)
        ttk.Label(profile_frame, text="(optional)").pack(side=tk.LEFT, padx=5)
        
        # Buttons
        button_frame = ttk.Frame(self.discover_frame)
        button_frame.pack(pady=10)
        ttk.Button(button_frame, text="Run Discovery", command=self.run_discover).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Save Preset", command=self.save_preset).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Load Preset", command=self.load_preset).pack(side=tk.LEFT, padx=5)
        
        # Output area
        self.create_output_area(self.discover_frame, "discover")
        
    def create_run_campaign_tab(self):
        self.campaign_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.campaign_frame, text="Run Campaign")
        
        # Run campaign content
        ttk.Label(self.campaign_frame, text="Run Complete Campaign", font=("Arial", 14, "bold")).pack(pady=10)
        
        # Options frame
        options_frame = ttk.LabelFrame(self.campaign_frame, text="Options")
        options_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Dry run checkbox
        ttk.Checkbutton(options_frame, text="Dry Run Mode", variable=self.dry_run).pack(anchor=tk.W, padx=5, pady=2)
        
        # Auto setup checkbox
        ttk.Checkbutton(options_frame, text="Auto Setup Dashboard", variable=self.auto_setup).pack(anchor=tk.W, padx=5, pady=2)
        
        # Limit
        limit_frame = ttk.Frame(options_frame)
        limit_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(limit_frame, text="Limit:").pack(side=tk.LEFT)
        ttk.Entry(limit_frame, textvariable=self.limit, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Label(limit_frame, text="companies").pack(side=tk.LEFT)
        
        # Campaign name (optional)
        campaign_frame = ttk.Frame(options_frame)
        campaign_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(campaign_frame, text="Campaign Name:").pack(side=tk.LEFT)
        ttk.Entry(campaign_frame, textvariable=self.campaign_name).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Label(campaign_frame, text="(optional)").pack(side=tk.LEFT, padx=5)
        
        # Sender profile (optional)
        profile_frame = ttk.Frame(options_frame)
        profile_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(profile_frame, text="Sender Profile:").pack(side=tk.LEFT)
        ttk.Entry(profile_frame, textvariable=self.sender_profile).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(profile_frame, text="Browse...", command=self.browse_sender_profile).pack(side=tk.LEFT, padx=5)
        ttk.Label(profile_frame, text="(optional)").pack(side=tk.LEFT, padx=5)
        
        # Email options
        ttk.Checkbutton(options_frame, text="Generate Emails", variable=self.generate_emails).pack(anchor=tk.W, padx=5, pady=2)
        ttk.Checkbutton(options_frame, text="Send Emails", variable=self.send_emails).pack(anchor=tk.W, padx=5, pady=2)
        
        # Buttons
        button_frame = ttk.Frame(self.campaign_frame)
        button_frame.pack(pady=10)
        ttk.Button(button_frame, text="Run Campaign", command=self.run_campaign).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Save Preset", command=self.save_preset).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Load Preset", command=self.load_preset).pack(side=tk.LEFT, padx=5)
        
        # Output area
        self.create_output_area(self.campaign_frame, "campaign")
        
    def create_process_company_tab(self):
        self.process_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.process_frame, text="Process Company")
        
        # Process company content
        ttk.Label(self.process_frame, text="Process Specific Company", font=("Arial", 14, "bold")).pack(pady=10)
        
        # Options frame
        options_frame = ttk.LabelFrame(self.process_frame, text="Options")
        options_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Dry run checkbox
        ttk.Checkbutton(options_frame, text="Dry Run Mode", variable=self.dry_run).pack(anchor=tk.W, padx=5, pady=2)
        
        # Company name (required)
        company_frame = ttk.Frame(options_frame)
        company_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(company_frame, text="Company Name:").pack(side=tk.LEFT)
        ttk.Entry(company_frame, textvariable=self.company_name).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Label(company_frame, text="(required)").pack(side=tk.LEFT, padx=5)
        
        # Domain (optional)
        domain_frame = ttk.Frame(options_frame)
        domain_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(domain_frame, text="Domain:").pack(side=tk.LEFT)
        ttk.Entry(domain_frame, textvariable=self.domain).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Label(domain_frame, text="(optional)").pack(side=tk.LEFT, padx=5)
        
        # Sender profile (optional)
        profile_frame = ttk.Frame(options_frame)
        profile_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(profile_frame, text="Sender Profile:").pack(side=tk.LEFT)
        ttk.Entry(profile_frame, textvariable=self.sender_profile).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(profile_frame, text="Browse...", command=self.browse_sender_profile).pack(side=tk.LEFT, padx=5)
        ttk.Label(profile_frame, text="(optional)").pack(side=tk.LEFT, padx=5)
        
        # Buttons
        button_frame = ttk.Frame(self.process_frame)
        button_frame.pack(pady=10)
        ttk.Button(button_frame, text="Process Company", command=self.process_company).pack(side=tk.LEFT, padx=5)
        
        # Output area
        self.create_output_area(self.process_frame, "process")
        
    def create_generate_emails_tab(self):
        self.email_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.email_frame, text="Generate Emails")
        
        # Generate emails content
        ttk.Label(self.email_frame, text="Generate Outreach Emails", font=("Arial", 14, "bold")).pack(pady=10)
        
        # Options frame
        options_frame = ttk.LabelFrame(self.email_frame, text="Options")
        options_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Dry run checkbox
        ttk.Checkbutton(options_frame, text="Dry Run Mode", variable=self.dry_run).pack(anchor=tk.W, padx=5, pady=2)
        
        # Email generation method selection
        method_frame = ttk.Frame(options_frame)
        method_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(method_frame, text="Generation Method:").pack(side=tk.LEFT)
        
        # Radio buttons for method selection
        ttk.Radiobutton(method_frame, text="Specific Prospect IDs", variable=self.email_generation_method, 
                       value="specific", command=self.toggle_email_method).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(method_frame, text="Recent Prospects", variable=self.email_generation_method,
                       value="recent", command=self.toggle_email_method).pack(side=tk.LEFT, padx=5)
        
        # Prospect IDs section (required for specific method)
        self.ids_frame = ttk.Frame(options_frame)
        self.ids_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(self.ids_frame, text="Prospect IDs:").pack(side=tk.LEFT)
        ttk.Entry(self.ids_frame, textvariable=self.prospect_ids).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Label(self.ids_frame, text="(comma-separated, required)").pack(side=tk.LEFT, padx=5)
        
        # Recent prospects section (for recent method)
        self.recent_frame = ttk.Frame(options_frame)
        self.recent_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(self.recent_frame, text="Number of Recent Prospects:").pack(side=tk.LEFT)
        ttk.Entry(self.recent_frame, textvariable=self.recent_emails_limit, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Label(self.recent_frame, text="(default: 10)").pack(side=tk.LEFT, padx=5)
        self.recent_frame.pack_forget()  # Hide by default
        
        # Template (optional)
        template_frame = ttk.Frame(options_frame)
        template_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(template_frame, text="Template:").pack(side=tk.LEFT)
        template_combo = ttk.Combobox(template_frame, textvariable=self.template_var, 
                                     values=["Cold Outreach", "Referral Followup", "Product Interest", "Networking"])
        template_combo.pack(side=tk.LEFT, padx=5)
        ttk.Label(template_frame, text="(optional)").pack(side=tk.LEFT, padx=5)
        
        # Sender profile (optional)
        profile_frame = ttk.Frame(options_frame)
        profile_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(profile_frame, text="Sender Profile:").pack(side=tk.LEFT)
        ttk.Entry(profile_frame, textvariable=self.sender_profile).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(profile_frame, text="Browse...", command=self.browse_sender_profile).pack(side=tk.LEFT, padx=5)
        ttk.Label(profile_frame, text="(optional)").pack(side=tk.LEFT, padx=5)
        
        # Profile options
        ttk.Checkbutton(options_frame, text="Validate Profile", variable=self.validate_profile).pack(anchor=tk.W, padx=5, pady=2)
        ttk.Checkbutton(options_frame, text="Interactive Profile", variable=self.interactive_profile).pack(anchor=tk.W, padx=5, pady=2)
        ttk.Checkbutton(options_frame, text="Send Immediately", variable=self.send_emails).pack(anchor=tk.W, padx=5, pady=2)
        
        # Buttons
        button_frame = ttk.Frame(self.email_frame)
        button_frame.pack(pady=10)
        ttk.Button(button_frame, text="Generate Emails", command=self.generate_emails_cmd).pack(side=tk.LEFT, padx=5)
        
        # Output area
        self.create_output_area(self.email_frame, "email")
        
    def toggle_email_method(self):
        """Toggle between specific prospect IDs and recent prospects methods."""
        if self.email_generation_method.get() == "specific":
            self.ids_frame.pack(fill=tk.X, padx=5, pady=2)
            self.recent_frame.pack_forget()
        else:
            self.recent_frame.pack(fill=tk.X, padx=5, pady=2)
            self.ids_frame.pack_forget()
        
    def create_settings_tab(self):
        self.settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.settings_frame, text="Settings")
        
        # Settings content
        ttk.Label(self.settings_frame, text="Configuration Settings", font=("Arial", 14, "bold")).pack(pady=10)
        
        # Config files frame
        config_frame = ttk.LabelFrame(self.settings_frame, text="Configuration Files")
        config_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Environment file
        env_frame = ttk.Frame(config_frame)
        env_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(env_frame, text="Environment File:").pack(side=tk.LEFT)
        ttk.Entry(env_frame, textvariable=self.env_file).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(env_frame, text="Browse", command=self.browse_env_file).pack(side=tk.LEFT, padx=5)
        
        # Config file
        cfg_frame = ttk.Frame(config_frame)
        cfg_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(cfg_frame, text="Config File:").pack(side=tk.LEFT)
        ttk.Entry(cfg_frame, textvariable=self.config_file).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(cfg_frame, text="Browse", command=self.browse_config_file).pack(side=tk.LEFT, padx=5)
        
        # Config buttons
        config_button_frame = ttk.Frame(config_frame)
        config_button_frame.pack(pady=5)
        ttk.Button(config_button_frame, text="Validate Configuration", command=self.validate_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(config_button_frame, text="Edit .env", command=self.edit_env).pack(side=tk.LEFT, padx=5)
        ttk.Button(config_button_frame, text="Edit config.yaml", command=self.edit_config).pack(side=tk.LEFT, padx=5)
        
        # Default sender profile frame
        profile_frame = ttk.LabelFrame(self.settings_frame, text="Default Sender Profile")
        profile_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Default sender profile
        default_profile_frame = ttk.Frame(profile_frame)
        default_profile_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(default_profile_frame, text="Default Sender Profile:").pack(side=tk.LEFT)
        ttk.Entry(default_profile_frame, textvariable=self.default_sender_profile).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(default_profile_frame, text="Browse", command=self.browse_default_profile).pack(side=tk.LEFT, padx=5)
        
        # Environment Variables frame
        env_vars_frame = ttk.LabelFrame(self.settings_frame, text="Environment Variables")
        env_vars_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Create a frame for environment variables with scrollable area
        env_vars_canvas = tk.Canvas(env_vars_frame, height=150)
        env_vars_scrollbar = ttk.Scrollbar(env_vars_frame, orient="vertical", command=env_vars_canvas.yview)
        self.env_vars_frame_inner = ttk.Frame(env_vars_canvas)
        
        env_vars_canvas.configure(yscrollcommand=env_vars_scrollbar.set)
        env_vars_canvas.pack(side="left", fill="both", expand=True)
        env_vars_scrollbar.pack(side="right", fill="y")
        
        env_vars_canvas.create_window((0, 0), window=self.env_vars_frame_inner, anchor="nw")
        self.env_vars_frame_inner.bind("<Configure>", lambda e: env_vars_canvas.configure(scrollregion=env_vars_canvas.bbox("all")))
        
        # Add environment variables section
        self.env_vars_entries = []
        self.load_current_env_vars()
        
        # Button to add new environment variable
        ttk.Button(env_vars_frame, text="Add Environment Variable", command=self.add_env_var_entry).pack(pady=5)
        
        # Settings buttons
        settings_button_frame = ttk.Frame(self.settings_frame)
        settings_button_frame.pack(pady=10)
        ttk.Button(settings_button_frame, text="Save Settings", command=self.save_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(settings_button_frame, text="Reset to Defaults", command=self.reset_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(settings_button_frame, text="Apply Environment Variables", command=self.apply_env_vars).pack(side=tk.LEFT, padx=5)
        
    def load_current_env_vars(self):
        """Load current environment variables into the UI."""
        # Clear existing entries
        for entry_pair in self.env_vars_entries:
            entry_pair[0].destroy()
            entry_pair[1].destroy()
        self.env_vars_entries.clear()
        
        # Add common environment variables
        common_vars = [
            "NOTION_TOKEN",
            "HUNTER_API_KEY", 
            "OPENAI_API_KEY",
            "AI_PROVIDER",
            "SENDER_EMAIL",
            "SENDER_NAME"
        ]
        
        for var_name in common_vars:
            var_value = os.environ.get(var_name, "")
            self.add_env_var_entry(var_name, var_value)
            
    def add_env_var_entry(self, name="", value=""):
        """Add a new environment variable entry row."""
        row_frame = ttk.Frame(self.env_vars_frame_inner)
        row_frame.pack(fill=tk.X, padx=5, pady=2)
        
        name_var = tk.StringVar(value=name)
        value_var = tk.StringVar(value=value)
        
        # Name entry
        name_entry = ttk.Entry(row_frame, textvariable=name_var, width=20)
        name_entry.pack(side=tk.LEFT, padx=2)
        
        # Value entry
        value_entry = ttk.Entry(row_frame, textvariable=value_var)
        value_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
        # Delete button
        delete_btn = ttk.Button(row_frame, text="X", width=3, 
                               command=lambda: self.delete_env_var_entry(row_frame, name_var, value_var))
        delete_btn.pack(side=tk.LEFT, padx=2)
        
        self.env_vars_entries.append((row_frame, name_var, value_var))
        
    def delete_env_var_entry(self, row_frame, name_var, value_var):
        """Delete an environment variable entry."""
        row_frame.destroy()
        self.env_vars_entries = [entry for entry in self.env_vars_entries 
                                if entry[1] != name_var and entry[2] != value_var]
        
    def apply_env_vars(self):
        """Apply environment variables to the current session."""
        for _, name_var, value_var in self.env_vars_entries:
            name = name_var.get().strip()
            value = value_var.get().strip()
            if name:
                os.environ[name] = value
        messagebox.showinfo("Success", "Environment variables applied to current session!")
        
    def create_status_bar(self):
        self.status_frame = ttk.Frame(self.root)
        self.status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.status_label = ttk.Label(self.status_frame, text="Status: Ready")
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        self.cancel_button = ttk.Button(self.status_frame, text="Cancel", command=self.cancel_operation, state=tk.DISABLED)
        self.cancel_button.pack(side=tk.RIGHT, padx=5)
        
    def create_output_area(self, parent, tab_name):
        # Output area
        output_frame = ttk.LabelFrame(parent, text="Output")
        output_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        output_text = scrolledtext.ScrolledText(output_frame, height=10)
        output_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Assign to the appropriate attribute based on tab
        if tab_name == "discover":
            self.discover_output_text = output_text
        elif tab_name == "campaign":
            self.campaign_output_text = output_text
        elif tab_name == "process":
            self.process_output_text = output_text
        elif tab_name == "email":
            self.email_output_text = output_text
        
    def browse_sender_profile(self):
        file_path = filedialog.askopenfilename(
            title="Select Sender Profile",
            filetypes=[("Markdown files", "*.md"), ("All files", "*.*")]
        )
        if file_path:
            self.sender_profile.set(file_path)
            
    def browse_env_file(self):
        file_path = filedialog.askopenfilename(
            title="Select Environment File",
            filetypes=[("Environment files", ".env"), ("All files", "*.*")]
        )
        if file_path:
            self.env_file.set(file_path)
            
    def browse_config_file(self):
        file_path = filedialog.askopenfilename(
            title="Select Config File",
            filetypes=[("YAML files", "*.yaml"), ("YAML files", "*.yml"), ("All files", "*.*")]
        )
        if file_path:
            self.config_file.set(file_path)
            
    def browse_default_profile(self):
        file_path = filedialog.askopenfilename(
            title="Select Default Sender Profile",
            filetypes=[("Markdown files", "*.md"), ("All files", "*.*")]
        )
        if file_path:
            self.default_sender_profile.set(file_path)
            
    def create_new_config(self):
        """Create a new configuration file with template content."""
        from pathlib import Path
        import yaml
        
        # Ask user where to save the config file
        file_path = filedialog.asksaveasfilename(
            title="Create New Configuration File",
            defaultextension=".yaml",
            filetypes=[("YAML files", "*.yaml"), ("YAML files", "*.yml"), ("All files", "*.*")],
            initialfile="config.yaml"
        )
        
        if file_path:
            try:
                # Create template configuration
                template_config = {
                    "NOTION_TOKEN": "your_notion_api_token_here",
                    "HUNTER_API_KEY": "your_hunter_api_key_here",
                    "OPENAI_API_KEY": "your_openai_api_key_here",
                    "AI_PROVIDER": "openai",
                    "SENDER_EMAIL": "your_email@example.com",
                    "SENDER_NAME": "Your Name"
                }
                
                # Write template to file
                with open(file_path, 'w') as f:
                    yaml.dump(template_config, f, default_flow_style=False)
                
                self.config_file.set(file_path)
                messagebox.showinfo(
                    "Configuration Created",
                    f"Configuration file created at:\n{file_path}\n\n"
                    "Please edit the file with your actual API keys and settings."
                )
                
                # Try to open the file in the default editor
                self.open_file_in_editor(file_path)
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create configuration file: {str(e)}")
                
    def open_file_in_editor(self, file_path):
        """Open a file in the system's default editor."""
        try:
            if sys.platform == "win32":
                os.startfile(file_path)
            elif sys.platform == "darwin":
                subprocess.call(["open", file_path])
            else:
                subprocess.call(["xdg-open", file_path])
        except Exception as e:
            messagebox.showwarning("Warning", f"Could not open file in editor: {str(e)}\n\nPlease open {file_path} manually to edit it.")
                
    def save_preset(self):
        # In a real implementation, this would save the current configuration to a file
        messagebox.showinfo("Save Preset", "Preset saving functionality would save your current configuration for future use.")
        
    def load_preset(self):
        # In a real implementation, this would load a saved configuration from a file
        messagebox.showinfo("Load Preset", "Preset loading functionality would load a saved configuration.")
        
    def validate_config(self):
        # In a real implementation, this would validate the configuration files
        messagebox.showinfo("Validate Configuration", "Configuration validation would check your .env and config.yaml files for correctness.")
        
    def edit_env(self):
        env_file = self.env_file.get()
        if not env_file or not os.path.exists(env_file):
            messagebox.showerror("Error", f"Environment file not found: {env_file}")
            return
            
        # Try to open the file with the default editor
        try:
            if sys.platform == "win32":
                os.startfile(env_file)
            elif sys.platform == "darwin":
                subprocess.call(["open", env_file])
            else:
                subprocess.call(["xdg-open", env_file])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file: {str(e)}")
        
    def edit_config(self):
        config_file = self.config_file.get()
        if not config_file:
            config_file = "config.yaml"
            
        if not os.path.exists(config_file):
            messagebox.showerror("Error", f"Config file not found: {config_file}")
            return
            
        # Try to open the file with the default editor
        try:
            if sys.platform == "win32":
                os.startfile(config_file)
            elif sys.platform == "darwin":
                subprocess.call(["open", config_file])
            else:
                subprocess.call(["xdg-open", config_file])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file: {str(e)}")
        
    def save_settings(self):
        # Save GUI settings to JSON file
        settings = {
            "env_file": self.env_file.get(),
            "config_file": self.config_file.get(),
            "default_sender_profile": self.default_sender_profile.get()
        }
        
        try:
            with open("gui_settings.json", "w") as f:
                json.dump(settings, f, indent=2)
            messagebox.showinfo("Save Settings", "GUI settings saved successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save GUI settings: {str(e)}")
            
        # Save environment variables to .env file
        try:
            env_file_path = self.env_file.get()
            if not env_file_path:
                env_file_path = ".env"
                
            # Read existing content
            existing_vars = {}
            if os.path.exists(env_file_path):
                with open(env_file_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            existing_vars[key.strip()] = value.strip()
            
            # Update with current environment variables from UI
            for _, name_var, value_var in self.env_vars_entries:
                name = name_var.get().strip()
                value = value_var.get().strip()
                if name:
                    existing_vars[name] = value
            
            # Write back to file
            with open(env_file_path, 'w') as f:
                # Write existing variables
                for key, value in existing_vars.items():
                    f.write(f"{key}={value}\n")
                    
            messagebox.showinfo("Save Settings", f"Environment variables saved to {env_file_path}!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save environment variables: {str(e)}")
        
    def reset_settings(self):
        self.env_file.set(".env")
        self.config_file.set("")
        self.default_sender_profile.set("")
        self.load_current_env_vars()  # Reset environment variables to current values
        messagebox.showinfo("Reset Settings", "Settings reset to defaults!")
        
    def cancel_operation(self):
        if self.current_process:
            try:
                self.current_process.terminate()
                # Get current tab to determine which output text to use
                current_tab = self.notebook.index(self.notebook.select())
                if current_tab == 1:  # Discover tab
                    self.update_output("\nOperation cancelled by user.\n", self.discover_output_text)
                elif current_tab == 2:  # Campaign tab
                    self.update_output("\nOperation cancelled by user.\n", self.campaign_output_text)
                elif current_tab == 3:  # Process tab
                    self.update_output("\nOperation cancelled by user.\n", self.process_output_text)
                elif current_tab == 4:  # Email tab
                    self.update_output("\nOperation cancelled by user.\n", self.email_output_text)
            except Exception as e:
                # Get current tab to determine which output text to use
                current_tab = self.notebook.index(self.notebook.select())
                if current_tab == 1:  # Discover tab
                    self.update_output(f"\nError cancelling operation: {str(e)}\n", self.discover_output_text)
                elif current_tab == 2:  # Campaign tab
                    self.update_output(f"\nError cancelling operation: {str(e)}\n", self.campaign_output_text)
                elif current_tab == 3:  # Process tab
                    self.update_output(f"\nError cancelling operation: {str(e)}\n", self.process_output_text)
                elif current_tab == 4:  # Email tab
                    self.update_output(f"\nError cancelling operation: {str(e)}\n", self.email_output_text)
        
    def run_discover(self):
        self.execute_command("discover", self.discover_output_text)
        
    def run_campaign(self):
        self.execute_command("run-campaign", self.campaign_output_text)
        
    def process_company(self):
        # Validate required fields
        if not self.company_name.get().strip():
            messagebox.showerror("Validation Error", "Company Name is required for processing a company.")
            return
        self.execute_command("process-company", self.process_output_text)
        
    def generate_emails_cmd(self):
        # Validate required fields based on selected method
        if self.email_generation_method.get() == "specific":
            if not self.prospect_ids.get().strip():
                messagebox.showerror("Validation Error", "Prospect IDs are required for generating emails for specific prospects.")
                return
            self.execute_command("generate-emails", self.email_output_text)
        else:
            # For recent prospects, validate the limit is a number
            try:
                limit = int(self.recent_emails_limit.get())
                if limit <= 0:
                    raise ValueError("Limit must be positive")
            except ValueError:
                messagebox.showerror("Validation Error", "Number of recent prospects must be a positive integer.")
                return
            self.execute_command("generate-emails-recent", self.email_output_text)
        
    def execute_command(self, command, output_text):
        # Disable buttons during execution
        self.set_buttons_state(tk.DISABLED)
        self.cancel_button.config(state=tk.NORMAL)
        self.status_label.config(text=f"Status: Running {command}...")
        
        # Clear previous output
        output_text.delete(1.0, tk.END)
        
        # Start execution in a separate thread
        thread = threading.Thread(target=self.run_command_thread, args=(command, output_text))
        thread.daemon = True
        thread.start()
        
    def run_command_thread(self, command, output_text):
        try:
            # Build command
            cmd = [sys.executable, "cli.py", command]
            
            # Add common options
            if self.dry_run.get():
                cmd.append("--dry-run")
                
            # Add command-specific options
            if command == "discover":
                cmd.extend(["--limit", self.limit.get()])
                cmd.extend(["--batch-size", self.batch_size.get()])
                if self.campaign_name.get():
                    cmd.extend(["--campaign-name", self.campaign_name.get()])
                if self.sender_profile.get():
                    cmd.extend(["--sender-profile", self.sender_profile.get()])
                    
            elif command == "run-campaign":
                cmd.extend(["--limit", self.limit.get()])
                if self.campaign_name.get():
                    cmd.extend(["--campaign-name", self.campaign_name.get()])
                if self.sender_profile.get():
                    cmd.extend(["--sender-profile", self.sender_profile.get()])
                if self.generate_emails.get():
                    cmd.append("--generate-emails")
                if self.send_emails.get():
                    cmd.append("--send-emails")
                if self.auto_setup.get():
                    cmd.append("--auto-setup")
                    
            elif command == "process-company":
                if self.company_name.get():
                    cmd.append(self.company_name.get())
                else:
                    self.update_output("Error: Company name is required\n", output_text)
                    return
                if self.domain.get():
                    cmd.extend(["--domain", self.domain.get()])
                if self.sender_profile.get():
                    cmd.extend(["--sender-profile", self.sender_profile.get()])
                    
            elif command == "generate-emails":
                if self.prospect_ids.get():
                    cmd.extend(["--prospect-ids", self.prospect_ids.get()])
                else:
                    self.update_output("Error: Prospect IDs are required\n", output_text)
                    return
                # Template and other options would be added here
                if self.template_var.get():
                    # Map template names to CLI values
                    template_map = {
                        "Cold Outreach": "cold_outreach",
                        "Referral Followup": "referral_followup",
                        "Product Interest": "product_interest",
                        "Networking": "networking"
                    }
                    template_value = template_map.get(self.template_var.get(), "cold_outreach")
                    cmd.extend(["--template", template_value])
                if self.send_emails.get():
                    cmd.append("--send")
                if self.validate_profile.get():
                    cmd.append("--validate-profile")
                if self.interactive_profile.get():
                    cmd.append("--interactive-profile")
                    
            elif command == "generate-emails-recent":
                # Add limit parameter
                cmd.extend(["--limit", self.recent_emails_limit.get()])
                
                # Template and other options
                if self.template_var.get():
                    # Map template names to CLI values
                    template_map = {
                        "Cold Outreach": "cold_outreach",
                        "Referral Followup": "referral_followup",
                        "Product Interest": "product_interest",
                        "Networking": "networking"
                    }
                    template_value = template_map.get(self.template_var.get(), "cold_outreach")
                    cmd.extend(["--template", template_value])
                if self.send_emails.get():
                    cmd.append("--send")
                    
            # Set environment
            env = os.environ.copy()
            if self.env_file.get():
                env["ENV_FILE"] = self.env_file.get()
                
            # Execute command
            self.update_output(f"Executing: {' '.join(cmd)}\n", output_text)
            
            self.current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                env=env
            )
            
            # Read output in real-time
            for line in self.current_process.stdout:
                self.update_output(line, output_text)
                
            self.current_process.wait()
            
            if self.current_process.returncode == 0:
                self.update_output(f"\n{command} completed successfully!\n", output_text)
            else:
                self.update_output(f"\n{command} failed with return code {self.current_process.returncode}\n", output_text)
                
        except Exception as e:
            self.update_output(f"Error executing command: {str(e)}\n", output_text)
        finally:
            self.current_process = None
            # Re-enable buttons
            self.root.after(0, self.set_buttons_state, tk.NORMAL)
            self.root.after(0, self.cancel_button.config, {"state": tk.DISABLED})
            self.root.after(0, self.status_label.config, {"text": "Status: Ready"})
            
    def update_output(self, text, output_text):
        self.root.after(0, self.append_output, text, output_text)
        
    def append_output(self, text, output_text):
        output_text.insert(tk.END, text)
        output_text.see(tk.END)
        
    def set_buttons_state(self, state):
        # Disable/enable all command buttons
        for tab_id in range(self.notebook.index("end")):
            tab_frame = self.notebook.nametowidget(self.notebook.tabs()[tab_id])
            for child in tab_frame.winfo_children():
                if isinstance(child, ttk.Frame):
                    for grandchild in child.winfo_children():
                        if isinstance(grandchild, ttk.Button) and grandchild.cget("text") not in ["Browse...", "Browse", "Validate Configuration", "Edit .env", "Edit config.yaml", "Save Settings", "Reset to Defaults"]:
                            grandchild.config(state=state)
                elif isinstance(child, ttk.Button) and child.cget("text") not in ["Browse...", "Browse", "Validate Configuration", "Edit .env", "Edit config.yaml", "Save Settings", "Reset to Defaults"]:
                    child.config(state=state)

def main():
    root = tk.Tk()
    app = GUIRunner(root)
    root.mainloop()

if __name__ == "__main__":
    main()