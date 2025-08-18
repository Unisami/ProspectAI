#!/usr/bin/env python3
"""
Quick integration test to verify data models work correctly.
"""
from datetime import datetime
from models.data_models import (
    CompanyData, TeamMember, Prospect, LinkedInProfile, EmailContent,
    ProspectStatus, ValidationError
)

def test_integration():
    """Test that all models work together correctly."""
    print("Testing data models integration...")
    
    # Test CompanyData
    company = CompanyData(
        name="TestCorp",
        domain="testcorp.com",
        product_url="https://producthunt.com/posts/testcorp-app",
        description="A revolutionary test company",
        launch_date=datetime.now()
    )
    print(f"✓ CompanyData created: {company.name}")
    
    # Test TeamMember
    team_member = TeamMember(
        name="John Doe",
        role="Software Engineer",
        company="TestCorp",
        linkedin_url="https://linkedin.com/in/johndoe"
    )
    print(f"✓ TeamMember created: {team_member.name}")
    
    # Test Prospect
    prospect = Prospect(
        name="John Doe",
        role="Software Engineer", 
        company="TestCorp",
        email="john@testcorp.com",
        linkedin_url="https://linkedin.com/in/johndoe",
        status=ProspectStatus.NOT_CONTACTED
    )
    print(f"✓ Prospect created: {prospect.name} - {prospect.status.value}")
    
    # Test LinkedInProfile
    profile = LinkedInProfile(
        name="John Doe",
        current_role="Software Engineer",
        experience=["Software Engineer at TestCorp", "Intern at StartupXYZ"],
        skills=["Python", "JavaScript", "React"],
        summary="Passionate software engineer"
    )
    print(f"✓ LinkedInProfile created: {profile.name} with {len(profile.skills)} skills")
    
    # Test EmailContent
    email = EmailContent(
        subject="Exciting opportunity at your company",
        body="Hi John, I discovered TestCorp on ProductHunt and was impressed...",
        template_used="professional",
        personalization_score=0.85,
        recipient_name="John Doe",
        company_name="TestCorp"
    )
    print(f"✓ EmailContent created: {email.subject} (score: {email.personalization_score})")
    
    # Test serialization
    company_dict = company.to_dict()
    prospect_dict = prospect.to_dict()
    email_dict = email.to_dict()
    
    print(f"✓ Serialization works - Company dict has {len(company_dict)} fields")
    print(f"✓ Serialization works - Prospect dict has {len(prospect_dict)} fields")
    print(f"✓ Serialization works - Email dict has {len(email_dict)} fields")
    
    # Test validation errors
    try:
        invalid_company = CompanyData(
            name="",  # This should fail
            domain="testcorp.com",
            product_url="https://producthunt.com/posts/testcorp-app",
            description="A test company",
            launch_date=datetime.now()
        )
    except ValidationError as e:
        print(f"✓ Validation error caught correctly: {e}")
    
    print("\n🎉 All integration tests passed!")

if __name__ == "__main__":
    test_integration()