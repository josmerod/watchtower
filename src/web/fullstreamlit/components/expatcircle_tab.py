"""ExpatCircle News Tab Component.

This component displays data from ExpatCircle News, an expat-focused news aggregation site.
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

# Add the src directory to the Python path
current_dir = Path(__file__).parent
src_dir = current_dir.parent.parent.parent
sys.path.insert(0, str(src_dir))

from utils.logging import get_logger

logger = get_logger("expatcircle_tab")


def load_expatcircle_data():
    """Load ExpatCircle News data from JSON file."""
    try:
        # Get project root directory
        project_root = Path(__file__).parent.parent.parent.parent
        data_file = os.path.join(
            project_root, "data", "expatcircle", "expatcircle_posts.json"
        )

        if not os.path.exists(data_file):
            logger.warning(f"ExpatCircle data file not found: {data_file}")
            return pd.DataFrame()

        with open(data_file, encoding="utf-8") as f:
            data = json.load(f)

        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data)
        logger.info(f"Loaded {len(df)} ExpatCircle News posts")
        return df

    except Exception as e:
        logger.error(f"Error loading ExpatCircle data: {e!s}")
        return pd.DataFrame()


def display_expatcircle_metrics(df: pd.DataFrame):
    """Display overview metrics for ExpatCircle data."""
    if df.empty:
        st.warning("No ExpatCircle News data available")
        return

    # Calculate metrics
    total_posts = len(df)

    # Categories if available
    categories = df["category"].unique() if "category" in df.columns else []

    # Recent posts (last 7 days)
    if "published_date" in df.columns:
        try:
            df["published_date"] = pd.to_datetime(df["published_date"])
            recent_posts = len(
                df[df["published_date"] >= datetime.now() - timedelta(days=7)]
            )
        except:
            recent_posts = 0
    else:
        recent_posts = 0

    # Display metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Posts", total_posts)

    with col2:
        st.metric("Categories", len(categories))

    with col3:
        st.metric("Recent Posts (7d)", recent_posts)

    with col4:
        if "trending" in df.columns:
            trending_count = len(df[df["trending"]])
            st.metric("Trending", trending_count)
        else:
            st.metric(
                "Active Sources",
                df["source"].nunique() if "source" in df.columns else 0,
            )


def display_expatcircle_posts(df: pd.DataFrame):
    """Display ExpatCircle posts with filtering and sorting."""
    st.subheader("🌍 ExpatCircle News Posts")

    if df.empty:
        st.warning("No ExpatCircle posts available")
        return

    # Filtering options
    col1, col2, col3 = st.columns(3)

    with col1:
        if "category" in df.columns:
            categories = ["All", *list(df["category"].unique())]
            selected_category = st.selectbox(
                "Category", categories, key="expatcircle_category"
            )
        else:
            selected_category = "All"

    with col2:
        if "content_type" in df.columns:
            content_types = ["All", *list(df["content_type"].unique())]
            selected_content = st.selectbox(
                "Content Type", content_types, key="expatcircle_content"
            )
        else:
            selected_content = "All"

    with col3:
        trending_filter = st.selectbox(
            "Trending",
            ["All", "Trending Only", "Non-Trending"],
            key="expatcircle_trending",
        )

    # Apply filters
    filtered_df = df.copy()

    if selected_category != "All" and "category" in df.columns:
        filtered_df = filtered_df[filtered_df["category"] == selected_category]

    if selected_content != "All" and "content_type" in df.columns:
        filtered_df = filtered_df[filtered_df["content_type"] == selected_content]

    if trending_filter != "All" and "trending" in df.columns:
        if trending_filter == "Trending Only":
            filtered_df = filtered_df[filtered_df["trending"]]
        else:
            filtered_df = filtered_df[not filtered_df["trending"]]

    # Sorting
    sort_options = ["Published Date", "Title", "Category"]
    if "engagement_score" in filtered_df.columns:
        sort_options.append("Engagement Score")

    sort_by = st.selectbox("Sort by", sort_options, key="expatcircle_sort")

    # Sort the dataframe
    if sort_by == "Published Date" and "published_date" in filtered_df.columns:
        try:
            filtered_df["published_date"] = pd.to_datetime(
                filtered_df["published_date"]
            )
            filtered_df = filtered_df.sort_values("published_date", ascending=False)
        except:
            pass
    elif sort_by == "Title" and "title" in filtered_df.columns:
        filtered_df = filtered_df.sort_values("title")
    elif sort_by == "Category" and "category" in filtered_df.columns:
        filtered_df = filtered_df.sort_values("category")
    elif sort_by == "Engagement Score" and "engagement_score" in filtered_df.columns:
        filtered_df = filtered_df.sort_values("engagement_score", ascending=False)

    st.write(f"Showing {len(filtered_df)} posts")

    # Display posts
    for _index, post in filtered_df.head(
        50
    ).iterrows():  # Limit to 50 posts for performance
        with st.container():
            col1, col2 = st.columns([3, 1])

            with col1:
                # Title and link
                title = post.get("title", "No Title")
                url = post.get("url", "#")

                if url != "#":
                    st.markdown(f"### [{title}]({url})")
                else:
                    st.markdown(f"### {title}")

                # Description
                description = post.get("description", post.get("excerpt", ""))
                if description:
                    st.write(
                        description[:300] + "..."
                        if len(description) > 300
                        else description
                    )

                # Tags and metadata
                col_meta1, col_meta2, col_meta3 = st.columns(3)

                with col_meta1:
                    if post.get("category"):
                        st.badge(post["category"], type="secondary")

                with col_meta2:
                    if post.get("published_date"):
                        try:
                            pub_date = pd.to_datetime(post["published_date"])
                            st.caption(f"📅 {pub_date.strftime('%Y-%m-%d %H:%M')}")
                        except:
                            st.caption(f"📅 {post['published_date']}")

                with col_meta3:
                    if post.get("trending"):
                        st.badge("🔥 Trending", type="primary")

            with col2:
                # Engagement metrics if available
                if post.get("engagement_score"):
                    st.metric("Engagement", f"{post['engagement_score']:.1f}")

                if post.get("comments_count"):
                    st.caption(f"💬 {post['comments_count']} comments")

                if post.get("views_count"):
                    st.caption(f"👁️ {post['views_count']} views")

        st.divider()


def create_expatcircle_insights(df: pd.DataFrame) -> list[str]:
    """Create insights summary for ExpatCircle data."""
    if df.empty:
        return ["No ExpatCircle data available for analysis."]

    insights = []

    try:
        total_posts = len(df)
        insights.append(
            f"📊 **{total_posts}** total posts collected from ExpatCircle News"
        )

        # Category analysis
        if "category" in df.columns:
            top_categories = df["category"].value_counts().head(3)
            if not top_categories.empty:
                top_cat = top_categories.index[0]
                insights.append(
                    f"🏆 **{top_cat}** is the most active category with {top_categories.iloc[0]} posts"
                )

        # Trending analysis
        if "trending" in df.columns:
            trending_count = len(df[df["trending"]])
            if trending_count > 0:
                trending_pct = (trending_count / total_posts) * 100
                insights.append(
                    f"🔥 **{trending_count}** posts are trending ({trending_pct:.1f}%)"
                )

        # Recent activity
        if "published_date" in df.columns:
            try:
                df["published_date"] = pd.to_datetime(df["published_date"])
                recent_posts = len(
                    df[df["published_date"] >= datetime.now() - timedelta(days=7)]
                )
                if recent_posts > 0:
                    insights.append(
                        f"📈 **{recent_posts}** posts published in the last 7 days"
                    )
            except:
                pass

        # Content type distribution
        if "content_type" in df.columns:
            content_types = df["content_type"].value_counts()
            if not content_types.empty:
                primary_type = content_types.index[0]
                insights.append(f"📝 **{primary_type}** is the primary content type")

    except Exception as e:
        logger.error(f"Error creating insights: {e}")
        insights.append("⚠️ Unable to generate detailed insights")

    return insights


def render(logger):
    """Render the ExpatCircle News tab."""
    try:
        st.header("🌍 ExpatCircle News")
        st.markdown(
            "*Latest news and discussions from the international expat community*"
        )

        # Load data
        with st.spinner("Loading ExpatCircle News data..."):
            df = load_expatcircle_data()

        if df.empty:
            st.warning(
                "No ExpatCircle News data available. Please run the ETL process first."
            )
            st.info(
                "Run: `python src/etl/news/news_get_expatcircle.py` to collect ExpatCircle data."
            )
            return

        # Display metrics
        display_expatcircle_metrics(df)

        # Tabs for different views
        tab1, tab2, tab3 = st.tabs(["📋 Posts", "📊 Analytics", "💡 Insights"])

        with tab1:
            display_expatcircle_posts(df)

        with tab2:
            st.subheader("📊 ExpatCircle Analytics")

            # Category distribution
            if "category" in df.columns and not df["category"].isna().all():
                st.subheader("Categories Distribution")
                category_counts = df["category"].value_counts()
                st.bar_chart(category_counts)

            # Publishing timeline
            if "published_date" in df.columns:
                try:
                    df["published_date"] = pd.to_datetime(df["published_date"])
                    df["date"] = df["published_date"].dt.date
                    daily_posts = df.groupby("date").size()

                    st.subheader("Publishing Timeline")
                    st.line_chart(daily_posts)
                except Exception as e:
                    st.error(f"Error creating timeline: {e}")

        with tab3:
            st.subheader("💡 ExpatCircle Insights")
            insights = create_expatcircle_insights(df)

            for insight in insights:
                st.markdown(f"• {insight}")

        # Footer
        st.markdown("---")
        st.markdown("*Data refreshed from ExpatCircle News community*")

    except Exception as e:
        logger.error(f"Error in expatcircle_tab.render: {e!s}")
        st.error(f"Error loading ExpatCircle tab: {e!s}")


if __name__ == "__main__":
    # Test the component
    logger = get_logger("expatcircle_tab_test")
    render(logger)
