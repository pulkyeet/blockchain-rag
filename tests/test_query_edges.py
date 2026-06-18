"""
Edge case tests for Phase 1 RAG pipeline. Requires API server running on localhost:8000
and corpus already seeded (reentrancy + 5 topic docs).
Run: pytest tests/test_query_edges.py -v
"""
import json
import time

import httpx
import pytest

BASE_URL = "http://localhost:8000/api/v1"


def parse_sse(text: str) -> list[dict]:
    events = []
    for line in text.splitlines():
        if line.startswith("data: "):
            events.append(json.loads(line[len("data: "):]))
    return events


def get_chunks_event(text: str) -> dict | None:
    for e in parse_sse(text):
        if e.get("type") == "chunks":
            return e
    return None


def get_full_answer(text: str) -> str:
    return "".join(e["content"] for e in parse_sse(text) if e.get("type") == "token")


class TestEmptyQuery:
    def test_empty_string_query(self):
        resp = httpx.post(f"{BASE_URL}/query", json={"query": "", "top_k": 3}, timeout=30.0)
        assert resp.status_code != 500, f"empty query crashed the server: {resp.text}"

    def test_whitespace_only_query(self):
        resp = httpx.post(f"{BASE_URL}/query", json={"query": "   ", "top_k": 3}, timeout=30.0)
        assert resp.status_code != 500


class TestZeroRelevantContext:
    def test_query_unrelated_to_corpus(self):
        resp = httpx.post(
            f"{BASE_URL}/query",
            json={"query": "what is the recipe for a classic margherita pizza", "top_k": 3},
            timeout=30.0,
        )
        assert resp.status_code == 200
        answer = get_full_answer(resp.text).lower()
        insufficient_markers = ["insufficient", "does not contain", "do not contain", "no relevant",
                                  "cannot answer", "not provided", "context does not"]
        flagged = any(m in answer for m in insufficient_markers)
        if not flagged:
            pytest.fail(
                f"Possible hallucination on out-of-corpus query. Answer was:\n{answer[:500]}\n"
                "Manually verify whether this is a false negative or a real hallucination."
            )


class TestLongDocChunking:
    def test_multi_chunk_doc_splits_correctly(self):
        long_text = (
            "Section A discusses the Byzantine Generals Problem as the foundational "
            "distributed systems challenge that blockchain consensus mechanisms solve. " * 40
            + " UNIQUE_MARKER_START specific detail about quantum-resistant signature schemes "
            "using lattice-based cryptography for post-quantum blockchain security. "
            + "Section B discusses validator slashing conditions in proof-of-stake systems. " * 40
            + " UNIQUE_MARKER_END specific detail about sharding and how it partitions "
            "validator sets across multiple chains to increase throughput."
        )
        ingest_resp = httpx.post(
            f"{BASE_URL}/ingest",
            json={"text": long_text, "source": "test_long_doc_temp", "doc_type": "docs"},
            timeout=60.0,
        )
        assert ingest_resp.status_code == 200, ingest_resp.text
        result = ingest_resp.json()
        assert result["status"] == "ok"
        assert result["chunks_created"] > 1, (
            f"expected multiple chunks for ~400+ token doc, got {result['chunks_created']}"
        )

        time.sleep(1)

        start_resp = httpx.post(
            f"{BASE_URL}/query",
            json={"query": "quantum-resistant signature schemes lattice-based cryptography", "top_k": 5},
            timeout=30.0,
        )
        chunks_event = get_chunks_event(start_resp.text)
        assert chunks_event is not None
        found_start = any(
            "UNIQUE_MARKER_START" in c["text"] for c in chunks_event["chunks"]
        )
        assert found_start, "could not retrieve chunk containing start-of-doc unique marker"

        end_resp = httpx.post(
            f"{BASE_URL}/query",
            json={"query": "sharding partitions validator sets across multiple chains", "top_k": 5},
            timeout=30.0,
        )
        chunks_event = get_chunks_event(end_resp.text)
        assert chunks_event is not None
        found_end = any(
            "UNIQUE_MARKER_END" in c["text"] for c in chunks_event["chunks"]
        )
        assert found_end, "could not retrieve chunk containing end-of-doc unique marker"


class TestDuplicateDetection:
    def test_byte_identical_duplicate_is_skipped(self):
        text = "This is a fixed test sentence for duplicate detection. UNIQUE_DEDUP_TEST_TOKEN_001."
        first = httpx.post(
            f"{BASE_URL}/ingest",
            json={"text": text, "source": "test_dedup_temp", "doc_type": "docs"},
            timeout=30.0,
        )
        assert first.status_code == 200, first.text
        assert first.json()["status"] == "ok"
        assert first.json()["chunks_created"] >= 1

        second = httpx.post(
            f"{BASE_URL}/ingest",
            json={"text": text, "source": "test_dedup_temp", "doc_type": "docs"},
            timeout=30.0,
        )
        assert second.status_code == 200, second.text
        assert second.json()["status"] == "already exists"
        assert second.json()["chunks_created"] == 0

    def test_near_duplicate_is_not_deduped(self):
        original = "Reentrancy occurs when an external call allows an attacker to re-enter a function before state updates complete."
        reworded = "A reentrancy bug happens when an external call lets an attacker call back into a function before the state has finished updating."

        httpx.post(f"{BASE_URL}/ingest",
                   json={"text": original, "source": "test_neardup_temp", "doc_type": "docs"},
                   timeout=30.0)
        second = httpx.post(f"{BASE_URL}/ingest",
                             json={"text": reworded, "source": "test_neardup_temp", "doc_type": "docs"},
                             timeout=30.0)
        assert second.status_code == 200
        result = second.json()
        assert result["status"] == "ok"
        assert result["chunks_created"] >= 1
