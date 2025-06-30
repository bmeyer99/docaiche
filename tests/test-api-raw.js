const puppeteer = require('puppeteer');

async function testAPIRaw() {
  console.log('🔍 Testing raw API response...');
  
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
  });
  
  try {
    const page = await browser.newPage();
    
    // First navigate to the admin UI to establish context
    await page.goto('http://localhost:4080/dashboard/providers', { 
      waitUntil: 'networkidle2',
      timeout: 30000 
    });
    
    const response = await page.evaluate(async () => {
      try {
        const res = await fetch('/api/v1/providers');
        const data = await res.json();
        return { success: true, data, status: res.status };
      } catch (error) {
        return { success: false, error: error.message };
      }
    });
    
    if (response.success) {
      console.log('✅ Raw API Response:');
      console.log('Status:', response.status);
      console.log('Data structure:', JSON.stringify(response.data, null, 2));
    } else {
      console.log('❌ API Error:', response.error);
    }
    
  } catch (error) {
    console.error('💥 Test failed:', error.message);
  } finally {
    await browser.close();
  }
}

testAPIRaw().catch(console.error);