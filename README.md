# Ansible Mention Monitoring Bot

A Python bot that monitors Reddit, Twitter, and Bluesky for mentions of Ansible and related products, providing sentiment analysis and engagement metrics.

## Features

- 🔍 **Multi-Platform Monitoring**: Reddit, Twitter, and Bluesky
- 📊 **Sentiment Analysis**: Automatic sentiment scoring using TextBlob
- 🎯 **Keyword Tracking**: Configurable keywords and subreddits
- 📈 **Engagement Metrics**: Track upvotes, likes, comments, and shares
- 💾 **Data Export**: Save results as JSON and CSV
- 📝 **Automated Reports**: Generate summary reports with top mentions
- ⚡ **Rate Limiting**: Built-in API rate limit handling

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/zy1125/ansible-mention-bot.git
   cd ansible-mention-bot
   ```

2. **Create virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up configuration**:
   ```bash
   cp .env.example .env
   # Edit .env with your API credentials
   ```

## API Setup

### Reddit API Setup

1. Go to [Reddit App Preferences](https://www.reddit.com/prefs/apps)
2. Click "Create App" or "Create Another App"
3. Choose "script" as the app type
4. Note down your `client_id` and `client_secret`
5. Add to `.env` file

### Twitter API Setup

1. Go to [Twitter Developer Portal](https://developer.twitter.com/)
2. Create a new app and get your Bearer Token
3. For additional features, also get API keys and access tokens
4. Add to `.env` file

### Bluesky API Setup

1. Create a Bluesky account at [bsky.app](https://bsky.app)
2. Generate an app password in your account settings
3. Use your handle (username) and app password for authentication
4. Add to `.env` file

## Configuration

Edit the `.env` file with your settings:

```bash
# Reddit API Configuration
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
REDDIT_USER_AGENT=ansible-mention-bot/1.0

# Twitter API Configuration
TWITTER_BEARER_TOKEN=your_twitter_bearer_token

# Bluesky API Configuration
BLUESKY_USERNAME=your_bluesky_username.bsky.social
BLUESKY_PASSWORD=your_bluesky_app_password

# Monitoring Configuration
PRODUCT_NAME=Ansible
KEYWORDS=ansible,ansible automation platform,red hat ansible,ansible tower,awx
SUBREDDITS=ansible,devops,sysadmin,automation,homelab,selfhosted,redhat
CHECK_INTERVAL_HOURS=4
```

## Usage

### Basic Usage

```bash
# Run a mention check for the last 24 hours
python mention_bot.py

# Check specific time range
python mention_bot.py --hours 12

# Don't save results to file
python mention_bot.py --no-save
```

### Test Individual Modules

```bash
# Test Reddit monitoring
python reddit_monitor.py

# Test Twitter monitoring  
python twitter_monitor.py

# Test Bluesky monitoring
python bluesky_monitor.py
```

## Output

The bot generates:

- **Console Report**: Summary with sentiment analysis and top mentions
- **JSON File**: Complete mention data with metadata
- **CSV File**: Simplified view for spreadsheet analysis
- **Log File**: Detailed execution logs

### Sample Report

```
=== Ansible Mention Report ===
Generated: 2025-08-15 10:30:00

📊 SUMMARY:
Total Mentions: 15
Platforms: reddit: 8, twitter: 5, bluesky: 2

😊 SENTIMENT ANALYSIS:
Positive: 8 (53.3%)
Negative: 2 (13.3%)
Neutral: 5 (33.3%)
Average Sentiment Score: 0.142

🔥 TOP MENTIONS (by engagement):
1. 🔴 Ansible automation is game-changing for our infrastructure...
   Author: devops_user | Score: 47 | Sentiment: positive
   URL: https://reddit.com/r/devops/comments/...

2. ☁️ Just discovered Ansible for my homelab setup...
   Author: bluesky_user | Score: 23 | Sentiment: positive
   URL: https://bsky.app/profile/user.bsky.social/post/...
```

## Automation

### GitHub Actions

Create `.github/workflows/mention-check.yml`:

```yaml
name: Mention Check
on:
  schedule:
    - cron: '0 */4 * * *'  # Every 4 hours
  workflow_dispatch:

jobs:
  check-mentions:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - run: pip install -r requirements.txt
      - run: python mention_bot.py
        env:
          REDDIT_CLIENT_ID: ${{ secrets.REDDIT_CLIENT_ID }}
          REDDIT_CLIENT_SECRET: ${{ secrets.REDDIT_CLIENT_SECRET }}
          TWITTER_BEARER_TOKEN: ${{ secrets.TWITTER_BEARER_TOKEN }}
          BLUESKY_USERNAME: ${{ secrets.BLUESKY_USERNAME }}
          BLUESKY_PASSWORD: ${{ secrets.BLUESKY_PASSWORD }}
```

### Cron Job

```bash
# Run every 4 hours
0 */4 * * * cd /path/to/ansible-mention-bot && /path/to/venv/bin/python mention_bot.py
```

## License

This project uses the following open-source libraries:
- **praw**: BSD License
- **tweepy**: MIT License
- **atproto**: MIT License
- **requests**: Apache 2.0
- **pandas**: BSD 3-Clause
- **textblob**: MIT License

See individual package licenses for full terms.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Support

For issues and questions:
- Create an issue on GitHub
- Check the logs in `mention_bot.log`
- Verify API credentials and rate limits

## Roadmap

- [ ] Slack/Discord notifications for negative mentions
- [ ] More sophisticated sentiment analysis (BERT/RoBERTa)
- [ ] Historical trend analysis
- [ ] Integration with more platforms (YouTube, HackerNews)
- [ ] Web dashboard for visualization
- [ ] Custom alerting rules