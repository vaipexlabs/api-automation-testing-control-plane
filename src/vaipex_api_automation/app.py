"""Deterministic FastAPI reference service for API quality scenarios."""

from typing import Annotated
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Query,
    Request,
    Response,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from vaipex_api_automation.models import (
    Health,
    Order,
    OrderCollection,
    OrderCreate,
    OrderPatch,
    OrderReplace,
    OrderStatus,
    Principal,
    Priority,
    ResetResult,
)
from vaipex_api_automation.repository import OrderRepository
from vaipex_api_automation.security import authenticate, require_admin, require_writer

SERVICE_NAME = "vaipex-api-quality-reference"
SERVICE_VERSION = "0.1.0"
SUPPORTED_FAILURES = {"dependency", "rate-limit", "timeout"}
APPLICATION_METHODS = "GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS"
DISABLED_METHODS = {"CONNECT", "TRACE"}


def _repository(request: Request) -> OrderRepository:
    return request.app.state.orders


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Order was not found.")


def inject_failure(
    mode: Annotated[str | None, Header(alias="X-Vaipex-Failure")] = None,
) -> None:
    if mode is None:
        return
    if mode not in SUPPORTED_FAILURES:
        supported = ", ".join(sorted(SUPPORTED_FAILURES))
        raise HTTPException(
            status_code=400,
            detail=f"Unknown failure mode. Use: {supported}.",
        )
    if mode == "rate-limit":
        raise HTTPException(
            status_code=429,
            detail="The deterministic rate limit was reached.",
            headers={"Retry-After": "30"},
        )
    if mode == "dependency":
        raise HTTPException(
            status_code=503,
            detail="The deterministic downstream dependency is unavailable.",
        )
    raise HTTPException(
        status_code=504,
        detail="The deterministic downstream dependency timed out.",
    )


def create_app() -> FastAPI:
    app = FastAPI(
        title="Vaipex API Automation Reference Service",
        summary="Deterministic resource API for comprehensive quality validation.",
        description=(
            "A self-contained order API with role and ownership boundaries, "
            "controlled failure modes, and explicit HTTP semantics."
        ),
        version=SERVICE_VERSION,
        contact={"name": "Vaipex Labs", "email": "vaipex.labs@gmail.com"},
        license_info={"name": "Apache-2.0"},
        openapi_tags=[
            {"name": "health", "description": "Service health contracts."},
            {"name": "orders", "description": "Governed order resource behavior."},
            {"name": "administration", "description": "Deterministic test controls."},
        ],
    )
    app.state.orders = OrderRepository()

    @app.middleware("http")
    async def correlation_id(request: Request, call_next):
        value = request.headers.get("X-Correlation-ID") or f"vaipex-{uuid4()}"
        if request.method in DISABLED_METHODS:
            response = JSONResponse(
                status_code=405,
                content={
                    "error": {
                        "code": "method_not_allowed",
                        "message": f"{request.method} is disabled by API policy.",
                    }
                },
                headers={"Allow": APPLICATION_METHODS},
            )
        else:
            response = await call_next(request)
        response.headers["X-Correlation-ID"] = value
        response.headers["X-Service-Version"] = SERVICE_VERSION
        return response

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, error: HTTPException) -> JSONResponse:
        del request
        code = {
            400: "bad_request",
            401: "unauthorized",
            403: "forbidden",
            404: "not_found",
            429: "rate_limited",
            503: "dependency_unavailable",
            504: "dependency_timeout",
        }.get(error.status_code, "request_failed")
        headers = dict(error.headers or {})
        if error.status_code in {401, 403}:
            headers["Cache-Control"] = "no-store"
        return JSONResponse(
            status_code=error.status_code,
            content={"error": {"code": code, "message": str(error.detail)}},
            headers=headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(
        request: Request, error: RequestValidationError
    ) -> JSONResponse:
        del request
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "The request did not satisfy the API contract.",
                    "details": error.errors(),
                }
            },
        )

    @app.get("/health/live", response_model=Health, tags=["health"])
    def liveness() -> Health:
        return Health(status="up", service=SERVICE_NAME, version=SERVICE_VERSION)

    @app.get("/health/ready", response_model=Health, tags=["health"])
    def readiness() -> Health:
        return Health(status="ready", service=SERVICE_NAME, version=SERVICE_VERSION)

    router = APIRouter(
        prefix="/v1/orders",
        tags=["orders"],
        dependencies=[Depends(inject_failure)],
    )

    @router.get("", response_model=OrderCollection)
    def list_orders(
        request: Request,
        principal: Annotated[Principal, Depends(authenticate)],
        page: Annotated[int, Query(ge=1)] = 1,
        page_size: Annotated[int, Query(ge=1, le=100)] = 20,
        status: OrderStatus | None = None,
        priority: Priority | None = None,
        sort: Annotated[
            str,
            Query(pattern=r"^-?(order_id|quantity|created_at)$"),
        ] = "order_id",
    ) -> OrderCollection:
        all_items = _repository(request).list_for(
            principal,
            status=status,
            priority=priority,
            sort=sort,
        )
        start = (page - 1) * page_size
        items = all_items[start : start + page_size]
        return OrderCollection(
            items=items,
            count=len(items),
            total=len(all_items),
            page=page,
            page_size=page_size,
        )

    @router.post("", response_model=Order, status_code=201)
    def create_order(
        payload: OrderCreate,
        request: Request,
        principal: Annotated[Principal, Depends(require_writer)],
        response: Response,
        idempotency_key: Annotated[
            str | None,
            Header(alias="Idempotency-Key", min_length=8, max_length=128),
        ] = None,
    ) -> Order:
        order, replayed = _repository(request).create(
            payload,
            principal.subject,
            idempotency_key=idempotency_key,
        )
        response.headers["Location"] = f"/v1/orders/{order.order_id}"
        response.headers["Idempotency-Replayed"] = str(replayed).lower()
        return order

    @router.get("/{order_id}", response_model=Order)
    def get_order(
        order_id: str,
        request: Request,
        principal: Annotated[Principal, Depends(authenticate)],
        response: Response,
        if_none_match: Annotated[str | None, Header(alias="If-None-Match")] = None,
    ) -> Order | Response:
        order = _repository(request).get_for(order_id, principal)
        if order is None:
            raise _not_found()
        etag = f'"{order.order_id}-v{order.version}"'
        if if_none_match == etag:
            return Response(status_code=304, headers={"ETag": etag})
        response.headers["ETag"] = etag
        response.headers["Cache-Control"] = "private, max-age=0, must-revalidate"
        return order

    @router.put("/{order_id}", response_model=Order)
    def replace_order(
        order_id: str,
        payload: OrderReplace,
        request: Request,
        principal: Annotated[Principal, Depends(require_writer)],
    ) -> Order:
        order = _repository(request).replace(order_id, payload, principal)
        if order is None:
            raise _not_found()
        return order

    @router.patch("/{order_id}", response_model=Order)
    def patch_order(
        order_id: str,
        payload: OrderPatch,
        request: Request,
        principal: Annotated[Principal, Depends(require_writer)],
    ) -> Order:
        order = _repository(request).patch(order_id, payload, principal)
        if order is None:
            raise _not_found()
        return order

    @router.delete("/{order_id}", status_code=204)
    def delete_order(
        order_id: str,
        request: Request,
        principal: Annotated[Principal, Depends(require_writer)],
    ) -> Response:
        if not _repository(request).delete(order_id, principal):
            raise _not_found()
        return Response(status_code=204)

    @router.head("/{order_id}")
    def head_order(
        order_id: str,
        request: Request,
        principal: Annotated[Principal, Depends(authenticate)],
    ) -> Response:
        order = _repository(request).get_for(order_id, principal)
        if order is None:
            raise _not_found()
        return Response(
            headers={
                "ETag": f'"{order.order_id}-v{order.version}"',
                "X-Resource-Owner": order.owner_id,
            }
        )

    @router.options("")
    @router.options("/{order_id}")
    def order_options() -> Response:
        return Response(
            status_code=204,
            headers={
                "Allow": APPLICATION_METHODS,
                "Access-Control-Allow-Methods": APPLICATION_METHODS,
            },
        )

    app.include_router(router)

    @app.post(
        "/v1/admin/reset",
        response_model=ResetResult,
        tags=["administration"],
    )
    def reset_state(
        request: Request,
        principal: Annotated[Principal, Depends(require_admin)],
    ) -> ResetResult:
        del principal
        count = _repository(request).reset()
        return ResetResult(restored_orders=count, status="reset")

    return app


app = create_app()
