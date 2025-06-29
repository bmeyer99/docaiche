#!/usr/bin/env node
/**
 * Generic Page Monitor for DocAIche
 * 
 * This script uses Puppeteer to monitor any page in the DocAIche app,
 * capturing console output, network requests, errors, and page behavior over time.
 * 
 * Usage: node test-monitor-page.js <url> [duration_in_seconds]
 * Example: node test-monitor-page.js http://192.168.4.199:4080/dashboard/providers 30
 */

const puppeteer = require('puppeteer');

// ANSI color codes for better console output
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  magenta: '\x1b[35m',
  cyan: '\x1b[36m',
};

// Get command line arguments
const args = process.argv.slice(2);
const url = args[0] || 'http://192.168.4.199:4080/dashboard/providers';
const duration = parseInt(args[1]) || 30; // Default 30 seconds

if (!url) {
  console.error('Usage: node test-monitor-page.js <url> [duration_in_seconds]');
  process.exit(1);
}

// Data collection
const collectedData = {
  consoleLogs: [],
  networkRequests: [],
  networkResponses: [],
  errors: [],
  websockets: new Map(),
  performanceMetrics: [],
};

// Helper function to format timestamps
function formatTimestamp(date) {
  const now = date || new Date();
  return now.toTimeString().split(' ')[0] + '.' + now.getMilliseconds().toString().padStart(3, '0');
}

async function monitorPage(pageUrl, monitorDuration) {
  console.log(`${colors.bright}${colors.blue}=== DocAIche Page Monitor ===${colors.reset}`);
  console.log(`URL: ${pageUrl}`);
  console.log(`Duration: ${monitorDuration} seconds`);
  console.log(`Started at: ${formatTimestamp()}\n`);

  const browser = await puppeteer.launch({
    headless: false, // Set to true for CI/automated testing
    devtools: true,  // Opens DevTools automatically
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-web-security', // For cross-origin requests
    ]
  });

  const page = await browser.newPage();
  
  // Set viewport
  await page.setViewport({ width: 1920, height: 1080 });

  // Enable request interception to monitor all network activity
  await page.setRequestInterception(true);

  // 1. Monitor console output
  page.on('console', msg => {
    const logEntry = {
      timestamp: formatTimestamp(),
      type: msg.type(),
      text: msg.text(),
      location: msg.location(),
    };
    collectedData.consoleLogs.push(logEntry);

    // Color code based on type
    let color = colors.reset;
    let prefix = '[CONSOLE]';
    
    switch(msg.type()) {
      case 'error':
        color = colors.red;
        prefix = '[ERROR]';
        break;
      case 'warning':
        color = colors.yellow;
        prefix = '[WARN]';
        break;
      case 'info':
        color = colors.cyan;
        prefix = '[INFO]';
        break;
      case 'debug':
        color = colors.magenta;
        prefix = '[DEBUG]';
        break;
      default:
        color = colors.reset;
        prefix = '[LOG]';
    }

    console.log(`${color}${formatTimestamp()} ${prefix} ${msg.text()}${colors.reset}`);
    
    // If there's a stack trace in console errors, print it
    if (msg.type() === 'error' && msg.stackTrace()) {
      console.log(`${color}Stack trace:${colors.reset}`);
      msg.stackTrace().forEach(frame => {
        console.log(`  at ${frame.functionName || '<anonymous>'} (${frame.url}:${frame.lineNumber}:${frame.columnNumber})`);
      });
    }
  });

  // 2. Monitor network requests
  page.on('request', request => {
    const reqData = {
      timestamp: formatTimestamp(),
      url: request.url(),
      method: request.method(),
      resourceType: request.resourceType(),
      headers: request.headers(),
    };
    collectedData.networkRequests.push(reqData);

    // Log API requests
    if (request.url().includes('/api/')) {
      console.log(`${colors.blue}${formatTimestamp()} [API REQUEST] ${request.method()} ${request.url()}${colors.reset}`);
    }
    
    // Continue all requests
    request.continue();
  });

  // 3. Monitor network responses
  page.on('response', response => {
    const respData = {
      timestamp: formatTimestamp(),
      url: response.url(),
      status: response.status(),
      statusText: response.statusText(),
      headers: response.headers(),
    };
    collectedData.networkResponses.push(respData);

    // Log API responses with color coding
    if (response.url().includes('/api/')) {
      let statusColor = colors.green;
      if (response.status() >= 400) statusColor = colors.red;
      else if (response.status() >= 300) statusColor = colors.yellow;
      
      console.log(`${statusColor}${formatTimestamp()} [API RESPONSE] ${response.status()} ${response.url()}${colors.reset}`);
      
      // Log rate limit headers if present
      const retryAfter = response.headers()['retry-after'];
      if (retryAfter) {
        console.log(`${colors.red}  → Rate limited! Retry after: ${retryAfter}${colors.reset}`);
      }
    }
  });

  // 4. Monitor page errors
  page.on('pageerror', error => {
    const errorData = {
      timestamp: formatTimestamp(),
      message: error.message,
      stack: error.stack,
    };
    collectedData.errors.push(errorData);
    console.log(`${colors.red}${formatTimestamp()} [PAGE ERROR] ${error.message}${colors.reset}`);
  });

  // 5. Monitor WebSocket connections (via CDP)
  const client = await page.target().createCDPSession();
  await client.send('Network.enable');
  
  client.on('Network.webSocketCreated', ({requestId, url}) => {
    console.log(`${colors.magenta}${formatTimestamp()} [WS CREATED] ${url}${colors.reset}`);
    collectedData.websockets.set(requestId, {
      url,
      created: formatTimestamp(),
      frames: []
    });
  });
  
  client.on('Network.webSocketFrameReceived', ({requestId, timestamp, response}) => {
    const ws = collectedData.websockets.get(requestId);
    if (ws) {
      ws.frames.push({
        timestamp: formatTimestamp(),
        direction: 'received',
        data: response.payloadData
      });
      console.log(`${colors.magenta}${formatTimestamp()} [WS RECEIVED] ${response.payloadData.substring(0, 100)}...${colors.reset}`);
    }
  });

  // Navigate to the page
  console.log(`\n${colors.cyan}Navigating to ${pageUrl}...${colors.reset}\n`);
  
  try {
    await page.goto(pageUrl, { 
      waitUntil: 'networkidle0',
      timeout: 30000 
    });
    console.log(`${colors.green}Page loaded successfully${colors.reset}\n`);
  } catch (error) {
    console.log(`${colors.red}Failed to load page: ${error.message}${colors.reset}\n`);
  }

  // 6. Periodically collect performance metrics
  const metricsInterval = setInterval(async () => {
    try {
      const metrics = await page.metrics();
      const performanceData = {
        timestamp: formatTimestamp(),
        metrics: metrics,
      };
      collectedData.performanceMetrics.push(performanceData);
      
      // Log key metrics
      console.log(`${colors.cyan}${formatTimestamp()} [METRICS] Heap: ${(metrics.JSHeapUsedSize / 1024 / 1024).toFixed(2)}MB, DOM Nodes: ${metrics.Nodes}, Event Listeners: ${metrics.JSEventListeners}${colors.reset}`);
    } catch (error) {
      console.error(`${colors.red}Failed to collect metrics: ${error.message}${colors.reset}`);
    }
  }, 5000); // Every 5 seconds

  // 7. Take periodic screenshots
  let screenshotCount = 0;
  const screenshotInterval = setInterval(async () => {
    try {
      const filename = `screenshot-${Date.now()}.png`;
      await page.screenshot({ 
        path: filename,
        fullPage: true 
      });
      screenshotCount++;
      console.log(`${colors.green}${formatTimestamp()} [SCREENSHOT] Saved ${filename}${colors.reset}`);
    } catch (error) {
      console.error(`${colors.red}Failed to take screenshot: ${error.message}${colors.reset}`);
    }
  }, 10000); // Every 10 seconds

  // Wait for the specified duration
  await new Promise(resolve => setTimeout(resolve, monitorDuration * 1000));

  // Clean up intervals
  clearInterval(metricsInterval);
  clearInterval(screenshotInterval);

  // Generate summary report
  console.log(`\n${colors.bright}${colors.blue}=== Monitoring Summary ===${colors.reset}`);
  console.log(`Duration: ${monitorDuration} seconds`);
  console.log(`Console logs: ${collectedData.consoleLogs.length}`);
  console.log(`  - Errors: ${collectedData.consoleLogs.filter(log => log.type === 'error').length}`);
  console.log(`  - Warnings: ${collectedData.consoleLogs.filter(log => log.type === 'warning').length}`);
  console.log(`Network requests: ${collectedData.networkRequests.length}`);
  console.log(`  - API calls: ${collectedData.networkRequests.filter(req => req.url.includes('/api/')).length}`);
  console.log(`Network responses: ${collectedData.networkResponses.length}`);
  console.log(`  - 4xx/5xx errors: ${collectedData.networkResponses.filter(resp => resp.status >= 400).length}`);
  console.log(`  - 429 errors: ${collectedData.networkResponses.filter(resp => resp.status === 429).length}`);
  console.log(`Page errors: ${collectedData.errors.length}`);
  console.log(`WebSocket connections: ${collectedData.websockets.size}`);
  console.log(`Screenshots taken: ${screenshotCount}`);

  // Show API request frequency
  const apiRequests = collectedData.networkRequests.filter(req => req.url.includes('/api/'));
  const requestCounts = {};
  apiRequests.forEach(req => {
    const endpoint = req.url.split('?')[0];
    requestCounts[endpoint] = (requestCounts[endpoint] || 0) + 1;
  });
  
  console.log(`\n${colors.bright}API Request Frequency:${colors.reset}`);
  Object.entries(requestCounts)
    .sort((a, b) => b[1] - a[1])
    .forEach(([endpoint, count]) => {
      console.log(`  ${endpoint}: ${count} requests`);
    });

  // Save detailed report
  const reportFilename = `monitor-report-${Date.now()}.json`;
  require('fs').writeFileSync(reportFilename, JSON.stringify(collectedData, null, 2));
  console.log(`\n${colors.green}Detailed report saved to: ${reportFilename}${colors.reset}`);

  await browser.close();
}

// Run the monitor
monitorPage(url, duration).catch(error => {
  console.error(`${colors.red}Monitor failed: ${error.message}${colors.reset}`);
  process.exit(1);
});