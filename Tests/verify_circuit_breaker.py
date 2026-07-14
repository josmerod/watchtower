"""Verification script for Circuit Breaker."""

import logging
import shutil
import time
from pathlib import Path

# Fix logging to show everything
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("VERIFY")

from src.etl.base import SimpleETL


class FailingETL(SimpleETL):
    def extract(self):
        raise ValueError("Simulated failure")


def cleanup(etl_name="test_circuit_breaker"):
    path = Path(f"data/{etl_name}")
    if path.exists():
        shutil.rmtree(path)


def test_circuit_breaker():
    etl_name = "test_circuit_breaker"
    cleanup(etl_name)

    logger.info("Initializing FailingETL with 0 retries and minimal delay")
    # Initialize with 0 retries to be fast
    etl = FailingETL(name=etl_name, max_retries=0, retry_delay=0)

    # Custom threshold
    etl.circuit_breaker.failure_threshold = 2

    logger.info("--- Run 1: Should fail, count -> 1 ---")
    try:
        etl.run()
    except Exception as e:
        logger.info(f"Caught expected error: {e}")

    cb = etl.circuit_breaker._load_state()
    logger.info(f"State after Run 1: {cb.model_dump()}")
    assert cb.failure_count == 1
    assert not cb.is_open

    logger.info("--- Run 2: Should fail, count -> 2 -> Trip ---")
    try:
        etl.run()
    except Exception as e:
        logger.info(f"Caught expected error: {e}")

    cb = etl.circuit_breaker._load_state()
    logger.info(f"State after Run 2: {cb.model_dump()}")
    assert cb.failure_count == 2
    assert cb.is_open

    logger.info("--- Run 3: Should stay open (Skip) ---")
    # Should NOT raise exception because it skips
    metrics = etl.run()

    logger.info(f"Metrics error count: {metrics.error_count}")
    logger.info(f"Metrics errors detail: {metrics.errors_detail}")

    assert metrics.records_extracted == 0, f"Expected 0 extracted, got {metrics.records_extracted}"
    assert metrics.error_count == 1, f"Expected error_count=1, got {metrics.error_count}"

    if metrics.errors_detail:
        error_type = metrics.errors_detail[0]["type"]
        assert error_type == "CircuitBreakerOpen", f"Expected CircuitBreakerOpen, got {error_type}"
    else:
        assert False, "No error details found"

    logger.info("Run 3 skipped as expected.")

    # Optional: Test Recovery
    # Manually reset recovery time to past
    logger.info("--- Testing Recovery ---")
    from datetime import datetime, timedelta

    etl.circuit_breaker.state.recovery_time = datetime.utcnow() - timedelta(minutes=1)
    etl.circuit_breaker._save_state()

    logger.info("--- Run 4: Should run (and fail again, but allowed to run) ---")
    try:
        etl.run()
    except Exception:
        logger.info("Caught expected error for Run 4")

    cb = etl.circuit_breaker._load_state()
    # It failed again, so count should increment to 3
    logger.info(f"State after Run 4: {cb.model_dump()}")
    assert cb.failure_count == 3
    assert cb.is_open  # Still open/tripped

    logger.info("--- Verification SUCCESS ---")
    cleanup(etl_name)


if __name__ == "__main__":
    test_circuit_breaker()
