#!/usr/bin/env python3
"""Reddit Recap — compact, high-signal thread sampler for Custom GPT input."""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from urllib.parse import urlparse

import praw
import praw.exceptions
import praw.models
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

KNOWN_BOTS = {
    "AutoModerator",
    "RemindMeBot",
    "WikiTextBot",
    "sneakpeekbot",
    "TotesMessenger",
    "CommonMisspellingBot",
    "HelperBot_",
    "FatFingerHelperBot",
    "AnimalFactsBot",
    "ModeratelyHelpfulBot",
    "RepostSleuthBot",
    "SaveVideo",
    "stabbot",
    "LinkifyBot",
    "sub_doesnt_exist_bot",
    "GifReversingBot",
    "haikusbot",
    "YoMommaJokeBot",
    "B0tRank",
    "converter-bot",
    "nice-scores",
}

TOURNAMENT_KEYWORDS = {
    "the international": "the-international",
    "dreamleague major": "dreamleague-major",
    "dreamleague": "dreamleague",
    "esl one major": "esl-one-major",
    "esl one": "esl-one",
    "pgl major": "pgl-major",
    "pgl": "pgl",
    "riyadh masters": "riyadh-masters",
    "bali major": "bali-major",
    "berlin major": "berlin-major",
    "katowice major": "katowice-major",
    "arlington major": "arlington-major",
    "lima major": "lima-major",
    "stockholm major": "stockholm-major",
}

# Regex for TI + number (ti10, ti11, ti12, …)
TI_PATTERN = re.compile(r"\bti(\d+)\b", re.IGNORECASE)

MAX_COMMENT_CHARS = 1000
DEFAULT_DEEP_BUDGET = 60
DEFAULT_FAST_BUDGET = 30

URL_PATTERN = re.compile(
    r"https?://(www\.|old\.|new\.)?reddit\.com/r/\w+/comments/\w+"
)
SHORT_URL_PATTERN = re.compile(r"https?://redd\.it/\w+")

# ---------------------------------------------------------------------------
# CLI parsing
# ---------------------------------------------------------------------------


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Reddit Recap — fetch and sample a Reddit thread into a compact Markdown recap."
    )
    parser.add_argument("url", help="Reddit thread URL")
    parser.add_argument(
        "--mode",
        choices=["fast", "deep"],
        default="deep",
        help="Sampling depth (default: deep)",
    )
    parser.add_argument(
        "--outdir", default="outputs", help="Output directory (default: outputs)"
    )
    parser.add_argument(
        "--max-comments",
        type=int,
        default=None,
        help="Total comment budget (default: 60 deep, 30 fast)",
    )
    parser.add_argument(
        "--top", type=int, default=None, help="Number of top comments to fetch"
    )
    parser.add_argument(
        "--controversial",
        type=int,
        default=None,
        help="Number of controversial comments to fetch",
    )
    parser.add_argument(
        "--new", type=int, default=None, help="Number of newest comments to fetch"
    )
    parser.add_argument(
        "--include-json",
        action="store_true",
        help="Also write a JSON output file",
    )
    parser.add_argument(
        "--min-len",
        type=int,
        default=0,
        help="Minimum comment body length in characters (default: 0)",
    )
    return parser.parse_args(argv)


def resolve_budget(top, controversial, new, total):
    """Distribute total budget across the three sort buckets."""
    specified = {}
    if top is not None:
        specified["top"] = top
    if controversial is not None:
        specified["controversial"] = controversial
    if new is not None:
        specified["new"] = new

    if len(specified) == 3:
        return top, controversial, new

    if len(specified) == 0:
        third = total // 3
        remainder = total % 3
        return (
            third + (1 if remainder > 0 else 0),
            third + (1 if remainder > 1 else 0),
            third,
        )

    used = sum(specified.values())
    remaining = max(0, total - used)
    unspecified_count = 3 - len(specified)
    per_unspecified = remaining // unspecified_count if unspecified_count else 0

    return (
        top if top is not None else per_unspecified,
        controversial if controversial is not None else per_unspecified,
        new if new is not None else per_unspecified,
    )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_url(url):
    """Check that *url* looks like a Reddit thread link."""
    if URL_PATTERN.match(url) or SHORT_URL_PATTERN.match(url):
        return url
    print(
        "Error: URL does not look like a Reddit thread link.\n"
        "Expected format: https://www.reddit.com/r/<subreddit>/comments/<id>/...\n"
        "            or:  https://redd.it/<id>",
        file=sys.stderr,
    )
    sys.exit(1)


# ---------------------------------------------------------------------------
# Reddit client
# ---------------------------------------------------------------------------


def init_reddit_client():
    """Create a read-only PRAW Reddit instance from environment variables."""
    client_id = os.environ.get("REDDIT_CLIENT_ID")
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
    user_agent = os.environ.get("REDDIT_USER_AGENT", "reddit-recap/1.0")

    if not client_id or not client_secret:
        print(
            "Error: Reddit API credentials not found.\n"
            "Set the following environment variables:\n"
            "  REDDIT_CLIENT_ID      — your app's client ID\n"
            "  REDDIT_CLIENT_SECRET  — your app's client secret\n"
            "  REDDIT_USER_AGENT     — (optional) custom user-agent string\n\n"
            "Create a Reddit 'script' app at https://www.reddit.com/prefs/apps",
            file=sys.stderr,
        )
        sys.exit(1)

    return praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
    )


# ---------------------------------------------------------------------------
# Retry helper
# ---------------------------------------------------------------------------


def with_retry(fn, max_retries=3, backoff_base=2):
    """Call *fn* with exponential backoff on transient errors."""
    for attempt in range(max_retries):
        try:
            return fn()
        except praw.exceptions.RedditAPIException as exc:
            if attempt == max_retries - 1:
                raise
            wait = backoff_base ** attempt
            print(f"API error (attempt {attempt + 1}/{max_retries}), retrying in {wait}s: {exc}")
            time.sleep(wait)
        except Exception as exc:
            if attempt == max_retries - 1:
                raise
            wait = backoff_base ** attempt
            print(f"Error (attempt {attempt + 1}/{max_retries}), retrying in {wait}s: {exc}")
            time.sleep(wait)


# ---------------------------------------------------------------------------
# Data extraction helpers
# ---------------------------------------------------------------------------


def is_valid_comment(comment):
    """Return True if the comment should be included in the recap."""
    if isinstance(comment, praw.models.MoreComments):
        return False
    if comment.body in ("[deleted]", "[removed]"):
        return False
    if comment.author is None:
        return False
    if str(comment.author) in KNOWN_BOTS:
        return False
    if comment.stickied:
        return False
    return True


def extract_comment_data(comment, min_len=0):
    """Convert a PRAW comment into a plain dict. Returns None if too short."""
    body = comment.body.strip()
    if min_len and len(body) < min_len:
        return None

    truncated = len(body) > MAX_COMMENT_CHARS
    if truncated:
        cut = body[:MAX_COMMENT_CHARS]
        space_idx = cut.rfind(" ")
        if space_idx > MAX_COMMENT_CHARS // 2:
            cut = cut[:space_idx]
        body = cut + "..."

    # Count loaded replies without expanding MoreComments
    try:
        num_replies = sum(
            1 for r in comment.replies if not isinstance(r, praw.models.MoreComments)
        )
    except Exception:
        num_replies = 0

    return {
        "id": comment.id,
        "author": str(comment.author),
        "score": comment.score,
        "body": body,
        "permalink": f"https://reddit.com{comment.permalink}",
        "created_utc": comment.created_utc,
        "num_replies": num_replies,
        "truncated": truncated,
    }


def fetch_thread_metadata(submission):
    """Extract thread-level metadata from a PRAW Submission."""
    posted_dt = datetime.fromtimestamp(submission.created_utc, tz=timezone.utc)
    return {
        "title": submission.title,
        "subreddit": str(submission.subreddit),
        "url": f"https://reddit.com{submission.permalink}",
        "posted_utc": submission.created_utc,
        "posted_str": posted_dt.strftime("%Y-%m-%d %H:%M UTC"),
        "score": submission.score,
        "num_comments": submission.num_comments,
        "selftext": (submission.selftext or "")[:2000],
    }


# ---------------------------------------------------------------------------
# Comment fetching
# ---------------------------------------------------------------------------


def fetch_comments_by_sort(reddit, url, sort_order, limit, min_len=0):
    """Fetch top-level comments for a thread using *sort_order*."""
    submission = reddit.submission(url=url)
    submission.comment_sort = sort_order
    submission.comment_limit = limit * 3  # overfetch for filtering headroom
    submission.comments.replace_more(limit=0)

    comments = []
    for comment in submission.comments:
        if not is_valid_comment(comment):
            continue
        data = extract_comment_data(comment, min_len=min_len)
        if data is not None:
            comments.append(data)
        if len(comments) >= limit:
            break
    return comments


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


def deduplicate_comments(top, controversial, new):
    """Remove duplicates across categories. Priority: top > controversial > new."""
    seen = set()

    def dedup(comments):
        result = []
        for c in comments:
            if c["id"] not in seen:
                seen.add(c["id"])
                result.append(c)
        return result

    return dedup(top), dedup(controversial), dedup(new)


# ---------------------------------------------------------------------------
# High-engagement (deep mode)
# ---------------------------------------------------------------------------


def fetch_high_engagement_comments(reddit, url, all_comments, top_n=5, replies_per=2):
    """Identify the most-replied-to comments and fetch their top replies."""
    candidates = sorted(all_comments, key=lambda c: c["num_replies"], reverse=True)
    candidates = [c for c in candidates if c["num_replies"] > 0][:top_n]
    if not candidates:
        return []

    # Re-fetch the submission sorted by "top" to access reply trees
    submission = reddit.submission(url=url)
    submission.comment_sort = "top"
    submission.comments.replace_more(limit=0)

    comment_map = {}
    for comment in submission.comments:
        if not isinstance(comment, praw.models.MoreComments):
            comment_map[comment.id] = comment

    high_engagement = []
    for candidate in candidates:
        praw_comment = comment_map.get(candidate["id"])
        replies_data = []
        if praw_comment:
            for reply in praw_comment.replies:
                if isinstance(reply, praw.models.MoreComments):
                    continue
                if not is_valid_comment(reply):
                    continue
                rd = extract_comment_data(reply)
                if rd:
                    replies_data.append(rd)
                if len(replies_data) >= replies_per:
                    break
        candidate_copy = dict(candidate)
        candidate_copy["replies_data"] = replies_data
        high_engagement.append(candidate_copy)

    return high_engagement


# ---------------------------------------------------------------------------
# Formatting — Markdown
# ---------------------------------------------------------------------------


def format_markdown(metadata, top, controversial, new, high_engagement=None):
    """Build the Markdown recap string."""
    lines = [
        "# Reddit Recap\n",
        "## Thread Info",
        f"- **Title:** {metadata['title']}",
        f"- **Subreddit:** r/{metadata['subreddit']}",
        f"- **Posted:** {metadata['posted_str']}",
        f"- **Score:** {metadata['score']} | **Comments:** {metadata['num_comments']}",
        f"- **Link:** {metadata['url']}",
        "\n---\n",
    ]

    def _section(title, comments):
        if not comments:
            return
        lines.append(f"## {title}\n")
        for i, c in enumerate(comments, 1):
            lines.append(f"### {i}. u/{c['author']} (score: {c['score']})")
            quoted = "\n".join(f"> {line}" for line in c["body"].split("\n"))
            lines.append(quoted)
            if c.get("truncated"):
                lines.append("*(truncated)*")
            lines.append(f"[permalink]({c['permalink']})\n")

    _section("Top Comments", top)
    _section("Controversial Comments", controversial)
    _section("Newest Comments", new)

    if high_engagement:
        lines.append("## High-Engagement Comments\n")
        for i, c in enumerate(high_engagement, 1):
            lines.append(
                f"### {i}. u/{c['author']} (score: {c['score']}, replies: {c['num_replies']})"
            )
            quoted = "\n".join(f"> {line}" for line in c["body"].split("\n"))
            lines.append(quoted)
            if c.get("truncated"):
                lines.append("*(truncated)*")
            lines.append(f"[permalink]({c['permalink']})\n")

            if c.get("replies_data"):
                lines.append("#### Top Replies")
                for r in c["replies_data"]:
                    reply_body = r["body"].replace("\n", " ")
                    lines.append(
                        f"- u/{r['author']} (score: {r['score']}): {reply_body} "
                        f"[permalink]({r['permalink']})"
                    )
                lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Formatting — JSON
# ---------------------------------------------------------------------------


def format_json(metadata, top, controversial, new, high_engagement=None):
    """Build the JSON recap string."""
    data = {
        "metadata": metadata,
        "comments": {
            "top": top,
            "controversial": controversial,
            "new": new,
        },
    }
    if high_engagement:
        data["comments"]["high_engagement"] = high_engagement
    return json.dumps(data, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Filename generation
# ---------------------------------------------------------------------------


def detect_tournament_tag(title):
    """Return a tournament slug if the title matches a known Dota 2 event."""
    title_lower = title.lower()

    # Check TI pattern first (ti10, ti11, …)
    ti_match = TI_PATTERN.search(title_lower)
    if ti_match:
        return f"ti{ti_match.group(1)}"

    # Check keyword map (longer keys first to prefer specific matches)
    for keyword in sorted(TOURNAMENT_KEYWORDS, key=len, reverse=True):
        if keyword in title_lower:
            return TOURNAMENT_KEYWORDS[keyword]

    return ""


def generate_filename(metadata):
    """Build a filename stem from metadata: date_tournament_safe-title."""
    posted_dt = datetime.fromtimestamp(metadata["posted_utc"], tz=timezone.utc)
    date_str = posted_dt.strftime("%Y-%m-%d")

    # Safe title
    safe_title = re.sub(r"[^a-z0-9]+", "-", metadata["title"].lower()).strip("-")[:80]

    tournament_tag = detect_tournament_tag(metadata["title"])
    if tournament_tag:
        return f"{date_str}_{tournament_tag}_{safe_title}"
    return f"{date_str}_{safe_title}"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    args = parse_args()

    url = validate_url(args.url)
    reddit = init_reddit_client()

    # Resolve comment budget
    total_budget = args.max_comments
    if total_budget is None:
        total_budget = DEFAULT_DEEP_BUDGET if args.mode == "deep" else DEFAULT_FAST_BUDGET
    top_n, cont_n, new_n = resolve_budget(
        args.top, args.controversial, args.new, total_budget
    )

    # Fetch metadata
    print("Fetching thread metadata...")
    submission = with_retry(lambda: reddit.submission(url=url))
    metadata = fetch_thread_metadata(submission)

    print(f"  {metadata['title']}")
    print(f"  r/{metadata['subreddit']} | {metadata['posted_str']}")
    print(f"  Mode: {args.mode} | Budget: {total_budget} (top:{top_n} controversial:{cont_n} new:{new_n})")

    # Fetch comments by sort order
    print("Fetching top comments...")
    top_comments = with_retry(
        lambda: fetch_comments_by_sort(reddit, url, "top", top_n, min_len=args.min_len)
    )
    print(f"  got {len(top_comments)}")

    print("Fetching controversial comments...")
    cont_comments = with_retry(
        lambda: fetch_comments_by_sort(reddit, url, "controversial", cont_n, min_len=args.min_len)
    )
    print(f"  got {len(cont_comments)}")

    print("Fetching newest comments...")
    new_comments = with_retry(
        lambda: fetch_comments_by_sort(reddit, url, "new", new_n, min_len=args.min_len)
    )
    print(f"  got {len(new_comments)}")

    # Deduplicate
    top_comments, cont_comments, new_comments = deduplicate_comments(
        top_comments, cont_comments, new_comments
    )

    # High-engagement (deep mode)
    high_engagement = []
    if args.mode == "deep":
        all_comments = top_comments + cont_comments + new_comments
        print("Fetching high-engagement replies...")
        high_engagement = with_retry(
            lambda: fetch_high_engagement_comments(reddit, url, all_comments)
        )
        print(f"  got {len(high_engagement)} high-engagement comments")

    # Format outputs
    md_output = format_markdown(
        metadata, top_comments, cont_comments, new_comments, high_engagement
    )

    # Write files
    os.makedirs(args.outdir, exist_ok=True)
    base_name = generate_filename(metadata)

    md_path = os.path.join(args.outdir, f"{base_name}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_output)
    print(f"\nMarkdown saved: {md_path}")

    if args.include_json:
        json_output = format_json(
            metadata, top_comments, cont_comments, new_comments, high_engagement
        )
        json_path = os.path.join(args.outdir, f"{base_name}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            f.write(json_output)
        print(f"JSON saved:     {json_path}")

    # Summary
    total = len(top_comments) + len(cont_comments) + len(new_comments)
    print(f"\nRecap complete: {total} unique comments sampled")
    if high_engagement:
        print(f"High-engagement comments with replies: {len(high_engagement)}")


if __name__ == "__main__":
    main()
