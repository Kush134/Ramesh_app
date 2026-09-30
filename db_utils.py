import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "dgca_documents.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS car_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            car_series_part TEXT,
            issue_no_date TEXT,
            subject TEXT,
            amendment_no_date TEXT,
            document_download_url TEXT UNIQUE,
            car_series TEXT,
            file_content BLOB,
            status TEXT DEFAULT 'Unchanged',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            markdown_file_path TEXT,
            markdown_updated INTEGER DEFAULT 0,
            chunks TEXT
        )
    """)
    # Migration: check and append new columns in case table was created previously without them
    cursor.execute("PRAGMA table_info(car_documents)")
    cols = [row[1] for row in cursor.fetchall()]
    if "file_content" not in cols:
        cursor.execute("ALTER TABLE car_documents ADD COLUMN file_content BLOB")
    if "created_at" not in cols:
        cursor.execute("ALTER TABLE car_documents ADD COLUMN created_at TIMESTAMP DEFAULT '2026-07-02 00:00:00'")
    if "status" not in cols:
        cursor.execute("ALTER TABLE car_documents ADD COLUMN status TEXT DEFAULT 'Unchanged'")
    if "markdown_file_path" not in cols:
        cursor.execute("ALTER TABLE car_documents ADD COLUMN markdown_file_path TEXT")
    if "markdown_updated" not in cols:
        cursor.execute("ALTER TABLE car_documents ADD COLUMN markdown_updated INTEGER DEFAULT 0")
    if "chunks" not in cols:
        cursor.execute("ALTER TABLE car_documents ADD COLUMN chunks TEXT")

    # Migration: remove UNIQUE constraint from document_download_url if it exists.
    # SQLite cannot drop constraints directly, so we recreate the table without it.
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='car_documents'")
    row = cursor.fetchone()
    if row and "document_download_url TEXT UNIQUE" in row[0]:
        cursor.executescript("""
            PRAGMA foreign_keys = OFF;
            BEGIN;
            CREATE TABLE car_documents_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                car_series_part TEXT,
                issue_no_date TEXT,
                subject TEXT,
                amendment_no_date TEXT,
                document_download_url TEXT,
                car_series TEXT,
                file_content BLOB,
                status TEXT DEFAULT 'Unchanged',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                markdown_file_path TEXT,
                markdown_updated INTEGER DEFAULT 0,
                chunks TEXT
            );
            INSERT INTO car_documents_new
                SELECT id, car_series_part, issue_no_date, subject, amendment_no_date,
                       document_download_url, car_series, file_content,
                       COALESCE(status, 'Unchanged'), created_at,
                       markdown_file_path, markdown_updated, chunks
                FROM car_documents;
            DROP TABLE car_documents;
            ALTER TABLE car_documents_new RENAME TO car_documents;
            COMMIT;
            PRAGMA foreign_keys = ON;
        """)

    # Initialize scheduler settings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scheduler_settings (
            id INTEGER PRIMARY KEY,
            frequency TEXT,
            is_active INTEGER,
            last_run TEXT,
            next_run TEXT
        )
    """)
    cursor.execute("SELECT COUNT(*) FROM scheduler_settings")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO scheduler_settings (id, frequency, is_active, last_run, next_run)
            VALUES (1, 'Disabled', 0, NULL, NULL)
        """)
    conn.commit()
    conn.close()

def save_records(records):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for record in records:
        # Use UPSERT (ON CONFLICT DO UPDATE) to keep downloaded file content and creation date preserved
        cursor.execute("""
            INSERT INTO car_documents (
                car_series_part, issue_no_date, subject, amendment_no_date, document_download_url, car_series, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))
            ON CONFLICT(document_download_url) DO UPDATE SET
                car_series_part=excluded.car_series_part,
                issue_no_date=excluded.issue_no_date,
                subject=excluded.subject,
                amendment_no_date=excluded.amendment_no_date,
                car_series=excluded.car_series
        """, (
            record.car_series_part,
            record.issue_no_date,
            record.subject,
            record.amendment_no_date,
            record.document_download_url,
            record.car_series
        ))
    conn.commit()
    conn.close()

def get_all_records():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    # Fetch all records, returning if a file exists rather than sending the full blob
    cursor.execute("""
        SELECT id, car_series_part, issue_no_date, subject, amendment_no_date, 
               document_download_url, car_series, created_at, status,
               (file_content IS NOT NULL) AS has_file, markdown_file_path, markdown_updated
        FROM car_documents
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_document_by_id(doc_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM car_documents WHERE id = ?", (doc_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def update_document_file(doc_id, file_content):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE car_documents SET file_content = ? WHERE id = ?", (file_content, doc_id))
    conn.commit()
    conn.close()

def get_pending_markdown_documents():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, car_series_part, issue_no_date, document_download_url, file_content
        FROM car_documents
        WHERE status = 'Updated' AND (markdown_updated = 0 OR markdown_updated IS NULL)
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def update_markdown_status(doc_id, file_path, status_flag, chunks_json=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE car_documents
        SET markdown_file_path = ?, markdown_updated = ?, chunks = ?
        WHERE id = ?
    """, (file_path, status_flag, chunks_json, doc_id))
    conn.commit()
    conn.close()

def delete_record_by_id(doc_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM car_documents WHERE id = ?", (doc_id,))
    conn.commit()
    conn.close()


def clear_all_records():
    """Delete every row from car_documents (called before a fresh scrape)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM car_documents")
    # Reset the auto-increment counter so IDs start from 1 again
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='car_documents'")
    conn.commit()
    conn.close()


def get_scheduler_settings():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM scheduler_settings WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def update_scheduler_settings(frequency, is_active, last_run, next_run):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE scheduler_settings
        SET frequency = ?, is_active = ?, last_run = ?, next_run = ?
        WHERE id = 1
    """, (frequency, is_active, last_run, next_run))
    conn.commit()
    conn.close()


def sync_scraped_records(records):
    """
    Sync scraped records to the database with revision-aware status tracking.

    - First run (DB empty): all records inserted as 'Unchanged'.
    - Subsequent runs:
        - Record exists (match by series, part, and version details):
            refresh document_download_url, but preserve the existing status.
        - Record does not exist:
            insert as a new row with status = 'Updated'.
    - No database records are automatically deleted to preserve historic revisions.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Detect first-run: DB is completely empty
    cursor.execute("SELECT COUNT(*) FROM car_documents")
    is_first_run = cursor.fetchone()[0] == 0

    if is_first_run:
        # ── FIRST RUN ─────────────────────────────────────────────────────────
        # Insert every scraped record as 'Unchanged' — this is the baseline.
        for r in records:
            cursor.execute("""
                INSERT OR IGNORE INTO car_documents (
                    car_series_part, issue_no_date, subject, amendment_no_date,
                    document_download_url, car_series, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'Unchanged', datetime('now', 'localtime'))
            """, (
                r.car_series_part,
                r.issue_no_date,
                r.subject,
                r.amendment_no_date,
                r.document_download_url,
                r.car_series
            ))
    else:
        # ── SUBSEQUENT RUNS ───────────────────────────────────────────────────
        # Load existing rows, keyed by composite (car_series, car_series_part, issue_no_date, amendment_no_date)
        cursor.execute("""
            SELECT id, car_series, car_series_part, issue_no_date,
                   amendment_no_date, document_download_url, status
            FROM car_documents
        """)
        db_rows = cursor.fetchall()
        
        # Build lookup dict with full version details as the key
        db_by_key = {}
        existing_ids = set()
        for row in db_rows:
            key = (
                row["car_series"],
                row["car_series_part"],
                row["issue_no_date"],
                row["amendment_no_date"]
            )
            db_by_key[key] = dict(row)
            existing_ids.add(row["id"])

        # Local helper to find the smallest unused positive integer ID (filling gaps)
        def get_next_available_id():
            candidate = 1
            while candidate in existing_ids:
                candidate += 1
            existing_ids.add(candidate)
            return candidate

        for r in records:
            key = (r.car_series, r.car_series_part, r.issue_no_date, r.amendment_no_date)

            if key in db_by_key:
                # ── Record already exists → preserve status, refresh URL
                db_row = db_by_key[key]
                cursor.execute("""
                    UPDATE car_documents
                    SET document_download_url = ?
                    WHERE id = ?
                """, (
                    r.document_download_url,
                    db_row["id"]
                ))
            else:
                # ── Genuinely new or previously deleted version → insert as 'Updated'
                next_id = get_next_available_id()
                cursor.execute("""
                    INSERT OR IGNORE INTO car_documents (
                        id, car_series_part, issue_no_date, subject, amendment_no_date,
                        document_download_url, car_series, status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 'Updated', datetime('now', 'localtime'))
                """, (
                    next_id,
                    r.car_series_part,
                    r.issue_no_date,
                    r.subject,
                    r.amendment_no_date,
                    r.document_download_url,
                    r.car_series
                ))

    conn.commit()
    conn.close()
