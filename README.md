

```markdown
# PathFinder: Your AI-Powered Career Companion

![PathFinder Logo](/public/background.png)

PathFinder is an intelligent, multi-modal career assistant designed to guide users through the uncertainties of early career development. Our system—driven by the persona "Sophia"—leverages cutting-edge language models, semantic vector search, and real-time voice interaction to provide personalized resume evaluations, job matching, and interview preparation.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture & Technologies](#architecture--technologies)
- [Installation & Setup](#installation--setup)
  - [Frontend Setup](#frontend-setup)
  - [Backend Setup](#backend-setup)
  - [Docker Deployment](#docker-deployment)
- [Usage](#usage)
- [Evaluation & Future Improvements](#evaluation--future-improvements)
- [References](#references)

---

## Overview

Modern job seekers face tremendous uncertainty—high competition, unclear career paths, and stress during interviews or resume crafting. PathFinder was developed to transform this experience by offering a conversational, empathetic, and intelligent career companion:

- **Personalized Resume Evaluation:** Analyze uploaded resumes to extract key skills, generate personalized improvement suggestions, and suggest matching roles.
- **Semantic Job Matching:** Utilize a retrieval-augmented generation (RAG) pipeline that leverages Pinecone vector search and GPT-4o-mini for relevant job recommendations.
- **Real-Time Interview Simulation:** Engage in voice-based mock interviews using WebRTC for a natural conversation with Sophia.
- **Career Planning Guidance:** Get actionable advice, practical tips, and supportive insights to ease the transition from academia to the professional world.

---

## Features

| Feature                     | PathFinder (Sophia)                | Generic Chatbot    | Traditional Career Portal |
| --------------------------- | ---------------------------------- | ------------------ | ------------------------- |
| **Personalization**         | High – resume & context-aware      | Medium – prompt-based | Medium – profile-based    |
| **Emotional Intelligence**  | Empathetic, stress-reducing tone   | Basic              | N/A                       |
| **Mock Interview Simulation** | Voice/text, role-specific         | Basic Q&A only     | N/A                       |
| **Resume Evaluation**       | AI-structured review with file parsing | Tips only       | N/A                       |
| **Semantic Job Matching**   | RAG pipeline using vector search   | None               | Tag/keyword-based         |
| **Real-Time Voice Chat**    | Yes (via WebRTC)                   | No                 | No                        |

---

## Architecture & Technologies

PathFinder is built as a modular system that seamlessly integrates multiple components:

- **Backend:** FastAPI microservices managing RESTful endpoints for chat, resume processing, job ingestion, and voice interactions.
- **Language Model:** OpenAI GPT-4o-mini (with enforced response formats) for natural language understanding and generation.
- **Vector Search:** Pinecone vector database with LangChain integration for semantic job matching.
- **Frontend:** React, TailwindCSS, and TypeScript—creating a calming, minimalist UI complemented by optional lofi background music.
- **Voice Interaction:** WebRTC implemented via aiortc for real-time, bi-directional audio communication.

Each subsystem (resume ingestion, job matching, prompt handling, and voice interaction) is loosely coupled, ensuring scalability and ease of future upgrades.

---

## Installation & Setup

Follow these steps to get your development environment up and running.

### Frontend Setup

1. **Clean Slate Setup:**
   ```bash
   npm cache clean --force
   rm -rf node_modules package-lock.json
   npm install
   ```
2. **Start the Frontend Development Server:**
   ```bash
   npm run dev
   ```
3. **Access the Application:**
   Open your browser at [http://localhost:3000](http://localhost:3000)

### Backend Setup

1. **Change Directory:**
   ```bash
   cd backend
   ```
2. **Create and Activate a Virtual Environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. **Set Environment Variables:**  
   Create a `.env` file and add your OpenAI API key (and any other required variables).

4. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
5. **Run the Backend Server:**
   ```bash
   uvicorn main:app --reload
   ```

### Docker Deployment

1. **Navigate to the Docker Directory:**
   ```bash
   cd docker
   ```
2. **Build and Run Docker Containers:**
   ```bash
   docker compose -f docker/docker-compose.yml up --build
   ```
   _Ensure Docker is running in the background._

---

## Usage

Once both the frontend and backend servers are running, you can interact with PathFinder via the web interface at [http://localhost:3000](http://localhost:3000). Upload your resume, chat with Sophia, or start a voice-based interview simulation to experience the full capabilities of the AI assistant.

---

## Evaluation & Future Improvements

### Evaluation Highlights

- **Resume Processing:**  
  Validate speed, skill extraction accuracy, and actionable resume feedback using internal test scenarios.

- **Job Matching:**  
  Assess the relevance of job recommendations based on semantic similarity and manually review output for coherence.

- **Voice Interaction:**  
  Verify session initialization, real-time performance, and natural conversational flow.

### Future Roadmap

- **Integrations:**  
  Real-time profile syncing via LinkedIn and GitHub APIs, and an in-app AI-powered resume builder.

- **User Experience Enhancements:**  
  Customizable avatars and voice options for Sophia, improved dashboard for job tracking, and extended UI personalization.

- **Research & Ethical Oversight:**  
  Longitudinal studies in university settings and periodic ethical audits to ensure fairness, bias detection, and data privacy.


---

## Conclusion

PathFinder is more than just a tool—it’s a holistic, empathetic AI platform that transforms the career development journey. By combining robust resume analytics, semantic job matching via a RAG pipeline, and real-time voice interactions, Sophia serves as a true companion for early-career professionals. With continued refinement, real-world testing, and ethical scaling, PathFinder will empower job seekers to confidently navigate their career paths.

---