"""Base ETL class for Intelligence domains."""

from typing import Generic, TypeVar

from src.etl.base import BaseETL
from src.models.base import BaseModel

InputType = TypeVar("InputType")
OutputType = TypeVar("OutputType")


class BaseIntelligenceETL(BaseETL[InputType, OutputType], Generic[InputType, OutputType]):
    """Base class for Intelligence ETL processes.

    Adds capabilities for:
    - Trend analysis
    - Complexity scoring
    - Opportunity identification
    """

    def __init__(self, name: str, **kwargs):
        super().__init__(name, **kwargs)
        # Initialize intelligence engines here if needed globally
        # self.trend_detector = ...

    def enrich_with_intelligence(self, item: BaseModel) -> BaseModel:
        """Apply intelligence analysis to a single item.

        Override this in subclasses to apply specific intelligence models.
        """
        return item
