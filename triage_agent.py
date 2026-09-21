import os
import re
import html
import email
import imaplib
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import pandas as pd
from bs4 import BeautifulSoup
from google import genai
from google.genai import types

# APScheduler for daily automation
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import atexit
import logging
import docx

from datetime import datetime, timedelta

import markdown 

# =====================================================================
# LOGGING SETUP
# =====================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        # ---> ADD encoding='utf-8' HERE <---
        logging.FileHandler('infiheal_digest.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# =====================================================================
# 1. DYNAMIC DOCX CONTEXT & SYSTEM PROMPT
# =====================================================================

def load_docx_funnel_context(folder_path: str = ".") -> str:
    """Scans the directory and automatically merges text from all .docx files."""
    context_chunks = []
    
    # Locate all .docx files in the directory (skipping temporary Word lock files starting with '~')
    docx_files = [f for f in os.listdir(folder_path) if f.endswith('.docx') and not f.startswith('~')]
    
    for filename in sorted(docx_files):
        file_path = os.path.join(folder_path, filename)
        try:
            doc = docx.Document(file_path)
            paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
            if paragraphs:
                context_chunks.append(f"--- SOURCE DOCUMENT: {filename} ---\n" + "\n".join(paragraphs))
                print(f"📄 Successfully loaded: {filename}")
        except Exception as e:
            print(f"⚠️ Warning: Could not read {filename}: {e}")
            
    return "\n\n".join(context_chunks)

# Automatically resolve the directory where triage_agent.py resides
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else "."
DOCX_FUNNEL_CONTEXT = load_docx_funnel_context(SCRIPT_DIR)

SYSTEM_PROMPT = f"""
You are the Lead Product Analyst and Data Diagnostician for Infiheal (Healo). 

--- CORE DIRECTIVE ---
DO NOT simply list numbers or report isolated percentage changes. Anyone can read a spreadsheet. Your job is to "use your brain"—connect the dots, analyze interlinked metrics, and form structural hypotheses about user behavior, product friction, and funnel health.
ONE OF YOUR IMPORTANT GOALS IS TO SPOT ANOMALIES. Focus 60% of your analysis on identifying unusual spikes, steep drops, and unexpected breaks across interlinked metrics. Keep the overall output short, crisp, and scannable so the PM can read it in 45 seconds.

--- PRODUCT & USER CONTEXT ---
{DOCX_FUNNEL_CONTEXT}

--- HISTORICAL BASELINE OVERRIDE ---
If the provided '7_day_average' or 'test_history_baseline' JSON payloads are empty or incomplete, you MUST actively extract the historical averages from the recent 7-day data provided in the --- PRODUCT & USER CONTEXT --- section above. Use this text-based history as your definitive baseline for ALL anomaly detection (both general metrics and tests).

--- TOP TESTS ANOMALY & NEW ENTRANT RULES ---
Compare 'top_5_tests_today' against 'test_history_baseline' using these rules:
1. 🆕 NEW ENTRANTS: If a test appears in 'top_5_tests_today' but is NOT present in 'test_history_baseline', explicitly flag it as a **Sudden New Entrant**.
2. ⚡ METRIC SPIKES: If a test's 'startCount', 'finishCount', or 'of the day (submit/completed)' is >40% higher than its historical average in 'test_history_baseline', flag it as a **Sudden Volume Spike**.
3. 📉 FUNNEL FRICTION: Evaluate 'startCount' vs 'finishCount' for today's tests to flag severe mid-test drop-offs.

--- ANALYSIS INSTRUCTIONS & CROSS-METRIC TRIANGULATION ---

1. Evaluate daily metrics against historical averages. Ignore minor daily noise.
2. Think autonomously like a Senior PM: Use the following examples as a mental framework to connect metrics, but look beyond them to find novel, unexpected correlations.
   - Example 1: If "Total Test Started" is stable but "Total test completed" drops, infer friction at the "signup/login wall".
   - Example 2: If "Avg chat spend" decreases, check if message counts or CTA clicks also dropped.
3. GSC Specific Diagnostic Rules: If organic/SEO metrics drop, check Google Search Console:
   - CTR Issue: Check the 'Search Results' report. Look for SERP feature changes.
   - Position Drop: Check if 'Average Position' dropped for top queries. 
   - Technical/Indexing: Check the 'Page Indexing' report for 5xx errors or 404s.
4. Cross-reference the primary drop with at least one or two secondary metrics.
5. Provide precise Hotjar targeting parameters based on the anomaly (e.g., URL path, event).

--- REQUIRED OUTPUT FORMAT ---
Generate an executive PM Digest structured as follows:

🔴 **Critical Funnel Anomalies & Causal Analysis**
- Identify major breakdowns across interlinked metrics. 
- State the root metric, the secondary impact, and your product hypothesis.

🟡 **Emerging Behavioral Trends**
- Highlight shifts across correlated metrics (e.g., shifts between Web vs. App adoption, chat intensity variations).

🟢 **Core Funnel Baselines**
- Brief confirmation of connected metrics operating healthily within expected corridors.

🔍 **Recommended PM Investigation & Action Plan**
- Concrete, actionable diagnostic steps (e.g., "Check Search Console for landing page ranking changes", "Set up Hotjar event tracking on the submit wall for mobile web").
"""

# =====================================================================
# 2. EMAIL INGESTION & DYNAMIC HTML PARSING
# =====================================================================
def fetch_latest_daily_email(username: str, app_password: str) -> str:
    """Connects to Gmail and fetches the raw HTML of the latest Daily Analysis email."""
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(username, app_password)
        mail.select("inbox")
        
        status, messages = mail.search(None, '(SUBJECT "Daily Analysis Data")')
        if status != "OK" or not messages[0]:
            logger.warning("No daily analysis emails found.")
            return ""

        # --- ADD THIS LINE ---
        logger.info(f"IMAP search matched UIDs: {messages[0]}")

        latest_email_id = messages[0].split()[-1]
        status, msg_data = mail.fetch(latest_email_id, "(RFC822)")
        
        html_content = ""
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/html":
                            html_content = part.get_payload(decode=True).decode()
                            break 
                else:
                    html_content = msg.get_payload(decode=True).decode()
                    
        # --- ADD THIS LINE ---
        logger.info(f"Fetched email subject/date snippet: {html_content[:300]}")

        return html_content
    
    except Exception as e:
        logger.error(f"Error fetching email: {e}")
    finally:
        try:
            mail.logout()
        except:
            pass
    return ""

def parse_all_infiheal_metrics_dynamically(html_text: str) -> tuple[str, dict, dict]:
    """Parses HTML into two dictionaries: General Metrics and Top 5 Tests."""
    general_metrics = {}
    test_metrics = {}
    
    date_match = re.search(r"Daily Analysis Summary \(([\d-]+) - [\d-]+\)", html_text)
    date_str = date_match.group(1) if date_match else datetime.now().strftime("%Y-%m-%d")
    
    soup = BeautifulSoup(html_text, 'html.parser')
    rows = soup.find_all('tr')
    
    for row in rows:
        cols = row.find_all(['td', 'th'])
        texts = [c.get_text(separator=" ", strip=True) for c in cols]
        
        if not texts:
            continue
            
        if 'startCount' in texts or 'finishCount' in texts:
            continue
            
        # 1. Top 5 Tests Extraction
        last_cell = texts[-1].lower()
        if 'test/' in last_cell or 'personality-' in last_cell:
            nums = [t for t in texts if t.isdigit()]
            if len(nums) >= 2:
                test_name = texts[-1]
                starts = int(nums[0])
                finishes = int(nums[1])
                cr = round((finishes / starts * 100), 2) if starts > 0 else 0.0
                
                test_metrics[test_name] = {
                    'Starts': starts,
                    'Finishes': finishes,
                    'CR (%)': cr
                }
            continue 
            
        # 2. General Metrics Extraction
        if len(texts) >= 2:
            key = texts[0]
            val_str = texts[1]
            
            if key.lower() == 'metric' or 'Top 5 tests' in key:
                continue
                
            clean_num = re.sub(r"[^\d.]", "", val_str)
            if clean_num and clean_num != ".":
                general_metrics[key] = float(clean_num) if "." in clean_num else int(clean_num)
            elif val_str.lower() in ['-', 'no data']:
                general_metrics[key] = "-"
            else:
                general_metrics[key] = val_str

        # Calculate Total Daily Signups by summing all 6 signup streams
    signup_keys = [
        "Healo-Web (Non-Anonymous) users who completed Sign up",
        "Healo App (Non-Anonymous) Users who completed Sign up",
        "Test (Non-Anonymous) Users Who completed sign up",
        "Test (Anonymous) Users Who completed sign up",
        "Healo Web (Anonymous) users who completed Sign Up",
        "Healo App (Anonymous) users who completed Sign up"
    ]
    
    total_signups = 0
    for key in signup_keys:
        val = general_metrics.get(key, 0)
        if isinstance(val, (int, float)):
            total_signups += val
            
    general_metrics["Total Daily Signups (Calculated)"] = total_signups

    return date_str, general_metrics, test_metrics

# =====================================================================
# 3. EXCEL MASTER ENGINE
# =====================================================================

def update_excel_master_sheets(date_str: str, general_metrics: dict, test_metrics: dict, excel_path: str = "infiheal_metrics_master.xlsx"):
    """Saves general metrics to one sheet, and test metrics with sub-columns to another."""
    if os.path.exists(excel_path):
        with pd.ExcelFile(excel_path) as xls:
            df_main = pd.read_excel(xls, sheet_name="Main Metrics", index_col=0) if "Main Metrics" in xls.sheet_names else pd.DataFrame(index=pd.Index([], name="Metric"))
            df_tests = pd.read_excel(xls, sheet_name="Top 5 Tests", header=[0, 1], index_col=0) if "Top 5 Tests" in xls.sheet_names else pd.DataFrame(index=pd.Index([], name="Test Name"))
    else:
        df_main = pd.DataFrame(index=pd.Index([], name="Metric"))
        df_tests = pd.DataFrame(index=pd.Index([], name="Test Name"))
        

    test_history_baseline = {}
    if not df_tests.empty:
        # Convert Excel '-' markers back to NaN for calculation
        temp_tests = df_tests.replace('-', pd.NA).apply(pd.to_numeric, errors='coerce')
        
        # Get the historical dates (level 0 of the MultiIndex columns)
        hist_dates = temp_tests.columns.get_level_values(0).unique()
        
        if len(hist_dates) > 0:
            # Grab up to the last 7 available dates
            last_7_dates = hist_dates[-7:]
            df_last_7 = temp_tests.loc[:, last_7_dates]
            
            # Average across the dates for each metric (level 1 of columns)
            test_avg_df = df_last_7.T.groupby(level=1).mean().T.round(1)
            
            # Convert to dictionary and clean out NaN values
            raw_dict = test_avg_df.to_dict(orient='index')
            for test_name, metrics in raw_dict.items():
                clean_metrics = {k: v for k, v in metrics.items() if pd.notna(v)}
                if clean_metrics:
                    test_history_baseline[test_name] = clean_metrics
    # =================================================================

    df_main[date_str] = pd.Series(general_metrics)
    df_main = df_main.astype(object).fillna('-')
    
    if test_metrics:
        df_today_tests = pd.DataFrame.from_dict(test_metrics, orient='index')
        df_today_tests.columns = pd.MultiIndex.from_product([[date_str], df_today_tests.columns])
        
        if df_tests.empty:
            df_tests = df_today_tests
        else:
            df_tests = df_tests.join(df_today_tests, how='outer')
            
    df_tests = df_tests.astype(object).fillna('-')
    
    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        df_main.to_excel(writer, sheet_name="Main Metrics")
        df_tests.to_excel(writer, sheet_name="Top 5 Tests")
        
    historical_cols = df_main.columns[:-1] 
    if len(historical_cols) == 0:
        avg_7d = general_metrics
        avg_30d = general_metrics
    else:
        numeric_df = df_main[historical_cols].apply(pd.to_numeric, errors='coerce')
        last_7_cols = numeric_df[numeric_df.columns[-7:]]
        last_30_cols = numeric_df[numeric_df.columns[-30:]]
        
        avg_7d = last_7_cols.mean(axis=1, skipna=True).round(2).to_dict()
        avg_30d = last_30_cols.mean(axis=1, skipna=True).round(2).to_dict()
        
    return {
        "today_data": general_metrics,
        "7_day_average": avg_7d,
        "30_day_average": avg_30d,
        "test_history_baseline": test_history_baseline # Passed to Gemini payload
    }

# =====================================================================
# 4. GEMINI API INTEGRATION
# =====================================================================

def generate_pm_triage_brief(date_str: str, payload: dict, system_context: str, api_key: str) -> str:
    """Sends the metrics and context to Gemini using the google-genai SDK."""
    client = genai.Client(api_key=api_key)
    
    user_message = f"""
    Here is the daily metric payload for {date_str}.
    
    TODAY'S METRICS: 
    {payload.get('today_general_metrics', {})}
    
    7-DAY AVERAGES: 
    {payload.get('7_day_average', {})}

    TOP 5 TESTS TODAY:
    {payload.get('top_5_tests', {})}

    TEST HISTORY BASELINE:
    {payload.get('test_history_baseline', {})}
    
    Please analyze this and output the PM digest exactly as instructed.
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=system_context,
                temperature=0.2
            )
        )
        if response.text is None:
            logger.warning("Gemini returned no text (possibly blocked or empty response).")
            return "⚠️ Gemini returned an empty response — no digest could be generated."
        return response.text
    except Exception as e:
        logger.error(f"Gemini API Error: {e}")
        return f"❌ Gemini API Error: {e}"

# =====================================================================
# 5. AUTOMATED NOTIFICATION DELIVERY
# =====================================================================

def send_digest_email(user_email: str, app_password: str, date_str: str, digest_content: str):
    """Emails the final PM Digest directly to the user in clean HTML."""
    msg = MIMEMultipart()
    msg['From'] = user_email
    msg['To'] = user_email
    msg['Subject'] = f"📊 Infiheal PM Daily Digest: {date_str}"
    
    # Convert Gemini's markdown response into HTML
    html_content = markdown.markdown(digest_content)
    
    # Wrap it in basic HTML styling for a clean, professional look
    html_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        {html_content}
      </body>
    </html>
    """
    
    # Attach as 'html' instead of 'plain'
    msg.attach(MIMEText(html_body, 'html'))
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(user_email, app_password)
        server.send_message(msg)
        server.quit()
        logger.info(f"✅ Email sent successfully for {date_str}")
    except Exception as e:
        logger.error(f"Failed to send email notification: {e}")

# =====================================================================
# 6. MAIN EXECUTION FUNCTION
# =====================================================================

def run_daily_digest(email_user: str, email_app_pass: str, gemini_api_key: str):
    """Main workflow execution"""
    try:
        logger.info("=" * 60)
        logger.info("🚀 Starting Daily Infiheal PM Digest Pipeline")
        logger.info("=" * 60)
        
        logger.info("1. Fetching today's metrics from Gmail...")
        raw_email_text = fetch_latest_daily_email(email_user, email_app_pass)
        
        if not raw_email_text:
            logger.error("❌ No email data retrieved. Aborting.")
            return
        
        logger.info("2. Parsing HTML tables into separate metric streams...")
        date_str, general_metrics, test_metrics = parse_all_infiheal_metrics_dynamically(raw_email_text)

        logger.info(f"Parsed general_metrics ({len(general_metrics)} keys): {general_metrics}")
        logger.info(f"Parsed test_metrics ({len(test_metrics)} keys): {test_metrics}")

        expected_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        if date_str != expected_date:
            logger.warning(
                f"⚠️ Fetched email date '{date_str}' does not match expected date "
                f"'{expected_date}' — likely a stale/old email from IMAP search. Skipping this run."
            )
            return
        
        logger.info(f"3. Updating Master Excel File for {date_str}...")
        payload_for_gemini = update_excel_master_sheets(date_str, general_metrics, test_metrics)
        logger.info("✅ Master Sheet Updated")
        
        logger.info("4. Filtering data and analyzing metrics with Gemini...")
        
        TARGET_METRICS = [
            "Total Users who tried sign up",
            "Healo-Web (Non-Anonymous) users who tried Sign up",
            "Healo App (Non-Anonymous) Users who tried Sign up",
            "Test (Non-Anonymous) Users Who tried sign up",
            "Healo Web (Anonymous) users who tried Sign Up",
            "Healo App (Anonymous) users who tried Sign up",
            "Total Users who completed sign up - (Verified Only)",
            "Healo-Web (Non-Anonymous) users who completed Sign up",
            "Healo App (Non-Anonymous) Users who completed Sign up",
            "Test (Non-Anonymous) Users Who completed sign up",
            "Test (Anonymous) Users Who completed sign up",
            "Healo Web (Anonymous) users who completed Sign Up",
            "Healo App (Anonymous) users who completed Sign up",
            "Total users who tried log in / sign in",
            "Total users who completed sign in",
            "Healo Web users who tried sign in",
            "Healo Web users who completed sign in",
            "App users who tried sign in",
            "App users who completed sign in",
            "Total Convo ID's",
            "Unique User Count",
            "Avg number of messages sent per user (Median)",
            "Total users who sent messages",
            "Total messages sent",
            "Min messages by a user",
            "Max messages by a user",
            "Avg chat spend on healo chat (in Minutes)",
            "Total conversations counted",
            "Total conversations created",
            "Min chat duration",
            "Max chat duration",
            "Top 3 users with maximum messages sent",
            "Number of returning users",
            "Avg time spent on Home (By screen Time ) (Minutes)",
            "Total time spent on Home (By screen Time ) (Minutes)",
            "Unique Home users",
            "Avg time spent on Healo (By screen Time ) (Minutes)",
            "Total time spent on Healo (By screen Time ) (Minutes)",
            "Unique Healo users",
            "Users coming to test page via SEO/goggle search",
            "Users coming to test page via healo",
            "Total users who started test ( SEO + HEALO combined)",
            "Start test action - via SEO traffic",
            "Start test action - via Healo traffic",
            "Total Test Started From All Sources",
            "Users shown the Premium Test popup",
            "Users who clicked 'Pay Now' on the Premium Test popup",
            "Total test completed",
            "Total users who clicked on Submit",
            "Total users who encounterd signup/login wall",
            "Users already logged in at the time of submission ( Return users)",
            "Total (Non-Anonymous) Users who completed sign up",
            "Total Users who completed sign in / Log in",
            "Total User redirected to Healo chatbot from Understand your score",
            "Total Daily Signups (Calculated)"
        ]
        
        # =====================================================================
    
        def normalize_text(text: str) -> str:
            """Converts to lowercase and collapses all extra spaces into a single space."""
            return " ".join(str(text).lower().split())

        # 1. Create a translation map: { 'clean_lowercase_name': 'Original Name' }
        normalized_targets = {normalize_text(m): m for m in TARGET_METRICS}
        
        filtered_today = {}
        filtered_7_day = {}
        
        # 2. Filter Today's Data
        for raw_key, value in payload_for_gemini.get('today_data', {}).items():
            clean_key = normalize_text(raw_key)
            if clean_key in normalized_targets:
                # Keep the clean, original name for Gemini
                filtered_today[normalized_targets[clean_key]] = value 
                
        # 3. Filter 7-Day Average Data
        for raw_key, value in payload_for_gemini.get('7_day_average', {}).items():
            clean_key = normalize_text(raw_key)
            if clean_key in normalized_targets:
                filtered_7_day[normalized_targets[clean_key]] = value

        logger.info(f"Filtered today ({len(filtered_today)} keys): {filtered_today}")
        logger.info(f"Filtered 7-day ({len(filtered_7_day)} keys): {filtered_7_day}")

        # =====================================================================
        
        ai_payload = {
            'today_general_metrics': filtered_today,
            '7_day_average': filtered_7_day,
            'top_5_tests': test_metrics, 
            'test_history_baseline': payload_for_gemini.get('test_history_baseline', {})
        }
        
        triage_brief = generate_pm_triage_brief(date_str, ai_payload, SYSTEM_PROMPT, gemini_api_key)
        
        logger.info("\n" + "=" * 60)
        logger.info(f"📊 INFIHEAL PM DAILY DIGEST ({date_str})")
        logger.info("=" * 60)
        logger.info(triage_brief)
        
        logger.info("5. Sending automated email notification...")
        send_digest_email(email_user, email_app_pass, date_str, triage_brief)
        
        logger.info("=" * 60)
        logger.info("✅ Daily digest pipeline completed successfully!")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ Critical error in daily digest pipeline: {e}", exc_info=True)


# =====================================================================
# 7. SCHEDULER SETUP
# =====================================================================

def start_scheduler(email_user: str, email_app_pass: str, gemini_api_key: str):
    """Initializes APScheduler for 3:10 PM (15:10) daily execution"""
    scheduler = BackgroundScheduler()
    
    scheduler.add_job(
        func=run_daily_digest,
        trigger=CronTrigger(hour=15, minute=10),
        args=(email_user, email_app_pass, gemini_api_key),
        id='infiheal_daily_digest',
        name='Infiheal PM Daily Digest',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("✅ Scheduler started! Job scheduled for 3:10 PM (15:10) daily.")
    
    atexit.register(lambda: scheduler.shutdown())
    
    return scheduler


# =====================================================================
# EXECUTION ENTRY POINT
# =====================================================================

if __name__ == "__main__":
    
    EMAIL_USER = "bmanikrishna.2004@gmail.com" 
    EMAIL_APP_PASS = "chpi evgo lfqe poec"
    GEMINI_API_KEY = "AQ.Ab8RN6Lm9e2v284B4BwYQQ1qKK5Vba3oTDTzfxPeNnSW7MxWrw"
    
    print("\n" + "=" * 60)
    print("🤖 Infiheal PM Daily Digest Automation")
    print("=" * 60)
    print(f"Executing run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Scheduled to run: Every day at 3:10 PM (15:10) via Task Scheduler")
    print("Logs saved to: infiheal_digest.log")
    print("=" * 60 + "\n")
    
    run_daily_digest(EMAIL_USER, EMAIL_APP_PASS, GEMINI_API_KEY)

    
    