"""
Twitter Monitoring Module for Ansible Mentions
Searches Twitter for mentions of Ansible and related keywords using Twitter API v2.
"""

import tweepy
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from textblob import TextBlob
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TwitterMonitor:
    def __init__(self, bearer_token: str, api_key: Optional[str] = None, 
                 api_secret: Optional[str] = None, access_token: Optional[str] = None,
                 access_token_secret: Optional[str] = None):
        """
        Initialize Twitter API connection.
        
        Args:
            bearer_token: Twitter API v2 Bearer Token (required)
            api_key: Twitter API v1.1 key (optional, for additional features)
            api_secret: Twitter API v1.1 secret (optional)
            access_token: Twitter API v1.1 access token (optional)
            access_token_secret: Twitter API v1.1 access token secret (optional)
        """
        try:
            # Initialize API v2 client (primary)
            self.client = tweepy.Client(
                bearer_token=bearer_token,
                consumer_key=api_key,
                consumer_secret=api_secret,
                access_token=access_token,
                access_token_secret=access_token_secret,
                wait_on_rate_limit=True
            )
            
            # Test the connection
            try:
                self.client.get_me()
                logger.info("Twitter API v2 connection established")
            except Exception:
                # If authenticated user info fails, we might only have bearer token
                logger.info("Twitter API v2 connection established (bearer token only)")
                
        except Exception as e:
            logger.error(f"Failed to connect to Twitter API: {e}")
            raise

    def search_mentions(self, keywords: List[str], hours_back: int = 24, 
                       max_results: int = 100) -> List[Dict[str, Any]]:
        """
        Search for mentions of keywords on Twitter.
        
        Args:
            keywords: List of keywords to search for
            hours_back: How many hours back to search
            max_results: Maximum number of tweets to retrieve
            
        Returns:
            List of mention dictionaries with metadata
        """
        mentions = []
        
        # Calculate time range
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours_back)
        
        # Build search query - Twitter API v2 syntax
        query_parts = []
        for keyword in keywords:
            # Use quotes for exact phrases, handle spaces
            if ' ' in keyword:
                query_parts.append(f'"{keyword}"')
            else:
                query_parts.append(keyword)
        
        # Combine with OR operator and exclude retweets
        query = f"({' OR '.join(query_parts)}) -is:retweet lang:en"
        
        logger.info(f"Searching Twitter with query: {query}")
        
        try:
            # Search tweets using Twitter API v2
            tweets = tweepy.Paginator(
                self.client.search_recent_tweets,
                query=query,
                max_results=min(max_results, 100),  # API limit per request
                start_time=start_time,
                end_time=end_time,
                tweet_fields=['created_at', 'author_id', 'public_metrics', 'context_annotations', 'lang'],
                user_fields=['username', 'name', 'verified', 'public_metrics'],
                expansions=['author_id']
            ).flatten(limit=max_results)
            
            # Process tweets
            users_map = {}
            tweet_list = list(tweets)
            
            # Create user lookup map if we have user data
            if hasattr(tweets, 'includes') and 'users' in tweets.includes:
                users_map = {user.id: user for user in tweets.includes['users']}
            
            for tweet in tweet_list:
                # Find which keyword matched
                matched_keyword = self._find_matching_keyword(tweet.text, keywords)
                if matched_keyword:
                    mention = self._extract_tweet_data(tweet, matched_keyword, users_map)
                    mentions.append(mention)
                    logger.info(f"Found mention: {tweet.text[:50]}...")
                    
        except Exception as e:
            logger.error(f"Error searching Twitter: {e}")
            
        return mentions

    def _find_matching_keyword(self, text: str, keywords: List[str]) -> Optional[str]:
        """Find which keyword appears in the tweet text."""
        text_lower = text.lower()
        for keyword in keywords:
            if keyword.lower() in text_lower:
                return keyword
        return None

    def _extract_tweet_data(self, tweet, keyword: str, users_map: Dict) -> Dict[str, Any]:
        """Extract relevant data from a tweet."""
        # Get user info if available
        user_info = users_map.get(tweet.author_id, {})
        username = getattr(user_info, 'username', f'user_{tweet.author_id}')
        display_name = getattr(user_info, 'name', username)
        verified = getattr(user_info, 'verified', False)
        
        # Analyze sentiment
        sentiment = self._analyze_sentiment(tweet.text)
        
        # Extract metrics
        metrics = tweet.public_metrics or {}
        
        return {
            'platform': 'twitter',
            'type': 'tweet',
            'id': tweet.id,
            'title': f"Tweet by @{username}",
            'content': tweet.text,
            'author': username,
            'author_display_name': display_name,
            'url': f"https://twitter.com/{username}/status/{tweet.id}",
            'score': metrics.get('like_count', 0) + metrics.get('retweet_count', 0),  # Combined engagement
            'num_comments': metrics.get('reply_count', 0),
            'created_utc': tweet.created_at.isoformat() if tweet.created_at else None,
            'keyword_matched': keyword,
            'sentiment_score': sentiment['polarity'],
            'sentiment_label': sentiment['label'],
            'raw_data': {
                'retweet_count': metrics.get('retweet_count', 0),
                'like_count': metrics.get('like_count', 0),
                'reply_count': metrics.get('reply_count', 0),
                'quote_count': metrics.get('quote_count', 0),
                'verified_user': verified,
                'language': tweet.lang,
                'context_annotations': getattr(tweet, 'context_annotations', [])
            }
        }

    def _analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment of text using TextBlob."""
        if not text or text.isspace():
            return {'polarity': 0.0, 'label': 'neutral'}
            
        # Clean text for sentiment analysis (remove URLs, mentions)
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
        """Clean tweet text for better sentiment analysis."""
        import re
        
        # Remove URLs
        text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
        
        # Remove mentions and hashtags for sentiment (but keep the text)
        text = re.sub(r'@\w+', '', text)
        text = re.sub(r'#(\w+)', r'\1', text)  # Keep hashtag text without #
        
        # Clean up extra whitespace
        text = ' '.join(text.split())
        
        return text.strip()

    def get_trending_hashtags(self, woeid: int = 1) -> List[Dict[str, Any]]:
        """
        Get trending hashtags. 
        Note: This requires Twitter API v1.1 with proper authentication.
        
        Args:
            woeid: Where On Earth ID (1 = Worldwide)
        """
        try:
            # This would require API v1.1 authentication
            # For now, return empty list as it requires additional setup
            logger.warning("Trending hashtags require Twitter API v1.1 authentication")
            return []
        except Exception as e:
            logger.error(f"Error getting trending hashtags: {e}")
            return []

    def search_user_mentions(self, username: str, hours_back: int = 24) -> List[Dict[str, Any]]:
        """Search for mentions of a specific user."""
        query = f"@{username} -is:retweet lang:en"
        return self.search_mentions([f"@{username}"], hours_back)


def main():
    """Test the Twitter monitor."""
    from dotenv import load_dotenv
    load_dotenv()
    
    # Test configuration
    monitor = TwitterMonitor(
        bearer_token=os.getenv('TWITTER_BEARER_TOKEN', 'test'),
        api_key=os.getenv('TWITTER_API_KEY'),
        api_secret=os.getenv('TWITTER_API_SECRET'),
        access_token=os.getenv('TWITTER_ACCESS_TOKEN'),
        access_token_secret=os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
    )
    
    keywords = ['ansible', 'ansible automation platform', 'red hat ansible']
    
    mentions = monitor.search_mentions(keywords, hours_back=24, max_results=20)
    
    print(f"Found {len(mentions)} mentions:")
    for mention in mentions[:5]:  # Show first 5
        print(f"- @{mention['author']}: {mention['content'][:60]}... (Engagement: {mention['score']}, Sentiment: {mention['sentiment_label']})")


if __name__ == "__main__":
    main()