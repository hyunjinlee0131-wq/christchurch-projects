// Copy committed pipeline outputs (projects/*/outputs) into the site:
// src/data/<project>/ for build-time imports, public/data/<project>/ for runtime fetches (maps).
import { cpSync, existsSync, mkdirSync, readdirSync, rmSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const site = join(dirname(fileURLToPath(import.meta.url)), "..");
const projects = join(site, "..", "projects");

for (const target of ["src/data", "public/data"]) rmSync(join(site, target), { recursive: true, force: true });
let n = 0;
for (const name of readdirSync(projects)) {
  const out = join(projects, name, "outputs");
  if (name.startsWith("_") || !existsSync(out)) continue;
  for (const target of ["src/data", "public/data"]) {
    const dest = join(site, target, name);
    mkdirSync(dest, { recursive: true });
    for (const f of readdirSync(out)) if (/\.(json|geojson)$/.test(f)) cpSync(join(out, f), join(dest, f));
    const figs = join(out, "figures");
    if (target === "public/data" && existsSync(figs)) cpSync(figs, join(dest, "figures"), { recursive: true });
  }
  n++;
}
console.log(`sync-data: ${n} project(s)`);
