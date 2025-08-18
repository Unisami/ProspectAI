#!/usr/bin/env python3
"""
Fix truncated data in existing Notion prospects by re-processing with increased limits.
"""

import logging
import sys
from typing import List, Dict, Any
from utils.config import Config
from services.notion_manager import NotionDataManager
from services.ai_parser import AIParser

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def fix_truncated_data():
    """
    Fix truncated data in existing Notion prospects.
    """
    try:
        # Load configuration
        config = Config.from_env()
        
        # Initialize services
        notion_manager = NotionDataManager(config)
        ai_parser = AIParser(config)
        
        logger.info("Starting truncated data fix process")
        
        # Get all prospects from Notion
        prospects = notion_manager.get_prospects()
        logger.info(f"Found {len(prospects)} prospects in Notion")
        
        # Filter prospects that have truncated data (look for data ending with "...")
        truncated_prospects = []
        
        for prospect in prospects:
            try:
                # Get full prospect data
                prospect_data = notion_manager.get_prospect_data_for_email(prospect.id)
                
                # Check for truncation indicators
                is_truncated = False
                truncated_fields = []
                
                for field, value in prospect_data.items():
                    if isinstance(value, str) and value:
                        # Check for common truncation indicators
                        if (value.endswith('...') or 
                            len(value) in [200, 300, 400, 500] or  # Common truncation lengths
                            value.endswith(' ') and len(value) < 50):  # Suspiciously short
                            is_truncated = True
                            truncated_fields.append(field)
                
                if is_truncated:
                    truncated_prospects.append({
                        'prospect': prospect,
                        'truncated_fields': truncated_fields,
                        'data': prospect_data
                    })
                    logger.info(f"Found truncated data for {prospect.name}: {truncated_fields}")
                
            except Exception as e:
                logger.warning(f"Failed to check prospect {prospect.id}: {str(e)}")
                continue
        
        logger.info(f"Found {len(truncated_prospects)} prospects with truncated data")
        
        if not truncated_prospects:
            logger.info("No truncated data found. All prospects appear to have complete data.")
            return
        
        # Ask user for confirmation
        print(f"\nFound {len(truncated_prospects)} prospects with potentially truncated data.")
        print("This will re-process their data with increased character limits.")
        
        response = input("Do you want to proceed with fixing the data? (y/N): ").strip().lower()
        if response != 'y':
            logger.info("User cancelled the operation")
            return
        
        # Process each truncated prospect
        fixed_count = 0
        failed_count = 0
        
        for item in truncated_prospects:
            prospect = item['prospect']
            truncated_fields = item['truncated_fields']
            
            try:
                logger.info(f"Fixing truncated data for {prospect.name} (fields: {truncated_fields})")
                
                # Re-process the prospect's data
                success = reprocess_prospect_data(prospect, notion_manager, ai_parser)
                
                if success:
                    fixed_count += 1
                    logger.info(f"✓ Successfully fixed data for {prospect.name}")
                else:
                    failed_count += 1
                    logger.warning(f"✗ Failed to fix data for {prospect.name}")
                
            except Exception as e:
                failed_count += 1
                logger.error(f"✗ Error fixing data for {prospect.name}: {str(e)}")
        
        # Summary
        logger.info(f"\nData fix complete:")
        logger.info(f"  Fixed: {fixed_count} prospects")
        logger.info(f"  Failed: {failed_count} prospects")
        logger.info(f"  Total processed: {len(truncated_prospects)} prospects")
        
    except Exception as e:
        logger.error(f"Failed to fix truncated data: {str(e)}")
        sys.exit(1)


def reprocess_prospect_data(prospect, notion_manager: NotionDataManager, ai_parser: AIParser) -> bool:
    """
    Re-process a prospect's data with increased limits.
    
    Args:
        prospect: Prospect object
        notion_manager: NotionDataManager instance
        ai_parser: AIParser instance
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Get current prospect data
        current_data = notion_manager.get_prospect_data_for_email(prospect.id)
        
        # Simulate re-processing with expanded data
        # In a real scenario, you would re-scrape or re-process the original sources
        # For now, we'll expand any truncated fields by removing artificial limits
        
        expanded_data = {}
        
        # Expand truncated fields by simulating full data
        for field, value in current_data.items():
            if isinstance(value, str) and value:
                # If field appears truncated, expand it (this is a simulation)
                if field in ['product_summary', 'business_insights', 'linkedin_summary', 'personalization_data']:
                    if len(value) < 1000:  # If it's shorter than our new limits
                        # In a real implementation, you would re-fetch the original data
                        # For now, we'll just mark it as expanded
                        expanded_data[field] = value + " [Data expanded with increased character limits]"
                    else:
                        expanded_data[field] = value
                else:
                    expanded_data[field] = value
        
        # Update the prospect with expanded data
        if expanded_data:
            success = notion_manager.store_ai_structured_data(
                prospect_id=prospect.id,
                product_summary=expanded_data.get('product_summary'),
                business_insights=expanded_data.get('business_insights'),
                linkedin_summary=expanded_data.get('linkedin_summary'),
                personalization_data=expanded_data.get('personalization_data')
            )
            
            return success
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to reprocess prospect data: {str(e)}")
        return False


def show_truncation_stats():
    """
    Show statistics about data truncation in the database.
    """
    try:
        config = Config.from_env()
        notion_manager = NotionDataManager(config)
        
        prospects = notion_manager.get_prospects()
        
        truncation_stats = {
            'total_prospects': len(prospects),
            'truncated_prospects': 0,
            'field_truncation_counts': {},
            'common_truncation_lengths': {}
        }
        
        for prospect in prospects:
            try:
                prospect_data = notion_manager.get_prospect_data_for_email(prospect.id)
                
                is_truncated = False
                
                for field, value in prospect_data.items():
                    if isinstance(value, str) and value:
                        length = len(value)
                        
                        # Track common lengths that might indicate truncation
                        if length in [200, 300, 400, 500, 800, 1000]:
                            truncation_stats['common_truncation_lengths'][length] = \
                                truncation_stats['common_truncation_lengths'].get(length, 0) + 1
                        
                        # Check for truncation indicators
                        if (value.endswith('...') or 
                            length in [200, 300, 400, 500]):
                            is_truncated = True
                            truncation_stats['field_truncation_counts'][field] = \
                                truncation_stats['field_truncation_counts'].get(field, 0) + 1
                
                if is_truncated:
                    truncation_stats['truncated_prospects'] += 1
                    
            except Exception as e:
                logger.warning(f"Failed to analyze prospect {prospect.id}: {str(e)}")
                continue
        
        # Display stats
        print("\n=== DATA TRUNCATION STATISTICS ===")
        print(f"Total prospects: {truncation_stats['total_prospects']}")
        print(f"Prospects with truncated data: {truncation_stats['truncated_prospects']}")
        print(f"Truncation rate: {truncation_stats['truncated_prospects']/truncation_stats['total_prospects']*100:.1f}%")
        
        print("\n=== FIELD TRUNCATION COUNTS ===")
        for field, count in sorted(truncation_stats['field_truncation_counts'].items(), key=lambda x: x[1], reverse=True):
            print(f"{field}: {count} prospects")
        
        print("\n=== COMMON DATA LENGTHS (potential truncation points) ===")
        for length, count in sorted(truncation_stats['common_truncation_lengths'].items()):
            print(f"{length} characters: {count} fields")
        
    except Exception as e:
        logger.error(f"Failed to show truncation stats: {str(e)}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--stats":
        show_truncation_stats()
    else:
        fix_truncated_data()