#!/usr/bin/env python3
"""
Project Reorganization Script
Organizes the messy root directory into a clean, professional structure.
"""

import os
import shutil
from pathlib import Path

def reorganize_project():
    """Reorganize the project structure."""
    
    # Define the reorganization mapping
    reorganization_map = {
        # Scripts - All utility and debug scripts
        'scripts/': [
            'apply_performance_optimizations.py',
            'check_personalization.py',
            'cli_profile_commands_check.py',
            'cli_profile_commands_fixed.py',
            'cli_profile_commands.py',
            'create_database.py',
            'debug_daily_analytics.py',
            'debug_discovery.py',
            'debug_email_content.py',
            'debug_email_generation.py',
            'debug_email_length.py',
            'debug_email_subject.py',
            'debug_notion_fields.py',
            'debug_notion_storage.py',
            'debug_team_extraction.py',
            'email_stats.py',
            'fast_linkedin_scraper.py',
            'find_missing_linkedin_urls.py',
            'fix_all_performance_issues.py',
            'fix_all_truncation_issues.py',
            'fix_truncated_data.py',
            'fix_workflow_bugs.py',
            'linkedin_performance_fix.py',
            'migrate_notion_database.py',
            'performance_benchmark.py',
            'quick_test.py',
            'run_performance_tests.py',
            'setup_dashboard.py',
            'setup_user_mentions.py',
            'simple_test.py',
            'update_existing_prospects_defaults.py',
            'verify_notion_schema.py',
        ],
        
        # Test files - Move standalone test files to tests/
        'tests/': [
            'test_campaign_email_generation.py',
            'test_campaign_limit_behavior.py',
            'test_company_deduplication.py',
            'test_complete_pipeline_with_email.py',
            'test_dashboard_creation.py',
            'test_data_fixes.py',
            'test_email_debug.py',
            'test_email_finder.py',
            'test_email_generation_fix.py',
            'test_email_pipeline.py',
            'test_email_send.py',
            'test_email_sending.py',
            'test_email_storage.py',
            'test_fast_linkedin_integration.py',
            'test_full_pipeline.py',
            'test_hunter_api.py',
            'test_hunter_config.py',
            'test_hunter_verbose.py',
            'test_interactive_controls.py',
            'test_json_extraction.py',
            'test_limit_logic_simple.py',
            'test_linkedin_finder_speed.py',
            'test_linkedin_optimization.py',
            'test_linkedin_performance.py',
            'test_models_integration.py',
            'test_notion_storage_limits.py',
            'test_notion_updates.py',
            'test_openai_api.py',
            'test_optimizations.py',
            'test_parallel_processing.py',
            'test_performance_comparison.py',
            'test_performance_improvement.py',
            'test_performance.py',
            'test_personalization_fix.py',
            'test_producthunt_linkedin_extraction.py',
            'test_producthunt_raw.py',
            'test_producthunt.py',
            'test_prospect_defaults.py',
            'test_simple_email.py',
            'test_team_extraction.py',
            'test_updated_scraper.py',
        ],
        
        # Configuration files
        'config/': [
            'config.yaml.template',
            'example-config.yaml',
            'final-test.yaml',
            'fast_linkedin_config.env',
            'performance_optimization.env',
            'performance_optimized.env',
        ],
        
        # Reports and analysis documents
        'reports/': [
            'AI_TOKEN_CONSUMPTION_ANALYSIS.md',
            'BUG_FIX_SUMMARY.md',
            'COMPANY_DEDUPLICATION_OPTIMIZATION.md',
            'CRITICAL_WORKFLOW_ANALYSIS.md',
            'DATA_FIXES_README.md',
            'EMAIL_GENERATION_FIX_SUMMARY.md',
            'EMAIL_STORAGE_IMPLEMENTATION.md',
            'FINAL_INTEGRATION_VALIDATION_SUMMARY.md',
            'IMPORT_OPTIMIZATION_SUMMARY.md',
            'INTEGRATION_TEST_REPORT.md',
            'LINKEDIN_FINDER_COMPARISON.md',
            'LINKEDIN_PERFORMANCE_BREAKTHROUGH.md',
            'LINKEDIN_PERFORMANCE_OPTIMIZATION.md',
            'LINKEDIN_STRATEGY_ANALYSIS.md',
            'NOTION_DATABASE_FIXES.md',
            'NOTION_PROGRESS_GUIDE.md',
            'PERFORMANCE_BREAKTHROUGH_SUMMARY.md',
            'PERFORMANCE_OPTIMIZATION_PLAN.md',
            'PERFORMANCE_OPTIMIZATIONS_SUMMARY.md',
            'PERFORMANCE_VALIDATION_REPORT.md',
            'PIPELINE_TEST_SUMMARY.md',
            'PRODUCTHUNT_LINKEDIN_FIX_SUMMARY.md',
            'SCRAPING_AND_PARSING_WORKFLOW.md',
            'TEST_CONSOLIDATION_SUMMARY.md',
            'import_analysis_report.txt',
            'import_cleanup_report.txt',
            'import_organization_report.txt',
            'import_validation_report.txt',
        ],
        
        # Archive - Old/backup files
        'archive/': [
            'producthunt_raw.html',
        ],
    }
    
    print("🗂️  Starting project reorganization...")
    
    # Create directories if they don't exist
    for directory in reorganization_map.keys():
        Path(directory).mkdir(exist_ok=True)
        print(f"📁 Created directory: {directory}")
    
    # Move files
    moved_count = 0
    for target_dir, files in reorganization_map.items():
        for file in files:
            if os.path.exists(file):
                try:
                    shutil.move(file, os.path.join(target_dir, file))
                    print(f"✅ Moved {file} → {target_dir}")
                    moved_count += 1
                except Exception as e:
                    print(f"❌ Failed to move {file}: {e}")
            else:
                print(f"⚠️  File not found: {file}")
    
    print(f"\n🎉 Reorganization complete! Moved {moved_count} files.")
    
    # Create a README for each new directory
    create_directory_readmes()
    
    print("\n📋 Created README files for new directories.")
    print("\n✨ Project structure is now organized!")

def create_directory_readmes():
    """Create README files for new directories."""
    
    readmes = {
        'scripts/README.md': """# Scripts Directory

This directory contains utility scripts, debugging tools, and maintenance scripts.

## Categories:

### 🔧 **Utility Scripts**
- `apply_performance_optimizations.py` - Apply performance optimizations
- `setup_dashboard.py` - Set up Notion dashboard
- `create_database.py` - Database creation utilities

### 🐛 **Debug Scripts**
- `debug_*.py` - Various debugging utilities
- `quick_test.py` - Quick testing script
- `simple_test.py` - Simple pipeline test

### 🔍 **Analysis Scripts**
- `performance_benchmark.py` - Performance benchmarking
- `email_stats.py` - Email statistics analysis

### 🛠️ **Maintenance Scripts**
- `fix_*.py` - Various fix utilities
- `migrate_*.py` - Migration scripts
- `verify_*.py` - Verification utilities

## Usage
Run any script from the project root directory:
```bash
python scripts/script_name.py
```
""",
        
        'config/README.md': """# Configuration Directory

This directory contains configuration templates and examples.

## Files:
- `config.yaml.template` - Main configuration template
- `example-config.yaml` - Example configuration
- `*.env` - Environment configuration examples

## Usage:
1. Copy a template file
2. Rename it (remove .template)
3. Fill in your API keys and settings
4. Use with `--config` flag or place in root directory
""",
        
        'reports/README.md': """# Reports Directory

This directory contains analysis reports, summaries, and documentation of fixes and optimizations.

## Categories:

### 📊 **Performance Reports**
- Performance analysis and optimization reports
- Benchmark results and comparisons

### 🐛 **Bug Fix Summaries**
- Documentation of bugs found and fixed
- Integration test reports

### 🔍 **Analysis Documents**
- Feature analysis and strategy documents
- Token consumption and cost analysis

### 📈 **Optimization Summaries**
- Performance improvement documentation
- System optimization reports
""",
        
        'tools/README.md': """# Tools Directory

This directory is reserved for development tools and utilities.

Currently empty - tools will be added as needed.
""",
        
        'archive/README.md': """# Archive Directory

This directory contains old files, backups, and deprecated code that might be needed for reference.

## Contents:
- Old HTML files and raw data
- Deprecated scripts and configurations
- Backup files from major refactoring
"""
    }
    
    for file_path, content in readmes.items():
        with open(file_path, 'w') as f:
            f.write(content)

if __name__ == "__main__":
    reorganize_project()