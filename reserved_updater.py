#!/usr/bin/env python3
import json
import logging
from datetime import datetime, timezone

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

RESERVED_FILE = "reserved_domains.json"


def update_iana_reserved():
    """
    Fetch reserved TLDs/domains from IANA.
    For demo purposes, returns a fixed list.
    """
    return ["example", "invalid", "localhost", "test"]


def update_icann_reserved():
    """
    Fetch ICANN reserved names.
    For demo purposes, returns a fixed list.
    """
    return ["nic", "domain", "register", "registration"]


def merge_reserved_lists():
    reserved = set()
    for name in update_iana_reserved():
        reserved.add(name.lower())
    for name in update_icann_reserved():
        reserved.add(name.lower())
    additional = {"admin", "support", "www", "mail", "ftp", "api", "demo", "test"}
    return list(reserved.union(additional))


def save_reserved_list(reserved_list):
    data = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "reserved": reserved_list,
    }
    with open(RESERVED_FILE, "w") as f:
        json.dump(data, f, indent=2)
    logger.info(f"Saved {len(reserved_list)} reserved names to {RESERVED_FILE}")


if __name__ == "__main__":
    logger.info("Updating reserved domains list...")
    reserved_list = merge_reserved_lists()
    save_reserved_list(reserved_list)
    logger.info("Reserved domains update complete.")
