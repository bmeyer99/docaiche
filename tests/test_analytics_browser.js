const puppeteer = require('puppeteer');

async function testAnalyticsPage() {
  console.log('🚀 Starting browser test for analytics page...');
  
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  
  try {
    const page = await browser.newPage();
    
    // Enable console logging
    page.on('console', msg => {
      const type = msg.type();
      const text = msg.text();
      if (type === 'error') {
        console.error('❌ Browser console error:', text);
      } else if (text.includes('Analytics') || text.includes('API endpoint')) {
        console.log(`📊 Browser console [${type}]:`, text);
      }
    });
    
    // Navigate to analytics page
    console.log('📍 Navigating to http://localhost:4080/dashboard/analytics');
    await page.goto('http://localhost:4080/dashboard/analytics', {
      waitUntil: 'networkidle2',
      timeout: 30000
    });
    
    // Wait for the page to load
    console.log('⏳ Waiting for analytics content to load...');
    await page.waitForTimeout(5000); // Give WebSocket time to connect
    
    // Check if API Endpoints section exists
    console.log('🔍 Checking for API Endpoints section...');
    const apiEndpointsSection = await page.evaluate(() => {
      const elements = Array.from(document.querySelectorAll('h3'));
      const apiEndpointsHeader = elements.find(el => el.textContent.includes('API Endpoints'));
      if (apiEndpointsHeader) {
        const parent = apiEndpointsHeader.closest('div.bg-muted\\/30');
        if (parent) {
          // Get all endpoint elements
          const endpoints = parent.querySelectorAll('div[class*="rounded-md"][class*="bg-muted"]');
          return {
            found: true,
            count: endpoints.length,
            endpoints: Array.from(endpoints).map(ep => {
              const text = ep.textContent;
              const classes = ep.className;
              return { text, hasError: classes.includes('text-red') || text.includes('Error') };
            })
          };
        }
      }
      return { found: false, count: 0, endpoints: [] };
    });
    
    if (apiEndpointsSection.found) {
      console.log(`✅ API Endpoints section found with ${apiEndpointsSection.count} endpoints`);
      apiEndpointsSection.endpoints.forEach((ep, i) => {
        console.log(`   ${i + 1}. ${ep.text} ${ep.hasError ? '❌ (Error)' : '✅'}`);
      });
    } else {
      console.log('❌ API Endpoints section NOT FOUND');
    }
    
    // Check system health data
    console.log('\n🔍 Checking system health data...');
    const systemHealthGroups = await page.evaluate(() => {
      const groups = [];
      const groupDivs = document.querySelectorAll('div.space-y-3 > div');
      
      groupDivs.forEach(div => {
        const titleEl = div.querySelector('h3');
        if (titleEl) {
          const title = titleEl.textContent;
          const services = div.querySelectorAll('div.grid > div[class*="rounded-lg"]');
          groups.push({
            title,
            serviceCount: services.length
          });
        }
      });
      
      return groups;
    });
    
    console.log('📊 System Health Groups:');
    systemHealthGroups.forEach(group => {
      console.log(`   - ${group.title}: ${group.serviceCount} services`);
    });
    
    // Take a screenshot
    await page.screenshot({ 
      path: 'analytics-page.png',
      fullPage: true 
    });
    console.log('📸 Screenshot saved as analytics-page.png');
    
  } catch (error) {
    console.error('❌ Test failed:', error);
  } finally {
    await browser.close();
  }
}

// Run the test
testAnalyticsPage().catch(console.error);