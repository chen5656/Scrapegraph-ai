@echo off
echo Installing ScrapeGraphAI dependencies...
pip install -e .
if %ERRORLEVEL% NEQ 0 (
    echo Failed to install package.
    pause
    exit /b %ERRORLEVEL%
)

echo Installing Playwright browsers...
playwright install
if %ERRORLEVEL% NEQ 0 (
    echo Failed to install Playwright browsers.
    pause
    exit /b %ERRORLEVEL%
)

echo Running HVAC Scraper...
python scrape_hvac.py
if %ERRORLEVEL% NEQ 0 (
    echo Scraper script failed.
    pause
    exit /b %ERRORLEVEL%
)

echo Done! Output saved to hvac_error_codes.json
pause
