"""
Product Analyzer service for comprehensive product information extraction and analysis.
"""

import time
import logging
from typing import (
    List,
    Optional,
    Dict,
    Any,
    Tuple
)
from dataclasses import dataclass
from datetime import datetime
import re
import json

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from utils.config import Config
from services.ai_parser import (
    AIParser,
    ProductInfo
)
from services.openai_client_manager import CompletionRequest





logger = logging.getLogger(__name__)


@dataclass
class Feature:
    """Data model for product features."""
    name: str
    description: str
    category: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'name': self.name,
            'description': self.description,
            'category': self.category
        }


@dataclass
class PricingInfo:
    """Data model for pricing information."""
    model: str  # e.g., "freemium", "subscription", "one-time"
    tiers: List[Dict[str, Any]]  # List of pricing tiers
    currency: str = "USD"
    billing_cycles: List[str] = None  # e.g., ["monthly", "yearly"]
    
    def __post_init__(self):
        if self.billing_cycles is None:
            self.billing_cycles = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'model': self.model,
            'tiers': self.tiers,
            'currency': self.currency,
            'billing_cycles': self.billing_cycles
        }


@dataclass
class MarketAnalysis:
    """Data model for market analysis."""
    target_market: str
    market_size: Optional[str] = None
    competitors: List[str] = None
    competitive_advantages: List[str] = None
    market_position: str = ""
    growth_potential: str = ""
    
    def __post_init__(self):
        if self.competitors is None:
            self.competitors = []
        if self.competitive_advantages is None:
            self.competitive_advantages = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'target_market': self.target_market,
            'market_size': self.market_size,
            'competitors': self.competitors,
            'competitive_advantages': self.competitive_advantages,
            'market_position': self.market_position,
            'growth_potential': self.growth_potential
        }


@dataclass
class ComprehensiveProductInfo:
    """Extended product information with comprehensive analysis."""
    basic_info: ProductInfo
    features: List[Feature]
    pricing: PricingInfo
    market_analysis: MarketAnalysis
    funding_info: Optional[Dict[str, Any]] = None
    team_size: Optional[int] = None
    launch_date: Optional[datetime] = None
    social_metrics: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'basic_info': self.basic_info.to_dict(),
            'features': [f.to_dict() for f in self.features],
            'pricing': self.pricing.to_dict(),
            'market_analysis': self.market_analysis.to_dict(),
            'funding_info': self.funding_info,
            'team_size': self.team_size,
            'launch_date': self.launch_date.isoformat() if self.launch_date else None,
            'social_metrics': self.social_metrics
        }


class RateLimiter:
    """Simple rate limiter for web scraping."""
    
    def __init__(self, delay: float = 2.0):
        self.delay = delay
        self.last_request_time = 0.0
    
    def wait_if_needed(self):
        """Wait if necessary to respect rate limits."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.delay:
            sleep_time = self.delay - time_since_last
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()


class ProductAnalyzer:
    """
    Service for comprehensive product information extraction and analysis.
    
    This class handles:
    - Analyzing product features, pricing, and market position
    - Extracting competitor information
    - Using AI parsing to structure unorganized product data
    - Gathering comprehensive product context for email personalization
    """
    
    def __init__(self, config: Config):
        """
        Initialize the Product Analyzer.
        
        Args:
            config: Configuration object containing API keys and settings
        """
        self.config = config
        self.rate_limiter = RateLimiter(delay=config.scraping_delay)
        
        # HTTP session for requests
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Selenium WebDriver options
        self.chrome_options = Options()
        self.chrome_options.add_argument('--headless')
        self.chrome_options.add_argument('--no-sandbox')
        self.chrome_options.add_argument('--disable-dev-shm-usage')
        self.chrome_options.add_argument('--disable-gpu')
        
        # Initialize AI parser for enhanced analysis
        try:
            self.ai_parser = AIParser(config)
            self.use_ai_parsing = True
            logger.info("AI parsing enabled for Product Analyzer")
        except Exception as e:
            logger.warning(f"Failed to initialize AI parser: {e}. Falling back to traditional parsing.")
            self.ai_parser = None
            self.use_ai_parsing = False
        
        logger.info("ProductAnalyzer initialized successfully")
    
    def analyze_product(self, product_url: str, company_website: str = "") -> ComprehensiveProductInfo:
        """
        Analyze a product comprehensively by extracting information from multiple sources.
        
        Args:
            product_url: URL of the product page (e.g., ProductHunt page)
            company_website: Optional company website URL for additional context
            
        Returns:
            ComprehensiveProductInfo object with detailed analysis
            
        Raises:
            Exception: If product analysis fails
        """
        logger.info(f"Starting comprehensive product analysis for: {product_url}")
        
        try:
            # Step 1: Extract basic product information
            basic_info = self._extract_basic_product_info(product_url)
            
            # Step 2: Extract detailed features
            features = self.extract_features(product_url, company_website)
            
            # Step 3: Analyze pricing information
            pricing = self.get_pricing_info(product_url, company_website)
            
            # Step 4: Perform market analysis
            market_analysis = self.analyze_market_position(basic_info, company_website)
            
            # Step 5: Gather additional context (funding, team size, etc.)
            additional_context = self._gather_additional_context(product_url, company_website)
            
            # Combine all information
            comprehensive_info = ComprehensiveProductInfo(
                basic_info=basic_info,
                features=features,
                pricing=pricing,
                market_analysis=market_analysis,
                funding_info=additional_context.get('funding_info'),
                team_size=additional_context.get('team_size'),
                launch_date=additional_context.get('launch_date'),
                social_metrics=additional_context.get('social_metrics')
            )
            
            logger.info(f"Successfully completed comprehensive product analysis")
            return comprehensive_info
            
        except Exception as e:
            logger.error(f"Failed to analyze product {product_url}: {str(e)}")
            raise
    
    def extract_features(self, product_url: str, company_website: str = "") -> List[Feature]:
        """
        Extract product features from product page and company website.
        
        Args:
            product_url: URL of the product page
            company_website: Optional company website URL
            
        Returns:
            List of Feature objects
        """
        logger.info("Extracting product features")
        
        features = []
        
        try:
            # Extract features from product page
            product_features = self._extract_features_from_url(product_url)
            features.extend(product_features)
            
            # Extract additional features from company website if available
            if company_website:
                website_features = self._extract_features_from_url(company_website)
                # Merge features, avoiding duplicates
                for feature in website_features:
                    if not any(f.name.lower() == feature.name.lower() for f in features):
                        features.append(feature)
            
            logger.info(f"Successfully extracted {len(features)} features")
            return features
            
        except Exception as e:
            logger.error(f"Failed to extract features: {str(e)}")
            return []
    
    def get_pricing_info(self, product_url: str, company_website: str = "") -> PricingInfo:
        """
        Extract pricing information from product sources.
        
        Args:
            product_url: URL of the product page
            company_website: Optional company website URL
            
        Returns:
            PricingInfo object with pricing details
        """
        logger.info("Extracting pricing information")
        
        try:
            # Try to extract pricing from company website first (usually more detailed)
            if company_website:
                pricing = self._extract_pricing_from_url(company_website)
                if pricing.model != "unknown":
                    return pricing
            
            # Fall back to product page
            pricing = self._extract_pricing_from_url(product_url)
            
            logger.info(f"Successfully extracted pricing info: {pricing.model}")
            return pricing
            
        except Exception as e:
            logger.error(f"Failed to extract pricing info: {str(e)}")
            # Return default pricing info
            return PricingInfo(
                model="unknown",
                tiers=[],
                currency="USD",
                billing_cycles=[]
            )
    
    def analyze_market_position(self, product_info: ProductInfo, company_website: str = "") -> MarketAnalysis:
        """
        Analyze market position and competitive landscape.
        
        Args:
            product_info: Basic product information
            company_website: Optional company website URL
            
        Returns:
            MarketAnalysis object with market insights
        """
        logger.info("Analyzing market position")
        
        try:
            # Use AI parsing for market analysis if available
            if self.use_ai_parsing and self.ai_parser:
                market_content = self._gather_market_content(product_info, company_website)
                
                if market_content:
                    # Create a comprehensive prompt for market analysis
                    analysis_prompt = f"""
                    Product: {product_info.name}
                    Description: {product_info.description}
                    Target Market: {product_info.target_market}
                    Existing Competitors: {', '.join(product_info.competitors)}
                    
                    Additional Context:
                    {market_content}
                    """
                    
                    # Use AI to analyze market position
                    ai_result = self._analyze_market_with_ai(analysis_prompt)
                    
                    if ai_result:
                        return ai_result
            
            # Fall back to basic analysis using existing product info
            return MarketAnalysis(
                target_market=product_info.target_market or "Unknown",
                competitors=product_info.competitors,
                market_position=product_info.market_analysis,
                competitive_advantages=[],
                growth_potential="Unknown"
            )
            
        except Exception as e:
            logger.error(f"Failed to analyze market position: {str(e)}")
            return MarketAnalysis(
                target_market="Unknown",
                competitors=[],
                market_position="",
                competitive_advantages=[],
                growth_potential="Unknown"
            )
    
    def _extract_basic_product_info(self, product_url: str) -> ProductInfo:
        """Extract basic product information using AI parsing."""
        logger.info("Extracting basic product information")
        
        self.rate_limiter.wait_if_needed()
        
        try:
            # Scrape the product page
            content = self._scrape_page_content(product_url)
            
            if self.use_ai_parsing and self.ai_parser:
                # Use AI parser to extract structured product info
                ai_result = self.ai_parser.parse_product_info(content, product_url)
                
                if ai_result.success and ai_result.data:
                    logger.info(f"AI parsing successful with confidence: {ai_result.confidence_score:.2f}")
                    return ai_result.data
                else:
                    logger.warning(f"AI parsing failed: {ai_result.error_message}")
            
            # Fall back to basic extraction
            return self._extract_basic_info_fallback(content, product_url)
            
        except Exception as e:
            logger.error(f"Failed to extract basic product info: {str(e)}")
            raise
    
    def _extract_features_from_url(self, url: str) -> List[Feature]:
        """Extract features from a specific URL."""
        logger.debug(f"Extracting features from: {url}")
        
        self.rate_limiter.wait_if_needed()
        
        try:
            content = self._scrape_page_content(url)
            
            if self.use_ai_parsing and self.ai_parser:
                # Use AI to extract and structure features
                features_content = self._extract_features_content(content)
                
                if features_content:
                    ai_features = self._extract_features_with_ai(features_content)
                    if ai_features:
                        return ai_features
            
            # Fall back to traditional feature extraction
            return self._extract_features_traditional(content)
            
        except Exception as e:
            logger.warning(f"Failed to extract features from {url}: {str(e)}")
            return []
    
    def _extract_pricing_from_url(self, url: str) -> PricingInfo:
        """Extract pricing information from a specific URL."""
        logger.debug(f"Extracting pricing from: {url}")
        
        self.rate_limiter.wait_if_needed()
        
        try:
            content = self._scrape_page_content(url)
            
            if self.use_ai_parsing and self.ai_parser:
                # Use AI to extract and structure pricing
                pricing_content = self._extract_pricing_content(content)
                
                if pricing_content:
                    ai_pricing = self._extract_pricing_with_ai(pricing_content)
                    if ai_pricing:
                        return ai_pricing
            
            # Fall back to traditional pricing extraction
            return self._extract_pricing_traditional(content)
            
        except Exception as e:
            logger.warning(f"Failed to extract pricing from {url}: {str(e)}")
            return PricingInfo(model="unknown", tiers=[])
    
    def _scrape_page_content(self, url: str) -> str:
        """Scrape content from a web page using Selenium for JavaScript rendering."""
        driver = None
        
        try:
            driver = webdriver.Chrome(options=self.chrome_options)
            driver.set_page_load_timeout(30)
            driver.get(url)
            
            # Wait for page to load
            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # Get page content
            content = driver.page_source
            
            logger.debug(f"Successfully scraped content from {url}")
            return content
            
        except Exception as e:
            logger.warning(f"Selenium scraping failed for {url}: {str(e)}. Trying requests fallback.")
            
            # Fall back to requests
            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                return response.text
            except Exception as fallback_e:
                logger.error(f"Both Selenium and requests failed for {url}: {str(fallback_e)}")
                raise
                
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass
    
    def _extract_basic_info_fallback(self, content: str, url: str) -> ProductInfo:
        """Fallback method for basic product info extraction."""
        soup = BeautifulSoup(content, 'html.parser')
        
        # Extract title
        title_elem = soup.find('title')
        name = title_elem.get_text(strip=True) if title_elem else "Unknown Product"
        
        # Extract description from meta tags
        desc_elem = soup.find('meta', attrs={'name': 'description'}) or soup.find('meta', attrs={'property': 'og:description'})
        description = desc_elem.get('content', '') if desc_elem else ""
        
        return ProductInfo(
            name=name,
            description=description,
            features=[],
            pricing_model="unknown",
            target_market="Unknown",
            competitors=[],
            market_analysis=""
        )
    
    def _extract_features_content(self, content: str) -> str:
        """Extract content sections that likely contain feature information."""
        soup = BeautifulSoup(content, 'html.parser')
        
        # Look for sections that might contain features
        feature_sections = []
        
        # Find sections with feature-related keywords
        feature_keywords = ['feature', 'capability', 'benefit', 'functionality', 'what we do', 'how it works']
        
        for keyword in feature_keywords:
            elements = soup.find_all(string=re.compile(keyword, re.I))
            for elem in elements:
                parent = elem.parent
                while parent and parent.name not in ['div', 'section', 'article']:
                    parent = parent.parent
                if parent and parent not in feature_sections:
                    feature_sections.append(parent)
        
        # Combine text from feature sections
        feature_text = ""
        for section in feature_sections[:5]:  # Limit to avoid too much content
            feature_text += section.get_text(separator=' ', strip=True) + "\n\n"
        
        return feature_text[:4000]  # Limit content length
    
    def _extract_features_with_ai(self, features_content: str) -> List[Feature]:
        """Use AI to extract structured features from content."""
        try:
            system_prompt = """You are an expert at analyzing product content and extracting structured feature information.

Your task is to analyze product content and extract features in JSON array format:

[
    {
        "name": "Feature name",
        "description": "Clear description of what this feature does",
        "category": "Feature category (optional)"
    }
]

Guidelines:
- Extract distinct product features and capabilities
- Keep feature names concise but descriptive
- Provide clear descriptions of what each feature accomplishes
- Group similar features under appropriate categories when possible
- Focus on user-facing features rather than technical implementation details
- Limit to the most important 10-15 features

Return only the JSON array, no additional text or explanation."""

            user_prompt = f"""
            Analyze the following product content and extract structured feature information:
            
            Content:
            {features_content}
            
            Return the data in the exact JSON format specified in the system prompt.
            """
            
            response = self.ai_parser.client_manager.make_completion(
                CompletionRequest(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.1,
                    max_tokens=1500
                ),
                self.ai_parser.client_id
            )
            
            if not response.success:
                raise Exception(response.error_message)
            
            # Parse the JSON response
            response_content = response.content
            json_start = response_content.find('[')
            json_end = response_content.rfind(']') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("No valid JSON array found in AI response")
            
            json_content = response_content[json_start:json_end]
            parsed_data = json.loads(json_content)
            
            # Create Feature objects
            features = []
            for feature_data in parsed_data:
                feature = Feature(
                    name=feature_data.get('name', ''),
                    description=feature_data.get('description', ''),
                    category=feature_data.get('category')
                )
                features.append(feature)
            
            logger.info(f"AI extracted {len(features)} features")
            return features
            
        except Exception as e:
            logger.error(f"AI feature extraction failed: {str(e)}")
            return []
    
    def _extract_features_traditional(self, content: str) -> List[Feature]:
        """Traditional method for feature extraction."""
        soup = BeautifulSoup(content, 'html.parser')
        features = []
        
        # Look for lists that might contain features
        lists = soup.find_all(['ul', 'ol'])
        
        for list_elem in lists:
            items = list_elem.find_all('li')
            if len(items) >= 3:  # Likely a feature list
                for item in items[:10]:  # Limit features
                    text = item.get_text(strip=True)
                    if len(text) > 10 and len(text) < 200:  # Reasonable feature length
                        feature = Feature(
                            name=text[:50],  # First part as name
                            description=text,
                            category="General"
                        )
                        features.append(feature)
        
        return features[:10]  # Limit to 10 features
    
    def _extract_pricing_content(self, content: str) -> str:
        """Extract content sections that likely contain pricing information."""
        soup = BeautifulSoup(content, 'html.parser')
        
        # Look for pricing-related sections
        pricing_sections = []
        pricing_keywords = ['pricing', 'price', 'plan', 'subscription', 'cost', 'free', 'premium', 'enterprise']
        
        for keyword in pricing_keywords:
            elements = soup.find_all(string=re.compile(keyword, re.I))
            for elem in elements:
                parent = elem.parent
                while parent and parent.name not in ['div', 'section', 'article']:
                    parent = parent.parent
                if parent and parent not in pricing_sections:
                    pricing_sections.append(parent)
        
        # Combine text from pricing sections
        pricing_text = ""
        for section in pricing_sections[:3]:  # Limit sections
            pricing_text += section.get_text(separator=' ', strip=True) + "\n\n"
        
        return pricing_text[:3000]  # Limit content length
    
    def _extract_pricing_with_ai(self, pricing_content: str) -> Optional[PricingInfo]:
        """Use AI to extract structured pricing from content."""
        try:
            system_prompt = """You are an expert at analyzing pricing content and extracting structured pricing information.

Your task is to analyze pricing content and extract information in JSON format:

{
    "model": "pricing model (freemium, subscription, one-time, enterprise, etc.)",
    "tiers": [
        {
            "name": "tier name (e.g., Free, Pro, Enterprise)",
            "price": "price amount",
            "billing": "billing cycle (monthly, yearly, one-time)",
            "features": ["key features included in this tier"]
        }
    ],
    "currency": "currency code (USD, EUR, etc.)",
    "billing_cycles": ["available billing cycles"]
}

Guidelines:
- Identify the overall pricing model
- Extract all pricing tiers with their details
- Include key features for each tier when available
- Determine currency from context
- If no clear pricing is found, use "unknown" for model

Return only the JSON object, no additional text or explanation."""

            user_prompt = f"""
            Analyze the following pricing content and extract structured pricing information:
            
            Content:
            {pricing_content}
            
            Return the data in the exact JSON format specified in the system prompt.
            """
            
            response = self.ai_parser.client_manager.make_completion(
                CompletionRequest(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.1,
                    max_tokens=1000
                ),
                self.ai_parser.client_id
            )
            
            if not response.success:
                raise Exception(response.error_message)
            
            # Parse the JSON response
            response_content = response.content
            json_start = response_content.find('{')
            json_end = response_content.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("No valid JSON found in AI response")
            
            json_content = response_content[json_start:json_end]
            parsed_data = json.loads(json_content)
            
            # Create PricingInfo object
            pricing = PricingInfo(
                model=parsed_data.get('model', 'unknown'),
                tiers=parsed_data.get('tiers', []),
                currency=parsed_data.get('currency', 'USD'),
                billing_cycles=parsed_data.get('billing_cycles', [])
            )
            
            logger.info(f"AI extracted pricing model: {pricing.model}")
            return pricing
            
        except Exception as e:
            logger.error(f"AI pricing extraction failed: {str(e)}")
            return None
    
    def _extract_pricing_traditional(self, content: str) -> PricingInfo:
        """Traditional method for pricing extraction."""
        soup = BeautifulSoup(content, 'html.parser')
        
        # Look for price indicators
        price_patterns = [r'\$\d+', r'€\d+', r'£\d+', r'\d+\s*USD', r'free', r'premium']
        
        pricing_model = "unknown"
        tiers = []
        
        text_content = soup.get_text().lower()
        
        # Determine pricing model based on keywords
        if 'free' in text_content and ('premium' in text_content or 'pro' in text_content):
            pricing_model = "freemium"
        elif 'subscription' in text_content or 'monthly' in text_content:
            pricing_model = "subscription"
        elif 'one-time' in text_content or 'lifetime' in text_content:
            pricing_model = "one-time"
        elif 'enterprise' in text_content:
            pricing_model = "enterprise"
        
        return PricingInfo(
            model=pricing_model,
            tiers=tiers,
            currency="USD"
        )
    
    def _gather_market_content(self, product_info: ProductInfo, company_website: str) -> str:
        """Gather content for market analysis."""
        content = f"Product: {product_info.name}\nDescription: {product_info.description}\n"
        
        if company_website:
            try:
                website_content = self._scrape_page_content(company_website)
                soup = BeautifulSoup(website_content, 'html.parser')
                
                # Extract relevant sections for market analysis
                about_section = soup.find(string=re.compile(r'about|mission|vision', re.I))
                if about_section and about_section.parent:
                    content += "\nAbout: " + about_section.parent.get_text(strip=True)[:500]
                
            except Exception as e:
                logger.warning(f"Failed to gather market content from website: {str(e)}")
        
        return content
    
    def _analyze_market_with_ai(self, analysis_prompt: str) -> Optional[MarketAnalysis]:
        """Use AI to analyze market position."""
        try:
            system_prompt = """You are an expert market analyst. Analyze the provided product information and extract market insights in JSON format:

{
    "target_market": "primary target market segment",
    "market_size": "estimated market size if determinable",
    "competitors": ["list of main competitors"],
    "competitive_advantages": ["key competitive advantages"],
    "market_position": "analysis of market position",
    "growth_potential": "assessment of growth potential"
}

Guidelines:
- Provide realistic market analysis based on the product information
- Identify clear target market segments
- List obvious competitors in the space
- Highlight unique value propositions as competitive advantages
- Assess market position objectively
- Evaluate growth potential based on market trends

Return only the JSON object, no additional text or explanation."""

            response = self.ai_parser.client_manager.make_completion(
                CompletionRequest(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": analysis_prompt}
                    ],
                    temperature=0.2,
                    max_tokens=1000
                ),
                self.ai_parser.client_id
            )
            
            if not response.success:
                raise Exception(response.error_message)
            
            # Parse the JSON response
            response_content = response.content
            json_start = response_content.find('{')
            json_end = response_content.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("No valid JSON found in AI response")
            
            json_content = response_content[json_start:json_end]
            parsed_data = json.loads(json_content)
            
            # Create MarketAnalysis object
            analysis = MarketAnalysis(
                target_market=parsed_data.get('target_market', 'Unknown'),
                market_size=parsed_data.get('market_size'),
                competitors=parsed_data.get('competitors', []),
                competitive_advantages=parsed_data.get('competitive_advantages', []),
                market_position=parsed_data.get('market_position', ''),
                growth_potential=parsed_data.get('growth_potential', '')
            )
            
            logger.info("AI market analysis completed successfully")
            return analysis
            
        except Exception as e:
            logger.error(f"AI market analysis failed: {str(e)}")
            return None
    
    def _gather_additional_context(self, product_url: str, company_website: str) -> Dict[str, Any]:
        """Gather additional context like funding info, team size, etc."""
        context = {}
        
        try:
            # Try to extract funding information
            if company_website:
                funding_info = self._extract_funding_info(company_website)
                if funding_info:
                    context['funding_info'] = funding_info
            
            # Try to extract team size
            team_size = self._estimate_team_size(product_url, company_website)
            if team_size:
                context['team_size'] = team_size
            
            # Extract social metrics if available
            social_metrics = self._extract_social_metrics(product_url)
            if social_metrics:
                context['social_metrics'] = social_metrics
                
        except Exception as e:
            logger.warning(f"Failed to gather additional context: {str(e)}")
        
        return context
    
    def _extract_funding_info(self, company_website: str) -> Optional[Dict[str, Any]]:
        """Extract funding information from company website."""
        try:
            content = self._scrape_page_content(company_website)
            soup = BeautifulSoup(content, 'html.parser')
            
            # Look for funding-related keywords
            funding_keywords = ['funding', 'investment', 'series a', 'series b', 'seed', 'venture']
            text_content = soup.get_text().lower()
            
            for keyword in funding_keywords:
                if keyword in text_content:
                    # Found funding mention - could extract more details with AI
                    return {'status': 'funded', 'details': f'Mentions {keyword}'}
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to extract funding info: {str(e)}")
            return None
    
    def _estimate_team_size(self, product_url: str, company_website: str) -> Optional[int]:
        """Estimate team size from available information."""
        try:
            # This is a simplified estimation - could be enhanced with LinkedIn data
            if company_website:
                content = self._scrape_page_content(company_website)
                soup = BeautifulSoup(content, 'html.parser')
                
                # Look for team section
                team_elements = soup.find_all(string=re.compile(r'team|staff|employee', re.I))
                if team_elements:
                    # Simple heuristic based on team mentions
                    return len(team_elements) * 2  # Rough estimate
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to estimate team size: {str(e)}")
            return None
    
    def _extract_social_metrics(self, product_url: str) -> Optional[Dict[str, Any]]:
        """Extract social metrics from ProductHunt or other sources."""
        try:
            if 'producthunt.com' in product_url:
                content = self._scrape_page_content(product_url)
                soup = BeautifulSoup(content, 'html.parser')
                
                # Look for upvotes, comments, etc.
                metrics = {}
                
                # This would need to be customized based on ProductHunt's current structure
                upvote_elem = soup.find(string=re.compile(r'\d+.*upvote', re.I))
                if upvote_elem:
                    metrics['upvotes'] = upvote_elem
                
                return metrics if metrics else None
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to extract social metrics: {str(e)}")
            return None
