from __future__ import annotations

"""Streamlit component: 4chan *General* threads visualisation.

The component loads the latest JSON produced by `FourChanGeneralsETL` and
presents the information divided by board in a set of sub-tabs.
"""

from pathlib import Path
import json
from typing import List, Dict, Any

import pandas as pd
import streamlit as st

from src.utils.logging import get_logger


DATA_FILE = Path("data/4chan_generals/output/latest.json")

def _load_data() -> List[Dict[str, Any]]:
    if not DATA_FILE.exists():
        return []
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover – runtime display
        logger = get_logger("4chanGeneralsTab")
        logger.error(f"Failed to load {DATA_FILE}: {exc}")
        return []

def _display_board(board: str, threads: List[Dict[str, Any]]):
    """Render a board section – simple table with clickable links."""

    if not threads:
        st.info("No active General threads detected.")
        return

    # Display as a native Streamlit dataframe for better compatibility
    df = pd.DataFrame(threads)
    if not df.empty:
        # Prepare display data
        display_df = df[
            [
                "subject",
                "replies", 
                "images",
                "last_modified",
                "url",
            ]
        ].copy()
        
        display_df.columns = ["Subject", "Replies", "Images", "Last Modified", "Thread URL"]
        
        # Use Streamlit's native dataframe display with clickable URLs
        st.dataframe(
            display_df,
            use_container_width=True,
            column_config={
                "Thread URL": st.column_config.LinkColumn(
                    "Thread URL",
                    help="Click to open the thread on 4chan",
                    display_text="View Thread"
                ),
                "Subject": st.column_config.TextColumn(
                    "Subject",
                    width="large"
                ),
                "Replies": st.column_config.NumberColumn(
                    "Replies",
                    format="%d"
                ),
                "Images": st.column_config.NumberColumn(
                    "Images", 
                    format="%d"
                ),
                "Last Modified": st.column_config.NumberColumn(
                    "Last Modified",
                    format="%d"
                )
            }
        )
    else:
        st.info("No data available for this board.")

def render(logger=None):  # pylint: disable=unused-argument
    """Public render function expected by the main app."""

    st.title("📑 4chan – Active *General* Threads")

    data = _load_data()
    if not data:
        st.warning(
            "No data found. Please run the *FourChanGeneralsETL* to generate the latest snapshot."
        )
        return

    # Group by board
    boards = sorted({item["board"] for item in data})
    grouped: Dict[str, List[Dict[str, Any]]] = {b: [] for b in boards}
    for item in data:
        grouped[item["board"]].append(item)

    board_tabs = st.tabs([f"/{b}/" for b in boards])
    for idx, board in enumerate(boards):
        with board_tabs[idx]:
            st.subheader(f"Board: /{board}/ – {len(grouped[board])} General threads")
            _display_board(board, grouped[board]) 