#!/usr/bin/env python3
"""
Test script to verify the data truncation and LinkedIn URL fixes.
"""

import logging
import sys
from typing import List, Dict, Any
from utils.config import Config
from services.product_hunt_scraper import ProductHuntScraper
from services.linkedin_finder import LinkedInFinder
from services.ai_parser import AIParser
from models.data_models import TeamMember

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_linkedin_finder():
    """
    Test the LinkedIn finder with sample team members.
    """
    print("\n=== TESTING LINKEDIN FINDER ===")
    
    try:
        config = Config.from_env()
        linkedin_finder = LinkedInFinder(config)
        
        # Test with sample team members (some with common names)
        test_members = [
            TeamMember(
                name="John Smith",
                role="CEO",
                company="TechCorp",
                linkedin_url=None
            ),
            TeamMember(
                name="Sarah Johnson",
                role="CTO",
                company="StartupXYZ",
                linkedin_url=None
            ),
            TeamMember(
                name="Mike Chen",
                role="Product Manager",
                company="InnovateCo",
                linkedin_url=None
            )
        ]
        
        print(f"Testing LinkedIn finder with {len(test_members)} sample members...")
        
        updated_members = linkedin_finder.find_linkedin_urls_for_team(test_members)
        
        # Show results
        for i, member in enumerate(updated_members):
            original = test_members[i]
            status = "✓ FOUND" if member.linkedin_url else "✗ NOT FOUND"
            print(f"{status}: {member.name} at {member.company}")
            if member.linkedin_url:
                print(f"    LinkedIn: {member.linkedin_url}")
        
        found_count = len([m for m in updated_members if m.linkedin_url])
        print(f"\nLinkedIn Finder Results: {found_count}/{len(test_members)} URLs found")
        
        return found_count > 0
        
    except Exception as e:
        logger.error(f"LinkedIn finder test failed: {str(e)}")
        return False


def test_ai_parser_limits():
    """
    Test the AI parser with longer content to verify increased limits.
    """
    print("\n=== TESTING AI PARSER LIMITS ===")
    
    try:
        config = Config.from_env()
        ai_parser = AIParser(config)
        
        # Create long test content to verify limits
        long_product_content = """
        Product Name: TestProduct Pro
        
        Description: This is a comprehensive business intelligence platform that helps companies analyze their data, generate insights, and make better decisions. The platform includes advanced analytics, machine learning capabilities, real-time dashboards, and automated reporting features. It's designed for enterprise customers who need scalable solutions for their data analysis needs.
        
        Features:
        - Advanced data analytics with machine learning
        - Real-time dashboard creation and customization
        - Automated report generation and scheduling
        - Integration with 50+ data sources including databases, APIs, and cloud services
        - Collaborative workspace for team analysis
        - Mobile app for on-the-go insights
        - Enterprise-grade security and compliance
        - Custom visualization tools
        - Predictive analytics and forecasting
        - Data governance and quality management
        
        Pricing: Enterprise pricing starts at $10,000/month for up to 100 users, with additional tiers for larger organizations. Custom pricing available for Fortune 500 companies.
        
        Target Market: Mid to large enterprises in finance, healthcare, retail, and technology sectors who need advanced data analytics capabilities.
        
        Competitors: Tableau, Power BI, Looker, Qlik Sense, Sisense, and other business intelligence platforms.
        
        Market Analysis: The business intelligence market is growing rapidly, with increasing demand for self-service analytics and AI-powered insights. Our platform differentiates through its ease of use, advanced ML capabilities, and comprehensive integration ecosystem.
        
        Funding: Series B funding of $25M led by Acme Ventures, with participation from Tech Capital and Innovation Partners. Total funding to date: $40M.
        
        Team: 150+ employees across engineering, sales, marketing, and customer success. Founded by former executives from major tech companies.
        """ * 3  # Repeat to make it longer
        
        print(f"Testing AI parser with {len(long_product_content)} characters of content...")
        
        # Test product info parsing
        result = ai_parser.parse_product_info(long_product_content)
        
        if result.success and result.data:
            product_info = result.data
            print("✓ Product parsing successful")
            print(f"  Name: {product_info.name}")
            print(f"  Description length: {len(product_info.description)} chars")
            print(f"  Features count: {len(product_info.features)}")
            print(f"  Market analysis length: {len(product_info.market_analysis)} chars")
            
            # Check if we got more complete data
            if len(product_info.description) > 300 and len(product_info.market_analysis) > 200:
                print("✓ Increased limits working - got more complete data")
                return True
            else:
                print("✗ Data still appears truncated")
                return False
        else:
            print(f"✗ Product parsing failed: {result.error_message}")
            return False
        
    except Exception as e:
        logger.error(f"AI parser test failed: {str(e)}")
        return False


def test_product_hunt_scraper_with_linkedin():
    """
    Test the ProductHunt scraper with LinkedIn URL finding.
    """
    print("\n=== TESTING PRODUCT HUNT SCRAPER WITH LINKEDIN FINDER ===")
    
    try:
        config = Config.from_env()
        scraper = ProductHuntScraper(config)
        
        # Test with a real ProductHunt URL (replace with current product)
        test_url = "https://www.producthunt.com/products/notion"  # Example URL
        
        print(f"Testing team extraction from: {test_url}")
        
        team_members = scraper.extract_team_info(test_url)
        
        if team_members:
            print(f"✓ Extracted {len(team_members)} team members")
            
            linkedin_count = len([m for m in team_members if m.linkedin_url])
            print(f"  Members with LinkedIn URLs: {linkedin_count}/{len(team_members)}")
            
            for member in team_members[:3]:  # Show first 3
                status = "✓" if member.linkedin_url else "✗"
                print(f"  {status} {member.name} - {member.role}")
                if member.linkedin_url:
                    print(f"    LinkedIn: {member.linkedin_url}")
            
            return linkedin_count > 0
        else:
            print("✗ No team members extracted")
            return False
        
    except Exception as e:
        logger.error(f"ProductHunt scraper test failed: {str(e)}")
        return False


def test_email_generator_limits():
    """
    Test that email generator uses increased character limits.
    """
    print("\n=== TESTING EMAIL GENERATOR LIMITS ===")
    
    try:
        from services.email_generator import EmailGenerator
        from models.data_models import Prospect, ProspectStatus
        
        config = Config.from_env()
        email_generator = EmailGenerator(config)
        
        # Create test prospect with long AI-structured data
        prospect = Prospect(
            name="John Doe",
            role="CEO",
            company="TestCorp",
            email="john@testcorp.com",
            status=ProspectStatus.NOT_CONTACTED
        )
        
        # Simulate AI-structured data with longer content
        ai_structured_data = {
            'product_summary': "This is a comprehensive product summary that would previously be truncated at 500 characters but now should be allowed to be much longer to provide better context for email personalization. " * 5,
            'business_insights': "These are detailed business insights about the company including funding, growth metrics, market position, and competitive advantages that should not be truncated. " * 4,
            'linkedin_summary': "This is a detailed LinkedIn profile summary with experience, skills, education, and background information that provides valuable context for personalization. " * 4,
            'personalization_data': "These are key personalization points extracted from various sources that help create more targeted and relevant outreach emails. " * 5
        }
        
        # Test data preparation
        personalization_data = email_generator._prepare_personalization_data(
            prospect=prospect,
            ai_structured_data=ai_structured_data
        )
        
        # Check if data is properly preserved without truncation
        print("✓ Testing personalization data limits:")
        
        fields_to_check = [
            ('product_summary', 1500),
            ('business_insights', 1000),
            ('linkedin_summary', 1000),
            ('personalization_points', 1200)
        ]
        
        all_good = True
        for field, expected_limit in fields_to_check:
            actual_length = len(personalization_data.get(field, ''))
            print(f"  {field}: {actual_length} chars (limit: {expected_limit})")
            
            if actual_length > 500:  # Should be longer than old limits
                print(f"    ✓ Increased limit working")
            else:
                print(f"    ✗ Still using old limits")
                all_good = False
        
        return all_good
        
    except Exception as e:
        logger.error(f"Email generator test failed: {str(e)}")
        return False


def run_all_tests():
    """
    Run all tests and provide a summary.
    """
    print("=== RUNNING DATA FIXES TESTS ===")
    
    tests = [
        ("LinkedIn Finder", test_linkedin_finder),
        ("AI Parser Limits", test_ai_parser_limits),
        ("Email Generator Limits", test_email_generator_limits),
        # ("ProductHunt Scraper with LinkedIn", test_product_hunt_scraper_with_linkedin),  # Commented out to avoid rate limits
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.error(f"Test {test_name} failed with exception: {str(e)}")
            results[test_name] = False
    
    # Summary
    print(f"\n{'='*50}")
    print("=== TEST RESULTS SUMMARY ===")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The data fixes are working correctly.")
    else:
        print("⚠️  Some tests failed. Please check the issues above.")
    
    return passed == total


if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_name = sys.argv[1].lower()
        if test_name == "linkedin":
            test_linkedin_finder()
        elif test_name == "parser":
            test_ai_parser_limits()
        elif test_name == "email":
            test_email_generator_limits()
        elif test_name == "scraper":
            test_product_hunt_scraper_with_linkedin()
        else:
            print("Available tests: linkedin, parser, email, scraper")
    else:
        run_all_tests()