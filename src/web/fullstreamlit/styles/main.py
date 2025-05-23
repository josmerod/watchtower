"""
Main styling module for the Watchtower Streamlit application.
Contains all the CSS styling used throughout the application.
"""

def get_main_style():
    """Returns the main CSS styling for the application"""
    return """
<style>
    /* Import Google Fonts - Poppins */
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');
    
    /* Main app background and text */
    .stApp {
        background-color: #1E1E2E !important;
        color: #E2E8F0;
        font-family: 'Poppins', sans-serif !important;
    }
    
    /* Headers */
    h1, h2, h3, h4, h5, h6 {
        color: #A37FFF !important;
        font-family: 'Poppins', sans-serif !important;
        font-weight: 600 !important;
        letter-spacing: 0.5px;
    }
    
    /* Body text */
    p, div, span, li {
        font-family: 'Poppins', sans-serif !important;
        font-weight: 400;
        line-height: 1.6;
        color: #E2E8F0;
    }
    
    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
        background-color: #2D2B55;
        border-radius: 8px 8px 0 0;
        padding: 5px 5px 0 5px;
        flex-wrap: wrap;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #2D2B55;
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
        color: #CCC6F2;
        font-family: 'Poppins', sans-serif !important;
        font-weight: 500;
        transition: all 0.3s ease;
        white-space: nowrap;
        min-width: auto;
    }
    .stTabs [aria-selected="true"] {
        background-color: #A37FFF !important;
        color: #1E1E2E !important;
        font-weight: 600;
        box-shadow: 0 4px 6px rgba(163, 127, 255, 0.2);
    }
    
    /* Responsive tables */
    .stDataFrame {
        width: 100%;
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
    }
    
    table {
        background-color: #2D2B55 !important;
        border-collapse: collapse;
        width: 100%;
        border-radius: 8px;
        overflow: hidden;
        font-family: 'Poppins', sans-serif !important;
        min-width: 600px; /* Ensure minimum width for readability */
    }
    
    /* Responsive cards */
    .video-card {
        background-color: #2D2B55;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
        transition: all 0.3s ease;
        width: 100%;
        box-sizing: border-box;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
    }
    
    .video-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.4);
    }
    
    /* Video thumbnail container */
    .stImage img {
        width: 100%;
        border-radius: 6px;
        margin-bottom: 10px;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
        transition: transform 0.3s ease;
    }
    
    .stImage img:hover {
        transform: scale(1.03);
    }
    
    /* Video title styling */
    .element-container .stMarkdown h3 {
        margin-top: 0;
        margin-bottom: 8px;
        font-size: 1.1rem;
        line-height: 1.4;
        overflow: hidden;
        text-overflow: ellipsis;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
    }
    
    /* Responsive grid container */
    .grid-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 1rem;
        width: 100%;
    }
    
    /* Media queries for responsive layout */
    @media screen and (max-width: 768px) {
        .stTabs [data-baseweb="tab"] {
            padding: 8px 12px;
            font-size: 0.9rem;
        }
        
        table {
            font-size: 0.9rem;
        }
        
        th, td {
            padding: 8px;
        }
        
        .video-card {
            padding: 10px;
        }
    }
    
    @media screen and (max-width: 480px) {
        .stTabs [data-baseweb="tab"] {
            padding: 6px 10px;
            font-size: 0.8rem;
        }
        
        table {
            font-size: 0.8rem;
        }
        
        th, td {
            padding: 6px;
        }
    }
    
    /* Sidebar */
    .css-1d391kg, .css-1lcbmhc {
        background-color: #2D2B55 !important;
    }
    
    /* Buttons */
    .stButton button {
        background-color: #A37FFF !important;
        color: #1E1E2E !important;
        border: none !important;
        border-radius: 6px !important;
        font-family: 'Poppins', sans-serif !important;
        font-weight: 500 !important;
        padding: 8px 16px !important;
        transition: all 0.3s ease;
    }
    .stButton button:hover {
        background-color: #B792FF !important;
        box-shadow: 0 4px 8px rgba(163, 127, 255, 0.3);
        transform: translateY(-2px);
    }
    
    /* Quick action buttons styling */
    .quick-action-button {
        background: linear-gradient(135deg, #A37FFF 0%, #B792FF 100%) !important;
        color: #1E1E2E !important;
        border: none !important;
        border-radius: 8px !important;
        font-family: 'Poppins', sans-serif !important;
        font-weight: 600 !important;
        padding: 12px 16px !important;
        font-size: 0.95rem !important;
        transition: all 0.2s ease !important;
        position: relative !important;
        overflow: hidden !important;
        cursor: pointer !important;
    }
    
    .quick-action-button:hover {
        background: linear-gradient(135deg, #B792FF 0%, #C9A6FF 100%) !important;
        box-shadow: 0 6px 12px rgba(163, 127, 255, 0.4) !important;
        transform: translateY(-3px) !important;
    }
    
    .quick-action-button:active {
        transform: translateY(-1px) !important;
        box-shadow: 0 3px 6px rgba(163, 127, 255, 0.3) !important;
    }
    
    .quick-action-button:disabled {
        background: #4A4A6A !important;
        color: #8B8B8B !important;
        cursor: not-allowed !important;
        transform: none !important;
        box-shadow: none !important;
    }
    
    /* Quick links styling */
    .quick-link-button {
        background: linear-gradient(135deg, #2D2B55 0%, #3C3970 100%) !important;
        color: #E2E8F0 !important;
        border: 2px solid #A37FFF !important;
        border-radius: 8px !important;
        font-family: 'Poppins', sans-serif !important;
        font-weight: 500 !important;
        padding: 10px 16px !important;
        transition: all 0.2s ease !important;
    }
    
    .quick-link-button:hover {
        background: linear-gradient(135deg, #A37FFF 0%, #B792FF 100%) !important;
        color: #1E1E2E !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 8px rgba(163, 127, 255, 0.3) !important;
    }
    
    /* System status styling */
    .system-status {
        animation: pulse 2s ease-in-out infinite alternate;
    }
    
    @keyframes pulse {
        from { opacity: 0.8; }
        to { opacity: 1; }
    }
    
    /* Cards and tables */
    .card, div.stDataFrame {
        background-color: #2D2B55 !important;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 15px;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
    }
    
    /* Table styling */
    th {
        background-color: #3C3970 !important;
        color: #E2E8F0 !important;
        padding: 12px;
        font-weight: 600;
        text-transform: uppercase;
        font-size: 0.85em;
        letter-spacing: 0.5px;
    }
    td {
        padding: 10px 12px;
        border-bottom: 1px solid #3C3970;
        vertical-align: middle;
        color: #E2E8F0;
    }
    tr:nth-child(even) {
        background-color: #252343 !important;
    }
    tr:hover {
        background-color: #34325A !important;
    }
    
    /* Input fields */
    .stTextInput input, .stDateInput input, .stSelectbox select {
        border-radius: 6px !important;
        border: 1px solid #3C3970 !important;
        background-color: #252343 !important;
        color: #E2E8F0 !important;
        font-family: 'Poppins', sans-serif !important;
    }
    
    /* Links */
    a {
        color: #A37FFF !important;
        text-decoration: none;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    a:hover {
        color: #B792FF !important;
        text-decoration: underline;
    }
    
    /* Custom scrollbar for better UX */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    ::-webkit-scrollbar-track {
        background: #1E1E2E;
    }
    ::-webkit-scrollbar-thumb {
        background: #3C3970;
        border-radius: 10px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #A37FFF;
    }
    
    /* Warning messages */
    .stAlert {
        background-color: #3C3970 !important;
        color: #E2E8F0 !important;
    }
    
    /* Dropdown elements */
    .stSelectbox > div[data-baseweb="select"] > div {
        background-color: #252343 !important;
        color: #E2E8F0 !important;
    }
    
    /* Date input */
    .stDateInput > div[data-baseweb="input"] > div {
        background-color: #252343 !important;
        color: #E2E8F0 !important;
    }
    
    /* Success messages */
    div[data-testid="stSuccessMessage"] {
        background-color: #2D2B55 !important;
        color: #A5FFAF !important;
        border-color: #A5FFAF !important;
    }

    /* Deals container */
    .deals-container {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 1rem;
        width: 100%;
        padding: 1rem;
    }

    .deals-column {
        min-width: 0;
        width: 100%;
        background-color: #2D2B55;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
        height: 100%;
        overflow-x: auto;
    }

    .deals-card {
        background-color: #2D2B55;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
        border-left: 3px solid #A37FFF;
        height: 100%;
        overflow-x: auto;
    }

    /* News container */
    .news-container {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 1rem;
        width: 100%;
        padding: 1rem;
    }

    .news-column {
        min-width: 0;
        width: 100%;
        background-color: #2D2B55;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
        height: 100%;
        overflow-x: auto;
    }

    .news-card {
        background-color: #2D2B55;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
        border-left: 3px solid #A37FFF;
        height: 100%;
        overflow-x: auto;
    }

    /* Shortcuts styling */
    .shortcuts-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 1.5rem;
        width: 100%;
        padding: 1rem;
    }

    .shortcuts-category {
        background-color: #2D2B55;
        border-radius: 8px;
        padding: 15px;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
        border-top: 3px solid #A37FFF;
        height: 100%;
    }

    .shortcut-item {
        display: flex;
        align-items: center;
        background-color: #34325A;
        border-radius: 6px;
        padding: 12px;
        margin-bottom: 12px;
        transition: all 0.3s ease;
    }

    .shortcut-item:hover {
        transform: translateY(-3px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
        background-color: #3C3970;
    }

    .shortcut-icon {
        font-size: 24px;
        margin-right: 15px;
        min-width: 30px;
        text-align: center;
    }

    .shortcut-content {
        flex-grow: 1;
    }

    .shortcut-title {
        font-weight: 600;
        font-size: 16px;
        margin-bottom: 5px;
    }

    .shortcut-description {
        font-size: 13px;
        color: #CCC6F2;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }

    /* Table responsiveness */
    .stDataFrame {
        width: 100%;
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
    }

    table {
        width: 100%;
        min-width: 100%;
        margin-bottom: 0;
    }
</style>
""" 