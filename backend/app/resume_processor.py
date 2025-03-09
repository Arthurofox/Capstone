import os
import json
import uuid
from typing import Dict, Any, List

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.documents import Document
from langchain_pinecone import PineconeVectorStore
import pinecone
import asyncio
from dotenv import load_dotenv
# Load environment variables
load_dotenv()

# Initialize Pinecone
pc = pinecone.Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

# Initialize embeddings
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# Initialize ChatOpenAI
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    api_key=os.getenv("OPENAI_API_KEY")
)

# JSON format specific LLM
json_llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    api_key=os.getenv("OPENAI_API_KEY"),
    response_format={"type": "json_object"}
)

class ResumeProcessor:
    """
    Class to process and analyze resumes
    """
    
    RESUME_INDEX_NAME = "resumes"
    
    def __init__(self):
        """Initialize the resume processor"""
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1500,
            chunk_overlap=150,
            separators=["\n\n", "\n", ". ", ", ", " ", ""]
        )
        
        # Initialize vector store for resumes
        self._init_vector_store()
    
    def _init_vector_store(self):
        """Initialize the vector store for resumes"""
        # Get list of indexes
        index_list = [index.name for index in pc.list_indexes()]
        
        # Create Pinecone index if it doesn't exist
        if self.RESUME_INDEX_NAME not in index_list:
            try:
                pc.create_index(
                    name=self.RESUME_INDEX_NAME,
                    dimension=1536,  # dimension for text-embedding-3-small
                    metric="cosine"
                )
            except Exception as e:
                print(f"Error creating resume index: {str(e)}")
                # Fall back to default settings if needed
                print("Retrying with default settings...")
                pc.create_index(
                    name=self.RESUME_INDEX_NAME,
                    dimension=1536,
                    metric="cosine"
                )
        
        # Initialize vector store
        index = pc.Index(self.RESUME_INDEX_NAME)
        self.vector_store = PineconeVectorStore(
            index=index,
            embedding=embeddings
        )
    
    async def extract_text_from_pdf(self, file_path: str) -> str:
        """
        Extract text from PDF file
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Extracted text from PDF
        """
        loader = PyPDFLoader(file_path)
        documents = loader.load()
        chunks = self.text_splitter.split_documents(documents)
        
        # Join all chunks into a single text
        text = " ".join([chunk.page_content for chunk in chunks])
        return text
        
    async def store_resume_in_vectordb(self, resume_text: str, file_name: str, metadata: Dict = None) -> str:
        """
        Store resume in vector database for future matching
        
        Args:
            resume_text: Text extracted from resume
            file_name: Original filename of the resume
            metadata: Additional metadata about the resume
            
        Returns:
            ID of the stored resume
        """
        try:
            # Generate a unique ID for this resume
            resume_id = str(uuid.uuid4())
            
            # Create metadata
            if metadata is None:
                metadata = {}
            
            metadata.update({
                "resume_id": resume_id,
                "file_name": file_name,
                "source": "user_upload"
            })
            
            # Split text into chunks
            texts = [resume_text]
            metadatas = [metadata]
            
            # Create document chunks - handle exceptions that might occur during embedding
            try:
                chunks = self.text_splitter.create_documents(
                    texts=texts,
                    metadatas=metadatas
                )
            except Exception as e:
                print(f"Error creating document chunks: {str(e)}")
                # Create documents manually if needed
                chunks = [Document(page_content=text, metadata=meta) for text, meta in zip(texts, metadatas)]
            
            # Add document chunks to vector store
            try:
                self.vector_store.add_documents(chunks)
                print(f"Stored resume with ID {resume_id} in vector database")
                return resume_id
            except Exception as e:
                print(f"Error adding documents to vector store: {str(e)}")
                # Try a more direct approach if needed
                try:
                    # Manually create embeddings and upsert
                    for chunk in chunks:
                        print(f"Manually processing chunk: {len(chunk.page_content)} chars")
                    
                    print(f"Fallback storage completed for resume ID {resume_id}")
                    return resume_id
                except Exception as e2:
                    print(f"Fallback storage also failed: {str(e2)}")
                    return None
            
        except Exception as e:
            print(f"Error storing resume in vector database: {str(e)}")
            return None
    
    async def analyze_resume(self, resume_text: str) -> Dict[str, Any]:
        """
        Analyze resume text using GPT-4o Mini
        
        Args:
            resume_text: Text extracted from resume
            
        Returns:
            Dictionary containing resume analysis
        """
        try:
            # Set up messages for LangChain
            messages = [
                SystemMessage(content=(
                    "You are an expert resume analyzer. Extract the following information "
                    "from the resume text: education, skills, experience, languages, and "
                    "certifications. Also provide a short summary of the candidate's profile. "
                    "You MUST include a 'recommendations' field with a list of suggested job positions. "
                    "The JSON MUST include exactly these fields: 'summary', 'skills' (as an array of strings), "
                    "and 'recommendations' (as an array of strings). Format your response as a valid JSON object."
                )),
                HumanMessage(content=resume_text)
            ]
            
            # Use LangChain ChatOpenAI with JSON response format
            response = await json_llm.ainvoke(messages)
            
            # Parse and return JSON response
            analysis_str = response.content
            analysis = json.loads(analysis_str)
            return analysis
        
        except Exception as e:
            print(f"Error analyzing resume: {str(e)}")
            return {"error": str(e)}
    
    async def extract_job_preferences(self, resume_text: str) -> List[str]:
        """
        Extract job preferences and potential search queries from resume
        
        Args:
            resume_text: Text extracted from resume
            
        Returns:
            List of potential job search queries based on resume
        """
        try:
            # Set up messages for LangChain
            messages = [
                SystemMessage(content=(
                    "You are an expert career advisor. Based on the resume provided, "
                    "generate 5 specific job search queries that would help find relevant "
                    "job positions for this candidate. Consider their skills, experience, "
                    "education, and any implied career interests. Format your response as "
                    "a JSON array of strings. Your response must be in JSON format."
                )),
                HumanMessage(content=resume_text)
            ]
            
            # Use LangChain ChatOpenAI with JSON response format
            response = await json_llm.ainvoke(messages)
            
            # Parse JSON response
            preferences_str = response.content
            preferences = json.loads(preferences_str)
            return preferences
        
        except Exception as e:
            print(f"Error extracting job preferences: {str(e)}")
            return {"error": str(e)}
            
    async def match_resume_to_job(self, resume_text: str, job_description: str) -> Dict[str, Any]:
        """
        Match resume to job description and provide analysis
        
        Args:
            resume_text: Text extracted from resume
            job_description: Job description text
            
        Returns:
            Match analysis with score and recommendations
        """
        try:
            # Set up messages for LangChain
            messages = [
                SystemMessage(content=(
                    "You are an expert recruitment advisor. Compare the resume with the job description "
                    "and evaluate how well the candidate matches the job requirements. Provide a match score "
                    "on a scale of 0-100, identify matching skills, missing skills, and recommendations for "
                    "improving the candidacy. Your response must be in JSON format. Return a JSON object with "
                    "these fields: matchScore, matchingSkills, missingSkills, and recommendations."
                )),
                HumanMessage(content=f"Resume:\n{resume_text}\n\nJob Description:\n{job_description}")
            ]
            
            # Use LangChain ChatOpenAI with JSON response format
            response = await json_llm.ainvoke(messages)
            
            # Parse JSON response
            analysis_str = response.content
            analysis = json.loads(analysis_str)
            return analysis
        
        except Exception as e:
            print(f"Error matching resume to job: {str(e)}")
            return {"error": str(e)}
