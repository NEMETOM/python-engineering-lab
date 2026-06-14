REQUIRED_TAGS = ["35", "55", "54", "44", "38"]


def validate_fix(msg: dict):

    for tag in REQUIRED_TAGS:
        if tag not in msg:
            raise ValueError(f"missing tag {tag}")

    if msg["35"] != "D":
        raise ValueError("only NewOrderSingle supported")

    return True
