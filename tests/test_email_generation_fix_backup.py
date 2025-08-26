#!/usr/bin/env python3
"""
Test script to verify the email generation fix.
This tests whether AI-structured data is properly passed to prevent placeholders.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.ai_service import AIService
from models.data_models import Prospect, LinkedInProfile, ProspectStatus, EmailTemplate, SenderProfile
from utils.configuration_service import ConfigurationService

def test_email_generation():
    """Test email generation with AI-structured data to ensure no placeholders."""
    
    # Initialize services
    config = ConfigurationService()
    ai_service = AIService(config.get_config())
    
    # Create a test prospect
    prospect = Prospect(
        id="test-prospect-123",
        name="John Smith",
        email="john@testcompany.com",
        company="TestCompany Inc",
        role="CTO",
        linkedin_url="https://linkedin.com/in/johnsmith",
        status=ProspectStatus.NOT_CONTACTED
    )
    
    # Create test LinkedIn profile
    linkedin_profile = LinkedInProfile(
        name="John Smith",
        current_role="CTO at TestCompany Inc",
        summary="Experienced technology leader focused on AI and automation solutions.",
        experience=["CTO at TestCompany Inc", "VP Engineering at PrevCompany"],
        skills=["AI", "Machine Learning", "Software Architecture"]
    )
    
    # Create test AI-structured data (this is what was missing before)
    ai_structured_data = {
        'business_insights': "TestCompany Inc is a rapidly growing B2B SaaS platform that helps mid-market companies streamline their customer onboarding processes. They've seen 300% growth in the past year and are expanding their engineering team to handle increased demand. Their main challenges include scaling their infrastructure and improving customer support efficiency.",
        'product_summary': "Their flagship product is an automated customer onboarding platform that reduces manual work by 80% and improves customer satisfaction scores. The platform integrates with popular CRMs and provides detailed analytics on onboarding performance.",
        'personalization_data': "John recently posted about the challenges of scaling engineering teams and mentioned they're looking for solutions to improve developer productivity. He's particularly interested in AI-powered tools that can automate repetitive tasks.",
        'market_analysis': "The customer onboarding software market is valued at $2.1B and growing at 15% CAGR. Key competitors include Userpilot and Appcues, but TestCompany differentiates through deeper CRM integrations.",
        'product_features': "Real-time analytics dashboard, drag-and-drop workflow builder, multi-channel communication automation, advanced segmentation, A/B testing capabilities, enterprise-grade security"
    }
    
    # Test product analysis data (what comes from Notion)
    product_analysis = {
        'company_name': 'TestCompany Inc',
        'product_description': 'Automated customer onboarding platform',
        'business_insights': ai_structured_data['business_insights'],
        'product_summary': ai_structured_data['product_summary'],
        'personalization_data': ai_structured_data['personalization_data'],
        'market_analysis': ai_structured_data['market_analysis'],
        'product_features': ai_structured_data['product_features']
    }
    
    # Create sender profile
    sender_profile = SenderProfile(
        name='Minhal Abdul Sami',
        current_role='AI Solutions Engineer',
        years_experience=5,
        key_skills=['AI', 'Automation', 'Process Optimization'],
        experience_summary='Expert in AI automation and process optimization',
        value_proposition='Helping companies increase productivity through AI-powered automation'
    )
    
    print("🧪 Testing Email Generation Fix...")
    print("=" * 50)
    
    try:
        # Generate email with AI-structured data (this is the fix we implemented)
        result = ai_service.generate_email(
            prospect=prospect,
            template_type=EmailTemplate.COLD_OUTREACH,
            linkedin_profile=linkedin_profile,
            product_analysis=product_analysis,
            additional_context={
                'source_mention': 'ProductHunt',
                'discovery_context': f'I discovered {prospect.company} on ProductHunt'
            },
            ai_structured_data=ai_structured_data,  # This was missing before!
            sender_profile=sender_profile
        )
        
        if result and result.success:
            email_content = result.data.content if hasattr(result.data, 'content') else str(result.data)
            
            print("✅ Email generated successfully!")
            print("\n📧 Generated Email:")
            print("-" * 40)
            print(email_content)
            print("-" * 40)
            
            # Check for placeholders that indicate the fix didn't work
            placeholders = [
                '[insert company',
                '[insert specific',
                '[mention specific',
                '[add specific',
                '[reference their',
                'PLACEHOLDER',
                '{{',
                '[[',
                '[YOUR_'
            ]
            
            found_placeholders = []
            for placeholder in placeholders:
                if placeholder.lower() in email_content.lower():
                    found_placeholders.append(placeholder)
            
            if found_placeholders:
                print(f"\n❌ PLACEHOLDERS FOUND: {found_placeholders}")
                print("The fix may not be working properly.")
                return False
            else:
                print("\n✅ NO PLACEHOLDERS FOUND!")
                
                # Check if specific business insights are mentioned
                insights_mentioned = []
                if "300% growth" in email_content:
                    insights_mentioned.append("Growth metrics")
                if "customer onboarding" in email_content.lower():
                    insights_mentioned.append("Product focus")
                if "scaling" in email_content.lower():
                    insights_mentioned.append("Scaling challenges")
                if "80%" in email_content:
                    insights_mentioned.append("Product benefits")
                
                if insights_mentioned:
                    print(f"✅ BUSINESS INSIGHTS USED: {', '.join(insights_mentioned)}")
                    print("🎉 FIX IS WORKING! AI is using actual data instead of placeholders.")
                    return True
                else:
                    print("⚠️  Email generated but specific business insights not clearly referenced.")
                    return False
        else:
            print(f"❌ Email generation failed: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Error during email generation: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_email_generation()
    if success:
        print("\n🎉 EMAIL GENERATION FIX VERIFIED!")
        print("The system now properly passes AI-structured data to prevent placeholders.")
    else:
        print("\n❌ Email generation fix needs more work.")
    
    sys.exit(0 if success else 1)
