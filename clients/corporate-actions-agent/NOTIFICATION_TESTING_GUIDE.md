# 🧪 Proactive Notification Testing Guide

This guide shows you how to test the proactive notification system for the Microsoft Teams Corporate Actions Bot.

## 🚀 Quick Start Testing

### 1. Start the Bot
```powershell
cd "d:\repos\corporateactions\clients\corporate-actions-agent"
npm run dev
```

### 2. Subscribe to Symbols
In Teams, send these messages to the bot:
```
/subscribe AAPL,MSFT,GOOGL
/settings
```

### 3. Test Notifications
Use the built-in test commands:
```
/test breaking AAPL
/test market-open
/test market-close
/test weekly
/test all
```

## 📋 Detailed Testing Scenarios

### A. Individual Notification Tests

#### Breaking News Alert
```
/test breaking AAPL
```
**Expected Result:**
- ✅ Console shows "Breaking News Test Triggered"
- 🔔 Simulated proactive message for AAPL subscribers
- 📊 Test history updated

#### Market Open/Close
```
/test market-open
/test market-close
```
**Expected Result:**
- ✅ Scheduled notification simulation
- 🕘 Would normally trigger at 9:30 AM / 4:00 PM ET
- 📱 Sent to users with market notifications enabled

#### Weekly Digest
```
/test weekly
```
**Expected Result:**
- ✅ Weekly summary simulation
- 📊 Includes user's subscribed symbols
- 🗓️ Would normally trigger Sunday 8:00 AM ET

#### Corporate Action Alert
```
/test corporate MSFT
```
**Expected Result:**
- 💰 Simulated dividend/split/merger announcement
- 🎯 Targeted to MSFT subscribers only
- ⚡ Immediate alert simulation

### B. Comprehensive Testing
```
/test all
```
**What it does:**
- 🔄 Triggers all notification types
- ⏱️ Runs them in sequence with delays
- 📊 Generates complete test history

### C. System Status Testing
```
/test subscription
/test history
/status
```
**Shows:**
- 📈 Current subscription statistics
- 📋 Notification history
- ✅ Service health status
- 🔧 System configuration

## 🔧 Development Testing

### Manual Testing with Node.js
```javascript
// Run the test script
node test-notifications.js

// Or use individual functions
const { testSubscription, testStatus } = require('./test-notifications.js');
testSubscription(['AAPL', 'MSFT']);
```

### Programmatic Testing
```typescript
// In your development environment
await notificationService.testNotification('breaking_news', userId, ['AAPL']);
await notificationService.triggerAllScheduledNotifications();
const stats = notificationService.getStats();
```

## ⏰ Real-World Scheduled Testing

### Production Schedule
- **Market Open**: 9:30 AM ET (Monday-Friday)
- **Market Close**: 4:00 PM ET (Monday-Friday)  
- **Weekly Digest**: 8:00 AM ET (Sunday)

### Manual Schedule Trigger
```
/test all
```
This simulates all scheduled notifications immediately.

## 🎯 Testing Real Proactive Messages

### Step 1: Enable Real Messaging
Currently, the `sendProactiveMessage` method is stubbed for safety. To test real proactive messages:

1. **Update NotificationService** (in production only):
```typescript
private async sendProactiveMessage(subscription: UserSubscription, message: string): Promise<void> {
    try {
        // Real Teams Bot Framework proactive messaging
        const adapter = this.app.adapter;
        const conversationReference = {
            user: { id: subscription.userId },
            conversation: { id: subscription.conversationId },
            serviceUrl: subscription.serviceUrl
        };
        
        await adapter.continueConversation(conversationReference, async (context) => {
            await context.sendActivity(message);
        });
        
        console.log(`✅ Proactive message sent to ${subscription.userName}`);
    } catch (error) {
        console.error(`❌ Failed to send proactive message:`, error);
        throw error;
    }
}
```

### Step 2: Test with Real Users
1. Deploy bot to Teams
2. Have users subscribe: `/subscribe AAPL`
3. Trigger test: `/test breaking AAPL`
4. Verify users receive actual proactive messages

## 📊 Monitoring & Validation

### Console Logs to Watch
```
✅ Added subscription for User (user-123) to symbols: AAPL,MSFT
🧪 TEST: Triggering breaking_news notification...
📤 Would send to Test User: 🚨 BREAKING: Corporate Action Alert...
✅ All scheduled notifications triggered for testing
```

### Status Commands
```
/status          # Overall system health
/test history    # Test notification history  
/test clear      # Clear test history
/settings        # User subscription details
```

### Statistics Monitoring
```
/test subscription
```
Shows:
- Total active subscriptions
- Notifications sent (test + real)
- Success rate percentage
- Unique symbols being tracked

## 🚨 Common Issues & Solutions

### Issue: "No subscription found"
**Solution:**
```
/subscribe AAPL
/test breaking AAPL
```

### Issue: Test notifications not appearing
**Solution:**
1. Check console logs for errors
2. Verify bot is running: `npm run dev`
3. Check subscription exists: `/settings`

### Issue: Scheduled notifications not working
**Solution:**
1. Verify service is running: `/status`
2. Check timezone configuration (ET/UTC)
3. Test manually: `/test all`

## 🎯 Best Practices

### For Development
1. **Always test with subscriptions first**
2. **Use `/test` commands for safe testing**
3. **Monitor console logs for detailed feedback**
4. **Clear test history regularly**: `/test clear`

### For Production
1. **Test with staging environment first**
2. **Start with limited user group**
3. **Monitor Azure Application Insights**
4. **Have rollback plan for notification failures**

### For Users
1. **Subscribe to relevant symbols only**
2. **Adjust notification preferences**: `/toggle`
3. **Check status regularly**: `/status`
4. **Report issues via feedback commands**

## 📈 Testing Checklist

- [ ] Bot starts successfully
- [ ] User can subscribe to symbols
- [ ] Test commands work (`/test breaking AAPL`)
- [ ] Status shows correct subscription count
- [ ] Console logs show notification attempts
- [ ] Test history tracks all tests
- [ ] Settings display correctly
- [ ] Toggle commands work
- [ ] Error handling works (invalid symbols)
- [ ] Unsubscribe works properly

## 🔮 Advanced Testing

### Load Testing
```javascript
// Test with multiple users
for (let i = 0; i < 10; i++) {
    await testSubscription([`USER${i}`, 'AAPL', 'MSFT']);
}
await triggerTestNotification('breaking_news', ['AAPL']);
```

### Integration Testing
```javascript
// Test MCP server integration
await testSearch('AAPL dividend');
await testSubscription(['AAPL']);
await triggerTestNotification('corporate_action', ['AAPL']);
```

### Performance Testing
```javascript
// Test notification system under load
const stats = notificationService.getStats();
console.log(`Processing ${stats.totalSubscriptions} subscriptions`);
await notificationService.triggerAllScheduledNotifications();
```

---

## 🎯 Ready to Test?

1. **Start the bot**: `npm run dev`
2. **Subscribe**: `/subscribe AAPL,MSFT`  
3. **Test notifications**: `/test all`
4. **Check results**: `/test history`

**Happy Testing! 🚀**
