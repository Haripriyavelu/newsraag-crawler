# crawler/models/article_models.py
"""
Article-specific data models.
"""
from dataclasses import dataclass
from typing import Optional, List
import hashlib
import re


@dataclass(frozen=True)
class ArticleContent:
    """Represents processed article content."""
    article_id: str
    title: str
    content: str
    summary: Optional[str] = None
    cleaned_content: Optional[str] = None
    extracted_entities: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    
    def __post_init__(self):
        """Validate content."""
        if not self.content.strip():
            raise ValueError("Article content cannot be empty")
    
    @property
    def content_hash(self) -> str:
        """Generate hash of content for deduplication."""
        content_for_hash = f"{self.title}{self.content}".lower()
        # Remove extra whitespace and normalize
        normalized = re.sub(r'\s+', ' ', content_for_hash).strip()
        return hashlib.sha256(normalized.encode()).hexdigest()


@dataclass
class ArticleStats:
    """Statistics for an article."""
    word_count: int = 0
    character_count: int = 0
    paragraph_count: int = 0
    has_images: bool = False
    has_tables: bool = False
    reading_time_minutes: int = 0
    
    @classmethod
    def from_content(cls, content: str) -> 'ArticleStats':
        """Calculate stats from content."""
        word_count = len(content.split())
        character_count = len(content)
        paragraph_count = content.count('\n\n') + 1
        reading_time = max(1, word_count // 200)  # Average reading speed
        
        return cls(
            word_count=word_count,
            character_count=character_count,
            paragraph_count=paragraph_count,
            has_images='<img' in content or '![' in content,
            has_tables='<table' in content or '|' in content,
            reading_time_minutes=reading_time
        )
