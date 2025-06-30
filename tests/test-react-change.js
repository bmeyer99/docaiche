const puppeteer = require('puppeteer');

async function testReactChange() {
  console.log('🔍 Testing React onChange handler...');
  
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
      console.log(`🖥️  BROWSER: ${text}`);
    });
    
    // Monitor network requests
    page.on('request', request => {
      const url = request.url();
      if (url.includes('/api/v1/providers/') && request.method() === 'POST') {
        console.log(`📡 SAVE REQUEST: ${request.method()} ${url}`);
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
    console.log('📝 Finding and changing Ollama endpoint input...');
    
    // Find the specific Ollama endpoint input and trigger React onChange
    const changeResult = await page.evaluate(() => {
      // Look for the input with the exact placeholder
      const inputs = Array.from(document.querySelectorAll('input'));
      const endpointInput = inputs.find(input => 
        input.placeholder === 'http://localhost:11434/api'
      );
      
      if (endpointInput) {
        console.log('Found Ollama endpoint input:', endpointInput.id);
        console.log('Current value:', endpointInput.value);
        
        // Create proper React event
        const newValue = 'http://localhost:11434/react-onChange-test';
        
        // Set value using React's way
        const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        nativeInputValueSetter.call(endpointInput, newValue);
        
        // Trigger React onChange
        const event = new Event('input', { bubbles: true });
        endpointInput.dispatchEvent(event);
        
        console.log('Triggered React onChange with value:', newValue);
        return { success: true, newValue, inputId: endpointInput.id };
      }
      
      console.log('Available inputs:');
      inputs.forEach((input, i) => {
        console.log(`  ${i}: placeholder="${input.placeholder}", id="${input.id}"`);
      });
      
      return { success: false };
    });
    
    if (changeResult.success) {
      console.log(`✅ React onChange triggered for ${changeResult.inputId}: ${changeResult.newValue}`);
      
      // Wait for debounced save
      console.log('⏳ Waiting 2 seconds for debounced save...');
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      console.log('✅ Wait completed');
      
    } else {
      console.log('❌ Failed to find Ollama endpoint input');
    }
    
  } catch (error) {
    console.error('💥 Test failed:', error.message);
  } finally {
    await browser.close();
    console.log('🔚 Browser closed');
  }
}

testReactChange().catch(console.error);