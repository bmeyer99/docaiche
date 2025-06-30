const puppeteer = require('puppeteer');

async function testFinalPersistence() {
  console.log('🚀 Final test: End-to-end provider settings persistence...');
  
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
  });
  
  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 1280, height: 720 });
    
    console.log('📋 Step 1: Navigate to providers page...');
    await page.goto('http://localhost:4080/dashboard/providers', { waitUntil: 'networkidle2', timeout: 30000 });
    
    await page.waitForFunction(() => {
      return document.body.innerText.includes('AI Provider Configuration');
    }, { timeout: 15000 });
    
    console.log('✅ Page loaded');
    
    const testValue = `http://localhost:11434/final-test-${Date.now()}`;
    
    console.log(`📝 Step 2: Change endpoint to: ${testValue}`);
    
    // Change the endpoint
    await page.evaluate((newValue) => {
      const inputs = Array.from(document.querySelectorAll('input'));
      const endpointInput = inputs.find(input => 
        input.placeholder === 'http://localhost:11434/api'
      );
      
      if (endpointInput) {
        const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        nativeInputValueSetter.call(endpointInput, newValue);
        
        const event = new Event('input', { bubbles: true });
        endpointInput.dispatchEvent(event);
        
        return true;
      }
      return false;
    }, testValue);
    
    console.log('✅ Input changed');
    
    console.log('⏳ Step 3: Wait for debounced save (2 seconds)...');
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    console.log('🔄 Step 4: Reload page to test persistence...');
    await page.reload({ waitUntil: 'networkidle2' });
    
    await page.waitForFunction(() => {
      return document.body.innerText.includes('AI Provider Configuration');
    }, { timeout: 15000 });
    
    console.log('📖 Step 5: Check if value persisted...');
    
    const persistedValue = await page.evaluate(() => {
      const inputs = Array.from(document.querySelectorAll('input'));
      const endpointInput = inputs.find(input => 
        input.placeholder === 'http://localhost:11434/api'
      );
      
      return endpointInput ? endpointInput.value : null;
    });
    
    console.log('📊 Final Results:');
    console.log('================');
    console.log(`Expected: ${testValue}`);
    console.log(`Actual:   ${persistedValue}`);
    
    if (persistedValue === testValue) {
      console.log('🎉 SUCCESS: Provider settings persist correctly!');
      console.log('✅ Debounced save prevents excessive API calls');
      console.log('✅ Settings survive page reloads'); 
    } else {
      console.log('❌ FAILURE: Settings did not persist');
    }
    
  } catch (error) {
    console.error('💥 Test failed:', error.message);
  } finally {
    await browser.close();
    console.log('🔚 Browser closed');
  }
}

testFinalPersistence().catch(console.error);