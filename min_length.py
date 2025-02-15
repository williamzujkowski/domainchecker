import json
import logging

# Load configuration
try:
    with open("config.json") as f:
        config = json.load(f)
except Exception as e:
    raise RuntimeError(f"Error loading config.json: {e}")

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Mapping of TLD to its allowed minimum SLD length (can be extended)
tld_minimums = {
    "in": 3,
    "ck": 3,
    "us": 3,
    "et": 2,
    "re": 3
}
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
    "code.et"
]

def filter_domains(domains, config_min_length, tld_minimums, default_min=3):
    """
    Filter domains based on configured minimum SLD length and TLD allowed minimum.
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
