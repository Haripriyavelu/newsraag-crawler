# NewsRaag Crawler

**Advanced AI-Powered Financial News Aggregation & Vector Indexing System**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![Azure](https://img.shields.io/badge/Azure-OpenAI%20%7C%20Blob%20%7C%20Insights-blue.svg)](https://azure.microsoft.com)
[![Qdrant](https://img.shields.io/badge/Qdrant-Vector%20DB-green.svg)](https://qdrant.tech)
[![Tests](https://img.shields.io/badge/Tests-Pytest-orange.svg)](https://pytest.org)

A production-ready financial news crawler with AI-powered content cleaning, semantic vector indexing, and enterprise-grade monitoring. Processes multiple financial news sources through RSS and web scraping, cleans content with Azure OpenAI GPT-4, and stores in vector databases for semantic search.

## 🚀 Quick Start

```bash
# Clone and setup
git clone <your-repo-url>
cd newsraag-crawler

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers (for web scraping)
playwright install chromium --with-deps

# Configure environment
cp .env.example .env
# Edit .env with your Azure OpenAI, Qdrant, and storage credentials

# Test source configuration
python main.py --test-sources

# Run crawler
python main.py
```

## 📊 Architecture Overview

### **Enhanced Unified Source System**
The crawler uses a sophisticated factory pattern with multiple processing templates:

```
┌─────────────────────────────────────────────────────────────┐
│                    Source Factory                           │
├─────────────────────────────────────────────────────────────┤
│  RSS Sources        │  HTML Scraping     │  Hybrid Sources │
│  • BabyPips         │  • Kabutan         │  • MarketWatch  │
│  • FXStreet         │  • Custom Sites    │  • Future       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│               Hierarchical Processing Pipeline              │
├─────────────────────────────────────────────────────────────┤
│  1. Crawl4AI (Primary)  →  2. BeautifulSoup (Fallback)     │
│  3. RSS Parser (Final)  →  4. Content Extraction           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  AI Content Processing                      │
├─────────────────────────────────────────────────────────────┤
│  • Azure OpenAI GPT-4 Content Cleaning                     │
│  • Financial Data Preservation                             │
│  • Navigation/Ad Removal                                    │
│  • Text Embedding Generation (3072-dim)                    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Storage & Indexing                      │
├─────────────────────────────────────────────────────────────┤
│  • Qdrant Vector Database (Semantic Search)                │
│  • Azure Blob Storage (Document Archive)                   │
│  • Redis Cache (Optional Performance Layer)                │
└─────────────────────────────────────────────────────────────┘
```

## 🔧 Core Features

### **Intelligent Multi-Source Processing**
- ✅ **Unified Source Factory**: Supports RSS, HTML scraping, and hybrid sources
- ✅ **Hierarchical Extraction**: Crawl4AI → BeautifulSoup → RSS fallbacks
- ✅ **AI-Powered Content Cleaning**: Azure OpenAI GPT-4 removes boilerplate
- ✅ **Smart Duplicate Detection**: Semantic deduplication with title normalization
- ✅ **Multi-language Support**: Japanese content translation (Kabutan)

### **Production-Grade Storage**
- ✅ **Vector Database**: Qdrant with 3072-dimension embeddings for semantic search
- ✅ **Cloud Archive**: Azure Blob Storage with structured JSON documents
- ✅ **Intelligent Cleanup**: 24-hour document lifecycle management
- ✅ **Performance Caching**: Redis integration with in-memory fallback

### **Enterprise Monitoring & Alerting**
- ✅ **Azure Application Insights**: Cloud telemetry and performance tracking
- ✅ **Health Check API**: RESTful endpoints (`/health`, `/metrics`) 
- ✅ **Slack Integration**: Real-time failure notifications and alerts
- ✅ **Resource Monitoring**: Memory, CPU, and dependency health tracking
- ✅ **LLM Usage Analytics**: Token consumption tracking and cost management

### **Reliability & Performance**
- ✅ **Graceful Degradation**: Continues operation when optional services fail
- ✅ **Memory Management**: Automatic garbage collection and resource monitoring
- ✅ **Error Recovery**: Comprehensive retry mechanisms and fallback strategies
- ✅ **Concurrent Processing**: Async/await with rate limiting and timeout handling

## 📈 Supported Data Sources

| Source | Type | Content Focus | Rate Limit | Status |
|--------|------|---------------|------------|--------|
| **BabyPips** | RSS | Forex education & beginner analysis | 1s | ✅ Active |
| **FXStreet** | RSS | Professional forex market analysis | 1s | ✅ Active |
| **MarketWatch** | RSS | Market news and financial updates | 2s | ✅ Active |
| **Kabutan** | HTML | Japanese stock market analysis | 3s | ✅ Active |

*Additional sources easily configurable via `config/sources.yaml`*

## 🏗️ Project Structure

```
newsraag-crawler/
├── main.py                          # Enhanced main entry point
├── requirements.txt                 # Python dependencies
├── config/
│   └── sources.yaml                # Source configurations
├── crawler/                        # Core crawling system
│   ├── factories/                  # Source factory pattern
│   ├── templates/                  # Processing templates (RSS, HTML)
│   ├── extractors/                 # Content extraction engines
│   ├── utils/                     # Crawler utilities and helpers
│   └── validators/                # Data validation and cleanup
├── monitoring/                     # Comprehensive monitoring system
│   ├── metrics.py                 # Local metrics collection
│   ├── app_insights.py           # Azure telemetry integration
│   ├── health_check.py           # Health monitoring APIs
│   ├── alerts.py                 # Slack notification system
│   └── duplicate_detector.py     # Content deduplication
├── clients/                       # External service integrations
│   ├── qdrant_client.py          # Vector database operations
│   └── vector_client.py          # Embedding operations
├── utils/                         # General utilities
│   ├── llm/                      # AI content processing
│   └── config/                   # Configuration management
├── models/                        # Data models and schemas
├── tests/                        # Comprehensive test suite
│   ├── unit/                     # Unit tests
│   ├── integration/              # Integration tests
│   └── fixtures/                 # Test data and mocks
└── docs/                         # Documentation
```

## 🔄 Data Processing Pipeline

### **1. Article Discovery**
```python
# Multi-strategy article discovery
RSS Feed → Web Scraping → Content Extraction
    ↓           ↓              ↓
Duplicate   Link           Article
Detection   Validation     Metadata
```

### **2. Content Processing**
```python
# AI-powered content cleaning pipeline
Raw HTML → GPT-4 Cleaning → Financial Data Preservation
    ↓            ↓                    ↓
Navigation   Content            Structured
Removal      Sanitization       Document
```

### **3. Storage & Indexing**
```python
# Multi-tier storage strategy
Clean Content → Vector Embedding → Database Storage
     ↓               ↓                  ↓
Azure Blob      Qdrant Index      Search Ready
Storage         (Semantic)        Documents
```

## 📊 Monitoring Dashboard

### **Health Check Endpoints**
```bash
# System health status
curl http://localhost:8001/health

# Detailed performance metrics  
curl http://localhost:8001/metrics
```

### **Real-time Statistics**
```
📊 ENHANCED CRAWL CYCLE SUMMARY
=====================================
🎯 Overall Results:
   📈 Articles discovered: 85
   ✅ Articles processed: 72
   ❌ Articles failed: 8
   ⏭️ Articles skipped: 5
   🎯 Success rate: 84.7%
   📡 Sources: 4/4 active

📋 Per-Source Performance:
   📡 babypips: 18/20 (90% success)
   📡 fxstreet: 22/25 (88% success) 
   📡 marketwatch: 15/18 (83% success)
   📡 kabutan: 17/22 (77% success)
```

## ⚙️ Configuration

### **Environment Variables**
Essential configuration in `.env`:

```bash
# Azure OpenAI Services
OPENAI_BASE_URL=https://your-endpoint.openai.azure.com/
OPENAI_API_KEY=your_api_key
AZURE_OPENAI_DEPLOYMENT=gpt-4-1106-preview
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-large
EMBEDDING_DIMENSION=3072

# Vector Database
QDRANT_URL=https://your-qdrant-cluster.com
QDRANT_API_KEY=your_qdrant_api_key

# Azure Storage
AZ_ACCOUNT_NAME=your_storage_account
AZ_ACCOUNT_KEY=your_storage_key

# Monitoring (Optional)
APPINSIGHTS_INSTRUMENTATIONKEY=your_insights_key
ALERT_SLACK_WEBHOOK=your_slack_webhook_url
ALERT_SLACK_ENABLED=true

# Performance Settings
LLM_TOKEN_LIMIT_PER_REQUEST=4000
LLM_DAILY_TOKEN_LIMIT=1000000
```

### **Source Configuration**
Add new sources in `config/sources.yaml`:

```yaml
sources:
  - name: your_source
    type: rss  # or html_scraping
    url: https://example.com/feed.xml
    rate_limit: 2
    max_articles: 50
    content_type: forex
    # Optional HTML selectors
    selectors:
      title: ".article-title"
      content: ".article-body"
      link: "a.article-link"
```

## 🧪 Testing

### **Run Tests**
```bash
# All tests
python run_tests.py all

# Unit tests only
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# Test with coverage
pytest --cov=crawler --cov=monitoring --cov-report=html

# Test specific functionality
pytest tests/unit/test_source_routing.py -v
```

### **Test Source Configuration**
```bash
# Verify source creation
python main.py --test-sources

# List available source types
python main.py --list-sources

# Check RSS feed health
python diagnose_rss_feeds.py
```

## 🚀 Deployment

### **Local Development**
```bash
# Standard development run
python main.py

# Clear vector database (fresh start)
python main.py --clear-collection

# Recreate database schema
python main.py --recreate-collection
```

### **Production Deployment**
```bash
# Use startup script for process monitoring
chmod +x startup.sh
./startup.sh

# Or with systemd service
sudo systemctl start newsraag-crawler
sudo systemctl enable newsraag-crawler
```

### **Azure App Service**
```bash
# Environment detection
PORT=8000  # Automatically detected
WEBSITE_HOSTNAME=your-app.azurewebsites.net

# Health checks available at:
# https://your-app.azurewebsites.net/health
# https://your-app.azurewebsites.net/metrics
```

## 🔧 Development Tools

### **Command Line Options**
```bash
# Development and testing
python main.py --test-sources        # Test source creation
python main.py --list-sources        # List available sources
python main.py --clear-collection    # Clear vector database
python main.py --recreate-collection # Recreate database schema

# Migration and backup
python migrate_main.py               # Safely migrate to enhanced version
```

### **Diagnostic Tools**
```bash
# RSS feed health check
python diagnose_rss_feeds.py

# Memory and performance analysis
python test_fixes.py

# Health monitoring
python test_health_check.py

# LLM integration testing
python integration_example.py
```

## 📈 Performance Metrics

### **Resource Usage**
- **Memory Baseline**: ~115MB with automatic cleanup at 800MB+
- **Processing Speed**: ~1.4 seconds per article (including AI cleaning)
- **LLM Efficiency**: ~2,100 tokens per article cleanup
- **Storage Compression**: 50% size reduction through intelligent cleaning
- **Uptime**: Continuous operation with automatic error recovery

### **Throughput Capacity**
- **Articles per Hour**: 50-200 depending on source configuration
- **Daily Processing**: 1,200-4,800 articles with default settings
- **Token Usage**: ~2.5M tokens per day (with 1,200 articles)
- **Storage Growth**: ~500MB-2GB per month of archived content

## 🛠️ Troubleshooting

### **Common Issues**

**Issue**: Sources showing 0 articles discovered
```bash
# Check RSS feed health
python diagnose_rss_feeds.py

# Verify source configuration
python main.py --test-sources

# Check individual source logs
grep "Processing source" crawler.log
```

**Issue**: Memory usage warnings
```bash
# Normal for large batches - automatic cleanup
# Check memory monitoring logs:
grep "Memory usage" crawler.log

# Force garbage collection:
python -c "import gc; gc.collect()"
```

**Issue**: Vector database connection errors
```bash
# Check Qdrant connectivity
python -c "from clients.qdrant_client import get_qdrant_client; print('OK' if get_qdrant_client() else 'Failed')"

# Recreate collection if needed
python main.py --recreate-collection
```

### **Log Locations**
- **Application Logs**: Console output with structured JSON logging
- **Health Status**: Available via `http://localhost:8001/health`
- **Metrics Data**: `/data/metrics/` JSON files
- **Heartbeat**: `/data/heartbeat/crawler_heartbeat.txt`

### **Debug Mode**
```bash
# Enable verbose logging
export PYTHONPATH=$PYTHONPATH:$(pwd)
python main.py --verbose

# Test single cycle
python main.py --single-cycle  # (if implemented)
```

## 🔐 Security Features

- **Environment-based Configuration**: No hardcoded credentials
- **Content Sanitization**: AI-powered content cleaning removes malicious content
- **URL Validation**: Comprehensive URL validation and sanitization  
- **Rate Limiting**: Respectful crawling with configurable delays
- **Memory Limits**: Automatic resource monitoring and cleanup
- **Path Validation**: Secure file operations with path validation

## 📚 Advanced Features

### **AI Content Processing**
```python
# GPT-4 powered content cleaning
Content → Remove Navigation → Preserve Financial Data → Clean Output
         Remove Ads           Extract Key Info      Structure JSON
```

### **Vector Similarity Search**
```python
# Semantic article search and deduplication
Query → Embedding → Vector Search → Ranked Results
       (3072-dim)   (Qdrant)       (Similarity)
```

### **Intelligent Monitoring**
```python
# Multi-layer health monitoring
Application → Resource → Dependencies → Cloud
Health        Usage      (Qdrant/Azure)  (Insights)
```

## 🤝 Contributing

### **Development Setup**
```bash
# Fork and clone repository
git clone https://github.com/yourusername/newsraag-crawler.git

# Install development dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # If available

# Run tests before changes
python run_tests.py all

# Follow coding standards
black . && flake8 .
```

### **Adding New Sources**
1. Add source configuration to `config/sources.yaml`
2. Test with `python main.py --test-sources`
3. Create unit tests for new source types
4. Update documentation

### **Architecture Principles**
- **Factory Pattern**: Use `SourceFactory` for new source types
- **Template Method**: Extend existing templates for consistency
- **Graceful Degradation**: Always provide fallbacks for failures
- **Comprehensive Logging**: Log all operations with structured data

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **Azure OpenAI**: AI-powered content processing
- **Qdrant**: High-performance vector database
- **Crawl4AI**: Modern web scraping capabilities
- **Playwright**: Reliable browser automation
- **FastAPI**: Health check API framework

---

**Built for production financial news processing with enterprise-grade reliability, monitoring, and AI-powered quality enhancement.**
