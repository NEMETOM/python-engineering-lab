from behave import then


@then("the order is {outcome}")
def step_then_outcome(context, outcome):
    assert outcome in ("approved", "rejected"), f"Unknown outcome: {outcome}"
    if outcome == "approved":
        assert context.decision.approved, (
            f"Expected approved but got rejected: {context.decision.reason}"
        )
    else:
        assert not context.decision.approved, "Expected rejected but got approved"


@then('the rejection reason mentions "{keyword}"')
def step_then_rejection_reason(context, keyword):
    assert context.decision.reason is not None, "No rejection reason set"
    assert keyword in context.decision.reason, (
        f"Expected '{keyword}' in reason: '{context.decision.reason}'"
    )
