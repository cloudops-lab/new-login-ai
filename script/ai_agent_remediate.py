import os
import sys
import json
import requests

API_KEY = os.getenv("LLM_API_KEY") or os.getenv("GEMINI_API_KEY")
LOG_FILE = sys.argv[1] if len(sys.argv) > 1 else "pipeline.log"

if not API_KEY:
    print("[AI Agent Error] LLM_API_KEY environment variable is not set.")
    sys.exit(0)

if not os.path.exists(LOG_FILE):
    print(f"[AI Agent Error] Log file '{LOG_FILE}' not found.")
    sys.exit(0)

with open(LOG_FILE, "r") as f:
    logs = "".join(f.readlines()[-120:])

prompt = f"""
You are an expert Autonomous DevOps CI/CD AI Agent.
Analyze the following Jenkins failure logs:
---
{logs}
---
Instructions:
1. Identify the primary root cause (e.g., Maven compiler error, missing package, shell typo, missing deployment repo).
2. Explain why it failed clearly.
3. Provide the exact step-by-step fix, including code/pom.xml changes or commands.

Respond ONLY with a valid JSON object matching this schema:
{{
  "error_category": "Category name",
  "root_cause": "Concise summary of the root cause",
  "explanation": "Detailed explanation of what failed and why",
  "recommended_fix": "Exact code, configuration, or shell command to resolve the failure"
}}
"""

# Groq OpenAI-compatible endpoint
url = "https://api.groq.com/openai/v1/chat/completions"
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

payload = {
    "model": "llama-3.1-8b-instant",
    "messages": [{"role": "user", "content": prompt}],
    "response_format": {"type": "json_object"},
    "temperature": 0.1
}

try:
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    resp_json = response.json()

    if response.status_code != 200:
        print(f"[AI Agent Error] API returned status {response.status_code}: {resp_json}")
        sys.exit(0)

    raw_text = resp_json["choices"][0]["message"]["content"]
    data = json.loads(raw_text)

    print("\n" + "=" * 65)
    print("           🤖 AI AGENT CI/CD TRIAGE & REMEDIATION")
    print("=" * 65)
    print(f"Error Category:   {data.get('error_category')}")
    print(f"Root Cause:       {data.get('root_cause')}")
    print(f"Explanation:      {data.get('explanation')}")
    print("-" * 65)
    print(f"Recommended Fix:\n{data.get('recommended_fix')}")
    print("=" * 65 + "\n")

    with open("ai_triage_report.json", "w") as out:
        out.write(json.dumps(data, indent=2))

except Exception as e:
    print(f"[AI Agent Warning] Failed to process log: {e}")
