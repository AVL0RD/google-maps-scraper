from fastapi import FastAPI, HTTPException, Query
from typing import Optional, List, Dict, Any
import logging
import asyncio
import sys
from concurrent.futures import ThreadPoolExecutor

# Import the scraper function (adjust path if necessary)
try:
    from gmaps_scraper_server.scraper import scrape_google_maps
except ImportError:
    # Handle case where scraper might be in a different structure later
    logging.error("Could not import scrape_google_maps from scraper.py")
    # Define a dummy function to allow API to start, but fail on call
    def scrape_google_maps(*args, **kwargs):
        raise ImportError("Scraper function not available.")

# Thread pool for running Playwright (Windows compatibility fix)
executor = ThreadPoolExecutor(max_workers=4)

def run_scraper_in_thread(query, max_places, lang, headless):
    """Run the async scraper in a new event loop in a thread"""
    import asyncio
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(scrape_google_maps(query, max_places, lang, headless))
    finally:
        loop.close()

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = FastAPI(
    title="Google Maps Scraper API",
    description="API to trigger Google Maps scraping based on a query.",
    version="0.1.0",
)

@app.post("/scrape", response_model=List[Dict[str, Any]])
async def run_scrape(
    query: str = Query(..., description="The search query for Google Maps (e.g., 'restaurants in New York')"),
    max_places: Optional[int] = Query(None, description="Maximum number of places to scrape. Scrapes all found if None."),
    lang: str = Query("en", description="Language code for Google Maps results (e.g., 'en', 'es')."),
    headless: bool = Query(True, description="Run the browser in headless mode (no UI). Set to false for debugging locally.")
):
    """
    Triggers the Google Maps scraping process for the given query.
    """
    logging.info(f"Received scrape request for query: '{query}', max_places: {max_places}, lang: {lang}, headless: {headless}")
    try:
        # Run the scraper in a thread pool to avoid Windows event loop issues
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            executor,
            run_scraper_in_thread,
            query,
            max_places,
            lang,
            headless
        )
        logging.info(f"Scraping finished for query: '{query}'. Found {len(results)} results.")
        return results
    except asyncio.TimeoutError:
        logging.error(f"Scraping timeout for query '{query}' after 300 seconds")
        raise HTTPException(status_code=504, detail="Scraping request timed out after 5 minutes")
    except ImportError as e:
         logging.error(f"ImportError during scraping for query '{query}': {e}")
         raise HTTPException(status_code=500, detail="Server configuration error: Scraper not available.")
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logging.error(f"An error occurred during scraping for query '{query}': {e}\n{error_trace}", exc_info=True)
        # Consider more specific error handling based on scraper exceptions
        raise HTTPException(status_code=500, detail=f"An internal error occurred during scraping: {str(e)}\n\nFull trace:\n{error_trace}")

@app.get("/scrape-get", response_model=List[Dict[str, Any]])
async def run_scrape_get(
    query: str = Query(..., description="The search query for Google Maps (e.g., 'restaurants in New York')"),
    max_places: Optional[int] = Query(None, description="Maximum number of places to scrape. Scrapes all found if None."),
    lang: str = Query("en", description="Language code for Google Maps results (e.g., 'en', 'es')."),
    headless: bool = Query(True, description="Run the browser in headless mode (no UI). Set to false for debugging locally.")
):
    """
    Triggers the Google Maps scraping process for the given query via GET request.
    """
    logging.info(f"Received GET scrape request for query: '{query}', max_places: {max_places}, lang: {lang}, headless: {headless}")
    try:
        # Run the scraper in a thread pool to avoid Windows event loop issues
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            executor,
            run_scraper_in_thread,
            query,
            max_places,
            lang,
            headless
        )
        logging.info(f"Scraping finished for query: '{query}'. Found {len(results)} results.")
        return results
    except asyncio.TimeoutError:
        logging.error(f"Scraping timeout for query '{query}' after 300 seconds")
        raise HTTPException(status_code=504, detail="Scraping request timed out after 5 minutes")
    except ImportError as e:
         logging.error(f"ImportError during scraping for query '{query}': {e}")
         raise HTTPException(status_code=500, detail="Server configuration error: Scraper not available.")
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logging.error(f"An error occurred during scraping for query '{query}': {e}\n{error_trace}", exc_info=True)
        # Consider more specific error handling based on scraper exceptions
        raise HTTPException(status_code=500, detail=f"An internal error occurred during scraping: {str(e)}\n\nFull trace:\n{error_trace}")


# Basic root endpoint for health check or info
@app.get("/")
async def read_root():
    return {"message": "Google Maps Scraper API is running."}

# Example for running locally (uvicorn main_api:app --reload)
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8001)