"""Private saved-Review route vocabulary, without Product imports."""

import re

SAVED_REVIEWS = "/review/saved"
HISTORICAL_EXECUTION_DOWNLOAD = re.compile(
    r"/review/execution/([0-9a-f]{64})/(request|result)\.json\Z")
HISTORICAL_POST_ROUTES = tuple("/review/" + action for action in (
    "reopen", "delete-preview", "delete-confirm", "retry-saving"))
HISTORICAL_VIEW = re.compile(
    r"/review/saved/([0-9a-f]{64})/(source|evidence|delete)/([0-9]+)"
    r"(?:/(request|result)\.json)?\Z")


def historical_html_route(path):
    return path == SAVED_REVIEWS or (HISTORICAL_VIEW.fullmatch(path) is not None
                                    and not path.endswith(".json"))
