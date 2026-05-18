from io import BytesIO
import sys
from types import SimpleNamespace
from unittest.mock import Mock

from PIL import Image

from chandra.input import parse_range_str
from chandra.model.schema import BatchOutputItem
from chandra.scripts import http_server


# ---------------------------------------------------------------------------
# parse_range_str – 1-based user input converted to 0-based indices
# ---------------------------------------------------------------------------

def test_parse_range_str_single_page():
    """Page '1' (1-based) maps to index 0 (0-based)."""
    assert parse_range_str("1") == [0]


def test_parse_range_str_range():
    """'1-3' maps to [0, 1, 2]."""
    assert parse_range_str("1-3") == [0, 1, 2]


def test_parse_range_str_comma_separated():
    """'1,3' maps to [0, 2]."""
    assert parse_range_str("1,3") == [0, 2]


def test_parse_range_str_mixed():
    """'1-2,5' maps to [0, 1, 4]."""
    assert parse_range_str("1-2,5") == [0, 1, 4]


def test_parse_range_str_deduplicates_and_sorts():
    """Duplicate and out-of-order pages are deduplicated and sorted."""
    assert parse_range_str("3,1,2,1") == [0, 1, 2]


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
    # Verify 1-based page indices are passed to load_file so that page 1
    # (the first page) is requested, not page 0 which would skip it.
    assert load_calls == [
        {"page_range": "1"},
        {"page_range": "2"},
        {"page_range": "3"},
    ]
    # Verify the response contains one result per page
    assert len(payload["pages"]) == 3
    assert [p["page_num"] for p in payload["pages"]] == [0, 1, 2]


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


def test_process_aborts_when_memory_pressure_is_too_high(monkeypatch):
    app = http_server.app
    client = app.test_client()

    mock_model = Mock()
    mock_model.generate = Mock(return_value=[_mock_batch_output(0)])
    monkeypatch.setattr(http_server, "model", mock_model)
    monkeypatch.setattr(http_server, "model_initializing", False)
    monkeypatch.setattr(http_server, "get_memory_limit_bytes", lambda: 1000)

    fake_process = Mock()
    fake_process.memory_info.return_value = SimpleNamespace(rss=950, vms=1200)
    fake_psutil = SimpleNamespace(Process=lambda: fake_process)
    monkeypatch.setitem(sys.modules, "psutil", fake_psutil)

    monkeypatch.setattr(
        http_server,
        "load_file",
        lambda *_: [Image.new("RGB", (100, 100), "white")],
    )

    response = client.post(
        "/process",
        data={"file": (BytesIO(b"mock image"), "sample.png")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 507
    payload = response.get_json()
    assert payload["success"] is False
    assert "memory is critically high" in payload["error"]
    assert mock_model.generate.call_count == 0


def test_process_continues_when_memory_pressure_is_below_threshold(monkeypatch):
    app = http_server.app
    client = app.test_client()

    mock_model = Mock()
    mock_model.generate = Mock(return_value=[_mock_batch_output(0)])
    monkeypatch.setattr(http_server, "model", mock_model)
    monkeypatch.setattr(http_server, "model_initializing", False)
    monkeypatch.setattr(http_server, "get_memory_limit_bytes", lambda: 1000)

    fake_process = Mock()
    fake_process.memory_info.return_value = SimpleNamespace(rss=890, vms=1200)
    fake_psutil = SimpleNamespace(Process=lambda: fake_process)
    monkeypatch.setitem(sys.modules, "psutil", fake_psutil)

    monkeypatch.setattr(
        http_server,
        "load_file",
        lambda *_: [Image.new("RGB", (100, 100), "white")],
    )

    response = client.post(
        "/process",
        data={"file": (BytesIO(b"mock image"), "sample.png")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert mock_model.generate.call_count == 1


def test_process_aborts_when_available_memory_is_too_low_without_cgroup_limit(monkeypatch):
    app = http_server.app
    client = app.test_client()

    mock_model = Mock()
    mock_model.generate = Mock(return_value=[_mock_batch_output(0)])
    monkeypatch.setattr(http_server, "model", mock_model)
    monkeypatch.setattr(http_server, "model_initializing", False)
    monkeypatch.setattr(http_server, "get_memory_limit_bytes", lambda: None)

    fake_process = Mock()
    fake_process.memory_info.return_value = SimpleNamespace(rss=100, vms=1200)
    fake_virtual_memory = SimpleNamespace(available=100, total=1000)
    fake_psutil = SimpleNamespace(Process=lambda: fake_process, virtual_memory=lambda: fake_virtual_memory)
    monkeypatch.setitem(sys.modules, "psutil", fake_psutil)

    monkeypatch.setattr(
        http_server,
        "load_file",
        lambda *_: [Image.new("RGB", (100, 100), "white")],
    )

    response = client.post(
        "/process",
        data={"file": (BytesIO(b"mock image"), "sample.png")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 507
    payload = response.get_json()
    assert payload["success"] is False
    assert "memory is critically low" in payload["error"]
    assert mock_model.generate.call_count == 0


def test_process_continues_when_available_memory_is_sufficient_without_cgroup_limit(monkeypatch):
    app = http_server.app
    client = app.test_client()

    mock_model = Mock()
    mock_model.generate = Mock(return_value=[_mock_batch_output(0)])
    monkeypatch.setattr(http_server, "model", mock_model)
    monkeypatch.setattr(http_server, "model_initializing", False)
    monkeypatch.setattr(http_server, "get_memory_limit_bytes", lambda: None)

    fake_process = Mock()
    fake_process.memory_info.return_value = SimpleNamespace(rss=100, vms=1200)
    fake_virtual_memory = SimpleNamespace(available=http_server.MIN_AVAILABLE_MEMORY_BYTES + 1, total=1000)
    fake_psutil = SimpleNamespace(Process=lambda: fake_process, virtual_memory=lambda: fake_virtual_memory)
    monkeypatch.setitem(sys.modules, "psutil", fake_psutil)

    monkeypatch.setattr(
        http_server,
        "load_file",
        lambda *_: [Image.new("RGB", (100, 100), "white")],
    )

    response = client.post(
        "/process",
        data={"file": (BytesIO(b"mock image"), "sample.png")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert mock_model.generate.call_count == 1


def test_process_aborts_when_vms_exceeds_available_memory(monkeypatch):
    """Abort with 507 when VMS-RSS (memory-mapped but not yet resident) > available.

    This catches the case where model weights are lazily mapped via safetensors
    mmap and would be paged in during inference, exhausting available RAM and
    triggering the OOM killer.
    """
    app = http_server.app
    client = app.test_client()

    mock_model = Mock()
    mock_model.generate = Mock(return_value=[_mock_batch_output(0)])
    monkeypatch.setattr(http_server, "model", mock_model)
    monkeypatch.setattr(http_server, "model_initializing", False)
    monkeypatch.setattr(http_server, "get_memory_limit_bytes", lambda: None)

    # RSS=6.5 GB, VMS=25 GB → unmapped=18.5 GB; available=6.4 GB < unmapped
    rss_bytes = 6_569 * 1024 * 1024
    vms_bytes = 25_627 * 1024 * 1024
    available_bytes = 6_437 * 1024 * 1024

    fake_process = Mock()
    fake_process.memory_info.return_value = SimpleNamespace(rss=rss_bytes, vms=vms_bytes)
    fake_virtual_memory = SimpleNamespace(available=available_bytes, total=vms_bytes)
    fake_psutil = SimpleNamespace(Process=lambda: fake_process, virtual_memory=lambda: fake_virtual_memory)
    monkeypatch.setitem(sys.modules, "psutil", fake_psutil)

    monkeypatch.setattr(
        http_server,
        "load_file",
        lambda *_: [Image.new("RGB", (100, 100), "white")],
    )

    response = client.post(
        "/process",
        data={"file": (BytesIO(b"mock image"), "sample.png")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 507
    payload = response.get_json()
    assert payload["success"] is False
    assert "Not enough system memory" in payload["error"]
    assert mock_model.generate.call_count == 0


def test_process_continues_when_vms_within_available_memory(monkeypatch):
    """Proceed normally when available memory covers the VMS-RSS gap."""
    app = http_server.app
    client = app.test_client()

    mock_model = Mock()
    mock_model.generate = Mock(return_value=[_mock_batch_output(0)])
    monkeypatch.setattr(http_server, "model", mock_model)
    monkeypatch.setattr(http_server, "model_initializing", False)
    monkeypatch.setattr(http_server, "get_memory_limit_bytes", lambda: None)

    # RSS=6 GB, VMS=10 GB → unmapped=4 GB; available=8 GB > unmapped → OK
    rss_bytes = 6 * 1024 * 1024 * 1024
    vms_bytes = 10 * 1024 * 1024 * 1024
    available_bytes = 8 * 1024 * 1024 * 1024

    fake_process = Mock()
    fake_process.memory_info.return_value = SimpleNamespace(rss=rss_bytes, vms=vms_bytes)
    fake_virtual_memory = SimpleNamespace(available=available_bytes, total=16 * 1024 * 1024 * 1024)
    fake_psutil = SimpleNamespace(Process=lambda: fake_process, virtual_memory=lambda: fake_virtual_memory)
    monkeypatch.setitem(sys.modules, "psutil", fake_psutil)

    monkeypatch.setattr(
        http_server,
        "load_file",
        lambda *_: [Image.new("RGB", (100, 100), "white")],
    )

    response = client.post(
        "/process",
        data={"file": (BytesIO(b"mock image"), "sample.png")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert mock_model.generate.call_count == 1

