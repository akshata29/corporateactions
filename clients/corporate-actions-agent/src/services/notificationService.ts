import { App } from '@microsoft/teams.apps';
import * as schedule from 'node-schedule';
import { format } from 'date-fns';

interface UserSubscription {
    userId: string;
    userName: string;
    symbols: string[];
    preferences: NotificationPreferences;
    conversationId: string;
    serviceUrl: string;
    createdAt: Date;
    lastActivity: Date;
}

interface NotificationPreferences {
    marketOpen: boolean;
    marketClose: boolean;
    breakingNews: boolean;
    weeklyDigest: boolean;
    immediateAlerts: boolean;
}

interface NotificationHistoryItem {
    timestamp: Date;
    type: string;
    message: string;
    symbols?: string[];
    success: boolean;
    userId: string;
}

interface PendingNotification {
    userId: string;
    userName: string;
    card: any;
    message: string;
    timestamp: Date;
}

/**
 * Enhanced Notification Service for proactive Teams messaging
 */
export class NotificationService {
    private subscriptions: Map<string, UserSubscription> = new Map();
    private notificationHistory: NotificationHistoryItem[] = [];
    private scheduledJobs: schedule.Job[] = [];
    private isRunning: boolean = false;
    private pendingNotifications: PendingNotification[] = [];

    constructor(private app: App) {
        console.log('🔔 NotificationService initialized');
    }

    async start(): Promise<void> {
        if (this.isRunning) {
            console.log('⚠️ Notification service is already running');
            return;
        }

        this.isRunning = true;
        console.log('🔔 Starting enhanced notification service...');

        // Schedule market open notifications (9:30 AM ET, Monday-Friday)
        const marketOpenJob = schedule.scheduleJob('30 9 * * 1-5', () => {
            this.sendMarketOpenNotifications();
        });
        this.scheduledJobs.push(marketOpenJob);

        // Schedule market close notifications (4:00 PM ET, Monday-Friday)  
        const marketCloseJob = schedule.scheduleJob('0 16 * * 1-5', () => {
            this.sendMarketCloseNotifications();
        });
        this.scheduledJobs.push(marketCloseJob);

        // Schedule weekly digest (Sunday 8:00 AM)
        const weeklyDigestJob = schedule.scheduleJob('0 8 * * 0', () => {
            this.sendWeeklyDigest();
        });
        this.scheduledJobs.push(weeklyDigestJob);

        console.log(`✅ Notification service started with ${this.scheduledJobs.length} scheduled jobs`);
    }

    async stop(): Promise<void> {
        if (!this.isRunning) {
            return;
        }

        console.log('🛑 Stopping notification service...');
        
        // Cancel all scheduled jobs
        this.scheduledJobs.forEach(job => {
            job.cancel();
        });
        this.scheduledJobs = [];
        
        this.isRunning = false;
        console.log('✅ Notification service stopped');
    }

    async addSubscription(
        userId: string, 
        userName: string, 
        symbols: string[],
        conversationId: string,
        serviceUrl: string
    ): Promise<void> {
        const existingSubscription = this.subscriptions.get(userId);
        
        const subscription: UserSubscription = {
            userId,
            userName,
            symbols: [...new Set([...(existingSubscription?.symbols || []), ...symbols])],
            preferences: existingSubscription?.preferences || {
                marketOpen: true,
                marketClose: true,
                breakingNews: true,
                weeklyDigest: true,
                immediateAlerts: true
            },
            conversationId,
            serviceUrl,
            createdAt: existingSubscription?.createdAt || new Date(),
            lastActivity: new Date()
        };

        this.subscriptions.set(userId, subscription);
        
        this.addNotificationHistory({
            timestamp: new Date(),
            type: 'subscription_added',
            message: `Subscribed to: ${symbols.join(', ')}`,
            symbols,
            success: true,
            userId
        });

        console.log(`✅ Added subscription for ${userName} (${userId}) to symbols: ${symbols.join(', ')}`);
    }

    async removeSubscription(userId: string, symbols: string[]): Promise<void> {
        const subscription = this.subscriptions.get(userId);
        if (!subscription) {
            throw new Error('No subscription found for user');
        }

        subscription.symbols = subscription.symbols.filter(s => !symbols.includes(s));
        subscription.lastActivity = new Date();

        if (subscription.symbols.length === 0) {
            this.subscriptions.delete(userId);
        } else {
            this.subscriptions.set(userId, subscription);
        }

        this.addNotificationHistory({
            timestamp: new Date(),
            type: 'subscription_removed',
            message: `Unsubscribed from: ${symbols.join(', ')}`,
            symbols,
            success: true,
            userId
        });

        console.log(`✅ Removed subscription for ${userId} from symbols: ${symbols.join(', ')}`);
    }

    async getUserSettings(userId: string): Promise<{
        subscribedSymbols: string[];
        marketOpen: boolean;
        marketClose: boolean;
        breakingNews: boolean;
        weeklyDigest: boolean;
    }> {
        const subscription = this.subscriptions.get(userId);
        
        return {
            subscribedSymbols: subscription?.symbols || [],
            marketOpen: subscription?.preferences.marketOpen || false,
            marketClose: subscription?.preferences.marketClose || false,
            breakingNews: subscription?.preferences.breakingNews || false,
            weeklyDigest: subscription?.preferences.weeklyDigest || false
        };
    }

    async updateUserSettings(userId: string, setting: string, enabled: boolean): Promise<void> {
        const subscription = this.subscriptions.get(userId);
        if (!subscription) {
            throw new Error('No subscription found for user');
        }

        // Map setting names to preference keys
        const settingMap: { [key: string]: keyof NotificationPreferences } = {
            'marketopen': 'marketOpen',
            'marketclose': 'marketClose',
            'breaking': 'breakingNews',
            'weekly': 'weeklyDigest'
        };

        const preferenceKey = settingMap[setting];
        if (!preferenceKey) {
            throw new Error(`Invalid setting: ${setting}`);
        }

        subscription.preferences[preferenceKey] = enabled;
        subscription.lastActivity = new Date();
        this.subscriptions.set(userId, subscription);

        this.addNotificationHistory({
            timestamp: new Date(),
            type: 'preference_updated',
            message: `${setting}: ${enabled ? 'enabled' : 'disabled'}`,
            success: true,
            userId
        });

        console.log(`✅ Updated ${setting} to ${enabled} for user ${userId}`);
    }

    private async sendMarketOpenNotifications(): Promise<void> {
        console.log('🌅 Sending market open notifications...');
        
        const enabledSubscriptions = Array.from(this.subscriptions.values())
            .filter(sub => sub.preferences.marketOpen);

        const message = `🌅 **Market Open Summary**

📅 **${format(new Date(), 'EEEE, MMMM do, yyyy')}**

Good morning! Markets are now open (9:30 AM ET).

💡 I'll monitor your subscribed symbols for any breaking corporate actions today!`;

        await this.sendToSubscribers(enabledSubscriptions, message, 'market_open');
    }

    private async sendMarketCloseNotifications(): Promise<void> {
        console.log('🌇 Sending market close notifications...');
        
        const enabledSubscriptions = Array.from(this.subscriptions.values())
            .filter(sub => sub.preferences.marketClose);

        const message = `🌇 **Market Close Summary**

📅 **${format(new Date(), 'EEEE, MMMM do, yyyy')}**

Markets are now closed (4:00 PM ET).

🌙 Good evening! I'll monitor for any after-hours news.`;

        await this.sendToSubscribers(enabledSubscriptions, message, 'market_close');
    }

    private async sendWeeklyDigest(): Promise<void> {
        console.log('📊 Sending weekly digest notifications...');
        
        const enabledSubscriptions = Array.from(this.subscriptions.values())
            .filter(sub => sub.preferences.weeklyDigest);

        for (const subscription of enabledSubscriptions) {
            const message = `📊 **Weekly Corporate Actions Digest**

📅 **Week of ${format(new Date(), 'MMMM do, yyyy')}**

Hello ${subscription.userName}! Here's your weekly summary:

📈 **Your Symbols:** ${subscription.symbols.join(', ')}

📅 Looking ahead: I'll continue monitoring for new developments.`;

            try {
                await this.sendProactiveMessage(subscription, message);
                
                this.addNotificationHistory({
                    timestamp: new Date(),
                    type: 'weekly_digest',
                    message: 'Weekly digest sent',
                    symbols: subscription.symbols,
                    success: true,
                    userId: subscription.userId
                });
            } catch (error) {
                console.error(`Failed to send weekly digest to ${subscription.userId}:`, error);
                
                this.addNotificationHistory({
                    timestamp: new Date(),
                    type: 'weekly_digest',
                    message: 'Weekly digest failed',
                    symbols: subscription.symbols,
                    success: false,
                    userId: subscription.userId
                });
            }
        }
    }    private async sendProactiveMessage(subscription: UserSubscription, message: string): Promise<void> {
        try {
            console.log(`📤 Sending proactive notification to ${subscription.userName}...`);
            
            // Create a notification adaptive card
            const notificationCard = {
                $schema: 'http://adaptivecards.io/schemas/adaptive-card.json',
                type: 'AdaptiveCard',
                version: '1.3',
                body: [
                    {
                        type: 'TextBlock',
                        text: '🔔 Proactive Notification',
                        weight: 'Bolder',
                        size: 'Medium',
                        color: 'Accent'
                    },
                    {
                        type: 'TextBlock',
                        text: message,
                        wrap: true,
                        spacing: 'Medium'
                    },
                    {
                        type: 'TextBlock',
                        text: `📅 ${format(new Date(), 'PPpp')} | 👤 ${subscription.userName}`,
                        size: 'Small',
                        color: 'Default',
                        isSubtle: true
                    }
                ],
                actions: [
                    {
                        type: 'Action.Submit',
                        title: '✅ Acknowledge',
                        data: { action: 'acknowledge_notification' }
                    },
                    {
                        type: 'Action.Submit',
                        title: '⚙️ Settings',
                        data: { action: 'viewSettings' }
                    },
                    {
                        type: 'Action.Submit',
                        title: '📊 View Events',
                        data: { action: 'viewEvents' }
                    }
                ]
            };

            // Store the notification card for retrieval by the main app
            // This approach works better with the Teams AI library architecture
            this.pendingNotifications = this.pendingNotifications || [];
            this.pendingNotifications.push({
                userId: subscription.userId,
                userName: subscription.userName,
                card: notificationCard,
                message: message,
                timestamp: new Date()
            });
            
            // Log detailed notification info for debugging
            console.log(`✅ Proactive notification queued for ${subscription.userName}`);
            console.log(`📋 Message preview: ${message.substring(0, 100)}...`);
            console.log(`📊 Total pending notifications: ${this.pendingNotifications.length}`);
            
            // In a real implementation, this would use Bot Framework proactive messaging:
            // const adapter = this.app.adapter;
            // const conversationReference = TurnContext.getConversationReference(subscription.activity);
            // await adapter.continueConversation(conversationReference, async (context) => {
            //     await context.sendActivity(MessageFactory.attachment(CardFactory.adaptiveCard(notificationCard)));
            // });
            
        } catch (error) {
            console.error(`❌ Failed to send proactive message to ${subscription.userId}:`, error);
            throw error;
        }
    }

    private async sendToSubscribers(
        subscriptions: UserSubscription[], 
        message: string, 
        notificationType: string
    ): Promise<void> {
        for (const subscription of subscriptions) {
            try {
                await this.sendProactiveMessage(subscription, message);
                
                this.addNotificationHistory({
                    timestamp: new Date(),
                    type: notificationType,
                    message: message.substring(0, 100) + '...',
                    success: true,
                    userId: subscription.userId
                });
            } catch (error) {
                console.error(`❌ Failed to send ${notificationType} notification to ${subscription.userId}:`, error);
                
                this.addNotificationHistory({
                    timestamp: new Date(),
                    type: notificationType,
                    message: message.substring(0, 100) + '...',
                    success: false,
                    userId: subscription.userId
                });
            }
        }
    }

    private addNotificationHistory(item: NotificationHistoryItem): void {
        this.notificationHistory.push(item);

        // Keep only last 1000 notifications to prevent memory issues
        if (this.notificationHistory.length > 1000) {
            this.notificationHistory = this.notificationHistory.slice(-500);
        }
    }

    /**
     * Check if notification service is running
     */
    get isServiceRunning(): boolean {
        return this.isRunning;
    }

    getStats(): {
        totalSubscriptions: number;
        totalNotificationsSent: number;
        successRate: number;
        uniqueSymbols: number;
    } {
        const totalNotifications = this.notificationHistory.length;
        const successfulNotifications = this.notificationHistory.filter(h => h.success).length;
        const uniqueSymbols = new Set(
            Array.from(this.subscriptions.values()).flatMap(sub => sub.symbols)
        ).size;

        return {
            totalSubscriptions: this.subscriptions.size,
            totalNotificationsSent: totalNotifications,
            successRate: totalNotifications > 0 ? (successfulNotifications / totalNotifications) * 100 : 0,
            uniqueSymbols
        };
    }

    /**
     * TEST METHODS - For development and testing purposes
     */
    
    /**
     * Manually trigger a test notification for development/testing
     */
    async testNotification(type: string, userId?: string, symbols?: string[]): Promise<void> {
        console.log(`🧪 TEST: Triggering ${type} notification...`);
          const targetSubscriptions = userId 
            ? [this.subscriptions.get(userId)].filter((sub): sub is UserSubscription => sub !== undefined)
            : Array.from(this.subscriptions.values());
        
        if (targetSubscriptions.length === 0) {
            console.log('⚠️ No subscriptions found for testing');
            return;
        }
        
        switch (type) {
            case 'breaking_news':
                await this.testBreakingNews(targetSubscriptions, symbols || ['AAPL']);
                break;
            case 'market_open':
                await this.testMarketOpen(targetSubscriptions);
                break;
            case 'market_close':
                await this.testMarketClose(targetSubscriptions);
                break;
            case 'weekly_digest':
                await this.testWeeklyDigest(targetSubscriptions);
                break;
            case 'corporate_action':
                await this.testCorporateAction(targetSubscriptions, symbols || ['MSFT']);
                break;
            default:
                console.log(`❌ Unknown test notification type: ${type}`);
        }
    }
    
    private async testBreakingNews(subscriptions: UserSubscription[], symbols: string[]): Promise<void> {
        const message = `🚨 **BREAKING: Corporate Action Alert**

📅 **${format(new Date(), 'EEEE, MMMM do, yyyy - h:mm a')}**

🔥 **${symbols.join(', ')} - Major Announcement**

A significant corporate action has been announced for your subscribed symbols!

📊 **Action Required:**
• Review the announcement details
• Check impact on your positions
• Consider implications for your portfolio

💡 Use \`/search ${symbols[0]}\` for more details or ask me: "What happened with ${symbols[0]}?"`;

        await this.sendToSubscribers(
            subscriptions.filter(sub => 
                sub.preferences.breakingNews && 
                sub.symbols.some(s => symbols.includes(s))
            ), 
            message, 
            'test_breaking_news'
        );
    }
    
    private async testMarketOpen(subscriptions: UserSubscription[]): Promise<void> {
        const message = `🌅 **TEST: Market Open Summary**

📅 **${format(new Date(), 'EEEE, MMMM do, yyyy - h:mm a')}**

Good morning! This is a test notification for market open.

🔔 **Your Active Subscriptions:**
${Array.from(this.subscriptions.values())
    .map(sub => `• ${sub.userName}: ${sub.symbols.join(', ')}`)
    .slice(0, 5)
    .join('\n')}

💡 I'm monitoring your symbols for corporate actions throughout the trading day!

🧪 **Test Mode:** This is a development test notification.`;

        await this.sendToSubscribers(
            subscriptions.filter(sub => sub.preferences.marketOpen),
            message,
            'test_market_open'
        );
    }
    
    private async testMarketClose(subscriptions: UserSubscription[]): Promise<void> {
        const message = `🌇 **TEST: Market Close Summary**

📅 **${format(new Date(), 'EEEE, MMMM do, yyyy - h:mm a')}**

Markets are closed! This is a test notification.

📊 **Today's Monitoring Summary:**
• ✅ No critical corporate actions detected
• 📈 Monitoring continues after-hours
• 🔔 You'll be notified of any breaking news

🌙 Good evening! Sweet dreams and happy trading tomorrow!

🧪 **Test Mode:** This is a development test notification.`;

        await this.sendToSubscribers(
            subscriptions.filter(sub => sub.preferences.marketClose),
            message,
            'test_market_close'
        );
    }
    
    private async testWeeklyDigest(subscriptions: UserSubscription[]): Promise<void> {
        for (const subscription of subscriptions.filter(sub => sub.preferences.weeklyDigest)) {
            const message = `📊 **TEST: Weekly Corporate Actions Digest**

📅 **Week of ${format(new Date(), 'MMMM do, yyyy')}**

Hello ${subscription.userName}! Here's your test weekly summary:

📈 **Your Symbols:** ${subscription.symbols.join(', ')}

📋 **This Week's Activity:**
• 💰 2 dividend announcements detected
• 📊 1 stock split in progress  
• 🤝 0 merger activities
• 📈 3 earnings calls scheduled

📅 **Looking Ahead:**
• Monday: AAPL earnings call
• Wednesday: MSFT ex-dividend date
• Friday: Market holiday (test)

💡 Ask me: "What's happening with [symbol]?" for detailed analysis.

🧪 **Test Mode:** This is a development test notification.`;

            await this.sendProactiveMessage(subscription, message);
            
            this.addNotificationHistory({
                timestamp: new Date(),
                type: 'test_weekly_digest',
                message: 'Test weekly digest sent',
                symbols: subscription.symbols,
                success: true,
                userId: subscription.userId
            });
        }
    }
    
    private async testCorporateAction(subscriptions: UserSubscription[], symbols: string[]): Promise<void> {
        const actionTypes = ['dividend', 'stock_split', 'merger', 'special_dividend'];
        const actionType = actionTypes[Math.floor(Math.random() * actionTypes.length)];
        
        const message = `💰 **Corporate Action Alert - ${symbols[0]}**

📅 **${format(new Date(), 'EEEE, MMMM do, yyyy - h:mm a')}**

🎯 **${actionType.replace('_', ' ').toUpperCase()} ANNOUNCEMENT**

**Company:** ${symbols[0]} Corporation
**Action:** ${actionType.replace('_', ' ')}
**Status:** Just announced
**Effective Date:** ${format(new Date(Date.now() + 14 * 24 * 60 * 60 * 1000), 'MMMM do, yyyy')}

💡 **Next Steps:**
• Review your ${symbols[0]} positions
• Check record dates and payment schedules
• Ask me for analysis: "/search ${symbols[0]} ${actionType}"

🧪 **Test Mode:** This is a simulated corporate action for testing.`;

        await this.sendToSubscribers(
            subscriptions.filter(sub => 
                sub.preferences.immediateAlerts && 
                sub.symbols.some(s => symbols.includes(s))
            ),
            message,
            'test_corporate_action'
        );
    }
    
    /**
     * Get test notification history
     */
    getTestNotificationHistory(): NotificationHistoryItem[] {
        return this.notificationHistory.filter(item => 
            item.type.startsWith('test_')
        );
    }
    
    /**
     * Clear test notification history
     */
    clearTestHistory(): void {
        this.notificationHistory = this.notificationHistory.filter(item => 
            !item.type.startsWith('test_')
        );
        console.log('🧪 Cleared test notification history');
    }
    
    /**
     * Trigger all scheduled notifications immediately for testing
     */
    async triggerAllScheduledNotifications(): Promise<void> {
        console.log('🧪 TEST: Triggering all scheduled notifications...');
        
        await this.sendMarketOpenNotifications();
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        await this.sendMarketCloseNotifications();
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        await this.sendWeeklyDigest();
        
        console.log('✅ All scheduled notifications triggered for testing');
    }

    /**
     * Get pending notifications for a user (for DevTools testing)
     */
    getPendingNotifications(userId?: string): PendingNotification[] {
        if (userId) {
            return this.pendingNotifications.filter(n => n.userId === userId);
        }
        return this.pendingNotifications;
    }

    /**
     * Clear pending notifications
     */
    clearPendingNotifications(userId?: string): void {
        if (userId) {
            this.pendingNotifications = this.pendingNotifications.filter(n => n.userId !== userId);
        } else {
            this.pendingNotifications = [];
        }
        console.log(`🧹 Cleared pending notifications${userId ? ` for user ${userId}` : ''}`);
    }

    /**
     * Get and clear the next pending notification for a user
     */
    getNextNotification(userId: string): PendingNotification | null {
        const index = this.pendingNotifications.findIndex(n => n.userId === userId);
        if (index >= 0) {
            const notification = this.pendingNotifications[index];
            this.pendingNotifications.splice(index, 1);
            return notification;
        }
        return null;
    }
}
