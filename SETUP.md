# Setup Guide - Environment Variables

## 🔑 Required API Keys

### 1. NewsAPI (Required)
**Purpose**: Get global news headlines and hot topics

**How to get**:
1. Visit https://newsapi.org/register
2. Sign up with email
3. Get free API key (100 requests/day)
4. Copy key to `.env`:
   ```
   NEWS_API_KEY=your_actual_key_here
   ```

**Cost**: Free tier available

---

### 2. Minimax AI (Required for AI Agent)
**Purpose**: Power the AI Agent team for analysis

**How to get**:
1. Visit https://www.minimaxi.com/
2. Create account
3. Generate API key from dashboard
4. Copy key to `.env`:
   ```
   MINIMAX_API_KEY=your_actual_key_here
   ```

**Cost**: Free credits available for testing

---

## 🔧 Optional APIs

### 3. Reddit API (Optional but Recommended)
**Purpose**: Official Reddit API access (higher rate limits)

**How to get**:
1. Visit https://www.reddit.com/wiki/api
2. Click "register"
3. Fill application form
4. Wait for approval (1-7 days)
5. Create app at https://www.reddit.com/prefs/apps
6. Copy credentials to `.env`:
   ```
   REDDIT_CLIENT_ID=your_client_id
   REDDIT_CLIENT_SECRET=your_client_secret
   REDDIT_USERNAME=your_username
   REDDIT_PASSWORD=your_password
   ```

**Note**: If not provided, will use public JSON API (limited)

---

### 4. Alpaca Trading (Optional)
**Purpose**: Paper trading integration

**How to get**:
1. Visit https://alpaca.markets/
2. Sign up for paper trading account
3. Generate API keys from dashboard
4. Copy to `.env`:
   ```
   ALPACA_API_KEY=your_key
   ALPACA_SECRET_KEY=your_secret
   ```

---

### 5. Twitter/X API (Optional)
**Purpose**: Twitter sentiment analysis

**How to get**:
1. Visit https://developer.twitter.com/
2. Apply for developer account
3. Create project and app
4. Copy Bearer Token to `.env`:
   ```
   TWITTER_BEARER_TOKEN=your_token
   ```

**Note**: Free tier has limited requests (500/month)

---

## 🚀 Quick Start

### Step 1: Copy environment file
```bash
cp .env.example .env
```

### Step 2: Edit .env file
Fill in your actual API keys in the `.env` file

### Step 3: Install dependencies
```bash
cd backend
pip install -r requirements.txt
```

### Step 4: Run backend
```bash
python main.py
```

### Step 5: Open frontend
Open `frontend/index.html` in browser

---

## 📊 API Usage Limits

| API | Free Tier | Paid Tier |
|-----|-----------|-----------|
| NewsAPI | 100 req/day | $449/month unlimited |
| Minimax | Credits based | Pay per use |
| Reddit | 30 req/min | Varies |
| Alpaca | Unlimited (paper) | Real money trading |
| Twitter | 500 req/month | $100/month (Elevated) |

---

## 🔒 Security Notes

1. **Never commit `.env` file to GitHub**
   - It's already in `.gitignore`
   - Only commit `.env.example`

2. **Rotate API keys regularly**
   - Especially for production

3. **Use environment-specific keys**
   - Development vs Production

4. **Monitor API usage**
   - Set up alerts for unexpected spikes

---

## 🆘 Troubleshooting

### NewsAPI returns 401
- Check if API key is correct
- Verify key is activated (may need email confirmation)

### Reddit API 403
- Token may have expired
- Check rate limits
- Verify OAuth scopes

### Minimax API errors
- Check API key validity
- Verify credit balance
- Check model availability

---

## 📞 Support

For API-specific issues:
- NewsAPI: https://newsapi.org/docs
- Minimax: https://www.minimaxi.com/docs
- Reddit: https://www.reddit.com/dev/api/
- Alpaca: https://alpaca.markets/docs/
