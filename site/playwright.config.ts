import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "e2e",
  timeout: 30_000,
  use: { baseURL: "http://localhost:4321/christchurch-projects/" },
  projects: [
    { name: "phone", use: { ...devices["Pixel 5"], viewport: { width: 360, height: 740 } } },
    { name: "desktop", use: { viewport: { width: 1280, height: 800 } } },
  ],
  webServer: { command: "npm run preview -- --port 4321", url: "http://localhost:4321/christchurch-projects/", reuseExistingServer: true, timeout: 120_000 },
});
