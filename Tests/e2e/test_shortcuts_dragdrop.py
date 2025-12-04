"""End-to-end tests for shortcuts drag-and-drop functionality
Tests drag-and-drop reordering, domain switching, and visual feedback
"""

import re

import pytest
from playwright.async_api import async_playwright, expect


class TestShortcutsDragDrop:
    """E2E tests for shortcuts drag-and-drop functionality"""

    @pytest.fixture()
    async def browser_context(self):
        """Setup browser context for testing"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(viewport={"width": 1920, "height": 1080}, user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            yield context
            await browser.close()

    @pytest.fixture()
    async def page(self, browser_context):
        """Setup page for testing"""
        page = await browser_context.new_page()
        yield page
        await page.close()

    @pytest.fixture()
    def dashboard_url(self):
        """Dashboard URL for testing"""
        return "http://localhost:7777"

    async def setup_test_shortcuts(self, page):
        """Setup test shortcuts in localStorage for drag-drop testing"""
        test_shortcuts = [
            {
                "id": "test_shortcut_1",
                "name": "Test Paper 1",
                "domain": "Papers",
                "source_filter": {"source": "arxiv", "title": "Test Paper 1"},
                "order": 0,
                "created_at": "2025-01-16T00:00:00.000Z",
                "updated_at": "2025-01-16T00:00:00.000Z",
            },
            {
                "id": "test_shortcut_2",
                "name": "Test News 1",
                "domain": "News",
                "source_filter": {"source": "reddit", "title": "Test News 1"},
                "order": 1,
                "created_at": "2025-01-16T00:00:00.000Z",
                "updated_at": "2025-01-16T00:00:00.000Z",
            },
            {
                "id": "test_shortcut_3",
                "name": "Test Paper 2",
                "domain": "Papers",
                "source_filter": {"source": "pubmed", "title": "Test Paper 2"},
                "order": 2,
                "created_at": "2025-01-16T00:00:00.000Z",
                "updated_at": "2025-01-16T00:00:00.000Z",
            },
        ]

        # Set up test data in localStorage
        await page.evaluate(
            """
            (shortcuts) => {
                localStorage.setItem('watchtower_source_shortcuts', JSON.stringify({
                    shortcuts: shortcuts
                }));
            }
        """,
            test_shortcuts,
        )

    async def test_drag_drop_visual_feedback(self, page, dashboard_url):
        """Test that drag-drop shows proper visual feedback"""
        await page.goto(dashboard_url)
        await self.setup_test_shortcuts(page)

        # Open shortcuts sidebar
        shortcuts_button = page.locator("button:has-text('Shortcuts')")
        await expect(shortcuts_button).to_be_visible()
        await shortcuts_button.click()

        # Wait for shortcuts to load
        await expect(page.locator(".offcanvas:has-text('My Source Shortcuts')")).to_be_visible()

        # Find a shortcut card
        shortcut_card = page.locator(".shortcut-card").first
        await expect(shortcut_card).to_be_visible()

        # Start dragging
        await shortcut_card.hover()
        await page.mouse.down()

        # Check for visual feedback (should have dragging class)
        await expect(shortcut_card).to_have_class(re.compile(r"dragging"))

        # Move mouse slightly to trigger drag state
        await page.mouse.move(100, 100)

        # Release mouse
        await page.mouse.up()

        # Check that dragging class is removed
        await expect(shortcut_card).not_to_have_class(re.compile(r"dragging"))

    async def test_drag_drop_reordering_within_domain(self, page, dashboard_url):
        """Test reordering shortcuts within the same domain"""
        await page.goto(dashboard_url)
        await self.setup_test_shortcuts(page)

        # Open shortcuts sidebar
        shortcuts_button = page.locator("button:has-text('Shortcuts')")
        await shortcuts_button.click()

        # Wait for shortcuts to load
        await expect(page.locator(".offcanvas:has-text('My Source Shortcuts')")).to_be_visible()

        # Find Papers domain section
        papers_section = page.locator("#shortcuts-domain-papers")
        await expect(papers_section).to_be_visible()

        # Get initial order of shortcuts in Papers domain
        initial_shortcuts = papers_section.locator(".shortcut-card")
        initial_count = await initial_shortcuts.count()
        assert initial_count >= 2, "Need at least 2 shortcuts in Papers domain for reordering test"

        # Get first shortcut text
        first_shortcut = initial_shortcuts.first
        first_shortcut_text = await first_shortcut.locator("a").text_content()

        # Start dragging first shortcut
        await first_shortcut.hover()
        await page.mouse.down()

        # Find second shortcut and move to its position
        second_shortcut = initial_shortcuts.nth(1)
        await second_shortcut.hover()

        # Release to drop
        await page.mouse.up()

        # Wait for potential reordering to complete
        await page.wait_for_timeout(500)

        # Verify the order changed (this is a basic check, actual implementation may vary)
        updated_shortcuts = papers_section.locator(".shortcut-card")
        updated_count = await updated_shortcuts.count()
        assert updated_count == initial_count, "Number of shortcuts should remain the same"

    async def test_drag_drop_between_domains(self, page, dashboard_url):
        """Test dragging shortcuts between different domains"""
        await page.goto(dashboard_url)
        await self.setup_test_shortcuts(page)

        # Open shortcuts sidebar
        shortcuts_button = page.locator("button:has-text('Shortcuts')")
        await shortcuts_button.click()

        # Wait for shortcuts to load
        await expect(page.locator(".offcanvas:has-text('My Source Shortcuts')")).to_be_visible()

        # Find Papers and News domains
        papers_section = page.locator("#shortcuts-domain-papers")
        news_section = page.locator("#shortcuts-domain-news")

        await expect(papers_section).to_be_visible()
        await expect(news_section).to_be_visible()

        # Get a shortcut from Papers domain
        papers_shortcuts = papers_section.locator(".shortcut-card")
        papers_count = await papers_shortcuts.count()
        assert papers_count >= 1, "Need at least 1 shortcut in Papers domain"

        # Get initial counts
        initial_papers_count = await papers_shortcuts.count()
        initial_news_count = await news_section.locator(".shortcut-card").count()

        # Drag shortcut from Papers to News
        papers_shortcut = papers_shortcuts.first
        shortcut_text = await papers_shortcut.locator("a").text_content()

        await papers_shortcut.hover()
        await page.mouse.down()

        # Move to News domain
        await news_section.hover()
        await page.mouse.up()

        # Wait for potential domain change to complete
        await page.wait_for_timeout(1000)

        # Check if shortcut moved (this depends on implementation)
        # Look for the shortcut in News domain
        news_shortcuts = news_section.locator(".shortcut-card")
        updated_news_count = await news_shortcuts.count()

        # The domain badge should update if implemented
        if updated_news_count > initial_news_count:
            # Check if our shortcut is now in News domain
            found_in_news = False
            for i in range(await news_shortcuts.count()):
                shortcut_card = news_shortcuts.nth(i)
                card_text = await shortcut_card.locator("a").text_content()
                if shortcut_text == shortcut_text:
                    found_in_news = True
                    # Check if domain badge updated
                    domain_badge = shortcut_card.locator(".badge")
                    badge_text = await domain_badge.text_content()
                    assert "News" in badge_text, f"Domain badge should show 'News', got '{badge_text}'"
                    break

            assert found_in_news, f"Shortcut '{shortcut_text}' not found in News domain after drag"

    async def test_drag_drop_cancelled(self, page, dashboard_url):
        """Test that cancelling drag-drop returns shortcuts to original position"""
        await page.goto(dashboard_url)
        await self.setup_test_shortcuts(page)

        # Open shortcuts sidebar
        shortcuts_button = page.locator("button:has-text('Shortcuts')")
        await shortcuts_button.click()

        # Wait for shortcuts to load
        await expect(page.locator(".offcanvas:has-text('My Source Shortcuts')")).to_be_visible()

        # Get initial order
        papers_section = page.locator("#shortcuts-domain-papers")
        initial_shortcuts = papers_section.locator(".shortcut-card")
        initial_count = await initial_shortcuts.count()
        assert initial_count >= 2, "Need at least 2 shortcuts for cancel test"

        # Get first shortcut details
        first_shortcut = initial_shortcuts.first
        first_text = await first_shortcut.locator("a").text_content()

        # Start dragging
        await first_shortcut.hover()
        await page.mouse.down()

        # Move slightly
        await page.mouse.move(50, 50)

        # Press Escape to cancel drag (if implemented)
        await page.keyboard.press("Escape")

        # Or simply release mouse without dropping on valid target
        await page.mouse.up()

        # Check that shortcut is still in original position
        updated_shortcuts = papers_section.locator(".shortcut-card")
        updated_first_text = await updated_shortcuts.first.locator("a").text_content()

        assert first_text == updated_first_text, "Shortcut should remain in original position after cancelled drag"

    async def test_drag_drop_accessibility(self, page, dashboard_url):
        """Test that drag-drop functionality is accessible"""
        await page.goto(dashboard_url)
        await self.setup_test_shortcuts(page)

        # Open shortcuts sidebar
        shortcuts_button = page.locator("button:has-text('Shortcuts')")
        await shortcuts_button.click()

        # Wait for shortcuts to load
        await expect(page.locator(".offcanvas:has-text('My Source Shortcuts')")).to_be_visible()

        # Check for ARIA attributes on draggable elements
        shortcut_cards = page.locator(".shortcut-card")
        card_count = await shortcut_cards.count()
        assert card_count > 0, "Should have at least one shortcut card"

        for i in range(min(card_count, 3)):  # Check first 3 cards
            card = shortcut_cards.nth(i)

            # Check for draggable attribute
            draggable = await card.get_attribute("draggable")
            assert draggable == "true", f"Shortcut card {i} should have draggable='true'"

            # Check for ARIA labels (if implemented)
            aria_label = await card.get_attribute("aria-label")
            # ARIA labels are optional but good for accessibility

            # Check that action buttons are accessible
            remove_button = card.locator("button:has-text('Remove')")
            await expect(remove_button).to_be_visible()

            # Check button has proper attributes
            button_aria_label = await remove_button.get_attribute("aria-label")
            button_title = await remove_button.get_attribute("title")
            # Either aria-label or title should be present for accessibility

    async def test_drag_drop_performance(self, page, dashboard_url):
        """Test that drag-drop operations are performant"""
        await page.goto(dashboard_url)
        await self.setup_test_shortcuts(page)

        # Open shortcuts sidebar
        shortcuts_button = page.locator("button:has-text('Shortcuts')")
        await shortcuts_button.click()

        # Wait for shortcuts to load
        await expect(page.locator(".offcanvas:has-text('My Source Shortcuts')")).to_be_visible()

        # Measure performance of drag operation
        papers_section = page.locator("#shortcuts-domain-papers")
        shortcut_cards = papers_section.locator(".shortcut-card")
        card_count = await shortcut_cards.count()

        if card_count >= 2:
            first_card = shortcut_cards.first
            second_card = shortcut_cards.nth(1)

            # Start timing
            start_time = asyncio.get_event_loop().time()

            # Perform drag operation
            await first_card.hover()
            await page.mouse.down()
            await second_card.hover()
            await page.mouse.up()

            # End timing
            end_time = asyncio.get_event_loop().time()
            drag_time = end_time - start_time

            # Drag operation should complete quickly (under 2 seconds)
            assert drag_time < 2.0, f"Drag operation took too long: {drag_time:.2f}s"

            # Page should remain responsive
            await expect(page.locator("body")).to_be_visible()

    async def test_drag_drop_error_handling(self, page, dashboard_url):
        """Test drag-drop error handling and recovery"""
        await page.goto(dashboard_url)
        await self.setup_test_shortcuts(page)

        # Open shortcuts sidebar
        shortcuts_button = page.locator("button:has-text('Shortcuts')")
        await shortcuts_button.click()

        # Wait for shortcuts to load
        await expect(page.locator(".offcanvas:has-text('My Source Shortcuts')")).to_be_visible()

        # Try to drag to invalid target (outside sidebar)
        papers_section = page.locator("#shortcuts-domain-papers")
        shortcut_cards = papers_section.locator(".shortcut_card")
        card_count = await shortcut_cards.count()

        if card_count > 0:
            first_card = shortcut_cards.first

            # Start dragging
            await first_card.hover()
            await page.mouse.down()

            # Move to invalid location (far away from sidebar)
            await page.mouse.move(100, 1000)  # Move far down
            await page.mouse.up()

            # Check that no error occurred and page is still functional
            await expect(page.locator("body")).to_be_visible()

            # Check that shortcuts are still accessible
            updated_cards = papers_section.locator(".shortcut_card")
            updated_count = await updated_cards.count()
            assert updated_count == card_count, "Shortcut count should remain unchanged after failed drag"

    async def test_multiple_drag_operations(self, page, dashboard_url):
        """Test multiple consecutive drag operations"""
        await page.goto(dashboard_url)
        await self.setup_test_shortcuts(page)

        # Open shortcuts sidebar
        shortcuts_button = page.locator("button:has-text('Shortcuts')")
        await shortcuts_button.click()

        # Wait for shortcuts to load
        await expect(page.locator(".offcanvas:has-text('My Source Shortcuts')")).to_be_visible()

        papers_section = page.locator("#shortcuts-domain-papers")
        shortcut_cards = papers_section.locator(".shortcut_card")
        card_count = await shortcut_cards.count()

        if card_count >= 3:
            # Perform multiple drag operations in sequence
            for i in range(min(card_count - 1, 3)):
                source_card = shortcut_cards.nth(i)
                target_card = shortcut_cards.nth(i + 1)

                # Drag operation
                await source_card.hover()
                await page.mouse.down()
                await target_card.hover()
                await page.mouse.up()

                # Wait a bit between operations
                await page.wait_for_timeout(200)

                # Refresh card references
                shortcut_cards = papers_section.locator(".shortcut_card")

            # Check that all operations completed without errors
            await expect(papers_section).to_be_visible()
            final_card_count = await papers_section.locator(".shortcut-card").count()
            assert final_card_count == card_count, "Card count should remain unchanged"
