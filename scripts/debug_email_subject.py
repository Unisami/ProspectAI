#!/usr/bin/env python3
"""
Debug email subject generation to see what's being generated.
"""

import logging
from services.ai_service import AIService, EmailTemplate
from models.data_models import Prospect
from utils.config import Config

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def debug_email_subject():
    """Debug the email subject generation."""
    
    print("🔍 DEBUGGING EMAIL SUBJECT GENERATION")
    print("=" * 50)
    
    try:
        # Initialize AI service
        config = Config.from_env()
        ai_service = AIService(config)
        
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
        
        # Try to generate email and catch the raw response
        print("\n🤖 Attempting email generation...")
        
        # Let's manually call the AI generation to see the raw response
        from services.openai_client_manager import CompletionRequest
        
        # Get template configuration
        template_config = ai_service._email_templates[EmailTemplate.COLD_OUTREACH]
        
        # Prepare personalization data
        personalization_data = ai_service._prepare_personalization_data(test_prospect)
        
        # Generate user prompt from template
        user_prompt = template_config["user_template"].format(**personalization_data)
        
        # Create completion request
        request = CompletionRequest(
            messages=[
                {"role": "system", "content": template_config["system_prompt"]},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=800
        )
        
        # Make completion request
        response = ai_service.client_manager.make_completion(request, ai_service.client_id)
        
        if response.success:
            print(f"\n📧 RAW AI RESPONSE:")
            print("=" * 40)
            print(response.content)
            print("=" * 40)
            
            # Try to parse it
            subject, body = ai_service._parse_generated_email_content(response.content)
            
            print(f"\n📊 PARSED RESULTS:")
            print(f"Subject: '{subject}' (Length: {len(subject)} characters)")
            print(f"Body preview: {body[:200]}...")
            
            if len(subject) > 200:
                print(f"\n❌ SUBJECT TOO LONG: {len(subject)} characters (max 200)")
                print("Need to adjust the prompt or validation")
            else:
                print(f"\n✅ SUBJECT LENGTH OK: {len(subject)} characters")
        else:
            print(f"❌ AI request failed: {response.error_message}")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        logger.exception("Debug failed")

if __name__ == "__main__":
    debug_email_subject()