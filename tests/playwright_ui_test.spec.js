const { test, expect, devices } = require('@playwright/test');

const BASE_URL = 'http://127.0.0.1:5000';

test.describe('WCFL UI Sanity - Desktop', () => {
  test.use({ viewport: { width: 1280, height: 720 } });

  test('Dashboard loads correctly', async ({ page }) => {
    await page.goto(BASE_URL);
    await expect(page.locator('h1.text-gradient')).toBeVisible();
    await expect(page.locator('.navbar')).toBeVisible();
    await expect(page.locator('.bento-grid')).toBeVisible();
  });

  test('Standings page cards check', async ({ page }) => {
    await page.goto(`${BASE_URL}/standings`);
    await expect(page.locator('.data-card').first()).toBeVisible();
  });
});

test.describe('WCFL UI Sanity - Mobile (Samsung S23)', () => {
  test.use({ 
    viewport: { width: 360, height: 800 },
    userAgent: 'Mozilla/5.0 (Linux; Android 13; SM-S911B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36'
  });

  test('Bottom navigation is visible', async ({ page }) => {
    await page.goto(BASE_URL);
    const navbar = page.locator('.navbar');
    await expect(navbar).toBeVisible();
    const box = await navbar.boundingBox();
    // On mobile, fixed at bottom. S23 height is 800, so box.y should be ~730.
    expect(box.y).toBeGreaterThan(600);
  });

  test('Stats cards are in a horizontal row', async ({ page }) => {
    await page.goto(BASE_URL);
    const statsRow = page.locator('.stats-row');
    await expect(statsRow).toHaveCSS('display', 'grid');
    // Using a more flexible check for grid columns since repeat(3, 1fr) computes differently
    const columns = await statsRow.evaluate(el => getComputedStyle(el).gridTemplateColumns.split(' ').length);
    expect(columns).toBe(3);
  });

  test('Tournament Hub bracket is scrollable', async ({ page }) => {
    await page.goto(`${BASE_URL}/fixtures`);
    const bracket = page.locator('.bracket-wrapper');
    await expect(bracket).toBeVisible();
    await expect(bracket).toHaveCSS('overflow-x', 'auto');
  });

  test('Groups stack vertically on mobile', async ({ page }) => {
    await page.goto(`${BASE_URL}/groups`);
    const groupGrid = page.locator('.group-grid');
    // In our mobile CSS, group-grid becomes 1 column (display: flex column or grid 1fr)
    const columns = await groupGrid.evaluate(el => getComputedStyle(el).gridTemplateColumns.split(' ').length);
    // On mobile max-width 1024px, we have grid-template-columns: repeat(auto-fill, minmax(100%, 1fr)) which effectively is 1 column
    expect(columns).toBe(1);
  });
});
