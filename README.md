# Reddit Recap

A local Python CLI tool that fetches a Reddit thread and outputs a compact, high-signal Markdown recap. Designed to be pasted into a Custom GPT for summarization.

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Create a Reddit API app

1. Go to https://www.reddit.com/prefs/apps
2. Click **"create another app…"**
3. Select **"script"**
4. Set a name (e.g., `reddit-recap`) and redirect URI to `http://localhost`
5. Note your **client ID** (under the app name) and **client secret**

### 3. Set environment variables

```bash
export REDDIT_CLIENT_ID="your_client_id"
export REDDIT_CLIENT_SECRET="your_client_secret"
export REDDIT_USER_AGENT="reddit-recap/1.0"  # optional
```

Or copy `.env.example` and load with your preferred method.

## Usage

### Basic

```bash
python reddit_recap.py "https://www.reddit.com/r/DotA2/comments/abc123/match_thread_ti_finals/"
```

### Fast mode (smaller budget)

```bash
python reddit_recap.py "https://www.reddit.com/r/DotA2/comments/abc123/..." --mode fast
```

### Custom comment budget

```bash
python reddit_recap.py "https://..." --max-comments 40 --top 15 --controversial 15 --new 10
```

### Include JSON output

```bash
python reddit_recap.py "https://..." --include-json
```

### Minimum comment length filter

```bash
python reddit_recap.py "https://..." --min-len 50
```

## Fast vs Deep Mode

| | Fast | Deep |
|---|---|---|
| Default comment budget | 30 | 60 |
| High-engagement section | No | Yes (top 5, with 1-2 replies each) |
| API calls | ~4 | ~5 |

Both modes sample the same three categories (top, controversial, new) and deduplicate across them.

## Output

Files are saved to `./outputs/` by default (configurable with `--outdir`).

### Filename format

```
YYYY-MM-DD_[tournament-tag]_safe-thread-title.md
```

Examples:
- `2026-02-18_the-international_ti-grand-finals-match-thread.md`
- `2026-02-18_pgl-major_day-3-discussion.md`
- `2026-02-18_general-dota-discussion-thread.md` (no tournament detected)

Tournament tags are auto-detected from the thread title for major Dota 2 Valve events (The International, Majors, etc.).

## CLI Reference

```
python reddit_recap.py <url> [options]

Positional:
  url                     Reddit thread URL

Options:
  --mode {fast,deep}      Sampling depth (default: deep)
  --outdir DIR            Output directory (default: outputs)
  --max-comments N        Total comment budget
  --top N                 Override top comment count
  --controversial N       Override controversial comment count
  --new N                 Override new comment count
  --include-json          Also write a JSON output file
  --min-len N             Minimum comment body length (default: 0)
```

## Why does the extracted count differ from Reddit's comment count?

Reddit's displayed comment count includes **all** comments: nested replies, deleted/removed comments, bot comments, and collapsed threads. This tool intentionally samples only a subset:

- Only top-level comments (not deep reply chains)
- Deleted/removed comments are skipped
- Known bot accounts are filtered out
- Stickied mod comments are excluded
- The "more comments" trees are not expanded (to keep the tool fast)

This is by design — the goal is a high-signal sample, not a complete dump.
