# Bakusai Thread Daily Safe Summary

This project monitors one configured forum thread and produces a shop-level daily summary.

It does not save post text, raw HTML, personal names, service details, or individual profiles.

## Usage

```bash
pip install -r requirements.txt
python crawler.py
python -m unittest discover -s tests -v
```

Configuration is read from environment variables or `.env`-style shell setup:

```text
TARGET_URL
BARK_KEY
STATE_FILE
SUMMARY_DIR
REQUEST_TIMEOUT
```

## GitHub Actions

Add these repository secrets:

```text
TARGET_URL
BARK_KEY
```

The workflow runs once every 45 minutes and can also be started manually. It stores
state in GitHub Actions cache under `.runtime-state/` instead of committing the
target URL or summaries to the repository.
