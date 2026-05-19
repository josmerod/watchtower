#!/bin/bash
echo "Starting ETL processes with Orchestrator at $(date)"
cd "$(dirname "$0")" || exit

# Run the python orchestrator with concurrent workers
if command -v uv &> /dev/null; then
    uv run python run_all_etl_orchestrator.py --workers 4
else
    echo "UV not found, falling back to python3"
    python3 run_all_etl_orchestrator.py --workers 4
fi

echo "ETL Workflow finished at $(date)."
