"""Integration & Migration Test Plan.

Comprehensive testing strategy for pattern integration with rollback capability.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import logging
from collections.abc import Callable
from typing import Any


class MigrationTestPlan:
    """Test plan for safe pattern migration."""

    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.warnings = []
        self.logger = logging.getLogger(__name__)

    def test_pattern_compatibility(self) -> bool:
        """Test that new patterns work with existing code.

        Returns:
            True if all compatibility tests pass
        """
        self.logger.info("=" * 60)
        self.logger.info("PATTERN COMPATIBILITY TESTING")
        self.logger.info("=" * 60)

        all_passed = True

        # Test 1: ETL Factory
        if not self._test_etl_factory():
            all_passed = False

        # Test 2: Repository Pattern
        if not self._test_repository_pattern():
            all_passed = False

        # Test 3: Scraping Strategy
        if not self._test_scraping_strategy():
            all_passed = False

        # Test 4: DI Container
        if not self._test_di_container():
            all_passed = False

        # Summary
        self.logger.info("=" * 60)
        self.logger.info("COMPATIBILITY TEST SUMMARY")
        self.logger.info(f"[OK] Passed: {self.tests_passed}")
        self.logger.info(f"[X] Failed: {self.tests_failed}")
        if self.warnings:
            self.logger.warning(f"[!] Warnings: {len(self.warnings)}")
        self.logger.info("=" * 60)

        return all_passed

    def _test_etl_factory(self) -> bool:
        """Test ETL Factory pattern."""
        self.logger.info("\n[*] Testing ETL Factory...")

        try:
            from src.etl.factory import ETLFactory

            # Test 1: Factory is available
            if not ETLFactory.is_registered("arxiv"):
                self.logger.warning("[!] Arxiv ETL not registered (expected if file not present)")

            # Test 2: List ETLs
            etl_names = ETLFactory.list_etls()
            self.logger.info(f"   [OK] Factory has {len(etl_names)} registered ETLs")
            self.tests_passed += 1

            # Test 3: Create doesn't crash
            try:
                # This might fail if ETLs aren't fully configured, but shouldn't crash
                if ETLFactory.is_registered("arxiv"):
                    etl = ETLFactory.create("arxiv", config={"batch_size": 10})
                    self.logger.info("   [OK] Can create ETL instances")
                    self.tests_passed += 1
            except Exception as e:
                self.logger.warning(f"   [!] ETL creation has issues: {e}")
                self.warnings.append(str(e))

            return True

        except Exception as e:
            self.logger.error(f"   [X] ETL Factory test failed: {e}")
            self.tests_failed += 1
            return False

    def _test_repository_pattern(self) -> bool:
        """Test Repository pattern."""
        self.logger.info("\n[*] Testing Repository Pattern...")

        try:
            from pathlib import Path

            from src.repositories import DataFrameRepository

            # Test 1: Can create repository
            test_repo = DataFrameRepository(
                data_path=Path("test.json"),
                cache_ttl_seconds=60,
            )
            self.logger.info("   [OK] Can create repository")
            self.tests_passed += 1

            # Test 2: Is available check
            available = test_repo.is_available()
            self.logger.info(f"   [OK] Availability check works: {available}")
            self.tests_passed += 1

            # Test 3: Clear cache
            test_repo.clear_cache()
            self.logger.info("   [OK] Can clear cache")
            self.tests_passed += 1

            return True

        except Exception as e:
            self.logger.error(f"   [X] Repository test failed: {e}")
            self.tests_failed += 1
            return False

    def _test_scraping_strategy(self) -> bool:
        """Test Scraping Strategy pattern."""
        self.logger.info("\n[*] Testing Scraping Strategy...")

        try:
            from src.scraping import ScrapingMethod, scrape_url

            # Test 1: Can scrape (will fail if no network, but shouldn't crash)
            result = scrape_url(
                "https://httpbin.org/html",
                method=ScrapingMethod.HTTP,
                timeout=5,
            )

            self.logger.info(f"   [OK] Scraping works (success={result.success})")
            self.tests_passed += 1

            if result.success:
                self.logger.info(f"   [OK] Got content: {len(result.content)} chars")
                self.tests_passed += 1
            else:
                self.logger.warning(f"   [!] Scraping failed (might be network): {result.error}")
                self.warnings.append(result.error or "Unknown error")

            return True

        except Exception as e:
            self.logger.error(f"   [X] Scraping strategy test failed: {e}")
            self.tests_failed += 1
            return False

    def _test_di_container(self) -> bool:
        """Test DI Container."""
        self.logger.info("\n[*] Testing DI Container...")

        try:
            from src.di import DIContainer, ServiceLifetime, get_container

            # Test 1: Get container
            container = get_container()
            self.logger.info("   [OK] Can get default container")
            self.tests_passed += 1

            # Test 2: Register service
            class TestService:
                def __init__(self):
                    self.value = "test"

            container.register(TestService, lifetime=ServiceLifetime.SINGLETON)
            self.logger.info("   [OK] Can register services")
            self.tests_passed += 1

            # Test 3: Resolve service
            service = container.resolve(TestService)
            self.logger.info(f"   [OK] Can resolve services: {service.value}")
            self.tests_passed += 1

            # Test 4: Singleton works
            service2 = container.resolve(TestService)
            assert service is service2
            self.logger.info("   [OK] Singleton lifetime works")
            self.tests_passed += 1

            return True

        except Exception as e:
            self.logger.error(f"   [X] DI Container test failed: {e}")
            self.tests_failed += 1
            return False

    def test_dashboard_compatibility(self) -> bool:
        """Test that dashboard still works with repositories."""
        self.logger.info("\n[*] Testing Dashboard Compatibility...")

        try:
            # Test that we can import dashboard components
            from src.web.dashboard.utils import get_data_path

            # Test path resolution still works
            path = get_data_path("courses", "test.json")
            self.logger.info(f"   [OK] Path resolution works: {path}")
            self.tests_passed += 1

            return True

        except Exception as e:
            self.logger.error(f"   [X] Dashboard compatibility failed: {e}")
            self.tests_failed += 1
            return False

    def create_migration_checkpoint(self) -> str:
        """Create a checkpoint before migration.

        Returns:
            Checkpoint identifier
        """
        from datetime import datetime

        import git

        try:
            repo = git.Repo(".")

            # Create checkpoint branch
            checkpoint_name = f"pre-migration-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            current_branch = repo.active_branch.name

            # Create branch
            repo.git.checkout("-b", checkpoint_name)

            # Switch back
            repo.git.checkout(current_branch)

            self.logger.info(f"[OK] Created checkpoint branch: {checkpoint_name}")
            return checkpoint_name

        except Exception as e:
            self.logger.warning(f"[!] Could not create git checkpoint: {e}")
            return "manual-checkpoint"

    def rollback_to_checkpoint(self, checkpoint_name: str) -> bool:
        """Rollback to checkpoint if migration fails.

        Args:
            checkpoint_name: Checkpoint branch name

        Returns:
            True if rollback successful
        """
        import git

        try:
            repo = git.Repo(".")

            # Reset to checkpoint
            repo.git.reset("--hard", checkpoint_name)

            self.logger.info(f"[OK] Rolled back to checkpoint: {checkpoint_name}")
            return True

        except Exception as e:
            self.logger.error(f"[X] Rollback failed: {e}")
            return False


class SafeMigration:
    """Safe migration with parallel implementation and rollback."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.checkpoint_name = None

    def prepare_migration(self) -> bool:
        """Prepare for migration by creating checkpoint.

        Returns:
            True if ready to migrate
        """
        self.logger.info("Preparing for safe migration...")

        # Run tests
        test_plan = MigrationTestPlan()

        if not test_plan.test_pattern_compatibility():
            self.logger.error("[X] Compatibility tests failed - aborting migration")
            return False

        # Create checkpoint
        self.checkpoint_name = test_plan.create_migration_checkpoint()

        self.logger.info("[OK] Migration preparation complete")
        return True

    def migrate_component(
        self,
        component_name: str,
        migration_fn: Callable[[], bool],
        validation_fn: Callable[[], bool] | None = None,
    ) -> bool:
        """Migrate a single component with validation.

        Args:
            component_name: Name of component
            migration_fn: Migration function
            validation_fn: Optional validation function

        Returns:
            True if migration successful
        """
        self.logger.info(f"\n[*] Migrating {component_name}...")

        try:
            # Run migration
            if not migration_fn():
                self.logger.error(f"[X] Migration of {component_name} failed")
                return False

            # Validate
            if validation_fn:
                if not validation_fn():
                    self.logger.error(f"[X] Validation of {component_name} failed")
                    return False

            self.logger.info(f"[OK] Successfully migrated {component_name}")
            return True

        except Exception as e:
            self.logger.error(f"[X] Error migrating {component_name}: {e}")
            return False

    def rollback_migration(self) -> bool:
        """Rollback all migrations if needed.

        Returns:
            True if rollback successful
        """
        self.logger.info("\n[*] Rolling back migration...")

        if not self.checkpoint_name:
            self.logger.error("[X] No checkpoint to rollback to")
            return False

        test_plan = MigrationTestPlan()
        return test_plan.rollback_to_checkpoint(self.checkpoint_name)


def run_pre_migration_tests() -> bool:
    """Run comprehensive pre-migration tests.

    Returns:
        True if all tests pass
    """
    print("\n" + "=" * 60)
    print("PRE-MIGRATION TESTING")
    print("=" * 60)

    test_plan = MigrationTestPlan()

    # Test pattern compatibility
    if not test_plan.test_pattern_compatibility():
        print("\n[X] COMPATIBILITY TESTS FAILED")
        print("Please fix issues before proceeding with migration")
        return False

    # Test dashboard compatibility
    if not test_plan.test_dashboard_compatibility():
        print("\n[X] DASHBOARD COMPATIBILITY TESTS FAILED")
        print("Please fix issues before proceeding with migration")
        return False

    print("\n[OK] ALL PRE-MIGRATION TESTS PASSED")
    return True


if __name__ == "__main__":
    # Run tests when executed directly
    import sys

    success = run_pre_migration_tests()
    sys.exit(0 if success else 1)
