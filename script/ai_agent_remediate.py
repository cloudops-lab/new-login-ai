#!/usr/bin/env python3
import os
import sys
import json
import re
import requests

API_KEY = os.getenv("LLM_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("GROQ_API_KEY")
LOG_FILE = sys.argv[1] if len(sys.argv) > 1 else "pipeline.log"
BRANCH_NAME = os.getenv("BRANCH_NAME", "feature-ai-fix")
GIT_PASS = os.getenv("GIT_PASS")

if not API_KEY:
    print("[AI Agent Error] LLM_API_KEY environment variable is not set.")
    sys.exit(0)

if not os.path.exists(LOG_FILE):
    print(f"[AI Agent Error] Log file '{LOG_FILE}' not found.")
    sys.exit(0)

with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
    logs = "".join(f.readlines()[-100:])

# Collect workspace source context
workspace_context = {}
for root, dirs, files in os.walk("."):
    if "/." in root or "/target" in root:
        continue
    print(f"Line 29 {files}")
    for file in files:
        if file in ["Jenkinsfile", "jenkinsfile", "pom.xml"] or file.endswith((".java", ".xml")):
            rel_path = os.path.relpath(os.path.join(root, file), ".")
            try:
                with open(rel_path, "r", encoding="utf-8", errors="ignore") as cf:
                    workspace_context[rel_path] = cf.read()
            except Exception:
                pass

context_str = "\n\n".join([f"=== FILE: {path} ===\n{content}" for path, content in workspace_context.items()])

prompt = f"""
You are an autonomous self-healing DevOps CI/CD AI Agent.
Analyze the following Jenkins failure logs and workspace source files:

--- FAILURE LOGS ---
{logs}

--- REPOSITORY FILES CONTEXT ---
{context_str}

TASK:
1. Identify the exact root cause of the failure.
2. If the issue is a typo like 'mvn1' in the pipeline script, target 'Jenkinsfile' (or 'jenkinsfile').
3. Provide precise search and replacement strings to fix the issue.

Respond ONLY with a valid JSON object matching this schema:
{{
  "error_category": "<category>",
  "root_cause": "<summary>",
  "explanation": "<detailed triage explanation>",
  "patches": [
    {{
      "file_path": "<exact relative path to file, e.g. Jenkinsfile or pom.xml>",
      "search_string": "<exact text to replace>",
      "replace_string": "<exact new corrected text>"
    }}
  ]
}}
"""

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

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

root_cause_text = "Command typo or runtime incompatibility"
explanation_text = "Automated remediation patch applied"
patches_applied = 0

try:
    response = requests.post(url, headers=headers, json=payload, timeout=45)
    resp_json = response.json()

    if response.status_code == 200:
        raw_text = resp_json["choices"][0]["message"]["content"]
        match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        data = json.loads(match.group(0)) if match else json.loads(raw_text)

        root_cause_text = data.get("root_cause", root_cause_text)
        explanation_text = data.get("explanation", explanation_text)
        patches = data.get("patches", [])

        print("\n" + "=" * 65)
        print("           🤖 DYNAMIC AI AGENT CI/CD REMEDIATION")
        print("=" * 65)
        print(f"Model Used:       {model}")
        print(f"Error Category:   {data.get('error_category')}")
        print(f"Root Cause:       {root_cause_text}")
        print(f"Explanation:      {explanation_text}")
        print("-" * 65)

        for p in patches:
            target_path = p.get("file_path")
            search_str = p.get("search_string")
            replace_str = p.get("replace_string")

            # Resolve file path casing if needed
            if target_path and not os.path.exists(target_path):
                if target_path.lower() == "jenkinsfile":
                    target_path = "Jenkinsfile" if os.path.exists("Jenkinsfile") else "jenkinsfile"

            if target_path and os.path.exists(target_path) and search_str:
                with open(target_path, "r", encoding="utf-8") as f:
                    file_content = f.read()

                if search_str in file_content:
                    file_content = file_content.replace(search_str, replace_str)
                    with open(target_path, "w", encoding="utf-8") as f:
                        f.write(file_content)
                    print(f" [Auto-Patch Applied] Successfully patched '{target_path}'")
                    patches_applied += 1
                else:
                    # Fallback regex if exact string had whitespace differences
                    if "mvn1" in search_str and "mvn1" in file_content:
                        file_content = re.sub(r"\bmvn1\b", "mvn", file_content)
                        with open(target_path, "w", encoding="utf-8") as f:
                            f.write(file_content)
                        print(f" [Auto-Patch Applied] Replaced 'mvn1' in '{target_path}'")
                        patches_applied += 1

        # Direct fallback for mvn1 in Jenkinsfile if not covered by LLM patch
        for jf in ["Jenkinsfile", "jenkinsfile"]:
            if os.path.exists(jf):
                with open(jf, "r", encoding="utf-8") as f:
                    content = f.read()
                if "mvn1" in content:
                    content = re.sub(r"\bmvn1\b", "mvn", content)
                    with open(jf, "w", encoding="utf-8") as f:
                        f.write(content)
                    print(f" [Auto-Healing] Corrected 'mvn1' to 'mvn' in '{jf}'")
                    patches_applied += 1

        print("=" * 65 + "\n")

except Exception as e:
    print(f"[AI Agent Error] Dynamic triage error: {e}")

# --- Create GitHub Pull Request ---
if GIT_PASS:
    repo_pr_url = "https://api.github.com/repos/cloudops-lab/new-login-ai/pulls"
    pr_headers = {
        "Authorization": f"token {GIT_PASS}",
        "Accept": "application/vnd.github.v3+json"
    }
    pr_payload = {
        "title": f"fix(ci): Auto-healing patch ({BRANCH_NAME})",
        "head": BRANCH_NAME,
        "base": "master",
        "body": f"### 🤖 Dynamic AI CI/CD Auto-Healing Report\n\n- **Root Cause:** {root_cause_text}\n- **Explanation:** {explanation_text}\n- **Patches Applied:** {patches_applied} change(s).\n\nPlease review and approve this PR."
    }

    try:
        pr_resp = requests.post(repo_pr_url, headers=pr_headers, json=pr_payload, timeout=20)
        pr_data = pr_resp.json()
        pr_url = pr_data.get("html_url")

        print("=======================================================")
        if pr_url:
            print(f"🚀 PULL REQUEST CREATED: {pr_url}")
        else:
            print("ℹ️ Pull Request Status: https://github.com/cloudops-lab/new-login-ai/pulls")
        print("👉 Please review and merge the PR into master on GitHub.")
        print("=======================================================\n")
    except Exception as pe:
        print(f"[AI Agent Warning] PR creation notice: {pe}")
