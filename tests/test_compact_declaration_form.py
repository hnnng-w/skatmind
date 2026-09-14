from itertools import product

import pytest

from skatmind.app_web.compact_declaration_form import (
    explicit_declaration_values,
    parse_compact_declaration,
)
from skatmind.app_web.form_registry import get_frontend_form_by_key_v1
from skatmind.app_web.session_form_translation import build_session_command_from_form_v1
from skatmind.capture_web.contracts import MATCH_CAPTURE_WEB_MAX_REQUEST_BYTES
from skatmind.declaration_diagnostics import DeclarationValueError
from skatmind.game_declaration import (
    BOOLEAN_DECLARATION_FIELDS,
    VALID_DECLARATION_GAME_TYPES,
    build_serializable_game_declaration,
    normalize_game_declaration_values,
)


@pytest.mark.parametrize("game_type", VALID_DECLARATION_GAME_TYPES)
@pytest.mark.parametrize("flags", tuple(product((False, True), repeat=4)))
def test_all_explicit_choices_match_canonical_normalizer(game_type, flags):
    explicit = dict(zip(BOOLEAN_DECLARATION_FIELDS, flags, strict=True))
    form = {"game_type": game_type, "bid_value": "", "matadors": "",
            **{name: "true" for name, checked in explicit.items() if checked}}
    try:
        expected = normalize_game_declaration_values(game_type=game_type, **explicit)
    except ValueError as expected_error:
        with pytest.raises(ValueError) as actual:
            parse_compact_declaration(form)
        assert str(actual.value) == str(expected_error)
    else:
        declaration = parse_compact_declaration(form)
        assert build_serializable_game_declaration(declaration) == expected
        command = build_session_command_from_form_v1(
            {"kind": "set_declaration", **explicit_declaration_values(declaration)},
            expected_revision=12)
        assert command.declaration == declaration
        assert all(getattr(command.declaration, name) is checked
                   for name, checked in explicit.items())


@pytest.mark.parametrize("game_type,flags,accepted", (
    ("clubs", (), True), ("grand", (), True),
    ("grand", ("hand_game", "schneider_announced", "schwarz_announced", "ouvert"), True),
    ("null", ("ouvert",), True), ("null", ("hand_game",), True),
    ("grand", ("schneider_announced",), False), ("clubs", ("ouvert",), False),
    ("null", ("schwarz_announced",), False),
))
def test_independent_expected_combinations(game_type, flags, accepted):
    form = {"game_type": game_type, "bid_value": "", "matadors": "",
            **{name: "true" for name in flags}}
    if not accepted:
        with pytest.raises(ValueError):
            parse_compact_declaration(form)
    else:
        result = parse_compact_declaration(form)
        assert tuple(name for name in BOOLEAN_DECLARATION_FIELDS if getattr(result, name)) == tuple(
            name for name in BOOLEAN_DECLARATION_FIELDS if name in flags)
        assert result.matadors is None and result.bid_value is None


@pytest.mark.parametrize("bid", ("", "1", "17", "19", "9999"))
def test_bid_unknown_positive_without_ladder_or_value_clamping(bid):
    result = parse_compact_declaration({"game_type": "null", "bid_value": bid, "matadors": ""})
    assert result.bid_value == (int(bid) if bid else None)


@pytest.mark.parametrize("field,value,reason", (
    ("bid_value", "0", "positive"), ("bid_value", "-1", "positive"),
    ("bid_value", "18.5", "integer"), ("bid_value", " 18", "integer"),
    ("matadors", "2.0", "integer"), ("matadors", "0", "grand_count"),
    ("matadors", "5", "grand_count"), ("game_type", "", "game_type"),
    ("game_type", "poker", "game_type"), ("hand_game", "false", "flag"),
    ("hand_game", ["true", "true"], "flag"), ("ouvert", "on", "flag"),
))
def test_field_failures_have_exact_private_reasons(field, value, reason):
    with pytest.raises(DeclarationValueError) as error:
        parse_compact_declaration({
            "game_type": "grand", "bid_value": "", "matadors": "", field: value})
    assert isinstance(error.value, ValueError) and error.value.reason == reason


@pytest.mark.parametrize("game_type,count", (("clubs", 11), ("grand", 4), ("grand", 2)))
def test_supplied_positive_count_is_preserved_without_polarity(game_type, count):
    declaration = parse_compact_declaration({
        "game_type": game_type, "bid_value": "", "matadors": str(count)})
    assert declaration.matadors == count
    assert set(build_serializable_game_declaration(declaration)) == {
        "game_type", "bid_value", "matadors", *BOOLEAN_DECLARATION_FIELDS}


@pytest.mark.parametrize("field", ("game_type", "bid_value", "matadors"))
def test_missing_normal_controls_rejected(field):
    values = {"game_type": "grand", "bid_value": "", "matadors": ""}
    del values[field]
    with pytest.raises(DeclarationValueError, match="fields"):
        parse_compact_declaration(values)


def test_legacy_explicit_session_parser_is_not_relaxed():
    values = {"kind": "set_declaration", "game_type": "grand", "matadors": "", "bid_value": "19",
              **{name: "false" for name in BOOLEAN_DECLARATION_FIELDS}}
    command = build_session_command_from_form_v1(values, expected_revision=0)
    assert command.declaration.bid_value == 19
    for name in BOOLEAN_DECLARATION_FIELDS:
        missing = dict(values)
        del missing[name]
        with pytest.raises(ValueError):
            build_session_command_from_form_v1(missing, expected_revision=0)


def test_compact_registry_preserves_limits_and_scopes_checkbox_controls():
    for key in ("session.declaration", "session.declaration_correction", "match.declaration"):
        definition = get_frontend_form_by_key_v1(key)
        fields = {field.field_key: field for field in definition.safe_fields}
        assert all(fields[name].control_type == "checkbox"
                   and fields[name].cardinality == "single"
                   and fields[name].allowed_values == ("true", "")
                   for name in BOOLEAN_DECLARATION_FIELDS)
        assert fields["declaration_selection"].reflection_length == 64
        assert not {"expected_revision", "target_revision", "declaration_form"} & fields.keys()
    for key in ("match.declaration", "match.declaration_clear"):
        assert get_frontend_form_by_key_v1(key).body_limit == MATCH_CAPTURE_WEB_MAX_REQUEST_BYTES
    legacy = get_frontend_form_by_key_v1("session.command.set_declaration")
    assert all(field.control_type == "select" and field.allowed_values == ("false", "true")
               for field in legacy.safe_fields if field.field_key in BOOLEAN_DECLARATION_FIELDS)
