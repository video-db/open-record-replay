"""Tests for macOS AX hook helpers."""

from types import SimpleNamespace

import pytest

from capture.native import ax_hook_darwin as darwin


class FakeAX:
    kAXErrorSuccess = 0
    kAXRoleAttribute = "AXRole"
    kAXTitleAttribute = "AXTitle"
    kAXDescriptionAttribute = "AXDescription"
    kAXValueAttribute = "AXValue"
    kAXPositionAttribute = "AXPosition"
    kAXSizeAttribute = "AXSize"


def test_normalize_ax_result_accepts_error_value_tuple():
    assert darwin._normalize_ax_result((0, "value")) == (0, "value")


def test_normalize_ax_result_accepts_value_error_tuple():
    assert darwin._normalize_ax_result(("value", 0)) == (0, "value")


def test_ax_element_to_info_maps_role_label_and_frame(monkeypatch):
    values = {
        "AXRole": "AXTextField",
        "AXTitle": "",
        "AXDescription": "Search",
        "AXValue": "",
        "AXPosition": SimpleNamespace(x=10, y=20),
        "AXSize": SimpleNamespace(width=300, height=40),
    }

    monkeypatch.setattr(darwin, "_get_ax_module", lambda: FakeAX)
    monkeypatch.setattr(darwin, "_copy_attribute", lambda _element, attr: values[attr])

    result = darwin._ax_element_to_info(object(), 1, 2)

    assert result == {
        "x": 10,
        "y": 20,
        "width": 300,
        "height": 40,
        "label": "Search",
        "type": "AXTextField",
    }


def test_find_elements_filters_by_type_and_prefers_label(monkeypatch):
    infos = {
        "root": {"type": "AXWindow", "label": "App", "x": 0, "y": 0, "width": 10, "height": 10},
        "save": {"type": "AXButton", "label": "Save", "x": 10, "y": 10, "width": 40, "height": 20},
        "save_as": {"type": "AXButton", "label": "Save As", "x": 20, "y": 20, "width": 80, "height": 20},
        "amount": {"type": "AXTextField", "label": "Amount", "x": 30, "y": 30, "width": 80, "height": 20},
    }

    monkeypatch.setattr(darwin, "_visible_application_roots", lambda: ["root"])
    monkeypatch.setattr(darwin, "_walk_ax_elements", lambda _root: iter(infos.keys()))
    monkeypatch.setattr(darwin, "_ax_element_to_info", lambda element, _x, _y: dict(infos[element]))

    results = darwin._find_elements("AXButton", "Save", limit=10)

    assert [item["label"] for item in results] == ["Save", "Save As"]
    assert all(item["found"] for item in results)


def test_handle_message_check_permissions(monkeypatch):
    responses = []

    monkeypatch.setattr(darwin, "_is_accessibility_trusted", lambda prompt=False: prompt)
    monkeypatch.setattr(darwin, "HAS_PYNPUT", True)
    monkeypatch.setattr(darwin, "write_response", responses.append)

    darwin.handle_message({
        "id": "req-1",
        "method": "check_permissions",
        "params": {"prompt": True},
    })

    assert responses[0]["id"] == "req-1"
    assert responses[0]["status"] == "ok"
    assert responses[0]["result"]["ready_for_event_recording"] is True
