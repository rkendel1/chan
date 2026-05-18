from io import BytesIO
from unittest.mock import Mock

from PIL import Image

from chandra.model.schema import BatchOutputItem
from chandra.scripts import http_server


def _mock_batch_output(page_num: int) -> BatchOutputItem:
    return BatchOutputItem(
        markdown=f"Page {page_num}",
        html=f"<p>Page {page_num}</p>",
        chunks={},
        raw=f"Page {page_num}",
        page_box=[0, 0, 100, 100],
        token_count=10,
        images={},
        error=False,
    )


def test_process_pdf_uses_lazy_page_loading_without_page_range(monkeypatch):
    app = http_server.app
    client = app.test_client()

    mock_model = Mock()
    call_counter = {"count": 0}

    def fake_generate(batch, **kwargs):
        page_num = call_counter["count"]
        call_counter["count"] += 1
        return [_mock_batch_output(page_num)]

    mock_model.generate = Mock(side_effect=fake_generate)
    monkeypatch.setattr(http_server, "model", mock_model)
    monkeypatch.setattr(http_server, "model_initializing", False)
    monkeypatch.setattr(http_server, "get_pdf_page_count", lambda _: 3)

    load_calls = []

    def fake_load_file(path, config):
        load_calls.append(config)
        return [Image.new("RGB", (100, 100), "white")]

    monkeypatch.setattr(http_server, "load_file", fake_load_file)

    response = client.post(
        "/process",
        data={"file": (BytesIO(b"%PDF-1.4 mock"), "sample.pdf")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["num_pages"] == 3
    assert mock_model.generate.call_count == 3
    assert load_calls == [
        {"page_range": "0"},
        {"page_range": "1"},
        {"page_range": "2"},
    ]


def test_process_pdf_falls_back_to_eager_loading_when_page_count_fails(monkeypatch):
    app = http_server.app
    client = app.test_client()

    mock_model = Mock()
    mock_model.generate = Mock(return_value=[_mock_batch_output(0)])
    monkeypatch.setattr(http_server, "model", mock_model)
    monkeypatch.setattr(http_server, "model_initializing", False)

    def fail_page_count(_):
        raise RuntimeError("boom")

    monkeypatch.setattr(http_server, "get_pdf_page_count", fail_page_count)

    load_calls = []
    eager_images = [
        Image.new("RGB", (100, 100), "white"),
        Image.new("RGB", (100, 100), "white"),
    ]

    def fake_load_file(path, config):
        load_calls.append(config)
        return eager_images

    monkeypatch.setattr(http_server, "load_file", fake_load_file)

    response = client.post(
        "/process",
        data={"file": (BytesIO(b"%PDF-1.4 mock"), "sample.pdf")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["num_pages"] == 2
    assert mock_model.generate.call_count == 2
    assert load_calls == [{}]
