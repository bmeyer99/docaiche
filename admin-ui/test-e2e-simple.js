const puppeteer = require('puppeteer');

async function testSimple() {
  console.log('Starting simple E2E test...');
  
  let browser;
  let page;
  
  try {
    browser = await puppeteer.launch({
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
    });
    
    page = await browser.newPage();
    
    // Try to navigate to a simple page first
    console.log('Navigating to http://localhost:4080...');
    await page.goto('http://localhost:4080', { 
      waitUntil: 'domcontentloaded',
      timeout: 10000 
    });
    
    console.log('✓ Successfully loaded page');
    
    // Take screenshot
    await page.screenshot({ path: 'test-simple-screenshot.png' });
    console.log('✓ Screenshot saved');
    
    // Now try the providers page
    console.log('\nNavigating to providers page...');
    await page.goto('http://localhost:4080/dashboard/providers-new', { 
      waitUntil: 'domcontentloaded',
      timeout: 10000 
    });
    
    console.log('✓ Successfully loaded providers page');
    
    // Wait a bit for React to render
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // Get page content
    const title = await page.title();
    console.log(`Page title: ${title}`);
    
    // Try to find any h1 element
    const h1Elements = await page.$$('h1');
    console.log(`Found ${h1Elements.length} h1 elements`);
    
    if (h1Elements.length > 0) {
      const h1Text = await page.evaluate(el => el.textContent, h1Elements[0]);
      console.log(`First h1 text: ${h1Text}`);
    }
    
    // Take screenshot
    await page.screenshot({ path: 'providers-page-screenshot.png', fullPage: true });
    console.log('✓ Providers page screenshot saved');
    
  } catch (error) {
    console.error('Error:', error.message);
    if (page) {
      await page.screenshot({ path: 'error-screenshot.png', fullPage: true });
    }
  } finally {
    if (browser) {
      await browser.close();
    }
  }
}

testSimple();