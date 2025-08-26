"""
Simple issue reporting service for capturing user feedback and technical issues.
"""
import sys
import platform
import logging
from typing import (
    List,
    Optional,
    Dict,
    Any
)
from datetime import datetime

from models.data_models import (
    Issue,
    IssueCategory,
    IssueStatus,
    ValidationError
)
from utils.config import Config
from services.notion_manager import OptimizedNotionDataManager

logger = logging.getLogger(__name__)


class IssueReporter:
    """Simple issue reporting service that captures user feedback with basic context."""
    
    def __init__(self, config: Config):
        """
        Initialize issue reporter.
        
        Args:
            config: Configuration object containing Notion credentials
        """
        self.config = config
        self.notion_manager = OptimizedNotionDataManager(config)
    
    def quick_report(self, message: str, category: Optional[str] = None) -> str:
        """
        Quickly report an issue with minimal context.
        
        Args:
            message: Brief description of the issue
            category: Optional category (Bug, Improvement, Question, Setup)
            
        Returns:
            Issue ID for tracking
            
        Raises:
            Exception: If issue creation fails
        """
        try:
            # Auto-categorize if not provided
            if not category:
                category = self._auto_categorize(message)
            
            # Validate category
            category_enum = self._parse_category(category)
            
            # Create issue with basic context
            issue = Issue(
                title=self._generate_title(message),
                description=message,
                category=category_enum,
                context=self._get_basic_context()
            )
            
            # Store in Notion
            issue_id = self.notion_manager.create_issue(issue)
            
            logger.info(f"Issue reported successfully: {issue_id}")
            return issue_id
            
        except Exception as e:
            logger.error(f"Failed to report issue: {str(e)}")
            raise Exception(f"Could not report issue: {str(e)}")
    
    def report_with_context(self, description: str, title: Optional[str] = None, 
                          category: Optional[str] = None, 
                          additional_context: Optional[Dict[str, Any]] = None) -> str:
        """
        Report an issue with custom context and details.
        
        Args:
            description: Detailed description of the issue
            title: Optional custom title
            category: Issue category
            additional_context: Extra context information
            
        Returns:
            Issue ID for tracking
        """
        try:
            # Generate title if not provided
            if not title:
                title = self._generate_title(description)
            
            # Auto-categorize if not provided
            if not category:
                category = self._auto_categorize(description)
            
            category_enum = self._parse_category(category)
            
            # Combine contexts
            context = self._get_basic_context()
            if additional_context:
                context.update(additional_context)
            
            # Create issue
            issue = Issue(
                title=title,
                description=description,
                category=category_enum,
                context=context
            )
            
            # Validate before storing
            validation_result = issue.validate()
            if not validation_result.is_valid:
                raise ValidationError(f"Issue validation failed: {validation_result.message}")
            
            # Store in Notion
            issue_id = self.notion_manager.create_issue(issue)
            
            logger.info(f"Issue reported with context: {issue_id}")
            return issue_id
            
        except Exception as e:
            logger.error(f"Failed to report issue with context: {str(e)}")
            raise Exception(f"Could not report issue: {str(e)}")
    
    def list_my_issues(self, status: Optional[str] = None, limit: int = 10) -> List[Issue]:
        """
        List user's reported issues.
        
        Args:
            status: Filter by status (Open, In Progress, Resolved, Closed)
            limit: Maximum number of issues to return
            
        Returns:
            List of issues
        """
        try:
            status_filter = None
            if status:
                status_filter = self._parse_status(status)
            
            issues = self.notion_manager.get_issues(
                status=status_filter,
                limit=limit
            )
            
            logger.info(f"Retrieved {len(issues)} issues")
            return issues
            
        except Exception as e:
            logger.error(f"Failed to list issues: {str(e)}")
            return []
    
    def get_issue(self, issue_id: str) -> Optional[Issue]:
        """
        Get a specific issue by ID.
        
        Args:
            issue_id: Issue identifier
            
        Returns:
            Issue object or None if not found
        """
        try:
            issue = self.notion_manager.get_issue_by_id(issue_id)
            return issue
        except Exception as e:
            logger.error(f"Failed to get issue {issue_id}: {str(e)}")
            return None
    
    def _get_basic_context(self) -> Dict[str, Any]:
        """
        Capture minimal useful context for debugging.
        
        Returns:
            Dictionary with basic system context
        """
        context = {
            'timestamp': datetime.now().isoformat(),
            'python_version': sys.version,
            'platform': platform.system(),
            'platform_version': platform.version(),
            'cli_command': ' '.join(sys.argv)
        }
        
        # Add any additional runtime context
        try:
            import os
            context['working_directory'] = os.getcwd()
            context['environment_variables'] = {
                'AI_PROVIDER': os.getenv('AI_PROVIDER', 'not_set'),
                'AI_MODEL': os.getenv('AI_MODEL', 'not_set')
            }
        except Exception:
            pass  # Don't fail if we can't get additional context
        
        return context
    
    def _generate_title(self, description: str) -> str:
        """
        Generate a concise title from the description.
        
        Args:
            description: Issue description
            
        Returns:
            Generated title (max 50 characters)
        """
        # Take first sentence or first 50 characters
        title = description.split('.')[0].strip()
        if len(title) > 50:
            title = title[:47] + "..."
        
        return title if title else "User reported issue"
    
    def _auto_categorize(self, text: str) -> str:
        """
        Automatically categorize issue based on keywords.
        
        Args:
            text: Issue text to analyze
            
        Returns:
            Category string
        """
        text_lower = text.lower()
        
        # Bug keywords
        bug_keywords = ['error', 'failed', 'crash', 'broken', 'bug', 'exception', 'traceback']
        if any(keyword in text_lower for keyword in bug_keywords):
            return 'Bug'
        
        # Setup keywords
        setup_keywords = ['install', 'setup', 'config', 'api key', 'permission', 'database']
        if any(keyword in text_lower for keyword in setup_keywords):
            return 'Setup'
        
        # Question keywords
        question_keywords = ['how', 'what', 'why', 'help', '?', 'explain']
        if any(keyword in text_lower for keyword in question_keywords):
            return 'Question'
        
        # Default to improvement
        return 'Improvement'
    
    def _parse_category(self, category: str) -> IssueCategory:
        """Parse category string to enum."""
        if not category:
            return IssueCategory.BUG
        
        category_map = {
            'bug': IssueCategory.BUG,
            'improvement': IssueCategory.IMPROVEMENT,
            'question': IssueCategory.QUESTION,
            'setup': IssueCategory.SETUP
        }
        
        return category_map.get(category.lower(), IssueCategory.BUG)
    
    def _parse_status(self, status: str) -> IssueStatus:
        """Parse status string to enum."""
        if not status:
            return IssueStatus.OPEN
        
        status_map = {
            'open': IssueStatus.OPEN,
            'in progress': IssueStatus.IN_PROGRESS,
            'resolved': IssueStatus.RESOLVED,
            'closed': IssueStatus.CLOSED
        }
        
        return status_map.get(status.lower(), IssueStatus.OPEN)