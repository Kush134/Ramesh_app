"""
temp_update_db.py
-----------------
Temporary one-off script to:
  - Parse markdown chunks from two existing .md files
  - Store those chunks (as JSON) into the car_documents table for IDs 3 and 4
  - Set markdown_file_path and markdown_updated = 1

Does NOT change any existing pipeline code. Safe to run multiple times.
Run with:  ..\\venv\\Scripts\\python.exe temp_update_db.py
"""

import json
import re
import sqlite3
from pathlib import Path

# ── paths ──────────────────────────────────────────────────────────
THIS_DIR = Path(__file__).parent
DB_PATH  = THIS_DIR / "dgca_documents.db"

# doc_id → markdown file (relative to THIS_DIR / Markdown_file/)
UPDATES = {
    3: THIS_DIR / "Markdown_file" / "car_7_129_CHUNK_U.md",
    4: THIS_DIR / "Markdown_file" / "CAR 145_2_CHUNK_U.md",
}

# -- helpers --------------------------------------------------------

def clean_text(value: str) -> str:
    value = value.replace("\u2013", "-").replace("\u2014", "-")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def parse_markdown_chunks(file_path: Path) -> list[dict]:
    """
    Parses a CHUNK_U.md file into a list of chunk dicts.

    Expected format:
        ================================================================================
        CHUNK ID: <int>
        CLAUSE: <heading text>
        --------------------------------------------------------------------------------
        ## <heading text>
        <body content>

    Returns list of {"chunk_id": int, "clause": str, "content": str}
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Markdown file not found: {file_path}")

    content = file_path.read_text(encoding="utf-8")
    parts = content.split("================================================================================")

    chunks: list[dict] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        match = re.search(
            r"CHUNK ID:\s*(\d+)\s+CLAUSE:\s*(.*?)\s*\n-+\s*\n(.*)",
            part,
            re.DOTALL,
        )
        if match:
            chunks.append({
                "chunk_id": int(match.group(1)),
                "clause":   match.group(2).strip(),
                "content":  clean_text(match.group(3)),
            })

    return chunks


# ── update & verify ────────────────────────────────────────────────

def update_doc(doc_id: int, md_path: Path) -> None:
    print(f"\n[Doc {doc_id}] Parsing: {md_path.name} ...")
    chunks = parse_markdown_chunks(md_path)
    if not chunks:
        print(f"[Doc {doc_id}] WARNING: No chunks parsed -- aborting update.")
        return

    print(f"[Doc {doc_id}] Parsed {len(chunks)} chunks. First clause: '{chunks[0]['clause']}'")

    chunks_json  = json.dumps(chunks, ensure_ascii=False)
    relative_path = str(md_path.relative_to(THIS_DIR))   # e.g. "Markdown_file\car_7_129_CHUNK_U.md"

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(
            "SELECT id FROM car_documents WHERE id = ?", (doc_id,)
        )
        if not cur.fetchone():
            print(f"[Doc {doc_id}] SKIP: Record not found in DB -- check the ID.")
            return

        conn.execute(
            """
            UPDATE car_documents
            SET chunks             = ?,
                markdown_file_path = ?,
                markdown_updated   = 1
            WHERE id = ?
            """,
            (chunks_json, relative_path, doc_id),
        )
        conn.commit()
        print(f"[Doc {doc_id}] OK DB updated -- chunks={len(chunks)}, markdown_updated=1")
    except Exception as exc:
        print(f"[Doc {doc_id}] ERROR DB error: {exc}")
        raise
    finally:
        conn.close()


def verify_doc(doc_id: int) -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT id, markdown_updated, markdown_file_path, chunks "
            "FROM car_documents WHERE id = ?",
            (doc_id,),
        ).fetchone()
        if not row:
            print(f"[Verify Doc {doc_id}] No record found.")
            return
        stored_chunks = json.loads(row["chunks"]) if row["chunks"] else []
        print(
            f"[Verify Doc {doc_id}]  "
            f"markdown_updated={row['markdown_updated']},  "
            f"file='{row['markdown_file_path']}',  "
            f"chunks_count={len(stored_chunks)},  "
            f"first_clause='{stored_chunks[0]['clause'] if stored_chunks else 'N/A'}'"
        )
    finally:
        conn.close()


# ── main ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 65)
    print("  Temporary DB Chunk Update")
    print("  Doc 3 <- car_7_129_CHUNK_U.md")
    print("  Doc 4 <- CAR 145_2_CHUNK_U.md")
    print("=" * 65)

    if not DB_PATH.exists():
        print(f"ERROR: Database not found at: {DB_PATH}")
        raise SystemExit(1)

    for doc_id, md_path in UPDATES.items():
        update_doc(doc_id, md_path)

    print("\n── Verification ─────────────────────────────────────────────")
    for doc_id in UPDATES:
        verify_doc(doc_id)

    print("\nAll done.")
