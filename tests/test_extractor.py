from __future__ import annotations

from unittest.mock import patch

from writing_tool.extractor import _parse_response, extract


class MockChoice:
    def __init__(self, content: str) -> None:
        self.message = MockMessage(content)


class MockMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class MockResponse:
    def __init__(self, content: str) -> None:
        self.choices = [MockChoice(content)]


class TestParseResponse:
    def test_valid_json(self) -> None:
        data = '{"entities": [{"label": "A", "type": "character", "props": {}}], "relationships": []}'
        result = _parse_response(data)
        assert len(result["entities"]) == 1
        assert result["entities"][0]["label"] == "A"

    def test_with_code_fence(self) -> None:
        data = '```json\n{"entities": [], "relationships": []}\n```'
        result = _parse_response(data)
        assert result == {"entities": [], "relationships": []}

    def test_invalid_json(self) -> None:
        result = _parse_response("not json at all")
        assert result == {"entities": [], "relationships": []}

    def test_not_a_dict(self) -> None:
        result = _parse_response('["list"]')
        assert result == {"entities": [], "relationships": []}

    def test_non_list_entities(self) -> None:
        data = '{"entities": "bad", "relationships": []}'
        result = _parse_response(data)
        assert result["entities"] == []

    def test_non_list_relationships(self) -> None:
        data = '{"entities": [], "relationships": "bad"}'
        result = _parse_response(data)
        assert result["relationships"] == []

    def test_props_not_dict(self) -> None:
        data = '{"entities": [{"label": "A", "type": "char", "props": "bad"}], "relationships": []}'
        result = _parse_response(data)
        assert result["entities"][0]["props"] == {}


class TestExtract:
    @patch("writing_tool.extractor.completion")
    def test_extract_calls_llm(self, mock_completion: object) -> None:
        mock_completion.return_value = MockResponse(  # type: ignore[assignment]
            '{"entities": [{"label": "Max", "type": "character", "props": {"age": 30}}], "relationships": []}'
        )
        result = extract("Max is 30 years old.")
        assert len(result["entities"]) == 1
        assert result["entities"][0]["label"] == "Max"

    @patch("writing_tool.extractor.completion")
    def test_extract_empty_response(self, mock_completion: object) -> None:
        mock_completion.return_value = MockResponse(None)  # type: ignore[assignment]
        result = extract("text")
        assert result == {"entities": [], "relationships": []}
