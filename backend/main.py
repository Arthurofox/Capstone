from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os, json
import uuid
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import logging
import asyncio
import sys
import pinecone
import re

# Add the current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# Import custom modules
from app.resume_processor import ResumeProcessor
from app.rag_system import JobOfferRAG
from app.prompt_handler import CareerAssistantPromptHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Career Assistant API",
    description="API for career guidance, resume analysis, and job recommendations",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize a shared ChatOpenAI instance
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7, api_key=os.getenv("OPENAI_API_KEY"))

# Initialize Pinecone
pc = pinecone.Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

# Initialize components
resume_processor = ResumeProcessor()
job_offer_rag = JobOfferRAG()
prompt_handler = CareerAssistantPromptHandler(
    prompt_xml_path="app/prompts/career_assistant_prompt.xml"
)

# Create temp directory if it doesn't exist
os.makedirs("temp", exist_ok=True)

# In-memory store for chat history
chat_sessions = {}

# Pydantic models for request/response validation
class ChatMessage(BaseModel):
    content: str
    session_id: Optional[str] = None
    context: Optional[dict] = None

class ChatResponse(BaseModel):
    content: str
    session_id: str

class ResumeAnalysis(BaseModel):
    summary: str
    skills: List[str]
    recommendations: List[str]
    job_matches: Optional[List[Dict[str, Any]]] = None
    resume_id: Optional[str] = None

class JobSearchQuery(BaseModel):
    query: str
    limit: Optional[int] = 5

class JobSearchResponse(BaseModel):
    results: List[Dict[str, Any]]

class RAGEvaluationResult(BaseModel):
    average_time: float
    average_score: float
    query_results: List[Dict[str, Any]]

class ResumeJobMatchRequest(BaseModel):
    resume_id: str
    job_id: str

def format_job_results(results):
    """Format job search results into a readable message"""
    if not results:
        return "I couldn't find any matching job listings at the moment. Could you try a different search term or let me know more about what you're looking for?"
    
    response = "Here are some job recommendations based on your request:\n\n"
    
    for i, result in enumerate(results, 1):
        content = result.get("content", "").strip()
        if not content:
            continue
            
        # Extract job information using regex
        title_match = re.search(r"Title:\s*(.+?)(?:\n|$)", content)
        company_match = re.search(r"Company:\s*(.+?)(?:\n|$)", content)
        location_match = re.search(r"Location:\s*(.+?)(?:\n|$)", content)
        
        # Get values from matches or metadata
        title = title_match.group(1).strip() if title_match else result.get("metadata", {}).get("title", "")
        company = company_match.group(1).strip() if company_match else result.get("metadata", {}).get("company", "")
        location = location_match.group(1).strip() if location_match else result.get("metadata", {}).get("location", "")
        
        # Extract description
        description = ""
        desc_start = content.find("Description:")
        if desc_start != -1:
            desc_text = content[desc_start + len("Description:"):].strip()
            description = desc_text.split("\n\n")[0].strip()
        
        # Skip entries with empty title and company
        if not title and not company:
            continue
            
        # Build response
        response += f"**{i}. {title}**\n"
        
        if company and company != "N/A" and company != "":
            response += f"Company: {company}\n"
            
        if location and location != "N/A" and location != "":
            response += f"Location: {location}\n"
        
        if description:
            # Truncate to first 150 characters
            description_snippet = description[:150] + "..." if len(description) > 150 else description
            response += f"Description: {description_snippet}\n"
        
        response += "\n"
    
    # If we couldn't format any jobs, provide a fallback message
    if response == "Here are some job recommendations based on your request:\n\n":
        response = "I found some job listings, but couldn't extract their details properly. Please try a more specific search term."
    
    return response

@app.post("/api/chat", response_model=ChatResponse)
async def chat(message: ChatMessage):
    try:
        logger.info(f"Received message: {message.content}")
        
        # Get or create session
        session_id = message.session_id or str(uuid.uuid4())
        if session_id not in chat_sessions:
            chat_sessions[session_id] = []
        
        # Get chat history
        chat_history = chat_sessions[session_id]
        
        # Check if the message is asking for job recommendations
        job_phrases = ["job", "career", "position", "opening", "opportunity", "employment",
                      "hiring", "work", "vacancy", "recommend", "recommendation"]
        
        is_job_request = any(phrase in message.content.lower() for phrase in job_phrases)
        
        response_content = ""
        
        if is_job_request:
            # This looks like a job recommendation request, use the RAG system
            try:
                # Get job recommendations from the vector database
                results = job_offer_rag.search_similar_jobs(message.content, k=5)
                
                if results:
                    # Format the results into a nice response
                    response_content = format_job_results(results)
                else:
                    # No results found, fall back to the general response
                    response_content = await prompt_handler.generate_response(
                        user_input=message.content,
                        chat_history=chat_history
                    )
            except Exception as e:
                logger.error(f"Error in job recommendation: {str(e)}")
                # If there's an error, fall back to the general response
                response_content = await prompt_handler.generate_response(
                    user_input=message.content,
                    chat_history=chat_history
                )
        else:
            # Not a job request, use the regular prompt handler
            response_content = await prompt_handler.generate_response(
                user_input=message.content,
                chat_history=chat_history
            )
        
        # Update chat history
        chat_history.append({"role": "user", "content": message.content})
        chat_history.append({"role": "assistant", "content": response_content})
        
        # Limit chat history length to prevent token issues
        if len(chat_history) > 20:
            chat_history = chat_history[-20:]
        
        chat_sessions[session_id] = chat_history
        
        return ChatResponse(content=response_content, session_id=session_id)
    
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    

# Resume upload and analysis endpoint
@app.post("/api/resume/upload", response_model=ResumeAnalysis)
async def upload_resume(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    logger.info(f"File received: {file.filename}")
    temp_path = f"temp/{file.filename}"
    
    try:
        # Save file
        content = await file.read()
        with open(temp_path, "wb") as buffer:
            buffer.write(content)
        
        # Extract text from PDF
        resume_text = await resume_processor.extract_text_from_pdf(temp_path)
        
        # Store resume in vector database
        resume_id = await resume_processor.store_resume_in_vectordb(
            resume_text=resume_text,
            file_name=file.filename
        )
        
        # Analyze resume
        analysis = await resume_processor.analyze_resume(resume_text)
        
        # Find matching job offers using RAG
        try:
            job_matches = job_offer_rag.find_jobs_for_resume(resume_text)
            logger.info(f"Found {len(job_matches)} matching job offers")
        except Exception as e:
            logger.error(f"Error finding job matches: {str(e)}")
            # Return empty list if there's an error
            job_matches = []
        
        # Make sure required fields exist in the analysis
        if 'summary' not in analysis:
            analysis['summary'] = "Could not extract summary from resume."
        
        if 'skills' not in analysis or not isinstance(analysis['skills'], list):
            analysis['skills'] = []
            
        if 'recommendations' not in analysis or not isinstance(analysis['recommendations'], list):
            analysis['recommendations'] = []
        
        # Include job matches and resume ID in the response
        analysis['job_matches'] = job_matches
        analysis['resume_id'] = resume_id
        
        # Use background_tasks to clean up the temporary file after sending the response
        background_tasks.add_task(os.remove, temp_path)
        
        return analysis

    except Exception as e:
        logger.error(f"Error in resume upload: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
# Job search endpoint
@app.post("/api/jobs/search", response_model=JobSearchResponse)
async def search_jobs(query: JobSearchQuery):
    try:
        results = job_offer_rag.search_similar_jobs(query.query, k=query.limit)
        return JobSearchResponse(results=results)
    except Exception as e:
        logger.error(f"Error in job search: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Ingest job offers endpoint (admin use)
@app.post("/api/admin/ingest-jobs")
async def ingest_jobs():
    try:
        # This is an admin endpoint that should be secured in production
        csv_path = "dataset/combined_job_offers.csv"
        
        # Load and process job data synchronously for immediate feedback
        documents = job_offer_rag.load_and_process_job_data(csv_path)
        logger.info(f"Loaded {len(documents)} job offers from CSV")
        
        # Ingest documents
        job_offer_rag.ingest_documents(documents)
        
        return {
            "status": "success", 
            "message": f"Ingested {len(documents)} job offers into vector database"
        }
    except Exception as e:
        logger.error(f"Error in job ingestion: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Evaluate RAG system endpoint (admin use)
@app.post("/api/admin/evaluate-rag", response_model=RAGEvaluationResult)
async def evaluate_rag():
    try:
        # Test queries for evaluation
        test_queries = [
            "Data Scientist with Python experience",
            "Entry level marketing position",
            "Finance internship in Paris",
            "Remote software engineer job",
            "Project management role in consulting"
        ]
        
        # Evaluate RAG system
        results = job_offer_rag.evaluate_rag_performance(test_queries)
        
        return results
    except Exception as e:
        logger.error(f"Error in RAG evaluation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Match resume to specific job endpoint
@app.post("/api/resume/job-match")
async def match_resume_to_job(request: ResumeJobMatchRequest):
    try:
        # Get resume text
        resume_path = f"temp/{request.resume_id}.pdf"
        if not os.path.exists(resume_path):
            raise HTTPException(status_code=404, detail="Resume not found")
        
        resume_text = await resume_processor.extract_text_from_pdf(resume_path)
        
        # Get job description
        job_results = job_offer_rag.search_similar_jobs(f"id:{request.job_id}", k=1)
        if not job_results:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job_description = job_results[0]["content"]
        
        # Match resume to job
        match_result = await resume_processor.match_resume_to_job(resume_text, job_description)
        
        return match_result
    except Exception as e:
        logger.error(f"Error matching resume to job: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Initialize on startup
@app.on_event("startup")
async def startup_event():
    try:
        logger.info("Starting up the application")
        
        # Check the Pinecone indexes
        index_list = [index.name for index in pc.list_indexes()]
        logger.info(f"Available Pinecone indexes: {index_list}")
        
        # Add code to check if indexes are empty and warn if they are
        if job_offer_rag.INDEX_NAME in index_list:
            try:
                # Get a sample to see if there's data
                sample_results = job_offer_rag.search_similar_jobs("sample test query", k=1)
                if not sample_results:
                    logger.warning(f"Job offers index '{job_offer_rag.INDEX_NAME}' exists but may be empty. Please run /api/admin/ingest-jobs")
                else:
                    logger.info(f"Job offers index '{job_offer_rag.INDEX_NAME}' contains data")
            except Exception as e:
                logger.warning(f"Could not query job offers index: {str(e)}")
        else:
            logger.warning(f"Job offers index '{job_offer_rag.INDEX_NAME}' does not exist. Please run /api/admin/ingest-jobs")
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)