const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  
  const page = await browser.newPage();
  
  try {
    console.log('Loading providers page...');
    await page.goto('http://localhost:4080/dashboard/providers-new');
    
    // Wait for the h1 element
    await page.waitForSelector('h1');
    const h1Text = await page.$eval('h1', el => el.textContent);
    console.log('Page title:', h1Text);
    
    // Click on Cloud tab
    console.log('Clicking Cloud tab...');
    const tabs = await page.$$('button[role="tab"]');
    for (const tab of tabs) {
      const text = await page.evaluate(el => el.textContent, tab);
      if (text.includes('Cloud')) {
        await tab.click();
        break;
      }
    }
    
    // Wait a moment
    await new Promise(r => setTimeout(r, 500));
    
    // Look for provider cards
    const cards = await page.$$('div[role="button"]');
    console.log(`Found ${cards.length} provider cards`);
    
    // Click OpenAI if found
    for (const card of cards) {
      const text = await page.evaluate(el => el.textContent, card);
      if (text && text.includes('OpenAI')) {
        console.log('Clicking OpenAI card...');
        await card.click();
        break;
      }
    }
    
    // Check if configuration panel appears
    await new Promise(r => setTimeout(r, 500));
    const h3s = await page.$$('h3');
    for (const h3 of h3s) {
      const text = await page.evaluate(el => el.textContent, h3);
      console.log('Found h3:', text);
    }
    
    // Take screenshot
    await page.screenshot({ path: 'providers-test.png', fullPage: true });
    console.log('Screenshot saved as providers-test.png');
    
    console.log('Test completed successfully!');
  } catch (error) {
    console.error('Error:', error.message);
    await page.screenshot({ path: 'error.png', fullPage: true });
  } finally {
    await browser.close();
  }
})();