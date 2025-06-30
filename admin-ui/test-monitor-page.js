const puppeteer = require('puppeteer');

async function monitorPage(url, duration = 15) {
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  
  const page = await browser.newPage();
  
  // Enable request interception
  await page.setRequestInterception(true);
  
  console.log(`\n🔍 Monitoring ${url} for ${duration} seconds...\n`);
  
  const requests = [];
  const errors = [];
  
  // Track all network requests
  page.on('request', (request) => {
    const url = request.url();
    const method = request.method();
    const resourceType = request.resourceType();
    
    // Filter out static assets for cleaner output
    if (!['image', 'stylesheet', 'font'].includes(resourceType)) {
      requests.push({
        timestamp: new Date().toISOString(),
        method,
        url,
        type: resourceType
      });
      
      console.log(`📡 ${method} ${url}`);
    }
    
    request.continue();
  });
  
  // Track responses
  page.on('response', (response) => {
    const status = response.status();
    const url = response.url();
    
    if (status >= 400 && !url.includes('favicon')) {
      console.log(`❌ Error ${status}: ${url}`);
      errors.push({
        timestamp: new Date().toISOString(),
        status,
        url
      });
    }
  });
  
  // Track console logs
  page.on('console', (msg) => {
    const type = msg.type();
    const text = msg.text();
    
    if (type === 'error') {
      console.log(`🔴 Console Error: ${text}`);
    } else if (type === 'warning') {
      console.log(`🟡 Console Warning: ${text}`);
    } else if (text.includes('API') || text.includes('fetch') || text.includes('model')) {
      console.log(`📝 Console: ${text}`);
    }
  });
  
  // Track page errors
  page.on('pageerror', (error) => {
    console.log(`💥 Page Error: ${error.message}`);
    errors.push({
      timestamp: new Date().toISOString(),
      type: 'page_error',
      message: error.message
    });
  });
  
  try {
    // Navigate to the page
    await page.goto(url, { 
      waitUntil: 'networkidle2',
      timeout: 30000 
    });
    
    console.log('\n✅ Page loaded successfully\n');
    
    // Wait for the specified duration
    await new Promise(resolve => setTimeout(resolve, duration * 1000));
    
  } catch (error) {
    console.error(`\n❌ Failed to load page: ${error.message}\n`);
  }
  
  // Summary
  console.log('\n📊 Summary:');
  console.log(`Total Requests: ${requests.length}`);
  console.log(`Errors: ${errors.length}`);
  
  if (errors.length > 0) {
    console.log('\n🔴 Errors detected:');
    errors.forEach(err => {
      console.log(`  - ${err.status || err.type}: ${err.url || err.message}`);
    });
  }
  
  // API calls summary
  const apiCalls = requests.filter(r => r.url.includes('/api/'));
  if (apiCalls.length > 0) {
    console.log(`\n📡 API Calls (${apiCalls.length}):`);
    apiCalls.forEach(call => {
      console.log(`  - ${call.method} ${call.url}`);
    });
  }
  
  await browser.close();
}

// Parse command line arguments
const args = process.argv.slice(2);
const url = args[0] || 'http://localhost:3000/dashboard/providers';
const duration = parseInt(args[1]) || 15;

if (!url.startsWith('http')) {
  console.error('Please provide a valid URL starting with http:// or https://');
  process.exit(1);
}

monitorPage(url, duration).catch(console.error);