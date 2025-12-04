#!/usr/bin/env python3
"""Watchtower Unified CLI Launcher

Command-line interface for easy deployment and management of the Watchtower platform.
Supports multiple execution modes and deployment strategies.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

try:
    from .main import ExecutionMode, WatchtowerLauncher
except ImportError:
    try:
        # Handle case when run as script from src/launcher directory
        from main import ExecutionMode, WatchtowerLauncher
    except ImportError:
        # Handle case when run from project root
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).parent))


class WatchtowerCLI:
    """Command-line interface for Watchtower platform."""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.launcher_script = self.project_root / "src" / "launcher" / "main.py"

    def run_development(self, args):
        """Run in development mode with hot reload."""
        print("Starting Watchtower in Development Mode")
        print("Hot reload enabled - changes will trigger automatic restarts")
        print("Dashboard: http://localhost:7777")
        print("Health monitoring: Active")
        print("=" * 60)

        env = os.environ.copy()
        env.update(
            {
                "WATCHTOWER_MODE": "development",
                "WATCHTOWER_ETL_INTERVAL": "1800",  # 30 minutes for dev
                "WATCHTOWER_HOT_RELOAD": "true",
                "WATCHTOWER_LOG_LEVEL": "DEBUG",
            }
        )

        self._run_launcher(env, args.background)

    def run_production(self, args):
        """Run in production mode."""
        print("Starting Watchtower in Production Mode")
        print("Optimized for stability and performance")
        print("Dashboard: http://localhost:7777")
        print("Health monitoring: Active")
        print("=" * 60)

        env = os.environ.copy()
        env.update(
            {
                "WATCHTOWER_MODE": "production",
                "WATCHTOWER_ETL_INTERVAL": "3600",  # 1 hour for production
                "WATCHTOWER_HOT_RELOAD": "false",
                "WATCHTOWER_LOG_LEVEL": "INFO",
            }
        )

        self._run_launcher(env, args.background)

    def run_etl_only(self, args):
        """Run ETL processes only."""
        print("Starting Watchtower ETL Only Mode")
        print("Running ETL processes without dashboard")
        print("Health monitoring: Active")
        print("=" * 60)

        env = os.environ.copy()
        env.update(
            {
                "WATCHTOWER_MODE": "etl_only",
                "WATCHTOWER_ETL_INTERVAL": str(args.interval or 3600),
                "WATCHTOWER_LOG_LEVEL": args.log_level or "INFO",
            }
        )

        self._run_launcher(env, args.background)

    def run_dashboard_only(self, args):
        """Run dashboard only."""
        print("Starting Watchtower Dashboard Only Mode")
        print("Dashboard: http://localhost:7777")
        print("Health monitoring: Active")
        print("=" * 60)

        env = os.environ.copy()
        env.update(
            {
                "WATCHTOWER_MODE": "dashboard_only",
                "WATCHTOWER_DASHBOARD_PORT": str(args.port or 7777),
                "WATCHTOWER_LOG_LEVEL": args.log_level or "INFO",
            }
        )

        self._run_launcher(env, args.background)

    def run_docker_dev(self, args):
        """Run using Docker Compose in development mode."""
        print("Starting Watchtower with Docker Compose (Development)")
        print("Building and running in containers")
        print("=" * 60)

        compose_file = self.project_root / "docker-compose.dev.yml"

        cmd = ["podman-compose", "-f", str(compose_file), "up"]
        if args.build:
            cmd.append("--build")

        try:
            subprocess.run(cmd, cwd=self.project_root, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Podman Compose failed: {e}")
            sys.exit(1)

    def run_docker_prod(self, args):
        """Run using Podman Compose in production mode."""
        print("Starting Watchtower with Podman Compose (Production)")
        print("Production container deployment")
        print("=" * 60)

        compose_file = self.project_root / "docker-compose.yml"

        cmd = ["podman-compose", "-f", str(compose_file), "up", "-d"]
        if args.build:
            cmd.insert(-1, "--build")

        try:
            subprocess.run(cmd, cwd=self.project_root, check=True)
            print("Production containers started successfully!")
            print("Dashboard available at: http://localhost:7777")
            print("Check status with: podman-compose logs -f")
        except subprocess.CalledProcessError as e:
            print(f"Podman Compose failed: {e}")
            sys.exit(1)

    def stop_docker(self, args):
        """Stop Podman containers."""
        print("Stopping Watchtower Podman containers...")

        compose_files = [
            self.project_root / "docker-compose.yml",
            self.project_root / "docker-compose.dev.yml",
        ]

        for compose_file in compose_files:
            if compose_file.exists():
                try:
                    subprocess.run(
                        ["podman-compose", "-f", str(compose_file), "down"],
                        cwd=self.project_root,
                        check=True,
                    )
                except subprocess.CalledProcessError:
                    pass  # Ignore errors if containers aren't running

        print("Docker containers stopped")

    def manage_service(self, args):
        """Manage system service."""
        print(f"Managing Watchtower service: {args.action}")

        service_script = self.project_root / "services" / "manage_service.py"

        if not service_script.exists():
            print("Service management script not found")
            sys.exit(1)

        cmd = [sys.executable, str(service_script), args.action]

        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Service management failed: {e}")
            sys.exit(1)

    def show_status(self, args):
        """Show current status."""
        print("Watchtower Status")
        print("=" * 40)

        # Check if processes are running
        try:
            import psutil

            watchtower_processes = []

            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    cmdline = proc.info.get("cmdline", [])
                    if cmdline and any("watchtower" in str(cmd).lower() for cmd in cmdline):
                        watchtower_processes.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            if watchtower_processes:
                print(f"Running processes: {len(watchtower_processes)}")
                for proc in watchtower_processes:
                    print(f"   PID {proc.info['pid']}: {' '.join(proc.info.get('cmdline', []))}")
            else:
                print("No Watchtower processes running")

        except ImportError:
            print("psutil not available for process monitoring")

        # Check Podman containers
        try:
            result = subprocess.run(
                ["podman-compose", "ps", "-q"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0 and result.stdout.strip():
                containers = result.stdout.strip().split("\n")
                print(f"Podman containers: {len(containers)} running")

                # Get container status
                status_result = subprocess.run(
                    ["podman-compose", "ps"],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                )

                if status_result.returncode == 0:
                    print(status_result.stdout)

            else:
                print("No Podman containers running")

        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Podman Compose not available")

        # Check data directory
        data_dir = self.project_root / "data"
        if data_dir.exists():
            total_files = sum(1 for _, _, files in os.walk(data_dir) for _ in files)
            print(f"Data files: {total_files}")
        else:
            print("Data directory not found")

        # Check logs
        logs_dir = self.project_root / "logs"
        if logs_dir.exists():
            log_files = list(logs_dir.glob("*.log"))
            print(f"Log files: {len(log_files)}")
        else:
            print("Logs directory not found")

    def _run_launcher(self, env: dict, background: bool = False):
        """Run the main launcher."""
        if not self.launcher_script.exists():
            print("Launcher script not found")
            sys.exit(1)

        cmd = [sys.executable, str(self.launcher_script)]

        try:
            if background:
                print("Running in background mode...")
                # Use nohup-like behavior for background execution
                subprocess.Popen(
                    cmd,
                    cwd=self.project_root,
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    preexec_fn=os.setsid if os.name != "nt" else None,
                )
                print("Watchtower started in background")
                print("Check logs for status: logs/launcher.log")
            else:
                subprocess.run(cmd, cwd=self.project_root, env=env, check=True)

        except subprocess.CalledProcessError as e:
            print(f"Launcher failed: {e}")
            sys.exit(1)
        except KeyboardInterrupt:
            print("\nShutdown requested by user")
            sys.exit(0)

    def setup_parser(self):
        """Setup command-line argument parser."""
        parser = argparse.ArgumentParser(
            description="Watchtower Intelligence Platform - Unified Launcher",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Development mode with hot reload
  python src/launcher/cli.py dev

  # Production mode
  python src/launcher/cli.py prod

  # ETL only mode
  python src/launcher/cli.py etl --interval 1800

  # Dashboard only mode
  python src/launcher/cli.py dashboard --port 8080

  # Podman development deployment
  python src/launcher/cli.py podman-dev --build

  # Production Podman deployment
  python src/launcher/cli.py podman-prod --build

  # Service management
  python src/launcher/cli.py service install
  python src/launcher/cli.py service start

  # Status check
  python src/launcher/cli.py status
            """,
        )

        subparsers = parser.add_subparsers(dest="command", help="Available commands")

        # Development mode
        dev_parser = subparsers.add_parser("dev", help="Development mode with hot reload")
        dev_parser.add_argument("--background", "-b", action="store_true", help="Run in background")
        dev_parser.set_defaults(func=self.run_development)

        # Production mode
        prod_parser = subparsers.add_parser("prod", help="Production mode")
        prod_parser.add_argument("--background", "-b", action="store_true", help="Run in background")
        prod_parser.set_defaults(func=self.run_production)

        # ETL only mode
        etl_parser = subparsers.add_parser("etl", help="ETL processes only")
        etl_parser.add_argument(
            "--interval",
            "-i",
            type=int,
            default=3600,
            help="ETL interval in seconds (default: 3600)",
        )
        etl_parser.add_argument("--background", "-b", action="store_true", help="Run in background")
        etl_parser.add_argument(
            "--log-level",
            "-l",
            choices=["DEBUG", "INFO", "WARNING", "ERROR"],
            default="INFO",
            help="Log level",
        )
        etl_parser.set_defaults(func=self.run_etl_only)

        # Dashboard only mode
        dashboard_parser = subparsers.add_parser("dashboard", help="Dashboard only")
        dashboard_parser.add_argument(
            "--port",
            "-p",
            type=int,
            default=7777,
            help="Dashboard port (default: 7777)",
        )
        dashboard_parser.add_argument("--background", "-b", action="store_true", help="Run in background")
        dashboard_parser.add_argument(
            "--log-level",
            "-l",
            choices=["DEBUG", "INFO", "WARNING", "ERROR"],
            default="INFO",
            help="Log level",
        )
        dashboard_parser.set_defaults(func=self.run_dashboard_only)

        # Podman development
        docker_dev_parser = subparsers.add_parser("podman-dev", help="Podman development mode")
        docker_dev_parser.add_argument("--build", action="store_true", help="Build images before starting")
        docker_dev_parser.set_defaults(func=self.run_docker_dev)

        # Podman production
        docker_prod_parser = subparsers.add_parser("podman-prod", help="Podman production mode")
        docker_prod_parser.add_argument("--build", action="store_true", help="Build images before starting")
        docker_prod_parser.set_defaults(func=self.run_docker_prod)

        # Podman stop
        docker_stop_parser = subparsers.add_parser("podman-stop", help="Stop Podman containers")
        docker_stop_parser.set_defaults(func=self.stop_docker)

        # Service management
        service_parser = subparsers.add_parser("service", help="System service management")
        service_parser.add_argument(
            "action",
            choices=["install", "uninstall", "start", "stop", "status"],
            help="Service action",
        )
        service_parser.set_defaults(func=self.manage_service)

        # Status check
        status_parser = subparsers.add_parser("status", help="Show current status")
        status_parser.set_defaults(func=self.show_status)

        return parser

    def run(self):
        """Main CLI entry point."""
        parser = self.setup_parser()
        args = parser.parse_args()

        if not hasattr(args, "func"):
            parser.print_help()
            return

        # Print header
        print("Watchtower Intelligence Platform")
        print("Real-time Data Collection & Monitoring")
        print("=" * 60)

        # Run the selected command
        try:
            args.func(args)
        except KeyboardInterrupt:
            print("\nOperation cancelled by user")
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)


def main():
    """Main entry point."""
    cli = WatchtowerCLI()
    cli.run()


if __name__ == "__main__":
    main()
