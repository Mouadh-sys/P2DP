import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_project_and_environment_lifecycle(async_client: AsyncClient, auth_headers: dict[str, str]) -> None:
    create_response = await async_client.post(
        "/api/projects",
        json={"name": "demo-project"},
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    project = create_response.json()
    project_id = project["id"]
    assert project["name"] == "demo-project"

    list_response = await async_client.get("/api/projects", headers=auth_headers)
    assert list_response.status_code == 200
    assert any(item["id"] == project_id for item in list_response.json())

    get_response = await async_client.get(f"/api/projects/{project_id}", headers=auth_headers)
    assert get_response.status_code == 200
    assert get_response.json()["id"] == project_id

    env_create_response = await async_client.post(
        f"/api/projects/{project_id}/environments",
        json={"target": "dev", "status": "pending"},
        headers=auth_headers,
    )
    assert env_create_response.status_code == 201
    environment = env_create_response.json()
    environment_id = environment["id"]
    assert environment["target"] == "dev"
    assert environment["project_id"] == project_id

    list_env_response = await async_client.get(
        f"/api/projects/{project_id}/environments",
        headers=auth_headers,
    )
    assert list_env_response.status_code == 200
    assert len(list_env_response.json()) == 1

    get_env_response = await async_client.get(f"/api/environments/{environment_id}", headers=auth_headers)
    assert get_env_response.status_code == 200
    assert get_env_response.json()["id"] == environment_id

    duplicate_env_response = await async_client.post(
        f"/api/projects/{project_id}/environments",
        json={"target": "local-k8s", "status": "active"},
        headers=auth_headers,
    )
    assert duplicate_env_response.status_code == 409

    delete_response = await async_client.delete(f"/api/projects/{project_id}", headers=auth_headers)
    assert delete_response.status_code == 204

    missing_response = await async_client.get(f"/api/projects/{project_id}", headers=auth_headers)
    assert missing_response.status_code == 404


@pytest.mark.asyncio
async def test_projects_require_authentication(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/projects")
    assert response.status_code == 401
