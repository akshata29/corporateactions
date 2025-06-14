"""
Corporate Action Data Schemas
Based on DTCC Corporate Action Data Dictionary
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class CorporateActionType(str, Enum):
    """Corporate Action Event Types"""
    DIVIDEND = "DIVIDEND"
    STOCK_SPLIT = "STOCK_SPLIT"
    MERGER = "MERGER"
    SPIN_OFF = "SPIN_OFF"
    RIGHTS_OFFERING = "RIGHTS_OFFERING"
    STOCK_DIVIDEND = "STOCK_DIVIDEND"
    TENDER_OFFER = "TENDER_OFFER"
    REDEMPTION = "REDEMPTION"


class EventStatus(str, Enum):
    """Event Status"""
    ANNOUNCED = "ANNOUNCED"
    CONFIRMED = "CONFIRMED"
    RECORD_DATE_SET = "RECORD_DATE_SET"
    EX_DATE_SET = "EX_DATE_SET"
    PAYABLE_DATE_SET = "PAYABLE_DATE_SET"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    PENDING = "PENDING"


class SecurityIdentifier(BaseModel):
    """Security identification"""
    symbol: str = Field(..., description="Stock symbol")
    cusip: Optional[str] = Field(None, description="CUSIP identifier")
    isin: Optional[str] = Field(None, description="ISIN identifier")
    sedol: Optional[str] = Field(None, description="SEDOL identifier")


class CorporateActionEvent(BaseModel):
    """Main Corporate Action Event Model"""
    event_id: str = Field(..., description="Unique event identifier")
    event_type: CorporateActionType = Field(..., description="Type of corporate action")
    security: SecurityIdentifier = Field(..., description="Security identifiers")
    issuer_name: str = Field(..., description="Name of the issuing company")
    
    # Key Dates
    announcement_date: date = Field(..., description="Date the action was announced")
    record_date: Optional[date] = Field(None, description="Record date for eligibility")
    ex_date: Optional[date] = Field(None, description="Ex-dividend/ex-rights date")
    payable_date: Optional[date] = Field(None, description="Payment/distribution date")
    effective_date: Optional[date] = Field(None, description="Effective date of the action")
    
    # Event Details
    status: EventStatus = Field(..., description="Current status of the event")
    description: str = Field(..., description="Detailed description of the corporate action")
    
    # Event-specific data (varies by type)
    event_details: Dict[str, Any] = Field(default_factory=dict, description="Type-specific event details")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    data_source: str = Field(default="MANUAL", description="Source of the data")


class DividendDetails(BaseModel):
    """Dividend-specific details"""
    dividend_amount: float = Field(..., description="Dividend amount per share")
    currency: str = Field(default="USD", description="Currency of the dividend")
    dividend_type: str = Field(..., description="Type of dividend (CASH, STOCK, etc.)")
    tax_rate: Optional[float] = Field(None, description="Applicable tax rate")


class StockSplitDetails(BaseModel):
    """Stock Split-specific details"""
    split_ratio_from: int = Field(..., description="Original shares (e.g., 1 in 2:1 split)")
    split_ratio_to: int = Field(..., description="New shares (e.g., 2 in 2:1 split)")
    fractional_share_handling: str = Field(..., description="How fractional shares are handled")


class MergerDetails(BaseModel):
    """Merger-specific details"""
    acquiring_company: str = Field(..., description="Name of acquiring company")
    acquiring_symbol: Optional[str] = Field(None, description="Symbol of acquiring company")
    exchange_ratio: Optional[float] = Field(None, description="Exchange ratio")
    cash_consideration: Optional[float] = Field(None, description="Cash consideration per share")
    stock_consideration: Optional[float] = Field(None, description="Stock consideration ratio")


class UserComment(BaseModel):
    """User comments/questions on corporate actions"""
    comment_id: str = Field(..., description="Unique comment identifier")
    event_id: str = Field(..., description="Related corporate action event ID")
    user_id: str = Field(..., description="User identifier")
    user_name: str = Field(..., description="User display name")
    organization: Optional[str] = Field(None, description="User's organization")
    
    comment_type: str = Field(..., description="Type: QUESTION, CONCERN, COMMENT, UPDATE")
    content: str = Field(..., description="Comment content")
    
    # Threading support
    parent_comment_id: Optional[str] = Field(None, description="Parent comment for replies")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_resolved: bool = Field(default=False, description="Whether the question/concern is resolved")


class EventSearchQuery(BaseModel):
    """Search query model for corporate actions"""
    event_types: Optional[List[CorporateActionType]] = Field(None, description="Filter by event types")
    symbols: Optional[List[str]] = Field(None, description="Filter by stock symbols")
    cusips: Optional[List[str]] = Field(None, description="Filter by CUSIP identifiers")
    
    # Date range filters
    announcement_date_from: Optional[date] = Field(None, description="Announcement date from")
    announcement_date_to: Optional[date] = Field(None, description="Announcement date to")
    record_date_from: Optional[date] = Field(None, description="Record date from")
    record_date_to: Optional[date] = Field(None, description="Record date to")
    
    # Status filter
    statuses: Optional[List[EventStatus]] = Field(None, description="Filter by event status")
    
    # Text search
    search_text: Optional[str] = Field(None, description="Free text search")
    
    # Pagination
    limit: int = Field(default=50, description="Maximum number of results")
    offset: int = Field(default=0, description="Offset for pagination")


class EventStatusUpdate(BaseModel):
    """Model for updating event status"""
    event_id: str = Field(..., description="Event identifier")
    new_status: EventStatus = Field(..., description="New status")
    update_reason: Optional[str] = Field(None, description="Reason for status update")
    updated_by: str = Field(..., description="User who made the update")
    update_details: Optional[Dict[str, Any]] = Field(None, description="Additional update details")
