from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from typing import Any
from urllib.parse import parse_qs, urlparse

from .config import (
    ControlConfig,
    HardwareConfig,
    NetworkConfig,
    validate_control_config,
    validate_hardware_config,
)
from .telemetry import TelemetryStore


@dataclass(frozen=True)
class ApiContext:
    # 供前端只读接口访问的运行上下文。
    telemetry_store: TelemetryStore
    hardware: HardwareConfig
    control: ControlConfig
    network: NetworkConfig | None = None
    calibration_report_path: Path | None = None


class _ApiHandler(BaseHTTPRequestHandler):
    # 这个服务只给前端读，不开放控制写接口。
    server_version = "CarControlAPI/1.0"

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self._write_cors_headers()
        self.end_headers()

    def do_GET(self) -> None:
        context: ApiContext = self.server.context  # type: ignore[attr-defined]
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/v1/health":
                payload = self._health_payload(context)
            elif parsed.path == "/api/v1/telemetry/latest":
                payload = self._latest_payload(context)
            elif parsed.path == "/api/v1/telemetry/history":
                payload = self._history_payload(context, parsed.query)
            elif parsed.path == "/api/v1/config/hardware":
                payload = {"ok": True, "data": asdict(context.hardware)}
            elif parsed.path == "/api/v1/config/control":
                payload = {"ok": True, "data": asdict(context.control)}
            elif parsed.path == "/api/v1/config/network":
                payload = {"ok": True, "data": asdict(context.network) if context.network is not None else None}
            elif parsed.path == "/api/v1/calibration/latest":
                payload = {"ok": True, "data": self._load_calibration_report(context)}
            elif parsed.path == "/api/v1/meta":
                payload = self._meta_payload()
            else:
                self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not found"})
                return
        except Exception as exc:  # noqa: BLE001
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "error": str(exc)})
            return
        self._send_json(HTTPStatus.OK, payload)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        # 前端轮询会很频繁，这里不打印访问日志，避免终端刷屏。
        return

    def _health_payload(self, context: ApiContext) -> dict[str, Any]:
        latest = context.telemetry_store.latest()
        startup_checks = self._startup_checks(context)
        return {
            "ok": True,
            "data": {
                "service": "car_control_system",
                "schema_version": 1,
                "telemetry_ready": latest is not None,
                "latest_loop_index": latest.loop_index if latest is not None else None,
                "mode_name": latest.mode_name if latest is not None else None,
                "input_source": latest.input_source if latest is not None else None,
                "input_link_state": latest.input_link_state if latest is not None else None,
                "startup_checks": startup_checks,
                "config_issues": startup_checks["config_issues"],
            },
        }

    def _latest_payload(self, context: ApiContext) -> dict[str, Any]:
        return {"ok": True, "data": context.telemetry_store.latest_payload()}

    def _history_payload(self, context: ApiContext, query: str) -> dict[str, Any]:
        params = parse_qs(query)
        limit_raw = params.get("limit", ["100"])[0]
        try:
            limit = max(1, min(500, int(limit_raw)))
        except ValueError:
            limit = 100
        return {"ok": True, "data": context.telemetry_store.history_payload(limit)}

    def _load_calibration_report(self, context: ApiContext) -> dict[str, Any] | None:
        if context.calibration_report_path is None:
            return None
        path = context.calibration_report_path
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def _meta_payload(self) -> dict[str, Any]:
        return {
            "ok": True,
            "data": {
                "service": "car_control_system",
                "version": "1",
                "schema_version": 1,
                "endpoints": [
                    "/api/v1/health",
                    "/api/v1/telemetry/latest",
                    "/api/v1/telemetry/history?limit=100",
                    "/api/v1/config/hardware",
                    "/api/v1/config/control",
                    "/api/v1/config/network",
                    "/api/v1/calibration/latest",
                    "/api/v1/meta",
                ],
            },
        }

    def _startup_checks(self, context: ApiContext) -> dict[str, Any]:
        hardware_issues = validate_hardware_config(context.hardware)
        control_issues = validate_control_config(context.control)
        bridge_exists = Path(context.hardware.bridge_library).exists()
        calibration_exists = (
            context.calibration_report_path is not None and context.calibration_report_path.exists()
        )
        return {
            "bridge_library_exists": bridge_exists,
            "calibration_report_exists": calibration_exists,
            "hardware_issues": hardware_issues,
            "control_issues": control_issues,
            "config_issues": hardware_issues + control_issues,
            "ok": bridge_exists and not hardware_issues and not control_issues,
        }

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self._write_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _write_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")


class FrontendApiServer:
    # 给前端提供只读 HTTP 接口，方便直接做仪表盘页面。
    def __init__(
        self,
        host: str,
        port: int,
        telemetry_store: TelemetryStore,
        hardware: HardwareConfig,
        control: ControlConfig,
        network: NetworkConfig | None = None,
        calibration_report_path: str | Path | None = None,
    ) -> None:
        self.context = ApiContext(
            telemetry_store=telemetry_store,
            hardware=hardware,
            control=control,
            network=network,
            calibration_report_path=Path(calibration_report_path) if calibration_report_path else None,
        )
        self._server = ThreadingHTTPServer((host, port), _ApiHandler)
        self._server.context = self.context  # type: ignore[attr-defined]
        self._thread: Thread | None = None

    @property
    def host(self) -> str:
        return str(self._server.server_address[0])

    @property
    def port(self) -> int:
        return int(self._server.server_address[1])

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def start(self) -> None:
        # 放到后台线程里跑，不阻塞小车主循环。
        if self._thread is not None:
            return
        self._thread = Thread(target=self._server.serve_forever, name="frontend-api", daemon=True)
        self._thread.start()

    def close(self) -> None:
        # 退出时优雅停止 HTTP 服务。
        self._server.shutdown()
        self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
