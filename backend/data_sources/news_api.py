"""
NewsAPI Client
獲取全球新聞熱點
"""

import requests
import asyncio
from typing import List, Dict
from datetime import datetime

class NewsAPIClient:
    def __init__(self, api_key: str = "949e672e9aae4589add2e409f5a2467a"):
        self.api_key = api_key
        self.base_url = "https://newsapi.org/v2"
        
    async def get_hot_topics(self, category: str = None, limit: int = 20) -> List[Dict]:
        """獲取熱點新聞話題"""
        
        url = f"{self.base_url}/top-headlines"
        params = {
            "language": "en",
            "pageSize": limit,
            "apiKey": self.api_key
        }
        
        if category:
            params["category"] = category
        
        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if data.get("status") == "ok":
                articles = data.get("articles", [])
                return self._process_articles(articles)
            else:
                return []
        except Exception as e:
            print(f"NewsAPI Error: {e}")
            return []
    
    async def search_news(self, query: str, limit: int = 10) -> List[Dict]:
        """搜索特定主題的新聞"""
        
        url = f"{self.base_url}/everything"
        params = {
            "q": query,
            "sortBy": "relevancy",
            "language": "en",
            "pageSize": limit,
            "apiKey": self.api_key
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if data.get("status") == "ok":
                articles = data.get("articles", [])
                return self._process_articles(articles)
            else:
                return []
        except Exception as e:
            print(f"NewsAPI Search Error: {e}")
            return []
    
    def _process_articles(self, articles: List[Dict]) -> List[Dict]:
        """處理新聞文章，提取投資相關信息"""
        
        processed = []
        
        for article in articles:
            title = article.get("title", "")
            description = article.get("description", "")
            content = f"{title} {description}".lower()
            
            # 提取投資主題
            topics = self._extract_topics(content)
            tickers = self._extract_tickers(title)
            
            processed.append({
                "id": f"news_{hash(title)}",
                "title": title,
                "description": description,
                "source": article.get("source", {}).get("name", "Unknown"),
                "url": article.get("url"),
                "published_at": article.get("publishedAt"),
                "topics": topics,
                "related_tickers": tickers,
                "data_source": "newsapi"
            })
        
        return processed
    
    def _extract_topics(self, content: str) -> List[str]:
        """提取投資主題"""
        
        topic_keywords = {
            "AI": ["ai", "artificial intelligence", "chatgpt", "machine learning"],
            "Crypto": ["crypto", "bitcoin", "btc", "ethereum", "eth", "blockchain"],
            "Energy": ["oil", "energy", "gas", "petroleum", "renewable"],
            "Tech": ["tech", "technology", "software", "cloud"],
            "Finance": ["fed", "interest rate", "inflation", "economy", "recession"],
            "China": ["china", "chinese", "beijing"],
            "EV": ["tesla", "ev", "electric vehicle", "battery"],
            "Semiconductor": ["chip", "semiconductor", "nvidia", "intel", "amd"]
        }
        
        found_topics = []
        for topic, keywords in topic_keywords.items():
            if any(kw in content for kw in keywords):
                found_topics.append(topic)
        
        return found_topics
    
    def _extract_tickers(self, title: str) -> List[str]:
        """提取股票代碼"""
        
        import re
        tickers = re.findall(r'\$([A-Z]{1,5})', title)
        
        # 常見公司名稱映射
        company_map = {
            "tesla": "TSLA",
            "apple": "AAPL",
            "amazon": "AMZN",
            "microsoft": "MSFT",
            "google": "GOOGL",
            "nvidia": "NVDA",
            "meta": "META",
            "netflix": "NFLX"
        }
        
        title_lower = title.lower()
        for company, ticker in company_map.items():
            if company in title_lower and ticker not in tickers:
                tickers.append(ticker)
        
        return tickers
