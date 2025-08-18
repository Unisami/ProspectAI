#!/usr/bin/env python3
"""

import logging
from typing import (
    Dict,
    Any,
    List,
    Optional
)
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from utils.config import Config


Interactive campaign control system for Notion-based management.
"""



logger = logging.getLogger(__name__)


class ControlAction(Enum):
    """Available control actions."""
    PAUSE = "pause"
    RESUME = "resume"
    STOP = "stop"
    PRIORITY_ADD = "priority_add"
    SPEED_CHANGE = "speed_change"
    LIMIT_CHANGE = "limit_change"


@dataclass
class ControlCommand:
    """Control command data structure."""
    action: ControlAction
    parameters: Dict[str, Any]
    requested_by: str
    requested_at: datetime
    campaign_id: Optional[str] = None


class InteractiveControlManager:
    """Manages interactive campaign controls via Notion."""
    
    def __init__(self, config: Config, notion_manager=None):
        """Initialize interactive control manager."""
        self.config = config
        self.notion_manager = notion_manager
        self.logger = logging.getLogger(__name__)
        
        # Control settings
        self.enable_controls = getattr(config, 'enable_interactive_controls', True)
        self.control_check_interval = getattr(config, 'control_check_interval', 30)  # seconds
        
    def create_control_interface(self, campaign_id: str, dashboard_id: str) -> bool:
        """Create interactive control interface in Notion."""
        if not self.enable_controls or not self.notion_manager:
            return False
            
        try:
            # Create control panel page
            control_page = self.notion_manager.client.pages.create(
                parent={"type": "page_id", "page_id": dashboard_id},
                properties={
                    "title": [{"text": {"content": f"🎮 Campaign Controls - {campaign_id}"}}]
                },
                children=[
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [{"text": {"content": "Campaign Control Panel"}}]
                        }
                    },
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"text": {"content": "Use the controls below to manage your campaign in real-time:"}}]
                        }
                    },
                    {
                        "object": "block",
                        "type": "heading_3",
                        "heading_3": {
                            "rich_text": [{"text": {"content": "⏸️ Pause/Resume Campaign"}}]
                        }
                    },
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"text": {"content": "To pause: Change campaign status to 'Paused' in Campaign Runs database\nTo resume: Change campaign status back to 'Running'"}}]
                        }
                    },
                    {
                        "object": "block",
                        "type": "heading_3",
                        "heading_3": {
                            "rich_text": [{"text": {"content": "🚫 Stop Campaign"}}]
                        }
                    },
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"text": {"content": "To stop: Change campaign status to 'Failed' in Campaign Runs database"}}]
                        }
                    },
                    {
                        "object": "block",
                        "type": "heading_3",
                        "heading_3": {
                            "rich_text": [{"text": {"content": "⚡ Priority Companies"}}]
                        }
                    },
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"text": {"content": "Add companies to priority queue by updating the 'Current Company' field with 'PRIORITY: CompanyName'"}}]
                        }
                    }
                ]
            )
            
            self.logger.info(f"Created control interface for campaign {campaign_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create control interface: {str(e)}")
            return False
    
    def check_control_commands(self, campaign_id: str, campaigns_db_id: str) -> List[ControlCommand]:
        """Check for control commands from Notion interface."""
        if not self.enable_controls or not self.notion_manager:
            return []
            
        try:
            # Get campaign page
            response = self.notion_manager.client.databases.query(
                database_id=campaigns_db_id,
                filter={
                    "property": "Campaign Name",
                    "title": {
                        "contains": campaign_id
                    }
                }
            )
            
            commands = []
            
            if response["results"]:
                campaign_page = response["results"][0]
                properties = campaign_page["properties"]
                
                # Check status changes
                status = self.notion_manager._extract_select(properties.get("Status", {}))
                current_company = self.notion_manager._extract_rich_text(properties.get("Current Company", {}))
                
                # Detect pause command
                if status == "Paused":
                    commands.append(ControlCommand(
                        action=ControlAction.PAUSE,
                        parameters={"reason": "User requested via Notion"},
                        requested_by="Notion User",
                        requested_at=datetime.now(),
                        campaign_id=campaign_id
                    ))
                
                # Detect stop command
                elif status == "Failed":
                    commands.append(ControlCommand(
                        action=ControlAction.STOP,
                        parameters={"reason": "User requested via Notion"},
                        requested_by="Notion User",
                        requested_at=datetime.now(),
                        campaign_id=campaign_id
                    ))
                
                # Detect priority company addition
                if current_company and current_company.startswith("PRIORITY:"):
                    company_name = current_company.replace("PRIORITY:", "").strip()
                    commands.append(ControlCommand(
                        action=ControlAction.PRIORITY_ADD,
                        parameters={"company_name": company_name},
                        requested_by="Notion User",
                        requested_at=datetime.now(),
                        campaign_id=campaign_id
                    ))
            
            return commands
            
        except Exception as e:
            self.logger.error(f"Failed to check control commands: {str(e)}")
            return []
    
    def execute_control_command(self, command: ControlCommand, controller) -> bool:
        """Execute a control command."""
        try:
            self.logger.info(f"Executing control command: {command.action.value}")
            
            if command.action == ControlAction.PAUSE:
                return controller.pause_campaign(command.parameters.get("reason", "User requested"))
            
            elif command.action == ControlAction.RESUME:
                return controller.resume_campaign()
            
            elif command.action == ControlAction.STOP:
                # Stop campaign by marking as failed
                if controller.current_campaign:
                    controller.current_campaign.status = controller.CampaignStatus.FAILED
                    controller._update_campaign_in_notion()
                return True
            
            elif command.action == ControlAction.PRIORITY_ADD:
                company_name = command.parameters.get("company_name")
                if company_name:
                    return controller.add_priority_companies([company_name])
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to execute control command: {str(e)}")
            return False
    
    def create_priority_companies_database(self, dashboard_id: str) -> str:
        """Create a database for managing priority companies."""
        try:
            properties = {
                "Company Name": {"title": {}},
                "Priority Level": {
                    "select": {
                        "options": [
                            {"name": "High", "color": "red"},
                            {"name": "Medium", "color": "yellow"},
                            {"name": "Low", "color": "gray"}
                        ]
                    }
                },
                "Status": {
                    "select": {
                        "options": [
                            {"name": "Pending", "color": "yellow"},
                            {"name": "Processing", "color": "blue"},
                            {"name": "Completed", "color": "green"},
                            {"name": "Skipped", "color": "gray"}
                        ]
                    }
                },
                "Added Date": {"date": {}},
                "Added By": {"rich_text": {}},
                "Domain": {"rich_text": {}},
                "Notes": {"rich_text": {}},
                "Campaign": {"rich_text": {}},
                "Processing Order": {"number": {}}
            }
            
            response = self.notion_manager.client.databases.create(
                parent={"type": "page_id", "page_id": dashboard_id},
                title=[{"type": "text", "text": {"content": "⚡ Priority Companies"}}],
                properties=properties
            )
            
            return response["id"]
            
        except Exception as e:
            self.logger.error(f"Failed to create priority companies database: {str(e)}")
            return ""
    
    def add_priority_company(self, priority_db_id: str, company_name: str, 
                           priority: str = "High", campaign: str = None) -> bool:
        """Add a company to the priority queue."""
        try:
            properties = {
                "Company Name": {
                    "title": [{"text": {"content": company_name}}]
                },
                "Priority Level": {
                    "select": {"name": priority}
                },
                "Status": {
                    "select": {"name": "Pending"}
                },
                "Added Date": {
                    "date": {"start": datetime.now().isoformat()}
                },
                "Added By": {
                    "rich_text": [{"text": {"content": "Interactive Control"}}]
                }
            }
            
            if campaign:
                properties["Campaign"] = {
                    "rich_text": [{"text": {"content": campaign}}]
                }
            
            self.notion_manager.client.pages.create(
                parent={"database_id": priority_db_id},
                properties=properties
            )
            
            self.logger.info(f"Added priority company: {company_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add priority company: {str(e)}")
            return False
    
    def get_priority_companies(self, priority_db_id: str) -> List[Dict[str, Any]]:
        """Get list of priority companies to process."""
        try:
            response = self.notion_manager.client.databases.query(
                database_id=priority_db_id,
                filter={
                    "property": "Status",
                    "select": {
                        "equals": "Pending"
                    }
                },
                sorts=[
                    {
                        "property": "Priority Level",
                        "direction": "ascending"
                    },
                    {
                        "property": "Added Date",
                        "direction": "ascending"
                    }
                ]
            )
            
            priority_companies = []
            for result in response["results"]:
                properties = result["properties"]
                priority_companies.append({
                    "name": self.notion_manager._extract_title(properties.get("Company Name", {})),
                    "priority": self.notion_manager._extract_select(properties.get("Priority Level", {})),
                    "domain": self.notion_manager._extract_rich_text(properties.get("Domain", {})),
                    "page_id": result["id"]
                })
            
            return priority_companies
            
        except Exception as e:
            self.logger.error(f"Failed to get priority companies: {str(e)}")
            return []
    
    def update_priority_company_status(self, page_id: str, status: str) -> bool:
        """Update the status of a priority company."""
        try:
            self.notion_manager.client.pages.update(
                page_id=page_id,
                properties={
                    "Status": {"select": {"name": status}}
                }
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update priority company status: {str(e)}")
            return False
