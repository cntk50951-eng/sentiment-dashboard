"""
AI Agent Analysis Team
基於 LangGraph + Minimax 的多 Agent 協作系統
"""

from typing import List, Dict, Optional
import json
from datetime import datetime
import os

class AnalysisTeam:
    """
    AI Agent 分析團隊
    包含多個專業 Agent，協作完成複雜分析任務
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("MINIMAX_API_KEY", "")
        self.base_url = "https://api.minimaxi.chat/v1/text/chatcompletion_v2"
        
        # Agent 配置
        self.agents = {
            "sentiment_analyst": {
                "role": "Sentiment Analyst",
                "description": "分析文本情感傾向，識別市場情緒",
                "model": "MiniMax-M1"
            },
            "topic_extractor": {
                "role": "Topic Extractor", 
                "description": "提取關鍵主題和趨勢",
                "model": "MiniMax-M1"
            },
            "opportunity_finder": {
                "role": "Opportunity Finder",
                "description": "識別投資機會和風險",
                "model": "MiniMax-M1"
            },
            "risk_assessor": {
                "role": "Risk Assessor",
                "description": "評估投資風險等級",
                "model": "MiniMax-M1"
            }
        }
    
    async def analyze_sentiment(self, topics: List[Dict]) -> List[Dict]:
        """
        對熱點話題進行情緒分析
        """
        analyzed = []
        
        for topic in topics:
            # 簡易情緒分析（實際應用中調用 Minimax API）
            sentiment_score = self._calculate_sentiment(topic.get("title", ""))
            
            topic["sentiment"] = sentiment_score
            topic["sentiment_label"] = self._get_sentiment_label(sentiment_score)
            topic["analyzed_at"] = datetime.now().isoformat()
            
            analyzed.append(topic)
        
        return analyzed
    
    async def analyze_topic_sentiment(self, topic: str) -> Dict:
        """
        深度分析特定話題的情緒
        """
        # 模擬 AI 分析結果
        return {
            "topic": topic,
            "overall_sentiment": 0.65,
            "bullish_percentage": 65,
            "bearish_percentage": 25,
            "neutral_percentage": 10,
            "trending_keywords": ["growth", "innovation", "bullish"],
            "analysis": f"Market sentiment for {topic} is predominantly positive.",
            "analyzed_at": datetime.now().isoformat()
        }
    
    async def identify_opportunities(
        self, 
        topics: List[Dict], 
        risk_level: str = "medium",
        time_horizon: str = "short"
    ) -> List[Dict]:
        """
        AI Agent 識別投資機會
        """
        opportunities = []
        
        for topic in topics:
            tickers = topic.get("related_tickers", [])
            sentiment = topic.get("sentiment", 0)
            
            for ticker in tickers:
                # 基於情緒和熱度判斷機會
                if sentiment > 0.5 and topic.get("score", 0) > 100:
                    opportunity = {
                        "ticker": ticker,
                        "opportunity_type": "watch",
                        "confidence": min(sentiment * 100, 95),
                        "reasoning": f"High positive sentiment ({sentiment:.2f}) and trending discussion",
                        "risk_level": risk_level,
                        "time_horizon": time_horizon,
                        "source_topic": topic.get("title"),
                        "identified_at": datetime.now().isoformat()
                    }
                    opportunities.append(opportunity)
        
        # 按信心度排序
        opportunities.sort(key=lambda x: x["confidence"], reverse=True)
        return opportunities[:10]
    
    async def process_user_query(self, query: str) -> Dict:
        """
        處理用戶查詢，拆解任務並協調 Agent 團隊
        """
        # 任務拆解
        tasks = self._decompose_query(query)
        
        results = {}
        for task_type, task_desc in tasks.items():
            if task_type == "sentiment":
                results[task_type] = await self.analyze_topic_sentiment(task_desc)
            elif task_type == "opportunity":
                results[task_type] = await self.identify_opportunities([{"title": task_desc}])
            elif task_type == "extraction":
                results[task_type] = {"topics": self._extract_topics_from_query(task_desc)}
        
        return {
            "original_query": query,
            "decomposed_tasks": tasks,
            "results": results,
            "summary": self._generate_summary(results),
            "processed_at": datetime.now().isoformat()
        }
    
    def _decompose_query(self, query: str) -> Dict:
        """
        拆解用戶意圖為子任務
        """
        query_lower = query.lower()
        tasks = {}
        
        # 情緒分析任務
        if any(word in query_lower for word in ["sentiment", "mood", "feeling", "emotion"]):
            tasks["sentiment"] = query
        
        # 機會識別任務
        if any(word in query_lower for word in ["opportunity", "chance", "buy", "invest"]):
            tasks["opportunity"] = query
        
        # 主題提取任務
        if any(word in query_lower for word in ["topic", "theme", "trend", "hot"]):
            tasks["extraction"] = query
        
        # 默認任務
        if not tasks:
            tasks["analysis"] = query
        
        return tasks
    
    def _calculate_sentiment(self, text: str) -> float:
        """
        計算文本情緒分數 (-1 到 1)
        """
        text_lower = text.lower()
        
        # 正面詞滙
        positive_words = [
            "bull", "buy", "moon", "rocket", "gain", "profit", "up", "rise",
            "surge", "jump", "rally", "boom", "growth", "strong", "beat"
        ]
        
        # 負面詞滙
        negative_words = [
            "bear", "sell", "crash", "dump", "loss", "down", "fall", "drop",
            "decline", "bearish", "weak", "miss", "fear", "panic"
        ]
        
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        total = positive_count + negative_count
        if total == 0:
            return 0.0
        
        return (positive_count - negative_count) / total
    
    def _get_sentiment_label(self, score: float) -> str:
        """獲取情緒標籤"""
        if score > 0.3:
            return "Bullish"
        elif score < -0.3:
            return "Bearish"
        else:
            return "Neutral"
    
    def _extract_topics_from_query(self, query: str) -> List[str]:
        """從查詢中提取主題"""
        # 簡易實現
        return ["AI", "Tech", "Market"]
    
    def _generate_summary(self, results: Dict) -> str:
        """生成分析摘要"""
        return "Analysis completed. See detailed results above."
