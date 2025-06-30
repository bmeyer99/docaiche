/**
 * Performance Testing Utilities
 * Tools for measuring and benchmarking component performance
 */

import { performance } from 'perf_hooks';

export interface PerformanceTestOptions {
  iterations?: number;
  warmupIterations?: number;
  timeout?: number;
  measureMemory?: boolean;
}

export interface PerformanceTestResult {
  testName: string;
  iterations: number;
  totalTime: number;
  averageTime: number;
  minTime: number;
  maxTime: number;
  standardDeviation: number;
  memoryUsage?: {
    before: number;
    after: number;
    delta: number;
  };
  percentiles: {
    p50: number;
    p75: number;
    p90: number;
    p95: number;
    p99: number;
  };
}

/**
 * Benchmark a function's performance
 */
export async function benchmarkFunction<T extends (...args: any[]) => any>(
  testName: string,
  fn: T,
  args: Parameters<T>,
  options: PerformanceTestOptions = {}
): Promise<PerformanceTestResult> {
  const {
    iterations = 100,
    warmupIterations = 10,
    timeout = 30000,
    measureMemory = false
  } = options;

  const times: number[] = [];
  let memoryBefore = 0;
  let memoryAfter = 0;

  // Warmup runs
  for (let i = 0; i < warmupIterations; i++) {
    await fn(...args);
  }

  // Force garbage collection if available
  if (global.gc) {
    global.gc();
  }

  // Measure memory before
  if (measureMemory && 'memory' in performance) {
    memoryBefore = (performance as any).memory.usedJSHeapSize;
  }

  const startTime = Date.now();

  // Actual benchmark runs
  for (let i = 0; i < iterations; i++) {
    // Check timeout
    if (Date.now() - startTime > timeout) {
      console.warn(`Benchmark "${testName}" timed out after ${i} iterations`);
      break;
    }

    const start = performance.now();
    await fn(...args);
    const end = performance.now();
    
    times.push(end - start);
  }

  // Measure memory after
  if (measureMemory && 'memory' in performance) {
    memoryAfter = (performance as any).memory.usedJSHeapSize;
  }

  // Calculate statistics
  const totalTime = times.reduce((sum, time) => sum + time, 0);
  const averageTime = totalTime / times.length;
  const minTime = Math.min(...times);
  const maxTime = Math.max(...times);

  // Standard deviation
  const variance = times.reduce((sum, time) => sum + Math.pow(time - averageTime, 2), 0) / times.length;
  const standardDeviation = Math.sqrt(variance);

  // Percentiles
  const sortedTimes = times.sort((a, b) => a - b);
  const percentiles = {
    p50: sortedTimes[Math.floor(sortedTimes.length * 0.5)],
    p75: sortedTimes[Math.floor(sortedTimes.length * 0.75)],
    p90: sortedTimes[Math.floor(sortedTimes.length * 0.9)],
    p95: sortedTimes[Math.floor(sortedTimes.length * 0.95)],
    p99: sortedTimes[Math.floor(sortedTimes.length * 0.99)]
  };

  const result: PerformanceTestResult = {
    testName,
    iterations: times.length,
    totalTime,
    averageTime,
    minTime,
    maxTime,
    standardDeviation,
    percentiles
  };

  if (measureMemory) {
    result.memoryUsage = {
      before: memoryBefore,
      after: memoryAfter,
      delta: memoryAfter - memoryBefore
    };
  }

  return result;
}

/**
 * Compare performance between two functions
 */
export async function comparePerformance<T extends (...args: any[]) => any>(
  testName: string,
  fn1: { name: string; fn: T },
  fn2: { name: string; fn: T },
  args: Parameters<T>,
  options: PerformanceTestOptions = {}
): Promise<{
  comparison: string;
  fn1Result: PerformanceTestResult;
  fn2Result: PerformanceTestResult;
  improvement: {
    percentage: number;
    factor: number;
    faster: string;
  };
}> {
  const [result1, result2] = await Promise.all([
    benchmarkFunction(`${testName} - ${fn1.name}`, fn1.fn, args, options),
    benchmarkFunction(`${testName} - ${fn2.name}`, fn2.fn, args, options)
  ]);

  const improvement = {
    percentage: ((result1.averageTime - result2.averageTime) / result1.averageTime) * 100,
    factor: result1.averageTime / result2.averageTime,
    faster: result1.averageTime < result2.averageTime ? fn1.name : fn2.name
  };

  const comparison = improvement.percentage > 0 
    ? `${fn2.name} is ${Math.abs(improvement.percentage).toFixed(2)}% faster than ${fn1.name}`
    : `${fn1.name} is ${Math.abs(improvement.percentage).toFixed(2)}% faster than ${fn2.name}`;

  return {
    comparison,
    fn1Result: result1,
    fn2Result: result2,
    improvement
  };
}

/**
 * React component performance testing utilities
 */
export class ComponentPerformanceTester {
  private results: Map<string, PerformanceTestResult[]> = new Map();

  async testComponentRender(
    componentName: string,
    renderFunction: () => void,
    options: PerformanceTestOptions = {}
  ): Promise<PerformanceTestResult> {
    const result = await benchmarkFunction(
      `${componentName} render`,
      renderFunction,
      [],
      options
    );

    // Store result
    const existing = this.results.get(componentName) || [];
    existing.push(result);
    this.results.set(componentName, existing);

    return result;
  }

  getComponentHistory(componentName: string): PerformanceTestResult[] {
    return this.results.get(componentName) || [];
  }

  generateReport(): {
    components: Record<string, {
      latestResult: PerformanceTestResult;
      trend: 'improving' | 'degrading' | 'stable';
      testCount: number;
    }>;
    summary: {
      totalComponents: number;
      averageRenderTime: number;
      slowestComponent: string;
      fastestComponent: string;
    };
  } {
    const components: Record<string, any> = {};
    let totalAverage = 0;
    let slowestTime = 0;
    let fastestTime = Infinity;
    let slowestComponent = '';
    let fastestComponent = '';

    for (const [componentName, results] of Array.from(this.results.entries())) {
      const latest = results[results.length - 1];
      
      // Determine trend
      let trend: 'improving' | 'degrading' | 'stable' = 'stable';
      if (results.length >= 2) {
        const previous = results[results.length - 2];
        const change = ((latest.averageTime - previous.averageTime) / previous.averageTime) * 100;
        
        if (change > 5) trend = 'degrading';
        else if (change < -5) trend = 'improving';
      }

      components[componentName] = {
        latestResult: latest,
        trend,
        testCount: results.length
      };

      totalAverage += latest.averageTime;

      if (latest.averageTime > slowestTime) {
        slowestTime = latest.averageTime;
        slowestComponent = componentName;
      }

      if (latest.averageTime < fastestTime) {
        fastestTime = latest.averageTime;
        fastestComponent = componentName;
      }
    }

    return {
      components,
      summary: {
        totalComponents: this.results.size,
        averageRenderTime: totalAverage / this.results.size,
        slowestComponent,
        fastestComponent
      }
    };
  }

  clearResults(): void {
    this.results.clear();
  }

  exportResults(): string {
    const report = this.generateReport();
    return JSON.stringify(report, null, 2);
  }
}

/**
 * Global component performance tester instance
 */
export const componentTester = new ComponentPerformanceTester();

/**
 * Utility to create performance test data
 */
export function createTestData(size: number): {
  simpleArray: number[];
  complexArray: Array<{ id: number; name: string; data: any }>;
  nestedObject: any;
} {
  const simpleArray = Array.from({ length: size }, (_, i) => i);
  
  const complexArray = Array.from({ length: size }, (_, i) => ({
    id: i,
    name: `Item ${i}`,
    data: {
      value: Math.random() * 1000,
      timestamp: Date.now(),
      nested: {
        prop1: `value-${i}`,
        prop2: Math.random() > 0.5,
        prop3: Array.from({ length: 10 }, (_, j) => `nested-${i}-${j}`)
      }
    }
  }));

  const nestedObject = {
    level1: {
      level2: {
        level3: {
          data: Array.from({ length: size }, (_, i) => ({ id: i, value: Math.random() }))
        }
      }
    }
  };

  return { simpleArray, complexArray, nestedObject };
}

/**
 * Load testing utility for API calls and async operations
 */
export async function loadTest(
  testName: string,
  asyncOperation: () => Promise<any>,
  options: {
    concurrency?: number;
    duration?: number;
    requestsPerSecond?: number;
  } = {}
): Promise<{
  testName: string;
  duration: number;
  totalRequests: number;
  requestsPerSecond: number;
  averageResponseTime: number;
  minResponseTime: number;
  maxResponseTime: number;
  errors: number;
  successRate: number;
}> {
  const {
    concurrency = 10,
    duration = 10000, // 10 seconds
    requestsPerSecond = 100
  } = options;

  const results: { time: number; success: boolean }[] = [];
  const startTime = Date.now();
  const endTime = startTime + duration;
  const interval = 1000 / requestsPerSecond;

  const workers = Array.from({ length: concurrency }, async () => {
    while (Date.now() < endTime) {
      const requestStart = performance.now();
      
      try {
        await asyncOperation();
        const requestEnd = performance.now();
        results.push({ time: requestEnd - requestStart, success: true });
      } catch (error) {
        const requestEnd = performance.now();
        results.push({ time: requestEnd - requestStart, success: false });
      }

      // Wait for next request
      await new Promise(resolve => setTimeout(resolve, interval));
    }
  });

  await Promise.all(workers);

  const actualDuration = Date.now() - startTime;
  const successfulRequests = results.filter(r => r.success);
  const responseTimes = successfulRequests.map(r => r.time);

  return {
    testName,
    duration: actualDuration,
    totalRequests: results.length,
    requestsPerSecond: results.length / (actualDuration / 1000),
    averageResponseTime: responseTimes.reduce((sum, time) => sum + time, 0) / responseTimes.length,
    minResponseTime: Math.min(...responseTimes),
    maxResponseTime: Math.max(...responseTimes),
    errors: results.filter(r => !r.success).length,
    successRate: (successfulRequests.length / results.length) * 100
  };
}

/**
 * Memory leak detection utility
 */
export class MemoryLeakDetector {
  private snapshots: Array<{ timestamp: number; heapUsed: number }> = [];
  private interval: NodeJS.Timeout | null = null;

  start(intervalMs: number = 5000): void {
    this.stop(); // Stop existing monitoring
    
    this.interval = setInterval(() => {
      if ('memory' in performance) {
        const heapUsed = (performance as any).memory.usedJSHeapSize;
        this.snapshots.push({
          timestamp: Date.now(),
          heapUsed
        });

        // Keep only last 100 snapshots
        if (this.snapshots.length > 100) {
          this.snapshots.shift();
        }
      }
    }, intervalMs);
  }

  stop(): void {
    if (this.interval) {
      clearInterval(this.interval);
      this.interval = null;
    }
  }

  detectLeaks(): {
    hasLeak: boolean;
    trend: 'increasing' | 'decreasing' | 'stable';
    averageGrowth: number;
    totalGrowth: number;
    recommendations: string[];
  } {
    if (this.snapshots.length < 10) {
      return {
        hasLeak: false,
        trend: 'stable',
        averageGrowth: 0,
        totalGrowth: 0,
        recommendations: ['Need more data points to detect leaks']
      };
    }

    const first = this.snapshots[0];
    const last = this.snapshots[this.snapshots.length - 1];
    const totalGrowth = last.heapUsed - first.heapUsed;
    const timeDiff = last.timestamp - first.timestamp;
    const averageGrowth = totalGrowth / (timeDiff / 1000); // bytes per second

    let trend: 'increasing' | 'decreasing' | 'stable' = 'stable';
    if (averageGrowth > 1024) trend = 'increasing'; // 1KB/s growth
    else if (averageGrowth < -1024) trend = 'decreasing';

    const hasLeak = trend === 'increasing' && averageGrowth > 10240; // 10KB/s

    const recommendations: string[] = [];
    if (hasLeak) {
      recommendations.push('Memory usage is steadily increasing');
      recommendations.push('Check for uncleaned event listeners');
      recommendations.push('Review component cleanup in useEffect');
      recommendations.push('Look for circular references');
      recommendations.push('Consider using WeakMap/WeakSet for object references');
    }

    return {
      hasLeak,
      trend,
      averageGrowth,
      totalGrowth,
      recommendations
    };
  }

  getReport() {
    const analysis = this.detectLeaks();
    
    const heapValues = this.snapshots.map(s => s.heapUsed);
    const summary = {
      duration: this.snapshots.length > 0 
        ? this.snapshots[this.snapshots.length - 1].timestamp - this.snapshots[0].timestamp
        : 0,
      peakMemory: Math.max(...heapValues),
      currentMemory: heapValues[heapValues.length - 1] || 0,
      averageMemory: heapValues.reduce((sum, val) => sum + val, 0) / heapValues.length || 0
    };

    return {
      snapshots: this.snapshots,
      analysis,
      summary
    };
  }

  clear(): void {
    this.snapshots = [];
  }
}

// Global memory leak detector
export const memoryLeakDetector = new MemoryLeakDetector();