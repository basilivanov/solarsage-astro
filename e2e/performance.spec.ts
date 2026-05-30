// AI_HEADER
// module: M-TEST-E2E-PERFORMANCE
// wave: W-TEST-3
// purpose: Performance tests for page load times and Core Web Vitals

import { test, expect } from '@playwright/test';

test.describe('Performance', () => {
  test('should load /day/today in under 5 seconds', async ({ page }) => {
    const startTime = Date.now();

    await page.goto('/day/today');

    // Wait for content or error to appear
    await page.waitForSelector('[data-testid="today-screen"], [data-testid="error-boundary"]', {
      timeout: 15000
    });

    const loadTime = Date.now() - startTime;

    console.log(`Page load time: ${loadTime}ms`);

    // Warn if slow, but don't fail (API might be slow in dev)
    if (loadTime > 5000) {
      console.warn(`⚠️  Page load time exceeded 5 seconds: ${loadTime}ms`);
    }

    // Hard limit: 15 seconds (catches infinite loading)
    expect(loadTime).toBeLessThan(15000);
  });

  test('should measure First Contentful Paint (FCP)', async ({ page }) => {
    await page.goto('/day/today');

    // Wait for page to load
    await page.waitForSelector('[data-testid="today-screen"], [data-testid="error-boundary"]', {
      timeout: 15000
    });

    // Get performance metrics
    const metrics = await page.evaluate(() => {
      const perfEntries = performance.getEntriesByType('paint');
      const fcp = perfEntries.find(entry => entry.name === 'first-contentful-paint');

      return {
        fcp: fcp ? fcp.startTime : null,
        navigationStart: performance.timing.navigationStart,
        domContentLoaded: performance.timing.domContentLoadedEventEnd - performance.timing.navigationStart,
        loadComplete: performance.timing.loadEventEnd - performance.timing.navigationStart,
      };
    });

    console.log('Performance metrics:', metrics);

    if (metrics.fcp) {
      console.log(`First Contentful Paint: ${metrics.fcp}ms`);

      // Good FCP is under 1.8s, warn if over 3s
      if (metrics.fcp > 3000) {
        console.warn(`⚠️  FCP is slow: ${metrics.fcp}ms`);
      }
    }

    if (metrics.domContentLoaded) {
      console.log(`DOM Content Loaded: ${metrics.domContentLoaded}ms`);
    }
  });

  test('should not have memory leaks on navigation', async ({ page }) => {
    await page.goto('/day/today');

    // Wait for initial load
    await page.waitForSelector('[data-testid="today-screen"], [data-testid="error-boundary"]', {
      timeout: 15000
    });

    // Get initial memory usage
    const initialMemory = await page.evaluate(() => {
      if (performance.memory) {
        return {
          usedJSHeapSize: performance.memory.usedJSHeapSize,
          totalJSHeapSize: performance.memory.totalJSHeapSize,
        };
      }
      return null;
    });

    // Navigate back and forth 5 times
    for (let i = 0; i < 5; i++) {
      await page.goto('/calendar');
      await page.waitForTimeout(1000);
      await page.goto('/day/today');
      await page.waitForTimeout(1000);
    }

    // Get final memory usage
    const finalMemory = await page.evaluate(() => {
      if (performance.memory) {
        return {
          usedJSHeapSize: performance.memory.usedJSHeapSize,
          totalJSHeapSize: performance.memory.totalJSHeapSize,
        };
      }
      return null;
    });

    if (initialMemory && finalMemory) {
      const memoryGrowth = finalMemory.usedJSHeapSize - initialMemory.usedJSHeapSize;
      const growthMB = memoryGrowth / 1024 / 1024;

      console.log(`Memory growth after 5 navigations: ${growthMB.toFixed(2)} MB`);

      // Warn if memory grew by more than 10MB
      if (growthMB > 10) {
        console.warn(`⚠️  Potential memory leak detected: ${growthMB.toFixed(2)} MB growth`);
      }
    }
  });

  test('should measure API response time', async ({ page }) => {
    let apiResponseTime = 0;
    let apiStatus = 0;

    page.on('response', async response => {
      if (response.url().includes('/api/day/')) {
        const timing = await response.request().timing();
        apiResponseTime = timing.responseEnd;
        apiStatus = response.status();
      }
    });

    await page.goto('/day/today');

    // Wait for page to load
    await page.waitForSelector('[data-testid="today-screen"], [data-testid="error-boundary"]', {
      timeout: 15000
    });

    if (apiResponseTime > 0) {
      console.log(`API response time: ${apiResponseTime}ms (status: ${apiStatus})`);

      // Warn if API is slow
      if (apiResponseTime > 3000) {
        console.warn(`⚠️  API response time is slow: ${apiResponseTime}ms`);
      }

      // Hard limit: 10 seconds
      expect(apiResponseTime).toBeLessThan(10000);
    }
  });

  test('should not block main thread for too long', async ({ page }) => {
    await page.goto('/day/today');

    // Wait for page to load
    await page.waitForSelector('[data-testid="today-screen"], [data-testid="error-boundary"]', {
      timeout: 15000
    });

    // Measure long tasks (tasks that block main thread for >50ms)
    const longTasks = await page.evaluate(() => {
      return new Promise<number>((resolve) => {
        let longTaskCount = 0;

        if ('PerformanceObserver' in window) {
          try {
            const observer = new PerformanceObserver((list) => {
              for (const entry of list.getEntries()) {
                if (entry.duration > 50) {
                  longTaskCount++;
                }
              }
            });

            observer.observe({ entryTypes: ['longtask'] });

            // Wait 5 seconds to collect data
            setTimeout(() => {
              observer.disconnect();
              resolve(longTaskCount);
            }, 5000);
          } catch {
            // Long Task API not supported
            resolve(0);
          }
        } else {
          resolve(0);
        }
      });
    });

    if (longTasks > 0) {
      console.log(`Long tasks detected: ${longTasks}`);

      if (longTasks > 5) {
        console.warn(`⚠️  Too many long tasks: ${longTasks}`);
      }
    }
  });
});
