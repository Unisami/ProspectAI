"""
Example of integrating LinkedIn scraper with Notion data storage.
This demonstrates how to extract LinkedIn profile data and store it in Notion.
"""

import os
import sys
from datetime import datetime

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.linkedin_scraper import LinkedInScraper
from services.notion_manager import NotionDataManager
from models.data_models import Prospect, ProspectStatus
from utils.config import Config
from utils.logging_config import setup_logging


def main():
    """
    Example of LinkedIn profile extraction and Notion storage integration.
    """
    # Set up logging
    setup_logging()
    
    # Load configuration (you would need to set up your actual config)
    config = Config()
    
    # Example LinkedIn URLs (replace with real ones for testing)
    linkedin_urls = [
        "https://linkedin.com/in/example-profile-1",
        "https://linkedin.com/in/example-profile-2"
    ]
    
    # Initialize services
    linkedin_scraper = LinkedInScraper(config)
    notion_manager = NotionDataManager(config)
    
    print("Starting LinkedIn profile extraction and Notion storage example...")
    
    for linkedin_url in linkedin_urls:
        try:
            print(f"\nProcessing: {linkedin_url}")
            
            # Extract LinkedIn profile data
            print("  Extracting LinkedIn profile data...")
            linkedin_profile = linkedin_scraper.extract_profile_data(linkedin_url)
            
            if not linkedin_profile:
                print("  ❌ Failed to extract LinkedIn profile data")
                continue
            
            print(f"  ✅ Extracted profile for: {linkedin_profile.name}")
            print(f"     Role: {linkedin_profile.current_role}")
            print(f"     Company: {linkedin_profile.company}")
            print(f"     Location: {linkedin_profile.location}")
            print(f"     Skills: {', '.join(linkedin_profile.skills[:5])}...")  # Show first 5 skills
            
            # Create a Prospect object
            prospect = Prospect(
                name=linkedin_profile.name,
                role=linkedin_profile.current_role or "Not specified",
                company=linkedin_profile.company or "Unknown",
                linkedin_url=linkedin_url,
                status=ProspectStatus.NOT_CONTACTED,
                notes=f"Extracted from LinkedIn on {datetime.now().strftime('%Y-%m-%d')}",
                source_url=linkedin_url
            )
            
            # Store prospect with LinkedIn data in Notion
            print("  Storing in Notion database...")
            page_id = notion_manager.store_prospect_with_linkedin_data(prospect, linkedin_profile)
            
            if page_id:
                print(f"  ✅ Stored in Notion with page ID: {page_id}")
            else:
                print("  ⚠️  Prospect may already exist in database")
            
        except Exception as e:
            print(f"  ❌ Error processing {linkedin_url}: {e}")
            continue
    
    print("\n" + "="*50)
    print("LinkedIn integration example completed!")
    print("="*50)


def demonstrate_linkedin_scraper_features():
    """
    Demonstrate various LinkedIn scraper features.
    """
    print("\n" + "="*50)
    print("LinkedIn Scraper Features Demo")
    print("="*50)
    
    # Create a mock config for demo purposes
    config = Config(
        notion_token="demo_token",
        hunter_api_key="demo_key",
        openai_api_key="demo_key",
        
    )
    scraper = LinkedInScraper(config)
    
    # Test URL validation
    print("\n1. URL Validation:")
    test_urls = [
        "https://linkedin.com/in/valid-profile",
        "https://www.linkedin.com/in/another-valid",
        "https://facebook.com/invalid",
        "https://linkedin.com/company/invalid",
        "not-a-url"
    ]
    
    for url in test_urls:
        is_valid = scraper._is_valid_linkedin_url(url)
        status = "✅ Valid" if is_valid else "❌ Invalid"
        print(f"  {url} -> {status}")
    
    # Test experience summary generation
    print("\n2. Experience Summary Generation:")
    from services.linkedin_scraper import LinkedInProfile
    
    sample_profile = LinkedInProfile(
        name="John Doe",
        current_role="Senior Software Engineer",
        company="Tech Corp",
        experience=[
            "Software Engineer at StartupCo (2020-2023)",
            "Junior Developer at WebDev Inc (2018-2020)",
            "Intern at CodeCorp (2017-2018)"
        ],
        skills=["Python", "JavaScript", "React", "Node.js", "AWS"],
        summary="Experienced software engineer with 5+ years in web development"
    )
    
    summary = scraper.get_experience_summary(sample_profile)
    print(f"  Experience Summary: {summary}")
    
    # Test skills extraction
    print("\n3. Skills Extraction:")
    skills = scraper.get_skills(sample_profile)
    print(f"  Top Skills: {', '.join(skills)}")
    
    print("\n" + "="*50)


if __name__ == "__main__":
    # Run the features demo first
    demonstrate_linkedin_scraper_features()
    
    # Note: The main integration example is commented out because it requires
    # actual LinkedIn URLs and proper API keys
    print("\nNote: The full integration example requires:")
    print("- Valid LinkedIn profile URLs")
    print("- Notion API token and database setup")
    print("- Proper configuration in .env file")
    print("\nTo run the full example, uncomment the main() call below and set up your config.")
    
    # Uncomment the line below to run the full integration example
    # main()