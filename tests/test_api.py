import pytest
import json
import tempfile

from fastapi.testclient import TestClient
from app.app import app

from app.users import User
from app.schemas import Transaction


@pytest.fixture
def client():
    client = TestClient(app)
    return client


# Create Superuser API Test
@pytest.mark.asyncio
async def test_create_superuser(client):
    response = await client.get("/users/create-superuser")
    assert response.status_code == 200


# Login API Test
@pytest.mark.asyncio
async def test_login(client):
    response = await client.post(
        "/login",
        json={"username": "transactionlog", "password": "admintransactionlog"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert "refresh_token" in response.json()
    assert "expire" in response.json()


# Refresh API Test
@pytest.mark.asyncio
async def test_refresh(client):
    # First, we need to login to get a refresh token
    response_login = await client.post(
        "/login",
        json={"username": "testuser", "password": "testpassword"}
    )
    refresh_token = response_login.json()["refresh_token"]

    # Then, we can test the refresh API
    response = await client.post(
        "/refresh",
        headers={"Authorization": f"Bearer {refresh_token}"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert "expire" in response.json()




# Create User API Test
@pytest.mark.asyncio
async def test_create_user(client):
    # First, we need to login to get an access token
    response_login = await client.post(
        "/login",
        json={"username": "testuser", "password": "testpassword"}
    )
    access_token = response_login.json()["access_token"]

    # Then, we can test the create user API
    response = await client.post(
        "/users",
        json={"username": "newuser", "password": "newpassword", "profile": "user"},
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    assert "username" in response.json()
    assert "password" not in response.json()
    assert "profile" in response.json()


# List Users API Test
@pytest.mark.asyncio
async def test_list_users(client):
    # First, we need to login to get an access token
    response_login = await client.post(
        "/login",
        json={"username": "testuser", "password": "testpassword"}
    )
    access_token = response_login.json()["access_token"]

    # Then, we can test the list users API
    response = await client.get(
        "/users",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


# Show User API Test
@pytest.mark.asyncio
async def test_show_user(client):
    # First, we need to login to get an access token
    response_login = await client.post(
        "/login",
        json={"username": "testuser", "password": "testpassword"}
    )
    access_token = response_login.json()["access_token"]

    # Then, we can test the show user API
    response_create = await client.post(
        "/users",
        json={"username": "newuser", "password": "newpassword", "profile": "user"},
        headers={"Authorization": f"Bearer {access_token}"}
    )
    user_id = response_create.json()["id"]
    response_show = await client.get(
        f"/users/{user_id}",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response_show.status_code == 200
    assert "username" in response_show.json()
    assert "password" not in response_show.json()
    assert "profile" in response_show.json()


# Update User API Test
@pytest.mark.asyncio
async def test_update_user(client):
    # Create a user to update
    user = {"name": "John Doe", "email": "johndoe@example.com", "password": "password"}
    response = await client.post("/users", jsclient=user)
    assert response.status_code == 200
    user_id = response.json()["id"]

    # Update the user
    update_data = {"name": "Jane Doe"}
    response = await client.put(f"/users/{user_id}", json=update_data, headers={"Authorization": "Bearer token"})
    assert response.status_code == 200
    assert response.json()["name"] == update_data["name"]
    
    # Clean up by deleting the user
    response = await client.delete(f"/users/{user_id}", headers={"Authorization": "Bearer token"})
    assert response.status_code == 200
    assert response.json() is True


# Delete User API Test
@pytest.mark.asyncio
async def test_delete_user(client):
    # Create a user to delete
    user = {"name": "John Doe", "email": "johndoe@example.com", "password": "password"}
    response = await client.post("/users", jsclient=user)
    assert response.status_code == 200
    user_id = response.json()["id"]

    # Delete the user
    respocliente = await client.delete(f"/users/{user_id}", headers={"Authorization": "Bearer token"})
    assert response.status_code == 200
    assert response.json() is True

    # Make sure the user is really deleted by trying to get it
    response = await client.get(f"/users/{user_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_transaction():
    # create a user with a balance of 1000
    user = User(username="testuser", password="password", balance=1000)
    user.save()

    # create a valid token for the user
    login = await client.post(
        "/login",
        json={"username": user.name, "password": user.password}
    )
    token = login.content["access_token"]

    # create a temporary file with transaction data
    transaction_data = [
        {"id": 1, "type": "deposit", "amount": 500, "date": "2022-01-01"},
        {"id": 2, "type": "withdrawal", "amount": 200, "date": "2022-01-02"}
    ]
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        json.dump(transaction_data, f)
    f.close()

    # make a POST request to create the transactions
    headers = {"Authorization": f"Bearer {token}"}
    with open(f.name, "rb") as file:
        response = client.post("/transactions", headers=headers, files={"file": file})

    # check the response
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "message": "All transactions saved correctly"}

    # check that the user's balance has been updated correctly
    user.refresh()
    assert user.balance == 1300

    # check that the transactions have been created correctly
    transactions = Transaction.select().where(Transaction.assigned_id == user.idx)
    assert transactions.count() == 2
    assert transactions[0].type == "deposit"
    assert transactions[0].amount == 500
    assert transactions[1].type == "withdrawal"
    assert transactions[1].amount == 200


@pytest.mark.asyncio
async def test_list_transactions():
    # create a user with some transactions
    user = User(username="testuser", password="password", balance=1000)
    user.save()
    deposit = Transaction(
        type="deposit", amount=500, assigned_id=user.idx, timestamp_date=1640995200
    )
    deposit.save()
    withdrawal = Transaction(
        type="withdrawal", amount=200, assigned_id=user.idx, timestamp_date=1641081600
    )
    withdrawal.save()

    # create a valid token for the user
    login = await client.post(
        "/login",
        json={"username": user.name, "password": user.password}
    )
    token = login.content["access_token"]

    # make a GET request to list the transactions
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/transactions", headers=headers)

    # check the response
    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["type"] == "deposit"
    assert response.json()[0]["amount"] == 500
    assert response.json()[1]["type"] == "withdrawal"
    assert response.json()[1]["amount"] == 200
