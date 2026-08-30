#!/usr/bin/env python3
import os
import sys
import json
import requests

API_KEY = os.getenv("LLM_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("GROQ_API_KEY")
LOG_FILE = sys.argv[1] if len(sys.argv) > 1 else "pipeline.log"

if not API_KEY:
    print("[AI Agent Error] No API Key provided. Set LLM_API_KEY environment variable.")
    sys.exit(0)

if not os.path.exists(LOG_FILE):
    print(f"[AI Agent Error] Log file '{LOG_FILE}' not found.")
    sys.exit(0)

# Read the last 150 lines where failure stacktraces occur
with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
    logs = "".join(f.readlines()[-150:])
print(logs)
prompt = f"""
You are an expert Autonomous DevOps CI/CD AI Agent.
Analyze the following Jenkins failure logs:
---
{logs}
---
Instructions:
1. Identify the primary root cause.
2. Determine which layer failed (e.g., Maven/Java compiler version issue, dependency failure, typo, permission).
3. Provide the exact step-by-step fix (exact XML snippet for pom.xml or shell commands).

Respond ONLY with a valid JSON object matching this schema:
{{
  "error_category": "Category name",
  "root_cause": "Concise summary of the root cause",
  "explanation": "Detailed explanation of what failed and why",
  "recommended_fix": "Exact code, configuration, or shell command to resolve the failure"
}}
"""

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

# Step 1: Detect active available model dynamically from Groq account
candidate_models = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "openai/gpt-oss-20b"]
selected_model = candidate_models[0]

try:
    models_resp = requests.get("https://api.groq.com/openai/v1/models", headers=headers, timeout=10)
    if models_resp.status_code == 200:
        available_ids = [m.get("id") for m in models_resp.json().get("data", [])]
        for candidate in candidate_models:
            if candidate in available_ids:
                selected_model = candidate
                break
        else:
            # Fallback to the first available text model if none matched
            if available_ids:
                selected_model = available_ids[0]
except Exception:
    selected_model = "llama-3.1-8b-instant"

# Step 2: Send Triage Query
url = "https://api.groq.com/openai/v1/chat/completions"
payload = {
    "model": selected_model,
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
    print(f"Model Used:       {selected_model}")
    print(f"Error Category:   {data.get('error_category')}")
    print(f"Root Cause:       {data.get('root_cause')}")
    print(f"Explanation:      {data.get('explanation')}")
    print("-" * 65)
    print("Recommended Fix:")
    print(data.get("recommended_fix"))
    print("=" * 65 + "\n")

    with open("ai_triage_report.json", "w", encoding="utf-8") as out:
        out.write(json.dumps(data, indent=2))

except Exception as e:
    print(f"[AI Agent Warning] Failed to process log: {e}")
