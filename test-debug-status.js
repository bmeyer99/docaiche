const puppeteer = require('puppeteer');

async function testDebugStatus() {
  console.log('🔍 Debugging status update issue...');
  
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
  });
  
  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 1280, height: 720 });
    
    // Monitor console logs
    page.on('console', msg => {
      console.log(`🖥️  BROWSER: ${msg.text()}`);
    });
    
    // Monitor network
    page.on('response', async response => {
      const url = response.url();
      if (url.includes('/api/v1/providers/ollama/test')) {
        console.log(`📡 TEST RESPONSE: ${response.status()}`);
        try {
          const body = await response.json();
          console.log(`📋 Response body:`, JSON.stringify(body, null, 2));
        } catch (e) {
          console.log(`⚠️  Could not parse response`);
        }
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
    
    // Set Base URL and test
    await page.evaluate(() => {
      const inputs = Array.from(document.querySelectorAll('input'));
      const baseUrlInput = inputs.find(input => 
        input.placeholder === 'http://localhost:11434/api'
      );
      
      if (baseUrlInput) {
        const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        nativeInputValueSetter.call(baseUrlInput, 'http://192.168.4.204:11434/api');
        
        const event = new Event('input', { bubbles: true });
        baseUrlInput.dispatchEvent(event);
      }
    });
    
    console.log('📝 Base URL set, clicking test...');
    
    // Click test and wait
    await page.evaluate(() => {
      const buttons = Array.from(document.querySelectorAll('button'));
      const testButton = buttons.find(button => 
        button.textContent && button.textContent.includes('Test Connection')
      );
      
      if (testButton) {
        testButton.click();
      }
    });
    
    console.log('⏳ Waiting for test to complete...');
    await new Promise(resolve => setTimeout(resolve, 8000));
    
    // Check final state
    const statusInfo = await page.evaluate(() => {
      const badge = document.querySelector('.border-amber-500, .border-green-500, .border-red-500, .border-blue-500');
      const alerts = Array.from(document.querySelectorAll('.border-green-200, .border-red-200'));
      
      return {
        badgeText: badge ? badge.textContent.trim() : 'No badge found',
        badgeClasses: badge ? badge.className : 'No badge',
        alertCount: alerts.length,
        alertTexts: alerts.map(alert => alert.textContent.trim())
      };
    });
    
    console.log('📊 Final state:', statusInfo);
    
  } catch (error) {
    console.error('💥 Test failed:', error.message);
  } finally {
    await browser.close();
    console.log('🔚 Browser closed');
  }
}

testDebugStatus().catch(console.error);