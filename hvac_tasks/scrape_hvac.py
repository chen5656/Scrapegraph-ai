# Run with:
# source .venv/bin/activate
# ./.venv/bin/python3 hvac_tasks/scrape_hvac.py

import os
import sys
import logging
from typing import List

from dotenv import load_dotenv

load_dotenv()

# Add current directory to path so we can import scrapegraphai from the source if not installed
sys.path.append(os.getcwd())

try:
    from scrapegraphai.docloaders import ChromiumLoader
    from scrapegraphai.utils.convert_to_md import convert_to_md
    from scrapegraphai.utils.split_text_into_chunks import split_text_into_chunks
except ImportError:
    print("Could not import scrapegraphai.")
    exit(1)


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

MARKDOWN_PROMPT = (
    "You are extracting HVAC error codes from the page content.\n"
    "Return Markdown only. Do not output JSON. Do not add headings or code fences.\n"
    "Output only bullet lines in this exact format:\n"
    "- CODE: description\n"
    "If a code has no description, use '- CODE'.\n"
    "If no codes are present, output a single line: - (none)\n"
    "Only include codes that appear in the content.\n\n"
    "CONTENT:\n{content}\n"
)

CHUNK_SIZE_TOKENS = 6000
OUTPUT_FILENAME = "hvac_error_codes.md"


def build_llm():
    google_key = os.environ.get("GOOGLE_API_KEY")
    if google_key:
        logging.info("Using Gemini for markdown output.")
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model="gemini-3-flash-preview",
            google_api_key=google_key,
            temperature=0,
            response_mime_type="text/plain",
        )

    openai_key = os.environ.get("OPENAI_API_KEY")
    if openai_key:
        logging.info("GOOGLE_API_KEY not found. Using OpenAI for markdown output.")
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            api_key=openai_key,
            model="gpt-4o-mini",
            temperature=0,
        )

    logging.info("No API keys found. Using Ollama (llama3.2).")
    from langchain_community.chat_models import ChatOllama

    return ChatOllama(model="llama3.2", temperature=0)


def save_progress(lines: List[str], output_path: str) -> None:
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines).rstrip() + "\n")


def fetch_markdown(url: str, headless: bool = True, timeout: int = 60) -> str:
    loader = ChromiumLoader([url], headless=headless, timeout=timeout)
    document = loader.load()
    if not document or not document[0].page_content.strip():
        raise ValueError("No HTML body content found in the response.")
    html = document[0].page_content
    return convert_to_md(html, url)


def extract_markdown_lines(llm, content: str) -> List[str]:
    prompt = MARKDOWN_PROMPT.format(content=content)
    response = llm.invoke(prompt)
    raw_text = getattr(response, "content", str(response))
    lines = []
    for line in raw_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(("-", "*")):
            item = stripped[1:].strip()
            if item and item.lower() != "(none)":
                lines.append(item)
    return lines


def merge_error_lines(items: List[str]) -> List[str]:
    seen = set()
    merged = []
    for item in items:
        code = item.split(":", 1)[0].strip()
        if not code:
            continue
        code_key = code.lower()
        if code_key in seen:
            continue
        seen.add(code_key)
        merged.append(f"- {item}")
    if not merged:
        merged.append("- (none)")
    return merged


def scrape_hvac_error_codes():
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

    llm_instance = build_llm()
    output_file = os.path.join(os.path.dirname(__file__), OUTPUT_FILENAME)
    markdown_lines = ["# HVAC Error Codes", ""]
    save_progress(markdown_lines, output_file)

    for brand in brands:
        url = f"{base_url}{brand}/"
        logging.info(f"Scraping: {url}")

        try:
            page_markdown = fetch_markdown(url)
            chunks = split_text_into_chunks(
                page_markdown, chunk_size=CHUNK_SIZE_TOKENS
            )

            extracted_items: List[str] = []
            for chunk in chunks:
                extracted_items.extend(extract_markdown_lines(llm_instance, chunk))

            merged_lines = merge_error_lines(extracted_items)
            brand_title = brand.replace("-", " ").title()

            markdown_lines.append(f"## {brand_title}")
            markdown_lines.extend(merged_lines)
            markdown_lines.append("")
            save_progress(markdown_lines, output_file)
        except Exception as e:
            logging.error(f"Could not scrape {brand}: {e}")
            exit(1)

    logging.info(f"\nScraping complete! Data saved to {output_file}")
    return markdown_lines


if __name__ == "__main__":
    scrape_hvac_error_codes()
