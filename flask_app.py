import os
import requests
import urllib3
import threading
import time
import asyncio
from datetime import datetime, timedelta
from flask import Flask, jsonify, render_template_string, request, Response, redirect
from flask_cors import CORS
from crawl import scrape
from db_utils import (
    init_db,
    save_records,
    get_all_records,
    get_document_by_id,
    update_document_file,
    delete_record_by_id,
    clear_all_records,
    get_scheduler_settings,
    update_scheduler_settings,
    sync_scraped_records,
)
from pathlib import Path
from dataclasses import asdict
from markdown_worker import run_markdown_worker_loop
from comparator import load_model
app = Flask(__name__)
CORS(app)

# Pre-load embedding model at startup to avoid first-request latency
print("Pre-loading embedding model...")
load_model()
print("Model loaded.")

# Hardcoded target URL for DGCA CAR Section 2
TARGET_URL = "https://www.dgca.gov.in/digigov-portal/?baseLocale=en_US?dynamicPage=CivilAviationReqContent/6/160/viewDynamicRuleContLvl2/html&maincivilAviationRequirements/6/0/viewDynamicRulesReq"
OUTPUT_JSON = Path("temp_scrape_results.json")

# Initialize DB on start
init_db()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DGCA Document API</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #073f88;
            --accent: #2d9cff;
            --bg: #f8fafc;
            --card: #ffffff;
            --text: #1e293b;
        }
        body {
            font-family: 'Inter', sans-serif;
            background-color: var(--bg);
            color: var(--text);
            margin: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
        }
        .container {
            text-align: center;
            background: var(--card);
            padding: 3rem;
            border-radius: 1.5rem;
            box-shadow: 0 10px 25px rgba(0,0,0,0.05);
            max-width: 500px;
            width: 90%;
        }
        h1 { color: var(--primary); font-weight: 800; margin-bottom: 1rem; }
        p { color: #64748b; margin-bottom: 2rem; }
        .btn {
            background: var(--primary);
            color: white;
            padding: 0.75rem 2rem;
            border-radius: 0.5rem;
            text-decoration: none;
            font-weight: 600;
            transition: all 0.2s;
            display: inline-block;
            border: none;
            cursor: pointer;
        }
        .btn:hover {
            background: var(--accent);
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(45, 156, 255, 0.3);
        }
        .status {
            margin-top: 1.5rem;
            font-size: 0.9rem;
            color: #94a3b8;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>DGCA Portal API</h1>
        <p>Extractor for Civil Aviation Requirements (CAR) documents.</p>
        <form action="/crawl" method="POST">
            <button type="submit" class="btn">Trigger Extraction</button>
        </form>
        <div class="status">Target: {{ target_url }}</div>
        <div style="margin-top: 1rem;">
            <a href="/data" style="color: var(--accent); text-decoration: none; font-size: 0.9rem;">View Stored Data</a>
        </div>
    </div>
</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML_TEMPLATE, target_url=TARGET_URL)


@app.route("/crawl", methods=["POST"])
def trigger_crawl():
    try:
        # Run the scraper
        # Note: We use headless=True for the API
        records = scrape(
            target_url=TARGET_URL,
            output_path=OUTPUT_JSON,
            headless=True,
            max_rows=0,
            channel="msedge" # or "" for default chromium
        )
        
        # Sync scraped data to SQLite, detecting updates/new entries
        sync_scraped_records(records)
        
        # Clean up temp file
        if OUTPUT_JSON.exists():
            os.remove(OUTPUT_JSON)
            
        return jsonify({
            "status": "success",
            "message": f"Successfully extracted and saved {len(records)} records.",
            "count": len(records)
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route("/data", methods=["GET"])
def view_data():
    records = get_all_records()
    return jsonify(records)


@app.route("/api/documents", methods=["GET"])
def api_get_documents():
    try:
        records = get_all_records()
        return jsonify(records)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/documents/<int:doc_id>/view", methods=["GET"])
def api_view_document(doc_id):
    try:
        doc = get_document_by_id(doc_id)
        if not doc:
            return jsonify({"status": "error", "message": "Document not found"}), 404
        
        file_content = doc.get("file_content")
        if not file_content:
            url = doc.get("document_download_url")
            if not url:
                return jsonify({"status": "error", "message": "Download URL missing"}), 400
            
            print(f"Downloading PDF on-demand from URL: {url}")
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
            }
            r = requests.get(url, headers=headers, verify=False, timeout=20)
            if r.status_code == 200:
                file_content = r.content
                update_document_file(doc_id, file_content)
            else:
                return jsonify({"status": "error", "message": f"Failed to download document from DGCA. Status: {r.status_code}"}), 502
        
        return Response(file_content, mimetype="application/pdf")
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/documents/<int:doc_id>/download", methods=["GET"])
def api_download_document(doc_id):
    try:
        doc = get_document_by_id(doc_id)
        if not doc:
            return jsonify({"status": "error", "message": "Document not found"}), 404
        
        file_content = doc.get("file_content")
        if not file_content:
            url = doc.get("document_download_url")
            if not url:
                return jsonify({"status": "error", "message": "Download URL missing"}), 400
            
            print(f"Downloading PDF on-demand from URL: {url}")
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
            }
            r = requests.get(url, headers=headers, verify=False, timeout=20)
            if r.status_code == 200:
                file_content = r.content
                update_document_file(doc_id, file_content)
            else:
                return jsonify({"status": "error", "message": f"Failed to download document from DGCA. Status: {r.status_code}"}), 502
        
        filename = doc.get("car_series_part") or f"document_{doc_id}"
        # Clean filename characters
        filename = "".join(c for c in filename if c.isalnum() or c in ("-", "_", " ")).strip()
        if not filename.lower().endswith(".pdf"):
            filename += ".pdf"
            
        return Response(
            file_content,
            mimetype="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=\"{filename}\""}
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/documents/<int:doc_id>/markdown", methods=["GET"])
def api_view_markdown(doc_id):
    try:
        doc = get_document_by_id(doc_id)
        if not doc:
            return jsonify({"status": "error", "message": "Document not found"}), 404
        
        rel_path = doc.get("markdown_file_path")
        if not rel_path:
            return jsonify({"status": "error", "message": "Markdown has not been generated for this document yet"}), 400
        
        base_dir = Path(__file__).parent
        file_path = base_dir / rel_path
        if not file_path.exists():
            return jsonify({"status": "error", "message": f"Markdown file not found on disk at {rel_path}"}), 404
            
        content = file_path.read_text(encoding="utf-8")
        return Response(content, mimetype="text/markdown")
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/documents/compare/<int:old_id>/<int:new_id>", methods=["GET"])
def api_compare_documents(old_id, new_id):
    try:
        from comparator import compare_db_documents_by_id
        res = compare_db_documents_by_id(old_id, new_id)
        if "error" in res:
            return jsonify({"status": "error", "message": res["error"]}), 400
        return jsonify(res["comparison"])
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/documents/<int:doc_id>", methods=["DELETE"])
def api_delete_document(doc_id):
    try:
        doc = get_document_by_id(doc_id)
        if not doc:
            return jsonify({"status": "error", "message": "Document not found"}), 404
        
        delete_record_by_id(doc_id)
        return jsonify({"status": "success", "message": f"Document ID {doc_id} successfully deleted."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/documents/<int:doc_id>/delete", methods=["GET"])
def api_delete_document_get(doc_id):
    try:
        doc = get_document_by_id(doc_id)
        if not doc:
            return "Document not found", 404
        
        delete_record_by_id(doc_id)
        return redirect("http://localhost:8501")
    except Exception as e:
        return f"Error: {str(e)}", 500




def calculate_next_run(frequency, start_time):
    if frequency == "Hourly":
        return start_time + timedelta(hours=1)
    elif frequency == "Daily":
        return start_time + timedelta(days=1)
    elif frequency == "Weekly":
        return start_time + timedelta(weeks=1)
    elif frequency == "Monthly":
        return start_time + timedelta(days=30)
    return None


@app.route("/api/scheduler", methods=["GET"])
def api_get_scheduler():
    try:
        settings = get_scheduler_settings()
        return jsonify(settings)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/scheduler", methods=["POST"])
def api_post_scheduler():
    try:
        req_data = request.json or {}
        frequency = req_data.get("frequency", "Disabled")

        if frequency not in ["Disabled", "Hourly", "Daily", "Weekly", "Monthly"]:
            return jsonify({"status": "error", "message": f"Invalid frequency: {frequency}"}), 400

        is_active = 0 if frequency == "Disabled" else 1

        if is_active == 1:
            next_run_dt = calculate_next_run(frequency, datetime.now())
            next_run_str = next_run_dt.isoformat() if next_run_dt else None
        else:
            next_run_str = None

        current_settings = get_scheduler_settings()
        last_run = current_settings.get("last_run") if current_settings else None

        update_scheduler_settings(frequency, is_active, last_run, next_run_str)

        return jsonify({
            "status": "success",
            "message": f"Scheduler configured to {frequency}.",
            "data": {
                "frequency": frequency,
                "is_active": is_active,
                "last_run": last_run,
                "next_run": next_run_str
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


def run_scheduler_loop():
    # Dedicated event loop inside the thread to avoid Playwright initialization error
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    print("[Scheduler] Background daemon thread initialized.")
    while True:
        try:
            settings = get_scheduler_settings()
            if settings and settings.get("is_active") == 1:
                next_run_str = settings.get("next_run")
                if next_run_str:
                    next_run = datetime.fromisoformat(next_run_str)
                    if datetime.now() >= next_run:
                        print(f"[{datetime.now()}] [Scheduler] Running scheduled crawl...")
                        try:
                            records = scrape(
                                target_url=TARGET_URL,
                                output_path=OUTPUT_JSON,
                                headless=True,
                                max_rows=0,
                                channel="msedge"
                            )
                            sync_scraped_records(records)

                            if OUTPUT_JSON.exists():
                                try:
                                    os.remove(OUTPUT_JSON)
                                except Exception:
                                    pass

                            last_run_str = datetime.now().isoformat()
                            next_run_dt = calculate_next_run(settings.get("frequency"), datetime.now())
                            next_run_next_str = next_run_dt.isoformat() if next_run_dt else None

                            update_scheduler_settings(
                                frequency=settings.get("frequency"),
                                is_active=1,
                                last_run=last_run_str,
                                next_run=next_run_next_str
                            )
                            print(f"[{datetime.now()}] [Scheduler] Crawler run complete. Next scheduled: {next_run_next_str}")
                        except Exception as scrape_err:
                            print(f"[{datetime.now()}] [Scheduler] Scraper failed: {str(scrape_err)}")
                            last_run_str = f"Error: {str(scrape_err)}"
                            next_run_dt = calculate_next_run(settings.get("frequency"), datetime.now())
                            next_run_next_str = next_run_dt.isoformat() if next_run_dt else None
                            update_scheduler_settings(
                                frequency=settings.get("frequency"),
                                is_active=1,
                                last_run=last_run_str,
                                next_run=next_run_next_str
                            )
        except Exception as loop_err:
            print(f"[{datetime.now()}] [Scheduler] Daemon error: {str(loop_err)}")

        time.sleep(10)


if __name__ == "__main__":
    # Start background scheduler daemon
    scheduler_thread = threading.Thread(target=run_scheduler_loop, daemon=True)
    scheduler_thread.start()

    # Start background markdown processor daemon
    markdown_worker_thread = threading.Thread(target=run_markdown_worker_loop, daemon=True)
    markdown_worker_thread.start()

    app.run(debug=True, port=5000, use_reloader=False)
