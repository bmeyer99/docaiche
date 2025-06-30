const puppeteer = require('puppeteer');

async function testProviderPersistence() {
  console.log('🚀 Starting browser test for provider settings persistence...');
  
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
  });
  
  try {
    const page = await browser.newPage();
    
    // Set viewport
    await page.setViewport({ width: 1280, height: 720 });
    
    // Enable console logging from the page
    page.on('console', async msg => {
      const text = msg.text();
      if (text.includes('ProvidersConfigPage') || text.includes('ProviderForm') || text.includes('model_selection')) {
        // Try to get actual values for JSHandle objects
        const args = await Promise.all(msg.args().map(async arg => {
          try {
            return await arg.jsonValue();
          } catch {
            return arg.toString();
          }
        }));
        
        if (args.length > 0) {
          console.log(`🌐 Browser Log:`, ...args);
        } else {
          console.log(`🌐 Browser Log: ${text}`);
        }
      }
    });
    
    // Log any errors
    page.on('pageerror', error => {
      console.log(`🔴 Page Error: ${error.message}`);
    });
    
    console.log('📍 Navigating to providers page...');
    await page.goto('http://localhost:4080/dashboard/providers', { 
      waitUntil: 'networkidle2',
      timeout: 30000 
    });
    
    console.log('⏳ Waiting for page to fully load...');
    await new Promise(resolve => setTimeout(resolve, 3000));
    
    // Check if the page loaded successfully
    const title = await page.title();
    console.log(`📄 Page title: ${title}`);
    
    // Look for provider configuration sections
    console.log('🔍 Checking for provider configuration elements...');
    
    const providerCards = await page.$$('[data-provider-config]');
    console.log(`🎯 Found ${providerCards.length} provider configuration sections`);
    
    // Check for model selection section
    const modelSelectionElements = await page.$$eval('h3', 
      headers => headers.filter(h => h.textContent.includes('Text Generation') || h.textContent.includes('Embeddings')).length
    );
    if (modelSelectionElements > 0) {
      console.log('✅ Model selection section found');
    } else {
      console.log('❌ Model selection section not found');
    }
    
    // Check for any error messages
    const errorMessages = await page.$$eval('[role="alert"], .text-red-500, .text-destructive', 
      elements => elements.map(el => el.textContent.trim()).filter(text => text.length > 0)
    );
    
    if (errorMessages.length > 0) {
      console.log('⚠️  Error messages found:');
      errorMessages.forEach(msg => console.log(`   - ${msg}`));
    } else {
      console.log('✅ No error messages detected');
    }
    
    // Check for loading states
    const loadingElements = await page.$$('[data-loading], .animate-spin, .loading');
    console.log(`⏱️  Loading elements found: ${loadingElements.length}`);
    
    // Look for provider form elements
    console.log('🔍 Checking for specific provider forms...');
    
    // Check for Ollama provider specifically
    const ollamaSection = await page.$$eval('*', 
      elements => elements.some(el => el.textContent && el.textContent.includes('Ollama'))
    );
    if (ollamaSection) {
      console.log('✅ Ollama provider section found');
      
      // Check for configuration inputs
      const configInputs = await page.$$eval('input[type="text"], input[type="url"], textarea', 
        inputs => inputs.length
      );
      console.log(`📝 Configuration inputs found: ${configInputs}`);
    } else {
      console.log('❌ Ollama provider section not found');
    }
    
    // Check current page URL
    const currentUrl = page.url();
    console.log(`🔗 Current URL: ${currentUrl}`);
    
    // Wait a bit more to let any async operations complete
    console.log('⏳ Waiting for async operations to complete...');
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // Take a screenshot for debugging
    console.log('📷 Taking screenshot...');
    await page.screenshot({ path: '/home/lab/docaiche/provider-page-test.png', fullPage: true });
    
    // Check for any network failures
    const failedRequests = [];
    page.on('requestfailed', request => {
      failedRequests.push(`${request.method()} ${request.url()} - ${request.failure().errorText}`);
    });
    
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    if (failedRequests.length > 0) {
      console.log('🔴 Failed network requests:');
      failedRequests.forEach(req => console.log(`   - ${req}`));
    } else {
      console.log('✅ No failed network requests');
    }
    
    // Test page reload to check persistence
    console.log('🔄 Testing page reload for persistence...');
    await page.reload({ waitUntil: 'networkidle2' });
    await new Promise(resolve => setTimeout(resolve, 3000));
    
    console.log('✅ Browser test completed successfully!');
    
  } catch (error) {
    console.error('❌ Browser test failed:', error.message);
    
    // Take error screenshot
    try {
      const page = browser.pages()[0];
      if (page) {
        await page.screenshot({ path: '/home/lab/docaiche/provider-page-error.png', fullPage: true });
        console.log('📷 Error screenshot saved');
      }
    } catch (screenshotError) {
      console.log('Could not take error screenshot:', screenshotError.message);
    }
  } finally {
    await browser.close();
    console.log('🏁 Browser test finished');
  }
}

// Run the test
testProviderPersistence().catch(console.error);