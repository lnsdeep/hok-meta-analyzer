import asyncio
import json
import csv
import os
import re
import random
from datetime import datetime
from playwright.async_api import async_playwright

# Data Credits:
# 1. English Hero Names / Epithets: https://liquipedia.net/honorofkings/
# 2. Hero Meta Stats / Metrics: https://camp.honorofkings.com/


# Extensive mapping for Global names -> Liquipedia URL paths
# If a hero keeps returning blank, add their global name and Liquipedia page name here.
MANUAL_MAPPINGS = {
    "Consort Yu": "Consort_Yu",
    "Donghuang": "Donghuang",
    "Arli": "Arli",
    "Ming": "Ming_Shiyin",
    "Prince of Lanling": "Lanling_Wang",
    "Wuyan": "Wuyan",
    "Lam": "Lam",
    "Lady Zhen": "Zhen_Ji",
    "Princess Frost": "Wang_Zhaojun",
    "Master Lu": "Master_Luban",
    "Doria": "Dolia",
    "Kui": "Kui",
    "Liang": "Zhang_Liang",
    "Menki": "Menki",
    "Fang": "Fang",
    "Biron": "Biron",
    "Wukong": "Sun_Wukong",
    "Musashi": "Musashi",
    "Dr Bian": "Dr_Bian",
    "Gao": "Gao",
    "Yango": "Yango",
    "Cirrus": "Yun_Zhongjun",
    "Arke": "A_Ke",
    "Flowborn (Tank)": "Flowborn/Tank",
    "Flowborn (Marksman)": "Flowborn/Marksman",
    "Flowborn (Mage)": "Flowborn/Mage",
    "Niumo": "Toro_(Honor_of_Kings)",
    "Shangguan": "Shangguan",
    "Pei": "Pei",
    "Kongming": "Kongming",
    "Shouyue": "Shouyue",
    "Xuance": "Xuance",
    "Yuhuan": "Yuhuan",
    "Haya": "Hai_Yue",
    "Mayene": "Ji_Xiaoman",
    "Ying": "Ying",
    "Jing": "Jing",
    "Shi": "Shi", # User confirmed https://liquipedia.net/honorofkings/Shi
    "Lady Sun": "Lady_Sun",
    "Dun": "Dun",
    "Zilong": "Zilong",
    "Mozi": "Mozi",
    "Garo": "Garo",
    "Arthur": "Arthur_(Honor_of_Kings)",
    "Diaochan": "Diaochan_(Honor_of_Kings)",
    "Lu Bu": "Lu_Bu_(Honor_of_Kings)"
}

async def safe_goto(page, url, retries=3, initial_delay=2, custom_headers=None):
    """Navigates to a URL with retry logic and exponential backoff."""
    if custom_headers:
        await page.set_extra_http_headers(custom_headers)
        
    for i in range(retries):
        try:
            # We use a slightly longer timeout for reliable loads
            response = await page.goto(url, timeout=15000, wait_until="domcontentloaded")
            if response and response.status == 429:
                raise Exception("HTTP 429: Too Many Requests")
            return response
        except Exception as e:
            if i == retries - 1:
                print(f"Failed to load {url} after {retries} attempts: {e}")
                return None
            # Exponential backoff: 2, 4, 8... with a little jitter
            delay = (initial_delay * (2 ** i)) + (random.random() * 2)
            print(f"Retry {i+1}/{retries} for {url} in {delay:.1f}s due to: {e}")
            await asyncio.sleep(delay)
    return None

async def get_liquipedia_mappings(context):
    """Scrapes the Liquipedia Portal:Heroes page to build a Global Name -> Wiki Path mapping."""
    page = await context.new_page()
    url = "https://liquipedia.net/honorofkings/Portal:Heroes"
    print(f"Fetching hero mappings from {url}...")
    
    mappings = {}
    try:
        # Use retry logic for the portal too
        success = await safe_goto(page, url)
        if not success:
            return mappings

        # Find all hero links in the portal tables
        links = await page.locator('.wiki-table a').all()
        for link in links:
            name = (await link.inner_text()).strip()
            href = await link.get_attribute('href')
            if name and href and '/honorofkings/' in href:
                path = href.split('/honorofkings/')[-1]
                mappings[name] = path
        
        # Also check the list items if tables don't cover everything
        list_links = await page.locator('li a').all()
        for link in list_links:
            name = (await link.inner_text()).strip()
            href = await link.get_attribute('href')
            if name and href and '/honorofkings/' in href and name not in mappings:
                path = href.split('/honorofkings/')[-1]
                mappings[name] = path
                
        print(f"Built mapping for {len(mappings)} heroes from portal.")
    except Exception as e:
        print(f"Error building dynamic mapping: {e}")
    finally:
        await page.close()
    return mappings

async def process_hero(semaphore, context, h, idx, total, liquipedia_map):
    """Processes a single hero: fetches metrics from Camp and metadata from Liquipedia."""
    async with semaphore:
        hero_id = h.get("heroId")
        name = h.get("heroName")
        roles = [r for r in [h.get("mainJobName"), h.get("minorJobName")] if r]
        
        hero_obj = {
            "id": hero_id,
            "chinese_hero_name": name,
            "english_hero_name": "", # Epithet from Liquipedia
            "roles": ", ".join(roles),
            "recommended_lane": h.get("recommendRoadName"),
            "image_url": h.get("icon"),
            "hero_page_url": f"https://camp.honorofkings.com/h5/app/index.html#/hero-detail?heroId={hero_id}",
            "popularity": "N/A", "win_rate": "0.00%", "pick_rate": "0.00%", "ban_rate": "0.00%"
        }

        print(f"[{idx+1}/{total}] Starting {name}...")
        page = await context.new_page()
        
        # -- 1. Get Camp Metrics --
        try:
            async with page.expect_response(lambda r: "getherodataall" in r.url and r.status == 200, timeout=10000) as metrics_res_info:
                # Reuse safe_goto for metrics page
                await safe_goto(page, hero_obj["hero_page_url"])
            
            metrics_res = await metrics_res_info.value
            metrics_data = await metrics_res.json()
            base_data = metrics_data.get("data", {}).get("heroData", {}).get("baseData", {})
            
            hero_obj["popularity"] = base_data.get("hot", "N/A")
            hero_obj["win_rate"] = base_data.get("winRate", "0.00%")
            hero_obj["pick_rate"] = base_data.get("matchRate", "0.00%")
            hero_obj["ban_rate"] = base_data.get("banRate", "0.00%")
        except Exception as e:
            print(f"  [!] Failed metrics for {name}: {e}")

        # -- 2. Scrape Liquipedia for Epithet --
        url_path = MANUAL_MAPPINGS.get(name) or liquipedia_map.get(name) or name.replace(" ", "_").replace("'", "%27")
        liq_url = f"https://liquipedia.net/honorofkings/{url_path}"
        
        # Liquipedia specific headers
        liq_headers = {
            "User-Agent": "HOK-Scraper-Bot/1.0 (Contact: user@example.com) " + 
                          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        try:
            # Navigate to Liquipedia using retry logic and custom headers
            success = await safe_goto(page, liq_url, custom_headers=liq_headers)
            
            if success:
                candidate_texts = []
                # Check headers (usually the 2nd header is the epithet)
                headers = await page.locator('.infobox-header-2').all_inner_texts()
                candidate_texts.extend(headers)
                
                # Also check descriptions but be careful of labels
                descriptions = await page.locator('.infobox-description').all_inner_texts()
                candidate_texts.extend(descriptions)
                
                ignore_list = ["General Information", "Esports Statistics", "Abilities", "Strategy", "History", "Trivia", "External Links", "Overview", "Lane", "Role"]
                
                for text in candidate_texts:
                    clean_text = text.strip()
                    if not clean_text or clean_text in ignore_list: continue
                    if clean_text.endswith(':'): continue
                    if clean_text.lower() in [i.lower() for i in ignore_list]: continue
                    
                    hero_obj["english_hero_name"] = clean_text
                    break
        except Exception as e:
            print(f"  [!] Failed Liquipedia for {name}: {e}")
        finally:
            await page.close()
            print(f"[{idx+1}/{total}] Completed {name}.")
            
        return hero_obj

async def scrape_all():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Shared context for the script
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 800}
        )
        
        # 1. Build initial mappings from Portal
        liquipedia_map = await get_liquipedia_mappings(context)
        
        # 2. Get the base list of heroes from the Camp site
        page = await context.new_page()
        base_url = "https://camp.honorofkings.com/h5/app/index.html#/hero-homepage"
        print(f"Navigating to {base_url} to fetch base hero list...")
        
        hero_data_payload = {}
        try:
            async with page.expect_response(lambda r: "getallherobriefinfo" in r.url and r.status == 200, timeout=20000) as response_info:
                await page.goto(base_url)
                try:
                    cookie_btn = page.get_by_role("button", name="Accept")
                    if await cookie_btn.is_visible(): await cookie_btn.click()
                except: pass
                
                all_heroes_btn = page.get_by_text("All heroes")
                await all_heroes_btn.wait_for(state="visible", timeout=10000)
                await all_heroes_btn.click()

            res = await response_info.value
            hero_data_payload = await res.json()
        finally:
            await page.close()

        raw_list = hero_data_payload.get("data", {}).get("heroList", [])
        if not raw_list:
            print("No heroes found. Exiting.")
            await browser.close()
            return

        print(f"Found {len(raw_list)} heroes. Processing concurrently (max 5 at a time)...")

        # 3. Process heroes concurrently using Semaphore and gather
        semaphore = asyncio.Semaphore(5)
        tasks = []
        for i, h in enumerate(raw_list):
            tasks.append(process_hero(semaphore, context, h, i, len(raw_list), liquipedia_map))
        
        processed_heroes = await asyncio.gather(*tasks)

        # -- Save Results --
        if processed_heroes:
            # Filter out any None results if Error Handling was modified to return None
            processed_heroes = [h for h in processed_heroes if h]
            
            with open("heroes.json", "w", encoding="utf-8") as f:
                json.dump(processed_heroes, f, indent=4, ensure_ascii=False)
            
            with open("heroes.csv", "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=processed_heroes[0].keys())
                writer.writeheader()
                writer.writerows(processed_heroes)

            print(f"Done! Saved {len(processed_heroes)} heroes to json and csv.")

            # --- ADD THIS NEW METADATA BLOCK ---
            from datetime import timezone
            
            # GitHub Actions runs in UTC, so we will format the time accordingly
            now = datetime.now()
            utc_now = datetime.now(timezone.utc)
            
            metadata_content = {
                "last_updated": now.strftime("%Y-%m-%d %H:%M:%S"),
                "data_refresh_time": utc_now.strftime("%Y-%m-%dT%H:%M:%SZ")
            }
            
            with open("metadata.json", "w", encoding="utf-8") as f:
                json.dump(metadata_content, f, indent=4)
                
            print("Updated metadata.json with latest timestamps.")
            # -----------------------------------
        
        await browser.close()

if __name__ == "__main__":
    start_time = datetime.now()
    asyncio.run(scrape_all())
    end_time = datetime.now()
    print(f"Total execution time: {end_time - start_time}")
