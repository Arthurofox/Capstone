from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os, json, uuid, re, time, asyncio, aiohttp, logging
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import pinecone

logging.basicConfig(level=logging.ERROR, handlers=[logging.StreamHandler()])
logger = logging.getLogger("VoiceAgentRTC")

from app.resume_processor import ResumeProcessor
from app.rag_system import JobOfferRAG
from app.prompt_handler import CareerAssistantPromptHandler
from app.formatters import format_job_results_html
from app.voice_agent import VoiceAgentRTC, webrtc_voice

load_dotenv()

app = FastAPI(
    title="Career Assistant API",
    description="API for career guidance, resume analysis, and job recommendations",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7, api_key=os.getenv("OPENAI_API_KEY"))
pc = pinecone.Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

resume_processor = ResumeProcessor()
job_offer_rag = JobOfferRAG()
prompt_handler = CareerAssistantPromptHandler(prompt_xml_path="app/prompts/career_assistant_prompt.xml")

# Get the prompt from the handler (assuming it has a method or attribute to access the raw prompt)
# If generate_response is async and needs input, we'll call it with a dummy input
async def get_voice_prompt():
    # Simplest approach: use generate_response with empty input to get the base prompt
    prompt = await prompt_handler.generate_response(user_input="", chat_history=[])
    return prompt

# Run async function to get prompt at startup
loop = asyncio.get_event_loop()
voice_instruction = loop.run_until_complete(get_voice_prompt())

os.makedirs("temp", exist_ok=True)
chat_sessions = {}

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
    if not results:
        return "I couldn't find any matching job listings at the moment. Please try a different search term."
    response = "Here are some job recommendations based on your request:\n\n"
    for i, result in enumerate(results, 1):
        content = result.get("content", "").strip()
        if not content:
            continue
        title_match = re.search(r"Title:\s(.+?)(?:\n|$)", content)
        company_match = re.search(r"Company:\s(.+?)(?:\n|$)", content)
        location_match = re.search(r"Location:\s(.+?)(?:\n|$)", content)
        title = title_match.group(1).strip() if title_match else result.get("metadata", {}).get("title", "")
        company = company_match.group(1).strip() if company_match else result.get("metadata", {}).get("company", "")
        location = location_match.group(1).strip() if location_match else result.get("metadata", {}).get("location", "")
        description = ""
        desc_start = content.find("Description:")
        if desc_start != -1:
            desc_text = content[desc_start + len("Description:"):].strip()
            description = desc_text.split("\n\n")[0].strip()
        if not title and not company:
            continue
        response += f"{i}. {title}\n"
        if company and company != "N/A":
            response += f"Company: {company}\n"
        if location and location != "N/A":
            response += f"Location: {location}\n"
        if description:
            description_snippet = description[:150] + "..." if len(description) > 150 else description
            response += f"Description: {description_snippet}\n"
        response += "\n"
    if response == "Here are some job recommendations based on your request:\n\n":
        response = "I found some job listings, but couldn't extract their details properly."
    return response

@app.post("/api/chat", response_model=ChatResponse)
async def chat(message: ChatMessage):
    try:
        session_id = message.session_id or str(uuid.uuid4())
        if session_id not in chat_sessions:
            chat_sessions[session_id] = []
        chat_history = chat_sessions[session_id]
        job_phrases = ["job", "career", "position", "opening", "opportunity", "employment",
                       "hiring", "work", "vacancy", "recommend", "recommendation",
                       "internship", "intern", "trainee", "stage"]
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
        chat_history.append({"role": "user", "content": message.content})
        chat_history.append({"role": "assistant", "content": response_content})
        if len(chat_history) > 20:
            chat_history = chat_history[-20:]
        chat_sessions[session_id] = chat_history
        return ChatResponse(content=response_content, session_id=session_id)
    except Exception as e:
        logger.error("Error in /api/chat: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/resume/upload", response_model=ResumeAnalysis)
async def upload_resume(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
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
    try:
        results = job_offer_rag.search_similar_jobs(query.query, k=query.limit)
        return JobSearchResponse(results=results)
    except Exception as e:
        logger.error("Error in /api/jobs/search: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/ingest-jobs")
async def ingest_jobs():
    try:
        csv_path = "dataset/combined_job_offers.csv"
        documents = job_offer_rag.load_and_process_job_data(csv_path)
        job_offer_rag.ingest_documents(documents)
        return {
            "status": "success",
            "message": f"Ingested {len(documents)} job offers into vector database"
        }
    except Exception as e:
        logger.error("Error in /api/admin/ingest-jobs: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/evaluate-rag", response_model=RAGEvaluationResult)
async def evaluate_rag():
    try:
        test_queries = [
            "Data Scientist with Python experience",
            "Entry level marketing position",
            "Finance internship in Paris",
            "Remote software engineer job",
            "Project management role in consulting"
        ]
        results = job_offer_rag.evaluate_rag_performance(test_queries)
        return results
    except Exception as e:
        logger.error("Error in /api/admin/evaluate-rag: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/resume/job-match")
async def match_resume_to_job(request: ResumeJobMatchRequest):
    try:
        resume_path = f"temp/{request.resume_id}.pdf"
        if not os.path.exists(resume_path):
            raise HTTPException(status_code=404, detail="Resume not found")
        resume_text = await resume_processor.extract_text_from_pdf(resume_path)
        job_results = job_offer_rag.search_similar_jobs(f"id:{request.job_id}", k=1)
        if not job_results:
            raise HTTPException(status_code=404, detail="Job not found")
        job_description = job_results[0]["content"]
        match_result = await resume_processor.match_resume_to_job(resume_text, job_description)
        return match_result
    except Exception as e:
        logger.error("Error in /api/resume/job-match: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/session")
async def get_session():
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
        "instructions": voice_instruction  # Use the prompt from handler
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

voice_agent = VoiceAgentRTC()
asyncio.ensure_future(voice_agent.connect())
app.add_api_route("/webrtc/voice", webrtc_voice, methods=["POST"])

@app.on_event("startup")
async def startup_event():
    pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)