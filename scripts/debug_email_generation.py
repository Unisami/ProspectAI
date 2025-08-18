#!/usr/bin/env python3
"""
Debug email generation to find the specific error.
"""

import logging
from services.ai_service import AIService, EmailTemplate
from models.data_models import Prospect
from utils.config import Config

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def debug_email_generation():
    """Debug the email generation process."""
    
    print("🔍 DEBUGGING EMAIL GENERATION")
    print("=" * 50)
    
    try:
        # Initialize AI service
        config = Config.from_env()
        ai_service = AIService(config)
        
        print("✅ AI Service initialized")
        
        # Create a test prospect
        test_prospect = Prospect(
            name="Test User",
            role="Software Engineer",
            company="TestCorp",
            email=None,
            linkedin_url=None,
            source_url="https://test.com",
            notes="Test prospect for debugging"
        )
        
        print(f"✅ Test prospect created: {test_prospect.name}")
        
        # Try to generate email
        print("\n🤖 Attempting email generation...")
        
        result = ai_service.generate_email(
            prospect=test_prospect,
            template_type=EmailTemplate.COLD_OUTREACH
        )
        
        if result.success:
            print("✅ Email generation successful!")
            print(f"Subject: {result.data.subject}")
            print(f"Body preview: {result.data.body[:200]}...")
        else:
            print(f"❌ Email generation failed: {result.error_message}")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        logger.exception("Debug failed")

if __name__ == "__main__":
    debug_email_generation()