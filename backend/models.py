from dataclasses import dataclass
from typing import Any, Dict, Optional
import pandas as pd


@dataclass
class CompanyFinancialModel:
    ticker: str
    profile: Optional[Dict[str, Any]] = None
    income_statement: Optional[pd.DataFrame] = None
    balance_sheet: Optional[pd.DataFrame] = None
    cash_flow: Optional[pd.DataFrame] = None
    financial_ratios: Optional[pd.DataFrame] = None
    key_metrics: Optional[pd.DataFrame] = None
    raw: Optional[Dict[str, Any]] = None

