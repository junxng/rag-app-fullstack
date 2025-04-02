from typing import List
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
import schemas
import crud
from database import SessionLocal
from uuid import uuid4

# Necessary imports for langchain summarization
from langchain_openai import OpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

# Necessary imports to chat with a PDF file
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from schemas import QuestionRequest
from database import SessionLocal
from config import Settings

# Get settings
settings = Settings()
# Initialize OpenAI with API key from environment
llm = OpenAI(openai_api_key=settings.OPENAI_API_KEY)

router = APIRouter(prefix="/pdfs")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("", response_model=schemas.PDFResponse, status_code=status.HTTP_201_CREATED)
def create_pdf(pdf: schemas.PDFRequest, db: Session = Depends(get_db)):
    return crud.create_pdf(db, pdf)

@router.post("/upload", response_model=schemas.PDFResponse, status_code=status.HTTP_201_CREATED)
def upload_pdf(file: UploadFile = File(...), db: Session = Depends(get_db)):
    file_name = f"{uuid4()}-{file.filename}"
    return crud.upload_pdf(db, file, file_name)

@router.get("", response_model=List[schemas.PDFResponse])
def get_pdfs(selected: bool = None, db: Session = Depends(get_db)):
    return crud.read_pdfs(db, selected)

@router.get("/{id}", response_model=schemas.PDFResponse)
def get_pdf_by_id(id: int, db: Session = Depends(get_db)):
    pdf = crud.read_pdf(db, id)
    if pdf is None:
        raise HTTPException(status_code=404, detail="PDF not found")
    return pdf

@router.get("/{id}/presigned-url")
def get_pdf_presigned_url(id: int, db: Session = Depends(get_db)):
    pdf = crud.read_pdf(db, id)
    if pdf is None:
        raise HTTPException(status_code=404, detail="PDF not found")
    
    presigned_url = crud.get_presigned_url(id, db)
    if presigned_url is None:
        raise HTTPException(status_code=500, detail="Failed to generate presigned URL")
        
    return {"url": presigned_url}

@router.put("/{id}", response_model=schemas.PDFResponse)
def update_pdf(id: int, pdf: schemas.PDFRequest, db: Session = Depends(get_db)):
    updated_pdf = crud.update_pdf(db, id, pdf)
    if updated_pdf is None:
        raise HTTPException(status_code=404, detail="PDF not found")
    return updated_pdf

@router.delete("/{id}", status_code=status.HTTP_200_OK)
def delete_pdf(id: int, db: Session = Depends(get_db)):
    if not crud.delete_pdf(db, id):
        raise HTTPException(status_code=404, detail="PDF not found")
    return {"message": "PDF successfully deleted"}


# LANGCHAIN
from langchain_core.prompts import ChatPromptTemplate
from operator import or_

langchain_llm = OpenAI(temperature=0, openai_api_key=settings.OPENAI_API_KEY)

# Modern LangChain approach using | operator (RunnableSequence)
summarize_template_string = """
        Provide a summary for the following text:
        {text}
"""

summarize_prompt = ChatPromptTemplate.from_template(summarize_template_string)
# Create a runnable sequence (prompt | llm | output parser)
summarize_chain = summarize_prompt | langchain_llm | StrOutputParser()

@router.post('/summarize-text')
async def summarize_text(text: str):
    # Use the modern invoke approach
    summary = summarize_chain.invoke({"text": text})
    return {'summary': summary}


# Ask a question about one PDF file
@router.post("/qa-pdf/{id}", response_model=schemas.AnswerResponse, status_code=status.HTTP_200_OK)
def qa_pdf_by_id(id: int, question_request: QuestionRequest, db: Session = Depends(get_db)):
    """
    Completely rewritten QA endpoint using the latest LangChain patterns
    with progress visualization using tqdm
    """
    import tempfile
    import requests
    import os
    import traceback
    from tqdm import tqdm
    
    # Get PDF from database
    pdf = crud.read_pdf(db, id)
    if pdf is None:
        raise HTTPException(status_code=404, detail="PDF not found")
    
    # Get question
    question = question_request.question
    if not question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    
    # Log what we're doing
    print(f"Processing QA for PDF ID {id}, question: {question}")
    print(f"PDF details: {pdf.name}, URL: {pdf.file}")
    
    try:
        # Step 1: Generate presigned URL and download PDF to temporary file
        try:
            # Get presigned URL using existing function
            presigned_url = crud.get_presigned_url(pdf_id=id, db=db)
            if not presigned_url:
                raise HTTPException(status_code=500, detail="Failed to generate presigned URL for PDF")
                
            print(f"Generated presigned URL for download")
            
            # Download using presigned URL with progress bar
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                print(f"Downloading PDF using presigned URL")
                
                # Stream download with progress bar
                response = requests.get(presigned_url, stream=True)
                
                if response.status_code != 200:
                    print(f"Download failed with status code: {response.status_code}")
                    raise HTTPException(status_code=500, detail=f"Failed to download PDF: HTTP {response.status_code}")
                
                # Get total file size for progress bar
                total_size = int(response.headers.get('content-length', 0))
                
                # Download with progress bar
                with tqdm(total=total_size, unit='B', unit_scale=True, desc="Downloading PDF") as pbar:
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:
                            temp_file.write(chunk)
                            pbar.update(len(chunk))
                
                temp_file_path = temp_file.name
                print(f"PDF downloaded to {temp_file_path}")
        except Exception as download_error:
            print(f"Error during download: {str(download_error)}")
            raise HTTPException(status_code=500, detail=f"Download error: {str(download_error)}")
        
        try:
            # Step 2: Process PDF with simpler approach
            # Import locally to avoid circular imports
            from langchain_community.document_loaders import PyPDFLoader
            from langchain_text_splitters import RecursiveCharacterTextSplitter
            from langchain_openai import OpenAI, OpenAIEmbeddings
            from langchain_community.vectorstores import FAISS
            
            # Load PDF
            print("Loading PDF with PyPDFLoader")
            loader = PyPDFLoader(temp_file_path)
            docs = loader.load()
            print(f"Loaded {len(docs)} pages from PDF")
            
            if not docs:
                return {"answer": "The PDF appears to be empty or could not be processed."}
            
            # Process text with progress visualization
            print("Splitting text into chunks")
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,  # Smaller chunks for better processing
                chunk_overlap=200
            )
            
            # Split documents with progress bar
            chunks = []
            for doc in tqdm(docs, desc="Processing PDF pages"):
                chunks.extend(text_splitter.split_documents([doc]))
            print(f"Split into {len(chunks)} chunks")
            
            # Create embeddings and vector store with progress visualization
            print("Creating embeddings")
            # Show a progress message since we can't track OpenAI API calls directly
            print("Starting embeddings creation with OpenAI... (this may take a few moments)")
            embeddings = OpenAIEmbeddings(openai_api_key=settings.OPENAI_API_KEY)
            
            # Handle the case where there are no chunks
            if not chunks:
                return {"answer": "The PDF could not be properly processed into searchable text."}
            
            # Create vector store with explicit FAISS import
            import faiss
            print("FAISS library loaded successfully")
            vectorstore = FAISS.from_documents(chunks, embeddings)
            
            # Set up retriever
            retriever = vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 3}  # Return top 3 most relevant chunks
            )
            
            # Get context for our question using modern invoke approach
            print("Retrieving relevant context")
            context_docs = retriever.invoke(question)  # Use invoke instead of get_relevant_documents
            
            if not context_docs:
                return {"answer": "I couldn't find relevant information in the document to answer your question."}
            
            # Extract text from context documents
            context = "\n\n".join([doc.page_content for doc in context_docs])
            
            # Create prompt for QA
            print("Creating prompt for QA")
            from langchain.prompts import ChatPromptTemplate
            
            prompt_template = """You are a helpful assistant that answers questions based on the provided document context.
            
            Context from the document:
            {context}
            
            Question: {question}
            
            Answer the question based only on the provided context. If you can't answer the question based on the context, say "I don't have enough information to answer this question based on the document."
            """
            
            qa_prompt = ChatPromptTemplate.from_template(prompt_template)
            
            # Create LLM
            print("Setting up LLM")
            qa_llm = OpenAI(
                temperature=0,
                openai_api_key=settings.OPENAI_API_KEY
            )
            
            # Create chain
            qa_chain = qa_prompt | qa_llm
            
            # Run chain
            print("Running QA chain")
            response = qa_chain.invoke({
                "context": context,
                "question": question
            })
            
            # Get answer - handle both string and object responses
            if hasattr(response, 'content'):
                answer = response.content
            else:
                # If response is a string, use it directly
                answer = str(response)
                
            print(f"Generated answer: {answer[:100]}...")
            
            # Format response to match schema
            return schemas.AnswerResponse(answer=answer)
            
        finally:
            # Clean up temporary file
            try:
                if 'temp_file_path' in locals() and temp_file_path and os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    print(f"Deleted temporary file {temp_file_path}")
            except Exception as cleanup_error:
                print(f"Error cleaning up temp file: {str(cleanup_error)}")
            
    except HTTPException as http_exc:
        # Re-raise HTTP exceptions directly
        raise http_exc
    except Exception as e:
        # Comprehensive error handling for other exceptions
        error_message = str(e)
        error_traceback = traceback.format_exc()
        print(f"Error in QA endpoint: {error_message}")
        print(f"Traceback: {error_traceback}")
        
        # Provide a user-friendly error message
        if "rate limit" in error_message.lower():
            detail = "OpenAI API rate limit exceeded. Please try again later."
        elif "api key" in error_message.lower():
            detail = "Issue with OpenAI API key. Please check server configuration."
        elif "time" in error_message.lower() and "out" in error_message.lower():
            detail = "Request timed out. The PDF may be too large or complex."
        elif "access denied" in error_message.lower() or "forbidden" in error_message.lower() or "403" in error_message:
            detail = "Access denied to the PDF file. Please check S3 permissions."
        elif "not found" in error_message.lower() or "404" in error_message:
            detail = "PDF file not found in storage."
        else:
            detail = f"Error processing PDF: {error_message}"
            
        raise HTTPException(status_code=500, detail=detail)
