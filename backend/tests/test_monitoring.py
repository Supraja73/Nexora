def test_monitoring_and_analytics(client):
    # 1. Overview metrics
    overview_res = client.get("/api/monitoring/overview")
    assert overview_res.status_code == 200
    odata = overview_res.json()
    assert "total_containers" in odata
    assert "running_containers" in odata
    assert "avg_cpu_percent" in odata
    assert "total_memory_used_mb" in odata
    assert "host_cpu_percent" in odata

    # 2. History metrics
    hist_res = client.get("/api/monitoring/history?minutes=30")
    assert hist_res.status_code == 200
    hdata = hist_res.json()
    assert "total_points" in hdata
    assert "timeline" in hdata

    # 3. Analytics overview
    analytics_res = client.get("/api/analytics/overview?timeframe=60")
    assert analytics_res.status_code == 200
    adata = analytics_res.json()
    assert "timeline" in adata
    assert "container_distribution" in adata

    # 4. Activity log
    act_res = client.get("/api/activity")
    assert act_res.status_code == 200
    act_data = act_res.json()
    assert "items" in act_data
    assert len(act_data["items"]) > 0
