# Sentiment Dashboard - AI-Powered Investment Intelligence

## 🎯 項目概述

一個基於 AI 的投資情緒分析儀表板，整合社交媒體熱點、新聞情緒和市場數據，幫助投資者發現潛在機會。

## 🏗️ 架構

```
sentiment-dashboard/
├── frontend/          # Stitch UI 前端
├── backend/           # FastAPI 後端
│   ├── agents/        # AI Agent 團隊 (Minimax)
│   ├── data_sources/  # 數據源集成
│   ├── core/          # 核心配置和異常
│   ├── utils/         # 工具類 (circuit breaker, cache, metrics)
│   └── api/           # API 路由
├── tests/             # 測試
└── docs/             # 文檔
```

## 🚀 核心功能

### 1. 情緒儀表盤
- 實時熱點話題監控
- 多維度情緒分析
- 投資機會識別
- 科技感 UI 界面

### 2. AI Agent 團隊
- **任務拆解與意圖理解** - 自動識別用戶查詢意圖
- **多 Agent 協作分析** - 專業分析師 Agent 協作
- **智能調研與建議** - 基於 Minimax API
- **關鍵詞情緒分析** - 無 API Key 時的備用方案

### 3. 數據源集成
- **NewsAPI** - 全球新聞熱點
- **Reddit JSON API** - 社交媒體情緒 (多 subreddit)
- **CoinGecko** - 加密貨幣數據

### 4. 可靠性保障
- **熔斷器模式 (Circuit Breaker)** - 防止級聯故障
- **連接池** - 高效的 HTTP 連接管理
- **智能緩存** - 減少重複請求
- **重試機制** - 指數退避策略
- **降級服務** - 數據源失敗時的備用方案

## 📊 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API 信息 |
| `/api/health` | GET | 服務健康檢查 |
| `/api/hot-topics` | GET | 獲取熱點話題 |
| `/api/sentiment/{topic}` | GET | 話題情緒分析 |
| `/api/sentiment/batch` | POST | 批量情緒分析 |
| `/api/opportunities` | GET | AI 識別投資機會 |
| `/api/agent/analyze` | POST | AI Agent 分析 |
| `/api/market/crypto` | GET | 加密貨幣數據 |
| `/api/aggregated` | GET | 聚合數據 |

## 🔧 技術棧

- **Frontend**: Stitch (科技感 UI)
- **Backend**: FastAPI + Python 3.10+
- **AI**: Minimax API (MiniMax-M2.5)
- **Data**: Real-time streaming + caching

## 📝 安裝

```bash
# 克隆項目
cd sentiment-dashboard

# 創建虛擬環境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安裝依賴
pip install -r requirements.txt

# 複製環境變量
cp .env.example .env
# 編輯 .env 添加你的 API Keys
```

## 🔐 環境變量

```env
# NewsAPI (可選)
NEWS_API_KEY=your_newsapi_key

# Minimax AI (可選，無 Key 時使用關鍵詞分析)
MINIMAX_API_KEY=your_minimax_key

# CoinGecko Pro (可選)
COINGECKO_API_KEY=your_coingecko_key
```

## 🧪 測試

```bash
# 運行所有測試
cd backend
pytest tests/ -v

# 運行特定測試
pytest tests/test_agents.py -v

# 運行帶覆蓋率的測試
pytest tests/ -v --cov=. --cov-report=html
```

## 🚀 運行

```bash
# 開發模式
cd backend
uvicorn main:app --reload

# 生產模式
uvicorn main:app --host 0.0.0.0 --port 8000
```

## 📈 新功能 (v1.1.0)

### AI Agent 增強
- ✅ 真正的 Minimax API 集成
- ✅ 智能任務拆解
- ✅ 回調響應緩存
- ✅ 多 Agent 協作

### 可靠性提升
- ✅ 完善的錯誤處理
- ✅ 降級服務 (Fallback)
- ✅ 數據聚合器
- ✅ 健康檢查端點

### API 擴展
- ✅ 批量情緒分析
- ✅ 聚合數據端點
- ✅ 快取統計
- ✅ 降級統計

## 🛡️ 錯誤處理

所有錯誤都會返回標準格式：

```json
{
  "error": "DataSourceError",
  "message": "Failed to fetch data",
  "source": "newsapi",
  "status_code": 500
}
```

## 📝 License

MIT
