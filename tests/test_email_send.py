#!/usr/bin/env python3
"""
Test script to send a simple email to debug the Resend API issue.
"""

import os
import sys
from datetime import datetime
from utils.config import Config
from services.email_sender import EmailSender

def test_simple_email():
    """Test sending a simple email to debug the issue."""
    print("🧪 Testing simple email send...")
    
    try:
        # Load configuration
        config = Config.from_env()
        
        # Initialize email sender
        email_sender = EmailSender(config)
        
        # Test 1: Very simple email
        print("\n📧 Test 1: Very simple email")
        simple_subject = "Test Email"
        simple_body = "This is a test email."
        simple_html = "<p>This is a test email.</p>"
        
        result = email_sender.send_email(
            recipient_email="romeomino415@gmail.com",
            subject=simple_subject,
            html_body=simple_html,
            text_body=simple_body,
            tags=["test"]
        )
        
        print(f"✅ Simple email result: {result.status} (ID: {result.email_id})")
        
    except Exception as e:
        print(f"❌ Simple email failed: {str(e)}")
        import traceback
        traceback.print_exc()
    
    try:
        # Test 2: Email with special characters
        print("\n📧 Test 2: Email with special characters")
        special_subject = "Test Email with Special Characters—Testing"
        special_body = """Hi there,

This is a test email with special characters:
• Bullet point
— Em dash
" Smart quotes "
' Apostrophe

Best regards,
Test"""
        
        special_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <p>{special_body.replace(chr(10), '<br>')}</p>
        </body>
        </html>
        """
        
        result = email_sender.send_email(
            recipient_email="romeomino415@gmail.com",
            subject=special_subject,
            html_body=special_html,
            text_body=special_body,
            tags=["test", "special-chars"]
        )
        
        print(f"✅ Special chars email result: {result.status} (ID: {result.email_id})")
        
    except Exception as e:
        print(f"❌ Special chars email failed: {str(e)}")
        import traceback
        traceback.print_exc()

def test_with_actual_content():
    """Test with actual email content from the database."""
    print("\n🧪 Testing with actual email content...")
    
    try:
        from controllers.prospect_automation_controller import ProspectAutomationController
        
        # Load configuration
        config = Config.from_env()
        controller = ProspectAutomationController(config)
        
        # Get a prospect with generated email content
        unsent_prospect_data = controller.notion_manager.get_prospects_by_email_status(
            generation_status="Generated",
            delivery_status="Not Sent"
        )
        
        if not unsent_prospect_data:
            print("❌ No prospects with generated emails found")
            return
        
        # Get the first prospect's data
        prospect_data = unsent_prospect_data[0]
        full_prospect_data = controller.notion_manager.get_prospect_data_for_email(prospect_data['id'])
        
        email_subject = full_prospect_data.get('email_subject', '')
        email_content = full_prospect_data.get('email_content', '')
        
        print(f"📧 Test 3: Actual email content")
        print(f"Subject: {repr(email_subject[:100])}")
        print(f"Content length: {len(email_content)}")
        print(f"Content preview: {repr(email_content[:200])}")
        
        # Clean the content
        import re
        email_content_clean = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', email_content)
        email_subject_clean = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', email_subject)
        
        # Convert to HTML
        html_body = email_content_clean.replace('\n\n', '</p><p>')
        html_body = html_body.replace('\n', '<br>')
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <p>{html_body}</p>
        </body>
        </html>
        """
        
        # Send to test email
        result = controller.email_sender.send_email(
            recipient_email="romeomino415@gmail.com",
            subject=f"[TEST] {email_subject_clean}",
            html_body=html_body,
            text_body=email_content_clean,
            tags=["test", "actual-content"]
        )
        
        print(f"✅ Actual content email result: {result.status} (ID: {result.email_id})")
        
    except Exception as e:
        print(f"❌ Actual content email failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Starting email send test...")
    test_simple_email()
    test_with_actual_content()
    print("\n✅ Test completed!")