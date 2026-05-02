"""Comprehensive unit tests for the `scorers` package.

Tests exact_match, numeric_close, keyword_match, json_valid, and registry.
Each test verifies that score functions return the expected shape:
    {"score": float, "passed": bool, "reason": str}
"""

from __future__ import annotations

import json

import pytest

from scorers.exact_match import score as exact_match_score
from scorers.json_valid import score as json_valid_score
from scorers.keyword_match import score as keyword_match_score
from scorers.numeric_close import score as numeric_close_score
from scorers.registry import get_scorer


# ---------------------------------------------------------------------------
# exact_match scorer
# ---------------------------------------------------------------------------


class TestExactMatchScore:
    """Tests for exact_match.score — exact string comparison after normalization."""

    # Happy path / normalization / mismatch

    @pytest.mark.parametrize(
        ("expected", "response", "expected_passed", "expected_reason_substr"),
        [
            # Exact match
            ("hello", "hello", True, "Matched expected answer"),
            # Case insensitivity
            ("Hello", "hello", True, "Matched expected answer"),
            ("HELLO", "hello", True, "Matched expected answer"),
            # Whitespace stripping
            ("  hello  ", "hello", True, "Matched expected answer"),
            ("hello", "  hello  ", True, "Matched expected answer"),
            # Mismatch
            ("hello", "world", False, "Expected 'hello' but got 'world'"),
            ("hello", "HELLOO", False, "Expected 'hello' but got 'HELLOO'"),
        ],
    )
    def test_exact_match_happy_and_normalization(
        self, expected, response, expected_passed, expected_reason_substr
    ):
        """Verify exact string match, case-insensitivity, and whitespace stripping."""
        task = {"expected": expected}
        result = exact_match_score(task, response)
        assert isinstance(result, dict)
        assert "score" in result
        assert "passed" in result
        assert "reason" in result
        assert result["passed"] is expected_passed
        assert expected_reason_substr in result["reason"]
        assert result["score"] == (1.0 if expected_passed else 0.0)

    def test_missing_expected_key(self):
        """Gracefully handle a task dict without an 'expected' key."""
        task = {}
        result = exact_match_score(task, "hello")
        assert result["score"] == 0.0
        assert result["passed"] is False
        assert "missing 'expected' or 'expected_output' key" in result["reason"]

    def test_uses_expected_output_when_expected_is_absent(self):
        """Benchmark task files use expected_output as their reference answer."""
        task = {"expected_output": "hello"}
        result = exact_match_score(task, "hello")
        assert result["score"] == 1.0
        assert result["passed"] is True

    def test_none_response(self):
        """A None response should be rejected."""
        task = {"expected": "hello"}
        result = exact_match_score(task, None)
        assert result["score"] == 0.0
        assert result["passed"] is False
        assert "None" in result["reason"]

    def test_empty_string_response(self):
        """Empty response should not match a non-empty expected value."""
        task = {"expected": "hello"}
        result = exact_match_score(task, "")
        assert result["score"] == 0.0
        assert result["passed"] is False
        assert "Expected 'hello' but got '" in result["reason"]

    def test_empty_expected_value(self):
        """Empty expected string should match an empty response after stripping."""
        task = {"expected": ""}
        result = exact_match_score(task, "")
        assert result["score"] == 1.0
        assert result["passed"] is True
        assert "Matched expected answer" in result["reason"]

    def test_empty_expected_with_whitespace_response(self):
        """Empty expected vs whitespace-only response — after strip both are empty."""
        task = {"expected": ""}
        result = exact_match_score(task, "   ")
        assert result["score"] == 1.0
        assert result["passed"] is True

    def test_none_expected_value(self):
        """Task with expected=None should be handled gracefully."""
        task = {"expected": None}
        result = exact_match_score(task, "hello")
        assert result["score"] == 0.0
        assert result["passed"] is False
        assert "None" in result["reason"]

    def test_non_string_response_coercion(self):
        """Numeric response should be coerced to string and compared."""
        task = {"expected": "42"}
        result = exact_match_score(task, 42)
        assert result["score"] == 1.0
        assert result["passed"] is True

    def test_non_string_expected_coercion(self):
        """Numeric expected should be coerced to string and compared."""
        task = {"expected": 42}
        result = exact_match_score(task, "42")
        assert result["score"] == 1.0
        assert result["passed"] is True


# ---------------------------------------------------------------------------
# numeric_close scorer
# ---------------------------------------------------------------------------


class TestNumericCloseScore:
    """Tests for numeric_close.score — number extraction and tolerance checking."""

    # Happy path / tolerance / custom tolerance

    @pytest.mark.parametrize(
        (
            "expected",
            "response",
            "tolerance",
            "expected_passed",
            "expected_reason_substr",
        ),
        [
            # Exact numeric match
            (42, "42", None, True, "within tolerance"),
            # Within tolerance (default 0.01)
            (42.0, "42.005", None, True, "within tolerance"),
            (42.0, "41.995", None, True, "within tolerance"),
            # Beyond tolerance
            (42.0, "42.02", None, False, "Expected 42.0"),
            (42.0, "41.98", None, False, "Expected 42.0"),
            # Custom tolerance 0.1
            (42.0, "42.09", 0.1, True, "within tolerance"),
            (42.0, "42.11", 0.1, False, "Expected 42.0"),
            # Negative numbers
            (-10, "-10", None, True, "within tolerance"),
            (-10.5, "-10.49", 0.1, True, "within tolerance"),
            (-10.5, "-10.61", 0.1, False, "Expected -10.5"),
            # Decimals
            (3.14, "3.14", None, True, "within tolerance"),
            (3.14159, "3.14158", 0.000001, False, "Expected 3.14159"),
            # Extract number from text
            (42.5, "The answer is 42.5", None, True, "within tolerance"),
            (
                100,
                "Speed was recorded at 100 km/h today",
                None,
                True,
                "within tolerance",
            ),
        ],
    )
    def test_numeric_close_various_cases(
        self, expected, response, tolerance, expected_passed, expected_reason_substr
    ):
        """Verify numeric extraction and tolerance logic for exact, within, and beyond."""
        task: dict = {"expected": expected}
        if tolerance is not None:
            task["tolerance"] = tolerance
        result = numeric_close_score(task, response)
        assert result["passed"] is expected_passed
        assert result["score"] == (1.0 if expected_passed else 0.0)
        assert expected_reason_substr in result["reason"]

    def test_none_response(self):
        """None response should return a clear failure."""
        task = {"expected": 42}
        result = numeric_close_score(task, None)
        assert result["score"] == 0.0
        assert result["passed"] is False
        assert "None" in result["reason"]

    def test_no_number_in_response(self):
        """Response without a number should indicate missing number."""
        task = {"expected": 42}
        result = numeric_close_score(task, "The answer is unknown")
        assert result["score"] == 0.0
        assert result["passed"] is False
        assert "No number found" in result["reason"]

    def test_missing_expected_key(self):
        """Task without 'expected' key should be handled gracefully."""
        task = {}
        result = numeric_close_score(task, "42")
        assert result["score"] == 0.0
        assert result["passed"] is False
        assert "missing 'expected' or 'expected_output' key" in result["reason"]

    def test_uses_expected_output_when_expected_is_absent(self):
        """Numeric tasks should work with the loader's expected_output field."""
        task = {"expected_output": "42"}
        result = numeric_close_score(task, "The answer is 42")
        assert result["score"] == 1.0
        assert result["passed"] is True

    def test_non_numeric_expected(self):
        """A non-numeric 'expected' value yields a parse error."""
        task = {"expected": "forty-two"}
        result = numeric_close_score(task, "42")
        assert result["score"] == 0.0
        assert result["passed"] is False
        assert "not numeric" in result["reason"]

    def test_expected_none(self):
        """expected=None should be treated as non-numeric."""
        task = {"expected": None}
        result = numeric_close_score(task, "42")
        assert result["score"] == 0.0
        assert result["passed"] is False
        assert "not numeric" in result["reason"]

    def test_non_string_response_coercion(self):
        """Numeric response should be coerced to string before regex extraction."""
        task = {"expected": 42}
        result = numeric_close_score(task, 42)
        assert result["score"] == 1.0
        assert result["passed"] is True

    def test_multiple_numbers_uses_first(self):
        """When multiple numbers appear, the first one is used for comparison."""
        task = {"expected": 10}
        result = numeric_close_score(task, "10 and 20 and 30")
        assert result["score"] == 1.0
        assert result["passed"] is True

    def test_decimal_without_leading_digit(self):
        """Regex should match numbers like .5 (decimal without leading zero)."""
        task = {"expected": 0.5}
        result = numeric_close_score(task, ".5")
        assert result["score"] == 1.0
        assert result["passed"] is True

    def test_negative_decimal_in_text(self):
        """Extract negative decimal from natural language text."""
        task = {"expected": -5.5}
        result = numeric_close_score(task, "The temperature dropped to -5.5 degrees")
        assert result["score"] == 1.0
        assert result["passed"] is True

    def test_whitespace_response(self):
        """Whitespace-only response should yield no number found."""
        task = {"expected": 1}
        result = numeric_close_score(task, "   ")
        assert result["score"] == 0.0
        assert result["passed"] is False
        assert "No number found" in result["reason"]


# ---------------------------------------------------------------------------
# keyword_match scorer
# ---------------------------------------------------------------------------


class TestKeywordMatchScore:
    """Tests for keyword_match.score — ratio of matched keywords against threshold."""

    # Happy path / partial match / none match / case insensitivity

    @pytest.mark.parametrize(
        (
            "keywords",
            "response",
            "threshold",
            "expected_passed",
            "expected_score",
            "expected_reason_substr",
        ),
        [
            # All present
            (["python", "fast"], "Python is fast", None, True, 1.0, "2/2"),
            # Partial match (2/3 = 0.6667 > default threshold 0.7 — actually fails threshold)
            (["python", "fast", "typed"], "Python is fast", None, False, 2 / 3, "2/3"),
            # No match
            (["rust", "memory"], "I love Python", None, False, 0.0, "0/2"),
            # All three present
            (
                ["python", "fast", "typed"],
                "Python is fast and typed",
                None,
                True,
                1.0,
                "3/3",
            ),
            # Case insensitivity
            (["Python"], "i love python", None, True, 1.0, "1/1"),
            # Custom threshold 0.8 — 1/2 = 0.5 should fail
            (["a", "b"], "only a", 0.8, False, 0.5, "threshold=0.8"),
            # Custom threshold 0.8 — 2/2 = 1.0 should pass
            (["a", "b"], "has a and b", 0.8, True, 1.0, "threshold=0.8"),
            # Default threshold 0.7 — 1/2 = 0.5 should fail
            (["a", "b"], "only a", None, False, 0.5, "threshold=0.7"),
            # Default threshold 0.7 -- 3/4 = 0.75 should pass
            # Use words that aren't substrings of other words in the response
            (
                ["alpha", "beta", "gamma", "delta"],
                "alpha beta and gamma",
                None,
                True,
                0.75,
                "threshold=0.7",
            ),
        ],
    )
    def test_keyword_match_various_cases(
        self,
        keywords,
        response,
        threshold,
        expected_passed,
        expected_score,
        expected_reason_substr,
    ):
        """Verify keyword ratio logic with different thresholds and match counts."""
        task: dict = {"expected_keywords": keywords}
        if threshold is not None:
            task["threshold"] = threshold
        result = keyword_match_score(task, response)
        assert result["passed"] is expected_passed
        assert result["score"] == pytest.approx(expected_score)
        assert expected_reason_substr in result["reason"]

    def test_empty_keywords_list(self):
        """An empty required keyword list should trivially pass."""
        task = {"expected_keywords": []}
        result = keyword_match_score(task, "any response at all")
        assert result["score"] == 1.0
        assert result["passed"] is True
        assert "No keywords required" in result["reason"]

    def test_missing_expected_keywords_key(self):
        """Task without 'expected_keywords' should fail gracefully."""
        task = {}
        result = keyword_match_score(task, "hello")
        assert result["score"] == 0.0
        assert result["passed"] is False
        assert (
            "missing 'expected_keywords' or 'metadata.keywords' key" in result["reason"]
        )

    def test_uses_metadata_keywords_when_expected_keywords_absent(self):
        """README task format stores keyword expectations under metadata.keywords."""
        task = {"metadata": {"keywords": ["attention", "encoder"]}}
        result = keyword_match_score(task, "Attention layers are used in an encoder.")
        assert result["score"] == 1.0
        assert result["passed"] is True

    def test_none_response(self):
        """None response should return a failure."""
        task = {"expected_keywords": ["test"]}
        result = keyword_match_score(task, None)
        assert result["score"] == 0.0
        assert result["passed"] is False
        assert "None" in result["reason"]

    def test_non_list_keywords(self):
        """Non-list expected_keywords should be rejected."""
        task = {"expected_keywords": "not-a-list"}
        result = keyword_match_score(task, "hello")
        assert result["score"] == 0.0
        assert result["passed"] is False
        assert "not a list" in result["reason"]

    def test_keywords_with_non_string_entries(self):
        """Keyword entries should be coerced to strings for matching."""
        task = {"expected_keywords": [42, "python"]}
        result = keyword_match_score(task, "The number is 42 and we use python")
        assert result["score"] == 1.0
        assert result["passed"] is True


# ---------------------------------------------------------------------------
# json_valid scorer
# ---------------------------------------------------------------------------


class TestJsonValidScore:
    """Tests for json_valid.score — JSON parse, tool match, and argument key checks."""

    # Helpers

    @staticmethod
    def _make_task(
        *,
        expected_tool: str | None = None,
        required_argument_keys: list[str] | None = None,
    ) -> dict:
        """Build a task dict with optional json_valid keys."""
        task: dict = {}
        if expected_tool is not None:
            task["expected_tool"] = expected_tool
        if required_argument_keys is not None:
            task["required_argument_keys"] = required_argument_keys
        return task

    @staticmethod
    def _make_response(
        *, tool: str | None = None, arguments: dict | None = None
    ) -> str:
        """Build a JSON response with optional tool/arguments keys."""
        payload: dict = {}
        if tool is not None:
            payload["tool"] = tool
        if arguments is not None:
            payload["arguments"] = arguments
        return json.dumps(payload)

    # Happy path

    def test_valid_json_correct_tool_and_arguments(self):
        """Full valid JSON with matching tool and all required arguments passes."""
        task = self._make_task(
            expected_tool="calculator", required_argument_keys=["a", "b"]
        )
        response = self._make_response(
            tool="calculator", arguments={"a": 1, "b": 2, "c": 3}
        )
        result = json_valid_score(task, response)
        assert result["score"] == 1.0
        assert result["passed"] is True
        assert "Tool matches" in result["reason"]
        assert "All required argument keys present" in result["reason"]
        assert "JSON parsed successfully" in result["reason"]
        assert "Tool matches" in result["reason"]
        assert "All required argument keys present" in result["reason"]

    def test_uses_metadata_tool_expectations(self):
        """README task format stores JSON scoring expectations under metadata."""
        task = {
            "metadata": {
                "expected_tool": "calculator",
                "required_argument_keys": ["a", "b"],
            }
        }
        response = self._make_response(tool="calculator", arguments={"a": 1, "b": 2})
        result = json_valid_score(task, response)
        assert result["score"] == 1.0
        assert result["passed"] is True

    # Invalid JSON

    def test_invalid_json_response(self):
        """Unparseable JSON should score 0.0."""
        task = self._make_task(expected_tool="calculator")
        result = json_valid_score(task, "not json at all")
        assert result["score"] == 0.0
        assert result["passed"] is False
        assert "Invalid JSON" in result["reason"]

    # Tool mismatch

    def test_tool_mismatch(self):
        """JSON parses but tool name does not match — partial credit."""
        task = self._make_task(expected_tool="calculator")
        response = self._make_response(tool="search_engine")
        result = json_valid_score(task, response)
        # 1 check passed (json) out of 2 total
        assert result["score"] == 0.5
        assert result["passed"] is False
        assert "Tool mismatch" in result["reason"]

    def test_missing_tool_key(self):
        """Missing tool key when expected_tool is configured should fail that check."""
        task = self._make_task(expected_tool="calculator")
        response = json.dumps({"arguments": {"a": 1}})
        result = json_valid_score(task, response)
        assert result["score"] == 0.5
        assert result["passed"] is False
        assert "Missing 'tool' key" in result["reason"]

    # Missing required argument keys

    def test_missing_required_argument_key(self):
        """Missing one required argument key fails the check."""
        task = self._make_task(
            expected_tool="calculator", required_argument_keys=["a", "b"]
        )
        response = self._make_response(tool="calculator", arguments={"a": 1})
        result = json_valid_score(task, response)
        # 2 out of 3 checks passed (json + tool match, but args fail)
        assert result["score"] == 0.6667
        assert result["passed"] is False
        assert "Missing argument keys: b" in result["reason"]

    def test_missing_arguments_key(self):
        """Missing 'arguments' top-level key when required_argument_keys is set."""
        task = self._make_task(required_argument_keys=["a"])
        response = json.dumps({"tool": "x"})
        result = json_valid_score(task, response)
        assert result["passed"] is False
        assert "Missing 'arguments' key" in result["reason"]

    def test_arguments_is_not_dict(self):
        """If 'arguments' is not an object, report type mismatch."""
        task = self._make_task(required_argument_keys=["a"])
        response = json.dumps({"tool": "x", "arguments": "not an object"})
        result = json_valid_score(task, response)
        assert result["passed"] is False
        assert "'arguments' is not an object" in result["reason"]

    # Partial credit / mixed checks

    def test_partial_credit_valid_json_wrong_tool_correct_arguments(self):
        """Valid JSON but wrong tool: 2/3 checks pass (rounded to 4 decimals)."""
        task = self._make_task(expected_tool="add", required_argument_keys=["x", "y"])
        response = self._make_response(tool="multiply", arguments={"x": 1, "y": 2})
        result = json_valid_score(task, response)
        assert result["score"] == 0.6667
        assert result["passed"] is False
        assert "Tool mismatch" in result["reason"]
        assert "All required argument keys present" in result["reason"]

    def test_partial_credit_valid_json_wrong_tool_missing_arguments(self):
        """Valid JSON but wrong tool and missing arguments: 1/3 checks pass (rounded to 4 decimals)."""
        task = self._make_task(expected_tool="add", required_argument_keys=["x", "y"])
        response = self._make_response(tool="multiply", arguments={"x": 1})
        result = json_valid_score(task, response)
        assert result["score"] == 0.3333
        assert result["passed"] is False
        assert "Tool mismatch" in result["reason"]
        assert "Missing argument keys: y" in result["reason"]

    # Validate JSON only

    def test_just_validate_json_no_tool_no_args(self):
        """When no expected_tool or required_argument_keys, just validate JSON structure."""
        task = self._make_task()
        response = json.dumps({"any": "thing"})
        result = json_valid_score(task, response)
        assert result["score"] == 1.0
        assert result["passed"] is True
        assert "JSON parsed successfully" in result["reason"]

    def test_just_validate_json_with_array(self):
        """Valid JSON array should be rejected because we expect an object (dict)."""
        task = self._make_task()
        response = json.dumps([1, 2, 3])
        result = json_valid_score(task, response)
        assert result["score"] == 0.0
        assert result["passed"] is False
        assert "list" in result["reason"]

    # Malformed response structure

    def test_none_response(self):
        """None response should be rejected."""
        task = self._make_task(expected_tool="x")
        result = json_valid_score(task, None)
        assert result["score"] == 0.0
        assert result["passed"] is False
        assert "None" in result["reason"]

    def test_non_dict_top_level_json(self):
        """Top-level JSON string should fail because it's not a dict."""
        task = self._make_task(expected_tool="x")
        result = json_valid_score(task, json.dumps("just a string"))
        assert result["passed"] is False
        assert "str" in result["reason"]

    def test_required_argument_keys_not_a_list(self):
        """If required_argument_keys is not a list, report type instead of checking."""
        task = {"expected_tool": "x", "required_argument_keys": "not-a-list"}
        response = self._make_response(tool="x", arguments={"a": 1})
        result = json_valid_score(task, response)
        # 2 out of 3 checks pass (json + tool), arguments check becomes a reason
        assert result["score"] == 0.6667
        assert result["passed"] is False
        assert "not a list" in result["reason"]

    def test_whitespace_around_json_is_stripped(self):
        """Leading/trailing whitespace around JSON should be tolerated."""
        task = self._make_task(expected_tool="weather")
        response = "   " + self._make_response(tool="weather") + "\n\t"
        result = json_valid_score(task, response)
        assert result["score"] == 1.0
        assert result["passed"] is True

    def test_empty_string_response(self):
        """Empty string response should fail JSON parsing."""
        task = self._make_task()
        result = json_valid_score(task, "")
        assert result["score"] == 0.0
        assert result["passed"] is False
        assert "Invalid JSON" in result["reason"]


# ---------------------------------------------------------------------------
# registry
# ---------------------------------------------------------------------------


class TestRegistry:
    """Tests for registry.get_scorer — scorer name resolution."""

    @pytest.mark.parametrize(
        "name",
        ["exact_match", "numeric_close", "keyword_match", "json_valid"],
    )
    def test_get_valid_scorer_by_name(self, name):
        """Each supported scorer name should resolve to a callable."""
        scorer = get_scorer(name)
        assert callable(scorer)

    def test_get_scorer_returns_actual_function(self):
        """Ensure returned function is the real module function."""
        assert get_scorer("exact_match") is exact_match_score
        assert get_scorer("numeric_close") is numeric_close_score
        assert get_scorer("keyword_match") is keyword_match_score
        assert get_scorer("json_valid") is json_valid_score

    def test_get_scorer_callable_signature(self):
        """Ensure returned callable accepts (task, response) and returns a dict."""
        scorer = get_scorer("exact_match")
        result = scorer({"expected": "hi"}, "hi")
        assert isinstance(result, dict)
        assert "score" in result
        assert "passed" in result
        assert "reason" in result

    def test_unknown_scorer_raises_value_error(self):
        """Requesting an unregistered scorer should raise a clear ValueError."""
        with pytest.raises(
            ValueError, match="Unknown scorer: 'fancy_scorer'.*Supported:"
        ):
            get_scorer("fancy_scorer")

    def test_unknown_scorer_error_message_includes_supported(self):
        """The error message should list supported scorers."""
        with pytest.raises(ValueError) as exc_info:
            get_scorer("unknown")
        message = str(exc_info.value)
        assert "exact_match" in message
        assert "numeric_close" in message
        assert "keyword_match" in message
        assert "json_valid" in message

    def test_empty_string_name_raises(self):
        """Empty string is not a valid scorer name."""
        with pytest.raises(ValueError, match="Unknown scorer: ''"):
            get_scorer("")

    def test_none_name_raises_value_error(self):
        """None is not registered and should raise ValueError (registry.get returns None)."""
        with pytest.raises(ValueError, match="Unknown scorer: None"):
            get_scorer(None)
