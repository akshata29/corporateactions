"""
Sample Corporate Action Data for Testing
"""

from datetime import date, datetime
from corporate_action_schemas import (
    CorporateActionEvent, CorporateActionType, EventStatus, 
    SecurityIdentifier, DividendDetails, StockSplitDetails, MergerDetails
)

# Sample Corporate Action Events
SAMPLE_EVENTS = [
    {
        "event_id": "CA-2025-001",
        "event_type": CorporateActionType.DIVIDEND,
        "security": {
            "symbol": "AAPL",
            "cusip": "037833100",
            "isin": "US0378331005"
        },
        "issuer_name": "Apple Inc.",
        "announcement_date": date(2025, 6, 1),
        "record_date": date(2025, 6, 15),
        "ex_date": date(2025, 6, 13),
        "payable_date": date(2025, 7, 1),
        "status": EventStatus.CONFIRMED,
        "description": "Quarterly cash dividend of $0.25 per share",
        "event_details": {
            "dividend_amount": 0.25,
            "currency": "USD",
            "dividend_type": "CASH",
            "tax_rate": 0.15
        },
        "data_source": "DTCC"
    },
    {
        "event_id": "CA-2025-002",
        "event_type": CorporateActionType.STOCK_SPLIT,
        "security": {
            "symbol": "TSLA",
            "cusip": "88160R101",
            "isin": "US88160R1014"
        },
        "issuer_name": "Tesla, Inc.",
        "announcement_date": date(2025, 5, 20),
        "record_date": date(2025, 6, 20),
        "ex_date": date(2025, 6, 21),
        "effective_date": date(2025, 6, 21),
        "status": EventStatus.ANNOUNCED,
        "description": "3-for-1 stock split to make shares more accessible to retail investors",
        "event_details": {
            "split_ratio_from": 1,
            "split_ratio_to": 3,
            "fractional_share_handling": "CASH_IN_LIEU"
        },
        "data_source": "EDGAR"
    },
    {
        "event_id": "CA-2025-003",
        "event_type": CorporateActionType.MERGER,
        "security": {
            "symbol": "TWTR",
            "cusip": "90184L102",
            "isin": "US90184L1026"
        },
        "issuer_name": "Twitter, Inc.",
        "announcement_date": date(2025, 4, 15),
        "record_date": date(2025, 6, 30),
        "effective_date": date(2025, 7, 15),
        "status": EventStatus.PENDING,
        "description": "Acquisition by X Holdings Corp. - Cash and stock consideration",
        "event_details": {
            "acquiring_company": "X Holdings Corp.",
            "acquiring_symbol": "X",
            "cash_consideration": 54.20,
            "stock_consideration": 0.5,
            "exchange_ratio": 1.0
        },
        "data_source": "SEC_FILING"
    },
    {
        "event_id": "CA-2025-004",
        "event_type": CorporateActionType.DIVIDEND,
        "security": {
            "symbol": "MSFT",
            "cusip": "594918104",
            "isin": "US5949181045"
        },
        "issuer_name": "Microsoft Corporation",
        "announcement_date": date(2025, 6, 10),
        "record_date": date(2025, 6, 25),
        "ex_date": date(2025, 6, 24),
        "payable_date": date(2025, 7, 10),
        "status": EventStatus.CONFIRMED,
        "description": "Quarterly cash dividend of $0.75 per share",
        "event_details": {
            "dividend_amount": 0.75,
            "currency": "USD",
            "dividend_type": "CASH",
            "tax_rate": 0.15
        },
        "data_source": "DTCC"
    },
    {
        "event_id": "CA-2025-005",
        "event_type": CorporateActionType.RIGHTS_OFFERING,
        "security": {
            "symbol": "GME",
            "cusip": "36467W109",
            "isin": "US36467W1099"
        },
        "issuer_name": "GameStop Corp.",
        "announcement_date": date(2025, 6, 5),
        "record_date": date(2025, 6, 18),
        "ex_date": date(2025, 6, 19),
        "effective_date": date(2025, 7, 5),
        "status": EventStatus.ANNOUNCED,
        "description": "Rights offering - 1 right for every 5 shares held, exercise price $15.00",
        "event_details": {
            "rights_ratio": "1:5",
            "exercise_price": 15.00,
            "currency": "USD",
            "subscription_period_start": date(2025, 6, 19),
            "subscription_period_end": date(2025, 7, 3)
        },
        "data_source": "COMPANY_FILING"
    }
]

# Sample Comments/Questions
SAMPLE_COMMENTS = [
    {
        "comment_id": "CMT-001",
        "event_id": "CA-2025-001",
        "user_id": "user_001",
        "user_name": "John Smith",
        "organization": "ABC Investment Management",
        "comment_type": "QUESTION",
        "content": "Has the tax treatment been confirmed for international shareholders?",
        "created_at": datetime(2025, 6, 2, 10, 30, 0),
        "is_resolved": False
    },
    {
        "comment_id": "CMT-002",
        "event_id": "CA-2025-002",
        "user_id": "user_002",
        "user_name": "Sarah Johnson",
        "organization": "XYZ Brokerage",
        "comment_type": "CONCERN",
        "content": "Need clarification on how fractional shares will be handled for our retail clients",
        "created_at": datetime(2025, 5, 21, 14, 15, 0),
        "is_resolved": False
    },
    {
        "comment_id": "CMT-003",
        "event_id": "CA-2025-003",
        "user_id": "user_003",
        "user_name": "Mike Davis",
        "organization": "DEF Custodian Bank",
        "comment_type": "QUESTION",
        "content": "What is the expected timeline for regulatory approval of this merger?",
        "created_at": datetime(2025, 4, 16, 9, 45, 0),
        "is_resolved": False
    },
    {
        "comment_id": "CMT-004",
        "event_id": "CA-2025-001",
        "user_id": "user_004",
        "user_name": "Lisa Brown",
        "organization": "GHI Asset Management",
        "comment_type": "UPDATE",
        "content": "Confirmed with transfer agent - payment will be processed on schedule",
        "created_at": datetime(2025, 6, 12, 16, 20, 0),
        "is_resolved": True
    }
]
