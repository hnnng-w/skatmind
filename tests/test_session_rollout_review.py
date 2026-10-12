from whole_game_review_fixtures import saved_opening

from skatmind.api.v1 import execute
from skatmind.session_rollout_review import derive_session_rollout_review_request_v1
from skatmind.whole_game_rollout_contracts import WholeGameRolloutSettingsV1


def test_changed_later_hidden_hands_and_outcomes_do_not_enrich_frozen_root():
    settings = WholeGameRolloutSettingsV1(random_seed=0, requested_worlds=1,
                                         wall_clock_timeout_ms=30000)
    outputs, roots = [], []
    for reversed_hands in (False, True):
        state, checkpoint = saved_opening(complete=True, reverse_hidden=reversed_hands)
        original = checkpoint.to_dict()
        request = derive_session_rollout_review_request_v1(
            state=state, checkpoint=checkpoint, settings=settings)
        root = request.to_dict()["document"]
        root.pop("whole_game_rollout_derivation")
        roots.append(root)
        result = execute(request).result.to_dict()["document"]["whole_game_rollout_result"]
        result["work"].pop("elapsed_ms")
        outputs.append(result)
        assert checkpoint.to_dict() == original
    assert roots[0] == roots[1]
    assert outputs[0] == outputs[1]
