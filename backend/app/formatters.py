"""
Module: formatters.py
---------------------
This module provides functions to process and format job listing results.
It includes functionality to generate a concise summary from a detailed job 
description using a language model and to format job results into an HTML 
table with descriptions.

Key Functions:
    - summarize_with_gpt: Summarizes a given text using the provided language model.
    - format_job_results_html: Formats a list of job listings into an HTML structure.
"""

import logging
from typing import List, Dict, Any
from langchain_openai import ChatOpenAI

# Configure module-level logger
logger = logging.getLogger(__name__)

def summarize_with_gpt(text: str, llm: ChatOpenAI) -> str:
    """
    Generate a concise summary of a job description using the language model.
    
    Constructs a prompt asking for a one-sentence summary of the provided text.
    If the summarization fails, it falls back to returning the first 150 characters 
    of the text with an ellipsis.
    
    Args:
        text (str): The detailed job description.
        llm (ChatOpenAI): Instance of ChatOpenAI used to generate the summary.
        
    Returns:
        str: A summarized version of the text.
    """
    prompt = f"Summarize the following job description in one short sentence:\n\n{text}"
    try:
        # Invoke the language model with the constructed prompt.
        return llm.invoke(prompt).content.strip()
    except Exception as e:
        # Log a warning and provide a fallback summary.
        logger.warning(f"[GPT-SUMMARY] Failed to summarize: {e}")
        return text[:150] + "..."

def format_job_results_html(results: List[Dict[str, Any]], llm: ChatOpenAI) -> str:
    """
    Format job listing results into an HTML table along with summarized descriptions.
    
    For each job listing, the function extracts metadata such as title, company, location,
    and URL to create table rows and also generates a summary of the job description using 
    the language model.
    
    Args:
        results (List[Dict[str, Any]]): List of job listing results.
        llm (ChatOpenAI): Instance of ChatOpenAI used for generating job description summaries.
    
    Returns:
        str: An HTML string containing a formatted table of job listings and their summaries.
    """
    if not results:
        return "<p>No job listings found for your request.</p>"

    # Lists to accumulate table row HTML and description summaries.
    table_rows = []
    descriptions = []

    for i, result in enumerate(results, 1):
        metadata = result.get("metadata", {})
        title = metadata.get("title", "—")
        company = metadata.get("company", "—")
        location = metadata.get("location", "—")
        url = metadata.get("url", "").strip()

        if not url:
            continue  # Skip job listings with no link provided.

        # Create a clickable link for the job posting.
        link = f'<a href="{url}" target="_blank" rel="noopener noreferrer">Apply</a>'

        # Append a table row with job details.
        table_rows.append(f"""
        <tr>
          <td>{i}</td>
          <td>{title}</td>
          <td>{company}</td>
          <td>{location}</td>
          <td>{link}</td>
        </tr>
        """)

        # Extract and process the job description from the content.
        content = result.get("content", "").strip()
        desc_start = content.find("Description:")
        description = content[desc_start + len("Description:"):].strip() if desc_start != -1 else content
        description = description.split("\n\n")[0].strip()

        # Summarize the description using the language model.
        summary = summarize_with_gpt(description, llm)
        descriptions.append(f"<li><strong>{i}.</strong> {summary}</li>")

    # If no rows were generated, inform the user.
    if not table_rows:
        return "<p>No job listings with usable links were found.</p>"

    # Return the complete HTML with the table and list of summaries.
    return f"""
    <p>Here are some job recommendations based on your request:</p>

    <table border="1" cellspacing="0" cellpadding="6" style="border-collapse: collapse; width: 100%;">
      <thead>
        <tr style="background-color: #f3f3f3;">
          <th>#</th>
          <th>Title</th>
          <th>Company</th>
          <th>Location</th>
          <th>Link</th>
        </tr>
      </thead>
      <tbody>
        {''.join(table_rows)}
      </tbody>
    </table>

    <p><strong>Descriptions:</strong></p>
    <ul>
      {''.join(descriptions)}
    </ul>
    """
    