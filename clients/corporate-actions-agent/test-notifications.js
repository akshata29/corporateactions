/**
 * Test script for Proactive Notification System
 * Usage: node test-notifications.js
 */

const axios = require('axios');

// Mock Teams conversation data
const mockUser = {
    userId: 'test-user-123',
    userName: 'Test User',
    conversationId: 'test-conv-456',
    serviceUrl: 'https://smba.trafficmanager.net/teams/'
};

// Test configuration
const BOT_PORT = process.env.PORT || 3978;
const BOT_URL = `http://localhost:${BOT_PORT}`;

async function testNotificationFlow() {
    console.log('🧪 Testing Proactive Notification System\n');
    
    try {
        // Test 1: Subscribe to symbols
        console.log('1️⃣ Testing subscription...');
        await simulateTeamsMessage('/subscribe AAPL,MSFT,TSLA');
        
        // Test 2: Check subscription status
        console.log('\n2️⃣ Checking subscription status...');
        await simulateTeamsMessage('/settings');
        
        // Test 3: Test immediate notification trigger
        console.log('\n3️⃣ Testing immediate notification...');
        await triggerTestNotification('breaking_news', ['AAPL']);
        
        // Test 4: Test market open notification
        console.log('\n4️⃣ Testing market open notification...');
        await triggerTestNotification('market_open');
        
        // Test 5: Test market close notification
        console.log('\n5️⃣ Testing market close notification...');
        await triggerTestNotification('market_close');
        
        // Test 6: Test weekly digest
        console.log('\n6️⃣ Testing weekly digest...');
        await triggerTestNotification('weekly_digest');
        
        // Test 7: Check notification history
        console.log('\n7️⃣ Checking notification history...');
        await simulateTeamsMessage('/status');
        
        console.log('\n✅ All notification tests completed!');
        console.log('\n📝 Next steps:');
        console.log('• Check the Teams bot console for notification logs');
        console.log('• Verify notifications would be sent to the correct conversation');
        console.log('• Test real-time corporate action triggers');
        
    } catch (error) {
        console.error('❌ Test failed:', error.message);
    }
}

async function simulateTeamsMessage(text) {
    const payload = {
        type: 'message',
        text: text,
        from: {
            id: mockUser.userId,
            name: mockUser.userName
        },
        conversation: {
            id: mockUser.conversationId
        },
        serviceUrl: mockUser.serviceUrl,
        timestamp: new Date().toISOString()
    };
    
    try {
        console.log(`📤 Sending: "${text}"`);
        // Note: This would normally go to the Teams Bot Framework endpoint
        // For testing, we'll just log the action
        console.log(`✅ Message processed (simulated)`);
        
        // Simulate delay
        await new Promise(resolve => setTimeout(resolve, 500));
        
    } catch (error) {
        console.error(`❌ Failed to send message: ${error.message}`);
    }
}

async function triggerTestNotification(type, symbols = []) {
    console.log(`🔔 Triggering ${type} notification${symbols.length > 0 ? ` for ${symbols.join(', ')}` : ''}...`);
    
    // Simulate notification trigger
    const notificationData = {
        type,
        symbols,
        timestamp: new Date().toISOString(),
        testMode: true
    };
    
    console.log(`✅ ${type} notification triggered (simulated)`);
    
    // Simulate delay
    await new Promise(resolve => setTimeout(resolve, 300));
}

// Manual testing functions you can call individually
async function testSubscription(symbols) {
    console.log(`\n🧪 Testing subscription to: ${symbols.join(', ')}`);
    await simulateTeamsMessage(`/subscribe ${symbols.join(',')}`);
}

async function testUnsubscription(symbols) {
    console.log(`\n🧪 Testing unsubscription from: ${symbols.join(', ')}`);
    await simulateTeamsMessage(`/unsubscribe ${symbols.join(',')}`);
}

async function testSettings() {
    console.log('\n🧪 Testing settings view...');
    await simulateTeamsMessage('/settings');
}

async function testToggleSetting(setting) {
    console.log(`\n🧪 Testing toggle for: ${setting}`);
    await simulateTeamsMessage(`/toggle ${setting}`);
}

async function testStatus() {
    console.log('\n🧪 Testing status check...');
    await simulateTeamsMessage('/status');
}

// Export functions for manual testing
if (require.main === module) {
    // Run full test suite
    testNotificationFlow();
} else {
    // Export individual test functions
    module.exports = {
        testSubscription,
        testUnsubscription,
        testSettings,
        testToggleSetting,
        testStatus,
        triggerTestNotification,
        simulateTeamsMessage
    };
}

console.log(`
🧪 PROACTIVE NOTIFICATION TESTING GUIDE

1. SUBSCRIPTION TESTING:
   • Run: node test-notifications.js
   • Or manually test with Teams bot commands:
     - /subscribe AAPL,MSFT,GOOGL
     - /settings
     - /status

2. IMMEDIATE TESTING (Add to NotificationService):
   • Add testBreakingNews() method
   • Add testMarketNotifications() method
   • Add testWeeklyDigest() method

3. REAL-TIME TESTING:
   • Start the Teams bot: npm run dev
   • Subscribe to symbols: /subscribe AAPL,MSFT
   • Trigger test notifications manually
   • Check console logs for notification attempts

4. SCHEDULED TESTING:
   • Market Open: Runs at 9:30 AM ET (Mon-Fri)
   • Market Close: Runs at 4:00 PM ET (Mon-Fri)
   • Weekly Digest: Runs at 8:00 AM ET (Sunday)

5. MANUAL TRIGGER TESTING:
   • Add debug endpoints to trigger notifications
   • Test different notification preferences
   • Verify conversation targeting works

6. PRODUCTION TESTING:
   • Deploy to Teams app
   • Subscribe with real user account
   • Wait for scheduled notifications
   • Monitor Azure Application Insights logs
`);
