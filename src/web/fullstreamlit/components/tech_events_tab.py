"""Tech Events & Conference Intelligence tab for Watchtower Streamlit application."""

from __future__ import annotations

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from src.web.fullstreamlit.utils.enhanced_data_service import UltraOptimizedDataService


def render(logger, data_service=None):
    """Render the Tech Events & Conference Intelligence tab.
    
    Args:
        logger: Logger instance for this component
        data_service: Data service for accessing events data
    """
    st.header("📅 Tech Events & Conference Intelligence")
    st.markdown("Discover technology conferences, workshops, and events with AI-powered recommendations")
    
    # Initialize data service if not provided
    if data_service is None:
        data_service = UltraOptimizedDataService(logger)
    
    # Load events data
    with st.spinner("🔄 Loading events intelligence..."):
        events_data = data_service.get_tech_events_intelligence()
    
    if 'error' in events_data:
        st.error("⚠️ Events Intelligence Temporarily Unavailable")
        st.warning(f"Error: {events_data['error']}")
        st.info("Please check your data connections and try refreshing the page.")
        return
    
    # Display overview metrics
    display_events_overview(events_data)
    
    st.divider()
    
    # Create main tabs
    main_tabs = st.tabs([
        "🎯 Upcoming Events",
        "⭐ High Quality Events", 
        "💰 Free Events",
        "📊 Analytics & Insights",
        "🔍 Event Search",
        "🎯 Personalized Recommendations"
    ])
    
    with main_tabs[0]:  # Upcoming Events
        render_upcoming_events(events_data, logger)
    
    with main_tabs[1]:  # High Quality Events
        render_high_quality_events(events_data, logger)
    
    with main_tabs[2]:  # Free Events
        render_free_events(events_data, logger)
    
    with main_tabs[3]:  # Analytics & Insights
        render_events_analytics(events_data, logger)
    
    with main_tabs[4]:  # Event Search
        render_event_search(events_data, logger)
    
    with main_tabs[5]:  # Personalized Recommendations
        render_personalized_recommendations(events_data, data_service, logger)


def display_events_overview(events_data: Dict[str, Any]):
    """Display events overview metrics.
    
    Args:
        events_data: Events intelligence data
    """
    stats = events_data.get('statistics', {})
    
    # Overview metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "📅 Total Events",
            stats.get('total_events', 0),
            delta=f"+{stats.get('upcoming_count', 0)} upcoming"
        )
    
    with col2:
        st.metric(
            "⭐ High Quality",
            stats.get('high_quality_count', 0),
            delta=f"{stats.get('avg_quality_score', 0):.1f} avg score"
        )
    
    with col3:
        st.metric(
            "💰 Free Events",
            stats.get('free_events_count', 0),
            delta=f"{stats.get('avg_roi_score', 0):.1f} avg ROI"
        )
    
    with col4:
        st.metric(
            "🤝 Networking Score",
            f"{stats.get('avg_networking_score', 0):.1f}",
            delta=f"{stats.get('avg_relevance_score', 0):.1f} relevance"
        )
    
    # Quick distributions
    if 'distributions' in events_data:
        dist = events_data['distributions']
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Event types pie chart
            if dist.get('event_types'):
                fig_types = px.pie(
                    values=list(dist['event_types'].values()),
                    names=list(dist['event_types'].keys()),
                    title="📋 Event Types Distribution"
                )
                fig_types.update_layout(height=300)
                st.plotly_chart(fig_types, use_container_width=True)
        
        with col2:
            # Format distribution
            if dist.get('formats'):
                fig_formats = px.pie(
                    values=list(dist['formats'].values()),
                    names=list(dist['formats'].keys()),
                    title="🌐 Event Formats Distribution"
                )
                fig_formats.update_layout(height=300)
                st.plotly_chart(fig_formats, use_container_width=True)


def render_upcoming_events(events_data: Dict[str, Any], logger):
    """Render upcoming events section.
    
    Args:
        events_data: Events intelligence data
        logger: Logger instance
    """
    st.subheader("🎯 Upcoming Tech Events")
    
    upcoming_events = events_data.get('upcoming_events', [])
    
    if not upcoming_events:
        st.info("📅 No upcoming events found. Check back later for new events!")
        return

    with st.expander("Filtros para Eventos Próximos", expanded=False):
        # Event filters moved into expander
        # Event type filter
        all_types = list(set(e.get('event_type', 'unknown') for e in upcoming_events))
        selected_types = st.multiselect(
            "Event Types",
            all_types,
            default=all_types,
            key="upcoming_event_types"  # Existing key preserved
        )
    
        # Format filter
        all_formats = list(set(e.get('format', 'unknown') for e in upcoming_events))
        selected_formats = st.multiselect(
            "Event Formats",
            all_formats,
            default=all_formats,
            key="upcoming_event_formats"  # Existing key preserved
        )
    
        # Cost filter
        cost_filter = st.selectbox(
            "Cost Filter",
            ["All", "Free Only", "Paid Only"],
            key="upcoming_cost_filter"  # Existing key preserved
        )
    
    # Apply filters
    filtered_events = filter_events(
        upcoming_events, selected_types, selected_formats, cost_filter
    )
    
    if not filtered_events:
        st.warning("No events match your filters. Try adjusting your selection.")
        return
    
    # Display events
    for i, event in enumerate(filtered_events[:20]):  # Limit to 20 events
        display_event_card(event, f"upcoming_{i}")


def render_high_quality_events(events_data: Dict[str, Any], logger):
    """Render high quality events section.
    
    Args:
        events_data: Events intelligence data
        logger: Logger instance
    """
    st.subheader("⭐ High Quality Tech Events")
    st.markdown("Events with quality scores ≥ 75, featuring expert speakers and valuable content")
    
    high_quality_events = events_data.get('high_quality_events', [])
    
    if not high_quality_events:
        st.info("⭐ No high quality events found. Quality scores are calculated based on speaker influence, content relevance, and networking potential.")
        return
    
    # Sort by quality score
    high_quality_events = sorted(
        high_quality_events, 
        key=lambda x: x.get('quality_score', 0), 
        reverse=True
    )
    
    # Display top quality events
    for i, event in enumerate(high_quality_events):
        display_event_card(event, f"quality_{i}", show_quality_badge=True)


def render_free_events(events_data: Dict[str, Any], logger):
    """Render free events section.
    
    Args:
        events_data: Events intelligence data
        logger: Logger instance
    """
    st.subheader("💰 Free Tech Events")
    st.markdown("High-value events that are free to attend - maximize your learning without cost")
    
    free_events = events_data.get('free_events', [])
    
    if not free_events:
        st.info("💰 No free events currently available. Check back later!")
        return
    
    # Sort by ROI score
    free_events = sorted(
        free_events, 
        key=lambda x: x.get('roi_score', 0), 
        reverse=True
    )
    
    # Display free events
    for i, event in enumerate(free_events):
        display_event_card(event, f"free_{i}", show_roi_badge=True)


def render_events_analytics(events_data: Dict[str, Any], logger):
    """Render events analytics and insights.
    
    Args:
        events_data: Events intelligence data
        logger: Logger instance
    """
    st.subheader("📊 Events Analytics & Insights")
    
    events = events_data.get('events', [])
    stats = events_data.get('statistics', {})
    distributions = events_data.get('distributions', {})
    
    if not events:
        st.warning("No events data available for analytics.")
        return
    
    # Create analytics tabs
    analytics_tabs = st.tabs([
        "📈 Scores Analysis",
        "🎯 Topics Trends", 
        "📍 Location Analysis",
        "💰 Cost Analysis"
    ])
    
    with analytics_tabs[0]:  # Scores Analysis
        render_scores_analysis(events, stats)
    
    with analytics_tabs[1]:  # Topics Trends
        render_topics_analysis(events, distributions)
    
    with analytics_tabs[2]:  # Location Analysis
        render_location_analysis(events)
    
    with analytics_tabs[3]:  # Cost Analysis
        render_cost_analysis(events)


def render_scores_analysis(events: List[Dict], stats: Dict):
    """Render events scores analysis.
    
    Args:
        events: List of events
        stats: Statistics data
    """
    st.markdown("#### 📊 Event Quality Metrics")
    
    # Extract scores for visualization
    quality_scores = [e.get('quality_score', 0) for e in events]
    relevance_scores = [e.get('relevance_score', 0) for e in events]
    networking_scores = [e.get('networking_score', 0) for e in events]
    roi_scores = [e.get('roi_score', 0) for e in events]
    
    # Scores distribution chart
    fig = go.Figure()
    
    fig.add_trace(go.Histogram(
        x=quality_scores,
        name="Quality Score",
        opacity=0.7,
        nbinsx=20
    ))
    
    fig.add_trace(go.Histogram(
        x=relevance_scores,
        name="Relevance Score",
        opacity=0.7,
        nbinsx=20
    ))
    
    fig.add_trace(go.Histogram(
        x=networking_scores,
        name="Networking Score",
        opacity=0.7,
        nbinsx=20
    ))
    
    fig.add_trace(go.Histogram(
        x=roi_scores,
        name="ROI Score",
        opacity=0.7,
        nbinsx=20
    ))
    
    fig.update_layout(
        title="Event Scores Distribution",
        xaxis_title="Score",
        yaxis_title="Count",
        barmode='overlay',
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Average scores comparison
    avg_scores = {
        'Quality': stats.get('avg_quality_score', 0),
        'Relevance': stats.get('avg_relevance_score', 0),
        'Networking': stats.get('avg_networking_score', 0),
        'ROI': stats.get('avg_roi_score', 0)
    }
    
    fig_avg = px.bar(
        x=list(avg_scores.keys()),
        y=list(avg_scores.values()),
        title="Average Scores by Category",
        color=list(avg_scores.values()),
        color_continuous_scale="viridis"
    )
    fig_avg.update_layout(height=400)
    st.plotly_chart(fig_avg, use_container_width=True)


def render_topics_analysis(events: List[Dict], distributions: Dict):
    """Render topics analysis.
    
    Args:
        events: List of events
        distributions: Distribution data
    """
    st.markdown("#### 🎯 Technology Topics Trends")
    
    top_topics = distributions.get('top_topics', [])
    
    if top_topics:
        # Topics chart
        topics, counts = zip(*top_topics)
        
        fig = px.bar(
            x=counts,
            y=topics,
            orientation='h',
            title="Most Popular Technology Topics",
            labels={'x': 'Event Count', 'y': 'Topics'}
        )
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)
        
        # Topics insights
        st.markdown("##### 💡 Topics Insights")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**🔥 Trending Topics:**")
            for topic, count in top_topics[:5]:
                st.markdown(f"• **{topic.title()}**: {count} events")
        
        with col2:
            st.markdown("**📈 Growth Areas:**")
            growth_topics = [t for t, c in top_topics if any(
                keyword in t.lower() for keyword in ['ai', 'ml', 'blockchain', 'cloud']
            )]
            for topic in growth_topics[:5]:
                st.markdown(f"• **{topic.title()}**: High growth area")
    else:
        st.info("No topics data available for analysis.")


def render_location_analysis(events: List[Dict]):
    """Render location analysis.
    
    Args:
        events: List of events
    """
    st.markdown("#### 📍 Events by Location")
    
    # Extract locations
    locations = {}
    virtual_count = 0
    
    for event in events:
        location = event.get('location', 'Unknown')
        if event.get('is_virtual') or location.lower() in ['online', 'virtual']:
            virtual_count += 1
        else:
            locations[location] = locations.get(location, 0) + 1
    
    # Add virtual events
    if virtual_count > 0:
        locations['Virtual/Online'] = virtual_count
    
    if locations:
        # Location distribution chart
        fig = px.bar(
            x=list(locations.values()),
            y=list(locations.keys()),
            orientation='h',
            title="Events by Location",
            labels={'x': 'Event Count', 'y': 'Location'}
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
        
        # Location insights
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**🌍 Top Locations:**")
            sorted_locations = sorted(locations.items(), key=lambda x: x[1], reverse=True)
            for location, count in sorted_locations[:5]:
                st.markdown(f"• **{location}**: {count} events")
        
        with col2:
            virtual_pct = (virtual_count / len(events)) * 100 if events else 0
            st.metric("🌐 Virtual Events", f"{virtual_count}", delta=f"{virtual_pct:.1f}% of total")
    else:
        st.info("No location data available for analysis.")


def render_cost_analysis(events: List[Dict]):
    """Render cost analysis.
    
    Args:
        events: List of events
    """
    st.markdown("#### 💰 Event Cost Analysis")
    
    # Extract costs
    free_events = [e for e in events if e.get('is_free', False)]
    paid_events = [e for e in events if not e.get('is_free', False)]
    costs = [e.get('estimated_cost', 0) for e in paid_events if e.get('estimated_cost', 0) > 0]
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Free vs Paid distribution
        distribution = {
            'Free': len(free_events),
            'Paid': len(paid_events)
        }
        
        fig = px.pie(
            values=list(distribution.values()),
            names=list(distribution.keys()),
            title="Free vs Paid Events Distribution"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        if costs:
            # Cost distribution histogram
            fig = px.histogram(
                x=costs,
                nbins=15,
                title="Paid Events Cost Distribution",
                labels={'x': 'Cost (USD)', 'y': 'Count'}
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No cost data available for paid events.")
    
    # Cost insights
    if costs:
        st.markdown("**💡 Cost Insights:**")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("💵 Average Cost", f"${sum(costs) / len(costs):.0f}")
        
        with col2:
            st.metric("💰 Median Cost", f"${sorted(costs)[len(costs)//2]:.0f}")
        
        with col3:
            st.metric("🏷️ Max Cost", f"${max(costs):.0f}")


def render_event_search(events_data: Dict[str, Any], logger):
    """Render event search functionality.
    
    Args:
        events_data: Events intelligence data
        logger: Logger instance
    """
    st.subheader("🔍 Search & Filter Events")
    st.markdown("Find the perfect tech event for your interests and schedule")
    
    events = events_data.get('events', [])
    
    if not events:
        st.warning("No events available for search.")
        return
    
    # Search and filter controls
    col1, col2 = st.columns([2, 1])
    
    with col1:
        search_query = st.text_input(
            "🔍 Search events by name, description, or topics",
            placeholder="e.g., Python, AI, React, blockchain...",
            key="event_search_query"
        )
    
    with col2:
        sort_by = st.selectbox(
            "Sort by",
            ["Quality Score", "Relevance Score", "ROI Score", "Networking Score", "Date"],
            key="event_search_sort"
        )
    
    # Advanced filters
    with st.expander("🎛️ Advanced Filters"):
        filter_col1, filter_col2, filter_col3 = st.columns(3)
        
        with filter_col1:
            # Event type filter
            all_types = list(set(e.get('event_type', 'unknown') for e in events))
            selected_types = st.multiselect(
                "Event Types",
                all_types,
                default=all_types,
                key="search_event_types"
            )
        
        with filter_col2:
            # Format filter
            all_formats = list(set(e.get('format', 'unknown') for e in events))
            selected_formats = st.multiselect(
                "Event Formats",
                all_formats,
                default=all_formats,
                key="search_event_formats"
            )
        
        with filter_col3:
            # Cost range
            max_cost = st.number_input(
                "Max Cost ($)",
                min_value=0,
                max_value=5000,
                value=1000,
                step=50,
                key="search_max_cost"
            )
        
        # Quality score range
        quality_range = st.slider(
            "Minimum Quality Score",
            min_value=0,
            max_value=100,
            value=50,
            key="search_quality_range"
        )
    
    # Apply search and filters
    filtered_events = search_and_filter_events(
        events, search_query, selected_types, selected_formats, max_cost, quality_range
    )
    
    # Sort events
    if sort_by == "Quality Score":
        filtered_events = sorted(filtered_events, key=lambda x: x.get('quality_score', 0), reverse=True)
    elif sort_by == "Relevance Score":
        filtered_events = sorted(filtered_events, key=lambda x: x.get('relevance_score', 0), reverse=True)
    elif sort_by == "ROI Score":
        filtered_events = sorted(filtered_events, key=lambda x: x.get('roi_score', 0), reverse=True)
    elif sort_by == "Networking Score":
        filtered_events = sorted(filtered_events, key=lambda x: x.get('networking_score', 0), reverse=True)
    elif sort_by == "Date":
        try:
            filtered_events = sorted(filtered_events, key=lambda x: datetime.fromisoformat(x.get('start_date', '').replace('Z', '+00:00')))
        except:
            pass
    
    # Display results
    st.markdown(f"**Found {len(filtered_events)} events matching your criteria**")
    
    if filtered_events:
        for i, event in enumerate(filtered_events[:50]):  # Limit to 50 results
            display_event_card(event, f"search_{i}")
    else:
        st.info("No events match your search criteria. Try adjusting your filters.")


def render_personalized_recommendations(events_data: Dict[str, Any], data_service, logger):
    """Render personalized event recommendations.
    
    Args:
        events_data: Events intelligence data
        data_service: Data service instance
        logger: Logger instance
    """
    st.subheader("🎯 Personalized Event Recommendations")
    st.markdown("Get AI-powered event recommendations based on your interests and preferences")
    
    # User preferences form
    with st.form("user_preferences"):
        st.markdown("#### 👤 Your Preferences")
        
        col1, col2 = st.columns(2)
        
        with col1:
            interests = st.multiselect(
                "Your Technology Interests",
                [
                    "Python", "JavaScript", "React", "Vue", "Angular",
                    "AI/Machine Learning", "Data Science", "Blockchain",
                    "Cloud Computing", "DevOps", "Mobile Development",
                    "Web Development", "Cybersecurity", "Database",
                    "Backend Development", "Frontend Development"
                ],
                default=["Python", "AI/Machine Learning"],
                help="Select your primary technology interests"
            )
            
            location = st.text_input(
                "Your Location",
                placeholder="e.g., San Francisco, CA",
                help="Your location for calculating travel convenience"
            )
        
        with col2:
            max_budget = st.number_input(
                "Maximum Budget per Event ($)",
                min_value=0,
                max_value=5000,
                value=500,
                step=50,
                help="Maximum amount you're willing to spend per event"
            )
            
            preferred_formats = st.multiselect(
                "Preferred Event Formats",
                ["in_person", "virtual", "hybrid"],
                default=["in_person", "virtual"],
                help="Select your preferred event formats"
            )
        
        generate_recommendations = st.form_submit_button("🎯 Generate Recommendations")
    
    if generate_recommendations and interests:
        with st.spinner("🤖 Generating personalized recommendations..."):
            # Create user profile
            user_profile = {
                "interests": interests,
                "location": location,
                "budget": max_budget,
                "preferred_formats": preferred_formats
            }
            
            # Generate recommendations (using demo data for now)
            recommendations = generate_demo_recommendations(events_data, user_profile)
            
            if recommendations:
                st.success(f"🎯 Found {len(recommendations)} recommended events for you!")
                
                for i, rec in enumerate(recommendations):
                    event = rec['event']
                    score = rec['recommendation_score']
                    reason = rec['recommendation_reason']
                    
                    # Display recommendation with score
                    st.markdown(f"### 🏆 Recommendation #{i+1} (Score: {score:.1f}/100)")
                    st.info(f"**Why this event?** {reason}")
                    
                    display_event_card(event, f"rec_{i}", show_recommendation_score=True, rec_score=score)
                    
                    st.divider()
            else:
                st.warning("No recommendations found. Try adjusting your preferences.")
    elif generate_recommendations:
        st.warning("Please select at least one technology interest to generate recommendations.")


def filter_events(events: List[Dict], selected_types: List[str], selected_formats: List[str], cost_filter: str) -> List[Dict]:
    """Filter events based on criteria.
    
    Args:
        events: List of events to filter
        selected_types: Selected event types
        selected_formats: Selected event formats
        cost_filter: Cost filter option
        
    Returns:
        Filtered list of events
    """
    filtered = []
    
    for event in events:
        # Type filter
        if event.get('event_type') not in selected_types:
            continue
        
        # Format filter
        if event.get('format') not in selected_formats:
            continue
        
        # Cost filter
        if cost_filter == "Free Only" and not event.get('is_free', False):
            continue
        elif cost_filter == "Paid Only" and event.get('is_free', False):
            continue
        
        filtered.append(event)
    
    return filtered


def search_and_filter_events(
    events: List[Dict], 
    search_query: str, 
    selected_types: List[str], 
    selected_formats: List[str], 
    max_cost: float, 
    min_quality: int
) -> List[Dict]:
    """Search and filter events based on multiple criteria.
    
    Args:
        events: List of events to search
        search_query: Search query string
        selected_types: Selected event types
        selected_formats: Selected event formats
        max_cost: Maximum cost filter
        min_quality: Minimum quality score
        
    Returns:
        Filtered and searched list of events
    """
    filtered = []
    
    for event in events:
        # Search query filter
        if search_query:
            searchable_text = " ".join([
                event.get('name', ''),
                event.get('description', ''),
                " ".join(event.get('topics', [])),
                " ".join(event.get('categories', []))
            ]).lower()
            
            if search_query.lower() not in searchable_text:
                continue
        
        # Type filter
        if event.get('event_type') not in selected_types:
            continue
        
        # Format filter
        if event.get('format') not in selected_formats:
            continue
        
        # Cost filter
        event_cost = event.get('estimated_cost', 0)
        if event_cost > max_cost:
            continue
        
        # Quality filter
        if event.get('quality_score', 0) < min_quality:
            continue
        
        filtered.append(event)
    
    return filtered


def generate_demo_recommendations(events_data: Dict[str, Any], user_profile: Dict[str, Any]) -> List[Dict]:
    """Generate demo recommendations based on user profile.
    
    Args:
        events_data: Events data
        user_profile: User preferences
        
    Returns:
        List of recommended events with scores
    """
    events = events_data.get('events', [])
    recommendations = []
    
    user_interests = [interest.lower() for interest in user_profile.get('interests', [])]
    user_budget = user_profile.get('budget', float('inf'))
    
    for event in events:
        # Calculate interest match
        event_topics = [topic.lower() for topic in event.get('topics', [])]
        event_categories = [cat.lower() for cat in event.get('categories', [])]
        
        interest_match = 0
        for interest in user_interests:
            for topic in event_topics + event_categories:
                if interest in topic or topic in interest:
                    interest_match += 1
                    break
        
        if interest_match == 0:
            continue
        
        # Budget filter
        event_cost = event.get('estimated_cost', 0)
        if event_cost > user_budget:
            continue
        
        # Calculate recommendation score
        recommendation_score = (
            min(interest_match * 20, 60) +  # Interest match (max 60 points)
            event.get('quality_score', 0) * 0.2 +  # Quality score (max 20 points)
            event.get('roi_score', 0) * 0.2  # ROI score (max 20 points)
        )
        
        if recommendation_score >= 50:  # Minimum threshold
            recommendations.append({
                'event': event,
                'recommendation_score': recommendation_score,
                'recommendation_reason': f"This event matches {interest_match} of your interests and has a quality score of {event.get('quality_score', 0):.1f}."
            })
    
    # Sort by recommendation score
    recommendations.sort(key=lambda x: x['recommendation_score'], reverse=True)
    
    return recommendations[:10]  # Top 10 recommendations


def display_event_card(
    event: Dict[str, Any], 
    key_suffix: str, 
    show_quality_badge: bool = False,
    show_roi_badge: bool = False,
    show_recommendation_score: bool = False,
    rec_score: float = 0
):
    """Display an event card with all relevant information.
    
    Args:
        event: Event data
        key_suffix: Unique suffix for streamlit keys
        show_quality_badge: Whether to show quality badge
        show_roi_badge: Whether to show ROI badge
        show_recommendation_score: Whether to show recommendation score
        rec_score: Recommendation score to display
    """
    with st.container():
        # Event header
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # Title with badges
            title_html = f"**{event.get('name', 'Unknown Event')}**"
            
            if show_quality_badge:
                quality_score = event.get('quality_score', 0)
                if quality_score >= 85:
                    title_html += " 🏆"
                elif quality_score >= 75:
                    title_html += " ⭐"
            
            if show_roi_badge:
                roi_score = event.get('roi_score', 0)
                if roi_score >= 80:
                    title_html += " 💎"
            
            if event.get('is_free'):
                title_html += " 🆓"
            
            if event.get('is_virtual'):
                title_html += " 🌐"
            
            st.markdown(title_html)
            
            # Event details
            organizer = event.get('organizer', 'Unknown Organizer')
            location = event.get('location', 'TBD')
            event_type = event.get('event_type', 'unknown').title()
            
            st.markdown(f"🏢 <span class='text-muted'>Organizado por:</span> **{organizer}** • 📍 <span class='text-muted'>Lugar:</span> **{location}** • 📋 <span class='text-muted'>Tipo:</span> **{event_type}**")
        
        with col2:
            # Date and cost
            try:
                start_date = datetime.fromisoformat(event.get('start_date', '').replace('Z', '+00:00'))
                date_str = start_date.strftime("%b %d, %Y")
                
                # Calculate days until event
                days_until = (start_date - datetime.utcnow()).days
                if days_until > 0:
                    date_str += f" ({days_until} days)"
                elif days_until == 0:
                    date_str += " (Hoy!)" # Changed to Spanish
                else:
                    date_str += " (Pasado)" # Changed to Spanish
            except:
                date_str = "Fecha TBD" # Changed to Spanish
            
            st.markdown(f"<span class='text-muted'>📅 Fecha:</span> **{date_str}**")
            
            cost_display_str = ""
            if event.get('is_free'):
                cost_display_str = "GRATIS"
            else:
                cost = event.get('estimated_cost', 0)
                cost_display_str = f"${cost:.0f}"
            st.markdown(f"<span class='text-muted'>💰 Costo:</span> **{cost_display_str}**")
        
        # Description
        description = event.get('description', 'No description available.')
        st.markdown(f"{description}")
        
        # Topics and categories
        col1, col2 = st.columns(2)
        
        with col1:
            topics = event.get('topics', [])
            if topics:
                topic_tags = " ".join([f"`{topic}`" for topic in topics[:5]])
                st.markdown(f"🏷️ <span class='text-muted'>Temas:</span> {topic_tags}")
        
        with col2:
            categories = event.get('categories', [])
            if categories:
                category_tags = " ".join([f"`{cat}`" for cat in categories])
                st.markdown(f"📂 <span class='text-muted'>Categorías:</span> {category_tags}")
        
        # Scores section
        if any([event.get('quality_score', 0), event.get('relevance_score', 0), event.get('networking_score', 0), event.get('roi_score', 0)]):
            st.markdown("<span class='text-muted'>📊 Puntuaciones del Evento:</span>")
            
            score_col1, score_col2, score_col3, score_col4 = st.columns(4)
            
            with score_col1:
                quality = event.get('quality_score', 0)
                st.metric("Quality", f"{quality:.0f}", help="Overall event quality based on speakers, content, and organization")
            
            with score_col2:
                relevance = event.get('relevance_score', 0)
                st.metric("Relevance", f"{relevance:.0f}", help="How relevant the content is to current tech trends")
            
            with score_col3:
                networking = event.get('networking_score', 0)
                st.metric("Networking", f"{networking:.0f}", help="Networking opportunities available")
            
            with score_col4:
                roi = event.get('roi_score', 0)
                st.metric("ROI", f"{roi:.0f}", help="Return on investment considering cost and value")
        
        # Recommendation score
        if show_recommendation_score:
            st.markdown(f"🎯 <span class='text-muted'>Puntuación de Recomendación:</span> **{rec_score:.1f}/100**")
        
        # Action buttons
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if event.get('registration_url'):
                st.link_button(
                    "📝 Register", 
                    event['registration_url'],
                    use_container_width=True
                )
        
        with col2:
            if event.get('website_url'):
                st.link_button(
                    "🌐 Event Website", 
                    event['website_url'],
                    use_container_width=True
                )
        
        with col3:
            # Add to calendar (placeholder)
            if st.button(f"📅 Add to Calendar", key=f"calendar_{key_suffix}", use_container_width=True):
                st.success("Calendar integration coming soon!")
        
        st.divider() 