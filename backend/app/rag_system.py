"""
Module: rag_system.py
---------------------
This module implements a Retrieval-Augmented Generation (RAG) system for job offers using
Pinecone as a vector store. It loads job offer data from CSV files, processes each row into
a Document, ingests the resulting document chunks into the vector database, and then enables
a semantic similarity search to retrieve relevant job offers.

Key Components:
    - Loading and processing job offer data from CSV.
    - Splitting long job descriptions into manageable chunks.
    - Ingesting document chunks into a Pinecone vector store.
    - Performing a similarity search based solely on the input query or resume text.
"""

import os
import re
import pandas as pd
from typing import List, Dict, Any
from dotenv import load_dotenv
import pinecone
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_pinecone import PineconeVectorStore

# Load environment variables from the .env file.
load_dotenv()

# Initialize OpenAI embeddings using a lightweight embedding model.
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# Initialize Pinecone with the API key provided in the environment.
pc = pinecone.Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

class JobOfferRAG:
    """
    A domain-agnostic RAG system for job offers using Pinecone as the vector store.

    This class handles:
      - Loading and processing job offer data from a CSV file.
      - Splitting the job offer texts into chunks using a recursive text splitter.
      - Ingesting these chunks into a Pinecone vector store.
      - Performing a semantic similarity search based solely on the query or resume text,
        leveraging the underlying embeddings.

    Attributes:
        INDEX_NAME (str): The name of the Pinecone index that stores job offers.
        text_splitter (RecursiveCharacterTextSplitter): Used to split job offer texts into chunks.
        vector_store (PineconeVectorStore): Interface for adding documents and performing similarity searches.
    """
    INDEX_NAME = "job-offers"
    
    def __init__(self):
        """Initialize the RAG system by setting up the text splitter and vector store."""
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100,
            separators=["\n\n", "\n", ". ", ", ", " ", ""]
        )
        
        # Get existing index names from Pinecone.
        index_list = [index.name for index in pc.list_indexes()]
        
        # Create the index if it does not exist.
        if self.INDEX_NAME not in index_list:
            try:
                pc.create_index(
                    name=self.INDEX_NAME,
                    dimension=1536,  # Dimension for the "text-embedding-3-small" model.
                    metric="cosine"
                )
            except Exception as e:
                print(f"Error creating index: {str(e)}")
                print("Retrying with default settings...")
                pc.create_index(
                    name=self.INDEX_NAME,
                    dimension=1536,
                    metric="cosine"
                )
        
        # Initialize the vector store with the created or existing index.
        index = pc.Index(self.INDEX_NAME)
        self.vector_store = PineconeVectorStore(
            index=index,
            embedding=embeddings
        )
    
    def load_and_process_job_data(self, csv_path: str) -> List[Document]:
        """
        Load job offers from a CSV file and convert each row into a Document object.
        
        The CSV is expected to have columns such as:
          title, company, location, contract_type, posted_date, education_level, 
          skills, languages, salary_range, description, and url.
        
        Args:
            csv_path (str): Path to the CSV file containing job offers.
        
        Returns:
            List[Document]: A list of Document objects representing the job offers.
        """
        # Read CSV file into a DataFrame.
        df = pd.read_csv(csv_path)
        documents = []
        
        # Process each row from the CSV.
        for _, row in df.iterrows():
            # Replace NaN values with empty strings.
            clean_row = {k: ('' if pd.isna(v) else str(v)) for k, v in row.items()}
            
            # Skip rows missing essential information like title or company.
            if not clean_row.get('title') or not clean_row.get('company'):
                continue
            
            # Create a structured multi-line string with job offer details.
            content = f"""
            Title: {clean_row.get('title', '')}
            Company: {clean_row.get('company', '')}
            Location: {clean_row.get('location', '')}
            Contract Type: {clean_row.get('contract_type', '')}
            Posted Date: {clean_row.get('posted_date', '')}
            Education Level: {clean_row.get('education_level', '')}
            Skills: {clean_row.get('skills', '')}
            Languages: {clean_row.get('languages', '')}
            Salary Range: {clean_row.get('salary_range', '')}
            
            Description:
            {clean_row.get('description', '')}
            
            URL: {clean_row.get('url', '')}
            """
            
            # Create metadata with selected fields.
            metadata = {
                "title": clean_row.get('title', ''),
                "company": clean_row.get('company', ''),
                "location": clean_row.get('location', ''),
                "contract_type": clean_row.get('contract_type', ''),
                "education_level": clean_row.get('education_level', ''),
                "skills": clean_row.get('skills', ''),
                "url": clean_row.get('url', '')
            }
            
            # Create and append a Document object.
            doc = Document(page_content=content, metadata=metadata)
            documents.append(doc)
        
        return documents
    
    def ingest_documents(self, documents: List[Document]) -> None:
        """
        Split the provided documents into smaller text chunks and ingest them into the vector store.
        
        Args:
            documents (List[Document]): List of Document objects to ingest.
        """
        chunks = self.text_splitter.split_documents(documents)
        self.vector_store.add_documents(chunks)
        print(f"Ingested {len(chunks)} chunks from {len(documents)} job offers")
    
    def search_similar_jobs(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Perform a similarity search for job offers based solely on the given query.
        
        This function relies on the semantic similarity provided by the vector store,
        returning job offers that are most similar to the input query.
        
        Args:
            query (str): The search query.
            k (int): The number of results to return (default is 5).
        
        Returns:
            List[Dict[str, Any]]: A list of job offer results with associated metadata and scores.
        """
        results = self.vector_store.similarity_search_with_score(query, k=k)
        formatted_results = []
        
        # Format the results by checking that content exists.
        for doc, score in results:
            if not doc.page_content.strip():
                continue
            formatted_results.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": score
            })
        
        return formatted_results[:k]
    
    def find_jobs_for_resume(self, resume_text: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Find suitable job offers based on a candidate's resume text.
        
        The function directly uses the resume text as the query, allowing the underlying
        vector store to retrieve semantically similar job offers.
        
        Args:
            resume_text (str): The text extracted from the candidate's resume.
            k (int): The number of job offers to return (default is 5).
        
        Returns:
            List[Dict[str, Any]]: A list of job offers matching the resume.
        """
        return self.search_similar_jobs(resume_text, k=k)
