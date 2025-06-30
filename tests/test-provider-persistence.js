const puppeteer = require('puppeteer');

async function testProviderPersistence() {
  console.log('🚀 Starting provider settings persistence test...');
  
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
  });
  
  try {
    const page = await browser.newPage();
    
    // Set viewport
    await page.setViewport({ width: 1280, height: 720 });
    
    console.log('📋 Step 1: Navigate to providers page...');
    await page.goto('http://localhost:4080/dashboard/providers', { 
      waitUntil: 'networkidle2',
      timeout: 30000 
    });
    
    // Wait for page to load
    await page.waitForSelector('[data-testid="providers-config-page"], .providers-page, [class*="provider"]', {
      timeout: 15000
    });
    
    console.log('✅ Providers page loaded successfully');
    
    // Take screenshot of initial state
    await page.screenshot({ 
      path: '/home/lab/docaiche/test-initial-state.png',
      fullPage: true 
    });
    console.log('📸 Screenshot saved: test-initial-state.png');
    
    console.log('🔍 Step 2: Examining provider configurations...');
    
    // Look for provider cards or sections
    const providerElements = await page.$$eval('[class*="provider"], [data-provider], .card', elements => {
      return elements.map(el => ({
        text: el.textContent?.substring(0, 100) || '',
        classes: el.className || '',
        id: el.id || '',
        hasInputs: el.querySelectorAll('input, textarea, select').length > 0
      }));
    });
    
    console.log(`Found ${providerElements.length} potential provider elements:`);
    providerElements.forEach((el, i) => {
      console.log(`  ${i + 1}. Classes: "${el.classes}", Has inputs: ${el.hasInputs}, Text: "${el.text.trim()}"`);
    });
    
    console.log('🔍 Step 3: Looking for Ollama provider specifically...');
    
    // Try to find Ollama provider section
    let ollamaSection = null;
    try {
      // Look for text containing "Ollama"
      const ollamaElements = await page.$$eval('*', elements => {
        return elements.filter(el => {
          const text = el.textContent || '';
          return text.includes('Ollama') || text.includes('ollama');
        }).map(el => ({
          tagName: el.tagName,
          className: el.className,
          id: el.id,
          text: el.textContent?.substring(0, 100) || ''
        }));
      });
      
      console.log(`Found ${ollamaElements.length} elements containing "Ollama":`);
      ollamaElements.forEach((el, i) => {
        console.log(`  ${i + 1}. ${el.tagName}.${el.className} - "${el.text.trim()}"`);
      });
      
      // Try to find a base URL input field
      const baseUrlInput = await page.$('input[placeholder*="localhost"], input[placeholder*="11434"], input[name*="base_url"], input[id*="base_url"]');
      
      if (baseUrlInput) {
        console.log('✅ Found base URL input field');
        
        console.log('📝 Step 4: Configuring Ollama provider...');
        
        // Clear existing value and set new one
        await baseUrlInput.click({ clickCount: 3 }); // Select all
        await baseUrlInput.type('http://localhost:11434');
        
        console.log('⌨️  Entered base URL: http://localhost:11434');
        
        // Look for save button
        const saveButton = await page.$('button[type="submit"], button:contains("Save"), button:contains("Update"), [data-testid*="save"]');
        
        if (saveButton) {
          console.log('💾 Step 5: Saving configuration...');
          await saveButton.click();
          
          // Wait for save to complete
          await page.waitForTimeout(2000);
          console.log('✅ Configuration saved');
        } else {
          console.log('⚠️  No explicit save button found - checking for auto-save...');
          // Wait a bit for potential auto-save
          await page.waitForTimeout(2000);
        }
        
        // Take screenshot after configuration
        await page.screenshot({ 
          path: '/home/lab/docaiche/test-after-config.png',
          fullPage: true 
        });
        console.log('📸 Screenshot saved: test-after-config.png');
        
        console.log('🔄 Step 6: Testing persistence - reloading page...');
        
        // Reload the page to test persistence
        await page.reload({ waitUntil: 'networkidle2' });
        
        // Wait for page to load again
        await page.waitForSelector('[data-testid="providers-config-page"], .providers-page, [class*="provider"]', {
          timeout: 15000
        });
        
        console.log('✅ Page reloaded successfully');
        
        // Check if the base URL value persisted
        const baseUrlInputAfter = await page.$('input[placeholder*="localhost"], input[placeholder*="11434"], input[name*="base_url"], input[id*="base_url"]');
        
        if (baseUrlInputAfter) {
          const persistedValue = await baseUrlInputAfter.evaluate(el => el.value);
          console.log(`🔍 Base URL value after reload: "${persistedValue}"`);
          
          if (persistedValue === 'http://localhost:11434') {
            console.log('🎉 SUCCESS: Provider configuration persisted correctly!');
          } else if (persistedValue) {
            console.log(`⚠️  PARTIAL SUCCESS: Value persisted but different: "${persistedValue}"`);
          } else {
            console.log('❌ FAILURE: Provider configuration was not persisted');
          }
        } else {
          console.log('❌ Could not find base URL input after reload');
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
      
    } catch (error) {
      console.log('❌ Error during Ollama configuration:', error.message);
    }
    
    console.log('🔍 Step 7: Checking backend API directly...');
    
    // Test the API endpoints directly
    try {
      const response = await page.evaluate(async () => {
        try {
          const res = await fetch('/api/v1/providers');
          return await res.json();
        } catch (error) {
          return { error: error.message };
        }
      });
      
      console.log('📡 API Response from /api/v1/providers:');
      if (response.error) {
        console.log(`❌ API Error: ${response.error}`);
      } else {
        const ollamaProvider = response.find(p => p.id === 'ollama');
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
      }
    } catch (error) {
      console.log(`❌ Failed to test API: ${error.message}`);
    }
    
    console.log('📊 Final Assessment:');
    console.log('==================');
    
    // Summary of findings
    const findings = [];
    
    if (providerElements.length > 0) {
      findings.push('✅ Provider elements found on page');
    } else {
      findings.push('❌ No provider elements found');
    }
    
    findings.forEach(finding => console.log(finding));
    
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