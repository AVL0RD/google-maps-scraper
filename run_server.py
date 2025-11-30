import asyncio
import sys
import uvicorn

# Set the Windows event loop policy before anything else
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

if __name__ == "__main__":
    uvicorn.run(
        "gmaps_scraper_server.main_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
