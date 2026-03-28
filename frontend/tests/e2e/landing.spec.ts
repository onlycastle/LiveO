import { test, expect } from "@playwright/test";

test.describe("Landing Page @fast", () => {
  test.beforeEach(async ({ page }) => {
    await page.request.post("http://localhost:8000/api/test/reset");
  });

  test("shows URL input field", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByTestId("landing-url-input")).toBeVisible();
  });

  test("shows connect button", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByTestId("landing-connect-button")).toBeVisible();
  });

  test("transitions to dashboard after URL submit", async ({ page }) => {
    await page.goto("/");

    // Fill URL and submit
    await page.getByTestId("landing-url-input").fill("https://twitch.tv/test");
    const startResponsePromise = page.waitForResponse((response) =>
      response.url() === "http://127.0.0.1:8000/api/stream/start"
      && response.request().method() === "POST",
    );
    await page.getByTestId("landing-connect-button").click();
    const startResponse = await startResponsePromise;
    expect(startResponse.ok()).toBeTruthy();

    // Should transition to dashboard — stream placeholder visible in test mode
    await expect(page.getByTestId("stream-placeholder")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByTestId("indicator-dashboard")).toBeVisible();
    await expect(page.getByTestId("transcript-feed")).toBeVisible();
  });
});
