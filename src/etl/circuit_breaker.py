"""Circuit Breaker for ETL processes.

Prevents cascading failures by temporarily disabling ETLs that fail repeatedly.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from src.config.settings import get_settings

logger = logging.getLogger(__name__)


class CircuitBreakerState(BaseModel):
    """Persistent state for the circuit breaker."""
    
    etl_name: str
    failure_count: int = 0
    last_failure_time: datetime | None = None
    is_open: bool = False
    recovery_time: datetime | None = None
    total_trips: int = 0


class CircuitBreaker:
    """Manages the health state of an ETL process."""

    def __init__(
        self,
        etl_name: str,
        failure_threshold: int = 5,
        recovery_timeout_minutes: int = 30,
        base_path: Path | None = None,
    ):
        self.etl_name = etl_name
        self.failure_threshold = failure_threshold
        self.recovery_timeout_minutes = recovery_timeout_minutes
        
        settings = get_settings()
        base_path = base_path or (Path(settings.project_root) / "data" / etl_name)
        self.state_file = base_path / "circuit_breaker.json"
        
        # Ensure directory exists
        if not self.state_file.parent.exists():
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            
        self.state = self._load_state()

    def _load_state(self) -> CircuitBreakerState:
        """Load state from JSON file."""
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text(encoding="utf-8"))
                return CircuitBreakerState(**data)
            except Exception as e:
                logger.warning(f"Failed to load circuit breaker state for {self.etl_name}: {e}")
        
        return CircuitBreakerState(etl_name=self.etl_name)

    def _save_state(self) -> None:
        """Save state to JSON file."""
        try:
            self.state_file.write_text(
                self.state.model_dump_json(indent=2), 
                encoding="utf-8"
            )
        except Exception as e:
            logger.error(f"Failed to save circuit breaker state for {self.etl_name}: {e}")

    def can_proceed(self) -> bool:
        """Check if the ETL is allowed to run."""
        if not self.state.is_open:
            return True
            
        # Check if recovery time has passed
        if self.state.recovery_time and datetime.utcnow() >= self.state.recovery_time:
            logger.info(f"Circuit breaker for {self.etl_name} recovery time passed. Tentatively closing.")
            # Note: We don't fully close it yet; we allow one run to prove itself. 
            # But for simplicity in this implementation, we can just return True.
            # If it fails again, it will trip immediately if we don't reset count.
            # Strategy: Let it run. If it succeeds, record_success will reset.
            # If it fails, record_failure will update timestamp and keep it open.
            return True
            
        logger.warning(
            f"Circuit breaker for {self.etl_name} is OPEN. "
            f"Recovery at {self.state.recovery_time} (UTC)."
        )
        return False

    def record_success(self) -> None:
        """Record a successful run."""
        if self.state.failure_count > 0 or self.state.is_open:
            logger.info(f"Circuit breaker for {self.etl_name} reset after success.")
            self.state.failure_count = 0
            self.state.is_open = False
            self.state.recovery_time = None
            self.state.last_failure_time = None
            self._save_state()

    def record_failure(self) -> None:
        """Record a failed run."""
        self.state.failure_count += 1
        self.state.last_failure_time = datetime.utcnow()
        
        if self.state.failure_count >= self.failure_threshold:
            if not self.state.is_open:
                self.state.is_open = True
                self.state.total_trips += 1
                logger.error(
                    f"Circuit breaker for {self.etl_name} TRIPPED after {self.state.failure_count} failures."
                )
            
            # Extend recovery time (could be exponential, but fixed for now)
            self.state.recovery_time = datetime.utcnow() + timedelta(minutes=self.recovery_timeout_minutes)
            
        self._save_state()
