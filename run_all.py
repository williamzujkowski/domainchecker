#!/usr/bin/env python3
import json
import logging
import os
import time
import sys
import requests

from generate_domains import generate_domains
from check_domains import check_domains


def load_config():
    """
    Load configuration from config.json and resolve any environment variable placeholders.
    """
    try:
        with open("config.json") as f:
            config = json.load(f)
    except Exception as e:
        sys.exit(f"Error loading config.json: {e}")

    def resolve(item):
        if isinstance(item, dict):
            return {k: resolve(v) for k, v in item.items()}
        elif isinstance(item, list):
            return [resolve(x) for x in item]
        elif isinstance(item, str):
            if item.startswith("${") and item.endswith("}"):
                env_var = item[2:-1]
                return os.environ.get(env_var, item)
            return item
        else:
            return item

    return resolve(config)


# Load configuration (with env var resolution)
config = load_config()

# Set up logging with fallback to console if file access fails
os.makedirs("logs", exist_ok=True)
LOG_FILE = "logs/run_all.log"
handlers = [logging.StreamHandler(sys.stdout)]
try:
    handlers.append(logging.FileHandler(LOG_FILE))
except PermissionError as e:
    print(f"Warning: Unable to open log file {LOG_FILE}: {e}")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=handlers,
)
logger = logging.getLogger(__name__)


def fetch_tld_list():
    url = "https://data.iana.org/TLD/tlds-alpha-by-domain.txt"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        lines = r.text.splitlines()
        tlds = [
            line.strip().lower()
            for line in lines
            if line and not line.startswith("#") and len(line.strip()) == 2
        ]
        logger.info(f"Fetched {len(tlds)} two-letter TLDs from IANA.")
        return tlds
    except Exception as e:
        logger.error(f"Error fetching TLD list: {e}")
        return ["us", "uk", "ca", "de", "fr"]


def cache_fresh(file_path, max_age_days):
    if os.path.exists(file_path):
        age = time.time() - os.path.getmtime(file_path)
        return (age / 86400) < max_age_days
    return False


def main():
    max_cache_age_days = config.get("max_cache_age_days", 7)
    min_tld = config.get("min_tld_length", 2)
    min_sld = config.get("min_sld_length", 2)

    # 1. TLD Cache: Check if tld_list.json is fresh
    tld_cache_file = "tld_list.json"
    if cache_fresh(tld_cache_file, max_cache_age_days):
        logger.info("Using cached TLD list.")
        try:
            with open(tld_cache_file) as f:
                tlds = json.load(f)
        except Exception as e:
            logger.error(f"Error reading TLD cache: {e}")
            tlds = fetch_tld_list()
            with open(tld_cache_file, "w") as f:
                json.dump(tlds, f)
    else:
        logger.info("TLD cache is stale or missing; fetching new TLD list.")
        tlds = fetch_tld_list()
        with open(tld_cache_file, "w") as f:
            json.dump(tlds, f)

    # 2. Generate domain candidates.
    domains_file = "output/generated_domains.txt"
    os.makedirs("output", exist_ok=True)
    count = 0
    with open(domains_file, "w", encoding="utf-8") as f:
        for domain in generate_domains(
            prefix_domain="",
            prefix_tld="",
            only_words=False,
            valid_words_set=None,
            reserved_set=None,
            emoji_mode=False,
        ):
            parts = domain.split(".")
            if len(parts) != 2:
                continue
            sld, tld = parts
            if len(sld) < min_sld or len(tld) < min_tld:
                continue
            f.write(domain + "\n")
            count += 1
    logger.info(f"Generated {count} candidate domains and saved to {domains_file}")

    # 3. Check domain availability.
    try:
        with open(domains_file, "r", encoding="utf-8") as f:
            domains_list = [line.strip() for line in f if line.strip()]
    except Exception as e:
        logger.error(f"Error reading generated domains file: {e}")
        sys.exit(1)
    results = check_domains(domains_list)
    logger.info("Domain availability check completed.")

    # 4. Save overall results.
    results_file = "domain_results.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    logger.info(f"Results saved to {results_file}")
    print(results["summary"])


if __name__ == "__main__":
    main()
