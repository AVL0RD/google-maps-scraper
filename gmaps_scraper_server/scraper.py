import json
import asyncio # Changed from time
import re
import os
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError # Changed to async
from urllib.parse import urlencode

# Import the extraction functions from our helper module
from . import extractor

# --- Constants ---
BASE_URL = "https://www.google.com/maps/search/"
DEFAULT_TIMEOUT = 30000  # 30 seconds for navigation and selectors
SCROLL_PAUSE_TIME = 1.5  # Pause between scrolls
MAX_SCROLL_ATTEMPTS_WITHOUT_NEW_LINKS = 5 # Stop scrolling if no new links found after this many scrolls

# --- Helper Functions ---
def create_search_url(query, lang="en", geo_coordinates=None, zoom=None):
    """Creates a Google Maps search URL."""
    params = {'q': query, 'hl': lang}
    # Note: geo_coordinates and zoom might require different URL structure (/maps/@lat,lng,zoom)
    # For simplicity, starting with basic query search
    return BASE_URL + "?" + urlencode(params)

# --- Main Scraping Logic ---
async def scrape_google_maps(query, max_places=None, lang="en", headless=True): # Added async
    """
    Scrapes Google Maps for places based on a query.

    Args:
        query (str): The search query (e.g., "restaurants in New York").
        max_places (int, optional): Maximum number of places to scrape. Defaults to None (scrape all found).
        lang (str, optional): Language code for Google Maps (e.g., 'en', 'es'). Defaults to "en".
        headless (bool, optional): Whether to run the browser in headless mode. Defaults to True.

    Returns:
        list: A list of dictionaries, each containing details for a scraped place.
              Returns an empty list if no places are found or an error occurs.
    """
    results = []
    place_links = set()
    scroll_attempts_no_new = 0
    browser = None

    async with async_playwright() as p: # Changed to async
        try:
            # Get proxy configuration from environment variables
            proxy_server = os.getenv("PROXY_SERVER")
            proxy_username = os.getenv("PROXY_USERNAME")
            proxy_password = os.getenv("PROXY_PASSWORD")

            # Build launch options
            launch_options = {
                "headless": headless,
                "args": [
                    '--disable-dev-shm-usage',  # Use /tmp instead of /dev/shm for shared memory
                    '--no-sandbox',  # Required for running in Docker
                    '--disable-setuid-sandbox',
                ]
            }

            # Add proxy if credentials are provided
            if proxy_server and proxy_username and proxy_password:
                launch_options["proxy"] = {
                    "server": proxy_server,
                    "username": proxy_username,
                    "password": proxy_password
                }
                print(f"Using proxy: {proxy_server}")
            else:
                print("No proxy configured - running without proxy")

            browser = await p.chromium.launch(**launch_options) # Added await
            context = await browser.new_context( # Added await
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                java_script_enabled=True,
                accept_downloads=False,
                # Consider setting viewport, locale, timezone if needed
                locale=lang,
            )
            page = await context.new_page() # Added await
            if not page:
                await browser.close() # Close browser before raising
                raise Exception("Failed to create a new browser page (context.new_page() returned None).")
            # Removed problematic: await page.set_default_timeout(DEFAULT_TIMEOUT)
            # Removed associated debug prints

            search_url = create_search_url(query, lang)
            print(f"Navigating to search URL: {search_url}")
            await page.goto(search_url, wait_until='domcontentloaded') # Added await
            await asyncio.sleep(3) # Wait for potential redirects

            # --- Handle potential consent forms ---
            # Check if we're on a consent page (consent.google.com)
            max_consent_attempts = 3
            for attempt in range(max_consent_attempts):
                if "consent.google.com" in page.url:
                    print(f"Detected consent page (attempt {attempt + 1}/{max_consent_attempts})")
                    try:
                        # Wait for page to fully load
                        await asyncio.sleep(2)
                        
                        # Find ALL buttons and try to click any that look like consent buttons
                        button_clicked = False
                        
                        # Method 1: Try to find buttons by common text patterns
                        button_text_patterns = [
                            "Accept all", "accept all", "ACCEPT ALL",
                            "Reject all", "reject all", "REJECT ALL",
                            "Continue", "I agree"
                        ]
                        
                        all_buttons = await page.locator("button").all()
                        print(f"Found {len(all_buttons)} buttons on consent page")
                        
                        for button in all_buttons:
                            try:
                                if not await button.is_visible():
                                    continue
                                    
                                button_text = await button.inner_text()
                                button_text = button_text.strip()
                                
                                # Check if button text contains any of our patterns
                                for pattern in button_text_patterns:
                                    if pattern.lower() in button_text.lower():
                                        print(f"Found consent button with text: '{button_text}' - clicking...")
                                        await button.click()
                                        button_clicked = True
                                        break
                                
                                if button_clicked:
                                    break
                            except Exception as e:
                                continue
                        
                        # Method 2: If no button found by text, try form submission buttons
                        if not button_clicked:
                            print("No button found by text, trying form submit buttons...")
                            try:
                                form_buttons = await page.locator("form[action*='consent'] button").all()
                                if form_buttons:
                                    visible_form_button = None
                                    for fb in form_buttons:
                                        if await fb.is_visible():
                                            visible_form_button = fb
                                            break
                                    
                                    if visible_form_button:
                                        print("Clicking first visible form button...")
                                        await visible_form_button.click()
                                        button_clicked = True
                            except Exception as e:
                                print(f"Error trying form buttons: {e}")
                        
                        if button_clicked:
                            print("Consent button clicked, waiting for navigation...")
                            await asyncio.sleep(3)
                            # Wait for navigation away from consent page
                            try:
                                await page.wait_for_url(lambda url: "consent.google.com" not in url, timeout=10000)
                                print("Successfully navigated away from consent page")
                            except PlaywrightTimeoutError:
                                print("Still on consent page after clicking button, trying again...")
                        else:
                            print("No consent button found - saving page for debugging")
                            try:
                                await page.screenshot(path="consent_debug.png")
                                print("Screenshot saved to consent_debug.png")
                            except:
                                pass
                            break
                    except Exception as e:
                        print(f"Error handling consent form: {e}")
                        import traceback
                        traceback.print_exc()
                        break
                else:
                    # Not on consent page, break the loop
                    break
            
            # Final wait for page to settle
            await asyncio.sleep(3)


            # --- Scrolling and Link Extraction ---
            print("Scrolling to load places...")
            feed_selector = '[role="feed"]'
            try:
                await page.wait_for_selector(feed_selector, state='visible', timeout=40000) # Increased timeout to 40s
            except PlaywrightTimeoutError:
                 # Check if it's a single result page (maps/place/)
                if "/maps/place/" in page.url:
                    print("Detected single place page.")
                    place_links.add(page.url)
                else:
                    print(f"Error: Feed element '{feed_selector}' not found. Maybe no results or page structure changed.")
                    await browser.close() # Added await
                    return [] # No results or page structure changed

            if await page.locator(feed_selector).count() > 0: # Added await
                last_height = await page.evaluate(f'document.querySelector(\'{feed_selector}\').scrollHeight') # Added await
                while True:
                    # Scroll down
                    await page.evaluate(f'document.querySelector(\'{feed_selector}\').scrollTop = document.querySelector(\'{feed_selector}\').scrollHeight') # Added await
                    await asyncio.sleep(SCROLL_PAUSE_TIME) # Changed to asyncio.sleep, added await

                    # Extract links after scroll
                    current_links_list = await page.locator(f'{feed_selector} a[href*="/maps/place/"]').evaluate_all('elements => elements.map(a => a.href)') # Added await
                    current_links = set(current_links_list)
                    new_links_found = len(current_links - place_links) > 0
                    place_links.update(current_links)
                    print(f"Found {len(place_links)} unique place links so far...")

                    if max_places is not None and len(place_links) >= max_places:
                        print(f"Reached max_places limit ({max_places}).")
                        place_links = set(list(place_links)[:max_places]) # Trim excess links
                        break

                    # Check if scroll height has changed
                    new_height = await page.evaluate(f'document.querySelector(\'{feed_selector}\').scrollHeight') # Added await
                    if new_height == last_height:
                        # Check for the "end of results" marker
                        end_marker_xpath = "//span[contains(text(), \"You've reached the end of the list.\")]"
                        if await page.locator(end_marker_xpath).count() > 0: # Added await
                            print("Reached the end of the results list.")
                            break
                        else:
                            # If height didn't change but end marker isn't there, maybe loading issue?
                            # Increment no-new-links counter
                            if not new_links_found:
                                scroll_attempts_no_new += 1
                                print(f"Scroll height unchanged and no new links. Attempt {scroll_attempts_no_new}/{MAX_SCROLL_ATTEMPTS_WITHOUT_NEW_LINKS}")
                                if scroll_attempts_no_new >= MAX_SCROLL_ATTEMPTS_WITHOUT_NEW_LINKS:
                                    print("Stopping scroll due to lack of new links.")
                                    break
                            else:
                                scroll_attempts_no_new = 0 # Reset if new links were found this cycle
                    else:
                        last_height = new_height
                        scroll_attempts_no_new = 0 # Reset if scroll height changed

                    # Optional: Add a hard limit on scrolls to prevent infinite loops
                    # if scroll_count > MAX_SCROLLS: break

            # --- Scraping Individual Places ---
            print(f"\nScraping details for {len(place_links)} places...")
            count = 0
            for link in place_links:
                count += 1
                print(f"Processing link {count}/{len(place_links)}: {link}") # Keep sync print
                try:
                    await page.goto(link, wait_until='domcontentloaded') # Added await
                    # Wait a bit for dynamic content if needed, or wait for a specific element
                    # await page.wait_for_load_state('networkidle', timeout=10000) # Or networkidle if needed

                    html_content = await page.content() # Added await
                    place_data = extractor.extract_place_data(html_content)

                    if place_data:
                        place_data['link'] = link # Add the source link
                        results.append(place_data)
                        # print(json.dumps(place_data, indent=2)) # Optional: print data as it's scraped
                    else:
                        print(f"  - Failed to extract data for: {link}")
                        # Optionally save the HTML for debugging
                        # with open(f"error_page_{count}.html", "w", encoding="utf-8") as f:
                        #     f.write(html_content)

                except PlaywrightTimeoutError:
                    print(f"  - Timeout navigating to or processing: {link}")
                except Exception as e:
                    print(f"  - Error processing {link}: {e}")
                await asyncio.sleep(0.5) # Changed to asyncio.sleep, added await

            await browser.close() # Added await

        except PlaywrightTimeoutError:
            print(f"Timeout error during scraping process.")
        except Exception as e:
            print(f"An error occurred during scraping: {e}")
            import traceback
            traceback.print_exc() # Print detailed traceback for debugging
        finally:
            # Ensure browser is closed if an error occurred mid-process
            if browser and browser.is_connected(): # Check if browser exists and is connected
                await browser.close() # Added await

    print(f"\nScraping finished. Found details for {len(results)} places.")
    return results

# --- Example Usage ---
# (Example usage block removed as this script is now intended to be imported as a module)