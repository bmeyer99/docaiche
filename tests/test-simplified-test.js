const puppeteer = require('puppeteer');

async function testSimplifiedTest() {
  console.log('🔍 Testing simplified test button functionality...');
  
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
  });
  
  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 1280, height: 720 });
    
    // Monitor network requests
    page.on('request', request => {
      const url = request.url();
      if (url.includes('/api/v1/providers/') && request.method() === 'POST') {
        console.log(`📡 API CALL: ${request.method()} ${url}`);
      }
    });
    
    page.on('response', response => {
      const url = response.url();
      if (url.includes('/api/v1/providers/') && response.request().method() === 'POST') {
        console.log(`📡 RESPONSE: ${response.status()} ${response.request().method()} ${url}`);
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
    
    console.log('📝 Change endpoint field to test current form values...');
    
    // Change the endpoint field
    await page.evaluate(() => {
      const inputs = Array.from(document.querySelectorAll('input'));
      const endpointInput = inputs.find(input => 
        input.placeholder === 'http://localhost:11434/api'
      );
      
      if (endpointInput) {
        const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        nativeInputValueSetter.call(endpointInput, 'http://localhost:11434/test-simplified');
        
        const event = new Event('input', { bubbles: true });
        endpointInput.dispatchEvent(event);
        
        return true;
      }
      return false;
    });
    
    console.log('✅ Endpoint changed to test value');
    
    console.log('🧪 Click Test Connection button...');
    
    // Click the test button
    await page.evaluate(() => {
      const buttons = Array.from(document.querySelectorAll('button'));
      const testButton = buttons.find(button => 
        button.textContent && button.textContent.includes('Test Connection')
      );
      
      if (testButton) {
        testButton.click();
        return true;
      }
      return false;
    });
    
    console.log('✅ Test Connection button clicked');
    
    // Wait for the test to complete
    console.log('⏳ Waiting for test to complete...');
    await new Promise(resolve => setTimeout(resolve, 5000));
    
    console.log('✅ Test completed');
    
  } catch (error) {
    console.error('💥 Test failed:', error.message);
  } finally {
    await browser.close();
    console.log('🔚 Browser closed');
  }
}

testSimplifiedTest().catch(console.error);