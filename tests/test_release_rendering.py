from __future__ import annotations

from collections import defaultdict

import pytest

from ratewall.release import _final_paper_quarto_text


def _release_context(impulse_row: dict[str, str]) -> dict[str, object]:
    context: defaultdict[str, object] = defaultdict(list)
    context["sources"] = []
    context["impulse"] = [impulse_row]
    return context


def test_final_paper_renders_public_interest_gdp_share_as_percent() -> None:
    text = _final_paper_quarto_text(
        _release_context(
            {
                "horizon": "1y",
                "annualized_public_interest_impulse_bil": "180",
                "annualized_public_interest_impulse_gdp_share": "0.005645",
            }
        ),
        [],
    )

    assert (
        "annualized public-interest impulse is `180` billion dollars, or `0.5645` "
        "percent of GDP in the generated table."
    ) in text


def test_final_paper_missing_public_interest_gdp_share_fails_loudly() -> None:
    context = _release_context(
        {
            "horizon": "1y",
            "annualized_public_interest_impulse_bil": "180",
        }
    )

    with pytest.raises(
        KeyError, match="annualized_public_interest_impulse_gdp_share"
    ):
        _final_paper_quarto_text(context, [])
