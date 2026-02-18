import re

def branch_is_valid(branch_name: str, pattern: str) -> bool:
    return bool(re.match(pattern, branch_name))


def commit_is_valid(message: str, forbidden_words: list[str]) -> bool:
    return not any(word in message for word in forbidden_words)


def pr_has_jira(title: str, pattern: str) -> bool:
    return bool(re.search(pattern, title))
