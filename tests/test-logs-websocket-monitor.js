const puppeteer = require('puppeteer');
const fs = require('fs');

async function monitorLogsWebSocket(url = 'http://192.168.4.199:4080/dashboard/logs', duration = 30) {
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  
  const page = await browser.newPage();
  
  // Enable request interception and CDP
  await page.setRequestInterception(true);
  const client = await page.target().createCDPSession();
  await client.send('Network.enable');
  await client.send('Runtime.enable');
  
  console.log(`\n🔍 Monitoring WebSocket on ${url} for ${duration} seconds...\n`);
  
  const wsConnections = [];
  const wsMessages = [];
  const apiCalls = [];
  const errors = [];
  const consoleLogs = [];
  
  // Track WebSocket connections
  client.on('Network.webSocketCreated', (params) => {
    console.log(`🔌 WebSocket Created: ${params.url}`);
    wsConnections.push({
      timestamp: new Date().toISOString(),
      id: params.requestId,
      url: params.url,
      status: 'created'
    });
  });
  
  client.on('Network.webSocketClosed', (params) => {
    console.log(`🔌 WebSocket Closed: ${params.requestId}`);
    const ws = wsConnections.find(w => w.id === params.requestId);
    if (ws) ws.status = 'closed';
  });
  
  client.on('Network.webSocketFrameReceived', (params) => {
    try {
      const data = JSON.parse(params.response.payloadData);
      console.log(`📥 WS Received: ${data.type}`);
      wsMessages.push({
        timestamp: new Date().toISOString(),
        requestId: params.requestId,
        type: data.type,
        data: data.data
      });
    } catch (e) {
      console.log(`📥 WS Received (raw): ${params.response.payloadData.substring(0, 100)}...`);
    }
  });
  
  client.on('Network.webSocketFrameSent', (params) => {
    console.log(`📤 WS Sent: ${params.response.payloadData}`);
  });
  
  // Track regular HTTP requests
  page.on('request', (request) => {
    const url = request.url();
    const method = request.method();
    
    // Focus on API calls
    if (url.includes('/api/')) {
      apiCalls.push({
        timestamp: new Date().toISOString(),
        method,
        url
      });
      console.log(`📡 ${method} ${url}`);
    }
    
    request.continue();
  });
  
  // Track responses
  page.on('response', (response) => {
    const status = response.status();
    const url = response.url();
    
    if (status >= 400 && url.includes('/api/')) {
      console.log(`❌ Error ${status}: ${url}`);
      errors.push({
        timestamp: new Date().toISOString(),
        status,
        url
      });
    }
  });
  
  // Enhanced console tracking for WebSocket logs
  page.on('console', (msg) => {
    const text = msg.text();
    const type = msg.type();
    
    // Capture all console logs for analysis
    consoleLogs.push({
      timestamp: new Date().toISOString(),
      type,
      text
    });
    
    // Filter for WebSocket related logs
    if (text.includes('WS') || text.includes('WebSocket') || text.includes('ws:') || text.includes('log') || text.includes('stream')) {
      console.log(`📝 Console [${type}]: ${text}`);
    } else if (type === 'error') {
      console.log(`🔴 Console Error: ${text}`);
    }
  });
  
  try {
    // Navigate to the logs page
    await page.goto(url, { 
      waitUntil: 'networkidle2',
      timeout: 30000 
    });
    
    console.log('\n✅ Logs page loaded successfully\n');
    
    // Take initial screenshot
    await page.screenshot({ 
      path: `logs-monitor-start-${Date.now()}.png`,
      fullPage: true 
    });
    
    // Wait a bit for WebSocket to potentially connect
    await new Promise(resolve => setTimeout(resolve, 5000));
    
    // Try to interact with the page to trigger WebSocket connection
    try {
      // Look for service selector and try to select a service
      await page.waitForSelector('select', { timeout: 5000 });
      const selects = await page.$$('select');
      if (selects.length > 0) {
        console.log('📌 Found service selector, attempting to select a service...');
        await selects[0].select('browser');
      }
    } catch (e) {
      console.log('ℹ️  No service selector found or already selected');
    }
    
    // Wait for the remaining duration
    const remainingTime = Math.max(0, duration - 5);
    console.log(`\n⏱️  Monitoring for ${remainingTime} more seconds...\n`);
    await new Promise(resolve => setTimeout(resolve, remainingTime * 1000));
    
    // Take final screenshot
    await page.screenshot({ 
      path: `logs-monitor-end-${Date.now()}.png`,
      fullPage: true 
    });
    
  } catch (error) {
    console.error(`\n❌ Error during monitoring: ${error.message}\n`);
    errors.push({
      timestamp: new Date().toISOString(),
      type: 'monitor_error',
      message: error.message
    });
  }
  
  // Generate detailed report
  const report = {
    url,
    duration,
    timestamp: new Date().toISOString(),
    summary: {
      wsConnections: wsConnections.length,
      wsMessages: wsMessages.length,
      apiCalls: apiCalls.length,
      errors: errors.length,
      consoleLogs: consoleLogs.length
    },
    websockets: wsConnections,
    wsMessages,
    apiCalls,
    errors,
    consoleLogs: consoleLogs.filter(log => 
      log.text.includes('WS') || 
      log.text.includes('WebSocket') || 
      log.text.includes('stream') ||
      log.type === 'error'
    )
  };
  
  // Save detailed report
  const reportFile = `logs-websocket-report-${Date.now()}.json`;
  fs.writeFileSync(reportFile, JSON.stringify(report, null, 2));
  
  // Print summary
  console.log('\n📊 WebSocket Monitoring Summary:');
  console.log(`Total WebSocket Connections: ${wsConnections.length}`);
  console.log(`WebSocket Messages: ${wsMessages.length}`);
  console.log(`API Calls: ${apiCalls.length}`);
  console.log(`Errors: ${errors.length}`);
  
  if (wsConnections.length > 0) {
    console.log('\n🔌 WebSocket Connections:');
    wsConnections.forEach(ws => {
      console.log(`  - ${ws.url} (${ws.status})`);
    });
  }
  
  if (wsMessages.length > 0) {
    console.log('\n📨 WebSocket Messages:');
    wsMessages.slice(0, 10).forEach(msg => {
      console.log(`  - ${msg.type}: ${JSON.stringify(msg.data).substring(0, 100)}...`);
    });
    if (wsMessages.length > 10) {
      console.log(`  ... and ${wsMessages.length - 10} more messages`);
    }
  }
  
  if (errors.length > 0) {
    console.log('\n🔴 Errors:');
    errors.forEach(err => {
      console.log(`  - ${err.status || err.type}: ${err.url || err.message}`);
    });
  }
  
  console.log(`\n📄 Detailed report saved to: ${reportFile}`);
  
  await browser.close();
}

// Parse command line arguments
const args = process.argv.slice(2);
const url = args[0] || 'http://192.168.4.199:4080/dashboard/logs';
const duration = parseInt(args[1]) || 30;

monitorLogsWebSocket(url, duration).catch(console.error);