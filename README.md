
### File: `README.md`

# 🚀 Domain Checker Project

Welcome to the official repository for the **Domain Checker Project**! This tool automatically generates candidate domains and checks their availability using configurable domain rules and caching to avoid redundant work. The project features domain generation, availability checking (via WHOIS and Domainr API fallback), and an automated workflow orchestrator.

---

## Overview

The project consists of several components:

- **Domain Generation:** Generates candidate domains based on 2‑letter SLDs and TLDs.
- **Domain Availability Check:** Uses WHOIS (with a fallback to Domainr API) to check whether domains are available.
- **Workflow Orchestration:** An orchestrator script (`run_all.py`) ties everything together, managing caching, generation, and checking.
- **Reserved Domains Updater:** Updates a list of reserved domains that should be excluded.
- **Minimum Length Filter (Test):** Filters a sample list of domains based on minimum SLD length.

---

## Directory Structure

```
.
├── config.json           # Configuration file (set domain rules, caching, API keys, etc.)
├── README.md             # This README file
├── SECURITY.md           # Security Policy
├── check_domains.py      # Script to check domain availability
├── generate_domains.py   # Script to generate candidate domains
├── min_length.py         # Script to filter domains based on minimum SLD length (test)
├── reserved_updater.py   # Script to update reserved domains list
├── run_all.py            # Orchestrator script to run the complete workflow
├── requirements.txt      # Python package dependencies
├── .gitignore            # Git ignore file
├── logs/                 # Directory for log files (generated automatically)
└── output/               # Directory for generated outputs (e.g., candidate domains, results)
```

---

## Configuration

### `config.json`

A sample configuration file is provided. For example:

```json
{
  "min_sld_length": 2,
  "min_tld_length": 2,
  "max_cache_age_days": 7,
  "thread_count": 10,
  "check_timeout": 10,
  "domainr_api_type": "rapidapi",
  "domainr_api_keys": "",
  "enable_email": false,
  "smtp_host": "",
  "smtp_port": 465,
  "smtp_user": "",
  "smtp_pass": "",
  "email_to": "",
  "enable_webhook": false,
  "webhook_url": ""
}
```

**Notes:**
- Set `"min_sld_length"` and `"min_tld_length"` to `2` if you wish to generate candidate domains using 2‑letter SLDs and TLDs.
- Update API keys, email, and webhook settings if you wish to use those features.
- Adjust other values (cache age, thread count, etc.) as needed.

---

## Setup and Running the Project

### 1. Clone the Repository

```bash
git clone https://yourgithublink.com/your-amazing-project.git
cd your-amazing-project
```

### 2. (Optional) Set Up a Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure the Project

Edit the `config.json` file as needed (for example, adjust minimum lengths, cache settings, and API credentials).

---

## Running the Project

### Update Reserved Domains List (Optional)

This command updates the reserved domains list (stored in `reserved_domains.json`):

```bash
python reserved_updater.py
```

### Run the Automated Workflow

The orchestrator script will:
- Check/update the cached TLD list.
- Generate candidate domains (saved to `output/generated_domains.txt`).
- Check domain availability.
- Save results to `domain_results.json` and print a summary.

Run the workflow with:

```bash
python run_all.py
```

### Run Individual Scripts

- **Generate Candidate Domains Only:**

  ```bash
  python generate_domains.py --prefix-domain ab --prefix-tld us --only-words
  ```

  This example generates candidate domains where the SLD starts with "ab" and the TLD starts with "us", and filters for those that form a valid 4‑letter word.

- **Check Domain Availability Only:**

  ```bash
  python check_domains.py --domains-file output/generated_domains.txt
  ```

  This command checks domain availability for domains listed in `output/generated_domains.txt`.

- **Test Minimum Length Filtering:**

  ```bash
  python min_length.py
  ```

  This script tests filtering a sample list of domains based on the minimum SLD length defined in `config.json`.

---

## Logs and Output Files

- **Logs:** All logs are saved in the `logs/` directory.
- **Candidate Domains:** Generated candidate domains are saved in `output/generated_domains.txt`.
- **Results:** Domain availability results are saved in `domain_results.json`.

---

## .gitignore

The repository includes a `.gitignore` file to exclude virtual environments, caches, logs, output files, and other auto-generated artifacts.

---

## Additional Notes

- **Permissions:** Ensure that you have write permissions for the `logs/` and `output/` directories.
- **Customization:** Feel free to modify and extend the scripts (e.g., add additional filtering, integrate new APIs, etc.).
- **Feedback:** If you encounter any issues or have suggestions, please submit an issue or pull request.

Happy coding and domain hunting!