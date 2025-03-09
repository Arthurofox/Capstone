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
# Load environment variables
load_dotenv()

# Initialize OpenAI embeddings
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# Initialize Pinecone
pc = pinecone.Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

class JobOfferRAG:
    """
    RAG system for job offers using Pinecone as vector store
    """
    INDEX_NAME = "job-offers"
    
    def __init__(self):
        """Initialize the RAG system"""
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100,
            separators=["\n\n", "\n", ". ", ", ", " ", ""]
        )
        
        # Get list of indexes
        index_list = [index.name for index in pc.list_indexes()]
        
        # Create Pinecone index if it doesn't exist
        if self.INDEX_NAME not in index_list:
            try:
                pc.create_index(
                    name=self.INDEX_NAME,
                    dimension=1536,  # dimension for text-embedding-3-small
                    metric="cosine"
                )
            except Exception as e:
                print(f"Error creating index: {str(e)}")
                # Try again without spec if it fails
                print("Retrying with default settings...")
                pc.create_index(
                    name=self.INDEX_NAME,
                    dimension=1536,
                    metric="cosine"
                )
        
        # Initialize vector store
        index = pc.Index(self.INDEX_NAME)
        self.vector_store = PineconeVectorStore(
            index=index,
            embedding=embeddings
        )
    
    def load_and_process_job_data(self, csv_path: str) -> List[Document]:
        """
        Load job offers from CSV and convert to Documents
        
        Args:
            csv_path: Path to the CSV file containing job offers
            
        Returns:
            List of Document objects
        """
        # Read CSV file
        df = pd.read_csv(csv_path)
        
        # Process each job offer row
        documents = []
        for _, row in df.iterrows():
            # Handle NaN values and clean data
            clean_row = {k: ('' if pd.isna(v) else str(v)) for k, v in row.items()}
            
            # Skip rows with missing essential information
            if not clean_row.get('title') or not clean_row.get('company'):
                continue
            
            # Create structured content from row data
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
            
            # Create metadata (cleaning any NaN values)
            metadata = {
                "title": clean_row.get('title', ''),
                "company": clean_row.get('company', ''),
                "location": clean_row.get('location', ''),
                "contract_type": clean_row.get('contract_type', ''),
                "education_level": clean_row.get('education_level', ''),
                "skills": clean_row.get('skills', ''),
                "url": clean_row.get('url', '')
            }
            
            # Create Document object
            doc = Document(page_content=content, metadata=metadata)
            documents.append(doc)
        
        return documents
    
    def ingest_documents(self, documents: List[Document]) -> None:
        """
        Split documents into chunks and add to vector store
        
        Args:
            documents: List of Document objects to ingest
        """
        # Split documents into chunks
        chunks = self.text_splitter.split_documents(documents)
        
        # Add to vector store
        self.vector_store.add_documents(chunks)
        
        print(f"Ingested {len(chunks)} chunks from {len(documents)} job offers")
    
    def search_similar_jobs(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Search for similar job offers based on query
        
        Args:
            query: Search query
            k: Number of results to return
            
        Returns:
            List of similar job offers with metadata
        """
        # Check if it's a domain-specific search (like finance)
        finance_keywords = ['finance', 'financial', 'banking', 'investment', 'accounting', 'trader', 'analyst']
        is_finance_query = any(keyword in query.lower() for keyword in finance_keywords)
        
        # Boost the search results if it's finance-related
        search_k = k * 2 if is_finance_query else k
        
        # Search vector store
        results = self.vector_store.similarity_search_with_score(query, k=search_k)
        
        # Filter and format results
        formatted_results = []
        for doc, score in results:
            # Skip empty content
            if not doc.page_content.strip():
                continue
                
            # For finance queries, prioritize finance-related jobs
            if is_finance_query:
                title = doc.metadata.get('title', '').lower()
                content = doc.page_content.lower()
                is_finance_job = any(keyword in title or keyword in content for keyword in finance_keywords)
                
                # If it's not a finance job and we have enough results, skip it
                if not is_finance_job and len(formatted_results) >= k:
                    continue
            
            formatted_results.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": score
            })
        
        # Limit to k results
        return formatted_results[:k]
    
    def find_jobs_for_resume(self, resume_text: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Find suitable job offers based on resume text
        
        Args:
            resume_text: Text extracted from resume
            k: Number of results to return
            
        Returns:
            List of job offers matching resume
        """
        # Extract key terms from resume to enhance search
        key_terms = []
        
        # Check for finance-related terms
        finance_terms = ['finance', 'financial', 'banking', 'investment', 'accounting', 
                         'trader', 'analyst', 'budget', 'treasury', 'audit']
        
        for term in finance_terms:
            if term in resume_text.lower():
                key_terms.append(term)
        
        # Create enhanced query using key terms
        if key_terms:
            enhanced_query = f"{' '.join(key_terms)} {resume_text[:1000]}"
            return self.search_similar_jobs(enhanced_query, k=k)
        else:
            # Use resume text as query if no key terms found
            return self.search_similar_jobs(resume_text[:1000], k=k)
    
    def evaluate_rag_performance(self, test_queries: List[str]) -> Dict[str, Any]:
        """
        Evaluate RAG system performance using test queries
        
        Args:
            test_queries: List of test queries
            
        Returns:
            Performance metrics
        """
        results = {}
        
        # Measure average retrieval time and relevance scores
        total_time = 0
        total_scores = 0
        query_results = []
        
        for query in test_queries:
            # Search for similar jobs
            import time
            start_time = time.time()
            search_results = self.search_similar_jobs(query, k=3)
            end_time = time.time()
            
            # Calculate metrics
            query_time = end_time - start_time
            avg_score = sum(result["score"] for result in search_results) / len(search_results) if search_results else 0
            
            total_time += query_time
            total_scores += avg_score
            
            query_results.append({
                "query": query,
                "time": query_time,
                "avg_score": avg_score,
                "results": search_results
            })
        
        # Calculate overall metrics
        avg_time = total_time / len(test_queries) if test_queries else 0
        avg_score = total_scores / len(test_queries) if test_queries else 0
        
        results = {
            "average_time": avg_time,
            "average_score": avg_score,
            "query_results": query_results
        }
        
        return results