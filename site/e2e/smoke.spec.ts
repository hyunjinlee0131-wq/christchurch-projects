import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

const errors: string[] = [];
test.beforeEach(({ page }) => {
  errors.length = 0;
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("console", (m) => { if (m.type() === "error" && !/tiles\.openfreemap|maplibre|WebGL/i.test(m.text())) errors.push(m.text()); });
});

async function noHorizontalScroll(page: Page) {
  const [sw, iw] = await page.evaluate(() => [document.documentElement.scrollWidth, window.innerWidth]);
  expect(sw).toBeLessThanOrEqual(iw);
}

async function firstParkHref(page: Page) {
  await page.goto("parks/");
  return (await page.locator("#rank-table tbody tr").first().locator("a").getAttribute("href"))!;
}

test("home shows Best Park card with #1 park", async ({ page }) => {
  await page.goto("./");
  await expect(page.getByRole("heading", { name: "Christchurch Projects", level: 1 })).toBeVisible();
  await expect(page.locator(".project .headline")).toContainText("#1:");
  await noHorizontalScroll(page);
});

test("leaderboard shows a ranked list without any input", async ({ page }) => {
  await page.goto("parks/");
  const rows = page.locator("#rank-table tbody tr:visible");
  await expect(rows).toHaveCount(10);
  await expect(rows.first().locator(".rank")).toHaveText("1");
  await noHorizontalScroll(page);
});

test("show all expands the list", async ({ page }) => {
  await page.goto("parks/");
  await page.getByRole("button", { name: /Show all/ }).click();
  expect(await page.locator("#rank-table tbody tr:visible").count()).toBeGreaterThan(300);
});

test("sliders re-rank the list", async ({ page }) => {
  await page.goto("parks/");
  const firstBefore = await page.locator("#rank-table tbody tr").first().getAttribute("data-id");
  for (const key of ["play", "seating", "bbq", "water", "sport", "trees", "size"]) await page.locator(`input[data-key=${key}]`).fill("0");
  await page.locator("input[data-key=dogs]").fill("3");
  await expect(page.locator("th.col-you")).toBeVisible();
  await expect(page.locator("#status")).toContainText("Re-ranked");
  const firstAfter = await page.locator("#rank-table tbody tr").first().getAttribute("data-id");
  expect(firstAfter).not.toBe(firstBefore);
});

test("all-zero weights show a message instead of breaking", async ({ page }) => {
  await page.goto("parks/");
  for (const s of await page.locator(".slider input").all()) await s.fill("0");
  await expect(page.locator("#status")).toContainText("Pick at least one");
  await expect(page.locator("#rank-table tbody tr").first().locator(".rank")).toHaveText("1");
});

test("park page has OG tags with absolute URLs", async ({ page }) => {
  await page.goto(await firstParkHref(page));
  const og = await page.locator('meta[property="og:image"]').getAttribute("content");
  expect(og).toMatch(/^https:\/\/hyunjinlee0131-wq\.github\.io\/christchurch-projects\/og\/parks\/.+\.png$/);
  await expect(page.getByRole("heading", { level: 1 })).toContainText("is #1 of");
  await noHorizontalScroll(page);
});

test("og image is served as a png", async ({ page, request }) => {
  const href = await firstParkHref(page);
  const slug = href.split("/").filter(Boolean).pop();
  const r = await request.get(`og/parks/${slug}.png`);
  expect(r.status()).toBe(200);
  expect(r.headers()["content-type"]).toContain("image/png");
});

test("smoke: page works with no Supabase env", async ({ page }) => {
  await page.goto(await firstParkHref(page));
  const vote = page.locator("button.vote");
  await expect(vote).toBeDisabled();
  await expect(vote).toHaveText("Voting coming soon");
  await page.goto("parks/");
  await expect(page.locator("#people-msg")).toHaveText("Voting opens soon.");
  expect(errors).toEqual([]);
});

for (const path of ["./", "parks/"]) {
  test(`no serious or critical axe violations on ${path}`, async ({ page }) => {
    await page.goto(path);
    const res = await new AxeBuilder({ page }).exclude("#park-map").analyze();
    const bad = res.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
    expect(bad.map((v) => `${v.id}: ${v.nodes.length}`)).toEqual([]);
  });
}

test("no serious or critical axe violations on a park page", async ({ page }) => {
  await page.goto(await firstParkHref(page));
  const res = await new AxeBuilder({ page }).analyze();
  const bad = res.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
  expect(bad.map((v) => `${v.id}: ${v.nodes.length}`)).toEqual([]);
});

test("keyboard: sliders and share button reachable by Tab", async ({ page, browserName }) => {
  await page.goto("parks/");
  const seen = new Set<string>();
  for (let i = 0; i < 40; i++) {
    await page.keyboard.press("Tab");
    seen.add(await page.evaluate(() => (document.activeElement as HTMLElement)?.dataset?.key ?? document.activeElement?.id ?? ""));
  }
  expect(seen.has("play")).toBe(true);
  expect(seen.has("near-me")).toBe(true);
});
