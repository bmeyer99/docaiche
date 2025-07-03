const puppeteer = require('puppeteer');

async function captureConsoleErrors() {
  console.log('Starting Chrome to capture console errors...');
  
  const browser = await puppeteer.launch({
    headless: false,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--disable-web-security',
      '--disable-features=VizDisplayCompositor'
    ]
  });

  const page = await browser.newPage();
  
  // Capture all console messages
  const consoleMessages = [];
  page.on('console', (msg) => {
    const timestamp = new Date().toISOString();
    const type = msg.type();
    const text = msg.text();
    
    // Only capture errors and warnings
    if (type === 'error' || type === 'warning') {
      const message = `[${timestamp}] ${type.toUpperCase()}: ${text}`;
      console.log(message);
      consoleMessages.push(message);
    }
  });

  // Capture network errors
  page.on('response', (response) => {
    if (!response.ok()) {
      const timestamp = new Date().toISOString();
      const message = `[${timestamp}] NETWORK ERROR: ${response.status()} ${response.url()}`;
      console.log(message);
      consoleMessages.push(message);
    }
  });

  // Capture JavaScript exceptions
  page.on('pageerror', (error) => {
    const timestamp = new Date().toISOString();
    const message = `[${timestamp}] PAGE ERROR: ${error.message}`;
    console.log(message);
    consoleMessages.push(message);
  });

  try {
    console.log('Navigating to monitoring page...');
    await page.goto('http://localhost:4080/dashboard/monitoring', {
      waitUntil: 'networkidle2',
      timeout: 30000
    });

    console.log('Waiting 10 seconds to capture real-time errors...');
    await page.waitForTimeout(10000);

    // Try clicking around to trigger more interactions
    console.log('Attempting to interact with charts...');
    try {
      await page.click('[data-testid="chart-container"]', { timeout: 5000 });
    } catch (e) {
      // Chart might not be ready or have different selector
    }

    await page.waitForTimeout(5000);

    console.log('\n=== SUMMARY ===');
    console.log(`Total errors/warnings captured: ${consoleMessages.length}`);
    
    if (consoleMessages.length > 0) {
      console.log('\nAll captured messages:');
      consoleMessages.forEach(msg => console.log(msg));
    } else {
      console.log('No console errors or warnings detected.');
    }

  } catch (error) {
    console.error('Error during page interaction:', error.message);
  } finally {
    await browser.close();
  }
}

// Run the capture
captureConsoleErrors().catch(console.error);