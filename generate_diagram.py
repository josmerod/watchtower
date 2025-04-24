from diagrams import Diagram, Cluster, Edge
from diagrams.programming.language import Python, Bash
from diagrams.onprem.network import Nginx
from diagrams.generic.compute import Rack
from diagrams.generic.storage import Storage
from diagrams.onprem.monitoring import Prometheus, Grafana
from diagrams.generic.database import SQL
from diagrams.generic.os import Windows, LinuxGeneral
from diagrams.onprem.client import User

# Create a more detailed diagram based on actual code structure
with Diagram("Watchtower Project Architecture", show=False, filename="project_diagram_detailed", direction="TB"):

    # User (manual interaction) and scheduler (cron/scheduled tasks)
    user = User("User")
    scheduler = Rack("Task Scheduler")

    # Management Scripts 
    with Cluster("Management Scripts"):
        bash_scripts = Bash(".sh Scripts")
        bat_scripts = Windows(".bat Scripts")
        ps_scripts = Windows(".ps1 Scripts")
    
    with Cluster("Data Storage"):
        with Cluster("Data"):
            games_data = Storage("Games Data")
            news_data = Storage("News Data")
            watcher_data = Storage("Watcher Data")
            golddigging_data = Storage("Golddigging Data")
        
        logs = Storage("Logs")

    # Main application code
    with Cluster("src"):
        # Orchestration layer
        with Cluster("Orchestrator"):
            meta_orchestrator = Python("Meta Orchestrator")
            etl_orchestrator = Python("ETL Orchestrator")
            genai_orchestrator = Python("GenAI Orchestrator")
            golddigging_orchestrator = Python("Golddigging Orchestrator")
        
        # Watchers (monitoring external sources)
        with Cluster("Watchers"):
            base_watcher = Python("Base Watcher")
            ms_skills_watcher = Python("MS Skills Watcher")
            watcher_runner = Python("Watcher Runner")
        
        # ETL processes (data extraction/transformation/loading)
        with Cluster("ETL Processes"):
            with Cluster("Games ETL"):
                games_etl = Python("Games ETL")
            with Cluster("News ETL"):
                news_etl = Python("News ETL")
            with Cluster("Golddigging ETL"):
                golddigging_etl = Python("Golddigging ETL")
        
        # Web interface (Streamlit)
        with Cluster("Web Interface"):
            streamlit_app = Nginx("Streamlit App")
            with Cluster("Components"):
                shortcuts_tab = Python("Shortcuts Tab")
                videos_tab = Python("Videos Tab")
                news_tab = Python("News Tab") 
                games_tab = Python("Games Tab")
                watchers_tab = Python("Watchers Tab")
                events_tab = Python("Events Tab")
                admin_tab = Python("Admin Tab")
        
        # Utilities
        with Cluster("Utils"):
            logging_util = Python("Logging Utility")
            file_system_util = Python("File System Utility")
    
    # Flow: User/Scheduler to Management Scripts
    user >> Edge(label="runs") >> bash_scripts
    user >> Edge(label="runs") >> bat_scripts
    user >> Edge(label="runs") >> ps_scripts
    
    scheduler >> Edge(label="triggers") >> bash_scripts
    scheduler >> Edge(label="triggers") >> bat_scripts
    scheduler >> Edge(label="triggers") >> ps_scripts
    
    # Management scripts to Orchestrators/Streamlit
    bash_scripts >> Edge(label="starts") >> meta_orchestrator
    bash_scripts >> Edge(label="starts") >> streamlit_app
    bat_scripts >> Edge(label="starts") >> meta_orchestrator
    bat_scripts >> Edge(label="starts") >> streamlit_app
    
    # Meta Orchestrator manages other orchestrators
    meta_orchestrator >> Edge(label="manages") >> etl_orchestrator
    meta_orchestrator >> Edge(label="manages") >> genai_orchestrator
    meta_orchestrator >> Edge(label="manages") >> golddigging_orchestrator
    
    # Orchestrators control ETL processes
    etl_orchestrator >> Edge(label="runs") >> games_etl
    etl_orchestrator >> Edge(label="runs") >> news_etl
    golddigging_orchestrator >> Edge(label="runs") >> golddigging_etl
    
    # Watchers monitor and trigger events
    ms_skills_watcher >> Edge(label="inherits from") >> base_watcher
    watcher_runner >> Edge(label="runs") >> ms_skills_watcher
    ms_skills_watcher >> Edge(label="triggers") >> etl_orchestrator
    
    # Data flow for ETLs
    games_etl >> Edge(label="writes") >> games_data
    news_etl >> Edge(label="writes") >> news_data
    golddigging_etl >> Edge(label="writes") >> golddigging_data
    ms_skills_watcher >> Edge(label="writes") >> watcher_data
    
    # Web app reads data
    games_tab >> Edge(label="reads") >> games_data
    news_tab >> Edge(label="reads") >> news_data
    watchers_tab >> Edge(label="reads") >> watcher_data
    
    # Streamlit app components
    streamlit_app >> shortcuts_tab
    streamlit_app >> videos_tab
    streamlit_app >> news_tab
    streamlit_app >> games_tab
    streamlit_app >> watchers_tab
    streamlit_app >> events_tab
    streamlit_app >> admin_tab
    
    # Logging
    meta_orchestrator >> Edge(label="writes") >> logs
    etl_orchestrator >> Edge(label="writes") >> logs
    games_etl >> Edge(label="writes") >> logs
    news_etl >> Edge(label="writes") >> logs
    ms_skills_watcher >> Edge(label="writes") >> logs
    streamlit_app >> Edge(label="writes") >> logs
    
    # Utils usage
    meta_orchestrator >> Edge(label="uses", style="dashed", color="lightgrey") >> logging_util
    etl_orchestrator >> Edge(label="uses", style="dashed", color="lightgrey") >> logging_util
    ms_skills_watcher >> Edge(label="uses", style="dashed", color="lightgrey") >> logging_util
    streamlit_app >> Edge(label="uses", style="dashed", color="lightgrey") >> logging_util
    base_watcher >> Edge(label="uses", style="dashed", color="lightgrey") >> file_system_util
    
print("Detailed diagram generated as project_diagram_detailed.png") 