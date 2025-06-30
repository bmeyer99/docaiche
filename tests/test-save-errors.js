const puppeteer = require('puppeteer');

async function testSaveErrors() {
  console.log('🔍 Testing for save errors...');
  
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
  });
  
  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 1280, height: 720 });
    
    // Listen for console errors
    page.on('console', msg => {
      if (msg.type() === 'error') {
        console.log('🚨 BROWSER ERROR:', msg.text());
      } else if (msg.text().includes('Failed to save') || msg.text().includes('error')) {
        console.log('⚠️  BROWSER LOG:', msg.text());
      }
    });
    
    // Listen for network requests
    page.on('requestfailed', request => {
      console.log('❌ NETWORK FAILED:', request.url(), request.failure().errorText);
    });
    
    page.on('response', response => {
      const url = response.url();
      if (url.includes('/api/v1/providers/') && url.includes('/config')) {
        console.log(`📡 API RESPONSE: ${response.status()} ${url}`);
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
    
    console.log('📝 Changing input field...');
    
    // Find and change the input field with more precise targeting
    const result = await page.evaluate(() => {
      const inputs = Array.from(document.querySelectorAll('input'));
      const baseUrlInput = inputs.find(input => 
        input.placeholder && input.placeholder.includes('localhost') && input.placeholder.includes('11434')
      );
      
      if (baseUrlInput) {
        console.log('Found input with placeholder:', baseUrlInput.placeholder);
        console.log('Current value:', baseUrlInput.value);
        
        // Change the value
        baseUrlInput.value = 'http://localhost:11434/debug-test';
        
        // Trigger all possible events
        const events = ['input', 'change', 'blur', 'keyup'];
        events.forEach(eventType => {
          const event = new Event(eventType, { bubbles: true });
          baseUrlInput.dispatchEvent(event);
        });
        
        console.log('New value set to:', baseUrlInput.value);
        return { success: true, newValue: baseUrlInput.value };
      }
      return { success: false, error: 'Input not found' };
    });
    
    if (result.success) {
      console.log(`✅ Input changed to: ${result.newValue}`);
      
      // Wait to see if save happens
      await new Promise(resolve => setTimeout(resolve, 10000));
      console.log('⏳ Waited 10 seconds for save...');
      
    } else {
      console.log('❌ Failed to change input:', result.error);
    }
    
  } catch (error) {
    console.error('💥 Test failed:', error.message);
  } finally {
    await browser.close();
    console.log('🔚 Browser closed');
  }
}

testSaveErrors().catch(console.error);