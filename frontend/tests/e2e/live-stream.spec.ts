import { test, expect } from "@playwright/test";

/**
 * Live Stream E2E Test — No Fallbacks
 *
 * Tests the full user flow with LIVEO_TEST_MODE=1:
 * 1. Enter URL → dashboard transition → stream-placeholder visible
 * 2. Indicator updates via WS → dashboard reflects non-zero values
 * 3. Candidate seed → confirm → preview → generate → generated shorts visible
 *
 * All assertions are strict. Failures produce tracebacks for debugging.
 */

const TWITCH_URL = "https://www.twitch.tv/subroza";
const BACKEND_URL = "http://localhost:8000";

test.describe("Live Stream E2E", () => {
  test.setTimeout(60_000);

  test.beforeEach(async ({ page }) => {
    // Reset backend state — must succeed, no fallback
    const resetResp = await page.request.post(`${BACKEND_URL}/api/test/reset`);
    expect(resetResp.status()).toBe(200);
  });

  test("1. URL input and dashboard transition", async ({ page }) => {
    await page.goto("/");

    // Landing page must show input and button
    await expect(page.getByTestId("landing-url-input")).toBeVisible();
    await expect(page.getByTestId("landing-connect-button")).toBeVisible();

    // Enter URL and connect
    await page.getByTestId("landing-url-input").fill(TWITCH_URL);
    await page.getByTestId("landing-connect-button").click();

    // Must transition to dashboard with test-mode placeholder
    await expect(page.getByTestId("stream-placeholder")).toBeVisible({ timeout: 10_000 });

    // Indicator dashboard must be visible
    await expect(page.getByTestId("indicator-dashboard")).toBeVisible();
  });

  test("2. Indicators and live captions update via WebSocket", async ({ page }) => {
    // Connect to dashboard
    await page.goto("/");
    await page.getByTestId("landing-url-input").fill(TWITCH_URL);
    await page.getByTestId("landing-connect-button").click();
    await expect(page.getByTestId("stream-placeholder")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByTestId("indicator-dashboard")).toBeVisible();
    await expect(page.getByTestId("transcript-feed")).toBeVisible();

    // Send indicator updates via test API — must succeed
    const audioResp = await page.request.post(`${BACKEND_URL}/api/test/events`, {
      data: {
        type: "indicator_update",
        data: { type: "audio_spike", value: 75, active: true },
      },
    });
    expect(audioResp.status()).toBe(200);

    const keywordResp = await page.request.post(`${BACKEND_URL}/api/test/events`, {
      data: {
        type: "indicator_update",
        data: { type: "keyword", value: 60, active: true },
      },
    });
    expect(keywordResp.status()).toBe(200);

    const transcriptResp = await page.request.post(`${BACKEND_URL}/api/test/events`, {
      data: {
        type: "transcript_update",
        data: {
          id: "line-live-1",
          timestamp: "00:12",
          text: "Enemy spotted mid, push now.",
          isHighlight: true,
        },
      },
    });
    expect(transcriptResp.status()).toBe(200);

    // Wait for WebSocket delivery
    await page.waitForTimeout(1_000);

    // Indicator dashboard must show the updated values
    const dashboard = page.getByTestId("indicator-dashboard");
    await expect(dashboard).toContainText("75", { timeout: 3_000 });
    await expect(dashboard).toContainText("60", { timeout: 3_000 });
    await expect(page.getByTestId("transcript-feed")).toContainText("Enemy spotted mid, push now.", { timeout: 3_000 });
  });

  test("3. Full candidate → generate → shorts flow", async ({ page }) => {
    // Connect to dashboard
    await page.goto("/");
    await page.getByTestId("landing-url-input").fill(TWITCH_URL);
    await page.getByTestId("landing-connect-button").click();
    await expect(page.getByTestId("stream-placeholder")).toBeVisible({ timeout: 10_000 });

    // Seed a candidate — must succeed
    const seedResp = await page.request.post(`${BACKEND_URL}/api/test/seed`, {
      data: {
        candidates: [{
          id: "sc-live-1",
          title: "Live Test Highlight",
          status: "pending",
          confidence: 85,
          indicators: ["audio_spike", "keyword"],
          startTime: "0:10",
          endTime: "0:25",
          duration: "0:15",
        }],
      },
    });
    expect(seedResp.status()).toBe(200);

    // Broadcast candidate_created WS event — must succeed
    const eventResp = await page.request.post(`${BACKEND_URL}/api/test/events`, {
      data: {
        type: "candidate_created",
        data: {
          id: "sc-live-1",
          title: "Live Test Highlight",
          status: "pending",
          confidence: 85,
          indicators: ["audio_spike", "keyword"],
          startTime: "0:10",
          endTime: "0:25",
          duration: "0:15",
          thumbnailUrl: "",
          isManual: false,
          capturedTranscript: null,
          progress: null,
        },
      },
    });
    expect(eventResp.status()).toBe(200);

    // Candidate card must appear
    await expect(page.getByTestId("candidate-card-sc-live-1")).toBeVisible({ timeout: 5_000 });

    // Click CONFIRM — must succeed
    await page.getByTestId("candidate-confirm-sc-live-1").click();

    // Card must reflect confirmed state (shows PREVIEW button)
    await expect(page.getByTestId("candidate-card-sc-live-1")).toContainText(/CONFIRMED|PREVIEW/i, { timeout: 5_000 });

    // Click PREVIEW button to open modal
    const previewButton = page.getByTestId("candidate-preview-sc-live-1");
    await expect(previewButton).toBeVisible({ timeout: 3_000 });
    await previewButton.click();

    // Preview modal must open
    await expect(page.getByTestId("preview-modal")).toBeVisible({ timeout: 3_000 });

    // Click GENERATE ALL
    await page.getByTestId("preview-generate-all").click();

    // Wait for generation to complete (3 templates × ~3s mock = ~9s)
    await page.waitForTimeout(10_000);

    // Generated shorts grid must be visible with content
    await expect(page.getByTestId("generated-shorts-grid")).toBeVisible();

    // Verify at least one bundle exists (the grid should show generated shorts)
    const gridText = await page.getByTestId("generated-shorts-grid").textContent();
    expect(gridText).toContain("BUNDLE");
  });
});
