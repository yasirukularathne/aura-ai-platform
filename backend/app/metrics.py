import re
import threading
import time

_UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-"
    r"[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


class Metrics:
    def __init__(self):
        self.started_at = time.time()
        self._lock = threading.Lock()
        self._requests: dict[tuple[str, str, int], int] = {}
        self._latency: dict[tuple[str, str], tuple[int, float]] = {}

    @staticmethod
    def normalize_path(path: str) -> str:
        parts = [
            "{id}" if _UUID_PATTERN.fullmatch(part) else part
            for part in path.split("/")
        ]
        return "/".join(parts)

    def record_request(self, method: str, path: str, status_code: int, duration: float):
        normalized_path = self.normalize_path(path)
        with self._lock:
            request_key = (method, normalized_path, status_code)
            self._requests[request_key] = self._requests.get(request_key, 0) + 1
            latency_key = (method, normalized_path)
            count, total = self._latency.get(latency_key, (0, 0.0))
            self._latency[latency_key] = (count + 1, total + duration)

    def render(self) -> str:
        lines = [
            "# HELP aura_uptime_seconds Process uptime in seconds.",
            "# TYPE aura_uptime_seconds gauge",
            f"aura_uptime_seconds {time.time() - self.started_at:.3f}",
            "# HELP aura_http_requests_total HTTP requests by response status.",
            "# TYPE aura_http_requests_total counter",
        ]
        with self._lock:
            for (method, path, status), count in sorted(self._requests.items()):
                lines.append(
                    "aura_http_requests_total"
                    f'{{method="{method}",path="{path}",status="{status}"}} {count}'
                )
            lines.extend(
                [
                    "# HELP aura_http_request_duration_seconds_sum "
                    "Total request duration.",
                    "# TYPE aura_http_request_duration_seconds_sum counter",
                ]
            )
            for (method, path), (_, total) in sorted(self._latency.items()):
                lines.append(
                    "aura_http_request_duration_seconds_sum"
                    f'{{method="{method}",path="{path}"}} {total:.6f}'
                )
        return "\n".join(lines) + "\n"


metrics = Metrics()
