"""Private Position input for the next unrecorded perspective play of a saved Match."""

from dataclasses import replace

from skatmind.api.v1.contracts import RequestDocumentV1, WorkflowV1
from skatmind.game_declaration import build_serializable_game_declaration
from skatmind.historical_decision_snapshot import _build_relative_player_map
from skatmind.input_loader import build_position_from_document
from skatmind.matador_inference import infer_visible_matadors_for_decision
from skatmind.match_capture_position_view import _build_trace
from skatmind.match_workspace_contracts import _require_match_position
from skatmind.rules import get_legal_cards


def current_match_position(workspace, position, *, samples):
    # The caller admitted this Workspace. Use the recording view's exact trace
    # projection for this slot alone, without preparing progress for other games.
    game = workspace.slots[_require_match_position(position) - 1].observed_game
    if game is None or game.declaration is None:
        return None
    me = game.perspective_player_id
    declaration = game.declaration
    declarer = game.declarer_player_id
    if declaration.ouvert and declarer != me:
        # A partial Match has no independent exact public opponent hand.
        return None
    trace, playable = _build_trace(game)
    if (playable is None or trace.next_player_id != me
            or trace.complete_play_trace or trace.recording_rule_end is not None):
        return None
    played = {p.card for p in trace.plays if p.player_id == me}
    hand = tuple(card for card in playable if card not in played)
    players = _build_relative_player_map(me, [p.player_id for p in game.players])
    relative = {player: role for role, player in players.items()}
    skat = game.discarded_cards if declarer == me and not declaration.hand_game else ()
    matadors = infer_visible_matadors_for_decision(
        game_type=declaration.game_type, hand_game=declaration.hand_game, acting_player_id=me,
        declarer_player_id=declarer, own_hand=hand, known_skat_cards=skat,
        public_plays=tuple((p.player_id, p.card) for p in trace.plays),
        public_hands=((me, hand),) if declaration.ouvert else ())
    completed = []
    for i, winner in enumerate(trace.winner_player_ids):
        plays = trace.plays[3 * i:3 * i + 3]
        completed.append({"cards": [p.card for p in plays],
                          "players": [relative[p.player_id] for p in plays],
                          "winner_player": relative[winner],
                          "winner_role": "declarer" if winner == declarer else "defenders"})
    current = trace.plays[3 * trace.completed_trick_count:]
    trick = [play.card for play in current]
    counts = dict(trace.player_play_counts)
    root = {
        "analysis_mode": "live_decision", "game_end_reason": "not_ended",
        "game_type": declaration.game_type,
        "game_declaration": build_serializable_game_declaration(
            replace(declaration, matadors=matadors)),
        "player_role": "declarer" if me == declarer else "defender",
        "declarer_player": relative[declarer],
        "player_position": next(p.seat for p in game.players if p.player_id == me),
        "trick_leader": relative[current[0].player_id] if current else "me",
        "next_player": "me", "hand": list(hand), "current_trick": trick,
        "completed_tricks": completed, "played_cards": [], "declarer_points": 0,
        "defender_points": 0, "skat": list(skat),
        "skat_visibility": "known_to_declarer" if skat else "unknown",
        "left_hand_size": 10 - counts[players["left"]],
        "right_hand_size": 10 - counts[players["right"]],
        "sample_count": samples, "random_seed": 0, "use_basic_opponent_strategy": True,
    }
    request = RequestDocumentV1(workflow=WorkflowV1.POSITION_ANALYSIS,
                                document=build_position_from_document(root))
    return request, tuple(get_legal_cards(list(hand), trick, declaration.game_type))
