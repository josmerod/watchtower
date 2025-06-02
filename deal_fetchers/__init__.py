# deal_fetchers/__init__.py
from .chollometro_fetcher import fetch_chollometro_deals
from .limitedtimed_fetcher import fetch_limitedtimed_deals

# Updated and new fetchers for this task:
from .producthunt_deals_fetcher import fetch_producthunt_deals
from .appsumo_fetcher import fetch_appsumo_deals
from .stacksocial_fetcher import fetch_stacksocial_deals

# The old_producthunt_fetcher is no longer imported.
