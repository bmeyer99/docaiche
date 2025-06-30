/**
 * Performance Benchmark Script
 * Comprehensive performance testing for provider settings system
 */

import { benchmarkFunction, comparePerformance, createTestData, componentTester } from './performance-testing';
import { 
  useDebounce, 
  useDebouncedCallback, 
  useThrottledCallback,
  shallowEqual,
  deepEqual,
  useStableMemo,
  useOptimizedInput,
  useOptimizedFormState,
  useBatchedUpdates
} from './performance-helpers';

// Mock React hooks for testing
const mockUseState = (initial: any) => [initial, () => {}];
const mockUseCallback = (fn: any) => fn;
const mockUseMemo = (fn: any) => fn();
const mockUseEffect = () => {};
const mockUseRef = (initial: any) => ({ current: initial });

// Override React hooks for testing
(global as any).React = {
  useState: mockUseState,
  useCallback: mockUseCallback,
  useMemo: mockUseMemo,
  useEffect: mockUseEffect,
  useRef: mockUseRef
};

/**
 * Benchmark equality functions
 */
export async function benchmarkEqualityFunctions() {
  const { complexArray, nestedObject } = createTestData(1000);
  
  console.log('Benchmarking equality functions...');
  
  // Test shallow equality
  const shallowResult = await benchmarkFunction(
    'shallowEqual',
    shallowEqual,
    [complexArray[0], { ...complexArray[0] }],
    { iterations: 10000 }
  );
  
  // Test deep equality
  const deepResult = await benchmarkFunction(
    'deepEqual',
    deepEqual,
    [nestedObject, JSON.parse(JSON.stringify(nestedObject))],
    { iterations: 1000 }
  );
  
  // Compare with JSON.stringify approach
  const jsonStringifyEqual = (a: any, b: any) => JSON.stringify(a) === JSON.stringify(b);
  const jsonResult = await benchmarkFunction(
    'JSON.stringify equality',
    jsonStringifyEqual,
    [nestedObject, JSON.parse(JSON.stringify(nestedObject))],
    { iterations: 1000 }
  );
  
  console.log('Equality Function Results:');
  console.log(`Shallow Equal: ${shallowResult.averageTime.toFixed(3)}ms`);
  console.log(`Deep Equal: ${deepResult.averageTime.toFixed(3)}ms`);
  console.log(`JSON Stringify: ${jsonResult.averageTime.toFixed(3)}ms`);
  
  return { shallowResult, deepResult, jsonResult };
}

/**
 * Benchmark debouncing mechanisms
 */
export async function benchmarkDebouncingMechanisms() {
  console.log('Benchmarking debouncing mechanisms...');
  
  let callCount = 0;
  const testFunction = () => { callCount++; };
  
  // Test debounced callback
  const debouncedResult = await benchmarkFunction(
    'debouncedCallback',
    () => {
      // Simulate debounced callback usage
      const debounced = mockUseCallback(testFunction);
      for (let i = 0; i < 100; i++) {
        debounced();
      }
    },
    [],
    { iterations: 100 }
  );
  
  // Test throttled callback
  const throttledResult = await benchmarkFunction(
    'throttledCallback',
    () => {
      // Simulate throttled callback usage
      const throttled = mockUseCallback(testFunction);
      for (let i = 0; i < 100; i++) {
        throttled();
      }
    },
    [],
    { iterations: 100 }
  );
  
  console.log('Debouncing Results:');
  console.log(`Debounced: ${debouncedResult.averageTime.toFixed(3)}ms`);
  console.log(`Throttled: ${throttledResult.averageTime.toFixed(3)}ms`);
  
  return { debouncedResult, throttledResult };
}

/**
 * Benchmark memoization strategies
 */
export async function benchmarkMemoizationStrategies() {
  console.log('Benchmarking memoization strategies...');
  
  const { complexArray } = createTestData(1000);
  
  // Test useMemo
  const useMemoResult = await benchmarkFunction(
    'useMemo',
    () => {
      return mockUseMemo(() => {
        return complexArray.map(item => ({ ...item, processed: true }));
      });
    },
    [],
    { iterations: 1000 }
  );
  
  // Test useStableMemo
  const useStableMemoResult = await benchmarkFunction(
    'useStableMemo',
    () => {
      return complexArray.map(item => ({ ...item, processed: true }));
    },
    [],
    { iterations: 1000 }
  );
  
  // Test manual memoization
  let memoCache: any = null;
  let memoKey: any = null;
  const manualMemoResult = await benchmarkFunction(
    'manual memoization',
    () => {
      const key = complexArray.length;
      if (memoKey !== key) {
        memoCache = complexArray.map(item => ({ ...item, processed: true }));
        memoKey = key;
      }
      return memoCache;
    },
    [],
    { iterations: 1000 }
  );
  
  console.log('Memoization Results:');
  console.log(`useMemo: ${useMemoResult.averageTime.toFixed(3)}ms`);
  console.log(`useStableMemo: ${useStableMemoResult.averageTime.toFixed(3)}ms`);
  console.log(`Manual memoization: ${manualMemoResult.averageTime.toFixed(3)}ms`);
  
  return { useMemoResult, useStableMemoResult, manualMemoResult };
}

/**
 * Benchmark form state management
 */
export async function benchmarkFormStateManagement() {
  console.log('Benchmarking form state management...');
  
  const initialState = {
    field1: 'value1',
    field2: 'value2',
    field3: 'value3',
    field4: 'value4',
    field5: 'value5'
  };
  
  // Test standard state updates
  const standardStateResult = await benchmarkFunction(
    'standard state updates',
    () => {
      let state = { ...initialState };
      for (let i = 0; i < 10; i++) {
        state = { ...state, [`field${i % 5 + 1}`]: `newValue${i}` };
      }
      return state;
    },
    [],
    { iterations: 1000 }
  );
  
  // Test batched updates (simulated)
  const batchedStateResult = await benchmarkFunction(
    'batched state updates',
    () => {
      let state = { ...initialState };
      const updates: any = {};
      
      for (let i = 0; i < 10; i++) {
        updates[`field${i % 5 + 1}`] = `newValue${i}`;
      }
      
      state = { ...state, ...updates };
      return state;
    },
    [],
    { iterations: 1000 }
  );
  
  console.log('Form State Management Results:');
  console.log(`Standard state: ${standardStateResult.averageTime.toFixed(3)}ms`);
  console.log(`Batched state: ${batchedStateResult.averageTime.toFixed(3)}ms`);
  
  return { standardStateResult, batchedStateResult };
}

/**
 * Benchmark data filtering and searching
 */
export async function benchmarkDataFiltering() {
  console.log('Benchmarking data filtering...');
  
  const { complexArray } = createTestData(10000);
  const searchTerm = 'Item 500';
  
  // Test filter with includes
  const filterIncludesResult = await benchmarkFunction(
    'filter with includes',
    () => {
      return complexArray.filter(item => 
        item.name.includes(searchTerm.split(' ')[1])
      );
    },
    [],
    { iterations: 100 }
  );
  
  // Test filter with indexOf
  const filterIndexOfResult = await benchmarkFunction(
    'filter with indexOf',
    () => {
      return complexArray.filter(item => 
        item.name.indexOf(searchTerm.split(' ')[1]) !== -1
      );
    },
    [],
    { iterations: 100 }
  );
  
  // Test filter with regex
  const regex = new RegExp(searchTerm.split(' ')[1], 'i');
  const filterRegexResult = await benchmarkFunction(
    'filter with regex',
    () => {
      return complexArray.filter(item => regex.test(item.name));
    },
    [],
    { iterations: 100 }
  );
  
  console.log('Data Filtering Results:');
  console.log(`Filter includes: ${filterIncludesResult.averageTime.toFixed(3)}ms`);
  console.log(`Filter indexOf: ${filterIndexOfResult.averageTime.toFixed(3)}ms`);
  console.log(`Filter regex: ${filterRegexResult.averageTime.toFixed(3)}ms`);
  
  return { filterIncludesResult, filterIndexOfResult, filterRegexResult };
}

/**
 * Benchmark object creation patterns
 */
export async function benchmarkObjectCreation() {
  console.log('Benchmarking object creation patterns...');
  
  const baseObject = { a: 1, b: 2, c: 3, d: 4, e: 5 };
  
  // Test object spread
  const spreadResult = await benchmarkFunction(
    'object spread',
    () => {
      return { ...baseObject, f: 6 };
    },
    [],
    { iterations: 10000 }
  );
  
  // Test Object.assign
  const assignResult = await benchmarkFunction(
    'Object.assign',
    () => {
      return Object.assign({}, baseObject, { f: 6 });
    },
    [],
    { iterations: 10000 }
  );
  
  // Test manual copy
  const manualResult = await benchmarkFunction(
    'manual copy',
    () => {
      const newObj: any = {};
      for (const key in baseObject) {
        newObj[key] = (baseObject as any)[key];
      }
      newObj.f = 6;
      return newObj;
    },
    [],
    { iterations: 10000 }
  );
  
  console.log('Object Creation Results:');
  console.log(`Object spread: ${spreadResult.averageTime.toFixed(3)}ms`);
  console.log(`Object.assign: ${assignResult.averageTime.toFixed(3)}ms`);
  console.log(`Manual copy: ${manualResult.averageTime.toFixed(3)}ms`);
  
  return { spreadResult, assignResult, manualResult };
}

/**
 * Run comprehensive benchmark suite
 */
export async function runComprehensiveBenchmarks() {
  console.log('🚀 Starting comprehensive performance benchmarks...\n');
  
  const results: any = {};
  
  try {
    results.equalityFunctions = await benchmarkEqualityFunctions();
    console.log('✅ Equality functions benchmark completed\n');
    
    results.debouncingMechanisms = await benchmarkDebouncingMechanisms();
    console.log('✅ Debouncing mechanisms benchmark completed\n');
    
    results.memoizationStrategies = await benchmarkMemoizationStrategies();
    console.log('✅ Memoization strategies benchmark completed\n');
    
    results.formStateManagement = await benchmarkFormStateManagement();
    console.log('✅ Form state management benchmark completed\n');
    
    results.dataFiltering = await benchmarkDataFiltering();
    console.log('✅ Data filtering benchmark completed\n');
    
    results.objectCreation = await benchmarkObjectCreation();
    console.log('✅ Object creation benchmark completed\n');
    
    // Generate summary report
    const summaryReport = generateBenchmarkSummary(results);
    console.log('📊 Benchmark Summary Report:');
    console.log(summaryReport);
    
    return { results, summaryReport };
    
  } catch (error) {
    console.error('❌ Benchmark failed:', error);
    throw error;
  }
}

/**
 * Generate benchmark summary report
 */
function generateBenchmarkSummary(results: any): string {
  const report = [];
  
  report.push('='.repeat(50));
  report.push('PERFORMANCE BENCHMARK SUMMARY');
  report.push('='.repeat(50));
  
  // Best performing approaches
  report.push('\n🏆 RECOMMENDED APPROACHES:');
  
  if (results.equalityFunctions) {
    const fastest = [
      { name: 'Shallow Equal', time: results.equalityFunctions.shallowResult.averageTime },
      { name: 'Deep Equal', time: results.equalityFunctions.deepResult.averageTime },
      { name: 'JSON Stringify', time: results.equalityFunctions.jsonResult.averageTime }
    ].sort((a, b) => a.time - b.time)[0];
    
    report.push(`• Equality Functions: ${fastest.name} (${fastest.time.toFixed(3)}ms)`);
  }
  
  if (results.memoizationStrategies) {
    const fastest = [
      { name: 'useMemo', time: results.memoizationStrategies.useMemoResult.averageTime },
      { name: 'useStableMemo', time: results.memoizationStrategies.useStableMemoResult.averageTime },
      { name: 'Manual', time: results.memoizationStrategies.manualMemoResult.averageTime }
    ].sort((a, b) => a.time - b.time)[0];
    
    report.push(`• Memoization: ${fastest.name} (${fastest.time.toFixed(3)}ms)`);
  }
  
  if (results.objectCreation) {
    const fastest = [
      { name: 'Spread', time: results.objectCreation.spreadResult.averageTime },
      { name: 'Object.assign', time: results.objectCreation.assignResult.averageTime },
      { name: 'Manual', time: results.objectCreation.manualResult.averageTime }
    ].sort((a, b) => a.time - b.time)[0];
    
    report.push(`• Object Creation: ${fastest.name} (${fastest.time.toFixed(3)}ms)`);
  }
  
  // Performance insights
  report.push('\n💡 PERFORMANCE INSIGHTS:');
  report.push('• Use shallow equality for prop comparisons');
  report.push('• Implement debouncing for user inputs (300ms recommended)');
  report.push('• Batch state updates to prevent cascading re-renders');
  report.push('• Use object spread for simple object updates');
  report.push('• Memoize expensive computations with proper dependencies');
  
  // Recommendations for provider settings
  report.push('\n🎯 PROVIDER SETTINGS OPTIMIZATIONS:');
  report.push('• Debounce field updates with 300ms delay');
  report.push('• Use React.memo with shallow comparison for provider cards');
  report.push('• Split context into data, actions, and state contexts');
  report.push('• Implement virtual scrolling for large provider lists');
  report.push('• Use stable references for event handlers');
  
  report.push('\n' + '='.repeat(50));
  
  return report.join('\n');
}

/**
 * Save benchmark results to file
 */
export function saveBenchmarkResults(results: any, filename?: string) {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const defaultFilename = `performance-benchmark-${timestamp}.json`;
  const file = filename || defaultFilename;
  
  const data = {
    timestamp: new Date().toISOString(),
    results,
    environment: {
      userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : 'Node.js',
      platform: typeof process !== 'undefined' ? process.platform : 'unknown',
      nodeVersion: typeof process !== 'undefined' ? process.version : 'unknown'
    }
  };
  
  return JSON.stringify(data, null, 2);
}