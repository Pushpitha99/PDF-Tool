import pytest
import uuid


@pytest.mark.asyncio
async def test_user_registration_and_login(client):
    """Positive Test: Registers a new user and verifies login credentials return a valid JWT token."""
    unique_username = f"qa_user_{uuid.uuid4().hex[:6]}"
    password = "testqapassword123"

    # Register
    reg_res = await client.post("/api/v1/auth/register", json={
        "username": unique_username,
        "password": password,
        "role": "user"
    })
    assert reg_res.status_code == 200
    reg_data = reg_res.json()
    assert reg_data["username"] == unique_username
    assert reg_data["role"] == "user"

    # Login
    login_res = await client.post("/api/v1/auth/login", json={
        "username": unique_username,
        "password": password
    })
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert "access_token" in login_data
    assert login_data["token_type"] == "bearer"
    assert login_data["user"]["username"] == unique_username


@pytest.mark.asyncio
async def test_invalid_login_credentials(client):
    """Negative Test: Supplying wrong password returns HTTP 401 Unauthorized."""
    login_res = await client.post("/api/v1/auth/login", json={
        "username": "non_existent_user_999",
        "password": "wrongpassword123"
    })
    assert login_res.status_code == 401
    data = login_res.json()
    assert "detail" in data
