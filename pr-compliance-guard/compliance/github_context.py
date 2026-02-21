import os


def get_github_context():
    return {
        "branch": os.getenv("GITHUB_HEAD_REF", ""),
        "commit_message": os.getenv("COMMIT_MESSAGE", ""),
        "pr_title": os.getenv("PR_TITLE", ""),
    }
