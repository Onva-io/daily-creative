"""Daily Photo end-to-end: sessions without a timer, publishing with a place,
and who gets to see the coordinates."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from httpx import AsyncClient

from test_uploads_submissions import (
    _auth_headers,
    _complete_profile,
    _create_ready_upload,
    _creative_type_params,
    _seed_prompt,
    assert_matches_schema,
    requires_postgres,
)
from test_uploads_submissions import client as _client_fixture
from test_uploads_submissions import db_engine as _db_engine_fixture
from test_uploads_submissions import openapi_spec as _openapi_spec_fixture

# Reuse the upload/submission fixtures rather than duplicating the app wiring.
client = _client_fixture
db_engine = _db_engine_fixture
openapi_spec = _openapi_spec_fixture

CREATIVE_TYPE_PHOTO = "photo"

BRIGHTON = {"latitude": 50.8225, "longitude": -0.1372}


async def _create_photo_session(
    client: AsyncClient,
    headers: dict[str, str],
    prompt_id: uuid.UUID,
    *,
    timer_mode: str = "no_timer",
    selected_timer_seconds: int | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "creative_type": CREATIVE_TYPE_PHOTO,
        "prompt_id": str(prompt_id),
        "timer_mode": timer_mode,
    }
    if selected_timer_seconds is not None:
        body["selected_timer_seconds"] = selected_timer_seconds
    created = await client.post("/api/v1/sessions", headers=headers, json=body)
    assert created.status_code == 201, created.text
    return created.json()


async def _create_ready_photo_session(
    client: AsyncClient,
    headers: dict[str, str],
    prompt_id: uuid.UUID,
) -> str:
    session = await _create_photo_session(client, headers, prompt_id)
    session_id = session["id"]
    # No timer: the client goes straight to the capture step.
    reached = await client.post(
        f"/api/v1/sessions/{session_id}/events",
        headers=headers,
        json={"event_type": "photo_step_reached"},
    )
    assert reached.status_code == 200, reached.text
    assert reached.json()["status"] == "active"
    assert reached.json()["stage"] == "ready_for_photo"
    return session_id


def _photo_submission_json(
    session_id: str,
    upload_id: str,
    *,
    prompt_id: uuid.UUID,
    caption: str | None = None,
    location: dict[str, Any] | None = None,
) -> dict[str, Any]:
    content: dict[str, Any] = {
        "creative_type": CREATIVE_TYPE_PHOTO,
        "upload_id": upload_id,
    }
    if caption is not None:
        content["caption"] = caption
    if location is not None:
        content["location"] = location
    return {
        "creative_type": CREATIVE_TYPE_PHOTO,
        "session_id": session_id,
        "prompt_id": str(prompt_id),
        "content": content,
    }


async def _publish_photo(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    location: dict[str, Any] | None,
    caption: str | None = None,
) -> dict[str, Any]:
    prompt = await _seed_prompt(client)
    session_id = await _create_ready_photo_session(client, headers, prompt.id)
    upload = await _create_ready_upload(client, headers)
    response = await client.post(
        "/api/v1/submissions",
        headers=headers,
        json=_photo_submission_json(
            session_id, upload["id"], prompt_id=prompt.id, caption=caption, location=location
        ),
    )
    assert response.status_code == 201, response.text
    return response.json()


@requires_postgres
@pytest.mark.asyncio
async def test_photo_session_without_timer_goes_straight_to_capture(
    client: AsyncClient, openapi_spec: dict[str, Any]
) -> None:
    headers = _auth_headers(client)
    await _complete_profile(client, headers)
    prompt = await _seed_prompt(client)

    session = await _create_photo_session(client, headers, prompt.id)
    assert_matches_schema(session, "CreativeSession", openapi_spec)
    assert session["creative_type"] == CREATIVE_TYPE_PHOTO
    assert session["timer_mode"] == "no_timer"
    assert session["selected_timer_seconds"] is None
    assert session["stage"] is None

    # timer_completed is meaningless without a countdown.
    completed = await client.post(
        f"/api/v1/sessions/{session['id']}/events",
        headers=headers,
        json={"event_type": "timer_completed"},
    )
    assert completed.status_code == 422
    assert completed.json()["error"]["code"] == "invalid_session_transition"

    reached = await client.post(
        f"/api/v1/sessions/{session['id']}/events",
        headers=headers,
        json={"event_type": "photo_step_reached"},
    )
    assert reached.status_code == 200
    assert reached.json()["stage"] == "ready_for_photo"


@requires_postgres
@pytest.mark.asyncio
async def test_photo_session_with_countdown_still_works(client: AsyncClient) -> None:
    headers = _auth_headers(client)
    await _complete_profile(client, headers)
    prompt = await _seed_prompt(client)

    session = await _create_photo_session(
        client, headers, prompt.id, timer_mode="countdown", selected_timer_seconds=300
    )
    assert session["timer_mode"] == "countdown"
    completed = await client.post(
        f"/api/v1/sessions/{session['id']}/events",
        headers=headers,
        json={"event_type": "timer_completed"},
    )
    assert completed.status_code == 200
    assert completed.json()["stage"] == "ready_for_photo"


@requires_postgres
@pytest.mark.asyncio
async def test_publish_photo_without_location(
    client: AsyncClient, openapi_spec: dict[str, Any]
) -> None:
    headers = _auth_headers(client)
    await _complete_profile(client, headers)

    body = await _publish_photo(client, headers, location=None, caption="Morning light")
    assert_matches_schema(body, "Submission", openapi_spec)
    assert body["creative_type"] == CREATIVE_TYPE_PHOTO
    assert body["caption"] == "Morning light"
    assert body["upload_id"] is not None
    assert body["content"]["creative_type"] == CREATIVE_TYPE_PHOTO
    assert body["content"]["image_url"]
    assert body["content"]["thumbnail_url"]
    assert body["content"]["location"] is None


@requires_postgres
@pytest.mark.asyncio
async def test_location_hidden_from_others_unless_author_shares_exact(
    client: AsyncClient, openapi_spec: dict[str, Any]
) -> None:
    author = _auth_headers(client, subject=f"descope|{uuid.uuid4()}")
    viewer = _auth_headers(client, subject=f"descope|{uuid.uuid4()}")
    await _complete_profile(client, author, username=f"author_{uuid.uuid4().hex[:8]}")
    await _complete_profile(client, viewer, username=f"viewer_{uuid.uuid4().hex[:8]}")

    body = await _publish_photo(
        client,
        author,
        location={**BRIGHTON, "label": "Brighton seafront", "source": "exif"},
    )
    assert_matches_schema(body, "Submission", openapi_spec)
    # The author sees their own coordinates in the create response.
    assert body["is_owner"] is True
    assert body["content"]["location"] == {
        "label": "Brighton seafront",
        "latitude": BRIGHTON["latitude"],
        "longitude": BRIGHTON["longitude"],
        "exact_shared": False,
    }

    # Another signed-in user: label only.
    detail = await client.get(f"/api/v1/submissions/{body['id']}", headers=viewer)
    assert detail.status_code == 200
    assert_matches_schema(detail.json(), "Submission", openapi_spec)
    assert detail.json()["content"]["location"] == {
        "label": "Brighton seafront",
        "latitude": None,
        "longitude": None,
        "exact_shared": False,
    }

    # Guest feed: label only, and no audit field leaks.
    feed = await client.get("/api/v1/feed/recent", params=_creative_type_params("photo"))
    assert feed.status_code == 200
    assert_matches_schema(feed.json(), "RecentFeed", openapi_spec)
    item = next(item for item in feed.json()["items"] if item["id"] == body["id"])
    assert item["content"]["location"]["latitude"] is None
    assert item["content"]["location"]["longitude"] is None
    assert item["content"]["location"]["label"] == "Brighton seafront"
    assert "source" not in item["content"]["location"]

    # The author, on the detail endpoint, still sees them.
    own_detail = await client.get(f"/api/v1/submissions/{body['id']}", headers=author)
    assert own_detail.status_code == 200
    assert own_detail.json()["content"]["location"]["latitude"] == BRIGHTON["latitude"]


@requires_postgres
@pytest.mark.asyncio
async def test_location_visible_to_everyone_when_author_shares_exact(
    client: AsyncClient,
) -> None:
    author = _auth_headers(client, subject=f"descope|{uuid.uuid4()}")
    await _complete_profile(client, author, username=f"author_{uuid.uuid4().hex[:8]}")

    body = await _publish_photo(
        client,
        author,
        location={**BRIGHTON, "label": "Brighton seafront", "source": "pin", "share_exact": True},
    )

    feed = await client.get("/api/v1/feed/recent", params=_creative_type_params("photo"))
    assert feed.status_code == 200
    item = next(item for item in feed.json()["items"] if item["id"] == body["id"])
    assert item["content"]["location"] == {
        "label": "Brighton seafront",
        "latitude": BRIGHTON["latitude"],
        "longitude": BRIGHTON["longitude"],
        "exact_shared": True,
    }


@requires_postgres
@pytest.mark.asyncio
async def test_label_only_location_is_allowed(client: AsyncClient) -> None:
    headers = _auth_headers(client)
    await _complete_profile(client, headers)
    body = await _publish_photo(client, headers, location={"label": "Kitchen table"})
    assert body["content"]["location"] == {
        "label": "Kitchen table",
        "latitude": None,
        "longitude": None,
        "exact_shared": False,
    }


@requires_postgres
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "location",
    [
        {"latitude": 50.0},  # half a pair
        {"latitude": 95.0, "longitude": 0.0},  # out of range
        {"label": "   "},  # nothing usable
        {"label": "Somewhere", "share_exact": True},  # exact without coordinates
        {**BRIGHTON, "source": "carrier-pigeon"},  # unknown source
    ],
)
async def test_invalid_locations_are_rejected(
    client: AsyncClient, location: dict[str, Any]
) -> None:
    headers = _auth_headers(client)
    await _complete_profile(client, headers)
    prompt = await _seed_prompt(client)
    session_id = await _create_ready_photo_session(client, headers, prompt.id)
    upload = await _create_ready_upload(client, headers)

    response = await client.post(
        "/api/v1/submissions",
        headers=headers,
        json=_photo_submission_json(
            session_id, upload["id"], prompt_id=prompt.id, location=location
        ),
    )
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "validation_error"


@requires_postgres
@pytest.mark.asyncio
async def test_photo_feed_is_separate_from_sketch_feed(client: AsyncClient) -> None:
    headers = _auth_headers(client)
    await _complete_profile(client, headers)
    body = await _publish_photo(client, headers, location=None)

    photo_feed = await client.get("/api/v1/feed/recent", params=_creative_type_params("photo"))
    assert any(item["id"] == body["id"] for item in photo_feed.json()["items"])
    sketch_feed = await client.get("/api/v1/feed/recent", params=_creative_type_params("sketch"))
    assert all(item["id"] != body["id"] for item in sketch_feed.json()["items"])


@requires_postgres
@pytest.mark.asyncio
async def test_photo_session_cannot_publish_sketch_content(client: AsyncClient) -> None:
    headers = _auth_headers(client)
    await _complete_profile(client, headers)
    prompt = await _seed_prompt(client)
    session_id = await _create_ready_photo_session(client, headers, prompt.id)
    upload = await _create_ready_upload(client, headers)

    response = await client.post(
        "/api/v1/submissions",
        headers=headers,
        json={
            "creative_type": "sketch",
            "session_id": session_id,
            "prompt_id": str(prompt.id),
            "content": {"creative_type": "sketch", "upload_id": upload["id"]},
        },
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "session_not_found"


@requires_postgres
@pytest.mark.asyncio
async def test_photo_preferences_are_scoped_to_the_photo_app(client: AsyncClient) -> None:
    headers = _auth_headers(client)
    await _complete_profile(client, headers)

    updated = await client.patch(
        "/api/v1/me/preferences",
        headers=headers,
        params=_creative_type_params("photo"),
        json={"remember_timer_option": True, "remembered_timer_mode": "no_timer"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["remember_timer_option"] is True
    assert updated.json()["remembered_timer_mode"] == "no_timer"

    sketch_prefs = await client.get(
        "/api/v1/me/preferences", headers=headers, params=_creative_type_params("sketch")
    )
    assert sketch_prefs.status_code == 200
    assert sketch_prefs.json()["remember_timer_option"] is False
