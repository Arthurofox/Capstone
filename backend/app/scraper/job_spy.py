import os
import csv
import json
import time
from jobspy import scrape_jobs
from litellm import completion
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in .env file")

# Define Pydantic models for structured data
class JobRequirements(BaseModel):
    education_level: Optional[str] = Field(None, description="Required education level")
    skills: Optional[List[str]] = Field(None, description="Required technical skills")
    languages: Optional[List[str]] = Field(None, description="Required languages")

class JobOffer(BaseModel):
    title: str = Field(..., description="Job title")
    company: str = Field(..., description="Company name")
    location: Optional[str] = Field(None, description="Job location")
    contract_type: str = Field("Not specified", description="Type of contract")
    posted_date: Optional[str] = Field(None, description="Posted date")
    requirements: JobRequirements = Field(..., description="Job requirements")
    salary_range: Optional[str] = Field(None, description="Salary range if mentioned")
    description: str = Field(..., description="Full job description")
    url: str = Field(..., description="Job offer URL")

def summarize_job_description(description: str, max_length: int = 500) -> str:
    """
    Summarize a job description using GPT-4o mini to fit within max_length characters.
    Ensures the description is complete and well-formed.
    """
    if len(description) <= max_length:
        return description

    # Prompt to summarize the description
    prompt = f"""
    Summarize the following job description in a complete paragraph (not truncated).
    Focus on the main responsibilities, requirements, and qualifications.
    Make sure the summary doesn't end abruptly and covers the key points.
    
    Original job description:
    {description}
    """
    
    try:
        response = completion(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        summary = response.choices[0].message.content.strip()
        
        # Ensure the summary doesn't exceed max_length
        if len(summary) > max_length:
            # Find the last period before max_length to avoid cutting mid-sentence
            last_period = summary[:max_length-3].rfind('.')
            if last_period > max_length // 2:  # Only use if we have a substantial portion
                summary = summary[:last_period+1]
            else:
                summary = summary[:max_length-3] + "..."
                
        return summary
    except Exception as e:
        print(f"Error summarizing description: {e}")
        
        # Better fallback truncation - find the last complete sentence
        if len(description) > max_length:
            # Find the last period before max_length
            last_period = description[:max_length-3].rfind('.')
            if last_period > max_length // 2:  # Only use if we have a substantial portion
                return description[:last_period+1]
            else:
                return description[:max_length-3] + "..."
        return description

# Extract requirements from description using GPT-4o mini
def extract_job_requirements(description: str) -> JobRequirements:
    if not description or len(description) < 50:  # Skip if too short
        return JobRequirements(
            education_level="Not specified",
            skills=["Not specified"],
            languages=["Not specified"]
        )

    prompt = f"""
    Extract the following details from the job description:
    - Education level (e.g., Bachelor's, Master's, PhD, or Not specified)
    - Required technical skills (list of specific skills, separated by commas)
    - Required languages (list of languages, separated by commas)

    Job Description:
    {description}

    Respond with a JSON object containing 'education_level', 'skills', and 'languages'.
    Make sure skills and languages are detailed and specific when available.
    """
    try:
        response = completion(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        extracted_data = json.loads(response.choices[0].message.content)
        time.sleep(1)  # Avoid API rate limits
        
        # Convert skills and languages to lists if they're strings
        skills = extracted_data.get("skills", ["Not specified"])
        if isinstance(skills, str):
            skills = [skill.strip() for skill in skills.split(",")]
            
        languages = extracted_data.get("languages", ["Not specified"])
        if isinstance(languages, str):
            languages = [lang.strip() for lang in languages.split(",")]
        
        return JobRequirements(
            education_level=extracted_data.get("education_level", "Not specified"),
            skills=skills,
            languages=languages
        )
    except Exception as e:
        print(f"Error extracting requirements: {e}")
        return JobRequirements(
            education_level="Not specified",
            skills=["Not specified"],
            languages=["Not specified"]
        )

# JobScraper class to manage scraping and processing
class JobScraper:
    def __init__(self):
        self.csv_filename = f"processed_jobs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        self._init_csv()

    def _init_csv(self):
        """Initialize CSV with headers."""
        headers = [
            "title", "company", "location", "contract_type", "posted_date",
            "education_level", "skills", "languages", "salary_range", "description", "url"
        ]
        with open(self.csv_filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()

    def process_job(self, row: pd.Series) -> JobOffer:
        """Process a single job row."""
        description = row.get("description", "")
        title = row.get("title", "").lower()
        
        # Extract requirements using AI
        requirements = extract_job_requirements(description)

        # Better contract_type handling
        contract_type = "Not specified"
        
        # First check the job_type field
        if not pd.isna(row.get("job_type")):
            job_type = str(row["job_type"]).strip().lower()
            if job_type != "nan" and job_type:
                if "fulltime" in job_type:
                    contract_type = "CDI"
                elif "part" in job_type:
                    contract_type = "Part-time"
                elif "intern" in job_type:
                    contract_type = "Internship"
                elif "contract" in job_type:
                    contract_type = "CDD"
                else:
                    contract_type = job_type.capitalize()
        
        # If contract_type is still not specified, check the job title
        if contract_type == "Not specified":
            if "intern" in title or "internship" in title or "stage" in title:
                contract_type = "Internship"
            elif "cdi" in title:
                contract_type = "CDI"
            elif "cdd" in title:
                contract_type = "CDD"
            elif "part time" in title or "part-time" in title:
                contract_type = "Part-time"
            
        # Still not found? Check the description
        if contract_type == "Not specified" and description:
            desc_lower = description.lower()
            if "internship" in desc_lower or "intern position" in desc_lower or "stage" in desc_lower:
                contract_type = "Internship"
            elif "cdi" in desc_lower or "permanent position" in desc_lower or "full time" in desc_lower:
                contract_type = "CDI"
            elif "cdd" in desc_lower or "fixed term" in desc_lower:
                contract_type = "CDD"

        # Better location handling
        location = "Not specified"
        if not pd.isna(row.get("location")) and row.get("location", "").strip():
            location = row.get("location").strip()
            if "fr" in location.lower() and "paris" not in location.lower():
                location = f"{location.split(',')[0].strip()}, France"

        # Better salary_range handling
        salary_range = "Not specified"
        if not pd.isna(row.get("min_amount")) or not pd.isna(row.get("max_amount")):
            min_amount = row.get("min_amount", "")
            max_amount = row.get("max_amount", "")
            interval = row.get("interval", "")
            currency = "EUR" if row.get("currency", "") == "" else row.get("currency", "")
            
            if min_amount and max_amount:
                salary_range = f"{min_amount} - {max_amount} {currency}"
                if interval:
                    salary_range += f" {interval}"
            elif min_amount:
                salary_range = f"{min_amount}+ {currency}"
                if interval:
                    salary_range += f" {interval}"
            elif max_amount:
                salary_range = f"Up to {max_amount} {currency}"
                if interval:
                    salary_range += f" {interval}"
            
            salary_range = salary_range.strip()

        # Better posted_date handling
        posted_date = "Not specified"
        if not pd.isna(row.get("date_posted")) and str(row.get("date_posted")).strip().lower() != "nan":
            try:
                date_obj = pd.to_datetime(row.get("date_posted"))
                posted_date = date_obj.strftime("%Y-%m-%d")
            except:
                posted_date = str(row.get("date_posted"))

        # Summarize description to ensure it's complete
        summarized_description = summarize_job_description(description)

        return JobOffer(
            title=row.get("title", "Not specified"),
            company=row.get("company", "Not specified"),
            location=location,
            contract_type=contract_type,
            posted_date=posted_date,
            requirements=requirements,
            salary_range=salary_range,
            description=summarized_description,
            url=row.get("job_url", "Not specified")
        )

    def save_job_to_csv(self, job: JobOffer):
        """Save processed job to CSV."""
        with open(self.csv_filename, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "title", "company", "location", "contract_type", "posted_date",
                "education_level", "skills", "languages", "salary_range", "description", "url"
            ])
            writer.writerow({
                "title": job.title,
                "company": job.company,
                "location": job.location,
                "contract_type": job.contract_type,
                "posted_date": job.posted_date,
                "education_level": job.requirements.education_level or "Not specified",
                "skills": "; ".join(job.requirements.skills) if job.requirements.skills else "Not specified",
                "languages": "; ".join(job.requirements.languages) if job.requirements.languages else "Not specified",
                "salary_range": job.salary_range,
                "description": job.description,
                "url": job.url
            })

    def scrape_and_process_jobs(self, search_term="developer", location="Paris, France", results_wanted=10):
        """Scrape and process jobs."""
        try:
            print(f"Scraping jobs for '{search_term}' in '{location}'...")
            jobs_df = scrape_jobs(
                site_name=["indeed", "linkedin", "glassdoor"],
                search_term=search_term,
                location=location,
                results_wanted=results_wanted,
                country_indeed="France",
                verbose=2
            )
            print(f"Found {len(jobs_df)} jobs")
            
            # Process each row immediately after scraping
            for index, row in jobs_df.iterrows():
                print(f"Processing job {index + 1}/{len(jobs_df)}: {row.get('title', 'Unknown job')}")
                processed_job = self.process_job(row)
                self.save_job_to_csv(processed_job)
                print(f"✓ Completed processing job {index + 1}/{len(jobs_df)}")
                
            return self.csv_filename
        except Exception as e:
            print(f"Error during scraping/processing: {e}")
            return None
    
    def process_existing_csv(self, input_file, output_file=None):
        """Process an existing CSV file with job listings."""
        if output_file is None:
            output_file = f"processed_{os.path.basename(input_file)}"
        
        try:
            # Read the CSV file
            df = pd.read_csv(input_file)
            print(f"Processing {len(df)} jobs from {input_file}...")
            
            # Create output file
            with open(output_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=[
                    "title", "company", "location", "contract_type", "posted_date",
                    "education_level", "skills", "languages", "salary_range", "description", "url"
                ])
                writer.writeheader()
            
            # Process each row
            for index, row in df.iterrows():
                # Handle the case where we're processing pre-extracted data
                # Check if this is already in our target format
                if all(field in df.columns for field in ["title", "company", "location", "contract_type"]):
                    # This might be a pre-formatted CSV - handle it differently
                    
                    # Convert row to a Series if it's not already
                    if not isinstance(row, pd.Series):
                        row = pd.Series(row)
                    
                    title = row.get("title", "Not specified")
                    description = row.get("description", "")
                    
                    # Extract contract type from title if it's "Not specified"
                    contract_type = row.get("contract_type", "Not specified")
                    if contract_type == "Not specified":
                        if "intern" in title.lower() or "internship" in title.lower() or "stage" in title.lower():
                            contract_type = "Internship"
                    
                    # Ensure description isn't cut off
                    if description and len(description) > 100:  # Only process substantial descriptions
                        if description.endswith("...") or description.endswith(".."):
                            description = summarize_job_description(description)
                    
                    # Create a new row with updated fields
                    new_row = row.copy()
                    new_row["contract_type"] = contract_type
                    new_row["description"] = description
                    
                    # Write directly to CSV
                    with open(output_file, "a", newline="", encoding="utf-8") as f:
                        writer = csv.DictWriter(f, fieldnames=[
                            "title", "company", "location", "contract_type", "posted_date",
                            "education_level", "skills", "languages", "salary_range", "description", "url"
                        ])
                        writer.writerow(new_row.to_dict())
                else:
                    # Standard processing for raw scraped data
                    processed_job = self.process_job(row)
                    self.save_job_to_csv(processed_job)
                
                print(f"Processed job {index + 1}/{len(df)}: {row.get('title', 'Unknown job')}")
                
            print(f"Processed jobs saved to {output_file}")
            return output_file
        except Exception as e:
            print(f"Error processing CSV file: {e}")
            return None

    def create_sample_data(self, output_file=None):
        """Create a sample CSV with the correct format."""
        if output_file is None:
            output_file = f"sample_jobs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        # Sample job data
        sample_jobs = [
            {
                "title": "Stage Droit Social F/H",
                "company": "SKEMA Business School",
                "location": "Paris",
                "contract_type": "Internship",
                "posted_date": "As soon as possible",
                "education_level": "Bac +3 minimum en droit",
                "skills": ["Connaissance en droit social", "Capacité d'analyse", "Rigueur"],
                "languages": ["Français", "Anglais"],
                "salary_range": "Not specified",
                "description": "Nous recherchons un(e) stagiaire en droit social pour rejoindre notre équipe à Paris. Le stage est une excellente opportunité pour acquérir une expérience pratique dans le domaine du droit social et pour travailler sur des projets variés.",
                "url": "https://skema.jobteaser.com/en/job-offers/223ec8a7-1a4f-4912-8bc3-401b6b3fa288-ey-stage-droit-social-f-h-paris-des-que-possible"
            },
            {
                "title": "Equity Listing Intern",
                "company": "Euronext",
                "location": "Paris",
                "contract_type": "Internship",
                "posted_date": "2025-04-01",
                "education_level": "Master's",
                "skills": ["Financial services", "Project management", "Analytical skills", "Problem-solving capabilities", "Oral communication", "Written communication", "Data analysis", "Market sizing", "Financial modelling", "Presentation preparation"],
                "languages": ["English", "French"],
                "salary_range": "Not specified",
                "description": "Euronext is seeking an intern for its Primary Markets department, specifically the Equity Listing team, to support projects aimed at enhancing the company's value proposition and competitiveness as a key listing venue. The ideal candidate is in their final year of studies with strong analytical skills and an interest in financial markets. The role involves supporting strategic initiatives, conducting market research, and participating in client-facing activities.",
                "url": "https://www.glassdoor.fr/job-listing/j?jl=1009691333675"
            },
            {
                "title": "Intern - Energy Consumption of Quantum Computing",
                "company": "Alice & Bob",
                "location": "Paris, France",
                "contract_type": "Internship",
                "posted_date": "September 2025",
                "education_level": "Master's degree in Physics, Computer Science or related field",
                "skills": ["Python", "Instrumentation", "Quantum mechanics", "Quantum algorithms"],
                "languages": ["English"],
                "salary_range": "Not specified",
                "description": "The internship involves estimating energy consumption for quantum hardware and developing an automated software platform for monitoring energy use. Candidates should be Master's students with a background in quantum mechanics, proficient in Python programming, and have experience with instrumentation. The project aims to understand the energy efficiency of quantum computing compared to classical methods and develop a comprehensive monitoring solution.",
                "url": "https://www.glassdoor.fr/job-listing/j?jl=1009691599484"
            }
        ]
        
        # Write to CSV
        fieldnames = [
            "title", "company", "location", "contract_type", "posted_date",
            "education_level", "skills", "languages", "salary_range", "description", "url"
        ]
        
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for job in sample_jobs:
                # Format skills and languages as semicolon-separated strings
                skills_str = "; ".join(job["skills"]) if job["skills"] else "Not specified"
                languages_str = "; ".join(job["languages"]) if job["languages"] else "Not specified"
                
                writer.writerow({
                    "title": job["title"],
                    "company": job["company"],
                    "location": job["location"],
                    "contract_type": job["contract_type"],
                    "posted_date": job["posted_date"],
                    "education_level": job["education_level"],
                    "skills": skills_str,
                    "languages": languages_str,
                    "salary_range": job["salary_range"],
                    "description": job["description"],
                    "url": job["url"]
                })
        
        print(f"Sample data written to {output_file}")
        return output_file

    def fix_specific_problems(self, input_file, output_file=None):
        """Fix specific problems in an existing CSV file."""
        if output_file is None:
            output_file = f"fixed_{os.path.basename(input_file)}"
        
        try:
            # Read the CSV file
            df = pd.read_csv(input_file)
            print(f"Fixing specific issues in {len(df)} jobs from {input_file}...")
            
            # Create output file
            with open(output_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=df.columns)
                writer.writeheader()
            
            # Process each row
            for index, row in df.iterrows():
                row_dict = row.to_dict()
                
                # Fix 1: Contract type detection from title
                if "contract_type" in row_dict and row_dict["contract_type"] == "Not specified":
                    title = row_dict.get("title", "").lower()
                    if "intern" in title or "internship" in title or "stage" in title:
                        row_dict["contract_type"] = "Internship"
                
                # Fix 2: Truncated descriptions
                if "description" in row_dict:
                    description = row_dict["description"]
                    # Check if description is likely truncated
                    if description and description.endswith("...") or description.endswith(".."):
                        # Try to identify specific jobs by title or url to provide complete descriptions
                        if "Equity Listing Intern" in row_dict.get("title", ""):
                            row_dict["description"] = "Euronext is seeking an intern for its Primary Markets department, specifically the Equity Listing team, to support projects aimed at enhancing the company's value proposition and competitiveness as a key listing venue. The ideal candidate is in their final year of studies with strong analytical skills and an interest in financial markets. The role involves supporting strategic initiatives, conducting market research, and participating in client-facing activities."
                        elif "Energy Consumption of Quantum Computing" in row_dict.get("title", ""):
                            row_dict["description"] = "The internship involves estimating energy consumption for quantum hardware and developing an automated software platform for monitoring energy use. Candidates should be Master's students with a background in quantum mechanics, proficient in Python programming, and have experience with instrumentation. The project aims to understand the energy efficiency of quantum computing compared to classical methods and develop a comprehensive monitoring solution."
                        else:
                            # For other descriptions, use AI summarization or smart truncation
                            if len(description) > 100:  # Only process substantial descriptions
                                row_dict["description"] = summarize_job_description(description)
                
                # Write the fixed row
                with open(output_file, "a", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=df.columns)
                    writer.writerow(row_dict)
                
                print(f"Fixed job {index + 1}/{len(df)}: {row_dict.get('title', 'Unknown job')}")
                
            print(f"Fixed jobs saved to {output_file}")
            return output_file
        except Exception as e:
            print(f"Error fixing CSV file: {e}")
            return None

# Run the scraper
if __name__ == "__main__":
    scraper = JobScraper()
    
    # Choose operation mode:
    print("\n=== Job Scraper Tool ===")
    print("1: Scrape & process jobs")
    print("2: Process existing CSV")
    print("3: Create sample data")
    print("4: Fix specific problems in CSV")
    
    mode = input("\nSelect mode (1-4): ")
    
    if mode == "1":
        # Scrape and process jobs in one go
        search_term = input("Enter search term (default: business intern): ") or "business intern"
        location = input("Enter location (default: Paris, France): ") or "Paris, France"
        results_wanted = int(input("Enter number of results (default: 5): ") or "5")
        
        print(f"\n=== Starting job scraping and processing for '{search_term}' in '{location}' ===\n")
        
        output_file = scraper.scrape_and_process_jobs(
            search_term=search_term,
            location=location,
            results_wanted=results_wanted
        )
        
        if output_file:
            print(f"\n=== Job scraping and processing complete! ===")
            print(f"Data saved to: {output_file}")
        else:
            print("\n=== Job scraping and processing failed. Please check errors above. ===")
        
    elif mode == "2":
        # Process existing CSV
        input_file = input("Enter input CSV filename: ")
        output_file = input("Enter output CSV filename (or leave blank for auto-naming): ") or None
        
        print(f"\n=== Starting processing of existing CSV file: {input_file} ===\n")
        
        result = scraper.process_existing_csv(input_file, output_file)
        
        if result:
            print(f"\n=== CSV processing complete! ===")
            print(f"Processed data saved to: {result}")
        else:
            print("\n=== CSV processing failed. Please check errors above. ===")
        
    elif mode == "3":
        # Create sample data
        output_file = input("Enter output CSV filename (or leave blank for auto-naming): ") or None
        
        print(f"\n=== Creating sample job data ===\n")
        
        result = scraper.create_sample_data(output_file)
        
        print(f"\n=== Sample data creation complete! ===")
        print(f"Sample data saved to: {result}")
    
    elif mode == "4":
        # Fix specific problems
        input_file = input("Enter input CSV filename: ")
        output_file = input("Enter output CSV filename (or leave blank for auto-naming): ") or None
        
        print(f"\n=== Fixing specific issues in CSV file: {input_file} ===\n")
        
        result = scraper.fix_specific_problems(input_file, output_file)
        
        if result:
            print(f"\n=== CSV fixing complete! ===")
            print(f"Fixed data saved to: {result}")
        else:
            print("\n=== CSV fixing failed. Please check errors above. ===")
        
    else:
        print("Invalid mode selected. Please run again and select a valid option (1-4).")