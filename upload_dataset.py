import requests
import json

# API endpoint
url = "http://localhost:8000/api/v1/doctor/datasets/upload?category=lipid"

# File to upload
file_path = "test_lipid_dataset.xlsx"

# Open and send file
with open(file_path, 'rb') as f:
    files = {'file': (file_path, f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
    response = requests.post(url, files=files)

# Print response
print("Status Code:", response.status_code)
print("Response:")
print(json.dumps(response.json(), indent=2))
