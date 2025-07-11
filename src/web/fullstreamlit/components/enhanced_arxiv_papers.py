"""Enhanced ArXiv Papers component with advanced intelligence features."""

import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional

import sys
from src.models.arxiv import TechnologyReadinessLevel, CommercialPotential
from src.etl.arxiv.enhanced_arxiv_etl import EnhancedArxivETL
from src.utils.logging import get_logger


def display_enhanced_papers():
    """Display enhanced ArXiv papers with intelligence features."""
    
    st.header("🚀 Enhanced ArXiv Intelligence")
    st.markdown("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
        <h4 style="color: white; margin: 0;">Advanced Research Intelligence Platform</h4>
        <p style="color: rgba(255,255,255,0.9); margin: 0.5rem 0 0 0; font-size: 0.9rem;">
            Comprehensive analysis with impact scoring, technology readiness assessment, and commercial viability evaluation
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Control panel
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🔄 Run Enhanced ETL", type="primary"):
            run_enhanced_etl()
    
    with col2:
        days_back = st.selectbox("📅 Days Back", [1, 3, 7, 14, 30], index=2)
    
    with col3:
        max_results = st.selectbox("📊 Max Papers", [50, 100, 200, 500], index=1)
    
    with col4:
        view_mode = st.selectbox("👁️ View Mode", ["Intelligence", "Standard", "Breakdown"], index=0)
    
    # Load and display enhanced papers
    enhanced_papers = load_enhanced_papers()
    
    if not enhanced_papers:
        st.info("📝 No enhanced papers found. Run the Enhanced ETL to generate intelligent analysis.")
        
        # Show sample/demo capabilities
        with st.expander("🎯 See Enhanced Features Demo"):
            show_enhanced_features_demo()
        return
    
    # Display statistics
    display_enhanced_statistics(enhanced_papers)
    
    # Display papers based on view mode
    if view_mode == "Intelligence":
        display_intelligence_view(enhanced_papers)
    elif view_mode == "Standard":
        display_standard_view(enhanced_papers)
    else:  # Breakdown
        display_breakdown_view(enhanced_papers)


def run_enhanced_etl():
    """Run the enhanced ArXiv ETL pipeline."""
    try:
        with st.spinner("🚀 Running Enhanced ArXiv ETL..."):
            # Initialize and run ETL
            etl = EnhancedArxivETL(
                name="streamlit_enhanced_arxiv",
                days_back=7,
                max_results=100,
                enable_advanced_scoring=True,
                enable_github_integration=True,
                enable_pwc_integration=False  # Disable PWC for faster processing
            )
            
            # Progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            status_text.text("Extracting papers from ArXiv...")
            progress_bar.progress(25)
            
            # Run ETL
            metrics = etl.run()
            
            progress_bar.progress(100)
            status_text.text("✅ Enhanced ETL completed!")
            
            # Show results
            st.success(f"✅ Successfully processed {metrics.records_loaded} papers!")
            st.metric("Processing Time", f"{metrics.duration_seconds:.1f}s")
            
            # Clear cache to reload new data
            st.cache_data.clear()
            st.rerun()
            
    except Exception as e:
        st.error(f"❌ ETL failed: {str(e)}")
        st.exception(e)


def load_enhanced_papers() -> Optional[List[Dict[str, Any]]]:
    """Load enhanced papers from the ETL output."""
    try:
        # Try different possible locations
        possible_paths = [
            "data/streamlit_enhanced_arxiv/output/latest_enhanced_papers.json",
            "data/enhanced_arxiv/output/latest_enhanced_papers.json",
            "data/arxiv/output/latest_enhanced_papers.json"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict) and 'papers' in data:
                        return data['papers']
                    elif isinstance(data, list):
                        return data
        
        return None
        
    except Exception as e:
        st.error(f"Error loading enhanced papers: {str(e)}")
        return None


def display_enhanced_statistics(papers: List[Dict[str, Any]]):
    """Display comprehensive statistics for enhanced papers."""
    
    st.subheader("📊 Intelligence Overview")
    
    # Calculate statistics
    total_papers = len(papers)
    breakthrough_papers = sum(1 for p in papers if p.get('is_breakthrough', False))
    high_impact_papers = sum(1 for p in papers if p.get('industry_impact_score', 0) >= 7.0)
    commercial_ready = sum(1 for p in papers if p.get('commercial_potential') in ['high', 'medium'])
    
    # Average scores
    avg_impact = sum(p.get('industry_impact_score', 0) for p in papers) / total_papers if total_papers else 0
    avg_innovation = sum(p.get('innovation_score', 0) for p in papers) / total_papers if total_papers else 0
    avg_citation = sum(p.get('citation_potential', 0) for p in papers) / total_papers if total_papers else 0
    avg_overall = sum(p.get('overall_significance_score', 0) for p in papers) / total_papers if total_papers else 0
    
    # Display metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            label="📚 Total Papers",
            value=total_papers,
            help="Total number of analyzed papers"
        )
    
    with col2:
        st.metric(
            label="🌟 Breakthrough",
            value=breakthrough_papers,
            delta=f"{(breakthrough_papers/total_papers*100):.1f}%" if total_papers else "0%",
            help="Papers identified as potential breakthroughs"
        )
    
    with col3:
        st.metric(
            label="🎯 High Impact",
            value=high_impact_papers,
            delta=f"{(high_impact_papers/total_papers*100):.1f}%" if total_papers else "0%",
            help="Papers with industry impact score ≥ 7.0"
        )
    
    with col4:
        st.metric(
            label="💼 Commercial Ready",
            value=commercial_ready,
            delta=f"{(commercial_ready/total_papers*100):.1f}%" if total_papers else "0%",
            help="Papers with high/medium commercial potential"
        )
    
    with col5:
        st.metric(
            label="⭐ Avg Significance",
            value=f"{avg_overall:.1f}",
            help="Average overall significance score"
        )
    
    # Score distribution
    st.subheader("📈 Score Distribution")
    score_cols = st.columns(4)
    
    with score_cols[0]:
        st.metric("🏭 Industry Impact", f"{avg_impact:.1f}/10")
    with score_cols[1]:
        st.metric("💡 Innovation", f"{avg_innovation:.1f}/10")
    with score_cols[2]:
        st.metric("📖 Citation Potential", f"{avg_citation:.1f}/10")
    with score_cols[3]:
        st.metric("🎯 Overall Score", f"{avg_overall:.1f}/10")


def display_intelligence_view(papers: List[Dict[str, Any]]):
    """Display papers in intelligence-focused view."""
    
    st.subheader("🧠 Intelligence Analysis")
    
    # Filter options
    col1, col2, col3 = st.columns(3)
    
    with col1:
        min_impact = st.slider("Min Impact Score", 0.0, 10.0, 5.0, 0.5)
    
    with col2:
        commercial_filter = st.selectbox(
            "Commercial Potential", 
            ["All", "High", "Medium", "Low", "Research"]
        )
    
    with col3:
        breakthrough_only = st.checkbox("Breakthrough Only")
    
    # Filter papers
    filtered_papers = papers.copy()
    
    if min_impact > 0:
        filtered_papers = [p for p in filtered_papers if p.get('industry_impact_score', 0) >= min_impact]
    
    if commercial_filter != "All":
        filtered_papers = [p for p in filtered_papers if p.get('commercial_potential', '').lower() == commercial_filter.lower()]
    
    if breakthrough_only:
        filtered_papers = [p for p in filtered_papers if p.get('is_breakthrough', False)]
    
    st.info(f"Showing {len(filtered_papers)} papers (filtered from {len(papers)})")
    
    # Sort by overall significance
    filtered_papers.sort(key=lambda x: x.get('overall_significance_score', 0), reverse=True)
    
    # Display papers
    for i, paper in enumerate(filtered_papers[:20]):  # Limit to top 20
        display_enhanced_paper_card(paper, i+1)


def display_enhanced_paper_card(paper: Dict[str, Any], rank: int):
    """Display an enhanced paper card with intelligence features."""
    
    # Determine card color based on significance
    significance = paper.get('overall_significance_score', 0)
    if significance >= 8:
        border_color = "#FF6B6B"  # Red for high significance
    elif significance >= 6:
        border_color = "#4ECDC4"  # Teal for medium significance
    else:
        border_color = "#45B7D1"  # Blue for standard
    
    # Card container
    with st.container():
        st.markdown(f"""
        <div style="
            border-left: 4px solid {border_color}; 
            padding: 1rem; 
            background: rgba(255,255,255,0.05); 
            border-radius: 8px; 
            margin-bottom: 1rem;
        ">
        """, unsafe_allow_html=True)
        
        # Header with rank and breakthrough indicator
        col1, col2 = st.columns([4, 1])
        
        with col1:
            breakthrough_badge = "🌟 BREAKTHROUGH" if paper.get('is_breakthrough') else ""
            st.markdown(f"**#{rank} {paper.get('title', 'Unknown Title')}** {breakthrough_badge}")
        
        with col2:
            st.metric("Significance", f"{paper.get('overall_significance_score', 0):.1f}/10")
        
        # Basic info
        authors = paper.get('authors', [])
        if isinstance(authors, list) and authors:
            st.caption(f"👥 {', '.join(authors[:3])}{'...' if len(authors) > 3 else ''}")
        
        categories = paper.get('categories', [])
        if categories:
            st.caption(f"🏷️ {', '.join(categories)}")
        
        # Intelligence scores
        score_cols = st.columns(5)
        
        with score_cols[0]:
            impact = paper.get('industry_impact_score', 0)
            st.metric("🏭 Impact", f"{impact:.1f}", delta=None)
        
        with score_cols[1]:
            innovation = paper.get('innovation_score', 0)
            st.metric("💡 Innovation", f"{innovation:.1f}", delta=None)
        
        with score_cols[2]:
            citation = paper.get('citation_potential', 0)
            st.metric("📖 Citations", f"{citation:.1f}", delta=None)
        
        with score_cols[3]:
            trl = paper.get('technology_readiness_level')
            if isinstance(trl, int):
                st.metric("🔬 TRL", f"TRL {trl}")
            else:
                st.metric("🔬 TRL", "N/A")
        
        with score_cols[4]:
            commercial = paper.get('commercial_potential', 'research')
            color_map = {
                'high': '🟢', 'medium': '🟡', 'low': '🔴', 'research': '🔵'
            }
            emoji = color_map.get(commercial.lower(), '⚪')
            st.metric("💼 Commercial", f"{emoji} {commercial.upper()}")
        
        # Technologies and applications
        if paper.get('related_technologies'):
            tech_list = paper['related_technologies'][:5]  # Limit to 5
            st.caption(f"🔧 **Technologies:** {', '.join(tech_list)}")
        
        if paper.get('potential_applications'):
            app_list = paper['potential_applications'][:3]  # Limit to 3
            st.caption(f"🎯 **Applications:** {', '.join(app_list)}")
        
        # Summary
        summary = paper.get('summary', '')
        if summary:
            truncated_summary = summary[:300] + "..." if len(summary) > 300 else summary
            st.write(truncated_summary)
        
        # Links
        link_cols = st.columns(3)
        
        with link_cols[0]:
            if paper.get('link'):
                st.markdown(f"[📄 ArXiv Paper]({paper['link']})")
        
        with link_cols[1]:
            if paper.get('pdf_url'):
                st.markdown(f"[📥 Download PDF]({paper['pdf_url']})")
        
        with link_cols[2]:
            github_info = paper.get('github_info')
            if github_info and github_info.get('html_url'):
                st.markdown(f"[💻 GitHub Repo]({github_info['html_url']})")
        
        st.markdown("</div>", unsafe_allow_html=True)


def display_standard_view(papers: List[Dict[str, Any]]):
    """Display papers in standard table view."""
    
    st.subheader("📋 Standard View")
    
    # Convert to DataFrame for table display
    df_data = []
    for paper in papers:
        row = {
            'Title': paper.get('title', '')[:80] + "..." if len(paper.get('title', '')) > 80 else paper.get('title', ''),
            'Authors': ', '.join(paper.get('authors', [])[:2]) + "..." if len(paper.get('authors', [])) > 2 else ', '.join(paper.get('authors', [])),
            'Categories': ', '.join(paper.get('categories', [])),
            'Impact Score': paper.get('industry_impact_score', 0),
            'Innovation': paper.get('innovation_score', 0),
            'Overall Score': paper.get('overall_significance_score', 0),
            'TRL': paper.get('technology_readiness_level', 'N/A'),
            'Commercial': paper.get('commercial_potential', 'research').upper(),
            'Breakthrough': '🌟' if paper.get('is_breakthrough') else '',
            'ArXiv ID': paper.get('arxiv_id', ''),
            'Link': paper.get('link', '')
        }
        df_data.append(row)
    
    df = pd.DataFrame(df_data)
    
    # Sort by overall score
    df = df.sort_values('Overall Score', ascending=False)
    
    # Display with formatting
    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            'Title': st.column_config.TextColumn('Title', width='large'),
            'Impact Score': st.column_config.NumberColumn('Impact Score', format="%.1f"),
            'Innovation': st.column_config.NumberColumn('Innovation', format="%.1f"),
            'Overall Score': st.column_config.NumberColumn('Overall Score', format="%.1f"),
            'Link': st.column_config.LinkColumn('ArXiv Link')
        }
    )


def display_breakdown_view(papers: List[Dict[str, Any]]):
    """Display detailed breakdown analysis."""
    
    st.subheader("🔍 Detailed Breakdown")
    
    # Tabs for different analyses
    tab1, tab2, tab3, tab4 = st.tabs(["🏆 Top Papers", "📊 Distributions", "🔬 Technology Analysis", "📈 Trends"])
    
    with tab1:
        display_top_papers_analysis(papers)
    
    with tab2:
        display_distributions_analysis(papers)
    
    with tab3:
        display_technology_analysis(papers)
    
    with tab4:
        display_trends_analysis(papers)


def display_top_papers_analysis(papers: List[Dict[str, Any]]):
    """Display top papers analysis."""
    
    # Top by different criteria
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**🏭 Top Impact Papers**")
        top_impact = sorted(papers, key=lambda x: x.get('industry_impact_score', 0), reverse=True)[:5]
        for i, paper in enumerate(top_impact, 1):
            score = paper.get('industry_impact_score', 0)
            title = paper.get('title', '')[:60] + "..." if len(paper.get('title', '')) > 60 else paper.get('title', '')
            st.write(f"{i}. **{title}** ({score:.1f}/10)")
    
    with col2:
        st.markdown("**💡 Top Innovation Papers**")
        top_innovation = sorted(papers, key=lambda x: x.get('innovation_score', 0), reverse=True)[:5]
        for i, paper in enumerate(top_innovation, 1):
            score = paper.get('innovation_score', 0)
            title = paper.get('title', '')[:60] + "..." if len(paper.get('title', '')) > 60 else paper.get('title', '')
            st.write(f"{i}. **{title}** ({score:.1f}/10)")
    
    # Breakthrough papers
    breakthrough_papers = [p for p in papers if p.get('is_breakthrough', False)]
    if breakthrough_papers:
        st.markdown("**🌟 Breakthrough Papers**")
        for paper in breakthrough_papers:
            title = paper.get('title', '')
            significance = paper.get('overall_significance_score', 0)
            st.write(f"• **{title}** (Significance: {significance:.1f}/10)")


def display_distributions_analysis(papers: List[Dict[str, Any]]):
    """Display distribution analysis."""
    
    # Commercial potential distribution
    commercial_dist = {}
    for paper in papers:
        potential = paper.get('commercial_potential', 'research')
        commercial_dist[potential] = commercial_dist.get(potential, 0) + 1
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**💼 Commercial Potential Distribution**")
        for potential, count in commercial_dist.items():
            percentage = (count / len(papers)) * 100
            st.write(f"• {potential.upper()}: {count} papers ({percentage:.1f}%)")
    
    # TRL distribution
    trl_dist = {}
    for paper in papers:
        trl = paper.get('technology_readiness_level')
        if isinstance(trl, int):
            trl_dist[f"TRL {trl}"] = trl_dist.get(f"TRL {trl}", 0) + 1
        else:
            trl_dist["Unknown"] = trl_dist.get("Unknown", 0) + 1
    
    with col2:
        st.markdown("**🔬 Technology Readiness Distribution**")
        for trl, count in sorted(trl_dist.items()):
            percentage = (count / len(papers)) * 100
            st.write(f"• {trl}: {count} papers ({percentage:.1f}%)")


def display_technology_analysis(papers: List[Dict[str, Any]]):
    """Display technology analysis."""
    
    # Collect all technologies
    all_technologies = []
    for paper in papers:
        technologies = paper.get('related_technologies', [])
        all_technologies.extend(technologies)
    
    # Count technologies
    from collections import Counter
    tech_counts = Counter(all_technologies)
    
    st.markdown("**🔧 Most Mentioned Technologies**")
    for tech, count in tech_counts.most_common(15):
        st.write(f"• **{tech}**: {count} papers")
    
    # Applications analysis
    all_applications = []
    for paper in papers:
        applications = paper.get('potential_applications', [])
        all_applications.extend(applications)
    
    app_counts = Counter(all_applications)
    
    st.markdown("**🎯 Top Application Areas**")
    for app, count in app_counts.most_common(10):
        st.write(f"• **{app}**: {count} papers")


def display_trends_analysis(papers: List[Dict[str, Any]]):
    """Display trends analysis."""
    
    # Calculate average trend alignment
    trend_averages = {}
    trend_names = {
        'ai_ml_trend': 'AI/ML',
        'llm_trend': 'Large Language Models',
        'cloud_trend': 'Cloud Computing',
        'data_trend': 'Data Engineering',
        'security_trend': 'Cybersecurity',
        'edge_trend': 'Edge Computing',
        'quantum_trend': 'Quantum Computing'
    }
    
    for paper in papers:
        trends = paper.get('trends_alignment', {})
        for trend, score in trends.items():
            if trend not in trend_averages:
                trend_averages[trend] = []
            trend_averages[trend].append(score)
    
    # Calculate averages and display
    st.markdown("**📈 Technology Trend Alignment**")
    for trend, scores in trend_averages.items():
        if scores:  # Only show trends with data
            avg_score = sum(scores) / len(scores)
            trend_name = trend_names.get(trend, trend.replace('_', ' ').title())
            papers_count = len([s for s in scores if s > 0])
            st.write(f"• **{trend_name}**: {avg_score:.1f}/10 (in {papers_count} papers)")


def show_enhanced_features_demo():
    """Show a demo of enhanced features."""
    
    st.markdown("""
    ### 🎯 Enhanced ArXiv Intelligence Features
    
    The Enhanced ArXiv ETL provides advanced analysis capabilities:
    
    **🧠 Intelligence Scoring**
    - **Industry Impact Score (0-10)**: Measures potential real-world impact
    - **Innovation Score (0-10)**: Evaluates novelty and breakthrough potential  
    - **Citation Potential (0-10)**: Predicts academic citation likelihood
    - **Overall Significance**: Weighted combination of all scores
    
    **🔬 Technology Assessment**
    - **Technology Readiness Level (TRL 1-9)**: NASA framework assessment
    - **Commercial Potential**: HIGH/MEDIUM/LOW/RESEARCH classification
    - **Implementation Feasibility**: Ready/Prototype/Experimental/Conceptual
    - **Breakthrough Detection**: Automatic identification of breakthrough papers
    
    **📊 Advanced Analytics**
    - **Research Category Classification**: AI/ML, Software Engineering, Data Engineering, etc.
    - **Technology Extraction**: Automatic identification of related technologies
    - **Application Areas**: Potential real-world applications
    - **Trend Alignment**: Alignment with current technology trends
    
    **🔗 External Integrations**
    - **GitHub Integration**: Automatic repository detection and metadata
    - **Papers With Code**: Links to code implementations and benchmarks
    - **Quality Indicators**: Multiple quality assessment metrics
    
    **📈 Intelligence Reports**
    - High-impact papers report
    - Breakthrough papers identification
    - Commercial potential analysis
    - Technology trend reports
    """)
    
    if st.button("🚀 Run Demo ETL"):
        st.info("Click 'Run Enhanced ETL' above to see these features in action!")


if __name__ == "__main__":
    display_enhanced_papers() 