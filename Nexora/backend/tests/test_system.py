def test_docker_status(client):
    response = client.get("/api/docker/status")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "mode" in data
    assert "engine_version" in data
    assert "cgroup_version" in data

def test_system_info(client):
    response = client.get("/api/system/info")
    assert response.status_code == 200
    data = response.json()
    assert "platform" in data
    assert "cpu_count" in data
    assert "memory_total_mb" in data
    assert "cgroup_info" in data
    assert "namespaces_info" in data
    assert "namespaces" in data["namespaces_info"]
