# Run with:
# source .venv/bin/activate
# ./.venv/bin/python3 scrape_hvac.py

import os
from dotenv import load_dotenv
load_dotenv()

import sys
import json
import logging

# Add current directory to path so we can import scrapegraphai from the source if not installed
sys.path.append(os.getcwd())

try:
    from scrapegraphai.graphs import SmartScraperGraph
except ImportError:
    print("Could not import scrapegraphai. ")
    exit(1)
    

# Setup logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

def scrape_hvac_error_codes():
    base_url = "https://www.212hvac.com/"
    brands = [
        "york", "trane", "rheem", "mitsubishi-electric", 
        "luxaire", "daikin", "goodman", "carrier", 
        "bryant", "american-standard"
    ]
    
    # Configuration for ScrapeGraphAI
    # Using Gemini as requested by the user
    google_key = os.environ.get("GOOGLE_API_KEY")
    
    if google_key:
        logging.info("Using Gemini (google_genai) for scraping.")
        graph_config = {
            "llm": {
                "api_key": google_key,
                "model": "google_genai/gemini-3-flash-preview",
            },
            "verbose": True,
            "headless": True,
        }
    else:
        openai_key = os.environ.get("OPENAI_API_KEY")
        if openai_key:
            logging.info("GOOGLE_API_KEY not found. Using OpenAI for scraping.")
            graph_config = {
                "llm": {
                    "api_key": openai_key,
                    "model": "openai/gpt-4o-mini",
                },
                "verbose": True,
                "headless": True,
            }
        else:
            logging.info("No API keys found. Using Ollama (llama3.2).")
            graph_config = {
                "llm": {
                    "model": "ollama/llama3.2",
                    "model_tokens": 8192,
                    "format": "json",
                },
                "verbose": True,
                "headless": True,
            }

    all_error_codes = {}

    for brand in brands:
        url = f"{base_url}{brand}/"
        logging.info(f"Scraping: {url}")
        
        try:
            # We want to extract a mapping of error/fault codes to their meaning/result.
            # The prompt should be specific about the structure.
            prompt = (
                f"Extract all HVAC error codes and their corresponding results or descriptions from the page. "
                f"Return a JSON object where the key is '{brand}' and the value is a list of objects, "
                f"each having a 'code' and 'result' field. "
                f"Example: {{ '{brand}': [ {{ 'code': 'E1', 'result': 'Compressor High Pressure' }} ] }}"
            )

            smart_scraper_graph = SmartScraperGraph(
                prompt=prompt,
                source=url,
                config=graph_config
            )

            result = smart_scraper_graph.run()
            
            # The result should be a dictionary. We merge it into all_error_codes.
            # Depending on the LLM's adherence to the format, we might need to adjust.
            if result:
                 # If the LLM returns the wrapper key as requested:
                if brand in result:
                    all_error_codes[brand] = result[brand]
                else:
                    # Fallback if it returned just the list or mixed keys
                    all_error_codes[brand] = result

        except Exception as e:
            logging.error(f"Could not scrape {brand}: {e}")
            exit(1)

    # Output the final JSON
    output_file = 'hvac_error_codes.json'
    with open(output_file, 'w') as f:
        json.dump(all_error_codes, f, indent=4)
    
    logging.info(f"\nScraping complete! Data saved to {output_file}")
    return all_error_codes

if __name__ == "__main__":
    scrape_hvac_error_codes()
