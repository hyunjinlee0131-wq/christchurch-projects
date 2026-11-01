// GA4, only when PUBLIC_GA4_ID is set. Everything is a safe no-op otherwise.
export type EventName = "vote" | "reweight" | "near_me" | "share" | "feedback" | "open_park";

let enabled = false;

export function initAnalytics(id: string | undefined = import.meta.env.PUBLIC_GA4_ID): void {
  if (!id || typeof window === "undefined") return;
  const w = window as any;
  w.dataLayer = w.dataLayer || [];
  w.gtag = w.gtag || function gtag() { w.dataLayer.push(arguments); };
  w.gtag("js", new Date());
  w.gtag("config", id);
  enabled = true;
}

export function track(event: EventName, params?: Record<string, string | number>): void {
  if (!enabled || typeof window === "undefined") return;
  try {
    (window as any).gtag?.("event", event, params ?? {});
  } catch {
    /* analytics must never break the page */
  }
}

export function _reset(): void {
  enabled = false;
}
