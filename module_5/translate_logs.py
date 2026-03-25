"""
读取 run_log.json，调用 Claude 将每条记录的 parsed output 翻译为英文，
生成双语版 run_log.json（每条记录同时包含 parsed_zh 和 parsed_en）。
"""

import json
import os
from datetime import datetime
from pathlib import Path
import anthropic

# 自动加载 .env 文件
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    for _line in _env_path.read_text().splitlines():
        if "=" in _line and not _line.startswith("#"):
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
API_KEY = os.environ.get("ANTHROPIC_API_KEY")
if not API_KEY:
    raise ValueError("ANTHROPIC_API_KEY not set. Please add it to your .env file or environment.")
RUN_LOG_PATH = os.path.join(SCRIPT_DIR, "run_log.json")

client = anthropic.Anthropic(api_key=API_KEY, base_url="https://openrouter.ai/api/v1")

TRANSLATE_PROMPT = """Translate the following JSON object from Chinese to English. 
Keep the exact same JSON structure and keys (do not translate keys). 
Translate ALL Chinese text values to natural, professional English.
For WeChat message drafts, translate the message content faithfully while maintaining the luxury tone.
Return ONLY valid JSON, no markdown fencing, no explanation."""


def translate_parsed(parsed_zh):
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[{
            "role": "user",
            "content": f"{TRANSLATE_PROMPT}\n\n{json.dumps(parsed_zh, ensure_ascii=False, indent=2)}"
        }],
        temperature=0.3,
    )
    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("```json")[-1].split("```")[0].strip() if "```json" in text else text.split("```")[1].split("```")[0].strip()
    return json.loads(text)


def main():
    with open(RUN_LOG_PATH, "r", encoding="utf-8") as f:
        runs = json.load(f)

    for i, run in enumerate(runs):
        parsed = run.get("output", {}).get("parsed")
        if not parsed:
            print(f"  Skipping run {i+1}: no parsed output")
            continue

        if "parsed_en" in run.get("output", {}):
            print(f"  [{i+1}/{len(runs)}] {run['input']['client_name']}: already translated, skipping")
            continue

        print(f"  [{i+1}/{len(runs)}] Translating {run['input']['client_name']}...")
        try:
            parsed_en = translate_parsed(parsed)
            run["output"]["parsed_zh"] = parsed
            run["output"]["parsed_en"] = parsed_en
            print(f"    Done.")
        except Exception as e:
            print(f"    Error: {e}")

    with open(RUN_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(runs, f, ensure_ascii=False, indent=2)

    print(f"\nAll done. Dual-language run_log saved.")


if __name__ == "__main__":
    main()
