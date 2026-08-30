import os
import sys
import subprocess
import json
import requests

API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("LLM_API_KEY")
LOG_FILE = sys.argv[1] if len(sys.argv) > 1 else "pipeline.log"

if not API_KEY:
    print("Error: Neither GEMINI_API_KEY nor LLM_API_KEY environment variable is set.")
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
2. If the failure is due to a missing tool or typo (e.g., 'mvn1: not found'), state the fix clearly.
3. Provide the exact shell command to install or resolve it if applicable.

Respond ONLY with a valid JSON object matching this schema:
{{
  "cause": "Short summary",
  "missing_tool": true,
  "remediation_cmd": "exact bash command to fix or empty string",
  "explanation": "concise explanation"
}}
"""

# Use v1 endpoint with gemini-2.5-flash or gemini-1.5-flash-latest
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}"
headers = {"Content-Type": "application/json"}

payload = {
    "contents": [{
        "parts": [{"text": prompt}]
    }],
    "generationConfig": {
        "response_mime_type": "application/json",
        "temperature": 0.1
    }
}

try:
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    resp_json = response.json()

    # Fallback to v1 gemini-1.5-flash-latest if v1beta returns error
    if response.status_code != 200:
        fallback_url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={API_KEY}"
        response = requests.post(fallback_url, headers=headers, json=payload, timeout=30)
        resp_json = response.json()

    if response.status_code != 200:
        print(f"Gemini API Error ({response.status_code}): {resp_json.get('error', resp_json)}")
        sys.exit(1)

    raw_text = resp_json["candidates"][0]["content"]["parts"][0]["text"]
    data = json.loads(raw_text)

    print("\n================ [AI AGENT TRIAGE] ================")
    print(f"Root Cause:     {data.get('cause')}")
    print(f"Explanation:    {data.get('explanation')}")
    print(f"Suggested Fix:  {data.get('remediation_cmd')}")
    print("===================================================\n")

    if data.get("missing_tool") and data.get("remediation_cmd"):
        cmd = data.get("remediation_cmd")
        print(f"[AI Self-Healing] Executing detected fix: {cmd}")
        subprocess.run(cmd, shell=True, check=False)

    with open("ai_triage.json", "w") as out:
        out.write(raw_text)

except Exception as e:
    print(f"AI Agent execution failed: {e}")
