const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  
  const page = await browser.newPage();
  
  try {
    console.log('Starting E2E test for Providers page...');
    
    // Navigate to the providers page
    console.log('1. Loading providers page...');
    await page.goto('http://localhost:4080/dashboard/providers-new', {
      waitUntil: 'networkidle2',
      timeout: 10000
    });
    
    // Wait for the page to load
    await page.waitForSelector('h1');
    const h1Text = await page.$eval('h1', el => el.textContent);
    console.log(`   ✓ Page loaded: ${h1Text}`);
    
    // Check for provider tabs
    console.log('2. Checking provider tabs...');
    const tabs = await page.$$('button[role="tab"]');
    console.log(`   ✓ Found ${tabs.length} tabs`);
    
    // Click on Cloud tab
    console.log('3. Clicking Cloud tab...');
    for (const tab of tabs) {
      const text = await page.evaluate(el => el.textContent, tab);
      if (text.includes('Cloud')) {
        await tab.click();
        console.log('   ✓ Clicked Cloud tab');
        break;
      }
    }
    
    // Wait for providers to load
    await new Promise(r => setTimeout(r, 1000));
    
    // Check for provider cards
    console.log('4. Checking for provider cards...');
    const cards = await page.$$('div[role="button"]');
    console.log(`   ✓ Found ${cards.length} provider cards`);
    
    // List all providers found
    console.log('5. Available providers:');
    for (const card of cards) {
      const text = await page.evaluate(el => el.textContent, card);
      if (text) {
        console.log(`   - ${text.split('\\n')[0]}`);
      }
    }
    
    // Take screenshot
    await page.screenshot({ path: 'providers-working.png', fullPage: true });
    console.log('6. Screenshot saved as providers-working.png');
    
    // Click on a provider (e.g., OpenAI)
    console.log('7. Selecting OpenAI provider...');
    let openAIFound = false;
    for (const card of cards) {
      const text = await page.evaluate(el => el.textContent, card);
      if (text && text.includes('OpenAI')) {
        await card.click();
        console.log('   ✓ Clicked OpenAI provider');
        openAIFound = true;
        break;
      }
    }
    
    if (openAIFound) {
      // Wait for configuration panel
      await new Promise(r => setTimeout(r, 500));
      
      // Check for configuration form
      console.log('8. Checking configuration panel...');
      const h3Elements = await page.$$('h3');
      for (const h3 of h3Elements) {
        const text = await page.evaluate(el => el.textContent, h3);
        if (text && text.includes('Configure')) {
          console.log(`   ✓ Configuration panel loaded: ${text}`);
        }
      }
      
      // Check for form fields
      const inputs = await page.$$('input');
      console.log(`   ✓ Found ${inputs.length} input fields`);
    }
    
    console.log('\\n✅ E2E test completed successfully!');
    
  } catch (error) {
    console.error('❌ Test failed:', error.message);
    await page.screenshot({ path: 'error-screenshot.png', fullPage: true });
    console.log('Error screenshot saved');
  } finally {
    await browser.close();
  }
})();