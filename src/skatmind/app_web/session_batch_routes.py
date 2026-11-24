import re

PAGE = "/sessions/game-review"
OVERVIEW = PAGE + "/overview"
WATCH = re.compile(PAGE + r"/watch/([0-9a-f]{64})/(status|results)\Z")
ACTIONS = tuple(PAGE + "/" + name for name in ("start", "resume", "cancel"))
DECISIONS = "/sessions/decisions"
DECISION = re.compile(DECISIONS + r"/([0-9a-f]{64})\Z")
ORIGIN = re.compile(r"/sessions/saved-analyses/(?P<token>[0-9a-f]{64})/from-game/"
                    r"(?P<play>[1-9]|[12][0-9]|30)/(?P<signature>[0-9a-f]{64})"
                    r"(?:/(?P<destination>overview|recording|review))?\Z")


def review_page(path):
    return path in (PAGE, OVERVIEW, DECISIONS) or DECISION.fullmatch(path) is not None
