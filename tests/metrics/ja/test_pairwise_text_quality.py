import pytest

from langcheck.metrics.ja.pairwise_text_quality import pairwise_comparison
from tests.utils import MockEvalClient

################################################################################
# Tests
################################################################################


@pytest.mark.parametrize(
    "generated_outputs_a,generated_outputs_b,prompts,sources_a,sources_b,reference_outputs",
    [
        (
            "東京は日本の首都です。",
            "ニューヨークは日本の首都です。",
            "日本の首都は何ですか？",
            None,
            None,
            None,
        ),
        (
            "東京は日本の首都です。",
            "ニューヨークは日本の首都です。",
            "日本の首都は何ですか？",
            None,
            None,
            "東京",
        ),
        (
            "東京は日本の首都です。",
            "ニューヨークは日本の首都です。",
            "日本の首都は何ですか？",
            "日本の首都 = 東京",
            None,
            None,
        ),
        (
            "東京は日本の首都です。",
            "ニューヨークは日本の首都です。",
            "日本の首都は何ですか？",
            "日本の首都 = 東京",
            "日本の首都 = 東京",
            None,
        ),
        (
            "東京は日本の首都です。",
            "ニューヨークは日本の首都です。",
            "日本の首都は何ですか？",
            "日本の首都 = 東京",
            "日本の首都 = 東京",
            "東京",
        ),
    ],
)
def test_pairwise_comparison_eval_client(
    generated_outputs_a,
    generated_outputs_b,
    prompts,
    sources_a,
    sources_b,
    reference_outputs,
):
    """Test the pairwise_comparison function.

    Test 1: No sources or reference outputs are provided.
    Test 2: Reference output is provided.
    Test 3: Source A is provided.
    Test 4: Both Source A and Source B are provided.
    Test 5: Source A, Source B, and the reference output are provided.
    """
    eval_client = MockEvalClient("Tie")
    metric_value = pairwise_comparison(
        generated_outputs_a,
        generated_outputs_b,
        prompts,
        sources_a=sources_a,
        sources_b=sources_b,
        reference_outputs=reference_outputs,
        eval_model=eval_client,
    )

    # MockEvalClient returns 0.5 for Tie
    assert metric_value == 0.5


@pytest.mark.parametrize(
    "generated_outputs_a,generated_outputs_b,prompts,sources_a,sources_b,reference_outputs",
    [
        (
            "東京は日本の首都です。",
            "ニューヨークは日本の首都です。",
            "日本の首都は何ですか？",
            None,
            None,
            None,
        )
    ],
)
def test_pairwise_comparison_inconsistency_eval_client(
    generated_outputs_a,
    generated_outputs_b,
    prompts,
    sources_a,
    sources_b,
    reference_outputs,
):
    """Test the pairwise_comparison function when inconsistent scores are
    returned when Model A and Model B are swapped.
    """
    # If Response A is selected for both the original order (Model A vs. Model
    # B) and the swapped order (Model B vs. Model A), then the results are
    # inconsistent.

    # We simulate the situation by setting the return value of the
    # MockEvalClient to 1. (Response B is better)
    eval_client = MockEvalClient("Response B")
    metric_value = pairwise_comparison(
        generated_outputs_a,
        generated_outputs_b,
        prompts,
        sources_a=sources_a,
        sources_b=sources_b,
        reference_outputs=reference_outputs,
        eval_model=eval_client,
    )

    # The score should be None if the results are inconsistent
    assert metric_value.metric_values[0] is None
