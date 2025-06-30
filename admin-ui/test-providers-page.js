const puppeteer = require('puppeteer');
const fs = require('fs');

async function testProvidersPage() {
  console.log('Starting Providers Page E2E Test...');
  
  let browser;
  let page;
  const baseUrl = 'http://localhost:3000';
  const results = [];

  try {
    // Launch browser
    browser = await puppeteer.launch({
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    
    page = await browser.newPage();
    await page.setViewport({ width: 1280, height: 800 });
    
    // Test 1: Load the page
    console.log('\n📝 Test 1: Loading providers page...');
    try {
      await page.goto(`${baseUrl}/dashboard/providers-new`, { 
        waitUntil: 'networkidle2',
        timeout: 30000 
      });
      
      // Check if redirected to login
      const currentUrl = page.url();
      if (currentUrl.includes('/login')) {
        console.log('❌ Redirected to login page - authentication required');
        results.push({ test: 'Page Load', status: 'BLOCKED', reason: 'Authentication required' });
      } else {
        console.log('✅ Page loaded successfully');
        results.push({ test: 'Page Load', status: 'PASS' });
      }
    } catch (error) {
      console.log(`❌ Failed to load page: ${error.message}`);
      results.push({ test: 'Page Load', status: 'FAIL', error: error.message });
    }
    
    // Test 2: Check page structure
    console.log('\n📝 Test 2: Checking page structure...');
    try {
      if (!page.url().includes('/login')) {
        const title = await page.$('h1');
        if (title) {
          const titleText = await title.evaluate(el => el.textContent);
          console.log(`✅ Found page title: "${titleText}"`);
          results.push({ test: 'Page Structure', status: 'PASS', details: titleText });
        } else {
          console.log('❌ Page title not found');
          results.push({ test: 'Page Structure', status: 'FAIL', reason: 'Title not found' });
        }
      }
    } catch (error) {
      console.log(`❌ Failed to check structure: ${error.message}`);
      results.push({ test: 'Page Structure', status: 'FAIL', error: error.message });
    }
    
    // Take a screenshot
    console.log('\n📸 Taking screenshot...');
    try {
      await page.screenshot({ 
        path: `screenshot-providers-page-${Date.now()}.png`,
        fullPage: true 
      });
      console.log('✅ Screenshot saved');
    } catch (error) {
      console.log(`❌ Failed to take screenshot: ${error.message}`);
    }
    
  } catch (error) {
    console.error('Fatal error:', error);
    results.push({ test: 'General', status: 'ERROR', error: error.message });
  } finally {
    if (browser) {
      await browser.close();
    }
  }
  
  // Generate report
  console.log('\n📊 Test Summary:');
  console.log('================');
  results.forEach(result => {
    const icon = result.status === 'PASS' ? '✅' : result.status === 'BLOCKED' ? '🚫' : '❌';
    console.log(`${icon} ${result.test}: ${result.status}`);
    if (result.reason) console.log(`   Reason: ${result.reason}`);
    if (result.error) console.log(`   Error: ${result.error}`);
    if (result.details) console.log(`   Details: ${result.details}`);
  });
  
  // Save results to file
  const report = {
    timestamp: new Date().toISOString(),
    url: baseUrl,
    results: results
  };
  
  fs.writeFileSync(
    `providers-test-report-${Date.now()}.json`,
    JSON.stringify(report, null, 2)
  );
  
  console.log('\n✅ Test report saved');
}

// Run the test
testProvidersPage().catch(console.error);