"""Personalization dashboard tab for user profiles and recommendations."""

from typing import List
import json

from dash import html, dcc
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State

from src.models.user_profile_model import UserProfile, SkillLevel, ResearchDomain
from src.models.ai_research_model import AIResearchPaper
from src.data_quality.user_profile_manager import UserProfileManager
from src.intelligence.recommendation_engine import ContentBasedRecommendationEngine
from src.utils.logging import get_logger

logger = get_logger("PersonalizationTab")


def render_personalization_tab() -> html.Div:
    """Render the personalization tab with user profile and recommendations.
    
    Returns:
        Dash HTML component
    """
    return html.Div([
        dbc.Container([
            # Header
            dbc.Row([
                dbc.Col([
                    html.H2("🎯 My AI Learning", className="mb-3"),
                    html.P(
                        "Personalize your AI content discovery experience",
                        className="text-muted"
                    )
                ])
            ], className="mb-4"),
            
            # Profile Setup Section
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H4("📝 Your Profile", className="mb-0")),
                        dbc.CardBody([
                            # User ID input (for demo - in production would use auth)
                            dbc.Row([
                                dbc.Col([
                                    dbc.Label("User ID:"),
                                    dbc.Input(
                                        id="personalization-user-id",
                                        type="text",
                                        placeholder="Enter your user ID",
                                        value="demo_user",
                                        className="mb-2"
                                    )
                                ], width=6)
                            ]),
                            
                            # Skill Level
                            dbc.Row([
                                dbc.Col([
                                    dbc.Label("Skill Level:"),
                                    dcc.Dropdown(
                                        id="personalization-skill-level",
                                        options=[
                                            {"label": level.value, "value": level.value}
                                            for level in SkillLevel
                                        ],
                                        value=SkillLevel.INTERMEDIATE.value,
                                        clearable=False,
                                        className="mb-2"
                                    )
                                ], width=6)
                            ]),
                            
                            # Preferred Domains
                            dbc.Row([
                                dbc.Col([
                                    dbc.Label("Preferred Domains (select multiple):"),
                                    dcc.Dropdown(
                                        id="personalization-domains",
                                        options=[
                                            {"label": domain.value, "value": domain.value}
                                            for domain in ResearchDomain
                                        ],
                                        value=[],
                                        multi=True,
                                        className="mb-3"
                                    )
                                ])
                            ]),
                            
                            # Save Button
                            dbc.Button(
                                "💾 Save Profile",
                                id="personalization-save-btn",
                                color="primary",
                                className="mt-2"
                            ),
                            
                            # Status message
                            html.Div(id="personalization-save-status", className="mt-2")
                        ])
                    ])
                ])
            ], className="mb-4"),
            
            # Recommendations Section
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H4("✨ Recommended For You", className="mb-0")),
                        dbc.CardBody([
                            dbc.Button(
                                "🔄 Get Recommendations",
                                id="personalization-recommend-btn",
                                color="success",
                                className="mb-3"
                            ),
                            html.Div(id="personalization-recommendations")
                        ])
                    ])
                ])
            ], className="mb-4"),
            
            # Progress Section
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H4("📊 Learning Progress", className="mb-0")),
                        dbc.CardBody([
                            html.Div(id="personalization-progress")
                        ])
                    ])
                ])
            ])
        ], fluid=True)
    ])


def register_personalization_callbacks(app):
    """Register Dash callbacks for the personalization tab.
    
    Args:
        app: Dash application instance
    """
    profile_manager = UserProfileManager()
    recommendation_engine = ContentBasedRecommendationEngine()
    
    @app.callback(
        Output("personalization-save-status", "children"),
        Input("personalization-save-btn", "n_clicks"),
        State("personalization-user-id", "value"),
        State("personalization-skill-level", "value"),
        State("personalization-domains", "value"),
        prevent_initial_call=True
    )
    def save_profile(n_clicks, user_id, skill_level, domains):
        """Save user profile preferences."""
        if not user_id:
            return dbc.Alert("Please enter a user ID", color="warning", duration=3000)
        
        try:
            # Get or create profile
            profile = profile_manager.get_or_create_profile(user_id)
            
            # Update preferences
            profile.skill_level = SkillLevel(skill_level)
            profile.preferred_domains = [ResearchDomain(d) for d in (domains or [])]
            
            # Save
            if profile_manager.save_profile(profile):
                return dbc.Alert(
                    f"✓ Profile saved successfully for {user_id}!",
                    color="success",
                    duration=3000
                )
            else:
                return dbc.Alert("Error saving profile", color="danger", duration=3000)
                
        except Exception as e:
            logger.error(f"Error saving profile: {e}")
            return dbc.Alert(f"Error: {str(e)}", color="danger", duration=3000)
    
    @app.callback(
        Output("personalization-recommendations", "children"),
        Input("personalization-recommend-btn", "n_clicks"),
        State("personalization-user-id", "value"),
        prevent_initial_call=True
    )
    def get_recommendations(n_clicks, user_id):
        """Generate personalized recommendations."""
        if not user_id:
            return dbc.Alert("Please enter a user ID and save your profile first", color="warning")
        
        try:
            # Load profile
            profile = profile_manager.load_profile(user_id)
            
            if not profile:
                return dbc.Alert(
                    "No profile found. Please save your profile first.",
                    color="warning"
                )
            
            # Load available papers from AI research ETL output
            from pathlib import Path
            from src.utils.file_system import get_project_root
            
            project_root = Path(get_project_root())
            papers_file = project_root / "data" / "ai_research_intelligence" / "output" / "ai_research_latest.json"
            
            if not papers_file.exists():
                return dbc.Alert(
                    "No papers available. Please run the AI Research ETL first.",
                    color="info"
                )
            
            # Load papers
            with open(papers_file, 'r', encoding='utf-8') as f:
                papers_data = json.load(f)
            
            papers = [AIResearchPaper(**p) for p in papers_data]
            
            # Generate recommendations
            recommendations = recommendation_engine.recommend_papers(
                profile,
                papers,
                top_n=10
            )
            
            if not recommendations:
                return dbc.Alert("No recommendations found. Try updating your profile.", color="info")
            
            # Render recommendations
            rec_cards = []
            for paper, score, breakdown in recommendations:
                explanation = recommendation_engine.explain_recommendation(paper, breakdown)
                
                rec_cards.append(
                    dbc.Card([
                        dbc.CardBody([
                            html.H5(paper.title, className="card-title"),
                            html.P(
                                f"Match: {score*100:.0f}% • {explanation}",
                                className="text-muted small"
                            ),
                            dbc.Badge(
                                paper.primary_domain.value,
                                color="primary",
                                className="me-2"
                            ),
                            dbc.Badge(
                                paper.complexity.value,
                                color="secondary",
                                className="me-2"
                            ),
                            dbc.Badge(
                                f"Trend: {paper.trend_score*100:.0f}%",
                                color="success" if paper.trend_score > 0.7 else "info"
                            ),
                            html.P(
                                paper.abstract[:200] + "..." if len(paper.abstract) > 200 else paper.abstract,
                                className="mt-2 mb-1"
                            ),
                            html.A(
                                "View Paper →",
                                href=str(paper.url),
                                target="_blank",
                                className="btn btn-sm btn-outline-primary"
                            )
                        ])
                    ], className="mb-3")
                )
            
            return html.Div(rec_cards)
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return dbc.Alert(f"Error: {str(e)}", color="danger")
    
    @app.callback(
        Output("personalization-progress", "children"),
        Input("personalization-user-id", "value")
    )
    def show_progress(user_id):
        """Show learning progress for user."""
        if not user_id:
            return html.P("Enter a user ID to view progress", className="text-muted")
        
        try:
            profile = profile_manager.load_profile(user_id)
            
            if not profile:
                return html.P("No profile found", className="text-muted")
            
            # Progress stats
            stats = [
                dbc.Col([
                    html.H3(len(profile.completed_papers), className="text-primary"),
                    html.P("Papers Read", className="text-muted")
                ], width=4),
                dbc.Col([
                    html.H3(len(profile.preferred_domains), className="text-success"),
                    html.P("Domains", className="text-muted")
                ], width=4),
                dbc.Col([
                    html.H3(len(profile.bookmarked_papers), className="text-info"),
                    html.P("Bookmarked", className="text-muted")
                ], width=4)
            ]
            
            return dbc.Row(stats)
            
        except Exception as e:
            logger.error(f"Error loading progress: {e}")
            return html.P(f"Error: {str(e)}", className="text-danger")
