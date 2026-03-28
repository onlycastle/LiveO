import { execFileSync } from "node:child_process";

import { expect, test } from "@playwright/test";

const TWITCH_URL = "https://www.twitch.tv/subroza";
const BACKEND_URL = "http://localhost:8000";

test.describe("Download Verify", () => {
  test.setTimeout(90_000);

  test.beforeEach(async ({ page }) => {
    const resetResp = await page.request.post(`${BACKEND_URL}/api/test/reset`);
    expect(resetResp.status()).toBe(200);
  });

  test("generated short downloads as a 1080x1920 artifact", async ({ page }) => {
    await page.goto("/");
    await page.getByTestId("landing-url-input").fill(TWITCH_URL);
    await page.getByTestId("landing-connect-button").click();
    await expect(page.getByTestId("stream-placeholder")).toBeVisible({ timeout: 10_000 });

    const transcriptResp = await page.request.post(`${BACKEND_URL}/api/test/events`, {
      data: {
        type: "transcript_update",
        data: {
          id: "line-download-1",
          timestamp: "00:22",
          text: "Clutch incoming, hold this angle.",
        },
      },
    });
    expect(transcriptResp.status()).toBe(200);

    const seedResp = await page.request.post(`${BACKEND_URL}/api/test/seed`, {
      data: {
        candidates: [{
          id: "sc-download-1",
          title: "Download Verification Highlight",
          status: "pending",
          confidence: 92,
          indicators: ["audio_spike", "keyword"],
          startTime: "0:20",
          endTime: "0:35",
          duration: "0:15",
        }],
      },
    });
    expect(seedResp.status()).toBe(200);

    const eventResp = await page.request.post(`${BACKEND_URL}/api/test/events`, {
      data: {
        type: "candidate_created",
        data: {
          id: "sc-download-1",
          title: "Download Verification Highlight",
          status: "pending",
          confidence: 92,
          indicators: ["audio_spike", "keyword"],
          startTime: "0:20",
          endTime: "0:35",
          duration: "0:15",
          thumbnailUrl: "",
          isManual: false,
          capturedTranscript: "Clutch incoming, hold this angle.",
          progress: null,
        },
      },
    });
    expect(eventResp.status()).toBe(200);

    await expect(page.getByTestId("candidate-card-sc-download-1")).toBeVisible({ timeout: 5_000 });
    await page.getByTestId("candidate-confirm-sc-download-1").click();
    await page.getByTestId("candidate-preview-sc-download-1").click();
    await expect(page.getByTestId("preview-modal")).toBeVisible({ timeout: 3_000 });
    await page.getByTestId("preview-generate-all").click();

    await expect(page.getByTestId("generated-shorts-grid")).toContainText("1 BUNDLE", { timeout: 20_000 });

    const bundle = page.locator('[data-testid^="short-bundle-"]').first();
    await expect(bundle).toBeVisible({ timeout: 5_000 });
    await bundle.click();

    const downloadButton = page.locator('[data-testid^="short-download-"]').first();
    await expect(downloadButton).toBeVisible({ timeout: 5_000 });

    const downloadPromise = page.waitForEvent("download");
    await downloadButton.click();
    const download = await downloadPromise;
    const filePath = await download.path();

    expect(filePath).toBeTruthy();

    const probeOutput = execFileSync("ffprobe", [
      "-v",
      "quiet",
      "-print_format",
      "json",
      "-show_format",
      "-show_streams",
      filePath!,
    ], { encoding: "utf8" });
    const probe = JSON.parse(probeOutput) as {
      streams: Array<{ codec_type?: string; width?: number; height?: number }>;
    };
    const videoStream = probe.streams.find((stream) => stream.codec_type === "video");

    expect(videoStream).toBeDefined();
    expect(videoStream?.width).toBe(1080);
    expect(videoStream?.height).toBe(1920);
  });
});
