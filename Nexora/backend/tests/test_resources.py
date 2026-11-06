def test_resource_management_and_cgroups(client):
    containers = client.get("/api/containers").json()
    assert len(containers) > 0
    cid = containers[0]["id"]

    # 1. Fetch current resources
    res = client.get(f"/api/containers/{cid}/resources")
    assert res.status_code == 200
    rdata = res.json()
    assert "cpu" in rdata
    assert "memory" in rdata
    assert "cgroup_parameters" in rdata
    assert rdata["cgroup_parameters"]["cpu_period_us"] == 100000

    # 2. Update resource limits dynamically
    update_payload = {
        "cpu_limit": 2.5,
        "memory_limit_mb": 768
    }
    up_res = client.post(f"/api/containers/{cid}/resources", json=update_payload)
    assert up_res.status_code == 200
    up_data = up_res.json()
    assert up_data["cpu_limit"] == 2.5
    assert up_data["memory_limit_mb"] == 768

    # 3. Verify updated limits in profile
    verify_res = client.get(f"/api/containers/{cid}/resources")
    assert verify_res.status_code == 200
    vdata = verify_res.json()
    assert vdata["cgroup_parameters"]["cpu_limit_cores"] == 2.5
    assert vdata["cgroup_parameters"]["memory_limit_mb"] == 768
    assert vdata["cgroup_parameters"]["cpu_quota_us"] == 250000

    # 4. Out-of-bounds validation check: CPU exceeds max
    invalid_cpu_res = client.post(f"/api/containers/{cid}/resources", json={"cpu_limit": 100.0})
    assert invalid_cpu_res.status_code == 422 # Pydantic validation error or 400

    # 5. Out-of-bounds validation check: Memory too low (< 32MB)
    invalid_mem_res = client.post(f"/api/containers/{cid}/resources", json={"memory_limit_mb": 10})
    assert invalid_mem_res.status_code == 422
