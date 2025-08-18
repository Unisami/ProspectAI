#!/usr/bin/env python3

"""
Script to create the Notion database for storing prospects.
"""

import os
from services.notion_manager import NotionDataManager
from utils.config import Config

def create_database():
    """Create the Notion database for prospects."""
    
    print("=== Creating Notion Database ===")
    
    try:
        # Load configuration
        config = Config.from_env()
        
        # Check if Notion token is configured
        if not config.notion_token:
            print("❌ Error: NOTION_TOKEN not configured in environment variables")
            print("Please set your Notion integration token in the .env file")
            return False
        
        print(f"✅ Notion token configured (length: {len(config.notion_token)} characters)")
        
        # Check if database ID is already set
        if config.notion_database_id:
            print(f"⚠️  Database ID already configured: {config.notion_database_id}")
            print("Do you want to create a new database anyway? (y/N): ", end="")
            response = input().strip().lower()
            if response != 'y':
                print("Cancelled.")
                return False
        
        # Create Notion manager
        notion_manager = NotionDataManager(config)
        
        print("🔍 Searching for existing pages to use as parent...")
        
        # Search for existing pages first
        try:
            response = notion_manager.client.search(
                filter={"property": "object", "value": "page"}
            )
            
            if response["results"]:
                print(f"✅ Found {len(response['results'])} existing pages")
                
                # Show available pages
                print("\nAvailable pages to use as parent:")
                for i, page in enumerate(response["results"][:5]):  # Show first 5
                    title = "Untitled"
                    if "properties" in page and "title" in page["properties"]:
                        title_prop = page["properties"]["title"]
                        if title_prop.get("title") and len(title_prop["title"]) > 0:
                            title = title_prop["title"][0]["text"]["content"]
                    elif "properties" in page:
                        # Try to find any title-like property
                        for prop_name, prop_value in page["properties"].items():
                            if prop_value.get("type") == "title" and prop_value.get("title"):
                                if len(prop_value["title"]) > 0:
                                    title = prop_value["title"][0]["text"]["content"]
                                    break
                    
                    print(f"  {i+1}. {title} (ID: {page['id']})")
                
                print(f"\nUsing the first page as parent: {title}")
                parent_page_id = response["results"][0]["id"]
                
            else:
                print("❌ No existing pages found that are shared with your integration.")
                print("\nTo create a database, you need to:")
                print("1. Go to your Notion workspace")
                print("2. Create a new page (or use an existing one)")
                print("3. Click the '...' menu on the page")
                print("4. Select 'Add connections'")
                print("5. Find and add your integration (the one you created for this project)")
                print("6. Run this script again")
                print("\nAlternatively, you can:")
                print("- Create a database manually in Notion")
                print("- Share it with your integration")
                print("- Copy the database ID and add it to your .env file as NOTION_DATABASE_ID")
                return False
                
        except Exception as e:
            print(f"❌ Error searching for pages: {e}")
            return False
        
        print("🔄 Creating Notion database...")
        
        # Create the database with the found parent page
        database_id = notion_manager._create_database_with_parent(parent_page_id)
        
        print(f"✅ Successfully created database with ID: {database_id}")
        
        # Update .env file with the new database ID
        env_file = ".env"
        if os.path.exists(env_file):
            print(f"🔄 Updating {env_file} with database ID...")
            
            # Read current .env content
            with open(env_file, 'r') as f:
                lines = f.readlines()
            
            # Update or add NOTION_DATABASE_ID
            updated = False
            for i, line in enumerate(lines):
                if line.startswith('NOTION_DATABASE_ID='):
                    lines[i] = f'NOTION_DATABASE_ID={database_id}\n'
                    updated = True
                    break
            
            if not updated:
                lines.append(f'NOTION_DATABASE_ID={database_id}\n')
            
            # Write back to .env
            with open(env_file, 'w') as f:
                f.writelines(lines)
            
            print(f"✅ Updated {env_file} with NOTION_DATABASE_ID={database_id}")
        else:
            print(f"⚠️  .env file not found. Please add this to your environment:")
            print(f"NOTION_DATABASE_ID={database_id}")
        
        print("\n🎉 Database creation completed successfully!")
        print("You can now run the discovery pipeline to store prospects.")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating database: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    create_database()