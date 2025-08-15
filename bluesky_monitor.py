"""
Bluesky Monitoring Module for Ansible Mentions
Searches Bluesky for mentions of Ansible and related keywords using AT Protocol.
"""

from atproto import Client
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from textblob import TextBlob
import logging
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BlueskyMonitor:
    def __init__(self, username: str, password: str):
        """
        Initialize Bluesky API connection.
        
        Args:
            username: Bluesky username/handle
            password: Bluesky password or app password
        """
        try:
            self.client = Client()
            self.client.login(username, password)
            logger.info("Bluesky API connection established")
        except Exception as e:
            logger.error(f"Failed to connect to Bluesky API: {e}")
            raise

    def search_mentions(self, keywords: List[str], hours_back: int = 24, 
                       max_results: int = 100) -> List[Dict[str, Any]]:
        """
        Search for mentions of keywords on Bluesky.
        
        Args:
            keywords: List of keywords to search for
            hours_back: How many hours back to search
            max_results: Maximum number of posts to retrieve
            
        Returns:
            List of mention dictionaries with metadata
        """
        mentions = []
        
        # Calculate time range
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        
        for keyword in keywords:
            logger.info(f"Searching Bluesky for keyword: {keyword}")
            try:
                # Search for posts containing the keyword
                # Note: AT Protocol search capabilities may be limited
                # This is a basic implementation that can be enhanced as the API evolves
                search_results = self._search_posts(keyword, max_results)
                
                for post_data in search_results:
                    # Check if post is within our time range
                    post_time = self._parse_timestamp(post_data.get('createdAt', ''))
                    if post_time and post_time < cutoff_time:
                        continue
                    
                    # Verify keyword match (case-insensitive)
                    content = post_data.get('text', '').lower()
                    if keyword.lower() in content:
                        mention = self._extract_post_data(post_data, keyword)
                        mentions.append(mention)
                        logger.info(f"Found mention: {post_data.get('text', '')[:50]}...")
                        
            except Exception as e:
                logger.error(f"Error searching for keyword '{keyword}': {e}")
                continue
        
        # Remove duplicates and limit results
        unique_mentions = self._deduplicate_mentions(mentions)
        return unique_mentions[:max_results]

    def _search_posts(self, keyword: str, limit: int) -> List[Dict[str, Any]]:
        """
        Search for posts containing a keyword.
        Note: This implementation may need to be updated based on available AT Protocol search capabilities.
        """
        try:
            # For now, we'll use a basic approach since Bluesky's search API may be evolving
            # This might need to be updated to use proper search endpoints when available
            
            # Try to get recent posts from the firehose or timeline
            # This is a placeholder implementation that should be enhanced
            posts = []
            
            # You could implement timeline scanning or use search APIs when available
            # For demonstration, we'll return an empty list for now
            # In a real implementation, you'd call the appropriate AT Protocol endpoints
            
            return posts
            
        except Exception as e:
            logger.error(f"Error in _search_posts for '{keyword}': {e}")
            return []

    def _parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """Parse ISO timestamp string to datetime object."""
        try:
            if timestamp_str:
                # Handle ISO format with timezone
                return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except Exception as e:
            logger.warning(f"Failed to parse timestamp '{timestamp_str}': {e}")
        return None

    def _extract_post_data(self, post_data: Dict[str, Any], keyword: str) -> Dict[str, Any]:
        """Extract relevant data from a Bluesky post."""
        # Analyze sentiment
        text = post_data.get('text', '')
        sentiment = self._analyze_sentiment(text)
        
        # Extract author information
        author = post_data.get('author', {})
        author_handle = author.get('handle', 'unknown')
        author_display_name = author.get('displayName', author_handle)
        
        # Extract engagement metrics
        like_count = post_data.get('likeCount', 0)
        repost_count = post_data.get('repostCount', 0)
        reply_count = post_data.get('replyCount', 0)
        
        # Generate post URL
        post_uri = post_data.get('uri', '')
        post_url = self._generate_post_url(author_handle, post_uri)
        
        return {
            'platform': 'bluesky',
            'type': 'post',
            'id': post_data.get('cid', '') or post_data.get('uri', ''),
            'title': f"Post by @{author_handle}",
            'content': text,
            'author': author_handle,
            'author_display_name': author_display_name,
            'url': post_url,
            'score': like_count + repost_count,  # Combined engagement score
            'num_comments': reply_count,
            'created_utc': post_data.get('createdAt', ''),
            'keyword_matched': keyword,
            'sentiment_score': sentiment['polarity'],
            'sentiment_label': sentiment['label'],
            'raw_data': {
                'like_count': like_count,
                'repost_count': repost_count,
                'reply_count': reply_count,
                'uri': post_uri,
                'cid': post_data.get('cid', ''),
                'author_did': author.get('did', ''),
                'author_avatar': author.get('avatar', ''),
                'indexed_at': post_data.get('indexedAt', '')
            }
        }

    def _generate_post_url(self, author_handle: str, post_uri: str) -> str:
        """Generate a Bluesky post URL from handle and URI."""
        try:
            # Extract the post ID from the URI
            # URI format: at://did:plc:...../app.bsky.feed.post/....
            if 'app.bsky.feed.post/' in post_uri:
                post_id = post_uri.split('app.bsky.feed.post/')[-1]
                return f"https://bsky.app/profile/{author_handle}/post/{post_id}"
        except Exception:
            pass
        
        # Fallback to profile URL if we can't construct the post URL
        return f"https://bsky.app/profile/{author_handle}"

    def _analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment of text using TextBlob."""
        if not text or text.isspace():
            return {'polarity': 0.0, 'label': 'neutral'}
            
        # Clean text for sentiment analysis
        clean_text = self._clean_text_for_sentiment(text)
        
        blob = TextBlob(clean_text)
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

    def _clean_text_for_sentiment(self, text: str) -> str:
        """Clean post text for better sentiment analysis."""
        # Remove URLs
        text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
        
        # Remove mentions for sentiment (but keep the text)
        text = re.sub(r'@[\w.-]+', '', text)
        
        # Remove hashtags for sentiment (but keep the text)
        text = re.sub(r'#(\w+)', r'\1', text)
        
        # Clean up extra whitespace
        text = ' '.join(text.split())
        
        return text.strip()

    def _deduplicate_mentions(self, mentions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate mentions based on post ID."""
        seen_ids = set()
        unique_mentions = []
        
        for mention in mentions:
            post_id = mention.get('id', '')
            if post_id and post_id not in seen_ids:
                seen_ids.add(post_id)
                unique_mentions.append(mention)
        
        return unique_mentions

    def get_user_profile(self, handle: str) -> Optional[Dict[str, Any]]:
        """Get user profile information."""
        try:
            profile = self.client.app.bsky.actor.get_profile({'actor': handle})
            return profile.dict() if profile else None
        except Exception as e:
            logger.error(f"Error getting profile for {handle}: {e}")
            return None


def main():
    """Test the Bluesky monitor."""
    from dotenv import load_dotenv
    load_dotenv()
    
    # Test configuration
    try:
        monitor = BlueskyMonitor(
            username=os.getenv('BLUESKY_USERNAME', 'test'),
            password=os.getenv('BLUESKY_PASSWORD', 'test')
        )
        
        keywords = ['ansible', 'ansible automation platform', 'red hat ansible']
        
        mentions = monitor.search_mentions(keywords, hours_back=24, max_results=20)
        
        print(f"Found {len(mentions)} mentions:")
        for mention in mentions[:5]:  # Show first 5
            print(f"- @{mention['author']}: {mention['content'][:60]}... "
                  f"(Engagement: {mention['score']}, Sentiment: {mention['sentiment_label']})")
                  
    except Exception as e:
        print(f"Error testing Bluesky monitor: {e}")


if __name__ == "__main__":
    main()