import praw
from datetime import datetime, timezone
from dotenv import load_dotenv
import os

from flask import Flask, jsonify
from flask_cors import CORS

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
CORS(app)  # Allow frontend requests

# Initialize Reddit API client
reddit = praw.Reddit(
    client_id=os.environ.get("REDDIT_CLIENT_ID"),
    client_secret=os.environ.get("REDDIT_CLIENT_SECRET"),
    user_agent="dota-reddit-reader script by /u/adrian",
)

print("✅ Reddit API Connected:", reddit.read_only)

# 🎯 Define subreddit and filters
SUBREDDIT_NAME = "dota2"
DESIRED_FLAIRS = {"Article", "Clips", "Bug", "Discussion"}
POST_LIMIT = 10

def fetch_relevant_posts():
    """
    Fetches posts from r/DotA2 with relevant flairs and displays them.
    """
    subreddit = reddit.subreddit(SUBREDDIT_NAME)
    useful_posts = []

    print(f"\n🔎 Fetching relevant posts from r/{SUBREDDIT_NAME}...")

    for submission in subreddit.top(time_filter="day", limit=POST_LIMIT * 2):  # Fetch more posts to filter down
        if submission.link_flair_text and submission.link_flair_text in DESIRED_FLAIRS:
            readable_time = datetime.fromtimestamp(submission.created_utc, timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')

            useful_posts.append({
                "title": submission.title,
                "flair": submission.link_flair_text,
                "created_at": readable_time,
                "url": submission.url,
                "score": submission.score,
                "comments": submission.num_comments
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