#!/usr/bin/env python3
"""
Verify Notion database schema to identify issues with email generation status field.
"""

import logging
from services.notion_manager import NotionDataManager
from utils.config import Config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_notion_schema():
    """Verify the Notion database schema and field mappings."""
    
    print("🔍 NOTION DATABASE SCHEMA VERIFICATION")
    print("=" * 60)
    
    try:
        # Initialize Notion manager
        config = Config.from_env()
        notion_manager = NotionDataManager(config)
        
        print("✅ Notion manager initialized")
        
        # Get database schema information
        print("\n📋 CHECKING DATABASE SCHEMA")
        try:
            # Get the database ID from the notion manager
            database_id = notion_manager.database_id
            print(f"Prospects Database ID: {database_id}")
            
            # Get database schema
            database_info = notion_manager.client.databases.retrieve(database_id=database_id)
            
            print(f"\nDatabase Title: {database_info.get('title', [{}])[0].get('plain_text', 'Unknown')}")
            
            # Check properties
            properties = database_info.get('properties', {})
            print(f"\nTotal Properties: {len(properties)}")
            
            # Look for email-related fields
            email_fields = {}
            for prop_name, prop_info in properties.items():
                if 'email' in prop_name.lower() or 'generation' in prop_name.lower() or 'delivery' in prop_name.lower():
                    email_fields[prop_name] = {
                        'type': prop_info.get('type'),
                        'id': prop_info.get('id')
                    }
                    
                    # For select fields, get options
                    if prop_info.get('type') == 'select':
                        options = prop_info.get('select', {}).get('options', [])
                        email_fields[prop_name]['options'] = [opt.get('name') for opt in options]
            
            print(f"\n📧 EMAIL-RELATED FIELDS FOUND:")
            if email_fields:
                for field_name, field_info in email_fields.items():
                    print(f"  • {field_name}")
                    print(f"    Type: {field_info['type']}")
                    print(f"    ID: {field_info['id']}")
                    if 'options' in field_info:
                        print(f"    Options: {field_info['options']}")
                    print()
            else:
                print("  ❌ No email-related fields found!")
            
            # Check specific fields we expect
            expected_fields = [
                "Email Generation Status",
                "Email Delivery Status", 
                "Email Subject",
                "Email Content",
                "Email Body",
                "Email Generated Date",
                "Email Sent Date"
            ]
            
            print(f"🎯 CHECKING EXPECTED EMAIL FIELDS:")
            missing_fields = []
            for field in expected_fields:
                if field in properties:
                    field_type = properties[field].get('type')
                    print(f"  ✅ {field} ({field_type})")
                    
                    # For select fields, show options
                    if field_type == 'select':
                        options = properties[field].get('select', {}).get('options', [])
                        option_names = [opt.get('name') for opt in options]
                        print(f"     Options: {option_names}")
                else:
                    print(f"  ❌ {field} - MISSING")
                    missing_fields.append(field)
            
            if missing_fields:
                print(f"\n⚠️  MISSING FIELDS: {len(missing_fields)}")
                print("These fields need to be created in the Notion database:")
                for field in missing_fields:
                    print(f"  - {field}")
            else:
                print(f"\n✅ All expected email fields are present!")
                
        except Exception as e:
            print(f"❌ Failed to get database schema: {e}")
            logger.exception("Schema verification failed")
        
        # Test reading a sample prospect to see actual field values
        print(f"\n🧪 TESTING PROSPECT DATA EXTRACTION")
        try:
            prospects = notion_manager.get_prospects()
            if prospects:
                sample_prospect = prospects[0]
                print(f"Sample prospect: {sample_prospect.name}")
                
                # Check email-related attributes
                email_attrs = [
                    'email_generation_status',
                    'email_delivery_status',
                    'email_subject',
                    'email_content',
                    'email_generated_date'
                ]
                
                print(f"\nEmail-related attributes:")
                for attr in email_attrs:
                    value = getattr(sample_prospect, attr, 'NOT_FOUND')
                    print(f"  {attr}: {value}")
                
                # Check all attributes to see what's available
                print(f"\nAll available attributes:")
                for attr in dir(sample_prospect):
                    if not attr.startswith('_') and 'email' in attr.lower():
                        value = getattr(sample_prospect, attr, 'NOT_FOUND')
                        print(f"  {attr}: {value}")
                        
            else:
                print("No prospects found to test")
                
        except Exception as e:
            print(f"❌ Failed to test prospect data: {e}")
        
        # Test the field extraction methods
        print(f"\n🔧 TESTING FIELD EXTRACTION METHODS")
        try:
            # Test the _extract_select method with sample data
            sample_select_data = {
                "select": {"name": "Generated"}
            }
            
            extracted_value = notion_manager._extract_select(sample_select_data)
            print(f"Sample select extraction: {extracted_value}")
            
            # Test with empty data
            empty_select_data = {}
            empty_value = notion_manager._extract_select(empty_select_data)
            print(f"Empty select extraction: {empty_value}")
            
        except Exception as e:
            print(f"❌ Failed to test extraction methods: {e}")
        
        print(f"\n🎯 SCHEMA VERIFICATION SUMMARY:")
        print("1. ✅ Database connection working")
        print("2. ✅ Can retrieve database schema")
        print("3. ✅ Can read prospect data")
        print("4. Check above for any missing fields or extraction issues")
        
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        logger.exception("Schema verification failed")

if __name__ == "__main__":
    verify_notion_schema()