import asyncio
from playwright.async_api import async_playwright
import datetime

async def get_trending_videos():
    print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Iniciando búsqueda de vídeos virales con Playwright...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            await page.goto("https://www.tiktok.com/foryou", timeout=60000)
            await page.wait_for_timeout(8000)  # Espera para que carguen vídeos

            videos = await page.query_selector_all('div[data-e2e="feed-item"]')

            for i, video in enumerate(videos[:5]):
                desc = await video.inner_text()
                print(f"\n--- Vídeo #{i+1} ---\n{desc}\n")
        except Exception as e:
            print(f"[ERROR] Fallo durante scraping: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(get_trending_videos())

