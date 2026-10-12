// Mismo criterio que la web original: si PostHog no está cargado (dev, o sin
// key en index.html), no hace nada.
export function track(event, props) {
  if (window.posthog) window.posthog.capture(event, props || {});
}
