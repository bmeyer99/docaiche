# DocAIche Page Monitoring Guide

This guide explains how to use the Puppeteer-based monitoring tool to observe and debug pages in the DocAIche application over time.

## Overview

The monitoring tool uses Puppeteer to:
- Capture all console output (logs, warnings, errors)
- Track all network requests and responses
- Monitor API call patterns and rate limiting
- Capture WebSocket connections
- Take periodic screenshots
- Collect performance metrics
- Generate detailed reports

## Installation

First, install the required dependencies:

```bash
cd /home/lab/docaiche/test-scripts
npm install
```

## Usage

### Quick Start

Monitor the AI Providers page for 30 seconds:
```bash
./monitor-page.sh
```

### Custom Monitoring

Monitor a specific page for a custom duration:
```bash
# Monitor analytics page for 60 seconds
./monitor-page.sh -u http://192.168.4.199:4080/dashboard/analytics -d 60

# Monitor search page for 2 minutes
./monitor-page.sh --url http://192.168.4.199:4080/dashboard/search --duration 120
```

### Direct Node.js Usage

You can also run the monitor directly with Node.js:
```bash
node test-monitor-page.js <url> [duration_in_seconds]
```

## What Gets Monitored

### 1. Console Output
- All console.log, console.error, console.warn messages
- Stack traces for errors
- Color-coded output for easy reading

### 2. Network Activity
- All HTTP requests and responses
- API endpoint usage patterns
- Response status codes
- Rate limiting (429) errors
- Retry-After headers

### 3. WebSocket Connections
- Connection establishment
- Message flow
- Connection closures

### 4. Performance Metrics
- JavaScript heap usage
- DOM node count
- Event listener count
- Collected every 5 seconds

### 5. Visual State
- Screenshots taken every 10 seconds
- Full page captures

## Output Files

All monitoring data is saved to the `monitor-reports/` directory:

- **monitor-YYYYMMDD-HHMMSS.log** - Console output from the monitoring session
- **monitor-report-{timestamp}.json** - Detailed JSON report with all collected data
- **screenshot-{timestamp}.png** - Page screenshots

## Interpreting Results

### API Request Frequency
The summary shows which API endpoints were called most frequently:
```
API Request Frequency:
  http://192.168.4.199:4080/api/v1/providers: 45 requests
  http://192.168.4.199:4080/api/v1/health: 12 requests
```

### Error Patterns
Look for:
- Console errors (red in output)
- 4xx/5xx HTTP responses
- Rate limiting (429) errors
- WebSocket disconnections

### Performance Issues
Monitor for:
- Increasing heap usage
- Growing DOM node count
- Excessive event listeners

## Common Issues to Watch For

### 1. Infinite API Retries
```
[API REQUEST] GET http://192.168.4.199:4080/api/v1/providers
[API RESPONSE] 429 http://192.168.4.199:4080/api/v1/providers
  → Rate limited! Retry after: 60
```

### 2. Console Errors
```
[ERROR] TypeError: Cannot read property 'data' of undefined
Stack trace:
  at fetchProviders (http://192.168.4.199:4080/_next/static/chunks/pages/dashboard/providers.js:123:45)
```

### 3. Memory Leaks
Watch for continuously increasing heap usage in the metrics.

## Troubleshooting

### Chrome Not Found
If you get a Chrome executable error, install Chrome:
```bash
# For Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y chromium-browser

# For macOS
brew install --cask google-chrome
```

### Permission Errors
Make sure the script is executable:
```bash
chmod +x monitor-page.sh
```

## Advanced Usage

### Headless Mode
Edit `test-monitor-page.js` and change:
```javascript
headless: false  // Change to true for headless mode
```

### Custom Wait Conditions
Modify the page.goto options:
```javascript
await page.goto(pageUrl, { 
  waitUntil: 'networkidle0',  // or 'load', 'domcontentloaded', 'networkidle2'
  timeout: 30000 
});
```

### Additional Monitoring
Add custom monitoring logic to `test-monitor-page.js`:
```javascript
// Monitor specific elements
await page.waitForSelector('.provider-card', { timeout: 5000 });

// Execute custom JavaScript
const providerCount = await page.evaluate(() => {
  return document.querySelectorAll('.provider-card').length;
});
```

## Example Use Cases

### 1. Debug Infinite Retries
```bash
./monitor-page.sh -u http://192.168.4.199:4080/dashboard/providers -d 60
```
Look for repeated API calls and 429 responses.

### 2. Monitor WebSocket Connections
```bash
./monitor-page.sh -u http://192.168.4.199:4080/dashboard/analytics -d 120
```
Watch for WebSocket creation and message flow.

### 3. Performance Testing
```bash
./monitor-page.sh -u http://192.168.4.199:4080/dashboard/search -d 300
```
Monitor heap usage and DOM nodes over 5 minutes.

## Tips

1. **Start with short durations** (30-60 seconds) to quickly identify issues
2. **Use longer durations** (2-5 minutes) to observe patterns over time
3. **Check the JSON report** for detailed analysis of collected data
4. **Compare screenshots** to see visual changes over time
5. **Monitor during different loads** to understand performance characteristics