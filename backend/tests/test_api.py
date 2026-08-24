"""API 冒烟测试：健康检查、配置、上传/列表/切块/删除、参数校验。"""


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    # 启动时自动导入了 samples/ 示例文档
    assert body["num_documents"] >= 2
    assert body["num_chunks"] > 0


def test_settings_does_not_leak_secrets(client):
    resp = client.get("/api/settings")
    assert resp.status_code == 200
    body = resp.json()
    assert body["chunk_size"] > 0
    assert body["top_k"] > 0
    assert "all-MiniLM-L6-v2" in body["embedding_model"]
    # 绝不能返回密钥本身，只返回布尔状态
    assert "openai_api_key" not in body
    assert body["openai_api_key_set"] is False
    assert body["llm_active"] is False


def test_empty_question_rejected(client):
    resp = client.post("/api/query", json={"question": "   "})
    assert resp.status_code == 422
    assert "问题不能为空" in resp.text


def test_invalid_top_k_rejected(client):
    resp = client.post("/api/query", json={"question": "什么是RAG", "top_k": 0})
    assert resp.status_code == 422


def test_upload_list_chunks_delete_roundtrip(client):
    # 上传
    content = ("测试文档：月球上没有大气层，因此声音无法传播。" * 30).encode("utf-8")
    resp = client.post(
        "/api/documents",
        files={"file": ("moon-test.txt", content, "text/plain")},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    doc = body["document"]
    assert doc["filename"] == "moon-test.txt"
    assert doc["num_chunks"] >= 1
    assert set(body["timings"]) == {"ingest_ms", "chunk_ms", "embed_ms", "index_ms"}
    doc_id = doc["id"]

    # 列表中能找到
    resp = client.get("/api/documents")
    assert resp.status_code == 200
    assert any(d["id"] == doc_id for d in resp.json())

    # 切块预览
    resp = client.get(f"/api/documents/{doc_id}/chunks")
    assert resp.status_code == 200
    chunks = resp.json()["chunks"]
    assert len(chunks) == doc["num_chunks"]
    assert chunks[0]["chunk_index"] == 0
    assert "月球" in chunks[0]["text"]

    # 删除
    resp = client.delete(f"/api/documents/{doc_id}")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    # 再删一次应 404，且错误信息友好
    resp = client.delete(f"/api/documents/{doc_id}")
    assert resp.status_code == 404
    assert "不存在" in resp.json()["detail"]


def test_unsupported_file_type_rejected(client):
    resp = client.post(
        "/api/documents",
        files={"file": ("evil.exe", b"binary", "application/octet-stream")},
    )
    assert resp.status_code == 400
    assert "暂不支持" in resp.json()["detail"]


def test_empty_file_rejected(client):
    resp = client.post(
        "/api/documents",
        files={"file": ("empty.txt", b"", "text/plain")},
    )
    assert resp.status_code == 400
