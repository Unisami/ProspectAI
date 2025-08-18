"""
Unit tests for the consolidated AI Service.

This module tests all AI operations including LinkedIn parsing, email generation,
product analysis, team extraction, and business metrics analysis.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from services.ai_service import (
    AIService, AIOperationType, EmailTemplate, ProductInfo, 
    BusinessMetrics, AIResult, ValidationResult
)
from models.data_models import (
    LinkedInProfile, TeamMember, Prospect, EmailContent, SenderProfile
)
from utils.config import Config
from services.openai_client_manager import CompletionResponse


class TestAIService:
    """Test cases for the AIService class."""
    
    # Using shared mock_config fixture from conftest.py
    
    @pytest.fixture
    def mock_client_manager(self):
        """Create a mock OpenAI client manager."""
        with patch('services.ai_service.get_client_manager') as mock:
            client_manager = Mock()
            mock.return_value = client_manager
            yield client_manager
    
    @pytest.fixture
    def ai_service(self, mock_config, mock_client_manager):
        """Create an AIService instance for testing."""
        return AIService(mock_config, "test_client")
    
    def test_initialization(self, mock_config, mock_client_manager):
        """Test AIService initialization."""
        service = AIService(mock_config, "test_client")
        
        assert service.client_id == "test_client"
        assert service.client_manager == mock_client_manager
        assert service.service_config.name == "AIService"
        assert service.service_config.enable_caching is True
        mock_client_manager.configure.assert_called_once_with(mock_config, "test_client")
    
    def test_parse_linkedin_profile_success(self, ai_service, mock_client_manager):
        """Test successful LinkedIn profile parsing."""
        # Mock successful AI response
        mock_response = CompletionResponse(
            content='{"name": "John Doe", "current_role": "Software Engineer at TechCorp", "experience": ["Senior Dev at StartupCo"], "skills": ["Python", "JavaScript"], "summary": "Experienced developer"}',
            model="gpt-3.5-turbo",
            usage={"total_tokens": 100},
            finish_reason="stop",
            success=True
        )
        mock_client_manager.make_completion.return_value = mock_response
        
        # Test the method
        result = ai_service.parse_linkedin_profile("<html>LinkedIn profile content</html>")
        
        # Assertions
        assert result.success is True
        assert result.operation_type == AIOperationType.LINKEDIN_PARSING
        assert isinstance(result.data, LinkedInProfile)
        assert result.data.name == "John Doe"
        assert result.data.current_role == "Software Engineer at TechCorp"
        assert result.data.skills == ["Python", "JavaScript"]
        assert result.confidence_score > 0
        assert result.cached is False
    
    def test_parse_linkedin_profile_with_cache(self, ai_service, mock_client_manager):
        """Test LinkedIn profile parsing with caching."""
        # Mock successful AI response
        mock_response = CompletionResponse(
            content='{"name": "John Doe", "current_role": "Software Engineer", "experience": [], "skills": [], "summary": ""}',
            model="gpt-3.5-turbo",
            usage={"total_tokens": 100},
            finish_reason="stop",
            success=True
        )
        mock_client_manager.make_completion.return_value = mock_response
        
        # First call
        result1 = ai_service.parse_linkedin_profile("<html>test content</html>")
        assert result1.cached is False
        
        # Second call should return cached result
        result2 = ai_service.parse_linkedin_profile("<html>test content</html>")
        assert result2.cached is True
        assert result2.data.name == result1.data.name
        
        # Should only call AI once
        assert mock_client_manager.make_completion.call_count == 1
    
    def test_parse_linkedin_profile_with_fallback(self, ai_service, mock_client_manager):
        """Test LinkedIn profile parsing with fallback data."""
        # Mock failed AI response
        mock_response = CompletionResponse(
            content="Invalid response",
            model="gpt-3.5-turbo",
            usage={},
            finish_reason="error",
            success=False,
            error_message="API error"
        )
        mock_client_manager.make_completion.return_value = mock_response
        
        # Fallback data
        fallback_data = {
            "name": "Jane Smith",
            "current_role": "Product Manager",
            "experience": ["PM at TechCorp"],
            "skills": ["Product Management"],
            "summary": "Experienced PM"
        }
        
        # Test with fallback
        result = ai_service.parse_linkedin_profile("<html>content</html>", fallback_data)
        
        # Should succeed with fallback data
        assert result.success is True
        assert result.data.name == "Jane Smith"
        assert result.confidence_score == 0.3  # Lower confidence for fallback
        assert "fallback" in result.error_message.lower()
    
    def test_generate_email_success(self, ai_service, mock_client_manager):
        """Test successful email generation."""
        # Mock successful AI response
        mock_response = CompletionResponse(
            content='Subject: Exciting opportunity at TechCorp\n\nHi John,\n\nI discovered TechCorp through ProductHunt and was impressed by your innovative product...',
            model="gpt-3.5-turbo",
            usage={"total_tokens": 150},
            finish_reason="stop",
            success=True
        )
        mock_client_manager.make_completion.return_value = mock_response
        
        # Create test prospect
        prospect = Prospect(
            id="test-id",
            name="John Doe",
            role="CTO",
            company="TechCorp",
            linkedin_url="https://linkedin.com/in/johndoe",
            email="john@techcorp.com",
            source_url="https://producthunt.com/posts/techcorp",
            notes="Innovative startup"
        )
        
        # Test email generation
        result = ai_service.generate_email(prospect, EmailTemplate.COLD_OUTREACH)
        
        # Assertions
        assert result.success is True
        assert result.operation_type == AIOperationType.EMAIL_GENERATION
        assert isinstance(result.data, EmailContent)
        assert result.data.subject == "Exciting opportunity at TechCorp"
        assert "ProductHunt" in result.data.body
        assert result.data.recipient_name == "John Doe"
        assert result.data.company_name == "TechCorp"
        assert result.confidence_score > 0
    
    def test_generate_email_with_personalization(self, ai_service, mock_client_manager):
        """Test email generation with full personalization data."""
        # Mock successful AI response
        mock_response = CompletionResponse(
            content='Subject: Your Python expertise at TechCorp\n\nHi John,\n\nI found TechCorp on ProductHunt and was impressed by your AI platform...',
            model="gpt-3.5-turbo",
            usage={"total_tokens": 200},
            finish_reason="stop",
            success=True
        )
        mock_client_manager.make_completion.return_value = mock_response
        
        # Create test data
        prospect = Prospect(
            id="test-id",
            name="John Doe",
            role="CTO",
            company="TechCorp",
            linkedin_url="https://linkedin.com/in/johndoe",
            email="john@techcorp.com",
            source_url="https://producthunt.com/posts/techcorp",
            notes="AI startup"
        )
        
        linkedin_profile = LinkedInProfile(
            name="John Doe",
            current_role="CTO at TechCorp",
            experience=["Senior Engineer at BigTech", "Lead Developer at StartupCo"],
            skills=["Python", "Machine Learning", "Leadership"],
            summary="Experienced technology leader with expertise in AI and machine learning"
        )
        
        product_info = ProductInfo(
            name="TechCorp AI Platform",
            description="Revolutionary AI platform for businesses",
            features=["Natural Language Processing", "Predictive Analytics", "Real-time Insights"],
            pricing_model="subscription",
            target_market="Enterprise businesses",
            competitors=["CompetitorA", "CompetitorB"],
            funding_status="Series A",
            market_analysis="Growing market with strong demand"
        )
        
        sender_profile = SenderProfile(
            name="Alice Johnson",
            current_role="Senior Software Engineer",
            years_experience=5,
            key_skills=["Python", "AI/ML", "Backend Development"],
            experience_summary="5 years of experience in AI and machine learning",
            value_proposition="Passionate about building scalable AI solutions"
        )
        
        # Test with full personalization
        result = ai_service.generate_email(
            prospect=prospect,
            template_type=EmailTemplate.COLD_OUTREACH,
            linkedin_profile=linkedin_profile,
            product_analysis=product_info,
            sender_profile=sender_profile
        )
        
        # Assertions
        assert result.success is True
        assert isinstance(result.data, EmailContent)
        assert result.data.personalization_score > 0.3  # Should be reasonably personalized
    
    def test_analyze_product_success(self, ai_service, mock_client_manager):
        """Test successful product analysis."""
        # Mock successful AI response
        mock_response = CompletionResponse(
            content='{"name": "TechCorp Platform", "description": "AI-powered business platform", "features": ["AI Analytics", "Real-time Data"], "pricing_model": "subscription", "target_market": "SMB", "competitors": ["CompetitorA"], "funding_status": "Series A", "market_analysis": "Growing market"}',
            model="gpt-3.5-turbo",
            usage={"total_tokens": 200},
            finish_reason="stop",
            success=True
        )
        mock_client_manager.make_completion.return_value = mock_response
        
        # Test product analysis
        result = ai_service.analyze_product(
            "Product content from ProductHunt page...",
            "https://producthunt.com/posts/techcorp"
        )
        
        # Assertions
        assert result.success is True
        assert result.operation_type == AIOperationType.PRODUCT_ANALYSIS
        assert isinstance(result.data, ProductInfo)
        assert result.data.name == "TechCorp Platform"
        assert result.data.description == "AI-powered business platform"
        assert "AI Analytics" in result.data.features
        assert result.data.pricing_model == "subscription"
        assert result.confidence_score > 0
    
    def test_extract_team_data_success(self, ai_service, mock_client_manager):
        """Test successful team data extraction."""
        # Mock successful AI response
        mock_response = CompletionResponse(
            content='[{"name": "John Smith", "role": "CEO", "company": "TechCorp", "linkedin_url": "https://linkedin.com/in/johnsmith"}, {"name": "Jane Doe", "role": "CTO", "company": "TechCorp", "linkedin_url": null}]',
            model="gpt-3.5-turbo",
            usage={"total_tokens": 150},
            finish_reason="stop",
            success=True
        )
        mock_client_manager.make_completion.return_value = mock_response
        
        # Test team extraction
        result = ai_service.extract_team_data(
            "Team information: John Smith is the CEO and Jane Doe is the CTO...",
            "TechCorp"
        )
        
        # Assertions
        assert result.success is True
        assert result.operation_type == AIOperationType.TEAM_EXTRACTION
        assert isinstance(result.data, list)
        assert len(result.data) == 2
        assert all(isinstance(member, TeamMember) for member in result.data)
        assert result.data[0].name == "John Smith"
        assert result.data[0].role == "CEO"
        assert result.data[1].name == "Jane Doe"
        assert result.data[1].role == "CTO"
        assert result.confidence_score == 1.0  # All members parsed successfully
    
    def test_extract_business_metrics_success(self, ai_service, mock_client_manager):
        """Test successful business metrics extraction."""
        # Mock successful AI response
        mock_response = CompletionResponse(
            content='{"employee_count": 25, "funding_amount": "$2M Series A", "growth_stage": "early-stage startup", "key_metrics": {"users": "10K+ active users", "revenue": "$500K ARR"}, "business_model": "B2B SaaS", "revenue_model": "subscription", "market_position": "Emerging player in AI space"}',
            model="gpt-3.5-turbo",
            usage={"total_tokens": 180},
            finish_reason="stop",
            success=True
        )
        mock_client_manager.make_completion.return_value = mock_response
        
        # Test business metrics extraction
        result = ai_service.extract_business_metrics(
            "Company data: TechCorp has 25 employees, raised $2M Series A...",
            "TechCorp"
        )
        
        # Assertions
        assert result.success is True
        assert result.operation_type == AIOperationType.BUSINESS_METRICS
        assert isinstance(result.data, BusinessMetrics)
        assert result.data.employee_count == 25
        assert result.data.funding_amount == "$2M Series A"
        assert result.data.growth_stage == "early-stage startup"
        assert result.data.business_model == "B2B SaaS"
        assert result.data.key_metrics["users"] == "10K+ active users"
        assert result.confidence_score > 0
    
    def test_validate_email_content_valid(self, ai_service):
        """Test email content validation for valid content."""
        valid_content = """
        Hi John,
        
        I discovered TechCorp through ProductHunt and was impressed by your innovative AI platform.
        As a software engineer with 5 years of experience in machine learning, I'd love to learn
        more about your team and discuss potential opportunities.
        
        Would you be open to a brief 15-minute conversation next week?
        
        Best regards,
        Alice
        """
        
        result = ai_service.validate_email_content(valid_content)
        
        assert result.is_valid is True
        assert len(result.issues) == 0
        assert result.spam_score < 0.3
        assert len(result.suggestions) == 0
    
    def test_validate_email_content_invalid(self, ai_service):
        """Test email content validation for invalid content."""
        invalid_content = """
        URGENT!!! ACT NOW!!! LIMITED TIME OFFER!!!
        
        Click here to get FREE MONEY guaranteed with no obligation!
        This is a RISK FREE opportunity that you MUST NOT MISS!
        
        CALL NOW!!!
        """
        
        result = ai_service.validate_email_content(invalid_content)
        
        assert result.is_valid is False
        assert len(result.issues) > 0
        assert result.spam_score >= 0.3
        assert "ProductHunt" in str(result.issues)  # Should mention missing ProductHunt reference
        # Check for either capitalization or exclamation mark issues
        issues_str = str(result.issues).lower()
        assert "exclamation" in issues_str or "capitalization" in issues_str
    
    def test_validate_email_content_too_short(self, ai_service):
        """Test email content validation for too short content."""
        short_content = "Hi John, interested in your company."
        
        result = ai_service.validate_email_content(short_content)
        
        assert result.is_valid is False
        assert "too short" in str(result.issues).lower()
        assert "more personalized content" in str(result.suggestions).lower()
    
    def test_validate_email_content_too_long(self, ai_service):
        """Test email content validation for too long content."""
        long_content = "Hi John, " + "This is a very long email. " * 100  # Very long content
        
        result = ai_service.validate_email_content(long_content)
        
        assert result.is_valid is False
        assert "too long" in str(result.issues).lower()
        assert "concise" in str(result.suggestions).lower()
    
    def test_cache_functionality(self, ai_service, mock_client_manager):
        """Test caching functionality across different operations."""
        # Mock AI response
        mock_response = CompletionResponse(
            content='{"name": "Test Product", "description": "Test description", "features": [], "pricing_model": "free", "target_market": "developers", "competitors": [], "funding_status": null, "market_analysis": ""}',
            model="gpt-3.5-turbo",
            usage={"total_tokens": 100},
            finish_reason="stop",
            success=True
        )
        mock_client_manager.make_completion.return_value = mock_response
        
        # First call
        result1 = ai_service.analyze_product("test content")
        assert result1.cached is False
        
        # Second call with same content should be cached
        result2 = ai_service.analyze_product("test content")
        assert result2.cached is True
        
        # Different content should not be cached
        result3 = ai_service.analyze_product("different content")
        assert result3.cached is False
        
        # Verify cache stats
        cache_stats = ai_service.get_cache_stats()
        assert cache_stats['total_entries'] == 2
        assert cache_stats['cache_enabled'] is True
        
        # Clear cache
        ai_service.clear_cache()
        cache_stats_after_clear = ai_service.get_cache_stats()
        assert cache_stats_after_clear['total_entries'] == 0
    
    def test_error_handling(self, ai_service, mock_client_manager):
        """Test error handling for AI operations."""
        # Mock failed AI response
        mock_response = CompletionResponse(
            content="",
            model="gpt-3.5-turbo",
            usage={},
            finish_reason="error",
            success=False,
            error_message="Rate limit exceeded"
        )
        mock_client_manager.make_completion.return_value = mock_response
        
        # Test failed operation
        result = ai_service.analyze_product("test content")
        
        assert result.success is False
        assert result.data is None
        assert "Rate limit exceeded" in result.error_message
        assert result.operation_type == AIOperationType.PRODUCT_ANALYSIS
    
    def test_invalid_json_handling(self, ai_service, mock_client_manager):
        """Test handling of invalid JSON responses from AI."""
        # Mock AI response with invalid JSON
        mock_response = CompletionResponse(
            content="This is not valid JSON content",
            model="gpt-3.5-turbo",
            usage={"total_tokens": 50},
            finish_reason="stop",
            success=True
        )
        mock_client_manager.make_completion.return_value = mock_response
        
        # Test operation with invalid JSON
        result = ai_service.analyze_product("test content")
        
        assert result.success is False
        assert result.data is None
        assert "JSON" in result.error_message
    
    def test_confidence_score_calculation(self, ai_service):
        """Test confidence score calculation for different operation types."""
        # Test LinkedIn parsing confidence
        linkedin_data = {
            "name": "John Doe",
            "current_role": "Software Engineer",
            "experience": ["Previous role"],
            "skills": ["Python", "JavaScript"],
            "summary": "Experienced developer"
        }
        score = ai_service._calculate_confidence_score(linkedin_data, AIOperationType.LINKEDIN_PARSING)
        assert 0.8 <= score <= 1.0  # Should be high confidence with all fields
        
        # Test product analysis confidence
        product_data = {
            "name": "Test Product",
            "description": "Test description",
            "features": ["Feature 1"],
            "pricing_model": "subscription",
            "target_market": "developers",
            "competitors": ["Competitor 1"]
        }
        score = ai_service._calculate_confidence_score(product_data, AIOperationType.PRODUCT_ANALYSIS)
        assert 0.7 <= score <= 1.0  # Should be high confidence
        
        # Test business metrics confidence
        metrics_data = {
            "employee_count": 25,
            "funding_amount": "$2M",
            "growth_stage": "early-stage",
            "business_model": "SaaS",
            "revenue_model": "subscription",
            "key_metrics": {"users": "10K"}
        }
        score = ai_service._calculate_confidence_score(metrics_data, AIOperationType.BUSINESS_METRICS)
        assert 0.9 <= score <= 1.0  # Should be very high confidence
    
    def test_personalization_score_calculation(self, ai_service):
        """Test personalization score calculation for email generation."""
        personalization_data = {
            "name": "John Doe",
            "company": "TechCorp",
            "product_name": "AI Platform",
            "skills": "Python, Machine Learning",
            "sender_name": "Alice Johnson"
        }
        
        # High personalization email
        high_personalization_body = """
        Hi John Doe,
        
        I discovered TechCorp through ProductHunt and was impressed by your AI Platform.
        As someone with experience in Python and Machine Learning, I'd love to discuss
        potential opportunities with your team.
        
        Best regards,
        Alice Johnson
        """
        
        score = ai_service._calculate_personalization_score(high_personalization_body, personalization_data)
        assert score >= 0.7  # Should be high personalization
        
        # Low personalization email
        low_personalization_body = """
        Hi there,
        
        I'm interested in your company and would like to discuss opportunities.
        
        Best regards,
        Someone
        """
        
        score = ai_service._calculate_personalization_score(low_personalization_body, personalization_data)
        assert score <= 0.3  # Should be low personalization
    
    def test_health_check(self, ai_service, mock_client_manager):
        """Test health check functionality."""
        # Mock successful health check
        mock_response = CompletionResponse(
            content="Hello",
            model="gpt-3.5-turbo",
            usage={"total_tokens": 5},
            finish_reason="stop",
            success=True
        )
        mock_client_manager.make_completion.return_value = mock_response
        
        health_status = ai_service.health_check()
        
        assert health_status['service'] == 'AIService'
        assert health_status['status'] == 'healthy'
        assert 'metrics' in health_status
        
        # Mock failed health check
        mock_response.success = False
        mock_response.error_message = "Connection failed"
        mock_client_manager.make_completion.return_value = mock_response
        
        health_status = ai_service.health_check()
        assert health_status['status'] == 'unhealthy'
        # Note: 'error' key is only present when an exception occurs, not when health check returns False
    
    def test_performance_metrics(self, ai_service, mock_client_manager):
        """Test performance metrics tracking."""
        # Mock successful AI response
        mock_response = CompletionResponse(
            content='{"name": "Test", "description": "Test", "features": [], "pricing_model": "free", "target_market": "test", "competitors": [], "funding_status": null, "market_analysis": ""}',
            model="gpt-3.5-turbo",
            usage={"total_tokens": 50},
            finish_reason="stop",
            success=True
        )
        mock_client_manager.make_completion.return_value = mock_response
        
        # Perform some operations
        ai_service.analyze_product("test content 1")
        ai_service.analyze_product("test content 2")
        
        # Check metrics
        metrics = ai_service.get_performance_metrics()
        
        assert metrics['service_name'] == 'AIService'
        assert metrics['total_operations'] >= 2
        assert 'analyze_product' in metrics['operations']
        assert metrics['operations']['analyze_product']['count'] >= 2
        
        # Reset metrics
        ai_service.reset_metrics()
        metrics_after_reset = ai_service.get_performance_metrics()
        assert metrics_after_reset['total_operations'] == 0


class TestAIServiceIntegration:
    """Integration tests for AIService with real-like scenarios."""
    
    @pytest.fixture
    def mock_client_manager(self):
        """Create a mock OpenAI client manager for integration testing."""
        with patch('services.ai_service.get_client_manager') as mock:
            client_manager = Mock()
            mock.return_value = client_manager
            yield client_manager
    
    def test_full_prospect_processing_workflow(self, mock_config, mock_client_manager):
        """Test a complete workflow from LinkedIn parsing to email generation."""
        ai_service = AIService(mock_config, "integration_test")
        
        # Mock LinkedIn parsing response
        linkedin_response = CompletionResponse(
            content='{"name": "Sarah Johnson", "current_role": "VP Engineering at InnovateAI", "experience": ["Senior Engineer at TechGiant", "Lead Developer at StartupCo"], "skills": ["Python", "Machine Learning", "Team Leadership"], "summary": "Experienced engineering leader passionate about AI and team building"}',
            model="gpt-3.5-turbo",
            usage={"total_tokens": 150},
            finish_reason="stop",
            success=True
        )
        
        # Mock email generation response
        email_response = CompletionResponse(
            content='Subject: Impressed by InnovateAI\'s AI platform\n\nHi Sarah,\n\nI discovered InnovateAI through ProductHunt and was impressed by your innovative AI platform. As a software engineer with experience in Python and Machine Learning, I\'d love to learn more about your team and discuss potential opportunities.\n\nWould you be open to a brief conversation?\n\nBest regards,\nAlice',
            model="gpt-3.5-turbo",
            usage={"total_tokens": 200},
            finish_reason="stop",
            success=True
        )
        
        # Set up mock responses in sequence
        mock_client_manager.make_completion.side_effect = [linkedin_response, email_response]
        
        # Step 1: Parse LinkedIn profile
        linkedin_result = ai_service.parse_linkedin_profile("<html>LinkedIn profile HTML content</html>")
        
        assert linkedin_result.success is True
        assert linkedin_result.data.name == "Sarah Johnson"
        assert "Machine Learning" in linkedin_result.data.skills
        
        # Step 2: Generate email using parsed LinkedIn data
        prospect = Prospect(
            id="test-prospect",
            name="Sarah Johnson",
            role="VP Engineering",
            company="InnovateAI",
            linkedin_url="https://linkedin.com/in/sarahjohnson",
            email="sarah@innovateai.com",
            source_url="https://producthunt.com/posts/innovateai",
            notes="AI startup with impressive team"
        )
        
        email_result = ai_service.generate_email(
            prospect=prospect,
            template_type=EmailTemplate.COLD_OUTREACH,
            linkedin_profile=linkedin_result.data
        )
        
        assert email_result.success is True
        assert "ProductHunt" in email_result.data.body
        assert "Sarah" in email_result.data.body
        assert "InnovateAI" in email_result.data.body
        assert email_result.data.personalization_score > 0.5
        
        # Verify both operations were called
        assert mock_client_manager.make_completion.call_count == 2
    
    def test_error_recovery_and_fallback(self, mock_config, mock_client_manager):
        """Test error recovery and fallback mechanisms."""
        ai_service = AIService(mock_config, "error_test")
        
        # Mock failed AI response
        failed_response = CompletionResponse(
            content="",
            model="gpt-3.5-turbo",
            usage={},
            finish_reason="error",
            success=False,
            error_message="API rate limit exceeded"
        )
        mock_client_manager.make_completion.return_value = failed_response
        
        # Test LinkedIn parsing with fallback
        fallback_data = {
            "name": "John Fallback",
            "current_role": "Engineer",
            "experience": ["Previous role"],
            "skills": ["Python"],
            "summary": "Fallback summary"
        }
        
        result = ai_service.parse_linkedin_profile(
            "<html>content</html>", 
            fallback_data=fallback_data
        )
        
        # Should succeed with fallback data
        assert result.success is True
        assert result.data.name == "John Fallback"
        assert result.confidence_score == 0.3  # Lower confidence for fallback
        assert "fallback" in result.error_message.lower()
        
        # Test operation without fallback - should fail
        result_no_fallback = ai_service.analyze_product("test content")
        assert result_no_fallback.success is False
        assert "rate limit" in result_no_fallback.error_message.lower()
    
    def test_caching_across_operations(self, mock_config, mock_client_manager):
        """Test caching behavior across different AI operations."""
        ai_service = AIService(mock_config, "cache_test")
        
        # Mock responses for different operations
        linkedin_response = CompletionResponse(
            content='{"name": "Cache Test", "current_role": "Engineer", "experience": [], "skills": [], "summary": ""}',
            model="gpt-3.5-turbo",
            usage={"total_tokens": 50},
            finish_reason="stop",
            success=True
        )
        
        product_response = CompletionResponse(
            content='{"name": "Cache Product", "description": "Test", "features": [], "pricing_model": "free", "target_market": "test", "competitors": [], "funding_status": null, "market_analysis": ""}',
            model="gpt-3.5-turbo",
            usage={"total_tokens": 75},
            finish_reason="stop",
            success=True
        )
        
        mock_client_manager.make_completion.side_effect = [linkedin_response, product_response]
        
        # First calls - should hit AI
        linkedin_result1 = ai_service.parse_linkedin_profile("test linkedin content")
        product_result1 = ai_service.analyze_product("test product content")
        
        assert linkedin_result1.cached is False
        assert product_result1.cached is False
        
        # Second calls with same content - should be cached
        linkedin_result2 = ai_service.parse_linkedin_profile("test linkedin content")
        product_result2 = ai_service.analyze_product("test product content")
        
        assert linkedin_result2.cached is True
        assert product_result2.cached is True
        
        # Verify cache stats
        cache_stats = ai_service.get_cache_stats()
        assert cache_stats['total_entries'] == 2
        assert cache_stats['cache_enabled'] is True
        
        # Should only call AI twice (once for each operation type)
        assert mock_client_manager.make_completion.call_count == 2


if __name__ == "__main__":
    pytest.main([__file__])