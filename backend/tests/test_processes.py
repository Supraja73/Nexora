def test_process_isolation_and_namespaces(client):
    # 1. Fetch container list to get a valid container
    containers = client.get("/api/containers").json()
    assert len(containers) > 0
    cid = containers[0]["id"]

    # 2. Get processes in container
    proc_res = client.get(f"/api/containers/{cid}/processes")
    assert proc_res.status_code == 200
    pdata = proc_res.json()
    assert "pid_namespace_id" in pdata
    assert "processes" in pdata
    assert len(pdata["processes"]) > 0
    
    # Check that PID 1 exists in container namespace and has a host PID
    first_proc = pdata["processes"][0]
    assert first_proc["container_pid"] == 1
    assert first_proc["host_pid"] > 1000
    assert "command" in first_proc

    # 3. Get namespace architecture guide
    arch_res = client.get("/api/processes/architecture")
    assert arch_res.status_code == 200
    adata = arch_res.json()
    assert "namespaces" in adata
    assert len(adata["namespaces"]) >= 6
    assert "vm_vs_container_comparison" in adata

    # 4. Compare multiple containers
    if len(containers) >= 2:
        compare_payload = {"container_ids": [containers[0]["id"], containers[1]["id"]]}
        comp_res = client.post("/api/processes/compare", json=compare_payload)
        assert comp_res.status_code == 200
        comp_data = comp_res.json()
        assert comp_data["comparison_count"] == 2
        assert "observation" in comp_data
