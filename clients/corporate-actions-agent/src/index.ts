import { App } from '@microsoft/teams.apps';
import { DevtoolsPlugin } from '@microsoft/teams.dev';
import { format } from 'date-fns';
import { MCPClientManager } from './services/mcpClientManager';
import { NotificationService } from './services/notificationService';
import { 
  createRAGSearchCard, 
  createEventsListCard, 
  createErrorCard, 
  createHelpCard,
  createStatusCard,
  createSubscriptionCard,
  createSettingsCard,
  createVisualizationCard,
  type RAGResponse,
  type CorporateActionEvent
} from './services/adaptiveCards';

// Initialize MCP client manager
const mcpClient = new MCPClientManager();

// Create the Teams app with basic functionality
const app = new App({
  plugins: [new DevtoolsPlugin()],
});

// Initialize notification service
const notificationService = new NotificationService(app);

// Enhanced message handler with corporate actions features
app.on('message', async ({ send, activity }: any) => {
  const text = activity.text?.toLowerCase().trim() || '';
  
  // Handle Adaptive Card actions
  if (activity.value && activity.value.action) {
    await handleAdaptiveCardAction(send, activity);
    return;
  }
  
  // Send typing indicator
  await send({ type: 'typing' });
  
  if (text.startsWith('/help')) {
    await handleHelpCommand(send);
  } else if (text.startsWith('/search')) {
    await handleSearchCommand(send, activity);
  } else if (text.startsWith('/events')) {
    await handleEventsCommand(send, activity);
  } else if (text.startsWith('/subscribe')) {
    await handleSubscribeCommand(send, activity);
  } else if (text.startsWith('/unsubscribe')) {
    await handleUnsubscribeCommand(send, activity);
  } else if (text.startsWith('/settings')) {
    await handleSettingsCommand(send, activity);
  } else if (text.startsWith('/toggle')) {
    await handleToggleCommand(send, activity);
  } else if (text.startsWith('/status')) {
    await handleStatusCommand(send);
  } else if (text.startsWith('/test')) {
    await handleTestCommand(send, activity);
  } else if (text.startsWith('/notifications')) {
    await handleNotificationsCommand(send, activity);
  } else if (text.startsWith('/')) {
    await send({
      type: 'message',
      text: '❓ Unknown command. Type `/help` to see available commands.'
    });
  } else {
    // Natural language processing placeholder
    await handleNaturalLanguageQuery(send, activity);
  }
});

// Handle Adaptive Card actions
async function handleAdaptiveCardAction(send: any, activity: any) {
  const action = activity.value.action;
  
  switch (action) {
    case 'viewEvents':
      await handleEventsCommand(send, { text: '/events' });
      break;
      
    case 'searchPrompt':
      await send({
        type: 'message',
        text: '🔍 **Search Corporate Actions**\n\nEnter your search query:\n\nExamples:\n• `/search AAPL dividend`\n• `/search stock splits this month`\n• `/search Tesla events`\n• "What happened with Microsoft this week?"'
      });
      break;
      
    case 'refreshEvents':
      await handleEventsCommand(send, { text: '/events' });
      break;
      
    case 'searchEvents':
      await send({
        type: 'message',
        text: '🔍 **Search for Specific Events**\n\nUse one of these commands:\n• `/search [company name]` - Search by company\n• `/search [event type]` - Search by event type (dividend, split, merger)\n• `/search [timeframe]` - Search by time (this week, last month)\n\nOr just ask me naturally: "Show me recent Apple events"'
      });
      break;
      
    case 'viewEventDetails':
      const eventId = activity.value.eventId;
      if (eventId) {
        await send({
          type: 'message',
          text: `🔍 **Event Details: ${eventId}**\n\nDetailed event information feature coming soon!\n\nFor now, try:\n• \`/search ${eventId}\`\n• Ask: "Tell me more about ${eventId}"`
        });
      }
      break;
      
    case 'refreshStatus':
      await handleStatusCommand(send);
      break;
      
    case 'testSearch':
      await handleSearchCommand(send, { text: '/search sample test query' });
      break;
      
    case 'viewSettings':
      await handleSettingsCommand(send, activity);
      break;
      
    case 'addSubscription':
      await send({
        type: 'message',
        text: '➕ **Add Symbol Subscription**\n\nUse the command:\n`/subscribe [symbols]`\n\nExamples:\n• `/subscribe AAPL`\n• `/subscribe AAPL,MSFT,GOOGL`\n• `/subscribe TSLA,NVDA`\n\nSeparate multiple symbols with commas.'
      });
      break;
      
    case 'removeSubscription':
      await send({
        type: 'message',
        text: '➖ **Remove Symbol Subscription**\n\nUse the command:\n`/unsubscribe [symbols]`\n\nExamples:\n• `/unsubscribe AAPL`\n• `/unsubscribe AAPL,MSFT`\n\nSeparate multiple symbols with commas.'
      });
      break;
      
    case 'toggleSettings':
      await send({
        type: 'message',
        text: '🔧 **Toggle Notification Settings**\n\nUse the toggle commands:\n• `/toggle marketopen` - Market open notifications\n• `/toggle marketclose` - Market close notifications\n• `/toggle breaking` - Breaking news alerts\n• `/toggle weekly` - Weekly digest\n\nExample: `/toggle marketopen`'
      });
      break;
      
    case 'retry':
      await send({
        type: 'message',
        text: '🔄 **Ready to try again!**\n\nWhat would you like to do?\n• `/search [query]` - Search for events\n• `/events` - List recent events\n• `/help` - Show all commands'
      });
      break;
      
    case 'help':
      await handleHelpCommand(send);
      break;
      
    case 'openDashboard':
      await send({
        type: 'message',
        text: '🌐 **Interactive Dashboard**\n\nFor full interactive charts with zoom, hover, filtering, and advanced visualizations, visit our web dashboard:\n\n**🔗 Dashboard URL:** http://localhost:8501\n\n**Features Available:**\n• 📊 Interactive Plotly charts\n• 🎨 Dynamic visualization generation\n• 🔍 Advanced filtering and search\n• 📈 Real-time data updates\n• 📋 Detailed event analysis\n\nOpen this URL in your browser for the complete visualization experience!'
      });
      break;

    case 'testNotifications':
      await send({
        type: 'message',
        text: '🧪 **Test Notification System**\n\nUse these commands to test proactive notifications:\n\n• `/test breaking AAPL` - Test breaking news\n• `/test market-open` - Test market open notification\n• `/test market-close` - Test market close notification\n• `/test weekly` - Test weekly digest\n• `/test all` - Test all notification types\n• `/test history` - View test history\n\n💡 Make sure you have subscriptions first: `/subscribe AAPL,MSFT`'
      });
      break;
    
    default:
      await send({
        type: 'message',
        text: `❓ Unknown action: ${action}`
      });
  }
}

// Welcome message for new members
app.on('activity', async ({ send, activity }: any) => {
  // Check if this is a member added event
  if (activity.type === 'conversationUpdate' && activity.membersAdded) {
    const welcomeText = `🏦 **Welcome to Enhanced Corporate Actions Bot!**

I'm powered by advanced MCP (Model Context Protocol) servers and can help you with:

📊 **AI-Powered Capabilities:**
• **Smart Search**: Ask complex questions about corporate actions
• **Event Analysis**: AI-powered insights and recommendations
• **Natural Language**: Just talk to me normally - I understand context!

🔔 **Proactive Notifications:**
• Breaking corporate action announcements
• Status updates on subscribed events
• Market open/close summaries

💬 **Available Commands:**
• \`/help\` - Show detailed help and capabilities
• \`/search [query]\` - AI-powered search with insights
• \`/events\` - Recent corporate actions with smart filtering
• \`/subscribe [symbols]\` - Smart notifications for symbols
• \`/status\` - Check system health and capabilities

🤖 **Just ask me naturally!**
Try: *"What are the upcoming Tesla events?"* or *"Show me dividend announcements this week"*`;

    await send({ type: 'message', text: welcomeText });
  }
});

// Command handlers
async function handleHelpCommand(send: any) {
  const helpCard = createHelpCard();
  
  await send({
    type: 'message',
    attachments: [
      {
        contentType: 'application/vnd.microsoft.card.adaptive',
        content: helpCard
      }
    ]
  });
}

async function handleSearchCommand(send: any, activity: any) {
  const query = activity.text.substring(7).trim();
  
  if (!query) {
    const errorCard = createErrorCard(
      'Please provide a search query. Example: `/search dividend announcements this week`',
      '🔍 Search Query Required'
    );
    
    await send({
      type: 'message',
      attachments: [
        {
          contentType: 'application/vnd.microsoft.card.adaptive',
          content: errorCard
        }
      ]
    });
    return;
  }

  await send({
    type: 'message',
    text: `🔍 Searching with AI insights: *${query}*`
  });

  try {
    // Use MCP client for enhanced search
    const response = await mcpClient.ragQuery(query, 5, true, []);
    
    if (response.error) {
      const errorCard = createErrorCard(
        `Search error: ${response.error}\n\nFalling back to basic search functionality...`,
        '❌ Search Error'
      );
      
      await send({
        type: 'message',
        attachments: [
          {
            contentType: 'application/vnd.microsoft.card.adaptive',
            content: errorCard
          }
        ]
      });
      return;
    }

    // Create RAG search result card
    const ragResponse: RAGResponse = {
      answer: response.answer || 'No results found',
      sources: response.sources || [],
      confidence_score: response.confidence_score || 0.0,
      query_intent: response.query_intent,
      requires_visualization: response.requires_visualization,
      note: response.note
    };

    // Use visualization card if visualization is required
    const searchCard = response.requires_visualization ? 
      createVisualizationCard(ragResponse, query) : 
      createRAGSearchCard(ragResponse, query);
    
    await send({
      type: 'message',
      attachments: [
        {
          contentType: 'application/vnd.microsoft.card.adaptive',
          content: searchCard
        }
      ]
    });

  } catch (error) {
    console.error('MCP search error:', error);
    
    const errorCard = createErrorCard(
      `MCP Integration Status: Connecting...\n\nI'm working to connect to the corporate actions servers:\n• RAG Server: ${mcpClient.getServerUrls().rag}\n• Search Server: ${mcpClient.getServerUrls().search}\n• Comments Server: ${mcpClient.getServerUrls().comments}\n\nAvailable now: Basic natural language processing and command handling!`,
      '🚧 Connection in Progress'
    );
    
    await send({
      type: 'message',
      attachments: [
        {
          contentType: 'application/vnd.microsoft.card.adaptive',
          content: errorCard
        }
      ]
    });
  }
}

async function handleEventsCommand(send: any, activity: any) {
  const params = activity.text.substring(7).trim();
  
  await send({
    type: 'message',
    text: `📊 **Fetching Recent Corporate Actions...**`
  });

  try {
    // Use MCP client to list recent events
    const response = await mcpClient.listEvents(10);

    if (response.error) {
      throw new Error(response.error);
    }

    const events: CorporateActionEvent[] = response.events || [];
    
    if (events.length === 0) {
      const errorCard = createErrorCard(
        `No recent events found${params ? ` matching "${params}"` : ''}.\n\nTry:\n• \`/events\` for all recent events\n• \`/search [company name]\` for specific companies\n• \`/subscribe [symbols]\` to get notifications when events happen`,
        '📊 No Events Found'
      );
      
      await send({
        type: 'message',
        attachments: [
          {
            contentType: 'application/vnd.microsoft.card.adaptive',
            content: errorCard
          }
        ]
      });
      return;
    }

    // Create events list card
    const title = `📊 Recent Corporate Actions${params ? ` matching "${params}"` : ''}`;
    const eventsCard = createEventsListCard(events, title);
    
    await send({
      type: 'message',
      attachments: [
        {
          contentType: 'application/vnd.microsoft.card.adaptive',
          content: eventsCard
        }
      ]
    });

  } catch (error) {
    console.error('Events fetch error:', error);
    
    // Create sample data for demonstration
    const sampleEvents: CorporateActionEvent[] = [
      {
        event_id: 'CA-2025-AAPL-001',
        company_name: 'Apple Inc',
        symbol: 'AAPL',
        event_type: 'dividend',
        description: 'Quarterly cash dividend',
        status: 'confirmed',
        announcement_date: '2025-06-10',
        ex_date: '2025-06-15',
        payment_date: '2025-06-20',
        event_details: { dividend_amount: 0.25 }
      },
      {
        event_id: 'CA-2025-TSLA-002', 
        company_name: 'Tesla Inc',
        symbol: 'TSLA',
        event_type: 'stock_split',
        description: '3-for-1 stock split',
        status: 'announced',
        announcement_date: '2025-06-08',
        ex_date: '2025-07-01',
        event_details: { split_ratio: '3:1' }
      }
    ];
    
    const eventsCard = createEventsListCard(sampleEvents, '📊 Sample Corporate Actions (Demo Mode)');
    
    await send({
      type: 'message',
      attachments: [
        {
          contentType: 'application/vnd.microsoft.card.adaptive',
          content: eventsCard
        }
      ]
    });
  }
}

async function handleSubscribeCommand(send: any, activity: any) {
  const symbols = activity.text.substring(10).trim();
  
  if (!symbols) {
    const errorCard = createErrorCard(
      'Please provide symbols to subscribe to. Example: `/subscribe AAPL,MSFT,GOOGL`',
      '🔔 Symbols Required'
    );
    
    await send({
      type: 'message',
      attachments: [
        {
          contentType: 'application/vnd.microsoft.card.adaptive',
          content: errorCard
        }
      ]
    });
    return;
  }

  const symbolList = symbols.split(',').map((s: string) => s.trim().toUpperCase()).filter((s: string) => s);
  
  try {
    // Add subscription using notification service
    await notificationService.addSubscription(
      activity.from.id,
      activity.from.name || 'User',
      symbolList,
      activity.conversation.id,
      activity.serviceUrl
    );

    const subscriptionCard = createSubscriptionCard(
      symbolList, 
      true,
      "I'll start monitoring these symbols and send you proactive notifications!"
    );

    await send({
      type: 'message',
      attachments: [
        {
          contentType: 'application/vnd.microsoft.card.adaptive',
          content: subscriptionCard
        }
      ]
    });

  } catch (error) {
    console.error('Subscription error:', error);
    
    const subscriptionCard = createSubscriptionCard(
      symbolList,
      false,
      `Failed to add subscription for: ${symbolList.join(', ')}\n\nFallback Mode: Your request has been noted, but proactive notifications are still being set up.\n\nFor now, try:\n• \`/search [symbol]\` - Search for specific company events\n• \`/events\` - See recent corporate actions\n• Ask me naturally: "What's new with [company]?"`
    );
    
    await send({
      type: 'message',
      attachments: [
        {
          contentType: 'application/vnd.microsoft.card.adaptive',
          content: subscriptionCard
        }
      ]
    });
  }
}

async function handleStatusCommand(send: any) {
  await send({ type: 'typing' });
  await send({ type: 'message', text: '🔧 Checking system health...' });

  try {
    const health = await mcpClient.getServiceHealth();
    const notificationStats = notificationService.getStats();
    
    const statusData = {
      health,
      botStatus: {
        port: process.env.PORT || 3978,
        mcpReady: mcpClient.isReady()
      },
      notificationStats: {
        isRunning: notificationService.isServiceRunning,
        totalSubscriptions: notificationStats.totalSubscriptions,
        uniqueSymbols: notificationStats.uniqueSymbols,
        totalNotificationsSent: notificationStats.totalNotificationsSent,
        successRate: notificationStats.successRate
      },
      serverUrls: mcpClient.getServerUrls()
    };

    const statusCard = createStatusCard(statusData);
    
    await send({
      type: 'message',
      attachments: [
        {
          contentType: 'application/vnd.microsoft.card.adaptive',
          content: statusCard
        }
      ]
    });

  } catch (error) {
    console.error('Status command error:', error);
    
    const errorCard = createErrorCard(
      `Basic System Status\n\n🤖 Teams Bot: ✅ Active and Ready\n🌐 Server: Running on port ${process.env.PORT || 3978}\n⏰ Uptime: Active since startup\n\n🚧 MCP Integration: Initializing...\n❓ RAG Server: Connecting\n❓ Search Server: Connecting\n❓ Comments Server: Connecting\n\nStatus: Basic functionality available, enhanced features loading...`,
      '🔧 System Status'
    );
    
    await send({
      type: 'message',
      attachments: [
        {
          contentType: 'application/vnd.microsoft.card.adaptive',
          content: errorCard
        }
      ]
    });
  }
}

async function handleUnsubscribeCommand(send: any, activity: any) {
  const symbols = activity.text.substring(12).trim();
  
  if (!symbols) {
    await send({
      type: 'message',
      text: '🔕 Please provide symbols to unsubscribe from. Example: `/unsubscribe AAPL,TSLA`'
    });
    return;
  }

  const symbolList = symbols.split(',').map((s: string) => s.trim().toUpperCase()).filter((s: string) => s);
  
  try {
    await notificationService.removeSubscription(activity.from.id, symbolList);

    await send({
      type: 'message',
      text: `✅ **Unsubscribed Successfully!**

🔕 **Removed:** ${symbolList.join(', ')}

You'll no longer receive notifications for these symbols.

💡 **Manage subscriptions:**
• \`/subscribe [symbols]\` - Add new symbols
• \`/settings\` - View current subscriptions
• \`/status\` - Check notification status`
    });

  } catch (error) {
    console.error('Unsubscribe error:', error);
    await send({
      type: 'message',
      text: `❌ **Unsubscribe Error**

${error instanceof Error ? error.message : 'Unknown error occurred'}

💡 Try \`/settings\` to see your current subscriptions.`
    });
  }
}

async function handleSettingsCommand(send: any, activity: any) {
  try {
    const settings = await notificationService.getUserSettings(activity.from.id);
    
    const settingsCard = createSettingsCard(settings);
    
    await send({
      type: 'message',
      attachments: [
        {
          contentType: 'application/vnd.microsoft.card.adaptive',
          content: settingsCard
        }
      ]
    });

  } catch (error) {
    console.error('Settings error:', error);
    
    const errorCard = createErrorCard(
      'No active subscriptions yet\n\nGet started:\n• `/subscribe AAPL,MSFT,GOOGL` - Subscribe to symbols\n• `/help` - See all available commands\n• Ask me naturally about corporate actions!',
      '⚙️ No Settings Found'
    );
    
    await send({
      type: 'message',
      attachments: [
        {
          contentType: 'application/vnd.microsoft.card.adaptive',
          content: errorCard
        }
      ]
    });
  }
}

async function handleToggleCommand(send: any, activity: any) {
  const setting = activity.text.substring(7).trim().toLowerCase();
  
  const validSettings = ['marketopen', 'marketclose', 'breaking', 'weekly'];
  
  if (!validSettings.includes(setting)) {
    await send({
      type: 'message',
      text: `❓ **Invalid Setting**

Valid options:
• \`/toggle marketopen\` - Market open notifications
• \`/toggle marketclose\` - Market close notifications  
• \`/toggle breaking\` - Breaking news alerts
• \`/toggle weekly\` - Weekly digest

💡 Use \`/settings\` to see your current preferences.`
    });
    return;
  }

  try {
    const currentSettings = await notificationService.getUserSettings(activity.from.id);
    
    // Map setting names to preference keys
    const settingMap: { [key: string]: keyof typeof currentSettings } = {
      'marketopen': 'marketOpen',
      'marketclose': 'marketClose', 
      'breaking': 'breakingNews',
      'weekly': 'weeklyDigest'
    };
    
    const preferenceKey = settingMap[setting];
    const currentValue = currentSettings[preferenceKey];
    const newValue = !currentValue;
    
    await notificationService.updateUserSettings(activity.from.id, setting, newValue);
    
    const settingNames: { [key: string]: string } = {
      'marketopen': 'Market Open Notifications',
      'marketclose': 'Market Close Notifications',
      'breaking': 'Breaking News Alerts', 
      'weekly': 'Weekly Digest'
    };
    
    await send({
      type: 'message',
      text: `✅ **Setting Updated**

${settingNames[setting]}: ${newValue ? '✅ Enabled' : '❌ Disabled'}

💡 Use \`/settings\` to see all your preferences.`
    });

  } catch (error) {
    console.error('Toggle setting error:', error);
    await send({
      type: 'message',
      text: `❌ **Setting Update Failed**

${error instanceof Error ? error.message : 'Please create a subscription first with `/subscribe [symbols]`'}

💡 Use \`/settings\` to see your current status.`
    });
  }
}

/**
 * Handle test commands for proactive notification testing
 */
async function handleTestCommand(send: any, activity: any) {
  const command = activity.text.substring(5).trim(); // Remove "/test "
  const parts = command.split(' ');
  const testType = parts[0]?.toLowerCase() || '';
  const testSymbols = parts.slice(1).map((s: string) => s.toUpperCase()).filter((s: string) => s);
  
  await send({ type: 'typing' });

  try {
    const userId = activity.from.id;
    
    // Check if user has subscriptions for most test types
    const settings = await notificationService.getUserSettings(userId);
    if (settings.subscribedSymbols.length === 0 && !['help', 'history', 'clear', 'all'].includes(testType)) {
      await send({
        type: 'message',
        text: `🧪 **Test Notification System**

⚠️ **No subscriptions found!** 

To test notifications, first subscribe to symbols:
\`/subscribe AAPL,MSFT,GOOGL\`

Then try your test command again.

📋 **Available test commands:**
• \`/test breaking [symbol]\` - Test breaking news alert
• \`/test market-open\` - Test market open notification
• \`/test market-close\` - Test market close notification  
• \`/test weekly\` - Test weekly digest
• \`/test corporate [symbol]\` - Test corporate action alert
• \`/test all\` - Test all notification types
• \`/test history\` - View test history
• \`/test clear\` - Clear test history
• \`/test help\` - Show this help`
      });
      return;
    }

    switch (testType) {
      case 'breaking':
        const symbolsForBreaking = testSymbols.length > 0 ? testSymbols : ['AAPL'];
        await notificationService.testNotification('breaking_news', userId, symbolsForBreaking);
        await send({
          type: 'message',
          text: `🧪 **Breaking News Test Triggered**

📊 **Test Type:** Breaking News Alert
🎯 **Symbols:** ${symbolsForBreaking.join(', ')}
👤 **User:** ${activity.from.name || 'Unknown'}

✅ Check console logs for notification simulation details.

💡 In production, this would send a proactive message to your Teams conversation.`
        });
        break;

      case 'market-open':
        await notificationService.testNotification('market_open', userId);
        await send({
          type: 'message',
          text: `🧪 **Market Open Test Triggered**

🌅 **Test Type:** Market Open Notification
⏰ **Normal Schedule:** 9:30 AM ET (Monday-Friday)
👤 **User:** ${activity.from.name || 'Unknown'}

✅ Check console logs for notification simulation details.

💡 This simulates the morning market open alert you'd receive.`
        });
        break;

      case 'market-close':
        await notificationService.testNotification('market_close', userId);
        await send({
          type: 'message',
          text: `🧪 **Market Close Test Triggered**

🌇 **Test Type:** Market Close Notification
⏰ **Normal Schedule:** 4:00 PM ET (Monday-Friday)
👤 **User:** ${activity.from.name || 'Unknown'}

✅ Check console logs for notification simulation details.

💡 This simulates the evening market close summary you'd receive.`
        });
        break;

      case 'weekly':
        await notificationService.testNotification('weekly_digest', userId);
        await send({
          type: 'message',
          text: `🧪 **Weekly Digest Test Triggered**

📊 **Test Type:** Weekly Digest
⏰ **Normal Schedule:** 8:00 AM ET (Sunday)
👤 **User:** ${activity.from.name || 'Unknown'}
📈 **Your Symbols:** ${settings.subscribedSymbols.join(', ')}

✅ Check console logs for notification simulation details.

💡 This simulates the weekly portfolio summary you'd receive.`
        });
        break;

      case 'corporate':
        const symbolsForCorporate = testSymbols.length > 0 ? testSymbols : ['MSFT'];
        await notificationService.testNotification('corporate_action', userId, symbolsForCorporate);
        await send({
          type: 'message',
          text: `🧪 **Corporate Action Test Triggered**

💰 **Test Type:** Corporate Action Alert
🎯 **Symbols:** ${symbolsForCorporate.join(', ')}
👤 **User:** ${activity.from.name || 'Unknown'}

✅ Check console logs for notification simulation details.

💡 This simulates alerts for dividend announcements, stock splits, mergers, etc.`
        });
        break;

      case 'all':
        await send({
          type: 'message',
          text: `🧪 **All Notifications Test Started**

🔄 Testing all notification types for ${activity.from.name || 'Unknown'}...

This will trigger:
• 🚨 Breaking News Alert
• 🌅 Market Open Notification  
• 🌇 Market Close Notification
• 📊 Weekly Digest
• 💰 Corporate Action Alert

⏱️ Please wait while tests run in sequence...`
        });

        // Run all test types in sequence with delays
        await notificationService.testNotification('breaking_news', userId, ['AAPL']);
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        await notificationService.testNotification('market_open', userId);
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        await notificationService.testNotification('market_close', userId);
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        await notificationService.testNotification('weekly_digest', userId);
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        await notificationService.testNotification('corporate_action', userId, ['MSFT']);

        await send({
          type: 'message',
          text: `✅ **All Notification Tests Completed**

🎯 **Summary:**
• ✅ Breaking News Alert tested
• ✅ Market Open Notification tested
• ✅ Market Close Notification tested  
• ✅ Weekly Digest tested
• ✅ Corporate Action Alert tested

📊 Check console logs for detailed simulation results.

💡 Use \`/test history\` to see test notification history.`
        });
        break;

      case 'history':
        const testHistory = notificationService.getTestNotificationHistory();
        if (testHistory.length === 0) {
          await send({
            type: 'message',
            text: `📋 **Test Notification History**

📭 No test notifications found.

💡 Run some tests first:
• \`/test breaking AAPL\`
• \`/test all\`
• \`/test weekly\``
          });
        } else {
          const historyText = testHistory.slice(-10).map((item, index) => {
            const time = format(item.timestamp, 'MMM do, h:mm a');
            const status = item.success ? '✅' : '❌';
            const type = item.type.replace('test_', '').replace('_', ' ').toUpperCase();
            return `${index + 1}. ${status} **${type}** - ${time}`;
          }).join('\n');

          await send({
            type: 'message',
            text: `📋 **Test Notification History** (Last 10)

${historyText}

📊 **Statistics:**
• Total Tests: ${testHistory.length}
• Success Rate: ${testHistory.filter(h => h.success).length}/${testHistory.length}

💡 Use \`/test clear\` to clear test history.`
          });
        }
        break;

      case 'clear':
        notificationService.clearTestHistory();
        await send({
          type: 'message',
          text: `🧹 **Test History Cleared**

✅ All test notification history has been cleared.

💡 Run new tests to populate history:
• \`/test all\`
• \`/test breaking AAPL\``
        });
        break;

      case 'help':
      case '':
        await send({
          type: 'message',
          text: `🧪 **Notification Testing System**

Test proactive notifications safely in development mode.

📋 **Available Commands:**

**🔥 Individual Tests:**
• \`/test breaking [symbol]\` - Breaking news alert
• \`/test market-open\` - Market open notification
• \`/test market-close\` - Market close notification
• \`/test weekly\` - Weekly portfolio digest
• \`/test corporate [symbol]\` - Corporate action alert

**🚀 Batch Testing:**
• \`/test all\` - Run all notification types

**📊 Management:**
• \`/test history\` - View test notification history
• \`/test clear\` - Clear test history

**💡 Examples:**
\`/test breaking AAPL\` - Test Apple breaking news
\`/test corporate MSFT\` - Test Microsoft corporate action
\`/test all\` - Test everything

**⚠️ Note:** These are simulated notifications for testing. In production, they would send actual proactive messages to Teams.`
        });
        break;

      default:
        await send({
          type: 'message',
          text: `❓ **Unknown Test Command**

You used: \`/test ${testType}\`

📋 **Valid test commands:**
• \`/test breaking [symbol]\`
• \`/test market-open\`
• \`/test market-close\`
• \`/test weekly\`
• \`/test corporate [symbol]\`
• \`/test all\`
• \`/test history\`
• \`/test help\`

💡 Use \`/test help\` for detailed usage guide.`
        });
    }

  } catch (error) {
    console.error('Test command error:', error);
    await send({
      type: 'message',
      text: `❌ **Test Command Failed**

${error instanceof Error ? error.message : 'Unknown error occurred'}

💡 Make sure you have subscriptions first: \`/subscribe AAPL,MSFT\`

🔧 Use \`/status\` to check system health.`
    });
  }
}

async function handleNaturalLanguageQuery(send: any, activity: any) {
  const query = activity.text.trim();
  const userName = activity.from?.name || 'User';
  
  await send({
    type: 'message',
    text: `🤖 Processing your query: *"${query}"*`
  });

  try {
    // Use MCP client for enhanced natural language processing
    const response = await mcpClient.processNaturalLanguage(query, userName);
    
    if (response.success) {
      // If it's a RAG response, use the appropriate card
      if (response.type === 'rag_answer') {
        const ragResponse: RAGResponse = {
          answer: response.answer,
          sources: response.sources || [],
          confidence_score: response.confidence || 0.0,
          query_intent: 'natural_language',
          requires_visualization: response.requires_visualization || false,
          note: 'Natural language query processed'
        };

        // Use visualization card if visualization is required
        const searchCard = response.requires_visualization ? 
          createVisualizationCard(ragResponse, query) : 
          createRAGSearchCard(ragResponse, query);
        
        await send({
          type: 'message',
          attachments: [
            {
              contentType: 'application/vnd.microsoft.card.adaptive',
              content: searchCard
            }
          ]
        });
        return;
      }

      // For other response types, create a simple response card
      let formattedResponse = `🤖 **AI Assistant Response:**\n\n${response.answer}`;

      // Add confidence indicator
      if (response.confidence > 0.8) {
        formattedResponse += `\n\n✅ **High Confidence** (${(response.confidence * 100).toFixed(0)}%)`;
      } else if (response.confidence > 0.6) {
        formattedResponse += `\n\n⚠️ **Medium Confidence** (${(response.confidence * 100).toFixed(0)}%)`;
      } else if (response.confidence > 0.3) {
        formattedResponse += `\n\n❓ **Moderate Confidence** (${(response.confidence * 100).toFixed(0)}%)`;
      }

      // Add sources for different response types
      if (response.sources && response.sources.length > 0) {
        if (response.type === 'search_results') {
          formattedResponse += '\n\n🔍 **Matching Events:**';
          response.sources.slice(0, 3).forEach((result: any, index: number) => {
            const company = result.issuer_name || result.company_name || 'Unknown';
            const eventType = (result.event_type || 'Event').replace('_', ' ');
            const status = result.status || 'Unknown';
            const emoji = getEventEmoji(result.event_type);
            
            formattedResponse += `\n${index + 1}. ${emoji} **${company}** - ${eventType} (${status})`;
          });
        } else {
          formattedResponse += '\n\n📊 **Data Sources:**';
          response.sources.slice(0, 3).forEach((source: any, index: number) => {
            const company = source.issuer_name || source.company_name || source.title || 'Unknown';
            const eventType = source.event_type || source.type || 'Document';
            formattedResponse += `\n${index + 1}. **${company}** - ${eventType}`;
          });
        }
      }

      // Add helpful commands
      formattedResponse += `\n\n💡 **Continue the conversation:**\n• Ask follow-up questions\n• \`/search [specific query]\` for detailed search\n• \`/subscribe [symbols]\` to get notifications`;

      await send({ type: 'message', text: formattedResponse });

    } else {
      // Fallback response - this will use the contextual fallbacks from MCPClientManager
      await send({ type: 'message', text: response.answer });
    }

  } catch (error) {
    console.error('Natural language processing error:', error);
    
    // Enhanced fallback with MCP integration status
    const errorCard = createErrorCard(
      `Hi ${userName}! I understand your question: "${query}"\n\nMCP Integration Status: Connecting to live data servers...\n\nI'm working to provide enhanced AI responses powered by:\n• 📊 Real-time corporate action data\n• 🧠 Advanced RAG (Retrieval-Augmented Generation)\n• 📈 Historical analysis and trends\n• 🔔 Proactive event notifications\n\nAvailable now:\n• \`/help\` - See all capabilities\n• \`/search [query]\` - Enhanced search\n• \`/status\` - Check system connectivity\n• \`/subscribe [symbols]\` - Get notifications\n\nAsk me again in a moment for live AI responses!`,
      '🤖 AI Processing'
    );
    
    await send({
      type: 'message',
      attachments: [
        {
          contentType: 'application/vnd.microsoft.card.adaptive',
          content: errorCard
        }
      ]
    });
  }
}

// Helper function for event emojis
function getEventEmoji(eventType: string): string {
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
}

// Start the application
(async () => {
  console.log('🚀 Starting Enhanced Corporate Actions Teams Bot...');
  console.log('📋 Initializing MCP integration and Teams framework...');
  
  try {
    // Initialize MCP client manager
    await mcpClient.initialize();
    console.log('✅ MCP client manager initialized');
    
    // Initialize notification service
    await notificationService.start();
    console.log('✅ Notification service started');
    
    const port = +(process.env.PORT || 3978);
    await app.start(port);
    
    console.log(`📡 Corporate Actions Bot running on port ${port}`);
    console.log('🌐 Ready to handle Teams messages with MCP integration!');
    console.log('');
    console.log('🌐 Endpoints:');
    console.log(`   • Bot Framework: http://localhost:${port}/api/messages`);
    console.log(`   • DevTools: http://localhost:${port + 1}/devtools`);
    console.log('');
    console.log('🔧 MCP Servers:');
    const urls = mcpClient.getServerUrls();
    Object.entries(urls).forEach(([name, url]) => {
      console.log(`   • ${name.toUpperCase()} Server: ${url}`);
    });
    console.log('');
    console.log('💡 Enhanced Commands Available:');
    console.log('   • /help - Show help and capabilities');
    console.log('   • /search [query] - AI-powered search with MCP');
    console.log('   • /events - Recent corporate actions');
    console.log('   • /subscribe [symbols] - Setup proactive notifications');
    console.log('   • /unsubscribe [symbols] - Remove notification subscriptions');
    console.log('   • /settings - View and manage notification preferences');
    console.log('   • /toggle [setting] - Toggle specific notification types');
    console.log('   • /status - Check system health with MCP diagnostics');
    console.log('   • Natural language queries with AI processing!');
    console.log('');
    console.log('🔔 Notification Features:');
    console.log('   • 🚨 Breaking news alerts for subscribed symbols');
    console.log('   • 📅 Market open/close summaries (9:30 AM & 4:00 PM ET)');
    console.log('   • 📊 Weekly digest notifications (Sunday mornings)');
    console.log('   • ⚡ Real-time corporate action monitoring');
    console.log('');
    
  } catch (error) {
    console.error('❌ Failed to start application:', error);
    console.log('🔄 Starting in basic mode without MCP integration...');
    
    try {
      const port = +(process.env.PORT || 3978);
      await app.start(port);
      console.log(`📡 Corporate Actions Bot running on port ${port} (Basic Mode)`);
    } catch (fallbackError) {
      console.error('❌ Failed to start even in basic mode:', fallbackError);
      process.exit(1);
    }
  }
})();

// Graceful shutdown
process.on('SIGINT', async () => {
  console.log('\n🛑 Shutting down gracefully...');
  await notificationService.stop();
  process.exit(0);
});

process.on('SIGTERM', async () => {
  console.log('\n🛑 Shutting down gracefully...');
  await notificationService.stop();
  process.exit(0);
});

/**
 * Handle notifications command - check for pending proactive notifications
 */
async function handleNotificationsCommand(send: any, activity: any) {
  const command = activity.text.substring(14).trim(); // Remove "/notifications "
  const userId = activity.from.id;
  
  await send({ type: 'typing' });

  try {
    if (command === 'check' || command === '') {
      // Get pending notifications for this user
      const pendingNotifications = notificationService.getPendingNotifications(userId);
      
      if (pendingNotifications.length === 0) {
        await send({
          type: 'message',
          text: `📬 **No Pending Notifications**

✅ You're all caught up! No pending proactive notifications.

💡 **To test notifications:**
• \`/test breaking AAPL\` - Test breaking news alert
• \`/test all\` - Test all notification types
• \`/notifications check\` - Check for pending notifications`
        });
        return;
      }

      // Show the first pending notification as an adaptive card
      const notification = notificationService.getNextNotification(userId);
      if (notification) {
        await send({
          type: 'message',
          text: `🔔 **Pending Notification** (${pendingNotifications.length} total)`
        });

        await send({
          type: 'message',
          attachments: [
            {
              contentType: 'application/vnd.microsoft.card.adaptive',
              content: notification.card
            }
          ]
        });

        // If there are more notifications, show a summary
        const remaining = notificationService.getPendingNotifications(userId).length;
        if (remaining > 0) {
          await send({
            type: 'message',
            text: `📋 **${remaining} more notifications pending**

Use \`/notifications check\` to see the next one.`
          });
        }
      }
    } else if (command === 'clear') {
      const count = notificationService.getPendingNotifications(userId).length;
      notificationService.clearPendingNotifications(userId);
      
      await send({
        type: 'message',
        text: `🧹 **Notifications Cleared**

✅ Cleared ${count} pending notifications.

💡 Use \`/test all\` to generate new test notifications.`
      });
    } else if (command === 'all') {
      // Show all pending notifications as a summary
      const pendingNotifications = notificationService.getPendingNotifications(userId);
      
      if (pendingNotifications.length === 0) {
        await send({
          type: 'message',
          text: `📭 No pending notifications to display.`
        });
        return;
      }

      const summaryText = pendingNotifications.map((notification, index) => {
        const time = format(notification.timestamp, 'h:mm a');
        const preview = notification.message.substring(0, 50) + '...';
        return `${index + 1}. **${time}** - ${preview}`;
      }).join('\n');

      await send({
        type: 'message',
        text: `📋 **All Pending Notifications** (${pendingNotifications.length})

${summaryText}

💡 Use \`/notifications check\` to view them as adaptive cards.
💡 Use \`/notifications clear\` to clear all pending notifications.`
      });
    } else {
      await send({
        type: 'message',
        text: `📬 **Notifications Command Help**

**Check for notifications:**
• \`/notifications\` or \`/notifications check\` - View next pending notification
• \`/notifications all\` - List all pending notifications
• \`/notifications clear\` - Clear all pending notifications

**Note:** This command is for checking proactive notifications that were triggered by test commands or scheduled events.

💡 Use \`/test all\` to generate test notifications first.`
      });
    }

  } catch (error) {
    console.error('Notifications command error:', error);
    await send({
      type: 'message',
      text: `❌ **Notifications Command Failed**

${error instanceof Error ? error.message : 'Unknown error occurred'}

💡 Try \`/test all\` to generate notifications first.`
    });
  }
}
