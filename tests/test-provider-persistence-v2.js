const puppeteer = require('puppeteer');

async function testProviderPersistence() {
  console.log('🚀 Starting provider settings persistence test v2...');
  
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
  });
  
  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 1280, height: 720 });
    
    console.log('📋 Step 1: Navigate to providers page...');
    await page.goto('http://localhost:4080/dashboard/providers', { 
      waitUntil: 'networkidle2',
      timeout: 30000 
    });
    
    // Wait for page content to load - look for text we know should be there
    await page.waitForFunction(() => {
      return document.body.innerText.includes('AI Provider Configuration') || 
             document.body.innerText.includes('Model Selection');
    }, { timeout: 15000 });
    
    console.log('✅ Providers page loaded successfully');
    
    // Take screenshot of initial state
    await page.screenshot({ 
      path: '/home/lab/docaiche/test-initial-state.png',
      fullPage: true 
    });
    console.log('📸 Screenshot saved: test-initial-state.png');
    
    console.log('🔍 Step 2: Looking for provider sections...');
    
    // Look for text containing provider names
    const pageText = await page.evaluate(() => document.body.innerText);
    const providerNames = ['Ollama', 'OpenAI', 'Anthropic', 'Groq', 'LM Studio'];
    const foundProviders = providerNames.filter(name => pageText.includes(name));
    
    console.log(`Found providers mentioned on page: ${foundProviders.join(', ')}`);
    
    if (foundProviders.length === 0) {
      console.log('❌ No provider names found in page text');
      console.log('Page text (first 1000 chars):');
      console.log(pageText.substring(0, 1000));
    }
    
    console.log('🔍 Step 3: Looking for input fields...');
    
    // Find all input fields
    const inputs = await page.evaluate(() => {
      const inputElements = Array.from(document.querySelectorAll('input'));
      return inputElements.map((input, index) => ({
        index,
        type: input.type || 'text',
        placeholder: input.placeholder || '',
        name: input.name || '',
        id: input.id || '',
        value: input.value || '',
        className: input.className || ''
      }));
    });
    
    console.log(`Found ${inputs.length} input fields:`);
    inputs.forEach((input, i) => {
      console.log(`  ${i + 1}. Type: ${input.type}, Placeholder: "${input.placeholder}", Name: "${input.name}", Value: "${input.value}"`);
    });
    
    // Look for a base URL input field specifically
    const baseUrlInput = inputs.find(input => 
      input.placeholder.toLowerCase().includes('localhost') ||
      input.placeholder.toLowerCase().includes('11434') ||
      input.placeholder.toLowerCase().includes('base') ||
      input.name.toLowerCase().includes('base_url') ||
      input.id.toLowerCase().includes('base_url')
    );
    
    if (baseUrlInput) {
      console.log(`✅ Found potential base URL input: index ${baseUrlInput.index}, placeholder: "${baseUrlInput.placeholder}"`);
      
      console.log('📝 Step 4: Configuring Ollama provider...');
      
      // Click and configure the input field
      const inputSelector = `input:nth-of-type(${baseUrlInput.index + 1})`;
      await page.click(inputSelector);
      // Select all text and replace
      await page.keyboard.down('Control');
      await page.keyboard.press('a');
      await page.keyboard.up('Control');
      await page.type(inputSelector, 'http://localhost:11434/custom');
      
      console.log('⌨️  Entered base URL: http://localhost:11434/custom');
      
      // Wait for potential auto-save
      await new Promise(resolve => setTimeout(resolve, 3000));
      
      // Take screenshot after configuration
      await page.screenshot({ 
        path: '/home/lab/docaiche/test-after-config.png',
        fullPage: true 
      });
      console.log('📸 Screenshot saved: test-after-config.png');
      
      console.log('🔄 Step 5: Testing persistence - reloading page...');
      
      // Reload the page
      await page.reload({ waitUntil: 'networkidle2' });
      
      // Wait for page to load again
      await page.waitForFunction(() => {
        return document.body.innerText.includes('AI Provider Configuration') || 
               document.body.innerText.includes('Model Selection');
      }, { timeout: 15000 });
      
      console.log('✅ Page reloaded successfully');
      
      // Check if the value persisted
      const inputAfterReload = await page.evaluate((selector) => {
        const input = document.querySelector(selector);
        return input ? input.value : null;
      }, inputSelector);
      
      console.log(`🔍 Base URL value after reload: "${inputAfterReload}"`);
      
      if (inputAfterReload === 'http://localhost:11434/custom') {
        console.log('🎉 SUCCESS: Provider configuration persisted correctly!');
      } else if (inputAfterReload) {
        console.log(`⚠️  PARTIAL SUCCESS: Value persisted but different: "${inputAfterReload}"`);
      } else {
        console.log('❌ FAILURE: Provider configuration was not persisted');
      }
      
      // Take screenshot after reload
      await page.screenshot({ 
        path: '/home/lab/docaiche/test-after-reload.png',
        fullPage: true 
      });
      console.log('📸 Screenshot saved: test-after-reload.png');
      
    } else {
      console.log('❌ Could not find base URL input field');
    }
    
    console.log('🔍 Step 6: Testing API endpoints directly...');
    
    // Test the API endpoints
    try {
      const providersResponse = await page.evaluate(async () => {
        try {
          const res = await fetch('/api/v1/providers');
          const data = await res.json();
          return { success: true, data, status: res.status };
        } catch (error) {
          return { success: false, error: error.message };
        }
      });
      
      console.log('📡 API Response from /api/v1/providers:');
      if (providersResponse.success) {
        console.log(`✅ Status: ${providersResponse.status}`);
        const ollamaProvider = providersResponse.data.find(p => p.id === 'ollama');
        if (ollamaProvider) {
          console.log('✅ Ollama provider found in API response:');
          console.log(`   - Configured: ${ollamaProvider.configured}`);
          console.log(`   - Status: ${ollamaProvider.status}`);
          console.log(`   - Enabled: ${ollamaProvider.enabled}`);
          console.log(`   - Config: ${JSON.stringify(ollamaProvider.config || {}, null, 2)}`);
          console.log(`   - Models: ${JSON.stringify(ollamaProvider.models || [], null, 2)}`);
        } else {
          console.log('❌ Ollama provider not found in API response');
        }
      } else {
        console.log(`❌ API Error: ${providersResponse.error}`);
      }
    } catch (error) {
      console.log(`❌ Failed to test API: ${error.message}`);
    }
    
    console.log('📊 Final Assessment:');
    console.log('==================');
    console.log(`✅ Page loaded successfully on port 4080`);
    console.log(`✅ Found ${foundProviders.length} provider names on page`);
    console.log(`✅ Found ${inputs.length} input fields`);
    if (baseUrlInput) {
      console.log(`✅ Found base URL input field`);
    } else {
      console.log(`❌ No base URL input field found`);
    }
    
  } catch (error) {
    console.error('💥 Test failed with error:', error.message);
    
    // Take screenshot of error state
    try {
      const page = browser.pages()[0];
      if (page) {
        await page.screenshot({ 
          path: '/home/lab/docaiche/test-error-state.png',
          fullPage: true 
        });
        console.log('📸 Error screenshot saved: test-error-state.png');
      }
    } catch (screenshotError) {
      console.log('Failed to take error screenshot:', screenshotError.message);
    }
  } finally {
    await browser.close();
    console.log('🔚 Browser closed');
  }
}

// Run the test
testProviderPersistence().catch(console.error);