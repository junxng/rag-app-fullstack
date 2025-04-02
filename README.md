# Retrieval-Augmented Generation Application Fullstack

This document provides comprehensive guidance for setting up and running the RAG-based PDF Manager application.

## Architecture Overview

This application is a full-stack PDF management system with built-in RAG (Retrieval Augmented Generation) capabilities:

- **Frontend**: Next.js React application for the user interface
- **Backend**: FastAPI Python service with LangChain for AI processing
- **Database**: PostgreSQL for storing PDF metadata
- **Storage**: AWS S3 for storing PDF files
- **AI**: OpenAI for embeddings and LLM capabilities

## System Requirements

- Python 3.11+
- Node.js 16+
- Docker & Docker Compose
- AWS S3 account with bucket and credentials
- OpenAI API key

## Environment Setup

1. **Create .env files for configuration**:

   Backend `.env` file (`/backend/.env`):
   ```
   # Database settings
   DATABASE_HOST=your_database_host
   DATABASE_NAME=your_database_name
   DATABASE_USER=your_database_user
   DATABASE_PASSWORD=your_password
   DATABASE_PORT=_your_atabase_host

   # AWS S3 settings
   AWS_KEY=your_aws_access_key
   AWS_SECRET=your_aws_secret_key
   AWS_S3_BUCKET=your_s3_bucket_name

   # OpenAI API settings
   OPENAI_API_KEY=your_openai_api_key
   ```

   Frontend `.env` file (`/frontend/.env`):
   ```
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

2. **Start Database with Docker**:
   ```bash
   docker-compose up -d db
   ```

## Build & Run Commands

### Using Package Managers

**Backend** (using UV package manager):
```bash
cd backend
uv venv --python 3.11.4
source .venv/bin/activate
uv pip sync requirements.txt
uv run uvicorn main:app --reload
```

**Frontend**:
```bash
cd frontend
npm ci
npm run dev
```

### Using Docker Compose (All Services)

Start everything with one command:
```bash
docker-compose up -d
```

## Features & Workflow

1. **Upload PDFs**: Upload PDFs to be stored in S3
2. **View PDFs**: Browse and view uploaded PDFs
3. **Query PDFs**: Ask questions about PDF content using LLM capabilities
4. **Delete PDFs**: Remove PDFs from the system

## Endpoints

### Backend API

- `GET /pdfs`: List all PDFs
- `GET /pdfs/{id}`: Get PDF by ID
- `GET /pdfs/{id}/presigned-url`: Get temporary URL to view PDF
- `POST /pdfs/upload`: Upload new PDF
- `POST /pdfs/qa-pdf/{id}`: Ask a question about a specific PDF
- `DELETE /pdfs/{id}`: Delete a PDF

## Troubleshooting

### Common Issues

1. **Database Connection Errors**:
   - Ensure PostgreSQL is running
   - Check if database credentials are correct
   - Verify that @ symbol in passwords is URL-encoded as %40

2. **S3 Connection Errors**:
   - Verify AWS credentials are valid
   - Check if S3 bucket exists and is accessible
   - Ensure proper permissions on S3 bucket
   - For PDF access issues, make sure presigned URLs are being generated correctly

3. **Missing Dependencies**:
   - FAISS: If you see "Could not import faiss", install it with: `uv pip install faiss-cpu`
   - Other dependencies: Run `uv pip install -r requirements.txt` to ensure all packages are installed

4. **LangChain/OpenAI Errors**:
   - Verify OpenAI API key is valid
   - Update deprecated LangChain imports:
     ```python
     # Old imports
     from langchain import OpenAI
     from langchain.embeddings.openai import OpenAIEmbeddings
     from langchain.vectorstores import FAISS
     
     # New imports
     from langchain_openai import OpenAI, OpenAIEmbeddings
     from langchain_community.vectorstores import FAISS
     ```
   - Use the modern method invocation patterns:
     ```python
     # Old pattern
     retriever.get_relevant_documents(query)
     
     # New pattern
     retriever.invoke(query)
     ```

## Code Style Guidelines

### Backend (Python)
* Imports: stdlib first, third-party second, local imports last
* Naming: snake_case for variables/functions, CamelCase for classes
* Error handling: Use FastAPI HTTPException for API errors
* Type hints: Always use type annotations
* Organization: Follow FastAPI project structure (models, schemas, crud, routers)

### Frontend (React/Next.js)
* Component structure: One component per file
* State management: React hooks (useState, useEffect, useCallback)
* Styling: CSS modules (component.module.css)
* Error handling: try/catch blocks with user-friendly alerts
* Naming: PascalCase for components, camelCase for variables/functions
