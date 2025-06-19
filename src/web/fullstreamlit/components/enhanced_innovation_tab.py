"""
Enhanced Innovation & Tech Trends Dashboard

This component provides advanced technology adoption intelligence with:
- Interactive Technology Radar
- Framework Battle Visualizations
- Adoption Trend Predictions
- Market Intelligence Dashboard
- Advanced Analytics and Insights
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import requests
import numpy as np
from pathlib import Path
import hashlib
import time
import asyncio
import aiohttp
import sys
import os
import subprocess
import re
import base64
import urllib.parse

# Use centralized path setup and safe logger
from ._path_setup import get_safe_logger

from web.fullstreamlit.utils.enhanced_data_service import UltraOptimizedDataService


def create_technology_radar_chart(radar_data: Dict[str, Any]) -> go.Figure:
    """Create an interactive technology radar chart."""
    if 'framework_battles' not in radar_data:
        return go.Figure()
    
    battles = radar_data['framework_battles']
    
    # Prepare data for radar chart
    technologies = []
    popularity_scores = []
    growth_rates = []
    job_demand = []
    community_health = []
    categories = []
    
    for category, battle_data in battles.items():
        for framework in battle_data.get('frameworks', []):
            technologies.append(framework['name'])
            popularity_scores.append(framework['popularity_score'])
            growth_rates.append(max(0, framework['growth_rate'] * 100))  # Normalize to positive
            job_demand.append(framework['job_market_demand'])
            community_health.append(framework['community_health'])
            categories.append(category)
    
    # Create radar chart
    fig = go.Figure()
    
    # Color mapping for categories
    colors = {
        'frontend': '#FF6B6B',
        'backend': '#4ECDC4', 
        'mobile': '#45B7D1',
        'ml': '#96CEB4'
    }
    
    for category in set(categories):
        category_mask = [cat == category for cat in categories]
        category_techs = [tech for tech, mask in zip(technologies, category_mask) if mask]
        category_popularity = [score for score, mask in zip(popularity_scores, category_mask) if mask]
        category_growth = [rate for rate, mask in zip(growth_rates, category_mask) if mask]
        category_job = [job for job, mask in zip(job_demand, category_mask) if mask]
        category_community = [comm for comm, mask in zip(community_health, category_mask) if mask]
        
        # Add trace for each technology in this category
        for i, tech in enumerate(category_techs):
            fig.add_trace(go.Scatterpolar(
                r=[category_popularity[i], category_growth[i], category_job[i], category_community[i]],
                theta=['Popularity', 'Growth Rate', 'Job Demand', 'Community Health'],
                fill='toself',
                name=f"{tech} ({category})",
                line_color=colors.get(category, '#A37FFF'),
                fillcolor=colors.get(category, '#A37FFF'),
                opacity=0.6,
                hovertemplate=f"<b>{tech}</b><br>" +
                            "Popularity: %{r[0]:.1f}<br>" +
                            "Growth: %{r[1]:.1f}%<br>" +
                            "Job Demand: %{r[2]:.1f}<br>" +
                            "Community: %{r[3]:.1f}<extra></extra>"
            ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100]
            )),
        showlegend=True,
        title={
            'text': "🎯 Technology Adoption Radar",
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 24, 'color': '#A37FFF'}
        },
        height=600,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': 'white'}
    )
    
    return fig


def create_framework_battle_chart(battles: Dict[str, Any]) -> go.Figure:
    """Create framework battle comparison chart."""
    if not battles:
        return go.Figure()
    
    # Prepare data
    categories = []
    winners = []
    runner_ups = []
    rising_stars = []
    confidence_scores = []
    
    for category, battle_data in battles.items():
        categories.append(category.title())
        winners.append(battle_data.get('winner', 'Unknown'))
        runner_ups.append(battle_data.get('runner_up', 'Unknown'))
        rising_stars.append(battle_data.get('rising_star', 'Unknown'))
        confidence_scores.append(battle_data.get('confidence_score', 0))
    
    # Create subplot with secondary y-axis
    fig = make_subplots(
        rows=1, cols=1,
        specs=[[{"secondary_y": True}]],
        subplot_titles=("Framework Battle Results",)
    )
    
    # Add confidence scores as line
    fig.add_trace(
        go.Scatter(
            x=categories,
            y=[score * 100 for score in confidence_scores],
            mode='lines+markers',
            name='Confidence Score',
            line=dict(color='#FFD700', width=3),
            marker=dict(size=8),
            hovertemplate='<b>%{x}</b><br>Confidence: %{y:.1f}%<extra></extra>'
        ),
        secondary_y=True
    )
    
    # Add winner information as bars
    fig.add_trace(
        go.Bar(
            x=categories,
            y=[1] * len(categories),
            name='Current Winner',
            text=winners,
            textposition='inside',
            marker_color='#00D4AA',
            hovertemplate='<b>%{x}</b><br>Winner: %{text}<extra></extra>'
        ),
        secondary_y=False
    )
    
    # Update layout
    fig.update_layout(
        title={
            'text': "⚔️ Framework Battle Championship",
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 20, 'color': '#A37FFF'}
        },
        showlegend=True,
        height=400,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': 'white'}
    )
    
    # Update y-axes
    fig.update_yaxes(title_text="Battle Status", secondary_y=False, showticklabels=False)
    fig.update_yaxes(title_text="Confidence Score (%)", secondary_y=True)
    
    return fig


def create_adoption_trends_chart(predictions: Dict[str, Any]) -> go.Figure:
    """Create technology adoption trends chart."""
    if not predictions:
        return go.Figure()
    
    # Prepare data
    technologies = []
    current_scores = []
    predicted_scores = []
    growth_rates = []
    confidence_levels = []
    recommendations = []
    
    for tech_name, prediction in predictions.items():
        technologies.append(tech_name)
        current_scores.append(prediction.get('current_score', 0))
        predicted_scores.append(prediction.get('predicted_score', 0))
        growth_rates.append(prediction.get('growth_rate', 0) * 100)
        confidence_levels.append(prediction.get('confidence', 0) * 100)
        recommendations.append(prediction.get('investment_recommendation', 'Hold'))
    
    # Create scatter plot
    fig = go.Figure()
    
    # Color mapping for recommendations
    color_map = {
        'Strong Buy': '#00D4AA',
        'Buy': '#4ECDC4',
        'Hold': '#FFD700',
        'Avoid': '#FF6B6B',
        'Monitor': '#A37FFF'
    }
    
    # Group by recommendation for better visualization
    for rec_type in set(recommendations):
        mask = [rec == rec_type for rec in recommendations]
        
        fig.add_trace(go.Scatter(
            x=[score for score, m in zip(current_scores, mask) if m],
            y=[score for score, m in zip(predicted_scores, mask) if m],
            mode='markers+text',
            name=rec_type,
            text=[tech for tech, m in zip(technologies, mask) if m],
            textposition='top center',
            marker=dict(
                size=[conf/5 for conf, m in zip(confidence_levels, mask) if m],  # Size based on confidence
                color=color_map.get(rec_type, '#A37FFF'),
                opacity=0.7,
                line=dict(width=2, color='white')
            ),
            hovertemplate='<b>%{text}</b><br>' +
                        'Current Score: %{x:.1f}<br>' +
                        'Predicted Score: %{y:.1f}<br>' +
                        f'Recommendation: {rec_type}<extra></extra>'
        ))
    
    # Add diagonal line for reference
    max_score = max(max(current_scores), max(predicted_scores))
    fig.add_trace(go.Scatter(
        x=[0, max_score],
        y=[0, max_score],
        mode='lines',
        name='No Change Line',
        line=dict(dash='dash', color='gray', width=1),
        showlegend=False
    ))
    
    fig.update_layout(
        title={
            'text': "📈 Technology Adoption Predictions",
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 20, 'color': '#A37FFF'}
        },
        xaxis_title="Current Adoption Score",
        yaxis_title="Predicted Adoption Score",
        showlegend=True,
        height=500,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': 'white'}
    )
    
    return fig


def create_market_intelligence_chart(market_data: Dict[str, Any]) -> go.Figure:
    """Create market intelligence visualization."""
    if not market_data or 'adoption_lifecycle' not in market_data:
        return go.Figure()
    
    lifecycle_data = market_data['adoption_lifecycle']
    
    # Prepare data for sunburst chart
    labels = []
    parents = []
    values = []
    
    # Add root
    labels.append("Technology Ecosystem")
    parents.append("")
    values.append(0)
    
    # Add lifecycle stages
    for stage, technologies in lifecycle_data.items():
        if technologies:
            stage_label = stage.title()
            labels.append(stage_label)
            parents.append("Technology Ecosystem")
            values.append(len(technologies))
            
            # Add individual technologies
            for tech_info in technologies[:5]:  # Limit to top 5 per stage
                tech_name = tech_info.get('technology', 'Unknown')
                labels.append(tech_name)
                parents.append(stage_label)
                values.append(tech_info.get('score', 1))
    
    # Create sunburst chart
    fig = go.Figure(go.Sunburst(
        labels=labels,
        parents=parents,
        values=values,
        branchvalues="total",
        maxdepth=3,
        hovertemplate='<b>%{label}</b><br>Value: %{value}<extra></extra>'
    ))
    
    fig.update_layout(
        title={
            'text': "🌱 Technology Adoption Lifecycle",
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 20, 'color': '#A37FFF'}
        },
        height=500,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': 'white'}
    )
    
    return fig


def display_enhanced_metrics(radar_data: Dict[str, Any]):
    """Display enhanced metrics with beautiful cards."""
    
    # Main metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    battles = radar_data.get('framework_battles', {})
    predictions = radar_data.get('adoption_predictions', {})
    recommendations = radar_data.get('recommendation_engine', {})
    
    with col1:
        battle_count = len(battles)
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 1.5rem; border-radius: 15px; text-align: center; 
                    box-shadow: 0 8px 32px rgba(0,0,0,0.3);">
            <h2 style="color: white; margin: 0; font-size: 2rem;">{battle_count}</h2>
            <p style="color: rgba(255,255,255,0.8); margin: 0.5rem 0 0 0;">Framework Battles</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        prediction_count = len(predictions)
        avg_confidence = sum(pred.get('confidence', 0) for pred in predictions.values()) / len(predictions) if predictions else 0
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); 
                    padding: 1.5rem; border-radius: 15px; text-align: center; 
                    box-shadow: 0 8px 32px rgba(0,0,0,0.3);">
            <h2 style="color: white; margin: 0; font-size: 2rem;">{prediction_count}</h2>
            <p style="color: rgba(255,255,255,0.8); margin: 0.5rem 0 0 0;">Predictions ({avg_confidence:.1%} Confidence)</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        strong_buys = len(recommendations.get('investment_grades', {}).get('strong_buy', []))
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); 
                    padding: 1.5rem; border-radius: 15px; text-align: center; 
                    box-shadow: 0 8px 32px rgba(0,0,0,0.3);">
            <h2 style="color: white; margin: 0; font-size: 2rem;">{strong_buys}</h2>
            <p style="color: rgba(255,255,255,0.8); margin: 0.5rem 0 0 0;">Strong Buy Signals</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        rising_count = len(recommendations.get('rising_technologies', []))
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); 
                    padding: 1.5rem; border-radius: 15px; text-align: center; 
                    box-shadow: 0 8px 32px rgba(0,0,0,0.3);">
            <h2 style="color: white; margin: 0; font-size: 2rem;">{rising_count}</h2>
            <p style="color: rgba(255,255,255,0.8); margin: 0.5rem 0 0 0;">Rising Technologies</p>
        </div>
        """, unsafe_allow_html=True)


def display_investment_recommendations(recommendations: Dict[str, Any]):
    """Display investment recommendations with enhanced styling."""
    st.subheader("💎 Investment Intelligence")
    
    investment_grades = recommendations.get('investment_grades', {})
    
    # Create tabs for different recommendation types
    rec_tabs = st.tabs(["🚀 Strong Buy", "📈 Buy", "⏸️ Hold", "🚨 Avoid"])
    
    with rec_tabs[0]:  # Strong Buy
        strong_buys = investment_grades.get('strong_buy', [])
        if strong_buys:
            for rec in strong_buys:
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #00D4AA, #00B894); 
                            padding: 1rem; border-radius: 10px; margin: 0.5rem 0;
                            border-left: 4px solid #00D4AA;">
                    <h4 style="color: white; margin: 0;">{rec.get('technology', 'Unknown')}</h4>
                    <p style="color: rgba(255,255,255,0.9); margin: 0.5rem 0 0 0;">
                        {rec.get('reason', 'No reason provided')}
                    </p>
                    <small style="color: rgba(255,255,255,0.7);">
                        Growth Potential: {rec.get('growth_potential', 'N/A')}
                    </small>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No strong buy recommendations at this time.")
    
    with rec_tabs[1]:  # Buy
        buys = investment_grades.get('buy', [])
        if buys:
            for rec in buys:
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #4ECDC4, #44A08D); 
                            padding: 1rem; border-radius: 10px; margin: 0.5rem 0;
                            border-left: 4px solid #4ECDC4;">
                    <h4 style="color: white; margin: 0;">{rec.get('technology', 'Unknown')}</h4>
                    <p style="color: rgba(255,255,255,0.9); margin: 0.5rem 0 0 0;">
                        {rec.get('reason', 'No reason provided')}
                    </p>
                    <small style="color: rgba(255,255,255,0.7);">
                        Growth Potential: {rec.get('growth_potential', 'N/A')}
                    </small>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No buy recommendations at this time.")
    
    with rec_tabs[2]:  # Hold
        holds = investment_grades.get('hold', [])
        if holds:
            for rec in holds:
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #FFD700, #FFA500); 
                            padding: 1rem; border-radius: 10px; margin: 0.5rem 0;
                            border-left: 4px solid #FFD700;">
                    <h4 style="color: white; margin: 0;">{rec.get('technology', 'Unknown')}</h4>
                    <p style="color: rgba(255,255,255,0.9); margin: 0.5rem 0 0 0;">
                        {rec.get('reason', 'No reason provided')}
                    </p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No hold recommendations at this time.")
    
    with rec_tabs[3]:  # Avoid
        avoids = investment_grades.get('avoid', [])
        if avoids:
            for rec in avoids:
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #FF6B6B, #FF5252); 
                            padding: 1rem; border-radius: 10px; margin: 0.5rem 0;
                            border-left: 4px solid #FF6B6B;">
                    <h4 style="color: white; margin: 0;">{rec.get('technology', 'Unknown')}</h4>
                    <p style="color: rgba(255,255,255,0.9); margin: 0.5rem 0 0 0;">
                        {rec.get('reason', 'No reason provided')}
                    </p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.success("No technologies to avoid!")


def display_market_trends(market_intelligence: Dict[str, Any]):
    """Display market trends and insights."""
    st.subheader("🔍 Market Intelligence")
    
    overall_trends = market_intelligence.get('overall_trends', [])
    category_insights = market_intelligence.get('category_insights', {})
    
    # Overall trends
    if overall_trends:
        st.markdown("**📊 Overall Market Trends:**")
        for trend in overall_trends:
            st.markdown(f"• {trend}")
    
    # Category insights
    if category_insights:
        st.markdown("**🎯 Category Insights:**")
        
        insight_cols = st.columns(2)
        
        for idx, (category, insight_data) in enumerate(category_insights.items()):
            with insight_cols[idx % 2]:
                confidence = insight_data.get('confidence', 0)
                confidence_color = '#00D4AA' if confidence > 0.8 else '#FFD700' if confidence > 0.6 else '#FF6B6B'
                
                st.markdown(f"""
                <div style="background: rgba(163, 127, 255, 0.1); 
                            padding: 1rem; border-radius: 8px; margin: 0.5rem 0;
                            border-left: 4px solid {confidence_color};">
                    <h5 style="color: #A37FFF; margin: 0;">{category.title()}</h5>
                    <p style="color: white; margin: 0.5rem 0; font-size: 0.9rem;">
                        {insight_data.get('insight', 'No insight available')}
                    </p>
                    <small style="color: rgba(255,255,255,0.7);">
                        Confidence: {confidence:.1%} | Leader: {insight_data.get('market_leader', 'Unknown')}
                    </small>
                </div>
                """, unsafe_allow_html=True)


async def load_technology_radar_data(data_service: UltraOptimizedDataService) -> Dict[str, Any]:
    """Load technology radar data asynchronously."""
    try:
        return await data_service.get_technology_radar()
    except Exception as e:
        st.error(f"Failed to load technology radar data: {e}")
        return {'error': str(e)}


def render(logger, data_service=None):
    """Render the enhanced Innovation & Tech dashboard."""
    
    # Enhanced header with gradient background
    st.markdown("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 2rem; border-radius: 15px; margin-bottom: 2rem;
                box-shadow: 0 10px 30px rgba(0,0,0,0.3);">
        <h1 style="color: white; margin: 0; font-size: 2.5rem; text-align: center;">
            🚀 Technology Adoption Intelligence
        </h1>
        <p style="color: rgba(255,255,255,0.8); text-align: center; margin: 1rem 0 0 0; font-size: 1.1rem;">
            Advanced AI-powered technology trend analysis and investment intelligence
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize data service if not provided
    if data_service is None:
        data_service = UltraOptimizedDataService(logger)
    
    # Load technology radar data
    with st.spinner("🔄 Loading Technology Intelligence..."):
        try:
            # Run async function in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            radar_data = loop.run_until_complete(load_technology_radar_data(data_service))
            loop.close()
        except Exception as e:
            logger.error(f"Failed to load technology radar: {e}")
            radar_data = {'error': str(e)}
    
    # Check for errors
    if 'error' in radar_data:
        st.error("⚠️ Technology Intelligence Temporarily Unavailable")
        st.warning(f"Error: {radar_data['error']}")
        st.info("Please check your data connections and try refreshing the page.")
        return
    
    # Display enhanced metrics
    display_enhanced_metrics(radar_data)
    
    st.markdown("---")
    
    # Create main visualization tabs
    main_tabs = st.tabs([
        "🎯 Technology Radar", 
        "⚔️ Framework Battles", 
        "📈 Adoption Trends",
        "🔍 Market Intelligence",
        "💎 Investment Hub"
    ])
    
    with main_tabs[0]:  # Technology Radar
        st.markdown("### 🎯 Interactive Technology Radar")
        st.markdown("Explore technology adoption patterns across multiple dimensions:")
        
        radar_chart = create_technology_radar_chart(radar_data)
        st.plotly_chart(radar_chart, use_container_width=True)
        
        # Technology filters and details
        battles = radar_data.get('framework_battles', {})
        if battles:
            selected_category = st.selectbox(
                "Focus on Category:",
                options=['All'] + list(battles.keys()),
                key="radar_category"
            )
            
            if selected_category != 'All':
                category_data = battles[selected_category]
                st.markdown(f"**{selected_category.title()} Category Leader: {category_data.get('winner', 'Unknown')}**")
                
                frameworks = category_data.get('frameworks', [])
                if frameworks:
                    # Display top 3 frameworks
                    top_frameworks = sorted(frameworks, key=lambda x: x['recommendation_score'], reverse=True)[:3]
                    
                    cols = st.columns(3)
                    for idx, fw in enumerate(top_frameworks):
                        with cols[idx]:
                            rank_emoji = ["🥇", "🥈", "🥉"][idx]
                            st.markdown(f"""
                            <div style="background: rgba(163, 127, 255, 0.1); 
                                        padding: 1rem; border-radius: 8px; text-align: center;">
                                <h4 style="color: #A37FFF; margin: 0;">{rank_emoji} {fw['name']}</h4>
                                <p style="color: white; margin: 0.5rem 0;">Score: {fw['recommendation_score']:.1f}</p>
                                <small style="color: rgba(255,255,255,0.7);">
                                    {fw['maturity_level']} | {fw['learning_curve']} curve
                                </small>
                            </div>
                            """, unsafe_allow_html=True)
    
    with main_tabs[1]:  # Framework Battles
        st.markdown("### ⚔️ Framework Battle Championship")
        st.markdown("See which frameworks dominate each technology category:")
        
        battles = radar_data.get('framework_battles', {})
        if battles:
            battle_chart = create_framework_battle_chart(battles)
            st.plotly_chart(battle_chart, use_container_width=True)
            
            # Battle details
            st.markdown("#### 🏆 Battle Results")
            
            battle_cols = st.columns(2)
            for idx, (category, battle_data) in enumerate(battles.items()):
                with battle_cols[idx % 2]:
                    winner = battle_data.get('winner', 'Unknown')
                    runner_up = battle_data.get('runner_up', 'Unknown') 
                    rising_star = battle_data.get('rising_star', 'Unknown')
                    confidence = battle_data.get('confidence_score', 0)
                    
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #667eea, #764ba2); 
                                padding: 1rem; border-radius: 10px; margin: 0.5rem 0;">
                        <h4 style="color: white; margin: 0;">{category.title()} Battle</h4>
                        <p style="color: rgba(255,255,255,0.9); margin: 0.5rem 0;">
                            🥇 <strong>Winner:</strong> {winner}<br>
                            🥈 <strong>Runner-up:</strong> {runner_up}<br>
                            ⭐ <strong>Rising Star:</strong> {rising_star}
                        </p>
                        <small style="color: rgba(255,255,255,0.7);">
                            Confidence: {confidence:.1%}
                        </small>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.warning("No framework battle data available.")
    
    with main_tabs[2]:  # Adoption Trends
        st.markdown("### 📈 Technology Adoption Predictions")
        st.markdown("AI-powered predictions for technology adoption over the next 12 months:")
        
        predictions = radar_data.get('adoption_predictions', {})
        if predictions:
            trends_chart = create_adoption_trends_chart(predictions)
            st.plotly_chart(trends_chart, use_container_width=True)
            
            # Prediction insights
            st.markdown("#### 🔮 Key Predictions")
            
            # Filter predictions by trend
            trend_filter = st.selectbox(
                "Filter by trend:",
                options=['All', 'rising', 'explosive', 'stable', 'declining'],
                key="trend_filter"
            )
            
            filtered_predictions = predictions
            if trend_filter != 'All':
                filtered_predictions = {
                    name: pred for name, pred in predictions.items()
                    if pred.get('trend_direction') == trend_filter
                }
            
            pred_cols = st.columns(2)
            for idx, (tech_name, prediction) in enumerate(list(filtered_predictions.items())[:6]):
                with pred_cols[idx % 2]:
                    trend = prediction.get('trend_direction', 'stable')
                    current_score = prediction.get('current_score', 0)
                    predicted_score = prediction.get('predicted_score', 0)
                    confidence = prediction.get('confidence', 0)
                    growth = prediction.get('expected_growth_percentage', 0)
                    
                    trend_emoji = {
                        'explosive': '🚀',
                        'rising': '📈', 
                        'stable': '➡️',
                        'declining': '📉'
                    }.get(trend, '❓')
                    
                    trend_color = {
                        'explosive': '#00D4AA',
                        'rising': '#4ECDC4',
                        'stable': '#FFD700', 
                        'declining': '#FF6B6B'
                    }.get(trend, '#A37FFF')
                    
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, {trend_color}, rgba(255,255,255,0.1)); 
                                padding: 1rem; border-radius: 10px; margin: 0.5rem 0;">
                        <h4 style="color: white; margin: 0;">{trend_emoji} {tech_name}</h4>
                        <p style="color: rgba(255,255,255,0.9); margin: 0.5rem 0;">
                            Current: {current_score:.1f} → Predicted: {predicted_score:.1f}<br>
                            Growth: {growth:+.1f}% | Confidence: {confidence:.1%}
                        </p>
                        <small style="color: rgba(255,255,255,0.7);">
                            Trend: {trend.title()}
                        </small>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.warning("No prediction data available.")
    
    with main_tabs[3]:  # Market Intelligence
        st.markdown("### 🔍 Market Intelligence Dashboard")
        
        market_intelligence = radar_data.get('market_intelligence', {})
        if market_intelligence:
            # Market lifecycle visualization
            lifecycle_chart = create_market_intelligence_chart(market_intelligence)
            st.plotly_chart(lifecycle_chart, use_container_width=True)
            
            # Market trends display
            display_market_trends(market_intelligence)
        else:
            st.warning("No market intelligence data available.")
    
    with main_tabs[4]:  # Investment Hub
        st.markdown("### 💎 Technology Investment Intelligence")
        st.markdown("Strategic recommendations for technology adoption and investment:")
        
        recommendations = radar_data.get('recommendation_engine', {})
        if recommendations:
            display_investment_recommendations(recommendations)
            
            # Top recommendations summary
            top_recs = recommendations.get('top_recommendations', [])
            if top_recs:
                st.markdown("#### 🌟 Top Strategic Recommendations")
                
                for idx, rec in enumerate(top_recs[:3], 1):
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #f093fb, #f5576c); 
                                padding: 1.5rem; border-radius: 15px; margin: 1rem 0;
                                box-shadow: 0 8px 32px rgba(0,0,0,0.3);">
                        <h4 style="color: white; margin: 0;">#{idx} {rec.get('technology', 'Unknown')}</h4>
                        <p style="color: rgba(255,255,255,0.9); margin: 0.5rem 0;">
                            {rec.get('reason', 'No reason provided')}
                        </p>
                        <small style="color: rgba(255,255,255,0.7);">
                            Growth Potential: {rec.get('growth_potential', 'N/A')}
                        </small>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.warning("No recommendation data available.")
    
    # Enhanced footer
    st.markdown("---")
    st.markdown(f"""
    <div style="text-align: center; padding: 1rem; 
                background: rgba(163, 127, 255, 0.1); border-radius: 10px;">
        <p style="color: #A37FFF; margin: 0; font-weight: bold;">
            🤖 Powered by Advanced AI Analytics
        </p>
        <small style="color: rgba(255,255,255,0.7);">
            Last updated: {radar_data.get('last_updated', datetime.now().isoformat())} | 
            Data sources: {', '.join(radar_data.get('data_sources', ['Unknown']))}
        </small>
    </div>
    """, unsafe_allow_html=True) 