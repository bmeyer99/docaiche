const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  
  const page = await browser.newPage();
  
  // Enable console logging
  page.on('console', msg => console.log('Browser console:', msg.text()));
  
  try {
    console.log('1. Navigating to providers page...');
    await page.goto('http://localhost:4080/dashboard/providers-new', {
      waitUntil: 'domcontentloaded',
      timeout: 1000
    });
    
    // Wait for provider cards
    await page.waitForSelector('div[role="button"]', { timeout: 1000 });
    
    // Click on Cloud tab
    const tabs = await page.$$('button[role="tab"]');
    for (const tab of tabs) {
      const text = await page.evaluate(el => el.textContent, tab);
      if (text.includes('Cloud')) {
        await tab.click();
        break;
      }
    }
    
    // Get all provider cards
    const cards = await page.$$('div[role="button"]');
    console.log(`2. Found ${cards.length} provider cards`);
    
    // Try clicking the first provider
    if (cards.length > 0) {
      console.log('3. Clicking on first provider...');
      await cards[0].click();
      
      // Wait a moment
      await new Promise(r => setTimeout(r, 500));
      
      // Check if configuration panel appeared
      const configPanel = await page.$('h3');
      if (configPanel) {
        const text = await page.evaluate(el => el.textContent, configPanel);
        console.log(`4. Configuration panel title: ${text}`);
      } else {
        console.log('4. No configuration panel found');
      }
      
      // Take screenshot
      await page.screenshot({ path: 'after-click.png', fullPage: true });
      console.log('5. Screenshot saved as after-click.png');
    }
    
  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await browser.close();
  }
})();