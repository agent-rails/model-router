from model_router import InMemorySink, TaskRequest, classify


def test_sink_records_every_decision():
    sink = InMemorySink()
    classify(TaskRequest(prompt="classify this", category="classification"), emit=sink)
    classify(TaskRequest(prompt="production deploy plan"), emit=sink)
    assert len(sink.events) == 2


def test_sink_filters_keyword_flagged():
    sink = InMemorySink()
    classify(TaskRequest(prompt="classify this", category="classification"), emit=sink)
    classify(TaskRequest(prompt="production deploy plan"), emit=sink)
    flagged = sink.keyword_flagged()
    assert len(flagged) == 1
    assert flagged[0].category is None


def test_event_captures_task_metadata():
    sink = InMemorySink()
    classify(
        TaskRequest(prompt="hello", category="chat", tool_schema_count=3, is_agentic=True),
        emit=sink,
    )
    event = sink.events[0]
    assert event.category == "chat"
    assert event.tool_schema_count == 3
    assert event.is_agentic is True
    assert event.prompt_chars == len("hello")
