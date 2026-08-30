"""§83 metrics (Prometheus + Grafana, per CLAUDE.md §11). Two series only,
deliberately: request volume and latency, labeled by route *template*
(`/decisions/{decision_id}`), never the raw path — an unbounded label
(a real UUID per request) would make this an unbounded-cardinality metric,
which is a real operational cost, not a hypothetical one (§109/§139's cost-
control discipline applied to observability itself). Anything more (business
metrics, per-tenant series) is a deliberate non-goal for this slice — §143
"avoid data hoarding" applies to metrics as much as to telemetry fields.
"""
from prometheus_client import Counter, Histogram

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests handled",
    labelnames=("method", "route", "status_code"),
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    labelnames=("method", "route"),
)
