import os
import sys
import subprocess
import json
import requests

API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("LLM_API_KEY")
LOG_FILE = sys.argv[1] if len(sys.argv) > 1 else "pipeline.log"

if not API_KEY:
    print("Error: No API key set.")
    sys.exit(1)

if not os.path.exists(LOG_FILE):
    print("Log file not found.")
    sys.exit(0)

with open(LOG_FILE, "r") as f:
    logs = "".join(f.readlines()[-100:])

prompt = f"""
You are an autonomous DevOps CI/CD AI agent.
Analyze the following Jenkins failure logs:
---
{logs}
---
Task:
1. Identify the root cause.
2. Provide the exact fix for pom.xml or system tools.

Respond ONLY with a valid JSON object matching this schema:
{{
  "cause": "Short summary",
  "explanation": "concise explanation",
  "remediation_cmd": "exact fix"
}}
"""

url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}"

payload = {
    "contents": [{"parts": [{"text": prompt}]}],
    "generationConfig": {
        "response_mime_type": "application/json",
        "temperature": 0.1
    }
}

try:
    # Notice: No custom Authorization or x-goog headers
    response = requests.post(url, json=payload, timeout=30)
    resp_json = response.json()

    if response.status_code != 200:
        print(f"Gemini API Error: {resp_json}")
        sys.exit(1)

    raw_text = resp_json["candidates"][0]["content"]["parts"][0]["text"]
    data = json.loads(raw_text)

    print("\n================ [AI AGENT TRIAGE] ================")
    print(f"Root Cause:     {data.get('cause')}")
    print(f"Explanation:    {data.get('explanation')}")
    print(f"Suggested Fix:  {data.get('remediation_cmd')}")
    print("===================================================\n")

except Exception as e:
    print(f"AI Agent execution failed: {e}")
