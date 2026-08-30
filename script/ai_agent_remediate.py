import os
import sys
import subprocess
import requests

LLM_API_KEY = os.getenv("LLM_API_KEY")
LOG_FILE = sys.argv[1] if len(sys.argv) > 1 else "pipeline.log"

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
2. If the failure is due to a missing tool/package on Ubuntu/Debian (e.g. 'mvn: not found'), provide the exact shell command to install it.
3. If it is a code/test failure, explain the fix.

Respond ONLY in valid JSON matching this schema:
{{
  "cause": "Short summary",
  "missing_tool": true or false,
  "remediation_cmd": "exact bash command to fix or empty string",
  "explanation": "concise explanation"
}}
"""

try:
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {LLM_API_KEY}"},
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
            "temperature": 0.1
        },
        timeout=30
    )
    
    import json
    result = response.json()["choices"][0]["message"]["content"]
    data = json.loads(result)

    print("=== [AI AGENT TRIAGE] ===")
    print(f"Cause: {data.get('cause')}")
    print(f"Explanation: {data.get('explanation')}")

    # Self-Healing Execution
    if data.get("missing_tool") and data.get("remediation_cmd"):
        cmd = data.get("remediation_cmd")
        print(f"\n[AI Self-Healing] Executing detected fix: {cmd}")
        # Execute the auto-fix if passwordless sudo or user permissions allow
        subprocess.run(cmd, shell=True, check=False)

    with open("ai_triage.json", "w") as out:
        out.write(result)

except Exception as e:
    print(f"AI Agent execution failed: {e}")
