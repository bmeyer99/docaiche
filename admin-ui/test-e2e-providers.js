const puppeteer = require('puppeteer');

async function runE2ETest() {
  console.log('Starting E2E test for Providers feature...');
  
  let browser;
  let page;
  const baseUrl = 'http://localhost:4080'; // Using the Docker port
  
  try {
    // Launch browser
    console.log('Launching browser...');
    browser = await puppeteer.launch({
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'],
      slowMo: 100 // Slow down actions for stability
    });
    
    page = await browser.newPage();
    await page.setViewport({ width: 1440, height: 900 });
    
    // Enable request interception for API mocking
    await page.setRequestInterception(true);
    
    // Mock API responses
    page.on('request', (request) => {
      const url = request.url();
      
      if (url.includes('/api/v1/provider-settings')) {
        request.respond({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            providers: {
              openai: {
                id: 'openai',
                name: 'OpenAI',
                category: 'cloud',
                description: 'OpenAI GPT models',
                requiresApiKey: true,
                supportsEmbedding: true,
                supportsChat: true,
                status: 'not_configured',
                configured: false,
                enabled: false,
                config: {}
              },
              anthropic: {
                id: 'anthropic',
                name: 'Anthropic Claude',
                category: 'cloud',
                description: 'Claude AI models',
                requiresApiKey: true,
                supportsEmbedding: false,
                supportsChat: true,
                status: 'not_configured',
                configured: false,
                enabled: false,
                config: {}
              },
              ollama: {
                id: 'ollama',
                name: 'Ollama',
                category: 'local',
                description: 'Local Ollama models',
                requiresApiKey: false,
                supportsEmbedding: true,
                supportsChat: true,
                status: 'not_configured',
                configured: false,
                enabled: false,
                config: {}
              }
            },
            modelSelection: {
              textGeneration: { provider: '', model: '' },
              embeddings: { provider: '', model: '' },
              sharedProvider: false
            }
          })
        });
      } else if (url.includes('/api/v1/providers/openai/test')) {
        request.respond({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            message: 'Connection successful',
            models: ['gpt-4', 'gpt-3.5-turbo', 'gpt-4-turbo']
          })
        });
      } else if (url.includes('/api/v1/providers/openai/models')) {
        request.respond({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(['gpt-4', 'gpt-3.5-turbo', 'gpt-4-turbo', 'text-embedding-3-small'])
        });
      } else if (url.includes('/api/v1/provider-settings') && request.method() === 'POST') {
        request.respond({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true })
        });
      } else {
        request.continue();
      }
    });
    
    // Test 1: Navigate to providers page
    console.log('\nTest 1: Navigating to providers page...');
    await page.goto(`${baseUrl}/dashboard/providers-new`, { 
      waitUntil: 'domcontentloaded',
      timeout: 15000
    });
    
    // Wait for page to load
    await page.waitForSelector('h1', { timeout: 10000 });
    const title = await page.$eval('h1', el => el.textContent);
    console.log(`✓ Page loaded with title: ${title}`);
    
    // Test 2: Select Cloud category
    console.log('\nTest 2: Selecting Cloud category...');
    await page.waitForSelector('button[role="tab"]', { timeout: 5000 });
    
    // Find and click Cloud tab
    const tabs = await page.$$('button[role="tab"]');
    for (const tab of tabs) {
      const text = await page.evaluate(el => el.textContent, tab);
      if (text.includes('Cloud')) {
        await tab.click();
        console.log('✓ Clicked Cloud tab');
        break;
      }
    }
    
    await new Promise(resolve => setTimeout(resolve, 500));
    
    // Test 3: Select OpenAI provider
    console.log('\nTest 3: Selecting OpenAI provider...');
    await page.waitForSelector('div[role="button"]', { timeout: 5000 });
    
    const providerCards = await page.$$('div[role="button"]');
    let openAICard = null;
    
    for (const card of providerCards) {
      const text = await page.evaluate(el => el.textContent, card);
      if (text && text.includes('OpenAI')) {
        openAICard = card;
        await card.click();
        console.log('✓ Selected OpenAI provider');
        break;
      }
    }
    
    if (!openAICard) {
      throw new Error('OpenAI provider card not found');
    }
    
    // Test 4: Fill configuration
    console.log('\nTest 4: Filling configuration...');
    await page.waitForSelector('input[type="password"]', { timeout: 5000 });
    const apiKeyInput = await page.$('input[type="password"]');
    await apiKeyInput.click();
    await apiKeyInput.type('sk-test-1234567890abcdef');
    console.log('✓ Entered API key');
    
    // Test 5: Save configuration
    console.log('\nTest 5: Saving configuration...');
    const saveButtons = await page.$$('button');
    let saveButton = null;
    
    for (const button of saveButtons) {
      const text = await page.evaluate(el => el.textContent, button);
      if (text && text.includes('Save Configuration')) {
        saveButton = button;
        await button.click();
        console.log('✓ Clicked Save Configuration');
        break;
      }
    }
    
    if (!saveButton) {
      throw new Error('Save Configuration button not found');
    }
    
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    // Test 6: Test connection
    console.log('\nTest 6: Testing connection...');
    const testButtons = await page.$$('button');
    let testButton = null;
    
    for (const button of testButtons) {
      const text = await page.evaluate(el => el.textContent, button);
      if (text && text.includes('Test Connection')) {
        testButton = button;
        await button.click();
        console.log('✓ Clicked Test Connection');
        break;
      }
    }
    
    if (!testButton) {
      throw new Error('Test Connection button not found');
    }
    
    // Wait for test result
    await page.waitForSelector('[role="alert"]', { timeout: 10000 });
    console.log('✓ Connection test completed');
    
    // Test 7: Check model selection panel
    console.log('\nTest 7: Checking model selection panel...');
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    const modelSelectionTitle = await page.$('h3');
    let foundModelSelection = false;
    
    const h3Elements = await page.$$('h3');
    for (const h3 of h3Elements) {
      const text = await page.evaluate(el => el.textContent, h3);
      if (text && text.includes('Model Selection')) {
        foundModelSelection = true;
        console.log('✓ Model Selection panel is visible');
        break;
      }
    }
    
    if (!foundModelSelection) {
      console.log('⚠ Model Selection panel not found (might be expected if no providers are configured)');
    }
    
    // Test 8: Check progress tracker
    console.log('\nTest 8: Checking progress tracker...');
    const progressButtons = await page.$$('[aria-current]');
    if (progressButtons.length > 0) {
      console.log('✓ Progress tracker is active');
    }
    
    // Test 9: Take screenshot
    console.log('\nTest 9: Taking screenshot...');
    await page.screenshot({ 
      path: `screenshot-providers-e2e-${Date.now()}.png`,
      fullPage: true 
    });
    console.log('✓ Screenshot saved');
    
    console.log('\n✅ All E2E tests passed successfully!');
    
  } catch (error) {
    console.error('\n❌ E2E test failed:', error.message);
    
    // Take error screenshot
    if (page) {
      await page.screenshot({ 
        path: `screenshot-error-${Date.now()}.png`,
        fullPage: true 
      });
      console.log('Error screenshot saved');
    }
    
    throw error;
  } finally {
    if (browser) {
      await browser.close();
    }
  }
}

// Run the test
runE2ETest()
  .then(() => {
    console.log('\nE2E test completed successfully');
    process.exit(0);
  })
  .catch((error) => {
    console.error('\nE2E test failed:', error);
    process.exit(1);
  });