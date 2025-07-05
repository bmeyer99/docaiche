/**
 * Debug script for Vector tab issues
 * Run this in the browser console to debug state and API issues
 */

// Test 1: Check if the config context is working
console.log("=== Debug Vector Tab Issues ===");

// Check if React DevTools are available
if (typeof React !== 'undefined') {
  console.log("✓ React is available");
} else {
  console.log("✗ React not available in global scope");
}

// Test 2: Check API endpoints
async function testAPIEndpoints() {
  console.log("\n=== Testing API Endpoints ===");
  
  try {
    // Test providers endpoint
    const providersResponse = await fetch('/api/v1/providers');
    const providers = await providersResponse.json();
    console.log("✓ Providers API:", providers.length, "providers found");
    
    // Check Ollama specifically
    const ollama = providers.find(p => p.id === 'ollama');
    if (ollama) {
      console.log("✓ Ollama found:", {
        status: ollama.status,
        configured: ollama.configured,
        models: ollama.models?.length || 0,
        supports_embedding: ollama.supports_embedding
      });
    } else {
      console.log("✗ Ollama not found in providers");
    }
    
    // Test config endpoint
    const configResponse = await fetch('/api/v1/config');
    const config = await configResponse.json();
    console.log("✓ Config API:", config.items?.length || 0, "config items");
    
    // Test Weaviate config
    const weaviateResponse = await fetch('/api/v1/admin/search/weaviate/config');
    const weaviateConfig = await weaviateResponse.json();
    console.log("✓ Weaviate Config:", weaviateConfig);
    
  } catch (error) {
    console.error("✗ API Error:", error);
  }
}

// Test 3: Check for JavaScript errors
function checkConsoleErrors() {
  console.log("\n=== Checking Console Errors ===");
  
  // Override console.error to capture errors
  const originalError = console.error;
  const errors = [];
  
  console.error = function(...args) {
    errors.push(args);
    originalError.apply(console, args);
  };
  
  // Return the error checker
  return function() {
    console.error = originalError;
    if (errors.length > 0) {
      console.log("✗ Console errors found:", errors.length);
      errors.forEach(error => console.log("  -", error));
    } else {
      console.log("✓ No console errors captured");
    }
  };
}

// Test 4: Check local storage and session storage
function checkStorage() {
  console.log("\n=== Checking Storage ===");
  
  const localStorage = window.localStorage;
  const sessionStorage = window.sessionStorage;
  
  console.log("LocalStorage items:", localStorage.length);
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i);
    console.log("  -", key, ":", localStorage.getItem(key)?.substring(0, 100));
  }
  
  console.log("SessionStorage items:", sessionStorage.length);
  for (let i = 0; i < sessionStorage.length; i++) {
    const key = sessionStorage.key(i);
    console.log("  -", key, ":", sessionStorage.getItem(key)?.substring(0, 100));
  }
}

// Test 5: Check for specific React contexts
function checkReactContexts() {
  console.log("\n=== Checking React Contexts ===");
  
  // Try to find React contexts in the DOM
  const reactFiberKeys = Object.keys(document.body).filter(key => key.startsWith('__reactFiber'));
  console.log("React fiber keys found:", reactFiberKeys.length);
  
  // Check for specific provider components
  const providerElements = document.querySelectorAll('[data-testid*="provider"], [class*="provider"]');
  console.log("Provider elements found:", providerElements.length);
}

// Run all tests
async function runAllTests() {
  const errorChecker = checkConsoleErrors();
  
  await testAPIEndpoints();
  checkStorage();
  checkReactContexts();
  
  errorChecker();
  
  console.log("\n=== Debug Complete ===");
}

// Instructions for user
console.log(`
Instructions:
1. Run: await runAllTests()
2. Click the Vector tab
3. Check the console output for errors
4. If errors appear, run: checkConsoleErrors() again
`);

// Auto-run basic tests
runAllTests();