const puppeteer = require('puppeteer');

async function testDetailedErrors() {
  console.log('🔍 Testing detailed validation errors...');
  
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
  });
  
  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 1280, height: 720 });
    
    // Capture all console messages with more detail
    page.on('console', msg => {
      const text = msg.text();
      const type = msg.type();
      
      if (text.includes('Invalid provider configuration in response')) {
        console.log(`🚨 VALIDATION ERROR: ${text} (type: ${type})`);
        
        // Try to get more details from the error object
        const args = msg.args();
        Promise.all(args.map(arg => arg.jsonValue().catch(() => 'Unable to serialize')))
          .then(values => {
            console.log('   Error details:', values);
          });
      } else if (type === 'error' || text.includes('error') || text.includes('Error')) {
        console.log(`❌ ERROR: ${text} (type: ${type})`);
      }
    });
    
    // Listen for network requests
    page.on('response', response => {
      const url = response.url();
      if (url.includes('/api/v1/providers') && !url.includes('/config')) {
        console.log(`📡 API CALL: ${response.status()} ${url}`);
      }
    });
    
    console.log('📋 Navigate to providers page...');
    await page.goto('http://localhost:4080/dashboard/providers', { 
      waitUntil: 'networkidle2',
      timeout: 30000 
    });
    
    await page.waitForFunction(() => {
      return document.body.innerText.includes('AI Provider Configuration');
    }, { timeout: 15000 });
    
    console.log('✅ Page loaded');
    
    // Wait to see all validation errors
    await new Promise(resolve => setTimeout(resolve, 3000));
    
  } catch (error) {
    console.error('💥 Test failed:', error.message);
  } finally {
    await browser.close();
    console.log('🔚 Browser closed');
  }
}

testDetailedErrors().catch(console.error);