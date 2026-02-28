"""Quick test script for the upload and status endpoints."""
import http.client
import json
import os

boundary = "----WebBoundary12345"
filepath = os.path.join(os.path.dirname(__file__), "discovery_report.json")

with open(filepath, "rb") as f:
    file_data = f.read()

body = (
    f"--{boundary}\r\n"
    f'Content-Disposition: form-data; name="file"; filename="discovery_report.json"\r\n'
    f"Content-Type: application/json\r\n\r\n"
).encode() + file_data + f"\r\n--{boundary}--\r\n".encode()

conn = http.client.HTTPConnection("localhost", 5000)

# Test upload
conn.request("POST", "/api/upload", body=body,
    headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
resp = conn.getresponse()
print("Upload:", resp.status, json.loads(resp.read()))

# Test status after upload
conn.request("GET", "/api/status")
resp = conn.getresponse()
status = json.loads(resp.read())
print("Status:", status)
print(f"  data_loaded={status['data_loaded']}, vms={status['vm_count']}, host={status['vcenter_host']}")

# Test summary endpoint
conn.request("GET", "/api/summary")
resp = conn.getresponse()
summary = json.loads(resp.read())
print(f"Summary: {summary['total_vms']} VMs, ${summary['total_monthly_cost']}/mo")

# Test disconnect
conn.request("POST", "/api/disconnect", body="{}", headers={"Content-Type": "application/json"})
resp = conn.getresponse()
print("Disconnect:", json.loads(resp.read()))

# Verify data cleared
conn.request("GET", "/api/status")
resp = conn.getresponse()
status = json.loads(resp.read())
print(f"After disconnect: data_loaded={status['data_loaded']}")
