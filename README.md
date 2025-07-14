# Interview Preparation Assistant

An advanced AI-powered interview preparation system that generates personalized interview questions based on resumes, provides real-time speech and answer feedback, adapts question difficulty using reinforcement learning, and offers resume strengthening suggestions.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [System Architecture](#system-architecture)
- [Installation](#installation)
- [Usage](#usage)
- [API Endpoints](#api-endpoints)
- [Voice Analysis](#voice-recording--speech-analysis)
- [RAG Evaluation System](#rag-evaluation-system)
- [Reinforcement Learning](#reinforcement-learning)
- [Frontend](#frontend)
- [Development](#development)
- [Technologies Used](#technologies-used)

## Overview

Interview Preparation Assistant is a comprehensive interview preparation tool designed to help candidates practice for HR interviews. The system analyzes uploaded resumes, generates relevant interview questions, evaluates candidate responses using both RAG and traditional LLM approaches, analyzes speech patterns for confidence assessment, and provides personalized feedback and resume improvement suggestions.

## Features

### Core Functionality
- **Resume Analysis**: Upload your resume for personalized interview questions
- **Customizable Difficulty Levels**: Choose between Easy, Medium, or Hard interview questions
- **Dynamic Difficulty Adjustment**: Questions adapt to your performance using reinforcement learning
- **Real-time Answer Evaluation**: Get scored feedback on your interview responses
- **RAG-Enhanced Evaluation**: Context-aware answer scoring using Retrieval-Augmented Generation
- **Resume Strengthening Suggestions**: Receive actionable tips to improve your resume
- **Interactive Chat Interface**: Practice interviews in a realistic chat environment

### Speech Analysis
- **Voice Input Support**: Answer questions using voice recording and transcription
- **Filler Word Detection**: Identification and counting of common filler words
- **Speaking Rate Analysis**: Words per minute (WPM) calculation
- **Confidence Scoring**: Based on speech patterns and clarity
- **Personalized Speech Feedback**: Suggestions to improve speaking confidence

### Advanced Features
- **Multi-model Evaluation**: Combines results from multiple LLM evaluations
- **Automated Evaluation Pipeline**: Testing and comparison of different evaluation approaches
- **Performance Visualization**: Charts comparing RAG vs non-RAG evaluation performance
- **Final Interview Summary**: Comprehensive feedback at the end of the interview
- **Multi-threading Performance**: Parallel processing for faster response times

## System Architecture

```
┌─────────────┐     ┌─────────────────┐     ┌──────────────────┐
│  Frontend   │◄───►│     Backend     │◄───►│  Speech Analysis │
│   (React)   │     │     (Flask)     │     │       Module     │
└─────────────┘     └─────────────────┘     └──────────────────┘
                            ▲
                ┌───────────┼───────────┐
                ▼           ▼           ▼
        ┌───────────┐ ┌──────────┐ ┌──────────┐
        │ ChromaDB  │ │ Resume   │ │ RL       │
        │ (Vector   │ │ Analysis │ │ Module   │
        │  Store)   │ │ Module   │ │          │
        └───────────┘ └──────────┘ └──────────┘
                ▲
                │
        ┌───────────────┐
        │ Evaluation    │
        │ Module        │
        └───────────────┘
```

The project consists of a Flask backend API and a React frontend:

- **Backend**: Python Flask server with multiple modules
  - Question Generation: Creates relevant HR interview questions
  - RAG Integration: ChromaDB for context-aware retrieval
  - Dual Evaluation System: Analyzes and scores candidate responses
  - Resume Strengthening: Provides resume improvement suggestions
  - Reinforcement Learning: Dynamically adjusts question difficulty
  - Speech Analysis: Processes and evaluates speech patterns
  - Database: Stores interview Q&A pairs and confidence metrics

- **Frontend**: React-based interactive UI
  - Modern chat interface with dark/light mode
  - Resume upload functionality
  - Interview session management
  - Real-time feedback display
  - Voice recording and processing
  - Feedback history visualization

## Installation

### Prerequisites

- Python 3.9+
- Node.js 14+
- npm or yarn
- FFmpeg (included in repository)

### Backend Setup

1. Clone the repository:
   ```
   git clone <repository-url>
   cd Interview_Preparation_Assistant
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install Python dependencies:
   ```
   pip install -r requirements.txt
   ```

4. API Keys Configuration:
   The system uses the following external APIs:
   - Hugging Face API for DeepSeek LLM (set via environment variables `HF_API_KEY1` and `HF_API_KEY2`)
   - Google Gemini API (set via environment variable `GEMINI_API_KEY`)
   - SerpAPI for job description retrieval (set via environment variable `SERPAPI_KEY`)

   Set these environment variables in your shell or in a `.env` file before running the backend. For example:
   ```sh
   export HF_API_KEY1=your_huggingface_key1
   export HF_API_KEY2=your_huggingface_key2
   export GEMINI_API_KEY=your_gemini_key
   export SERPAPI_KEY=your_serpapi_key
   ```

5. FFmpeg for audio processing:
   The project includes FFmpeg binaries in the ffmpeg/bin folder. If you want to use a different FFmpeg installation:
   - Download from https://ffmpeg.org/download.html
   - Or use package manager:
     ```
     # Windows (using Chocolatey)
     choco install ffmpeg
     
     # macOS
     brew install ffmpeg
     
     # Linux
     sudo apt install ffmpeg
     ```

### Frontend Setup

1. Navigate to the frontend directory:
   ```
   cd interview-prepper-frontend
   ```

2. Install JavaScript dependencies:
   ```
   npm install
   ```

## Usage

### Starting the Backend

```
python app.py
```

The backend server will run on http://localhost:8000

### API Health Checks

To verify the external APIs are working:

```bash
python Question_generation/test_api.py
```

To test document retrieval from ChromaDB:

```bash
python Question_generation/test_retrieval.py
```

To inspect the database contents:

```bash
python check_database.py
```

### Troubleshooting

If you encounter issues with audio recording or transcription:

1. Ensure your browser has permission to access the microphone
2. Check that FFmpeg is correctly configured in the `ffmpeg/bin` directory
3. Make sure all Python dependencies are installed (run `pip install -r requirements.txt`)
4. Check the audio log in `temp_audio/audio_log.txt` for debugging information
5. If experiencing 504 Gateway Timeout or DNS errors with Hugging Face API:
   - Try alternating between API keys
   - Consider setting up a local model for more reliable results

### Starting the Frontend

```
cd interview-prepper-frontend
npm start
```

The frontend application will run on http://localhost:3000

### Using the Application

1. Upload your resume and optionally provide a job description
2. Select the difficulty level for your interview
3. Click "Start Interview" to begin the simulation
4. Answer each question thoughtfully
5. Receive feedback on your responses
6. When finished, type "exit" or click "End Interview" for comprehensive feedback

## API Endpoints

- `POST /upload_resume`: Upload a resume file
  - Params: resume (file), job_description (text), difficulty (text)
  - Returns: extracted text, resume strengthening suggestions

- `POST /chat`: Main interview interaction endpoint
  - Params: message (text), current_difficulty (text, optional)
  - Returns: 
    - Normal mode: bot reply, score and feedback for answers
    - On "exit": JSON array of all Q&As with scores, feedback, and confidence metrics

- `POST /transcribe`: Audio transcription and speech analysis endpoint
  - Params: audio (file) - Audio recording (various formats supported)
  - Returns: transcript (text), confidence_score, confidence_feedback, and analysis metrics

## Voice Recording & Speech Analysis

The application includes advanced speech analysis features:

- **Audio Recording**: Record your interview answers directly in the browser
- **Multi-format Support**: Handles various audio formats with FFmpeg conversion
- **Speech Transcription**: Convert speech to text for analysis
- **Filler Word Detection**: Identifies common filler words ("um", "uh", "like", etc.)
- **Speaking Rate Analysis**: Calculates words per minute (WPM) to gauge speaking pace
- **Confidence Scoring**: Composite score based on clarity, filler words, and speaking rate
- **Speech Feedback**: Personalized suggestions to improve speaking confidence

### Speech Metrics

The system analyzes several key metrics:
- **Filler Word Count**: Number of filler words used
- **Filler Word Ratio**: Percentage of total words that are fillers
- **Speaking Rate**: Words per minute (WPM)
- **Optimal Range**: Compares WPM to ideal speaking pace (120-160 WPM)
- **Clarity Score**: Based on transcription confidence

### Technical Implementation

The speech analysis module utilizes:
- FFmpeg for audio format conversion and standardization
- Multiple fallback methods for handling various audio formats
- Temporary file management for processing
- Error handling for incomplete or corrupted recordings
- Background noise compensation techniques

### Using the Voice Feature

1. Click the microphone button to start recording
2. Speak your answer clearly into the microphone
3. Click the stop button when finished
4. The system will:
   - Transcribe your speech
   - Analyze for confidence indicators (filler words, speaking rate)
   - Calculate a confidence score (0-10)
   - Provide feedback on your speaking style
   - Display the transcribed text in the chat
   - Store the confidence metrics in the database

### Database Schema

The main table `interview_qa` stores:
- Questions and answers
- Difficulty levels
- Evaluation scores and feedback
- Speech confidence metrics:
  - `confidence_score`: Numeric score based on speech analysis
  - `confidence_feedback`: Specific feedback on speaking performance
- Timestamps for session tracking

## Frontend

The frontend consists of:

- **Main App Component**: Manages resume upload and interview settings
  - Dark/light mode toggle
  - Resume file uploader
  - Job description input
  - Difficulty selector
  
- **Chat Component**: Handles the interview conversation
  - Message history display
  - Text input for typed answers
  - Voice recording for spoken answers
  - Dynamic difficulty adjustment controls
  
- **Feedback Components**:
  - Real-time feedback on answers
  - Speech confidence metrics and suggestions
  - Final interview summary
  - Feedback history viewer

## Development

### Backend Structure

- `app.py`: Main Flask application and API endpoints
- `Question_generation/models.py`: Database models for storing interview Q&A pairs
- `Question_generation/Retrivel.py`: ChromaDB integration for document retrieval
- `Question_generation/llm_utils.py`: Parallel LLM query processing utilities
- `Evaluation_module/evaluation.py`: Answer evaluation logic
- `Evaluation_module/interview_evaluation_dataset.json`: Test dataset for evaluation
- `Evaluation_module/run_evaluation_dataset.py`: Automated evaluation pipeline
- `Evaluation_module/plot_rag_vs_norag.py`: Visualization of evaluation results
- `Resume_strengthening/resume_strengthening.py`: Resume improvement suggestions module
- `RL_module/dynamic_difficulty.py`: Reinforcement learning for difficulty adjustment
- `speech_analysis.py`: Audio transcription and speech confidence analysis
- `check_database.py`: Utility for viewing database contents

### Frontend Structure

- `src/App.js`: Main React component and resume upload logic
- `src/chat.jsx`: Interview chat interface with feedback display
- `src/voice-button.jsx`: Audio recording component
- `src/FeedbackHistory.jsx`: Component for displaying interview history
- `src/ConfirmationModal.jsx`: UI for confirming difficulty changes
- `src/App.css`: Main styling for the application

## RAG Evaluation System

The system implements a Retrieval-Augmented Generation (RAG) approach to improve answer evaluation:

1. **Document Retrieval**: Uses ChromaDB to store and retrieve relevant interview context
2. **Context Enhancement**: Enriches evaluations with domain-specific knowledge
3. **Comparative Analysis**: Runs parallel evaluations with and without RAG
4. **Gemini Selection**: Uses Google's Gemini to select the most appropriate evaluation
5. **Performance Analysis**: Tracks and visualizes the effectiveness of RAG vs non-RAG approaches

The evaluation pipeline can be run on test datasets to measure performance:
```bash
python Evaluation_module/run_evaluation_dataset.py
```

Results can be visualized with:
```bash
python Evaluation_module/plot_rag_vs_norag.py
```

## Reinforcement Learning

The dynamic difficulty adjustment system uses Q-learning to adapt to user performance:

- **State Representation**: Combines current difficulty level and recent performance scores
- **Action Space**: Keep, increase, or decrease difficulty level
- **Reward Function**: Based on user engagement and appropriate challenge level
- **Exploration Strategy**: Epsilon-greedy approach to balance exploration and exploitation
- **Memory**: Tracks recent performance to inform difficulty decisions

This creates a more personalized interview experience that adapts to the candidate's skill level in real-time.

## Technologies Used

### Backend
- Flask: Web framework
- SQLAlchemy: ORM for database operations
- PyPDF2: PDF parsing
- HuggingFace API: DeepSeek LLM for question generation and evaluation
- Google Gemini API: For meta-evaluation and decision making
- ChromaDB: Vector database for context retrieval
- Sentence Transformers: Embedding generation for semantic search
- SerpAPI: For job description retrieval
- FFmpeg: Audio processing and format conversion
- Speech Recognition: Audio transcription

### Frontend
- React: UI framework
- Web Speech API: Voice recognition functionality
- CSS3: Modern styling with dark/light mode support
- FontAwesome: Icon library for enhanced UI

---

© 2025 Interview Prepper | AI-Powered Interview Simulation
