"""
Reddit JSON API Client
無需認證，公開訪問
"""

import requests
import re
from typing import List, Dict
from datetime import datetime

class RedditClient:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
        self.subreddits = [
            "wallstreetbets",
            "investing",
            "stocks",
            "StockMarket",
            "CryptoCurrency",
            "Bitcoin"
        ]
    
    async def get_hot_posts(self, limit: int = 10) -> List[Dict]:
        """獲取多個 subreddit 的熱門帖子"""
        
        all_posts = []
        
        for subreddit in self.subreddits:
            try:
                url = f"https://www.reddit.com/r/{subreddit}/hot.json"
                params = {"limit": limit}
                
                response = requests.get(
                    url, 
                    headers=self.headers, 
                    params=params, 
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    posts = data.get("data", {}).get("children", [])
                    
                    for post in posts:
                        post_data = post.get("data", {})
                        
                        processed_post = {
                            "id": post_data.get("id"),
                            "title": post_data.get("title"),
                            "score": post_data.get("score", 0),
                            "comments": post_data.get("num_comments", 0),
                            "subreddit": subreddit,
                            "author": post_data.get("author"),
                            "url": f"https://reddit.com{post_data.get('permalink', '')}",
                            "created_at": datetime.fromtimestamp(
                                post_data.get("created_utc", 0)
                            ).isoformat(),
                            "topics": self._extract_topics(post_data.get("title", "")),
                            "related_tickers": self._extract_tickers(
                                post_data.get("title", "")
                            ),
                            "data_source": "reddit"
                        }
                        
                        all_posts.append(processed_post)
                        
            except Exception as e:
                print(f"Reddit Error for r/{subreddit}: {e}")
                continue
        
        # 按熱度排序
        all_posts.sort(key=lambda x: x["score"], reverse=True)
        return all_posts[:limit]
    
    async def get_subreddit_posts(self, subreddit: str, limit: int = 10) -> List[Dict]:
        """獲取特定 subreddit 的帖子"""
        
        try:
            url = f"https://www.reddit.com/r/{subreddit}/hot.json"
            params = {"limit": limit}
            
            response = requests.get(
                url, 
                headers=self.headers, 
                params=params, 
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                posts = data.get("data", {}).get("children", [])
                
                return [
                    {
                        "id": post["data"].get("id"),
                        "title": post["data"].get("title"),
                        "score": post["data"].get("score", 0),
                        "comments": post["data"].get("num_comments", 0),
                        "subreddit": subreddit,
                        "author": post["data"].get("author"),
                        "url": f"https://reddit.com{post['data'].get('permalink', '')}",
                        "topics": self._extract_topics(post["data"].get("title", "")),
                        "related_tickers": self._extract_tickers(
                            post["data"].get("title", "")
                        ),
                        "data_source": "reddit"
                    }
                    for post in posts
                ]
            else:
                return []
                
        except Exception as e:
            print(f"Reddit Error: {e}")
            return []
    
    def _extract_topics(self, title: str) -> List[str]:
        """提取話題主題"""
        
        title_lower = title.lower()
        topics = []
        
        topic_keywords = {
            "AI": ["ai", "artificial intelligence", "chatgpt", "machine learning"],
            "Crypto": ["crypto", "bitcoin", "btc", "ethereum", "eth"],
            "Energy": ["oil", "energy", "gas", "petroleum"],
            "EV": ["tesla", "ev", "electric vehicle"],
            "Tech": ["tech", "technology", "google", "apple", "microsoft"],
            "Finance": ["fed", "interest rate", "inflation", "cpi"],
            "Meme": ["meme", "yolo", "moon", "rocket"],
            "Earnings": ["earnings", "revenue", "profit", "quarterly"]
        }
        
        for topic, keywords in topic_keywords.items():
            if any(kw in title_lower for kw in keywords):
                topics.append(topic)
        
        return topics
    
    def _extract_tickers(self, title: str) -> List[str]:
        """提取股票代碼"""
        
        # $XXX 格式
        tickers = re.findall(r'\$([A-Z]{1,5})', title)
        
        # 常見公司名稱
        company_map = {
            "tesla": "TSLA", "apple": "AAPL", "amazon": "AMZN",
            "microsoft": "MSFT", "google": "GOOGL", "nvidia": "NVDA",
            "meta": "META", "netflix": "NFLX", "amd": "AMD",
            "intel": "INTC", "coinbase": "COIN"
        }
        
        title_lower = title.lower()
        for company, ticker in company_map.items():
            if company in title_lower and ticker not in tickers:
                tickers.append(ticker)
        
        return tickers
