# deal_aggregator.py
from deal_fetchers import chollometro_fetcher, producthunt_fetcher, limitedtimed_fetcher
# In a real app, you might have a logger
# import logging
# logger = logging.getLogger(__name__)

def get_all_deals(apply_filters=True, travel_location_filter="Valencia, Spain"):
    """
    Fetches deals from all configured sources, aggregates them,
    and optionally applies filters.
    """
    all_deals = []
    aggregated_deals = []

    # Fetch deals from Chollometro
    try:
        # print("Fetching Chollometro deals...") # Basic logging
        chollometro_deals = chollometro_fetcher.fetch_chollometro_deals()
        if chollometro_deals:
            all_deals.extend(chollometro_deals)
        # print(f"Fetched {len(chollometro_deals if chollometro_deals else [])} deals from Chollometro.")
    except Exception as e:
        # In a real app, log this error
        # logger.error(f"Error fetching Chollometro deals: {e}")
        print(f"Error fetching Chollometro deals: {e}") # Placeholder for logging

    # Fetch deals from Product Hunt
    try:
        # print("Fetching Product Hunt deals...")
        producthunt_deals = producthunt_fetcher.fetch_producthunt_deals()
        if producthunt_deals:
            all_deals.extend(producthunt_deals)
        # print(f"Fetched {len(producthunt_deals if producthunt_deals else [])} deals from Product Hunt.")
    except Exception as e:
        # logger.error(f"Error fetching Product Hunt deals: {e}")
        print(f"Error fetching Product Hunt deals: {e}")

    # Fetch deals from Limited Time Deals
    try:
        # print("Fetching Limited Time Deals...")
        limitedtimed_deals = limitedtimed_fetcher.fetch_limitedtimed_deals()
        if limitedtimed_deals:
            all_deals.extend(limitedtimed_deals)
        # print(f"Fetched {len(limitedtimed_deals if limitedtimed_deals else [])} deals from Limited Time Deals.")
    except Exception as e:
        # logger.error(f"Error fetching Limited Time Deals: {e}")
        print(f"Error fetching Limited Time Deals: {e}")

    # Placeholder for removing duplicates if necessary
    # aggregated_deals = remove_duplicates(all_deals)
    aggregated_deals = all_deals # Assuming no duplicates for now

    if apply_filters:
        # print(f"Applying filters. Initial deal count: {len(aggregated_deals)}")
        filtered_deals = []
        for deal in aggregated_deals:
            # Basic travel deal filtering for Spain, prioritizing Valencia
            # This assumes 'category' and 'location' fields in your deal data model
            is_travel_deal = deal.get('category', '').lower() == 'travel'
            location_matches = False
            if is_travel_deal and deal.get('location'):
                location_lower = deal.get('location', '').lower()
                # Prioritize Valencia
                if travel_location_filter:
                    target_location_lower = travel_location_filter.lower()
                    if target_location_lower in location_lower:
                         location_matches = True
                # Broader Spain filter if Valencia not specifically matched or no filter given
                elif 'spain' in location_lower or 'españa' in location_lower:
                    location_matches = True

            if is_travel_deal and location_matches:
                filtered_deals.append(deal)
            elif not is_travel_deal: # Include non-travel deals if not specifically filtering for travel
                # Or, if you only want travel deals, this else-if would be removed
                # and only travel deals matching the location would be added.
                # For now, let's assume we want relevant travel deals + all other deals.
                # The client request was "Chollos de viajes? (pero en España, sobretodo cerca de Valencia)."
                # This implies a specific focus on these, but not necessarily exclusion of all others.
                # This part needs clarification based on exact client needs.
                # For now, let's refine to: if filters are applied, we are looking *specifically*
                # for travel deals matching the criteria.
                pass # This logic will be refined based on whether we ONLY want travel deals matching criteria or ALL deals + filtered travel deals

        # Refined logic: If filtering is on, only return travel deals matching location.
        # If the goal is to *only* show travel deals for Valencia/Spain when filters are active:
        if apply_filters and travel_location_filter:
            final_deals = []
            for deal in aggregated_deals:
                is_travel_deal = deal.get('category', '').lower() == 'travel'
                location_matches = False
                if is_travel_deal and deal.get('location'):
                    location_lower = deal.get('location', '').lower()
                    # Check for Valencia (or specified travel_location_filter)
                    if travel_location_filter.lower() in location_lower:
                        location_matches = True
                    # If Valencia not found, check for general Spain
                    elif "spain" in location_lower or "españa" in location_lower:
                        location_matches = True # Or make this more specific if Valencia is a hard requirement

                if is_travel_deal and location_matches:
                    final_deals.append(deal)
                elif not is_travel_deal: # Add non-travel deals
                     final_deals.append(deal)
            # print(f"Deal count after filtering: {len(final_deals)}")
            return final_deals
        else: # No filters, or filter toggle is off
            # print(f"No filters applied or filter toggle off. Deal count: {len(aggregated_deals)}")
            return aggregated_deals
    else:
        return aggregated_deals

if __name__ == '__main__':
    # Example usage (assuming fetchers return some dummy data for testing)
    # To test this, you'd need to modify the fetcher functions to return sample deal dictionaries.
    print("Simulating deal fetching and aggregation...")

    # --- Monkey patch fetchers for local testing ---
    def mock_fetch_chollometro():
        return [
            {'title': 'Super Laptop Offer', 'category': 'electronics', 'location': None, 'discounted_price': 700},
            {'title': 'Weekend Getaway Valencia', 'category': 'travel', 'location': 'Valencia, Spain', 'discounted_price': 150},
            {'title': 'Beach Holiday Alicante', 'category': 'travel', 'location': 'Alicante, Spain', 'discounted_price': 200},
        ]
    def mock_fetch_producthunt():
        return [
            {'title': 'New SaaS Tool', 'category': 'software', 'location': None, 'discounted_price': 10},
            {'title': 'Madrid City Tour', 'category': 'travel', 'location': 'Madrid, Spain', 'discounted_price': 90},
        ]
    def mock_fetch_limitedtimed():
        return []

    chollometro_fetcher.fetch_chollometro_deals = mock_fetch_chollometro
    producthunt_fetcher.fetch_producthunt_deals = mock_fetch_producthunt
    limitedtimed_fetcher.fetch_limitedtimed_deals = mock_fetch_limitedtimed
    # --- End monkey patch ---

    print("\n--- Getting all deals (no specific travel filter beyond 'Spain' if location present) ---")
    all_deals_unfiltered = get_all_deals(apply_filters=False)
    for deal in all_deals_unfiltered:
        print(deal)

    print("\n--- Getting deals, with travel filter for 'Valencia, Spain' (plus all non-travel) ---")
    deals_filtered_valencia = get_all_deals(apply_filters=True, travel_location_filter="Valencia, Spain")
    for deal in deals_filtered_valencia:
        print(deal)

    print("\n--- Getting deals, with travel filter for 'Spain' (plus all non-travel) ---")
    deals_filtered_spain = get_all_deals(apply_filters=True, travel_location_filter="Spain")
    for deal in deals_filtered_spain:
        print(deal)
