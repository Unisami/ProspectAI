# Dashboard and Monitoring Guide

This guide covers the comprehensive dashboard and monitoring features of the Job Prospect Automation system, including campaign tracking, progress monitoring, and system health management.

## 📊 Overview

The system provides a complete monitoring solution built on Notion databases that track:

- **Campaign Progress**: Real-time tracking of discovery campaigns
- **Processing Logs**: Detailed step-by-step operation logging
- **System Status**: Component health and API quota monitoring
- **Performance Metrics**: Success rates, processing times, and error tracking

## 🚀 Quick Setup

### 1. Create Dashboard

```bash
# Set up the complete dashboard system
python setup_dashboard.py
```

This creates four main components:
- 📊 **Main Dashboard**: Central monitoring hub
- 🎯 **Campaign Runs**: Track campaign progress and metrics
- 📋 **Processing Log**: Detailed operation logging
- ⚙️ **System Status**: Component health monitoring

### 2. Configure Dashboard IDs

After setup, add the generated IDs to your configuration:

```yaml
# config.yaml
DASHBOARD_ID: 'your-dashboard-id'
CAMPAIGNS_DB_ID: 'your-campaigns-db-id'
LOGS_DB_ID: 'your-logs-db-id'
STATUS_DB_ID: 'your-status-db-id'
```

## 🎯 Campaign Management

### Campaign Tracking Features

The Campaign Runs database tracks:

- **Campaign Name**: Unique identifier for each campaign
- **Status**: Not Started, Running, Paused, Completed, Failed
- **Progress**: Percentage completion with visual progress bars
- **Current Step**: Real-time status of current operation
- **Metrics**: Companies processed, prospects found, emails generated
- **Success Rate**: Campaign effectiveness percentage
- **Timing**: Start time, estimated completion, duration
- **Error Tracking**: Error count and failure analysis

### Campaign Status Values

| Status | Description | Color |
|--------|-------------|-------|
| Not Started | Campaign created but not yet running | Gray |
| Running | Campaign actively processing | Yellow |
| Paused | Campaign temporarily stopped | Orange |
| Completed | Campaign finished successfully | Green |
| Failed | Campaign terminated due to errors | Red |

### Using Campaign Tracking

```python
from services.notion_manager import NotionDataManager, CampaignProgress, CampaignStatus
from utils.config import Config
from datetime import datetime

# Initialize
config = Config.from_env()
notion_manager = NotionDataManager(config)

# Create campaign
campaign_data = CampaignProgress(
    campaign_id="campaign-001",
    name="ProductHunt Discovery - Week 1",
    status=CampaignStatus.RUNNING,
    start_time=datetime.now(),
    current_step="Discovering companies",
    companies_target=50,
    companies_processed=0,
    prospects_found=0,
    emails_generated=0,
    success_rate=0.0
)

# Create campaign entry
campaign_page_id = notion_manager.create_campaign(
    campaign_data=campaign_data,
    campaigns_db_id="your-campaigns-db-id"
)

# Update progress
campaign_data.companies_processed = 25
campaign_data.prospects_found = 75
campaign_data.success_rate = 0.85

notion_manager.update_campaign_progress(
    campaign_page_id=campaign_page_id,
    campaign_data=campaign_data
)
```

## 📋 Processing Logs

### Log Entry Types

The Processing Log database captures detailed information about each processing step:

- **Timestamp**: Exact time of operation
- **Campaign**: Associated campaign name
- **Company**: Company being processed
- **Step**: Processing stage (Discovery, Team Extraction, etc.)
- **Status**: Started, Completed, Failed, Skipped
- **Duration**: Processing time in seconds
- **Details**: Additional context information
- **Error Message**: Failure details if applicable
- **Metrics**: Prospects found, emails discovered

### Processing Steps

| Step | Description | Typical Duration |
|------|-------------|------------------|
| Discovery | Finding companies on ProductHunt | 2-5 seconds |
| Team Extraction | Identifying team members | 5-10 seconds |
| Email Finding | Discovering contact emails | 3-8 seconds |
| LinkedIn Scraping | Extracting LinkedIn profiles | 10-15 seconds |
| AI Processing | Parsing and structuring data | 15-30 seconds |
| Email Generation | Creating personalized emails | 10-20 seconds |
| Storage | Saving data to Notion | 2-5 seconds |

### Logging Processing Steps

```python
# Log a processing step
success = notion_manager.log_processing_step(
    logs_db_id="your-logs-db-id",
    campaign_name="ProductHunt Discovery - Week 1",
    company_name="Acme Corporation",
    step="Team Extraction",
    status="Completed",
    duration=8.5,
    details="Found 3 team members with LinkedIn profiles",
    prospects_found=3,
    emails_found=2
)

# Log an error
notion_manager.log_processing_step(
    logs_db_id="your-logs-db-id",
    campaign_name="ProductHunt Discovery - Week 1",
    company_name="Failed Company",
    step="Email Finding",
    status="Failed",
    duration=5.2,
    error_message="Hunter.io API rate limit exceeded",
    prospects_found=0,
    emails_found=0
)
```

## ⚙️ System Status Monitoring

### Component Health Tracking

The System Status database monitors:

- **Component**: Service name (ProductHunt Scraper, AI Parser, etc.)
- **Status**: Healthy, Warning, Error, Offline
- **Last Update**: Most recent status check
- **API Quota Used**: Percentage of API limits consumed
- **Rate Limit Status**: Current rate limiting state
- **Error Count**: Errors in last 24 hours
- **Success Rate**: Success percentage in last 24 hours
- **Details**: Additional status information

### System Components

| Component | Function | Health Indicators |
|-----------|----------|-------------------|
| ProductHunt Scraper | Company discovery | Response time, success rate |
| AI Parser | Data structuring | Token usage, parsing accuracy |
| Email Finder | Contact discovery | API quota, success rate |
| LinkedIn Scraper | Profile extraction | Rate limits, extraction success |
| Email Generator | Email creation | Generation time, quality scores |
| Email Sender | Email delivery | Delivery rate, bounce rate |
| Notion Manager | Data storage | Write success, response time |

### Status Values

| Status | Description | Action Required |
|--------|-------------|-----------------|
| Healthy | Operating normally | None |
| Warning | Minor issues detected | Monitor closely |
| Error | Significant problems | Investigate immediately |
| Offline | Service unavailable | Check configuration |

### Updating System Status

```python
# Update component status
notion_manager.update_system_status(
    status_db_id="your-status-db-id",
    component="Email Finder",
    status="Warning",
    details="Approaching Hunter.io monthly limit (80% used)",
    api_quota_used=0.80,
    error_count=2,
    success_rate=0.95
)

# Update with error status
notion_manager.update_system_status(
    status_db_id="your-status-db-id",
    component="LinkedIn Scraper",
    status="Error",
    details="Rate limit exceeded, backing off for 30 minutes",
    error_count=5,
    success_rate=0.60
)
```

## 📈 Performance Analytics

### Key Metrics to Monitor

1. **Campaign Metrics**
   - Success rate per campaign
   - Average processing time per company
   - Prospects found per company
   - Email discovery rate

2. **System Performance**
   - API response times
   - Error rates by component
   - Token consumption rates
   - Processing throughput
   - Estimated API call usage

3. **Quality Metrics**
   - Data completeness rates
   - LinkedIn profile coverage
   - Email personalization scores
   - Delivery success rates

### Analytics Queries

```python
# Get campaign performance summary
def get_campaign_analytics(notion_manager, campaigns_db_id):
    """Get campaign performance analytics."""
    campaigns = notion_manager.client.databases.query(
        database_id=campaigns_db_id
    )
    
    total_campaigns = len(campaigns["results"])
    completed_campaigns = sum(1 for c in campaigns["results"] 
                            if c["properties"]["Status"]["select"]["name"] == "Completed")
    
    avg_success_rate = sum(c["properties"]["Success Rate"]["number"] or 0 
                          for c in campaigns["results"]) / max(1, total_campaigns)
    
    return {
        "total_campaigns": total_campaigns,
        "completed_campaigns": completed_campaigns,
        "completion_rate": completed_campaigns / max(1, total_campaigns),
        "average_success_rate": avg_success_rate
    }

# Get processing performance
def get_processing_analytics(notion_manager, logs_db_id):
    """Get processing step analytics."""
    logs = notion_manager.client.databases.query(
        database_id=logs_db_id,
        filter={
            "property": "Status",
            "select": {"equals": "Completed"}
        }
    )
    
    step_durations = {}
    for log in logs["results"]:
        step = log["properties"]["Step"]["select"]["name"]
        duration = log["properties"]["Duration (s)"]["number"]
        
        if step not in step_durations:
            step_durations[step] = []
        if duration:
            step_durations[step].append(duration)
    
    # Calculate averages
    avg_durations = {
        step: sum(durations) / len(durations)
        for step, durations in step_durations.items()
        if durations
    }
    
    return avg_durations

# Get API usage analytics
def get_api_usage_analytics(notion_manager, analytics_db_id):
    """Get API call usage analytics from daily summaries."""
    analytics = notion_manager.client.databases.query(
        database_id=analytics_db_id,
        sorts=[{"property": "Date", "direction": "descending"}]
    )
    
    api_usage_data = []
    for entry in analytics["results"]:
        date_prop = entry["properties"]["Date"]["title"]
        api_calls_prop = entry["properties"].get("API Calls", {}).get("number")
        
        if date_prop and api_calls_prop is not None:
            date_text = date_prop[0]["text"]["content"]
            api_usage_data.append({
                "date": date_text,
                "api_calls": api_calls_prop
            })
    
    return api_usage_data
```

## 🔍 Monitoring Best Practices

### 1. Regular Health Checks

```python
def perform_health_check(notion_manager, status_db_id):
    """Perform comprehensive system health check."""
    components = [
        "ProductHunt Scraper",
        "AI Parser", 
        "Email Finder",
        "LinkedIn Scraper",
        "Email Generator",
        "Email Sender",
        "Notion Manager"
    ]
    
    for component in components:
        try:
            # Test component functionality
            status = test_component(component)
            
            notion_manager.update_system_status(
                status_db_id=status_db_id,
                component=component,
                status="Healthy" if status else "Error",
                details=f"Health check at {datetime.now()}",
                success_rate=1.0 if status else 0.0
            )
        except Exception as e:
            notion_manager.update_system_status(
                status_db_id=status_db_id,
                component=component,
                status="Error",
                details=f"Health check failed: {str(e)}",
                error_count=1
            )
```

### 2. Automated Alerts

Set up automated monitoring by checking status regularly:

```python
def check_for_alerts(notion_manager, status_db_id):
    """Check for system alerts and issues."""
    status_entries = notion_manager.client.databases.query(
        database_id=status_db_id,
        filter={
            "or": [
                {"property": "Status", "select": {"equals": "Error"}},
                {"property": "Status", "select": {"equals": "Warning"}}
            ]
        }
    )
    
    alerts = []
    for entry in status_entries["results"]:
        component = entry["properties"]["Component"]["title"][0]["text"]["content"]
        status = entry["properties"]["Status"]["select"]["name"]
        details = entry["properties"]["Details"]["rich_text"]
        details_text = details[0]["text"]["content"] if details else "No details"
        
        alerts.append({
            "component": component,
            "status": status,
            "details": details_text
        })
    
    return alerts
```

### 3. Performance Optimization

Monitor these metrics for optimization opportunities:

- **Slow Processing Steps**: Identify bottlenecks
- **High Error Rates**: Focus improvement efforts
- **API Quota Usage**: Optimize request patterns
- **Success Rate Trends**: Track quality improvements

## 🎮 Interactive Campaign Controls

The system includes an interactive control system that allows real-time campaign management through Notion interface changes. This enables you to pause, resume, stop, or modify campaigns while they're running.

### Control Actions Available

The interactive control system supports the following actions:

- **Pause Campaign**: Temporarily stop campaign execution
- **Resume Campaign**: Continue a paused campaign
- **Stop Campaign**: Permanently terminate a campaign
- **Priority Companies**: Add companies to priority processing queue
- **Speed Changes**: Modify processing speed (future feature)
- **Limit Changes**: Adjust processing limits (future feature)

### How Interactive Controls Work

The system monitors your Notion Campaign Runs database for specific changes and translates them into control commands:

1. **Status Changes**: Changing campaign status triggers control actions
   - Change to "Paused" → Pauses the campaign
   - Change to "Failed" → Stops the campaign
   - Change to "Running" → Resumes a paused campaign

2. **Priority Companies**: Update the "Current Company" field with special syntax
   - Format: `PRIORITY: CompanyName`
   - Adds the company to priority processing queue

3. **Real-time Monitoring**: The system checks for control commands every 30 seconds during campaign execution

### Using Interactive Controls

#### Pausing a Campaign
1. Open your Notion "Campaign Runs" database
2. Find the active campaign
3. Change the "Status" field from "Running" to "Paused"
4. The system will detect this change and pause execution

#### Stopping a Campaign
1. Open your Notion "Campaign Runs" database
2. Find the active campaign
3. Change the "Status" field to "Failed"
4. The system will stop the campaign permanently

#### Adding Priority Companies
1. Open your Notion "Campaign Runs" database
2. Find the active campaign
3. Update the "Current Company" field to: `PRIORITY: YourCompanyName`
4. The system will add this company to the priority queue

### Testing Interactive Controls

Use the provided test script to verify interactive controls are working:

```bash
# Test interactive control system
python test_interactive_controls.py
```

This script will:
- Check for active campaigns in your database
- Monitor for control commands over 5 iterations
- Execute any detected commands
- Provide instructions for manual testing

#### Test Script Output Example
```
🎮 Testing Interactive Campaign Controls...
📊 Campaigns DB ID: your-campaigns-db-id
1. Checking for active campaigns...
   Found 1 active campaigns
   Testing controls for: Discovery Campaign 2024-01-31 14:30
2. Testing control command detection...
   Check 1/5...
   🎮 Found 1 control commands:
      - Action: pause
      - Parameters: {'reason': 'User requested via Notion'}
      - Requested by: Notion User
      - Executing command...
      - Result: ✅ Success
```

### Configuration

Interactive controls are enabled by default. You can configure them in your settings:

```yaml
# Interactive control settings
ENABLE_INTERACTIVE_CONTROLS: 'true'
CONTROL_CHECK_INTERVAL: '30'  # seconds between checks
```

### Troubleshooting Interactive Controls

#### Controls Not Detected
- Verify your campaigns database ID is correctly configured
- Ensure the campaign status is exactly "Running", "Paused", or "Failed"
- Check that you have write permissions to the Notion database
- Run the test script to diagnose issues

#### Commands Not Executing
- Verify the controller has proper permissions
- Check the campaign is actually running when you make changes
- Ensure the control manager is properly initialized

#### Priority Companies Not Processing
- Verify the format is exactly: `PRIORITY: CompanyName`
- Check that the company name matches available companies
- Ensure the priority companies database is configured

## 🔔 Automated Notifications

The system includes a comprehensive notification manager that sends automated alerts and summaries for campaign monitoring and system health.

### Notification Types

The notification system supports several types of automated notifications:

- **Campaign Completed**: Sent when campaigns finish with success metrics
- **Campaign Failed**: Alerts when campaigns encounter critical errors
- **Daily Summary**: Daily automation statistics and performance metrics
- **Error Alert**: Real-time alerts for system component failures
- **Weekly Report**: Comprehensive weekly performance analysis
- **API Quota Warning**: Alerts when approaching API usage limits

### Configuring Notifications

Add notification settings to your configuration:

```yaml
# Notification Settings
ENABLE_NOTIFICATIONS: 'true'
NOTIFICATION_METHODS: ['notion']  # Available: notion, email, webhook

# Optional: User mention settings for enhanced notifications (future feature)
NOTION_USER_ID: 'your-notion-user-id'  # For @mentions in notifications
USER_EMAIL: 'your-email@domain.com'    # For @remind notifications
```

### Using the Notification Manager

```python
from services.notification_manager import NotificationManager
from utils.config import Config

# Initialize notification manager
config = Config.from_env()
notification_manager = NotificationManager(config, notion_manager)

# Send campaign completion notification
campaign_data = {
    'name': 'ProductHunt Discovery - Week 1',
    'companies_processed': 25,
    'prospects_found': 75,
    'success_rate': 0.85,
    'duration_minutes': 45.2,
    'status': 'Completed'
}

success = notification_manager.send_campaign_completion_notification(campaign_data)

# Send daily summary
daily_stats = {
    'campaigns_run': 3,
    'companies_processed': 50,
    'prospects_found': 150,
    'emails_generated': 120,
    'success_rate': 0.88,
    'processing_time_minutes': 180.5,
    'api_calls': 2350,
    'top_campaign': 'Morning Discovery'
}

notification_manager.send_daily_summary_notification(daily_stats)

# Send error alert
error_data = {
    'component': 'LinkedIn Scraper',
    'error_message': 'Rate limit exceeded',
    'campaign_name': 'Discovery Campaign',
    'company_name': 'Acme Corp'
}

notification_manager.send_error_alert(error_data)
```

### Notification Delivery Methods

#### Notion Notifications
- Creates enhanced notification blocks directly on your dashboard page
- Uses callouts with priority-based colors and emojis for better visibility
- Includes quick action links to relevant dashboard sections
- High priority notifications get additional reminder blocks
- Rich formatting with contextual troubleshooting guides
- Preserves notification history for review

#### Email Notifications (Future)
- Placeholder for email delivery integration
- Will use existing email sender service
- Configurable recipient lists and templates

#### Webhook Notifications (Future)
- Support for Slack, Discord, and other webhook services
- Real-time delivery for critical alerts
- Customizable payload formats

### Automated Scheduling

The notification manager includes methods for automated scheduling:

```python
# Schedule daily summary (typically called by cron or scheduler)
success = notification_manager.schedule_daily_summary()

# This method automatically:
# 1. Calculates daily statistics from campaign data
# 2. Formats the summary with key metrics
# 3. Sends notification via configured methods
```

### Integration with Campaign Tracking

The notification system integrates seamlessly with the campaign tracking system:

```python
from controllers.prospect_automation_controller import ProspectAutomationController

# The controller automatically sends notifications for:
# - Campaign completion (success or failure)
# - Critical errors during processing
# - Daily summary updates

controller = ProspectAutomationController(config)

# Notifications are sent automatically during pipeline execution
results = controller.run_discovery_pipeline(
    limit=25,
    campaign_name="Automated Discovery"
)

# Campaign completion notification sent automatically
# Error notifications sent for any failures
# Daily summary can be triggered manually or via scheduler
```

### Notification Content Examples

#### Campaign Completion Notification
```
🎉 Campaign 'ProductHunt Discovery - Week 1' Completed

Campaign Summary:
• Companies Processed: 25
• Prospects Found: 75
• Success Rate: 85.0%
• Duration: 45.2 minutes
• Status: Completed

📊 Quick Links:
• View Campaign Details: Campaign Runs Database
• Check Processing Logs: Processing Log Database
• Review Daily Analytics: Daily Analytics Database

View Dashboard: https://notion.so/[dashboard-id]
```

#### Daily Summary Notification
```
📊 Daily Summary - 2024-01-31

Today's Automation Summary:
• Campaigns Run: 3
• Companies Processed: 50
• Prospects Found: 150
• Emails Generated: 120
• Success Rate: 88.0%
• Processing Time: 180.5 minutes
• API Calls: 2350

Top Campaign: Morning Discovery

📈 Quick Actions:
• View Detailed Analytics: Daily Analytics Database
• Check System Status: System Status Database
• Review Email Queue: Email Queue Database

View Dashboard: https://notion.so/[dashboard-id]
```

#### Error Alert Notification
```
🚨 Error Alert - LinkedIn Scraper

Error Details:
• Component: LinkedIn Scraper
• Error: Rate limit exceeded
• Campaign: Discovery Campaign
• Company: Acme Corp
• Time: 2024-01-31 14:30:15

🔧 Troubleshooting:
• Check Processing Logs for details
• Review System Status for component health
• Verify API quotas and rate limits

View Dashboard: https://notion.so/[dashboard-id]
```

## 🛠️ Troubleshooting

### Common Dashboard Issues

1. **Dashboard Not Created**
   ```bash
   Error: Failed to create campaign dashboard
   ```
   - Check Notion integration permissions
   - Verify API token is valid
   - Ensure workspace access
   - The system now creates dashboard pages directly in your workspace for improved reliability
   - Ensure your integration has permission to create pages and databases in the workspace
   
   **Diagnostic Tool:**
   ```bash
   python test_dashboard_creation.py
   ```
   This script tests each step of dashboard creation separately to isolate the specific issue.

2. **Status Updates Failing**
   ```bash
   Error: Failed to update system status
   ```
   - Verify database IDs are correct
   - Check Notion API connectivity
   - Validate status values

3. **Missing Log Entries**
   - Ensure logging is enabled in configuration
   - Check database permissions
   - Verify log database ID

4. **Daily Analytics Issues**
   ```bash
   Error: Failed to create daily summary
   ```
   - Verify analytics database ID is configured
   - Check database permissions and access
   - Ensure database schema is correct
   
   **Diagnostic Tool:**
   ```bash
   python debug_daily_analytics.py
   ```
   This script tests daily analytics creation step by step:
   - Verifies database access and configuration
   - Shows existing entries in the analytics database
   - Tests daily summary creation process
   - Validates entry creation and data structure
   
   **API Call Estimation:** The daily analytics now includes estimated API call counts based on operations performed:
   - Campaign setup calls (5 per campaign)
   - Company processing calls (15 per company)
   - Prospect processing calls (8 per prospect)
   - Email generation calls (3 per email)
   - Logging and storage calls (2 per log entry)

### Maintenance Tasks

1. **Regular Cleanup**
   ```python
   # Archive old campaigns
   # Clean up old log entries
   # Reset error counters
   ```

2. **Performance Monitoring**
   ```python
   # Check processing times
   # Monitor success rates
   # Track API usage
   ```

3. **Data Validation**
   ```python
   # Verify data integrity
   # Check for missing entries
   # Validate status consistency
   ```

## 🔗 Integration Examples

### With Existing Workflows

```python
from controllers.prospect_automation_controller import ProspectAutomationController
from utils.config import Config

def run_monitored_discovery():
    """Run discovery with automatic progress tracking."""
    config = Config.from_env()
    controller = ProspectAutomationController(config)
    
    # The controller now handles all campaign tracking automatically
    campaign_name = f"Discovery Campaign - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    
    try:
        # Run discovery with automatic progress tracking
        results = controller.run_discovery_pipeline(
            limit=50,
            campaign_name=campaign_name
        )
        
        # Get campaign progress information
        progress = controller.get_campaign_progress()
        if progress:
            print(f"Campaign: {progress['name']}")
            print(f"Status: {progress['status']}")
            print(f"Progress: {progress['progress_percentage']:.1f}%")
            print(f"Companies processed: {progress['companies_processed']}")
            print(f"Prospects found: {progress['prospects_found']}")
            print(f"Success rate: {progress['success_rate']:.1f}%")
        
        return results
        
    except Exception as e:
        print(f"Campaign failed: {e}")
        # Campaign failure is automatically tracked by the controller
        raise

# Alternative: Use the controller's built-in progress tracking
def run_with_custom_monitoring():
    """Example with custom progress monitoring."""
    config = Config.from_env()
    controller = ProspectAutomationController(config)
    
    # Enable progress tracking in configuration
    controller.dashboard_config['enable_progress_tracking'] = True
    
    # Run discovery - progress is automatically tracked
    results = controller.run_discovery_pipeline(
        limit=25,
        campaign_name="Custom Monitored Campaign"
    )
    
    # Access current campaign information
    if controller.current_campaign:
        print(f"Campaign ID: {controller.current_campaign.campaign_id}")
        print(f"Current step: {controller.current_campaign.current_step}")
        print(f"Error count: {controller.current_campaign.error_count}")
    
    return results
```

## � Conitroller Progress Tracking Methods

The `ProspectAutomationController` now includes built-in progress tracking methods that automatically handle campaign monitoring:

### Available Methods

#### `get_campaign_progress() -> Optional[Dict[str, Any]]`
Get current campaign progress information.

```python
controller = ProspectAutomationController(config)
progress = controller.get_campaign_progress()

if progress:
    print(f"Campaign: {progress['name']}")
    print(f"Status: {progress['status']}")
    print(f"Progress: {progress['progress_percentage']:.1f}%")
    print(f"Current step: {progress['current_step']}")
    print(f"Companies processed: {progress['companies_processed']}")
    print(f"Prospects found: {progress['prospects_found']}")
    print(f"Success rate: {progress['success_rate']:.1f}%")
    print(f"Error count: {progress['error_count']}")
```

#### Internal Progress Tracking Methods

The controller includes several internal methods that handle progress tracking automatically:

- `_start_campaign_tracking(campaign_name, target_companies)`: Initialize campaign tracking
- `_update_campaign_step(step)`: Update current processing step
- `_update_campaign_current_company(company_name)`: Update current company being processed
- `_update_campaign_progress()`: Update progress with current statistics
- `_complete_campaign_tracking(status)`: Mark campaign as completed or failed
- `_log_processing_step(...)`: Log detailed processing steps
- `_update_system_status(...)`: Update system component health

These methods are called automatically during `run_discovery_pipeline()` execution and handle all error cases gracefully.

### Configuration

Progress tracking is controlled by the `dashboard_config` in the controller:

```python
controller.dashboard_config = {
    'campaigns_db_id': 'your-campaigns-db-id',
    'logs_db_id': 'your-logs-db-id', 
    'status_db_id': 'your-status-db-id',
    'enable_progress_tracking': True
}
```

If any database IDs are missing or `enable_progress_tracking` is False, the methods will log warnings but continue execution without failing.

## 📚 Additional Resources

- [Notion API Documentation](https://developers.notion.com/docs)
- [Campaign Management Best Practices](USAGE_EXAMPLES.md#campaign-management)
- [System Monitoring Guide](TROUBLESHOOTING_GUIDE.md#monitoring)
- [Performance Optimization](README.md#performance-optimization)

---

The dashboard and monitoring system provides comprehensive visibility into your job prospect automation workflow, enabling you to track progress, identify issues, and optimize performance effectively.