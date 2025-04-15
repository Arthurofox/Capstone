from crawl4ai import AsyncWebCrawler, CacheMode, BrowserConfig, CrawlerRunConfig
from crawl4ai.extraction_strategy import LLMExtractionStrategy, JsonCssExtractionStrategy
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from typing import List, Optional
import asyncio
import json
import os
import csv
from datetime import datetime
import litellm
import csv
# Load environment variables
load_dotenv()
litellm._turn_on_debug()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in .env file")

class JobRequirements(BaseModel):
    education_level: str = Field(..., description="Required education level")
    skills: List[str] = Field(..., description="Required technical skills")
    languages: List[str] = Field(..., description="Required languages")

class JobOffer(BaseModel):
    title: str = Field(..., description="Job title")
    company: str = Field(..., description="Company name")
    location: str = Field(..., description="Job location")
    contract_type: str = Field(..., description="Type of contract")
    description: str = Field(..., description="Full job description")
    posted_date: str = Field(..., description="Posted date")
    requirements: JobRequirements = Field(..., description="Job requirements")
    salary_range: Optional[str] = Field(None, description="Salary range if mentioned")
    url: str = Field(..., description="Job offer URL")

def process_cookies(cookies):
    """Process cookies to ensure they have all required fields."""
    for cookie in cookies:
        if 'path' not in cookie:
            cookie['path'] = '/'
        cookie['secure'] = True
        cookie['httpOnly'] = True
        cookie['value'] = str(cookie['value'])
    return cookies

def load_cookies(cookie_path: str = 'cookies.json'):
    """Load cookies from a JSON file and process them."""
    try:
        with open(cookie_path, 'r') as f:
            cookies = json.load(f)
            return process_cookies(cookies)
    except Exception as e:
        print(f"Error loading cookies: {e}")
        return None

class JobScraper:
    def __init__(self, base_url="https://skema.jobteaser.com/fr/job-offers"):
        self.base_url = base_url
        self.cookies = load_cookies('cookies.json')
        self.browser_config = BrowserConfig(
            headless=False,
            verbose=True,
            cookies=self.cookies,
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36")
        
        self.csv_filename = f"job_offers_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        self._init_csv()

    def _init_csv(self):
        """Initialize CSV file with headers."""
        headers = [
            'title', 'company', 'location', 'contract_type', 'posted_date',
            'education_level', 'skills', 'languages', 'salary_range',
            'description', 'url'
        ]
        with open(self.csv_filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()

    def save_job_to_csv(self, job: JobOffer):
        """Save a job offer to CSV file."""
        # Assuming self.filters is a dict like:
        # {'keywords': 'developer', 'location': 'Paris', 'contract_type': 'Internship'}
        search_filters_str = json.dumps(self.filters) if hasattr(self, 'filters') else ''

        job_dict = {
            'title': job.title,
            'company': job.company,
            'location': job.location,
            'contract_type': job.contract_type,
            'posted_date': job.posted_date,
            'education_level': job.requirements.education_level,
            'skills': '; '.join(job.requirements.skills),
            'languages': '; '.join(job.requirements.languages),
            'salary_range': job.salary_range or 'Not specified',
            'description': job.description,
            'url': job.url,
            'search_filters': search_filters_str  
        }
        
        # Write row to CSV file (header assumed to be handled separately if needed)
        with open(self.csv_filename, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=job_dict.keys())
            writer.writerow(job_dict)

    async def apply_filters(self, **filters):
        """Generate JavaScript code for applying filters."""
        js_code = []
        
        if filters.get('keywords'):
            js_code.append(f"""
                (async () => {{
                    const searchInput = document.querySelector('[data-testid="job-ads-autocomplete-keyword-search-input"]');
                    if (searchInput) {{
                        searchInput.value = "{filters['keywords']}";
                        searchInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        await new Promise(r => setTimeout(r, 1000));
                    }}
                }})();
            """)
        
        if filters.get('location'):
            js_code.append(f"""
                (async () => {{
                    const locationInput = document.querySelector('.LocationFilter_main__input__B11T6');
                    if (locationInput) {{
                        locationInput.value = "{filters['location']}";
                        locationInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        await new Promise(r => setTimeout(r, 1000));
                    }}
                }})();
            """)
        
        if filters.get('contract_type'):
            js_code.append(f"""
                (async () => {{
                    const contractFilter = document.querySelector('[data-testid="job-ads-contract-filter"]');
                    if (contractFilter) {{
                        contractFilter.click();
                        await new Promise(r => setTimeout(r, 1000));
                        const contractOption = Array.from(document.querySelectorAll('li')).find(li => 
                            li.textContent.toLowerCase().includes('{filters["contract_type"]}'.toLowerCase()));
                        if (contractOption) {{
                            contractOption.click();
                            await new Promise(r => setTimeout(r, 1000));
                        }}
                    }}
                }})();
            """)
        
        if js_code:
            js_code.append("await new Promise(r => setTimeout(r, 2000));")
        
        return js_code

    async def collect_job_links(self, crawler: AsyncWebCrawler, **filters):
        """Collect all job links from listing pages."""
        job_links = set()
        page = 1
        
        # Define extraction strategy for links with the updated schema
        link_schema = {
            "name": "Job Links",
            "baseSelector": "ul[data-testid='job-ads-wrapper'] li",
            "fields": [
                {
                    "name": "link",
                    "selector": "div[data-testid='jobad-card'] a.JobAdCard_link__n5lkb",
                    "type": "attribute",
                    "attribute": "href"
                }
            ]
        }
        
        link_strategy = JsonCssExtractionStrategy(link_schema, verbose=True)
        
        while True:
            print(f"\nCollecting links from page {page}...")
            
            # Apply filters only on the first page
            js_code = await self.apply_filters(**filters) if page == 1 else None
            
            # Wait until the job list items are present
            run_config = CrawlerRunConfig(
                extraction_strategy=link_strategy,
                cache_mode=CacheMode.ENABLED,
                js_code=js_code,
                exclude_external_links=True,
                exclude_social_media_links=True,
                exclude_external_images=True, 
                wait_for="css:ul[data-testid='job-ads-wrapper'] li"
            )
            
            result = await crawler.arun(
                url=f"{self.base_url}?page={page}",
                config=run_config
            )
            
            try:
                # Extract links from the JSON result
                if result.extracted_content:
                    content = json.loads(result.extracted_content)
                    if isinstance(content, list):
                        new_links = set(item["link"] for item in content if "link" in item)
                    else:
                        new_links = set(content.get('link', []))
                    
                    if new_links:
                        print(f"Found {len(new_links)} job links on page {page}")
                    else:
                        print(f"No new job links found on page {page}")
                    
                    job_links.update(new_links)
                    
                    # Check for pagination (using a unique pagination class if available)
                    if "Pagination_item__Raak6" not in result.html:
                        print("No more pages found.")
                        break
                    
                    page += 1
                    await asyncio.sleep(1)  # Delay between pages
                else:
                    print("No links found on this page.")
                    break
                
            except Exception as e:
                print(f"Error collecting links from page {page}: {e}")
                if hasattr(result, 'extracted_content'):
                    print("Raw content:", result.extracted_content)
                break
        
        # Convert relative URLs to absolute URLs
        absolute_links = {
            link if link.startswith('http') else f"https://skema.jobteaser.com{link}"
            for link in job_links
        }
        
        return list(absolute_links)


    async def scrape_job_page(self, url: str, crawler: AsyncWebCrawler) -> JobOffer:
        """Scrape individual job page and extract the job offer details."""
        print(f"Scraping job at {url}")

        # Instantiate a fresh LLM extraction strategy for this job page.
        llm_strategy = LLMExtractionStrategy(
            provider="openai/gpt-4o-mini",
            api_token=OPENAI_API_KEY,
            schema=JobOffer.model_json_schema(),
            extraction_type="schema",
            instruction="""
            Extract job offer details from the provided HTML snippet using the following mapping:
            - **title:** Job title.
            - **company:** Company name.
            - **location:** Job location.
            - **contract_type:** Type of contract.
            - **posted_date:** The posted date.
            - **description:** Full job description.
            - **requirements:** Parse and extract 'education_level', 'skills', and 'languages' from the description.
            - **salary_range:** Include if mentioned.
            Return a single JSON object following the provided schema.
            """,
            chunk_token_threshold=1000,
            overlap_rate=0.1,
            apply_chunking=True,
            input_format="html",
            extra_args={"temperature": 0.1, "max_tokens": 1000}
        )

        # Use a run configuration that excludes extraneous content.
        run_config = CrawlerRunConfig(
            extraction_strategy=llm_strategy,
            cache_mode=CacheMode.BYPASS,  # Force fresh extraction every time.
            exclude_external_links=True,
            exclude_social_media_links=True,
            exclude_external_images=True,
            excluded_tags=["script", "style", "header", "footer", "nav"],
            # Restrict the HTML to likely job details; adjust selectors based on your page.
            css_selector="#main-content, .job-description, article"
        )

        result = await crawler.arun(url=url, config=run_config, magic=True)

        try:
            content = json.loads(result.extracted_content)
        except Exception as e:
            print("Error parsing JSON:", e)
            print("Raw extracted content:", result.extracted_content)
            raise

        # If the result is a list, select the first non-error item.
        if isinstance(content, list):
            job_data = next((item for item in content if not item.get('error', False)), None)
            if not job_data:
                raise ValueError("No valid job data found in response")
        else:
            job_data = content

        job_data['url'] = url
        return JobOffer(**job_data)

    async def scrape_jobs(self, **filters):
        """Main scraping function."""
        async with AsyncWebCrawler(config=self.browser_config) as crawler:
            try:
                # Collect job links first
                job_links = await self.collect_job_links(crawler, **filters)
                print(f"\nFound {len(job_links)} total jobs to process")
                
                # Process each job page
                for index, url in enumerate(job_links, 1):
                    try:
                        print(f"\nProcessing job {index}/{len(job_links)}")
                        job = await self.scrape_job_page(url, crawler)
                        self.save_job_to_csv(job)
                        print(f"Processed: {job.title} at {job.company}")
                        await asyncio.sleep(1)
                    except Exception as e:
                        print(f"Error processing job {url}: {e}")
                
                print(f"\nScraping complete! Processed {len(job_links)} jobs")
                print(f"Results saved to: {self.csv_filename}")
                
            except Exception as e:
                print(f"Error during scraping: {e}")

async def main():
    scraper = JobScraper()
    filters = {
        'keywords': 'developer',
        'location': '',
        'contract_type': 'thesis'
    }
    
    try:
        await scraper.scrape_jobs(**filters)
    except Exception as e:
        print(f"Error during scraping: {e}")

if __name__ == "__main__":
    print("Starting job navigation...")
    asyncio.run(main())
    print("Navigation complete.")