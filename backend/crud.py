from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException
import models, schemas
from config import Settings
from botocore.exceptions import NoCredentialsError, BotoCoreError
import urllib.parse

def create_pdf(db: Session, pdf: schemas.PDFRequest):
    db_pdf = models.PDF(name=pdf.name, selected=pdf.selected, file=pdf.file)
    db.add(db_pdf)
    db.commit()
    db.refresh(db_pdf)
    return db_pdf

def read_pdfs(db: Session, selected: bool = None):
    if selected is None:
        return db.query(models.PDF).all()
    else:
        return db.query(models.PDF).filter(models.PDF.selected == selected).all()

def read_pdf(db: Session, id: int):
    return db.query(models.PDF).filter(models.PDF.id == id).first()

def update_pdf(db: Session, id: int, pdf: schemas.PDFRequest):
    db_pdf = db.query(models.PDF).filter(models.PDF.id == id).first()
    if db_pdf is None:
        return None
    update_data = pdf.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_pdf, key, value)
    db.commit()
    db.refresh(db_pdf)
    return db_pdf

def delete_pdf(db: Session, id: int):
    """Delete PDF from both S3 and database with transaction safety"""
    db_pdf = db.query(models.PDF).filter(models.PDF.id == id).first()
    if db_pdf is None:
        return None
    
    # Extract file name from S3 URL
    file_url = db_pdf.file
    s3_delete_success = True
    file_key = None
    
    if file_url and 's3.amazonaws.com/' in file_url:
        try:
            settings = Settings()
            s3_client = Settings.get_s3_client()
            BUCKET_NAME = settings.AWS_S3_BUCKET
            
            # Extract the key (filename) from the URL
            file_key = file_url.split('amazonaws.com/')[1]
            file_key = urllib.parse.unquote(file_key)
            
            # Check if file exists in S3 before attempting deletion
            try:
                s3_client.head_object(Bucket=BUCKET_NAME, Key=file_key)
                # File exists, so delete it
                s3_client.delete_object(
                    Bucket=BUCKET_NAME,
                    Key=file_key
                )
            except s3_client.exceptions.ClientError as e:
                # File doesn't exist in S3 or other error
                error_code = e.response.get('Error', {}).get('Code')
                if error_code == '404':
                    # File not found - just log and continue
                    print(f"File {file_key} not found in S3, continuing with DB deletion")
                else:
                    # Other error - log but mark as failed
                    print(f"S3 error checking file existence: {str(e)}")
                    s3_delete_success = False
                
        except (NoCredentialsError, BotoCoreError) as e:
            # Log error and mark S3 deletion as failed
            print(f"Error with S3 credentials or connection: {str(e)}")
            s3_delete_success = False
    
    try:
        # Delete from database
        db.delete(db_pdf)
        db.commit()
        
        # If database deletion succeeded but S3 deletion failed, retry S3 deletion
        if not s3_delete_success and file_key:
            try:
                settings = Settings()
                s3_client = Settings.get_s3_client()
                BUCKET_NAME = settings.AWS_S3_BUCKET
                
                s3_client.delete_object(
                    Bucket=BUCKET_NAME,
                    Key=file_key
                )
                print(f"Successfully deleted S3 object on retry: {file_key}")
            except Exception as retry_error:
                print(f"Failed to delete S3 object on retry: {str(retry_error)}")
                # Consider implementing a cleanup job or queue for orphaned S3 objects
                
        return True
        
    except Exception as db_error:
        # If database deletion fails, log the error and re-raise
        print(f"Database deletion error: {str(db_error)}")
        db.rollback()
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to delete PDF from database: {str(db_error)}"
        )

def upload_pdf(db: Session, file: UploadFile, file_name: str):
    """Upload PDF to S3 and store reference in database with transaction safety"""
    settings = Settings()
    s3_client = Settings.get_s3_client()
    BUCKET_NAME = settings.AWS_S3_BUCKET
    s3_upload_success = False
    
    try:
        # First, validate the file
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="File must be a PDF")
            
        # Set up the S3 file URL
        file_url = f'https://{BUCKET_NAME}.s3.amazonaws.com/{file_name}'
        
        # Create database record first without committing
        db_pdf = models.PDF(name=file.filename, selected=False, file=file_url)
        db.add(db_pdf)
        
        # Try to upload to S3
        try:
            s3_client.upload_fileobj(
                file.file,
                BUCKET_NAME,
                file_name,
                ExtraArgs={
                    'ContentType': 'application/pdf'
                }
            )
            s3_upload_success = True
        except (NoCredentialsError, BotoCoreError) as s3_error:
            # If S3 upload fails, roll back database changes
            db.rollback()
            raise HTTPException(status_code=500, detail=f"S3 upload failed: {str(s3_error)}")
        
        # If we got here, S3 upload succeeded so commit the database transaction
        db.commit()
        db.refresh(db_pdf)
        return db_pdf
        
    except Exception as e:
        # If any other error occurred and we uploaded to S3, try to delete from S3
        if s3_upload_success:
            try:
                s3_client.delete_object(
                    Bucket=BUCKET_NAME,
                    Key=file_name
                )
            except Exception as cleanup_error:
                # Log cleanup error but continue with the main error
                print(f"Error cleaning up S3 after failure: {str(cleanup_error)}")
        
        # Ensure DB transaction is rolled back
        db.rollback()
        
        # Re-raise HTTP exceptions
        if isinstance(e, HTTPException):
            raise e
            
        # Convert other exceptions to HTTP 500
        raise HTTPException(status_code=500, detail=f"Error uploading PDF: {str(e)}")

def get_presigned_url(pdf_id: int, db: Session, expiration=3600):
    """Generate a pre-signed URL for temporary access to S3 object"""
    db_pdf = read_pdf(db, pdf_id)
    if db_pdf is None:
        return None
        
    file_url = db_pdf.file
    if not file_url or 's3.amazonaws.com/' not in file_url:
        return file_url  # Return original URL if not an S3 URL
        
    try:
        settings = Settings()
        s3_client = Settings.get_s3_client()
        BUCKET_NAME = settings.AWS_S3_BUCKET
        
        # Extract the key (filename) from the URL
        file_key = file_url.split('amazonaws.com/')[1]
        
        # URL decode in case the key has URL-encoded characters
        file_key = urllib.parse.unquote(file_key)
        
        # Generate presigned URL
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': BUCKET_NAME,
                'Key': file_key
            },
            ExpiresIn=expiration
        )
        
        return presigned_url
    except (NoCredentialsError, BotoCoreError) as e:
        print(f"Error generating presigned URL: {str(e)}")
        return file_url  # Fall back to the original URL


# def upload_pdf(db: Session, file: UploadFile, file_name: str):
#     s3_client = Settings.get_s3_client()
#     BUCKET_NAME = Settings().AWS_S3_BUCKET

#     try:
#         s3_client.upload_fileobj(
#             file.file,
#             BUCKET_NAME,
#             file_name,
#             ExtraArgs={'ACL': 'public-read'}
#         )
#         file_url = f'https://{BUCKET_NAME}.s3.amazonaws.com/{file_name}'
        
#         db_pdf = models.PDF(name=file.filename, selected=False, file=file_url)
#         db.add(db_pdf)
#         db.commit()
#         db.refresh(db_pdf)
#         return db_pdf
#     except NoCredentialsError:
#         raise HTTPException(status_code=500, detail="Error in AWS credentials")
#     except BotoCoreError as e:
#         raise HTTPException(status_code=500, detail=str(e))