const puppeteer = require('puppeteer');

async function testSaveNetwork() {
  console.log('🔍 Testing save network calls...');
  
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
  });
  
  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 1280, height: 720 });
    
    // Monitor all network requests
    page.on('request', request => {
      const url = request.url();
      if (url.includes('/api/v1/providers/') && (url.includes('/config') || request.method() === 'POST')) {
        console.log(`📡 REQUEST: ${request.method()} ${url}`);
      }
    });
    
    page.on('response', response => {
      const url = response.url();
      if (url.includes('/api/v1/providers/') && (url.includes('/config') || response.request().method() === 'POST')) {
        console.log(`📡 RESPONSE: ${response.status()} ${response.request().method()} ${url}`);
      }
    });
    
    page.on('requestfailed', request => {
      const url = request.url();
      if (url.includes('/api/v1/providers/')) {
        console.log(`❌ REQUEST FAILED: ${request.method()} ${url} - ${request.failure().errorText}`);
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
    
    console.log('📝 Changing input field and watching for save calls...');
    
    // Change the input field
    const result = await page.evaluate(() => {
      const inputs = Array.from(document.querySelectorAll('input'));
      const endpointInput = inputs.find(input => 
        input.placeholder && input.placeholder.includes('localhost') && input.placeholder.includes('11434')
      );
      
      if (endpointInput) {
        console.log('Changing input from:', endpointInput.value);
        endpointInput.value = 'http://localhost:11434/save-test';
        
        // Trigger all events
        const events = ['input', 'change', 'blur'];
        events.forEach(eventType => {
          const event = new Event(eventType, { bubbles: true });
          endpointInput.dispatchEvent(event);
        });
        
        console.log('Changed input to:', endpointInput.value);
        return { success: true, newValue: endpointInput.value };
      }
      return { success: false };
    });
    
    if (result.success) {
      console.log(`✅ Input changed to: ${result.newValue}`);
      
      // Wait to see save network requests
      await new Promise(resolve => setTimeout(resolve, 10000));
      console.log('⏳ Waited 10 seconds for save network calls...');
      
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

testSaveNetwork().catch(console.error);