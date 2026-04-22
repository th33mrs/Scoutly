# Contributing to Trovly

## Adding a New Job Source

1. Write a fetch function in sources.py that returns a list of JobPosting objects
2. Add it to SOURCE_MAP at the bottom of sources.py
3. Add a toggle in config.py under ENABLED_SOURCES
4. Test with python main.py --once
5. Submit a PR

## Code Style

- No f-strings (breaks heredoc pasting)
- Use .format() for string formatting
- Use try/except around all external API calls
- Run python security.py before submitting

## Reporting Issues

Open a GitHub issue with what you expected, what happened, your Python version, and any error output (redact secrets).
