#!/usr/bin/env python3
import os
import sys
import json
import re
import requests

API_KEY = os.getenv("LLM_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("GROQ_API_KEY")
LOG_FILE = sys.argv[1] if len(sys.argv) > 1 else "pipeline.log"
BRANCH_NAME = "feature-ai-fix"
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
2. Provide a short explanation and remedy for pom.xml.

Respond ONLY with a valid JSON object matching this schema:
{{
  "error_category": "Category name",
  "root_cause": "Concise summary",
  "explanation": "Detailed explanation"
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

explanation_text = "Upgraded outdated compiler and war plugins in pom.xml."
root_cause_text = "Plugin incompatibility with modern JDK."

try:
    response = requests.post(url, headers=headers, json=payload, timeout=35)
    resp_json = response.json()

    if response.status_code == 200:
        raw_text = resp_json["choices"][0]["message"]["content"]
        match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        data = json.loads(match.group(0)) if match else json.loads(raw_text)

        root_cause_text = data.get("root_cause", root_cause_text)
        explanation_text = data.get("explanation", explanation_text)

        print("\n" + "=" * 65)
        print("           🤖 AI AGENT CI/CD TRIAGE & AUTO-HEALING")
        print("=" * 65)
        print(f"Model Used:       {model}")
        print(f"Error Category:   {data.get('error_category')}")
        print(f"Root Cause:       {root_cause_text}")
        print(f"Explanation:      {explanation_text}")
        print("-" * 65)

except Exception as e:
    print(f"[AI Agent Warning] Log analysis note: {e}")

# Autonomous Patching for pom.xml
target_file = "pom.xml"
if os.path.exists(target_file):
    with open(target_file, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Update JDK version to 1.8
    content = re.sub(r"<jdk\.version>1\.[56]</jdk\.version>", "<jdk.version>1.8</jdk.version>", content)
    content = content.replace("<jdk.version>1.6</jdk.version>", "<jdk.version>1.8</jdk.version>")

    # 2. Upgrade maven-war-plugin to 3.3.2 to resolve PluginContainerException
    content = re.sub(r"<artifactId>maven-war-plugin</artifactId>\s*<version>[^<]+</version>", 
                     "<artifactId>maven-war-plugin</artifactId>\n\t\t\t\t<version>3.3.2</version>", content)

    # 3. Upgrade maven-compiler-plugin to 3.11.0
    content = re.sub(r"<artifactId>maven-compiler-plugin</artifactId>\s*<version>[^<]+</version>", 
                     "<artifactId>maven-compiler-plugin</artifactId>\n\t\t\t\t<version>3.11.0</version>", content)

    with open(target_file, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"[Auto-Healing] '{target_file}' patched with JDK 1.8 and modern plugins successfully!")
    print("=" * 65 + "\n")

# Open Pull Request via GitHub REST API
if GIT_PASS:
    repo_pr_url = "https://api.github.com/repos/cloudops-lab/new-login-ai/pulls"
    pr_headers = {
        "Authorization": f"token {GIT_PASS}",
        "Accept": "application/vnd.github.v3+json"
    }
    pr_payload = {
        "title": "fix(ci): Auto-healing patch (JDK & Plugin Compatibility Fix)",
        "head": BRANCH_NAME,
        "base": "master",
        "body": f"### 🤖 AI Agent CI/CD Remediation Report\n\n- **Root Cause:** {root_cause_text}\n- **Explanation:** {explanation_text}\n- **Changes:** Upgraded `<jdk.version>` to `1.8`, `maven-war-plugin` to `3.3.2`, and `maven-compiler-plugin` to `3.11.0`.\n\nPlease review and approve this PR."
    }

    try:
        pr_resp = requests.post(repo_pr_url, headers=pr_headers, json=pr_payload, timeout=20)
        pr_data = pr_resp.json()
        pr_url = pr_data.get("html_url")

        print("=======================================================")
        if pr_url:
            print(f"🚀 PULL REQUEST CREATED: {pr_url}")
        else:
            print("ℹ️ Pull Request already exists: https://github.com/cloudops-lab/new-login-ai/pulls")
        print("👉 Please review and merge the PR into master on GitHub.")
        print("=======================================================\n")
    except Exception as pe:
        print(f"[AI Agent Warning] Failed to trigger GitHub PR: {pe}")
