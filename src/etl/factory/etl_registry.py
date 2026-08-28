"""ETL Registry - Centralized registration of all ETLs.

This module registers all ETLs with the ETLFactory for dynamic instantiation.
"""

from src.etl.factory.etl_factory import ETLFactory

# Import ETL classes to register them
# Note: We use lazy imports to avoid circular dependencies


def register_all_etls() -> None:
    """Register all ETLs with the factory.

    This function should be called during application initialization
    to populate the ETL registry.
    """
    # ArXiv ETLs
    try:
        from src.etl.arxiv.arxiv_etl import ArxivETL

        ETLFactory.register(
            "arxiv",
            ArxivETL,
            config={"batch_size": 100, "enable_checkpointing": True},
        )
    except Exception as e:
        import logging

        logging.warning(f"Failed to register ArxivETL: {e}")

    # News ETLs
    try:
        # BUG: src.etl.news.hackernews_etl does not exist; registration always
        # fails and is silently swallowed by the except below.
        from src.etl.news.hackernews_etl import HackerNewsETL  # type: ignore[import-untyped]

        ETLFactory.register(
            "hackernews",
            HackerNewsETL,
            config={"max_stories": 30},
        )
    except Exception as e:
        import logging

        logging.warning(f"Failed to register HackerNewsETL: {e}")

    # Course ETLs
    try:
        # BUG: src.etl.courses.khan_academy_etl does not exist; registration always
        # fails and is silently swallowed by the except below.
        from src.etl.courses.khan_academy_etl import KhanAcademyETL  # type: ignore[import-untyped]

        ETLFactory.register(
            "khan_academy",
            KhanAcademyETL,
            config={"batch_size": 50},
        )
    except Exception as e:
        import logging

        logging.warning(f"Failed to register KhanAcademyETL: {e}")

    # Games ETLs
    try:
        # BUG: src.etl.games.enhanced_free_games_etl does not exist; registration
        # always fails and is silently swallowed by the except below.
        from src.etl.games.enhanced_free_games_etl import EnhancedFreeGamesETL  # type: ignore[import-untyped]

        ETLFactory.register(
            "free_games",
            EnhancedFreeGamesETL,
            config={"enable_checkpointing": True},
        )
    except Exception as e:
        import logging

        logging.warning(f"Failed to register EnhancedFreeGamesETL: {e}")

    # AI Platforms ETLs
    try:
        from src.etl.ai_platforms.anthropic_etl import AnthropicETL

        ETLFactory.register(
            "anthropic",
            AnthropicETL,
            config={"enable_checkpointing": True, "batch_size": 20},
        )
    except Exception as e:
        import logging

        logging.warning(f"Failed to register AnthropicETL: {e}")

    # Entertainment ETLs
    try:
        # BUG: spotify_browse_etl exists but defines no SpotifyBrowseETL class;
        # registration always fails and is silently swallowed by the except below.
        from src.etl.entertainment.spotify_browse_etl import (  # type: ignore[attr-defined]
            SpotifyBrowseETL,
        )

        ETLFactory.register(
            "spotify_browse",
            SpotifyBrowseETL,
            config={"enable_checkpointing": True},
        )
    except Exception as e:
        import logging

        logging.warning(f"Failed to register SpotifyBrowseETL: {e}")

    # Deal ETLs
    try:
        # BUG: src.etl.deals.software_deals_etl does not exist; registration always
        # fails and is silently swallowed by the except below.
        from src.etl.deals.software_deals_etl import SoftwareDealsETL  # type: ignore[import-untyped]

        ETLFactory.register(
            "software_deals",
            SoftwareDealsETL,
            config={"enable_checkpointing": True},
        )
    except Exception as e:
        import logging

        logging.warning(f"Failed to register SoftwareDealsETL: {e}")

    # Spanish Public Aid ETL (refactored)
    try:
        # BUG: src.etl.spanish_public_aid.spanish_public_aid_etl_refactored does
        # not exist; registration always fails and is silently swallowed by the
        # except below, so the "spanish_public_aid" factory name is never bound.
        from src.etl.spanish_public_aid.spanish_public_aid_etl_refactored import (  # type: ignore[import-untyped]
            SpanishPublicAidETLRefactored,
        )

        ETLFactory.register(
            "spanish_public_aid",
            SpanishPublicAidETLRefactored,
            config={
                "max_aids_per_source": 20,
                "request_delay_seconds": 2.0,
                "enable_checkpointing": True,
            },
        )
    except Exception as e:
        import logging

        logging.warning(f"Failed to register SpanishPublicAidETLRefactored: {e}")

    # YouTube Shorts ETL (refactored)
    try:
        from src.etl.youtube_shorts.youtube_shorts_etl import YouTubeShortsETL

        # BUG: YouTubeShortsETL is a plain class, not a BaseETL subclass; the
        # factory would try to instantiate it with BaseETL-style kwargs.
        ETLFactory.register(
            "youtube_shorts",
            YouTubeShortsETL,  # type: ignore[arg-type]
            config={"enable_checkpointing": True},
        )
    except Exception as e:
        import logging

        logging.warning(f"Failed to register YouTubeShortsETL: {e}")

    import logging

    logging.info(f"Registered {len(ETLFactory.list_etls())} ETLs with factory")

    # Virtual Museums ETL
    try:
        from src.etl.museums.museum_etl import VirtualMuseumsETL

        ETLFactory.register("virtual_museums", VirtualMuseumsETL)
    except Exception as e:
        logging.warning(f"Failed to register VirtualMuseumsETL: {e}")


# Auto-register on import
register_all_etls()
