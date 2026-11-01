// 1200×630 share image per park, rendered at build time (satori → SVG → resvg → PNG).
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { Resvg } from "@resvg/resvg-js";
import type { APIRoute, GetStaticPaths } from "astro";
import satori from "satori";
import data from "../../../data/best_park/parks.json";

const require = createRequire(import.meta.url);
const fontDir = join(dirname(require.resolve("@fontsource/inter/package.json")), "files");
const font = (f: string) => readFileSync(join(fontDir, f));
const fonts = [
  { name: "Inter", data: font("inter-latin-700-normal.woff"), weight: 700 as const, style: "normal" as const },
  { name: "Inter", data: font("inter-latin-ext-700-normal.woff"), weight: 700 as const, style: "normal" as const },
  { name: "Inter", data: font("inter-latin-400-normal.woff"), weight: 400 as const, style: "normal" as const },
  { name: "Inter", data: font("inter-latin-ext-400-normal.woff"), weight: 400 as const, style: "normal" as const },
];

export const getStaticPaths: GetStaticPaths = () =>
  data.parks.map((p) => ({ params: { slug: p.slug }, props: { name: p.name, rank: p.rank, score: p.score } }));

const el = (type: string, style: Record<string, unknown>, children: unknown) => ({ type, props: { style, children } });

export const GET: APIRoute = async ({ props }) => {
  const { name, rank, score } = props as { name: string; rank: number; score: number };
  const svg = await satori(
    el("div", { width: "100%", height: "100%", display: "flex", flexDirection: "column", justifyContent: "space-between",
                padding: "64px", background: "#1f6f5c", color: "#ffffff", fontFamily: "Inter" }, [
      el("div", { fontSize: 32, opacity: 0.85 }, "Best Park in Christchurch"),
      el("div", { display: "flex", flexDirection: "column" }, [
        el("div", { fontSize: name.length > 28 ? 64 : 84, fontWeight: 700, lineHeight: 1.05 }, name),
        el("div", { fontSize: 44, marginTop: 24 }, `#${rank} park in Christchurch · ${score}/100`),
      ]),
      el("div", { fontSize: 28, opacity: 0.85 }, "Christchurch Projects · vote for your favourite"),
    ]) as any,
    { width: 1200, height: 630, fonts },
  );
  const png = new Resvg(svg, { fitTo: { mode: "width", value: 1200 } }).render().asPng();
  return new Response(new Uint8Array(png), { headers: { "Content-Type": "image/png" } });
};
