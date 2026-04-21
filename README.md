# Job Scanner Bot

Automated job scanner that monitors multiple job boards, matches postings against your resume using semantic similarity (sentence-transformers), and sends alerts via Discord and/or Telegram.

## Architecture

```
config.py        → All settings, API keys, resume text, thresholds
sources.py       → Job source plugins (Adzuna, Remotive, Arbeitnow, USAJobs, The Muse, RSS)
matcher.py       → Sentence-transformer cosine similarity engine
alerts.py        → Discord webhook + Telegram bot notifications
main.py          → Scheduler, deduplication, CLI entry point
```

## Quick Start

```bash
# 1. Create venv
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Edit config.py:
#    - Paste your resume into RESUME_TEXT
#    - Set SEARCH_QUERIES for your target roles
#    - Add API keys (Adzuna is free, Remotive/Arbeitnow need no keys)
#    - Add Discord webhook URL and/or Telegram bot token

# 4. Run diagnostic first to tune your threshold
python main.py --stats

# 5. Single scan test
python main.py --once

# 6. Run on schedule (every 30 min by default)
python main.py
```

## Tuning the Threshold

85% is aggressive. Run `--stats` first to see your score distribution. If you get zero matches, try lowering to 0.60-0.70 and work up. Semantic similarity at 0.85 means "nearly identical topic and skill set" — most real job matches land in 0.55-0.80.

**Recommended approach:**
1. Start with `SIMILARITY_THRESHOLD = 0.55`
2. Run `--stats`, examine the histogram
3. Raise the threshold until you're getting 5-15 matches per scan

## Setting Up Alerts

### Discord
1. Open your Discord server
2. Channel Settings → Integrations → Webhooks → New Webhook
3. Copy the webhook URL into `config.py`

### Telegram
1. Message @BotFather on Telegram → `/newbot` → follow prompts
2. Copy the bot token into `config.py`
3. Message @userinfobot to get your chat ID
4. Copy your chat ID into `config.py`

## Running as a Background Service

### tmux / screen
```bash
tmux new -s jobscan
python main.py
# Ctrl+B, D to detach
```

### systemd (Linux)
```ini
# /etc/systemd/system/jobscanner.service
[Unit]
Description=Job Scanner Bot
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/job_scanner
ExecStart=/path/to/job_scanner/venv/bin/python main.py
Restart=on-failure
RestartSec=60

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable jobscanner
sudo systemctl start jobscanner
```

## Adding New Job Sources

Create a function in `sources.py`:

```python
def fetch_my_source(queries: list[str]) -> list[JobPosting]:
    jobs = []
    # ... fetch logic ...
    jobs.append(JobPosting(
        title="...", company="...", description="...",
        url="...", source="my_source", uid="my_source:unique_id"
    ))
    return jobs
```

Then register it in `SOURCE_MAP` and `ENABLED_SOURCES`.

## CLI Reference

| Command | Description |
|---|---|
| `python main.py` | Run continuous scanner (default 30 min interval) |
| `python main.py --once` | Single scan, then exit |
| `python main.py --stats` | Score distribution diagnostic |
| `python main.py --reset` | Clear seen-jobs database |
