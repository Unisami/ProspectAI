#!/usr/bin/env python3
"""
Simple debug script to test email content length limits.
"""

import logging
from utils.config import Config
from services.email_sender import EmailSender

# Enable detailed logging
logging.basicConfig(level=logging.INFO)

def test_email_lengths():
    """Test different email content lengths to find the breaking point."""
    print("🧪 Testing email content lengths...")
    
    config = Config.from_env()
    sender = EmailSender(config)
    
    # Base content that we know works
    base_content = "This is a test email. "
    
    # Test different lengths
    test_lengths = [50, 100, 500, 1000, 1500, 2000]
    
    for length in test_lengths:
        # Create content of specific length
        content = (base_content * (length // len(base_content) + 1))[:length]
        html_content = f"<p>{content}</p>"
        
        print(f"\n📧 Testing length {length}...")
        print(f"Content preview: {repr(content[:100])}")
        
        try:
            result = sender.send_email(
                recipient_email="test@example.com",
                subject=f"Length Test {length}",
                html_body=html_content,
                text_body=content,
                tags=["length-test"]
            )
            
            if result.status == "sent" and result.email_id:
                print(f"✅ SUCCESS: {result.email_id}")
            else:
                print(f"❌ FAILED: {result.status}")
                
        except Exception as e:
            print(f"❌ EXCEPTION: {str(e)}")
            break

if __name__ == "__main__":
    test_email_lengths()