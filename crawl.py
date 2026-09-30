#!/usr/bin/env python3
"""DGCA Civil Aviation Requirements (CAR) document scraper using Playwright.

The DGCA "digigov" portal renders its CAR catalogue dynamically. Investigation
of the live page established exactly how documents are wired up:

* The catalogue lives in a single ``table.MsoNormalTable`` whose header row is
  "CAR Series Part | Issue No. and Date | Subject | Most recent Amendment No. |
  Date of Amendment". Rows are grouped under ``SERIES``/``SECTION`` heading rows.
* Each *active* document row has an anchor in its first cell carrying a
  ``data-url="dynamicPdf/<attachId>"`` attribute (REVOKED rows have no anchor and
  no link). The anchor has no ``href`` and no inline ``onclick`` -- the click is
  bound in JavaScript.
* Clicking the anchor triggers ``GET <portal>/Upload?flag=iframeAttachView&
  attachId=<attachId>`` which streams the PDF (``application/pdf``). The
  ``attachId`` is exactly the ``data-url`` value with the ``dynamicPdf/`` prefix
  removed (already URL-encoded).

The scraper therefore drives a real Chromium/Edge browser (so the session and
JavaScript behave naturally), waits for the catalogue to render, reads the
``data-url`` of every document row, and builds the absolute download URL
directly -- no per-row clicking required. A generic click + network-interception
fallback is retained in case the page structure changes.

Usage:
    python app.py --url "<DGCA CAR sub-url>" --output dgca_car_docs.json --channel msedge

Install:
    pip install playwright
    python -m playwright install chromium   # or use --channel msedge / chrome
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

from playwright.sync_api import (
    Browser,
    BrowserContext,
    Download,
    Error as PlaywrightError,
    Page,
    Response,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)

# Confirmed portal endpoint that streams a document for a given attachId.
ATTACH_ENDPOINT = "Upload?flag=iframeAttachView&attachId={attach_id}"
# data-url prefix that precedes the attachId on each document anchor.
DATA_URL_PREFIX = "dynamicPdf/"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------
@dataclass
class Record:
    car_series_part: str
    issue_no_date: str
    subject: str
    amendment_no_date: str
    document_download_url: str
    car_series: str = ""  # SERIES/SECTION heading the row sits under (context)


@dataclass
class NetEvent:
    ts: float
    url: str
    status: int
    content_type: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def normalize_space(value: Optional[str]) -> str:
    return re.sub(r"\s+", " ", (value or "")).strip()


def is_same_origin(url: str, target_url: str) -> bool:
    parsed = urlparse(url)
    target = urlparse(target_url)
    return parsed.scheme in {"http", "https"} and parsed.netloc == target.netloc


def portal_base(target_url: str) -> str:
    """Return the portal root (e.g. https://host/digigov-portal/) for urljoin."""
    parsed = urlparse(target_url)
    path = parsed.path
    if not path.endswith("/"):
        path = path.rsplit("/", 1)[0] + "/"
    return f"{parsed.scheme}://{parsed.netloc}{path}"


def attach_id_from_data_url(data_url: str) -> str:
    """Extract the (already URL-encoded) attachId from a data-url attribute."""
    value = (data_url or "").strip()
    if value.startswith(DATA_URL_PREFIX):
        return value[len(DATA_URL_PREFIX):]
    # Fall back to the trailing path segment if the prefix ever changes.
    return value.rsplit("/", 1)[-1] if "/" in value else value


def build_download_url(base: str, attach_id: str) -> str:
    # attach_id is already percent-encoded in the DOM; do not re-encode it.
    return urljoin(base, ATTACH_ENDPOINT.format(attach_id=attach_id))


def looks_like_doc_url(url: str, content_type: str = "") -> bool:
    u = url.lower()
    c = (content_type or "").lower()
    if u.endswith(".pdf") or ".pdf?" in u or "application/pdf" in c or "octet-stream" in c:
        return True
    return any(h in u for h in ("upload?flag=iframeattachview", "attachid=", "downloaddocument"))


# ---------------------------------------------------------------------------
# Primary extraction: read data-url anchors straight from the CAR table
# ---------------------------------------------------------------------------
def extract_table_rows(page: Page) -> List[Dict[str, Any]]:
    """Walk the CAR catalogue table, returning one dict per document row.

    Each dict carries the four schema fields plus the SERIES/SECTION context and
    the raw ``data-url`` so the caller can build the absolute download URL.
    """
    return page.evaluate(
        r"""
        () => {
            const norm = (s) => (s || '').replace(/\s+/g, ' ').trim();
            const table = document.querySelector('table.MsoNormalTable')
                || Array.from(document.querySelectorAll('table'))
                    .find(t => /CAR Series Part/i.test(t.innerText || ''));
            if (!table) return [];

            const out = [];
            let section = '';
            for (const tr of table.querySelectorAll('tr')) {
                const cells = Array.from(tr.querySelectorAll('td, th'))
                    .map(td => norm(td.innerText));
                const nonEmpty = cells.filter(Boolean);

                // Skip the header row.
                if (/^CAR Series Part$/i.test(cells[0] || '')) continue;

                // SERIES/SECTION heading rows (single spanning cell, no anchor).
                const anchor = tr.querySelector('a[data-url]');
                if (!anchor && nonEmpty.length <= 1 &&
                    /^(SECTION|SERIES)\b/i.test(nonEmpty[0] || '')) {
                    section = norm(nonEmpty[0]).slice(0, 250);
                    continue;
                }

                if (!anchor) continue;  // e.g. REVOKED rows -> no document

                const dataUrl = anchor.getAttribute('data-url') || '';
                if (!dataUrl) continue;

                out.push({
                    car_series: section,
                    car_series_part: cells[0] || norm(anchor.innerText),
                    issue_no_date: cells[1] || '',
                    subject: cells[2] || '',
                    // "Most recent Amendment No." + "Date of Amendment"
                    amendment_no_date: norm([cells[3], cells[4]].filter(Boolean).join(' ')),
                    data_url: dataUrl,
                });
            }
            return out;
        }
        """
    )


def scrape_via_data_urls(page: Page, target_url: str) -> List[Record]:
    base = portal_base(target_url)
    rows = extract_table_rows(page)
    records: List[Record] = []
    seen = set()
    for row in rows:
        attach_id = attach_id_from_data_url(row.get("data_url", ""))
        if not attach_id:
            continue
        url = build_download_url(base, attach_id)
        if not is_same_origin(url, target_url):
            continue
        key = (normalize_space(row.get("car_series_part")), url)
        if key in seen:
            continue
        seen.add(key)
        records.append(
            Record(
                car_series_part=normalize_space(row.get("car_series_part")),
                issue_no_date=normalize_space(row.get("issue_no_date")),
                subject=normalize_space(row.get("subject")),
                amendment_no_date=normalize_space(row.get("amendment_no_date")),
                document_download_url=url,
                car_series=normalize_space(row.get("car_series")),
            )
        )
    return records


# ---------------------------------------------------------------------------
# Fallback extraction: click each candidate and intercept the network
# ---------------------------------------------------------------------------
def scrape_via_clicks(page: Page, target_url: str, events: List[NetEvent]) -> List[Record]:
    """Generic fallback used only if no data-url anchors are present.

    Tags every plausible document anchor, clicks it, and harvests the document
    URL from intercepted same-origin responses.
    """
    base = portal_base(target_url)
    tagged: List[Dict[str, Any]] = page.evaluate(
        r"""
        () => {
            const norm = (s) => (s || '').replace(/\s+/g, ' ').trim();
            const table = document.querySelector('table.MsoNormalTable')
                || Array.from(document.querySelectorAll('table'))
                    .find(t => /CAR Series Part/i.test(t.innerText || ''));
            if (!table) return [];
            let section = '', idx = 1;
            const out = [];
            for (const tr of table.querySelectorAll('tr')) {
                const cells = Array.from(tr.querySelectorAll('td, th'))
                    .map(td => norm(td.innerText));
                const nonEmpty = cells.filter(Boolean);
                const a = tr.querySelector('a');
                if (!a && nonEmpty.length <= 1 && /^(SECTION|SERIES)\b/i.test(nonEmpty[0] || '')) {
                    section = norm(nonEmpty[0]).slice(0, 250);
                    continue;
                }
                if (!a) continue;
                a.setAttribute('data-scrape-id', String(idx));
                out.push({
                    scrape_id: String(idx), car_series: section,
                    car_series_part: cells[0] || norm(a.innerText),
                    issue_no_date: cells[1] || '', subject: cells[2] || '',
                    amendment_no_date: norm([cells[3], cells[4]].filter(Boolean).join(' ')),
                });
                idx += 1;
            }
            return out;
        }
        """
    )

    records: List[Record] = []
    seen = set()
    for cand in tagged:
        locator = page.locator(f"a[data-scrape-id='{cand['scrape_id']}']").first
        before_ts = time.time()
        try:
            locator.scroll_into_view_if_needed(timeout=8_000)
            locator.click(timeout=8_000)
        except PlaywrightError:
            continue
        try:
            page.wait_for_load_state("networkidle", timeout=6_000)
        except PlaywrightTimeoutError:
            pass

        doc_urls = [
            e.url for e in events
            if e.ts >= before_ts and is_same_origin(e.url, target_url)
            and looks_like_doc_url(e.url, e.content_type)
        ]
        if not doc_urls:
            continue
        url = sorted(dict.fromkeys(doc_urls), key=len)[0]
        key = (normalize_space(cand.get("car_series_part")), url)
        if key in seen:
            continue
        seen.add(key)
        records.append(
            Record(
                car_series_part=normalize_space(cand.get("car_series_part")),
                issue_no_date=normalize_space(cand.get("issue_no_date")),
                subject=normalize_space(cand.get("subject")),
                amendment_no_date=normalize_space(cand.get("amendment_no_date")),
                document_download_url=url,
                car_series=normalize_space(cand.get("car_series")),
            )
        )
    return records


# ---------------------------------------------------------------------------
# Scraper core
# ---------------------------------------------------------------------------
def scrape(
    target_url: str,
    output_path: Path,
    headless: bool,
    max_rows: int,
    channel: str = "",
) -> List[Record]:
    if urlparse(target_url).scheme not in {"http", "https"}:
        raise ValueError("Target URL must be http/https")

    events: List[NetEvent] = []

    with sync_playwright() as p:
        # channel ("chrome"/"msedge") uses a browser already installed on the
        # machine, avoiding Playwright's bundled-Chromium download (handy when a
        # corporate proxy blocks the CDN). Empty channel = bundled Chromium.
        launch_kwargs: Dict[str, Any] = {"headless": headless}
        if channel:
            launch_kwargs["channel"] = channel
        browser: Browser = p.chromium.launch(**launch_kwargs)
        context: BrowserContext = browser.new_context(
            accept_downloads=True,
            ignore_https_errors=True,  # bypass corporate proxy SSL issues
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/127.0.0.0 Safari/537.36"
            ),
        )
        page: Page = context.new_page()
        # Increase default navigation timeout for slow government portals
        page.set_default_navigation_timeout(180_000)
        page.set_default_timeout(60_000)

        def on_response(response: Response) -> None:
            if is_same_origin(response.url, target_url):
                events.append(
                    NetEvent(
                        ts=time.time(),
                        url=response.url,
                        status=response.status,
                        content_type=response.headers.get("content-type", ""),
                    )
                )

        page.on("response", on_response)

        # --- Load target (with retries for slow government portals) ---------
        # Use 'commit' wait strategy: resolves as soon as the server responds
        # with HTTP headers — much faster than waiting for DOM/load events.
        # Fall back to 'domcontentloaded' if 'commit' is not enough.
        max_nav_retries = 3
        nav_success = False
        last_nav_error: Optional[Exception] = None
        for attempt in range(1, max_nav_retries + 1):
            try:
                print(f"[Scraper] Navigation attempt {attempt}/{max_nav_retries}...")
                page.goto(target_url, wait_until="commit", timeout=120_000)
                nav_success = True
                break
            except PlaywrightTimeoutError as exc:
                last_nav_error = exc
                print(f"[Scraper] Attempt {attempt} timed out: {exc}")
                if attempt < max_nav_retries:
                    print(f"[Scraper] Retrying in 5 seconds...")
                    time.sleep(5)
            except PlaywrightError as exc:
                last_nav_error = exc
                print(f"[Scraper] Attempt {attempt} failed: {exc}")
                if attempt < max_nav_retries:
                    time.sleep(5)

        if not nav_success:
            raise RuntimeError(
                f"Failed to navigate to the DGCA portal after {max_nav_retries} attempts. "
                f"Last error: {last_nav_error}. "
                "Please check your network connection and ensure the portal is accessible."
            )

        # The CAR catalogue is injected via AJAX after initial load; wait for it.
        # Since we navigated with wait_until='commit', the page JS may still be
        # loading. Give it a moment before checking for table content.
        time.sleep(3)
        try:
            # Wait for the table structure
            page.wait_for_selector(
                "table.MsoNormalTable, table:has-text('CAR Series Part')",
                state="visible",
                timeout=90_000,
            )
            # CRITICAL: Wait for at least one data cell to have actual text 
            # to ensure AJAX content is rendered.
            page.wait_for_function(
                "() => { const cells = document.querySelectorAll('td'); return cells.length > 0 && cells[0].innerText.trim().length > 0; }",
                timeout=60_000
            )
            # Give it a tiny bit of extra time to settle
            time.sleep(2)
        except PlaywrightTimeoutError as exc:
            raise RuntimeError(
                "CAR catalogue table did not appear; the portal structure may "
                "have changed or the URL is incorrect."
            ) from exc
        try:
            page.wait_for_load_state("networkidle", timeout=30_000)
        except PlaywrightTimeoutError:
            pass

        if page.url and not is_same_origin(page.url, target_url):
            raise RuntimeError(f"Navigation escaped target origin: {page.url}")

        # --- Primary path: derive URLs from data-url attributes -------------
        records = scrape_via_data_urls(page, target_url)

        # --- Fallback path: click + intercept (only if primary found nothing)
        if not records:
            records = scrape_via_clicks(page, target_url, events)

        browser.close()

    if max_rows > 0:
        records = records[:max_rows]

    output_path.write_text(
        json.dumps([asdict(r) for r in records], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return records


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scrape DGCA CAR Series Part document download URLs with Playwright"
    )
    parser.add_argument("--url", required=True, help="DGCA CAR sub-url to scrape")
    parser.add_argument(
        "--output", default="dgca_car_documents.json", help="Path to JSON output file"
    )
    parser.add_argument(
        "--headless", action="store_true", help="Run browser headless (default: headed)"
    )
    parser.add_argument(
        "--max-rows", type=int, default=0,
        help="Limit number of records written (0 = no limit; useful for testing)",
    )
    parser.add_argument(
        "--channel", default="",
        choices=["", "chrome", "msedge", "chrome-beta", "msedge-beta"],
        help="Use an installed browser instead of bundled Chromium "
        "(e.g. 'msedge' or 'chrome' to skip the Playwright download).",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        records = scrape(
            args.url, Path(args.output), args.headless, args.max_rows, args.channel
        )
    except Exception as exc:  # noqa: BLE001 - surface any failure to the CLI
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    print(f"Extracted {len(records)} records -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
