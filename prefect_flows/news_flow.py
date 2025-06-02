import sys
import os

# Add project root to sys.path to allow imports from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import necessary libraries from Prefect
from prefect import flow, task

# Import the main logic from the existing script
# Ensure the path is correct based on your project structure.
# If src is at the root of your project, this import should work.
# If you encounter ModuleNotFoundError, you might need to adjust PYTHONPATH or how you run the flow.
from src.etl.news.news_get_ycombinator import main as fetch_ycombinator_news_main

# Define a Prefect task that wraps the ycombinator news fetching logic
@task(name="Fetch YCombinator News")
def fetch_ycombinator_news_task():
    """
    A Prefect task that fetches the latest news from YCombinator
    by calling the main function from news_get_ycombinator.py.
    """
    print("Fetching YCombinator news...")
    try:
        fetch_ycombinator_news_main()
        print("Successfully fetched YCombinator news.")
        # Optionally, you could return some status or data here
        # For example, return the number of articles fetched if the main function provides it
    except Exception as e:
        print(f"Error fetching YCombinator news: {e}")
        # Re-raise the exception to mark the task as failed
        raise

# Define a Prefect flow that orchestrates the news fetching task(s)
@flow(name="Daily News Fetch Flow")
def daily_news_flow():
    """
    A Prefect flow that orchestrates the fetching of daily news.
    Currently, it only includes fetching news from YCombinator.
    """
    print("Starting the Daily News Fetch Flow...")
    fetch_ycombinator_news_task()
    print("Daily News Fetch Flow finished.")

# Main block to allow execution of the script,
# which can be useful for local testing or specific deployment patterns.
# For Prefect 2.x and later, flows are typically deployed using `prefect deploy`.
# Running this script directly (e.g., `python prefect_flows/news_flow.py`)
# will execute the flow locally if not imported as a module.
if __name__ == "__main__":
    # This will run the flow when the script is executed directly.
    # It's useful for local testing.
    # For deployments, Prefect will typically import the flow object.
    daily_news_flow()

    # To register this flow with a Prefect server/cloud and create a deployment
    # (which includes scheduling, parameters, etc.), you would typically use the Prefect CLI:
    #
    # 1. Ensure your Prefect server or agent is running.
    # 2. Navigate to your project directory in the terminal.
    # 3. Run a command like:
    #    prefect deploy --name "Daily News Deployment" --flow-path prefect_flows/news_flow.py:daily_news_flow --cron "0 8 * * *"
    #
    # This command does the following:
    #   - `prefect deploy`: Initiates the deployment process.
    #   - `--name "Daily News Deployment"`: Assigns a name to this deployment.
    #   - `--flow-path prefect_flows/news_flow.py:daily_news_flow`: Specifies the location of the flow definition.
    #     (path_to_file.py:flow_function_name)
    #   - `--cron "0 8 * * *"`: (Example) Sets a CRON schedule for the flow to run daily at 8 AM.
    #     Scheduling is highly flexible and can be defined in various ways.
    #
    # Alternatively, you can define deployments in a prefect.yaml file.
    # The `prefect init` command you ran earlier might have created a basic prefect.yaml.
    # You can define deployments there and then apply them using `prefect deploy -f prefect.yaml`.
    #
    # For now, this script just defines the flow. Scheduling and deployment
    # will be handled via Prefect's deployment mechanisms as a separate step.
    pass
