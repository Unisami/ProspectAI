#!/usr/bin/env python3
"""
Example Usage of Outreach Automation Setup Script
=================================================

This file shows different ways to use the setup_and_run.py script
for various automation scenarios.
"""

import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    """Run a command and show the result"""
    print(f"\n{'='*60}")
    print(f"🚀 {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("✅ Success!")
        if result.stdout:
            print("Output:", result.stdout[:500])  # First 500 chars
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed with exit code: {e.returncode}")
        if e.stderr:
            print("Error:", e.stderr[:500])
        return False

def main():
    """Main example function"""
    script_path = Path(__file__).parent / "setup_and_run.py"
    
    if not script_path.exists():
        print("❌ setup_and_run.py not found!")
        return 1
    
    print("🎯 Outreach Automation Tool - Usage Examples")
    print("=" * 60)
    
    # Show AI provider info first
    print("\n💡 Before starting, you might want to learn about AI providers:")
    print("   python show_ai_providers.py")
    
    examples = [
        {
            "cmd": [sys.executable, str(script_path), "--help"],
            "desc": "Show help and available options"
        },
        {
            "cmd": [sys.executable, str(script_path), "--action", "discover", "--limit", "5"],
            "desc": "Quick discovery of 5 companies (for testing)"
        },
        {
            "cmd": [sys.executable, str(script_path), "--action", "discover", "--limit", "20", "--campaign-name", "Test Campaign"],
            "desc": "Full discovery campaign with 20 companies"
        },
        {
            "cmd": [sys.executable, str(script_path), "--action", "process-company", "--company-name", "OpenAI"],
            "desc": "Process a specific company"
        },
        {
            "cmd": [sys.executable, str(script_path), "--action", "test"],
            "desc": "Test the system configuration"
        }
    ]
    
    print("\n📚 Available Examples:")
    for i, example in enumerate(examples, 1):
        print(f"{i}. {example['desc']}")
    
    choice = input("\nSelect an example to run (1-5, or 'q' to quit): ").strip()
    
    if choice.lower() == 'q':
        print("👋 Goodbye!")
        return 0
    
    try:
        example_index = int(choice) - 1
        if 0 <= example_index < len(examples):
            example = examples[example_index]
            
            # Ask for confirmation
            confirm = input(f"\nRun: {' '.join(example['cmd'])}\nContinue? (y/n): ").strip().lower()
            
            if confirm == 'y':
                success = run_command(example['cmd'], example['desc'])
                return 0 if success else 1
            else:
                print("❌ Cancelled by user")
                return 0
        else:
            print("❌ Invalid choice")
            return 1
    
    except ValueError:
        print("❌ Invalid input")
        return 1

if __name__ == "__main__":
    sys.exit(main())
