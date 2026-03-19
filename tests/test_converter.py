"""Tests for the file-converter tool."""

import json
import os
import sys
from io import BytesIO
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools", "file-converter"))
import convert


class TestCSVConversions:
    """Tests for CSV/TSV conversions."""

    def test_csv_to_json(self):
        csv_content = "name,age,city\nAlice,30,London\nBob,25,Paris"
        result = convert.convert(csv_content, "csv", "json")
        assert "error" not in result
        assert result["rows"] == 2
        assert result["columns"] == ["name", "age", "city"]
        assert result["data"][0]["name"] == "Alice"

    def test_tsv_to_json(self):
        tsv_content = "name\tage\nAlice\t30\nBob\t25"
        result = convert.convert(tsv_content, "tsv", "json")
        assert result["rows"] == 2
        assert result["data"][0]["name"] == "Alice"

    def test_json_to_csv(self):
        json_content = json.dumps(
            [
                {"name": "Alice", "age": 30},
                {"name": "Bob", "age": 25},
            ]
        )
        result = convert.convert(json_content, "json", "csv")
        assert "error" not in result
        assert result["rows"] == 2
        assert "Alice" in result["data"]

    def test_json_to_csv_with_data_key(self):
        json_content = json.dumps({"data": [{"name": "Alice"}, {"name": "Bob"}]})
        result = convert.convert(json_content, "json", "csv")
        assert result["rows"] == 2

    def test_json_to_csv_invalid(self):
        result = convert.convert('"just a string"', "json", "csv")
        assert "error" in result

    def test_csv_to_tsv(self):
        csv_content = "a,b\n1,2"
        result = convert.convert(csv_content, "csv", "tsv")
        assert "error" not in result
        assert "\t" in result["data"]


class TestHTMLConversions:
    """Tests for HTML conversions."""

    def test_html_to_text(self):
        html = "<h1>Title</h1><p>Hello <b>world</b></p>"
        result = convert.convert(html, "html", "text")
        assert "Title" in result["data"]
        assert "Hello" in result["data"]
        assert "<h1>" not in result["data"]

    def test_html_to_json_with_table(self):
        html = "<table><tr><th>Name</th><th>Age</th></tr><tr><td>Alice</td><td>30</td></tr></table>"
        result = convert.convert(html, "html", "json")
        assert result["table_count"] == 1
        assert result["tables"][0]["headers"] == ["Name", "Age"]

    def test_html_to_json_no_tables(self):
        html = "<p>Just text</p>"
        result = convert.convert(html, "html", "json")
        assert "No tables found" in result.get("note", "")


class TestMarkdownConversions:
    """Tests for Markdown conversions."""

    def test_markdown_to_text(self):
        md = "# Title\n\nHello **world**"
        result = convert.convert(md, "markdown", "text")
        assert "Title" in result["data"]
        assert "**" not in result["data"]

    def test_markdown_to_html(self):
        md = "# Title\n\n**bold**"
        result = convert.convert(md, "markdown", "html")
        assert "<h1>" in result["data"]
        assert "<strong>" in result["data"]

    def test_md_alias(self):
        md = "# Test"
        result = convert.convert(md, "md", "text")
        assert "error" not in result


class TestXMLConversions:
    """Tests for XML conversions."""

    def test_xml_to_json(self):
        xml = "<root><item>hello</item></root>"
        result = convert.convert(xml, "xml", "json")
        assert result["data"]["root"]["item"] == "hello"

    def test_xml_to_json_invalid(self):
        result = convert.convert("not xml", "xml", "json")
        assert "error" in result

    def test_json_to_xml(self):
        data = json.dumps({"root": {"item": "hello"}})
        result = convert.convert(data, "json", "xml")
        assert "error" not in result
        assert "<item>hello</item>" in result["data"]


class TestUnsupportedConversion:
    def test_unsupported_path(self):
        result = convert.convert("data", "pdf", "csv")
        assert "error" in result
        assert "Unsupported conversion" in result["error"]


class TestListConversions:
    def test_list_conversions(self):
        result = convert.list_conversions()
        assert result["count"] > 0
        assert all("from" in c and "to" in c for c in result["conversions"])


class TestConvertHandler:
    """Tests for the HTTP handler."""

    def _make_handler(self, path):
        handler = convert.ConvertHandler.__new__(convert.ConvertHandler)
        handler.path = path
        handler.headers = {}
        handler.wfile = BytesIO()
        handler.requestline = "GET / HTTP/1.1"
        handler.client_address = ("127.0.0.1", 0)
        handler.request_version = "HTTP/1.1"
        return handler

    def test_health_endpoint(self):
        handler = self._make_handler("/health")
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.do_GET()
        handler.send_response.assert_called_with(200)
        body = json.loads(handler.wfile.getvalue())
        assert body["status"] == "ok"

    def test_conversions_endpoint(self):
        handler = self._make_handler("/conversions")
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.do_GET()
        handler.send_response.assert_called_with(200)
        body = json.loads(handler.wfile.getvalue())
        assert "conversions" in body
