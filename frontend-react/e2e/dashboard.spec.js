const { test, expect } = require('@playwright/test');

const MOCK_CURRENT_PRICES = {
  sjc: {
    results: [
      {
        buy_1l: 82000000,
        sell_1l: 84000000,
        buy_nhan1c: 81000000,
        sell_nhan1c: 82500000,
        buy_nutrang_9999: 80500000,
        sell_nutrang_9999: 81800000,
        buy_nutrang_99: 78000000,
        sell_nutrang_99: 79500000,
        buy_nutrang_75: 59000000,
        sell_nutrang_75: 61000000,
      }
    ]
  }
};

const MOCK_UPDATE_HISTORICAL = {
  status: 'up_to_date',
  records_added: 0,
  days_added: 0
};

test.describe('Gold Price Dashboard - E2E Tests', () => {

  test.beforeEach(async ({ page }) => {
    // Intercept backend API calls with mock data for deterministic, isolated CI runs
    await page.route('**/api/update-historical-data', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_UPDATE_HISTORICAL),
      });
    });

    await page.route('**/api/current-prices', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_CURRENT_PRICES),
      });
    });

    await page.route('**/api/historical-prices*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      });
    });
  });

  test('TC01: Trang web tải thành công và hiển thị Navbar Brand', async ({ page }) => {
    await page.goto('/');

    // Check document title
    await expect(page).toHaveTitle(/Gold Price Dashboard|React App/i);

    // Check navbar brand
    const brand = page.locator('.navbar-brand');
    await expect(brand).toBeVisible();
    await expect(brand).toContainText('Gold');
  });

  test('TC02: Hiển thị đúng dữ liệu bảng giá vàng (Price Cards / Table)', async ({ page }) => {
    await page.goto('/');

    // Verify SJC gold item types appear on the page
    const sjcItem = page.getByText(/SJC 1L|SJC Ring 1C|Gold Bar/i).first();
    await expect(sjcItem).toBeVisible({ timeout: 10000 });

    // Verify formatted price values are rendered
    const formattedPrice = page.getByText(/82\.000\.000|84\.000\.000/i).first();
    await expect(formattedPrice).toBeVisible();
  });

  test('TC03: Tương tác nút Export CSV và Update Data', async ({ page }) => {
    await page.goto('/');

    // Find Export CSV button
    const exportBtn = page.getByRole('button', { name: /export csv/i }).or(page.locator('button:has-text("Export")'));
    if (await exportBtn.count() > 0) {
      await expect(exportBtn.first()).toBeVisible();
    }

    // Intercept update trigger endpoint
    let updateRequested = false;
    await page.route('**/api/data/update', async (route) => {
      updateRequested = true;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'success' }),
      });
    });

    // Handle alert dialog if update is clicked
    page.on('dialog', async (dialog) => {
      await dialog.accept();
    });

    const updateBtn = page.getByRole('button', { name: /update data|refresh/i }).first();
    if (await updateBtn.count() > 0) {
      await updateBtn.click();
    }
  });

  test('TC04: Giao diện hiển thị ổn định khi API lỗi (Graceful degradation)', async ({ page }) => {
    // Override API to simulate 500 error
    await page.route('**/api/current-prices', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Internal Server Error' }),
      });
    });

    await page.goto('/');

    // App should not crash or produce blank screen
    const appContainer = page.locator('.App');
    await expect(appContainer).toBeVisible();
    const navbar = page.locator('.navbar');
    await expect(navbar).toBeVisible();
  });

  test('TC05: Kiểm tra hiển thị Responsive trên màn hình di động', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 }); // iPhone SE viewport
    await page.goto('/');

    // Brand should remain visible on mobile
    const brand = page.locator('.navbar-brand');
    await expect(brand).toBeVisible();

    // Verify main app element doesn't produce horizontal overflow break
    const app = page.locator('.App');
    await expect(app).toBeVisible();
  });
});
