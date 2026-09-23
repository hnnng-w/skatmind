# Bilingual Home information architecture

## Status

Issue #255 restores an ordinary fifth Learning task card within the unchanged
five-task/three-group contract. It supersedes only #229's compact plain-link
exception and clarifies collection purpose; see the current navigation guide below.

Issue #229 revises the private navigation and introduction design below. The
current source chooser, same-context reuse, Match review presentation and browser
evidence are documented in [Home and recorded-game review navigation](home_and_recorded_review_navigation.md).
The former scope-guide, generic related-panel and large Product-card choices are
historical #217 evidence, explicitly superseded rather than retroactively denied.

Issue #217 implements the Home and Product-concept slice frozen by the
[bilingual profile-driven frontend UX contract](bilingual_profile_driven_frontend_ux_contract.md).
This is private unified-browser presentation. It adds no Public API export, Root
workflow, Schema, persistence format, dependency, or Product behavior.

The private version is exactly:

```text
FRONTEND_INFORMATION_ARCHITECTURE_VERSION = 1
```

Issue #217 extends the implemented subset of the complete Issue #215 policy
vocabulary with exactly:

```text
home_separates_record_analyze_learn_and_product_information
```

The complete implemented tuple through Issue #220, in canonical vocabulary
order, is:

```text
technical_contracts_and_machine_values_remain_english
unified_frontend_visible_content_supports_german_and_english
one_private_local_frontend_profile_per_managed_data_root
saved_language_overrides_browser_language
browser_language_bootstraps_only_without_saved_preference
user_facing_names_replace_required_manual_internal_ids
normal_workflows_are_task_first_and_profile_driven
advanced_settings_are_secondary_explicit_and_explained
validation_preserves_safe_values_and_workflow_context
home_separates_record_analyze_learn_and_product_information
language_and_profile_never_change_product_semantics
no_external_translation_profile_sync_or_cloud_service
```

Issue #218 adds validation preservation and Issue #219 adds user-facing names and
profile-driven creation. Task-first active workflows and the complete explained
Advanced/Technical hierarchy are implemented by Issue #220.

## Private values

The exact group keys and order are:

```text
record_games
analyze_and_review
learn_across_matches
```

The exact task keys and Home presentation order are:

```text
record_match
record_session
review_game
analyze_decision
learning_insights
```

The exact mapping is:

```text
record_match       -> /matches
record_session     -> /sessions
review_game        -> /review/recorded
analyze_decision   -> /analyze
learning_insights  -> /learning
```

The exact group membership is:

```text
record_games:
    record_match
    record_session

analyze_and_review:
    review_game
    analyze_decision

learn_across_matches:
    learning_insights

```

Contract validation rejects a boolean or changed version and every duplicate,
missing, reordered, orphaned, or extra group, task, mapping, membership, related
area, or empty-state key. These values remain private under
`src/skatmind/app_web/`.

## Routes and navigation

Served static Route order remains independent of visible navigation. The chooser
is appended; manual `/review` and `/about` stay supported:

```text
/
/analyze
/review
/sessions
/matches
/learning
/settings
/about
/review/recorded
```

The concise visible navigation labels are:

| Route | English | German |
| --- | --- | --- |
| `/` | Home | Startseite |
| `/analyze` | Analyze one decision | Eine Entscheidung analysieren |
| `/review/recorded` | Review recorded games | Erfasste Spiele auswerten |
| `/sessions` | Record an individual game | Einzelspiel erfassen |
| `/matches` | Record a 36-game Match | 36er-Match erfassen |
| `/learning` | Learn across Matches | Über Matches lernen |
| `/settings` | Settings | Einstellungen |
| `/about` (footer) | About SkatMind | Über SkatMind |

Issue #225 added Settings while retaining the then-six Home tasks. Issue #229
now has five tasks and keeps About in the footer; normal navigation order is
Home, Match, Session, recorded review, Analyze, Learning, Settings. The #225 forms are documented in
[Settings and Player seat setup](settings_and_player_seat_setup.md). Public APIs,
cookies, Engine workflows, persistence and Product identities remain unchanged.

## Home groups

The exact bilingual headings are:

| Key | English | German |
| --- | --- | --- |
| `record_games` | Record games | Spiele erfassen |
| `analyze_and_review` | Analyze and review | Analysieren und auswerten |
| `learn_across_matches` | Learn across Matches | Über mehrere Matches lernen |

The exact bilingual task titles are:

| Key | English | German |
| --- | --- | --- |
| `record_match` | Record a 36-game Match | 36er-Match erfassen |
| `record_session` | Record an individual game | Einzelspiel erfassen |
| `analyze_decision` | Analyze one decision | Eine Entscheidung analysieren |
| `review_game` | Review recorded games | Erfasste Spiele auswerten |
| `learning_insights` | Explore patterns across recorded Matches | Muster über erfasste Matches hinweg untersuchen |

Home leads directly with the three semantic group sections. The four primary
cards have an H3, one purpose sentence, and one GET action. Learning has only one
compact secondary description/action. Per-task unit/timing/detail blocks and
repeated introductory copy are removed. Recording explains later continuation
and evidence-limited review. No JavaScript is needed.

## Historical scope guide (superseded by #229)

The former Home scope guide began with:

```text
Which area do I need?
Welchen Bereich brauche ich?
```

It maps one Decision to Analyze, one Game being recorded or resumed to Session,
one completed Game being evaluated to Review, one complete 36-position Match to
Match Capture, and multiple recorded Matches to Learning. It explicitly states
that Session records or continues one Game while Review evaluates one Game that
is already completed. The guide uses no internal IDs or analysis, data, or
reproducibility terminology.

## Product units

The visible concepts are:

| Area | Scope | Timing |
| --- | --- | --- |
| Analyze | one Decision | current or retrospective |
| Review | one completed individual Game | retrospective |
| Session | one resumable individual Game | during play or afterward |
| Match | one complete 36-position Match | during observation or afterward |
| Learning | multiple recorded Matches and selected evidence | after Match recording |
| About | Product and local-installation information | any time |

Analyze explains that one Decision may use current visible information or a
reconstructed retrospective Decision. It does not promise guaranteed real-time
speed and changes no Position input, setting, execution, or Result.

Manual `/review` explicitly covers one completed individual Skat game. It may present
recorded Decisions, alternatives, Result, Overbid, Settlement, and selected
optional evidence. A complete 36-position list belongs under Match Capture.

One Session equals one Game. It may be recorded during play or afterward, can be
resumed, and is appropriate for a standalone Game. It is not automatically
inserted into a Match.

Match Capture is the primary recording workflow for one complete EuroSkat 36er
Standard Match with the same three participants. It retains all 36 authoritative
positions, including Played Games and Passed Deals, persists locally, and can be
resumed. A one-Game Session remains a separate object.

Learning explores descriptive patterns across explicitly selected evidence from
multiple recorded Matches. Its visible journey is:

```text
1. record one or more complete 36-position Matches;
2. explicitly add selected Matches to a learning collection;
3. explicitly choose the saved Match version to use;
4. explicitly build insights;
5. review or download the summaries.
```

Nothing is imported, selected, analyzed, or built automatically. The summaries
do not establish Player truth, Rating, intent, or learned behavior. Corpus
operations and preparation remain unchanged.

## Empty states

The Session landing explains that no standalone one-Game record exists, defines
the resumable during-or-afterward unit, distinguishes it from Match Capture, and
points to the bilingual name-first creation form implemented by Issue #219.

The Match landing explains that no complete Match is recorded, defines the same-
three-participant 36-position unit with Played Games and Passed Deals, and points
to the bilingual friendly Match creation action implemented by Issue #219.

The Learning landing explains that no learning collection exists, defines its
cross-Match purpose and recorded-Match prerequisite, and directs the user to
record Matches before explicitly creating a named collection. None of these
empty states performs creation or profile mutation by itself.

An active Learning collection with no imported Match data explains why no cross-
game summary is available and directs the user to record a Match, add it
explicitly, select the saved Match version, and explicitly build insights. The
existing zero counts remain secondary diagnostics. No empty state creates,
opens, imports, selects, analyzes, or prepares anything.

## Historical related areas (superseded by #229)

Issue #217 originally added these generic existing-route GET links:

```text
Analyze -> Review
Review -> Analyze and Match
Session -> Match
Match -> Session and Learning
Learning -> Match
```

Issue #229 removes these generic panels. Targeted correction, transfer,
prerequisite and source/return links remain at their actual controls. The normal
Review task now opens existing recordings; its explicit manual link preserves the
independent wizard's state. No source is copied into manual input.

## Localization and rendering

The English and German catalogs add sorted parity-checked `home.group.*`,
`home.scope_guide.*`, `home.task.*`, `concept.*`, `empty.*`, and `related.*`
keys. Visible German or English Issue #217 copy is not hard-coded in Python.

On a German workflow page, the Product concept, related links, empty state,
landing page, and creation form appear in German. Issue #220 completes the active
dashboard, guided Analyze/Review, and fixed Result translation boundary. Home
and active workflows have no transitional-English region. See
[Task-first bilingual stateful workflows](task_first_bilingual_stateful_workflows.md).

The packaged CSS adds only the semantic Home grouping, compact cards, scope and
concept guides, empty states, responsive long-label handling, native disclosure,
and existing visible-focus integration. There is no external resource,
framework, or new JavaScript.

## Security and compatibility

Home rendering performs no Product execution or managed-item discovery. The
implementation preserves loopback binding, bootstrap and app cookie, Host and
Origin validation, `Referrer-Policy: origin`, CSP, no CORS, no external request,
no access log, retained active contexts, and all existing information
boundaries. It renders no private path, identifier, fingerprint, Card, document,
token, cookie, or port.

The compatibility baseline remains:

```text
Package:                    0.17.0
Python:                     >=3.13
License:                    AGPL-3.0-only
Runtime dependencies:       unchanged
Public API contract:        1
Root workflows:             7
Console Scripts:            1
Settlement Matrix:          version 3, 61 cases
Authoritative Schemas:      71
Packaged Schemas:           71
Session examples:           6
Generated outputs:          98
Private Corpus downloads:   10
```

## UAT and next action

The post-Issue-#220 implementation state is:

```text
UAT-FINDING-001:
    implementation remediation complete through Issue #220
    open pending repeated UAT-01

UAT-FINDING-002:
    resolved by Issue #213

UAT-FINDING-003:
    Home, concept, and active-workflow distinction implemented
    open pending repeated UAT-01

UAT-FINDING-004:
    resolved by Issue #214

UAT-FINDING-005:
    creation and relevant active-view remediation implemented
    open pending repeated UAT-01

UAT-FINDING-006:
    open
    Issue #218 implementation complete
    pending repeated UAT-01

UAT-FINDING-007:
    task-first remediation implemented
    open pending repeated UAT-01

UAT-FINDING-008:
    German and English unified-frontend implementation complete
    open pending repeated UAT-01

Repeated UAT-01:
    failed

UAT-02 through UAT-12:
    paused

Issue #208:
    open

B-09:
    open

B-07:
    open
```

Issue #219 does not repeat UAT or close a finding. Package `1.0.0` and Release
preparation remain not ready. After merge and green exact-commit CI, the next action is:

```text
Repeat UAT-01 under Issue #208.
```
