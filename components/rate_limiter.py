"""
Rate Limit Detection and Management

Detects API rate limit errors, tracks usage, and provides
graceful degradation with exponential backoff.
"""

import time
import re
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field


@dataclass
class RateLimitInfo:
    """Information about rate limit status"""
    is_limited: bool = False
    retry_after: Optional[float] = None  # Seconds to wait
    quota_limit: Optional[int] = None
    quota_used: Optional[int] = None
    quota_remaining: Optional[int] = None
    reset_time: Optional[datetime] = None
    provider: str = "unknown"


@dataclass
class UsageStats:
    """API usage statistics"""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rate_limit_hits: int = 0
    last_call_time: Optional[datetime] = None
    session_start: datetime = field(default_factory=datetime.now)
    
    def get_success_rate(self) -> float:
        """Get success rate as percentage"""
        if self.total_calls == 0:
            return 100.0
        return (self.successful_calls / self.total_calls) * 100
    
    def get_calls_per_minute(self) -> float:
        """Get average calls per minute"""
        elapsed = (datetime.now() - self.session_start).total_seconds() / 60
        if elapsed == 0:
            return 0.0
        return self.total_calls / elapsed


class RateLimiter:
    """
    Rate limit detection and management.
    
    Detects rate limit errors from various providers,
    tracks usage, and implements exponential backoff.
    """
    
    def __init__(self):
        """Initialize rate limiter"""
        self.stats = UsageStats()
        self.last_rate_limit: Optional[RateLimitInfo] = None
        self._backoff_multiplier = 1.0
    
    def detect_rate_limit(self, error_message: str, provider: str = "unknown") -> RateLimitInfo:
        """
        Detect if error is a rate limit error.
        
        Args:
            error_message: Error message from API
            provider: AI provider name
        
        Returns:
            RateLimitInfo with detected information
        """
        info = RateLimitInfo(provider=provider)
        
        error_lower = error_message.lower()
        
        # Common rate limit indicators
        rate_limit_keywords = [
            '429', 'rate limit', 'quota exceeded', 'too many requests',
            'retry after', 'rate_limit_exceeded', 'resource_exhausted'
        ]
        
        if any(keyword in error_lower for keyword in rate_limit_keywords):
            info.is_limited = True
            self.stats.rate_limit_hits += 1
            
            # Extract retry_after if present
            retry_match = re.search(r'retry.*?(\d+)\.?\d*\s*s', error_lower)
            if retry_match:
                info.retry_after = float(retry_match.group(1))
            
            # Extract quota information (Gemini format)
            quota_match = re.search(r'quota.*?(\d+)', error_message)
            if quota_match:
                info.quota_limit = int(quota_match.group(1))
            
            # Extract quota from violations block
            if 'quota_value:' in error_message:
                value_match = re.search(r'quota_value:\s*(\d+)', error_message)
                if value_match:
                    info.quota_limit = int(value_match.group(1))
            
            # Default retry after if not specified
            if info.retry_after is None:
                info.retry_after = 60.0  # Default 1 minute
            
            self.last_rate_limit = info
        
        return info
    
    def record_call(self, success: bool = True) -> None:
        """
        Record an API call.
        
        Args:
            success: Whether the call succeeded
        """
        self.stats.total_calls += 1
        self.stats.last_call_time = datetime.now()
        
        if success:
            self.stats.successful_calls += 1
            # Reduce backoff on success
            self._backoff_multiplier = max(1.0, self._backoff_multiplier * 0.5)
        else:
            self.stats.failed_calls += 1
            # Increase backoff on failure
            self._backoff_multiplier = min(8.0, self._backoff_multiplier * 2.0)
    
    def should_retry(self, attempt: int, max_attempts: int = 3) -> bool:
        """
        Check if should retry after rate limit.
        
        Args:
            attempt: Current attempt number
            max_attempts: Maximum attempts allowed
        
        Returns:
            True if should retry
        """
        return attempt < max_attempts
    
    def get_backoff_time(self, attempt: int) -> float:
        """
        Calculate exponential backoff time.
        
        Args:
            attempt: Current attempt number (0-based)
        
        Returns:
            Seconds to wait before retry
        """
        base_delay = 2.0  # Base delay in seconds
        max_delay = 300.0  # Max 5 minutes
        
        # Exponential backoff: 2^attempt * base_delay * multiplier
        delay = min(
            (2 ** attempt) * base_delay * self._backoff_multiplier,
            max_delay
        )
        
        return delay
    
    def get_stats_dict(self) -> Dict[str, Any]:
        """
        Get usage statistics as dictionary.
        
        Returns:
            Dictionary with stats
        """
        return {
            'total_calls': self.stats.total_calls,
            'successful_calls': self.stats.successful_calls,
            'failed_calls': self.stats.failed_calls,
            'rate_limit_hits': self.stats.rate_limit_hits,
            'success_rate': f"{self.stats.get_success_rate():.1f}%",
            'calls_per_minute': f"{self.stats.get_calls_per_minute():.1f}",
            'session_duration': str(datetime.now() - self.stats.session_start).split('.')[0],
            'last_rate_limit': {
                'provider': self.last_rate_limit.provider,
                'quota_limit': self.last_rate_limit.quota_limit,
                'retry_after': self.last_rate_limit.retry_after
            } if self.last_rate_limit else None
        }
    
    def estimate_quota_usage(self, provider: str) -> Dict[str, Any]:
        """
        Estimate quota usage based on provider.
        
        Args:
            provider: AI provider name
        
        Returns:
            Dictionary with quota estimates
        """
        # Provider-specific quota limits (free tier)
        quotas = {
            'Gemini 2.0 Flash (FREE)': {
                'daily_limit': 50,
                'hourly_limit': 50
            },
            'Groq (FREE & FAST)': {
                'daily_limit': 14400,
                'hourly_limit': 600
            },
            'OpenAI GPT-4': {
                'daily_limit': None,  # Token-based, not count-based
                'hourly_limit': None
            }
        }
        
        provider_quota = quotas.get(provider, {'daily_limit': None, 'hourly_limit': None})
        
        result = {
            'provider': provider,
            'total_calls': self.stats.total_calls,
            'daily_limit': provider_quota['daily_limit'],
            'hourly_limit': provider_quota['hourly_limit']
        }
        
        if provider_quota['daily_limit']:
            result['estimated_remaining'] = max(0, provider_quota['daily_limit'] - self.stats.total_calls)
            result['usage_percentage'] = min(100, (self.stats.total_calls / provider_quota['daily_limit']) * 100)
        
        return result
    
    def get_warning_level(self, provider: str) -> str:
        """
        Get warning level based on usage.
        
        Args:
            provider: AI provider name
        
        Returns:
            Warning level: 'safe', 'warning', 'critical', 'exceeded'
        """
        estimate = self.estimate_quota_usage(provider)
        
        if 'usage_percentage' not in estimate:
            return 'safe'
        
        usage = estimate['usage_percentage']
        
        if usage >= 100:
            return 'exceeded'
        elif usage >= 80:
            return 'critical'
        elif usage >= 50:
            return 'warning'
        else:
            return 'safe'


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """
    Get or create global rate limiter instance.
    
    Returns:
        Global RateLimiter instance
    """
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter

