import os
import time
import requests
import urllib3
import tempfile
import sys
import json
from pathlib import Path

# Ensure sibling imports inside the API_DEV folder are prioritized
sys.path.insert(0, str(Path(__file__).parent))

from db_utils import (
    get_pending_markdown_documents,
    update_markdown_status,
    update_document_file,
)
from pdf_index_chunker import process_pdf_to_markdown

def sanitize_filename(name: str) -> str:
    """Sanitize the document name to form a safe filename, replacing spaces with underscores."""
    cleaned = "".join(c for c in name if c.isalnum() or c in ("-", "_", " ")).strip()
    cleaned = cleaned.replace(" ", "_")
    # Collapse multiple underscores
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned

def process_single_document(doc: dict) -> None:
    doc_id = doc["id"]
    part = doc.get("car_series_part") or ""
    issue = doc.get("issue_no_date") or ""
    download_url = doc.get("document_download_url")
    file_content = doc.get("file_content")

    print(f"[Markdown Worker] Processing doc {doc_id}: Part='{part}' Issue='{issue}'")

    # 1. Download PDF if not already present in the database blob
    if not file_content:
        if not download_url:
            print(f"[Markdown Worker] ERROR: Document ID {doc_id} has no download URL or file content. Skipping.")
            update_markdown_status(doc_id, None, -1)
            return

        print(f"[Markdown Worker] Downloading PDF from URL: {download_url}")
        try:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
            }
            r = requests.get(download_url, headers=headers, verify=False, timeout=30)
            if r.status_code == 200:
                file_content = r.content
                # Update database content cache
                update_document_file(doc_id, file_content)
                print(f"[Markdown Worker] Successfully downloaded and cached PDF for doc ID {doc_id}.")
            else:
                print(f"[Markdown Worker] ERROR: Failed to download PDF. Status: {r.status_code}")
                update_markdown_status(doc_id, None, -1)
                return
        except Exception as e:
            print(f"[Markdown Worker] ERROR: Exception downloading PDF: {str(e)}")
            update_markdown_status(doc_id, None, -1)
            return

    # 2. Write file_content to temporary file
    temp_pdf_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(file_content)
            temp_pdf_path = tmp.name

        # 3. Form output filepath
        safe_name = sanitize_filename(f"{part}_{issue}")
        if not safe_name:
            safe_name = f"doc_{doc_id}"
        
        markdown_filename = f"{safe_name}.md"
        
        base_dir = Path(__file__).parent
        markdown_dir = base_dir / "Markdown_file"
        markdown_dir.mkdir(parents=True, exist_ok=True)
        markdown_filepath = markdown_dir / markdown_filename

        # Relative path inside the DB: saved as folder + filename
        db_save_path = f"Markdown_file/{markdown_filename}"

        print(f"[Markdown Worker] Chunking to output folder/path: {db_save_path}")
        
        # 4. Call chunker
        success, chunks = process_pdf_to_markdown(temp_pdf_path, str(markdown_filepath))
        
        # 5. Update DB status and file path
        if success and markdown_filepath.exists():
            chunks_json = json.dumps(chunks, ensure_ascii=False) if chunks else None
            update_markdown_status(doc_id, db_save_path, 1, chunks_json)
            print(f"[Markdown Worker] Success: doc ID {doc_id} chunked and status updated.")
        else:
            update_markdown_status(doc_id, None, -1, None)
            print(f"[Markdown Worker] Error: doc ID {doc_id} chunking returned failure or file not written.")

    except Exception as ex:
        print(f"[Markdown Worker] ERROR: Unexpected exception processing doc ID {doc_id}: {str(ex)}")
        update_markdown_status(doc_id, None, -1)
    finally:
        # 6. Cleanup temporary file
        if temp_pdf_path and os.path.exists(temp_pdf_path):
            try:
                os.remove(temp_pdf_path)
            except Exception:
                pass

def run_markdown_worker_loop():
    print("[Markdown Worker] Daemon thread initialized and running.")
    while True:
        try:
            pending_docs = get_pending_markdown_documents()
            if pending_docs:
                print(f"[Markdown Worker] Found {len(pending_docs)} updated documents pending markdown generation.")
                for doc in pending_docs:
                    process_single_document(doc)
            else:
                # No pending work
                pass
        except Exception as e:
            print(f"[Markdown Worker] Loop exception: {str(e)}")
        
        time.sleep(10)
