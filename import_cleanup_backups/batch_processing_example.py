"""
Example demonstrating batch processing and progress tracking functionality.
"""

import time
from datetime import datetime
from controllers.prospect_automation_controller import ProspectAutomationController
from models.data_models import CompanyData
from utils.config import Config
from utils.logging_config import setup_logging, get_logger


def progress_callback(batch_progress):
    """Example progress callback function."""
    print(f"\n--- Progress Update ---")
    print(f"Batch ID: {batch_progress.batch_id}")
    print(f"Status: {batch_progress.status.value}")
    print(f"Progress: {batch_progress.processed_companies}/{batch_progress.total_companies} companies")
    print(f"Success Rate: {(batch_progress.successful_companies / max(1, batch_progress.processed_companies)) * 100:.1f}%")
    print(f"Total Prospects: {batch_progress.total_prospects}")
    if batch_progress.current_company:
        print(f"Currently Processing: {batch_progress.current_company}")
    print(f"Last Update: {batch_progress.last_update_time.strftime('%H:%M:%S')}")
    print("-" * 25)


def main():
    """Demonstrate batch processing functionality."""
    # Set up logging
    setup_logging(log_level="INFO")
    logger = get_logger(__name__)
    
    logger.info("Starting batch processing example")
    
    try:
        # Load configuration
        config = Config.from_env()
        
        # Initialize controller
        controller = ProspectAutomationController(config)
        
        # Create sample companies for demonstration
        sample_companies = [
            CompanyData(
                name="Example Company 1",
                domain="example1.com",
                product_url="https://producthunt.com/posts/example1",
                description="First example company",
                launch_date=datetime.now()
            ),
            CompanyData(
                name="Example Company 2", 
                domain="example2.com",
                product_url="https://producthunt.com/posts/example2",
                description="Second example company",
                launch_date=datetime.now()
            ),
            CompanyData(
                name="Example Company 3",
                domain="example3.com", 
                product_url="https://producthunt.com/posts/example3",
                description="Third example company",
                launch_date=datetime.now()
            )
        ]
        
        print("\n=== Batch Processing Example ===")
        print(f"Processing {len(sample_companies)} companies in batches")
        
        # Start batch processing with progress callback
        results = controller.run_batch_processing(
            companies=sample_companies,
            batch_size=2,  # Process 2 companies at a time
            progress_callback=progress_callback
        )
        
        # Display final results
        print("\n=== Final Results ===")
        print(f"Batch ID: {results['batch_id']}")
        print(f"Status: {results['status']}")
        
        summary = results['summary']
        print(f"\nSummary:")
        print(f"  Total Companies: {summary['total_companies']}")
        print(f"  Processed: {summary['processed_companies']}")
        print(f"  Successful: {summary['successful_companies']}")
        print(f"  Failed: {summary['failed_companies']}")
        print(f"  Success Rate: {summary['success_rate']:.1f}%")
        print(f"  Total Prospects: {summary['total_prospects']}")
        print(f"  Total Processing Time: {summary['total_processing_time']:.2f}s")
        print(f"  Average Time per Company: {summary['average_processing_time']:.2f}s")
        
        timeline = results['timeline']
        print(f"\nTimeline:")
        print(f"  Started: {timeline['start_time']}")
        print(f"  Completed: {timeline['end_time']}")
        print(f"  Duration: {timeline['duration_seconds']:.1f} seconds")
        
        # Display detailed results
        print(f"\nDetailed Results:")
        for i, result in enumerate(results['detailed_results'], 1):
            status = "✅ Success" if result['success'] else "❌ Failed"
            print(f"  {i}. {result['company_name']}: {status}")
            print(f"     Prospects: {result['prospects_found']}, Emails: {result['emails_found']}")
            print(f"     Processing Time: {result['processing_time']:.2f}s")
            if result['error_message']:
                print(f"     Error: {result['error_message']}")
        
        # Demonstrate batch history
        print(f"\n=== Batch History ===")
        history = controller.list_batch_history()
        if history:
            for batch in history[:3]:  # Show last 3 batches
                print(f"Batch {batch['batch_id']}: {batch['status']} - {batch['processed_companies']}/{batch['total_companies']} companies")
        else:
            print("No batch history available")
        
        # Demonstrate pause/resume functionality
        print(f"\n=== Pause/Resume Demo ===")
        print("Note: In a real scenario, you would pause during processing")
        print("and resume later. This is just a demonstration of the API.")
        
        # Show current batch status
        current_batch = controller.get_batch_progress()
        if current_batch:
            print(f"Current batch status: {current_batch.status.value}")
        
        logger.info("Batch processing example completed successfully")
        
    except Exception as e:
        logger.error(f"Batch processing example failed: {str(e)}")
        raise


if __name__ == "__main__":
    main()