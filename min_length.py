#!/usr/bin/env python3
import json
import logging
import sys
import os


def load_config():
    """
    Load configuration from config.json and resolve any environment variable placeholders.
    Any string in the form "${VAR}" will be replaced with the value of the environment variable VAR.
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


# Load configuration using the new loader
config = load_config()

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Mapping of TLD to its allowed minimum SLD length (can be extended)
tld_minimums = {"in": 3, "ck": 3, "us": 3, "et": 2, "re": 3}
default_min = 3
config_min_length = config.get("min_sld_length", 4)

# Sample list of domains for testing (replace with actual list)
domains = [
    "ad.in",
    "abc.in",
    "home.us",
    "ba.ck",
    "tech.re",
    "fa.ke",
    "su.ck",
    "admin.us",
    "cu.re",
    "code.et",
]


def filter_domains(domains, config_min_length, tld_minimums, default_min=3):
    """
    Filter domains based on the configured minimum SLD length and each TLD's allowed minimum.
    """
    filtered = []
    for domain in domains:
        parts = domain.split(".")
        if len(parts) != 2:
            continue
        sld, tld = parts
        allowed_min = tld_minimums.get(tld, default_min)
        if config_min_length < allowed_min:
            continue
        if len(sld) >= config_min_length:
            filtered.append(domain)
    return filtered


filtered_domains = filter_domains(domains, config_min_length, tld_minimums, default_min)
logger.info(f"Filtered domains: {filtered_domains}")
print("Filtered domains:", filtered_domains)
