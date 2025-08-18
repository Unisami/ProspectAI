"""Main entry point for the job prospect automation system."""



import sys

from controllers.prospect_automation_controller import ProspectAutomationController
from utils.config import Config
from utils.logging_config import (
    setup_logging,
    configure_external_loggers,
    get_logger
)


def main():
    """Main function to initialize and run the prospect automation system."""
    try:
        # Set up logging
        setup_logging(log_level="INFO")
        configure_external_loggers()
        logger = get_logger(__name__)
        
        logger.info("Starting Job Prospect Automation System")
        
        # Load configuration from YAML file
        config = Config.from_file("config.yaml")
        config.validate()
        logger.info("Configuration loaded and validated successfully")
        
        # Initialize the main controller
        controller = ProspectAutomationController(config)
        logger.info("ProspectAutomationController initialized successfully")
        
        # Run the discovery pipeline
        logger.info("Starting discovery pipeline...")
        results = controller.run_discovery_pipeline()
        
        # Display results
        summary = results['summary']
        logger.info("Discovery pipeline completed!")
        logger.info(f"Companies processed: {summary['companies_processed']}")
        logger.info(f"Prospects found: {summary['prospects_found']}")
        logger.info(f"Emails found: {summary['emails_found']}")
        logger.info(f"LinkedIn profiles extracted: {summary['linkedin_profiles_extracted']}")
        logger.info(f"Success rate: {summary['success_rate']:.1f}%")
        
        if summary['duration_seconds']:
            logger.info(f"Total duration: {summary['duration_seconds']:.1f} seconds")
        
        # Display batch processing capabilities
        logger.info("\nBatch Processing Features Available:")
        logger.info("- Process companies in configurable batch sizes")
        logger.info("- Real-time progress tracking with callbacks")
        logger.info("- Pause and resume functionality")
        logger.info("- Persistent state storage in Notion")
        logger.info("- Comprehensive error handling and recovery")
        logger.info("- Detailed statistics and reporting")
        logger.info("\nSee examples/batch_processing_example.py for usage examples")
        
        logger.info("System execution complete")
        
    except ValueError as e:
        print(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
