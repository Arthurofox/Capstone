# CLAUDE.md - Project Guide

## Commands
- Run app: `python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload`
- Install dependencies: `pip install -r requirements.txt`
- Generate requirements from .in: `pip-compile requirements.in`
- Update dependencies: `pip install -U -r requirements.txt`

## Code Style
- **Imports**: Group imports: stdlib, third-party, local (alphabetical order)
- **Naming**: snake_case for variables/functions, CamelCase for classes
- **Types**: Use type hints for function parameters and return values
- **Error Handling**: Use try/except blocks with specific exceptions
- **FastAPI**: Use Pydantic models for request/response validation
- **Documentation**: Docstrings for complex functions

## Project Structure
- `main.py`: Main FastAPI application
- API endpoints with async functions
- OpenAI integration for content processing
- FAISS vector store for document retrieval