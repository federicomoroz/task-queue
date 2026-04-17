import pytest


def test_post_task_echo(test_client):
    r = test_client.post("/tasks", json={
        "type": "echo",
        "queue": "default",
        "payload": {"msg": "hello"},
    })
    assert r.status_code == 202
    data = r.json()
    assert data["id"] == 1
    assert data["type"] == "echo"
    assert data["status"] == "pending"
    assert data["queue"] == "default"


def test_post_task_http_request(test_client):
    r = test_client.post("/tasks", json={
        "type": "http_request",
        "queue": "high",
        "payload": {"method": "GET", "url": "https://example.com"},
        "max_retries": 5,
    })
    assert r.status_code == 202
    data = r.json()
    assert data["max_retries"] == 5


def test_post_task_unknown_type(test_client):
    r = test_client.post("/tasks", json={
        "type": "unknown_type",
        "queue": "default",
        "payload": {},
    })
    assert r.status_code == 422


def test_get_task_by_id(test_client):
    test_client.post("/tasks", json={"type": "echo", "queue": "default", "payload": {}})
    r = test_client.get("/tasks/1")
    assert r.status_code == 200
    assert r.json()["id"] == 1


def test_get_task_not_found(test_client):
    r = test_client.get("/tasks/9999")
    assert r.status_code == 404


def test_list_tasks_empty(test_client):
    r = test_client.get("/tasks")
    assert r.status_code == 200
    assert r.json() == []


def test_list_tasks_filter_by_queue(test_client):
    test_client.post("/tasks", json={"type": "echo", "queue": "high", "payload": {}})
    test_client.post("/tasks", json={"type": "echo", "queue": "low", "payload": {}})

    r = test_client.get("/tasks?queue=high")
    assert r.status_code == 200
    tasks = r.json()
    assert len(tasks) == 1
    assert tasks[0]["queue"] == "high"


def test_list_tasks_filter_by_status(test_client):
    test_client.post("/tasks", json={"type": "echo", "queue": "default", "payload": {}})
    r = test_client.get("/tasks?status=pending")
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_health_endpoint(test_client):
    r = test_client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_spa_returns_html(test_client):
    r = test_client.get("/")
    assert r.status_code == 200
    assert "task-queue" in r.text.lower()
