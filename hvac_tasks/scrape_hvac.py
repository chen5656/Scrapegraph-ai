# Run with:
# source .venv/bin/activate
# ./.venv/bin/python3 hvac_tasks/scrape_hvac.py

import os
import sys
import logging
from typing import List, Optional
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

OUTPUT_FILENAME = "hvac_error_codes.md"

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


def save_progress(lines: List[str], output_path: str) -> None:
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines).rstrip() + "\n")


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
    output_file = os.path.join(os.path.dirname(__file__), OUTPUT_FILENAME)
    
    markdown_lines = ["# HVAC Error Codes", ""]
    save_progress(markdown_lines, output_file)

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

            # SmartScraperGraph handles fetching, chunking, and JSON repair automatically.
            result = smart_scraper.run()
            
            # The result will adhere to the BrandErrorCodes schema (or be a dict mimicking it)
            # Depending on the version/LLM, it might be a dict or a Pydantic object.
            error_codes = []
            if isinstance(result, dict):
                error_codes = result.get("error_codes", [])
            elif hasattr(result, "error_codes"):
                error_codes = result.error_codes

            brand_title = brand.replace("-", " ").title()
            markdown_lines.append(f"## {brand_title}")

            if not error_codes:
                markdown_lines.append("- (none)")
            else:
                for item in error_codes:
                    code = item.get("code") if isinstance(item, dict) else item.code
                    desc = item.get("description") if isinstance(item, dict) else item.description
                    if desc:
                        markdown_lines.append(f"- {code}: {desc}")
                    else:
                        markdown_lines.append(f"- {code}")
            
            markdown_lines.append("")
            save_progress(markdown_lines, output_file)

        except Exception as e:
            logging.error(f"Could not scrape {brand}: {e}")
            # Continue to next brand instead of hard exit, to get as much data as possible
            raise

    logging.info(f"\nScraping complete! Data saved to {output_file}")
    return markdown_lines


if __name__ == "__main__":
    scrape_hvac_error_codes_list()
