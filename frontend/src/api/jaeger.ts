const jaegerUiBase =
  (import.meta.env.VITE_JAEGER_UI_URL as string | undefined)?.replace(/\/$/, "") ?? "http://localhost:16686";

export function jaegerTraceUrl(traceId: string): string {
  return `${jaegerUiBase}/trace/${traceId}`;
}
