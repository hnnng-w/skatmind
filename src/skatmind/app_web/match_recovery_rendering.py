from __future__ import annotations

from html import escape

from .compact_card_rendering import compact_card_selector, compact_recorded_card
from .recorded_trick_progress import project_match_trick_progress
from .recorded_trick_rendering import render_recorded_history
from .stateful_localization import card_name, text, translated
from .task_first_rendering import disclosure, form, hidden, paragraph


def _name(context, locale, player_id):
    return next((player.player_label or text(locale, "task.player", number=index)
                 for index, player in enumerate(context.workspace.match_definition.participants, 1)
                 if player.player_id == player_id), text(locale, "task.unknown"))


def _location(locale, index):
    return text(locale, "recovery.location", trick=(index - 1) // 3 + 1,
                position=(index - 1) % 3 + 1)


def _link(locale, index, count):
    label = escape(_location(locale, index))
    if index <= count:
        return f'<a href="#match-play-{index}">{label}</a>'
    return label


def render_match_diagnostic(context, locale, diagnostic, *, proposed_index=None):
    count = len(context.workspace.slots[context.selected_position - 1].observed_game.plays)
    body = '<p>' + _link(locale, diagnostic.play_index, count) + ': '
    body += escape(_name(context, locale, diagnostic.player_id)) + ' — '
    body += escape(card_name(locale, diagnostic.card)) + '</p>'
    body += paragraph(locale, f"recovery.reason.{diagnostic.reason}")
    if diagnostic.complete_replay:
        body += paragraph(locale, "recovery.complete_replay")
    if diagnostic.required_suit is not None:
        body += paragraph(locale, "recovery.required", suit=text(
            locale, f"recovery.suit.{diagnostic.required_suit}"))
    if diagnostic.expected_player_id is not None:
        body += paragraph(locale, "recovery.expected_player",
                          player=_name(context, locale, diagnostic.expected_player_id))
    if diagnostic.witness_card is not None:
        witness = diagnostic.witness_index
        key = ("recovery.witness.known" if witness is None else
               "recovery.witness.proposed" if witness == proposed_index or witness > count
               else "recovery.witness.accepted")
        body += paragraph(locale, key, card=card_name(locale, diagnostic.witness_card))
        if witness is not None:
            body += '<p>' + _link(locale, witness, count) + '</p>'
    body += paragraph(locale, "recovery.observations")
    body += '<p><a href="#match-declaration">' + translated(
        locale, "recovery.check_declaration") + '</a> · <a href="#match-evidence">' + translated(
        locale, "recovery.check_evidence") + '</a></p>'
    return '<div class="match-diagnostic">' + body + '</div>'


def _action(context, locale, selection, key):
    return form(locale, "/matches/recovery/select",
        hidden("managed_handle", context.handle) + hidden("recovery_selection", selection.token),
        key)


def _play_list(context, locale, plays):
    return '<ol>' + ''.join('<li>' + escape(_location(locale, play.decision_index))
        + ' — ' + escape(_name(context, locale, play.player_id)) + ': '
        + escape(card_name(locale, play.card)) + '</li>' for play in plays) + '</ol>'


def _removed_annotations(context, locale, game, candidate):
    retained_notes = {note.commentary_id for note in candidate.commentaries}
    retained_links = {link.link_id for link in candidate.response_links}
    notes_by_id = {note.commentary_id: note for note in game.commentaries}
    content = '<ul>'
    for note in game.commentaries:
        if note.commentary_id not in retained_notes:
            content += '<li>' + escape(_location(locale, note.decision_index)) + ': '
            content += escape(note.text) + '</li>'
    for link in game.response_links:
        if link.link_id not in retained_links:
            content += '<li>' + translated(locale, "recovery.response_removed",
                source=_location(locale, notes_by_id[link.commentary_id].decision_index),
                response=_location(locale, link.response_decision_index)) + '</li>'
    return content + '</ul>'


def _replacement_effects(context, locale, game, old, preview):
    candidate = preview.candidate
    pair = ' → '.join(compact_recorded_card(locale, card, show_code=False) + ' '
                      + escape(card_name(locale, card)) for card in (old.card, preview.card))
    body = '<p class="recovery-card-change">' + pair + '</p>'
    if candidate.change.status == "unchanged":
        return body + paragraph(locale, "recovery.unchanged")
    following = len(game.plays) - old.decision_index
    if following:
        body += paragraph(locale, "recovery.following", count=following)
    for before, after in candidate.changed_tricks:
        if before.winner_player_id == after.winner_player_id:
            effect = translated(locale, "recovery.winner_same", trick=before.number,
                                player=_name(context, locale, after.winner_player_id))
        else:
            effect = translated(locale, "recovery.winner_changed", trick=before.number,
                before=_name(context, locale, before.winner_player_id),
                after=_name(context, locale, after.winner_player_id))
        if game.declaration.game_type != "null" and before.points != after.points:
            effect += ' ' + translated(locale, "recovery.points",
                                      before=before.points, after=after.points)
        body += '<p>' + effect + '</p>'
    if game.commentaries or game.response_links:
        body += paragraph(locale, "recovery.annotations_unchanged")
    return body


def render_match_recovery(context, locale, selections, *, progress=None):
    state = context.recovery
    game = context.workspace.slots[context.selected_position - 1].observed_game
    if game is None:
        return "", ""
    feedback = ''
    if state.notice and not state.routine_confirmation:
        feedback += '<p role="status">' + translated(locale, f"recovery.{state.notice}") + '</p>'
    diagnostic = state.diagnostic if state.diagnostic_source == context.workspace else None
    if diagnostic is not None:
        feedback += paragraph(locale, "recovery.rejected", cards=', '.join(
            card_name(locale, card) for card in state.proposed_cards))
        feedback += render_match_diagnostic(context, locale, diagnostic,
                                            proposed_index=state.proposed_index)
    if progress is None:
        progress = project_match_trick_progress(context.workspace, context.selected_position)
    warning = progress.warning
    if warning is not None:
        feedback += paragraph(locale, "recovery.warning")
        feedback += render_match_diagnostic(context, locale, warning)
    selection = state.selected
    tokens = {item.token for item in selections}
    if selection is not None and selection.token in tokens:
        old = game.plays[selection.play_index - 1]
        feedback += '<section id="match-recovery" tabindex="-1"><h3>' + translated(
            locale, "recovery.preview_title") + '</h3>'
        feedback += paragraph(locale, "recovery.selected",
                              game=text(locale, "task.match.position",
                                        number=context.selected_position),
                              location=_location(locale, old.decision_index),
                              player=_name(context, locale, old.player_id),
                              card=card_name(locale, old.card))
        fields = hidden("managed_handle", context.handle)
        preview = state.preview
        if preview is not None and preview.selection != selection:
            preview = None
        main_action = ''
        if selection.action == "replace" and preview is None:
            main_action = form(locale, "/matches/recovery/preview", fields
                + hidden("recovery_selection", selection.token)
                + compact_card_selector(locale, mode="play", selected=(old.card,), name="card",
                    legend_key="recovery.choose_card", guidance_key="recovery.choice_guidance"),
                "recovery.preview_card", primary=True)
        if preview is not None:
            candidate = preview.candidate
            if selection.action == "replace":
                feedback += _replacement_effects(context, locale, game, old, preview)
            else:
                feedback += paragraph(locale, "recovery.removal",
                    retained=candidate.retained_play_count, removed=candidate.removed_play_count,
                    location=_location(locale, old.decision_index),
                    notes=candidate.removed_commentary_count,
                    responses=candidate.removed_response_count)
                feedback += disclosure(locale, "recovery.retained_plays", _play_list(
                    context, locale, game.plays[:selection.play_index - 1]))
                feedback += disclosure(locale, "recovery.removed_plays", _play_list(
                    context, locale, game.plays[selection.play_index - 1:]))
                if candidate.removed_commentary_count or candidate.removed_response_count:
                    feedback += disclosure(locale, "recovery.removed_annotations",
                        _removed_annotations(context, locale, game, candidate.game))
                feedback += paragraph(locale, "recovery.removal_final")
                feedback += paragraph(locale, "recovery.metadata_unchanged")
            if candidate.warning is not None:
                feedback += paragraph(locale, "recovery.candidate_warning")
                feedback += render_match_diagnostic(context, locale, candidate.warning,
                                                    proposed_index=selection.play_index)
            confirmation = ('' if selection.action == "replace" else
                '<label><input type="checkbox" name="confirm_apply" required>'
                + translated(locale, "recovery.confirm") + '</label>')
            main_action = form(locale, "/matches/recovery/apply", fields
                + hidden("recovery_selection", preview.apply_token)
                + confirmation, "recovery.apply", primary=True,
                submitter=("confirm_apply", "on") if selection.action == "replace" else None)
        feedback += '<div class="recovery-primary-actions">' + main_action
        feedback += form(locale, "/matches/recovery/cancel", fields, "recovery.cancel") + '</div>'
        rewind = next(item for item in selections if item.play_index == old.decision_index
                      and item.action == "rewind")
        if selection.action == "replace":
            if preview is not None:
                feedback += _action(context, locale, selection, "recovery.choose_another")
            feedback += '<div class="recovery-danger">'
            feedback += paragraph(locale, "recovery.rewind_prepare")
            feedback += _action(context, locale, rewind, "recovery.rewind")
            feedback += '</div>'
        feedback += '</section>'
    history = ''
    if game.plays:
        last = next(item for item in selections if item.play_index == len(game.plays)
                    and item.action == "rewind")
        history += _action(context, locale, last, "recovery.undo_last")
        actions = {}
        for play in game.plays:
            markup = '<div class="match-recovery-actions">'
            for action, key in (("replace", "recovery.correct"), ("rewind", "recovery.rewind")):
                item = next(item for item in selections
                            if item.play_index == play.decision_index and item.action == action)
                markup += _action(context, locale, item, key)
            actions[play.decision_index] = markup + '</div>'
        history += '<div class="match-history">' + render_recorded_history(
            progress, locale, actions=actions, anchor_prefix="match-play") + '</div>'
    return feedback, history
