#!/usr/bin/env python3
"""
Test script for email sending functionality.
"""

import sys
from typing import List

from controllers.prospect_automation_controller import ProspectAutomationController
from utils.config import Config
from utils.logging_config import setup_logging, get_logger
from services.email_generator import EmailGenerator, EmailTemplate
from services.email_sender import EmailSender
from models.data_models import Prospect, ProspectStatus, EmailContent


def setup_test_logging():
    """Setup logging for the test."""
    setup_logging(log_level="INFO")
    return get_logger(__name__)


def print_separator(title: str):
    """Print a formatted separator for test sections."""
    print("\n" + "="*80)
    print(f" {title}")
    print("="*80)


def test_email_sending_with_real_prospect(send_emails: bool = False):
    """Test email sending with a real prospect."""
    logger = setup_test_logging()
    
    print_separator("EMAIL SENDING TEST")
    
    try:
        # Load configuration
        logger.info("Loading configuration...")
        config = Config.from_file("config.yaml")
        
        # Initialize controller
        logger.info("Initializing ProspectAutomationController...")
        controller = ProspectAutomationController(config)
        
        # Get prospects with emails
        logger.info("Retrieving prospects from Notion...")
        prospects = controller.notion_manager.get_prospects()
        prospects_with_emails = [p for p in prospects if p.email and p.email.strip()]
        
        if not prospects_with_emails:
            logger.warning("No prospects with emails found")
            print("❌ No prospects with emails available for sending test")
            return
        
        # Use the first prospect with email
        test_prospect = prospects_with_emails[0]
        
        print(f"\n🎯 TESTING WITH REAL PROSPECT:")
        print(f"   Name: {test_prospect.name}")
        print(f"   Role: {test_prospect.role}")
        print(f"   Company: {test_prospect.company}")
        print(f"   Email: {test_prospect.email}")
        
        # Step 1: Generate email
        print_separator("STEP 1: EMAIL GENERATION")
        
        logger.info("Generating email...")
        email_generator = EmailGenerator(config=config)
        
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
        print(f"   Subject: {email_content.subject}")
        print(f"   Personalization Score: {email_content.personalization_score}")
        print(f"   Body preview: {email_content.body[:150]}...")
        
        # Step 2: Send email (if requested)
        if send_emails:
            print_separator("STEP 2: EMAIL SENDING")
            
            logger.info("Sending email...")
            email_sender = EmailSender(config=config, notion_manager=controller.notion_manager)
            
            try:
                send_result = email_sender.send_email(
                    recipient_email=test_prospect.email,
                    subject=email_content.subject,
                    body=email_content.body,
                    prospect_id=test_prospect.id if test_prospect.id else None
                )
                
                if send_result.get('success', False):
                    print(f"✅ Email sent successfully!")
                    print(f"   Message ID: {send_result.get('message_id', 'N/A')}")
                    print(f"   Sent to: {test_prospect.email}")
                    print(f"   Subject: {email_content.subject}")
                else:
                    print(f"❌ Email sending failed: {send_result.get('error', 'Unknown error')}")
                
                return send_result
                
            except Exception as e:
                logger.error(f"Email sending failed: {str(e)}")
                print(f"❌ Email sending failed: {str(e)}")
                return None
        
        else:
            print_separator("STEP 2: EMAIL SENDING")
            print("📧 Email sending skipped (send_emails=False)")
            print("   To actually send emails, use --send-emails flag")
            print(f"   Would send to: {test_prospect.email}")
            print(f"   Subject: {email_content.subject}")
        
        return email_content
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        print(f"❌ Test failed: {str(e)}")
        sys.exit(1)


def test_bulk_email_generation_and_sending(send_emails: bool = False, limit: int = 3):
    """Test bulk email generation and sending."""
    logger = setup_test_logging()
    
    print_separator("BULK EMAIL GENERATION & SENDING TEST")
    
    try:
        # Load configuration
        logger.info("Loading configuration...")
        config = Config.from_file("config.yaml")
        
        # Initialize controller
        logger.info("Initializing ProspectAutomationController...")
        controller = ProspectAutomationController(config)
        
        # Get prospects
        logger.info("Retrieving prospects from Notion...")
        prospects = controller.notion_manager.get_prospects()
        
        if not prospects:
            logger.warning("No prospects found")
            print("❌ No prospects available for bulk test")
            return
        
        # Limit prospects for testing
        test_prospects = prospects[:limit]
        prospects_with_emails = [p for p in test_prospects if p.email and p.email.strip()]
        
        print(f"\n📊 BULK TEST SUMMARY:")
        print(f"   Total prospects: {len(test_prospects)}")
        print(f"   With emails: {len(prospects_with_emails)}")
        print(f"   Testing limit: {limit}")
        
        if prospects_with_emails:
            print(f"\n📧 PROSPECTS WITH EMAILS:")
            for i, prospect in enumerate(prospects_with_emails, 1):
                print(f"   {i}. {prospect.name} at {prospect.company} ({prospect.email})")
        
        # Step 1: Generate emails for all prospects
        print_separator("STEP 1: BULK EMAIL GENERATION")
        
        logger.info(f"Generating emails for {len(test_prospects)} prospects...")
        
        generated_emails = []
        failed_generations = []
        
        email_generator = EmailGenerator(config=config)
        
        for i, prospect in enumerate(test_prospects, 1):
            try:
                logger.info(f"Generating email {i}/{len(test_prospects)} for {prospect.name}")
                
                email_content = email_generator.generate_outreach_email(
                    prospect=prospect,
                    template_type=EmailTemplate.COLD_OUTREACH,
                    linkedin_profile=None,
                    product_analysis=None,
                    additional_context={
                        'source_mention': 'ProductHunt',
                        'discovery_context': f'I discovered {prospect.company} on ProductHunt'
                    }
                )
                
                generated_emails.append({
                    'prospect': prospect,
                    'email_content': email_content
                })
                
                print(f"   ✅ {prospect.name}: Generated (score: {email_content.personalization_score:.2f})")
                
            except Exception as e:
                failed_generations.append({
                    'prospect': prospect,
                    'error': str(e)
                })
                print(f"   ❌ {prospect.name}: Failed - {str(e)}")
        
        print(f"\n📊 GENERATION RESULTS:")
        print(f"   Successful: {len(generated_emails)}")
        print(f"   Failed: {len(failed_generations)}")
        
        # Step 2: Send emails (if requested)
        if send_emails and generated_emails:
            print_separator("STEP 2: BULK EMAIL SENDING")
            
            # Only send to prospects with valid emails
            sendable_emails = [item for item in generated_emails if item['prospect'].email and item['prospect'].email.strip()]
            
            if not sendable_emails:
                print("⚠️  No prospects with valid emails for sending")
                return
            
            logger.info(f"Sending emails to {len(sendable_emails)} prospects...")
            
            email_sender = EmailSender(config=config, notion_manager=controller.notion_manager)
            sent_emails = []
            failed_sends = []
            
            for i, item in enumerate(sendable_emails, 1):
                prospect = item['prospect']
                email_content = item['email_content']
                
                try:
                    logger.info(f"Sending email {i}/{len(sendable_emails)} to {prospect.name}")
                    
                    send_result = email_sender.send_email(
                        recipient_email=prospect.email,
                        subject=email_content.subject,
                        body=email_content.body,
                        prospect_id=prospect.id if prospect.id else None
                    )
                    
                    if send_result.get('success', False):
                        sent_emails.append({
                            'prospect': prospect,
                            'result': send_result
                        })
                        print(f"   ✅ {prospect.name}: Sent (ID: {send_result.get('message_id', 'N/A')})")
                    else:
                        failed_sends.append({
                            'prospect': prospect,
                            'error': send_result.get('error', 'Unknown error')
                        })
                        print(f"   ❌ {prospect.name}: Failed - {send_result.get('error', 'Unknown error')}")
                    
                    # Add delay between sends
                    if i < len(sendable_emails):
                        import time
                        time.sleep(2)  # 2 second delay between emails
                
                except Exception as e:
                    failed_sends.append({
                        'prospect': prospect,
                        'error': str(e)
                    })
                    print(f"   ❌ {prospect.name}: Exception - {str(e)}")
            
            print(f"\n📊 SENDING RESULTS:")
            print(f"   Sent successfully: {len(sent_emails)}")
            print(f"   Failed to send: {len(failed_sends)}")
            
            if sent_emails:
                print(f"\n✅ SUCCESSFULLY SENT EMAILS:")
                for item in sent_emails:
                    prospect = item['prospect']
                    print(f"   • {prospect.name} at {prospect.company} ({prospect.email})")
        
        else:
            print_separator("STEP 2: BULK EMAIL SENDING")
            if not send_emails:
                print("📧 Email sending skipped (send_emails=False)")
                print("   To actually send emails, use --send-emails flag")
                if generated_emails:
                    sendable_count = len([item for item in generated_emails if item['prospect'].email])
                    print(f"   Would send to {sendable_count} prospects with emails")
            else:
                print("⚠️  No generated emails available for sending")
        
        return {
            'generated': len(generated_emails),
            'failed_generation': len(failed_generations),
            'sent': len(sent_emails) if send_emails else 0,
            'failed_sending': len(failed_sends) if send_emails else 0
        }
        
    except Exception as e:
        logger.error(f"Bulk test failed: {str(e)}")
        print(f"❌ Bulk test failed: {str(e)}")
        sys.exit(1)


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test email sending functionality")
    parser.add_argument('--send-emails', action='store_true', 
                       help='Actually send emails (default: False)')
    parser.add_argument('--bulk', action='store_true',
                       help='Test bulk email generation and sending')
    parser.add_argument('--limit', type=int, default=3,
                       help='Limit number of prospects for bulk test (default: 3)')
    
    args = parser.parse_args()
    
    if args.bulk:
        result = test_bulk_email_generation_and_sending(
            send_emails=args.send_emails, 
            limit=args.limit
        )
    else:
        result = test_email_sending_with_real_prospect(send_emails=args.send_emails)
    
    print_separator("TEST COMPLETED")
    if args.send_emails:
        print("✅ Email sending test completed!")
    else:
        print("✅ Email generation test completed!")
        print("   Use --send-emails to test actual email sending")


if __name__ == "__main__":
    main()