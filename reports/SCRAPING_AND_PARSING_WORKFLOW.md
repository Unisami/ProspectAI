# Scraping and Parsing Workflow

This document explains how the scraping and parsing pipeline works in the job prospect automation system. It's a sophisticated multi-stage process that combines web scraping, AI parsing, and data enrichment.

## 🔄 **Complete Workflow Overview**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   ProductHunt   │───▶│   Raw HTML      │───▶│   AI Parser     │───▶│   Structured    │
│   Discovery     │    │   Extraction    │    │   Processing    │    │   Data Storage  │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │                       │
         ▼                       ▼                       ▼                       ▼
    • Find new                • Web scraping          • OpenAI/Azure           • Notion database
      products                • HTML parsing          • Data structuring       • Rich text blocks
    • Extract URLs            • Content extraction    • Entity extraction      • No truncation
    • Rate limiting           • Multiple strategies   • Validation             • Full preservation
```

## 📋 **Detailed Pipeline Stages**

### **Stage 1: Discovery & Initial Scraping**

#### **1.1 ProductHunt Discovery** (`services/product_hunt_scraper.py`)

```python
# Main entry point
def get_latest_products(self, limit: int = 50) -> List[ProductData]:
    """Scrape ProductHunt for latest product launches"""
```

**Process:**
1. **HTTP Request to ProductHunt homepage**
   - Uses requests with proper headers
   - Rate limiting (2-second delays)
   - Retry logic with exponential backoff

2. **HTML Parsing with BeautifulSoup**
   - Extracts product cards from homepage
   - Multiple extraction strategies:
     - Primary: Look for product elements with class patterns
     - Fallback: Search for links to `/posts/` URLs
     - Alternative: Parse JSON data from Apollo GraphQL

3. **Data Extraction**
   - Product name and description
   - ProductHunt URL
   - Company name (derived from URL)
   - Launch date

#### **1.2 Website URL Discovery** (`services/website_extractor.py`)

```python
def extract_website_url(self, product_url: str) -> str:
    """Extract company website from ProductHunt page"""
```

**Dual Strategy Approach:**
1. **Selenium (Primary)**
   - Handles JavaScript-rendered content
   - Looks for "Visit Website" buttons
   - Extracts external links

2. **Requests (Fallback)**
   - Faster for static content
   - BeautifulSoup parsing
   - Pattern matching for website links

### **Stage 2: Team Member Extraction**

#### **2.1 AI-Enhanced Team Extraction** (`services/ai_team_extractor.py`)

```python
def extract_team_from_product_url(self, product_url: str, company_name: str) -> List[TeamMember]:
    """Extract team members using AI parsing"""
```

**Multi-Strategy Extraction:**

1. **Raw HTML Acquisition**
   - Selenium for JavaScript content
   - Requests fallback
   - Full page content capture

2. **Team Section Identification**
   ```python
   def _extract_team_section(self, html: str) -> str:
       """Extract team-specific content from HTML"""
   ```
   - **Strategy 1**: Apollo GraphQL JSON parsing
     - Regex patterns for User objects
     - Extract name, headline, username
     - Find makers arrays

   - **Strategy 2**: HTML element parsing
     - User avatar images with alt text
     - Role information in surrounding elements
     - LinkedIn links in parent containers

   - **Strategy 3**: Text pattern matching
     - "— Name, role @ Company" patterns
     - "I'm Name, role" patterns
     - Parenthetical role descriptions

   - **Strategy 4**: Direct LinkedIn link extraction
     - Find LinkedIn URLs in page
     - Match with nearby names
     - Context-based association

3. **AI Structuring** (`services/ai_parser.py`)
   ```python
   def structure_team_data(self, raw_team_info: str, company_name: str) -> ParseResult:
       """Use AI to structure team member data"""
   ```

#### **2.2 LinkedIn URL Discovery** (`services/linkedin_finder.py`)

For team members without LinkedIn URLs:

```python
def find_linkedin_urls_for_team(self, team_members: List[TeamMember]) -> List[TeamMember]:
    """Find LinkedIn URLs using multiple search strategies"""
```

**Search Strategies:**
1. **Google/DuckDuckGo Search**
   - `"Name" Company site:linkedin.com/in`
   - `"Name" "Role" Company linkedin`
   - Profile verification by username matching

2. **Company Website Crawling**
   - Find company domains (company.com, company.io, etc.)
   - Crawl team pages (/team, /about, /people)
   - Extract LinkedIn links near names

3. **Social Media Aggregators**
   - Crunchbase profiles
   - AngelList profiles
   - Extract LinkedIn URLs from profiles

4. **Name Variations**
   - Nicknames (William → Bill, Michael → Mike)
   - Initials (John Smith → J. Smith)
   - Different name formats

### **Stage 3: Data Enrichment**

#### **3.1 Email Discovery** (`services/email_finder.py`)

```python
def find_emails_for_team_members(self, team_members: List[TeamMember], domain: str) -> Dict[str, str]:
    """Find email addresses for team members"""
```

**Email Finding Strategies:**
1. **Hunter.io API Integration**
   - Domain-based email search
   - Email pattern detection
   - Verification scores

2. **Pattern-Based Generation**
   - Common patterns: first.last@domain.com
   - Variations: firstlast@, first@, f.last@
   - Domain validation (very permissive for modern domains like x.ai, app.link, meet-ting.com)
   - Accepts domains as short as 3 characters (e.g., x.ai)
   - Flexible format validation for complex domains and subdomains

#### **3.2 LinkedIn Profile Scraping** (`services/linkedin_scraper.py`)

```python
def extract_profile_data(self, linkedin_url: str) -> LinkedInProfile:
    """Extract detailed LinkedIn profile data"""
```

**Profile Data Extraction:**
- Professional summary
- Work experience
- Skills and endorsements
- Education background
- Current role and company

### **Stage 4: AI-Powered Data Structuring**

#### **4.1 Product Analysis** (`services/product_analyzer.py`)

```python
def analyze_product_comprehensively(self, company_data: CompanyData) -> ComprehensiveProductInfo:
    """Comprehensive product analysis with AI enhancement"""
```

**Analysis Components:**
- Product features and capabilities
- Target market identification
- Competitive landscape analysis
- Pricing model assessment
- Market positioning
- Business model evaluation

#### **4.2 AI Parser Integration** (`services/ai_parser.py`)

The AI parser uses OpenAI/Azure OpenAI to structure raw data:

```python
class AIParser:
    """Service for parsing and structuring scraped data using AI"""
    
    def parse_linkedin_profile(self, raw_html: str) -> ParseResult:
        """Parse LinkedIn HTML into structured data"""
    
    def parse_product_info(self, raw_content: str) -> ParseResult:
        """Parse product information into structured data"""
    
    def structure_team_data(self, raw_team_info: str) -> ParseResult:
        """Structure team member information"""
    
    def extract_business_metrics(self, company_data: str) -> ParseResult:
        """Extract business metrics and insights"""
```

**AI Processing Features:**
- **Increased Input Limits**: 10,000-12,000 characters
- **Enhanced Output**: 2,500-3,000 tokens
- **Structured JSON Output**: Consistent data formats
- **Error Handling**: Fallback strategies
- **Confidence Scoring**: Data quality assessment

### **Stage 5: Data Storage & Preservation**

#### **5.1 Notion Integration** (`services/notion_manager.py`)

```python
def store_ai_structured_data(self, prospect_id: str, **data) -> bool:
    """Store AI-processed data without truncation"""
```

**Storage Features:**
- **No Truncation**: Full data preservation
- **Rich Text Blocks**: Split long content into multiple 2000-char blocks
- **Data Reconstruction**: Seamless retrieval of complete data
- **Duplicate Prevention**: Returns existing prospect ID instead of creating duplicates
- **Comprehensive Fields**: 
  - Product summary (unlimited length)
  - Business insights (unlimited length)
  - LinkedIn summary (unlimited length)
  - Personalization data (unlimited length)

#### **5.2 Data Structure in Notion**

```
Prospect Record:
├── Basic Info (Name, Role, Company, Email, LinkedIn)
├── AI-Structured Data
│   ├── Product Summary (Rich Text Blocks)
│   ├── Business Insights (Rich Text Blocks)
│   ├── LinkedIn Summary (Rich Text Blocks)
│   └── Personalization Data (Rich Text Blocks)
├── Processing Metadata
│   ├── AI Processing Status
│   ├── Processing Date
│   └── Confidence Scores
└── Email Generation Data
    ├── Generated Emails
    ├── Email Status
    └── Delivery Tracking
```

## 🔧 **Technical Implementation Details**

### **Rate Limiting & Error Handling**

```python
class RateLimiter:
    """Manages request timing to respect external service limits"""
    
    def wait_if_needed(self):
        """Enforce delays between requests"""
```

**Rate Limiting Strategy:**
- 2-second delays between ProductHunt requests
- 10-second delays between LinkedIn searches
- Exponential backoff on failures
- Respect for robots.txt and API limits

### **Multi-Strategy Fallbacks**

Each scraping component has multiple fallback strategies:

1. **Primary Strategy**: Most reliable method (e.g., Selenium)
2. **Secondary Strategy**: Faster fallback (e.g., Requests)
3. **Tertiary Strategy**: Alternative parsing (e.g., Regex)
4. **AI Enhancement**: Structure any extracted data

### **Data Validation & Quality**

```python
def validate_extracted_data(self, data: Dict[str, Any]) -> ValidationResult:
    """Validate extracted data quality"""
```

**Validation Checks:**
- Required fields presence
- Data format validation
- LinkedIn URL verification
- Email address validation
- Duplicate detection (returns existing prospect ID if found)

## 📊 **Data Flow Example**

Here's how a single company flows through the pipeline:

```
1. ProductHunt Discovery
   Input: "https://www.producthunt.com/"
   Output: ProductData(name="TechCorp", url="https://www.producthunt.com/products/techcorp")

2. Website Extraction
   Input: ProductHunt URL
   Output: "https://techcorp.com"

3. Team Extraction
   Input: ProductHunt page HTML
   Processing: AI parsing + multiple strategies
   Output: [TeamMember(name="John Smith", role="CEO"), ...]

4. LinkedIn Discovery
   Input: Team members without LinkedIn URLs
   Processing: Multi-strategy search
   Output: Updated team members with LinkedIn URLs

5. Email Finding
   Input: Team members + company domain
   Processing: Hunter.io + pattern generation
   Output: Email addresses for team members

6. LinkedIn Scraping
   Input: LinkedIn URLs
   Processing: Profile data extraction
   Output: LinkedInProfile objects with full data

7. AI Structuring
   Input: All raw data
   Processing: OpenAI/Azure OpenAI structuring
   Output: Structured, personalization-ready data

8. Notion Storage
   Input: Structured data
   Processing: Rich text block creation
   Output: Complete data stored without truncation
```

## 🚀 **Performance Optimizations**

### **Parallel Processing**
- Multiple team members processed concurrently
- Batch API requests where possible
- Asynchronous operations for I/O

### **Caching Strategy**
- LinkedIn profile caching
- Company domain caching
- AI parsing result caching

### **Memory Management**
- Streaming HTML processing
- Garbage collection of large objects
- Efficient data structures

## 🔍 **Monitoring & Debugging**

### **Comprehensive Logging**
```python
logger.info(f"Extracted {len(team_members)} team members")
logger.debug(f"Team HTML content length: {len(team_html)}")
logger.warning(f"No LinkedIn URL found for {member.name}")
logger.error(f"AI parsing failed: {error_message}")
```

### **Success Metrics**
- Team member extraction rate
- LinkedIn URL discovery rate
- Email finding success rate
- AI parsing confidence scores
- Data completeness metrics

### **Error Tracking**
- Failed scraping attempts
- Rate limiting encounters
- AI parsing failures
- Data validation errors

This pipeline ensures comprehensive, high-quality prospect data extraction with minimal manual intervention and maximum data preservation.