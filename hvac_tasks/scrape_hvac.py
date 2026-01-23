# Run with:
# source .venv/bin/activate
# ./.venv/bin/python3 hvac_tasks/scrape_hvac.py

import os
import sys
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Add current directory to path so we can import scrapegraphai from the source if not installed
sys.path.append(os.getcwd())

try:
    from scrapegraphai.graphs import SmartScraperGraph
except ImportError:
    print("Could not import scrapegraphai.")
    exit(1)


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

# Directory for results
OUTPUT_DIR = "output"

# Define the schema for the output
class ErrorCode(BaseModel):
    code: str = Field(description="The error code label (e.g., E1, 24)")
    description: Optional[str] = Field(description="The explanation of what the error code means")

class BrandErrorCodes(BaseModel):
    error_codes: List[ErrorCode] = Field(description="A list of error codes and their descriptions")


def get_graph_config():
    google_key = os.environ.get("GOOGLE_API_KEY")
    if google_key:
        logging.info("Using Gemini for scraping.")
        return {
            "llm": {
                "api_key": google_key,
                "model": "gemini-2.5-flash",
            },
            "verbose": False,
            "headless": True,
        }

    openai_key = os.environ.get("OPENAI_API_KEY")
    if openai_key:
        logging.info("GOOGLE_API_KEY not found. Using OpenAI for scraping.")
        return {
            "llm": {
                "api_key": openai_key,
                "model": "openai/gpt-4o-mini",
            },
            "verbose": False,
            "headless": True,
        }

    logging.info("No API keys found. Defaulting to Ollama (llama3.2).")
    return {
        "llm": {
            "model": "ollama/llama3.2",
            "temperature": 0,
            "format": "json",
        },
        "verbose": False,
        "headless": True,
    }


def save_brand_json(brand_data: Dict[str, Any], output_path: str) -> None:
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(brand_data, f, indent=4, ensure_ascii=False)


def scrape_hvac_error_codes_list():
    base_url = "https://www.212hvac.com/"
    brands = [
        "york",
        "trane",
        "rheem",
        "mitsubishi-electric",
        "luxaire",
        "daikin",
        "goodman",
        "carrier",
        "bryant",
        "american-standard",
    ]

    graph_config = get_graph_config()
    
    # Create output directory
    output_dir = Path(__file__).parent / OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    for brand in brands:
        url = f"{base_url}{brand}/"
        logging.info(f"Scraping {brand}: {url}")

        prompt = (
            f"Extract all HVAC error codes and their descriptions for the brand {brand} from this page. "
            "If no error codes are found, return an empty list."
        )

        try:
            smart_scraper = SmartScraperGraph(
                prompt=prompt,
                source=url,
                config=graph_config,
                schema=BrandErrorCodes
            )

            result = smart_scraper.run()
            
            error_codes = []
            if isinstance(result, dict):
                error_codes = result.get("error_codes", [])
            elif hasattr(result, "error_codes"):
                error_codes = result.error_codes

            # Normalize error codes to a list of dicts
            normalized_codes = []
            for item in error_codes:
                if isinstance(item, dict):
                    normalized_codes.append(item)
                else:
                    normalized_codes.append({
                        "code": item.code,
                        "description": item.description
                    })

            brand_data = {
                "brand": brand,
                "error_codes": normalized_codes,
                "last_updated": datetime.now().isoformat()
            }

            output_file = output_dir / f"{brand}.json"
            save_brand_json(brand_data, str(output_file))
            logging.info(f"Saved {brand} to {output_file}")

        except Exception as e:
            logging.error(f"Could not scrape {brand}: {e}")
            # Continue to next brand instead of hard exit
            continue

    logging.info(f"\nScraping complete! Data saved in {output_dir}")


if __name__ == "__main__":
    scrape_hvac_error_codes_list()
