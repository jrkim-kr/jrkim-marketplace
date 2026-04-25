#!/usr/bin/env python3
"""
Notion AI Report - Local LLM Automation (Ollama)

This script automates the workflow:
1. proper PDF text extraction
2. Analysis using Local LLM (Ollama)
3. JSON generation
4. Notion Page Creation (calling create_notion_page.py)

Usage:
    python3 notion_report_local.py <pdf_path> [--model llama3.2]
"""

import argparse
import json
import os
import sys
import subprocess
import datetime
import re
from pathlib import Path

import site

# Try to add user site packages to path automatically (common issue on macOS)
user_site = site.getusersitepackages()
if user_site and user_site not in sys.path:
    sys.path.append(user_site)

try:
    import requests
    from pypdf import PdfReader
except ImportError:
    print("Error: Missing dependencies.")
    print("Please run this command to install them:")
    print(f"{sys.executable} -m pip install pypdf requests")
    sys.exit(1)

# Configuration
OLLAMA_API_URL = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "llama3.2"  # User can override
SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
CREATE_PAGE_SCRIPT = os.path.join(SKILL_DIR, "create_notion_page.py")
OUTPUT_DIR = os.path.expanduser("~/Projects/Personal/notion-ai-report-logger/reports/json")

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

SYSTEM_PROMPT = """
You are an expert AI Analyst. Your task is to analyze the provided PDF text and extract structured data for a Notion database.
You MUST output ONLY valid JSON. Do not include markdown formatting (like ```json).

# Database Schema & Extraction Rules

1. **보고서명 (Report Title)**: Extract accurately from the cover or first page.
2. **발행일 (Date)**: Format YYYY-MM-DD.
3. **발행기관 (Organization)**: e.g., McKinsey, SPRi, etc.
4. **카테고리 (Category)**: Choose EXACTLY ONE from: ["전략 / 산업", "ROI / 시장", "기술 트랜드", "정책 / 규제"]
   - 전략 / 산업: Business strategy, industry application
   - ROI / 시장: Market size, economic impact
   - 기술 트랜드: Tech trends, new capabilities
   - 정책 / 규제: Policy, laws, ethics, governance
5. **주제 (Topics)**: List of relevant tags (e.g., ["AI 자동화", "Agentic AI"]).
6. **요약 (Summary)**: 3-5 key sentences. Format: "1. Sentence\\n2. Sentence\\n3. Sentence"
7. **한 문장 정의 (One-line Definition)**: "This report is about [Topic] for [Purpose]."
8. **PM 핵심 질문 (PM Key Questions)**:
   - First, determine the Category.
   - Then, select the corresponding 3 fixed questions from the table below.
   - Finally, extract answers for these 3 questions from the text.
   - Format: "Q1. [Question]\\nA1. [Answer]\\n\\nQ2. ...\\nA2. ..."
   - If answer not found, use "(보고서에서 직접 다루지 않음)".

   [Category: 전략 / 산업]
   Q1: 이 기술은 업무 구조를 어떻게 바꾸는가?
   Q2: 판단·책임은 조직 내 누구에게 이동하는가?
   Q3: 지금 PoC로 시작해도 되는 영역은 어디인가?

   [Category: ROI / 시장]
   Q1: 시장은 얼마나 크고 얼마나 빠르게 커지는가?
   Q2: 고객은 무엇에 실제로 돈을 쓰는가?
   Q3: 우리 포지션은 비용 절감 vs 매출 기여 중 어디인가?

   [Category: 기술 트랜드]
   Q1: 기술의 Before / After는 무엇인가?
   Q2: 기존 한계를 질적으로 깨는 변화인가?
   Q3: 지금은 실험 단계 vs 적용 단계인가?

   [Category: 정책 / 규제]
   Q1: 무엇이 금지 / 제한 / 권고인가?
   Q2: 리스크는 법적·평판·운영 중 어디에 있는가?
   Q3: PM이 선제 차단해야 할 지점은?

9. **PM 한 줄 결론 (PM Insight)**: One key insight for a Product Manager.
10. **상태 (Status)**: Always "Not started".
11. **작성일 (Created Date)**: Today's date (YYYY-MM-DD).
12. **URL**: Leave empty (or user provided).

# Output Format (JSON)
{
  "보고서명": "String",
  "발행일": "YYYY-MM-DD",
  "발행기관": "String",
  "카테고리": "String",
  "주제": ["String", "String"],
  "요약": "String",
  "한 문장 정의": "String",
  "PM 핵심 질문": "String",
  "PM 한 줄 결론": "String",
  "상태": "Not started",
  "작성일": "YYYY-MM-DD"
}
"""

def extract_text(pdf_path):
    print(f"Reading PDF: {pdf_path}...")
    try:
        reader = PdfReader(pdf_path)
        text = ""
        # Limit to first 30 pages to avoid context window overflow if too large, 
        # but for local models we need to be careful. Llama 3 has 8k context usually.
        # Let's be conservative and take first 10k characters or first 10 pages.
        max_pages = min(len(reader.pages), 15) 
        for i in range(max_pages):
            text += reader.pages[i].extract_text() + "\n"
        return text
    except Exception as e:
        print(f"Error reading PDF: {e}")
        sys.exit(1)

def call_ollama(text, model):
    print(f"Analyzing with Ollama ({model})...")
    
    # Calculate today's date for the prompt
    today = datetime.date.today().strftime("%Y-%m-%d")
    final_system_prompt = SYSTEM_PROMPT.replace("Today's date (YYYY-MM-DD)", today)
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": final_system_prompt},
            {"role": "user", "content": f"Analyze this report content:\n\n{text[:6000]}"} # Truncate to safe limit for diverse hardware
        ],
        "stream": False,
        "options": {
            "temperature": 0.1  # Low temperature for factual extraction
        }
    }

    try:
        response = requests.post(OLLAMA_API_URL, json=payload)
        if response.status_code != 200:
            print(f"Ollama Error ({response.status_code}): {response.text}")
        response.raise_for_status()
        result = response.json()
        content = result["message"]["content"]
        return content
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to Ollama.")
        print("Make sure Ollama is running (try 'ollama serve' or check menu bar).")
        sys.exit(1)
    except Exception as e:
        print(f"Ollama API Error: {e}")
        sys.exit(1)

def parse_json(content):
    # Try to find JSON block
    match = re.search(r'\{.*\}', content, re.DOTALL)
    if match:
        json_str = match.group(0)
    else:
        json_str = content

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        print("Error: Failed to parse JSON from LLM response.")
        print("Raw Output:\n", content)
        sys.exit(1)

def save_json_file(data):
    # Filename generation: YYYYMM_Agency_Title_Date.json
    try:
        pub_date = data.get("발행일", "2024-01-01").replace("-", "")[:6] # YYYYMM
        agency = data.get("발행기관", "Unknown").replace(" ", "")
        title_slug = data.get("보고서명", "Report")[:10].replace(" ", "-") # Simple slug
        today = datetime.date.today().strftime("%Y%m%d")
        
        filename = f"{pub_date}_{agency}_{title_slug}_{today}.json"
        # Sanitize filename
        filename = re.sub(r'[^\w\-_\.]', '', filename)
        
        filepath = os.path.join(OUTPUT_DIR, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"Saved analysis to: {filepath}")
        return filepath
    except Exception as e:
        print(f"Error saving file: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Analyze PDF and upload to Notion using Local LLM")
    parser.add_argument("pdf_path", help="Path to the PDF file")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Ollama model to use (default: llama3.2)")
    args = parser.parse_args()

    if not os.path.exists(args.pdf_path):
        print(f"Error: File not found: {args.pdf_path}")
        sys.exit(1)

    # 1. Extract
    text = extract_text(args.pdf_path)

    # 2. Analyze
    llm_response = call_ollama(text, args.model)
    
    # 3. Parse
    data = parse_json(llm_response)
    
    # 4. Save
    json_path = save_json_file(data)
    
    if json_path:
        # 5. Upload to Notion
        print("Uploading to Notion...")
        subprocess.run([sys.executable, CREATE_PAGE_SCRIPT, "--file", json_path])

if __name__ == "__main__":
    main()
