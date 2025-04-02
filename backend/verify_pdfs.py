# verify_pdfs.py
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get connection parameters
user = os.environ['DATABASE_USER']
password = os.environ['DATABASE_PASSWORD']
host = os.environ['DATABASE_HOST']
port = os.environ['DATABASE_PORT']
db_name = os.environ['DATABASE_NAME']

# Create connection string with URL-encoded password
password_encoded = password.replace('@', '%40')
DATABASE_URL = f"postgresql://{user}:{password_encoded}@{host}:{port}/{db_name}"

# Create engine
engine = create_engine(DATABASE_URL)

# Connect and query
with engine.connect() as connection:
    # Query all PDFs
    result = connection.execute(text("SELECT * FROM pdfs"))
    
    # Print results
    pdfs = []
    for row in result:
        pdf_info = {
            "id": row.id,
            "name": row.name,
            "file": row.file,
            "selected": row.selected
        }
        pdfs.append(pdf_info)
        print(f"ID: {row.id}, Name: {row.name}, Selected: {row.selected}")
        print(f"File URL: {row.file}")
        print("-" * 50)
    
    print(f"Total PDFs found: {len(pdfs)}")