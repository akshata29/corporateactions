import { App } from '@microsoft/teams.apps';
import { DevtoolsPlugin } from '@microsoft/teams.dev';
import { MCPClientManager } from './services/mcpClientManager';
import { NotificationService } from './services/notificationService';
console.log('🔍 About to import CorporateActionsBot...'); // Add this
import { CorporateActionsBot } from './bot';
console.log('✅ CorporateActionsBot imported successfully'); // Add this

// Initialize MCP client manager
const mcpClient = new MCPClientManager();
console.log('✅ MCPClientManager created'); // Add this

// Create the Teams app with basic functionality
const app = new App({
  plugins: [new DevtoolsPlugin()],
});
console.log('✅ Teams App created'); // Add this

// Initialize notification service
const notificationService = new NotificationService(app);
console.log('✅ NotificationService created'); // Add this

// Initialize the enhanced Corporate Actions Bot
console.log('🔍 About to create CorporateActionsBot...'); // Add this
const corporateBot = new CorporateActionsBot(app, mcpClient, notificationService);
console.log('✅ CorporateActionsBot created successfully'); // Add this

console.log('🔍 About to register handlers...'); // Add this
// Register all bot handlers (this is the critical missing step!)
corporateBot.registerHandlers();
console.log('✅ Handlers registered successfully'); // Add this

// Enhanced initialization and startup
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
    console.log('   • /dashboard, /home - Interactive corporate actions dashboard');
    console.log('   • dashboard, home - Same as above (no slash needed)');
    console.log('   • /help - Show comprehensive help with inquiry management');
    console.log('   • /search [query] - AI-powered search with MCP');
    console.log('   • /events - Recent corporate actions');
    console.log('   • /subscribe [symbols] - Setup proactive notifications');
    console.log('   • /unsubscribe [symbols] - Remove notification subscriptions');
    console.log('   • /notifications settings - View and manage preferences');
    console.log('   • /status - Check system health with MCP diagnostics');
    console.log('   • Natural language queries with AI processing!');
    console.log('');
    console.log('📋 Inquiry Management Features:');
    console.log('   • 🆕 Create inquiries for corporate actions');
    console.log('   • 👁️ View all inquiries for events');
    console.log('   • ✏️ Edit your own inquiries');
    console.log('   • 🚦 Smart validation prevents duplicate open inquiries');
    console.log('   • 📊 Real-time dashboard with personalized insights');
    console.log('');
    console.log('🔔 Notification Features:');
    console.log('   • 🚨 Breaking news alerts for subscribed symbols');
    console.log('   • 📅 Market open/close summaries (9:30 AM & 4:00 PM ET)');
    console.log('   • 📊 Weekly digest notifications (Sunday mornings)');
    console.log('   • ⚡ Real-time corporate action monitoring');
    console.log('   • 🔄 Inquiry status updates and responses');
    console.log('');
    
  } catch (error) {
    console.error('❌ Failed to start application:', error);
    console.log('🔄 Starting in basic mode without MCP integration...');
    
    try {
      const port = +(process.env.PORT || 3978);
      await app.start(port);
      console.log(`📡 Corporate Actions Bot running on port ${port} (Basic Mode)`);
      console.log('⚠️ Note: Dashboard and inquiry management features may be limited in basic mode');
    } catch (fallbackError) {
      console.error('❌ Failed to start even in basic mode:', fallbackError);
      process.exit(1);
    }
  }
})();

export default app;