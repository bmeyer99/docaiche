const puppeteer = require('puppeteer');

describe('Complete Provider Configuration Flow E2E', () => {
  let browser;
  let page;
  const baseUrl = process.env.TEST_URL || 'http://localhost:3000';

  beforeAll(async () => {
    browser = await puppeteer.launch({
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox'],
      slowMo: 50 // Slow down actions for stability
    });
  });

  afterAll(async () => {
    if (browser) {
      await browser.close();
    }
  });

  beforeEach(async () => {
    page = await browser.newPage();
    await page.setViewport({ width: 1440, height: 900 });
    
    // Set up request interception for API mocking
    await page.setRequestInterception(true);
    
    page.on('request', (request) => {
      const url = request.url();
      
      // Mock API responses
      if (url.includes('/api/v1/providers')) {
        request.respond({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([
            {
              id: 'openai',
              name: 'OpenAI',
              category: 'cloud',
              description: 'OpenAI GPT models',
              requires_api_key: true,
              supports_embedding: true,
              supports_chat: true,
              status: 'not_configured',
              configured: false,
              enabled: false
            },
            {
              id: 'anthropic',
              name: 'Anthropic Claude',
              category: 'cloud',
              description: 'Claude AI models',
              requires_api_key: true,
              supports_embedding: false,
              supports_chat: true,
              status: 'not_configured',
              configured: false,
              enabled: false
            },
            {
              id: 'ollama',
              name: 'Ollama',
              category: 'local',
              description: 'Local Ollama models',
              requires_api_key: false,
              supports_embedding: true,
              supports_chat: true,
              status: 'not_configured',
              configured: false,
              enabled: false
            }
          ])
        });
      } else if (url.includes('/api/v1/models/config')) {
        request.respond({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            text_generation: { provider: '', model: '' },
            embeddings: { provider: '', model: '' },
            use_shared_provider: false
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
      } else if (url.includes('/api/v1/providers/openai/config')) {
        request.respond({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true })
        });
      } else {
        request.continue();
      }
    });
    
    // Mock authentication
    await page.evaluateOnNewDocument(() => {
      localStorage.setItem('auth-token', 'test-token');
    });
  });

  afterEach(async () => {
    if (page) {
      await page.close();
    }
  });

  it('should complete full provider configuration flow', async () => {
    // Step 1: Navigate to providers page
    await page.goto(`${baseUrl}/dashboard/providers-new`, { 
      waitUntil: 'networkidle2',
      timeout: 30000
    });

    // Verify page loaded
    await page.waitForSelector('h1::-p-text(AI Provider Configuration)', { timeout: 10000 });
    
    // Step 2: Select Cloud category
    await page.click('button[role="tab"]::-p-text(Cloud)');
    await page.waitForTimeout(500);

    // Step 3: Select OpenAI provider
    const providerCards = await page.$$('div[role="button"]');
    let openAICard = null;
    
    for (const card of providerCards) {
      const text = await card.evaluate(el => el.textContent);
      if (text && text.includes('OpenAI')) {
        openAICard = card;
        break;
      }
    }
    
    expect(openAICard).toBeTruthy();
    await openAICard.click();
    
    // Step 4: Verify configuration panel appears
    await page.waitForSelector('h3::-p-text(Configure OpenAI)', { timeout: 5000 });
    
    // Step 5: Fill in API key
    const apiKeyInput = await page.waitForSelector('input[type="password"]', { timeout: 5000 });
    await apiKeyInput.click();
    await apiKeyInput.type('sk-test-1234567890abcdef');
    
    // Step 6: Save configuration
    const saveButton = await page.waitForSelector('button::-p-text(Save Configuration)', { timeout: 5000 });
    await saveButton.click();
    
    // Wait for save to complete
    await page.waitForTimeout(1000);
    
    // Step 7: Test connection
    const testButton = await page.waitForSelector('button::-p-text(Test Connection)', { timeout: 5000 });
    await testButton.click();
    
    // Wait for test result
    await page.waitForSelector('[role="alert"]', { timeout: 10000 });
    
    // Step 8: Verify model selection panel appears
    await page.waitForSelector('h3::-p-text(Model Selection)', { timeout: 5000 });
    
    // Step 9: Select text generation model
    const comboboxes = await page.$$('button[role="combobox"]');
    expect(comboboxes.length).toBeGreaterThanOrEqual(2);
    
    // Click first combobox (text generation provider)
    await comboboxes[0].click();
    await page.waitForTimeout(500);
    
    // Select OpenAI from dropdown
    const openAIOption = await page.waitForSelector('[role="option"]::-p-text(OpenAI)', { timeout: 5000 });
    await openAIOption.click();
    await page.waitForTimeout(500);
    
    // Click second combobox (text generation model)
    await comboboxes[1].click();
    await page.waitForTimeout(500);
    
    // Select GPT-4 model
    const gpt4Option = await page.waitForSelector('[role="option"]::-p-text(gpt-4)', { timeout: 5000 });
    await gpt4Option.click();
    
    // Step 10: Enable shared provider
    const sharedProviderSwitch = await page.waitForSelector('button[role="switch"]', { timeout: 5000 });
    await sharedProviderSwitch.click();
    
    // Step 11: Save model selection
    const saveModelButton = await page.waitForSelector('button::-p-text(Save Model Selection)', { timeout: 5000 });
    await saveModelButton.click();
    
    // Wait for save to complete
    await page.waitForTimeout(1000);
    
    // Step 12: Verify current configuration shows up
    const currentConfig = await page.waitForSelector('h3::-p-text(Current Configuration)', { timeout: 5000 });
    expect(currentConfig).toBeTruthy();
    
    // Verify the configuration details
    const configText = await page.evaluate(() => {
      const configCard = document.querySelector('h3:has-text("Current Configuration")').closest('[data-slot="card"]');
      return configCard ? configCard.textContent : '';
    });
    
    expect(configText).toContain('OpenAI');
    expect(configText).toContain('gpt-4');
    expect(configText).toContain('Using shared provider');
  }, 60000); // 60 second timeout for complete flow

  it('should handle errors gracefully', async () => {
    await page.goto(`${baseUrl}/dashboard/providers-new`, { 
      waitUntil: 'networkidle2' 
    });

    // Select provider
    await page.click('button[role="tab"]::-p-text(Cloud)');
    await page.waitForTimeout(500);
    
    const providerCards = await page.$$('div[role="button"]');
    for (const card of providerCards) {
      const text = await card.evaluate(el => el.textContent);
      if (text && text.includes('OpenAI')) {
        await card.click();
        break;
      }
    }
    
    // Try to save without API key
    const saveButton = await page.waitForSelector('button::-p-text(Save Configuration)', { timeout: 5000 });
    await saveButton.click();
    
    // Should show validation error
    const errorMessage = await page.waitForSelector('[role="alert"]::-p-text(required)', { timeout: 5000 });
    expect(errorMessage).toBeTruthy();
  });

  it('should support keyboard navigation', async () => {
    await page.goto(`${baseUrl}/dashboard/providers-new`, { 
      waitUntil: 'networkidle2' 
    });

    // Tab to first interactive element
    await page.keyboard.press('Tab');
    
    // Use arrow keys to navigate tabs
    await page.keyboard.press('ArrowRight');
    await page.waitForTimeout(500);
    
    // Check if Cloud tab is selected
    const cloudTab = await page.$('button[role="tab"][aria-selected="true"]::-p-text(Cloud)');
    expect(cloudTab).toBeTruthy();
    
    // Tab to provider cards
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    
    // Select provider with Enter
    await page.keyboard.press('Enter');
    
    // Verify configuration panel appears
    const configPanel = await page.waitForSelector('h3::-p-text(Configure)', { timeout: 5000 });
    expect(configPanel).toBeTruthy();
  });

  it('should show progress tracker', async () => {
    await page.goto(`${baseUrl}/dashboard/providers-new`, { 
      waitUntil: 'networkidle2' 
    });

    // Check all progress steps are visible
    const progressSteps = await page.$$('[role="button"]:has-text("Select Provider"), [role="button"]:has-text("Configure"), [role="button"]:has-text("Test Connection"), [role="button"]:has-text("Select Models")');
    expect(progressSteps.length).toBe(4);
    
    // Verify first step is active
    const activeStep = await page.$('[aria-current="step"]');
    const activeText = await activeStep.evaluate(el => el.textContent);
    expect(activeText).toContain('Select Provider');
  });
});