// Load MapLibre once, with its worker wired up (bundlers break MapLibre's relative worker lookup).
let loading: Promise<typeof import("maplibre-gl")> | null = null;

export function loadMapLibre() {
  return (loading ??= (async () => {
    const [m, worker] = await Promise.all([
      import("maplibre-gl"),
      import("maplibre-gl/dist/maplibre-gl-worker.mjs?url"),
      import("maplibre-gl/dist/maplibre-gl.css"),
    ]);
    m.setWorkerUrl(worker.default);
    return m;
  })());
}

/** LINZ national aerial imagery (CC BY 4.0). A key is optional today; set PUBLIC_LINZ_API_KEY if LINZ requires one. */
export function linzAerialTiles(): string {
  const key = import.meta.env.PUBLIC_LINZ_API_KEY;
  return `https://basemaps.linz.govt.nz/v1/tiles/aerial/WebMercatorQuad/{z}/{x}/{y}.webp${key ? `?api=${key}` : ""}`;
}
