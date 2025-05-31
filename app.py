import streamlit as st
from goodreads_scraper import get_top_nonfiction_books

def main():
    # 1. Set page title
    st.set_page_config(page_title="Goodreads Non-Fiction", layout="wide")

    # 2. Add main header
    st.title("Goodreads Top Non-Fiction Books")
    st.subheader("Most Read This Week")

    # 3. Call function to fetch book data
    books = get_top_nonfiction_books()

    # 4. Check if list is empty
    if not books:
        st.warning("No books found or there was an error fetching data.")
        st.info("Please ensure `goodreads_scraper.py` is working correctly and check your internet connection.")
    else:
        # 5. If books are found, iterate and display
        st.markdown("### Here are the top non-fiction books from Goodreads for this week:")

        for i, book in enumerate(books):
            title = book.get('title', 'No Title Provided')
            url = book.get('goodreads_url', '#') # Default to '#' if URL is missing

            # Display book with a clickable link
            # Using st.markdown for link formatting
            st.markdown(f"{i+1}. [{title}]({url})", unsafe_allow_html=True)

            # Optional: Add a divider after each book, except the last one
            if i < len(books) - 1:
                st.divider()

if __name__ == '__main__':
    main()
