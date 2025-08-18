#!/usr/bin/env python3
"""
Notification management system for automated alerts and summaries.
"""

import logging
from typing import (
    Dict,
    Any,
    List,
    Optional
)
from datetime import (
    datetime,
    timedelta
)
from dataclasses import dataclass
from enum import Enum
from datetime import date

from utils.config import Config



logger = logging.getLogger(__name__)


class NotificationType(Enum):
    """Types of notifications."""
    CAMPAIGN_COMPLETED = "campaign_completed"
    CAMPAIGN_FAILED = "campaign_failed"
    DAILY_SUMMARY = "daily_summary"
    ERROR_ALERT = "error_alert"
    WEEKLY_REPORT = "weekly_report"
    API_QUOTA_WARNING = "api_quota_warning"


@dataclass
class NotificationData:
    """Data structure for notifications."""
    notification_type: NotificationType
    title: str
    message: str
    priority: str  # High, Medium, Low
    data: Dict[str, Any]
    created_at: datetime


class NotificationManager:
    """Manages automated notifications and alerts."""
    
    def __init__(self, config: Config, notion_manager=None):
        """Initialize notification manager."""
        self.config = config
        self.notion_manager = notion_manager
        self.logger = logging.getLogger(__name__)
        
        # Notification settings
        self.enable_notifications = getattr(config, 'enable_notifications', True)
        self.notification_methods = getattr(config, 'notification_methods', ['notion'])
        
        # User mention settings for push notifications
        self.user_mention_id = getattr(config, 'notion_user_id', None)  # User's Notion ID for @mentions
        self.user_email = getattr(config, 'user_email', None)  # For @remind notifications
        
    def send_campaign_completion_notification(self, campaign_data: Dict[str, Any]) -> bool:
        """Send notification when campaign completes."""
        if not self.enable_notifications:
            return False
            
        try:
            # Create notification content
            success_rate = campaign_data.get('success_rate', 0) * 100
            
            if success_rate >= 80:
                emoji = "🎉"
                priority = "Medium"
            elif success_rate >= 50:
                emoji = "✅"
                priority = "Medium"
            else:
                emoji = "⚠️"
                priority = "High"
            
            title = f"{emoji} Campaign '{campaign_data.get('name', 'Unknown')}' Completed"
            
            message = f"""
Campaign Summary:
• Companies Processed: {campaign_data.get('companies_processed', 0)}
• Prospects Found: {campaign_data.get('prospects_found', 0)}
• Success Rate: {success_rate:.1f}%
• Duration: {campaign_data.get('duration_minutes', 0):.1f} minutes
• Status: {campaign_data.get('status', 'Unknown')}

{self._get_dashboard_link()}
            """.strip()
            
            notification = NotificationData(
                notification_type=NotificationType.CAMPAIGN_COMPLETED,
                title=title,
                message=message,
                priority=priority,
                data=campaign_data,
                created_at=datetime.now()
            )
            
            return self._send_notification(notification)
            
        except Exception as e:
            self.logger.error(f"Failed to send campaign completion notification: {str(e)}")
            return False
    
    def send_daily_summary_notification(self, daily_stats: Dict[str, Any]) -> bool:
        """Send daily summary notification."""
        if not self.enable_notifications:
            return False
            
        try:
            title = f"📊 Daily Summary - {datetime.now().strftime('%Y-%m-%d')}"
            
            message = f"""
Today's Automation Summary:
• Campaigns Run: {daily_stats.get('campaigns_run', 0)}
• Companies Processed: {daily_stats.get('companies_processed', 0)}
• Prospects Found: {daily_stats.get('prospects_found', 0)}
• Emails Generated: {daily_stats.get('emails_generated', 0)}
• Success Rate: {daily_stats.get('success_rate', 0) * 100:.1f}%
• Processing Time: {daily_stats.get('processing_time_minutes', 0):.1f} minutes
• API Calls: {daily_stats.get('api_calls', 0)}

Top Campaign: {daily_stats.get('top_campaign', 'N/A')}

{self._get_dashboard_link()}
            """.strip()
            
            notification = NotificationData(
                notification_type=NotificationType.DAILY_SUMMARY,
                title=title,
                message=message,
                priority="Low",
                data=daily_stats,
                created_at=datetime.now()
            )
            
            return self._send_notification(notification)
            
        except Exception as e:
            self.logger.error(f"Failed to send daily summary notification: {str(e)}")
            return False
    
    def send_error_alert(self, error_data: Dict[str, Any]) -> bool:
        """Send error alert notification."""
        if not self.enable_notifications:
            return False
            
        try:
            title = f"🚨 Error Alert - {error_data.get('component', 'System')}"
            
            message = f"""
Error Details:
• Component: {error_data.get('component', 'Unknown')}
• Error: {error_data.get('error_message', 'Unknown error')}
• Campaign: {error_data.get('campaign_name', 'N/A')}
• Company: {error_data.get('company_name', 'N/A')}
• Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Please check the system logs for more details.

{self._get_dashboard_link()}
            """.strip()
            
            notification = NotificationData(
                notification_type=NotificationType.ERROR_ALERT,
                title=title,
                message=message,
                priority="High",
                data=error_data,
                created_at=datetime.now()
            )
            
            return self._send_notification(notification)
            
        except Exception as e:
            self.logger.error(f"Failed to send error alert: {str(e)}")
            return False
    
    def send_weekly_report(self, weekly_stats: Dict[str, Any]) -> bool:
        """Send weekly performance report."""
        if not self.enable_notifications:
            return False
            
        try:
            week_start = datetime.now() - timedelta(days=7)
            title = f"📈 Weekly Report - {week_start.strftime('%Y-%m-%d')} to {datetime.now().strftime('%Y-%m-%d')}"
            
            message = f"""
Weekly Automation Report:
• Total Campaigns: {weekly_stats.get('total_campaigns', 0)}
• Companies Processed: {weekly_stats.get('total_companies', 0)}
• Prospects Found: {weekly_stats.get('total_prospects', 0)}
• Emails Generated: {weekly_stats.get('total_emails', 0)}
• Average Success Rate: {weekly_stats.get('avg_success_rate', 0) * 100:.1f}%
• Total Processing Time: {weekly_stats.get('total_processing_time', 0):.1f} hours
• Total API Calls: {weekly_stats.get('total_api_calls', 0)}

Best Performing Day: {weekly_stats.get('best_day', 'N/A')}
Most Active Campaign: {weekly_stats.get('most_active_campaign', 'N/A')}

{self._get_dashboard_link()}
            """.strip()
            
            notification = NotificationData(
                notification_type=NotificationType.WEEKLY_REPORT,
                title=title,
                message=message,
                priority="Low",
                data=weekly_stats,
                created_at=datetime.now()
            )
            
            return self._send_notification(notification)
            
        except Exception as e:
            self.logger.error(f"Failed to send weekly report: {str(e)}")
            return False
    
    def _send_notification(self, notification: NotificationData) -> bool:
        """Send notification using configured methods."""
        success = False
        
        for method in self.notification_methods:
            if method == 'notion':
                success |= self._send_notion_notification(notification)
            elif method == 'email':
                success |= self._send_email_notification(notification)
            elif method == 'webhook':
                success |= self._send_webhook_notification(notification)
        
        return success
    
    def _send_notion_notification(self, notification: NotificationData) -> bool:
        """Send notification by creating a sub-page in Daily Analytics with @mentions for push notifications."""
        if not self.notion_manager:
            return False
            
        try:
            # Get the analytics database to create notification sub-page
            analytics_db_id = getattr(self.config, 'analytics_db_id', None)
            if not analytics_db_id:
                self.logger.warning("Analytics database not configured, falling back to dashboard notification")
                return self._send_dashboard_notification(notification)
            
            # Create notification sub-page in Daily Analytics database
            notification_page = self._create_notification_subpage(analytics_db_id, notification)
            
            if notification_page:
                self.logger.info(f"Sent push notification via sub-page: {notification.title}")
                return True
            else:
                return False
            
        except Exception as e:
            self.logger.error(f"Failed to send Notion notification: {str(e)}")
            return False
    
    def _create_notification_subpage(self, analytics_db_id: str, notification: NotificationData) -> bool:
        """Create a notification sub-page in Daily Analytics with @mentions."""
        try:
            today = date.today()
            
            # Create notification page title with emoji and priority
            page_title = f"{self._get_notification_emoji(notification.notification_type)} {notification.title}"
            
            # Prepare notification content with @mentions for push notifications
            notification_content = self._format_notification_with_mentions(notification)
            
            # Create the notification page
            page_response = self.notion_manager.client.pages.create(
                parent={"database_id": analytics_db_id},
                properties={
                    "Date": {
                        "title": [{"text": {"content": f"{today.strftime('%Y-%m-%d')} - {notification.notification_type.value.title()}"}}]
                    },
                    "Campaigns Run": {"number": 0},  # Default values for required fields
                    "Companies Processed": {"number": 0},
                    "Prospects Found": {"number": 0},
                    "Emails Generated": {"number": 0},
                    "Emails Sent": {"number": 0},
                    "Success Rate": {"number": 0},
                    "Processing Time (min)": {"number": 0},
                    "API Calls Made": {"number": 0},
                    "Errors Encountered": {"number": 0},
                    "Top Performing Campaign": {
                        "rich_text": [{"text": {"content": "Notification Entry"}}]
                    },
                    "Notes": {
                        "rich_text": [{"text": {"content": f"Priority: {notification.priority} | Type: {notification.notification_type.value}"}}]
                    }
                },
                children=notification_content
            )
            
            self.logger.info(f"Created notification sub-page: {page_title}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create notification sub-page: {str(e)}")
            return False
    
    def _format_notification_with_mentions(self, notification: NotificationData) -> List[Dict]:
        """Format notification content with @mentions and @remind for push notifications."""
        content_blocks = []
        
        # Add main notification content with @mention for push notification
        mention_text = self._create_mention_text()
        
        content_blocks.extend([
            {
                "object": "block",
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [
                        {"text": {"content": f"{self._get_notification_emoji(notification.notification_type)} {notification.title}"}}
                    ],
                    "color": self._get_notification_color(notification.priority)
                }
            },
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {"text": {"content": f"🔔 {mention_text} - You have a new automation notification!"}}
                    ]
                }
            },
            {
                "object": "block",
                "type": "callout",
                "callout": {
                    "rich_text": [{"text": {"content": notification.message}}],
                    "icon": {"emoji": self._get_notification_emoji(notification.notification_type)},
                    "color": self._get_notification_color(notification.priority)
                }
            }
        ])
        
        # Add reminder for high priority notifications
        if notification.priority == "High":
            reminder_text = self._create_reminder_text(notification)
            content_blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {"text": {"content": f"⚠️ HIGH PRIORITY: {reminder_text}"}}
                    ]
                }
            })
        
        # Add quick action links
        quick_actions = self._get_quick_action_links(notification.notification_type)
        if quick_actions:
            content_blocks.extend([
                {
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [{"text": {"content": "🚀 Quick Actions"}}]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"text": {"content": quick_actions}}]
                    }
                }
            ])
        
        # Add timestamp and metadata
        content_blocks.extend([
            {
                "object": "block",
                "type": "divider",
                "divider": {}
            },
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {"text": {"content": f"📅 {notification.created_at.strftime('%Y-%m-%d %H:%M:%S')} | Priority: {notification.priority} | Type: {notification.notification_type.value.title()}"}}
                    ]
                }
            }
        ])
        
        return content_blocks
    
    def _create_mention_text(self) -> str:
        """Create @mention text for push notifications."""
        if self.user_mention_id:
            # This would create an actual @mention, but requires the user's Notion ID
            # For now, we'll use a placeholder that users can customize
            return "@YourName"  # Users can replace this with their actual @mention
        else:
            return "@mention-user-here"  # Placeholder for users to customize
    
    def _create_reminder_text(self, notification: NotificationData) -> str:
        """Create @remind text for high priority notifications."""
        if notification.notification_type == NotificationType.ERROR_ALERT:
            return "@remind Check system errors in 1 hour"
        elif notification.notification_type == NotificationType.CAMPAIGN_FAILED:
            return "@remind Review failed campaign in 30 minutes"
        else:
            return "@remind Follow up on this notification in 2 hours"
    
    def _get_quick_action_links(self, notification_type: NotificationType) -> str:
        """Get quick action links based on notification type."""
        base_url = "https://notion.so/"
        
        if notification_type == NotificationType.CAMPAIGN_COMPLETED:
            return f"""• 📊 View Campaign Details: Campaign Runs Database
• 📋 Check Processing Logs: Processing Log Database  
• 📈 Review Analytics: Daily Analytics Database
• 📧 Check Email Queue: Email Queue Database"""
            
        elif notification_type == NotificationType.DAILY_SUMMARY:
            return f"""• 📈 View Detailed Analytics: Daily Analytics Database
• ⚙️ Check System Status: System Status Database
• 📧 Review Email Queue: Email Queue Database
• 🎯 Start New Campaign: Run discovery command"""
            
        elif notification_type == NotificationType.ERROR_ALERT:
            return f"""• 📋 Check Processing Logs: Look for error details
• ⚙️ Review System Status: Check component health
• 🔧 Troubleshoot: Verify API quotas and settings
• 📞 Get Help: Check documentation or support"""
        
        return ""
    
    def _send_dashboard_notification(self, notification: NotificationData) -> bool:
        """Fallback method to send notification to main dashboard."""
        try:
            dashboard_id = getattr(self.config, 'dashboard_id', None)
            if not dashboard_id:
                return False
            
            # Add simple notification block to dashboard
            self.notion_manager.client.blocks.children.append(
                block_id=dashboard_id,
                children=[
                    {
                        "object": "block",
                        "type": "callout",
                        "callout": {
                            "rich_text": [{"text": {"content": f"🔔 {notification.title}\n\n{notification.message}"}}],
                            "icon": {"emoji": self._get_notification_emoji(notification.notification_type)},
                            "color": self._get_notification_color(notification.priority)
                        }
                    }
                ]
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send dashboard notification: {str(e)}")
            return False
    
    def _format_notification_content(self, notification: NotificationData) -> str:
        """Format notification content for better readability."""
        content = notification.message
        
        # Add quick action links based on notification type
        if notification.notification_type == NotificationType.CAMPAIGN_COMPLETED:
            content += f"\n\n📊 Quick Links:"
            content += f"\n• View Campaign Details: Campaign Runs Database"
            content += f"\n• Check Processing Logs: Processing Log Database"
            content += f"\n• Review Daily Analytics: Daily Analytics Database"
            
        elif notification.notification_type == NotificationType.DAILY_SUMMARY:
            content += f"\n\n📈 Quick Actions:"
            content += f"\n• View Detailed Analytics: Daily Analytics Database"
            content += f"\n• Check System Status: System Status Database"
            content += f"\n• Review Email Queue: Email Queue Database"
            
        elif notification.notification_type == NotificationType.ERROR_ALERT:
            content += f"\n\n🔧 Troubleshooting:"
            content += f"\n• Check Processing Logs for details"
            content += f"\n• Review System Status for component health"
            content += f"\n• Verify API quotas and rate limits"
        
        return content
    
    def _get_notification_emoji(self, notification_type: NotificationType) -> str:
        """Get appropriate emoji for notification type."""
        emoji_map = {
            NotificationType.CAMPAIGN_COMPLETED: "🎉",
            NotificationType.CAMPAIGN_FAILED: "🚨",
            NotificationType.DAILY_SUMMARY: "📊",
            NotificationType.ERROR_ALERT: "⚠️",
            NotificationType.WEEKLY_REPORT: "📈",
            NotificationType.API_QUOTA_WARNING: "⚡"
        }
        return emoji_map.get(notification_type, "🔔")
    
    def _get_notification_color(self, priority: str) -> str:
        """Get appropriate color for notification priority."""
        color_map = {
            "High": "red",
            "Medium": "yellow",
            "Low": "gray"
        }
        return color_map.get(priority, "default")
    
    def _create_notification_reminder(self, dashboard_id: str, notification: NotificationData) -> bool:
        """Create a reminder for high priority notifications."""
        try:
            # Add a reminder block for high priority notifications
            reminder_time = notification.created_at.strftime('%Y-%m-%d %H:%M')
            
            self.notion_manager.client.blocks.children.append(
                block_id=dashboard_id,
                children=[
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {"content": f"🔴 HIGH PRIORITY: {notification.title}"}
                                }
                            ]
                        }
                    }
                ]
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create notification reminder: {str(e)}")
            return False
    
    def _send_email_notification(self, notification: NotificationData) -> bool:
        """Send notification via email (placeholder for future implementation)."""
        # This could be implemented using the existing email sender
        self.logger.info(f"Email notification (not implemented): {notification.title}")
        return False
    
    def _send_webhook_notification(self, notification: NotificationData) -> bool:
        """Send notification via webhook (placeholder for future implementation)."""
        # This could be implemented for Slack, Discord, etc.
        self.logger.info(f"Webhook notification (not implemented): {notification.title}")
        return False
    
    def _get_dashboard_link(self) -> str:
        """Get link to the main dashboard."""
        dashboard_id = getattr(self.config, 'dashboard_id', None)
        if dashboard_id:
            return f"View Dashboard: https://notion.so/{dashboard_id.replace('-', '')}"
        return "Dashboard link not available"
    
    def schedule_daily_summary(self) -> bool:
        """Schedule daily summary notification (to be called by scheduler)."""
        try:
            # This would typically be called by a scheduler like cron
            # For now, it's a manual trigger
            
            controller = ProspectAutomationController(self.config)
            daily_stats = controller._calculate_daily_stats()
            
            return self.send_daily_summary_notification(daily_stats)
            
        except Exception as e:
            self.logger.error(f"Failed to schedule daily summary: {str(e)}")
            return False
