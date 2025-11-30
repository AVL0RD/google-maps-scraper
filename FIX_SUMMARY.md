# Google Maps Scraper - Bug Fix Summary

## Problem
The Google Maps scraper was experiencing infinite loading and returning blank/empty results when accessed through the API endpoint.

## Root Cause
The scraper was getting stuck on Google's consent page (`consent.google.com`). When using the IPRoyal proxy, Google would redirect to a consent page before showing the Maps results. The original consent handling code:
1. Checked for consent buttons BEFORE the redirect happened
2. Used limited selectors that didn't match the actual consent page buttons
3. Had no mechanism to detect when stuck on `consent.google.com`

This caused the scraper to:
- Wait indefinitely for the feed element `[role="feed"]` that never appeared
- Timeout after 40 seconds without finding any results
- Return empty arrays or hang indefinitely

## Solution Implemented
Enhanced the consent form handling in `gmaps_scraper_server/scraper.py`:

### 1. URL-Based Detection
Added explicit check for `consent.google.com` in the page URL after navigation:
```python
if "consent.google.com" in page.url:
    # Handle consent page
```

### 2. Multiple Retry Attempts
Implemented a retry loop (up to 3 attempts) to handle consent pages that may require multiple interactions.

### 3. Comprehensive Button Detection
Instead of waiting for specific selectors, the code now:
- Finds ALL buttons on the page using `page.locator("button").all()`
- Checks each button's text content against multiple patterns:
  - "Accept all", "Reject all", "Continue", "I agree" (case-insensitive)
- Clicks the first matching visible button

### 4. Fallback Strategy
If no buttons are found by text matching, tries to find form submission buttons:
```python
form_buttons = await page.locator("form[action*='consent'] button").all()
```

### 5. Debug Capabilities
Added screenshot capture when consent buttons aren't found, saving to `consent_debug.png` for troubleshooting.

### 6. Proper Navigation Waiting
After clicking consent button, waits for navigation away from `consent.google.com`:
```python
await page.wait_for_url(lambda url: "consent.google.com" not in url, timeout=10000)
```

## Test Results
After the fix:
- ✅ Coffee shops in Seattle: 2 results in 22.45 seconds
- ✅ Restaurants in New York: 3 results in 30.05 seconds
- ✅ API endpoint working correctly
- ✅ Handles both consent page and no-consent-page scenarios

## Code Changes
**File**: `gmaps_scraper_server/scraper.py`
**Lines**: 79-165 (consent handling section)

## How to Test
1. Start the server:
   ```bash
   cd google-maps-scraper
   uvicorn gmaps_scraper_server.main_api:app --reload
   ```

2. Test via API:
   ```python
   import requests
   response = requests.get(
       "http://127.0.0.1:8000/scrape-get",
       params={"query": "coffee shops in Seattle", "max_places": 2}
   )
   print(response.json())
   ```

3. Or via browser:
   ```
   http://127.0.0.1:8000/scrape-get?query=coffee+shops+in+Seattle&max_places=2
   ```

## Notes
- The consent page appears intermittently based on proxy IP location and Google's detection
- The fix handles both scenarios (with and without consent page)
- Screenshots are saved to help debug if new consent page variants appear
- Total wait time after navigation is ~8 seconds (3s + 2s + 3s) to allow for redirects and page loading

## Environment Variables Update (2025-11-30)

The proxy configuration has been updated to use environment variables instead of hardcoded credentials for better security and Railway deployment compatibility.

### Changes Made:
1. Added `import os` to read environment variables
2. Replaced hardcoded proxy dictionary with environment variable reading:
   - `PROXY_SERVER` - Proxy server URL
   - `PROXY_USERNAME` - Proxy username
   - `PROXY_PASSWORD` - Proxy password
3. Made proxy configuration optional (falls back to no-proxy if variables not set)

### Railway Deployment:
See [RAILWAY_DEPLOYMENT.md](./RAILWAY_DEPLOYMENT.md) for detailed instructions on setting up environment variables in Railway.

**Quick Setup:**
In Railway, add these 3 variables:
- `PROXY_SERVER` = `http://geo.iproyal.com:12321`
- `PROXY_USERNAME` = `HI6aN8eockzYSiC8`
- `PROXY_PASSWORD` = `X0SmzS2xVYBPb9MI`

---

## Created: 2025-11-30
