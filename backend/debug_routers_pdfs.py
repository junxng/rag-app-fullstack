import os
from dotenv import load_dotenv
load_dotenv()

# Print environment variables (excluding sensitive data)
print("Environment variables:")
print(f"DATABASE_HOST: {os.environ.get('DATABASE_HOST')}")
print(f"DATABASE_NAME: {os.environ.get('DATABASE_NAME')}")
print(f"OpenAI API Key set: {'Yes' if os.environ.get('OPENAI_API_KEY') else 'No'}")
print(f"AWS S3 Credentials set: {'Yes' if os.environ.get('AWS_KEY') and os.environ.get('AWS_SECRET') else 'No'}")
print(f"AWS_S3_BUCKET: {os.environ.get('AWS_S3_BUCKET')}")

# Test database connection
print("\nTesting database connection...")
from sqlalchemy import create_engine, text
user = os.environ['DATABASE_USER']
password = os.environ['DATABASE_PASSWORD']
host = os.environ['DATABASE_HOST']
port = os.environ['DATABASE_PORT']
db_name = os.environ['DATABASE_NAME']
password_encoded = password.replace('@', '%40')
DATABASE_URL = f"postgresql://{user}:{password_encoded}@{host}:{port}/{db_name}"
print(f"Database URL: {DATABASE_URL}")

try:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as connection:
        print("Database connection successful")
except Exception as e:
    print(f"Database connection error: {str(e)}")

# Test S3 connection
print("\nTesting S3 connection...")
import boto3
from botocore.exceptions import NoCredentialsError, BotoCoreError, ClientError

try:
    s3_client = boto3.client(
        's3',
        aws_access_key_id=os.environ.get('AWS_KEY'),
        aws_secret_access_key=os.environ.get('AWS_SECRET')
    )
    
    # Try to list objects in the specific bucket
    bucket_name = os.environ.get('AWS_S3_BUCKET')
    try:
        response = s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=5)
        if 'Contents' in response:
            print(f"S3 connection successful - found {len(response['Contents'])} objects in bucket '{bucket_name}'")
            
            # Try to get one of the PDFs
            if len(response['Contents']) > 0:
                key = response['Contents'][0]['Key']
                print(f"Testing access to object: {key}")
                
                # Try to generate a presigned URL
                presigned_url = s3_client.generate_presigned_url(
                    'get_object',
                    Params={
                        'Bucket': bucket_name,
                        'Key': key
                    },
                    ExpiresIn=3600
                )
                print(f"Successfully generated presigned URL for {key}")
                print(f"Presigned URL: {presigned_url}")
        else:
            print(f"Bucket '{bucket_name}' exists but appears to be empty")
            
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchBucket':
            print(f"Bucket '{bucket_name}' does not exist!")
        elif error_code == 'AccessDenied':
            print(f"Access denied to bucket '{bucket_name}' - check permissions")
        else:
            print(f"Error accessing bucket: {str(e)}")
        
except (NoCredentialsError, BotoCoreError) as e:
    print(f"S3 credentials error: {str(e)}")
except Exception as e:
    print(f"S3 connection error: {str(e)}")

# Test OpenAI connection
print("\nTesting OpenAI connection...")
import openai

try:
    openai.api_key = os.environ.get("OPENAI_API_KEY")
    client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    models = client.models.list()
    print(f"OpenAI connection successful - found models")
except Exception as e:
    print(f"OpenAI connection error: {str(e)}")

print("\nAll tests completed")