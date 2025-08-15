#!/usr/bin/env python3
"""
Ansible Mention Monitoring Bot
Main script that coordinates Reddit and Twitter monitoring for Ansible mentions.
"""

import os
import json
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv
import logging
import argparse

from reddit_monitor import RedditMonitor
from twitter_monitor import TwitterMonitor
from bluesky_monitor import BlueskyMonitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mention_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MentionBot:
    def __init__(self, config_file: str = '.env'):
        """Initialize the mention monitoring bot."""
        load_dotenv(config_file)
        
        # Load configuration
        self.product_name = os.getenv('PRODUCT_NAME', 'Ansible')
        self.keywords = [k.strip() for k in os.getenv('KEYWORDS', 'ansible').split(',')]
        self.subreddits = [s.strip() for s in os.getenv('SUBREDDITS', 'ansible,devops').split(',')]
        self.check_interval_hours = int(os.getenv('CHECK_INTERVAL_HOURS', '4'))
        
        # Initialize monitors
        self.reddit_monitor = None
        self.twitter_monitor = None
        self.bluesky_monitor = None
        
        self._setup_reddit_monitor()
        self._setup_twitter_monitor()
        self._setup_bluesky_monitor()
        
        logger.info(f"MentionBot initialized for {self.product_name}")
        logger.info(f"Keywords: {self.keywords}")
        logger.info(f"Subreddits: {self.subreddits}")

    def _setup_reddit_monitor(self):
        """Setup Reddit monitor if credentials are available."""
        reddit_client_id = os.getenv('REDDIT_CLIENT_ID')
        reddit_client_secret = os.getenv('REDDIT_CLIENT_SECRET')
        reddit_user_agent = os.getenv('REDDIT_USER_AGENT')
        
        if reddit_client_id and reddit_client_secret and reddit_user_agent:
            try:
                self.reddit_monitor = RedditMonitor(
                    client_id=reddit_client_id,
                    client_secret=reddit_client_secret,
                    user_agent=reddit_user_agent
                )
                logger.info("Reddit monitor initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Reddit monitor: {e}")
        else:
            logger.warning("Reddit credentials not found - Reddit monitoring disabled")

    def _setup_twitter_monitor(self):
        """Setup Twitter monitor if credentials are available."""
        twitter_bearer_token = os.getenv('TWITTER_BEARER_TOKEN')
        twitter_api_key = os.getenv('TWITTER_API_KEY')
        twitter_api_secret = os.getenv('TWITTER_API_SECRET')
        twitter_access_token = os.getenv('TWITTER_ACCESS_TOKEN')
        twitter_access_token_secret = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
        
        if twitter_bearer_token:
            try:
                self.twitter_monitor = TwitterMonitor(
                    bearer_token=twitter_bearer_token,
                    api_key=twitter_api_key,
                    api_secret=twitter_api_secret,
                    access_token=twitter_access_token,
                    access_token_secret=twitter_access_token_secret
                )
                logger.info("Twitter monitor initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Twitter monitor: {e}")
        else:
            logger.warning("Twitter credentials not found - Twitter monitoring disabled")

    def _setup_bluesky_monitor(self):
        """Setup Bluesky monitor if credentials are available."""
        bluesky_username = os.getenv('BLUESKY_USERNAME')
        bluesky_password = os.getenv('BLUESKY_PASSWORD')
        
        if bluesky_username and bluesky_password:
            try:
                self.bluesky_monitor = BlueskyMonitor(
                    username=bluesky_username,
                    password=bluesky_password
                )
                logger.info("Bluesky monitor initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Bluesky monitor: {e}")
        else:
            logger.warning("Bluesky credentials not found - Bluesky monitoring disabled")

    def collect_mentions(self, hours_back: int = None) -> List[Dict[str, Any]]:
        """Collect mentions from all available platforms."""
        if hours_back is None:
            hours_back = self.check_interval_hours
            
        all_mentions = []
        
        # Collect Reddit mentions
        if self.reddit_monitor:
            logger.info("Collecting Reddit mentions...")
            try:
                reddit_mentions = self.reddit_monitor.search_mentions(
                    keywords=self.keywords,
                    subreddits=self.subreddits,
                    hours_back=hours_back
                )
                all_mentions.extend(reddit_mentions)
                logger.info(f"Found {len(reddit_mentions)} Reddit mentions")
            except Exception as e:
                logger.error(f"Error collecting Reddit mentions: {e}")
        
        # Collect Twitter mentions
        if self.twitter_monitor:
            logger.info("Collecting Twitter mentions...")
            try:
                twitter_mentions = self.twitter_monitor.search_mentions(
                    keywords=self.keywords,
                    hours_back=hours_back,
                    max_results=100
                )
                all_mentions.extend(twitter_mentions)
                logger.info(f"Found {len(twitter_mentions)} Twitter mentions")
            except Exception as e:
                logger.error(f"Error collecting Twitter mentions: {e}")
        
        # Collect Bluesky mentions
        if self.bluesky_monitor:
            logger.info("Collecting Bluesky mentions...")
            try:
                bluesky_mentions = self.bluesky_monitor.search_mentions(
                    keywords=self.keywords,
                    hours_back=hours_back,
                    max_results=100
                )
                all_mentions.extend(bluesky_mentions)
                logger.info(f"Found {len(bluesky_mentions)} Bluesky mentions")
            except Exception as e:
                logger.error(f"Error collecting Bluesky mentions: {e}")
        
        logger.info(f"Total mentions collected: {len(all_mentions)}")
        return all_mentions

    def analyze_sentiment_summary(self, mentions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze overall sentiment distribution."""
        if not mentions:
            return {'total': 0, 'positive': 0, 'negative': 0, 'neutral': 0}
        
        sentiment_counts = {'positive': 0, 'negative': 0, 'neutral': 0}
        total_score = 0
        
        for mention in mentions:
            sentiment_label = mention.get('sentiment_label', 'neutral')
            sentiment_counts[sentiment_label] += 1
            total_score += mention.get('sentiment_score', 0)
        
        return {
            'total': len(mentions),
            'positive': sentiment_counts['positive'],
            'negative': sentiment_counts['negative'],
            'neutral': sentiment_counts['neutral'],
            'average_sentiment': total_score / len(mentions) if mentions else 0,
            'positive_percentage': (sentiment_counts['positive'] / len(mentions)) * 100,
            'negative_percentage': (sentiment_counts['negative'] / len(mentions)) * 100
        }

    def get_top_mentions(self, mentions: List[Dict[str, Any]], limit: int = 10) -> List[Dict[str, Any]]:
        """Get top mentions sorted by engagement/score."""
        return sorted(mentions, key=lambda x: x.get('score', 0), reverse=True)[:limit]

    def save_mentions(self, mentions: List[Dict[str, Any]], filename: str = None) -> str:
        """Save mentions to a file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"mentions_{timestamp}.json"
        
        # Save as JSON
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(mentions, f, indent=2, ensure_ascii=False, default=str)
        
        # Also save as CSV for easy viewing
        csv_filename = filename.replace('.json', '.csv')
        if mentions:
            df = pd.DataFrame(mentions)
            # Select key columns for CSV
            key_columns = ['platform', 'type', 'title', 'author', 'sentiment_label', 
                          'sentiment_score', 'score', 'created_utc', 'url']
            available_columns = [col for col in key_columns if col in df.columns]
            df[available_columns].to_csv(csv_filename, index=False)
        
        logger.info(f"Mentions saved to {filename} and {csv_filename}")
        return filename

    def generate_report(self, mentions: List[Dict[str, Any]]) -> str:
        """Generate a text report of findings."""
        if not mentions:
            return "No mentions found in the specified time period."
        
        sentiment_summary = self.analyze_sentiment_summary(mentions)
        top_mentions = self.get_top_mentions(mentions, 5)
        
        # Platform breakdown
        platform_counts = {}
        for mention in mentions:
            platform = mention['platform']
            platform_counts[platform] = platform_counts.get(platform, 0) + 1
        
        report = f"""
=== {self.product_name} Mention Report ===
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📊 SUMMARY:
Total Mentions: {sentiment_summary['total']}
Platforms: {', '.join(f"{k}: {v}" for k, v in platform_counts.items())}

😊 SENTIMENT ANALYSIS:
Positive: {sentiment_summary['positive']} ({sentiment_summary['positive_percentage']:.1f}%)
Negative: {sentiment_summary['negative']} ({sentiment_summary['negative_percentage']:.1f}%)
Neutral: {sentiment_summary['neutral']} ({100 - sentiment_summary['positive_percentage'] - sentiment_summary['negative_percentage']:.1f}%)
Average Sentiment Score: {sentiment_summary['average_sentiment']:.3f}

🔥 TOP MENTIONS (by engagement):
"""
        
        for i, mention in enumerate(top_mentions, 1):
            platform_emoji = {"reddit": "🔴", "twitter": "🐦", "bluesky": "☁️"}.get(mention['platform'], "📱")
            report += f"\n{i}. {platform_emoji} {mention['title'][:60]}..."
            report += f"\n   Author: {mention['author']} | Score: {mention['score']} | Sentiment: {mention['sentiment_label']}"
            report += f"\n   URL: {mention['url']}\n"
        
        return report

    def run_check(self, hours_back: int = None, save_results: bool = True) -> Dict[str, Any]:
        """Run a complete mention check."""
        logger.info("Starting mention check...")
        
        mentions = self.collect_mentions(hours_back)
        sentiment_summary = self.analyze_sentiment_summary(mentions)
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'mentions': mentions,
            'summary': sentiment_summary,
            'report': self.generate_report(mentions)
        }
        
        if save_results and mentions:
            filename = self.save_mentions(mentions)
            results['saved_file'] = filename
        
        # Print report
        print(results['report'])
        
        return results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Ansible Mention Monitoring Bot')
    parser.add_argument('--hours', type=int, default=None, 
                       help='Hours back to search (default: from config)')
    parser.add_argument('--no-save', action='store_true', 
                       help='Don\'t save results to file')
    parser.add_argument('--config', type=str, default='.env',
                       help='Configuration file path')
    
    args = parser.parse_args()
    
    try:
        bot = MentionBot(config_file=args.config)
        results = bot.run_check(
            hours_back=args.hours,
            save_results=not args.no_save
        )
        
        # Exit codes for automation
        if results['summary']['negative'] > results['summary']['positive']:
            logger.warning("More negative mentions than positive detected!")
            exit(1)
        else:
            exit(0)
            
    except Exception as e:
        logger.error(f"Bot execution failed: {e}")
        exit(2)


if __name__ == "__main__":
    main()