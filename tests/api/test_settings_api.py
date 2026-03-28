import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_get_settings_defaults(client: AsyncClient):
    resp = await client.get("/api/settings")
    assert resp.status_code == 200
    body = resp.json()
    assert body["shortsDuration"] == "30s"
    assert body["autoConfirmThreshold"] == 85
    assert "indicatorSensitivity" in body


@pytest.mark.anyio
async def test_patch_settings_updates_field(client: AsyncClient):
    resp = await client.patch("/api/settings", json={
        "shortsDuration": "60s",
    })
    assert resp.status_code == 200
    assert resp.json()["shortsDuration"] == "60s"


@pytest.mark.anyio
async def test_settings_round_trip(client: AsyncClient):
    # Read defaults
    resp = await client.get("/api/settings")
    original = resp.json()
    assert original["shortsDuration"] == "30s"

    # Update
    await client.patch("/api/settings", json={"shortsDuration": "45s"})

    # Confirm persisted
    resp = await client.get("/api/settings")
    assert resp.json()["shortsDuration"] == "45s"

    # Other defaults unchanged
    assert resp.json()["autoConfirmThreshold"] == original["autoConfirmThreshold"]


@pytest.mark.anyio
async def test_patch_settings_threshold(client: AsyncClient):
    resp = await client.patch("/api/settings", json={
        "autoConfirmThreshold": 70,
    })
    assert resp.status_code == 200
    assert resp.json()["autoConfirmThreshold"] == 70
