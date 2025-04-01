import logging
from typing import List, Dict, Any
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

def summarize_with_gpt(text: str, llm: ChatOpenAI) -> str:
    prompt = f"Summarize the following job description in one short sentence:\n\n{text}"
    try:
        return llm.invoke(prompt).content.strip()
    except Exception as e:
        logger.warning(f"[GPT-SUMMARY] Failed to summarize: {e}")
        return text[:150] + "..."

def format_job_results_html(results: List[Dict[str, Any]], llm: ChatOpenAI) -> str:
    if not results:
        return "<p>No job listings found for your request.</p>"

    table_rows = []
    descriptions = []

    for i, result in enumerate(results, 1):
        metadata = result.get("metadata", {})
        title = metadata.get("title", "—")
        company = metadata.get("company", "—")
        location = metadata.get("location", "—")
        url = metadata.get("url", "").strip()

        if not url:
            continue  # Skip if no link

        link = f'<a href="{url}" target="_blank" rel="noopener noreferrer">Apply</a>'

        table_rows.append(f"""
        <tr>
          <td>{i}</td>
          <td>{title}</td>
          <td>{company}</td>
          <td>{location}</td>
          <td>{link}</td>
        </tr>
        """)

        content = result.get("content", "").strip()
        desc_start = content.find("Description:")
        description = content[desc_start + len("Description:"):].strip() if desc_start != -1 else content
        description = description.split("\n\n")[0].strip()

        summary = summarize_with_gpt(description, llm)
        descriptions.append(f"<li><strong>{i}.</strong> {summary}</li>")

    if not table_rows:
        return "<p>No job listings with usable links were found.</p>"

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
