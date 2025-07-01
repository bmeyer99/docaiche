const puppeteer = require('puppeteer');

async function testEndToEndFix() {
  console.log('🚀 Testing end-to-end provider configuration and test...');
  
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
  });
  
  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 1280, height: 720 });
    
    // Monitor console logs
    page.on('console', msg => {
      const text = msg.text();
      if (text.includes('Set Base URL') || text.includes('Test') || text.includes('Error')) {
        console.log(`🖥️  BROWSER: ${text}`);
      }
    });
    
    let testRequestSent = false;
    let testResponseReceived = false;
    
    // Monitor network requests
    page.on('request', request => {
      const url = request.url();
      if (url.includes('/api/v1/providers/ollama/test') && request.method() === 'POST') {
        testRequestSent = true;
        console.log(`📡 TEST REQUEST: ${request.method()} ${url}`);
        
        try {
          const body = JSON.parse(request.postData());
          if (body.base_url) {
            console.log(`✅ base_url sent: ${body.base_url}`);
          } else {
            console.log(`❌ base_url missing in request`);
          }
        } catch (e) {
          console.log(`⚠️  Could not parse request body`);
        }
      }
    });
    
    page.on('response', async response => {
      const url = response.url();
      if (url.includes('/api/v1/providers/ollama/test') && response.request().method() === 'POST') {
        testResponseReceived = true;
        console.log(`📡 TEST RESPONSE: ${response.status()} ${response.statusText()}`);
        
        if (response.status() === 200) {
          try {
            const responseBody = await response.json();
            console.log(`✅ Success response:`, responseBody.success ? 'Connection successful' : 'Connection failed');
            if (responseBody.models) {
              console.log(`📋 Models found: ${responseBody.models.length}`);
            }
          } catch (e) {
            console.log(`⚠️  Could not parse response body`);
          }
        } else {
          console.log(`❌ Test failed with status ${response.status()}`);
        }
      }
    });
    
    console.log('📋 Step 1: Navigate to providers page...');
    await page.goto('http://localhost:4080/dashboard/providers', { 
      waitUntil: 'networkidle2',
      timeout: 30000 
    });
    
    await page.waitForFunction(() => {
      return document.body.innerText.includes('AI Provider Configuration');
    }, { timeout: 15000 });
    
    console.log('✅ Page loaded');
    
    console.log('📝 Step 2: Configure Ollama with valid Base URL...');
    
    // Set a valid Ollama server URL
    const validOllamaUrl = 'http://192.168.4.204:11434/api';
    
    const configResult = await page.evaluate((baseUrl) => {
      const inputs = Array.from(document.querySelectorAll('input'));
      const baseUrlInput = inputs.find(input => 
        input.placeholder === 'http://localhost:11434/api'
      );
      
      if (baseUrlInput) {
        const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        nativeInputValueSetter.call(baseUrlInput, baseUrl);
        
        const event = new Event('input', { bubbles: true });
        baseUrlInput.dispatchEvent(event);
        
        console.log(`Set Base URL to: ${baseUrl}`);
        return { success: true, value: baseUrl };
      }
      return { success: false };
    }, validOllamaUrl);
    
    if (configResult.success) {
      console.log(`✅ Base URL configured: ${configResult.value}`);
    } else {
      console.log('❌ Failed to configure Base URL');
      return;
    }
    
    console.log('🧪 Step 3: Test connection...');
    
    // Click the test button
    const testClicked = await page.evaluate(() => {
      const buttons = Array.from(document.querySelectorAll('button'));
      const testButton = buttons.find(button => 
        button.textContent && button.textContent.includes('Test Connection')
      );
      
      if (testButton && !testButton.disabled) {
        testButton.click();
        return true;
      }
      return false;
    });
    
    if (testClicked) {
      console.log('✅ Test Connection button clicked');
    } else {
      console.log('❌ Failed to click Test Connection button');
      return;
    }
    
    console.log('⏳ Step 4: Wait for test results...');
    await new Promise(resolve => setTimeout(resolve, 5000));
    
    // Check for any toast messages
    const toastMessages = await page.evaluate(() => {
      const toasts = Array.from(document.querySelectorAll('[role="status"], .toast, [data-toast], [data-sonner-toast]'));
      return toasts.map(toast => ({
        text: toast.textContent,
        classes: toast.className
      })).filter(toast => toast.text && toast.text.trim());
    });
    
    console.log('📊 Final Results:');
    console.log('================');
    
    if (testRequestSent) {
      console.log('✅ Test request was sent to backend');
    } else {
      console.log('❌ No test request was sent');
    }
    
    if (testResponseReceived) {
      console.log('✅ Test response was received from backend');
    } else {
      console.log('❌ No test response was received');
    }
    
    if (toastMessages.length > 0) {
      console.log('📝 Toast notifications:');
      toastMessages.forEach((toast, i) => {
        console.log(`   ${i + 1}. ${toast.text.trim()}`);
      });
    } else {
      console.log('📝 No toast notifications found');
    }
    
    // Final status check
    const providerStatus = await page.evaluate(() => {
      const badges = Array.from(document.querySelectorAll('.border-green-500, .border-red-500, .border-amber-500'));
      return badges.map(badge => badge.textContent.trim());
    });
    
    if (providerStatus.length > 0) {
      console.log('🏷️  Provider status badges:', providerStatus);
    }
    
    if (testRequestSent && testResponseReceived) {
      console.log('🎉 SUCCESS: End-to-end test flow completed successfully!');
    } else {
      console.log('❌ FAILURE: Test flow incomplete');
    }
    
  } catch (error) {
    console.error('💥 Test failed:', error.message);
  } finally {
    await browser.close();
    console.log('🔚 Browser closed');
  }
}

testEndToEndFix().catch(console.error);