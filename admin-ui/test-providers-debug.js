const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  
  const page = await browser.newPage();
  
  // Enable console logging
  page.on('console', msg => console.log('Browser console:', msg.text()));
  page.on('pageerror', error => console.log('Browser error:', error.message));
  
  try {
    console.log('1. Navigating to providers page...');
    await page.goto('http://localhost:4080/dashboard/providers-new', {
      waitUntil: 'domcontentloaded',
      timeout: 1000
    });
    
    // Get page content immediately
    const content = await page.evaluate(() => {
      return {
        title: document.title,
        h1: document.querySelector('h1')?.textContent,
        bodyText: document.body.innerText.substring(0, 500),
        hasProviderCards: !!document.querySelector('[data-testid="provider-card"]'),
        hasTabs: !!document.querySelector('[role="tab"]'),
        tabCount: document.querySelectorAll('[role="tab"]').length
      };
    });
    
    console.log('2. Page content:');
    console.log('   Title:', content.title);
    console.log('   H1:', content.h1);
    console.log('   Has provider cards:', content.hasProviderCards);
    console.log('   Has tabs:', content.hasTabs);
    console.log('   Tab count:', content.tabCount);
    console.log('   Body preview:', content.bodyText);
    
    // Take screenshot
    await page.screenshot({ path: 'providers-debug.png', fullPage: true });
    console.log('3. Screenshot saved as providers-debug.png');
    
  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await browser.close();
  }
})();