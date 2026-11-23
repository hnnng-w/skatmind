import re
from hmac import digest

PAGE = "/matches/whole-review"
OVERVIEW = PAGE + "/overview"
ACTIONS = tuple(PAGE + "/" + action for action in ("start", "cancel", "resume"))

# The archive token identifies the immutable original. The separate signature
# binds its overview row to a particular opened recording and review run.
ORIGIN = re.compile(r"/matches/saved-analyses/(?P<token>[0-9a-f]{64})/from-review/"
                    r"(?P<game>[1-9]|[12][0-9]|3[0-6])/(?P<play>[1-9]|[12][0-9]|30)/"
                    r"(?P<signature>[0-9a-f]{64})(?:/(?P<destination>overview|recording))?\Z")


def original_path(scope, binding, token, game, play, evidence_id):
    row = f"{token}/from-review/{game}/{play}"
    signature = digest(scope.key, f"overview:{binding}:{row}:{evidence_id}".encode(),
                       "sha256").hex()
    return f"/matches/saved-analyses/{row}/{signature}"
