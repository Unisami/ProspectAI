"""
Hunter.io email finder service for discovering and verifying email addresses.
"""

import time
import logging
from typing import (
    List,
    Optional,
    Dict,
    Any
)
from functools import wraps

import requests
from difflib import SequenceMatcher

from models.data_models import (
    EmailData,
    EmailVerification,
    TeamMember
)
from utils.config import Config
from utils.configuration_service import get_configuration_service
from utils.error_handling import (
    get_error_handler,
    ErrorCategory,
    retry_with_backoff
)
from utils.api_monitor import get_api_monitor




logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter for Hunter.io API calls."""
    
    def __init__(self, requests_per_minute: int = 10):
        self.requests_per_minute = requests_per_minute
        self.min_delay = 60.0 / requests_per_minute  # Minimum delay between requests
        self.last_request_time = 0.0
    
    def wait_if_needed(self):
        """Wait if necessary to respect rate limits."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_delay:
            sleep_time = self.min_delay - time_since_last
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
            time.sleep(sleep_time)
            self.last_request_time = time.time()
        else:
            self.last_request_time = current_time


class EmailFinder:
    """
    Hunter.io email finder service for discovering and verifying email addresses.
    
    This class handles:
    - Finding emails by domain using Hunter.io API
    - Finding specific person emails using Hunter.io API
    - Email verification using Hunter.io API
    - Rate limiting and retry mechanisms
    - Error handling for API failures and rate limits
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the EmailFinder with Hunter.io API configuration.
        
        Args:
            config: Configuration object (deprecated, use ConfigurationService)
        """
        # Use ConfigurationService for centralized configuration management
        if config:
            # Backward compatibility: if config is provided, use it directly
            logger.warning("Direct config parameter is deprecated. Consider using ConfigurationService.")
            self.config = config
        else:
            # Use centralized configuration service
            config_service = get_configuration_service()
            self.config = config_service.get_config()
        
        self.api_key = self.config.hunter_api_key
        self.base_url = "https://api.hunter.io/v2"
        self.rate_limiter = RateLimiter(requests_per_minute=self.config.hunter_requests_per_minute)
        self.error_handler = get_error_handler()
        self.api_monitor = get_api_monitor()
        
        # HTTP session for requests
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'JobProspectAutomation/1.0'
        })
        
        logger.info("EmailFinder initialized with Hunter.io API")
    
    def test_connection(self) -> bool:
        """
        Test the Hunter.io API connection.
        
        Returns:
            True if connection is successful
            
        Raises:
            Exception if connection fails
        """
        try:
            # Test with account info endpoint
            url = f"{self.base_url}/account"
            params = {'api_key': self.api_key}
            
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                return True
            elif response.status_code == 401:
                raise Exception("Hunter.io API key is invalid")
            else:
                raise Exception(f"Hunter.io API returned status {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            raise Exception(f"Hunter.io API connection failed: {str(e)}")
    
    @retry_with_backoff(category=ErrorCategory.API_RATE_LIMIT)
    def find_company_emails(self, domain: str) -> List[EmailData]:
        """
        Find all available emails for a company domain using Hunter.io.
        
        Args:
            domain: Company domain (e.g., "example.com")
            
        Returns:
            List of EmailData objects containing found emails
            
        Raises:
            Exception: If API call fails after all retry attempts
        """
        logger.info(f"Finding emails for domain: {domain}")
        
        if not domain or not domain.strip():
            logger.warning("Empty domain provided")
            return []
        
        self.rate_limiter.wait_if_needed()
        
        start_time = time.time()
        try:
            # Hunter.io domain search endpoint
            url = f"{self.base_url}/domain-search"
            params = {
                'domain': domain.strip(),
                'api_key': self.api_key,
                'limit': 100  # Maximum results per request
            }
            
            response = self.session.get(url, params=params)
            response_time = time.time() - start_time
            
            # Record API call for monitoring
            self.api_monitor.record_api_call(
                service='hunter_io',
                endpoint='domain-search',
                response_time=response_time,
                status_code=response.status_code,
                success=response.status_code < 400,
                rate_limit_headers=dict(response.headers)
            )
            
            response.raise_for_status()
            data = response.json()
            
            # Check for API errors
            if 'errors' in data:
                error_msg = data['errors'][0].get('details', 'Unknown API error')
                error = Exception(f"Hunter.io API error: {error_msg}")
                self.error_handler.handle_error(
                    error, 'hunter_io', 'find_company_emails',
                    context={'domain': domain}, category=ErrorCategory.API_QUOTA
                )
                raise error
            
            # Parse email results
            emails = self._parse_domain_search_results(data)
            
            logger.info(f"Found {len(emails)} emails for domain {domain}")
            return emails
            
        except requests.exceptions.HTTPError as e:
            response_time = time.time() - start_time
            self.api_monitor.record_api_call(
                service='hunter_io',
                endpoint='domain-search',
                response_time=response_time,
                status_code=e.response.status_code if e.response else 0,
                success=False,
                error_message=str(e)
            )
            
            if e.response and e.response.status_code == 429:
                error = Exception("Hunter.io rate limit exceeded")
                self.error_handler.handle_error(
                    error, 'hunter_io', 'find_company_emails',
                    context={'domain': domain}, category=ErrorCategory.API_RATE_LIMIT
                )
                raise error
            elif e.response and e.response.status_code == 401:
                error = Exception("Hunter.io API key invalid or expired")
                self.error_handler.handle_error(
                    error, 'hunter_io', 'find_company_emails',
                    context={'domain': domain}, category=ErrorCategory.AUTHENTICATION
                )
                raise error
            else:
                self.error_handler.handle_error(
                    e, 'hunter_io', 'find_company_emails',
                    context={'domain': domain}, category=ErrorCategory.NETWORK
                )
                raise
        except requests.exceptions.RequestException as e:
            response_time = time.time() - start_time
            self.api_monitor.record_api_call(
                service='hunter_io',
                endpoint='domain-search',
                response_time=response_time,
                status_code=0,
                success=False,
                error_message=str(e)
            )
            
            self.error_handler.handle_error(
                e, 'hunter_io', 'find_company_emails',
                context={'domain': domain}, category=ErrorCategory.NETWORK
            )
            raise
        except Exception as e:
            self.error_handler.handle_error(
                e, 'hunter_io', 'find_company_emails',
                context={'domain': domain}
            )
            raise
    
    @retry_with_backoff(category=ErrorCategory.API_RATE_LIMIT)
    def find_person_email(self, name: str, domain: str) -> Optional[EmailData]:
        """
        Find a specific person's email using Hunter.io email finder.
        
        Args:
            name: Person's full name (e.g., "John Doe")
            domain: Company domain (e.g., "example.com")
            
        Returns:
            EmailData object if email found, None otherwise
            
        Raises:
            Exception: If API call fails after all retry attempts
        """
        logger.info(f"Finding email for {name} at {domain}")
        
        if not name or not name.strip() or not domain or not domain.strip():
            logger.warning("Empty name or domain provided")
            return None
        
        self.rate_limiter.wait_if_needed()
        
        start_time = time.time()
        try:
            # Parse name into first and last name
            name_parts = name.strip().split()
            if len(name_parts) < 2:
                logger.warning(f"Name '{name}' doesn't contain first and last name")
                return None
            
            first_name = name_parts[0]
            last_name = name_parts[-1]  # Use last part as last name
            
            # Hunter.io email finder endpoint
            url = f"{self.base_url}/email-finder"
            params = {
                'domain': domain.strip(),
                'first_name': first_name,
                'last_name': last_name,
                'api_key': self.api_key
            }
            
            response = self.session.get(url, params=params)
            response_time = time.time() - start_time
            
            # Record API call for monitoring
            self.api_monitor.record_api_call(
                service='hunter_io',
                endpoint='email-finder',
                response_time=response_time,
                status_code=response.status_code,
                success=response.status_code < 400,
                rate_limit_headers=dict(response.headers)
            )
            
            response.raise_for_status()
            data = response.json()
            
            # Check for API errors
            if 'errors' in data:
                error_msg = data['errors'][0].get('details', 'Unknown API error')
                error = Exception(f"Hunter.io API error: {error_msg}")
                self.error_handler.handle_error(
                    error, 'hunter_io', 'find_person_email',
                    context={'name': name, 'domain': domain}, category=ErrorCategory.API_QUOTA
                )
                raise error
            
            # Parse email result
            email_data = self._parse_email_finder_result(data)
            
            if email_data:
                logger.info(f"Found email for {name}: {email_data.email}")
            else:
                logger.info(f"No email found for {name} at {domain}")
            
            return email_data
            
        except requests.exceptions.HTTPError as e:
            response_time = time.time() - start_time
            self.api_monitor.record_api_call(
                service='hunter_io',
                endpoint='email-finder',
                response_time=response_time,
                status_code=e.response.status_code if e.response else 0,
                success=False,
                error_message=str(e)
            )
            
            if e.response and e.response.status_code == 429:
                error = Exception("Hunter.io rate limit exceeded")
                self.error_handler.handle_error(
                    error, 'hunter_io', 'find_person_email',
                    context={'name': name, 'domain': domain}, category=ErrorCategory.API_RATE_LIMIT
                )
                raise error
            elif e.response and e.response.status_code == 401:
                error = Exception("Hunter.io API key invalid or expired")
                self.error_handler.handle_error(
                    error, 'hunter_io', 'find_person_email',
                    context={'name': name, 'domain': domain}, category=ErrorCategory.AUTHENTICATION
                )
                raise error
            else:
                self.error_handler.handle_error(
                    e, 'hunter_io', 'find_person_email',
                    context={'name': name, 'domain': domain}, category=ErrorCategory.NETWORK
                )
                raise
        except requests.exceptions.RequestException as e:
            response_time = time.time() - start_time
            self.api_monitor.record_api_call(
                service='hunter_io',
                endpoint='email-finder',
                response_time=response_time,
                status_code=0,
                success=False,
                error_message=str(e)
            )
            
            self.error_handler.handle_error(
                e, 'hunter_io', 'find_person_email',
                context={'name': name, 'domain': domain}, category=ErrorCategory.NETWORK
            )
            raise
        except Exception as e:
            self.error_handler.handle_error(
                e, 'hunter_io', 'find_person_email',
                context={'name': name, 'domain': domain}
            )
            raise
    
    @retry_with_backoff(category=ErrorCategory.API_RATE_LIMIT)
    def verify_email(self, email: str) -> EmailVerification:
        """
        Verify an email address using Hunter.io email verifier.
        
        Args:
            email: Email address to verify
            
        Returns:
            EmailVerification object with verification results
            
        Raises:
            Exception: If API call fails after all retry attempts
        """
        logger.info(f"Verifying email: {email}")
        
        if not email or not email.strip():
            logger.warning("Empty email provided for verification")
            raise ValueError("Email cannot be empty")
        
        self.rate_limiter.wait_if_needed()
        
        start_time = time.time()
        try:
            # Hunter.io email verifier endpoint
            url = f"{self.base_url}/email-verifier"
            params = {
                'email': email.strip(),
                'api_key': self.api_key
            }
            
            response = self.session.get(url, params=params)
            response_time = time.time() - start_time
            
            # Record API call for monitoring
            self.api_monitor.record_api_call(
                service='hunter_io',
                endpoint='email-verifier',
                response_time=response_time,
                status_code=response.status_code,
                success=response.status_code < 400,
                rate_limit_headers=dict(response.headers)
            )
            
            response.raise_for_status()
            data = response.json()
            
            # Check for API errors
            if 'errors' in data:
                error_msg = data['errors'][0].get('details', 'Unknown API error')
                error = Exception(f"Hunter.io API error: {error_msg}")
                self.error_handler.handle_error(
                    error, 'hunter_io', 'verify_email',
                    context={'email': email}, category=ErrorCategory.API_QUOTA
                )
                raise error
            
            # Parse verification result
            verification = self._parse_verification_result(data, email)
            
            logger.info(f"Email verification result for {email}: {verification.result}")
            return verification
            
        except requests.exceptions.HTTPError as e:
            response_time = time.time() - start_time
            self.api_monitor.record_api_call(
                service='hunter_io',
                endpoint='email-verifier',
                response_time=response_time,
                status_code=e.response.status_code if e.response else 0,
                success=False,
                error_message=str(e)
            )
            
            if e.response and e.response.status_code == 429:
                error = Exception("Hunter.io rate limit exceeded")
                self.error_handler.handle_error(
                    error, 'hunter_io', 'verify_email',
                    context={'email': email}, category=ErrorCategory.API_RATE_LIMIT
                )
                raise error
            elif e.response and e.response.status_code == 401:
                error = Exception("Hunter.io API key invalid or expired")
                self.error_handler.handle_error(
                    error, 'hunter_io', 'verify_email',
                    context={'email': email}, category=ErrorCategory.AUTHENTICATION
                )
                raise error
            else:
                self.error_handler.handle_error(
                    e, 'hunter_io', 'verify_email',
                    context={'email': email}, category=ErrorCategory.NETWORK
                )
                raise
        except requests.exceptions.RequestException as e:
            response_time = time.time() - start_time
            self.api_monitor.record_api_call(
                service='hunter_io',
                endpoint='email-verifier',
                response_time=response_time,
                status_code=0,
                success=False,
                error_message=str(e)
            )
            
            self.error_handler.handle_error(
                e, 'hunter_io', 'verify_email',
                context={'email': email}, category=ErrorCategory.NETWORK
            )
            raise
        except Exception as e:
            self.error_handler.handle_error(
                e, 'hunter_io', 'verify_email',
                context={'email': email}
            )
            raise
    
    def match_emails_to_team_members(self, emails: List[EmailData], team_members: List[TeamMember]) -> Dict[str, EmailData]:
        """
        Match found emails to team members based on names and positions.
        
        Args:
            emails: List of EmailData objects from Hunter.io
            team_members: List of TeamMember objects to match
            
        Returns:
            Dictionary mapping team member names to their matched EmailData
        """
        logger.info(f"Matching {len(emails)} emails to {len(team_members)} team members")
        
        matches = {}
        
        for team_member in team_members:
            best_match = None
            best_score = 0.0
            
            for email in emails:
                score = self._calculate_match_score(team_member, email)
                
                if score > best_score and score > 0.6:  # Minimum confidence threshold
                    best_score = score
                    best_match = email
            
            if best_match:
                matches[team_member.name] = best_match
                logger.info(f"Matched {team_member.name} to {best_match.email} (score: {best_score:.2f})")
            else:
                logger.info(f"No email match found for {team_member.name}")
        
        logger.info(f"Successfully matched {len(matches)} team members to emails")
        return matches
    
    def _parse_domain_search_results(self, data: Dict[str, Any]) -> List[EmailData]:
        """
        Parse Hunter.io domain search API response into EmailData objects.
        
        Args:
            data: Raw API response data
            
        Returns:
            List of EmailData objects
        """
        emails = []
        
        try:
            if 'data' not in data or 'emails' not in data['data']:
                logger.warning("No emails found in Hunter.io response")
                return emails
            
            for email_info in data['data']['emails']:
                try:
                    email_data = EmailData(
                        email=email_info.get('value', ''),
                        first_name=email_info.get('first_name'),
                        last_name=email_info.get('last_name'),
                        position=email_info.get('position'),
                        department=email_info.get('department'),
                        confidence=email_info.get('confidence'),
                        sources=email_info.get('sources', [])
                    )
                    emails.append(email_data)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse email data: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error parsing domain search results: {str(e)}")
        
        return emails
    
    def _parse_email_finder_result(self, data: Dict[str, Any]) -> Optional[EmailData]:
        """
        Parse Hunter.io email finder API response into EmailData object.
        
        Args:
            data: Raw API response data
            
        Returns:
            EmailData object if email found, None otherwise
        """
        try:
            if 'data' not in data or not data['data']:
                return None
            
            email_info = data['data']
            
            # Check if email was found
            if not email_info.get('email'):
                return None
            
            return EmailData(
                email=email_info.get('email', ''),
                first_name=email_info.get('first_name'),
                last_name=email_info.get('last_name'),
                position=email_info.get('position'),
                department=email_info.get('department'),
                confidence=email_info.get('confidence'),
                sources=email_info.get('sources', [])
            )
            
        except Exception as e:
            logger.error(f"Error parsing email finder result: {str(e)}")
            return None
    
    def _parse_verification_result(self, data: Dict[str, Any], email: str) -> EmailVerification:
        """
        Parse Hunter.io email verification API response into EmailVerification object.
        
        Args:
            data: Raw API response data
            email: Email address that was verified
            
        Returns:
            EmailVerification object
        """
        try:
            if 'data' not in data:
                # Default verification result if no data
                return EmailVerification(email=email, result="unknown")
            
            verification_data = data['data']
            
            return EmailVerification(
                email=email,
                result=verification_data.get('result', 'unknown'),
                score=verification_data.get('score'),
                regexp=verification_data.get('regexp'),
                gibberish=verification_data.get('gibberish'),
                disposable=verification_data.get('disposable'),
                webmail=verification_data.get('webmail'),
                mx_records=verification_data.get('mx_records'),
                smtp_server=verification_data.get('smtp_server'),
                smtp_check=verification_data.get('smtp_check'),
                accept_all=verification_data.get('accept_all'),
                block=verification_data.get('block')
            )
            
        except Exception as e:
            logger.error(f"Error parsing verification result: {str(e)}")
            # Return default verification result
            return EmailVerification(email=email, result="unknown")
    
    def find_and_verify_team_emails(self, team_members: List[TeamMember], domain: str) -> Dict[str, Dict[str, Any]]:
        """
        Complete workflow to find and verify emails for team members using individual email finder.
        
        Args:
            team_members: List of TeamMember objects
            domain: Company domain
            
        Returns:
            Dictionary mapping team member names to their email data and verification results
        """
        logger.info(f"Finding and verifying emails for {len(team_members)} team members at {domain}")
        
        results = {}
        
        try:
            # Use individual email finder for each team member
            # This is more reliable than domain search which often fails
            logger.info(f"Using individual email finder for all {len(team_members)} team members")
            
            for team_member in team_members:
                try:
                    # Try to find email using individual email finder
                    email_data = self.find_person_email(team_member.name, domain)
                    
                    if email_data:
                        logger.info(f"Found email for {team_member.name}: {email_data.email}")
                        
                        # Verify the found email
                        try:
                            verification = self.verify_email(email_data.email)
                            results[team_member.name] = {
                                'email_data': email_data,
                                'verification': verification,
                                'is_deliverable': verification.result == 'deliverable',
                                'confidence_score': email_data.confidence or 0
                            }
                            logger.info(f"Verified email for {team_member.name}: {verification.result}")
                        except Exception as e:
                            logger.warning(f"Failed to verify email for {team_member.name}: {str(e)}")
                            # Still include the email data even if verification fails
                            results[team_member.name] = {
                                'email_data': email_data,
                                'verification': None,
                                'is_deliverable': None,
                                'confidence_score': email_data.confidence or 0
                            }
                    else:
                        logger.info(f"No email found for {team_member.name} at {domain}")
                        
                except Exception as e:
                    logger.warning(f"Failed to find email for {team_member.name}: {str(e)}")
                    continue
            
            logger.info(f"Successfully processed emails for {len(results)} team members")
            return results
            
        except Exception as e:
            logger.error(f"Failed to find and verify team emails: {str(e)}")
            raise
    
    def get_best_emails(self, results: Dict[str, Dict[str, Any]], min_confidence: int = 70) -> Dict[str, str]:
        """
        Extract the best emails from find_and_verify_team_emails results.
        
        Args:
            results: Results from find_and_verify_team_emails
            min_confidence: Minimum confidence score to include email
            
        Returns:
            Dictionary mapping team member names to their best email addresses
        """
        best_emails = {}
        
        for team_member_name, result in results.items():
            email_data = result['email_data']
            verification = result['verification']
            confidence = result['confidence_score']
            
            # Skip emails below minimum confidence
            if confidence < min_confidence:
                logger.info(f"Skipping {team_member_name} email due to low confidence: {confidence}")
                continue
            
            # Prefer deliverable emails
            if verification and verification.result == 'deliverable':
                best_emails[team_member_name] = email_data.email
                logger.info(f"Selected deliverable email for {team_member_name}: {email_data.email}")
            elif verification and verification.result in ['risky', 'unknown'] and confidence >= 80:
                # Accept risky/unknown emails if confidence is high
                best_emails[team_member_name] = email_data.email
                logger.info(f"Selected high-confidence email for {team_member_name}: {email_data.email}")
            elif not verification and confidence >= 90:
                # Accept unverified emails if confidence is very high
                best_emails[team_member_name] = email_data.email
                logger.info(f"Selected high-confidence unverified email for {team_member_name}: {email_data.email}")
            else:
                logger.info(f"Skipping {team_member_name} email due to verification/confidence issues")
        
        logger.info(f"Selected {len(best_emails)} best emails from {len(results)} results")
        return best_emails
    
    def _calculate_match_score(self, team_member: TeamMember, email_data: EmailData) -> float:
        """
        Calculate similarity score between a team member and email data.
        
        Args:
            team_member: TeamMember object
            email_data: EmailData object
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        score = 0.0
        
        # Parse team member name
        name_parts = team_member.name.lower().split()
        if len(name_parts) < 2:
            return 0.0
        
        first_name = name_parts[0]
        last_name = name_parts[-1]
        
        # Compare first name
        if email_data.first_name:
            first_similarity = SequenceMatcher(None, first_name, email_data.first_name.lower()).ratio()
            score += first_similarity * 0.4
        
        # Compare last name
        if email_data.last_name:
            last_similarity = SequenceMatcher(None, last_name, email_data.last_name.lower()).ratio()
            score += last_similarity * 0.4
        
        # Compare position/role
        if email_data.position and team_member.role:
            position_similarity = SequenceMatcher(None, team_member.role.lower(), email_data.position.lower()).ratio()
            score += position_similarity * 0.2
        
        # Bonus for high confidence emails
        if email_data.confidence and email_data.confidence > 80:
            score += 0.1
        
        return min(score, 1.0)  # Cap at 1.0
