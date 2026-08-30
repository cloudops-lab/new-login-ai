#!/usr/bin/env python3
import os
import sys
import json
import requests
import subprocess

API_KEY = os.getenv("LLM_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("GROQ_API_KEY")
LOG_FILE = sys.argv[1] if len(sys.argv) > 1 else "pipeline.log"

if not API_KEY:
    print("[AI Agent Error] LLM_API_KEY environment variable is not set.")
    sys.exit(0)

if not os.path.exists(LOG_FILE):
    print(f"[AI Agent Error] Log file '{LOG_FILE}' not found.")
    sys.exit(0)

with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
    logs = "".join(f.readlines()[-120:])

pom_content = ""
if os.path.exists("pom.xml"):
    with open("pom.xml", "r", encoding="utf-8") as pf:
        pom_content = pf.read()

prompt = f"""
You are an autonomous self-healing DevOps CI/CD AI Agent.
Analyze the following Jenkins failure logs:
---
{logs}
---
The current workspace 'pom.xml' content is:
---
{pom_content}
---

Task:
1. Identify the root cause of failure.
2. If the issue is fixable in repository files (e.g., 'pom.xml' Java version, plugin version, typo):
   - Set "can_auto_heal": true
   - Set "target_file": "pom.xml"
   - Set "updated_file_content": full updated content for pom.xml with the fix applied (e.g. changing jdk.version from 1.6 to 1.8).
3. If it is a missing system package:
   - Set "can_auto_heal": true
   - Set "system_command": "sudo apt install -y ..."

Respond ONLY with a valid JSON object matching this schema:
{{
  "error_category": "Category name",
  "root_cause": "Concise summary",
  "explanation": "Detailed explanation",
  "can_auto_heal": true,
  "target_file": "pom.xml",
  "updated_file_content": "full updated content or empty string",
  "system_command": "command to run or empty string"
}}
"""

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

# Fetch available Groq models
model = "llama-3.1-8b-instant"
try:
    models_resp = requests.get("https://api.groq.com/openai/v1/models", headers=headers, timeout=5)
    if models_resp.status_code == 200:
        ids = [m.get("id") for m in models_resp.json().get("data", [])]
        for m_candidate in ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "openai/gpt-oss-20b"]:
            if m_candidate in ids:
                model = m_candidate
                break
except Exception:
    pass

url = "https://api.groq.com/openai/v1/chat/completions"
payload = {
    "model": model,
    "messages": [{"role": "user", "content": prompt}],
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
    data = json.loads(raw_text)

    print("\n" + "=" * 65)
    print("           🤖 AI AGENT CI/CD TRIAGE & AUTO-HEALING")
    print("=" * 65)
    print(f"Error Category:   {data.get('error_category')}")
    print(f"Root Cause:       {data.get('root_cause')}")
    print(f"Explanation:      {data.get('explanation')}")
    print("-" * 65)

    if data.get("can_auto_heal"):
        target_file = data.get("target_file")
        updated_content = data.get("updated_file_content")
        if target_file and updated_content and len(updated_content.strip()) > 20:
            print(f"[Auto-Healing] Overwriting and fixing '{target_file}'...")
            with open(target_file, "w", encoding="utf-8") as tf:
                tf.write(updated_content)
            print(f"[Auto-Healing] '{target_file}' patched successfully locally!")

            # Git Auto-Commit & Push back to GitHub
            try:
                print("[Auto-Healing] Pushing fix to remote GitHub repository...")
                subprocess.run("git config user.name 'AI Auto-Healing Agent'", shell=True, check=True)
                subprocess.run("git config user.email 'ai-agent@cloudops.internal'", shell=True, check=True)
                subprocess.run(f"git add {target_file}", shell=True, check=True)
                subprocess.run("git commit -m 'fix(ci): autonomous patch applied by AI agent'", shell=True, check=True)
                subprocess.run("git push origin master", shell=True, check=True)
                print("[Auto-Healing] Changes successfully pushed to GitHub!")
            except Exception as ge:
                print(f"[Auto-Healing Warning] Git push failed: {ge}")

    print("=" * 65 + "\n")

except Exception as e:
    print(f"[AI Agent Warning] Error: {e}")
