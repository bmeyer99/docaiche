const puppeteer = require('puppeteer');

async function testReactInput() {
  console.log('🔍 Testing React input change...');
  
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
    
    console.log('📋 Navigate to providers page...');
    await page.goto('http://localhost:4080/dashboard/providers', { 
      waitUntil: 'networkidle2',
      timeout: 30000 
    });
    
    await page.waitForFunction(() => {
      return document.body.innerText.includes('AI Provider Configuration');
    }, { timeout: 15000 });
    
    console.log('✅ Page loaded');
    
    console.log('📝 Simulating proper React input change...');
    
    // Find the input field and trigger React onChange
    const changeResult = await page.evaluate(() => {
      // Find the input
      const inputs = Array.from(document.querySelectorAll('input'));
      const endpointInput = inputs.find(input => 
        input.placeholder && input.placeholder.includes('localhost') && input.placeholder.includes('11434')
      );
      
      if (endpointInput) {
        console.log('Found input, current value:', endpointInput.value);
        
        // Create a proper React synthetic event
        const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        const newValue = 'http://localhost:11434/react-test';
        
        // Set the value using React's method
        nativeInputValueSetter.call(endpointInput, newValue);
        
        // Trigger React's onChange event
        const event = new Event('input', { bubbles: true });
        event.simulated = true;
        endpointInput.dispatchEvent(event);
        
        console.log('Triggered React input event with value:', newValue);
        return { success: true, newValue };
      }
      return { success: false };
    });
    
    if (changeResult.success) {
      console.log(`✅ React input change triggered: ${changeResult.newValue}`);
      
      // Wait to see save network requests
      await new Promise(resolve => setTimeout(resolve, 10000));
      console.log('⏳ Waited 10 seconds for save network calls...');
      
    } else {
      console.log('❌ Failed to trigger React input change');
    }
    
  } catch (error) {
    console.error('💥 Test failed:', error.message);
  } finally {
    await browser.close();
    console.log('🔚 Browser closed');
  }
}

testReactInput().catch(console.error);