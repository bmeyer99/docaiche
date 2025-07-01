const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  
  const page = await browser.newPage();
  
  // Capture all console logs
  const logs = [];
  page.on('console', msg => {
    const text = msg.text();
    logs.push(text);
    console.log('Browser console:', text);
  });
  
  page.on('pageerror', error => {
    console.log('Browser error:', error.message);
  });
  
  try {
    console.log('1. Navigating to providers page...\n');
    await page.goto('http://localhost:4080/dashboard/providers-new', {
      waitUntil: 'domcontentloaded',
      timeout: 1000
    });
    
    // Wait a moment for React to render
    await new Promise(r => setTimeout(r, 500));
    
    console.log('\n2. Checking for provider data logs...');
    const providerLogs = logs.filter(log => log.includes('[ProvidersPage]'));
    if (providerLogs.length > 0) {
      console.log('Found provider data logs:');
      providerLogs.forEach(log => console.log('  ', log));
    } else {
      console.log('No provider data logs found');
    }
    
    // Try to click a provider
    console.log('\n3. Attempting to click a provider...');
    
    // Click Cloud tab first
    const tabs = await page.$$('button[role="tab"]');
    for (const tab of tabs) {
      const text = await page.evaluate(el => el.textContent, tab);
      if (text.includes('Cloud')) {
        await tab.click();
        console.log('   Clicked Cloud tab');
        break;
      }
    }
    
    // Wait for providers to load
    await new Promise(r => setTimeout(r, 500));
    
    // Try clicking a provider
    const cards = await page.$$('div[role="button"]');
    console.log(`   Found ${cards.length} provider cards`);
    
    if (cards.length > 0) {
      console.log('   Clicking first provider card...');
      await cards[0].click();
      
      // Check for click logs
      await new Promise(r => setTimeout(r, 500));
      const clickLogs = logs.filter(log => log.includes('Clicked provider'));
      if (clickLogs.length > 0) {
        console.log('\n4. Click logs found:');
        clickLogs.forEach(log => console.log('  ', log));
      } else {
        console.log('\n4. No click logs found - click handler may not be firing');
      }
    }
    
    // Take screenshot
    await page.screenshot({ path: 'console-test.png', fullPage: true });
    console.log('\n5. Screenshot saved as console-test.png');
    
  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await browser.close();
  }
})();