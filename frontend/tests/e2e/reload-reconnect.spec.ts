import { test, expect } from "@playwright/test";

test.describe("Reload and Reconnect @fast", () => {
  test("bootstrap recovers state after reload", async ({ page }) => {
    // Reset and seed
    await page.request.post("http://localhost:8000/api/test/reset");
    await page.request.post("http://localhost:8000/api/test/seed", {
      data: {
        candidates: [{
          id: "sc-reload-1",
          title: "Reload Test",
          status: "pending",
          confidence: 90,
          indicators: ["keyword"],
          startTime: "0:00",
          endTime: "0:15",
          duration: "0:15",
        }],
      },
    });

    // Navigate, connect, verify data loaded
    await page.goto("/");
    await page.getByTestId("landing-url-input").fill("https://twitch.tv/test");
    await page.getByTestId("landing-connect-button").click();
    await expect(page.getByTestId("stream-placeholder")).toBeVisible({ timeout: 10_000 });

    // Candidate should be visible
    await expect(page.getByTestId("candidate-card-sc-reload-1")).toBeVisible({ timeout: 5_000 });
  });
});
