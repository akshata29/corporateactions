import { App } from '@microsoft/teams.apps';
import { MCPClientManager } from './services/mcpClientManager';
import { NotificationService } from './services/notificationService';
import { format } from 'date-fns';

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
        this.app = app;
        this.mcpClient = mcpClient;
        this.notificationService = notificationService;
    }

    /**
     * Register all bot event handlers and commands
     */
    registerHandlers(): void {
        // Welcome message for new conversations
        this.app.on('membersAdded', async ({ send, activity }) => {
            await this.sendWelcomeMessage(send);
        });

        // Help command
        this.app.on('message', async ({ send, activity }) => {
            const text = activity.text?.toLowerCase().trim() || '';
            
            if (text.startsWith('/help')) {
                await this.handleHelpCommand(send);
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

            // Comment command
            if (text.startsWith('/comment')) {
                await this.handleCommentCommand(send, activity);
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
     * Send enhanced welcome message
     */
    private async sendWelcomeMessage(send: any): Promise<void> {
        const welcomeText = `🏦 **Welcome to Enhanced Corporate Actions Bot!**

I'm powered by advanced MCP (Model Context Protocol) servers and can help you with:

📊 **AI-Powered Capabilities:**
• **Smart Search**: Ask complex questions like "Show me dividend announcements this week over $1"
• **RAG Assistant**: Context-aware conversations with chat history
• **Event Analysis**: AI-powered insights and recommendations
• **Natural Language**: Just talk to me normally - I understand context!

🔔 **Proactive Notifications:**
• Breaking corporate action announcements
• Status updates on subscribed events
• Market open/close summaries with highlights
• Weekly digests for your portfolio

💬 **Enhanced Commands:**
• \`/help\` - Comprehensive guide and capabilities
• \`/search [query]\` - AI-powered search with confidence scoring
• \`/events [filters]\` - Recent actions with smart filtering
• \`/subscribe [symbols]\` - Smart notifications for symbols
• \`/status\` - Check MCP server health and capabilities
• \`/notifications\` - Manage preferences and history

🤖 **Just ask me naturally!**
Try: *"What are the upcoming Tesla events?"* or *"Analyze dividend trends for tech stocks"*

I maintain conversation context and provide intelligent follow-ups!`;

        await send({
            type: 'message',
            text: welcomeText,
            attachments: [{
                contentType: 'application/vnd.microsoft.card.adaptive',
                content: {
                    type: 'AdaptiveCard',
                    version: '1.3',
                    body: [
                        {
                            type: 'TextBlock',
                            text: '🚀 Quick Actions',
                            weight: 'Bolder',
                            size: 'Medium'
                        },
                        {
                            type: 'ActionSet',
                            actions: [
                                {
                                    type: 'Action.Submit',
                                    title: '📊 Recent Events',
                                    data: { action: 'events' }
                                },
                                {
                                    type: 'Action.Submit', 
                                    title: '🔍 Smart Search',
                                    data: { action: 'search', query: 'dividend tech companies' }
                                },
                                {
                                    type: 'Action.Submit',
                                    title: '🔔 Setup Notifications',
                                    data: { action: 'subscribe', symbols: 'AAPL,MSFT,GOOGL' }
                                }
                            ]
                        }
                    ]
                }
            }]
        });
    }

    /**
     * Handle help command with comprehensive guide
     */
    private async handleHelpCommand(send: any): Promise<void> {
        const helpText = `🔍 **Enhanced Corporate Actions Bot - Command Guide**

**🔍 Search & Query (AI-Powered):**
• \`/search dividend AAPL\` - Search with AI insights and confidence scoring
• \`/events\` - Recent actions with smart filtering and status indicators
• \`/events confirmed 10\` - Show 10 confirmed events
• Natural language: *"Show me Tesla stock splits"* - Context-aware responses

**💬 Subscription & Notifications:**
• \`/subscribe AAPL,MSFT,GOOGL\` - Multi-symbol smart subscriptions
• \`/unsubscribe TSLA\` - Remove specific symbols
• \`/notifications settings\` - Configure notification preferences
• \`/notifications history\` - View recent notification history

**💬 Comments & Collaboration:**
• \`/comment CA-2025-001 This needs clarification\` - Add structured comments
• \`/comment CA-2025-001 question What's the timeline?\` - Categorized questions

**🛠️ System & Status:**
• \`/status\` - Check MCP server health and capabilities
• \`/status detailed\` - Detailed system diagnostics with performance metrics
• \`/help\` - Show this enhanced help guide

**🤖 AI Features:**
• **Context Awareness**: I remember our conversation history
• **Smart Insights**: AI-powered analysis with confidence scoring
• **Dynamic Responses**: Contextual follow-ups and clarifications
• **Multi-modal Support**: Rich formatting with charts and graphs
• **MCP Integration**: Real-time data from specialized servers

**💡 Pro Tips:**
• Use natural language for complex queries - I understand context!
• Subscribe to symbols you track regularly for proactive updates
• Ask follow-up questions - I maintain conversation history
• Check \`/status\` if experiencing issues with data freshness

**🔔 Proactive Notifications Include:**
• 🚨 Breaking corporate action announcements
• 📈 Market open/close summaries with key highlights
• 💬 Comments and updates on events you're following
• 📊 Weekly/monthly digest of your subscribed symbols

**📊 Example Natural Language Queries:**
• "What dividend events happened this week with amounts over $2?"
• "Show me upcoming stock splits and their ratios"
• "Analyze merger activity in the technology sector"
• "Create a summary of FAANG dividend announcements this quarter"`;

        await send({ type: 'message', text: helpText });
    }

    /**
     * Handle search command with enhanced AI integration
     */
    private async handleSearchCommand(send: any, activity: any): Promise<void> {
        const query = activity.text.substring(7).trim(); // Remove "/search "
        
        if (!query) {
            await send({
                type: 'message',
                text: '🔍 Please provide a search query. Example: `/search dividend announcements this week`'
            });
            return;
        }

        await send({ type: 'typing' });
        await send({
            type: 'message',
            text: `🔍 Searching with AI insights: *${query}*`
        });

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
                await send({
                    type: 'message',
                    text: `❌ Search error: ${response.error}`
                });
                return;
            }

            const answer = response.answer || 'No results found';
            const sources = response.sources || [];
            const confidence = response.confidence_score || 0.0;
            const requiresViz = response.requires_visualization || false;

            // Format enhanced response
            let formattedResponse = `🤖 **AI-Powered Search Results:**\n\n${answer}`;

            // Add confidence indicator
            if (confidence > 0.8) {
                formattedResponse += `\n\n✅ **High Confidence** (${(confidence * 100).toFixed(0)}%)`;
            } else if (confidence > 0.6) {
                formattedResponse += `\n\n⚠️ **Medium Confidence** (${(confidence * 100).toFixed(0)}%)`;
            } else {
                formattedResponse += `\n\n❓ **Lower Confidence** (${(confidence * 100).toFixed(0)}%) - Consider refining your query`;
            }

            // Add visualization note if detected
            if (requiresViz) {
                formattedResponse += '\n\n📊 *This query would benefit from visualizations. Try our Streamlit dashboard for charts!*';
            }

            // Add sources with enhanced formatting
            if (sources.length > 0) {
                formattedResponse += '\n\n🔗 **Related Events:**';
                sources.slice(0, 3).forEach((source: any, index: number) => {
                    const company = source.issuer_name || source.company_name || 'Unknown';
                    const eventType = (source.event_type || 'Unknown').replace('_', ' ');
                    const status = source.status || 'Unknown';
                    const statusEmoji = {
                        'confirmed': '✅', 'announced': '📅', 'pending': '⏳', 
                        'processed': '✅', 'cancelled': '❌'
                    }[status] || '❓';
                    
                    formattedResponse += `\n${index + 1}. ${statusEmoji} **${company}** - ${eventType} (${source.event_id || 'N/A'})`;
                });
            }

            await send({ type: 'message', text: formattedResponse });

            // Add response to conversation history
            this.addToConversationHistory(userId, 'assistant', answer);

        } catch (error) {
            console.error('Search command error:', error);
            await send({
                type: 'message',
                text: '❌ Sorry, I encountered an issue with the search service. Please try again later.'
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
        await send({ type: 'message', text: '📊 Fetching recent corporate actions...' });

        try {
            const searchParams: any = { limit };
            
            if (statusFilter) {
                searchParams.status = statusFilter;
            }

            const eventsData = await this.mcpClient.searchCorporateActions(searchParams);

            if (eventsData.error) {
                await send({
                    type: 'message',
                    text: `❌ Error retrieving events: ${eventsData.error}`
                });
                return;
            }

            const events = eventsData.events || [];

            if (events.length === 0) {
                const filterMsg = statusFilter ? ` with status '${statusFilter}'` : '';
                await send({
                    type: 'message',
                    text: `📊 No recent corporate actions found${filterMsg}.`
                });
                return;
            }

            // Format events with enhanced styling
            let eventsText = `📈 **Recent Corporate Actions** (${events.length} found):\n\n`;

            events.forEach((event: any, index: number) => {
                const company = event.issuer_name || event.company_name || 'Unknown';
                const symbol = event.symbol || 'N/A';
                const eventType = (event.event_type || 'Unknown').replace('_', ' ');
                const status = event.status || 'Unknown';
                const announced = event.announcement_date || 'Unknown';
                const eventId = event.event_id || 'N/A';

                // Status emoji mapping
                const statusEmoji = {
                    'confirmed': '✅', 'announced': '📅', 'pending': '⏳',
                    'processed': '✅', 'cancelled': '❌'
                }[status] || '❓';

                // Event type emoji mapping
                const typeEmoji = {
                    'dividend': '💰', 'stock split': '📈', 'merger': '🤝',
                    'spinoff': '🔄', 'acquisition': '🏢', 'rights': '📜'
                }[eventType.toLowerCase()] || '📊';

                eventsText += `**${index + 1}. ${typeEmoji} ${company} (${symbol})**\n`;
                eventsText += `${statusEmoji} Status: ${status}\n`;
                eventsText += `📅 Announced: ${announced}\n`;
                eventsText += `🆔 ID: \`${eventId}\`\n`;
                eventsText += `Type: ${eventType}\n\n`;
            });

            // Add helpful actions
            eventsText += '💡 **Actions:**\n';
            eventsText += '• Use `/comment [event_id] [message]` to add comments\n';
            eventsText += '• Ask me natural language questions about these events\n';
            eventsText += '• Use `/subscribe [symbol]` for future notifications';

            await send({ type: 'message', text: eventsText });

        } catch (error) {
            console.error('Events command error:', error);
            await send({
                type: 'message',
                text: '❌ Failed to retrieve events. Please try again later.'
            });
        }
    }

    /**
     * Handle subscribe command with enhanced subscription management
     */
    private async handleSubscribeCommand(send: any, activity: any): Promise<void> {
        const symbols = activity.text.substring(10).trim(); // Remove "/subscribe "
        
        if (!symbols) {
            await send({
                type: 'message',
                text: '🔔 Please provide symbols to subscribe to. Example: `/subscribe AAPL,MSFT,GOOGL`'
            });
            return;
        }

        try {
            const userId = activity.from.id;
            const userName = activity.from.name || 'Unknown User';
            const conversationId = activity.conversation.id;
            const serviceUrl = activity.serviceUrl;

            const symbolList = symbols.split(',').map((s: string) => s.trim().toUpperCase()).filter((s: string) => s);
            
            await this.notificationService.addSubscription(
                userId,
                userName,
                symbolList,
                conversationId,
                serviceUrl
            );

            const confirmText = `✅ **Subscription Confirmed!**

📈 **Subscribed to:** ${symbolList.join(', ')}
👤 **User:** ${userName}
🔔 **You'll receive notifications for:**
• New corporate action announcements
• Status updates on existing events
• Market summaries (if enabled)
• Comments and Q&A updates

🛠️ **Manage your subscriptions:**
• \`/unsubscribe [symbols]\` - Remove specific symbols
• \`/notifications settings\` - Configure preferences
• \`/notifications history\` - View recent alerts

🤖 **Try asking:** "What's new with my subscribed symbols?" or "Show me upcoming events for my portfolio"`;

            await send({ type: 'message', text: confirmText });

        } catch (error) {
            console.error('Subscribe command error:', error);
            await send({
                type: 'message',
                text: '❌ Failed to add subscription. Please try again later.'
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
            const userId = activity.from.id;
            const symbolList = symbols.split(',').map((s: string) => s.trim().toUpperCase()).filter((s: string) => s);
            
            await this.notificationService.removeSubscription(userId, symbolList);

            await send({
                type: 'message',
                text: `✅ Successfully unsubscribed from: **${symbolList.join(', ')}**`
            });

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
        await send({ type: 'message', text: '🔧 Checking system health...' });

        try {
            const health = await this.mcpClient.getServiceHealth();
            const notificationStats = this.notificationService.getStats();

            let statusText = '🔧 **System Status Report**\n\n';

            // MCP Server Status
            statusText += '🖥️ **MCP Server Health:**\n';
            Object.entries(health).forEach(([name, status]: [string, any]) => {
                const emoji = status.status === 'healthy' ? '✅' : '❌';
                statusText += `${emoji} **${name.toUpperCase()}**: ${status.status}\n`;
                if (detailed && status.error) {
                    statusText += `   Error: ${status.error}\n`;
                }
            });

            // Notification Service Status
            statusText += `\n🔔 **Notification Service:**\n`;
            statusText += `📊 Active Subscriptions: ${notificationStats.totalSubscriptions}\n`;
            statusText += `📨 Total Notifications Sent: ${notificationStats.totalNotificationsSent}\n`;
            statusText += `✅ Success Rate: ${notificationStats.successRate.toFixed(1)}%\n`;
            statusText += `📈 Unique Symbols Tracked: ${notificationStats.uniqueSymbols}\n`;

            if (detailed) {
                statusText += `\n🔧 **Technical Details:**\n`;
                statusText += `🌐 Server URLs:\n`;
                Object.entries(this.mcpClient.getServerUrls()).forEach(([name, url]) => {
                    statusText += `   ${name}: ${url}\n`;
                });
                statusText += `⏰ Current Time: ${format(new Date(), 'PPpp')}\n`;
                statusText += `🚀 Bot Ready: ${this.mcpClient.isReady() ? 'Yes' : 'No'}\n`;
            }

            statusText += '\n💡 **Quick Actions:**\n';
            statusText += '• Try a search query to test MCP integration\n';
            statusText += '• Check `/notifications settings` for your preferences\n';
            statusText += '• Use `/help` for comprehensive guidance';

            await send({ type: 'message', text: statusText });

        } catch (error) {
            console.error('Status command error:', error);
            await send({
                type: 'message',
                text: '❌ Failed to retrieve system status. Please try again later.'
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
     * Handle comment command for event collaboration
     */
    private async handleCommentCommand(send: any, activity: any): Promise<void> {
        const parts = activity.text.split(' ');
        if (parts.length < 3) {
            await send({
                type: 'message',
                text: '💬 Usage: `/comment [event_id] [your comment]`\nExample: `/comment CA-2025-001 This needs clarification`'
            });
            return;
        }

        const eventId = parts[1];
        const comment = parts.slice(2).join(' ');
        const userName = activity.from.name || 'Unknown User';

        try {
            await send({ type: 'typing' });

            const result = await this.mcpClient.addComment(eventId, userName, comment);

            if (result.success) {
                await send({
                    type: 'message',
                    text: `✅ **Comment Added Successfully**\n\n📝 **Event:** ${eventId}\n👤 **User:** ${userName}\n💬 **Comment:** ${comment}\n\n💡 Ask me: "Show comments for ${eventId}" to see all discussions`
                });
            } else {
                await send({
                    type: 'message',
                    text: `❌ Failed to add comment: ${result.error || 'Unknown error'}`
                });
            }

        } catch (error) {
            console.error('Comment command error:', error);
            await send({
                type: 'message',
                text: '❌ Failed to add comment. Please try again later.'
            });
        }
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
                await send({
                    type: 'message',
                    text: `❌ I encountered an issue: ${response.error}`
                });
                return;
            }

            const answer = response.answer || "I'm not sure about that. Could you try rephrasing your question?";
            const confidence = response.confidence_score || 0.0;
            const requiresViz = response.requires_visualization || false;

            let responseText = `🤖 ${answer}`;

            // Add confidence indicator for lower confidence responses
            if (confidence < 0.7) {
                responseText += `\n\n💡 *I'm ${(confidence * 100).toFixed(0)}% confident in this response. Feel free to ask for clarification or try a more specific question.*`;
            }

            // Suggest visualization if detected
            if (requiresViz) {
                responseText += '\n\n📊 *This data would look great in a chart! Check out our Streamlit dashboard for visualizations.*';
            }

            // Add contextual follow-up suggestions
            if (response.sources && response.sources.length > 0) {
                responseText += '\n\n💡 **Follow up with:**';
                responseText += '\n• "Tell me more about [specific event]"';
                responseText += '\n• "Show me related events"';
                responseText += '\n• "What are the implications?"';
            }

            await send({ type: 'message', text: responseText });

            // Add response to conversation history
            this.addToConversationHistory(userId, 'assistant', answer);

        } catch (error) {
            console.error('Natural language query error:', error);
            await send({
                type: 'message',
                text: '❌ I apologize, but I encountered an issue processing your request. Please try again or use specific commands like `/search` or `/events`.'
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
