"""检索链路测试：验证提问能命中示例文档并返回带引用的答案。"""


def test_query_hits_sample_documents(client):
    resp = client.post("/api/query", json={"question": "什么是 RAG？它解决了什么问题？"})
    assert resp.status_code == 200, resp.text
    body = resp.json()

    # 没有配置 LLM Key 时走抽取式回答
    assert body["mode"] == "extractive"
    assert body["model"] is None
    assert body["answer"].strip()

    # 必须命中示例文档并返回引用
    citations = body["citations"]
    assert len(citations) >= 1
    assert any("rag" in c["source"].lower() for c in citations), citations
    # 分数在合法范围内且按相关度降序
    scores = [c["score"] for c in citations]
    assert all(0.0 <= s <= 1.0 for s in scores)
    assert scores == sorted(scores, reverse=True)
    # 引用编号从 1 开始连续
    assert [c["ref"] for c in citations] == list(range(1, len(citations) + 1))

    # 教学字段：返回增强后的 prompt 和各步骤耗时
    assert "【资料】" in body["prompt"]
    assert "【问题】" in body["prompt"]
    for key in ("embed_ms", "retrieve_ms", "generate_ms"):
        assert key in body["timings"]


def test_query_returns_relevant_chunk_content(client):
    resp = client.post("/api/query", json={"question": "chunk_overlap 重叠有什么作用？", "top_k": 3})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["citations"]) <= 3
    # 至少有一条引用内容与切块相关
    combined = "".join(c["text"] for c in body["citations"])
    assert "重叠" in combined or "切块" in combined or "chunk" in combined.lower()


def test_top_k_limits_citation_count(client):
    resp = client.post("/api/query", json={"question": "向量检索的原理", "top_k": 1})
    assert resp.status_code == 200
    assert len(resp.json()["citations"]) == 1
