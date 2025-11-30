# Railway Deployment Guide

## Environment Variables Configuration

To deploy this Google Maps scraper on Railway, you need to configure proxy credentials using environment variables.

### Required Environment Variables

In your Railway project dashboard, add these 3 environment variables:

| Variable Name | Value | Description |
|--------------|-------|-------------|
| `PROXY_SERVER` | `http://geo.iproyal.com:12321` | Proxy server URL |
| `PROXY_USERNAME` | `HI6aN8eockzYSiC8` | Proxy username |
| `PROXY_PASSWORD` | `X0SmzS2xVYBPb9MI` | Proxy password |

### Steps to Configure in Railway

1. Go to your Railway project dashboard
2. Select your service/deployment
3. Click on the **"Variables"** tab
4. Click **"New Variable"** button
5. Add each variable:
   - Name: `PROXY_SERVER`
   - Value: `http://geo.iproyal.com:12321`
   - Click "Add"
6. Repeat for `PROXY_USERNAME` and `PROXY_PASSWORD`
7. Railway will automatically redeploy with the new variables

### How It Works

The `scraper.py` file now reads these environment variables:

```python
proxy_server = os.getenv("PROXY_SERVER")
proxy_username = os.getenv("PROXY_USERNAME")
proxy_password = os.getenv("PROXY_PASSWORD")
```

- **If all 3 variables are set**: Uses the proxy configuration
- **If any variable is missing**: Runs without proxy (useful for local testing)

### Testing Locally

#### Option 1: Set Environment Variables in Shell

**Windows (PowerShell):**
```powershell
$env:PROXY_SERVER="http://geo.iproyal.com:12321"
$env:PROXY_USERNAME="HI6aN8eockzYSiC8"
$env:PROXY_PASSWORD="X0SmzS2xVYBPb9MI"
python run_server.py
```

**Linux/Mac (Bash):**
```bash
export PROXY_SERVER="http://geo.iproyal.com:12321"
export PROXY_USERNAME="HI6aN8eockzYSiC8"
export PROXY_PASSWORD="X0SmzS2xVYBPb9MI"
python run_server.py
```

#### Option 2: Use .env File (Optional)

1. Install `python-dotenv`:
   ```bash
   pip install python-dotenv
   ```

2. Create a `.env` file in the project root:
   ```
   PROXY_SERVER=http://geo.iproyal.com:12321
   PROXY_USERNAME=HI6aN8eockzYSiC8
   PROXY_PASSWORD=X0SmzS2xVYBPb9MI
   ```

3. **IMPORTANT**: Add `.env` to your `.gitignore`:
   ```
   .env
   ```

4. Load it in your code (if needed for local dev)

#### Option 3: Run Without Proxy (Local Testing)

Simply run without setting environment variables:
```bash
python run_server.py
```

The scraper will work but may face rate limiting from Google without a proxy.

### Logs to Verify Configuration

When the scraper runs, check the logs:

- **With proxy**: `Using proxy: http://geo.iproyal.com:12321`
- **Without proxy**: `No proxy configured - running without proxy`

### Security Best Practices

✅ **DO:**
- Store credentials in Railway environment variables
- Add `.env` to `.gitignore` if using locally
- Use Railway's variable management UI

❌ **DON'T:**
- Commit proxy credentials to Git
- Share credentials in public repositories
- Hardcode credentials in the code

### Changing Proxy Credentials

To update proxy credentials:
1. Go to Railway Variables tab
2. Click on the variable you want to change
3. Update the value
4. Save (Railway will auto-redeploy)

No code changes required!

## Additional Railway Configuration

### Playwright Installation

Make sure your `Dockerfile` or Railway buildpack includes Playwright browser installation:

```dockerfile
RUN playwright install chromium
RUN playwright install-deps
```

This is already included in the project's Docker configuration.

---

**Need help?** Check the [FIX_SUMMARY.md](./FIX_SUMMARY.md) for troubleshooting tips.
