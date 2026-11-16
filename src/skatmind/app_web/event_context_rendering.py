"""Compact DE/EN native forms and immutable-context inspection, without execution."""

from html import escape

from skatmind.errors import SkatMindError
from skatmind.event_context_sources import recording_players_v1, recording_version_v1

from .event_context_forms import actual_platform
from .event_context_frontend import capture_event_page, checkpoint_review, platform_document
from .stateful_localization import managed_name
from .translation_catalog import translate_frontend_message_v1 as translate
from .workflow_state import StaleFrontendWorkflowRevisionError


def _e(value):
    return escape(str(value), quote=True)


def _text(locale, key, **values):
    return _e(translate(locale, "event." + key, **values))


def _input(locale, name, value="", *, key=None, required=False, kind="text"):
    return (f'<label>{_text(locale, key or name)} <input name="{name}" type="{kind}"'
            f' value="{_e(value)}" maxlength="2000"{" required" if required else ""}></label>')


def _select(locale, name, choices, selected="", *, key=None):
    return (f'<label>{_text(locale, key or name)} <select name="{name}">'
            + "".join(f'<option value="{_e(value)}"{" selected" if value == selected else ""}>'
                      f'{_e(label)}</option>' for value, label in choices) + '</select></label>')


def _form(page, active, family, action, body, locale, *, label=None):
    return (f'<form method="post" action="/{family}/event-context/{action}" class="form-grid">'
            f'<input type="hidden" name="managed_handle" value="{active.handle}">'
            f'<input type="hidden" name="event_selection" value="{page.selection}">'
            + body + f'<button type="submit">{_text(locale, label or action)}</button></form>')


def _amount(value):
    if value is None:
        return ""
    # Ordinary submitted amounts are decimal fractions with at most six places.
    if 10**6 % value.denominator == 0:
        scaled = value.numerator * (10**6 // value.denominator)
        whole, tail = divmod(scaled, 10**6)
        return str(whole) if not tail else f"{whole}.{tail:06d}".rstrip("0")
    return f"{value.numerator}/{value.denominator}"


def suggested_title(app, document, locale):
    source = recording_version_v1(document).source
    fallback = (document.workspace.match_definition.title if source.family == "match" else
                translate(locale, "event.suggested_title", players=", ".join(
                    label for _, label in _players(document))))
    return managed_name(locale, app.frontend_profile.document, source.family + "es"
        if source.family == "match" else "sessions", source.product_id, fallback)[:500].rstrip()


def platform_field(document, locale, terms=None):
    platform = actual_platform(document, terms)
    if platform is not None:
        return f'<p>{_text(locale, "platform")}: {_text(locale, "platform." + platform)}</p>'
    return _select(locale, "platform", [("", translate(locale, "event.choose")),
        *[(value, translate(locale, "event.platform." + value))
          for value in ("euroskat", "in_person")]])


def _terms_fields(document, locale, terms=None):
    modes = ("tournament", "tournament_cent")
    body = _select(locale, "event_mode", [(mode, translate(locale, "event.mode." + mode))
        for mode in modes], "tournament" if terms is None else terms.mode)
    return body + platform_field(document, locale, terms)


def _checkpoint_fields(locale, checkpoint=None, *, through=None):
    return ''.join(_input(locale, name, getattr(checkpoint, name) if checkpoint is not None
        else through if name == "through_position" and through is not None else "",
        required=True, kind="number")
        for name in ("through_position", "personal_points", "own_losses"))


def _players(document):
    values = (document.workspace.match_definition.participants
              if hasattr(document, "workspace") else document.state.players)
    return tuple((player.player_id, player.player_label or player.player_id) for player in values)


def _selected_field(document, locale):
    _, selected = recording_players_v1(document)
    if selected is None:
        return _select(locale, "selected_player", [("", translate(locale, "event.choose")),
            *[(str(index), label) for index, (_, label) in enumerate(_players(document), 1)]])
    label = dict(_players(document))[selected]
    return f'<p>{_text(locale, "participant", player=label)}</p>'


def _attach_forms(app, active, family, page, locale):
    if family != "sessions":
        return ""
    body = f'<details><summary>{_text(locale, "attach_title")}</summary>'
    for event in page.journal.heads:
        if page.context is not None and event.event_id != page.context.event_id:
            continue
        choice = capture_event_page(app, active, family, event_id=event.event_id)
        labels = {}
        for _, document in choice.documents:
            binding = event.binding(recording_version_v1(document).source)
            if binding is not None:
                labels.update({binding.player(player): label
                               for player, label in _players(document)})
        fields = (f'<p>{_e(event.event_name)}</p>'
                  f'<input type="hidden" name="event_choice" value="{_e(event.event_id)}">')
        existing = event.binding(recording_version_v1(page.document).source)
        game = "" if existing is None else existing.game_position
        fields += _input(locale, "game_position", game, required=True, kind="number")
        fields += _selected_field(page.document, locale)
        for index, (player, label) in enumerate(_players(page.document), 1):
            mapped = existing.player(player) if existing is not None else player
            if mapped in event.participant_ids:
                continue
            selected = (str(event.participant_ids.index(mapped) + 1)
                        if mapped in event.participant_ids else "")
            choices = [("", translate(locale, "event.choose")), *[(str(number), labels.get(identity,
                translate(locale, "event.player_number", number=number)))
                for number, identity in enumerate(event.participant_ids, 1)]]
            fields += f'<p>{_e(label)}</p>' + _select(locale, f"map_{index}", choices, selected,
                                                                   key="maps_to")
        body += _form(choice, active, family, "attach", fields, locale)
    return body + '</details>'


def _projection(value, locale):
    body = f'<p>{_text(locale, "status." + value.status)}</p>'
    if value.personal_points is not None:
        if value.game_position == 37:
            body += f'<p>{_text(locale, "final_projection", through=value.established_through,
                points=value.personal_points, losses=value.own_losses)}</p>'
        else:
            body += f'<p>{_text(locale, "projection", game=value.game_position,
                through=value.established_through, points=value.personal_points,
                losses=value.own_losses,
                remaining=value.remaining_including_current)}</p>'
    if value.checkpoint is not None:
        body += f'<p>{_text(locale, "anchor", through=value.checkpoint.through_position,
            points=value.checkpoint.personal_points, losses=value.checkpoint.own_losses)}</p>'
    if value.unresolved:
        body += '<ul>' + ''.join(f'<li>{_text(locale, "gap", position=row.fact.position,
            state=translate(locale, "event.position." + row.fact.status))}</li>'
            for row in value.unresolved) + '</ul>'
    for item in value.disagreements:
        body += f'<p>{_text(locale, "disagreement", through=item.checkpoint.through_position,
            supplied=item.checkpoint.personal_points, supplied_losses=item.checkpoint.own_losses,
            derived=item.derived_points, derived_losses=item.derived_losses)}</p>'
        if value.acknowledges(item):
            body += f'<p>{_text(locale, "acknowledged")}</p>'
    return body


def render_event_context(app, active, family, locale):
    try:
        with active.capture.lock if family == "matches" else active.lock:
            page = capture_event_page(app, active, family)
        if family == "sessions":
            from skatmind.accounting_state import CentRoundV1
            from skatmind.accounting_store import load_accounting

            if type(load_accounting(app.managed_home.root).for_source(
                    recording_version_v1(page.document).source)) is CentRoundV1:
                return ""
        body = f'<section class="panel" id="event-context"><h2>{_text(locale, "title")}</h2>'
        body += f'<p>{_text(locale, "capture_only")}</p>'
        if page.context is None:
            body += f'<details><summary>{_text(locale, "create")}</summary>'
            fields = _selected_field(page.document, locale)
            fields += _input(locale, "title", suggested_title(app, page.document, locale),
                             key="editable_title", required=True)
            fields += _terms_fields(page.document, locale)
            body += _form(page, active, family, "create", fields, locale) + '</details>'
        else:
            event = page.context
            body += f'<p>{_e(event.event_name)}</p>'
            if recording_players_v1(page.document)[1]:
                body += _selected_field(page.document, locale)
            else:
                bound = event.binding(recording_version_v1(page.document).source)
                player = dict(_players(page.document))[bound.source_selected_player_id]
                body += f'<p>{_text(locale, "participant", player=player)}</p>'
            body += _projection(page.prepared, locale)
            if family == "matches" and active.selected_position == 36:
                body += f'<details><summary>{_text(locale, "list_end")}</summary>'
                body += _projection(checkpoint_review(page, 36), locale) + '</details>'
            if event.tournament:
                latest = event.checkpoints[-1] if event.checkpoints else None
                if latest is not None:
                    body += f'<p>{_text(locale, "saved_anchor", through=latest.through_position,
                        points=latest.personal_points, losses=latest.own_losses)}</p>'
                needs_anchor = bool(page.prepared.unresolved)
                body += (f'<details{" open" if needs_anchor else ""}><summary>'
                         f'{_text(locale, "checkpoint" if needs_anchor else "correct_score")}'
                         '</summary>')
                body += _form(page, active, family, "checkpoint", _checkpoint_fields(locale,
                    None if needs_anchor else latest,
                    through=page.prepared.game_position - 1), locale) + '</details>'
                if event.checkpoints:
                    body += f'<details><summary>{_text(locale, "reconciliation")}</summary>'
                    for checkpoint in event.checkpoints:
                        review = checkpoint_review(page, checkpoint.through_position)
                        disagreement = None if review is None else next((item for item in
                            review.disagreements if item.checkpoint == checkpoint), None)
                        if disagreement is not None:
                            item = disagreement
                            message = _text(locale, "disagreement",
                                through=checkpoint.through_position,
                                supplied=checkpoint.personal_points,
                                supplied_losses=checkpoint.own_losses,
                                derived=item.derived_points, derived_losses=item.derived_losses)
                            body += f'<p>{message}</p>'
                            if not review.acknowledges(disagreement):
                                fields = (f'<input type="hidden" name="through_position"'
                                    f' value="{checkpoint.through_position}">'
                                    '<input type="hidden" name="disagreement"'
                                    f' value="{review.disagreement_identity(item)}">')
                                body += _form(page, active, family, "reconfirm", fields, locale)
                            else:
                                body += f'<p>{_text(locale, "acknowledged")}</p>'
                    fields = _select(locale, "through_position", [(str(c.through_position),
                        str(c.through_position)) for c in event.checkpoints])
                    body += _form(page, active, family, "remove", fields, locale)
                    body += '</details>'
            body += f'<details><summary>{_text(locale, "terms")}</summary>'
            term = page.prepared.terms
            fields = _input(locale, "title", event.event_name, key="editable_title", required=True)
            fields += _terms_fields(platform_document(page), locale, term)
            body += _form(page, active, family, "terms", fields, locale) + '</details>'
            body += (f'<details><summary>{_text(locale, "frozen")}</summary>'
                     f'<p>{_text(locale, "no_ranking")}</p>')
            body += _form(page, active, family, "freeze", _input(locale, "decision_index",
                required=True, kind="number"), locale)
            source = recording_version_v1(page.document).source
            for value in page.journal.preparations:
                if value.target_key == source and value.decision_index is not None:
                    label = _text(locale, "frozen_item", revision=value.context_revision,
                                  game=value.game_position, decision=value.decision_index)
                    body += f'<details><summary>{label}</summary>'
                    body += f'<p>{_text(locale, "frozen_historical")}</p>'
                    current_sources = {recording_version_v1(document)
                                       for _, document in page.documents}
                    if (value.context_fingerprint != event.fingerprint
                            or value.target_source not in current_sources
                            or any(ref not in current_sources
                                   for row in value.basis for ref in row.sources)):
                        body += f'<p>{_text(locale, "frozen_stale")}</p>'
                    body += _projection(value, locale) + '</details>'
            body += '</details>'
        body += _attach_forms(app, active, family, page, locale)
        location = (f"/matches/position/{active.selected_position}" if family == "matches"
                    else "/sessions/current")
        return (body + f'<p><a href="{location}#event-context">'
                f'{_text(locale, "reload")}</a></p></section>')
    except (OSError, ValueError, SkatMindError, StaleFrontendWorkflowRevisionError):
        return (f'<section class="panel" id="event-context"><h2>{_text(locale, "title")}</h2>'
                f'<p role="alert">{_text(locale, "unavailable")}</p></section>')
