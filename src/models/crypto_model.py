"""Crypto models for cryptocurrency asset metrics."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CryptoAsset(BaseModel):
    """Cryptocurrency asset market snapshot."""
    
    model_config = ConfigDict(extra="ignore")

    id: str = Field(..., description="Unique coin identifier")
    symbol: str = Field(..., description="Coin ticker symbol")
    name: str = Field(..., description="Full name of cryptocurrency")
    current_price: Optional[float] = Field(0.0, description="Current price in USD")
    market_cap: Optional[float] = Field(0.0, description="Total market capitalization")
    market_cap_rank: Optional[int] = Field(None, description="Global market cap rank")
    total_volume: Optional[float] = Field(0.0, description="24h trading volume")
    price_change_percentage_24h: Optional[float] = Field(0.0, description="24h price change percentage")
    last_updated: datetime = Field(..., description="Last timestamp of price update")
    
    data_type: str = Field("crypto_asset", description="Used for intel parsing")
