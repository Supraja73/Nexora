def test_security_validations(client):
    # 1. Invalid container name with dangerous characters
    bad_name_payload = {
        "name": "bad;rm -rf /;test",
        "image": "alpine:latest",
        "cpu_limit": 1.0,
        "memory_limit_mb": 256
    }
    res1 = client.post("/api/containers", json=bad_name_payload)
    assert res1.status_code == 422 # Pydantic regex validator rejection

    # 2. Name with path traversal
    traversal_payload = {
        "name": "../../etc/shadow",
        "image": "alpine:latest",
        "cpu_limit": 1.0,
        "memory_limit_mb": 256
    }
    res2 = client.post("/api/containers", json=traversal_payload)
    assert res2.status_code == 422

    # 3. Disallowed image
    unauthorized_img_payload = {
        "name": "malicious-app",
        "image": "evil-hacker-repo/backdoor:v1",
        "cpu_limit": 1.0,
        "memory_limit_mb": 256
    }
    res3 = client.post("/api/containers", json=unauthorized_img_payload)
    assert res3.status_code == 400
    assert "not permitted by NEXORA security policy" in res3.json()["detail"]

    # 4. Prohibited port mapping: mapping host port 22 (SSH)
    ssh_port_payload = {
        "name": "port-hijack-test",
        "image": "alpine:latest",
        "cpu_limit": 1.0,
        "memory_limit_mb": 256,
        "port_mapping": "22:80"
    }
    res4 = client.post("/api/containers", json=ssh_port_payload)
    assert res4.status_code == 400
    assert "reserved for sensitive host services" in res4.json()["detail"]

    # 5. Invalid port range (negative or > 65535)
    invalid_port_payload = {
        "name": "invalid-port-range",
        "image": "alpine:latest",
        "cpu_limit": 1.0,
        "memory_limit_mb": 256,
        "port_mapping": "99999:80"
    }
    res5 = client.post("/api/containers", json=invalid_port_payload)
    assert res5.status_code == 422 or res5.status_code == 400
