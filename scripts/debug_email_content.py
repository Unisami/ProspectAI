#!/usr/bin/env python3
"""
Debug script to examine email content from database and identify validation issues.
"""

import re
from utils.config import Config
from controllers.prospect_automation_controller import ProspectAutomationController

def debug_email_content():
    """Debug the actual email content causing validation errors."""
    print("🔍 Debugging email content from database...")
    
    try:
        config = Config.from_env()
        controller = ProspectAutomationController(config)
        
        # Get prospects with generated emails
        unsent_prospect_data = controller.notion_manager.get_prospects_by_email_status(
            generation_status="Generated",
            delivery_status="Not Sent"
        )
        
        if not unsent_prospect_data:
            print("❌ No prospects with generated emails found")
            return
        
        # Examine the first prospect's email content
        prospect_data = unsent_prospect_data[0]
        full_prospect_data = controller.notion_manager.get_prospect_data_for_email(prospect_data['id'])
        
        email_subject = full_prospect_data.get('email_subject', '')
        email_content = full_prospect_data.get('email_content', '')
        
        print(f"\n📧 Analyzing email content for: {full_prospect_data.get('name', 'Unknown')}")
        print(f"Subject: {repr(email_subject)}")
        print(f"Content length: {len(email_content)}")
        
        # Check for problematic characters
        print(f"\n🔍 Character analysis:")
        print(f"- Contains null bytes: {'\\x00' in repr(email_content)}")
        print(f"- Contains control chars: {bool(re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', email_content))}")
        print(f"- Contains unicode: {any(ord(c) > 127 for c in email_content)}")
        print(f"- Contains quotes: {repr(email_content.count('\"'))}")
        print(f"- Contains single quotes: {repr(email_content.count(chr(39)))}")
        print(f"- Contains backslashes: {repr(email_content.count('\\\\'))}")
        
        # Show first 500 characters with repr to see exact formatting
        print(f"\n📝 First 500 characters (repr):")
        print(repr(email_content[:500]))
        
        # Try to identify specific problematic patterns
        print(f"\n🚨 Potential issues:")
        
        # Check for empty required fields
        if not email_subject.strip():
            print("- Empty subject after strip()")
        if not email_content.strip():
            print("- Empty content after strip()")
            
        # Check for JSON-breaking characters
        json_breaking = ['"', '\\', '\n', '\r', '\t']
        for char in json_breaking:
            count = email_content.count(char)
            if count > 0:
                print(f"- Contains {count} '{char}' characters")
        
        # Try cleaning the content
        print(f"\n🧹 Testing content cleaning:")
        
        # Clean control characters
        content_clean = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', email_content)
        print(f"- After control char removal: {len(content_clean)} chars")
        
        # Clean unicode
        content_ascii = email_content.encode('ascii', 'ignore').decode('ascii')
        print(f"- After ASCII conversion: {len(content_ascii)} chars")
        
        # Test with minimal content
        print(f"\n🧪 Testing with progressively more content:")
        
        test_lengths = [100, 200, 500, 1000, len(email_content)]
        for length in test_lengths:
            test_content = email_content[:length]
            test_subject = email_subject
            
            # Clean the test content
            test_content_clean = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', test_content)
            test_subject_clean = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', test_subject)
            
            try:
                # Convert to HTML
                html_body = test_content_clean.replace('\n\n', '</p><p>')
                html_body = html_body.replace('\n', '<br>')
                html_body = f"""
                <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <p>{html_body}</p>
                </body>
                </html>
                """
                
                # Test send
                result = controller.email_sender.send_email(
                    recipient_email="test@example.com",
                    subject=f"[TEST {length}] {test_subject_clean}",
                    html_body=html_body,
                    text_body=test_content_clean,
                    tags=["debug", f"length-{length}"]
                )
                
                print(f"  ✅ Length {length}: SUCCESS (ID: {result.email_id})")
                
            except Exception as e:
                print(f"  ❌ Length {length}: FAILED - {str(e)}")
                if length == 100:  # If even 100 chars fail, show the content
                    print(f"     Content: {repr(test_content[:100])}")
                break
        
    except Exception as e:
        print(f"❌ Debug failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_email_content()