# src/web/fullstreamlit/components/ecommerce_tab.py
import streamlit as st
import pandas as pd
import json
import os

# Define the path to the processed Shoppy.gg data
DATA_FILE_PATH = "data/shoppy/shoppy_processed_data.json"

def load_shoppy_data():
    """
    Loads processed Shoppy.gg data from the JSON file.
    Returns a pandas DataFrame or None if data cannot be loaded.
    """
    if not os.path.exists(DATA_FILE_PATH):
        st.warning(f"Shoppy.gg data file not found at: {DATA_FILE_PATH}")
        st.info("Please run the Shoppy.gg ETL process to collect data.")
        return None

    try:
        with open(DATA_FILE_PATH, "r") as f:
            data = json.load(f)
        if not data:
            st.info("No Shoppy.gg data found. The data file is empty.")
            return None
        return pd.DataFrame(data)
    except json.JSONDecodeError:
        st.error(f"Error decoding JSON from {DATA_FILE_PATH}. The file might be corrupted.")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred while loading Shoppy.gg data: {e}")
        return None

def render(logger):
    """
    Renders the Shoppy.gg data tab in the Streamlit application.
    """
    st.header("🛍️ Shoppy.gg Tracker")

    df_shoppy = load_shoppy_data()

    if df_shoppy is not None and not df_shoppy.empty:
        st.info(f"Displaying {len(df_shoppy)} products from Shoppy.gg (mock data).")

        # Columns to display - adjust as per the actual data model and needs
        # From src/models/ecommerce.py: ShoppyProduct
        # product_id, name, price, seller, description, url, fetched_at, parsed_at, category, stock_status
        columns_to_display = [
            "name", "price", "seller", "product_id",
            "category", "stock_status", "url", "fetched_at", "parsed_at"
        ]

        # Filter out columns that might not exist in the DataFrame to prevent errors
        displayable_columns = [col for col in columns_to_display if col in df_shoppy.columns]

        st.dataframe(df_shoppy[displayable_columns])

        # Allow data download
        st.download_button(
            label="Descargar datos como CSV",
            data=df_shoppy.to_csv(index=False).encode('utf-8'),
            file_name='shoppy_gg_products.csv',
            mime='text/csv',
        )
    elif df_shoppy is not None and df_shoppy.empty: # Explicitly check for empty DataFrame after loading
        st.info("Shoppy.gg data loaded, but it's currently empty. No products to display.")
    else:
        # load_shoppy_data() already shows warnings/errors
        logger.info("Shoppy.gg data DataFrame is None or could not be loaded.")

if __name__ == "__main__":
    # This part is for testing the component independently
    # You would need to create a dummy data/shoppy/shoppy_processed_data.json file
    # or run the mock ETL first.

    # Mock logger for standalone testing
    class MockLogger:
        def info(self, msg): print(f"INFO: {msg}")
        def warning(self, msg): print(f"WARNING: {msg}")
        def error(self, msg): print(f"ERROR: {msg}")

    # Create dummy data file for testing
    dummy_data_dir = "data/shoppy"
    os.makedirs(dummy_data_dir, exist_ok=True)
    dummy_data = [
        {
            "product_id": "mock1", "name": "Mock Product 1", "price": "10 USD",
            "seller": "Mock Seller A", "url": "http://example.com/mock1",
            "fetched_at": "2023-01-01T12:00:00", "parsed_at": "2023-01-01T12:05:00",
            "category": "Test", "stock_status": "Available"
        },
        {
            "product_id": "mock2", "name": "Mock Product 2", "price": "20 USD",
            "seller": "Mock Seller B", "url": "http://example.com/mock2",
            "fetched_at": "2023-01-01T13:00:00", "parsed_at": "2023-01-01T13:05:00",
            "category": "Another Test", "stock_status": "Limited"
        }
    ]
    with open(DATA_FILE_PATH, "w") as f:
        json.dump(dummy_data, f)

    render(MockLogger())

    # Clean up dummy file
    # os.remove(DATA_FILE_PATH)
    # print(f"Cleaned up {DATA_FILE_PATH}")
