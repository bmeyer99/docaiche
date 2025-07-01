const fetch = require('node-fetch');

async function testAPIFlow() {
  console.log('Testing API flow for providers page...\n');
  
  try {
    // 1. Test providers endpoint
    console.log('1. Fetching providers from API...');
    const providersRes = await fetch('http://localhost:4080/api/v1/providers');
    const providers = await providersRes.json();
    console.log(`   ✓ Found ${providers.length} providers`);
    
    // Group by category
    const byCategory = {
      local: providers.filter(p => p.category === 'local'),
      cloud: providers.filter(p => p.category === 'cloud'),
      enterprise: providers.filter(p => p.category === 'enterprise')
    };
    
    console.log(`   - Local: ${byCategory.local.length} providers`);
    console.log(`   - Cloud: ${byCategory.cloud.length} providers`);
    console.log(`   - Enterprise: ${byCategory.enterprise.length} providers`);
    
    // 2. Test model selection
    console.log('\n2. Fetching model selection...');
    const configRes = await fetch('http://localhost:4080/api/v1/config');
    const config = await configRes.json();
    const modelSelection = config.items?.find(item => item.key === 'ai.model_selection');
    
    if (modelSelection) {
      console.log('   ✓ Model selection found:');
      console.log(`   - Text: ${modelSelection.value.textGeneration.provider} / ${modelSelection.value.textGeneration.model}`);
      console.log(`   - Embeddings: ${modelSelection.value.embeddings.provider} / ${modelSelection.value.embeddings.model}`);
      console.log(`   - Shared provider: ${modelSelection.value.sharedProvider}`);
    } else {
      console.log('   ⚠ No model selection found');
    }
    
    // 3. Show cloud providers details
    console.log('\n3. Cloud providers details:');
    byCategory.cloud.forEach(provider => {
      console.log(`   - ${provider.name} (${provider.id})`);
      console.log(`     Status: ${provider.status}`);
      console.log(`     Configured: ${provider.configured}`);
      console.log(`     Enabled: ${provider.enabled}`);
    });
    
  } catch (error) {
    console.error('Error:', error.message);
  }
}

testAPIFlow();