"""Finite mappings from accepted mutations, not routes or English result prose."""

from .operation_feedback import feedback_players, player_ordinal


def learning_import_message(status, relation, selection_mode):
    if status != "applied":
        return None
    if relation == "duplicate_snapshot":
        return ("version_selected", ()) if selection_mode == "select_imported" else None
    if relation == "new_match" or (selection_mode == "select_imported" and relation in {
            "newer_revision", "older_revision", "same_revision_content_conflict"}):
        return "version_added", ()
    return None


def session_command_message(active, command):
    kind = command.kind
    fixed = {"set_game_metadata": "details", "set_declarer": "declarer",
             "set_declaration": "declaration", "set_game_end": "ending"}
    if kind in fixed:
        return fixed[kind], ()
    if kind == "record_play":
        return "play", (("card", command.card), ("player", player_ordinal(
            active.state.players, command.player_id)))
    if kind == "record_dealt_card":
        if command.destination == "skat":
            return "skat", (("count", 1),)
        return "initial_cards", (("count", 1), ("player", player_ordinal(
            active.state.players, command.player_id)))
    if kind == "record_discard":
        return "discards", (("count", 1),)
    if kind == "set_public_hand":
        return "public_hand", (("player", player_ordinal(active.state.players, command.player_id)),)
    return None


def session_batch_message(active, task, commands):
    # The implicit metadata Command is deliberately not a Card acknowledgement.
    cards = tuple(command for command in commands if command.kind == task.kind)
    if task.kind == "record_play":
        return session_command_message(active, cards[0])
    if task.kind == "record_discard":
        return "discards", (("count", len(cards)),)
    if task.destination == "skat":
        return "skat", (("count", len(cards)),)
    return "initial_cards", (("count", len(cards)), ("player", player_ordinal(
        active.state.players, task.player_id)))


def match_operation_message(active, operation, previous_game):
    game = active.workspace.slots[active.selected_position - 1].observed_game
    if operation in {"start_game", "mark_passed_deal"}:
        return ("game_started" if operation == "start_game" else "game_passed",
                (("number", active.selected_position),))
    if operation == "append_plays" and previous_game is not None:
        accepted = game.plays[len(previous_game.plays):]
        if len(accepted) == 1:
            play = accepted[0]
            return "play", (("card", play.card), ("player", player_ordinal(
                feedback_players(active), play.player_id)))
        if accepted:
            return "plays", (("count", len(accepted)),)
    if operation == "set_perspective_hand" and game.perspective_initial_hand:
        return "hand", (("player", player_ordinal(feedback_players(active),
            active.workspace.match_definition.perspective_player_id)),)
    if operation in {"set_original_skat", "set_discarded_cards"}:
        cards = game.original_skat if operation == "set_original_skat" else game.discarded_cards
        if cards:
            return ("skat" if operation == "set_original_skat" else "discards",
                    (("count", len(cards)),))
    if operation == "set_declaration" and game.declaration is not None:
        return "declaration", ()
    if operation == "update_match_metadata":
        return "details", ()
    return None
