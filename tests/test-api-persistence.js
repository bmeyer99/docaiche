const puppeteer = require('puppeteer');

async function testAPIPersistence() {
  console.log('🚀 Testing API-level provider persistence...');
  
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
    
    // Wait for page to load
    await page.waitForFunction(() => {
      return document.body.innerText.includes('AI Provider Configuration');
    }, { timeout: 15000 });
    
    console.log('✅ Page loaded successfully');
    
    console.log('🔍 Step 2: Check initial API state...');
    
    // Get initial state from API
    const initialState = await page.evaluate(async () => {
      try {
        const res = await fetch('/api/v1/providers');
        const data = await res.json();
        const ollama = data.find(p => p.id === 'ollama');
        return { 
          success: true, 
          ollama: ollama || null,
          status: res.status
        };
      } catch (error) {
        return { success: false, error: error.message };
      }
    });
    
    if (initialState.success && initialState.ollama) {
      console.log('✅ Initial Ollama config from API:');
      console.log(`   - Configured: ${initialState.ollama.configured}`);
      console.log(`   - Status: ${initialState.ollama.status}`);
      console.log(`   - Enabled: ${initialState.ollama.enabled}`);
      console.log(`   - Config: ${JSON.stringify(initialState.ollama.config || {}, null, 2)}`);
    } else {
      console.log('❌ Failed to get initial state:', initialState.error);
    }
    
    console.log('📝 Step 3: Update configuration via UI...');
    
    // Find and update the base URL input
    const inputUpdated = await page.evaluate(() => {
      const inputs = Array.from(document.querySelectorAll('input'));
      const baseUrlInput = inputs.find(input => 
        input.placeholder && input.placeholder.includes('localhost') && input.placeholder.includes('11434')
      );
      
      if (baseUrlInput) {
        baseUrlInput.value = 'http://localhost:11434/test-persistence';
        // Trigger change events
        baseUrlInput.dispatchEvent(new Event('input', { bubbles: true }));
        baseUrlInput.dispatchEvent(new Event('change', { bubbles: true }));
        baseUrlInput.dispatchEvent(new Event('blur', { bubbles: true }));
        return true;
      }
      return false;
    });
    
    if (inputUpdated) {
      console.log('✅ Updated base URL to: http://localhost:11434/test-persistence');
      
      // Wait for potential auto-save
      await new Promise(resolve => setTimeout(resolve, 5000));
      console.log('⏳ Waited 5 seconds for auto-save...');
      
      console.log('🔍 Step 4: Check API state after change...');
      
      // Check if the change persisted to the API
      const updatedState = await page.evaluate(async () => {
        try {
          const res = await fetch('/api/v1/providers');
          const data = await res.json();
          const ollama = data.find(p => p.id === 'ollama');
          return { 
            success: true, 
            ollama: ollama || null,
            status: res.status
          };
        } catch (error) {
          return { success: false, error: error.message };
        }
      });
      
      if (updatedState.success && updatedState.ollama) {
        console.log('✅ Updated Ollama config from API:');
        console.log(`   - Configured: ${updatedState.ollama.configured}`);
        console.log(`   - Status: ${updatedState.ollama.status}`);
        console.log(`   - Enabled: ${updatedState.ollama.enabled}`);
        console.log(`   - Config: ${JSON.stringify(updatedState.ollama.config || {}, null, 2)}`);
        
        // Check if the endpoint was updated
        const hasUpdatedUrl = updatedState.ollama.config && 
                              updatedState.ollama.config.endpoint === 'http://localhost:11434/test-persistence';
        
        if (hasUpdatedUrl) {
          console.log('🎉 SUCCESS: Configuration change persisted to backend API!');
        } else {
          console.log('❌ FAILURE: Configuration change did not persist to backend');
          console.log(`Expected: http://localhost:11434/test-persistence`);
          console.log(`Got: ${updatedState.ollama.config?.endpoint || 'undefined'}`);
        }
      } else {
        console.log('❌ Failed to get updated state:', updatedState.error);
      }
      
    } else {
      console.log('❌ Could not find or update base URL input');
    }
    
    console.log('🔍 Step 5: Test config endpoint directly...');
    
    // Test the config endpoint
    const configResponse = await page.evaluate(async () => {
      try {
        const res = await fetch('/api/v1/config');
        const data = await res.json();
        return { success: true, data, status: res.status };
      } catch (error) {
        return { success: false, error: error.message };
      }
    });
    
    if (configResponse.success) {
      console.log('✅ Config endpoint response:');
      console.log(`   - Status: ${configResponse.status}`);
      
      // Look for Ollama configuration
      const ollamaConfig = configResponse.data.items?.find(item => 
        item.key && item.key.includes('ollama')
      );
      
      if (ollamaConfig) {
        console.log('✅ Found Ollama config in /api/v1/config:');
        console.log(`   - Key: ${ollamaConfig.key}`);
        console.log(`   - Value: ${JSON.stringify(ollamaConfig.value, null, 2)}`);
      } else {
        console.log('❌ No Ollama config found in /api/v1/config');
      }
    } else {
      console.log(`❌ Config endpoint error: ${configResponse.error}`);
    }
    
    console.log('📊 Final Assessment:');
    console.log('==================');
    
    if (initialState.success) {
      console.log('✅ API endpoints accessible');
    } else {
      console.log('❌ API endpoints not accessible');
    }
    
    if (inputUpdated) {
      console.log('✅ UI input field found and updated');
    } else {
      console.log('❌ UI input field not found');
    }
    
  } catch (error) {
    console.error('💥 Test failed:', error.message);
  } finally {
    await browser.close();
    console.log('🔚 Browser closed');
  }
}

testAPIPersistence().catch(console.error);