/**
 * Page Visibility API test
 * Tests if our pause/resume functionality works correctly
 */

console.log('🔍 Testing Page Visibility API Integration');
console.log('==========================================');

// Check if Page Visibility API is supported
if (typeof document.hidden !== 'undefined') {
    console.log('✅ Page Visibility API supported');
    console.log('Current visibility state:', document.hidden ? 'hidden' : 'visible');
} else {
    console.log('❌ Page Visibility API not supported');
}

// Add visibility change listener to test
let visibilityChangeCount = 0;
const originalHandler = document.onvisibilitychange;

document.addEventListener('visibilitychange', function testVisibilityHandler() {
    visibilityChangeCount++;
    const state = document.hidden ? 'hidden' : 'visible';
    const timestamp = new Date().toLocaleTimeString();
    
    console.log(`🔄 Visibility changed #${visibilityChangeCount} at ${timestamp}: ${state}`);
    
    // Check if our analytics store responds to visibility changes
    if (window.useAnalyticsStore && typeof window.useAnalyticsStore.getState === 'function') {
        const storeState = window.useAnalyticsStore.getState();
        console.log('   Store isPaused:', storeState.isPaused);
        console.log('   Store connectionStatus:', storeState.connectionStatus);
    }
    
    // Auto-remove after 10 visibility changes to avoid spam
    if (visibilityChangeCount >= 10) {
        document.removeEventListener('visibilitychange', testVisibilityHandler);
        console.log('🛑 Test handler removed after 10 visibility changes');
    }
});

console.log('\n📋 Manual Test Instructions:');
console.log('1. Keep this console open');
console.log('2. Switch to another tab (should show "hidden")');
console.log('3. Switch back to this tab (should show "visible")'); 
console.log('4. Repeat a few times');
console.log('5. Check that WebSocket messages are paused when hidden');
console.log('6. Verify fresh data is requested when tab becomes visible');

// Test function to manually trigger visibility change simulation
window.testVisibilityChange = function() {
    console.log('🎭 Simulating visibility change...');
    
    // Dispatch a mock visibility change event
    const event = new Event('visibilitychange');
    document.dispatchEvent(event);
};

console.log('\n🎭 You can also call window.testVisibilityChange() to simulate visibility changes');