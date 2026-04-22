def test_tasks_panel(auth_client):
    client, _ = auth_client
    r = client.get("/tasks")
    assert r.status_code == 200


def test_tasks_count_empty(auth_client):
    client, _ = auth_client
    r = client.get("/tasks/count")
    assert r.status_code == 200


def test_tasks_panel_filter(auth_client):
    client, _ = auth_client
    r = client.get("/tasks?filter=local")
    assert r.status_code == 200


def test_mark_task_done(auth_client, db_task):
    client, _ = auth_client
    r = client.post(f"/tasks/{db_task.id}/done")
    assert r.status_code == 200


def test_mark_task_undone(auth_client, db_task):
    client, _ = auth_client
    client.post(f"/tasks/{db_task.id}/done")
    r = client.post(f"/tasks/{db_task.id}/undone")
    assert r.status_code == 200


def test_delete_task(auth_client, db_task):
    client, _ = auth_client
    r = client.delete(f"/tasks/{db_task.id}")
    assert r.status_code == 200


def test_get_task_edit_form(auth_client, db_task):
    client, _ = auth_client
    r = client.get(f"/tasks/{db_task.id}/edit")
    assert r.status_code == 200
    assert db_task.title in r.text


def test_update_task(auth_client, db_task):
    client, _ = auth_client
    r = client.put(f"/tasks/{db_task.id}", data={"title": "Updated task title"})
    assert r.status_code == 200
    assert "Updated task title" in r.text


def test_tasks_count_with_task(auth_client, db_task):
    client, _ = auth_client
    r = client.get("/tasks/count")
    assert r.status_code == 200


def test_unauthenticated_tasks(client):
    r = client.get("/tasks")
    assert r.status_code == 401
