import praw
from datetime import datetime, timezone
from dotenv import load_dotenv
import os

from flask import Flask, jsonify
from flask_cors import CORS

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# Initialize Reddit API client
reddit = praw.Reddit(
    client_id=os.environ.get("REDDIT_CLIENT_ID"),
    client_secret=os.environ.get("REDDIT_CLIENT_SECRET"),
    user_agent="dota-reddit-reader script by /u/adrian",
)

print("✅ Reddit API Connected:", reddit.read_only)

# 🎯 Define subreddit and filters
SUBREDDIT_NAME = "dota2"
# DESIRED_FLAIRS = {"Article", "Clips", "Bug", "Discussion", "Fluff"}
DESIRED_FLAIRS = {"Article", "Fluff"}
POST_LIMIT = 15

def time_ago(created_utc):
    now = datetime.now(timezone.utc)
    diff = now - datetime.fromtimestamp(created_utc, timezone.utc)

    if diff.days < 1:
        hours = diff.seconds // 3600
        if hours < 1:
            minutes = diff.seconds // 60
            return f"{minutes} minutes ago" if minutes > 1 else "Just now"
        return f"{hours} hours ago"

    elif diff.days < 7:
        return f"{diff.days} days ago"

    elif diff.days < 14:
        return "1 week ago"

    elif diff.days < 30:
        return f"{diff.days // 7} weeks ago"

    elif diff.days < 60:
        return "1 month ago"

    elif diff.days < 365:
        return f"{diff.days // 30} months ago"

    else:
        return f"{diff.days // 365} years ago"

def determine_media_type(submission):
    """
    Determines if the Reddit post contains an image, video, or is just text.
    """
    url = submission.url

    # ✅ Check if it's a Reddit-hosted video
    if submission.is_video:
        return {
            "media_type": "video",
            "media_url": submission.media["reddit_video"]["fallback_url"] if submission.media else None
        }

    # ✅ Check if it's an image
    image_extensions = (".jpg", ".png", ".gif", ".jpeg", ".webp")
    if url.endswith(image_extensions):
        return {
            "media_type": "image",
            "media_url": url
        }

    # ✅ Check if it's an embedded YouTube, Imgur, or other external media
    if "youtube.com" in url or "youtu.be" in url:
        return {
            "media_type": "youtube",
            "media_url": url
        }
    if "imgur.com" in url or "gfycat.com" in url:
        return {
            "media_type": "external_image",
            "media_url": url
        }

    # ✅ If none of the above, it's a text post or external link
    if submission.is_self:
        return {
            "media_type": "text",
            "media_url": None,
            "text_content": submission.selftext
        }
    
    return {
        "media_type": "link",
        "media_url": url
    }


def fetch_relevant_posts():
    """
    Fetches posts from r/DotA2 with relevant flairs and displays them.
    """
    subreddit = reddit.subreddit(SUBREDDIT_NAME)
    useful_posts = []

    print(f"\n🔎 Fetching relevant posts from r/{SUBREDDIT_NAME}...")

    for submission in subreddit.top(time_filter="day", limit=POST_LIMIT * 2):  # Fetch more posts to filter down
        media_info = determine_media_type(submission)

        if submission.link_flair_text and submission.link_flair_text in DESIRED_FLAIRS:
            useful_posts.append({
                "author_name": submission.author.name if submission.author.name else "Unknown",
                "author_image": submission.author.icon_img,
                "title": submission.title,
                "flair": submission.link_flair_text,
                "created_at": time_ago(submission.created_utc),
                "media_type": media_info["media_type"],
                "media_url": media_info["media_url"],
                "text_content": media_info.get("text_content", ""),
                "url": submission.url,
                "score": submission.score,
                "comments": submission.num_comments,
            })

        if len(useful_posts) >= POST_LIMIT:
            break

    return useful_posts

def display_posts(posts):
    """
    Displays the relevant posts in a readable format.
    """
    print("\n📌 **Relevant Dota 2 Posts** 📌\n")
    for idx, post in enumerate(posts, start=1):
        print(f"{idx}. **{post['title']}**")
        print(f"   🏷 Flair: {post['flair']} | 📆 Posted on {post['created_at']} | 👍 {post['score']} Upvotes | 💬 {post['comments']} Comments")
        print(f"   🔗 [Reddit Link]({post['url']})\n")

if __name__ == "__main__":
    posts = fetch_relevant_posts()
    
    if posts:
        display_posts(posts)
    else:
        print("⚠️ No relevant posts found.")

@app.route('/api/posts', methods=['GET'])
def get_posts():
    """API route to fetch Reddit posts."""
    posts = fetch_relevant_posts()
    return jsonify(posts)

if __name__ == "__main__":
    app.run(debug=True)