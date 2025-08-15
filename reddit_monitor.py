"""
Reddit Monitoring Module for Ansible Mentions
Searches specified subreddits for mentions of Ansible and related keywords.
"""

import praw
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any
from textblob import TextBlob
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RedditMonitor:
    def __init__(self, client_id: str, client_secret: str, user_agent: str):
        """Initialize Reddit API connection."""
        try:
            self.reddit = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent=user_agent
            )
            logger.info("Reddit API connection established")
        except Exception as e:
            logger.error(f"Failed to connect to Reddit API: {e}")
            raise

    def search_mentions(self, keywords: List[str], subreddits: List[str], 
                       hours_back: int = 24, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Search for mentions across specified subreddits.
        
        Args:
            keywords: List of keywords to search for
            subreddits: List of subreddit names to search
            hours_back: How many hours back to search
            limit: Maximum number of posts to check per subreddit
            
        Returns:
            List of mention dictionaries with metadata
        """
        mentions = []
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        
        for subreddit_name in subreddits:
            logger.info(f"Searching r/{subreddit_name}")
            try:
                subreddit = self.reddit.subreddit(subreddit_name)
                
                # Search recent posts
                for post in subreddit.new(limit=limit):
                    post_time = datetime.fromtimestamp(post.created_utc)
                    
                    # Skip posts older than our cutoff
                    if post_time < cutoff_time:
                        continue
                    
                    # Check if any keyword appears in title or text
                    content = f"{post.title} {post.selftext}".lower()
                    
                    for keyword in keywords:
                        if keyword.lower() in content:
                            mention = self._extract_mention_data(post, keyword)
                            mentions.append(mention)
                            logger.info(f"Found mention in r/{subreddit_name}: {post.title[:50]}...")
                            break  # Don't duplicate posts for multiple keywords
                
                # Also check comments in recent posts
                for post in subreddit.hot(limit=50):  # Check fewer posts for comments
                    post_time = datetime.fromtimestamp(post.created_utc)
                    if post_time < cutoff_time:
                        continue
                        
                    # Expand comment tree
                    post.comments.replace_more(limit=5)
                    
                    for comment in post.comments.list()[:20]:  # Limit comments per post
                        if hasattr(comment, 'created_utc'):
                            comment_time = datetime.fromtimestamp(comment.created_utc)
                            if comment_time < cutoff_time:
                                continue
                                
                            for keyword in keywords:
                                if keyword.lower() in comment.body.lower():
                                    mention = self._extract_comment_data(comment, post, keyword)
                                    mentions.append(mention)
                                    logger.info(f"Found mention in comment: {comment.body[:50]}...")
                                    break
                                    
            except Exception as e:
                logger.error(f"Error searching r/{subreddit_name}: {e}")
                continue
        
        return mentions

    def _extract_mention_data(self, post, keyword: str) -> Dict[str, Any]:
        """Extract relevant data from a Reddit post."""
        # Simple sentiment analysis
        text = f"{post.title} {post.selftext}"
        sentiment = self._analyze_sentiment(text)
        
        return {
            'platform': 'reddit',
            'type': 'post',
            'id': post.id,
            'title': post.title,
            'content': post.selftext,
            'author': str(post.author) if post.author else '[deleted]',
            'subreddit': str(post.subreddit),
            'url': f"https://reddit.com{post.permalink}",
            'score': post.score,
            'num_comments': post.num_comments,
            'created_utc': datetime.fromtimestamp(post.created_utc).isoformat(),
            'keyword_matched': keyword,
            'sentiment_score': sentiment['polarity'],
            'sentiment_label': sentiment['label'],
            'raw_data': {
                'upvote_ratio': post.upvote_ratio,
                'distinguished': post.distinguished,
                'stickied': post.stickied
            }
        }

    def _extract_comment_data(self, comment, post, keyword: str) -> Dict[str, Any]:
        """Extract relevant data from a Reddit comment."""
        sentiment = self._analyze_sentiment(comment.body)
        
        return {
            'platform': 'reddit',
            'type': 'comment',
            'id': comment.id,
            'title': f"Comment on: {post.title}",
            'content': comment.body,
            'author': str(comment.author) if comment.author else '[deleted]',
            'subreddit': str(post.subreddit),
            'url': f"https://reddit.com{comment.permalink}",
            'score': comment.score,
            'num_comments': 0,  # Comments don't have sub-comments in our scope
            'created_utc': datetime.fromtimestamp(comment.created_utc).isoformat(),
            'keyword_matched': keyword,
            'sentiment_score': sentiment['polarity'],
            'sentiment_label': sentiment['label'],
            'raw_data': {
                'is_submitter': comment.is_submitter,
                'parent_post_id': post.id,
                'parent_post_title': post.title
            }
        }

    def _analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment of text using TextBlob."""
        if not text or text.isspace():
            return {'polarity': 0.0, 'label': 'neutral'}
            
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        
        # Convert polarity to label
        if polarity > 0.1:
            label = 'positive'
        elif polarity < -0.1:
            label = 'negative'
        else:
            label = 'neutral'
            
        return {
            'polarity': polarity,
            'subjectivity': blob.sentiment.subjectivity,
            'label': label
        }

    def get_trending_topics(self, subreddit_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get trending topics from a specific subreddit."""
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            trending = []
            
            for post in subreddit.hot(limit=limit):
                trending.append({
                    'title': post.title,
                    'score': post.score,
                    'url': f"https://reddit.com{post.permalink}",
                    'num_comments': post.num_comments,
                    'created_utc': datetime.fromtimestamp(post.created_utc).isoformat()
                })
            
            return trending
        except Exception as e:
            logger.error(f"Error getting trending topics from r/{subreddit_name}: {e}")
            return []


def main():
    """Test the Reddit monitor."""
    from dotenv import load_dotenv
    load_dotenv()
    
    # Test configuration
    monitor = RedditMonitor(
        client_id=os.getenv('REDDIT_CLIENT_ID', 'test'),
        client_secret=os.getenv('REDDIT_CLIENT_SECRET', 'test'),
        user_agent=os.getenv('REDDIT_USER_AGENT', 'ansible-mention-bot/1.0')
    )
    
    keywords = ['ansible', 'ansible automation platform']
    subreddits = ['ansible', 'devops']
    
    mentions = monitor.search_mentions(keywords, subreddits, hours_back=24)
    
    print(f"Found {len(mentions)} mentions:")
    for mention in mentions[:5]:  # Show first 5
        print(f"- {mention['title'][:60]}... (Score: {mention['score']}, Sentiment: {mention['sentiment_label']})")


if __name__ == "__main__":
    main()