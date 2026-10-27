"""Shared exact captured Match/version captions; labels never authorize a source."""

from collections import Counter

from .stateful_localization import managed_name, text


def version_labels(locale, snapshots):
    counts = Counter(snapshot["workspace_revision"] for snapshot in snapshots)
    seen = Counter()
    labels = {}
    for snapshot in snapshots:
        revision = snapshot["workspace_revision"]
        seen[revision] += 1
        label = text(locale, "task.learning.saved_revision", revision=revision)
        if counts[revision] > 1:
            label = text(locale, "task.learning.version_variant",
                         revision_label=label, number=seen[revision])
        labels[snapshot["match_snapshot_id"]] = label
    return labels


def snapshot_labels(state, locale, profile=None, recorded=(), snapshots=()):
    titles = {}
    for item in recorded:
        titles.setdefault(item.semantic_product_id, item.display_label)
    # A result describes the selected Snapshot, even when discovery lists a later title.
    titles.update({item.match_id: item.workspace.match_definition.title for item in snapshots})
    names = {match["match_id"]: managed_name(locale, profile, "matches", match["match_id"],
             titles.get(match["match_id"])) for match in state["matches"]}
    counts = Counter(names.values())
    labels = {}
    for number, match in enumerate(state["matches"], 1):
        name = names[match["match_id"]]
        if counts[name] > 1:
            name = text(locale, "task.learning.report_match", name=name, number=number)
        versions = version_labels(locale, match["snapshots"])
        for snapshot in match["snapshots"]:
            identity = snapshot["match_snapshot_id"]
            labels[identity] = text(locale, "task.learning.report_target",
                                    name=name, version=versions[identity])
    return labels
