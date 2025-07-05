import React, { useState, useEffect } from 'react';
import { useFormChangeDetection, createFieldUpdaters } from './admin-ui/src/features/search-config/hooks/use-change-detection';

// Test component to verify change detection functionality
function TestChangeDetection() {
  const [config, setConfig] = useState({ apiKey: '', model: '' });
  const [testResults, setTestResults] = useState<string[]>([]);
  
  const changeDetection = useFormChangeDetection({
    onUserChange: (event) => {
      setTestResults(prev => [...prev, `User change detected: ${event.fieldPath} = ${event.newValue}`]);
    },
    onSystemChange: (event) => {
      setTestResults(prev => [...prev, `System change detected: ${event.fieldPath} = ${event.newValue}`]);
    }
  });
  
  // Create wrapped updaters
  const { userUpdaters, systemUpdaters } = createFieldUpdaters(changeDetection, {
    apiKey: (value: string) => setConfig(prev => ({ ...prev, apiKey: value })),
    model: (value: string) => setConfig(prev => ({ ...prev, model: value }))
  });
  
  // Run tests on mount
  useEffect(() => {
    runTests();
  }, []);
  
  const runTests = async () => {
    const results: string[] = [];
    
    // Test 1: Initial state
    results.push(`Test 1 - Initial isDirty: ${changeDetection.isDirty} (should be false)`);
    results.push(`Test 1 - Initial lastUserChange: ${changeDetection.lastUserChange} (should be null)`);
    results.push(`Test 1 - Initial changeHistory length: ${changeDetection.changeHistory.length} (should be 0)`);
    
    // Test 2: System update (shouldn't mark as dirty)
    systemUpdaters.apiKey('test-api-key');
    await new Promise(resolve => setTimeout(resolve, 100));
    results.push(`Test 2 - After system update isDirty: ${changeDetection.isDirty} (should be false)`);
    results.push(`Test 2 - changeHistory length: ${changeDetection.changeHistory.length} (should be 1)`);
    
    // Test 3: User update (should mark as dirty)
    userUpdaters.model('gpt-4');
    await new Promise(resolve => setTimeout(resolve, 100));
    results.push(`Test 3 - After user update isDirty: ${changeDetection.isDirty} (should be true)`);
    results.push(`Test 3 - lastUserChange fieldPath: ${changeDetection.lastUserChange?.fieldPath} (should be 'model')`);
    results.push(`Test 3 - changeHistory length: ${changeDetection.changeHistory.length} (should be 2)`);
    
    // Test 4: Check hasUserChanges
    results.push(`Test 4 - hasUserChanges: ${changeDetection.hasUserChanges()} (should be true)`);
    
    // Test 5: Get changes by source
    const userChanges = changeDetection.getChangesBySource('user');
    const systemChanges = changeDetection.getChangesBySource('system');
    results.push(`Test 5 - User changes count: ${userChanges.length} (should be 1)`);
    results.push(`Test 5 - System changes count: ${systemChanges.length} (should be 1)`);
    
    // Test 6: Get changes by field
    const apiKeyChanges = changeDetection.getChangesByField('apiKey');
    const modelChanges = changeDetection.getChangesByField('model');
    results.push(`Test 6 - apiKey changes count: ${apiKeyChanges.length} (should be 1)`);
    results.push(`Test 6 - model changes count: ${modelChanges.length} (should be 1)`);
    
    // Test 7: Mark as clean
    changeDetection.markAsClean();
    await new Promise(resolve => setTimeout(resolve, 100));
    results.push(`Test 7 - After markAsClean isDirty: ${changeDetection.isDirty} (should be false)`);
    results.push(`Test 7 - changeHistory still exists: ${changeDetection.changeHistory.length} (should be 2)`);
    
    // Test 8: Reset
    changeDetection.reset();
    await new Promise(resolve => setTimeout(resolve, 100));
    results.push(`Test 8 - After reset isDirty: ${changeDetection.isDirty} (should be false)`);
    results.push(`Test 8 - After reset changeHistory: ${changeDetection.changeHistory.length} (should be 0)`);
    results.push(`Test 8 - After reset lastUserChange: ${changeDetection.lastUserChange} (should be null)`);
    
    // Test 9: Direct trackChange calls
    changeDetection.trackChange('customField', 'newValue', 'oldValue', 'user');
    await new Promise(resolve => setTimeout(resolve, 100));
    results.push(`Test 9 - After direct user trackChange isDirty: ${changeDetection.isDirty} (should be true)`);
    
    changeDetection.markAsClean();
    changeDetection.trackChange('customField2', 'newValue2', 'oldValue2', 'system');
    await new Promise(resolve => setTimeout(resolve, 100));
    results.push(`Test 9 - After direct system trackChange isDirty: ${changeDetection.isDirty} (should be false)`);
    
    // Test 10: Form integration features
    results.push(`Test 10 - canSave: ${changeDetection.canSave} (should match isDirty)`);
    results.push(`Test 10 - hasUnsavedChanges: ${changeDetection.hasUnsavedChanges} (should match isDirty)`);
    
    setTestResults(results);
  };
  
  return (
    <div>
      <h2>Change Detection Test Results</h2>
      <div>
        <h3>Current State:</h3>
        <p>Config: {JSON.stringify(config)}</p>
        <p>isDirty: {String(changeDetection.isDirty)}</p>
        <p>canSave: {String(changeDetection.canSave)}</p>
        <p>changeHistory length: {changeDetection.changeHistory.length}</p>
      </div>
      <div>
        <h3>Test Results:</h3>
        {testResults.map((result, index) => (
          <p key={index}>{result}</p>
        ))}
      </div>
    </div>
  );
}

export default TestChangeDetection;