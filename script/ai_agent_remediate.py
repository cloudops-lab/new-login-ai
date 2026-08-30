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
2. If it is a missing OS package (e.g., 'mvn: not found'), provide the apt/yum install command in 'system_cmd'.
3. If it is a typo or syntax error in a repository file (e.g., 'mvn1' in Jenkinsfile), specify:
   - 'target_file': relative path of the file to fix (e.g., 'Jenkinsfile' or 'jenkinsfile')
   - 'search_string': exact wrong text
   - 'replace_string': correct replacement text

Respond ONLY with a valid JSON object matching this schema:
{{
  "cause": "Short summary",
  "explanation": "concise explanation",
  "is_system_dependency": true or false,
  "system_cmd": "bash install command or empty",
  "target_file": "file name or empty",
  "search_string": "text to replace or empty",
  "replace_string": "replacement text or empty"
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
        print(f"Gemini API Error: {resp_json}")
        sys.exit(1)

    raw_text = resp_json["candidates"][0]["content"]["parts"][0]["text"]
    data = json.loads(raw_text)

    print("\n================ [AI AGENT TRIAGE] ================")
    print(f"Root Cause:     {data.get('cause')}")
    print(f"Explanation:    {data.get('explanation')}")
    print("===================================================\n")

    # 1. System Dependency Self-Healing
    if data.get("is_system_dependency") and data.get("system_cmd"):
        cmd = data.get("system_cmd")
        print(f"[AI Self-Healing] Installing missing system tool: {cmd}")
        subprocess.run(f"sudo {cmd}", shell=True, check=False)

    # 2. Code/Jenkinsfile Self-Healing
    target_file = data.get("target_file")
    search_str = data.get("search_string")
    replace_str = data.get("replace_string")

    if target_file and os.path.exists(target_file) and search_str:
        print(f"[AI Self-Healing] Patching file '{target_file}': replacing '{search_str}' with '{replace_str}'")
        with open(target_file, "r") as f:
            content = f.read()
        
        new_content = content.replace(search_str, replace_str)
        with open(target_file, "w") as f:
            f.write(new_content)
            
        print("[AI Self-Healing] File patched successfully.")

    with open("ai_triage.json", "w") as out:
        out.write(raw_text)

except Exception as e:
    print(f"AI Agent execution failed: {e}")
