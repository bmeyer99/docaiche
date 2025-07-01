const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  
  const page = await browser.newPage();
  
  try {
    console.log('Testing Providers Page...\n');
    
    // Navigate to the providers page
    console.log('1. Loading page...');
    await page.goto('http://localhost:4080/dashboard/providers-new', {
      waitUntil: 'domcontentloaded',
      timeout: 1000
    });
    
    // Take initial screenshot
    await page.screenshot({ path: 'providers-1-initial.png', fullPage: true });
    console.log('   ✓ Page loaded - screenshot saved as providers-1-initial.png');
    
    // Wait for content
    await page.waitForSelector('h1', { timeout: 1000 });
    const h1Text = await page.$eval('h1', el => el.textContent);
    console.log(`   ✓ Page title: ${h1Text}`);
    
    // Check tabs
    console.log('\n2. Checking tabs...');
    const tabs = await page.$$('button[role="tab"]');
    for (const tab of tabs) {
      const text = await page.evaluate(el => el.textContent, tab);
      console.log(`   - Found tab: ${text}`);
    }
    
    // Click Cloud tab
    console.log('\n3. Clicking Cloud tab...');
    for (const tab of tabs) {
      const text = await page.evaluate(el => el.textContent, tab);
      if (text.includes('Cloud')) {
        await tab.click();
        break;
      }
    }
    await new Promise(r => setTimeout(r, 1000));
    
    // Take screenshot after clicking cloud
    await page.screenshot({ path: 'providers-2-cloud-tab.png', fullPage: true });
    console.log('   ✓ Cloud tab clicked - screenshot saved');
    
    // Check for providers
    console.log('\n4. Checking for providers...');
    const cards = await page.$$('div[role="button"]');
    console.log(`   ✓ Found ${cards.length} provider cards`);
    
    if (cards.length === 0) {
      // Check for "No providers" message
      const pageText = await page.evaluate(() => document.body.innerText);
      if (pageText.includes('No cloud providers available')) {
        console.log('   ❌ ERROR: Page shows "No cloud providers available"');
        console.log('   This means the frontend is not properly loading data from the API');
      }
    } else {
      // List providers
      console.log('\n5. Available providers:');
      for (const card of cards) {
        const text = await page.evaluate(el => el.textContent, card);
        console.log(`   - ${text.split('\\n')[0]}`);
      }
    }
    
    // Check Enterprise tab
    console.log('\n6. Checking Enterprise tab...');
    for (const tab of tabs) {
      const text = await page.evaluate(el => el.textContent, tab);
      if (text.includes('Enterprise')) {
        await tab.click();
        break;
      }
    }
    await new Promise(r => setTimeout(r, 1000));
    
    const enterpriseCards = await page.$$('div[role="button"]');
    console.log(`   ✓ Found ${enterpriseCards.length} enterprise provider cards`);
    
    await page.screenshot({ path: 'providers-3-enterprise-tab.png', fullPage: true });
    
    console.log('\n✅ Test completed!');
    
  } catch (error) {
    console.error('\n❌ Test failed:', error.message);
    await page.screenshot({ path: 'error-screenshot.png', fullPage: true });
  } finally {
    await browser.close();
  }
})();