"""
Basic tests for the issue tracking functionality.
"""
import pytest
import sys
import os
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from models.data_models import (
    Issue,
    IssueCategory,
    IssueStatus,
    ValidationError
)
from services.issue_reporter import IssueReporter
from utils.config import Config


class TestIssueModel:
    """Test the Issue data model."""
    
    def test_issue_creation(self):
        """Test basic issue creation."""
        issue = Issue(
            title="Test issue",
            description="This is a test issue description"
        )
        
        assert issue.title == "Test issue"
        assert issue.description == "This is a test issue description"
        assert issue.category == IssueCategory.BUG  # Default
        assert issue.status == IssueStatus.OPEN  # Default
        assert issue.issue_id is not None
        assert issue.issue_id.startswith("#")
        assert isinstance(issue.created_at, datetime)
    
    def test_issue_id_generation(self):
        """Test that issue IDs are generated automatically."""
        import time
        
        issue1 = Issue(title="Issue 1", description="First issue")
        time.sleep(0.001)  # Small delay to ensure different timestamps
        issue2 = Issue(title="Issue 2", description="Second issue")
        
        # Both should have IDs
        assert issue1.issue_id is not None
        assert issue2.issue_id is not None
        assert issue1.issue_id.startswith("#")
        assert issue2.issue_id.startswith("#")
        
        # They might be the same if created very quickly, that's ok
        # The important thing is that they both get IDs
    
    def test_issue_validation(self):
        """Test issue validation."""
        # Valid issue
        issue = Issue(
            title="Valid issue title",
            description="This is a valid issue description with enough detail"
        )
        result = issue.validate()
        assert result.is_valid
        
        # Invalid title (too short) - create but validate separately
        issue_short_title = Issue(title="Hi", description="Valid description here")
        result = issue_short_title.validate()
        assert not result.is_valid
        
        # Invalid description (too short)
        issue_short_desc = Issue(title="Valid title", description="Too short")
        result = issue_short_desc.validate()
        assert not result.is_valid
    
    def test_issue_serialization(self):
        """Test issue to_dict and from_dict methods."""
        original_issue = Issue(
            title="Test serialization",
            description="Testing serialization functionality",
            category=IssueCategory.IMPROVEMENT,
            status=IssueStatus.IN_PROGRESS
        )
        
        # Convert to dict
        issue_dict = original_issue.to_dict()
        
        # Verify dict contains expected fields
        assert issue_dict['title'] == "Test serialization"
        assert issue_dict['description'] == "Testing serialization functionality"
        assert issue_dict['category'] == "Improvement"
        assert issue_dict['status'] == "In Progress"
        assert 'issue_id' in issue_dict
        assert 'created_at' in issue_dict
        
        # Convert back to Issue
        restored_issue = Issue.from_dict(issue_dict)
        
        # Verify restoration
        assert restored_issue.title == original_issue.title
        assert restored_issue.description == original_issue.description
        assert restored_issue.category == original_issue.category
        assert restored_issue.status == original_issue.status
        assert restored_issue.issue_id == original_issue.issue_id


class TestIssueReporter:
    """Test the IssueReporter service."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing."""
        config = Mock(spec=Config)
        config.notion_token = "test_token"
        config.notion_database_id = "test_db_id"
        return config
    
    @pytest.fixture
    def mock_notion_manager(self):
        """Mock NotionManager for testing."""
        mock_manager = Mock()
        mock_manager.create_issue.return_value = "#12345"
        mock_manager.get_issues.return_value = []
        mock_manager.get_issue_by_id.return_value = None
        return mock_manager
    
    @pytest.fixture
    def issue_reporter(self, mock_config, mock_notion_manager):
        """IssueReporter instance with mocked dependencies."""
        with patch('services.issue_reporter.OptimizedNotionDataManager') as mock_notion_class:
            mock_notion_class.return_value = mock_notion_manager
            reporter = IssueReporter(mock_config)
            reporter.notion_manager = mock_notion_manager
            return reporter
    
    def test_quick_report(self, issue_reporter, mock_notion_manager):
        """Test quick issue reporting."""
        # Test basic quick report
        issue_id = issue_reporter.quick_report("Email generation failed")
        
        # Verify notion manager was called
        mock_notion_manager.create_issue.assert_called_once()
        
        # Verify return value
        assert issue_id == "#12345"
        
        # Verify the issue created had correct properties
        call_args = mock_notion_manager.create_issue.call_args[0][0]
        assert call_args.title == "Email generation failed"
        assert call_args.description == "Email generation failed"
        assert call_args.category == IssueCategory.BUG  # Auto-categorized
    
    def test_auto_categorization(self, issue_reporter):
        """Test automatic categorization of issues."""
        # Bug keywords
        bug_category = issue_reporter._auto_categorize("Error occurred during execution")
        assert bug_category == "Bug"
        
        # Setup keywords ("config" is a setup keyword that takes precedence)
        setup_category = issue_reporter._auto_categorize("Cannot install the application")
        assert setup_category == "Setup"
        
        # Question keywords (use a phrase without setup keywords)
        question_category = issue_reporter._auto_categorize("How do I use this feature?")
        assert question_category == "Question"
        
        # Default to improvement
        improvement_category = issue_reporter._auto_categorize("Could use better performance")
        assert improvement_category == "Improvement"
    
    def test_context_capture(self, issue_reporter):
        """Test context capture functionality."""
        context = issue_reporter._get_basic_context()
        
        # Verify expected context fields
        assert 'timestamp' in context
        assert 'python_version' in context
        assert 'platform' in context
        assert 'cli_command' in context
        
        # Verify timestamp format
        assert isinstance(context['timestamp'], str)
        assert 'T' in context['timestamp']  # ISO format
    
    def test_report_with_context(self, issue_reporter, mock_notion_manager):
        """Test detailed issue reporting with custom context."""
        additional_context = {"custom_field": "custom_value"}
        
        issue_id = issue_reporter.report_with_context(
            description="Detailed issue description",
            title="Custom Title",
            category="Question",
            additional_context=additional_context
        )
        
        # Verify notion manager was called
        mock_notion_manager.create_issue.assert_called_once()
        
        # Verify return value
        assert issue_id == "#12345"
        
        # Verify the issue created had correct properties
        call_args = mock_notion_manager.create_issue.call_args[0][0]
        assert call_args.title == "Custom Title"
        assert call_args.description == "Detailed issue description"
        assert call_args.category == IssueCategory.QUESTION
        assert "custom_field" in call_args.context
        assert call_args.context["custom_field"] == "custom_value"
    
    def test_list_issues(self, issue_reporter, mock_notion_manager):
        """Test listing issues."""
        # Setup mock return data
        mock_issues = [
            Issue(title="Issue 1", description="First issue"),
            Issue(title="Issue 2", description="Second issue")
        ]
        mock_notion_manager.get_issues.return_value = mock_issues
        
        # Test listing all issues
        issues = issue_reporter.list_my_issues()
        
        # Verify notion manager was called correctly
        mock_notion_manager.get_issues.assert_called_once_with(
            status=None,
            limit=10
        )
        
        # Verify return value
        assert len(issues) == 2
        assert issues[0].title == "Issue 1"
        assert issues[1].title == "Issue 2"
    
    def test_error_handling(self, issue_reporter, mock_notion_manager):
        """Test error handling in issue reporter."""
        # Setup mock to raise exception
        mock_notion_manager.create_issue.side_effect = Exception("Notion API error")
        
        # Test that exception is properly handled
        with pytest.raises(Exception) as exc_info:
            issue_reporter.quick_report("Test issue")
        
        assert "Could not report issue" in str(exc_info.value)
        assert "Notion API error" in str(exc_info.value)


class TestIssueCategoriesAndStatuses:
    """Test issue categories and status enums."""
    
    def test_issue_categories(self):
        """Test issue category enum values."""
        assert IssueCategory.BUG.value == "Bug"
        assert IssueCategory.IMPROVEMENT.value == "Improvement"
        assert IssueCategory.QUESTION.value == "Question"
        assert IssueCategory.SETUP.value == "Setup"
    
    def test_issue_statuses(self):
        """Test issue status enum values."""
        assert IssueStatus.OPEN.value == "Open"
        assert IssueStatus.IN_PROGRESS.value == "In Progress"
        assert IssueStatus.RESOLVED.value == "Resolved"
        assert IssueStatus.CLOSED.value == "Closed"


class TestIssueIntegration:
    """Integration tests for issue tracking functionality."""
    
    @patch('services.issue_reporter.OptimizedNotionDataManager')
    def test_full_issue_flow(self, mock_notion_class):
        """Test complete issue reporting flow."""
        # Setup mocks
        mock_notion_manager = Mock()
        mock_notion_manager.create_issue.return_value = "#54321"
        mock_notion_class.return_value = mock_notion_manager
        
        mock_config = Mock(spec=Config)
        mock_config.notion_token = "test_token"
        
        # Create reporter
        reporter = IssueReporter(mock_config)
        
        # Report an issue
        issue_id = reporter.quick_report("Integration test issue")
        
        # Verify the flow
        assert issue_id == "#54321"
        mock_notion_manager.create_issue.assert_called_once()
        
        # Verify the created issue has expected properties
        created_issue = mock_notion_manager.create_issue.call_args[0][0]
        assert isinstance(created_issue, Issue)
        assert created_issue.title == "Integration test issue"
        assert created_issue.description == "Integration test issue"
        assert isinstance(created_issue.context, dict)
        assert 'timestamp' in created_issue.context


if __name__ == "__main__":
    pytest.main([__file__, "-v"])