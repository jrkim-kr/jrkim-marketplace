---
description: Analyze a local PDF and create a page in the Notion "AI Report Study" database with PM-framework study notes
argument-hint: "<PDF file path>"
---

Plugin asset directory for this command: `${CLAUDE_PLUGIN_ROOT}/notion-ai-report`

# Notion AI Report Logger

## Purpose

A meta-database that **accumulates AI/Agentic/automation reports organized by PM judgment questions and decision-making frameworks**.
When the user provides an AI-related report PDF, analyze its content and automatically create a page in the Notion "AI Report Study" database with all fields populated.

## Input

The user provides a local PDF file path via `$ARGUMENTS`:

- **Local PDF file path** — e.g., `/Users/jrkim/Downloads/report.pdf`

## Notion Database Information

- **API Key**: read from `$NOTION_API_KEY` environment variable
- **Database ID**: `309341dc2a9380ed9001caa63f9f45ba`
- **Notion Version**: `2022-06-28`

### Database Field Schema

| Field Name | Type | Existing Options | Description |
|-----------|------|-----------------|-------------|
| **Report Title** | title | — | Original report title |
| **URL** | url | — | Original PDF link |
| **Publication Date** | date | — | Report publication date (YYYY-MM-DD) |
| **Publisher** | select | McKinsey, Samjong KPMG, Snowflake, SPRi | Publishing organization |
| **Category** | select | Strategy / Industry, ROI / Market, Tech Trends, Policy / Regulation | Report topic classification |
| **Topics** | multi_select | AI Automation, Agentic AI, Industry Applications, ROI | Related topic tags (multiple) |
| **Summary** | rich_text | — | Core content summary (3-5 sentences) |
| **One-Sentence Definition** | rich_text | — | Define this report in one sentence |
| **PM Key Questions** | rich_text | — | Key questions this report answers from a PM perspective |
| **PM One-Line Conclusion** | rich_text | — | One-line key insight for PMs |
| **Status** | status | Not started, In progress, Done | Study status |
| **Created Date** | date | — | Notion page creation date (today's date) |
| **Completion Date** | date | — | Report study completion date (user fills manually, command leaves empty) |

---

## PM Key Questions by Report Type (Fixed)

Once the category is determined, PM key questions are **automatically mapped from the table below**. They are not extracted from the PDF.

| Category | Key Sources | Why a PM Reads This Report | PM Key Questions (Fixed 3) | Strengthened Record Areas | Intentionally De-emphasized/Excluded |
|----------|------------|---------------------------|---------------------------|--------------------------|-------------------------------------|
| **Strategy / Industry** | KPMG, McKinsey, Deloitte, Accenture | *Where and in what structure should AI be used?* | • How does this technology change **work structures**?\n• To whom does **judgment and responsibility** shift within the org?\n• Where can we **start a PoC now**? | Judgment checklists, org/responsibility structure, decision points | Model architecture, algorithm details |
| **ROI / Market** | IDC, CB Insights, PitchBook | *Does this make money? Is there scale?* | • How **big and fast** is the market growing?\n• What are customers **actually spending money on**?\n• Is our position **cost reduction vs revenue contribution**? | KPI/metric summaries, unit price/ROI logic | Agent autonomy debate, abstract future vision |
| **Tech Trends** | AI Index, OpenAI/Google releases, paper meta | *What's now possible, and what will be soon?* | • What is the technology's **Before / After**?\n• Is this a **qualitative breakthrough** over previous limitations?\n• Is this currently at **experimental vs deployment stage**? | Technology change summary, capability boundaries | Org/responsibility design |
| **Policy / Regulation** | Government, EU, public institutions, AI ethics reports | *How far is too far?* | • What is **prohibited / restricted / recommended**?\n• Is the risk **legal, reputational, or operational**?\n• What should PMs **preemptively block**? | Risk map, governance checks | PoC ideas, performance discussion |

## Study Notes Structure (2-Layer Question Framework)

Generate structured study notes in the **body (children blocks)** of the Notion page.
DB fields are for search/comparison metadata; the body is for in-depth study records.

### DB Fields vs Body Role Separation

| Aspect | DB Fields (properties) | Body (children blocks) |
|--------|----------------------|----------------------|
| Purpose | Search, filter, compare | Study, depth, records |
| PM Key Questions | Fixed questions + concise answers (1-2 sentences) | Fixed questions detailed answers + unique questions |
| Across reports | Same category = same questions | Different per report |

### 2-Layer Question Framework

| Layer | Name | Source | Purpose |
|-------|------|--------|---------|
| **Layer 1** | Fixed Frame Questions | Category-specific fixed table (see above) | Horizontal comparison across reports in same category |
| **Layer 2** | Report-Specific Questions | Derived from PDF content | Vertical depth unique to this report |

### Layer 2 Unique Question Derivation Criteria (Fixed)

Questions differ per report, but the **3 derivation criteria are fixed**:

| Derivation Criterion | Question Form | Description |
|---------------------|---------------|-------------|
| **Differentiation** | "Unlike other reports, this report argues ___" | Unique perspective only this report covers |
| **Counter-intuitive** | "Generally ___ is assumed, but this report says ___" | Claims contrary to common belief |
| **Actionable** | "A criterion usable for ___ decisions starting tomorrow" | Immediately applicable decision criteria |

### Body 6-Section Template

Apply the same 6-section structure to all reports:

| Section | Notion Block | Content |
|---------|-------------|---------|
| **① One-Sentence Definition** | callout (💡) + callout (⚡) | Core definition + 3-second summary |
| **② Fixed Frame Questions** | heading_2 + toggle × 3 | Layer 1: Category-fixed Q1~Q3 detailed answers |
| **③ Report-Specific Questions** | callout (derivation criteria) + toggle × 3 | Layer 2: Differentiation/Counter-intuitive/Actionable Q4~Q6 answers |
| **④ Thinking Framework & Decision Criteria** | table + callout + bulleted_list | Before/After transition + suitable task conditions |
| **⑤ PM Checklist** | to_do × 5 | Practical judgment checklist (reusable) |
| **⑥ Application & Conclusion** | toggle + quote | PoC areas + report connections + final conclusion |

### Common Pattern for Toggle Internals

```
toggle title (question, bold)
├── quote: core answer (1-2 sentences)
├── detailed evidence (numbered_list / bulleted_list / table)
└── callout (💬): PM one-line summary
```

### Block Type Mapping

| Content Type | Notion Block | Icon |
|-------------|-------------|------|
| Key insight highlight | callout | 💡 definition, ⚡ summary, 🎯 compression, ⚠️ risk, 💬 PM summary, 👤 role, 📌 criteria, 📍 position |
| Collapsible detail | toggle | — |
| Comparison structure | table + table_row | — |
| Action items | to_do | — |
| Key conclusion quote | quote | — |
| Lists | bulleted_list_item / numbered_list_item | — |
| Section divider | divider | — |

---

## Execution Steps

### Step 1: Read PDF File

- Use the Read tool to directly read the PDF file.
- For files that are too large, use the `pages` parameter for chunked reading (max 20 pages at a time).

### Step 2: Analyze PDF Content and Extract Fields

Analyze the PDF content and extract the following fields. **All content must be based on the PDF source material.**

#### Field Extraction Guide:

1. **Report Title**: Extract the exact report title from the cover page or first page
2. **Publication Date**: Extract the publication date from cover, preface, or body (YYYY-MM-DD format)
3. **Publisher**: The organization that authored/published the report
   - If not in existing options, use a new value (Notion select auto-creates new options)
4. **Category**: Classify the report topic into the most fitting of the 4 existing categories
   - `Strategy / Industry`: Industry strategy, business strategy, AI application by industry
   - `ROI / Market`: Market size, investment returns, economic impact
   - `Tech Trends`: Technology trends, new AI technologies, technological advancement
   - `Policy / Regulation`: AI policy, regulation, governance, ethics
   - If none fit perfectly, choose the closest match
5. **Topics**: Select 1 or more related topic tags
   - New tags can be added beyond existing options if needed
6. **Summary**: Summarize the report's core content in 3-5 sentences. Write one sentence per line, separated by numbered format (`1. 2. 3.`) with line breaks
   - Format: `1. First sentence\n2. Second sentence\n3. Third sentence`
7. **One-Sentence Definition**: Format as "This report is a ___ about ___"
8. **PM Key Questions**: **Automatically map 3 questions from the fixed table based on category**, and **extract answers from PDF content** in Q&A format.
   - Format: `Q1. [Fixed question]\nA1. [PDF-based answer, 1-2 sentences]\n\nQ2. ...\nA2. ...\n\nQ3. ...\nA3. ...`
   - Answers must be based on PDF source material, written concisely in 1-2 sentences
   - If no answer can be found in the PDF, note `(Not directly addressed in the report)`
9. **PM One-Line Conclusion**: One-line key insight PMs should take from this report
10. **Status**: `Not started` (default — not yet studied)
11. **Created Date**: Today's date (YYYY-MM-DD)
12. **URL**: Only fill if the user provides one separately
13. **Body Study Notes**: Generate structured study notes for the Notion page body following the 6-section template from the "Study Notes Structure" section above. Layer 1 covers detailed answers to category-fixed questions; Layer 2 derives unique questions from the PDF based on the derivation criteria (differentiation/counter-intuitive/actionable) and answers them.

### Step 3: User Confirmation

Present the extracted field values in a table for user review:

```
## Extraction Results

| Field | Value |
|-------|-------|
| Report Title | ... |
| Publisher | ... |
| Publication Date | ... |
| Category | ... |
| Topics | ... |
| One-Sentence Definition | ... |
| Summary | ... |
| PM Key Questions | ... |
| PM One-Line Conclusion | ... |

Create the Notion page?
```

Use AskUserQuestion to confirm:
- "Create now" — Create with the content as shown
- "Edit then create" — Tell me what to modify

### Step 4: Save Local Files

Before creating the Notion page, save the extracted data to the local project.

**Project path**: `/Users/jrkim/Projects/Personal/notion-ai-report-logger/`

**Directory structure**:
```
notion-ai-report-logger/
├── ai-reports/              ← Original PDF storage
├── reports/                 ← Extraction results
│   ├── md/                  ← Markdown summary files
│   └── json/                ← Notion API data files (notion_report_data.json)
└── .claude/
```

**Filename convention**: `{pub_year_month}_{publisher}_{abbreviated_title}_{created_date(YYYYMMDD)}.{md|json}`
- Publication year-month: `YYYYMM` (e.g., `202509`)
- Publisher: Organization name as-is (e.g., `McKinsey`)
- Abbreviated title: 2-3 keywords joined by `-` (e.g., `AI-Agent-Innovation`)
- Created date: `YYYYMMDD` (e.g., `20260216`)

**4-1. Save JSON file** (`reports/json/`):

```json
{
  "report_title": "Report Title",
  "url": "https://...",
  "publication_date": "2025-01-15",
  "publisher": "McKinsey",
  "category": "Strategy / Industry",
  "topics": ["AI Automation", "Agentic AI"],
  "summary": "1. First key point\n2. Second key point\n3. Third key point",
  "one_sentence_definition": "This report is...",
  "pm_key_questions": "Q1. ...\nA1. ...\n\nQ2. ...\nA2. ...\n\nQ3. ...\nA3. ...",
  "pm_one_line_conclusion": "One-line conclusion...",
  "status": "Not started",
  "created_date": "2026-02-16"
}
```

**4-2. Save Markdown file** (`reports/md/`):

Organize report information into a structured Markdown table:
- Basic info table (report title, publisher, publication date, category, topics, status, created date)
- One-sentence definition (placed before summary)
- Summary (numbered list)
- PM key questions (Q&A format, questions in bold)
- PM one-line conclusion
- Original PDF reference path

### Step 5: Create Notion Page

After confirmation, use the following Python scripts bundled with this plugin.

**Script paths** (inside this plugin):
- `${CLAUDE_PLUGIN_ROOT}/notion-ai-report/create_notion_page.py`
- `${CLAUDE_PLUGIN_ROOT}/notion-ai-report/append_study_notes.py`

Usage:
```bash
# Create new page
python3 "${CLAUDE_PLUGIN_ROOT}/notion-ai-report/create_notion_page.py" --file /path/to/reports/json/{filename}.json

# Append study notes to existing page
python3 "${CLAUDE_PLUGIN_ROOT}/notion-ai-report/append_study_notes.py" --input /path/to/reports/study_notes/{filename}.json

# Dry-run (create blocks only, no API calls)
python3 "${CLAUDE_PLUGIN_ROOT}/notion-ai-report/append_study_notes.py" --input study_notes.json --dry-run
```

### Step 6: Report Results

On success:
```
✅ Complete!
- Report Title: [title]
- Notion URL: [Notion URL]
- Local MD: reports/md/{filename}.md
- Local JSON: reports/json/{filename}.json
```

On failure, inform the user of the error and suggest solutions.

---

## Batch Processing

If the user wants to process multiple PDFs at once:
1. Receive the file path list
2. Repeat Steps 1-5 sequentially for each PDF
3. After processing, show a summary table of all results

---

## Error Handling

| Situation | Response |
|-----------|----------|
| Cannot read PDF | Request file path verification, validate file format |
| PDF contains only scanned images | Inform OCR is not supported, suggest manual input |
| Notion API error | Handle by error code (401: check API key, 404: check DB ID) |
| Cannot extract field value | Leave field empty and notify user |

---

## Notes

- Extract report content **accurately**. Do not speculate.
- Leave fields empty and notify user when they cannot be clearly confirmed from the PDF.
- Consider Notion API rich_text limit (2000 chars) and split processing accordingly.
- Inform the user in advance when new options are needed for publisher/category/topics.
