#!/usr/bin/env python3
"""Test if business insights are now loaded in the updated model."""

from services.notion_manager import NotionDataManager
from utils.config import Config

def test_business_insights():
    config = Config.from_env()
    notion_manager = NotionDataManager(config)
    
    # Get the most recent prospects
    prospects = notion_manager.get_prospects()
    recent_prospects = sorted([p for p in prospects if p.id], key=lambda x: x.created_at, reverse=True)[:2]
    
    for prospect in recent_prospects:
        print(f'\n=== {prospect.name} at {prospect.company} ===')
        print(f'Created: {prospect.created_at}')
        
        # Check the new AI-structured data fields
        print(f'\nAI-Structured Data:')
        if prospect.product_summary:
            print(f'  Product Summary: {len(prospect.product_summary)} chars - "{prospect.product_summary[:100]}..."')
        else:
            print('  Product Summary: EMPTY')
            
        if prospect.business_insights:
            print(f'  Business Insights: {len(prospect.business_insights)} chars - "{prospect.business_insights[:100]}..."')
        else:
            print('  Business Insights: EMPTY')
            
        if prospect.linkedin_summary:
            print(f'  LinkedIn Summary: {len(prospect.linkedin_summary)} chars - "{prospect.linkedin_summary[:100]}..."')
        else:
            print('  LinkedIn Summary: EMPTY')
            
        if prospect.personalization_data:
            print(f'  Personalization Data: {len(prospect.personalization_data)} chars - "{prospect.personalization_data[:100]}..."')
        else:
            print('  Personalization Data: EMPTY')

if __name__ == "__main__":
    test_business_insights()
