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

def fetch_relevant_posts():
    """
    Fetches posts from r/DotA2 with relevant flairs and displays them.
    """
    subreddit = reddit.subreddit(SUBREDDIT_NAME)
    useful_posts = []

    print(f"\n🔎 Fetching relevant posts from r/{SUBREDDIT_NAME}...")

    for submission in subreddit.top(time_filter="day", limit=POST_LIMIT * 2):  # Fetch more posts to filter down
        if submission.link_flair_text and submission.link_flair_text in DESIRED_FLAIRS:
            useful_posts.append({
                "author_name": submission.author.name,
                "author_image": submission.author.icon_img,
                "title": submission.title,
                "flair": submission.link_flair_text,
                "created_at": time_ago(submission.created_utc),
                "url": submission.url,
                "score": submission.score,
                "comments": submission.num_comments,
                "selftext": submission.selftext,
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