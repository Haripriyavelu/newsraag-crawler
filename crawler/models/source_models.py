# crawler/models/source_models.py
"""
Data models for source configuration and processing results.
Following Domain-Driven Design principles.
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
from enum import Enum
import hashlib
import re


class ProcessingStatus(Enum):
    """Status of content processing."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class ContentMetrics:
    """Metrics for processed content."""
    original_length: int
    processed_length: int
    processing_time_seconds: float
    llm_tokens_used: int = 0
    extraction_method: str = ""
    
    @property
    def compression_ratio(self) -> float:
        """Calculate content compression ratio."""
        if self.original_length == 0:
            return 0.0
        return self.processed_length / self.original_length


@dataclass
class ProcessingJob:
    """Represents a content processing job."""
    job_id: str
    source_name: str
    article_metadata: 'ArticleMetadata'
    status: ProcessingStatus = ProcessingStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    def mark_started(self):
        """Mark job as started."""
        self.status = ProcessingStatus.IN_PROGRESS
        self.started_at = datetime.utcnow()
    
    def mark_completed(self, metrics: Optional[ContentMetrics] = None):
        """Mark job as completed."""
        self.status = ProcessingStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.metrics = metrics
    
    def mark_failed(self, error: str):
        """Mark job as failed."""
        self.status = ProcessingStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error_message = error
        self.retry_count += 1
    
    @property
    def can_retry(self) -> bool:
        """Check if job can be retried."""
        return self.retry_count < self.max_retries and self.status == ProcessingStatus.FAILED
    
    @property
    def processing_duration(self) -> Optional[timedelta]:
        """Get processing duration if completed."""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None


@dataclass
class SourceHealth:
    """Health status of a news source."""
    source_name: str
    is_healthy: bool = True
    last_check: datetime = field(default_factory=datetime.utcnow)
    last_successful_crawl: Optional[datetime] = None
    consecutive_failures: int = 0
    average_response_time: float = 0.0
    error_rate: float = 0.0
    total_articles_processed: int = 0
    
    def mark_success(self, response_time: float):
        """Mark successful operation."""
        self.is_healthy = True
        self.last_successful_crawl = datetime.utcnow()
        self.consecutive_failures = 0
        self.last_check = datetime.utcnow()
        # Update average response time (simple moving average)
        if self.average_response_time == 0:
            self.average_response_time = response_time
        else:
            self.average_response_time = (self.average_response_time + response_time) / 2
    
    def mark_failure(self, error: str):
        """Mark failed operation."""
        self.consecutive_failures += 1
        self.last_check = datetime.utcnow()
        # Mark as unhealthy after 3 consecutive failures
        if self.consecutive_failures >= 3:
            self.is_healthy = False
    
    @property
    def uptime_percentage(self) -> float:
        """Calculate uptime percentage (simplified)."""
        if self.total_articles_processed == 0:
            return 100.0
        success_rate = 100.0 - self.error_rate
        return max(0.0, min(100.0, success_rate))


@dataclass
class CrawlerConfig:
    """Global crawler configuration."""
    max_concurrent_sources: int = 5
    default_timeout_seconds: int = 30
    default_rate_limit: int = 1
    enable_llm_cleaning: bool = True
    enable_translation: bool = True
    max_content_length: int = 100000
    cleanup_interval_hours: int = 24
    monitoring_enabled: bool = True
    
    def validate(self) -> List[str]:
        """Validate configuration and return errors."""
        errors = []
        
        if self.max_concurrent_sources <= 0:
            errors.append("max_concurrent_sources must be positive")
        
        if self.default_timeout_seconds <= 0:
            errors.append("default_timeout_seconds must be positive")
        
        if self.max_content_length <= 0:
            errors.append("max_content_length must be positive")
            
        return errors


@dataclass
class TemplateConfig:
    """Configuration for source templates."""
    template_name: str
    template_version: str = "1.0"
    supported_source_types: List[str] = field(default_factory=list)
    required_config_fields: List[str] = field(default_factory=list)
    optional_config_fields: List[str] = field(default_factory=list)
    default_values: Dict[str, Any] = field(default_factory=dict)
    
    def is_compatible_with_source(self, source_type: str) -> bool:
        """Check if template is compatible with source type."""
        return source_type in self.supported_source_types
    
    def validate_source_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate source configuration against template requirements."""
        errors = []
        
        # Check required fields
        for field in self.required_config_fields:
            if field not in config:
                errors.append(f"Required field '{field}' is missing")
        
        return errors
