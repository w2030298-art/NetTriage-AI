"""Integration tests for the API error-response format."""

from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from nettriage.api.errors import APIError, APIErrorCode
from nettriage.api.main import create_app


@pytest.fixture
def app_with_error_route() -> FastAPI:
    """App instance with an explicit error-raising route for testing."""
    app = create_app()

    @app.get("/__test_error__")
    def _raise_error() -> None:
        raise APIError(
            code=APIErrorCode.CSV_FILE_TOO_LARGE,
            message="File is too large",
            details={"size_mb": 90, "max_mb": 20},
        )

    return app


class TestErrorResponseFormat:
    def test_api_error_produces_correct_json(
        self, app_with_error_route: FastAPI
    ) -> None:
        """A raised APIError is caught and formatted to the standard shape."""
        with TestClient(app_with_error_route) as client:
            response = client.get("/__test_error__")

        assert response.status_code == 500
        body: dict[str, Any] = response.json()

        assert "error" in body
        error = body["error"]
        assert error["code"] == "CSV_FILE_TOO_LARGE"
        assert error["message"] == "File is too large"
        assert error["details"] == {"size_mb": 90, "max_mb": 20}

    def test_api_error_without_details_defaults_to_empty_dict(
        self, app_with_error_route: FastAPI
    ) -> None:
        """When details are omitted the response body contains an empty dict."""
        # Override the test route to raise without details
        apps = create_app()

        @apps.get("/__test_no_details__")
        def _raise_error() -> None:
            raise APIError(code=APIErrorCode.BATCH_NOT_FOUND, message="Missing")

        apps.exception_handler(APIError)(_api_error_handler)

        with TestClient(apps) as client:
            response = client.get("/__test_no_details__")
        body = response.json()
        assert body["error"]["details"] == {}


def _api_error_handler(request: Any, exc: APIError) -> Any:
    """Standalone handler for the no-details test."""
    from starlette.responses import JSONResponse

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": exc.code.value,
                "message": exc.message,
                "details": exc.details,
            }
        },
    )
