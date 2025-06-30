const puppeteer = require('puppeteer');

async function testProviderStatusFix() {
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
  });
  
  try {
    const page = await browser.newPage();
    await page.goto('http://localhost:4080/dashboard/providers');
    
    console.log('Navigated to providers page');
    
    // Wait for page to load
    await new Promise(resolve => setTimeout(resolve, 3000));
    
    // Check what's on the page
    const pageContent = await page.evaluate(() => {
      const buttons = Array.from(document.querySelectorAll('button'));
      return {
        title: document.title,
        buttonTexts: buttons.map(btn => btn.textContent?.trim()).filter(Boolean),
        hasProviderSection: !!document.querySelector('[data-provider-config]'),
        allText: document.body.textContent?.substring(0, 500)
      };
    });
    
    console.log('Page content:', pageContent);
    
    if (pageContent.buttonTexts.length === 0) {
      console.log('No buttons found, page may not have loaded correctly');
      return;
    }
    
    // Find test connection button
    const hasTestButton = pageContent.buttonTexts.some(text => text.includes('Test Connection'));
    if (!hasTestButton) {
      console.log('No Test Connection button found. Available buttons:', pageContent.buttonTexts);
      return;
    }
    
    // Take screenshot of initial state
    await page.screenshot({ path: 'before-test.png', fullPage: true });
    console.log('Took screenshot of initial state');
    
    // Find and click test connection button
    const testButton = await page.evaluateHandle(() => {
      const buttons = Array.from(document.querySelectorAll('button'));
      return buttons.find(btn => btn.textContent?.includes('Test Connection'));
    });
    console.log('Found test connection button');
    
    await testButton.click();
    console.log('Clicked test connection button');
    
    // Wait for test to complete (either success or failure) 
    await new Promise(resolve => setTimeout(resolve, 8000));
    
    // Take screenshot after test
    await page.screenshot({ path: 'after-test.png', fullPage: true });
    console.log('Took screenshot after test');
    
    // Check if status badge shows "Connected" and model selection is enabled
    const results = await page.evaluate(() => {
      const badges = document.querySelectorAll('[class*="badge"], [class*="Badge"]');
      let statusBadge = null;
      for (const badge of badges) {
        if (badge.textContent.includes('Connected') || badge.textContent.includes('Failed') || badge.textContent.includes('Not Tested')) {
          statusBadge = badge.textContent;
          break;
        }
      }
      
      // Check if model selection selects are enabled
      const modelSelects = document.querySelectorAll('select, [role="combobox"]');
      let modelSelectsEnabled = false;
      for (const select of modelSelects) {
        if (!select.disabled && !select.hasAttribute('aria-disabled')) {
          modelSelectsEnabled = true;
          break;
        }
      }
      
      return { statusBadge, modelSelectsEnabled };
    });
    
    console.log('Status badge text:', results.statusBadge);
    console.log('Model selects enabled:', results.modelSelectsEnabled);
    
    if (results.statusBadge && results.statusBadge.includes('Connected')) {
      console.log('✅ SUCCESS: Status badge shows "Connected" after test!');
      if (results.modelSelectsEnabled) {
        console.log('✅ SUCCESS: Model selection is now enabled!');
      } else {
        console.log('❌ ISSUE: Model selection is still disabled');
      }
    } else {
      console.log('❌ ISSUE: Status badge does not show "Connected". Current text:', results.statusBadge);
    }
    
  } catch (error) {
    console.error('Test failed:', error);
  } finally {
    await browser.close();
  }
}

testProviderStatusFix();