#!/usr/bin/env python3
"""
Comprehensive test script for the entire job prospect automation pipeline.
Tests the complete workflow from discovery to email sending.
"""

import sys
import time
from datetime import datetime
from typing import Dict, Any, List

from controllers.prospect_automation_controller import ProspectAutomationController
from utils.config import Config
from utils.logging_config import setup_logging, get_logger
from services.email_generator import EmailTemplate


def setup_test_logging():
    """Setup logging for the test."""
    setup_logging(log_level="INFO")
    return get_logger(__name__)


def print_separator(title: str):
    """Print a formatted separator for test sections."""
    print("\n" + "="*80)
    print(f" {title}")
    print("="*80)


def print_results_summary(results: Dict[str, Any]):
    """Print a formatted summary of pipeline results."""
    summary = results.get('summary', {})
    
    print(f"\n📊 PIPELINE RESULTS SUMMARY:")
    print(f"   Companies processed: {summary.get('companies_processed', 0)}")
    print(f"   Prospects found: {summary.get('prospects_found', 0)}")
    print(f"   Emails found: {summary.get('emails_found', 0)}")
    print(f"   LinkedIn profiles: {summary.get('linkedin_profiles_extracted', 0)}")
    print(f"   Success rate: {summary.get('success_rate', 0):.1f}%")
    
    if summary.get('duration_seconds'):
        print(f"   Duration: {summary['duration_seconds']:.1f} seconds")


def test_configuration_validation(controller: ProspectAutomationController, logger):
    """Test configuration validation and basic service initialization."""
    print_separator("STEP 1: CONFIGURATION VALIDATION")
    
    try:
        # Validate configuration
        controller.config.validate()
        logger.info("✅ Configuration validation passed")
        
        # Check if services are initialized
        services = {
            'ProductHunt Scraper': controller.product_hunt_scraper,
            'Notion Manager': controller.notion_manager,
            'Email Finder': controller.email_finder,
            'LinkedIn Scraper': controller.linkedin_scraper,
            'Email Generator': controller.email_generator,
            'Email Sender': controller.email_sender,
            'Product Analyzer': controller.product_analyzer,
            'AI Parser': controller.ai_parser
        }
        
        print(f"\n🔧 SERVICE INITIALIZATION STATUS:")
        for service_name, service in services.items():
            status = "✅" if service is not None else "❌"
            print(f"   {service_name}: {status}")
        
        # Check sender profile
        if controller.sender_profile:
            print(f"   Sender Profile: ✅ {controller.sender_profile.name}")
        else:
            print(f"   Sender Profile: ⚠️  Not loaded")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Configuration validation failed: {str(e)}")
        return False


def test_discovery_pipeline(controller: ProspectAutomationController, logger, limit: int = 5):
    """Test the complete discovery pipeline."""
    print_separator("STEP 2: DISCOVERY PIPELINE")
    
    try:
        logger.info(f"Starting discovery pipeline with limit={limit}")
        start_time = time.time()
        
        # Run the discovery pipeline
        results = controller.run_discovery_pipeline(limit=limit)
        
        end_time = time.time()
        duration = end_time - start_time
        
        logger.info(f"✅ Discovery pipeline completed in {duration:.1f} seconds")
        print_results_summary(results)
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Discovery pipeline failed: {str(e)}")
        return None


def test_email_generation(controller: ProspectAutomationController, logger, 
                         prospect_ids: List[str], template_type: EmailTemplate = EmailTemplate.COLD_OUTREACH):
    """Test email generation for prospects."""
    print_separator("STEP 3: EMAIL GENERATION")
    
    if not prospect_ids:
        logger.warning("⚠️  No prospect IDs available for email generation")
        return None
    
    try:
        logger.info(f"Generating emails for {len(prospect_ids)} prospects")
        
        # Generate emails
        email_results = controller.generate_outreach_emails(
            prospect_ids=prospect_ids,
            template_type=template_type
        )
        
        successful = len(email_results.get('successful', []))
        failed = len(email_results.get('failed', []))
        
        logger.info(f"✅ Email generation completed: {successful} successful, {failed} failed")
        
        # Print sample email content
        if email_results.get('successful'):
            sample = email_results['successful'][0]
            print(f"\n📧 SAMPLE EMAIL GENERATED:")
            print(f"   Prospect: {sample['prospect_name']} at {sample['company']}")
            email_content = sample['email_content']
            print(f"   Subject: {email_content.get('subject', 'N/A')}")
            print(f"   Body preview: {email_content.get('body', '')[:200]}...")
            print(f"   Personalization score: {email_content.get('personalization_score', 'N/A')}")
        
        return email_results
        
    except Exception as e:
        logger.error(f"❌ Email generation failed: {str(e)}")
        return None


def test_email_sending(controller: ProspectAutomationController, logger, 
                      prospect_ids: List[str], send_emails: bool = False):
    """Test email sending (optional)."""
    print_separator("STEP 4: EMAIL SENDING")
    
    if not prospect_ids:
        logger.warning("⚠️  No prospect IDs available for email sending")
        return None
    
    if not send_emails:
        logger.info("📧 Email sending skipped (send_emails=False)")
        logger.info("   To test email sending, set send_emails=True")
        return None
    
    try:
        logger.info(f"Sending emails to {len(prospect_ids)} prospects")
        
        # Generate and send emails
        send_results = controller.generate_and_send_outreach_emails(
            prospect_ids=prospect_ids,
            template_type=EmailTemplate.COLD_OUTREACH,
            send_immediately=True,
            delay_between_emails=2.0
        )
        
        generated = send_results.get('emails_generated', 0)
        sent = send_results.get('emails_sent', 0)
        failed = send_results.get('errors', 0)
        
        logger.info(f"✅ Email sending completed: {generated} generated, {sent} sent, {failed} failed")
        
        return send_results
        
    except Exception as e:
        logger.error(f"❌ Email sending failed: {str(e)}")
        return None


def test_workflow_status(controller: ProspectAutomationController, logger):
    """Test workflow status and statistics."""
    print_separator("STEP 5: WORKFLOW STATUS")
    
    try:
        status_info = controller.get_workflow_status()
        
        print(f"\n📈 WORKFLOW STATUS:")
        for key, value in status_info.items():
            print(f"   {key}: {value}")
        
        logger.info("✅ Workflow status retrieved successfully")
        return status_info
        
    except Exception as e:
        logger.error(f"❌ Failed to get workflow status: {str(e)}")
        return None


def extract_prospect_ids_from_results(results: Dict[str, Any]) -> List[str]:
    """Extract prospect IDs from discovery results."""
    prospect_ids = []
    
    if results and 'prospects' in results:
        for prospect in results['prospects']:
            if prospect.get('id'):
                prospect_ids.append(prospect['id'])
    
    return prospect_ids


def main():
    """Main test function."""
    print_separator("JOB PROSPECT AUTOMATION - FULL PIPELINE TEST")
    
    # Setup logging
    logger = setup_test_logging()
    logger.info("Starting comprehensive pipeline test")
    
    # Configuration
    TEST_LIMIT = 3  # Number of companies to process
    SEND_EMAILS = False  # Set to True to actually send emails
    
    try:
        # Load configuration
        logger.info("Loading configuration...")
        config = Config.from_file("config.yaml")
        
        # Initialize controller
        logger.info("Initializing ProspectAutomationController...")
        controller = ProspectAutomationController(config)
        
        # Test 1: Configuration validation
        if not test_configuration_validation(controller, logger):
            logger.error("Configuration validation failed. Stopping test.")
            sys.exit(1)
        
        # Test 2: Discovery pipeline
        discovery_results = test_discovery_pipeline(controller, logger, limit=TEST_LIMIT)
        if not discovery_results:
            logger.error("Discovery pipeline failed. Stopping test.")
            sys.exit(1)
        
        # Extract prospect IDs for email testing
        prospect_ids = extract_prospect_ids_from_results(discovery_results)
        
        if not prospect_ids:
            # Try to get prospects from Notion
            try:
                prospects = controller.notion_manager.get_prospects()
                prospect_ids = [p.id for p in prospects[:5] if p.id]  # Get up to 5 prospects
                logger.info(f"Retrieved {len(prospect_ids)} prospect IDs from Notion")
            except Exception as e:
                logger.warning(f"Could not retrieve prospects from Notion: {str(e)}")
        
        # Test 3: Email generation
        email_results = test_email_generation(controller, logger, prospect_ids)
        
        # Test 4: Email sending (optional)
        send_results = test_email_sending(controller, logger, prospect_ids, send_emails=SEND_EMAILS)
        
        # Test 5: Workflow status
        status_info = test_workflow_status(controller, logger)
        
        # Final summary
        print_separator("FINAL TEST SUMMARY")
        
        print(f"✅ Configuration validation: PASSED")
        print(f"✅ Discovery pipeline: {'PASSED' if discovery_results else 'FAILED'}")
        print(f"✅ Email generation: {'PASSED' if email_results else 'FAILED'}")
        print(f"✅ Email sending: {'PASSED' if send_results else 'SKIPPED' if not SEND_EMAILS else 'FAILED'}")
        print(f"✅ Workflow status: {'PASSED' if status_info else 'FAILED'}")
        
        if discovery_results:
            print_results_summary(discovery_results)
        
        logger.info("🎉 Full pipeline test completed successfully!")
        
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Test failed with unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()