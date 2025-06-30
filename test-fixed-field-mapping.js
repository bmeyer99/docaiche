const puppeteer = require('puppeteer');

async function testFixedFieldMapping() {
  console.log('🔍 Testing fixed field mapping for Base URL...');
  
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
  });
  
  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 1280, height: 720 });
    
    // Monitor network requests
    let requestBody = null;
    page.on('request', request => {
      const url = request.url();
      if (url.includes('/api/v1/providers/ollama/test') && request.method() === 'POST') {
        requestBody = request.postData();
        console.log(`📡 TEST REQUEST: ${request.method()} ${url}`);
        console.log(`📋 REQUEST BODY: ${requestBody}`);
      }
    });
    
    page.on('response', response => {
      const url = response.url();
      if (url.includes('/api/v1/providers/ollama/test') && response.request().method() === 'POST') {
        console.log(`📡 TEST RESPONSE: ${response.status()} ${response.statusText()}`);
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
    
    console.log('📝 Set a test Base URL value...');
    
    // Set a specific test value
    const testUrl = 'http://test-server:11434/api';
    await page.evaluate((newValue) => {
      const inputs = Array.from(document.querySelectorAll('input'));
      const baseUrlInput = inputs.find(input => 
        input.placeholder === 'http://localhost:11434/api'
      );
      
      if (baseUrlInput) {
        const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        nativeInputValueSetter.call(baseUrlInput, newValue);
        
        const event = new Event('input', { bubbles: true });
        baseUrlInput.dispatchEvent(event);
        
        console.log(`Set Base URL to: ${newValue}`);
        return true;
      }
      return false;
    }, testUrl);
    
    console.log('✅ Base URL set');
    
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
    await new Promise(resolve => setTimeout(resolve, 3000));
    
    // Check what toast message appeared
    const toastMessages = await page.evaluate(() => {
      const toasts = Array.from(document.querySelectorAll('[role="status"], .toast, [data-toast]'));
      return toasts.map(toast => toast.textContent).filter(text => text && text.trim());
    });
    
    console.log('📊 Results:');
    console.log('==========');
    
    if (requestBody) {
      const parsedBody = JSON.parse(requestBody);
      console.log('✅ Request sent with body:', JSON.stringify(parsedBody, null, 2));
      
      if (parsedBody.base_url) {
        console.log('🎉 SUCCESS: base_url field correctly sent to backend');
        console.log(`   Value: ${parsedBody.base_url}`);
      } else if (parsedBody.endpoint) {
        console.log('❌ STILL BROKEN: endpoint field sent instead of base_url');
        console.log(`   Value: ${parsedBody.endpoint}`);
      } else {
        console.log('❌ PROBLEM: No base_url or endpoint field found in request');
      }
    } else {
      console.log('❌ No request captured');
    }
    
    if (toastMessages.length > 0) {
      console.log('📝 Toast messages:', toastMessages);
    } else {
      console.log('📝 No toast messages found');
    }
    
  } catch (error) {
    console.error('💥 Test failed:', error.message);
  } finally {
    await browser.close();
    console.log('🔚 Browser closed');
  }
}

testFixedFieldMapping().catch(console.error);