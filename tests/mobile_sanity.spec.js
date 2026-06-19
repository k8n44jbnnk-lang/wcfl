const { test, expect } = require('@playwright/test');

const BASE_URL = 'http://127.0.0.1:5000';

const viewports = [
  { name: 'Samsung S23', width: 360, height: 800 },
  { name: 'iPhone 14 Pro Max', width: 430, height: 932 },
  { name: 'iPhone SE', width: 375, height: 667 }
];

for (const device of viewports) {
  test.describe(`WCFL Mobile Sanity (${device.name})`, () => {
    test.use({ 
      viewport: { width: device.width, height: device.height },
      userAgent: 'Mozilla/5.0 (Mobile)'
    });
    
    test('Dashboard Alignment & Navigation', async ({ page }) => {
      await page.goto(BASE_URL);
      
      const navbar = page.locator('.navbar');
      await expect(navbar).toBeVisible();
      const box = await navbar.boundingBox();
      // On mobile, navbar is fixed at bottom
      expect(box.y + box.height).toBeCloseTo(device.height, 1);
  
      // Check Hero title alignment
      const title = page.locator('.text-gradient').first();
      const titleBox = await title.boundingBox();
      expect(titleBox.width).toBeLessThanOrEqual(device.width);
      
      // Check stats row horizontal alignment
      const statsRow = page.locator('.stats-row').first();
      const statsBox = await statsRow.boundingBox();
      expect(statsBox.width).toBeLessThanOrEqual(device.width);
    });
  
    test('Standings Page Card Alignment', async ({ page }) => {
      await page.goto(`${BASE_URL}/standings`);
      
      const firstCard = page.locator('.data-card').first();
      await expect(firstCard).toBeVisible();
      const cardBox = await firstCard.boundingBox();
      // We expect padding left and right (at least 12px each side)
      expect(cardBox.width).toBeLessThanOrEqual(device.width); 
      
      const pts = firstCard.locator('.stat-val');
      await expect(pts).toBeVisible();
    });
  
    test('Teams Page Card Alignment', async ({ page }) => {
      await page.goto(`${BASE_URL}/team-leaderboard`);
      
      const teamCard = page.locator('.data-card').first();
      await expect(teamCard).toBeVisible();
      const teamCardBox = await teamCard.boundingBox();
      expect(teamCardBox.width).toBeLessThanOrEqual(device.width);
    });
  
    test('Admin Page Mobile Responsiveness', async ({ page }) => {
      await page.goto(`${BASE_URL}/admin`);
      if (page.url().includes('login')) {
          const loginCard = page.locator('.card').first();
          await expect(loginCard).toBeVisible();
          const loginBox = await loginCard.boundingBox();
          expect(loginBox.width).toBeLessThanOrEqual(device.width);
      } else {
          const tabsBar = page.locator('.tabs-bar');
          await expect(tabsBar).toBeVisible();
      }
    });
  
    test('No horizontal overflow on core pages', async ({ page }) => {
      const pages = ['', '/fixtures', '/groups', '/standings', '/team-leaderboard'];
      for (const p of pages) {
        await page.goto(`${BASE_URL}${p}`);
        const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
        expect(overflow, `Horizontal overflow detected on ${p} at ${device.width}px`).toBe(false);
      }
    });
  });
}
