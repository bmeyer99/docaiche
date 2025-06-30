const puppeteer = require('puppeteer');

async function testDebugSave() {
  console.log('🔍 Testing save with debug logs...');
  
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
  });
  
  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 1280, height: 720 });
    
    // Monitor console logs from the page
    page.on('console', msg => {
      const text = msg.text();
      if (text.includes('handleFieldChange') || text.includes('Debounced save') || text.includes('Saving config')) {
        console.log(`🖥️  BROWSER: ${text}`);
      }
    });
    
    // Monitor network requests
    page.on('request', request => {
      const url = request.url();
      if (url.includes('/api/v1/providers/') && request.method() === 'POST') {
        console.log(`📡 SAVE REQUEST: ${request.method()} ${url}`);
      }
    });
    
    page.on('response', response => {
      const url = response.url();
      if (url.includes('/api/v1/providers/') && response.request().method() === 'POST') {
        console.log(`📡 SAVE RESPONSE: ${response.status()} ${response.request().method()} ${url}`);
      }
    });
    
    console.log('📋 Navigate to providers page...');
    await page.goto('http://localhost:4080/dashboard/providers', { 
      waitUntil: 'networkidle2',
      timeout: 30000 
    });
    
    await page.waitForFunction(() => {
      return document.body.innerText.includes('AI Provider Configuration');
    }, { timeout: 15000 });
    
    console.log('✅ Page loaded');
    console.log('📝 Changing input field value...');
    
    // Change the input field value
    const changeResult = await page.evaluate(() => {
      const inputs = Array.from(document.querySelectorAll('input'));
      const endpointInput = inputs.find(input => 
        input.placeholder && input.placeholder.includes('localhost') && input.placeholder.includes('11434')
      );
      
      if (endpointInput) {
        console.log('Found input, changing value...');
        endpointInput.value = 'http://localhost:11434/debug-test';
        
        // Trigger React onChange event
        const event = new Event('input', { bubbles: true });
        endpointInput.dispatchEvent(event);
        
        console.log('Input changed and event dispatched');
        return { success: true, newValue: endpointInput.value };
      }
      return { success: false };
    });
    
    if (changeResult.success) {
      console.log(`✅ Input changed to: ${changeResult.newValue}`);
      
      // Wait for debounced save
      console.log('⏳ Waiting for debounced save (2 seconds)...');
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      console.log('✅ Wait completed');
      
    } else {
      console.log('❌ Failed to change input');
    }
    
  } catch (error) {
    console.error('💥 Test failed:', error.message);
  } finally {
    await browser.close();
    console.log('🔚 Browser closed');
  }
}

testDebugSave().catch(console.error);