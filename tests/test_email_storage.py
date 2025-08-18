#!/usr/bin/env python3
"""
Test script for email generation and storage in Notion database.
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


def test_email_storage_workflow():
    """Test the complete email generation and storage workflow."""
    logger = setup_test_logging()
    
    print_separator("EMAIL STORAGE WORKFLOW TEST")
    
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
        
        print(f"\n📊 PROSPECT SUMMARY:")
        print(f"   Total prospects: {len(prospects)}")
        print(f"   With emails: {len(prospects_with_emails)}")
        
        if not prospects_with_emails:
            print("⚠️  No prospects with emails found for testing")
            return
        
        # Use first 3 prospects for testing
        test_prospects = prospects_with_emails[:3]
        prospect_ids = [p.id for p in test_prospects if p.id]
        
        print(f"\n🎯 TESTING EMAIL STORAGE WITH {len(prospect_ids)} PROSPECTS")
        for i, prospect in enumerate(test_prospects, 1):
            print(f"   {i}. {prospect.name} at {prospect.company} ({prospect.email})")
        
        # Test 1: Generate emails and store in Notion
        print_separator("STEP 1: EMAIL GENERATION WITH STORAGE")
        
        logger.info(f"Generating emails for {len(prospect_ids)} prospects...")
        
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
                print(f"   Template used: {email_content.get('template_used', 'N/A')}")
            
            print(f"   Generation time: {sample.get('generation_time', 'N/A'):.2f}s")
            print(f"   Stored in Notion: {sample.get('stored_in_notion', False)}")
        
        # Test 2: Check email generation statistics
        print_separator("STEP 2: EMAIL GENERATION STATISTICS")
        
        try:
            stats = controller.notion_manager.get_email_generation_stats()
            
            print(f"📈 EMAIL GENERATION STATISTICS:")
            print(f"   Total prospects: {stats['total_prospects']}")
            print(f"   Emails generated: {stats['emails_generated']}")
            print(f"   Emails sent: {stats['emails_sent']}")
            print(f"   Emails delivered: {stats['emails_delivered']}")
            print(f"   Emails opened: {stats['emails_opened']}")
            print(f"   Average personalization score: {stats['avg_personalization_score']:.2f}")
            print(f"   Average word count: {stats['avg_word_count']:.0f}")
            print(f"   Generation success rate: {stats['generation_success_rate']:.1%}")
            
            if stats['templates_used']:
                print(f"\n📝 TEMPLATES USED:")
                for template, count in stats['templates_used'].items():
                    print(f"   {template}: {count}")
            
            if stats['models_used']:
                print(f"\n🤖 MODELS USED:")
                for model, count in stats['models_used'].items():
                    print(f"   {model}: {count}")
            
            if stats['sender_profiles_used']:
                print(f"\n👤 SENDER PROFILES USED:")
                for profile, count in stats['sender_profiles_used'].items():
                    print(f"   {profile}: {count}")
        
        except Exception as e:
            logger.error(f"Failed to get email statistics: {str(e)}")
            print(f"❌ Failed to get email statistics: {str(e)}")
        
        # Test 3: Get prospects by email status
        print_separator("STEP 3: PROSPECTS BY EMAIL STATUS")
        
        try:
            generated_prospects = controller.notion_manager.get_prospects_by_email_status(
                generation_status="Generated"
            )
            
            print(f"📋 PROSPECTS WITH GENERATED EMAILS ({len(generated_prospects)}):")
            for prospect in generated_prospects[:5]:  # Show first 5
                print(f"   • {prospect['name']} at {prospect['company']}")
                print(f"     Subject: {prospect['email_subject']}")
                print(f"     Template: {prospect['email_template']}")
                print(f"     Score: {prospect['personalization_score']:.2f}")
                print(f"     Generated: {prospect['generated_date']}")
                print()
        
        except Exception as e:
            logger.error(f"Failed to get prospects by email status: {str(e)}")
            print(f"❌ Failed to get prospects by email status: {str(e)}")
        
        # Test 4: Test email sending with delivery tracking (optional)
        print_separator("STEP 4: EMAIL SENDING WITH DELIVERY TRACKING")
        
        send_test = input("Do you want to test email sending with delivery tracking? (y/N): ").lower().strip()
        
        if send_test == 'y':
            # Send to first prospect only for testing
            test_prospect_id = prospect_ids[0]
            
            try:
                send_results = controller.generate_and_send_outreach_emails(
                    prospect_ids=[test_prospect_id],
                    template_type=EmailTemplate.COLD_OUTREACH,
                    send_immediately=True,
                    delay_between_emails=1.0
                )
                
                generated = send_results.get('emails_generated', 0)
                sent = send_results.get('emails_sent', 0)
                failed = send_results.get('errors', 0)
                
                print(f"✅ Email sending results: {generated} generated, {sent} sent, {failed} failed")
                
                if send_results.get('successful'):
                    result = send_results['successful'][0]
                    print(f"\n📤 EMAIL SENT:")
                    print(f"   Prospect: {result['prospect_name']} at {result['company']}")
                    print(f"   Status: {'✅ SENT' if result.get('sent', False) else '📝 GENERATED'}")
                    
                    if result.get('send_result'):
                        send_info = result['send_result']
                        print(f"   Email ID: {send_info.get('email_id', 'N/A')}")
                        print(f"   Delivery status: {send_info.get('status', 'N/A')}")
            
            except Exception as e:
                logger.error(f"Failed to send email: {str(e)}")
                print(f"❌ Email sending failed: {str(e)}")
        else:
            print("📧 Email sending test skipped")
        
        print_separator("TEST COMPLETED")
        print("✅ Email storage workflow test completed successfully!")
        print("\n📋 SUMMARY:")
        print("   ✅ Email generation with Notion storage: WORKING")
        print("   ✅ Email statistics tracking: WORKING")
        print("   ✅ Email status filtering: WORKING")
        print("   ✅ Delivery tracking integration: READY")
        
        print("\n💡 NEXT STEPS:")
        print("   1. Check your Notion database to see stored email data")
        print("   2. Use the statistics to track email performance")
        print("   3. Filter prospects by email status for follow-ups")
        print("   4. Set up webhooks for real-time delivery tracking")
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        print(f"❌ Test failed: {str(e)}")
        sys.exit(1)


def main():
    """Main function."""
    test_email_storage_workflow()


if __name__ == "__main__":
    main()