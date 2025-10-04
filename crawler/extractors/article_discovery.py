"""
Article discovery implementations following Open-Closed Principle.
"""

import asyncio
import aiohttp
import feedparser
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from abc import ABC, abstractmethod
from urllib.parse import urljoin

from ..interfaces.news_source_interface import IArticleDiscovery, ArticleMetadata


class BaseArticleDiscovery(IArticleDiscovery):
    """Base discovery with common functionality."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.base_url = config.get('url', '')

    @abstractmethod
    async def discover_articles(self, session: aiohttp.ClientSession, max_articles: int = 10) -> List[ArticleMetadata]:
        """Subclasses implement specific discovery logic."""
        pass


class RSSArticleDiscovery(BaseArticleDiscovery):
    """RSS feed discovery."""
    
    async def discover_articles(self, session: aiohttp.ClientSession, max_articles: int = 10) -> List[ArticleMetadata]:
        """Discover articles from RSS feed."""
        articles = []
        try:
            async with session.get(self.base_url) as response:
                if response.status != 200:
                    return []
                
                feed_content = await response.text()
                feed = feedparser.parse(feed_content)
                
                for entry in feed.entries[:max_articles]:
                    article = ArticleMetadata(
                        title=entry.get('title', 'No Title'),
                        url=entry.get('link', ''),
                        content='',  # Will be extracted later
                        published_date=entry.get('published_parsed'),
                        source_name=self.config.get('name', 'Unknown')
                    )
                    articles.append(article)
                    
        except Exception as e:
            print(f"RSS discovery failed: {e}")
        
        return articles


class HTMLArticleDiscovery(BaseArticleDiscovery):
    """HTML page discovery for sites without RSS."""
    
    async def discover_articles(self, session: aiohttp.ClientSession, max_articles: int = 10) -> List[ArticleMetadata]:
        """Discover articles by scraping HTML page."""
        articles = []
        try:
            async with session.get(self.base_url) as response:
                if response.status != 200:
                    return []
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Look for article links using common patterns
                link_selectors = ['a[href*="/news/"]', 'a[href*="/article/"]', '.headline a', 'h2 a, h3 a']
                
                found_urls = set()
                for selector in link_selectors:
                    links = soup.select(selector)[:max_articles]
                    for link in links:
                        href = link.get('href', '')
                        if href and href not in found_urls:
                            full_url = urljoin(self.base_url, href)
                            found_urls.add(href)
                            
                            article = ArticleMetadata(
                                title=link.get_text(strip=True) or 'No Title',
                                url=full_url,
                                content='',  # Will be extracted later
                                source_name=self.config.get('name', 'Unknown')
                            )
                            articles.append(article)
                            
                            if len(articles) >= max_articles:
                                break
                    
                    if len(articles) >= max_articles:
                        break
                        
        except Exception as e:
            print(f"HTML discovery failed: {e}")
        
        return articles


class YouTubeArticleDiscovery(BaseArticleDiscovery):
    """YouTube channel/playlist discovery."""
    
    async def discover_articles(self, session: aiohttp.ClientSession, max_articles: int = 10) -> List[ArticleMetadata]:
        """Discover YouTube videos - ready for API integration."""
        # Tomorrow someone can implement YouTube API here
        return []


class TwitterArticleDiscovery(BaseArticleDiscovery):
    """Twitter timeline discovery."""
    
    async def discover_articles(self, session: aiohttp.ClientSession, max_articles: int = 10) -> List[ArticleMetadata]:
        """Discover Twitter posts - ready for API integration."""
        # Tomorrow someone can implement Twitter API here
        return []


class RedditArticleDiscovery(BaseArticleDiscovery):
    """Reddit subreddit discovery."""
    
    async def discover_articles(self, session: aiohttp.ClientSession, max_articles: int = 10) -> List[ArticleMetadata]:
        """Discover Reddit posts - ready for API integration."""
        # Tomorrow someone can implement Reddit API here
        return []


# Registry for easy extension
DISCOVERY_REGISTRY = {
    'rss': RSSArticleDiscovery,
    'html_scraping': HTMLArticleDiscovery, 
    'youtube': YouTubeArticleDiscovery,
    'twitter': TwitterArticleDiscovery,
    'reddit': RedditArticleDiscovery,
}


def create_article_discovery(source_type: str, config: Dict[str, Any]) -> IArticleDiscovery:
    """Factory function - to add new discovery methods, just add to registry above."""
    discovery_class = DISCOVERY_REGISTRY.get(source_type, HTMLArticleDiscovery)
    return discovery_class(config)
