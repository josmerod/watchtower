"""Comprehensive Monitoring Dashboard for Watchtower System
Leverages existing ETL metrics, watcher events, logs, and system health monitoring.
"""

import glob
import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.file_system import get_project_root
from utils.logging import get_logger

# Use centralized path setup and safe logger

logger = get_logger("MonitoringTab")


class MonitoringDataCollector:
    """Collects monitoring data from various sources in the Watchtower system."""

    def __init__(self):
        """Initialize the monitoring data collector."""
        self.project_root = Path(get_project_root())
        self.logs_dir = self.project_root / "logs"
        self.watchers_dir = self.project_root / "data" / "watchers"
        self.orchestrator_logs_dir = self.project_root / "src" / "orchestrator" / "logs"

    def get_etl_performance_metrics(self) -> dict[str, Any]:
        """Collect ETL performance metrics from logs."""
        try:
            etl_metrics = {
                "total_runs": 0,
                "successful_runs": 0,
                "failed_runs": 0,
                "average_duration": 0.0,
                "last_run_times": {},
                "performance_by_etl": {},
                "daily_stats": {},
                "error_patterns": {},
            }

            # Get all ETL log files from today and yesterday
            today = datetime.now().strftime("%Y-%m-%d")
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

            log_files = []
            for date in [today, yesterday]:
                pattern = str(self.logs_dir / f"*ETL_{date}.log")
                log_files.extend(glob.glob(pattern))

            for log_file in log_files:
                etl_name = os.path.basename(log_file).split("_")[0]

                try:
                    with open(log_file, encoding="utf-8") as f:
                        content = f.read()

                    # Extract metrics from log content
                    metrics = self._parse_etl_log(content, etl_name)

                    if etl_name not in etl_metrics["performance_by_etl"]:
                        etl_metrics["performance_by_etl"][etl_name] = {
                            "runs": 0,
                            "successes": 0,
                            "failures": 0,
                            "total_duration": 0.0,
                            "avg_duration": 0.0,
                            "last_run": None,
                            "records_processed": 0,
                            "errors": [],
                        }

                    etl_metrics["performance_by_etl"][etl_name].update(metrics)
                    etl_metrics["total_runs"] += metrics.get("runs", 0)
                    etl_metrics["successful_runs"] += metrics.get("successes", 0)
                    etl_metrics["failed_runs"] += metrics.get("failures", 0)

                except Exception as e:
                    logger.warning(f"Failed to parse ETL log {log_file}: {e}")

            # Calculate overall averages
            if etl_metrics["total_runs"] > 0:
                etl_metrics["success_rate"] = (
                    etl_metrics["successful_runs"] / etl_metrics["total_runs"]
                ) * 100
            else:
                etl_metrics["success_rate"] = 0.0

            return etl_metrics

        except Exception as e:
            logger.error(f"Failed to collect ETL metrics: {e}")
            return {"error": str(e)}

    def _parse_etl_log(self, content: str, etl_name: str) -> dict[str, Any]:
        """Parse ETL log content to extract metrics."""
        metrics = {
            "runs": 0,
            "successes": 0,
            "failures": 0,
            "total_duration": 0.0,
            "last_run": None,
            "records_processed": 0,
            "errors": [],
        }

        lines = content.split("\n")

        for line in lines:
            # Extract timestamps
            timestamp_match = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", line)
            if timestamp_match:
                try:
                    timestamp = datetime.strptime(
                        timestamp_match.group(1), "%Y-%m-%d %H:%M:%S"
                    )
                    if not metrics["last_run"] or timestamp > metrics["last_run"]:
                        metrics["last_run"] = timestamp
                except:
                    pass

            # Count successful completions
            if (
                "completed successfully" in line.lower()
                or "etl process completed" in line.lower()
            ):
                metrics["successes"] += 1
                metrics["runs"] += 1

            # Count failures
            elif "error" in line.lower() or "failed" in line.lower():
                metrics["failures"] += 1
                if (
                    "error" in line.lower() and len(metrics["errors"]) < 5
                ):  # Keep last 5 errors
                    metrics["errors"].append(line.strip())

            # Extract duration information
            duration_match = re.search(
                r"duration.*?(\d+\.?\d*)\s*seconds?", line.lower()
            )
            if duration_match:
                try:
                    duration = float(duration_match.group(1))
                    metrics["total_duration"] += duration
                except:
                    pass

            # Extract records processed
            records_match = re.search(
                r"(?:processed|extracted|loaded|transformed).*?(\d+).*?(?:records?|items?|articles?)",
                line.lower(),
            )
            if records_match:
                try:
                    records = int(records_match.group(1))
                    metrics["records_processed"] += records
                except:
                    pass

        # Calculate average duration
        if metrics["runs"] > 0:
            metrics["avg_duration"] = metrics["total_duration"] / metrics["runs"]

        return metrics

    def get_watcher_status(self) -> dict[str, Any]:
        """Collect watcher status and events."""
        try:
            watcher_status = {
                "active_watchers": 0,
                "total_events": 0,
                "recent_changes": [],
                "watcher_details": {},
                "health_status": "Unknown",
            }

            if not self.watchers_dir.exists():
                return watcher_status

            # Get all watcher directories
            for watcher_dir in self.watchers_dir.iterdir():
                if watcher_dir.is_dir() and watcher_dir.name != "debug":
                    watcher_name = watcher_dir.name

                    # Get watcher state
                    state_file = watcher_dir / "state.json"
                    events_dir = watcher_dir / "events"

                    watcher_info = {
                        "name": watcher_name,
                        "status": "Unknown",
                        "last_check": None,
                        "last_value": None,
                        "events_count": 0,
                        "recent_events": [],
                    }

                    # Read state file
                    if state_file.exists():
                        try:
                            with open(state_file) as f:
                                state_data = json.load(f)

                            watcher_info["last_check"] = state_data.get("last_check")
                            watcher_info["last_value"] = state_data.get("last_value")
                            watcher_info["status"] = "Active"
                            watcher_status["active_watchers"] += 1

                        except Exception as e:
                            logger.warning(
                                f"Failed to read state for watcher {watcher_name}: {e}"
                            )
                            watcher_info["status"] = "Error"

                    # Count events
                    if events_dir.exists():
                        event_files = list(events_dir.glob("*.json"))
                        watcher_info["events_count"] = len(event_files)
                        watcher_status["total_events"] += len(event_files)

                        # Get recent events
                        recent_events = sorted(
                            event_files, key=lambda x: x.stat().st_mtime, reverse=True
                        )[:3]
                        for event_file in recent_events:
                            try:
                                with open(event_file) as f:
                                    event_data = json.load(f)
                                watcher_info["recent_events"].append(event_data)

                                # Add to global recent changes
                                if event_data.get("type") == "change_detected":
                                    watcher_status["recent_changes"].append(
                                        {
                                            "watcher": watcher_name,
                                            "timestamp": event_data.get("timestamp"),
                                            "old_value": event_data.get("old_value"),
                                            "new_value": event_data.get("new_value"),
                                        }
                                    )
                            except Exception as e:
                                logger.warning(
                                    f"Failed to read event file {event_file}: {e}"
                                )

                    watcher_status["watcher_details"][watcher_name] = watcher_info

            # Determine overall health status
            if watcher_status["active_watchers"] > 0:
                watcher_status["health_status"] = "Healthy"
            elif watcher_status["active_watchers"] == 0:
                watcher_status["health_status"] = "No Active Watchers"
            else:
                watcher_status["health_status"] = "Degraded"

            return watcher_status

        except Exception as e:
            logger.error(f"Failed to collect watcher status: {e}")
            return {"error": str(e)}

    def get_system_health(self) -> dict[str, Any]:
        """Get overall system health metrics."""
        try:
            system_health = {
                "status": "Unknown",
                "data_freshness": {},
                "disk_usage": {},
                "recent_activity": [],
                "service_status": {},
            }

            # Check data freshness
            data_dir = self.project_root / "data"
            if data_dir.exists():
                for category_dir in data_dir.iterdir():
                    if category_dir.is_dir():
                        # Find latest files in each category
                        latest_files = []
                        for pattern in ["*latest*.json", "*.json", "*.csv"]:
                            latest_files.extend(category_dir.glob(pattern))

                        if latest_files:
                            latest_file = max(
                                latest_files, key=lambda x: x.stat().st_mtime
                            )
                            age_hours = (
                                datetime.now()
                                - datetime.fromtimestamp(latest_file.stat().st_mtime)
                            ).total_seconds() / 3600
                            system_health["data_freshness"][category_dir.name] = {
                                "age_hours": age_hours,
                                "status": "Fresh"
                                if age_hours < 24
                                else "Stale"
                                if age_hours < 72
                                else "Very Stale",
                            }

            # Check recent activity from main log
            main_log = self.logs_dir / "watchtower.log"
            if main_log.exists():
                try:
                    with open(main_log, encoding="utf-8") as f:
                        lines = f.readlines()

                    # Get last 20 lines for recent activity
                    recent_lines = lines[-20:] if len(lines) > 20 else lines
                    for line in recent_lines:
                        if line.strip():
                            system_health["recent_activity"].append(line.strip())

                except Exception as e:
                    logger.warning(f"Failed to read main log: {e}")

            # Determine overall status
            fresh_data_count = sum(
                1
                for info in system_health["data_freshness"].values()
                if info["status"] == "Fresh"
            )
            total_data_sources = len(system_health["data_freshness"])

            if total_data_sources == 0:
                system_health["status"] = "No Data"
            elif fresh_data_count / total_data_sources > 0.8:
                system_health["status"] = "Healthy"
            elif fresh_data_count / total_data_sources > 0.5:
                system_health["status"] = "Degraded"
            else:
                system_health["status"] = "Unhealthy"

            return system_health

        except Exception as e:
            logger.error(f"Failed to collect system health: {e}")
            return {"error": str(e)}

    def get_orchestrator_status(self) -> dict[str, Any]:
        """Get orchestrator status and logs."""
        try:
            orchestrator_status = {
                "active_orchestrators": 0,
                "recent_logs": [],
                "status": "Unknown",
            }

            if not self.orchestrator_logs_dir.exists():
                return orchestrator_status

            # Get recent orchestrator logs
            log_files = list(self.orchestrator_logs_dir.glob("*.log"))
            if log_files:
                # Get the most recent log file
                latest_log = max(log_files, key=lambda x: x.stat().st_mtime)

                try:
                    with open(latest_log, encoding="utf-8") as f:
                        lines = f.readlines()

                    # Get last 10 lines
                    recent_lines = lines[-10:] if len(lines) > 10 else lines
                    orchestrator_status["recent_logs"] = [
                        line.strip() for line in recent_lines if line.strip()
                    ]

                    # Check if orchestrators are active
                    for line in recent_lines:
                        if "started" in line.lower() and "orchestrator" in line.lower():
                            orchestrator_status["active_orchestrators"] += 1

                    orchestrator_status["status"] = (
                        "Active"
                        if orchestrator_status["active_orchestrators"] > 0
                        else "Inactive"
                    )

                except Exception as e:
                    logger.warning(f"Failed to read orchestrator log: {e}")
                    orchestrator_status["status"] = "Error"

            return orchestrator_status

        except Exception as e:
            logger.error(f"Failed to collect orchestrator status: {e}")
            return {"error": str(e)}


def display_system_overview(monitoring_data: dict[str, Any]):
    """Display system overview metrics."""
    st.subheader("🔍 System Overview")

    col1, col2, col3, col4 = st.columns(4)

    # ETL Metrics
    with col1:
        etl_data = monitoring_data.get("etl_metrics", {})
        if "error" not in etl_data:
            success_rate = etl_data.get("success_rate", 0)
            st.metric(
                "ETL Success Rate",
                f"{success_rate:.1f}%",
                delta=f"{etl_data.get('successful_runs', 0)} successful",
            )
        else:
            st.metric("ETL Success Rate", "Error", delta="Check logs")

    # Watcher Status
    with col2:
        watcher_data = monitoring_data.get("watcher_status", {})
        if "error" not in watcher_data:
            active_watchers = watcher_data.get("active_watchers", 0)
            total_events = watcher_data.get("total_events", 0)
            st.metric(
                "Active Watchers", active_watchers, delta=f"{total_events} total events"
            )
        else:
            st.metric("Active Watchers", "Error", delta="Check configuration")

    # System Health
    with col3:
        system_data = monitoring_data.get("system_health", {})
        if "error" not in system_data:
            status = system_data.get("status", "Unknown")
            fresh_sources = sum(
                1
                for info in system_data.get("data_freshness", {}).values()
                if info.get("status") == "Fresh"
            )
            st.metric(
                "System Health", status, delta=f"{fresh_sources} fresh data sources"
            )
        else:
            st.metric("System Health", "Error", delta="Check system")

    # Orchestrator Status
    with col4:
        orchestrator_data = monitoring_data.get("orchestrator_status", {})
        if "error" not in orchestrator_data:
            status = orchestrator_data.get("status", "Unknown")
            active_count = orchestrator_data.get("active_orchestrators", 0)
            st.metric("Orchestrators", status, delta=f"{active_count} active")
        else:
            st.metric("Orchestrators", "Error", delta="Check processes")


def display_etl_performance(etl_metrics: dict[str, Any]):
    """Display ETL performance dashboard."""
    st.subheader("⚙️ ETL Performance")

    if "error" in etl_metrics:
        st.error(f"❌ Failed to load ETL metrics: {etl_metrics['error']}")
        return

    # Performance overview
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Total ETL Runs",
            etl_metrics.get("total_runs", 0),
            delta=f"{etl_metrics.get('successful_runs', 0)} successful",
        )

    with col2:
        st.metric(
            "Failed Runs",
            etl_metrics.get("failed_runs", 0),
            delta=f"{etl_metrics.get('success_rate', 0):.1f}% success rate",
        )

    with col3:
        avg_duration = 0
        total_duration = 0
        total_runs = 0
        for etl_data in etl_metrics.get("performance_by_etl", {}).values():
            total_duration += etl_data.get("total_duration", 0)
            total_runs += etl_data.get("runs", 0)

        if total_runs > 0:
            avg_duration = total_duration / total_runs

        st.metric("Avg Duration", f"{avg_duration:.1f}s", delta="per ETL run")

    # ETL Performance by Process
    if etl_metrics.get("performance_by_etl"):
        st.subheader("📊 Performance by ETL Process")

        # Prepare data for charts
        etl_names = []
        success_rates = []
        avg_durations = []
        records_processed = []

        for etl_name, data in etl_metrics["performance_by_etl"].items():
            if data.get("runs", 0) > 0:
                etl_names.append(etl_name.replace("ETL", ""))
                success_rate = (data.get("successes", 0) / data.get("runs", 1)) * 100
                success_rates.append(success_rate)
                avg_durations.append(data.get("avg_duration", 0))
                records_processed.append(data.get("records_processed", 0))

        if etl_names:
            # Success rate chart
            col1, col2 = st.columns(2)

            with col1:
                fig_success = px.bar(
                    x=etl_names,
                    y=success_rates,
                    title="ETL Success Rates",
                    labels={"x": "ETL Process", "y": "Success Rate (%)"},
                    color=success_rates,
                    color_continuous_scale="RdYlGn",
                    range_color=[0, 100],
                )
                fig_success.update_layout(showlegend=False, height=400)
                st.plotly_chart(fig_success, use_container_width=True)

            with col2:
                fig_duration = px.bar(
                    x=etl_names,
                    y=avg_durations,
                    title="Average ETL Duration",
                    labels={"x": "ETL Process", "y": "Duration (seconds)"},
                    color=avg_durations,
                    color_continuous_scale="Viridis",
                )
                fig_duration.update_layout(showlegend=False, height=400)
                st.plotly_chart(fig_duration, use_container_width=True)

        # ETL Details Table
        st.subheader("📋 ETL Process Details")

        etl_details = []
        for etl_name, data in etl_metrics["performance_by_etl"].items():
            if data.get("runs", 0) > 0:
                etl_details.append(
                    {
                        "ETL Process": etl_name.replace("ETL", ""),
                        "Total Runs": data.get("runs", 0),
                        "Successes": data.get("successes", 0),
                        "Failures": data.get("failures", 0),
                        "Success Rate": f"{(data.get('successes', 0) / data.get('runs', 1)) * 100:.1f}%",
                        "Avg Duration": f"{data.get('avg_duration', 0):.1f}s",
                        "Records Processed": f"{data.get('records_processed', 0):,}",
                        "Last Run": data.get("last_run").strftime("%Y-%m-%d %H:%M")
                        if data.get("last_run")
                        else "Unknown",
                    }
                )

        if etl_details:
            df_etl = pd.DataFrame(etl_details)
            st.dataframe(df_etl, use_container_width=True)


def display_watcher_monitoring(watcher_status: dict[str, Any]):
    """Display watcher monitoring dashboard."""
    st.subheader("👁️ Watcher Monitoring")

    if "error" in watcher_status:
        st.error(f"❌ Failed to load watcher status: {watcher_status['error']}")
        return

    # Watcher overview
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Active Watchers",
            watcher_status.get("active_watchers", 0),
            delta=watcher_status.get("health_status", "Unknown"),
        )

    with col2:
        st.metric(
            "Total Events",
            watcher_status.get("total_events", 0),
            delta=f"{len(watcher_status.get('recent_changes', []))} recent changes",
        )

    with col3:
        health_status = watcher_status.get("health_status", "Unknown")
        health_color = (
            "🟢"
            if health_status == "Healthy"
            else "🟡"
            if health_status == "Degraded"
            else "🔴"
        )
        st.metric("Health Status", f"{health_color} {health_status}", delta="")

    # Watcher details
    if watcher_status.get("watcher_details"):
        st.subheader("📋 Watcher Details")

        watcher_data = []
        for watcher_name, details in watcher_status["watcher_details"].items():
            last_check = details.get("last_check")
            if last_check:
                try:
                    last_check_dt = datetime.fromisoformat(
                        last_check.replace("Z", "+00:00")
                    )
                    time_ago = datetime.now() - last_check_dt.replace(tzinfo=None)
                    time_ago_str = f"{time_ago.total_seconds() / 3600:.1f}h ago"
                except:
                    time_ago_str = "Unknown"
            else:
                time_ago_str = "Never"

            watcher_data.append(
                {
                    "Watcher": watcher_name.replace("_", " ").title(),
                    "Status": details.get("status", "Unknown"),
                    "Last Check": time_ago_str,
                    "Events": details.get("events_count", 0),
                    "Last Value": str(details.get("last_value", "Unknown"))[:50] + "..."
                    if details.get("last_value")
                    and len(str(details.get("last_value"))) > 50
                    else str(details.get("last_value", "Unknown")),
                }
            )

        if watcher_data:
            df_watchers = pd.DataFrame(watcher_data)
            st.dataframe(df_watchers, use_container_width=True)

    # Recent changes
    if watcher_status.get("recent_changes"):
        st.subheader("🔄 Recent Changes Detected")

        for change in watcher_status["recent_changes"][:5]:  # Show last 5 changes
            with st.expander(f"🔔 {change['watcher']} - {change['timestamp']}"):
                st.write(f"**Old Value:** {change['old_value']}")
                st.write(f"**New Value:** {change['new_value']}")
                st.write(f"**Timestamp:** {change['timestamp']}")


def display_system_health(system_health: dict[str, Any]):
    """Display system health dashboard."""
    st.subheader("🏥 System Health")

    if "error" in system_health:
        st.error(f"❌ Failed to load system health: {system_health['error']}")
        return

    # Health overview
    status = system_health.get("status", "Unknown")
    status_color = (
        "🟢" if status == "Healthy" else "🟡" if status == "Degraded" else "🔴"
    )

    st.metric("Overall System Status", f"{status_color} {status}", delta="")

    # Data freshness
    if system_health.get("data_freshness"):
        st.subheader("📅 Data Freshness")

        freshness_data = []
        for source, info in system_health["data_freshness"].items():
            age_hours = info.get("age_hours", 0)
            status = info.get("status", "Unknown")

            if age_hours < 1:
                age_display = f"{age_hours * 60:.0f}m"
            elif age_hours < 24:
                age_display = f"{age_hours:.1f}h"
            else:
                age_display = f"{age_hours / 24:.1f}d"

            status_emoji = (
                "🟢" if status == "Fresh" else "🟡" if status == "Stale" else "🔴"
            )

            freshness_data.append(
                {
                    "Data Source": source.replace("_", " ").title(),
                    "Status": f"{status_emoji} {status}",
                    "Age": age_display,
                    "Hours": age_hours,
                }
            )

        if freshness_data:
            df_freshness = pd.DataFrame(freshness_data)

            # Create a color-coded chart
            fig = px.bar(
                df_freshness,
                x="Data Source",
                y="Hours",
                title="Data Age by Source",
                color="Hours",
                color_continuous_scale="RdYlGn_r",  # Red for old, green for fresh
                hover_data=["Status", "Age"],
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)

            # Table view
            st.dataframe(
                df_freshness[["Data Source", "Status", "Age"]], use_container_width=True
            )


def display_logs_viewer():
    """Display logs viewer section."""
    st.subheader("📄 Logs Viewer")

    project_root = Path(get_project_root())
    logs_dir = project_root / "logs"

    if not logs_dir.exists():
        st.warning("Logs directory not found.")
        return

    # Get available log files
    log_files = sorted(
        logs_dir.glob("*.log"), key=lambda x: x.stat().st_mtime, reverse=True
    )

    if not log_files:
        st.warning("No log files found.")
        return

    # Log file selector
    log_file_names = [f.name for f in log_files]
    selected_log = st.selectbox("Select Log File", log_file_names)

    if selected_log:
        selected_path = logs_dir / selected_log

        try:
            # Show file info
            file_stat = selected_path.stat()
            file_size = file_stat.st_size / 1024 / 1024  # MB
            file_modified = datetime.fromtimestamp(file_stat.st_mtime)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("File Size", f"{file_size:.1f} MB")
            with col2:
                st.metric("Last Modified", file_modified.strftime("%H:%M:%S"))
            with col3:
                st.metric("Lines", "Loading...")

            # Read and display log content
            with open(selected_path, encoding="utf-8") as f:
                lines = f.readlines()

            # Update line count
            col3.metric("Lines", f"{len(lines):,}")

            # Display options
            col1, col2, col3 = st.columns(3)
            with col1:
                show_lines = st.selectbox(
                    "Show lines", [50, 100, 200, 500, "All"], index=1
                )
            with col2:
                log_level_filter = st.selectbox(
                    "Filter by level", ["All", "ERROR", "WARNING", "INFO", "DEBUG"]
                )
            with col3:
                search_term = st.text_input("Search in logs")

            # Filter lines
            filtered_lines = lines

            if log_level_filter != "All":
                filtered_lines = [
                    line for line in filtered_lines if log_level_filter in line
                ]

            if search_term:
                filtered_lines = [
                    line
                    for line in filtered_lines
                    if search_term.lower() in line.lower()
                ]

            # Limit lines
            if show_lines != "All":
                filtered_lines = filtered_lines[-int(show_lines) :]

            # Display logs
            if filtered_lines:
                st.text_area(
                    f"Log Content ({len(filtered_lines)} lines)",
                    value="".join(filtered_lines),
                    height=400,
                    disabled=True,
                )
            else:
                st.info("No matching log entries found.")

        except Exception as e:
            st.error(f"Failed to read log file: {e}")


def render(logger, data_service=None):
    """Render the comprehensive monitoring dashboard."""
    st.header("👁️ Watchtower System Monitoring")
    st.markdown(
        "Real-time monitoring of ETL processes, watchers, system health, and logs"
    )

    # Initialize data collector
    collector = MonitoringDataCollector()

    # Data collection with progress indicator
    with st.spinner("🔄 Collecting monitoring data..."):
        monitoring_data = {
            "etl_metrics": collector.get_etl_performance_metrics(),
            "watcher_status": collector.get_watcher_status(),
            "system_health": collector.get_system_health(),
            "orchestrator_status": collector.get_orchestrator_status(),
        }

    # Display system overview
    display_system_overview(monitoring_data)

    st.divider()

    # Create tabs for different monitoring sections
    tabs = st.tabs(
        [
            "⚙️ ETL Performance",
            "👁️ Watcher Status",
            "🏥 System Health",
            "📄 Logs Viewer",
            "🔄 Real-time Status",
        ]
    )

    with tabs[0]:
        display_etl_performance(monitoring_data["etl_metrics"])

    with tabs[1]:
        display_watcher_monitoring(monitoring_data["watcher_status"])

    with tabs[2]:
        display_system_health(monitoring_data["system_health"])

    with tabs[3]:
        display_logs_viewer()

    with tabs[4]:
        st.subheader("🔄 Real-time Status")
        st.info("Real-time monitoring features coming soon!")

        # Placeholder for real-time features
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("🔴 Live ETL Status")
            st.markdown("Monitor ETL processes in real-time")
            if st.button("🔄 Refresh ETL Status"):
                st.rerun()

        with col2:
            st.subheader("📊 Live System Metrics")
            st.markdown("Real-time system performance metrics")
            if st.button("📈 Refresh Metrics"):
                st.rerun()

    # Auto-refresh option
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        if st.button("🔄 Refresh All Data"):
            st.rerun()

    with col2:
        auto_refresh = st.checkbox("Auto-refresh (5min)")
        if auto_refresh:
            st.rerun()

    with col3:
        st.markdown(f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
