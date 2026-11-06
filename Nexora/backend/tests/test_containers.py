def test_container_lifecycle(client):
    # 1. List existing containers
    list_res = client.get("/api/containers")
    assert list_res.status_code == 200
    containers = list_res.json()
    assert isinstance(containers, list)
    assert len(containers) > 0

    # 2. Create a test container
    create_payload = {
        "name": "nexora-test-unit",
        "image": "alpine:latest",
        "cpu_limit": 1.5,
        "memory_limit_mb": 256,
        "port_mapping": "8888:80",
        "restart_policy": "unless-stopped"
    }
    create_res = client.post("/api/containers", json=create_payload)
    assert create_res.status_code == 201
    created_data = create_res.json()
    cid = created_data["id"]
    assert created_data["name"] == "nexora-test-unit"

    # 3. Inspect container
    inspect_res = client.get(f"/api/containers/{cid}")
    assert inspect_res.status_code == 200
    details = inspect_res.json()
    assert details["cpu_limit"] == 1.5
    assert details["memory_limit_mb"] == 256
    assert "cgroups_path" in details

    # 4. Get live stats
    stats_res = client.get(f"/api/containers/{cid}/stats")
    assert stats_res.status_code == 200
    stats_data = stats_res.json()
    assert stats_data["container_id"] == cid
    assert "cpu_percent" in stats_data
    assert "memory_used_mb" in stats_data
    assert "rx_human" in stats_data

    # 5. Pause container
    pause_res = client.post(f"/api/containers/{cid}/pause")
    assert pause_res.status_code == 200
    assert pause_res.json()["status"] == "paused"

    # 6. Unpause container
    unpause_res = client.post(f"/api/containers/{cid}/unpause")
    assert unpause_res.status_code == 200
    assert unpause_res.json()["status"] == "unpaused"

    # 7. Restart container
    restart_res = client.post(f"/api/containers/{cid}/restart")
    assert restart_res.status_code == 200
    assert restart_res.json()["status"] == "restarted"

    # 8. Stop container
    stop_res = client.post(f"/api/containers/{cid}/stop")
    assert stop_res.status_code == 200
    assert stop_res.json()["status"] == "stopped"

    # 9. Start container
    start_res = client.post(f"/api/containers/{cid}/start")
    assert start_res.status_code == 200
    assert start_res.json()["status"] == "started"

    # 10. Delete container
    del_res = client.delete(f"/api/containers/{cid}?force=true")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "removed"

    # Verify not found after deletion
    verify_res = client.get(f"/api/containers/{cid}")
    assert verify_res.status_code == 404
