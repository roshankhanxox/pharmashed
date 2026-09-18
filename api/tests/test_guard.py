"""Unit tests for the numeric guard (M17)."""

from pharmashed_api.assistant.guard import check


def test_ok_when_number_in_tool_results():
    result = check(
        answer="The score is **0.62** under stated priors.",
        tool_results=[{"score": 0.62, "tier": "high"}],
    )
    assert result["status"] == "ok"


def test_ok_percentage_form():
    result = check(
        answer="62% of draws exceed RQ = 1.",
        tool_results=[{"score": 0.62}],
    )
    assert result["status"] == "ok"


def test_warn_fabricated_number():
    result = check(
        answer="The concentration is 1234.5 ng/L.",
        tool_results=[{"pec_p50": 999.0}],
    )
    assert result["status"] == "warn"
    assert "1234.5" in result["unmatched"]


def test_small_int_allowed():
    result = check(
        answer="This is the 3rd highest site out of 9.",
        tool_results=[{}],
    )
    assert result["status"] == "ok"


def test_number_in_question_allowed():
    result = check(
        answer="You asked about 5 sites.",
        tool_results=[{}],
        question="List the 5 top sites.",
    )
    assert result["status"] == "ok"


def test_rounded_form_allowed():
    result = check(
        answer="Score is 0.6.",
        tool_results=[{"score": 0.6234}],
    )
    assert result["status"] == "ok"


def test_multiple_numbers_all_matched():
    result = check(
        answer="Score 0.42, RQ p50 = 2.1, PEC = 350.0 ng/L.",
        tool_results=[{"score": 0.42, "rq_p50": 2.1, "pec_p50_ng_l": 350.0}],
    )
    assert result["status"] == "ok"


def test_unmatched_reports_all():
    result = check(
        answer="Score 0.91 and PEC 9999 ng/L.",
        tool_results=[{"score": 0.42}],
    )
    assert result["status"] == "warn"
    assert len(result["unmatched"]) >= 1


def test_empty_answer_ok():
    result = check(answer="", tool_results=[{"score": 0.5}])
    assert result["status"] == "ok"


def test_tool_results_nested():
    result = check(
        answer="Drivers: lambda rho = 0.85.",
        tool_results=[{"drivers": [{"param": "lambda", "rho": 0.85}]}],
    )
    assert result["status"] == "ok"
