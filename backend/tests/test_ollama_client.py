from services.ollama_client import extract_json_from_response


def test_extract_plain_json():
    text = '{"analysis": "Good deck.", "queries": ["o:proliferate"]}'
    result = extract_json_from_response(text)
    assert result["analysis"] == "Good deck."
    assert result["queries"] == ["o:proliferate"]


def test_extract_json_from_markdown_code_block():
    text = '```json\n{"analysis": "Needs ramp.", "queries": ["t:artifact o:mana"]}\n```'
    result = extract_json_from_response(text)
    assert result["analysis"] == "Needs ramp."


def test_extract_json_with_surrounding_text():
    text = 'Here is the analysis:\n{"analysis": "Synergy deck.", "queries": ["o:counter"]}\nDone.'
    result = extract_json_from_response(text)
    assert result["analysis"] == "Synergy deck."


def test_extract_json_returns_none_on_failure():
    result = extract_json_from_response("This is not JSON at all.")
    assert result is None
