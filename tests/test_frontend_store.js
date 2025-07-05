/**
 * Frontend store test script
 * This tests if our Zustand store implementation is working
 * Run this in the browser console on the analytics page
 */

// Test script for browser console
console.log('🧪 Testing Analytics Store Implementation');
console.log('=======================================');

// Check if our test function exists
if (typeof window.testAnalyticsStore === 'function') {
    console.log('✅ Test function found');
    window.testAnalyticsStore();
} else {
    console.log('❌ Test function not found');
    
    // Try to access the store directly if available
    if (window.__ZUSTAND__) {
        console.log('✅ Zustand store detected');
        console.log('Zustand stores:', Object.keys(window.__ZUSTAND__));
    } else {
        console.log('❌ No Zustand store detected');
    }
}

// Check if WebSocket manager is available
if (typeof window.AnalyticsWebSocketManager !== 'undefined') {
    console.log('✅ AnalyticsWebSocketManager available');
} else {
    console.log('❌ AnalyticsWebSocketManager not available');
}

// Check network connections
setTimeout(() => {
    const wsConnections = performance.getEntriesByType('resource')
        .filter(entry => entry.name.includes('ws://') || entry.name.includes('wss://'));
    
    if (wsConnections.length > 0) {
        console.log('✅ WebSocket connections detected:', wsConnections.length);
        wsConnections.forEach(conn => console.log('  -', conn.name));
    } else {
        console.log('❌ No WebSocket connections detected');
    }
}, 2000);

console.log('\n📋 Instructions:');
console.log('1. Navigate to http://localhost:4080/dashboard/analytics');
console.log('2. Open browser console (F12)');
console.log('3. Paste this script and run it');
console.log('4. Check if data persists when navigating away and back');
console.log('5. Use browser dev tools to see Network tab for WebSocket connections');