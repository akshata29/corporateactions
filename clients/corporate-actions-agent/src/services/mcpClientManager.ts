import axios from 'axios';

/**
 * MCP Client Manager for Corporate Actions
 * Manages connections to MCP servers using streamable-http protocol
 */
export class MCPClientManager {
    private baseUrls: { [key: string]: string };
    private isInitialized: boolean = false;    constructor() {
        // Use SSE endpoints for Teams bot integration
        this.baseUrls = {
            rag: process.env.SSE_RAG_SERVER_URL || 'http://localhost:8003',
            search: process.env.SSE_SEARCH_SERVER_URL || 'http://localhost:8004', 
            comments: process.env.SSE_COMMENTS_SERVER_URL || 'http://localhost:8005'
        };
    }    async initialize(): Promise<void> {
        console.log('🔧 Initializing MCP Client Manager...');
        
        // Test connectivity to all SSE servers using health endpoints
        for (const [name, url] of Object.entries(this.baseUrls)) {
            try {
                const response = await axios.get(`${url}/health`, { 
                    timeout: 5000,
                    headers: {
                        'Accept': 'application/json'
                    }
                });
                console.log(`✅ ${name.toUpperCase()} SSE server connected: ${url} (${response.data.status})`);
            } catch (error: any) {
                console.warn(`⚠️ ${name.toUpperCase()} SSE server not available: ${url}`);
            }
        }
        
        this.isInitialized = true;
    }    /**
     * Enhanced RAG query with chat history support using SSE endpoints
     */
    async ragQuery(
        query: string, 
        maxResults: number = 5, 
        chatHistory: Array<{role: string, content: string}> = []
    ): Promise<any> {        try {
            const response = await axios.get(`${this.baseUrls.rag}/rag-query`, {
                params: {
                    query,
                    max_results: maxResults,
                    chat_history: JSON.stringify(chatHistory)
                },
                headers: {
                    'Accept': 'application/json'
                },
                timeout: 30000  // Reduced from 30000 to 15000ms
            });

            return response.data;
        } catch (error: any) {
            console.error('RAG query error:', error.message);
            return {
                error: error.message || 'Failed to query RAG server',
                answer: 'Sorry, I encountered an issue processing your request. Please try a simpler query or try again later.',
                sources: [],
                confidence_score: 0.0
            };
        }
    }    /**
     * Search corporate actions using SSE endpoints
     */
    async searchCorporateActions(
        params: { 
            query?: string, 
            status?: string, 
            event_type?: string, 
            limit?: number 
        }
    ): Promise<any> {
        try {
            const response = await axios.get(`${this.baseUrls.rag}/search-corporate-actions`, {
                params: params,
                headers: {
                    'Accept': 'application/json'
                },
                timeout: 15000
            });

            return response.data;
        } catch (error: any) {
            console.error('Search corporate actions error:', error.message);
            return {
                error: error.message || 'Failed to search corporate actions',
                results: []
            };
        }
    }

    /**
     * Web search using SSE endpoints
     */
    async webSearch(
        query: string, 
        maxResults: number = 10, 
        searchType: string = "general",
        dateFilter: string = ""
    ): Promise<any> {
        try {
            const response = await axios.get(`${this.baseUrls.search}/web-search`, {
                params: {
                    query,
                    max_results: maxResults,
                    search_type: searchType,
                    date_filter: dateFilter
                },
                headers: {
                    'Accept': 'application/json'
                },
                timeout: 30000
            });

            return response.data;
        } catch (error: any) {
            console.error('Web search error:', error.message);
            return {
                error: error.message || 'Failed to perform web search',
                results: []
            };
        }
    }

    /**
     * News search using SSE endpoints
     */
    async newsSearch(
        query: string, 
        maxResults: number = 10, 
        freshness: string = "week"
    ): Promise<any> {
        try {
            const response = await axios.get(`${this.baseUrls.search}/news-search`, {
                params: {
                    query,
                    max_results: maxResults,
                    freshness
                },
                headers: {
                    'Accept': 'application/json'
                },
                timeout: 30000
            });

            return response.data;
        } catch (error: any) {
            console.error('News search error:', error.message);
            return {
                error: error.message || 'Failed to perform news search',
                results: []
            };
        }
    }

    /**
     * Financial data search using SSE endpoints
     */
    async financialDataSearch(
        symbol: string, 
        dataType: string = "general", 
        maxResults: number = 10
    ): Promise<any> {
        try {
            const response = await axios.get(`${this.baseUrls.search}/financial-data-search`, {
                params: {
                    symbol,
                    data_type: dataType,
                    max_results: maxResults
                },
                headers: {
                    'Accept': 'application/json'
                },
                timeout: 30000
            });

            return response.data;
        } catch (error: any) {
            console.error('Financial data search error:', error.message);
            return {
                error: error.message || 'Failed to perform financial data search',
                results: []
            };
        }
    }

    /**
     * Get event comments using SSE endpoints
     */
    async getEventComments(
        eventId: string, 
        limit: number = 50, 
        offset: number = 0,
        commentType: string = "",
        status: string = ""
    ): Promise<any> {
        try {
            const response = await axios.get(`${this.baseUrls.comments}/event-comments/${eventId}`, {
                params: {
                    limit,
                    offset,
                    comment_type: commentType,
                    status
                },
                headers: {
                    'Accept': 'application/json'
                },
                timeout: 15000
            });

            return response.data;
        } catch (error: any) {
            console.error('Get event comments error:', error.message);
            return {
                error: error.message || 'Failed to get event comments',
                comments: []
            };
        }
    }

    /**
     * Natural language query processing
     */
    async processNaturalLanguage(query: string, userName: string = 'User'): Promise<any> {
        try {
            // First try RAG query for comprehensive answers
            const ragResult = await this.ragQuery(query, 5, true, []);
            
            if (ragResult.answer && !ragResult.error) {
                return {
                    success: true,
                    answer: ragResult.answer,
                    sources: ragResult.sources || [],
                    confidence: ragResult.confidence_score || 0.5,
                    type: 'rag_answer'
                };
            }

            // Fallback to search if RAG fails
            const searchResult = await this.searchCorporateActions({
                query: query,
                limit: 5
            });

            if (searchResult.results && searchResult.results.length > 0) {
                const summary = this.generateSearchSummary(searchResult.results, query);
                return {
                    success: true,
                    answer: summary,
                    sources: searchResult.results,
                    confidence: 0.7,
                    type: 'search_results'
                };
            }

            // Return contextual fallback
            return {
                success: false,
                answer: this.generateContextualFallback(query, userName),
                sources: [],
                confidence: 0.1,
                type: 'fallback'
            };

        } catch (error: any) {
            console.error('Natural language processing error:', error.message);
            return {
                success: false,
                answer: this.generateContextualFallback(query, userName),
                sources: [],
                confidence: 0.0,
                type: 'error'
            };
        }
    }

    /**
     * Generate search summary from results
     */
    private generateSearchSummary(results: any[], query: string): string {
        const count = results.length;
        const companies = [...new Set(results.map(r => r.issuer_name || r.company_name).filter(Boolean))];
        const eventTypes = [...new Set(results.map(r => r.event_type).filter(Boolean))];

        let summary = `🔍 **Found ${count} corporate action${count > 1 ? 's' : ''} matching "${query}"**\n\n`;

        if (companies.length > 0) {
            summary += `📊 **Companies**: ${companies.slice(0, 5).join(', ')}${companies.length > 5 ? ` and ${companies.length - 5} more` : ''}\n`;
        }

        if (eventTypes.length > 0) {
            summary += `📈 **Event Types**: ${eventTypes.slice(0, 3).join(', ')}${eventTypes.length > 3 ? ` and more` : ''}\n\n`;
        }

        summary += `**Recent Events:**\n`;
        results.slice(0, 3).forEach((result, index) => {
            const company = result.issuer_name || result.company_name || 'Unknown';
            const eventType = result.event_type?.replace('_', ' ') || 'Event';
            const status = result.status || 'Unknown';
            const emoji = this.getEventEmoji(result.event_type);
            
            summary += `${index + 1}. ${emoji} **${company}** - ${eventType} (${status})\n`;
        });

        summary += `\n💡 **Ask for more details**: "Tell me about [company] event" or use \`/search [specific query]\``;

        return summary;
    }

    /**
     * Generate contextual fallback response
     */
    private generateContextualFallback(query: string, userName: string): string {
        const lowerQuery = query.toLowerCase();
        
        if (lowerQuery.includes('apple') || lowerQuery.includes('aapl')) {
            return `🍎 **Apple (AAPL) Corporate Actions**\n\n🤖 Hi ${userName}! I understand you're asking about Apple.\n\n🔧 **MCP Integration Status**: Connecting to live data servers...\n\nI'm working to provide real-time Apple corporate action data. For now:\n\n💡 **Try these commands:**\n• \`/search Apple dividend\`\n• \`/subscribe AAPL\` to get notifications\n• \`/status\` to check system connectivity`;
        }
        
        if (lowerQuery.includes('dividend')) {
            return `💰 **Dividend Information**\n\n🤖 Hi ${userName}! I understand you're asking about dividends.\n\n🔧 **Enhanced AI Integration**: Connecting to live dividend data...\n\nI'll soon provide:\n• Real dividend announcements and analysis\n• Dividend yield trends and comparisons\n• Payment dates and ex-dividend schedules\n• AI-powered dividend predictions\n\n💡 **For now, try:**\n• \`/search dividend [company]\`\n• \`/subscribe [symbols]\` for dividend alerts`;
        }

        if (lowerQuery.includes('split')) {
            return `📈 **Stock Split Information**\n\n🤖 Hi ${userName}! I understand you're asking about stock splits.\n\n🔧 **Live Data Integration**: Connecting to split announcement feeds...\n\nI'll soon provide:\n• Real-time stock split announcements\n• Split ratio analysis and implications\n• Historical split patterns and outcomes\n• Post-split price adjustment calculations\n\n💡 **For now, try:**\n• \`/search stock split [company]\`\n• \`/events\` for recent split announcements`;
        }

        return `🤖 **Hi ${userName}! I understand your question: "${query}"**\n\n🔧 **MCP Servers Status**: Establishing connections...\n\nI'm powered by advanced corporate actions servers that provide:\n• 📊 Real-time corporate action data\n• 🧠 AI-powered analysis and insights  \n• 📈 Historical trends and patterns\n• 🔔 Proactive event notifications\n\n💡 **While connecting, try:**\n• \`/help\` - See all available commands\n• \`/search [your query]\` - Enhanced search\n• \`/status\` - Check system connectivity\n• \`/subscribe [symbols]\` - Get notifications\n\n🔄 **Ask me again in a moment for live data!**`;
    }

    /**
     * Get emoji for event type
     */
    private getEventEmoji(eventType: string): string {
        const emojiMap: { [key: string]: string } = {
            'dividend': '💰',
            'stock_split': '📈',
            'merger': '🤝',
            'acquisition': '🏢',
            'spinoff': '🔄',
            'rights': '📜',
            'special_dividend': '💎',
            'stock_dividend': '📊'
        };
        return emojiMap[eventType] || '📋';
    }    /**
     * Get service health across all SSE servers
     */
    async getServiceHealth(): Promise<any> {
        const health: { [key: string]: any } = {};
        
        for (const [name, url] of Object.entries(this.baseUrls)) {
            try {
                const response = await axios.get(`${url}/health`, { 
                    timeout: 5000,
                    headers: {
                        'Accept': 'application/json'
                    }
                });
                
                health[name] = {
                    status: 'healthy',
                    url,
                    service: response.data.service || 'SSE API'
                };
            } catch (error: any) {
                health[name] = {
                    status: 'unhealthy',
                    url,
                    error: error.message
                };
            }
        }
        
        return health;
    }

    /**
     * Check if client is ready
     */
    isReady(): boolean {
        return this.isInitialized;
    }

    /**
     * Get server URLs for debugging
     */
    getServerUrls(): { [key: string]: string } {
        return { ...this.baseUrls };
    }

    /**
     * List recent corporate action events using SSE endpoints
     */
    async listEvents(limit: number = 10): Promise<any> {
        try {
            const response = await axios.get(`${this.baseUrls.rag}/events`, {
                params: {
                    limit
                },
                headers: {
                    'Accept': 'application/json'
                },
                timeout: 15000
            });

            return response.data;
        } catch (error: any) {
            console.error('List events error:', error.message);
            return {
                error: error.message || 'Failed to list events',
                events: [],
                total_count: 0
            };
        }
    }

    /**
     * Create a new inquiry for a corporate action event
     */
    async createInquiry(
        eventId: string,
        userId: string,
        userName: string,
        organization: string,
        subject: string,
        description: string,
        priority: string = "MEDIUM"
    ): Promise<any> {
        try {
            const response = await axios.post(`${this.baseUrls.rag}/mcp/tools/create_inquiry_tool`, {
                event_id: eventId,
                user_id: userId,
                user_name: userName,
                organization: organization,
                subject: subject,
                description: description,
                priority: priority
            }, {
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                timeout: 15000
            });

            return response.data;
        } catch (error: any) {
            console.error('Create inquiry error:', error.message);
            return {
                success: false,
                error: error.message || 'Failed to create inquiry'
            };
        }
    }

    /**
     * Get all inquiries for a specific event
     */
    async getInquiries(eventId: string): Promise<any> {
        try {
            const response = await axios.post(`${this.baseUrls.rag}/mcp/tools/get_inquiries_tool`, {
                event_id: eventId
            }, {
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                timeout: 15000
            });

            return response.data;
        } catch (error: any) {
            console.error('Get inquiries error:', error.message);
            return {
                inquiries: [],
                count: 0,
                error: error.message || 'Failed to get inquiries'
            };
        }
    }

    /**
     * Get user's inquiries for a specific event
     */
    async getUserInquiries(eventId: string, userId: string): Promise<any> {
        try {
            const response = await axios.post(`${this.baseUrls.rag}/mcp/tools/get_user_inquiries_tool`, {
                event_id: eventId,
                user_id: userId
            }, {
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                timeout: 15000
            });

            return response.data;
        } catch (error: any) {
            console.error('Get user inquiries error:', error.message);
            return {
                inquiries: [],
                count: 0,
                error: error.message || 'Failed to get user inquiries'
            };
        }
    }

    /**
     * Update an existing inquiry
     */
    async updateInquiry(
        inquiryId: string,
        updates: {
            subject?: string;
            description?: string;
            priority?: string;
            status?: string;
            response?: string;
            resolution_notes?: string;
            assigned_to?: string;
        }
    ): Promise<any> {
        try {
            const response = await axios.post(`${this.baseUrls.rag}/mcp/tools/update_inquiry_tool`, {
                inquiry_id: inquiryId,
                ...updates
            }, {
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                timeout: 15000
            });

            return response.data;
        } catch (error: any) {
            console.error('Update inquiry error:', error.message);
            return {
                success: false,
                error: error.message || 'Failed to update inquiry'
            };
        }
    }

    /**
     * Delete an inquiry (user's own only)
     */
    async deleteInquiry(inquiryId: string, userId: string): Promise<any> {
        try {
            const response = await axios.post(`${this.baseUrls.rag}/mcp/tools/delete_inquiry_tool`, {
                inquiry_id: inquiryId,
                user_id: userId
            }, {
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                timeout: 15000
            });

            return response.data;
        } catch (error: any) {
            console.error('Delete inquiry error:', error.message);
            return {
                success: false,
                error: error.message || 'Failed to delete inquiry'
            };
        }
    }

    /**
     * Get upcoming events for subscribed user symbols
     */
    async getUpcomingEvents(userId: string, daysAhead: number = 7): Promise<any> {
        try {
            const response = await axios.post(`${this.baseUrls.rag}/mcp/tools/get_upcoming_events_tool`, {
                user_id: userId,
                days_ahead: daysAhead
            }, {
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                timeout: 15000
            });

            return response.data;
        } catch (error: any) {
            console.error('Get upcoming events error:', error.message);
            return {
                upcoming_events: [],
                total_events: 0,
                error: error.message || 'Failed to get upcoming events'
            };
        }
    }

    /**
     * Get all inquiries for a user across all their subscribed events
     */
    async getAllUserInquiries(userId: string): Promise<any> {
        try {
            // First, get the user's upcoming events
            const eventsResult = await this.getUpcomingEvents(userId, 30); // Look back/forward 30 days
            const events = eventsResult.upcoming_events || [];
            
            // Then get user inquiries for each event
            const allInquiries: any[] = [];
            for (const event of events) {
                try {
                    const inquiriesResult = await this.getUserInquiries(event.event_id, userId);
                    if (inquiriesResult.inquiries && inquiriesResult.inquiries.length > 0) {
                        allInquiries.push(...inquiriesResult.inquiries);
                    }
                } catch (error) {
                    console.error(`Error getting inquiries for event ${event.event_id}:`, error);
                }
            }
            
            // Sort by creation date (newest first)
            allInquiries.sort((a, b) => {
                const dateA = new Date(a.created_at || 0);
                const dateB = new Date(b.created_at || 0);
                return dateB.getTime() - dateA.getTime();
            });
            
            return {
                inquiries: allInquiries,
                count: allInquiries.length,
                events_checked: events.length
            };

        } catch (error: any) {
            console.error('Get all user inquiries error:', error.message);
            return {
                inquiries: [],
                count: 0,
                error: error.message || 'Failed to get user inquiries'
            };
        }
    }
    
    /**
     * Save user subscription to CosmosDB
     */
    /**
     * Save user subscription to database
     */
    async saveSubscription(
        userId: string,
        userName: string,
        organization: string,
        symbols: string,
        eventTypes?: string
    ): Promise<any> {
        try {
            const response = await axios.post(`${this.baseUrls.rag}/mcp/tools/save_subscription_tool`, {
                user_id: userId,
                user_name: userName,
                organization: organization,
                symbols: symbols,
                event_types: eventTypes || ""
            }, {
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                timeout: 15000
            });

            return response.data;
        } catch (error: any) {
            console.error('Error saving subscription:', error);
            return {
                success: false,
                error: error.response?.data?.message || error.message || 'Unknown error'
            };
        }
    }

    /**
     * Remove user subscription from database
     */
    async removeSubscription(userId: string): Promise<any> {
        try {
            // For now, we'll save an empty subscription to effectively remove it
            // In a real implementation, you might want a dedicated delete endpoint
            const response = await axios.post(`${this.baseUrls.rag}/mcp/tools/save_subscription_tool`, {
                user_id: userId,
                user_name: "User",
                organization: "Teams",
                symbols: "",
                event_types: ""
            }, {
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                timeout: 15000
            });

            return response.data;
        } catch (error: any) {
            console.error('Error removing subscription:', error);
            return {
                success: false,
                error: error.response?.data?.message || error.message || 'Unknown error'
            };
        }
    }

    /**
     * Get user subscription from CosmosDB
     */
    async getSubscription(userId: string): Promise<any> {
        try {
            const response = await axios.post(`${this.baseUrls.rag}/mcp/tools/get_subscription_tool`, {
                user_id: userId
            }, {
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                timeout: 15000
            });

            return response.data;
        } catch (error: any) {
            console.error('Get subscription error:', error.message);
            return {
                subscription: null,
                error: error.message || 'Failed to get subscription'
            };
        }
    }
}
