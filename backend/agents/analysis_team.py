"""
AI Agent Analysis Team
基於 LangGraph + Minimax 的多 Agent 協作系統
"""

import json
from typing import List, Dict, Optional, Any
from datetime import datetime
import os
import asyncio

# Import for API calls
import aiohttp


class AnalysisTeam:
    """
    AI Agent 分析團隊
    包含多個專業 Agent，協作完成複雜分析任務
    
    Features:
    - Real Minimax API integration
    - Task decomposition and intent understanding
    - Multi-agent collaboration
    - Intelligent caching
    """
    
    def __init__(
        self,
        api_key: str = None,
        model: str = "MiniMax-M2.5"
    ):
        self.api_key = api_key or os.getenv("MINIMAX_API_KEY", "")
        self.model = model
        self.base_url = "https://api.minimaxi.chat/v1/text/chatcompletion_v2"
        
        # Cache for AI responses
        self._cache: Dict[str, tuple] = {}
        self._cache_ttl = 300  # 5 minutes
        
        # Agent configurations
        self.agents = {
            "sentiment_analyst": {
                "role": "Sentiment Analyst",
                "description": "分析文本情感傾向，識別市場情緒",
                "system_prompt": """你是一個專業的金融情緒分析師。你的任務是分析文本中表達的情緒，並給出-1到1之間的情緒分數。
                    - 正分數表示積極/看漲情緒
                    - 負分數表示消極/看跌情緒
                    - 接近0表示中性
                    
                    請用JSON格式返回分析結果：
                    {"sentiment": <float>, "sentiment_label": "<Bullish/Bearish/Neutral>", "keywords": [<list of sentiment keywords>], "reasoning": "<brief explanation>"}"""
            },
            "topic_extractor": {
                "role": "Topic Extractor",
                "description": "提取關鍵主題和趨勢",
                "system_prompt": """你是一個專業的主題分析師。你的任務是從文本中提取關鍵主題和趨勢。
                    識別的主題類別包括：AI、Crypto、Energy、Tech、Finance、China、EV、Semiconductor、Healthcare、Real Estate、E-commerce、Gaming。
                    
                    請用JSON格式返回：
                    {"topics": [<list of topics>], "trending_keywords": [<list of keywords>], "sectors_affected": [<related sectors>]}"""
            },
            "opportunity_finder": {
                "role": "Opportunity Finder",
                "description": "識別投資機會和風險",
                "system_prompt": """你是一個專業的投資分析師。你的任務是識別潛在的投資機會和風險。
                    根據市場情緒和趨勢，評估是否應該關注某個標的。
                    
                    請用JSON格式返回：
                    {"opportunity_type": "<buy/watch/avoid>", "confidence": <0-100>, "reasoning": "<分析理由>", "risk_level": "<low/medium/high>", "time_horizon": "<short/medium/long>", "entry_points": [<suggested entry prices if any>], "red_flags": [<warnings if any>]}"""
            },
            "risk_assessor": {
                "role": "Risk Assessor",
                "description": "評估投資風險等級",
                "system_prompt": """你是一個專業的風險管理專家。你的任務是評估投資相關的風險等級。
                    
                    請用JSON格式返回：
                    {"risk_level": "<low/medium/high>", "risk_factors": [<list of risk factors>], "volatility_assessment": "<assessment>", "recommendation": "<advice>"}"""
            }
        }
    
    async def _call_minimax(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> Optional[str]:
        """
        Call Minimax API with proper error handling.
        
        Args:
            messages: List of message dictionaries
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text or None on error
        """
        if not self.api_key:
            return None
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    elif response.status == 401:
                        print("Minimax API: Invalid API key")
                        return None
                    elif response.status == 429:
                        print("Minimax API: Rate limited")
                        return None
                    else:
                        print(f"Minimax API: Error {response.status}")
                        return None
        except asyncio.TimeoutError:
            print("Minimax API: Request timeout")
            return None
        except Exception as e:
            print(f"Minimax API: {str(e)}")
            return None
    
    async def _get_cached_response(self, prompt: str) -> Optional[str]:
        """Get cached response if available and not expired."""
        cache_key = hash(prompt)
        
        if cache_key in self._cache:
            response, timestamp = self._cache[cache_key]
            if datetime.now().timestamp() - timestamp < self._cache_ttl:
                return response
        return None
    
    def _cache_response(self, prompt: str, response: str):
        """Cache an API response."""
        cache_key = hash(prompt)
        self._cache[cache_key] = (response, datetime.now().timestamp())
    
    async def analyze_sentiment(self, topics: List[Dict]) -> List[Dict]:
        """
        對熱點話題進行情緒分析
        
        Args:
            topics: List of topic dictionaries
            
        Returns:
            Analyzed topics with sentiment data
        """
        analyzed = []
        
        for topic in topics:
            title = topic.get("title", "")
            
            # Try AI-powered sentiment analysis
            if self.api_key and len(title) > 10:
                sentiment_data = await self._analyze_with_ai(title)
                if sentiment_data:
                    topic["sentiment"] = sentiment_data.get("sentiment", 0)
                    topic["sentiment_label"] = sentiment_data.get("sentiment_label", "Neutral")
                    topic["sentiment_keywords"] = sentiment_data.get("keywords", [])
                    topic["sentiment_reasoning"] = sentiment_data.get("reasoning", "")
                else:
                    # Fallback to keyword-based
                    sentiment_score = self._calculate_sentiment(title)
                    topic["sentiment"] = sentiment_score
                    topic["sentiment_label"] = self._get_sentiment_label(sentiment_score)
            else:
                # Keyword-based fallback
                sentiment_score = self._calculate_sentiment(title)
                topic["sentiment"] = sentiment_score
                topic["sentiment_label"] = self._get_sentiment_label(sentiment_score)
            
            topic["analyzed_at"] = datetime.now().isoformat()
            analyzed.append(topic)
        
        return analyzed
    
    async def _analyze_with_ai(self, text: str) -> Optional[Dict]:
        """Use AI to analyze sentiment."""
        # Check cache first
        cached = await self._get_cached_response(f"sentiment_{text}")
        if cached:
            try:
                return json.loads(cached)
            except:
                pass
        
        system_prompt = self.agents["sentiment_analyst"]["system_prompt"]
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"請分析以下文本的情緒：\n\n{text}"}
        ]
        
        response = await self._call_minimax(messages)
        
        if response:
            # Try to parse JSON from response
            try:
                # Find JSON in response
                start = response.find("{")
                end = response.rfind("}") + 1
                if start >= 0 and end > start:
                    json_str = response[start:end]
                    result = json.loads(json_str)
                    self._cache_response(f"sentiment_{text}", json_str)
                    return result
            except json.JSONDecodeError:
                pass
        
        return None
    
    async def analyze_topic_sentiment(self, topic: str) -> Dict:
        """
        深度分析特定話題的情緒
        
        Args:
            topic: Topic to analyze
            
        Returns:
            Detailed sentiment analysis
        """
        # Try AI analysis first
        if self.api_key:
            result = await self._deep_analyze_with_ai(topic)
            if result:
                return result
        
        # Fallback to basic analysis
        return {
            "topic": topic,
            "overall_sentiment": self._calculate_sentiment(topic),
            "bullish_percentage": 50,
            "bearish_percentage": 30,
            "neutral_percentage": 20,
            "trending_keywords": self._extract_keywords(topic),
            "analysis": "Basic keyword-based analysis.",
            "analyzed_at": datetime.now().isoformat()
        }
    
    async def _deep_analyze_with_ai(self, topic: str) -> Optional[Dict]:
        """Deep AI analysis for a topic."""
        cached = await self._get_cached_response(f"deep_{topic}")
        if cached:
            try:
                return json.loads(cached)
            except:
                pass
        
        system_prompt = """你是一個專業的金融分析師。請對給定的主題進行深度情緒分析。
            考慮以下方面：
            - 整體市場情緒（樂觀/悲觀/中性）
            - 看好百分比
            - 看跌百分比
            - 中立百分比
            - 趨勢關鍵詞
            - 詳細分析
            
            請用JSON格式返回完整分析。"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"請深度分析以下主題的情緒：{topic}\n\n請提供全面的市場情緒分析，包括具體的百分比和關鍵詞。"}
        ]
        
        response = await self._call_minimax(messages, max_tokens=1500)
        
        if response:
            try:
                # Extract JSON
                start = response.find("{")
                end = response.rfind("}") + 1
                if start >= 0 and end > start:
                    json_str = response[start:end]
                    result = json.loads(json_str)
                    result["analyzed_at"] = datetime.now().isoformat()
                    result["topic"] = topic
                    self._cache_response(f"deep_{topic}", json_str)
                    return result
            except (json.JSONDecodeError, ValueError):
                pass
        
        return None
    
    async def identify_opportunities(
        self,
        topics: List[Dict],
        risk_level: str = "medium",
        time_horizon: str = "short"
    ) -> List[Dict]:
        """
        AI Agent 識別投資機會
        
        Args:
            topics: List of analyzed topics
            risk_level: Preferred risk level
            time_horizon: Investment time horizon
            
        Returns:
            List of identified opportunities
        """
        opportunities = []
        
        for topic in topics:
            tickers = topic.get("related_tickers", [])
            sentiment = topic.get("sentiment", 0)
            score = topic.get("score", topic.get("engagement_score", 0))
            
            for ticker in tickers:
                # Try AI opportunity analysis
                if self.api_key and sentiment != 0:
                    opp = await self._find_opportunity_with_ai(
                        ticker,
                        topic.get("title", ""),
                        sentiment,
                        risk_level,
                        time_horizon
                    )
                    if opp:
                        opportunities.append(opp)
                        continue
                
                # Fallback to rule-based
                if sentiment > 0.3 and score > 50:
                    opp = {
                        "ticker": ticker,
                        "opportunity_type": "watch" if sentiment > 0.5 else "consider",
                        "confidence": min(abs(sentiment) * 100 + 30, 95),
                        "reasoning": f"Positive sentiment ({sentiment:.2f}) with decent engagement ({score})",
                        "risk_level": risk_level,
                        "time_horizon": time_horizon,
                        "source_topic": topic.get("title"),
                        "identified_at": datetime.now().isoformat()
                    }
                    opportunities.append(opp)
        
        # Remove duplicates and sort
        seen = set()
        unique_opps = []
        for opp in opportunities:
            if opp["ticker"] not in seen:
                seen.add(opp["ticker"])
                unique_opps.append(opp)
        
        unique_opps.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        return unique_opps[:10]
    
    async def _find_opportunity_with_ai(
        self,
        ticker: str,
        title: str,
        sentiment: float,
        risk_level: str,
        time_horizon: str
    ) -> Optional[Dict]:
        """Find opportunities using AI."""
        cache_key = f"opp_{ticker}_{title[:20]}"
        cached = await self._get_cached_response(cache_key)
        if cached:
            try:
                result = json.loads(cached)
                result["source_topic"] = title
                result["identified_at"] = datetime.now().isoformat()
                return result
            except:
                pass
        
        system_prompt = self.agents["opportunity_finder"]["system_prompt"]
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"""請分析以下投資機會：

標的: {ticker}
相關新聞/討論: {title}
當前情緒分數: {sentiment}
風險偏好: {risk_level}
投資期限: {time_horizon}

請根據市場情緒和趨勢，評估這個標的是否是一個值得關注的機會。"""}
        ]
        
        response = await self._call_minimax(messages, max_tokens=800)
        
        if response:
            try:
                start = response.find("{")
                end = response.rfind("}") + 1
                if start >= 0 and end > start:
                    json_str = response[start:end]
                    result = json.loads(json_str)
                    result["ticker"] = ticker
                    result["source_topic"] = title
                    result["identified_at"] = datetime.now().isoformat()
                    self._cache_response(cache_key, json_str)
                    return result
            except (json.JSONDecodeError, ValueError):
                pass
        
        return None
    
    async def process_user_query(self, query: str) -> Dict:
        """
        處理用戶查詢，拆解任務並協調 Agent 團隊
        
        Args:
            query: User query
            
        Returns:
            Analysis results with task decomposition
        """
        # Task decomposition
        tasks = self._decompose_query(query)
        
        results = {}
        
        for task_type, task_desc in tasks.items():
            if task_type == "sentiment":
                results[task_type] = await self.analyze_topic_sentiment(task_desc)
            elif task_type == "opportunity":
                # Need context for opportunity finding
                results[task_type] = {
                    "query": task_desc,
                    "status": "Please provide more context or use /api/opportunities endpoint",
                    "suggestion": "Try /api/opportunities for AI-identified opportunities"
                }
            elif task_type == "extraction":
                results[task_type] = {"topics": self._extract_topics_from_query(task_desc)}
            elif task_type == "analysis":
                results[task_type] = await self._general_analysis(task_desc)
        
        return {
            "original_query": query,
            "decomposed_tasks": tasks,
            "results": results,
            "summary": self._generate_summary(results),
            "processed_at": datetime.now().isoformat()
        }
    
    async def _general_analysis(self, query: str) -> Dict:
        """General AI analysis for user queries."""
        cached = await self._get_cached_response(f"gen_{query[:50]}")
        if cached:
            try:
                return json.loads(cached)
            except:
                pass
        
        messages = [
            {"role": "system", "content": "你是一個專業的投資分析助手。請用中文回答用戶的問題，提供有價值的分析和見解。"},
            {"role": "user", "content": query}
        ]
        
        response = await self._call_minimax(messages, max_tokens=1500)
        
        if response:
            result = {"analysis": response, "type": "general"}
            try:
                self._cache_response(f"gen_{query[:50]}", json.dumps(result))
            except:
                pass
            return result
        
        return {"analysis": "抱歉，AI分析目前不可用。", "type": "error"}
    
    def _decompose_query(self, query: str) -> Dict[str, str]:
        """
        拆解用戶意圖為子任務
        
        Args:
            query: User query
            
        Returns:
            Dictionary of task types and descriptions
        """
        query_lower = query.lower()
        tasks = {}
        
        # Sentiment analysis task
        sentiment_keywords = ["sentiment", "mood", "feeling", "emotion", "情緒", "趨勢"]
        if any(word in query_lower for word in sentiment_keywords):
            # Extract the topic from query
            topic = query
            for kw in sentiment_keywords:
                topic = topic.lower().replace(kw, "").strip()
            tasks["sentiment"] = topic or query
        
        # Opportunity identification task
        opp_keywords = ["opportunity", "chance", "buy", "invest", "投資", "機會", "股票"]
        if any(word in query_lower for word in opp_keywords):
            tasks["opportunity"] = query
        
        # Topic extraction task
        topic_keywords = ["topic", "theme", "trend", "hot", "主題", "趨勢", "熱門"]
        if any(word in query_lower for word in topic_keywords):
            tasks["extraction"] = query
        
        # General analysis
        if not tasks:
            tasks["analysis"] = query
        
        return tasks
    
    def _calculate_sentiment(self, text: str) -> float:
        """
        計算文本情緒分數 (-1 到 1)
        
        Uses keyword-based analysis as fallback.
        
        Args:
            text: Text to analyze
            
        Returns:
            Sentiment score between -1 and 1
        """
        text_lower = text.lower()
        
        # Positive keywords
        positive_words = [
            "bull", "bullish", "buy", "moon", "rocket", "gain", "profit",
            "up", "rise", "surge", "jump", "rally", "boom", "growth",
            "strong", "beat", "breakout", "support", "long", "calls",
            "ath", "all time high", "pump", "winner", "profit", "gains",
            "upgrade", "outperform", "positive", "optimistic"
        ]
        
        # Negative keywords
        negative_words = [
            "bear", "bearish", "sell", "crash", "dump", "loss", "down",
            "fall", "drop", "decline", "weak", "miss", "fear", "panic",
            "resistance", "short", "puts", "bear market", "correction",
            "selloff", "loser", "failure", "downgrade", "underperform",
            "negative", "pessimistic", "risk", "warning"
        ]
        
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        total = positive_count + negative_count
        if total == 0:
            return 0.0
        
        return (positive_count - negative_count) / total
    
    def _get_sentiment_label(self, score: float) -> str:
        """
        Get sentiment label from score.
        
        Args:
            score: Sentiment score (-1 to 1)
            
        Returns:
            Sentiment label
        """
        if score > 0.3:
            return "Bullish"
        elif score < -0.3:
            return "Bearish"
        else:
            return "Neutral"
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract trending keywords from text."""
        # Simple keyword extraction
        keywords = []
        text_lower = text.lower()
        
        tech_keywords = ["ai", "tech", "software", "cloud", "semiconductor"]
        finance_keywords = ["fed", "rate", "inflation", "economy", "gdp"]
        crypto_keywords = ["crypto", "bitcoin", "eth", "blockchain", "defi"]
        
        for kw in tech_keywords + finance_keywords + crypto_keywords:
            if kw in text_lower:
                keywords.append(kw)
        
        return keywords[:5]
    
    def _extract_topics_from_query(self, query: str) -> List[str]:
        """Extract topics from query."""
        topics = []
        query_lower = query.lower()
        
        topic_map = {
            "AI": ["ai", "artificial intelligence", "chatgpt", "openai"],
            "Crypto": ["crypto", "bitcoin", "ethereum", "defi"],
            "Tech": ["tech", "technology", "software"],
            "Finance": ["fed", "inflation", "economy", "market"],
            "EV": ["tesla", "ev", "electric vehicle"],
            "Semiconductor": ["chip", "nvidia", "intel", "amd"]
        }
        
        for topic, keywords in topic_map.items():
            if any(kw in query_lower for kw in keywords):
                topics.append(topic)
        
        return topics or ["General"]
    
    def _generate_summary(self, results: Dict) -> str:
        """Generate analysis summary."""
        if not results:
            return "No analysis results available."
        
        # Try to summarize based on result types
        if "sentiment" in results:
            sent = results["sentiment"]
            if isinstance(sent, dict):
                label = sent.get("sentiment_label", "Neutral")
                return f"情緒分析完成。整體趨勢：{label}"
        
        if "opportunity" in results:
            return "投資機會分析完成。請查看詳細結果。"
        
        if "analysis" in results:
            return "分析完成。請查看詳細結果。"
        
        return "Analysis completed. See detailed results above."
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics."""
        return {
            "cache_size": len(self._cache),
            "cache_ttl": self._cache_ttl
        }
