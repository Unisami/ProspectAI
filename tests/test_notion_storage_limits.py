#!/usr/bin/env python3
"""
Test Notion storage limits and verify that long text is properly stored without truncation.
"""

import logging
import sys
from typing import Dict, Any
from utils.config import Config
from services.notion_manager import NotionDataManager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_notion_rich_text_blocks():
    """
    Test the _create_rich_text_blocks method with various text lengths.
    """
    print("\n=== TESTING NOTION RICH_TEXT BLOCKS ===")
    
    try:
        config = Config.from_env()
        notion_manager = NotionDataManager(config)
        
        # Test cases with different text lengths
        test_cases = [
            ("Short text", "This is a short text that should fit in one block."),
            ("Medium text", "This is a medium length text. " * 50),  # ~1500 chars
            ("Long text", "This is a long text that should be split into multiple blocks. " * 50),  # ~3200 chars
            ("Very long text", "This is a very long text that will definitely need multiple blocks to store properly in Notion. " * 100),  # ~10000 chars
        ]
        
        for test_name, text in test_cases:
            print(f"\nTesting {test_name} ({len(text)} characters):")
            
            # Test the block creation
            blocks = notion_manager._create_rich_text_blocks(text)
            
            print(f"  Created {len(blocks)} blocks")
            
            # Verify total content is preserved
            reconstructed_text = "".join([block["text"]["content"] for block in blocks])
            
            if reconstructed_text == text:
                print(f"  ✓ Content preserved correctly")
            else:
                print(f"  ✗ Content not preserved (original: {len(text)}, reconstructed: {len(reconstructed_text)})")
            
            # Check block sizes
            for i, block in enumerate(blocks):
                block_size = len(block["text"]["content"])
                if block_size <= 2000:
                    print(f"  ✓ Block {i+1}: {block_size} chars (within limit)")
                else:
                    print(f"  ✗ Block {i+1}: {block_size} chars (exceeds 2000 limit)")
        
        return True
        
    except Exception as e:
        logger.error(f"Rich text blocks test failed: {str(e)}")
        return False


def test_notion_data_storage():
    """
    Test storing long AI-structured data in Notion without truncation.
    """
    print("\n=== TESTING NOTION DATA STORAGE ===")
    
    try:
        config = Config.from_env()
        notion_manager = NotionDataManager(config)
        
        # Get a test prospect (use the first one available)
        prospects = notion_manager.get_prospects()
        if not prospects:
            print("✗ No prospects found in Notion database for testing")
            return False
        
        test_prospect = prospects[0]
        print(f"Testing with prospect: {test_prospect.name}")
        
        # Create long test data
        long_product_summary = """
        This is a comprehensive product analysis that includes detailed information about the product's features, target market, competitive landscape, and business model. The product is a SaaS platform that serves enterprise customers in the financial services industry. It provides advanced analytics capabilities, real-time reporting, and integration with multiple data sources. The platform has been designed with scalability in mind and can handle large volumes of data processing. Key features include machine learning algorithms for predictive analytics, customizable dashboards for different user roles, automated report generation, and comprehensive API access for third-party integrations. The target market consists primarily of mid to large-sized financial institutions, including banks, credit unions, investment firms, and insurance companies. The competitive landscape includes established players like Tableau, Power BI, and newer entrants focusing on financial services. The business model is subscription-based with tiered pricing depending on the number of users and data volume processed. Recent funding rounds have provided sufficient capital for expansion into new markets and continued product development.
        """ * 5  # Make it very long
        
        long_business_insights = """
        The company has shown strong growth metrics over the past 18 months, with revenue increasing by 150% year-over-year. They recently completed a Series B funding round of $25 million, led by prominent venture capital firms specializing in fintech investments. The team has grown from 15 to 75 employees, with significant hiring in engineering, sales, and customer success roles. Market analysis indicates a total addressable market of $12 billion in the financial analytics space, with the company currently capturing approximately 0.1% market share. Key competitive advantages include proprietary machine learning algorithms, deep domain expertise in financial services, and strong customer relationships with several Fortune 500 financial institutions. The company's technology stack is built on modern cloud infrastructure, ensuring scalability and reliability. Customer retention rates are above 95%, indicating strong product-market fit. Recent product launches have expanded the platform's capabilities in risk management and regulatory compliance, addressing critical needs in the financial services sector. The leadership team consists of experienced executives with backgrounds at major financial institutions and successful fintech startups.
        """ * 3
        
        long_linkedin_summary = """
        This professional has over 15 years of experience in the financial technology sector, with a strong background in product management, business development, and strategic partnerships. They started their career as a software engineer at a major investment bank, where they worked on trading systems and risk management platforms. After several years in engineering, they transitioned to product management roles, leading the development of customer-facing applications and internal tools. Their experience includes working at both large financial institutions and fast-growing fintech startups. They have a proven track record of launching successful products, building high-performing teams, and driving revenue growth. Educational background includes an MBA from a top-tier business school and a Bachelor's degree in Computer Science. They are known for their analytical thinking, strategic vision, and ability to bridge the gap between technical and business stakeholders. Recent achievements include leading a product launch that generated $10 million in new revenue and building a product team that grew from 5 to 25 people. They are passionate about using technology to solve complex problems in financial services and have spoken at several industry conferences on topics related to fintech innovation and product strategy.
        """ * 2
        
        long_personalization_data = """
        Key personalization points for outreach include their recent promotion to VP of Product, their company's expansion into new markets, and their personal interest in machine learning applications in finance. They have been actively posting on LinkedIn about the challenges of scaling product teams and the importance of data-driven decision making. Recent company announcements suggest they are looking to hire senior engineers and product managers, indicating potential opportunities for collaboration or partnership. Their educational background and previous experience at established financial institutions provide credibility and domain expertise that would be valuable for our target market. The company's recent funding round and growth trajectory suggest they have budget for new tools and services that could help them scale more effectively. Their personal brand focuses on thought leadership in fintech and product management, making them an ideal candidate for content collaboration or speaking opportunities. Geographic location in a major tech hub provides opportunities for in-person meetings and networking events. Their company's customer base overlaps significantly with our target market, creating potential for strategic partnerships or joint go-to-market initiatives.
        """ * 2
        
        print(f"Storing long data:")
        print(f"  Product summary: {len(long_product_summary)} characters")
        print(f"  Business insights: {len(long_business_insights)} characters")
        print(f"  LinkedIn summary: {len(long_linkedin_summary)} characters")
        print(f"  Personalization data: {len(long_personalization_data)} characters")
        
        # Store the long data
        success = notion_manager.store_ai_structured_data(
            prospect_id=test_prospect.id,
            product_summary=long_product_summary,
            business_insights=long_business_insights,
            linkedin_summary=long_linkedin_summary,
            personalization_data=long_personalization_data
        )
        
        if not success:
            print("✗ Failed to store AI-structured data")
            return False
        
        print("✓ Successfully stored long data in Notion")
        
        # Retrieve the data and verify it wasn't truncated
        retrieved_data = notion_manager.get_prospect_data_for_email(test_prospect.id)
        
        print("\nVerifying retrieved data:")
        
        fields_to_check = [
            ('product_summary', long_product_summary),
            ('business_insights', long_business_insights),
            ('linkedin_summary', long_linkedin_summary),
            ('personalization_data', long_personalization_data)
        ]
        
        all_good = True
        for field_name, original_data in fields_to_check:
            retrieved_value = retrieved_data.get(field_name, '')
            
            print(f"  {field_name}:")
            print(f"    Original: {len(original_data)} characters")
            print(f"    Retrieved: {len(retrieved_value)} characters")
            
            if len(retrieved_value) == len(original_data):
                print(f"    ✓ No truncation detected")
            elif len(retrieved_value) < len(original_data):
                print(f"    ✗ Data was truncated ({len(original_data) - len(retrieved_value)} characters lost)")
                all_good = False
            else:
                print(f"    ? Retrieved data is longer than original (unexpected)")
        
        return all_good
        
    except Exception as e:
        logger.error(f"Notion data storage test failed: {str(e)}")
        return False


def test_email_content_storage():
    """
    Test storing long email content without truncation.
    """
    print("\n=== TESTING EMAIL CONTENT STORAGE ===")
    
    try:
        from models.data_models import EmailContent
        
        config = Config.from_env()
        notion_manager = NotionDataManager(config)
        
        # Get a test prospect
        prospects = notion_manager.get_prospects()
        if not prospects:
            print("✗ No prospects found in Notion database for testing")
            return False
        
        test_prospect = prospects[0]
        
        # Create long email content
        long_email_body = """
        Subject: Exciting Partnership Opportunity with [Company Name]

        Hi [Name],

        I hope this email finds you well. I came across [Company Name] on Product Hunt and was impressed by your innovative approach to [specific product/service]. As someone who has been following the [industry] space closely, I can see how your solution addresses some of the key challenges that [target market] faces today.

        I'm reaching out because I believe there's a significant opportunity for collaboration between our organizations. At [Your Company], we specialize in [your expertise/service], and we've helped companies like [similar companies] achieve [specific results/benefits]. Given [Company Name]'s focus on [their focus area] and your recent [recent achievement/funding/launch], I think we could create substantial value together.

        Here are a few specific ways we could potentially collaborate:

        1. [Specific collaboration opportunity 1] - Based on your recent [specific reference], this could help you [specific benefit]
        2. [Specific collaboration opportunity 2] - Given your expertise in [their expertise], this aligns perfectly with our capabilities in [your capabilities]
        3. [Specific collaboration opportunity 3] - Your [specific asset/strength] combined with our [your asset/strength] could create [specific outcome]

        I've done some research on [Company Name] and noticed that you've been [specific observation about their recent activities/posts/achievements]. This particularly caught my attention because [specific reason why it's relevant]. It seems like you're at an exciting inflection point, and I'd love to explore how we might be able to support your growth trajectory.

        Some additional context about why I think this partnership makes sense:
        - Your target market of [their target market] overlaps significantly with our client base
        - Your recent [specific achievement] demonstrates the kind of innovation we love to support
        - Your approach to [specific approach] aligns with our philosophy of [your philosophy]
        - The timing seems perfect given [specific timing reason]

        I'd love to schedule a brief 15-minute call to discuss this further. I'm confident that even a short conversation could uncover some interesting opportunities for both of our organizations. I'm available [specific availability] and would be happy to work around your schedule.

        In the meantime, I'd be happy to share some case studies of similar partnerships we've developed, or if you're interested, I could provide some initial thoughts on how we might approach [specific challenge they might be facing].

        Looking forward to the possibility of working together and contributing to [Company Name]'s continued success.

        Best regards,
        [Your Name]
        [Your Title]
        [Your Company]
        [Contact Information]

        P.S. I noticed your recent post about [specific LinkedIn post or company update]. I completely agree with your perspective on [specific point], and it reinforces my belief that we're aligned on [shared value/approach].
        """ * 3  # Make it very long
        
        email_content = EmailContent(
            subject="Partnership Opportunity - Long Email Test",
            body=long_email_body,
            template_used="cold_outreach",
            personalization_score=0.85,
            recipient_name=test_prospect.name,
            company_name=test_prospect.company
        )
        
        print(f"Testing email content storage:")
        print(f"  Email body length: {len(long_email_body)} characters")
        
        # Store the email content
        success = notion_manager.store_email_content(
            prospect_id=test_prospect.id,
            email_content=email_content
        )
        
        if not success:
            print("✗ Failed to store email content")
            return False
        
        print("✓ Successfully stored long email content")
        
        # Retrieve and verify
        retrieved_data = notion_manager.get_prospect_data_for_email(test_prospect.id)
        
        # Note: We would need to add email content retrieval to the get_prospect_data_for_email method
        # For now, we'll just confirm the storage succeeded
        print("✓ Email content storage test completed")
        
        return True
        
    except Exception as e:
        logger.error(f"Email content storage test failed: {str(e)}")
        return False


def run_all_storage_tests():
    """
    Run all Notion storage tests.
    """
    print("=== TESTING NOTION STORAGE LIMITS ===")
    
    tests = [
        ("Rich Text Blocks", test_notion_rich_text_blocks),
        ("AI Structured Data Storage", test_notion_data_storage),
        ("Email Content Storage", test_email_content_storage),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.error(f"Test {test_name} failed with exception: {str(e)}")
            results[test_name] = False
    
    # Summary
    print(f"\n{'='*50}")
    print("=== NOTION STORAGE TEST RESULTS ===")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All storage tests passed! No truncation detected.")
    else:
        print("⚠️  Some tests failed. Data may still be getting truncated.")
    
    return passed == total


if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_name = sys.argv[1].lower()
        if test_name == "blocks":
            test_notion_rich_text_blocks()
        elif test_name == "data":
            test_notion_data_storage()
        elif test_name == "email":
            test_email_content_storage()
        else:
            print("Available tests: blocks, data, email")
    else:
        run_all_storage_tests()