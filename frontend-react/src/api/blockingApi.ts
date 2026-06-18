// TODO: Backend needed: GET /blocking-signals or GET /crawler/blocking-signals.
export function getBlockingEndpointStatus() {
  return { connected: false, endpoint: "/blocking-signals" };
}
