#!/usr/bin/env python3
import itertools
import string
import argparse
import sys
import logging
import json
import os
import requests


def load_config():
    """
    Load configuration from config.json and resolve any environment variable placeholders.
    For any string value of the form "${VAR}", substitute it with the value of the environment variable VAR.
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
LOG_FILE = "logs/generate_domains.log"
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

RESERVED_FILE = "reserved_domains.json"


def load_reserved_list():
    """
    Load the set of reserved domain strings from RESERVED_FILE.
    Returns an empty set if the file does not exist or cannot be read.
    """
    if os.path.exists(RESERVED_FILE):
        try:
            with open(RESERVED_FILE, "r") as f:
                data = json.load(f)
                return set(data.get("reserved", []))
        except Exception as e:
            logger.error(f"Error reading reserved file: {e}")
            return set()
    else:
        logger.warning(
            f"Reserved file {RESERVED_FILE} not found. Using empty reserved list."
        )
        return set()


def load_valid_words():
    """
    Load a set of 4-letter English words using NLTK.
    This is used for filtering candidate domains to valid words.
    """
    try:
        import nltk
        from nltk.corpus import words as nltk_words
    except ImportError:
        logger.error("NLTK is not installed. Please install nltk.")
        sys.exit(1)
    try:
        nltk.data.find("corpora/words")
    except LookupError:
        logger.info("Downloading NLTK words corpus...")
        nltk.download("words")
    valid = set(word.lower() for word in nltk_words.words() if len(word) == 4)
    return valid


def get_valid_tlds():
    """
    Fetch the current TLD list from IANA and return only two-letter TLDs.
    """
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


def is_reserved(domain_str, tld_str, reserved_set):
    """
    Check if the candidate combination should be excluded.
    Returns True if either the SLD or TLD is reserved or the full combination is reserved.
    """
    if domain_str == tld_str:
        return True
    if domain_str in reserved_set or tld_str in reserved_set:
        return True
    candidate_word = domain_str + tld_str
    return candidate_word in reserved_set


def generate_domains(
    prefix_domain="",
    prefix_tld="",
    only_words=False,
    valid_words_set=None,
    reserved_set=None,
    emoji_mode=False,
):
    """
    Generate candidate domains.

    - If emoji_mode is True, generate candidate domains using emoji characters.
    - Otherwise, generate domains using 2-letter combinations from the Latin alphabet.

    Optional filters:
      - prefix_domain: SLD must start with these characters.
      - prefix_tld: TLD must start with these characters.
      - only_words: Only yield domains where the concatenation of SLD and TLD is a valid 4-letter word.
      - reserved_set: A set of reserved strings to exclude.
    """
    count = 0
    if emoji_mode:
        emoji_list = ["😀", "😃", "😄", "😁", "😆", "😂", "🤣", "😊", "😍", "😉"]
        for domain_tuple in itertools.product(emoji_list, repeat=2):
            domain_str = "".join(domain_tuple)
            if prefix_domain and not domain_str.startswith(prefix_domain):
                continue
            for tld_tuple in itertools.product(emoji_list, repeat=2):
                tld_str = "".join(tld_tuple)
                if prefix_tld and not tld_str.startswith(prefix_tld):
                    continue
                yield f"{domain_str}.{tld_str}"
                count += 1
                if count % 1000 == 0:
                    logger.info(f"Generated {count} emoji candidate domains so far...")
    else:
        letters = string.ascii_lowercase
        valid_tlds = get_valid_tlds()
        # Apply minimum TLD length from config
        min_tld = config.get("min_tld_length", 2)
        valid_tlds = [t for t in valid_tlds if len(t) >= min_tld]
        for domain_tuple in itertools.product(letters, repeat=2):
            domain_str = "".join(domain_tuple)
            if prefix_domain and not domain_str.startswith(prefix_domain):
                continue
            for tld in valid_tlds:
                if prefix_tld and not tld.startswith(prefix_tld):
                    continue
                if reserved_set and is_reserved(domain_str, tld, reserved_set):
                    continue
                candidate_word = domain_str + tld
                if (
                    only_words
                    and valid_words_set
                    and candidate_word not in valid_words_set
                ):
                    continue
                yield f"{domain_str}.{tld}"
                count += 1
                if count % 1000 == 0:
                    logger.info(f"Generated {count} candidate domains so far...")


def main():
    parser = argparse.ArgumentParser(
        description="Generate candidate domains using two-letter SLDs and valid two-letter TLDs from IANA."
    )
    parser.add_argument(
        "--prefix-domain",
        type=str,
        default="",
        help="Filter domains with SLD starting with these characters.",
    )
    parser.add_argument(
        "--prefix-tld",
        type=str,
        default="",
        help="Filter domains with TLD starting with these characters.",
    )
    parser.add_argument(
        "--outfile",
        type=str,
        default="output/generated_domains.txt",
        help="Output file for generated domains.",
    )
    parser.add_argument(
        "--only-words",
        action="store_true",
        help="Only output domains that form a valid 4-letter English word.",
    )
    parser.add_argument(
        "--emoji",
        action="store_true",
        help="Generate candidate domains using emoji characters.",
    )
    args = parser.parse_args()

    os.makedirs("output", exist_ok=True)
    reserved_set = load_reserved_list() if not args.emoji else None
    valid_words_set = load_valid_words() if args.only_words and not args.emoji else None

    count = 0
    with open(args.outfile, "w", encoding="utf-8") as f:
        for domain in generate_domains(
            args.prefix_domain,
            args.prefix_tld,
            args.only_words,
            valid_words_set,
            reserved_set,
            emoji_mode=args.emoji,
        ):
            f.write(domain + "\n")
            count += 1
    logger.info(f"Generated {count} candidate domains and saved to {args.outfile}")


if __name__ == "__main__":
    main()
