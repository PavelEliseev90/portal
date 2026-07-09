"""Capture lot detail modal screenshot for presentation."""
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(__file__).parent / "screenshots" / "04-lot-detail-modal.png"


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        page.goto("http://localhost:8005/viewer.html", wait_until="networkidle")
        page.wait_for_selector("button[data-calc]", timeout=20_000)
        page.locator("button[data-calc]").first.click()
        page.wait_for_function(
            """() => {
              const b = document.querySelector('button[data-calc]');
              return b && b.textContent.includes('Пересчитать');
            }""",
            timeout=90_000,
        )
        page.locator("#rows tr").first.locator("td").nth(1).click()
        page.wait_for_selector("#modalBack[style*='flex'], #modalBack", timeout=15_000)
        page.wait_for_function(
            "() => getComputedStyle(document.getElementById('modalBack')).display === 'flex'",
            timeout=10_000,
        )
        page.wait_for_timeout(800)
        page.locator("#modalBack .modal").screenshot(path=str(OUT))
        browser.close()
    print(f"Saved: {OUT}")


if __name__ == "__main__":
    main()
