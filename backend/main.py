# main.py
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from openai import AsyncOpenAI
import os, json
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter



# Define at the global level with other initializations
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200
)

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize OpenAI client
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"), http_client=None)

# Initialize embeddings and vector store
embeddings = OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))
vector_store = None
VECTOR_STORE_PATH = "vector_store"

# Create temp directory if it doesn't exist
os.makedirs("temp", exist_ok=True)

# Pydantic models for request/response validation
class ChatMessage(BaseModel):
    content: str
    context: Optional[dict] = None

class ResumeAnalysis(BaseModel):
    summary: str
    skills: List[str]
    recommendations: List[str]

# Chat endpoint
@app.post("/api/chat")
async def chat(message: ChatMessage):
    try:
        print("Received message:", message.content)  # Debug log
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an AI career advisor..."},
                {"role": "user", "content": message.content}
            ]
        )
        print("Response:", response.choices[0].message.content)  # Debug log
        return {"content": response.choices[0].message.content}
    except Exception as e:
        print("Error:", str(e))  # Debug log
        raise HTTPException(status_code=500, detail=str(e))
    
    
@app.post("/api/resume/upload", response_model=ResumeAnalysis)
async def upload_resume(file: UploadFile = File(...)):
    print(f"File received: {file.filename}")
    temp_path = f"temp/{file.filename}"
    
    try:
        content = await file.read()
        with open(temp_path, "wb") as buffer:
            buffer.write(content)
        
        loader = PyPDFLoader(temp_path)
        documents = loader.load()
        chunks = text_splitter.split_documents(documents)
        
        # Generate analysis using GPT with structured output
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system", 
                    "content": "Generate a JSON response with: {summary: string, skills: string[], recommendations: string[]}"
                },
                {"role": "user", "content": " ".join([chunk.page_content for chunk in chunks])}
            ],
            response_format={"type": "json_object"}
        )
        
        print("GPT Response:", response.choices[0].message.content)
        return json.loads(response.choices[0].message.content)

    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Initialize vector store on startup if it exists
@app.on_event("startup")
async def startup_event():
    global vector_store
    if os.path.exists(VECTOR_STORE_PATH):
        vector_store = FAISS.load_local(VECTOR_STORE_PATH, embeddings)

# Optionally add a health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)