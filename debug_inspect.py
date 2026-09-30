from playwright.sync_api import sync_playwright
import json

def debug_extract(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel="msedge")
        page = browser.new_page()
        print(f"Navigating to {url}")
        page.goto(url, wait_until="networkidle", timeout=60000)
        
        # Wait for any table
        page.wait_for_selector("table", timeout=10000)
        
        tables = page.evaluate("""
            () => {
                return Array.from(document.querySelectorAll('table')).map(t => ({
                    innerText: t.innerText.slice(0, 100),
                    className: t.className,
                    rowCount: t.querySelectorAll('tr').length
                }));
            }
        """)
        print(f"Found {len(tables)} tables")
        for i, t in enumerate(tables):
            print(f"Table {i}: {t}")
            
        # Try to extract rows like crawl.py does
        results = page.evaluate("""
            () => {
                const table = document.querySelector('table.MsoNormalTable')
                    || Array.from(document.querySelectorAll('table'))
                        .find(t => /CAR Series Part/i.test(t.innerText || ''));
                if (!table) return "TABLE NOT FOUND";
                
                const rows = [];
                for (const tr of table.querySelectorAll('tr')) {
                    const cells = Array.from(tr.querySelectorAll('td, th')).map(td => td.innerText.trim());
                    rows.push(cells);
                }
                return rows;
            }
        """)
        print("First 5 rows of detected table:")
        print(json.dumps(results[:5], indent=2))
        
        browser.close()

if __name__ == "__main__":
    url = "https://www.dgca.gov.in/digigov-portal/?baseLocale=en_US?dynamicPage=CivilAviationReqContent/6/160/viewDynamicRuleContLvl2/html&maincivilAviationRequirements/6/0/viewDynamicRulesReq"
    debug_extract(url)
