import re
from hmac import digest

PAGE = "/matches/whole-review"
OVERVIEW = PAGE + "/overview"
WHOLE_SETUP = PAGE + "/match"
GAME = re.compile(PAGE + r"/game/([1-9]|[12][0-9]|3[0-6])\Z")
WATCH = re.compile(PAGE + r"/watch/([0-9a-f]{64})/(status|results)\Z")


def game_scope(path):
    match = GAME.fullmatch(path)
    return int(match[1]) if match else None


def batch_page(path):
    return path in (PAGE, OVERVIEW, WHOLE_SETUP) or game_scope(path) is not None


ACTIONS = tuple(PAGE + "/" + action for action in ("start", "cancel", "resume"))

# The archive token identifies the immutable original. The separate signature
# binds its overview row to a particular opened recording and review run.
ORIGIN = re.compile(r"/matches/saved-analyses/(?P<token>[0-9a-f]{64})/from-review/"
                    r"(?P<game>[1-9]|[12][0-9]|3[0-6])/(?P<play>[1-9]|[12][0-9]|30)/"
                    r"(?P<signature>[0-9a-f]{64})(?:/(?P<destination>overview|recording|review))?\Z")


def original_path(scope, binding, token, game, play, evidence_id):
    row = f"{token}/from-review/{game}/{play}"
    signature = digest(scope.key, f"overview:{binding}:{row}:{evidence_id}".encode(),
                       "sha256").hex()
    return f"/matches/saved-analyses/{row}/{signature}"
