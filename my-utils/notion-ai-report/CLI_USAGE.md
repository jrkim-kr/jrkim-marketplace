# Notion AI Report - CLI Usage Guide

## Prerequisites

1.  **Ollama Installed & Running**
    -   **Install**: `brew install ollama`
    -   **Start Service**: `brew services start ollama` (Recommended)
        -   *Alternative*: Run `ollama serve` in a **separate** terminal window and keep it open.
    -   **Download Model**: `ollama pull llama3.2`

2.  **Python Dependencies**
    -   **Install**:
        ```bash
        python3 -m pip install -r requirements.txt
        ```
    -   *Note*: If `pip` command is missing, using `python3 -m pip` is the standard fix on macOS.

## How to Run

Navigate to the skill directory:
```bash
cd /Users/jrkim/.claude/skills/notion-ai-report
```

Run the automation script with a PDF file:
```bash
python3 notion_report_local.py /path/to/your/report.pdf
```

### Options

Specify a different Ollama model:
```bash
python3 notion_report_local.py /path/to/report.pdf --model mistral
```

## Troubleshooting

-   **"Connection Refused"**: Ensure Ollama is running (`ollama serve`).
-   **"File not found"**: Check your PDF path.
-   **"JSON Parse Error"**: The model might have failed to output valid JSON. Try a stronger model (e.g., `llama3` instead of `llama3.2` or `mistral`).
