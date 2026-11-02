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
  await expect(page.locator(".project").first().locator(".headline")).toContainText("#1:");
  await noHorizontalScroll(page);
});

test("leaderboard shows a ranked list without any input", async ({ page }) => {
  await page.goto("parks/");
  // People's Choice comes first (user decision); the ranking follows it without any input needed
  await expect(page.getByRole("heading", { name: "People's Choice" })).toBeInViewport();
  await expect(page.locator("h2").nth(0)).toHaveText("People's Choice");
  await expect(page.locator("h2").nth(1)).toHaveText("Ranking");
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

test("sort by a factor reorders the list and shows that factor", async ({ page }) => {
  await page.goto("parks/");
  await page.getByLabel("Sort by").selectOption("bbq");
  await expect(page.locator("th.col-factor")).toHaveText("Barbecues");
  const values = await page.locator("#rank-table tbody tr:visible td.col-factor").allTextContents();
  const n = values.map((v) => parseInt(v, 10));
  expect(n.length).toBe(10);
  expect(n).toEqual([...n].sort((a, b) => b - a));
  expect(n[0]).toBeGreaterThan(0);
  await expect(page.locator("#rank-table tbody tr:visible").first().locator(".rank")).toHaveText("1");
  await page.getByLabel("Sort by").selectOption("score");
  await expect(page.locator("th.col-factor")).toBeHidden();
});

test("search finds parks by name", async ({ page }) => {
  await page.goto("parks/");
  await page.getByLabel("Search parks").fill("hagley");
  const names = await page.locator("#rank-table tbody tr:visible td.name").allTextContents();
  expect(names.length).toBeGreaterThan(0);
  expect(names.every((n) => /hagley/i.test(n))).toBe(true);
  await page.getByLabel("Search parks").fill("zzzz-no-such-park");
  await expect(page.locator("#status")).toContainText("No parks match");
});

test("parks near me sorts by distance", async ({ page, context }) => {
  await context.grantPermissions(["geolocation"]);
  await context.setGeolocation({ latitude: -43.531, longitude: 172.6206 }); // Cathedral Square
  await page.goto("parks/");
  await page.getByRole("button", { name: "Parks near me" }).click();
  await expect(page.locator("th.col-dist")).toBeVisible();
  const km = (await page.locator("#rank-table tbody tr:visible td.col-dist").allTextContents()).map(parseFloat);
  expect(km).toEqual([...km].sort((a, b) => a - b));
  expect(km[0]).toBeLessThan(1.5);
});

test("sliders and method section are gone", async ({ page }) => {
  await page.goto("parks/");
  await expect(page.locator(".slider")).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "How this was calculated" })).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "What matters to you?" })).toHaveCount(0);
});

test("keyboard: search, sort and near-me reachable by Tab", async ({ page }) => {
  await page.goto("parks/");
  const seen = new Set<string>();
  for (let i = 0; i < 15; i++) {
    await page.keyboard.press("Tab");
    seen.add(await page.evaluate(() => document.activeElement?.id ?? ""));
  }
  expect([...seen]).toEqual(expect.arrayContaining(["park-search", "sort-by", "near-me"]));
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

test("map renders parks", async ({ page }) => {
  await page.goto("parks/");
  await page.locator("#park-map").scrollIntoViewIfNeeded();
  await expect(page.locator("#park-map canvas")).toBeVisible({ timeout: 15_000 });
  await expect(page.locator("#park-map")).not.toContainText("could not load");
  expect(errors.filter((e) => /park map failed/.test(e))).toEqual([]);
});

test("inline links keep their spaces", async ({ page }) => {
  await page.goto(await firstParkHref(page));
  await expect(page.locator(".site-footer")).toContainText("Christchurch City Council (CC BY 4.0)");
  await expect(page.locator(".site-footer")).toContainText("Council. Source on GitHub");
  await expect(page.locator("main")).toContainText("Open in a map · Directions");
});

test("feedback box hidden when nothing to show", async ({ page }) => {
  await page.goto(await firstParkHref(page));
  await expect(page.locator(".feedback")).toBeHidden();
});

test("pipes page shows headline finding and tool link or coming-soon", async ({ page }) => {
  await page.goto("pipes/");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("sewer pipes");
  await expect(page.locator(".headline")).toContainText("riskiest 10%");
  await expect(page.locator(".tree-answer")).toContainText("95% CI"); // wording is generated from the CI
  const link = page.locator("#open-tool");
  const soon = page.getByText("Interactive tool coming soon");
  expect((await link.count()) + (await soon.count())).toBeGreaterThan(0);
  await expect(page.locator("img[src$='rate_by_material.png']")).toBeVisible();
  await noHorizontalScroll(page);
});

test("home lists both projects", async ({ page }) => {
  await page.goto("./");
  await expect(page.locator(".project")).toHaveCount(2);
  await expect(page.locator(".project").nth(1)).toContainText("sewer pipes");
});

test("no serious or critical axe violations on pipes/", async ({ page }) => {
  await page.goto("pipes/");
  const res = await new AxeBuilder({ page }).analyze();
  const bad = res.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
  expect(bad.map((v) => `${v.id}: ${v.nodes.length}`)).toEqual([]);
});
