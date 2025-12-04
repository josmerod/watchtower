"""Pydantic models for health check and metrics API endpoints."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class HealthStatus(BaseModel):
    """Health check response model."""

    status: str = Field(..., description="System status: ok, degraded, or down")
    timestamp: datetime = Field(..., description="Health check timestamp")
    version: str = Field(default="1.0.0", description="Dashboard version")
    uptime_seconds: float | None = Field(None, description="Server uptime in seconds")
    details: dict[str, Any] = Field(default_factory=dict, description="Additional health details")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class ETLHealthMetrics(BaseModel):
    """Individual ETL health metrics."""

    etl_name: str = Field(..., description="ETL process name")
    last_run_time: datetime | None = Field(None, description="Last successful run time")
    success_rate: float | None = Field(None, description="Recent success rate percentage")
    error_count: int = Field(default=0, description="Recent error count")
    total_runs: int = Field(default=0, description="Total runs in analysis window")
    status: str = Field(default="unknown", description="ETL status: healthy, degraded, or failed")


class MetricsSummary(BaseModel):
    """Comprehensive metrics summary response model."""

    generated_at: datetime = Field(..., description="Metrics generation timestamp")
    total_sources: int = Field(..., description="Total number of ETL sources")
    total_items: int = Field(..., description="Total items across all sources")
    last_etl_run_times: dict[str, datetime | None] = Field(..., description="Last run times per ETL")
    error_rates_per_source: dict[str, float] = Field(..., description="Error rates per source")
    etl_health: list[ETLHealthMetrics] = Field(default_factory=list, description="Individual ETL health metrics")
    performance_metrics: dict[str, Any] = Field(default_factory=dict, description="Performance summary")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


class MetricsCacheEntry(BaseModel):
    """Cache entry for metrics responses."""

    data: dict[str, Any] = Field(..., description="Cached response data")
    timestamp: datetime = Field(..., description="Cache entry timestamp")
    ttl_minutes: int = Field(default=5, description="Time to live in minutes")

    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        from datetime import timedelta

        return datetime.utcnow() > (self.timestamp + timedelta(minutes=self.ttl_minutes))
