import logging
import sys
from pathlib import Path

import prawcore


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from reddit_recap import generate_recap, is_reddit_thread_url  # noqa: E402


logger = logging.getLogger(__name__)
APP_COMMENT_BUDGET = 60


class RecapError(Exception):
    pass


def build_recap(url: str):
    clean_url = (url or "").strip()
    if not clean_url:
        raise RecapError("Reddit URL is required.")
    if not is_reddit_thread_url(clean_url):
        raise RecapError("URL must be a Reddit thread URL.")

    try:
        recap = generate_recap(
            clean_url,
            mode="deep",
            max_comments=APP_COMMENT_BUDGET,
        )
    except ValueError as exc:
        raise RecapError(str(exc)) from exc
    except prawcore.exceptions.OAuthException as exc:
        logger.warning("Reddit OAuth error: %s", exc)
        raise RecapError("Reddit API credentials were rejected.") from exc
    except prawcore.exceptions.Forbidden as exc:
        logger.warning("Reddit forbidden response for URL %s: %s", clean_url, exc)
        raise RecapError("This Reddit post or subreddit is private or inaccessible.") from exc
    except prawcore.exceptions.NotFound as exc:
        logger.warning("Reddit not found response for URL %s: %s", clean_url, exc)
        raise RecapError("Reddit post was not found.") from exc
    except prawcore.exceptions.TooManyRequests as exc:
        logger.warning("Reddit rate limit for URL %s: %s", clean_url, exc)
        raise RecapError("Reddit API rate limit reached. Try again later.") from exc
    except Exception as exc:
        logger.exception("Unexpected recap generation error")
        raise RecapError("Unable to fetch this Reddit thread right now.") from exc

    metadata = recap["metadata"]
    return {
        "title": metadata["title"],
        "subreddit": metadata["subreddit"],
        "url": metadata["url"],
        "comment_count": recap["comment_count"],
        "markdown": recap["markdown"],
        "filename": f"{recap['filename']}.md",
    }
