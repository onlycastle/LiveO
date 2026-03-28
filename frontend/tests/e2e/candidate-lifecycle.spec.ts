import { test, expect } from "@playwright/test";

test.describe("Candidate Lifecycle @fast", () => {
  test.beforeEach(async ({ page }) => {
    // Reset state via API
    await page.request.post("http://localhost:8000/api/test/reset");

    // Seed test data
    await page.request.post("http://localhost:8000/api/test/seed", {
      data: {
        candidates: [{
          id: "sc-e2e-1",
          title: "E2E Test Highlight",
          status: "pending",
          confidence: 85,
          indicators: ["audio_spike"],
          startTime: "0:10",
          endTime: "0:25",
          duration: "0:15",
        }],
      },
    });

    // Navigate and connect
    await page.goto("/");
    await page.getByTestId("landing-url-input").fill("https://twitch.tv/test");
    await page.getByTestId("landing-connect-button").click();
    await expect(page.getByTestId("stream-placeholder")).toBeVisible({ timeout: 10_000 });
  });

  test("confirm button changes candidate status", async ({ page }) => {
    // Wait for candidate card to appear
    await expect(page.getByTestId("candidate-card-sc-e2e-1")).toBeVisible({ timeout: 5_000 });

    // Click confirm
    await page.getByTestId("candidate-confirm-sc-e2e-1").click();

    // Verify the card shows "CONFIRMED" status (or PREVIEW button)
    await expect(page.getByTestId("candidate-card-sc-e2e-1")).toContainText(/CONFIRMED|PREVIEW/i, { timeout: 5_000 });
  });

  test("skip button dismisses candidate", async ({ page }) => {
    await expect(page.getByTestId("candidate-card-sc-e2e-1")).toBeVisible({ timeout: 5_000 });
    await page.getByTestId("candidate-skip-sc-e2e-1").click();

    // Card should show DISMISSED
    await expect(page.getByTestId("candidate-card-sc-e2e-1")).toContainText(/DISMISSED/i, { timeout: 5_000 });
  });
});
