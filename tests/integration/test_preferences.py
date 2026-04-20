def test_get_preferences(auth_client):
    client, _ = auth_client
    r = client.get("/preferences")
    assert r.status_code == 200


def test_save_font(auth_client):
    client, _ = auth_client
    r = client.post("/preferences/font", data={"font": "mono"})
    assert r.status_code == 200
    assert "Saved" in r.text


def test_save_palette(auth_client):
    client, _ = auth_client
    r = client.post("/preferences/palette", data={"palette": "dark"})
    assert r.status_code == 200
    assert "Saved" in r.text


def test_save_history_depth(auth_client):
    client, _ = auth_client
    r = client.post("/preferences/history-depth", data={"max_edit_history": "5"})
    assert r.status_code == 200
    assert "Saved" in r.text


def test_save_history_depth_clamped(auth_client):
    client, _ = auth_client
    r = client.post("/preferences/history-depth", data={"max_edit_history": "99"})
    assert r.status_code == 200


def test_toggle_ai_summary(auth_client):
    client, _ = auth_client
    r = client.post("/preferences/ai-summary-toggle", data={"save_ai_summaries": "on"})
    assert r.status_code == 200


def test_save_languages(auth_client):
    client, _ = auth_client
    r = client.post("/preferences/languages", data={"languages": ["en", "fr"]})
    assert r.status_code == 200
    assert "Saved" in r.text


def test_unauthenticated_preferences(client):
    r = client.get("/preferences")
    assert r.status_code == 401
