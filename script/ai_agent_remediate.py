import os
import sys
import json
import requests

API_KEY = os.getenv("GEMINI_API_KEY")
LOG_FILE = sys.argv[1] if len(sys.argv) > 1 else "pipeline.log"

if not API_KEY:
    print("[AI Agent Error] GEMINI_API_KEY environment variable is not set.")
    sys.exit(0)

if not os.path.exists(LOG_FILE):
    print(f"[AI Agent Error] Log file '{LOG_FILE}' not found.")
    sys.exit(0)

with open(LOG_FILE, "r") as f:
    # Read the trailing 120 lines where errors and stacktraces occur
    logs = "".join(f.readlines()[-120:])

prompt = f"""
You are an expert Autonomous DevOps CI/CD AI Agent.
Analyze the following Jenkins failure logs:
---
{logs}
---
Instructions:
1. Identify the primary root cause.
2. Determine which layer failed (e.g., Syntax/Typo, Missing System Dependency, Maven/Build Error, Unit Test Failure, Authentication/Permission).
3. Provide the exact step-by-step fix, including code changes or shell commands needed to resolve the issue.

Respond ONLY with a valid JSON object matching this schema:
{{
  "error_category": "Category name",
  "root_cause": "Concise summary of the root cause",
  "explanation": "Detailed explanation of what failed and why",
  "recommended_fix": "Exact code, configuration, or shell command to resolve the failure"
}}
"""

url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={API_KEY}"
headers = {"Content-Type": "application/json"}

payload = {
    "contents": [{"parts": [{"text": prompt}]}],
    "generationConfig": {
        "response_mime_type": "application/json",
        "temperature": 0.1
    }
}

try:
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    resp_json = response.json()

    if response.status_code != 200:
        print(f"[AI Agent Error] API returned status {response.status_code}: {resp_json.get('error', resp_json)}")
        sys.exit(0)

    raw_text = resp_json["candidates"][0]["content"]["parts"][0]["text"]
    data = json.loads(raw_text)

    print("\n" + "=" * 60)
    print("           🤖 AI AGENT CI/CD TRIAGE & REMEDIATION")
    print("=" * 60)
    print(f"Error Category:   {data.get('error_category')}")
    print(f"Root Cause:       {data.get('root_cause')}")
    print(f"Explanation:      {data.get('explanation')}")
    print("-" * 60)
    print(f"Recommended Fix:\n{data.get('recommended_fix')}")
    print("=" * 60 + "\n")

    # Save output report for artifact archiving or notifications
    with open("ai_triage_report.json", "w") as out:
        out.write(json.dumps(data, indent=2))

except Exception as e:
    print(f"[AI Agent Warning] Failed to process log: {e}")
