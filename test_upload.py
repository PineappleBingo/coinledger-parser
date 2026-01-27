import requests

# Test the upload endpoint
url = "http://localhost:8000/api/upload"
file_path = "import/Xverse Import transactions - Sheet1.csv"

try:
    with open(file_path, 'rb') as f:
        files = {'file': (file_path, f, 'text/csv')}
        response = requests.post(url, files=files)
        
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        print(f"Response: {response.json()}")
    else:
        print(f"Error Response Text: {response.text}")
    
except Exception as e:
    print(f"Error: {e}")
