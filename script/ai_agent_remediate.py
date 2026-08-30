#!/usr/bin/env python3
import os
import sys
import json
import re
import requests
import subprocess

API_KEY = os.getenv("LLM_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("GROQ_API_KEY")
LOG_FILE = sys.argv[1] if len(sys.argv) > 1 else "pipeline.log"
BRANCH_NAME = "feature/ai-auto-heal"

GIT_USER = os.getenv("GIT_USER", "Chandandhani")
GIT_PASS = os.getenv("GIT_PASS")

if not API_KEY:
    print("[AI Agent Error] LLM_API_KEY environment variable is not set.")
    sys.exit(0)

if not os.path.exists(LOG_FILE):
    print(f"[AI Agent Error] Log file '{LOG_FILE}' not found.")
    sys.exit(0)

with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
    logs = "".join(f.readlines()[-80:])

prompt = f"""
You are an autonomous self-healing DevOps CI/CD AI Agent.
Analyze the following Jenkins failure logs:
---
{logs}
---

Task:
1. Identify the primary root cause.
2. If the issue is due to unsupported Java 1.6 / compiler plugin in pom.xml, configure the patch to change jdk.version from 1.6 to 1.8.
3. Provide the exact text to search and replace in the target file.

Provide your response in JSON format matching this exact schema:
{{
  "error_category": "Category name",
  "root_cause": "Concise summary",
  "explanation": "Detailed explanation",
  "target_file": "pom.xml",
  "search_string": "<jdk.version>1.6</jdk.version>",
  "replace_string": "<jdk.version>1.8</jdk.version>"
}}
"""

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

# Auto-detect available Groq model
model = "llama-3.1-8b-instant"
try:
    models_resp = requests.get("https://api.groq.com/openai/v1/models", headers=headers, timeout=5)
    if models_resp.status_code == 200:
        ids = [m.get("id") for m in models_resp.json().get("data", [])]
        for m_cand in ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "openai/gpt-oss-20b"]:
            if m_cand in ids:
                model = m_cand
                break
except Exception:
    pass

url = "https://api.groq.com/openai/v1/chat/completions"
payload = {
    "model": model,
    "messages": [
        {"role": "system", "content": "You are an automated DevOps assistant. Always respond with valid JSON only."},
        {"role": "user", "content": prompt}
    ],
    "response_format": {"type": "json_object"},
    "temperature": 0.1
}

try:
    response = requests.post(url, headers=headers, json=payload, timeout=35)
    resp_json = response.json()

    if response.status_code != 200:
        print(f"[AI Agent Error] API returned status {response.status_code}: {resp_json}")
        sys.exit(0)

    raw_text = resp_json["choices"][0]["message"]["content"]
    
    match = re.search(r"\{.*\}", raw_text, re.DOTALL)
    if match:
        data = json.loads(match.group(0))
    else:
        data = json.loads(raw_text)

    print("\n" + "=" * 65)
    print("           🤖 AI AGENT CI/CD TRIAGE & AUTO-HEALING")
    print("=" * 65)
    print(f"Model Used:       {model}")
    print(f"Error Category:   {data.get('error_category')}")
    print(f"Root Cause:       {data.get('root_cause')}")
    print(f"Explanation:      {data.get('explanation')}")
    print("-" * 65)

    target_file = data.get("target_file", "pom.xml")
    search_str = data.get("search_string")
    replace_str = data.get("replace_string")

    if os.path.exists(target_file) and search_str and replace_str:
        print(f"[Auto-Healing] Creating feature branch '{BRANCH_NAME}'...")
        subprocess.run(f"git checkout -B {BRANCH_NAME}", shell=True, check=True)

        print(f"[Auto-Healing] Patching '{target_file}': replacing '{search_str}' with '{replace_str}'...")
        with open(target_file, "r", encoding="utf-8") as f:
            file_content = f.read()

        if search_str in file_content:
            patched_content = file_content.replace(search_str, replace_str)
        else:
            patched_content = re.sub(r"<jdk\.version>1\.[56]</jdk\.version>", "<jdk.version>1.8</jdk.version>", file_content)

        with open(target_file, "w", encoding="utf-8") as f:
            f.write(patched_content)

        print(f"[Auto-Healing] '{target_file}' patched successfully!")

        try:
            print(f"[Auto-Healing] Committing and pushing to origin/{BRANCH_NAME}...")
            subprocess.run(f"git config user.name '{GIT_USER}'", shell=True, check=True)
            subprocess.run("git config user.email 'ai-agent@cloudops.internal'", shell=True, check=True)

            if GIT_PASS:
                remote_url = f"https://{GIT_USER}:{GIT_PASS}@github.com/cloudops-lab/loginapp.git"
                subprocess.run(f"git remote set-url origin {remote_url}", shell=True, check=True)

            subprocess.run(f"git add {target_file}", shell=True, check=True)
            subprocess.run("git commit -m 'fix(ci): autonomous patch applied by AI agent'", shell=True, check=True)
            subprocess.run(f"git push -u origin {BRANCH_NAME} --force", shell=True, check=True)
            print(f"[Auto-Healing] Feature branch '{BRANCH_NAME}' pushed successfully to GitHub!")
        except Exception as ge:
            print(f"[Auto-Healing Warning] Git push failed: {ge}")

    print("=" * 65 + "\n")

except Exception as e:
    print(f"[AI Agent Warning] Error: {e}")
