// TODO: Backend needed: GET /logs or GET /audit-logs.
export function getAuditLogEndpointStatus() {
  return { connected: false, endpoint: "/audit-logs" };
}
