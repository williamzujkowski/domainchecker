#!/usr/bin/env python3
import argparse
import concurrent.futures
import logging
import os
import sys
import json
import time
import whois  # Requires python-whois; supports many TLDs.
import requests
import smtplib
import ssl
from email.mime.text import MIMEText
from threading import Lock

# Load configuration
try:
    with open("config.json") as f:
        config = json.load(f)
except Exception as e:
    sys.exit(f"Error loading config.json: {e}")

THREAD_COUNT = config.get("thread_count", 10)
CHECK_TIMEOUT = config.get("check_timeout", 10)
DOMAINR_API_TYPE = config.get("domainr_api_type", "rapidapi")
DOMAINR_API_KEYS = (
    config.get("domainr_api_keys", "").split(",")
    if config.get("domainr_api_keys")
    else []
)

# Set up logging with fallback to console if file access fails
os.makedirs("logs", exist_ok=True)
LOG_FILE = "logs/check_domains.log"
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

OUTPUT_FILE = "output/available_domains.txt"
STATUS_FILE = "output/domain_status.json"  # stores previous run statuses

# Email/Webhook settings
ENABLE_EMAIL = config.get("enable_email", False)
SMTP_HOST = config.get("smtp_host", "")
SMTP_PORT = int(config.get("smtp_port", 465))
SMTP_USER = config.get("smtp_user", "")
SMTP_PASS = config.get("smtp_pass", "")
EMAIL_TO = config.get("email_to", "")

ENABLE_WEBHOOK = config.get("enable_webhook", False)
WEBHOOK_URL = config.get("webhook_url", "")

api_key_lock = Lock()
DOMAINR_API_KEY_INDEX = 0


def load_domain_list(input_file):
    """Load a list of domains from a file."""
    if not os.path.exists(input_file):
        logger.error(f"Domain list file {input_file} not found.")
        sys.exit(1)
    with open(input_file, "r", encoding="utf-8") as f:
        domains = [line.strip() for line in f if line.strip()]
    return domains


def load_previous_status():
    """Load previous domain status from file."""
    if os.path.exists(STATUS_FILE):
        try:
            with open(STATUS_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading status file: {e}")
    return {}


def save_status(status):
    os.makedirs("output", exist_ok=True)
    with open(STATUS_FILE, "w") as f:
        json.dump(status, f, indent=2)


def rotate_domainr_key():
    """Rotate to the next Domainr API key."""
    global DOMAINR_API_KEY_INDEX
    with api_key_lock:
        if not DOMAINR_API_KEYS:
            return None
        key = DOMAINR_API_KEYS[DOMAINR_API_KEY_INDEX]
        DOMAINR_API_KEY_INDEX = (DOMAINR_API_KEY_INDEX + 1) % len(DOMAINR_API_KEYS)
        return key


def whois_lookup(domain_punycode):
    """Perform a WHOIS lookup for the domain. Returns True if available."""
    try:
        result = whois.whois(domain_punycode)
        if not result or result.get("domain_name") is None:
            return True
        return False
    except Exception as e:
        logger.warning(f"WHOIS lookup exception for {domain_punycode}: {e}")
        return True


def domainr_lookup(domain_punycode):
    """Perform a lookup using the Domainr API. Returns True if available."""
    api_key = rotate_domainr_key()
    if not api_key:
        logger.error("No Domainr API key provided.")
        return False
    url = "https://api.domainr.com/v2/status"
    params = {"domain": domain_punycode}
    headers = {}
    if DOMAINR_API_TYPE == "rapidapi":
        headers["X-RapidAPI-Key"] = api_key
        headers["X-RapidAPI-Host"] = "domainr.p.rapidapi.com"
    else:
        params["client_id"] = api_key

    try:
        response = requests.get(
            url, params=params, headers=headers, timeout=CHECK_TIMEOUT
        )
        if response.status_code == 429:
            logger.warning(
                f"Rate limit hit for {domain_punycode}. Retrying after delay..."
            )
            time.sleep(5)
            return domainr_lookup(domain_punycode)
        data = response.json()
        for status in data.get("status", []):
            if status.get("status") in ("undelegated", "inactive"):
                return True
        return False
    except Exception as e:
        logger.error(f"Domainr lookup error for {domain_punycode}: {e}")
        return False


def check_domain(domain):
    """
    Check a domain's availability.
    Returns tuple (domain, available:bool).
    """
    logger.info(f"Checking {domain}...")
    try:
        domain_punycode = domain.encode("idna").decode("ascii")
    except Exception as e:
        logger.error(f"Error converting {domain} to punycode: {e}")
        domain_punycode = domain

    available = whois_lookup(domain_punycode)
    if available:
        logger.info(f"WHOIS indicates {domain} is available.")
    else:
        logger.info(f"WHOIS indicates {domain} is taken.")

    # Fallback to Domainr API if needed
    if not available and DOMAINR_API_KEYS:
        available = domainr_lookup(domain_punycode)
    return domain, available


def send_email_notification(new_domains, summary):
    """Send an email notification with available domains."""
    try:
        body = "New available domains:\n" + "\n".join(new_domains) + "\n\n" + summary
        msg = MIMEText(body)
        msg["Subject"] = "Domain Availability Alert"
        msg["From"] = SMTP_USER
        msg["To"] = EMAIL_TO
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, [EMAIL_TO], msg.as_string())
        logger.info("Email notification sent.")
    except Exception as e:
        logger.error(f"Error sending email: {e}")


def send_webhook_notification(new_domains, summary):
    """Send a webhook notification."""
    try:
        payload = {
            "event": "domain_available",
            "domains": new_domains,
            "summary": summary,
        }
        response = requests.post(WEBHOOK_URL, json=payload, timeout=CHECK_TIMEOUT)
        if response.status_code == 200:
            logger.info("Webhook notification sent.")
        else:
            logger.warning(f"Webhook responded with status {response.status_code}.")
    except Exception as e:
        logger.error(f"Error sending webhook: {e}")


def score_domain(domain):
    """
    Compute a heuristic score for the domain.
    Returns an integer score (0-100).
    """
    score = 0
    try:
        name, tld = domain.split(".")
    except Exception:
        return 0
    if len(name) <= 3:
        score += 40
    elif len(name) <= 5:
        score += 30
    else:
        score += 10
    if tld == "com":
        score += 30
    elif tld in {"net", "org"}:
        score += 20
    else:
        score += 10
    if "-" in name or any(char.isdigit() for char in name):
        score -= 20
    return max(0, min(score, 100))


def check_domains(domains):
    """
    Check availability for a list of domains.
    Returns a dict with keys 'available', 'unavailable', 'errors', and 'summary'.
    """
    previous_status = load_previous_status()
    current_status = {}
    available_domains = []
    new_available = []
    unavailable_domains = []
    errors = []

    start_time = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=THREAD_COUNT) as executor:
        future_to_domain = {executor.submit(check_domain, d): d for d in domains}
        for future in concurrent.futures.as_completed(future_to_domain):
            try:
                domain, available = future.result()
            except Exception as e:
                logger.error(f"Error checking domain: {e}")
                errors.append(future_to_domain[future])
                continue
            current_status[domain] = available
            if available:
                available_domains.append(domain)
                if not previous_status.get(domain, False):
                    new_available.append(domain)
            else:
                unavailable_domains.append(domain)
    duration = time.time() - start_time
    summary = (
        f"Checked {len(domains)} domains in {duration:.1f} seconds. "
        f"{len(available_domains)} available, {len(new_available)} newly available."
    )
    logger.info(summary)

    os.makedirs("output", exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for d in available_domains:
            f.write(f"{d} (Score: {score_domain(d)})\n")

    save_status(current_status)

    if new_available:
        if ENABLE_EMAIL:
            send_email_notification(new_available, summary)
        if ENABLE_WEBHOOK and WEBHOOK_URL:
            send_webhook_notification(new_available, summary)

    return {
        "available": available_domains,
        "unavailable": unavailable_domains,
        "errors": errors,
        "summary": summary,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Check domain availability using WHOIS and Domainr API with multi-threading."
    )
    parser.add_argument(
        "--domains-file",
        type=str,
        default="output/generated_domains.txt",
        help="File with list of domains to check.",
    )
    args = parser.parse_args()

    domains = load_domain_list(args.domains_file)
    results = check_domains(domains)
    print(results["summary"])


if __name__ == "__main__":
    main()
