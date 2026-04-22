

def test_list_labels(auth_client):
    client, _ = auth_client
    r = client.get("/labels")
    assert r.status_code == 200


def test_create_label(auth_client):
    client, _ = auth_client
    r = client.post("/labels", data={"title": "Work"})
    assert r.status_code == 200
    assert "Work" in r.text


def test_create_label_empty_title(auth_client):
    client, _ = auth_client
    r = client.post("/labels", data={"title": "  "})
    assert r.status_code == 422


def test_update_label(auth_client, db):
    client, user = auth_client
    from app.labels.service import create_label
    label = create_label(db, user.id, "OldTitle", "", "")
    r = client.put(f"/labels/{label.id}", data={"title": "NewTitle"})
    assert r.status_code == 200
    assert "NewTitle" in r.text


def test_delete_label(auth_client, db):
    client, user = auth_client
    from app.labels.service import create_label
    label = create_label(db, user.id, "ToDelete", "", "")
    r = client.delete(f"/labels/{label.id}")
    assert r.status_code == 200


def test_update_label_not_found(auth_client):
    client, _ = auth_client
    r = client.put("/labels/nonexistent", data={"title": "X"})
    assert r.status_code == 404


def test_unauthenticated_labels(client):
    r = client.get("/labels")
    assert r.status_code == 401
