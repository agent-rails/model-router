from model_router import JsonlSink, TaskRequest, classify


def test_jsonl_sink_writes_and_reads_back_events(tmp_path):
    sink = JsonlSink(tmp_path / "nested" / "events.jsonl")
    classify(TaskRequest(prompt="classify this", category="classification"), emit=sink)
    classify(TaskRequest(prompt="rotate this", category="auth"), emit=sink)

    records = sink.read_all()
    assert len(records) == 2
    assert records[0]["decision"]["model"] == "claude-haiku-4-5"
    assert records[0]["category"] == "classification"
    assert records[1]["decision"]["source"] == "override"


def test_jsonl_sink_never_writes_raw_prompt(tmp_path):
    distinctive_prompt = "the-secret-marker-xyz789 classify this"
    sink = JsonlSink(tmp_path / "events.jsonl")
    classify(TaskRequest(prompt=distinctive_prompt, category="classification"), emit=sink)

    raw_contents = (tmp_path / "events.jsonl").read_text()
    assert distinctive_prompt not in raw_contents


def test_jsonl_sink_read_all_on_missing_file_returns_empty(tmp_path):
    sink = JsonlSink(tmp_path / "does_not_exist.jsonl")
    assert sink.read_all() == []


def test_jsonl_sink_expands_user_home(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    sink = JsonlSink("~/model_router_home_test/events.jsonl")
    classify(TaskRequest(prompt="classify this", category="classification"), emit=sink)
    assert (tmp_path / "model_router_home_test" / "events.jsonl").exists()
