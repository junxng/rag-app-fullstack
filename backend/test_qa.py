import requests
import json

# Test the presigned URL endpoint
def test_presigned_url(pdf_id):
    url = f"http://localhost:8000/pdfs/{pdf_id}/presigned-url"
    response = requests.get(url)
    print(f"Status code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Presigned URL: {data.get('url')}")
        return data.get('url')
    else:
        print(f"Error: {response.text}")
        return None

# Test the QA endpoint
def test_qa_endpoint(pdf_id, question):
    url = f"http://localhost:8000/pdfs/qa-pdf/{pdf_id}"
    payload = {"question": question}
    headers = {"Content-Type": "application/json"}
    
    response = requests.post(url, data=json.dumps(payload), headers=headers)
    print(f"Status code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Answer: {data.get('answer')}")
    else:
        print(f"Error: {response.text}")
    
    return response

# Test PDF with ID 6 (allergic.pdf)
pdf_id = 6
print("Testing presigned URL endpoint...")
presigned_url = test_presigned_url(pdf_id)

if presigned_url:
    print("\nTesting PDF access...")
    pdf_response = requests.get(presigned_url)
    print(f"PDF access status code: {pdf_response.status_code}")
    print(f"PDF size: {len(pdf_response.content)} bytes")

print("\nTesting QA endpoint...")
question = "What are the common symptoms of allergies?"
qa_response = test_qa_endpoint(pdf_id, question)