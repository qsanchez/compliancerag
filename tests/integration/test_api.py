"""Integration test: smoke-test the running API server.

Requires local API running: task api:up
Also requires AWS credentials and local pgvector with data loaded.
"""

import os

import httpx
import pytest

pytestmark = pytest.mark.integration

_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
_API_KEY = os.getenv("API_KEY", "localdevapikey")

_HEADERS = {"X-API-Key": _API_KEY}


def test_health_returns_200() -> None:
    response = httpx.get(f"{_BASE_URL}/health", headers=_HEADERS)
    assert response.status_code == 200


def test_health_response_shape() -> None:
    response = httpx.get(f"{_BASE_URL}/health", headers=_HEADERS)
    body = response.json()
    assert "status" in body


def test_chat_gdpr_question_returns_200() -> None:
    payload = {"question": "What does Article 32 of GDPR require?"}
    response = httpx.post(f"{_BASE_URL}/chat", json=payload, headers=_HEADERS, timeout=60)
    assert response.status_code == 200


def test_chat_response_shape() -> None:
    payload = {"question": "What are the main obligations for data controllers under GDPR?"}
    response = httpx.post(f"{_BASE_URL}/chat", json=payload, headers=_HEADERS, timeout=60)
    body = response.json()
    assert "answer" in body
    assert "citations" in body
    assert isinstance(body["answer"], str)
    assert len(body["answer"]) > 0
    assert isinstance(body["citations"], list)


def test_chat_requires_auth() -> None:
    payload = {"question": "What is GDPR?"}
    response = httpx.post(f"{_BASE_URL}/chat", json=payload, timeout=10)
    assert response.status_code in (401, 403)


def test_chat_rejects_empty_question() -> None:
    payload = {"question": ""}
    response = httpx.post(f"{_BASE_URL}/chat", json=payload, headers=_HEADERS, timeout=10)
    assert response.status_code == 422
