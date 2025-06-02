import streamlit as st
import json
from datetime import datetime

def load_data(filename="summarized_adv_posts.json"):
    """
    Loads JSON data from the specified file.
    Handles FileNotFoundError and JSONDecodeError.
    Returns the loaded data (list of dictionaries) or None if an error occurs.
    """
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        st.error(f"Error: The file '{filename}' was not found. Please run the ETL script first.")
        return None
    except json.JSONDecodeError:
        st.error(f"Error: Could not decode JSON from '{filename}'. The file might be corrupted or not valid JSON.")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred while loading '{filename}': {e}")
        return None

if __name__ == "__main__":
    st.set_page_config(layout="wide") # Use wide layout for better readability
    st.title("4chan Post Summaries Dashboard")

    # Determine the board name from the filename (simple approach)
    # TODO: Make this more robust if filenames change structure
    source_filename = "summarized_adv_posts.json" # Default, could be made dynamic

    # Attempt to extract board name from filename like "summarized_BOARD_posts.json"
    board_name_display = "adv" # Default
    try:
        if source_filename.startswith("summarized_") and source_filename.endswith("_posts.json"):
            board_name_display = source_filename.split("_")[1]
    except IndexError:
        pass # Keep default if parsing fails

    summarized_posts = load_data(source_filename)

    if summarized_posts:
        st.header(f"Summarized Posts from /{board_name_display}/")

        if not summarized_posts:
            st.warning("No posts found in the data file.")
        else:
            for post in summarized_posts:
                subject = post.get('subject', 'No Subject')
                thread_url = post.get('thread_url', '#')
                summary_text = post.get('summary_text', 'No summary available.')
                replies = post.get('replies', 0)
                images = post.get('images', 0)
                timestamp_unix = post.get('timestamp', 0)

                # Format timestamp
                try:
                    readable_time = datetime.fromtimestamp(timestamp_unix).strftime('%Y-%m-%d %H:%M:%S')
                except TypeError: # handles if timestamp is None or not a number
                    readable_time = "Invalid timestamp"
                except ValueError: # handles if timestamp is out of range
                     readable_time = f"Timestamp out of range: {timestamp_unix}"


                st.subheader(subject)

                col1, col2 = st.columns([4,1]) # Create two columns, first one wider

                with col1:
                    st.markdown(f"**Thread URL:** [{thread_url}]({thread_url})")
                    st.markdown(f"**Posted on:** {readable_time}")
                    st.markdown(f"**Replies:** {replies} | **Images:** {images}")

                # Displaying the summary text
                st.markdown("---") # Visual separator for sections within a post
                st.markdown("##### Summary:")
                st.markdown(f"> {summary_text}") # Blockquote style for summary

                # Displaying the full comment preview if significantly different from summary or longer
                full_comment_preview = post.get('full_comment_preview', '')
                if full_comment_preview and len(full_comment_preview) > len(summary_text) + 20: # Only show if substantially more
                    st.markdown("##### Full Comment Preview (first 500 chars):")
                    st.markdown(f"> {full_comment_preview}")

                st.markdown("---") # Separator between posts
    else:
        # Error messages are handled by load_data, but we can add a generic one here if needed
        st.info("No data to display. Ensure the ETL script has run and generated the data file.")

    st.sidebar.info(f"Data loaded from: {source_filename}")
    st.sidebar.markdown("Refresh the page to see new data if the source file is updated.")
    st.sidebar.markdown("---")
    st.sidebar.markdown("### About")
    st.sidebar.markdown("This dashboard displays summarized posts from 4chan, processed by the `etl_4chan.py` script.")

    # Example: Add a way to refresh data (though Streamlit's model usually handles this by rerun)
    if st.sidebar.button('Reload Data'):
        st.rerun()
