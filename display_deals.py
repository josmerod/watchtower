# display_deals.py
from deal_aggregator import get_all_deals

# Removed monkey-patching of individual fetchers.
# display_deals.py will now rely on deal_aggregator.get_all_deals()
# to use the actual (simulated) fetchers from the deal_fetchers package.

def display_deals_console(deals):
    """Prints a list of deals to the console in a structured way."""
    if not deals:
        print("No deals to display.")
        return

    print("\n--- Deal Feed ---")
    for i, deal in enumerate(deals):
        print(f"\n--- Deal #{i+1} ---")
        print(f"Title: {deal.get('title', 'N/A')}")
        if deal.get('original_price') and deal.get('discounted_price'):
            print(f"Price: {deal.get('currency', '')}{deal.get('discounted_price')} (Original: {deal.get('currency', '')}{deal.get('original_price')})")
        else:
            print(f"Price: {deal.get('currency', '')}{deal.get('discounted_price', 'N/A')}")
        if deal.get('discount_percentage'):
            print(f"Discount: {deal.get('discount_percentage')}% off")
        print(f"Source: {deal.get('source_platform', 'N/A')}")
        print(f"Category: {deal.get('category', 'N/A')}")
        if deal.get('location'):
            print(f"Location: {deal.get('location')}")
        print(f"Description: {deal.get('description', 'N/A')}")
        print(f"Link: {deal.get('url', '#')}")
        if deal.get('end_date'):
            print(f"Expires: {deal.get('end_date')}")
    print("\n--- End of Deal Feed ---")

if __name__ == "__main__":
    print("Fetching and displaying deals for Valencia focus...")
    # True to apply filters, focusing on Valencia travel deals + others
    valencia_focused_deals = get_all_deals(apply_filters=True, travel_location_filter="Valencia, Spain")
    display_deals_console(valencia_focused_deals)

    print("\n==================================================")
    print("Fetching and displaying all deals (unfiltered)...")
    all_deals_unfiltered = get_all_deals(apply_filters=False)
    display_deals_console(all_deals_unfiltered)

    # Example of how one might fetch for "Spain" in general for travel
    print("\n==================================================")
    print("Fetching and displaying deals with general Spain travel focus...")
    spain_focused_deals = get_all_deals(apply_filters=True, travel_location_filter="Spain")
    display_deals_console(spain_focused_deals)
