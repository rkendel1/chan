from chandra.scripts import http_server


def test_initialize_model_defaults_to_hf(monkeypatch):
    captured = {}

    monkeypatch.setattr(http_server, "model", None)
    monkeypatch.setattr(http_server, "model_initializing", False)
    monkeypatch.delenv("INFERENCE_METHOD", raising=False)

    def fake_manager(method):
        captured["method"] = method
        return object()

    monkeypatch.setattr(http_server, "InferenceManager", fake_manager)

    http_server.initialize_model()

    assert captured["method"] == "hf"


def test_main_uses_hf_when_inference_method_is_not_set(monkeypatch):
    captured = {}

    monkeypatch.delenv("INFERENCE_METHOD", raising=False)
    monkeypatch.setattr(
        http_server,
        "initialize_model",
        lambda method: captured.setdefault("method", method),
    )
    monkeypatch.setattr(
        http_server.app,
        "run",
        lambda **kwargs: captured.setdefault("run_kwargs", kwargs),
    )

    http_server.main()

    assert captured["method"] == "hf"
    assert captured["run_kwargs"]["port"] == 5000
