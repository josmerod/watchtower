import sys
import os

# Add project root to sys.path to allow imports from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import necessary libraries from Prefect
from prefect import flow, task

# Import ETL logic
# Ensure the path is correct based on your project structure.
from src.etl.arxiv.arxiv_etl import ArxivETL
from src.etl.games.games_get_deals import get_deals, get_bundles, get_giveaways

# --- ArXiv Tasks ---

@task(name="Run ArXiv ETL")
def run_arxiv_etl_task(days_back: int = 7, max_results: int = 100):
    """
    A Prefect task that runs the ArXiv ETL process.

    Args:
        days_back (int): Number of days back to fetch ArXiv papers.
        max_results (int): Maximum number of ArXiv papers to fetch.
    """
    print(f"Starting ArXiv ETL task with days_back={days_back}, max_results={max_results}...")
    try:
        # Instantiate ArxivETL with provided parameters
        # Assuming 'arxiv_cs_papers' is a suitable name for this ETL instance
        etl_instance = ArxivETL(name="arxiv_cs_papers", days_back=days_back, max_results=max_results)
        # Run the ETL process
        etl_instance.run()
        print("ArXiv ETL task completed successfully.")
        # Optionally, return status or path to output files
    except Exception as e:
        print(f"Error during ArXiv ETL task: {e}")
        # Re-raise the exception to ensure the Prefect task is marked as failed
        raise

# --- Game Deals Tasks ---

@task(name="Fetch Game Deals")
def fetch_game_deals_task():
    """
    A Prefect task that fetches current game deals.
    """
    print("Starting Fetch Game Deals task...")
    try:
        get_deals()
        print("Fetch Game Deals task completed successfully.")
    except Exception as e:
        print(f"Error during Fetch Game Deals task: {e}")
        raise

@task(name="Fetch Game Bundles")
def fetch_game_bundles_task():
    """
    A Prefect task that fetches current game bundles.
    """
    print("Starting Fetch Game Bundles task...")
    try:
        get_bundles()
        print("Fetch Game Bundles task completed successfully.")
    except Exception as e:
        print(f"Error during Fetch Game Bundles task: {e}")
        raise

@task(name="Fetch Game Giveaways")
def fetch_game_giveaways_task():
    """
    A Prefect task that fetches current game giveaways.
    """
    print("Starting Fetch Game Giveaways task...")
    try:
        get_giveaways()
        print("Fetch Game Giveaways task completed successfully.")
    except Exception as e:
        print(f"Error during Fetch Game Giveaways task: {e}")
        raise

# --- Main Data Collection Flow ---

@flow(name="Periodic Data Collection Flow")
def periodic_data_collection_flow(arxiv_days_back: int = 7, arxiv_max_results: int = 100):
    """
    A Prefect flow that orchestrates the collection of data from ArXiv and game deal sources.
    - ArXiv ETL is run with configurable parameters.
    - Game deals, bundles, and giveaways are fetched.
    These two sets of operations (ArXiv and Games) run independently within this flow.
    """
    print("Starting Periodic Data Collection Flow...")
    print(f"Parameters: arxiv_days_back={arxiv_days_back}, arxiv_max_results={arxiv_max_results}")

    # Run ArXiv ETL
    # Parameters for the ArXiv task are passed from the flow's parameters
    run_arxiv_etl_task(days_back=arxiv_days_back, max_results=arxiv_max_results)

    # Run Game Deals tasks
    # These tasks run sequentially by default if called one after another.
    # If you wanted them to run in parallel and they are independent,
    # you could submit them and gather results, but for now, sequential is fine.
    deal_task_result = fetch_game_deals_task.submit()
    bundle_task_result = fetch_game_bundles_task.submit()
    giveaway_task_result = fetch_game_giveaways_task.submit()

    # Wait for game tasks to complete (optional if you don't need their results here,
    # but good practice if subsequent steps depend on them or for overall flow completion).
    # Using .wait() ensures they finish before the flow is considered complete.
    # If there were dependencies *between* game tasks, you'd use `wait_for` in submit.
    # Example: fetch_game_bundles_task.submit(wait_for=[deal_task_result])
    deal_task_result.wait()
    bundle_task_result.wait()
    giveaway_task_result.wait()

    print("Periodic Data Collection Flow finished.")

# Main block for local execution and testing
if __name__ == "__main__":
    # Example of running the flow locally with specific parameters
    periodic_data_collection_flow(arxiv_days_back=3, arxiv_max_results=50)

    # To deploy this flow (including scheduling, parameters, etc.),
    # you would typically use the Prefect CLI, similar to the news_flow.py:
    #
    # prefect deploy --name "Data Collection Deployment" \
    #                --flow-path prefect_flows/data_collection_flow.py:periodic_data_collection_flow \
    #                --cron "0 10 * * *" \
    #                --param arxiv_days_back=7 \
    #                --param arxiv_max_results=150
    #
    # This defines the flow. Scheduling and deployment are handled by Prefect Deployments.
    pass
