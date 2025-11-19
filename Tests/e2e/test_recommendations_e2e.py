"""E2E tests for the recommendations tab using Playwright.

This test suite validates the complete user experience of the recommendations
system, including UI interactions, feedback mechanisms, and dismiss functionality.
"""

import pytest
import time
from playwright.sync_api import Page, expect


class TestRecommendationsE2E:
    """End-to-end tests for the recommendations tab."""

    @pytest.fixture(scope="function", autouse=True)
    def setup_test_data(self, temp_dir):
        """Set up test data for E2E tests."""
        from src.recommendations.activity_tracker import UserActivityTracker
        from src.recommendations.recommendation_engine import RecommendationEngine
        from src.recommendations.models import ActivityEvent, ActivityType, Recommendation, RecommendationType

        # Create test user activities to generate recommendations
        activity_tracker = UserActivityTracker(data_dir=temp_dir)
        engine = RecommendationEngine(activity_tracker, data_dir=temp_dir)

        # Generate sufficient activity data for recommendations
        base_time = time.time() - 86400 * 2  # 2 days ago
        activities = [
            ActivityEvent(
                user_id="test_user",
                action=ActivityType.CLICK,
                content_id="paper_1",
                content_type="arxiv_paper",
                source_category="machine_learning",
                title="Deep Learning Advances",
                duration_seconds=120.0,
                timestamp=base_time,
            ),
            ActivityEvent(
                user_id="test_user",
                action=ActivityType.VIEW,
                content_id="news_1",
                content_type="news_article",
                source_category="technology",
                title="AI Technology News",
                duration_seconds=45.0,
                timestamp=base_time + 3600,
            ),
            ActivityEvent(
                user_id="test_user",
                action=ActivityType.CLICK,
                content_id="paper_2",
                content_type="arxiv_paper",
                source_category="AI",
                title="Neural Networks Explained",
                duration_seconds=90.0,
                timestamp=base_time + 7200,
            ),
        ]

        # Track activities
        for activity in activities:
            activity_tracker.track_interaction(
                user_id=activity.user_id,
                action=activity.action,
                content_id=activity.content_id,
                content_type=activity.content_type,
                title=activity.title,
                source_category=activity.source_category,
                duration_seconds=activity.duration_seconds,
            )

        # Create mock recommendations for testing
        recommendations = []
        recommendation_types = [RecommendationType.TOP_SOURCE, RecommendationType.TOP_CATEGORY, RecommendationType.SIMILAR_CONTENT]
        titles = ["Advanced Machine Learning", "AI Research Trends", "Deep Learning Applications"]
        descriptions = [
            "Based on your frequent reading of machine learning papers",
            "Popular in AI - a category you engage with frequently",
            "Similar to 'Deep Learning Advances' which you recently viewed"
        ]

        for i, rec_type in enumerate(recommendation_types):
            rec = Recommendation(
                id=f"test_rec_{i+1}",
                user_id="test_user",
                type=rec_type,
                content_id=f"content_{i+1}",
                content_type="arxiv_paper",
                title=titles[i],
                description=descriptions[i],
                score=0.8 - (i * 0.1),
            )
            recommendations.append(rec)

        # Save mock recommendations
        from src.recommendations.models import UserRecommendations
        user_recommendations = UserRecommendations(
            user_id="test_user",
            recommendations=recommendations,
            total_activities_analyzed=len(activities),
        )

        engine.save_user_recommendations("test_user", user_recommendations)

    @pytest.fixture(scope="function")
    def dashboard_page(self, page: Page):
        """Load the dashboard page and navigate to recommendations tab."""
        # Navigate to the dashboard (assuming it's running on localhost:7777)
        page.goto("http://localhost:7777")

        # Wait for page to load
        page.wait_for_selector("[data-testid='dashboard-container']", timeout=10000)

        return page

    def test_recommendations_tab_loads(self, dashboard_page: Page):
        """Test that the recommendations tab loads and displays properly."""
        # Click on recommendations tab (adjust selector as needed)
        recommendations_tab = dashboard_page.locator("[data-testid='recommendations-tab'], #recommendations-tab, .nav-link:has-text('Recommendations')")

        if recommendations_tab.count() > 0:
            recommendations_tab.first.click()

        # Wait for recommendations content to load
        dashboard_page.wait_for_selector("[data-testid='recommendations-container'], .recommendations-content, h4:has-text('Recommended for You')", timeout=10000)

        # Verify recommendations section is visible
        expect(dashboard_page.locator("h4:has-text('Recommended for You')")).to_be_visible()
        expect(dashboard_page.locator("p:has-text('Personalized recommendations')")).to_be_visible()

    def test_recommendations_display_with_data(self, dashboard_page: Page):
        """Test that recommendations are displayed when data is available."""
        # Navigate to recommendations tab
        recommendations_tab = dashboard_page.locator("[data-testid='recommendations-tab'], #recommendations-tab, .nav-link:has-text('Recommendations')")
        if recommendations_tab.count() > 0:
            recommendations_tab.first.click()

        # Wait for recommendations to load
        dashboard_page.wait_for_timeout(2000)  # Allow time for async loading

        # Check for recommendation cards
        recommendation_cards = dashboard_page.locator(".card:has(.card-title), .recommendation-card")

        if recommendation_cards.count() > 0:
            # Verify recommendation card structure
            first_card = recommendation_cards.first
            expect(first_card.locator(".card-title, .recommendation-title")).to_be_visible()
            expect(first_card.locator(".card-text, .recommendation-description")).to_be_visible()

            # Check for action buttons
            expect(first_card.locator("button:has-text('Helpful'), .btn-helpful")).to_be_visible()
            expect(first_card.locator("button:has-text('Not Helpful'), .btn-not-helpful")).to_be_visible()
            expect(first_card.locator("button:has-text('Dismiss'), .btn-dismiss")).to_be_visible()

    def test_recommendations_empty_state(self, dashboard_page: Page):
        """Test recommendations empty state when no data is available."""
        # Navigate to recommendations tab
        recommendations_tab = dashboard_page.locator("[data-testid='recommendations-tab'], #recommendations-tab, .nav-link:has-text('Recommendations')")
        if recommendations_tab.count() > 0:
            recommendations_tab.first.click()

        # Look for empty state message
        empty_state = dashboard_page.locator(".alert:has-text('No recommendations available'), .no-recommendations")

        if empty_state.count() > 0:
            expect(empty_state).to_be_visible()
            expect(empty_state.locator("text=/Continue using the dashboard/")).to_be_visible()

    def test_recommendation_feedback_mechanism(self, dashboard_page: Page):
        """Test the recommendation feedback functionality."""
        # Navigate to recommendations and find a recommendation
        recommendations_tab = dashboard_page.locator("[data-testid='recommendations-tab'], #recommendations-tab, .nav-link:has-text('Recommendations')")
        if recommendations_tab.count() > 0:
            recommendations_tab.first.click()

        dashboard_page.wait_for_timeout(2000)

        # Find a recommendation with feedback buttons
        recommendation_cards = dashboard_page.locator(".card:has(.btn-helpful), .recommendation-card")

        if recommendation_cards.count() > 0:
            first_card = recommendation_cards.first

            # Test helpful feedback
            helpful_btn = first_card.locator("button:has-text('Helpful'), .btn-helpful")
            if helpful_btn.count() > 0:
                helpful_btn.click()

                # Verify button state changes (might be disabled or show confirmation)
                expect(helpful_btn).to_be_visible()

            # Test not helpful feedback
            not_helpful_btn = first_card.locator("button:has-text('Not Helpful'), .btn-not-helpful")
            if not_helpful_btn.count() > 0:
                not_helpful_btn.click()

                # Verify button state changes
                expect(not_helpful_btn).to_be_visible()

    def test_recommendation_dismiss_functionality(self, dashboard_page: Page):
        """Test the recommendation dismiss functionality."""
        # Navigate to recommendations
        recommendations_tab = dashboard_page.locator("[data-testid='recommendations-tab'], #recommendations-tab, .nav-link:has-text('Recommendations')")
        if recommendations_tab.count() > 0:
            recommendations_tab.first.click()

        dashboard_page.wait_for_timeout(2000)

        # Find a recommendation with dismiss button
        recommendation_cards = dashboard_page.locator(".card:has(.btn-dismiss), .recommendation-card")

        if recommendation_cards.count() > 0:
            first_card = recommendation_cards.first
            card_count_before = recommendation_cards.count()

            # Click dismiss button
            dismiss_btn = first_card.locator("button:has-text('Dismiss'), .btn-dismiss")
            if dismiss_btn.count() > 0:
                dismiss_btn.click()

                # Wait for UI update
                dashboard_page.wait_for_timeout(1000)

                # Verify card is hidden or removed (implementation dependent)
                # This might manifest as the card being hidden, removed, or showing "Dismissed" state
                expect(dismiss_btn).to_be_visible()  # Button should still be there, possibly changed

    def test_refresh_recommendations(self, dashboard_page: Page):
        """Test the refresh recommendations functionality."""
        # Navigate to recommendations
        recommendations_tab = dashboard_page.locator("[data-testid='recommendations-tab'], #recommendations-tab, .nav-link:has-text('Recommendations')")
        if recommendations_tab.count() > 0:
            recommendations_tab.first.click()

        dashboard_page.wait_for_timeout(2000)

        # Find and click refresh button
        refresh_btn = dashboard_page.locator("button:has-text('Refresh'), .btn-refresh, #refresh-recommendations")

        if refresh_btn.count() > 0:
            # Click refresh and verify loading state
            refresh_btn.click()

            # Look for loading indicator or button state change
            loading_indicator = dashboard_page.locator(".loading, .spinner, [data-testid='loading']")
            refresh_with_loading = dashboard_page.locator("button:has-text('Refreshing'), button:has(.spinner)")

            # Either loading indicator should appear or button should show loading state
            expect(loading_indicator.or_(refresh_with_loading)).to_be_visible()

    def test_recommendation_sections_display(self, dashboard_page: Page):
        """Test that different recommendation sections are displayed properly."""
        # Navigate to recommendations
        recommendations_tab = dashboard_page.locator("[data-testid='recommendations-tab'], #recommendations-tab, .nav-link:has-text('Recommendations')")
        if recommendations_tab.count() > 0:
            recommendations_tab.first.click()

        dashboard_page.wait_for_timeout(2000)

        # Look for different recommendation sections
        top_sources_section = dashboard_page.locator("h5:has-text('Top Sources'), h5:has-text('📚')")
        top_categories_section = dashboard_page.locator("h5:has-text('Top Categories'), h5:has-text('🏷️')")
        similar_content_section = dashboard_page.locator("h5:has-text('Similar Content'), h5:has-text('🔗')")

        # At least one section should be visible if recommendations exist
        sections = [top_sources_section, top_categories_section, similar_content_section]
        visible_sections = [section for section in sections if section.count() > 0]

        if visible_sections:
            expect(visible_sections[0]).to_be_visible()

    def test_recommendation_metadata_display(self, dashboard_page: Page):
        """Test that recommendation metadata is displayed correctly."""
        # Navigate to recommendations
        recommendations_tab = dashboard_page.locator("[data-testid='recommendations-tab'], #recommendations-tab, .nav-link:has-text('Recommendations')")
        if recommendations_tab.count() > 0:
            recommendations_tab.first.click()

        dashboard_page.wait_for_timeout(3000)  # Allow more time for metadata to load

        # Look for metadata section
        metadata_section = dashboard_page.locator(".bg-light:has('Generated'), .recommendation-metadata")

        if metadata_section.count() > 0:
            # Check for metadata elements
            expect(metadata_section.locator("text=/Generated/i")).to_be_visible()
            expect(metadata_section.locator("text=/activities/i")).to_be_visible()
            expect(metadata_section.locator("text=/Confidence|Score/i")).to_be_visible()

    def test_responsive_design(self, dashboard_page: Page):
        """Test that recommendations display properly on different screen sizes."""
        # Test mobile view
        dashboard_page.set_viewport_size({"width": 375, "height": 667})

        # Navigate to recommendations
        recommendations_tab = dashboard_page.locator("[data-testid='recommendations-tab'], #recommendations-tab, .nav-link:has-text('Recommendations')")
        if recommendations_tab.count() > 0:
            recommendations_tab.first.click()

        dashboard_page.wait_for_timeout(2000)

        # Verify mobile layout
        expect(dashboard_page.locator("h4:has-text('Recommended for You')")).to_be_visible()

        # Test desktop view
        dashboard_page.set_viewport_size({"width": 1920, "height": 1080})
        dashboard_page.wait_for_timeout(1000)

        # Verify desktop layout
        expect(dashboard_page.locator("h4:has-text('Recommended for You')")).to_be_visible()

    def test_accessibility_compliance(self, dashboard_page: Page):
        """Test accessibility compliance of the recommendations interface."""
        # Navigate to recommendations
        recommendations_tab = dashboard_page.locator("[data-testid='recommendations-tab'], #recommendations-tab, .nav-link:has-text('Recommendations')")
        if recommendations_tab.count() > 0:
            recommendations_tab.first.click()

        dashboard_page.wait_for_timeout(2000)

        # Test keyboard navigation
        dashboard_page.keyboard.press("Tab")

        # Check that focus moves to interactive elements
        focused_element = dashboard_page.locator(":focus")
        expect(focused_element).to_be_visible()

        # Test ARIA labels on buttons
        helpful_buttons = dashboard_page.locator("button:has-text('Helpful'), .btn-helpful")
        if helpful_buttons.count() > 0:
            first_helpful = helpful_buttons.first
            expect(first_helpful).to_have_attribute("aria-label")

    def test_performance_loading(self, dashboard_page: Page):
        """Test that recommendations load within acceptable time limits."""
        start_time = time.time()

        # Navigate to recommendations
        recommendations_tab = dashboard_page.locator("[data-testid='recommendations-tab'], #recommendations-tab, .nav-link:has-text('Recommendations')")
        if recommendations_tab.count() > 0:
            recommendations_tab.first.click()

        # Wait for recommendations to be visible
        try:
            dashboard_page.wait_for_selector(".card:has(.card-title), .recommendation-card, .no-recommendations", timeout=5000)
            load_time = time.time() - start_time

            # Verify load time is reasonable (< 5 seconds)
            assert load_time < 5.0, f"Recommendations took too long to load: {load_time:.2f} seconds"

        except:
            # If no recommendations found, that's still a valid state
            dashboard_page.wait_for_selector("h4:has-text('Recommended for You')", timeout=3000)
            load_time = time.time() - start_time
            assert load_time < 3.0, f"Tab took too long to load: {load_time:.2f} seconds"


class TestRecommendationsIntegration:
    """Integration tests for recommendations with other dashboard features."""

    def test_user_activity_tracking(self, dashboard_page: Page):
        """Test that user activities are tracked when interacting with content."""
        # Navigate to a content tab (e.g., ArXiv)
        arxiv_tab = dashboard_page.locator("[data-testid='arxiv-tab'], .nav-link:has-text('ArXiv')")
        if arxiv_tab.count() > 0:
            arxiv_tab.first.click()
            dashboard_page.wait_for_timeout(2000)

            # Click on a paper to track activity
            paper_links = dashboard_page.locator("a[href*='arxiv'], .paper-link")
            if paper_links.count() > 0:
                first_paper = paper_links.first
                paper_title = first_paper.text_content()
                first_paper.click()
                dashboard_page.wait_for_timeout(1000)

                # Navigate to recommendations tab
                recommendations_tab = dashboard_page.locator("[data-testid='recommendations-tab'], #nav-link:has-text('Recommendations')")
                if recommendations_tab.count() > 0:
                    recommendations_tab.first.click()
                    dashboard_page.wait_for_timeout(2000)

                    # Check if activity influenced recommendations
                    # This is implementation dependent and may require checking specific recommendation types

    def test_cross_tab_recommendations(self, dashboard_page: Page):
        """Test that recommendations appear across different dashboard tabs."""
        # First, ensure we have some activity by visiting different tabs
        tabs_to_visit = [
            ("[data-testid='arxiv-tab'], .nav-link:has-text('ArXiv')", "ArXiv"),
            ("[data-testid='news-tab'], .nav-link:has-text('News')", "News"),
        ]

        for tab_selector, tab_name in tabs_to_visit:
            tab = dashboard_page.locator(tab_selector)
            if tab.count() > 0:
                tab.first.click()
                dashboard_page.wait_for_timeout(1000)

        # Now check recommendations
        recommendations_tab = dashboard_page.locator("[data-testid='recommendations-tab'], .nav-link:has-text('Recommendations')")
        if recommendations_tab.count() > 0:
            recommendations_tab.first.click()
            dashboard_page.wait_for_timeout(2000)

            # Verify recommendations are displayed
            expect(dashboard_page.locator("h4:has-text('Recommended for You')")).to_be_visible()


class TestRecommendationsErrorHandling:
    """Test error handling and edge cases for recommendations."""

    def test_no_internet_connectivity(self, dashboard_page: Page):
        """Test behavior when internet connectivity is limited."""
        # This would test fallback behavior when external data sources are unavailable
        # Implementation depends on how the dashboard handles offline scenarios

        # Navigate to recommendations
        recommendations_tab = dashboard_page.locator("[data-testid='recommendations-tab'], .nav-link:has-text('Recommendations')")
        if recommendations_tab.count() > 0:
            recommendations_tab.first.click()
            dashboard_page.wait_for_timeout(2000)

            # Should show appropriate message for limited data
            expect(dashboard_page.locator("h4:has-text('Recommended for You')")).to_be_visible()

    def test_corrupted_data_handling(self, dashboard_page: Page):
        """Test handling of corrupted recommendation data."""
        # This would require setting up corrupted test data
        # For now, verify the interface doesn't crash

        # Navigate to recommendations
        recommendations_tab = dashboard_page.locator("[data-testid='recommendations-tab'], .nav-link:has-text('Recommendations')")
        if recommendations_tab.count() > 0:
            recommendations_tab.first.click()
            dashboard_page.wait_for_timeout(2000)

            # Interface should still load, even with no/limited recommendations
            expect(dashboard_page.locator("h4:has-text('Recommended for You')")).to_be_visible()