#!/usr/bin/env python3
"""
Find and update missing LinkedIn URLs for existing prospects in Notion.
"""

import logging
import sys
from typing import List, Dict, Any
from utils.config import Config
from services.notion_manager import NotionDataManager
from services.linkedin_finder import LinkedInFinder
from models.data_models import TeamMember

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def find_missing_linkedin_urls():
    """
    Find and update missing LinkedIn URLs for existing prospects.
    """
    try:
        # Load configuration
        config = Config.from_env()
        
        # Initialize services
        notion_manager = NotionDataManager(config)
        linkedin_finder = LinkedInFinder(config)
        
        logger.info("Starting LinkedIn URL discovery process")
        
        # Get all prospects from Notion
        prospects = notion_manager.get_prospects()
        logger.info(f"Found {len(prospects)} prospects in Notion")
        
        # Filter prospects without LinkedIn URLs
        prospects_without_linkedin = [p for p in prospects if not p.linkedin_url]
        logger.info(f"Found {len(prospects_without_linkedin)} prospects without LinkedIn URLs")
        
        if not prospects_without_linkedin:
            logger.info("All prospects already have LinkedIn URLs!")
            return
        
        # Ask user for confirmation
        print(f"\nFound {len(prospects_without_linkedin)} prospects without LinkedIn URLs.")
        print("This will search for their LinkedIn profiles using multiple strategies.")
        print("Note: This process may take several minutes due to rate limiting.")
        
        response = input("Do you want to proceed with LinkedIn URL discovery? (y/N): ").strip().lower()
        if response != 'y':
            logger.info("User cancelled the operation")
            return
        
        # Process prospects in batches to avoid overwhelming external services
        batch_size = 10
        found_count = 0
        failed_count = 0
        
        for i in range(0, len(prospects_without_linkedin), batch_size):
            batch = prospects_without_linkedin[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}/{(len(prospects_without_linkedin) + batch_size - 1)//batch_size}")
            
            for prospect in batch:
                try:
                    logger.info(f"Searching for LinkedIn URL: {prospect.name} at {prospect.company}")
                    
                    # Create TeamMember object for LinkedIn finder
                    team_member = TeamMember(
                        name=prospect.name,
                        role=prospect.role,
                        company=prospect.company,
                        linkedin_url=None
                    )
                    
                    # Find LinkedIn URL
                    updated_members = linkedin_finder.find_linkedin_urls_for_team([team_member])
                    
                    if updated_members and updated_members[0].linkedin_url:
                        linkedin_url = updated_members[0].linkedin_url
                        logger.info(f"Found LinkedIn URL for {prospect.name}: {linkedin_url}")
                        
                        # Update prospect in Notion
                        success = update_prospect_linkedin_url(notion_manager, prospect.id, linkedin_url)
                        
                        if success:
                            found_count += 1
                            logger.info(f"✓ Updated LinkedIn URL for {prospect.name}")
                        else:
                            failed_count += 1
                            logger.warning(f"✗ Failed to update LinkedIn URL for {prospect.name}")
                    else:
                        logger.info(f"No LinkedIn URL found for {prospect.name}")
                        failed_count += 1
                
                except Exception as e:
                    failed_count += 1
                    logger.error(f"✗ Error processing {prospect.name}: {str(e)}")
        
        # Summary
        logger.info(f"\nLinkedIn URL discovery complete:")
        logger.info(f"  Found and updated: {found_count} prospects")
        logger.info(f"  Not found/failed: {failed_count} prospects")
        logger.info(f"  Total processed: {len(prospects_without_linkedin)} prospects")
        
    except Exception as e:
        logger.error(f"Failed to find missing LinkedIn URLs: {str(e)}")
        sys.exit(1)


def update_prospect_linkedin_url(notion_manager: NotionDataManager, prospect_id: str, linkedin_url: str) -> bool:
    """
    Update a prospect's LinkedIn URL in Notion.
    
    Args:
        notion_manager: NotionDataManager instance
        prospect_id: Prospect ID in Notion
        linkedin_url: LinkedIn URL to update
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Update the LinkedIn URL field
        properties = {
            "LinkedIn": {"url": linkedin_url}
        }
        
        notion_manager.client.pages.update(
            page_id=prospect_id,
            properties=properties
        )
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to update LinkedIn URL: {str(e)}")
        return False


def show_linkedin_stats():
    """
    Show statistics about LinkedIn URL coverage in the database.
    """
    try:
        config = Config.from_env()
        notion_manager = NotionDataManager(config)
        
        prospects = notion_manager.get_prospects()
        
        stats = {
            'total_prospects': len(prospects),
            'with_linkedin': 0,
            'without_linkedin': 0,
            'companies_with_linkedin': set(),
            'companies_without_linkedin': set()
        }
        
        for prospect in prospects:
            if prospect.linkedin_url:
                stats['with_linkedin'] += 1
                stats['companies_with_linkedin'].add(prospect.company)
            else:
                stats['without_linkedin'] += 1
                stats['companies_without_linkedin'].add(prospect.company)
        
        # Display stats
        print("\n=== LINKEDIN URL COVERAGE STATISTICS ===")
        print(f"Total prospects: {stats['total_prospects']}")
        print(f"With LinkedIn URLs: {stats['with_linkedin']} ({stats['with_linkedin']/stats['total_prospects']*100:.1f}%)")
        print(f"Without LinkedIn URLs: {stats['without_linkedin']} ({stats['without_linkedin']/stats['total_prospects']*100:.1f}%)")
        
        print(f"\nCompanies with LinkedIn coverage: {len(stats['companies_with_linkedin'])}")
        print(f"Companies without LinkedIn coverage: {len(stats['companies_without_linkedin'])}")
        
        # Show companies that need LinkedIn URL discovery
        if stats['companies_without_linkedin']:
            print(f"\n=== COMPANIES NEEDING LINKEDIN URL DISCOVERY ===")
            for company in sorted(stats['companies_without_linkedin']):
                count = len([p for p in prospects if p.company == company and not p.linkedin_url])
                print(f"{company}: {count} prospects")
        
    except Exception as e:
        logger.error(f"Failed to show LinkedIn stats: {str(e)}")


def test_linkedin_finder():
    """
    Test the LinkedIn finder with a sample team member.
    """
    try:
        config = Config.from_env()
        linkedin_finder = LinkedInFinder(config)
        
        # Test with a sample team member
        test_member = TeamMember(
            name="John Smith",  # Replace with a real name for testing
            role="CEO",
            company="TestCorp",  # Replace with a real company for testing
            linkedin_url=None
        )
        
        print(f"Testing LinkedIn finder with: {test_member.name} at {test_member.company}")
        
        updated_members = linkedin_finder.find_linkedin_urls_for_team([test_member])
        
        if updated_members and updated_members[0].linkedin_url:
            print(f"✓ Found LinkedIn URL: {updated_members[0].linkedin_url}")
        else:
            print("✗ No LinkedIn URL found")
        
    except Exception as e:
        logger.error(f"LinkedIn finder test failed: {str(e)}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--stats":
            show_linkedin_stats()
        elif sys.argv[1] == "--test":
            test_linkedin_finder()
        else:
            print("Usage: python find_missing_linkedin_urls.py [--stats|--test]")
    else:
        find_missing_linkedin_urls()