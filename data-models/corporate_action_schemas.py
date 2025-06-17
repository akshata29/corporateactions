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


# Process workflow enums and models for inquiry system
class InquiryStatus(str, Enum):
    """Inquiry status for process workflow"""
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    IN_REVIEW = "IN_REVIEW"
    RESPONDED = "RESPONDED"
    ESCALATED = "ESCALATED"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"

class InquiryPriority(str, Enum):
    """Inquiry priority levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"

class UserRole(str, Enum):
    """User roles for the application"""
    CONSUMER = "CONSUMER"
    ADMINISTRATOR = "ADMINISTRATOR"
    ANALYST = "ANALYST"
    SUPPORT = "SUPPORT"

class NotificationType(str, Enum):
    """Notification types for push notifications"""
    STATUS_CHANGE = "STATUS_CHANGE"
    NEW_RESPONSE = "NEW_RESPONSE"
    ESCALATION = "ESCALATION"
    RESOLUTION = "RESOLUTION"
    DEADLINE_REMINDER = "DEADLINE_REMINDER"

class ProcessInquiry(BaseModel):
    """Enhanced inquiry model for process workflow"""
    inquiry_id: str = Field(..., description="Unique inquiry identifier")
    event_id: str = Field(..., description="Related corporate action event ID")
    
    # User information
    user_id: str = Field(..., description="User identifier")
    user_name: str = Field(..., description="User display name")
    user_role: UserRole = Field(default=UserRole.CONSUMER, description="User role")
    organization: Optional[str] = Field(None, description="User's organization")
    
    # Inquiry details
    subject: str = Field(..., description="Inquiry subject/title")
    description: str = Field(..., description="Detailed inquiry description")
    priority: InquiryPriority = Field(default=InquiryPriority.MEDIUM, description="Inquiry priority")
    status: InquiryStatus = Field(default=InquiryStatus.OPEN, description="Current inquiry status")
    
    # Process tracking
    assigned_to: Optional[str] = Field(None, description="Administrator assigned to handle inquiry")
    response: Optional[str] = Field(None, description="Administrative response")
    resolution_notes: Optional[str] = Field(None, description="Final resolution notes")
    
    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    due_date: Optional[datetime] = Field(None, description="Expected response due date")
    resolved_at: Optional[datetime] = Field(None, description="Resolution timestamp")
    
    # Subscription and notification
    subscribers: List[str] = Field(default_factory=list, description="User IDs subscribed to this inquiry")
    notification_history: List[Dict[str, Any]] = Field(default_factory=list, description="Notification history")

class UserSubscription(BaseModel):
    """User subscription to corporate actions"""
    user_id: str = Field(..., description="User identifier")
    user_name: str = Field(..., description="User display name")
    organization: Optional[str] = Field(None, description="User's organization")
    
    # Subscription details
    symbols: List[str] = Field(default_factory=list, description="Subscribed stock symbols")
    event_types: List[CorporateActionType] = Field(default_factory=list, description="Subscribed event types")
    
    # Notification preferences
    notify_new_events: bool = Field(default=True, description="Notify on new events")
    notify_status_changes: bool = Field(default=True, description="Notify on status changes")
    notify_new_inquiries: bool = Field(default=True, description="Notify on new inquiries")
    notify_inquiry_responses: bool = Field(default=True, description="Notify on inquiry responses")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class NotificationEvent(BaseModel):
    """Notification event for push notifications"""
    notification_id: str = Field(..., description="Unique notification identifier")
    user_id: str = Field(..., description="Target user identifier")
    
    # Notification content
    type: NotificationType = Field(..., description="Type of notification")
    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification message")
    
    # Related entities
    event_id: Optional[str] = Field(None, description="Related corporate action event ID")
    inquiry_id: Optional[str] = Field(None, description="Related inquiry ID")
    
    # Delivery
    sent_at: Optional[datetime] = Field(None, description="When notification was sent")
    read_at: Optional[datetime] = Field(None, description="When notification was read")
    acknowledged_at: Optional[datetime] = Field(None, description="When notification was acknowledged")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
