import { App } from '@microsoft/teams.apps';
import { MCPClientManager } from './services/mcpClientManager';
import { NotificationService } from './services/notificationService';
import { format } from 'date-fns';
import { createDashboardCard, createInquiryFormCard, createInquiriesListCard, createEditableInquiriesListCard, createHelpCard, createRAGSearchCard, createEventsListCard, createSubscriptionCard, createSettingsCard, createStatusCard, createErrorCard } from './services/adaptiveCards';

console.log('🔍 bot.ts file loaded'); // Add this line

/**
 * Enhanced Corporate Actions Bot with MCP Integration
 * Provides AI-powered corporate actions assistance with proactive notifications
 */
export class CorporateActionsBot {
    private app: App;
    private mcpClient: MCPClientManager;
    private notificationService: NotificationService;
    private conversationHistory: Map<string, Array<{role: string, content: string}>> = new Map();

    constructor(
        app: App, 
        mcpClient: MCPClientManager, 
        notificationService: NotificationService
    ) {
        console.log('🔍 CorporateActionsBot constructor called'); // Add this line
        this.app = app;
        this.mcpClient = mcpClient;
        this.notificationService = notificationService;
    }

    /**
     * Register all bot event handlers and commands
     */
    registerHandlers(): void {
        console.log('🔧 Registering CorporateActionsBot handlers...');
        
        // Welcome message for new conversations
        this.app.on('membersAdded', async ({ send, activity }) => {
            await this.sendWelcomeMessage(send);
        });

        // Handle adaptive card submit actions
        this.app.on('adaptiveCardSubmit', async ({ send, activity }) => {
            await this.handleAdaptiveCardActions(send, activity);
        });

        // Help command
        this.app.on('message', async ({ send, activity }) => {
            const text = activity.text?.toLowerCase().trim() || '';
            console.log(`Received message: ${text}`);
            
            // If it's an adaptive card action, handle it
            if (activity.value?.action) {
                await this.handleAdaptiveCardActions(send, activity);
                return;
            }

            // Show dashboard by default for empty messages
            if (!text || text === 'dashboard' || text === 'home') {
                await this.handleRefreshDashboard(send, activity);
                return;
            }

            if (text.startsWith('/help')) {
                await this.handleHelpCommand(send);
                return;
            }

            if (text.startsWith('/settings')) {
                await this.handleSettingsCommand(send, activity);
                return;
            }

            // Dashboard command
            if (text.startsWith('/dashboard') || text.startsWith('/home')) {
                console.log("Handling dashboard command");
                await this.handleRefreshDashboard(send, activity);
                return;
            }

            // Search command
            if (text.startsWith('/search')) {
                await this.handleSearchCommand(send, activity);
                return;
            }

            // Events command
            if (text.startsWith('/events')) {
                await this.handleEventsCommand(send, activity);
                return;
            }

            // Subscribe command
            if (text.startsWith('/subscribe')) {
                await this.handleSubscribeCommand(send, activity);
                return;
            }

            // Unsubscribe command
            if (text.startsWith('/unsubscribe')) {
                await this.handleUnsubscribeCommand(send, activity);
                return;
            }

            // Status command
            if (text.startsWith('/status')) {
                await this.handleStatusCommand(send, activity);
                return;
            }

            // Notifications command
            if (text.startsWith('/notifications')) {
                await this.handleNotificationsCommand(send, activity);
                return;
            }

            // Inquiry management commands
            if (text.startsWith('/inquiries')) {
                await this.handleInquiriesCommand(send, activity);
                return;
            }

            if (text.startsWith('/create-inquiry')) {
                await this.handleCreateInquiryCommand(send, activity);
                return;
            }

            if (text.startsWith('/edit-inquiry')) {
                await this.handleEditInquiryCommand(send, activity);
                return;
            }

            // Natural language processing for non-commands
            if (!text.startsWith('/')) {
                await this.handleNaturalLanguageQuery(send, activity);
                return;
            }

            // Unknown command
            await send({
                type: 'message',
                text: '❓ Unknown command. Type `/help` to see available commands.'
            });
        });
    }

    /**
     * Send enhanced welcome message with dashboard
     */
    private async sendWelcomeMessage(send: any): Promise<void> {
        try {
            // Get user's subscription and upcoming events for dashboard
            const userId = 'teams_user_' + Date.now(); // You should get actual user ID from Teams context
            const upcomingEvents = await this.mcpClient.getUpcomingEvents(userId);
            
            // Get sample events if no subscription exists
            const events = upcomingEvents.upcoming_events?.length > 0 
                ? upcomingEvents.upcoming_events 
                : await this.getSampleEvents();
            
            // Get inquiries (empty for new users)
            const inquiries: any[] = [];
            
            const dashboardCard = createDashboardCard(events, inquiries, 'Teams User');
            
            await send({
                type: 'message',
                attachments: [{
                    contentType: 'application/vnd.microsoft.card.adaptive',
                    content: dashboardCard
                }]
            });
        } catch (error) {
            console.error('Error sending welcome message:', error);
            await send({
                type: 'message',
                text: '🏦 **Welcome to Corporate Actions Assistant!**\n\n🤖 I provide AI-powered insights and inquiry management for corporate actions.\n\n💡 **Try these commands:**\n• `/help` - See all available commands\n• `/events` - View recent corporate actions\n• `/search [query]` - Search for specific events\n• `/subscribe [symbols]` - Get notifications\n\n🔧 **Enhanced Features:**\n• 📝 Create and manage inquiries\n• 📊 Real-time dashboard updates\n• 🔔 Proactive notifications\n• 🧠 AI-powered insights'
            });
        }
    }

    /**
     * Handle help command with comprehensive guide
     */
    private async handleHelpCommand(send: any): Promise<void> {
        const helpCard = createHelpCard();
        
        await send({
            type: 'message',
            attachments: [{
                contentType: 'application/vnd.microsoft.card.adaptive',
                content: helpCard
            }]
        });
    }

// private async handleHelpCommand(send: any): Promise<void> {
//         const helpText = `🔍 **Enhanced Corporate Actions Bot - Command Guide**

// **🏠 Dashboard & Inquiry Management:**
// • \`dashboard\` or \`home\` - Show interactive corporate actions dashboard
// • **Dashboard Features**:
//   - 📊 View upcoming corporate actions with real-time status
//   - 📝 Create, view, and edit inquiries for any event
//   - 🔔 Track your inquiry status and get personalized insights
//   - 🚦 Smart button controls based on your inquiry status
// • **Inquiry Actions** (via Dashboard):
//   - 🆕 **Create Inquiry** - Submit new inquiries (disabled if you have open ones)
//   - 👁️ **View Inquiries** - See all inquiries for an event
//   - ✏️ **Edit Inquiries** - Modify your own inquiries (enabled only if you have inquiries)

// **🔍 Search & Query (AI-Powered):**
// • \`/search dividend AAPL\` - Search with AI insights and confidence scoring
// • \`/events\` - Recent actions with smart filtering and status indicators
// • \`/events confirmed 10\` - Show 10 confirmed events
// • Natural language: *"Show me Tesla stock splits"* - Context-aware responses

// **💬 Subscription & Notifications:**
// • \`/subscribe AAPL,MSFT,GOOGL\` - Multi-symbol smart subscriptions
// • \`/unsubscribe TSLA\` - Remove specific symbols
// • \`/notifications settings\` - Configure notification preferences
// • \`/notifications history\` - View recent notification history

// **💬 Comments & Collaboration:**
// • \`/comment CA-2025-001 This needs clarification\` - Add structured comments
// • \`/comment CA-2025-001 question What's the timeline?\` - Categorized questions

// **🛠️ System & Status:**
// • \`/status\` - Check MCP server health and capabilities
// • \`/status detailed\` - Detailed system diagnostics with performance metrics
// • \`/help\` - Show this enhanced help guide

// **🔄 Quick Actions:**
// • Just type a message without \`/\` for natural language queries
// • Dashboard automatically refreshes when you perform inquiry actions
// • All inquiry management uses real-time data from our specialized servers

// **🤖 AI Features:**
// • **Context Awareness**: I remember our conversation history
// • **Smart Insights**: AI-powered analysis with confidence scoring
// • **Dynamic Responses**: Contextual follow-ups and clarifications
// • **Multi-modal Support**: Rich formatting with charts and graphs
// • **MCP Integration**: Real-time data from specialized servers
// • **Inquiry Intelligence**: Smart validation prevents duplicate open inquiries

// **📋 Inquiry Management Rules:**
// • 🚫 **One Active Inquiry Rule**: You can only have one open inquiry per event
// • ✅ **Resolution Required**: Resolve existing inquiries before creating new ones
// • ✏️ **Edit Anytime**: Modify your inquiries until they're resolved
// • 👥 **Visibility**: View all inquiries but only edit your own

// **💡 Pro Tips:**
// • **Start with Dashboard**: Type \`dashboard\` to see all available actions
// • **Use Natural Language**: I understand context - ask complex questions!
// • **Subscribe for Updates**: Get notified about events you care about
// • **Check Inquiry Status**: Dashboard shows if you have open inquiries
// • **Ask Follow-up Questions**: I maintain conversation history for context

// **🔔 Proactive Notifications Include:**
// • 🚨 Breaking corporate action announcements
// • 📈 Market open/close summaries with key highlights
// • 💬 Comments and updates on events you're following
// • 📊 Weekly/monthly digest of your subscribed symbols
// • 🔄 Inquiry status updates and responses

// **📊 Example Natural Language Queries:**
// • "What dividend events happened this week with amounts over $2?"
// • "Show me upcoming stock splits and their ratios"
// • "Analyze merger activity in the technology sector"
// • "Create a summary of FAANG dividend announcements this quarter"
// • "Do I have any open inquiries for Apple events?"
// • "What's the status of my Tesla inquiry?"

// **🎯 Getting Started:**
// 1. Type \`dashboard\` to see the main interface
// 2. Browse upcoming corporate actions
// 3. Click "🆕" to create inquiries for events you're interested in
// 4. Use "👁️" to view all inquiries or "✏️" to edit your own
// 5. Subscribe to symbols you track regularly with \`/subscribe\`

// **Need Help?** Just ask me naturally - "How do I create an inquiry?" or "Show me my dashboard"`;

//         await send({ type: 'message', text: helpText });
//     }

    /**
     * Handle search command with enhanced AI integration
     */
    /**
     * Handle search command with enhanced AI integration
     */
    private async handleSearchCommand(send: any, activity: any): Promise<void> {
        const query = activity.text.substring(7).trim(); // Remove "/search "
        
        if (!query) {
            const errorCard = createErrorCard(
                'Please provide a search query. Example: `/search dividend announcements this week`',
                '🔍 Search Query Required'
            );
            
            await send({
                type: 'message',
                attachments: [{
                    contentType: 'application/vnd.microsoft.card.adaptive',
                    content: errorCard
                }]
            });
            return;
        }

        await send({ type: 'typing' });

        try {
            // Get conversation history for context
            const userId = activity.from.id;
            const chatHistory = this.getConversationHistory(userId);

            // Perform enhanced RAG query
            const response = await this.mcpClient.ragQuery(
                query,
                5,
                true,
                chatHistory
            );

            // Update conversation history
            this.addToConversationHistory(userId, 'user', query);

            if (response.error) {
                const errorCard = createErrorCard(
                    `Search error: ${response.error}`,
                    '❌ Search Failed'
                );
                
                await send({
                    type: 'message',
                    attachments: [{
                        contentType: 'application/vnd.microsoft.card.adaptive',
                        content: errorCard
                    }]
                });
                return;
            }

            // Create adaptive card for search results
            const searchCard = createRAGSearchCard(response, query);
            
            await send({
                type: 'message',
                attachments: [{
                    contentType: 'application/vnd.microsoft.card.adaptive',
                    content: searchCard
                }]
            });

            // Add response to conversation history
            this.addToConversationHistory(userId, 'assistant', response.answer || 'No results found');

        } catch (error) {
            console.error('Search command error:', error);
            const errorCard = createErrorCard(
                'I encountered an issue with the search service. Please try again later.',
                '❌ Search Service Error'
            );
            
            await send({
                type: 'message',
                attachments: [{
                    contentType: 'application/vnd.microsoft.card.adaptive',
                    content: errorCard
                }]
            });
        }
    }

    /**
     * Handle events command with smart filtering
     */
    private async handleEventsCommand(send: any, activity: any): Promise<void> {
        const parts = activity.text.split(' ');
        let limit = 5;
        let statusFilter = '';

        // Parse parameters
        for (let i = 1; i < parts.length; i++) {
            const part = parts[i];
            if (/^\d+$/.test(part)) {
                limit = Math.min(parseInt(part), 20);
            } else if (['confirmed', 'announced', 'pending', 'processed', 'cancelled'].includes(part.toLowerCase())) {
                statusFilter = part.toLowerCase();
            }
        }

        await send({ type: 'typing' });

        try {
            const searchParams: any = { limit };
            
            if (statusFilter) {
                searchParams.status = statusFilter;
            }

            const eventsData = await this.mcpClient.searchCorporateActions(searchParams);

            if (eventsData.error) {
                const errorCard = createErrorCard(
                    `Error retrieving events: ${eventsData.error}`,
                    '❌ Events Error'
                );
                
                await send({
                    type: 'message',
                    attachments: [{
                        contentType: 'application/vnd.microsoft.card.adaptive',
                        content: errorCard
                    }]
                });
                return;
            }

            const events = eventsData.events || [];

            if (events.length === 0) {
                const filterMsg = statusFilter ? ` with status '${statusFilter}'` : '';
                const errorCard = createErrorCard(
                    `No recent corporate actions found${filterMsg}.`,
                    '📊 No Events Found'
                );
                
                await send({
                    type: 'message',
                    attachments: [{
                        contentType: 'application/vnd.microsoft.card.adaptive',
                        content: errorCard
                    }]
                });
                return;
            }

            // Create adaptive card for events list
            const title = statusFilter ? `Recent Corporate Actions (${statusFilter.toUpperCase()})` : 'Recent Corporate Actions';
            const eventsCard = createEventsListCard(events, title);
            
            await send({
                type: 'message',
                attachments: [{
                    contentType: 'application/vnd.microsoft.card.adaptive',
                    content: eventsCard
                }]
            });

        } catch (error) {
            console.error('Events command error:', error);
            const errorCard = createErrorCard(
                'Failed to retrieve corporate actions. Please try again later.',
                '❌ Service Error'
            );
            
            await send({
                type: 'message',
                attachments: [{
                    contentType: 'application/vnd.microsoft.card.adaptive',
                    content: errorCard
                }]
            });
        }
    }

    /**
     * Handle subscribe command with enhanced subscription management
     */
    private async handleSubscribeCommand(send: any, activity: any): Promise<void> {
        const symbols = activity.text.substring(10).trim(); // Remove "/subscribe "
        
        if (!symbols) {
            const errorCard = createErrorCard(
                'Please provide symbols to subscribe to. Example: `/subscribe AAPL,MSFT,GOOGL`',
                '🔔 Symbols Required'
            );
            
            await send({
                type: 'message',
                attachments: [{
                    contentType: 'application/vnd.microsoft.card.adaptive',
                    content: errorCard
                }]
            });
            return;
        }

        try {
            const userId = this.getUserId(activity);
            const userName = activity.from.name || 'Teams User';
            const organization = 'Microsoft Teams';
            const conversationId = activity.conversation.id;
            const serviceUrl = activity.serviceUrl;

            const symbolList = symbols.split(',').map((s: string) => s.trim().toUpperCase()).filter((s: string) => s);
            
            // Save subscription to database via MCP server
            const result = await this.mcpClient.saveSubscription(
                userId,
                userName,
                organization,
                symbolList.join(',')
            );

            if (result.success) {
                // Also add to notification service for real-time notifications
                await this.notificationService.addSubscription(
                    userId,
                    userName,
                    symbolList,
                    conversationId,
                    serviceUrl
                );

                // Create success subscription card
                const subscriptionCard = createSubscriptionCard(
                    symbolList,
                    true,
                    'Subscription saved successfully to database'
                );
                
                await send({
                    type: 'message',
                    attachments: [{
                        contentType: 'application/vnd.microsoft.card.adaptive',
                        content: subscriptionCard
                    }]
                });
            } else {
                // Create error subscription card
                const subscriptionCard = createSubscriptionCard(
                    symbolList,
                    false,
                    `Failed to save subscription to database: ${result.error || 'Unknown error occurred'}`
                );
                
                await send({
                    type: 'message',
                    attachments: [{
                        contentType: 'application/vnd.microsoft.card.adaptive',
                        content: subscriptionCard
                    }]
                });
            }

        } catch (error) {
            console.error('Subscribe command error:', error);
            const errorCard = createErrorCard(
                'Failed to add subscription. Please try again later.',
                '❌ Subscription Error'
            );
            
            await send({
                type: 'message',
                attachments: [{
                    contentType: 'application/vnd.microsoft.card.adaptive',
                    content: errorCard
                }]
            });
        }
    }

    /**
     * Handle unsubscribe command
     */
    private async handleUnsubscribeCommand(send: any, activity: any): Promise<void> {
        const symbols = activity.text.substring(12).trim(); // Remove "/unsubscribe "
        
        if (!symbols) {
            await send({
                type: 'message',
                text: '🔕 Please provide symbols to unsubscribe from. Example: `/unsubscribe AAPL,TSLA`'
            });
            return;
        }

        try {
            const userId = this.getUserId(activity);
            const userName = activity.from.name || 'Teams User';
            const organization = 'Microsoft Teams';
            const symbolList = symbols.split(',').map((s: string) => s.trim().toUpperCase()).filter((s: string) => s);
            
            // Get current subscription from database
            const currentSubscription = await this.mcpClient.getSubscription(userId);
            
            if (!currentSubscription.subscription) {
                await send({
                    type: 'message',
                    text: '❌ **No subscription found**\n\nYou don\'t have any active subscriptions to remove from.'
                });
                return;
            }

            const currentSymbols = currentSubscription.subscription.symbols || [];
            const remainingSymbols = currentSymbols.filter((s: string) => !symbolList.includes(s));
            
            if (remainingSymbols.length === currentSymbols.length) {
                await send({
                    type: 'message',
                    text: `❌ **Symbols not found in subscription**\n\nYou are not subscribed to: ${symbolList.join(', ')}\n\n**Current subscriptions:** ${currentSymbols.join(', ')}`
                });
                return;
            }

            // Update subscription in database with remaining symbols
            if (remainingSymbols.length > 0) {
                const result = await this.mcpClient.saveSubscription(
                    userId,
                    userName,
                    organization,
                    remainingSymbols.join(',')
                );

                if (result.success) {
                    // Also remove from notification service
                    await this.notificationService.removeSubscription(userId, symbolList);

                    await send({
                        type: 'message',
                        text: `✅ **Successfully unsubscribed from:** ${symbolList.join(', ')}\n\n📈 **Remaining subscriptions:** ${remainingSymbols.join(', ')}\n\n💾 **Database Status:** Subscription updated successfully`
                    });
                } else {
                    await send({
                        type: 'message',
                        text: `❌ **Failed to update subscription in database**\n\n${result.error || 'Unknown error occurred'}`
                    });
                }
            } else {
                // Remove entire subscription if no symbols remain
                const result = await this.mcpClient.removeSubscription(userId);
                
                if (result.success) {
                    // Also remove from notification service
                    await this.notificationService.removeSubscription(userId, symbolList);

                    await send({
                        type: 'message',
                        text: `✅ **Successfully unsubscribed from:** ${symbolList.join(', ')}\n\n📭 **All subscriptions removed**\n\n💾 **Database Status:** Subscription removed successfully`
                    });
                } else {
                    await send({
                        type: 'message',
                        text: `❌ **Failed to remove subscription from database**\n\n${result.error || 'Unknown error occurred'}`
                    });
                }
            }

        } catch (error) {
            console.error('Unsubscribe command error:', error);
            await send({
                type: 'message',
                text: '❌ Failed to remove subscription. Please try again later.'
            });
        }
    }

    /**
     * Handle status command with detailed system diagnostics
     */
    private async handleStatusCommand(send: any, activity: any): Promise<void> {
        const detailed = activity.text.includes('detailed');

        await send({ type: 'typing' });

        try {
            const health = await this.mcpClient.getServiceHealth();
            const notificationStats = this.notificationService.getStats();
            
            // Prepare status data for the adaptive card
            const statusData = {
                health: health,
                botStatus: {
                    port: process.env.PORT || 3978,
                    mcpReady: this.mcpClient.isReady(),
                    timestamp: new Date().toISOString()
                },
                notificationStats: {
                    ...notificationStats,
                    isRunning: this.notificationService.isServiceRunning
                },
                serverUrls: this.mcpClient.getServerUrls(),
                detailed: detailed
            };

            // Create status adaptive card
            const statusCard = createStatusCard(statusData);
            
            await send({
                type: 'message',
                attachments: [{
                    contentType: 'application/vnd.microsoft.card.adaptive',
                    content: statusCard
                }]
            });

        } catch (error) {
            console.error('Status command error:', error);
            const errorCard = createErrorCard(
                'Failed to retrieve system status. Please try again later.',
                '❌ Status Error'
            );
            
            await send({
                type: 'message',
                attachments: [{
                    contentType: 'application/vnd.microsoft.card.adaptive',
                    content: errorCard
                }]
            });
        }
    }

        /**
     * Handle /inquiries command - view inquiries for a specific event
     */
    private async handleInquiriesCommand(send: any, activity: any): Promise<void> {
        const parts = activity.text.trim().split(' ');
        
        if (parts.length < 2) {
            const errorCard = createErrorCard(
                'Please provide an event ID. Example: `/inquiries event_123` or use `/inquiries list` to see recent events with IDs.',
                '📋 Event ID Required'
            );
            
            await send({
                type: 'message',
                attachments: [{
                    contentType: 'application/vnd.microsoft.card.adaptive',
                    content: errorCard
                }]
            });
            return;
        }

        const eventIdOrAction = parts[1];

        try {
            if (eventIdOrAction === 'list') {
                // Show recent events with their IDs for reference
                const userId = this.getUserId(activity);
                console.log(`🔍 /inquiries list - userId: ${userId}`);
                
                const result = await this.mcpClient.getUpcomingEvents(userId, 7); // Use same 7 days as dashboard
                console.log(`🔍 /inquiries list - getUpcomingEvents result:`, JSON.stringify(result, null, 2));
                
                let events = result.upcoming_events; // Fix: use upcoming_events instead of events
                
                // If no upcoming events, use sample events like dashboard does
                if (!events || events.length === 0) {
                    console.log(`🔍 /inquiries list - No upcoming events, getting sample events`);
                    events = await this.getSampleEvents();
                    console.log(`🔍 /inquiries list - Sample events count: ${events.length}`);
                }
                
                if (events && events.length > 0) {
                    // Get inquiries for the events from the inquiry collection
                    const allInquiries: any[] = [];
                    for (const event of events) {
                        try {
                            console.log(`🔍 Getting inquiries for event: ${event.event_id}`);
                            const inquiriesResult = await this.mcpClient.getInquiries(event.event_id);
                            console.log(`🔍 Inquiries result for ${event.event_id}:`, JSON.stringify(inquiriesResult, null, 2));
                            if (inquiriesResult.inquiries) {
                                allInquiries.push(...inquiriesResult.inquiries);
                            }
                        } catch (error) {
                            console.error(`Error getting inquiries for event ${event.event_id}:`, error);
                        }
                    }
                    
                    console.log(`🔍 /inquiries list - Total events: ${events.length}, Total inquiries: ${allInquiries.length}`);
                    
                    const eventsCard = createEventsListCard(events, allInquiries);
                    
                    await send({
                        type: 'message',
                        attachments: [{
                            contentType: 'application/vnd.microsoft.card.adaptive',
                            content: eventsCard
                        }]
                    });
                } else {
                    console.log(`🔍 /inquiries list - Still no events found after sample events fallback`);
                    const errorCard = createErrorCard(
                        'No events found. This might indicate an issue with the MCP server connection or sample data.',
                        '📋 No Events Found'
                    );
                    
                    await send({
                        type: 'message',
                        attachments: [{
                            contentType: 'application/vnd.microsoft.card.adaptive',
                            content: errorCard
                        }]
                    });
                }
            } else {
                // View inquiries for specific event
                const eventId = eventIdOrAction;
                const result = await this.mcpClient.getInquiries(eventId);
                
                if (result.inquiries && result.inquiries.length > 0) {
                    const inquiriesCard = createInquiriesListCard(result.inquiries, eventId);
                    
                    await send({
                        type: 'message',
                        attachments: [{
                            contentType: 'application/vnd.microsoft.card.adaptive',
                            content: inquiriesCard
                        }]
                    });
                } else {
                    const errorCard = createErrorCard(
                        `No inquiries found for event ${eventId}. You can create one with \`/create-inquiry ${eventId}\``,
                        '📋 No Inquiries Found'
                    );
                    
                    await send({
                        type: 'message',
                        attachments: [{
                            contentType: 'application/vnd.microsoft.card.adaptive',
                            content: errorCard
                        }]
                    });
                }
            }

        } catch (error) {
            console.error('Inquiries command error:', error);
            const errorCard = createErrorCard(
                'Failed to retrieve inquiries. Please try again later.',
                '❌ Inquiries Error'
            );
            
            await send({
                type: 'message',
                attachments: [{
                    contentType: 'application/vnd.microsoft.card.adaptive',
                    content: errorCard
                }]
            });
        }
    }

    /**
     * Handle /create-inquiry command - create new inquiry for an event
     */
    private async handleCreateInquiryCommand(send: any, activity: any): Promise<void> {
        const parts = activity.text.trim().split(' ');
        
        if (parts.length < 2) {
            const errorCard = createErrorCard(
                'Please provide an event ID. Example: `/create-inquiry event_123` or use `/inquiries list` to see available events.',
                '📋 Event ID Required'
            );
            
            await send({
                type: 'message',
                attachments: [{
                    contentType: 'application/vnd.microsoft.card.adaptive',
                    content: errorCard
                }]
            });
            return;
        }

        const eventId = parts[1];

        try {
            const userId = this.getUserId(activity);
            
            // Check if user already has an open inquiry for this event
            const userInquiriesResult = await this.mcpClient.getUserInquiries(eventId, userId);
            const openInquiries = (userInquiriesResult.inquiries || [])
                .filter((inq: any) => ['OPEN', 'ACKNOWLEDGED'].includes(inq.status));
            
            if (openInquiries.length > 0) {
                const errorCard = createErrorCard(
                    `You already have an open inquiry for this event (${openInquiries[0].inquiry_id}). Please resolve it before creating a new one, or use \`/edit-inquiry ${openInquiries[0].inquiry_id}\` to modify it.`,
                    '🚫 Open Inquiry Exists'
                );
                
                await send({
                    type: 'message',
                    attachments: [{
                        contentType: 'application/vnd.microsoft.card.adaptive',
                        content: errorCard
                    }]
                });
                return;
            }

            // Create inquiry form
            const eventData = {
                event_id: eventId,
                // We'll use placeholder data since we don't have full event details
                issuer_name: 'Corporate Action Event',
                security: { symbol: 'N/A' }
            };
            
            const inquiryForm = createInquiryFormCard(eventData, userId, activity.from?.name || 'Teams User');
            
            await send({
                type: 'message',
                attachments: [{
                    contentType: 'application/vnd.microsoft.card.adaptive',
                    content: inquiryForm
                }]
            });

        } catch (error) {
            console.error('Create inquiry command error:', error);
            const errorCard = createErrorCard(
                'Failed to create inquiry form. Please try again later.',
                '❌ Create Inquiry Error'
            );
            
            await send({
                type: 'message',
                attachments: [{
                    contentType: 'application/vnd.microsoft.card.adaptive',
                    content: errorCard
                }]
            });
        }
    }

    /**
     * Handle /edit-inquiry command - edit existing inquiry
     */
    private async handleEditInquiryCommand(send: any, activity: any): Promise<void> {
        const parts = activity.text.trim().split(' ');
        
        if (parts.length < 2) {
            const userId = this.getUserId(activity);
            
            // If no inquiry ID provided, show user's inquiries
            try {
                const result = await this.mcpClient.getUserInquiries('', userId);
                
                if (result.inquiries && result.inquiries.length > 0) {
                    const editableInquiriesCard = createEditableInquiriesListCard(result.inquiries, userId);
                    
                    await send({
                        type: 'message',
                        attachments: [{
                            contentType: 'application/vnd.microsoft.card.adaptive',
                            content: editableInquiriesCard
                        }]
                    });
                } else {
                    const errorCard = createErrorCard(
                        'You have no inquiries to edit. Create one first with `/create-inquiry event_id`',
                        '📋 No Inquiries Found'
                    );
                    
                    await send({
                        type: 'message',
                        attachments: [{
                            contentType: 'application/vnd.microsoft.card.adaptive',
                            content: errorCard
                        }]
                    });
                }
            } catch (error) {
                console.error('Edit inquiry command error:', error);
                const errorCard = createErrorCard(
                    'Failed to retrieve your inquiries. Please try again later.',
                    '❌ Edit Inquiry Error'
                );
                
                await send({
                    type: 'message',
                    attachments: [{
                        contentType: 'application/vnd.microsoft.card.adaptive',
                        content: errorCard
                    }]
                });
            }
            return;
        }

        const inquiryId = parts[1];

        try {
            const userId = this.getUserId(activity);
            
            // Get the specific inquiry
            const inquiry = await this.mcpClient.getInquiry(inquiryId);
            
            if (!inquiry || inquiry.error) {
                const errorCard = createErrorCard(
                    `Inquiry ${inquiryId} not found. Use \`/edit-inquiry\` without parameters to see your inquiries.`,
                    '📋 Inquiry Not Found'
                );
                
                await send({
                    type: 'message',
                    attachments: [{
                        contentType: 'application/vnd.microsoft.card.adaptive',
                        content: errorCard
                    }]
                });
                return;
            }

            // Check if user owns this inquiry
            if (inquiry.user_id !== userId) {
                const errorCard = createErrorCard(
                    'You can only edit your own inquiries. Use `/edit-inquiry` to see your inquiries.',
                    '🚫 Permission Denied'
                );
                
                await send({
                    type: 'message',
                    attachments: [{
                        contentType: 'application/vnd.microsoft.card.adaptive',
                        content: errorCard
                    }]
                });
                return;
            }

            // Check if inquiry is editable (not resolved)
            if (inquiry.status === 'RESOLVED') {
                const errorCard = createErrorCard(
                    'Cannot edit resolved inquiries. Create a new inquiry if needed.',
                    '🚫 Inquiry Resolved'
                );
                
                await send({
                    type: 'message',
                    attachments: [{
                        contentType: 'application/vnd.microsoft.card.adaptive',
                        content: errorCard
                    }]
                });
                return;
            }

            // Create editable inquiry form
            const eventData = {
                event_id: inquiry.event_id,
                issuer_name: inquiry.issuer_name || 'Corporate Action Event',
                security: { symbol: inquiry.symbol || 'N/A' }
            };
            
            const inquiryForm = createInquiryFormCard(
                eventData, 
                userId, 
                activity.from?.name || 'Teams User',
                inquiry // Pass existing inquiry for editing
            );
            
            await send({
                type: 'message',
                attachments: [{
                    contentType: 'application/vnd.microsoft.card.adaptive',
                    content: inquiryForm
                }]
            });

        } catch (error) {
            console.error('Edit inquiry command error:', error);
            const errorCard = createErrorCard(
                'Failed to edit inquiry. Please try again later.',
                '❌ Edit Inquiry Error'
            );
            
            await send({
                type: 'message',
                attachments: [{
                    contentType: 'application/vnd.microsoft.card.adaptive',
                    content: errorCard
                }]
            });
        }
    }

    /**
     * Handle notifications command with comprehensive preference management
     */
    private async handleNotificationsCommand(send: any, activity: any): Promise<void> {
        const parts = activity.text.split(' ');
        const subcommand = parts[1] || 'status';
        const userId = activity.from.id;

        try {
            if (subcommand === 'settings') {
                const settings = await this.notificationService.getUserSettings(userId);
                
                const settingsText = `⚙️ **Notification Settings**

📱 **Current Preferences:**
• Market Open Notifications: ${settings.marketOpen ? '✅ Enabled' : '❌ Disabled'}
• Market Close Notifications: ${settings.marketClose ? '✅ Enabled' : '❌ Disabled'}
• Breaking News Alerts: ${settings.breakingNews ? '✅ Enabled' : '❌ Disabled'}
• Weekly Digest: ${settings.weeklyDigest ? '✅ Enabled' : '❌ Disabled'}

📊 **Subscribed Symbols:** ${settings.subscribedSymbols.length > 0 ? settings.subscribedSymbols.join(', ') : 'None'}

🔧 **Quick Settings:**
• \`/notifications enable market\` - Enable market notifications
• \`/notifications disable market\` - Disable market notifications
• \`/notifications enable digest\` - Enable weekly digest
• \`/notifications disable digest\` - Disable weekly digest

💡 **Pro Tip:** Use natural language! Ask me "Turn on weekly digests" or "Disable market alerts"`;

                await send({ type: 'message', text: settingsText });

            } else if (subcommand === 'history') {
                const history = await this.notificationService.getNotificationHistory(userId, 10);
                
                if (history.length === 0) {
                    await send({ type: 'message', text: '📭 No recent notifications found.' });
                    return;
                }

                let historyText = '📜 **Recent Notification History:**\n\n';
                history.forEach((notification, index) => {
                    const time = format(notification.timestamp, 'PPp');
                    const type = notification.type.replace('_', ' ').toUpperCase();
                    const status = notification.success ? '✅' : '❌';
                    historyText += `${index + 1}. ${status} **${type}** - ${time}\n   ${notification.message}\n\n`;
                });

                await send({ type: 'message', text: historyText });

            } else if (subcommand.startsWith('enable') || subcommand.startsWith('disable')) {
                const action = subcommand;
                const setting = parts[2] || '';
                
                if (!setting) {
                    await send({
                        type: 'message',
                        text: '❓ Please specify what to enable/disable. Example: `/notifications enable market`'
                    });
                    return;
                }
                
                await this.notificationService.updateUserSettings(userId, setting, action === 'enable');
                
                await send({
                    type: 'message',
                    text: `✅ ${setting} notifications ${action}d successfully!`
                });

            } else {
                // Default: show notification status
                const status = await this.notificationService.getNotificationStatus(userId);
                
                const statusText = `🔔 **Notification Status**

📊 **Your Profile:**
• Active Subscriptions: ${status.activeSubscriptions}
• Recent Notifications: ${status.recentNotifications}
• Last Activity: ${status.lastActivity}

🔧 **Available Commands:**
• \`/notifications settings\` - View and manage preferences
• \`/notifications history\` - View recent notification history
• \`/subscribe [symbols]\` - Add new subscriptions
• \`/unsubscribe [symbols]\` - Remove subscriptions

💡 **Natural Language:** Try saying "Show my notification settings" or "Turn off market alerts"`;

                await send({ type: 'message', text: statusText });
            }

        } catch (error) {
            console.error('Notifications command error:', error);
            await send({
                type: 'message',
                text: '❌ Failed to access notification settings. Please try again later.'
            });
        }
    }

    /**
     * Handle adaptive card actions (new inquiry management)
     */
    private async handleAdaptiveCardActions(send: any, activity: any): Promise<void> {
        const action = activity.value?.action;
        
        switch (action) {
            case 'refresh_dashboard':
                await this.handleRefreshDashboard(send, activity);
                break;
                
            case 'create_inquiry':
                await this.handleCreateInquiry(send, activity);
                break;
                
            case 'view_inquiries':
                await this.handleViewInquiries(send, activity);
                break;
                
            case 'edit_inquiries':
                await this.handleEditInquiries(send, activity);
                break;
                
            case 'submit_inquiry':
                await this.handleSubmitInquiry(send, activity);
                break;
                
            case 'update_inquiry':
                await this.handleUpdateInquiry(send, activity);
                break;
                
            case 'back_to_dashboard':
                await this.handleRefreshDashboard(send, activity);
                break;
                
            case 'view_events':
                await this.handleEventsCommand(send, activity);
                break;
                
            case 'search_prompt':
                await send({
                    type: 'message',
                    text: '🔍 **AI-Powered Search**\n\nType `/search` followed by your query to search for corporate actions.\n\n**Examples:**\n• `/search dividend AAPL`\n• `/search stock splits this month`\n• `/search merger activity tech`\n\nOr just ask me naturally: *"Show me Tesla events"*'
                });
                break;
                
            case 'settings':
                await this.handleSettingsCommand(send, activity);
                break;
                
            case 'help':
                await this.handleHelpCommand(send);
                break;
                
            default:
                await send({
                    type: 'message',
                    text: '❓ Unknown action. Please try again.'
                });
        }
    }

    /**
     * Handle dashboard refresh
     */
    private async handleRefreshDashboard(send: any, activity: any): Promise<void> {
        try {
            const userId = this.getUserId(activity);
            
            // Get upcoming events and inquiries
            const [upcomingEvents, subscription] = await Promise.all([
                this.mcpClient.getUpcomingEvents(userId),
                this.mcpClient.getSubscription(userId)
            ]);
            
            const events = upcomingEvents.upcoming_events?.length > 0 
                ? upcomingEvents.upcoming_events 
                : await this.getSampleEvents();
            
            // Get all inquiries for the events
            const allInquiries: any[] = [];
            for (const event of events) {
                try {
                    const inquiriesResult = await this.mcpClient.getInquiries(event.event_id);
                    if (inquiriesResult.inquiries) {
                        allInquiries.push(...inquiriesResult.inquiries);
                    }
                } catch (error) {
                    console.error(`Error getting inquiries for event ${event.event_id}:`, error);
                }
            }
            
            const userName = activity.from?.name || 'Teams User';
            const dashboardCard = createDashboardCard(events, allInquiries, userName);
            
            await send({
                type: 'message',
                attachments: [{
                    contentType: 'application/vnd.microsoft.card.adaptive',
                    content: dashboardCard
                }]
            });
        } catch (error) {
            console.error('Error refreshing dashboard:', error);
            await send({
                type: 'message',
                text: '❌ **Error refreshing dashboard**\n\nI encountered an issue loading the latest data. Please try again in a moment or use `/help` to see available commands.'
            });
        }
    }

    /**
     * Get user ID from Teams activity
     */
    private getUserId(activity: any): string {
        return `teams_${activity.from?.aadObjectId || activity.from?.id || Date.now()}`;
    }
    
    /**
     * Handle create inquiry action
     */
    private async handleCreateInquiry(send: any, activity: any): Promise<void> {
        const eventData = {
            event_id: activity.value?.event_id,
            issuer_name: activity.value?.company,
            security: { symbol: activity.value?.symbol }
        };
        
        const inquiryForm = createInquiryFormCard(eventData, 'create');
        
        await send({
            type: 'message',
            attachments: [{
                contentType: 'application/vnd.microsoft.card.adaptive',
                content: inquiryForm
            }]
        });
    }

    private async handleSettingsCommand(send: any, activity: any): Promise<void> 
    {
        try {
            const userId = this.getUserId(activity);
            console.log(`🔍 Settings command - userId: ${userId}`);
            
            // Get settings from both sources
            const [notificationSettings, databaseSubscription] = await Promise.all([
                this.notificationService.getUserSettings(userId),
                this.mcpClient.getSubscription(userId)
            ]);
            
            console.log(`🔍 Settings command - notificationSettings:`, JSON.stringify(notificationSettings, null, 2));
            console.log(`🔍 Settings command - databaseSubscription:`, JSON.stringify(databaseSubscription, null, 2));
            
            // Merge the settings data
            let subscribedSymbols: string[] = [];
            let userName = activity.from?.name || 'Teams User';
            let organization = 'Microsoft Teams';
            
            // Get subscribed symbols from database if available
            if (databaseSubscription.subscription && databaseSubscription.subscription.symbols) {
                subscribedSymbols = databaseSubscription.subscription.symbols;
                userName = databaseSubscription.subscription.user_name || userName;
                organization = databaseSubscription.subscription.organization || organization;
                console.log(`🔍 Settings command - using database symbols:`, subscribedSymbols);
            }
            
            // If no database subscription, fall back to notification service
            if (subscribedSymbols.length === 0 && notificationSettings.subscribedSymbols) {
                subscribedSymbols = notificationSettings.subscribedSymbols;
                console.log(`🔍 Settings command - using notification service symbols:`, subscribedSymbols);
            }
            
            console.log(`🔍 Settings command - final subscribedSymbols:`, subscribedSymbols);
            
            // Create combined settings object
            const combinedSettings = {
                ...notificationSettings,
                subscribedSymbols: subscribedSymbols,
                userName: userName,
                organization: organization,
                databaseSubscription: databaseSubscription.subscription ? 'Connected' : 'Not found',
                localNotifications: notificationSettings.subscribedSymbols?.length > 0 ? 'Active' : 'Inactive'
            };
            
            console.log(`🔍 Settings command - combinedSettings:`, JSON.stringify(combinedSettings, null, 2));
            
            // Create settings adaptive card
            const settingsCard = createSettingsCard(combinedSettings);
            
            await send({
                type: 'message',
                attachments: [{
                    contentType: 'application/vnd.microsoft.card.adaptive',
                    content: settingsCard
                }]
            });

        } catch (error) {
            console.error('Settings command error:', error);
            const errorCard = createErrorCard(
                `Failed to load settings: ${error.message || 'Unknown error'}. Please try again later.`,
                '❌ Settings Error'
            );
            
            await send({
                type: 'message',
                attachments: [{
                    contentType: 'application/vnd.microsoft.card.adaptive',
                    content: errorCard
                }]
            });
        }
    }

    /**
     * Handle edit inquiries action - show user's inquiries for editing
     */
    private async handleEditInquiries(send: any, activity: any): Promise<void> {
        try {
            const userId = this.getUserId(activity);
            const eventId = activity.value?.event_id;
            const eventData = {
                event_id: eventId,
                issuer_name: activity.value?.company,
                security: { symbol: activity.value?.symbol }
            };
            
            // Get user's inquiries for this event
            const userInquiriesResult = await this.mcpClient.getUserInquiries(userId, eventId);
            const userInquiries = userInquiriesResult.inquiries || [];
            
            if (userInquiries.length === 0) {
                await send({
                    type: 'message',
                    text: `📭 **No Inquiries to Edit**\n\nYou haven't created any inquiries for this event yet.\n\n💡 Use the "Create Inquiry" button to submit your first inquiry for **${eventData.issuer_name}** (${eventData.security.symbol}).`
                });
                return;
            }
            
            // Create editable inquiries list card
            const editableInquiriesCard = createEditableInquiriesListCard(userInquiries, eventData);
            
            await send({
                type: 'message',
                attachments: [{
                    contentType: 'application/vnd.microsoft.card.adaptive',
                    content: editableInquiriesCard
                }]
            });
        } catch (error) {
            console.error('Error handling edit inquiries:', error);
            await send({
                type: 'message',
                text: '❌ **Error loading your inquiries**\n\nI encountered an issue loading your inquiries for editing. Please try again.'
            });
        }
    }

    /**
     * Handle update inquiry action - process inquiry updates
     */
    private async handleUpdateInquiry(send: any, activity: any): Promise<void> {
        try {
            const userId = this.getUserId(activity);
            const inquiryId = activity.value?.inquiry_id;
            const subject = activity.value?.subject;
            const description = activity.value?.description;
            const priority = activity.value?.priority;
            
            if (!inquiryId) {
                await send({
                    type: 'message',
                    text: '❌ **Invalid Inquiry**\n\nNo inquiry ID provided for update. Please try again.'
                });
                return;
            }
            
            // Validate required fields
            if (!subject?.trim() || !description?.trim()) {
                await send({
                    type: 'message',
                    text: '❌ **Missing Information**\n\nPlease provide both a subject and description for your inquiry.'
                });
                return;
            }
            
            const result = await this.mcpClient.updateInquiry(
                inquiryId,
                userId,
                subject.trim(),
                description.trim(),
                priority || 'MEDIUM'
            );
            
            if (result.success) {
                await send({
                    type: 'message',
                    text: `✅ **Inquiry Updated Successfully!**\n\n📋 **Inquiry ID:** ${inquiryId}\n🏢 **Event:** ${activity.value?.company} (${activity.value?.symbol})\n📝 **Updated Subject:** ${subject}\n\n💡 Your changes have been saved. You can view all inquiries using the dashboard.`
                });
                
                // Refresh dashboard to show updated inquiry
                await this.handleRefreshDashboard(send, activity);
            } else {
                await send({
                    type: 'message',
                    text: `❌ **Failed to update inquiry**\n\n${result.error || 'Unknown error occurred'}\n\nPlease check that you have permission to edit this inquiry and try again.`
                });
            }
        } catch (error) {
            console.error('Error updating inquiry:', error);
            await send({
                type: 'message',
                text: '❌ **Error updating inquiry**\n\nI encountered an issue updating your inquiry. Please try again.'
            });
        }
    }

    /**
     * Handle view inquiries action
     */
    private async handleViewInquiries(send: any, activity: any): Promise<void> {
        try {
            const eventId = activity.value?.event_id;
            const eventData = {
                event_id: eventId,
                issuer_name: activity.value?.company,
                security: { symbol: activity.value?.symbol }
            };
            
            const inquiriesResult = await this.mcpClient.getInquiries(eventId);
            const inquiries = inquiriesResult.inquiries || [];
            
            const inquiriesCard = createInquiriesListCard(inquiries, eventData);
            
            await send({
                type: 'message',
                attachments: [{
                    contentType: 'application/vnd.microsoft.card.adaptive',
                    content: inquiriesCard
                }]
            });
        } catch (error) {
            console.error('Error viewing inquiries:', error);
            await send({
                type: 'message',
                text: '❌ **Error loading inquiries**\n\nI encountered an issue loading the inquiries. Please try again.'
            });
        }
    }

    /**
     * Handle submit inquiry action
     */
    private async handleSubmitInquiry(send: any, activity: any): Promise<void> {
        try {
            const userId = this.getUserId(activity);
            const userName = activity.from?.name || 'Teams User';
            const organization = 'Microsoft Teams';
            
            const result = await this.mcpClient.createInquiry(
                activity.value?.event_id,
                userId,
                userName,
                organization,
                activity.value?.subject,
                activity.value?.description,
                activity.value?.priority
            );
            
            if (result.success) {
                await send({
                    type: 'message',
                    text: `✅ **Inquiry Created Successfully!**\n\n📋 **Inquiry ID:** ${result.inquiry_id}\n🏢 **Event:** ${activity.value?.company} (${activity.value?.symbol})\n📝 **Subject:** ${activity.value?.subject}\n\n💡 You can track this inquiry using the View Inquiries button on the dashboard.`
                });
                
                // Refresh dashboard
                await this.handleRefreshDashboard(send, activity);
            } else {
                await send({
                    type: 'message',
                    text: `❌ **Failed to create inquiry**\n\n${result.error || 'Unknown error occurred'}\n\nPlease try again or contact support.`
                });
            }
        } catch (error) {
            console.error('Error submitting inquiry:', error);
            await send({
                type: 'message',
                text: '❌ **Error creating inquiry**\n\nI encountered an issue creating your inquiry. Please try again.'
            });
        }
    }

    /**
     * Get sample events for demo purposes
     */
    private async getSampleEvents(): Promise<any[]> {
        return [
            {
                event_id: "AAPL_DIVIDEND_2025_Q2_001",
                event_type: "DIVIDEND",
                security: { symbol: "AAPL" },
                issuer_name: "Apple Inc.",
                status: "ANNOUNCED",
                announcement_date: "2025-06-10",
                description: "$0.25 quarterly cash dividend declared",
                event_details: { dividend_amount: 0.25 }
            },
            {
                event_id: "TSLA_STOCK_SPLIT_2025_001",
                event_type: "STOCK_SPLIT",
                security: { symbol: "TSLA" },
                issuer_name: "Tesla, Inc.",
                status: "CONFIRMED", 
                announcement_date: "2025-06-08",
                description: "3-for-1 stock split announced",
                event_details: { split_ratio_from: 1, split_ratio_to: 3 }
            },
            {
                event_id: "MSFT_DIVIDEND_2025_Q2_002",
                event_type: "DIVIDEND",
                security: { symbol: "MSFT" },
                issuer_name: "Microsoft Corporation",
                status: "COMPLETED",
                announcement_date: "2025-06-05",
                description: "$0.75 quarterly cash dividend completed",
                event_details: { dividend_amount: 0.75 }
            }
        ];
    }
    
    /**
     * Handle natural language queries using enhanced RAG
     */
    private async handleNaturalLanguageQuery(send: any, activity: any): Promise<void> {
        const query = activity.text.trim();
        const userId = activity.from.id;

        if (!query) {
            return;
        }

        await send({ type: 'typing' });

        try {
            // Get conversation history for context
            const chatHistory = this.getConversationHistory(userId);

            // Use enhanced RAG query
            const response = await this.mcpClient.ragQuery(
                query,
                5,
                true,
                chatHistory
            );

            // Update conversation history
            this.addToConversationHistory(userId, 'user', query);

            if (response.error) {
                const errorCard = createErrorCard(
                    `I encountered an issue: ${response.error}`,
                    '❌ Query Error'
                );
                
                await send({
                    type: 'message',
                    attachments: [{
                        contentType: 'application/vnd.microsoft.card.adaptive',
                        content: errorCard
                    }]
                });
                return;
            }

            // Create adaptive card for natural language response
            const responseCard = createRAGSearchCard(response, query);
            
            await send({
                type: 'message',
                attachments: [{
                    contentType: 'application/vnd.microsoft.card.adaptive',
                    content: responseCard
                }]
            });

            // Add response to conversation history
            this.addToConversationHistory(userId, 'assistant', response.answer || "I'm not sure about that.");

        } catch (error) {
            console.error('Natural language query error:', error);
            const errorCard = createErrorCard(
                'I apologize, but I encountered an issue processing your request. Please try again or use specific commands like `/search` or `/events`.',
                '❌ Processing Error'
            );
            
            await send({
                type: 'message',
                attachments: [{
                    contentType: 'application/vnd.microsoft.card.adaptive',
                    content: errorCard
                }]
            });
        }
    }

    /**
     * Get conversation history for a user
     */
    private getConversationHistory(userId: string): Array<{role: string, content: string}> {
        return this.conversationHistory.get(userId) || [];
    }

    /**
     * Add message to conversation history
     */
    private addToConversationHistory(userId: string, role: string, content: string): void {
        if (!this.conversationHistory.has(userId)) {
            this.conversationHistory.set(userId, []);
        }

        const history = this.conversationHistory.get(userId)!;
        history.push({ role, content });

        // Keep only last 10 messages for context
        if (history.length > 10) {
            this.conversationHistory.set(userId, history.slice(-10));
        }
    }
}
