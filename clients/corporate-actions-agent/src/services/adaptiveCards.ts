/**
 * Adaptive Card templates for Corporate Actions Teams Bot
 */

export interface CorporateActionEvent {
  event_id?: string;
  company_name?: string;
  issuer_name?: string;
  symbol?: string;
  event_type?: string;
  description?: string;
  status?: string;
  announcement_date?: string;
  ex_date?: string;
  record_date?: string;
  payment_date?: string;
  event_details?: any;
}

export interface RAGResponse {
  answer: string;
  sources: CorporateActionEvent[];
  confidence_score: number;
  query_intent?: string;
  requires_visualization?: boolean;
  note?: string;
}

/**
 * Enhanced Adaptive Cards for Corporate Actions with Inquiry Management
 */

export function createDashboardCard(events: any[], inquiries: any[], userName: string): any {
    const now = new Date();
    const dateStr = now.toLocaleDateString('en-US', { 
        weekday: 'long', 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
    });

    // Build events section
    const eventsSection = events.slice(0, 5).map((event, index) => {
        const symbol = event.security?.symbol || event.symbol || 'N/A';
        const issuer = event.issuer_name || event.company_name || 'Unknown Company';
        const eventType = event.event_type?.replace('_', ' ') || 'Event';
        const status = event.status || 'Unknown';
        const description = event.description || 'No description available';
        
        // Get inquiry count for this event
        const eventInquiries = inquiries.filter(inq => inq.event_id === event.event_id);
        const openInquiries = eventInquiries.filter(inq => ['OPEN', 'ACKNOWLEDGED'].includes(inq.status));
        
        return {
            type: "Container",
            items: [
                {
                    type: "ColumnSet",
                    columns: [
                        {
                            type: "Column",
                            width: "stretch",
                            items: [
                                {
                                    type: "TextBlock",
                                    text: `🏢 **${issuer} (${symbol})**`,
                                    weight: "Bolder",
                                    size: "Medium"
                                },
                                {
                                    type: "TextBlock",
                                    text: `📋 ${eventType} • ${getStatusEmoji(status)} ${status}`,
                                    spacing: "None",
                                    isSubtle: true
                                },
                                {
                                    type: "TextBlock",
                                    text: description,
                                    spacing: "Small",
                                    wrap: true,
                                    maxLines: 2
                                },
                                ...(eventInquiries.length > 0 ? [{
                                    type: "TextBlock",
                                    text: `💬 ${eventInquiries.length} inquiries (${openInquiries.length} open)`,
                                    spacing: "Small",
                                    isSubtle: true,
                                    size: "Small"
                                }] : [])
                            ]
                        },
                        {
                            type: "Column",
                            width: "auto",
                            items: [
                                {
                                    type: "ActionSet",
                                    actions: [
                                        {
                                            type: "Action.Submit",
                                            title: "🆕",
                                            data: {
                                                action: "create_inquiry",
                                                event_id: event.event_id,
                                                company: issuer,
                                                symbol: symbol
                                            },
                                            tooltip: openInquiries.length > 0 ? "You have open inquiries" : "Create new inquiry"
                                        },
                                        {
                                            type: "Action.Submit",
                                            title: "👁️",
                                            data: {
                                                action: "view_inquiries",
                                                event_id: event.event_id,
                                                company: issuer,
                                                symbol: symbol
                                            },
                                            tooltip: "View all inquiries"
                                        },
                                        {
                                            type: "Action.Submit",
                                            title: "✏️",
                                            data: {
                                                action: "edit_inquiries",
                                                event_id: event.event_id,
                                                company: issuer,
                                                symbol: symbol
                                            },
                                            tooltip: openInquiries.length > 0 ? `Edit ${openInquiries.length} open inquiries` : "No inquiries to edit"
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ],
            separator: index > 0,
            spacing: "Medium"
        };
    });

    return {
        type: "AdaptiveCard",
        version: "1.5",
        body: [
            {
                type: "Container",
                style: "emphasis",
                items: [
                    {
                        type: "ColumnSet",
                        columns: [
                            {
                                type: "Column",
                                width: "stretch",
                                items: [
                                    {
                                        type: "TextBlock",
                                        text: "🏦 Corporate Actions Dashboard",
                                        size: "Large",
                                        weight: "Bolder",
                                        color: "Light"
                                    },
                                    {
                                        type: "TextBlock",
                                        text: `Welcome back, ${userName}! • ${dateStr}`,
                                        isSubtle: true,
                                        color: "Light"
                                    }
                                ]
                            },
                            {
                                type: "Column",
                                width: "auto",
                                items: [
                                    {
                                        type: "Image",
                                        url: "https://img.icons8.com/fluency/48/dashboard-layout.png",
                                        height: "40px"
                                    }
                                ]
                            }
                        ]
                    }
                ]
            },
            {
                type: "Container",
                items: [
                    {
                        type: "ColumnSet",
                        columns: [
                            {
                                type: "Column",
                                width: "stretch",
                                items: [
                                    {
                                        type: "TextBlock",
                                        text: "📊 Quick Stats",
                                        weight: "Bolder",
                                        size: "Medium"
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        type: "FactSet",
                        facts: [
                            {
                                title: "📈 Active Events",
                                value: events.filter(e => ['ANNOUNCED', 'CONFIRMED'].includes(e.status)).length.toString()
                            },
                            {
                                title: "💬 Total Inquiries",
                                value: inquiries.length.toString()
                            },
                            {
                                title: "📝 Open Inquiries",
                                value: inquiries.filter(inq => ['OPEN', 'ACKNOWLEDGED'].includes(inq.status)).length.toString()
                            },
                            {
                                title: "✅ Resolved",
                                value: inquiries.filter(inq => inq.status === 'RESOLVED').length.toString()
                            }
                        ]
                    }
                ]
            },
            {
                type: "Container",
                items: [
                    {
                        type: "TextBlock",
                        text: "📋 Recent Corporate Actions",
                        weight: "Bolder",
                        size: "Medium",
                        spacing: "Large"
                    },
                    {
                        type: "TextBlock",
                        text: "Click inquiry buttons to create (🆕), view (👁️), or edit (✏️) inquiries",
                        isSubtle: true,
                        size: "Small"
                    },
                    ...eventsSection
                ]
            }
        ],
        actions: [
            {
                type: "Action.Submit",
                title: "🔄 Refresh Dashboard",
                data: {
                    action: "refresh_dashboard"
                }
            },
            {
                type: "Action.Submit",
                title: "⚙️ Settings",
                data: {
                    action: "settings"
                }
            },
            {
                type: "Action.Submit",
                title: "📞 Help",
                data: {
                    action: "help"
                }
            }
        ]
    };
}

export function createInquiryFormCard(eventData: any, action: 'create' | 'edit', inquiryData?: any): any {
    const symbol = eventData.security?.symbol || eventData.symbol || 'N/A';
    const issuer = eventData.issuer_name || eventData.company_name || 'Unknown Company';
    const isEdit = action === 'edit';
    
    return {
        type: "AdaptiveCard",
        version: "1.5",
        body: [
            {
                type: "Container",
                style: "emphasis",
                items: [
                    {
                        type: "TextBlock",
                        text: `${isEdit ? '✏️ Edit Inquiry' : '🆕 Create New Inquiry'}`,
                        size: "Large",
                        weight: "Bolder",
                        color: "Light"
                    },
                    {
                        type: "TextBlock",
                        text: `${issuer} (${symbol})`,
                        isSubtle: true,
                        color: "Light"
                    }
                ]
            },
            {
                type: "Container",
                items: [
                    {
                        type: "TextBlock",
                        text: "📝 Inquiry Details",
                        weight: "Bolder",
                        size: "Medium"
                    },
                    {
                        type: "Input.Text",
                        id: "subject",
                        label: "Subject",
                        placeholder: "Brief description of your inquiry",
                        value: inquiryData?.subject || "",
                        isRequired: true
                    },
                    {
                        type: "Input.ChoiceSet",
                        id: "priority",
                        label: "Priority",
                        style: "compact",
                        value: inquiryData?.priority || "MEDIUM",
                        choices: [
                            { title: "🟢 Low", value: "LOW" },
                            { title: "🟡 Medium", value: "MEDIUM" },
                            { title: "🟠 High", value: "HIGH" },
                            { title: "🔴 Urgent", value: "URGENT" }
                        ]
                    },
                    {
                        type: "Input.Text",
                        id: "description",
                        label: "Description",
                        placeholder: "Provide detailed information about your inquiry...",
                        value: inquiryData?.description || "",
                        isMultiline: true,
                        isRequired: true
                    }
                ]
            }
        ],
        actions: [
            {
                type: "Action.Submit",
                title: isEdit ? "💾 Update Inquiry" : "✅ Create Inquiry",
                style: "positive",
                data: {
                    action: isEdit ? "update_inquiry" : "submit_inquiry",
                    event_id: eventData.event_id,
                    inquiry_id: inquiryData?.inquiry_id,
                    company: issuer,
                    symbol: symbol
                }
            },
            {
                type: "Action.Submit",
                title: "❌ Cancel",
                data: {
                    action: "cancel"
                }
            }
        ]
    };
}

export function createInquiriesListCard(inquiries: any[], eventData: any): any {
    const symbol = eventData.security?.symbol || eventData.symbol || 'N/A';
    const issuer = eventData.issuer_name || eventData.company_name || 'Unknown Company';
    
    const inquiryItems = inquiries.slice(0, 10).map((inquiry, index) => {
        const priorityColor = getPriorityColor(inquiry.priority);
        const statusColor = getStatusColor(inquiry.status);
        
        return {
            type: "Container",
            items: [
                {
                    type: "ColumnSet",
                    columns: [
                        {
                            type: "Column",
                            width: "stretch",
                            items: [
                                {
                                    type: "TextBlock",
                                    text: `📋 ${inquiry.subject || 'No Subject'}`,
                                    weight: "Bolder",
                                    wrap: true
                                },
                                {
                                    type: "ColumnSet",
                                    columns: [
                                        {
                                            type: "Column",
                                            width: "auto",
                                            items: [
                                                {
                                                    type: "TextBlock",
                                                    text: `${getPriorityEmoji(inquiry.priority)} ${inquiry.priority}`,
                                                    size: "Small",
                                                    weight: "Bolder"
                                                }
                                            ]
                                        },
                                        {
                                            type: "Column",
                                            width: "auto",
                                            items: [
                                                {
                                                    type: "TextBlock",
                                                    text: `${getStatusEmoji(inquiry.status)} ${inquiry.status}`,
                                                    size: "Small",
                                                    isSubtle: true
                                                }
                                            ]
                                        }
                                    ]
                                },
                                {
                                    type: "TextBlock",
                                    text: `👤 ${inquiry.user_name} (${inquiry.organization || 'N/A'})`,
                                    size: "Small",
                                    isSubtle: true
                                },
                                {
                                    type: "TextBlock",
                                    text: inquiry.description || 'No description',
                                    wrap: true,
                                    maxLines: 3,
                                    size: "Small"
                                },
                                ...(inquiry.response ? [{
                                    type: "TextBlock",
                                    text: `💬 **Response:** ${inquiry.response}`,
                                    wrap: true,
                                    size: "Small",
                                    color: "Good"
                                }] : [])
                            ]
                        }
                    ]
                }
            ],
            separator: index > 0,
            spacing: "Medium"
        };
    });

    return {
        type: "AdaptiveCard",
        version: "1.5",
        body: [
            {
                type: "Container",
                style: "emphasis",
                items: [
                    {
                        type: "TextBlock",
                        text: "👁️ View Inquiries",
                        size: "Large",
                        weight: "Bolder",
                        color: "Light"
                    },
                    {
                        type: "TextBlock",
                        text: `${issuer} (${symbol}) • ${inquiries.length} inquiries`,
                        isSubtle: true,
                        color: "Light"
                    }
                ]
            },
            {
                type: "Container",
                items: inquiryItems.length > 0 ? inquiryItems : [
                    {
                        type: "TextBlock",
                        text: "📭 No inquiries found for this corporate action",
                        horizontalAlignment: "Center",
                        isSubtle: true
                    }
                ]
            }
        ],
        actions: [
            {
                type: "Action.Submit",
                title: "🔙 Back to Dashboard",
                data: {
                    action: "back_to_dashboard"
                }
            }
        ]
    };
}

// Helper functions for styling
function getStatusEmoji(status: string): string {
    const emojiMap: { [key: string]: string } = {
        'ANNOUNCED': '📢',
        'CONFIRMED': '✅', 
        'COMPLETED': '🎯',
        'PENDING': '⏳',
        'CANCELLED': '❌',
        'OPEN': '🟡',
        'ACKNOWLEDGED': '🟠',
        'IN_REVIEW': '🔵',
        'RESPONDED': '🟢',
        'ESCALATED': '🔴',
        'RESOLVED': '✅',
        'CLOSED': '⚫'
    };
    return emojiMap[status] || '📋';
}

function getPriorityEmoji(priority: string): string {
    const emojiMap: { [key: string]: string } = {
        'LOW': '🟢',
        'MEDIUM': '🟡',
        'HIGH': '🟠',
        'URGENT': '🔴'
    };
    return emojiMap[priority] || '🟡';
}

function getPriorityColor(priority: string): string {
    const colorMap: { [key: string]: string } = {
        'LOW': 'Good',
        'MEDIUM': 'Warning', 
        'HIGH': 'Attention',
        'URGENT': 'Destructive'
    };
    return colorMap[priority] || 'Default';
}

function getStatusColor(status: string): string {
    const colorMap: { [key: string]: string } = {
        'OPEN': 'Warning',
        'ACKNOWLEDGED': 'Attention',
        'IN_REVIEW': 'Accent',
        'RESPONDED': 'Good',
        'ESCALATED': 'Destructive',
        'RESOLVED': 'Good',
        'CLOSED': 'Default'
    };
    return colorMap[status] || 'Default';
}

/**
 * Get event type emoji
 */
function getEventEmoji(eventType: string): string {
  const eventEmojis: { [key: string]: string } = {
    'dividend': '💰',
    'stock_split': '📊',
    'merger': '🤝',
    'spinoff': '🔄',
    'special_dividend': '💎',
    'rights_offering': '🎫',
    'stock_buyback': '🔙'
  };
  return eventEmojis[eventType] || '📋';
}

/**
 * Format date for display
 */
function formatDate(dateString: string | undefined): string {
  if (!dateString) return 'N/A';
  try {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  } catch {
    return dateString;
  }
}

/**
 * Create an Adaptive Card for RAG search results
 */
export function createRAGSearchCard(response: RAGResponse, query: string): any {
  const { answer, sources, confidence_score, note } = response;
  
  // Confidence indicator
  let confidenceText = '';
  if (confidence_score > 0.8) {
    confidenceText = `High Confidence (${(confidence_score * 100).toFixed(0)}%)`;
  } else if (confidence_score > 0.6) {
    confidenceText = `Medium Confidence (${(confidence_score * 100).toFixed(0)}%)`;
  } else {
    confidenceText = `Lower Confidence (${(confidence_score * 100).toFixed(0)}%)`;
  }

  const card: any = {
    type: "AdaptiveCard",
    $schema: "http://adaptivecards.io/schemas/adaptive-card.json",
    version: "1.4",
    body: [
      {
        type: "Container",
        style: "emphasis",
        items: [
          {
            type: "TextBlock",
            text: "🤖 AI-Powered Search Results",
            weight: "Bolder",
            size: "Medium",
            color: "Accent"
          },
          {
            type: "TextBlock",
            text: `Query: "${query}"`,
            size: "Small",
            isSubtle: true
          }
        ]
      },
      {
        type: "Container",
        spacing: "Medium",
        items: [
          {
            type: "TextBlock",
            text: answer,
            wrap: true
          }
        ]
      },
      {
        type: "FactSet",
        facts: [
          {
            title: "Confidence:",
            value: confidenceText
          }
        ]
      }
    ]
  };

  // Add note if present
  if (note) {
    (card.body[2] as any).facts.push({
      title: "Note:",
      value: note
    });
  }

  // Add related events section if sources exist
  if (sources && sources.length > 0) {
    const relatedEvents = sources.slice(0, 3).map((source) => {
      const company = source.issuer_name || source.company_name || 'Unknown Company';
      const eventType = (source.event_type || 'unknown').replace('_', ' ');
      const status = source.status || 'Unknown';
      const eventId = source.event_id || 'N/A';
      
      return {
        type: "Container",
        spacing: "Small",
        items: [
          {
            type: "TextBlock",
            text: `${getEventEmoji(source.event_type || '')} **${company}**`,
            weight: "Bolder"
          },
          {
            type: "TextBlock",
            text: `${eventType.toUpperCase()} • ${status} • ID: ${eventId}`,
            size: "Small",
            isSubtle: true
          }
        ],
        selectAction: {
          type: "Action.Submit",
          data: {
            action: "viewEventDetails",
            eventId: eventId
          }
        }
      };
    });

    card.body.push({
      type: "Container",
      spacing: "Medium",
      items: [
        {
          type: "TextBlock",
          text: "🔗 Related Events",
          weight: "Bolder",
          size: "Medium"
        },
        ...relatedEvents
      ]
    });
  }

  return card;
}

/**
 * Create an Adaptive Card for events listing
 */
export function createEventsListCard(events: CorporateActionEvent[], title?: string): any {
  // Group events by type
  const groupedEvents: { [key: string]: CorporateActionEvent[] } = {};
  events.forEach((event) => {
    const type = event.event_type || 'unknown';
    if (!groupedEvents[type]) groupedEvents[type] = [];
    groupedEvents[type].push(event);
  });

  const card: any = {
    type: "AdaptiveCard",
    $schema: "http://adaptivecards.io/schemas/adaptive-card.json",
    version: "1.4",
    body: [
      {
        type: "Container",
        style: "emphasis",
        items: [
          {
            type: "TextBlock",
            text: title || "📊 Recent Corporate Actions",
            weight: "Bolder",
            size: "Medium",
            color: "Accent"
          },
          {
            type: "TextBlock",
            text: `${events.length} events found`,
            size: "Small",
            isSubtle: true
          }
        ]
      }
    ]
  };

  // Add event type sections
  Object.entries(groupedEvents).forEach(([type, typeEvents]) => {
    const typeName = type.replace('_', ' ').toUpperCase();
    const emoji = getEventEmoji(type);
    
    const eventItems = typeEvents.slice(0, 3).map((event) => {
      const company = event.issuer_name || event.company_name || 'Unknown Company';
      const status = event.status || 'Unknown';
      const eventId = event.event_id || 'N/A';
      const description = event.description || 'No description available';
      
      // Format event-specific details
      let detailsText = '';
      if (event.event_details) {
        if (type === 'dividend' && event.event_details.dividend_amount) {
          detailsText = `Amount: $${event.event_details.dividend_amount}`;
        } else if (type === 'stock_split' && event.event_details.split_ratio) {
          detailsText = `Ratio: ${event.event_details.split_ratio}`;
        }
      }
      
      const facts = [
        { title: "Status:", value: status },
        { title: "Event ID:", value: eventId }
      ];
      
      if (detailsText) {
        facts.push({ title: "Details:", value: detailsText });
      }
      
      if (event.ex_date) {
        facts.push({ title: "Ex-Date:", value: formatDate(event.ex_date) });
      }
      
      if (event.payment_date) {
        facts.push({ title: "Payment Date:", value: formatDate(event.payment_date) });
      }

      return {
        type: "Container",
        spacing: "Small",
        items: [
          {
            type: "TextBlock",
            text: company,
            weight: "Bolder"
          },
          {
            type: "TextBlock",
            text: description,
            wrap: true,
            maxLines: 2
          },
          {
            type: "FactSet",
            facts: facts
          }
        ],
        selectAction: {
          type: "Action.Submit",
          data: {
            action: "viewEventDetails",
            eventId: eventId
          }
        }
      };
    });

    card.body.push({
      type: "Container",
      spacing: "Medium",
      items: [
        {
          type: "TextBlock",
          text: `${emoji} ${typeName} EVENTS (${typeEvents.length})`,
          weight: "Bolder",
          color: "Accent"
        },
        ...eventItems
      ]
    });
  });

  // Add actions
  card.body.push({
    type: "ActionSet",
    actions: [
      {
        type: "Action.Submit",
        title: "🔄 Refresh Events",
        data: {
          action: "refreshEvents"
        }
      },
      {
        type: "Action.Submit", 
        title: "🔍 Search Events",
        data: {
          action: "searchEvents"
        }
      }
    ]
  });

  return card;
}

/**
 * Create an error Adaptive Card
 */
export function createErrorCard(error: string, title: string = "❌ Error"): any {
  return {
    type: "AdaptiveCard",
    $schema: "http://adaptivecards.io/schemas/adaptive-card.json",
    version: "1.4",
    body: [
      {
        type: "Container",
        style: "attention",
        items: [
          {
            type: "TextBlock",
            text: title,
            weight: "Bolder",
            size: "Medium",
            color: "Attention"
          },
          {
            type: "TextBlock",
            text: error,
            wrap: true
          }
        ]
      },
      {
        type: "ActionSet",
        actions: [
          {
            type: "Action.Submit",
            title: "🔄 Try Again",
            data: {
              action: "retry"
            }
          },
          {
            type: "Action.Submit",
            title: "ℹ️ Help",
            data: {
              action: "help"
            }
          }
        ]
      }
    ]
  };
}

/**
 * Create a help Adaptive Card
 */
export function createHelpCard(): any {
  return {
    type: "AdaptiveCard",
    $schema: "http://adaptivecards.io/schemas/adaptive-card.json",
    version: "1.4",
    body: [
      {
        type: "Container",
        style: "emphasis",
        items: [
          {
            type: "ColumnSet",
            columns: [
              {
                type: "Column",
                width: "auto",
                items: [
                  {
                    type: "TextBlock",
                    text: "🤖",
                    size: "ExtraLarge"
                  }
                ]
              },
              {
                type: "Column",
                width: "stretch",
                items: [
                  {
                    type: "TextBlock",
                    text: "Corporate Actions AI Assistant",
                    weight: "Bolder",
                    size: "Large",
                    color: "Light"
                  },
                  {
                    type: "TextBlock",
                    text: "Enhanced with inquiry management and real-time dashboard",
                    color: "Light",
                    isSubtle: true
                  }
                ]
              }
            ]
          }
        ]
      },
      {
        type: "Container",
        spacing: "Medium",
        items: [
          {
            type: "TextBlock",
            text: "🏠 **Dashboard & Inquiry Management**",
            weight: "Bolder",
            size: "Medium",
            color: "Accent"
          },
          {
            type: "TextBlock",
            text: "• Type `dashboard` or `home` for interactive corporate actions dashboard\n• 📝 Create, view, and edit inquiries directly from the dashboard\n• 🚦 Smart controls prevent duplicate open inquiries\n• 🔄 Real-time status updates and personalized insights",
            wrap: true,
            spacing: "Small"
          }
        ]
      },
      {
        type: "Container",
        spacing: "Medium",
        items: [
          {
            type: "TextBlock",
            text: "📋 **Available Commands**",
            weight: "Bolder",
            size: "Medium",
            color: "Accent"
          },
          {
            type: "FactSet",
            facts: [
              { title: "dashboard, home", value: "Interactive dashboard with inquiry management" },
              { title: "/search [query]", value: "AI-powered search with confidence scoring" },
              { title: "/events", value: "Recent corporate actions with smart filtering" },
              { title: "/inquiries list", value: "Show recent events with IDs for reference" },
              { title: "/inquiries [event_id]", value: "View all inquiries for a specific event" },
              { title: "/create-inquiry [event_id]", value: "Create new inquiry for an event" },
              { title: "/edit-inquiry [inquiry_id]", value: "Edit your existing inquiry" },
              { title: "/edit-inquiry", value: "Show your inquiries to select for editing" },
              { title: "/subscribe [symbols]", value: "Multi-symbol smart subscriptions" },
              { title: "/unsubscribe [symbols]", value: "Remove specific symbol notifications" },
              { title: "/notifications settings", value: "Configure notification preferences" },
              { title: "/notifications history", value: "View recent notification history" },
              { title: "/comment [id] [text]", value: "Add structured comments to events" },
              { title: "/status", value: "Check MCP server health and capabilities" },
              { title: "/help", value: "Show this comprehensive help guide" }
            ]
          }
        ]
      },
      {
        type: "Container",
        spacing: "Medium",
        items: [
          {
            type: "TextBlock",
            text: "📋 **Inquiry Management Rules**",
            weight: "Bolder",
            size: "Medium",
            color: "Attention"
          },
          {
            type: "TextBlock",
            text: "• 🚫 **One Active Inquiry Rule**: Only one open inquiry per event per user\n• ✅ **Resolution Required**: Resolve existing inquiries before creating new ones\n• ✏️ **Edit Anytime**: Modify your inquiries until they're resolved\n• 👥 **View All**: See all inquiries but only edit your own",
            wrap: true,
            spacing: "Small"
          }
        ]
      },
      {
        type: "Container",
        spacing: "Medium",
        items: [
          {
            type: "TextBlock",
            text: "💡 **Example Queries**",
            weight: "Bolder",
            size: "Medium",
            color: "Accent"
          },
          {
            type: "TextBlock",
            text: "• \"What dividend events happened this week with amounts over $2?\"\n• \"Show me upcoming stock splits and their ratios\"\n• \"Analyze merger activity in the technology sector\"\n• \"Do I have any open inquiries for Apple events?\"\n• \"What's the status of my Tesla inquiry?\"",
            wrap: true,
            spacing: "Small"
          }
        ]
      },
      {
        type: "Container",
        spacing: "Medium",
        items: [
          {
            type: "TextBlock",
            text: "🎯 **Getting Started**",
            weight: "Bolder",
            size: "Medium",
            color: "Good"
          },
          {
            type: "TextBlock",
            text: "1. Type `dashboard` to see the main interface\n2. Browse upcoming corporate actions\n3. Click \"🆕\" to create inquiries for events\n4. Use \"👁️\" to view all inquiries or \"✏️\" to edit yours\n5. Subscribe to symbols with `/subscribe AAPL,MSFT`",
            wrap: true,
            spacing: "Small"
          }
        ]
      }
    ],
    actions: [
      {
        type: "Action.Submit",
        title: "🏠 Open Dashboard",
        style: "positive",
        data: {
          action: "refresh_dashboard"
        }
      },
      {
        type: "Action.Submit",
        title: "📊 View Recent Events",
        data: {
          action: "view_events"
        }
      },
      {
        type: "Action.Submit",
        title: "🔍 Search Events",
        data: {
          action: "search_prompt"
        }
      },
      {
        type: "Action.Submit",
        title: "⚙️ Settings",
        data: {
          action: "settings"
        }
      }
    ]
  };
}

/**
 * Create a status Adaptive Card
 */
export function createStatusCard(statusData: any): any {
  const { health, botStatus, notificationStats, serverUrls } = statusData;
  
  // Determine overall health status
  const healthStatuses = Object.values(health || {}).map((status: any) => status.status);
  const overallHealth = healthStatuses.includes('error') ? 'error' : 
                       healthStatuses.includes('warning') ? 'warning' : 'healthy';
  
  const healthColor = overallHealth === 'healthy' ? 'good' : 
                     overallHealth === 'warning' ? 'warning' : 'attention';

  return {
    type: "AdaptiveCard",
    $schema: "http://adaptivecards.io/schemas/adaptive-card.json",
    version: "1.4",
    body: [
      {
        type: "Container",
        style: "emphasis",
        items: [
          {
            type: "ColumnSet",
            columns: [
              {
                type: "Column",
                width: "auto",
                items: [
                  {
                    type: "Image",
                    url: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='%23007acc' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z'%3E%3C/path%3E%3C/svg%3E",
                    width: "24px",
                    height: "24px"
                  }
                ]
              },
              {
                type: "Column",
                width: "stretch",
                items: [
                  {
                    type: "TextBlock",
                    text: "🔧 System Status Report",
                    weight: "bolder",
                    size: "medium",
                    color: "accent"
                  },
                  {
                    type: "TextBlock",
                    text: `Overall Status: ${overallHealth.toUpperCase()}`,
                    size: "small",
                    color: healthColor,
                    weight: "bolder"
                  }
                ]
              }
            ]
          }
        ]
      },
      {
        type: "Container",
        spacing: "medium",
        items: [
          {
            type: "TextBlock",
            text: "🖥️ **MCP Server Health**",
            weight: "bolder",
            size: "medium"
          },
          {
            type: "FactSet",
            facts: Object.entries(health || {}).map(([name, status]: [string, any]) => ({
              title: `${name.toUpperCase()}:`,
              value: status.status === 'healthy' ? '✅ Healthy' : 
                     status.status === 'warning' ? '⚠️ Warning' : '❌ Error'
            }))
          }
        ]
      },
      {
        type: "Container",
        spacing: "medium",
        items: [
          {
            type: "TextBlock",
            text: "🤖 **Teams Bot Status**",
            weight: "bolder",
            size: "medium"
          },
          {
            type: "FactSet",
            facts: [
              {
                title: "Status:",
                value: "✅ Active and responding"
              },
              {
                title: "Port:",
                value: `${botStatus?.port || 3978}`
              },
              {
                title: "MCP Client:",
                value: botStatus?.mcpReady ? "✅ Ready" : "⏳ Initializing"
              }
            ]
          }
        ]
      },
      {
        type: "Container",
        spacing: "medium",
        items: [
          {
            type: "TextBlock",
            text: "🔔 **Notification Service**",
            weight: "bolder",
            size: "medium"
          },
          {
            type: "FactSet",
            facts: [
              {
                title: "Status:",
                value: notificationStats?.isRunning ? "✅ Running" : "❌ Stopped"
              },
              {
                title: "Active Subscriptions:",
                value: `${notificationStats?.totalSubscriptions || 0}`
              },
              {
                title: "Tracked Symbols:",
                value: `${notificationStats?.uniqueSymbols || 0}`
              },
              {
                title: "Notifications Sent:",
                value: `${notificationStats?.totalNotificationsSent || 0}`
              },
              ...(notificationStats?.successRate ? [{
                title: "Success Rate:",
                value: `${notificationStats.successRate.toFixed(1)}%`
              }] : [])
            ]
          }
        ]
      },
      {
        type: "Container",
        spacing: "medium",
        items: [
          {
            type: "TextBlock",
            text: "🌐 **Server URLs**",
            weight: "bolder",
            size: "medium"
          },
          {
            type: "FactSet",
            facts: Object.entries(serverUrls || {}).map(([name, url]) => ({
              title: `${name}:`,
              value: url as string
            }))
          }
        ]
      },
      {
        type: "ActionSet",
        actions: [
          {
            type: "Action.Submit",
            title: "🔄 Refresh Status",
            data: {
              action: "refreshStatus"
            }
          },
          {
            type: "Action.Submit",
            title: "🔍 Test Search",
            data: {
              action: "testSearch"
            }
          },
          {
            type: "Action.Submit",
            title: "📊 View Events",
            data: {
              action: "viewEvents"
            }
          }
        ]
      }
    ]
  };
}

/**
 * Create a subscription success Adaptive Card
 */
export function createSubscriptionCard(symbols: string[], isSuccess: boolean, message?: string): any {
  const cardColor = isSuccess ? "good" : "attention";
  const statusIcon = isSuccess ? "✅" : "❌";
  const title = isSuccess ? "Subscription Added Successfully!" : "Subscription Error";

  return {
    type: "AdaptiveCard",
    $schema: "http://adaptivecards.io/schemas/adaptive-card.json",
    version: "1.4",
    body: [
      {
        type: "Container",
        style: isSuccess ? "good" : "attention",
        items: [
          {
            type: "ColumnSet",
            columns: [
              {
                type: "Column",
                width: "auto",
                items: [
                  {
                    type: "TextBlock",
                    text: statusIcon,
                    size: "large"
                  }
                ]
              },
              {
                type: "Column",
                width: "stretch",
                items: [
                  {
                    type: "TextBlock",
                    text: title,
                    weight: "bolder",
                    size: "medium",
                    color: cardColor
                  },
                  ...(symbols.length > 0 ? [{
                    type: "TextBlock",
                    text: `Symbols: ${symbols.join(', ')}`,
                    size: "small",
                    isSubtle: true
                  }] : [])
                ]
              }
            ]
          }
        ]
      },
      ...(message ? [{
        type: "Container",
        spacing: "medium",
        items: [
          {
            type: "TextBlock",
            text: message,
            wrap: true,
            size: "default"
          }
        ]
      }] : []),
      ...(isSuccess ? [{
        type: "Container",
        spacing: "medium",
        items: [
          {
            type: "TextBlock",
            text: "**You'll now receive:**",
            weight: "bolder",
            size: "medium"
          },
          {
            type: "FactSet",
            facts: [
              {
                title: "🚨 Breaking News:",
                value: "Immediate alerts for major announcements"
              },
              {
                title: "📅 Market Hours:",
                value: "Daily summaries at 9:30 AM & 4:00 PM ET"
              },
              {
                title: "📊 Weekly Digest:",
                value: "Sunday morning summary of your symbols"
              },
              {
                title: "⚡ Real-time Alerts:",
                value: "New corporate actions as they happen"
              }
            ]
          }
        ]
      }] : []),
      {
        type: "ActionSet",
        actions: isSuccess ? [
          {
            type: "Action.Submit",
            title: "⚙️ Manage Settings",
            data: {
              action: "viewSettings"
            }
          },
          {
            type: "Action.Submit",
            title: "📊 View Events",
            data: {
              action: "viewEvents"
            }
          },
          {
            type: "Action.Submit",
            title: "➕ Add More Symbols",
            data: {
              action: "addSubscription"
            }
          }
        ] : [
          {
            type: "Action.Submit",
            title: "🔄 Try Again",
            data: {
              action: "retry"
            }
          },
          {
            type: "Action.Submit",
            title: "ℹ️ Help",
            data: {
              action: "help"
            }
          }
        ]
      }
    ]
  };
}

/**
 * Create a settings Adaptive Card
 */
export function createSettingsCard(settings: any): any {
  const { subscribedSymbols, marketOpen, marketClose, breakingNews, weeklyDigest } = settings;

  return {
    type: "AdaptiveCard",
    $schema: "http://adaptivecards.io/schemas/adaptive-card.json",
    version: "1.4",
    body: [
      {
        type: "Container",
        style: "emphasis",
        items: [
          {
            type: "ColumnSet",
            columns: [
              {
                type: "Column",
                width: "auto",
                items: [
                  {
                    type: "Image",
                    url: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='%23007acc' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Ccircle cx='12' cy='12' r='3'%3E%3C/circle%3E%3Cpath d='M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1 1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z'%3E%3C/path%3E%3C/svg%3E",
                    width: "24px",
                    height: "24px"
                  }
                ]
              },
              {
                type: "Column",
                width: "stretch",
                items: [
                  {
                    type: "TextBlock",
                    text: "⚙️ Your Notification Settings",
                    weight: "bolder",
                    size: "medium",
                    color: "accent"
                  },
                  {
                    type: "TextBlock",
                    text: `${subscribedSymbols?.length || 0} symbols subscribed`,
                    size: "small",
                    isSubtle: true
                  }
                ]
              }
            ]
          }
        ]
      },
      {
        type: "Container",
        spacing: "medium",
        items: [
          {
            type: "TextBlock",
            text: "📈 **Subscribed Symbols**",
            weight: "bolder",
            size: "medium"
          },
          {
            type: "TextBlock",
            text: subscribedSymbols?.length > 0 ? subscribedSymbols.join(', ') : 'None',
            wrap: true,
            size: "default",
            color: subscribedSymbols?.length > 0 ? "default" : "attention"
          }
        ]
      },
      {
        type: "Container",
        spacing: "medium",
        items: [
          {
            type: "TextBlock",
            text: "🔔 **Notification Preferences**",
            weight: "bolder",
            size: "medium"
          },
          {
            type: "FactSet",
            facts: [
              {
                title: "Market Open (9:30 AM ET):",
                value: marketOpen ? "✅ Enabled" : "❌ Disabled"
              },
              {
                title: "Market Close (4:00 PM ET):",
                value: marketClose ? "✅ Enabled" : "❌ Disabled"
              },
              {
                title: "Breaking News Alerts:",
                value: breakingNews ? "✅ Enabled" : "❌ Disabled"
              },
              {
                title: "Weekly Digest (Sundays):",
                value: weeklyDigest ? "✅ Enabled" : "❌ Disabled"
              }
            ]
          }
        ]
      },
      {
        type: "ActionSet",
        actions: [
          {
            type: "Action.Submit",
            title: "➕ Add Symbols",
            data: {
              action: "addSubscription"
            }
          },
          {
            type: "Action.Submit",
            title: "➖ Remove Symbols",
            data: {
              action: "removeSubscription"
            }
          },
          {
            type: "Action.Submit",
            title: "🔧 Toggle Settings",
            data: {
              action: "toggleSettings"
            }
          },
          {
            type: "Action.Submit",
            title: "📊 View Events",
            data: {
              action: "viewEvents"
            }
          }
        ]
      }
    ]
  };
}

/**
 * Create an Adaptive Card for visualization responses
 */
export function createVisualizationCard(response: RAGResponse, query: string): any {
  const { answer, sources } = response;
  
  // Analyze the data to determine the best visualization
  const visualizationSuggestions = analyzeDataForVisualization(sources);
  
  const card: any = {
    type: "AdaptiveCard",
    $schema: "http://adaptivecards.io/schemas/adaptive-card.json",
    version: "1.4",
    body: [
      {
        type: "Container",
        style: "emphasis",
        items: [
          {
            type: "TextBlock",
            text: "📊 Data Visualization Response",
            weight: "Bolder",
            size: "Medium",
            color: "Accent"
          },
          {
            type: "TextBlock",
            text: `Query: "${query}"`,
            size: "Small",
            isSubtle: true
          }
        ]
      },
      {
        type: "Container",
        spacing: "Medium",
        items: [
          {
            type: "TextBlock",
            text: answer,
            wrap: true
          }
        ]
      }
    ]
  };

  // Add visualization summary based on data analysis
  if (visualizationSuggestions.canVisualize && sources.length > 0) {
    // Create text-based chart representation
    const chartData = createTextChart(sources, visualizationSuggestions.chartType);
    
    card.body.push({
      type: "Container",
      spacing: "Medium",
      items: [
        {
          type: "TextBlock",
          text: `📈 ${visualizationSuggestions.title}`,
          weight: "Bolder",
          size: "Medium"
        },
        {
          type: "TextBlock",
          text: chartData.textChart,
          fontType: "Monospace",
          wrap: true
        },
        {
          type: "FactSet",
          facts: chartData.summary
        }
      ]
    });
  } else {
    // Show why visualization isn't possible
    card.body.push({
      type: "Container",
      spacing: "Medium",
      style: "attention",
      items: [
        {
          type: "TextBlock",
          text: "⚠️ Visualization Limitation",
          weight: "Bolder",
          color: "Attention"
        },
        {
          type: "TextBlock",
          text: "Text-based charts are displayed here. For interactive charts with zoom, hover, and filtering capabilities, please visit our web dashboard.",
          wrap: true
        }
      ]
    });
  }

  // Add data sources
  if (sources && sources.length > 0) {
    const sourceItems = sources.slice(0, 5).map((source, index) => {
      const company = source.issuer_name || source.company_name || 'Unknown';
      const eventType = (source.event_type || 'unknown').replace('_', ' ');
      const status = source.status || 'Unknown';
      
      return {
        type: "Container",
        spacing: "Small",
        items: [
          {
            type: "TextBlock",
            text: `${index + 1}. ${getEventEmoji(source.event_type || '')} **${company}**`,
            weight: "Bolder"
          },
          {
            type: "TextBlock",
            text: `${eventType.toUpperCase()} • ${status}`,
            size: "Small",
            isSubtle: true
          }
        ]
      };
    });

    card.body.push({
      type: "Container",
      spacing: "Medium",
      items: [
        {
          type: "TextBlock",
          text: `📋 Data Sources (${sources.length} events)`,
          weight: "Bolder",
          size: "Medium"
        },
        ...sourceItems
      ]
    });
  }

  // Add actions for enhanced visualization
  card.body.push({
    type: "ActionSet",
    actions: [
      {
        type: "Action.OpenUrl",
        title: "🌐 Open Interactive Dashboard",
        url: "http://localhost:8501"
      },
      {
        type: "Action.Submit",
        title: "🔄 Refresh Data",
        data: {
          action: "refreshEvents"
        }
      },
      {
        type: "Action.Submit",
        title: "📊 View All Events",
        data: {
          action: "viewEvents"
        }
      }
    ]
  });

  return card;
}

/**
 * Analyze data to determine the best visualization approach
 */
function analyzeDataForVisualization(sources: CorporateActionEvent[]): {
  canVisualize: boolean;
  chartType: string;
  title: string;
  description: string;
} {
  if (!sources || sources.length === 0) {
    return {
      canVisualize: false,
      chartType: 'none',
      title: 'No Data Available',
      description: 'No data available for visualization'
    };
  }

  // Analyze event types
  const eventTypes = sources.reduce((acc, event) => {
    const type = event.event_type || 'unknown';
    acc[type] = (acc[type] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  // Analyze status distribution
  const statusTypes = sources.reduce((acc, event) => {
    const status = event.status || 'unknown';
    acc[status] = (acc[status] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  // Determine best chart type based on data variety
  if (Object.keys(statusTypes).length > 1) {
    return {
      canVisualize: true,
      chartType: 'status_pie',
      title: 'Event Status Distribution',
      description: 'Distribution of events by their status'
    };
  } else if (Object.keys(eventTypes).length > 1) {
    return {
      canVisualize: true,
      chartType: 'event_type_bar',
      title: 'Event Type Distribution',
      description: 'Distribution of events by type'
    };
  } else {
    return {
      canVisualize: true,
      chartType: 'company_list',
      title: 'Company Event Summary',
      description: 'List of companies with events'
    };
  }
}

/**
 * Create a text-based chart representation
 */
function createTextChart(sources: CorporateActionEvent[], chartType: string): {
  textChart: string;
  summary: Array<{ title: string; value: string }>;
} {
  switch (chartType) {
    case 'status_pie':
      return createStatusPieChart(sources);
    case 'event_type_bar':
      return createEventTypeBarChart(sources);
    case 'company_list':
      return createCompanyListChart(sources);
    default:
      return createGenericChart(sources);
  }
}

/**
 * Create a text-based status pie chart
 */
function createStatusPieChart(sources: CorporateActionEvent[]): {
  textChart: string;
  summary: Array<{ title: string; value: string }>;
} {
  const statusCounts = sources.reduce((acc, event) => {
    const status = event.status || 'unknown';
    acc[status] = (acc[status] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const total = sources.length;
  const maxBarLength = 20;
  
  let chart = "Status Distribution:\n\n";
  const summary: Array<{ title: string; value: string }> = [];

  Object.entries(statusCounts)
    .sort(([,a], [,b]) => b - a)
    .forEach(([status, count]) => {
      const percentage = (count / total * 100).toFixed(1);
      const barLength = Math.round((count / total) * maxBarLength);
      const bar = "█".repeat(barLength) + "░".repeat(maxBarLength - barLength);
      
      const statusIcon = status === 'confirmed' ? '✅' : 
                        status === 'announced' ? '📢' : 
                        status === 'pending' ? '⏳' : '❓';
      
      chart += `${statusIcon} ${status.toUpperCase().padEnd(12)} ${bar} ${count} (${percentage}%)\n`;
      summary.push({ title: status.toUpperCase(), value: `${count} events (${percentage}%)` });
    });

  return { textChart: chart, summary };
}

/**
 * Create a text-based event type bar chart
 */
function createEventTypeBarChart(sources: CorporateActionEvent[]): {
  textChart: string;
  summary: Array<{ title: string; value: string }>;
} {
  const typeCounts = sources.reduce((acc, event) => {
    const type = event.event_type || 'unknown';
    acc[type] = (acc[type] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const maxCount = Math.max(...Object.values(typeCounts));
  const maxBarLength = 20;
  
  let chart = "Event Type Distribution:\n\n";
  const summary: Array<{ title: string; value: string }> = [];

  Object.entries(typeCounts)
    .sort(([,a], [,b]) => b - a)
    .forEach(([type, count]) => {
      const barLength = Math.round((count / maxCount) * maxBarLength);
      const bar = "█".repeat(barLength) + "░".repeat(maxBarLength - barLength);
      const emoji = getEventEmoji(type);
      const typeName = type.replace('_', ' ').toUpperCase();
      
      chart += `${emoji} ${typeName.padEnd(15)} ${bar} ${count}\n`;
      summary.push({ title: typeName, value: `${count} events` });
    });

  return { textChart: chart, summary };
}

/**
 * Create a company list chart
 */
function createCompanyListChart(sources: CorporateActionEvent[]): {
  textChart: string;
  summary: Array<{ title: string; value: string }>;
} {
  const companyCounts = sources.reduce((acc, event) => {
    const company = event.issuer_name || event.company_name || 'Unknown';
    acc[company] = (acc[company] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  let chart = "Companies with Events:\n\n";
  const summary: Array<{ title: string; value: string }> = [];

  Object.entries(companyCounts)
    .sort(([,a], [,b]) => b - a)
    .slice(0, 10)
    .forEach(([company, count], index) => {
      const medal = index === 0 ? '🥇' : index === 1 ? '🥈' : index === 2 ? '🥉' : '🏢';
      chart += `${medal} ${company.padEnd(25)} ${count} event${count > 1 ? 's' : ''}\n`;
      summary.push({ title: company, value: `${count} events` });
    });

  return { textChart: chart, summary };
}

/**
 * Create a generic chart
 */
function createGenericChart(sources: CorporateActionEvent[]): {
  textChart: string;
  summary: Array<{ title: string; value: string }>;
} {
  let chart = "Corporate Actions Summary:\n\n";
  
  sources.slice(0, 5).forEach((event, index) => {
    const company = event.issuer_name || event.company_name || 'Unknown';
    const type = event.event_type || 'unknown';
    const status = event.status || 'unknown';
    const emoji = getEventEmoji(type);
    
    chart += `${index + 1}. ${emoji} ${company} - ${type.replace('_', ' ')} (${status})\n`;
  });

  const summary = [
    { title: "Total Events", value: sources.length.toString() },
    { title: "Companies", value: new Set(sources.map(e => e.issuer_name || e.company_name)).size.toString() },
    { title: "Event Types", value: new Set(sources.map(e => e.event_type)).size.toString() }
  ];

  return { textChart: chart, summary };
}
