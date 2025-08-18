#!/usr/bin/env python3
"""
Debug the discovery issue where it claims no unprocessed companies exist.
"""

from controllers.prospect_automation_controller import ProspectAutomationController
from utils.config import Config

def debug_discovery():
    """Debug the discovery process."""
    print("🔍 Debugging Discovery Process")
    print("=" * 40)
    
    # Initialize controller
    config = Config.from_env()
    controller = ProspectAutomationController(config)
    
    # Clear the cache to force refresh
    controller._clear_processed_companies_cache()
    print("✅ Cleared processed companies cache")
    
    # Get fresh data from Notion
    companies, domains = controller._get_cached_processed_companies()
    print(f"📊 Found {len(companies)} processed companies and {len(domains)} domains in Notion")
    
    # Show recent processed companies
    if companies:
        print("\n📋 Recent processed companies:")
        for i, company in enumerate(companies[-10:]):
            print(f"  {i+1}. {company}")
    
    # Test ProductHunt scraping
    print("\n🔍 Testing ProductHunt discovery...")
    try:
        # Get some companies from ProductHunt
        raw_products = controller.product_hunt_scraper.get_latest_products(limit=5)
        # Convert to CompanyData format
        from models.data_models import CompanyData
        raw_companies = []
        for product in raw_products:
            try:
                domain = controller.product_hunt_scraper.extract_company_domain(product)
                company = CompanyData(
                    name=product.name,
                    domain=domain,
                    product_url=product.product_url,
                    description=product.description,
                    launch_date=product.launch_date
                )
                raw_companies.append(company)
            except Exception as e:
                print(f"  ⚠️ Error converting {product.name}: {e}")
                continue
        print(f"📦 Found {len(raw_companies)} companies from ProductHunt")
        
        if raw_companies:
            print("\n📋 Companies from ProductHunt:")
            for i, company in enumerate(raw_companies):
                print(f"  {i+1}. {company.name} - {company.domain}")
                
                # Check if this company would be filtered out
                is_processed_name = company.name.lower() in [c.lower() for c in companies]
                is_processed_domain = company.domain and company.domain.lower() in [d.lower() for d in domains]
                
                if is_processed_name:
                    print(f"      ❌ Would be filtered out by NAME")
                elif is_processed_domain:
                    print(f"      ❌ Would be filtered out by DOMAIN")
                else:
                    print(f"      ✅ Would be processed (NEW)")
        
        # Test the filtering
        print(f"\n🔍 Testing company filtering...")
        unprocessed = controller._filter_unprocessed_companies(raw_companies)
        print(f"📊 After filtering: {len(unprocessed)} unprocessed companies")
        
        if unprocessed:
            print("\n📋 Unprocessed companies:")
            for i, company in enumerate(unprocessed):
                print(f"  {i+1}. {company.name} - {company.domain}")
        else:
            print("❌ No unprocessed companies found - this is the problem!")
            
    except Exception as e:
        print(f"❌ Error during ProductHunt scraping: {e}")
    
    print("\n🎯 Diagnosis:")
    if len(companies) > 50:
        print("- You have many processed companies in Notion")
        print("- The system might be too aggressive in filtering")
        print("- Consider clearing old data or adjusting the filtering logic")
    else:
        print("- Reasonable number of processed companies")
        print("- The issue might be elsewhere")

if __name__ == "__main__":
    debug_discovery()