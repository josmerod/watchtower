import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            print("Navigating...")
            await page.goto("https://www.opensourceprojects.dev/", timeout=60000)
            print("Waiting for load state...")
            await page.wait_for_load_state("networkidle")
            
            # Save HTML
            content = await page.content()
            with open("debug_source.html", "w", encoding="utf-8") as f:
                f.write(content)
            print("Saved debug_source.html")
            
            # Try to identify items
            # It seems to be a list of cards. Let's look for common tags.
            # Just printing the first few <a> tags text and hrefs to see structure
            links = await page.query_selector_all("a")
            print(f"Found {len(links)} links")
            for i, link in enumerate(links[:20]):
                text = await link.inner_text()
                href = await link.get_attribute("href")
                print(f"Link {i}: {text.strip()} -> {href}")
                
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
