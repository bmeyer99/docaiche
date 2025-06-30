const puppeteer = require('puppeteer');

async function testStatusUpdate() {
  console.log('🔍 Testing status badge update after successful test...');
  
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
  });
  
  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 1280, height: 720 });
    
    console.log('📋 Navigate to providers page...');
    await page.goto('http://localhost:4080/dashboard/providers', { 
      waitUntil: 'networkidle2',
      timeout: 30000 
    });
    
    await page.waitForFunction(() => {
      return document.body.innerText.includes('AI Provider Configuration');
    }, { timeout: 15000 });
    
    console.log('✅ Page loaded');
    
    // Check initial status
    const initialStatus = await page.evaluate(() => {
      const badge = document.querySelector('.border-amber-500, .border-green-500, .border-red-500');
      return badge ? badge.textContent.trim() : 'No badge found';
    });
    
    console.log(`📊 Initial status: ${initialStatus}`);
    
    console.log('📝 Configure Base URL...');
    
    // Set valid Base URL
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
        
        return true;
      }
      return false;
    });
    
    console.log('✅ Base URL configured');
    
    console.log('🧪 Click Test Connection button...');
    
    // Click test button
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
    
    console.log('✅ Test button clicked');
    
    // Wait for test to complete
    console.log('⏳ Waiting for test to complete...');
    await new Promise(resolve => setTimeout(resolve, 5000));
    
    // Check status after test
    const finalStatus = await page.evaluate(() => {
      const badge = document.querySelector('.border-amber-500, .border-green-500, .border-red-500');
      return badge ? badge.textContent.trim() : 'No badge found';
    });
    
    console.log(`📊 Final status: ${finalStatus}`);
    
    // Check for success alert
    const successAlert = await page.evaluate(() => {
      const alerts = Array.from(document.querySelectorAll('.border-green-200, .bg-green-50'));
      return alerts.length > 0;
    });
    
    console.log('📊 Results:');
    console.log('===========');
    console.log(`Initial status: ${initialStatus}`);
    console.log(`Final status: ${finalStatus}`);
    console.log(`Success alert visible: ${successAlert}`);
    
    if (initialStatus !== finalStatus && finalStatus.includes('Connected')) {
      console.log('🎉 SUCCESS: Status badge updated correctly after test!');
    } else if (finalStatus.includes('Connected')) {
      console.log('✅ GOOD: Status shows connected (may have been cached)');
    } else {
      console.log('❌ FAILURE: Status badge did not update to show success');
    }
    
  } catch (error) {
    console.error('💥 Test failed:', error.message);
  } finally {
    await browser.close();
    console.log('🔚 Browser closed');
  }
}

testStatusUpdate().catch(console.error);