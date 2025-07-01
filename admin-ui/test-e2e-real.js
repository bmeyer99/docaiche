const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  
  const page = await browser.newPage();
  
  try {
    console.log('Starting REAL E2E test - no mocks!');
    
    // Navigate to the providers page
    console.log('Loading providers page...');
    await page.goto('http://localhost:4080/dashboard/providers-new', {
      waitUntil: 'networkidle2'
    });
    
    // Wait for the page to fully load
    await page.waitForSelector('h1');
    const h1Text = await page.$eval('h1', el => el.textContent);
    console.log('Page title:', h1Text);
    
    // Take initial screenshot
    await page.screenshot({ path: 'e2e-1-initial.png', fullPage: true });
    console.log('Initial screenshot saved');
    
    // Wait for provider data to load from REAL API
    await page.waitForSelector('button[role="tab"]', { timeout: 10000 });
    
    // Click on Cloud tab
    console.log('Clicking Cloud tab...');
    const tabs = await page.$$('button[role="tab"]');
    for (const tab of tabs) {
      const text = await page.evaluate(el => el.textContent, tab);
      if (text.includes('Cloud')) {
        await tab.click();
        console.log('Clicked Cloud tab');
        break;
      }
    }
    
    // Wait for providers to load
    await new Promise(r => setTimeout(r, 1000));
    
    // Check what's actually on the page
    const pageContent = await page.evaluate(() => document.body.innerText);
    console.log('Page content includes:', pageContent.substring(0, 500));
    
    // Take screenshot after clicking Cloud tab
    await page.screenshot({ path: 'e2e-2-cloud-tab.png', fullPage: true });
    console.log('Cloud tab screenshot saved');
    
    // Look for provider cards
    const cards = await page.$$('div[role="button"]');
    console.log(`Found ${cards.length} provider cards`);
    
    // List all provider names found
    for (const card of cards) {
      const text = await page.evaluate(el => el.textContent, card);
      console.log('Provider card found:', text);
    }
    
    // If no providers, check if there's an error message
    const noProvidersText = await page.$('text=/No.*providers.*available/i');
    if (noProvidersText) {
      console.log('WARNING: No providers available message found');
      
      // Check network tab to see what API calls were made
      page.on('response', response => {
        if (response.url().includes('/api/')) {
          console.log('API Response:', response.url(), response.status());
        }
      });
    }
    
    console.log('Test completed!');
  } catch (error) {
    console.error('Error:', error.message);
    await page.screenshot({ path: 'e2e-error.png', fullPage: true });
  } finally {
    await browser.close();
  }
})();