from pydantic import BaseModel, Field
from typing import List, Dict

class PredictionRequest(BaseModel):
    features: List[float] = Field(..., min_items=15, max_items=15, description="List of 15 numerical features")

class PredictionResponse(BaseModel):
    signal: int = Field(..., description="Trade signal: 1 (Buy), -1 (Sell), 0 (Neutral)")
    confidence: float = Field(..., description="Signal confidence")
    votes: Dict[str, int] = Field(..., description="Individual model votes")
