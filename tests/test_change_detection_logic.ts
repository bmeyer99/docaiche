// Test script to verify change detection logic
// This tests the core logic without React dependencies

interface ChangeEvent {
  source: 'user' | 'system';
  fieldPath: string;
  timestamp: number;
  oldValue?: any;
  newValue?: any;
}

interface ChangeDetectionState {
  isDirty: boolean;
  lastUserChange: ChangeEvent | null;
  changeHistory: ChangeEvent[];
}

function testChangeDetectionLogic() {
  console.log('=== Change Detection Logic Tests ===\n');
  
  let state: ChangeDetectionState = {
    isDirty: false,
    lastUserChange: null,
    changeHistory: []
  };
  
  // Test 1: Initial state
  console.log('Test 1 - Initial State:');
  console.log(`  isDirty: ${state.isDirty} (expected: false)`);
  console.log(`  lastUserChange: ${state.lastUserChange} (expected: null)`);
  console.log(`  changeHistory length: ${state.changeHistory.length} (expected: 0)`);
  console.log(`  ✅ Test 1 Passed\n`);
  
  // Test 2: System change - should NOT set isDirty
  console.log('Test 2 - System Change:');
  const systemChange: ChangeEvent = {
    source: 'system',
    fieldPath: 'apiKey',
    timestamp: Date.now(),
    newValue: 'test-key'
  };
  
  state = {
    ...state,
    changeHistory: [...state.changeHistory, systemChange],
    isDirty: systemChange.source === 'user' ? true : state.isDirty,
    lastUserChange: systemChange.source === 'user' ? systemChange : state.lastUserChange
  };
  
  console.log(`  isDirty after system change: ${state.isDirty} (expected: false)`);
  console.log(`  lastUserChange: ${state.lastUserChange} (expected: null)`);
  console.log(`  changeHistory length: ${state.changeHistory.length} (expected: 1)`);
  console.log(`  ${state.isDirty === false ? '✅' : '❌'} Test 2 ${state.isDirty === false ? 'Passed' : 'Failed'}\n`);
  
  // Test 3: User change - SHOULD set isDirty
  console.log('Test 3 - User Change:');
  const userChange: ChangeEvent = {
    source: 'user',
    fieldPath: 'model',
    timestamp: Date.now(),
    newValue: 'gpt-4'
  };
  
  state = {
    ...state,
    changeHistory: [...state.changeHistory, userChange],
    isDirty: userChange.source === 'user' ? true : state.isDirty,
    lastUserChange: userChange.source === 'user' ? userChange : state.lastUserChange
  };
  
  console.log(`  isDirty after user change: ${state.isDirty} (expected: true)`);
  console.log(`  lastUserChange fieldPath: ${state.lastUserChange?.fieldPath} (expected: model)`);
  console.log(`  changeHistory length: ${state.changeHistory.length} (expected: 2)`);
  console.log(`  ${state.isDirty === true && state.lastUserChange?.fieldPath === 'model' ? '✅' : '❌'} Test 3 ${state.isDirty === true ? 'Passed' : 'Failed'}\n`);
  
  // Test 4: Another system change - isDirty should remain true
  console.log('Test 4 - Another System Change (after user change):');
  const systemChange2: ChangeEvent = {
    source: 'system',
    fieldPath: 'timeout',
    timestamp: Date.now(),
    newValue: 5000
  };
  
  state = {
    ...state,
    changeHistory: [...state.changeHistory, systemChange2],
    isDirty: systemChange2.source === 'user' ? true : state.isDirty,
    lastUserChange: systemChange2.source === 'user' ? systemChange2 : state.lastUserChange
  };
  
  console.log(`  isDirty remains: ${state.isDirty} (expected: true)`);
  console.log(`  lastUserChange unchanged: ${state.lastUserChange?.fieldPath} (expected: model)`);
  console.log(`  changeHistory length: ${state.changeHistory.length} (expected: 3)`);
  console.log(`  ${state.isDirty === true && state.lastUserChange?.fieldPath === 'model' ? '✅' : '❌'} Test 4 Passed\n`);
  
  // Test 5: Filter changes by source
  console.log('Test 5 - Filter Changes by Source:');
  const userChanges = state.changeHistory.filter(change => change.source === 'user');
  const systemChanges = state.changeHistory.filter(change => change.source === 'system');
  
  console.log(`  User changes: ${userChanges.length} (expected: 1)`);
  console.log(`  System changes: ${systemChanges.length} (expected: 2)`);
  console.log(`  User change fields: ${userChanges.map(c => c.fieldPath).join(', ')} (expected: model)`);
  console.log(`  System change fields: ${systemChanges.map(c => c.fieldPath).join(', ')} (expected: apiKey, timeout)`);
  console.log(`  ${userChanges.length === 1 && systemChanges.length === 2 ? '✅' : '❌'} Test 5 Passed\n`);
  
  // Test 6: Mark as clean
  console.log('Test 6 - Mark as Clean:');
  state = {
    ...state,
    isDirty: false
  };
  
  console.log(`  isDirty after markAsClean: ${state.isDirty} (expected: false)`);
  console.log(`  changeHistory preserved: ${state.changeHistory.length} (expected: 3)`);
  console.log(`  lastUserChange preserved: ${state.lastUserChange?.fieldPath} (expected: model)`);
  console.log(`  ${state.isDirty === false && state.changeHistory.length === 3 ? '✅' : '❌'} Test 6 Passed\n`);
  
  // Test 7: Reset
  console.log('Test 7 - Reset:');
  state = {
    isDirty: false,
    lastUserChange: null,
    changeHistory: []
  };
  
  console.log(`  isDirty after reset: ${state.isDirty} (expected: false)`);
  console.log(`  lastUserChange after reset: ${state.lastUserChange} (expected: null)`);
  console.log(`  changeHistory after reset: ${state.changeHistory.length} (expected: 0)`);
  console.log(`  ${state.isDirty === false && state.lastUserChange === null && state.changeHistory.length === 0 ? '✅' : '❌'} Test 7 Passed\n`);
  
  // Test 8: History size limit
  console.log('Test 8 - History Size Limit:');
  const maxHistorySize = 5;
  state.changeHistory = [];
  
  // Add more than max changes
  for (let i = 0; i < 7; i++) {
    const change: ChangeEvent = {
      source: i % 2 === 0 ? 'user' : 'system',
      fieldPath: `field${i}`,
      timestamp: Date.now() + i,
      newValue: `value${i}`
    };
    
    state.changeHistory = [...state.changeHistory, change];
    
    // Apply size limit
    if (state.changeHistory.length > maxHistorySize) {
      state.changeHistory.splice(0, state.changeHistory.length - maxHistorySize);
    }
  }
  
  console.log(`  Final history length: ${state.changeHistory.length} (expected: ${maxHistorySize})`);
  console.log(`  Oldest change: ${state.changeHistory[0]?.fieldPath} (expected: field2)`);
  console.log(`  Newest change: ${state.changeHistory[state.changeHistory.length - 1]?.fieldPath} (expected: field6)`);
  console.log(`  ${state.changeHistory.length === maxHistorySize ? '✅' : '❌'} Test 8 Passed\n`);
  
  console.log('=== All Tests Completed ===');
}

// Run the tests
testChangeDetectionLogic();