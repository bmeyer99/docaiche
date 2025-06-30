const puppeteer = require('puppeteer');

async function debugPage() {
  console.log('🔍 Debugging providers page...');
  
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
  });
  
  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 1280, height: 720 });
    
    console.log('📋 Navigating to providers page...');
    await page.goto('http://localhost:4080/dashboard/providers', { 
      waitUntil: 'networkidle2',
      timeout: 30000 
    });
    
    console.log('✅ Page loaded, taking screenshot...');
    await page.screenshot({ 
      path: '/home/lab/docaiche/debug-providers-page.png',
      fullPage: true 
    });
    console.log('📸 Screenshot saved: debug-providers-page.png');
    
    // Get page title
    const title = await page.title();
    console.log(`📄 Page title: "${title}"`);
    
    // Get page URL
    const url = await page.url();
    console.log(`🔗 Current URL: ${url}`);
    
    // Check if we got redirected
    if (!url.includes('/providers')) {
      console.log('⚠️  Page was redirected away from providers');
    }
    
    // Get all text content
    const bodyText = await page.evaluate(() => document.body.innerText);
    console.log('📝 Page text (first 500 chars):');
    console.log(bodyText.substring(0, 500));
    
    // Look for common error messages
    const errorMessages = await page.evaluate(() => {
      const errorKeywords = ['error', 'failed', 'not found', '404', '500', 'unauthorized', 'forbidden'];
      const text = document.body.innerText.toLowerCase();
      return errorKeywords.filter(keyword => text.includes(keyword));
    });
    
    if (errorMessages.length > 0) {
      console.log(`⚠️  Found potential error indicators: ${errorMessages.join(', ')}`);
    }
    
    // Check if page has loaded content
    const hasContent = await page.evaluate(() => {
      const elements = document.querySelectorAll('*');
      return elements.length > 10; // Should have more than just basic HTML structure
    });
    
    console.log(`📊 Page has content: ${hasContent}`);
    
    // Try to find any provider-related elements with broader selectors
    const providerElements = await page.evaluate(() => {
      const selectors = [
        '[class*="provider"]',
        '[data-provider]',
        '[id*="provider"]',
        '.card',
        '[class*="config"]',
        'input',
        'form',
        'button'
      ];
      
      const results = {};
      selectors.forEach(selector => {
        const elements = document.querySelectorAll(selector);
        results[selector] = elements.length;
      });
      
      return results;
    });
    
    console.log('🔍 Element counts by selector:');
    Object.entries(providerElements).forEach(([selector, count]) => {
      console.log(`  ${selector}: ${count} elements`);
    });
    
  } catch (error) {
    console.error('💥 Debug failed:', error.message);
    
    // Take screenshot of error state
    try {
      const page = browser.pages()[0];
      if (page) {
        await page.screenshot({ 
          path: '/home/lab/docaiche/debug-error.png',
          fullPage: true 
        });
        console.log('📸 Error screenshot saved: debug-error.png');
      }
    } catch (screenshotError) {
      console.log('Failed to take error screenshot:', screenshotError.message);
    }
  } finally {
    await browser.close();
    console.log('🔚 Browser closed');
  }
}

debugPage().catch(console.error);