#!/usr/bin/env python3
"""
Test script specifically for the email generation and sending pipeline.
"""

import sys
from typing import List

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


def test_email_generation_and_sending(send_emails: bool = False):
    """Test email generation and optionally sending."""
    logger = setup_test_logging()
    
    print_separator("EMAIL GENERATION & SENDING TEST")
    
    try:
        # Load configuration
        logger.info("Loading configuration...")
        config = Config.from_file("config.yaml")
        
        # Initialize controller
        logger.info("Initializing ProspectAutomationController...")
        controller = ProspectAutomationController(config)
        
        # Get existing prospects from Notion
        logger.info("Retrieving prospects from Notion...")
        prospects = controller.notion_manager.get_prospects()
        
        if not prospects:
            logger.warning("No prospects found in Notion database")
            print("❌ No prospects available for email generation")
            return
        
        # Filter prospects with valid emails
        prospects_with_emails = [p for p in prospects if p.email and p.email.strip()]
        prospects_without_emails = [p for p in prospects if not p.email or not p.email.strip()]
        
        print(f"\n📊 PROSPECT SUMMARY:")
        print(f"   Total prospects: {len(prospects)}")
        print(f"   With emails: {len(prospects_with_emails)}")
        print(f"   Without emails: {len(prospects_without_emails)}")
        
        if prospects_with_emails:
            print(f"\n📧 PROSPECTS WITH EMAILS:")
            for i, prospect in enumerate(prospects_with_emails[:5], 1):
                print(f"   {i}. {prospect.name} at {prospect.company} ({prospect.email})")
        
        if prospects_without_emails:
            print(f"\n⚠️  PROSPECTS WITHOUT EMAILS:")
            for i, prospect in enumerate(prospects_without_emails[:5], 1):
                print(f"   {i}. {prospect.name} at {prospect.company}")
        
        # Use prospects with emails for testing, or all prospects if none have emails
        test_prospects = prospects_with_emails if prospects_with_emails else prospects[:3]
        prospect_ids = [p.id for p in test_prospects if p.id]
        
        if not prospect_ids:
            logger.error("No valid prospect IDs found")
            return
        
        print(f"\n🎯 TESTING WITH {len(prospect_ids)} PROSPECTS")
        
        # Test email generation
        print_separator("STEP 1: EMAIL GENERATION")
        
        logger.info(f"Generating emails for {len(prospect_ids)} prospects...")
        
        try:
            email_results = controller.generate_outreach_emails(
                prospect_ids=prospect_ids,
                template_type=EmailTemplate.COLD_OUTREACH
            )
            
            successful = len(email_results.get('successful', []))
            failed = len(email_results.get('failed', []))
            
            print(f"✅ Email generation results: {successful} successful, {failed} failed")
            
            # Show sample generated email
            if email_results.get('successful'):
                sample = email_results['successful'][0]
                print(f"\n📧 SAMPLE GENERATED EMAIL:")
                print(f"   Prospect: {sample['prospect_name']} at {sample['company']}")
                
                email_content = sample.get('email_content', {})
                if isinstance(email_content, dict):
                    print(f"   Subject: {email_content.get('subject', 'N/A')}")
                    body = email_content.get('body', '')
                    if body:
                        print(f"   Body preview: {body[:200]}...")
                    print(f"   Personalization score: {email_content.get('personalization_score', 'N/A')}")
                else:
                    print(f"   Email content: {str(email_content)[:200]}...")
            
            # Show failed emails
            if email_results.get('failed'):
                print(f"\n❌ FAILED EMAIL GENERATIONS:")
                for failure in email_results['failed'][:3]:
                    print(f"   {failure.get('prospect_name', 'Unknown')}: {failure.get('error', 'Unknown error')}")
        
        except Exception as e:
            logger.error(f"Email generation failed: {str(e)}")
            print(f"❌ Email generation failed: {str(e)}")
            return
        
        # Test email sending if requested
        if send_emails and prospects_with_emails:
            print_separator("STEP 2: EMAIL SENDING")
            
            # Only send to prospects with valid emails
            email_prospect_ids = [p.id for p in prospects_with_emails[:2] if p.id]  # Limit to 2 for testing
            
            if email_prospect_ids:
                logger.info(f"Sending emails to {len(email_prospect_ids)} prospects...")
                
                try:
                    send_results = controller.generate_and_send_outreach_emails(
                        prospect_ids=email_prospect_ids,
                        template_type=EmailTemplate.COLD_OUTREACH,
                        send_immediately=True,
                        delay_between_emails=2.0
                    )
                    
                    generated = send_results.get('emails_generated', 0)
                    sent = send_results.get('emails_sent', 0)
                    failed = send_results.get('errors', 0)
                    
                    print(f"✅ Email sending results: {generated} generated, {sent} sent, {failed} failed")
                    
                    # Show sending details
                    if send_results.get('successful'):
                        print(f"\n📤 SENT EMAILS:")
                        for result in send_results['successful']:
                            status = "✅ SENT" if result.get('sent', False) else "📝 GENERATED"
                            print(f"   {result['prospect_name']} at {result['company']}: {status}")
                    
                except Exception as e:
                    logger.error(f"Email sending failed: {str(e)}")
                    print(f"❌ Email sending failed: {str(e)}")
            else:
                print("⚠️  No prospects with valid emails for sending test")
        
        elif send_emails:
            print_separator("STEP 2: EMAIL SENDING")
            print("⚠️  Email sending skipped - no prospects with valid emails")
        
        else:
            print_separator("STEP 2: EMAIL SENDING")
            print("📧 Email sending skipped (send_emails=False)")
            print("   To test email sending, set send_emails=True")
        
        print_separator("TEST COMPLETED")
        print("✅ Email pipeline test completed successfully!")
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        print(f"❌ Test failed: {str(e)}")
        sys.exit(1)


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test email generation and sending pipeline")
    parser.add_argument('--send-emails', action='store_true', 
                       help='Actually send emails (default: False)')
    
    args = parser.parse_args()
    
    test_email_generation_and_sending(send_emails=args.send_emails)


if __name__ == "__main__":
    main()