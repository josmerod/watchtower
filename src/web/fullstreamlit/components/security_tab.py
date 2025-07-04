"""Security Intelligence Tab Component.

This component displays security vulnerability data and intelligence including:
- CVE vulnerabilities from NVD
- GitHub Security Advisories
- npm security alerts
- Security trends and analytics
- Risk assessments and mitigation strategies

Provides comprehensive security intelligence for software professionals.
"""

import json
from datetime import datetime
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


def prepare_vulnerability_chart_data(security_data: dict[str, Any]) -> go.Figure:
    """Prepare vulnerability trends chart data."""
    vulnerabilities = security_data.get('vulnerabilities', [])

    if not vulnerabilities:
        # Create empty chart
        fig = go.Figure()
        fig.add_annotation(
            text="No vulnerability data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font={'size': 16}
        )
        fig.update_layout(
            title="Vulnerability Trends",
            showlegend=False,
            height=400
        )
        return fig

    # Process data for time series
    df = pd.DataFrame(vulnerabilities)

    # Convert dates
    if 'published_date' in df.columns:
        df['published_date'] = pd.to_datetime(df['published_date'], errors='coerce')
        df = df.dropna(subset=['published_date'])

        # Group by date and risk level
        daily_counts = df.groupby([df['published_date'].dt.date, 'risk_level']).size().reset_index()
        daily_counts.columns = ['date', 'risk_level', 'count']

        # Create subplots
        fig = px.bar(
            daily_counts,
            x='date',
            y='count',
            color='risk_level',
            title='Daily Vulnerability Trends by Risk Level',
            color_discrete_map={
                'critical': '#FF0000',
                'high': '#FF8C00',
                'medium': '#FFD700',
                'low': '#32CD32',
                'info': '#87CEEB'
            }
        )

        fig.update_layout(
            xaxis_title="Date",
            yaxis_title="Number of Vulnerabilities",
            height=400,
            showlegend=True
        )

        return fig

    else:
        # Fallback: risk level distribution
        risk_counts = df['risk_level'].value_counts()

        fig = px.pie(
            values=risk_counts.values,
            names=risk_counts.index,
            title='Vulnerability Distribution by Risk Level',
            color_discrete_map={
                'critical': '#FF0000',
                'high': '#FF8C00',
                'medium': '#FFD700',
                'low': '#32CD32',
                'info': '#87CEEB'
            }
        )

        fig.update_layout(height=400)
        return fig

def prepare_technology_impact_chart(security_data: dict[str, Any]) -> go.Figure:
    """Prepare technology impact analysis chart."""
    vulnerabilities = security_data.get('vulnerabilities', [])

    if not vulnerabilities:
        fig = go.Figure()
        fig.add_annotation(
            text="No technology impact data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font={'size': 16}
        )
        fig.update_layout(title="Technology Impact Analysis", height=400)
        return fig

    # Process technology stack data
    tech_vuln_counts = {}
    tech_severity_sums = {}

    for vuln in vulnerabilities:
        tech_stack = vuln.get('technology_stack', [])
        severity = vuln.get('severity_score', 0)

        # Handle different data formats
        if isinstance(tech_stack, str):
            try:
                tech_stack = json.loads(tech_stack)
            except:
                tech_stack = [tech_stack] if tech_stack else []

        if not isinstance(tech_stack, list):
            tech_stack = []

        for tech in tech_stack:
            if tech:
                tech_vuln_counts[tech] = tech_vuln_counts.get(tech, 0) + 1
                tech_severity_sums[tech] = tech_severity_sums.get(tech, 0) + severity

    if not tech_vuln_counts:
        fig = go.Figure()
        fig.add_annotation(
            text="No technology data to display",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font={'size': 16}
        )
        fig.update_layout(title="Technology Impact Analysis", height=400)
        return fig

    # Calculate average severity per technology
    tech_avg_severity = {
        tech: tech_severity_sums[tech] / count
        for tech, count in tech_vuln_counts.items()
    }

    # Create bubble chart
    technologies = list(tech_vuln_counts.keys())
    vuln_counts = [tech_vuln_counts[tech] for tech in technologies]
    avg_severities = [tech_avg_severity[tech] for tech in technologies]

    fig = go.Figure(data=go.Scatter(
        x=vuln_counts,
        y=avg_severities,
        mode='markers+text',
        text=technologies,
        textposition="middle center",
        marker={
            'size': [count * 3 for count in vuln_counts],
            'color': avg_severities,
            'colorscale': 'Reds',
            'showscale': True,
            'colorbar': {'title': "Avg Severity"},
            'sizemode': 'diameter',
            'sizeref': 2. * max(vuln_counts) / (40. ** 2),
            'sizemin': 4
        }
    ))

    fig.update_layout(
        title='Technology Impact Analysis',
        xaxis_title='Number of Vulnerabilities',
        yaxis_title='Average Severity Score',
        height=500,
        showlegend=False
    )

    return fig

def display_vulnerability_summary(security_data: dict[str, Any]):
    """Display vulnerability summary metrics."""
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        total_count = security_data.get('total_count', 0)
        st.metric(
            "Total Vulnerabilities",
            f"{total_count:,}",
            help="Total number of vulnerabilities tracked"
        )

    with col2:
        critical_count = security_data.get('critical_count', 0)
        delta_critical = f"+{critical_count}" if critical_count > 0 else None
        st.metric(
            "Critical",
            critical_count,
            delta=delta_critical,
            delta_color="inverse",
            help="Critical severity vulnerabilities (9.0+ score)"
        )

    with col3:
        avg_severity = security_data.get('average_severity', 0)
        st.metric(
            "Avg Severity",
            f"{avg_severity:.1f}",
            help="Average CVSS/severity score"
        )

    with col4:
        patch_availability = security_data.get('patch_availability', 0)
        st.metric(
            "Patches Available",
            f"{patch_availability:.0f}%",
            help="Percentage of vulnerabilities with available patches"
        )

    with col5:
        urgent_count = security_data.get('needs_urgent_attention', 0)
        delta_urgent = f"+{urgent_count}" if urgent_count > 0 else None
        st.metric(
            "Urgent Attention",
            urgent_count,
            delta=delta_urgent,
            delta_color="inverse",
            help="Critical vulnerabilities needing immediate attention"
        )

def display_risk_breakdown(security_data: dict[str, Any]):
    """Display risk level breakdown."""
    st.subheader("🎯 Risk Level Breakdown")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        critical_count = security_data.get('critical_count', 0)
        st.metric("🔴 Critical", critical_count)

    with col2:
        high_count = security_data.get('high_count', 0)
        st.metric("🟠 High", high_count)

    with col3:
        medium_count = security_data.get('medium_count', 0)
        st.metric("🟡 Medium", medium_count)

    with col4:
        low_count = security_data.get('low_count', 0)
        st.metric("🟢 Low", low_count)

def display_critical_vulnerabilities(security_data: dict[str, Any]):
    """Display critical vulnerabilities table."""
    st.subheader("🚨 Critical Vulnerabilities")

    vulnerabilities = security_data.get('vulnerabilities', [])
    critical_vulns = [
        v for v in vulnerabilities
        if v.get('risk_level') == 'critical' or v.get('severity_score', 0) >= 9.0
    ]

    if not critical_vulns:
        st.success("✅ No critical vulnerabilities detected!")
        return

    # Convert to DataFrame for display
    pd.DataFrame(critical_vulns)

    # Prepare display columns

    # Filter and prepare display data
    display_data = []
    for vuln in critical_vulns:
        # Handle affected packages
        affected_packages = vuln.get('affected_packages', [])
        if isinstance(affected_packages, str):
            try:
                affected_packages = json.loads(affected_packages)
            except:
                affected_packages = [affected_packages] if affected_packages else []

        if isinstance(affected_packages, list):
            packages_str = ', '.join(affected_packages[:3])
            if len(affected_packages) > 3:
                packages_str += f' (+{len(affected_packages) - 3} more)'
        else:
            packages_str = str(affected_packages)

        display_data.append({
            'CVE ID': vuln.get('cve_id', 'N/A'),
            'Title': vuln.get('title', 'No title')[:80] + '...' if len(vuln.get('title', '')) > 80 else vuln.get('title', 'No title'),
            'Severity': f"{vuln.get('severity_score', 0):.1f}",
            'Source': vuln.get('source_name', 'Unknown'),
            'Affected Packages': packages_str,
            'Patch Available': '✅' if vuln.get('patch_available') else '❌',
            'Days Since Published': vuln.get('days_since_published', 'N/A'),
            'URL': vuln.get('source_url', '#')
        })

    if display_data:
        df_display = pd.DataFrame(display_data)

        # Make URLs clickable
        if 'URL' in df_display.columns:
            df_display['CVE ID'] = df_display.apply(
                lambda row: f"[{row['CVE ID']}]({row['URL']})" if row['URL'] != '#' else row['CVE ID'],
                axis=1
            )
            df_display = df_display.drop('URL', axis=1)

        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No critical vulnerability data to display")

def display_affected_technologies(security_data: dict[str, Any]):
    """Display affected technologies analysis."""
    st.subheader("💻 Affected Technologies")

    affected_technologies = security_data.get('affected_technologies', [])

    if not affected_technologies:
        st.info("No technology impact data available")
        return

    # Display as tags/badges
    st.write("Technologies with security vulnerabilities:")

    # Group technologies for better display
    tech_cols = st.columns(min(len(affected_technologies), 5))

    for i, tech in enumerate(affected_technologies):
        col_idx = i % len(tech_cols)
        with tech_cols[col_idx]:
            st.write(f"🔧 **{tech}**")

def display_recent_activity(security_data: dict[str, Any]):
    """Display recent security activity."""
    st.subheader("📈 Recent Security Activity")

    vulnerabilities = security_data.get('vulnerabilities', [])
    recent_vulns = [
        v for v in vulnerabilities
        if v.get('is_recent', False) or v.get('days_since_published', 999) <= 7
    ]

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Recent Vulnerabilities", len(recent_vulns))

    with col2:
        with_exploits = security_data.get('with_exploits', 0)
        st.metric("With Exploits", with_exploits)

    with col3:
        recent_count = security_data.get('recent_vulnerabilities', 0)
        st.metric("Last 30 Days", recent_count)

    # Show latest vulnerabilities
    if recent_vulns:
        st.write("**Latest Vulnerabilities:**")
        for vuln in recent_vulns[:5]:
            severity = vuln.get('severity_score', 0)
            risk_level = vuln.get('risk_level', 'unknown')
            title = vuln.get('title', 'No title')

            # Color code by risk level
            if risk_level == 'critical':
                st.error(f"🔴 **{title}** (Severity: {severity:.1f})")
            elif risk_level == 'high':
                st.warning(f"🟠 **{title}** (Severity: {severity:.1f})")
            elif risk_level == 'medium':
                st.info(f"🟡 **{title}** (Severity: {severity:.1f})")
            else:
                st.success(f"🟢 **{title}** (Severity: {severity:.1f})")

def display_mitigation_strategies(security_data: dict[str, Any]):
    """Display mitigation strategies and recommendations."""
    st.subheader("🛡️ Mitigation Strategies")

    vulnerabilities = security_data.get('vulnerabilities', [])

    # Collect all mitigation strategies
    all_strategies = set()
    for vuln in vulnerabilities:
        strategies = vuln.get('mitigation_strategies', [])
        if isinstance(strategies, str):
            try:
                strategies = json.loads(strategies)
            except:
                strategies = [strategies] if strategies else []

        if isinstance(strategies, list):
            all_strategies.update(strategies)

    if all_strategies:
        st.write("**Recommended Security Actions:**")
        for strategy in sorted(all_strategies):
            st.write(f"• {strategy}")
    else:
        st.info("No specific mitigation strategies available")

    # General security recommendations
    st.write("**General Security Best Practices:**")
    general_recommendations = [
        "Regularly update all software dependencies",
        "Implement automated vulnerability scanning",
        "Monitor security advisories for your technology stack",
        "Establish incident response procedures",
        "Conduct regular security assessments",
        "Use dependency management tools with security features",
        "Implement multi-layered security controls"
    ]

    for rec in general_recommendations:
        st.write(f"• {rec}")

def render(logger, data_service):
    """Render the Security Intelligence tab."""
    st.header("🛡️ Security Intelligence Dashboard")
    st.markdown("Real-time security vulnerability monitoring and intelligence for software professionals")

    # Load security data
    with st.spinner("Loading security intelligence data..."):
        security_data = data_service.get_security_intelligence()

    if 'error' in security_data:
        st.error("⚠️ Security Intelligence Unavailable")
        st.warning(security_data['error'])
        st.info("To enable security intelligence:")
        st.code("python src/etl/security/security_get_vulnerabilities.py")
        return

    # Display summary metrics
    display_vulnerability_summary(security_data)

    st.divider()

    # Create main content columns
    col1, col2 = st.columns([2, 1])

    with col1:
        # Vulnerability trends chart
        st.subheader("📊 Vulnerability Trends")
        vulnerability_chart = prepare_vulnerability_chart_data(security_data)
        st.plotly_chart(vulnerability_chart, use_container_width=True)

        # Critical vulnerabilities table
        display_critical_vulnerabilities(security_data)

    with col2:
        # Risk breakdown
        display_risk_breakdown(security_data)

        st.divider()

        # Recent activity
        display_recent_activity(security_data)

        st.divider()

        # Affected technologies
        display_affected_technologies(security_data)

    st.divider()

    # Technology impact analysis
    st.subheader("🎯 Technology Impact Analysis")
    tech_impact_chart = prepare_technology_impact_chart(security_data)
    st.plotly_chart(tech_impact_chart, use_container_width=True)

    st.divider()

    # Mitigation strategies
    display_mitigation_strategies(security_data)

    # Footer with data info
    st.divider()
    total_vulns = security_data.get('total_count', 0)
    st.markdown(f"*Security intelligence based on {total_vulns:,} vulnerabilities from multiple sources including CVE, GitHub Security Advisories, and package registries*")
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
