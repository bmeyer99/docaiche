const puppeteer = require('puppeteer');

async function testDebouncedSave() {
  console.log('🔍 Testing debounced save functionality...');
  
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
        console.log(`📡 SAVE REQUEST: ${request.method()} ${url}`);
        console.log(`   Body: ${request.postData()}`);
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
    
    console.log('📝 Simulating keystroke changes...');
    
    // Type multiple characters to test debouncing
    const typingResult = await page.evaluate(() => {
      const inputs = Array.from(document.querySelectorAll('input'));
      const endpointInput = inputs.find(input => 
        input.placeholder && input.placeholder.includes('localhost') && input.placeholder.includes('11434')
      );
      
      if (endpointInput) {
        console.log('Found input, simulating typing...');
        
        // Clear the input
        endpointInput.value = '';
        endpointInput.dispatchEvent(new Event('input', { bubbles: true }));
        
        // Type each character with a small delay to simulate real typing
        const testUrl = 'http://localhost:11434/debounce-test';
        
        for (let i = 0; i < testUrl.length; i++) {
          setTimeout(() => {
            endpointInput.value = testUrl.substring(0, i + 1);
            endpointInput.dispatchEvent(new Event('input', { bubbles: true }));
            console.log(`Typed: "${endpointInput.value}"`);
          }, i * 100); // 100ms between each character
        }
        
        return { success: true, finalValue: testUrl };
      }
      return { success: false };
    });
    
    if (typingResult.success) {
      console.log(`✅ Simulated typing: ${typingResult.finalValue}`);
      
      // Wait for debounced save (should be 1 second after last keystroke)
      console.log('⏳ Waiting for debounced save...');
      await new Promise(resolve => setTimeout(resolve, 8000)); // Wait 8 seconds total
      
      console.log('✅ Debounce period completed');
      
    } else {
      console.log('❌ Failed to simulate typing');
    }
    
  } catch (error) {
    console.error('💥 Test failed:', error.message);
  } finally {
    await browser.close();
    console.log('🔚 Browser closed');
  }
}

testDebouncedSave().catch(console.error);