from __future__ import annotations

import importlib
import sys


def _clear_api_modules() -> None:
    for name in list(sys.modules):
        if name == "src.api" or name.startswith("src.api."):
            sys.modules.pop(name, None)


def test_src_api_import_is_lazy() -> None:
    _clear_api_modules()
    api = importlib.import_module("src.api")

    assert callable(api.get_all_routers)
    assert callable(api.register_all_routers)


def test_importing_mcc_routes_does_not_pull_full_router_aggregator() -> None:
    _clear_api_modules()
    module = importlib.import_module("src.api.routes.mcc_routes")

    assert module.router.prefix == "/api/mcc"


def test_routes_package_lazily_exports_mcc_router() -> None:
    _clear_api_modules()
    routes_pkg = importlib.import_module("src.api.routes")
    router = getattr(routes_pkg, "mcc_router")

    assert router.prefix == "/api/mcc"
