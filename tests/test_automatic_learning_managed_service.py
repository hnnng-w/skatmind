from automatic_learning_helpers import source_fixture
from test_unified_local_app_managed_items import _save_match, _save_session

from skatmind.app_web.automatic_learning import (
    automatic_learning_root_v1,
    initialize_managed_automatic_learning_v1,
    resume_managed_automatic_learning_v1,
)
from skatmind.app_web.contracts import MANAGED_LOCAL_DATA_CATEGORIES
from skatmind.app_web.managed_data import prepare_managed_home_v1
from skatmind.app_web.managed_item_contracts import (
    MANAGED_ITEM_FAMILIES,
    MANAGED_ITEM_MAX_CANDIDATES,
)
from skatmind.app_web.managed_item_discovery import discover_managed_items_v1
from skatmind.learning_corpus_persistence import initialize_learning_corpus_directory_v1


def test_private_root_keeps_existing_bytes_categories_and_discovery_unchanged(
    tmp_path, monkeypatch,
):
    home = prepare_managed_home_v1(tmp_path / "disposable")
    _save_session(home.category("sessions").path / "session.json")
    _save_match(home.category("matches").path / "match.json")
    initialize_learning_corpus_directory_v1(home.category("corpora").path / "manual",
                                             corpus_id="manual-independent")
    before = {path: path.read_bytes() for path in home.root.rglob("*") if path.is_file()}
    views = tuple(discover_managed_items_v1(home.category(family).path, family=family, generation=1)
                  for family in MANAGED_ITEM_FAMILIES)
    assert not automatic_learning_root_v1(home).exists()

    def forbidden(*args, **kwargs):
        raise AssertionError("Storage must not execute analysis or preparation.")

    import skatmind.api.v1 as api
    import skatmind.app_web.managed_item_discovery as discovery
    import skatmind.corpus_web.preparation as preparation

    # Catch accidental workflow wiring at existing application-facing boundaries.
    for name in dir(api):
        if name.startswith("execute") and callable(getattr(api, name)):
            monkeypatch.setattr(api, name, forbidden)
    for name in dir(preparation):
        if name.startswith(("prepare_", "build_")) and callable(getattr(preparation, name)):
            monkeypatch.setattr(preparation, name, forbidden)
    monkeypatch.setattr(discovery, "discover_managed_items_v1", forbidden)
    store = initialize_managed_automatic_learning_v1(home)
    store.publish_object(source_fixture()[1])
    resumed = resume_managed_automatic_learning_v1(home)
    preview = resumed.preview_cleanup(expected_manifest=resumed.snapshot().manifest.fingerprint)
    assert resumed.commit_cleanup(preview).status == "saved"
    assert all(path.read_bytes() == raw for path, raw in before.items())
    assert MANAGED_LOCAL_DATA_CATEGORIES == MANAGED_ITEM_FAMILIES
    assert MANAGED_ITEM_FAMILIES == ("sessions", "matches", "corpora")
    assert MANAGED_ITEM_MAX_CANDIDATES == 2048
    assert tuple(discover_managed_items_v1(home.category(family).path, family=family, generation=1)
                 for family in MANAGED_ITEM_FAMILIES) == views
    assert automatic_learning_root_v1(home).parent == home.root
