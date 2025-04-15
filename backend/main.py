"""
PathFinder - Capstone Project: Career Assistant API
----------------------------------------------------

This script serves as the main entry point for the Career Assistant API. It integrates several services
to provide career guidance, resume analysis, job recommendations, and voice assistant capabilities.

Key Components:
    - FastAPI for asynchronous REST API development.
    - Pydantic for request and response data validation.
    - Integration with external services:
        • OpenAI's ChatOpenAI for language model responses.
        • Pinecone for vector database operations.
    - Custom modules for processing resumes, job recommendations (RAG system), prompt handling, formatting,
      and voice interactions.
      
The API provides endpoints for:
    - Session updates (attaching resume data to chat contexts).
    - Chat interactions with dynamic handling of job-related queries.
    - Uploading and analyzing resumes.
    - Searching for jobs.
    - Administrative operations for data ingestion and cleanup.
    - Voice assistant session initialization for real-time interactions.
    
Author: [Your Name]
Date: [Current Date]
"""

# =============================================================================
# Import Necessary Libraries and Modules
# =============================================================================

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os, json, uuid, re, time, asyncio, aiohttp, logging
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import pinecone

# Configure logging to capture errors and important logs during execution.
logging.basicConfig(level=logging.ERROR, handlers=[logging.StreamHandler()])
logger = logging.getLogger("VoiceAgentRTC")

# =============================================================================
# Import Custom Application Modules
# =============================================================================

from app.resume_processor import ResumeProcessor
from app.rag_system import JobOfferRAG
from app.prompt_handler import CareerAssistantPromptHandler
from app.formatters import format_job_results_html
from app.voice_agent import VoiceAgentRTC, webrtc_voice

# Load environment variables from a .env file for sensitive configurations such as API keys.
load_dotenv()

# =============================================================================
# Initialize FastAPI Application and Middleware
# =============================================================================

app = FastAPI(
    title="Career Assistant API",
    description="API for career guidance, resume analysis, and job recommendations",
    version="1.0.0"
)

# Enable Cross-Origin Resource Sharing (CORS) for specified origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# Initialize External Services and Helper Objects
# =============================================================================

# Instantiate the language model for generating responses.
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.6, api_key=os.getenv("OPENAI_API_KEY"))

# Initialize Pinecone vector database using the provided API key.
pc = pinecone.Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

# Instantiate custom modules for resume processing, job recommendations, and prompt handling.
resume_processor = ResumeProcessor()
job_offer_rag = JobOfferRAG()
prompt_handler = CareerAssistantPromptHandler(prompt_xml_path="app/prompts/career_assistant_prompt.xml")
voice_prompt_handler = CareerAssistantPromptHandler(prompt_xml_path="app/prompts/vocal_career_assistant_prompt.xml")

# Generate a system prompt for voice interactions from the voice prompt handler.
voice_instruction = voice_prompt_handler.create_system_prompt()

# =============================================================================
# Global Configurations and Data Structures
# =============================================================================

# Create a temporary directory for storing uploaded files (if it doesn't already exist).
os.makedirs("temp", exist_ok=True)

# A dictionary to keep track of chat sessions using session IDs.
chat_sessions = {}

# =============================================================================
# Define Pydantic Data Models for Request and Response Bodies
# =============================================================================

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

class SessionUpdateRequest(BaseModel):
    session_id: str
    resume_data: Optional[Dict[str, Any]] = None



# =============================================================================
# API Endpoints
# =============================================================================

@app.post("/api/session/update")
async def update_session(request: SessionUpdateRequest):
    """
    Update an existing chat session with resume data to provide personalized responses.
    
    - If the session does not exist, a new one is created.
    - If resume data is provided, it is added as a 'system' context message at the beginning of the session.
    
    This allows the language model to reference the user's background and skills during conversation.
    """
    try:
        if request.session_id not in chat_sessions:
            chat_sessions[request.session_id] = []
            
        if request.resume_data:
            resume_context = {
                "role": "system",
                "content": f"""
                The user has uploaded a resume with the following information:
                
                Summary: {request.resume_data.get('summary', 'Not available')}
                
                Skills: {', '.join(request.resume_data.get('skills', []))}
                
                Use this information to personalize your responses. Reference their skills 
                and background when relevant.
                """
            }
            chat_sessions[request.session_id].insert(0, resume_context)
            
        return {"status": "success", "message": "Session updated successfully"}
    except Exception as e:
        logger.error(f"Error in /api/session/update: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat", response_model=ChatResponse)
async def chat(message: ChatMessage):
    """
    Process a chat message from the user and generate an appropriate response.
    
    Determines if the message is a job-related query by scanning for specific job-related phrases.
    Depending on the query type, it either:
      - Attempts to retrieve matching job results and formats them for the user.
      - Or generates a response using the career assistant prompt handler.
    
    The conversation (both the user and assistant messages) is stored in the session history.
    The session history is also trimmed to ensure optimal performance.
    """
    try:
        session_id = message.session_id or str(uuid.uuid4())
        if session_id not in chat_sessions:
            chat_sessions[session_id] = []
        chat_history = chat_sessions[session_id]

        # Identify job-related queries using preset key phrases.
        job_phrases = ["job offers", "job listings", "find jobs", "search jobs", 
                       "internship offers", "intern offers", "job opportunities",
                       "show me jobs", "find internships"]
        is_job_request = any(phrase in message.content.lower() for phrase in job_phrases)
        
        response_content = ""
        if is_job_request:
            try:
                results = job_offer_rag.search_similar_jobs(message.content, k=5)
                if results:
                    response_content = format_job_results_html(results, llm)
                else:
                    response_content = await prompt_handler.generate_response(
                        user_input=message.content,
                        chat_history=chat_history
                    )
            except Exception:
                response_content = await prompt_handler.generate_response(
                    user_input=message.content,
                    chat_history=chat_history
                )
        else:
            response_content = await prompt_handler.generate_response(
                user_input=message.content,
                chat_history=chat_history
            )
        
        # Append current interaction to session history.
        chat_history.append({"role": "user", "content": message.content})
        chat_history.append({"role": "assistant", "content": response_content})
        
        # Trim chat history to keep the session context manageable.
        if len(chat_history) > 22:  # Allows for 20 visible messages plus up to 2 system messages.
            system_messages = [msg for msg in chat_history if msg["role"] == "system"]
            visible_messages = [msg for msg in chat_history if msg["role"] != "system"][-20:]
            chat_sessions[session_id] = system_messages + visible_messages
        else:
            chat_sessions[session_id] = chat_history
            
        return ChatResponse(content=response_content, session_id=session_id)
    except Exception as e:
        logger.error("Error in /api/chat: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/resume/upload", response_model=ResumeAnalysis)
async def upload_resume(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    Upload and process a resume document (PDF).
    
    The endpoint:
      - Saves the uploaded file temporarily.
      - Extracts text content from the file.
      - Stores the resume in a vector database.
      - Analyzes the resume to extract key data (summary, skills, recommendations).
      - Tries to match the resume with available job listings.
      - Cleans up by deleting the temporary file.
    """
    temp_path = f"temp/{file.filename}"
    try:
        content = await file.read()
        with open(temp_path, "wb") as buffer:
            buffer.write(content)
        resume_text = await resume_processor.extract_text_from_pdf(temp_path)
        resume_id = await resume_processor.store_resume_in_vectordb(
            resume_text=resume_text,
            file_name=file.filename
        )
        analysis = await resume_processor.analyze_resume(resume_text)
        try:
            job_matches = job_offer_rag.find_jobs_for_resume(resume_text)
        except Exception:
            job_matches = []
        if 'summary' not in analysis:
            analysis['summary'] = "Could not extract summary from resume."
        if 'skills' not in analysis or not isinstance(analysis['skills'], list):
            analysis['skills'] = []
        if 'recommendations' not in analysis or not isinstance(analysis['recommendations'], list):
            analysis['recommendations'] = []
        analysis['job_matches'] = job_matches
        analysis['resume_id'] = resume_id
        background_tasks.add_task(os.remove, temp_path)
        return analysis
    except Exception as e:
        logger.error("Error in /api/resume/upload: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/jobs/search", response_model=JobSearchResponse)
async def search_jobs(query: JobSearchQuery):
    """
    Search for job listings that are similar to the user's query.
    
    Leverages the job recommendation system to find and return a list of matching job offers.
    """
    try:
        results = job_offer_rag.search_similar_jobs(query.query, k=query.limit)
        return JobSearchResponse(results=results)
    except Exception as e:
        logger.error("Error in /api/jobs/search: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/ingest-jobs")
async def ingest_jobs():
    """
    Administrative endpoint to ingest job data from a CSV file into the vector database.
    
    Processes a CSV file containing job listings and stores the resulting documents for use by the job recommendation module.
    """
    try:
        csv_path = "dataset/processed_jobs_final.csv"
        documents = job_offer_rag.load_and_process_job_data(csv_path)
        job_offer_rag.ingest_documents(documents)
        return {
            "status": "success",
            "message": f"Ingested {len(documents)} job offers into vector database"
        }
    except Exception as e:
        logger.error("Error in /api/admin/ingest-jobs: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """
    Health check endpoint to confirm that the API service is operational.
    """
    return {"status": "healthy"}

@app.get("/session")
async def get_session():
    """
    Initializes a voice assistant session using the OpenAI real-time API.
    
    Constructs a payload with the required model, voice configuration, and system prompt instructions,
    then returns session details upon successful initialization.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY environment variable is not set")
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not set")

    url = "https://api.openai.com/v1/realtime/sessions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "gpt-4o-realtime-preview-2024-12-17",
        "voice": "alloy",
        "instructions": voice_instruction  # Use the voice-specific system prompt
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status != 200:
                    logger.error("Failed to fetch ephemeral token: %s", await response.text())
                    raise HTTPException(status_code=response.status, detail="Failed to fetch ephemeral token")
                return await response.json()
    except Exception as e:
        logger.error("Critical error in get_session: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.post("/api/admin/clear-jobs")
async def admin_clear_jobs():
    """
    Administrative endpoint to clear all job offer records from the vector database.
    """
    try:
        index = pc.Index(JobOfferRAG.INDEX_NAME)
        index.delete(delete_all=True)
        return {"status": "success", "message": "All job offers cleared from database"}
    except Exception as e:
        logger.error(f"Error clearing job database: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to clear job database: {str(e)}")

@app.post("/api/admin/clear-resumes")
async def admin_clear_resumes():
    """
    Administrative endpoint to clear all resume records from the vector database.
    """
    try:
        index = pc.Index(ResumeProcessor.RESUME_INDEX_NAME)
        index.delete(delete_all=True)
        return {"status": "success", "message": "All resumes cleared from database"}
    except Exception as e:
        logger.error(f"Error clearing resume database: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to clear resume database: {str(e)}")

# =============================================================================
# Voice Assistant Initialization and WebRTC Route
# =============================================================================

# Instantiate and start the voice agent for real-time interactions.
voice_agent = VoiceAgentRTC()
asyncio.ensure_future(voice_agent.connect())

# Register a WebRTC endpoint for voice interactions.
app.add_api_route("/webrtc/voice", webrtc_voice, methods=["POST"])

# =============================================================================
# Main Execution
# =============================================================================

# Start the API server using Uvicorn when executed as the main program.
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
