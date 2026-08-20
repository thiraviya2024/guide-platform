import requests
import json

# Use the actual file path from the upload response
file_path = "uploads/datasets/20260807_185008_test_lipid_dataset.xlsx"  # Use the path from upload response

# Confirm and import
url = "http://localhost:8000/api/v1/doctor/datasets/confirm"
params = {
    "category": "lipid",
    "file_path": file_path,
    "uploaded_by": "doctor"
}

# Mapping should be sent as a JSON string in the body
mapping = {
    "Patient ID": "unknown",
    "Total Cholesterol": "total_cholesterol",
    "LDL": "ldl",
    "HDL": "hdl",
    "Triglycerides": "triglycerides",
    "VLDL": "vldl",
    "Non-HDL": "non_hdl"
}

payload = json.dumps(mapping)  # Send mapping as JSON string

response = requests.post(url, params=params, data=payload, headers={"Content-Type": "application/json"})

print("Status Code:", response.status_code)
print("Response:")
try:
    print(json.dumps(response.json(), indent=2))
except:
    print(response.text)
