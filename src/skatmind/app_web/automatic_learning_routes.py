"""Private bounded automatic-Match UI routes; no Product imports."""

import re

AUTOMATIC_PAGE = "/learning/automatic"
AUTOMATIC_BODY_LIMIT = 4096
AUTOMATIC_POST_ROUTES = tuple(AUTOMATIC_PAGE + "/" + action for action in (
    "update", "exclude-preview", "cleanup-preview", "confirm", "recording"))
AUTOMATIC_VIEW = re.compile(
    r"/learning/automatic/([0-9a-f]{64})/(all|[0-9]+|source/[0-9]+|situation/[0-9]+|"
    r"evidence/[0-9]+(?:/(?:request|result|strategy-source)\.json)?|downloads/[a-z0-9-]+\.json)\Z")
AUTOMATIC_CONFIRMATION = re.compile(r"/learning/automatic/confirmation/([0-9a-f]{64})\Z")


def automatic_html_route(route):
    return (route == AUTOMATIC_PAGE or AUTOMATIC_CONFIRMATION.fullmatch(route) is not None
            or AUTOMATIC_VIEW.fullmatch(route) is not None and not route.endswith(".json"))
