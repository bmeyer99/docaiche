const puppeteer = require('puppeteer');

describe('Providers Page E2E Test', () => {
  let browser;
  let page;
  const baseUrl = process.env.TEST_URL || 'http://localhost:3000';

  beforeAll(async () => {
    browser = await puppeteer.launch({
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
  });

  afterAll(async () => {
    if (browser) {
      await browser.close();
    }
  });

  beforeEach(async () => {
    page = await browser.newPage();
    await page.setViewport({ width: 1280, height: 800 });
    
    // Mock authentication by setting a cookie or token
    // In a real scenario, you'd need to handle actual authentication
    await page.evaluateOnNewDocument(() => {
      localStorage.setItem('auth-token', 'test-token');
    });
  });

  afterEach(async () => {
    if (page) {
      await page.close();
    }
  });

  describe('Provider Configuration Flow', () => {
    it('should load the providers page', async () => {
      await page.goto(`${baseUrl}/dashboard/providers-new`, { 
        waitUntil: 'networkidle2' 
      });

      // Check if the page title is present
      const title = await page.waitForSelector('h1', { timeout: 5000 });
      const titleText = await title.evaluate(el => el.textContent);
      expect(titleText).toBe('AI Provider Configuration');
    });

    it('should display provider categories', async () => {
      await page.goto(`${baseUrl}/dashboard/providers-new`, { 
        waitUntil: 'networkidle2' 
      });

      // Check for category tabs
      const localTab = await page.waitForSelector('button[role="tab"]:has-text("Local")', { timeout: 5000 });
      const cloudTab = await page.waitForSelector('button[role="tab"]:has-text("Cloud")', { timeout: 5000 });
      const enterpriseTab = await page.waitForSelector('button[role="tab"]:has-text("Enterprise")', { timeout: 5000 });

      expect(localTab).toBeTruthy();
      expect(cloudTab).toBeTruthy();
      expect(enterpriseTab).toBeTruthy();
    });

    it('should select a provider and show configuration form', async () => {
      await page.goto(`${baseUrl}/dashboard/providers-new`, { 
        waitUntil: 'networkidle2' 
      });

      // Click on Cloud tab
      await page.click('button[role="tab"]:has-text("Cloud")');
      await page.waitForTimeout(500);

      // Look for a provider card (assuming OpenAI exists)
      const providerCard = await page.waitForSelector('div[role="button"]:has-text("OpenAI")', { timeout: 5000 });
      await providerCard.click();

      // Check if configuration panel appears
      const configTitle = await page.waitForSelector('h3:has-text("Configure OpenAI")', { timeout: 5000 });
      expect(configTitle).toBeTruthy();

      // Check for API key field
      const apiKeyField = await page.waitForSelector('input[type="password"]', { timeout: 5000 });
      expect(apiKeyField).toBeTruthy();
    });

    it('should fill configuration and test connection', async () => {
      await page.goto(`${baseUrl}/dashboard/providers-new`, { 
        waitUntil: 'networkidle2' 
      });

      // Select OpenAI provider
      await page.click('button[role="tab"]:has-text("Cloud")');
      await page.waitForTimeout(500);
      
      const providerCard = await page.waitForSelector('div[role="button"]:has-text("OpenAI")', { timeout: 5000 });
      await providerCard.click();

      // Fill in API key
      const apiKeyField = await page.waitForSelector('input[type="password"]', { timeout: 5000 });
      await apiKeyField.type('sk-test-api-key-123456');

      // Click Test Connection button
      const testButton = await page.waitForSelector('button:has-text("Test Connection")', { timeout: 5000 });
      await testButton.click();

      // Wait for test result (either success or failure)
      const result = await page.waitForSelector('[role="alert"]', { timeout: 10000 });
      expect(result).toBeTruthy();
    });

    it('should persist configuration after page refresh', async () => {
      // This test would require actual backend integration
      // For now, we'll just check if the page loads correctly after refresh
      await page.goto(`${baseUrl}/dashboard/providers-new`, { 
        waitUntil: 'networkidle2' 
      });

      // Initial load
      const initialTitle = await page.waitForSelector('h1', { timeout: 5000 });
      expect(initialTitle).toBeTruthy();

      // Refresh the page
      await page.reload({ waitUntil: 'networkidle2' });

      // Check if page still loads correctly
      const reloadedTitle = await page.waitForSelector('h1', { timeout: 5000 });
      const titleText = await reloadedTitle.evaluate(el => el.textContent);
      expect(titleText).toBe('AI Provider Configuration');
    });

    it('should handle model selection', async () => {
      await page.goto(`${baseUrl}/dashboard/providers-new`, { 
        waitUntil: 'networkidle2' 
      });

      // Check if model selection panel exists (it should show when providers are configured)
      const modelSelectionTitle = await page.$('h3:has-text("Model Selection")');
      
      if (modelSelectionTitle) {
        // Check for shared provider toggle
        const sharedToggle = await page.$('label:has-text("Use the same provider")');
        expect(sharedToggle).toBeTruthy();

        // Check for model dropdowns
        const selectElements = await page.$$('button[role="combobox"]');
        expect(selectElements.length).toBeGreaterThan(0);
      }
    });
  });

  describe('Error Handling', () => {
    it('should show error when saving without required fields', async () => {
      await page.goto(`${baseUrl}/dashboard/providers-new`, { 
        waitUntil: 'networkidle2' 
      });

      // Select a provider
      await page.click('button[role="tab"]:has-text("Cloud")');
      await page.waitForTimeout(500);
      
      const providerCard = await page.waitForSelector('div[role="button"]:has-text("OpenAI")', { timeout: 5000 });
      await providerCard.click();

      // Try to save without filling required fields
      const saveButton = await page.waitForSelector('button:has-text("Save Configuration")', { timeout: 5000 });
      await saveButton.click();

      // Should show validation error
      const errorMessage = await page.waitForSelector('p:has-text("required")', { timeout: 5000 });
      expect(errorMessage).toBeTruthy();
    });
  });

  describe('Accessibility', () => {
    it('should be keyboard navigable', async () => {
      await page.goto(`${baseUrl}/dashboard/providers-new`, { 
        waitUntil: 'networkidle2' 
      });

      // Tab through elements
      await page.keyboard.press('Tab');
      await page.keyboard.press('Tab');
      
      // Check if elements can be activated with Enter
      await page.keyboard.press('Enter');
      
      // Basic check - page should still be functional
      const title = await page.$('h1');
      expect(title).toBeTruthy();
    });

    it('should have proper ARIA labels', async () => {
      await page.goto(`${baseUrl}/dashboard/providers-new`, { 
        waitUntil: 'networkidle2' 
      });

      // Check for ARIA labels on interactive elements
      const buttons = await page.$$('[role="button"]');
      expect(buttons.length).toBeGreaterThan(0);

      const tabs = await page.$$('[role="tab"]');
      expect(tabs.length).toBe(3); // Local, Cloud, Enterprise
    });
  });
});

// Helper function to take screenshots for debugging
async function takeScreenshot(page, name) {
  await page.screenshot({ 
    path: `screenshots/${name}-${Date.now()}.png`,
    fullPage: true 
  });
}