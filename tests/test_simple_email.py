#!/usr/bin/env python3
"""
Simple test script for email generation using the direct email generator.
"""

import sys
from typing import List

from controllers.prospect_automation_controller import ProspectAutomationController
from utils.config import Config
from utils.logging_config import setup_logging, get_logger
from services.email_generator import EmailGenerator, EmailTemplate
from models.data_models import Prospect, ProspectStatus


def setup_test_logging():
    """Setup logging for the test."""
    setup_logging(log_level="INFO")
    return get_logger(__name__)


def print_separator(title: str):
    """Print a formatted separator for test sections."""
    print("\n" + "="*80)
    print(f" {title}")
    print("="*80)


def test_direct_email_generation():
    """Test direct email generation with a sample prospect."""
    logger = setup_test_logging()
    
    print_separator("DIRECT EMAIL GENERATION TEST")
    
    try:
        # Load configuration
        logger.info("Loading configuration...")
        config = Config.from_file("config.yaml")
        
        # Initialize email generator directly
        logger.info("Initializing EmailGenerator...")
        email_generator = EmailGenerator(config=config)
        
        # Create a sample prospect for testing
        sample_prospect = Prospect(
            name="John Smith",
            role="CTO",
            company="TechCorp",
            email="john.smith@techcorp.com",
            linkedin_url="https://linkedin.com/in/johnsmith",
            source_url="https://producthunt.com/products/techcorp",
            status=ProspectStatus.NOT_CONTACTED,
            notes="Found on ProductHunt, AI-powered analytics platform"
        )
        
        print(f"\n🎯 TESTING WITH SAMPLE PROSPECT:")
        print(f"   Name: {sample_prospect.name}")
        print(f"   Role: {sample_prospect.role}")
        print(f"   Company: {sample_prospect.company}")
        print(f"   Email: {sample_prospect.email}")
        
        # Test email generation
        print_separator("EMAIL GENERATION")
        
        logger.info("Generating outreach email...")
        
        try:
            email_content = email_generator.generate_outreach_email(
                prospect=sample_prospect,
                template_type=EmailTemplate.COLD_OUTREACH,
                linkedin_profile=None,  # No LinkedIn data for this test
                product_analysis=None,  # No product analysis for this test
                additional_context={
                    'source_mention': 'ProductHunt',
                    'discovery_context': f'I discovered {sample_prospect.company} on ProductHunt'
                }
            )
            
            print(f"✅ Email generated successfully!")
            print(f"\n📧 GENERATED EMAIL:")
            print(f"   Subject: {email_content.subject}")
            print(f"   Template: {email_content.template_used}")
            print(f"   Personalization Score: {email_content.personalization_score}")
            print(f"\n   Body:")
            print("   " + "-"*60)
            # Print body with proper indentation
            for line in email_content.body.split('\n'):
                print(f"   {line}")
            print("   " + "-"*60)
            
            return email_content
            
        except Exception as e:
            logger.error(f"Email generation failed: {str(e)}")
            print(f"❌ Email generation failed: {str(e)}")
            return None
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        print(f"❌ Test failed: {str(e)}")
        sys.exit(1)


def test_with_real_prospects():
    """Test email generation with real prospects from Notion."""
    logger = setup_test_logging()
    
    print_separator("REAL PROSPECTS EMAIL GENERATION TEST")
    
    try:
        # Load configuration
        logger.info("Loading configuration...")
        config = Config.from_file("config.yaml")
        
        # Initialize controller to get real prospects
        logger.info("Initializing ProspectAutomationController...")
        controller = ProspectAutomationController(config)
        
        # Get real prospects from Notion
        logger.info("Retrieving prospects from Notion...")
        prospects = controller.notion_manager.get_prospects()
        
        if not prospects:
            logger.warning("No prospects found in Notion database")
            print("❌ No prospects available for testing")
            return
        
        # Filter prospects with emails
        prospects_with_emails = [p for p in prospects if p.email and p.email.strip()]
        
        if not prospects_with_emails:
            logger.warning("No prospects with emails found")
            print("⚠️  No prospects with emails available for testing")
            # Use first prospect anyway for testing
            test_prospect = prospects[0]
            test_prospect.email = "test@example.com"  # Add dummy email for testing
        else:
            test_prospect = prospects_with_emails[0]
        
        print(f"\n🎯 TESTING WITH REAL PROSPECT:")
        print(f"   Name: {test_prospect.name}")
        print(f"   Role: {test_prospect.role}")
        print(f"   Company: {test_prospect.company}")
        print(f"   Email: {test_prospect.email}")
        
        # Initialize email generator directly
        email_generator = EmailGenerator(config=config)
        
        # Test email generation
        print_separator("EMAIL GENERATION")
        
        logger.info("Generating outreach email...")
        
        try:
            email_content = email_generator.generate_outreach_email(
                prospect=test_prospect,
                template_type=EmailTemplate.COLD_OUTREACH,
                linkedin_profile=None,
                product_analysis=None,
                additional_context={
                    'source_mention': 'ProductHunt',
                    'discovery_context': f'I discovered {test_prospect.company} on ProductHunt'
                }
            )
            
            print(f"✅ Email generated successfully!")
            print(f"\n📧 GENERATED EMAIL:")
            print(f"   Subject: {email_content.subject}")
            print(f"   Template: {email_content.template_used}")
            print(f"   Personalization Score: {email_content.personalization_score}")
            print(f"\n   Body:")
            print("   " + "-"*60)
            # Print body with proper indentation
            for line in email_content.body.split('\n'):
                print(f"   {line}")
            print("   " + "-"*60)
            
            return email_content
            
        except Exception as e:
            logger.error(f"Email generation failed: {str(e)}")
            print(f"❌ Email generation failed: {str(e)}")
            return None
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        print(f"❌ Test failed: {str(e)}")
        sys.exit(1)


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test email generation directly")
    parser.add_argument('--real-prospects', action='store_true', 
                       help='Use real prospects from Notion (default: use sample prospect)')
    
    args = parser.parse_args()
    
    if args.real_prospects:
        test_with_real_prospects()
    else:
        test_direct_email_generation()
    
    print_separator("TEST COMPLETED")
    print("✅ Email generation test completed successfully!")


if __name__ == "__main__":
    main()