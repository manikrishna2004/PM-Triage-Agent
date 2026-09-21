# Infiheal PM Triage Agent

An automated **Product Management (PM) triage and analytics agent** built for Infiheal / Healo. It converts daily product analytics emails into a concise executive digest by combining current-day metrics, historical baselines, test-level funnel data, and product context.

The agent is designed to answer a PM's most important daily question:

> **What changed, why might it have changed, and what should I investigate next?**

---

## Overview

The pipeline automates five major steps:

```text
Daily Analytics Email
        │
        ▼
 Gmail / IMAP ingestion
        │
        ▼
 Dynamic HTML metric parsing
        │
        ├──────────────► Top 5 test metrics
        │
        ▼
 Master Excel history
        │
        ├──────────────► 7-day baseline
        ├──────────────► 30-day baseline
        └──────────────► Test history baseline
        │
        ▼
 Gemini 2.5 Flash
        │
        ▼
 PM Triage Digest
        │
        ▼
 HTML Email Delivery
```

The agent also loads product-context `.docx` files from its own directory so the LLM can interpret metrics using the product's existing funnel definitions, user behavior observations, test categories, and previous analysis.

---

## Why this agent exists

A conventional analytics dashboard can show:

- signups
- logins
- test starts
- test completions
- chat messages
- engagement
- home-page activity
- premium-test interactions

But a PM still has to manually connect these numbers.

This agent performs that first layer of diagnostic reasoning automatically.

Instead of reporting:

> "Test completion fell by 18%."

it is instructed to investigate relationships such as:

```text
Stable test starts
        +
Lower completions
        +
Higher signup/login-wall encounters
        ↓
Possible conversion friction around the submission wall
```

The goal is **cross-metric diagnosis rather than isolated metric reporting**.

---

# Core Capabilities

## 1. Automated Gmail ingestion

The agent connects to Gmail through IMAP and searches for the latest email with the subject:

```text
Daily Analysis Data
```

It extracts the HTML body and passes it to the metric parser.

### Validation

The pipeline checks that the email corresponds to the expected previous day. Stale or mismatched reports are skipped instead of being blindly analyzed.

---

## 2. Dynamic analytics parsing

The HTML report is parsed using:

- `BeautifulSoup`
- regular expressions
- dynamic table extraction

The parser separates:

### General metrics

Examples include:

- signup attempts
- completed signups
- sign-in attempts
- completed sign-ins
- conversation IDs
- unique users
- messages sent
- chat spend
- returning users
- Home activity
- Healo activity
- SEO/test traffic
- test starts
- test completions
- signup/login-wall encounters
- premium-test interactions
- Healo redirects

### Test-level metrics

For each detected test, the agent extracts:

```text
Starts
Finishes
Completion Rate
```

Completion rate is calculated as:

```text
Completion Rate = Finishes / Starts × 100
```

The parser also calculates:

```text
Total Daily Signups
```

by aggregating the configured signup streams.

---

# 3. Historical baseline engine

The agent maintains an Excel-based analytics history:

```text
infiheal_metrics_master.xlsx
```

It maintains two logical sheets:

### `Main Metrics`

Stores daily general product metrics.

### `Top 5 Tests`

Stores daily test-level:

- Starts
- Finishes
- Completion Rate

The historical data is used to calculate:

- 7-day averages
- 30-day averages
- test-specific historical baselines

This gives the LLM context for distinguishing meaningful changes from normal daily noise.

---

# 4. Anomaly detection

Anomaly detection is the central purpose of the agent.

The system prompt explicitly prioritizes unusual:

- spikes
- steep drops
- unexpected breaks
- funnel discontinuities
- cross-metric inconsistencies

The intended analysis puts substantial attention on anomalies rather than simply summarizing every available metric.

## Test anomaly rules

### Sudden New Entrant

If a test appears in today's top tests but does not exist in the historical test baseline:

```text
🆕 Sudden New Entrant
```

### Sudden Volume Spike

If a test's:

- starts
- finishes
- or relevant completion/submit volume

is more than **40% above its historical baseline**, it is flagged as:

```text
⚡ Sudden Volume Spike
```

### Funnel Friction

The agent compares:

```text
Starts → Finishes
```

to identify severe test-level drop-offs.

---

# 5. Cross-metric PM reasoning

The LLM is instructed to triangulate metrics instead of treating them independently.

For example:

### Test funnel

```text
Test Started
     ↓
Submit
     ↓
Signup/Login Wall
     ↓
Completion
```

A completion decline is therefore investigated alongside:

- test starts
- submit activity
- signup/login-wall encounters
- returning users
- signups
- sign-ins

### Chat engagement

Changes in chat activity are interpreted alongside:

- total messages
- users sending messages
- average messages/user
- conversation counts
- returning users
- Healo traffic
- relevant CTA activity

### SEO/test traffic

When organic traffic changes, the agent is instructed to investigate potential:

- CTR changes
- ranking/position changes
- indexing issues
- 404/5xx problems
- landing-page behavior

The generated recommendation can therefore point a PM toward Google Search Console or Hotjar rather than stopping at the observed metric change.

---

# 6. Product-context aware analysis

The agent automatically reads `.docx` files located beside the Python script.

The loader:

1. Finds `.docx` files
2. Ignores temporary Word files beginning with `~`
3. Extracts non-empty paragraphs
4. Labels each document
5. Combines them into the LLM's product context

This allows the same metric to be interpreted in the context of existing product research instead of treating the analytics dataset as isolated numbers.

Example context can include:

- test categories
- user behavior observations
- Home-page analysis
- B2B product context
- previous funnel investigations
- historical PM findings

---

# 7. LLM-generated PM digest

The agent uses the Google GenAI SDK with:

```text
Gemini 2.5 Flash
```

The model receives:

```text
Today's metrics
+
7-day averages
+
Top 5 tests
+
Test historical baseline
+
Product/funnel context
```

The system prompt asks the model to behave like a:

> Lead Product Analyst and Data Diagnostician

The output is intentionally short and designed to be scanned quickly by a PM.

---

# Output Format

Every digest follows four sections.

## 🔴 Critical Funnel Anomalies & Causal Analysis

Highlights major breakdowns across connected metrics.

Each finding should identify:

```text
Root metric
   ↓
Secondary impact
   ↓
Product hypothesis
```

---

## 🟡 Emerging Behavioral Trends

Highlights correlated behavioral changes such as:

- Web vs App shifts
- changes in chat intensity
- changing test behavior
- changes in returning-user activity
- unusual traffic patterns

---

## 🟢 Core Funnel Baselines

Provides a short health check for metrics that remain within expected ranges.

---

## 🔍 Recommended PM Investigation & Action Plan

Converts observations into concrete next steps.

Examples:

```text
Check Search Console for landing-page ranking changes.

Inspect Hotjar recordings for mobile users reaching the
test submission/signup wall.

Add event tracking around the premium-test purchase funnel.
```

---

# Data Flow

```text
                  ┌──────────────────────┐
                  │ Daily Analytics Email│
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │ Gmail IMAP Ingestion │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │ HTML Table Parser    │
                  │ BeautifulSoup + RE   │
                  └──────────┬───────────┘
                             │
              ┌──────────────┴──────────────┐
              ▼                             ▼
      General Metrics                 Test Metrics
              │                             │
              └──────────────┬──────────────┘
                             ▼
                  ┌──────────────────────┐
                  │ Excel Master Engine  │
                  │                      │
                  │ 7D / 30D baselines  │
                  │ Test baselines       │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │ Metric Filtering     │
                  │ & Payload Creation   │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │ Gemini 2.5 Flash     │
                  │ PM Reasoning Layer   │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │ Markdown → HTML      │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │ Gmail SMTP Delivery  │
                  └──────────────────────┘
```

---

# Project Structure

A recommended deployment structure is:

```text
Infiheal-Agent/
│
├── triage_agent.py
│
├── infiheal_metrics_master.xlsx
│
├── infiheal_digest.log
├── infiheal_task_log.txt
│
├── run_infiheal_digest.bat
│
├── User Analysis-Insights.docx
├── User Analysis-Insights-2.docx
├── B2B Infiiheal Page.docx
├── Categories.docx
├── Daily Analytics.docx
│
└── README.md
```

The `.docx` files are contextual knowledge sources. The exact set can evolve without changing the core parsing logic.

---

# Tech Stack

| Layer | Technology |
|---|---|
| Language | Python |
| Email ingestion | Gmail IMAP |
| Email delivery | Gmail SMTP |
| HTML parsing | BeautifulSoup |
| Data processing | Pandas |
| Historical storage | Excel / OpenPyXL |
| Product context | python-docx |
| LLM | Google Gemini 2.5 Flash |
| LLM SDK | `google-genai` |
| Scheduling | APScheduler |
| Markdown → HTML | Python Markdown |
| Logging | Python `logging` |
| Automation | Windows Task Scheduler / batch launcher |

---

# Installation

## 1. Clone / create the project

```bash
git clone <your-repository-url>
cd Infiheal-Agent
```

Or place the Python script, Excel file, and context documents in the same directory.

---

## 2. Create a virtual environment

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

---

## 3. Install dependencies

```bash
pip install pandas beautifulsoup4 google-genai apscheduler python-docx markdown openpyxl
```

Equivalent `requirements.txt`:

```text
pandas
beautifulsoup4
google-genai
apscheduler
python-docx
markdown
openpyxl
```

---

# Configuration

The current implementation requires three credentials:

```text
EMAIL_USER
EMAIL_APP_PASS
GEMINI_API_KEY
```

These should **not** be hardcoded in the Python source.

Recommended configuration:

```python
import os

EMAIL_USER = os.getenv("INFIHEAL_EMAIL")
EMAIL_APP_PASS = os.getenv("INFIHEAL_EMAIL_APP_PASSWORD")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
```

Then configure the environment variables on the machine running the agent.

For Gmail, use an **App Password** where required rather than storing a normal account password in source code.

> **Security:** If credentials have ever been committed to Git, pasted into a public repository, or shared outside the intended environment, rotate/revoke them before deployment.

---

# Running the Agent

## Run once

```bash
python triage_agent.py
```

The script:

1. Fetches the latest Daily Analysis email
2. Parses metrics
3. Validates the report date
4. Updates the Excel master
5. Builds the AI payload
6. Generates the PM digest
7. Sends the digest by email

---

# Daily Scheduling

The Python application contains an APScheduler job configured for:

```text
15:10 / 3:10 PM
```

every day.

The scheduler uses:

```python
CronTrigger(hour=15, minute=10)
```

For Windows Task Scheduler, the included batch launcher can be used as the entry point.

Update the batch file so that it calls the actual Python filename used in the repository.

Example:

```bat
@echo off

cd /D C:\path\to\Infiheal-Agent

call venv\Scripts\activate.bat

python triage_agent.py

echo [%date% %time%] Infiheal digest automation executed >> infiheal_task_log.txt
```

---

# Logs

The application writes logs to:

```text
infiheal_digest.log
```

The log records:

- scheduler startup
- Gmail retrieval
- parsing status
- Excel updates
- Gemini API calls
- digest generation
- email delivery
- exceptions

A separate task log can be used to record batch-level executions.

---

# Failure Handling

The pipeline contains checks for several failure modes.

### No analytics email

```text
No email data retrieved → run aborted
```

### Stale report

If the email date does not match the expected previous day:

```text
run skipped
```

This prevents an old analytics email from contaminating the daily history.

### Gemini failure

The Gemini call is wrapped in exception handling and returns an explicit API error instead of silently failing.

### Email delivery failure

SMTP errors are logged without crashing the entire Python process.

---

# Important Implementation Notes

## 1. Product context is directory-dependent

The context loader scans the directory containing the Python script:

```python
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
```

Therefore, the relevant `.docx` files should be placed in that directory.

---

## 2. Excel is the historical memory layer

The Excel workbook is not just an export.

It acts as the historical baseline store used by the agent to compare today's data with previous days.

The agent uses:

```text
Main Metrics
Top 5 Tests
```

to construct historical context.

---

## 3. The agent is intentionally not a dashboard

Its primary output is not a visualization.

It is a **decision-support digest**.

The intended workflow is:

```text
Analytics
   ↓
Anomaly detection
   ↓
Cross-metric reasoning
   ↓
Product hypothesis
   ↓
PM investigation
```

---

# Product Analytics Context

The internal analysis documents used by the agent cover several important areas of the Healo funnel.

For example, historical analysis identified Asexual and Allosexual tests as high-volume tests with comparatively low completion rates in the examined period, while also highlighting the importance of signup/login-wall behavior. 

The broader product analysis also tracks engagement across:

- Home
- Healo
- DuoChat
- Self Tests
- Music
- Community
- Mood Meter
- Streaks
- Heals

This allows the agent's recommendations to be grounded in the existing product funnel rather than generic analytics terminology.

---

# Example PM Reasoning

A useful output from this system should look conceptually like:

```text
🔴 Critical Funnel Anomalies & Causal Analysis

• Test starts remained stable, but completions dropped materially while
  signup/login-wall encounters increased. This points to friction near
  result submission rather than acquisition.

🟡 Emerging Behavioral Trends

• Test traffic is increasing while completion quality is weakening,
  suggesting a possible shift in incoming audience intent.

🟢 Core Funnel Baselines

• Login and chat metrics remain broadly within their recent baseline.

🔍 Recommended PM Investigation & Action Plan

• Inspect Hotjar recordings for users reaching the submission wall.
• Compare mobile vs desktop wall encounters.
• Check whether the affected test's acquisition mix changed in Search Console.
```

The exact findings are generated dynamically from the daily payload.

---

# Known Limitations

### Aggregate-data limitation

The agent primarily works with daily aggregates. Some questions require user-level or event-level data that daily reports cannot provide.

Examples include:

- Day-1 / Day-7 / Day-30 cohort retention
- exact time from signup to first message
- exact time-to-drop-off
- individual lifecycle tracing
- complete paid-conversion paths

These limitations were explicitly identified in the product analysis work.

---

### External tools are recommendations, not direct integrations

The current implementation can recommend investigations in tools such as:

- Hotjar
- Google Search Console

but it does not directly query those platforms.

Their data must be connected separately if automated retrieval is desired.

---

### Test completion can exceed 100%

Completion rate is based on daily starts vs daily finishes.

A completion can belong to a user who started the test on an earlier day, so:

```text
daily finishes > daily starts
```

can legitimately produce a completion rate above 100%.

This should not automatically be interpreted as a data error.

---

# Security Checklist

Before pushing this project to GitHub:

- [ ] Remove all API keys from source code
- [ ] Remove Gmail App Passwords from source code
- [ ] Add `.env` / environment variables
- [ ] Add `.env` to `.gitignore`
- [ ] Check Git history for previously committed secrets
- [ ] Rotate any exposed credentials
- [ ] Do not commit internal analytics containing user-identifiable information
- [ ] Do not commit private production exports unless explicitly approved

Suggested `.gitignore`:

```gitignore
__pycache__/
*.pyc

.env
.venv/
venv/

*.log

# Local analytics / internal data
*.xlsx

# Optional: keep public sample data separately
```

---

# Future Improvements

## Data layer

- Replace Excel with a database or warehouse
- Add event-level analytics
- Maintain versioned metric definitions
- Add data-quality validation before LLM analysis

## Analytics layer

- Automatic anomaly scoring
- Week-over-week and month-over-month comparisons
- Segment-level baselines
- Mobile vs desktop anomaly detection
- Web vs app anomaly detection
- Funnel-specific thresholds

## AI layer

- Structured JSON output
- Confidence scores for hypotheses
- Evidence references for every finding
- Regression detection
- Root-cause ranking based on supporting metrics
- Historical hypothesis tracking
- PM feedback loop to improve recommendations

## Integrations

Potential future integrations:

```text
Google Analytics / GA4
Google Search Console
Hotjar
Product analytics event store
Slack
Jira
Notion
```

This would allow the agent to move from:

```text
"Something unusual happened."
```

to:

```text
"Something unusual happened → supporting evidence → likely causes
→ recommended investigation → tracked PM action."
```

---

# Architecture Summary

```text
                    ┌─────────────────────┐
                    │   Daily Analytics   │
                    │       Email         │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   Data Ingestion    │
                    │     Gmail IMAP      │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   Metric Parser     │
                    │ BeautifulSoup / RE  │
                    └──────────┬──────────┘
                               │
                 ┌─────────────┴─────────────┐
                 ▼                           ▼
        ┌────────────────┐          ┌────────────────┐
        │ General Metrics│          │  Test Metrics  │
        └───────┬────────┘          └───────┬────────┘
                │                           │
                └─────────────┬─────────────┘
                              ▼
                    ┌─────────────────────┐
                    │ Historical Baseline  │
                    │ Excel Master Engine  │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Metric Selection +  │
                    │ Context Assembly     │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   Gemini 2.5 Flash  │
                    │   PM Triage Engine  │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Executive PM Digest │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Gmail SMTP Delivery │
                    └─────────────────────┘
```

---

# Author / Project Context

**Infiheal PM Triage Agent**

Built as a product-management automation workflow to reduce the manual effort required to interpret daily Healo analytics and surface actionable funnel anomalies.

The system combines:

**Product Analytics + Historical Baselines + LLM Reasoning + Automated Reporting**

rather than treating an LLM as a simple text summarizer.

---

## License

Add the appropriate license before publishing this repository publicly.

For an internal company project, keep the repository private unless the relevant organization approves public release.

