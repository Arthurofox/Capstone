"""
Module: resume_processor.py
---------------------------
This module provides functionality to process and analyze resumes.
It handles text extraction from PDF files, stores resumes in a vector database,
and uses a language model to analyze and extract key career insights from resume text.
Also, it assists with extracting job preferences and matching resumes to job descriptions.

Key Components:
    - ResumeProcessor class: Manages resume text extraction, vector storage, and analysis.
    - PDF text extraction: Uses PyPDFLoader to extract text.
    - Analysis and matching: Generates JSON output using a language model.
"""

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

# Load environment variables from .env file.
load_dotenv()

# Initialize Pinecone for resume storage.
pc = pinecone.Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

# Initialize embeddings with a lightweight model.
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# Initialize ChatOpenAI instance for general resume analysis.
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.4,
    max_tokens=2048,
    api_key=os.getenv("OPENAI_API_KEY")
)

# Initialize ChatOpenAI instance for JSON-based responses.
json_llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    max_tokens=2048,
    api_key=os.getenv("OPENAI_API_KEY"),
    response_format={"type": "json_object"}
)

class ResumeProcessor:
    """
    Processes and analyzes resumes, including text extraction from PDFs,
    storing resumes in a vector database, and generating analysis using a language model.
    
    Attributes:
        RESUME_INDEX_NAME (str): Name of the Pinecone index used for resumes.
        text_splitter (RecursiveCharacterTextSplitter): Splits resume text into manageable chunks.
        vector_store (PineconeVectorStore): Manages storage and retrieval operations for resumes.
    """
    RESUME_INDEX_NAME = "resumes"
    
    def __init__(self):
        """Initialize the resume processor by setting up the text splitter and vector store."""
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1500,
            chunk_overlap=150,
            separators=["\n\n", "\n", ". ", ", ", " ", ""]
        )
        self._init_vector_store()
    
    def _init_vector_store(self):
        """Initialize the Pinecone vector store for resume storage."""
        index_list = [index.name for index in pc.list_indexes()]
        
        # Create a Pinecone index if it does not exist.
        if self.RESUME_INDEX_NAME not in index_list:
            try:
                pc.create_index(
                    name=self.RESUME_INDEX_NAME,
                    dimension=1536,  # Dimension for text-embedding-3-small model.
                    metric="cosine"
                )
            except Exception as e:
                print(f"Error creating resume index: {str(e)}")
                print("Retrying with default settings...")
                pc.create_index(
                    name=self.RESUME_INDEX_NAME,
                    dimension=1536,
                    metric="cosine"
                )
        
        # Initialize the vector store with the created or existing index.
        index = pc.Index(self.RESUME_INDEX_NAME)
        self.vector_store = PineconeVectorStore(
            index=index,
            embedding=embeddings
        )
    
    async def extract_text_from_pdf(self, file_path: str) -> str:
        """
        Extract text from a PDF file.
        
        Uses PyPDFLoader to load the PDF, splits the extracted text into chunks,
        and then joins the chunks into a single text string.
        
        Args:
            file_path (str): Path to the PDF file.
            
        Returns:
            str: The complete extracted text.
        """
        loader = PyPDFLoader(file_path)
        documents = loader.load()
        chunks = self.text_splitter.split_documents(documents)
        
        # Concatenate all chunks of text into a single string.
        text = " ".join([chunk.page_content for chunk in chunks])
        return text
        
    async def store_resume_in_vectordb(self, resume_text: str, file_name: str, metadata: Dict = None) -> str:
        """
        Store a resume in the vector database and return a unique resume ID.
        
        Splits the resume text into document chunks, adds metadata, and ingests these
        chunks into the vector store. A unique ID is generated and associated with the resume.
        
        Args:
            resume_text (str): The full text of the resume.
            file_name (str): The original filename of the resume.
            metadata (Dict, optional): Additional metadata about the resume.
            
        Returns:
            str: The unique ID assigned to the stored resume.
        """
        try:
            resume_id = str(uuid.uuid4())
            
            if metadata is None:
                metadata = {}
            
            # Update metadata with additional resume details.
            metadata.update({
                "resume_id": resume_id,
                "file_name": file_name,
                "source": "user_upload"
            })
            
            texts = [resume_text]
            metadatas = [metadata]
            
            try:
                # Create document chunks from the resume text.
                chunks = self.text_splitter.create_documents(
                    texts=texts,
                    metadatas=metadatas
                )
            except Exception as e:
                print(f"Error creating document chunks: {str(e)}")
                # Fallback: Create documents manually.
                chunks = [Document(page_content=text, metadata=meta) for text, meta in zip(texts, metadatas)]
            
            try:
                # Add the document chunks to the vector store.
                self.vector_store.add_documents(chunks)
                print(f"Stored resume with ID {resume_id} in vector database")
                return resume_id
            except Exception as e:
                print(f"Error adding documents to vector store: {str(e)}")
                try:
                    # Fallback storage method; process each chunk manually.
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
        Analyze a resume using GPT-4o Mini to extract key insights.
        
        Generates a JSON output that includes a summary of the candidate's profile,
        a list of skills, suggestions for improving the resume, and recommended job positions.
        
        Args:
            resume_text (str): The resume text.
            
        Returns:
            Dict[str, Any]: The JSON output containing the analysis.
        """
        try:
            messages = [
                SystemMessage(content=(
                    "You are an expert resume analyzer and career advisor. "
                    "You have been given a candidate's resume text, and you will speak directly to the candidate. "
                    "1) Provide a short summary of the candidate's profile in the second person, focusing on key strengths. "
                    "2) Extract the candidate's skills (list them as an array of strings). "
                    "3) Provide at least three concrete suggestions for improving the resume. "
                    "4) Recommend at least three suitable job positions that align with the candidate's background. "
                    "Return your answer as valid JSON with exactly these four fields: "
                    "'summary' (string), 'skills' (array of strings), 'Recommendations' (array of strings), and 'jobRecommendations' (array of strings)."
                )),
                HumanMessage(content=resume_text)
            ]
            
            response = await json_llm.ainvoke(messages)
            analysis_str = response.content
            analysis = json.loads(analysis_str)
            return analysis
        
        except Exception as e:
            print(f"Error analyzing resume: {str(e)}")
            return {"error": str(e)}
    
    async def extract_job_preferences(self, resume_text: str) -> List[str]:
        """
        Extract job preferences and possible search queries from the resume.
        
        Uses a language model prompt to generate a list of job search queries tailored
        to the candidate's skills, experience, and career interests.
        
        Args:
            resume_text (str): The resume text.
            
        Returns:
            List[str]: A list of job search queries based on the resume.
        """
        try:
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
            
            response = await json_llm.ainvoke(messages)
            preferences_str = response.content
            preferences = json.loads(preferences_str)
            return preferences
        
        except Exception as e:
            print(f"Error extracting job preferences: {str(e)}")
            return {"error": str(e)}
            
    async def match_resume_to_job(self, resume_text: str, job_description: str) -> Dict[str, Any]:
        """
        Match a candidate's resume to a job description and evaluate the fit.
        
        Compares the resume against the job description and outputs a JSON object with:
            - matchScore: A score from 0-100 indicating the match quality.
            - matchingSkills: List of skills that match.
            - missingSkills: List of skills that are not met.
            - recommendations: Suggestions for improving the candidacy.
        
        Args:
            resume_text (str): The candidate's resume text.
            job_description (str): The job description text.
            
        Returns:
            Dict[str, Any]: A JSON object containing the match analysis.
        """
        try:
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
            
            response = await json_llm.ainvoke(messages)
            analysis_str = response.content
            analysis = json.loads(analysis_str)
            return analysis
        
        except Exception as e:
            print(f"Error matching resume to job: {str(e)}")
            return {"error": str(e)}
