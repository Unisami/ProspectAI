#!/usr/bin/env python3
"""
Windows-compatible progress indicators that avoid Unicode characters.
Provides alternatives to Rich library's SpinnerColumn for cross-platform compatibility.
"""

from rich.console import Console
from rich.progress import Progress, TextColumn
from typing import Optional
import time
import threading


class WindowsCompatibleProgress:
    """
    Windows-compatible progress indicator without Unicode characters.
    Alternative to Rich's SpinnerColumn that causes encoding errors on Windows.
    """
    
    def __init__(self, console: Optional[Console] = None):
        """
        Initialize Windows-compatible progress indicator.
        
        Args:
            console: Rich console instance (optional)
        """
        self.console = console or Console()
        self.active_tasks = {}
        self.step_counter = 0
        
    def create_simple_progress(self, description: str = "Working..."):
        """
        Create a simple progress context that uses plain text instead of Unicode spinners.
        
        Args:
            description: Initial description for the progress
            
        Returns:
            Context manager for simple progress tracking
        """
        return SimpleProgressContext(self.console, description)
    
    def show_step_progress(self, current_step: int, total_steps: int, description: str):
        """
        Show step-based progress without Unicode characters.
        
        Args:
            current_step: Current step number (1-based)
            total_steps: Total number of steps
            description: Description of current step
        """
        percentage = (current_step / total_steps) * 100
        self.console.print(f"[blue]Step {current_step}/{total_steps} ({percentage:.1f}%): {description}[/blue]")
    
    def print_simple_status(self, message: str, status: str = "info"):
        """
        Print status message with color coding.
        
        Args:
            message: Status message
            status: Status type ('info', 'success', 'warning', 'error')
        """
        color_map = {
            'info': 'blue',
            'success': 'green', 
            'warning': 'yellow',
            'error': 'red'
        }
        color = color_map.get(status, 'blue')
        self.console.print(f"[{color}]{message}[/{color}]")


class SimpleProgressContext:
    """Context manager for simple progress tracking without Unicode."""
    
    def __init__(self, console: Console, initial_description: str):
        self.console = console
        self.current_description = initial_description
        self.tasks = {}
        self.task_counter = 0
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.console.print("[green]Operation completed successfully![/green]")
        else:
            self.console.print(f"[red]Operation failed: {str(exc_val)}[/red]")
    
    def add_task(self, description: str, total: Optional[int] = None):
        """
        Add a new task to track.
        
        Args:
            description: Task description
            total: Total work units (ignored in simple mode)
            
        Returns:
            Task ID for updating progress
        """
        task_id = f"task_{self.task_counter}"
        self.task_counter += 1
        self.tasks[task_id] = {
            'description': description,
            'completed': False
        }
        self.console.print(f"[blue]Starting: {description}[/blue]")
        return task_id
    
    def update(self, task_id: str, description: Optional[str] = None, completed: Optional[bool] = None):
        """
        Update task progress.
        
        Args:
            task_id: Task ID returned from add_task
            description: New description (optional)
            completed: Whether task is completed (optional)
        """
        if task_id in self.tasks:
            if description:
                self.tasks[task_id]['description'] = description
            if completed is not None:
                self.tasks[task_id]['completed'] = completed
                if completed:
                    self.console.print(f"[green]Completed: {self.tasks[task_id]['description']}[/green]")


def create_windows_compatible_progress(console: Optional[Console] = None) -> WindowsCompatibleProgress:
    """
    Factory function to create Windows-compatible progress indicator.
    
    Args:
        console: Rich console instance (optional)
        
    Returns:
        WindowsCompatibleProgress instance
    """
    return WindowsCompatibleProgress(console)


def replace_spinner_progress(console: Console, description: str = "Working..."):
    """
    Direct replacement for SpinnerColumn-based Progress.
    Use this as a drop-in replacement in existing code.
    
    Args:
        console: Rich console instance
        description: Initial progress description
        
    Returns:
        SimpleProgressContext that mimics Progress behavior
    """
    progress_helper = WindowsCompatibleProgress(console)
    return progress_helper.create_simple_progress(description)


# Example usage and migration guide
if __name__ == "__main__":
    console = Console()
    
    # Example 1: Simple replacement for SpinnerColumn
    console.print("[blue]Example 1: Simple Progress Replacement[/blue]")
    
    with replace_spinner_progress(console, "Processing data...") as progress:
        task = progress.add_task("Loading configuration...")
        time.sleep(1)  # Simulate work
        progress.update(task, completed=True)
        
        task2 = progress.add_task("Connecting to services...")
        time.sleep(1)  # Simulate work
        progress.update(task2, completed=True)
    
    # Example 2: Step-based progress
    console.print("\n[blue]Example 2: Step-based Progress[/blue]")
    
    helper = create_windows_compatible_progress(console)
    
    total_steps = 3
    helper.show_step_progress(1, total_steps, "Initializing system")
    time.sleep(0.5)
    
    helper.show_step_progress(2, total_steps, "Processing data") 
    time.sleep(0.5)
    
    helper.show_step_progress(3, total_steps, "Finalizing results")
    time.sleep(0.5)
    
    helper.print_simple_status("All operations completed successfully!", "success")
    
    console.print("\n[green]Windows-compatible progress demonstration complete![/green]")