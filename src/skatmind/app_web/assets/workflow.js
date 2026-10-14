"use strict";

// Run in the head: no in-flow first paint, even while the DOM is still loading.
document.documentElement.classList.add("operation-overlays");

// Read and retire the one-return instruction in the head, before any fragment
// target exists. Neither history entries nor browser storage retain positions.
const languageReturnMeta = document.querySelector('meta[name="language-return"]');
let languageView = null;
let languageFeedbackReturn = false;
try {
  const returned = languageReturnMeta ? JSON.parse(languageReturnMeta.content) : null;
  const navigation = performance.getEntriesByType("navigation")[0];
  languageFeedbackReturn = !!returned && navigation?.type === "navigate" &&
    location.search === `?_language_return=${returned.token}`;
  if (languageFeedbackReturn && returned.view) languageView = returned.view;
  if (navigation?.type === "navigate" &&
      (returned || /^\?_language_return=[0-9a-f]{64}$/.test(location.search))) {
    history.replaceState(history.state, "", location.pathname);
  }
} finally {
  languageReturnMeta?.remove();
}
// An interaction during parsing wins. There is no timer/load/resize restoration
// that can pull the user back after reading or typing has resumed.
for (const type of ["pointerdown", "keydown", "wheel", "touchstart", "input"]) {
  document.addEventListener(type, () => { languageView = null; }, {capture: true, once: true});
}

function languageLandmarks() {
  const ids = [...document.querySelectorAll("[id]")]
    .filter(element => !element.id.startsWith("validation-") &&
      /^[a-zA-Z][a-zA-Z0-9_-]{0,127}$/.test(element.id)).slice(0, 4096)
    .map(element => ({anchor: `id:${element.id}`, element}));
  return ids.concat([...document.querySelectorAll("form[data-language-form]")]
    .map(element => ({anchor: `form:${element.dataset.languageForm}`, element})));
}

function captureLanguageView(focus) {
  const x = Math.max(0, Math.min(1000000, scrollX));
  if (scrollY <= 0) return {anchor: "top", offset: 0, x, focus};
  const candidates = languageLandmarks().filter(({element}) => {
    const rect = element.getBoundingClientRect();
    return element.getClientRects().length && rect.height > 0 && rect.width > 0 &&
      rect.bottom > 0 && rect.top < innerHeight && Math.abs(rect.top) <= 8192;
  });
  candidates.sort((a, b) => Math.abs(a.element.getBoundingClientRect().top) -
    Math.abs(b.element.getBoundingClientRect().top));
  const target = candidates[0];
  if (!target) throw new Error();
  return {anchor: target.anchor, offset: target.element.getBoundingClientRect().top, x, focus};
}

// Presentation-only count; native controls and the explicit submit work without this.
function updateCardSelection(fieldset) {
  const cards = Array.from(fieldset.querySelectorAll('input[name="cards"]:checked'),
    input => input.value);
  const summary = fieldset.querySelector(".compact-selection");
  if (!summary) return;
  summary.querySelector(".compact-count").textContent =
    summary.dataset.countTemplate.replace("{count}", String(cards.length));
  summary.querySelector(".compact-selected").textContent = cards.join(", ");
}

function restoreLanguageView() {
  const view = languageView;
  languageView = null;
  if (!view) return;
  for (const fieldset of document.querySelectorAll(".compact-cards")) updateCardSelection(fieldset);
  const target = languageLandmarks().find(item => item.anchor === view.anchor)?.element;
  if (view.anchor === "top" || target?.getClientRects().length) {
    const y = view.anchor === "top" ? 0 : scrollY + target.getBoundingClientRect().top - view.offset;
    window.scrollTo({left: view.x, top: Math.max(0, y), behavior: "instant"});
    const control = [...document.querySelectorAll('.language-selector button[name="language"]')]
      .find(button => button.value === view.focus);
    control?.focus({preventScroll: true});
  }
}

// The expectation delays incomplete-body paint, not page visibility. An observer
// runs in the parser microtask before rendering is released, rather than scrolling
// back after DOMContentLoaded/load or an animation frame. It is retired immediately.
const languageViewObserver = languageView ? new MutationObserver(() => {
  if (document.getElementById("language-view-ready")) {
    languageViewObserver.disconnect();
    restoreLanguageView();
  }
}) : null;
languageViewObserver?.observe(document.documentElement, {childList: true, subtree: true});

function safePresentationValues(form) {
  const allowed = new Set(form.dataset.preserveFields.split(" "));
  const limits = JSON.parse(form.dataset.preserveLimits);
  const values = {};
  for (const control of form.elements) {
    if (!allowed.has(control.name) || control.disabled ||
        ["hidden", "file", "password", "submit", "button"].includes(control.type)) continue;
    values[control.name] ??= [];
    if (["radio", "checkbox"].includes(control.type) && !control.checked) continue;
    values[control.name].push(...(control.tagName === "SELECT" && control.multiple ?
      Array.from(control.selectedOptions, option => option.value) : [control.value]));
  }
  for (const [name, entries] of Object.entries(values)) {
    const [length, count] = limits[name];
    if (entries.length > count || entries.some(value => Array.from(value).length > length)) {
      throw new Error();
    }
  }
  return values;
}

// Only the selected-Match control island uses preparation requests. No analysis
// is queued or submitted here, and no page/global preference is persisted.
function initializeMatchDecisionSelection(root) {
  const selectorForm = root.querySelector("form[data-decision-selector]");
  const selector = selectorForm?.querySelector('select[name="decision_index"]');
  const apply = selectorForm?.querySelector("[data-apply-decision]");
  let controls = root.querySelector("[data-match-analysis-controls]");
  let language = document.querySelector("form.language-selector");
  const status = root.querySelector("[data-selection-status]");
  if (!selector || !apply || !controls || !language || !status ||
      typeof fetch !== "function" || typeof DOMParser !== "function") return;
  const scope = root.dataset.source;
  const drafts = new Map(), disabled = new WeakMap();
  let applied = root.dataset.applied, desired = selector.value;
  let ready = root.dataset.ready === "true" && desired === applied;
  let generation = 0, pending = false, transport = selectorForm, languageReady = true;
  const formKey = form => form.getAttribute("action");
  const remember = () => {
    const forms = [...controls.querySelectorAll("form[data-language-form]")];
    drafts.set(applied, {forms: forms.map(form => [formKey(form), safePresentationValues(form)]),
      disclosures: [...controls.querySelectorAll("details")].map(detail => detail.open)});
  };
  const block = () => {
    if (ready) {
      try { remember(); } catch { /* Oversized drafts are not copied to another context. */ }
    }
    ready = false;
    languageReady = false;
    root.dataset.ready = "false";
    root.setAttribute("aria-busy", "true");
    for (const control of [...controls.querySelectorAll("input, select, textarea, button"),
                           ...language.querySelectorAll("button")]) {
      if (!disabled.has(control)) disabled.set(control, control.disabled);
      control.disabled = true;
    }
    for (const field of controls.querySelectorAll('[name="visible_decision_index"]')) {
      field.value = desired;
    }
    status.textContent = root.dataset.loadingLabel;
    status.hidden = false;
  };
  const fail = () => {
    ready = false;
    root.dataset.ready = "false";
    root.setAttribute("aria-busy", "false");
    status.textContent = root.dataset.failedLabel;
    status.hidden = false;
    apply.hidden = false;
    apply.disabled = false;
  };
  const restore = replacement => {
    const draft = drafts.get(replacement.dataset.applied);
    if (!draft) return;
    for (const form of replacement.querySelectorAll("form[data-language-form]")) {
      const values = draft.forms.find(([key]) => key === formKey(form))?.[1];
      if (!values) continue;
      const allowed = new Set(form.dataset.preserveFields.split(" "));
      for (const control of form.elements) {
        if (!allowed.has(control.name) || !(control.name in values) ||
            ["hidden", "file", "password", "submit", "button"].includes(control.type)) continue;
        if (["checkbox", "radio"].includes(control.type)) {
          control.checked = values[control.name].includes(control.value);
        } else control.value = values[control.name][0] ?? "";
      }
    }
    [...replacement.querySelectorAll("[data-match-analysis-controls] details")]
      .forEach((detail, index) => { detail.open = draft.disclosures[index] ?? false; });
  };
  const install = (replacement, nextForm, nextControls, nextLanguage, successful) => {
    const fields = [...nextForm.querySelectorAll('input[type="hidden"]')].map(field => {
      const current = [...selectorForm.elements].find(control => control.name === field.name);
      if (!current) throw new Error();
      return [current, field.value];
    });
    const label = replacement.querySelector("[data-applied-decision]");
    const nextSelector = nextForm.querySelector('select[name="decision_index"]');
    if (!label || !nextSelector) throw new Error();
    if (successful) restore(replacement);
    const top = selector.getBoundingClientRect().top, x = scrollX;
    const handoff = controls.contains(document.activeElement);
    selector.innerHTML = nextSelector.innerHTML;
    selector.value = desired;
    controls.replaceWith(document.importNode(nextControls, true));
    controls = root.querySelector("[data-match-analysis-controls]");
    controls.hidden = !successful;
    fields.forEach(([current, value]) => { current.value = value; });
    for (const name of ["languageForm", "preserveFields", "preserveLimits"]) {
      selectorForm.dataset[name] = nextForm.dataset[name];
    }
    transport = selectorForm;
    language.replaceWith(document.importNode(nextLanguage, true));
    language = document.querySelector("form.language-selector");
    languageReady = true;
    root.querySelector("[data-applied-decision]").textContent = label.textContent;
    applied = replacement.dataset.applied;
    root.dataset.applied = applied;
    ready = successful;
    root.dataset.ready = String(ready);
    if (successful) {
      // Retire only feedback immediately attached to this selector form.
      let previous = selectorForm.previousElementSibling;
      while (previous?.matches(".error-summary, .validation-anchor")) {
        const sibling = previous.previousElementSibling;
        previous.remove();
        previous = sibling;
      }
    }
    root.setAttribute("aria-busy", "false");
    status.hidden = successful;
    apply.hidden = successful;
    apply.disabled = false;
    window.scrollTo({left: x, top: Math.max(0, scrollY +
      selector.getBoundingClientRect().top - top), behavior: "instant"});
    if (handoff) selector.focus({preventScroll: true});
  };
  const refresh = async () => {
    if (pending) return;
    pending = true;
    apply.disabled = true;
    const ticket = generation, requested = desired;
    let next = false;
    try {
      const body = new URLSearchParams(new FormData(transport));
      body.set("decision_index", requested);
      const response = await fetch(transport.action, {method: "POST", credentials: "same-origin",
        headers: {"X-SkatMind-Selection": "prepare"}, body});
      const page = new DOMParser().parseFromString(await response.text(), "text/html");
      const replacement = page.querySelector("[data-match-selection]");
      const nextForm = replacement?.querySelector("form[data-decision-selector]");
      const nextControls = replacement?.querySelector("[data-match-analysis-controls]");
      const nextLanguage = page.querySelector("form.language-selector");
      if (!replacement || replacement.dataset.source !== scope ||
          !nextForm || !nextControls || !nextLanguage) throw new Error();
      if (!response.ok) {
        if (ticket === generation && requested === desired) {
          install(replacement, nextForm, nextControls, nextLanguage, false);
        }
        throw new Error();
      }
      if (replacement.dataset.applied !== requested || replacement.dataset.ready !== "true") {
        throw new Error();
      }
      // Serialize preparation requests, coalescing only selection changes. A late
      // response may advance the transport binding, but never installs stale controls.
      transport = nextForm;
      if (ticket !== generation || requested !== desired) {
        if (ticket !== generation) next = true;
        else fail(); // An uncommitted input preview does not authorize another request.
        return;
      }
      install(replacement, nextForm, nextControls, nextLanguage, true);
    } catch { fail(); }
    finally {
      pending = false;
      if (next) void refresh();
    }
  };
  selector.addEventListener("input", () => {
    desired = selector.value;
    if (!ready || desired !== applied) block();
  });
  selector.addEventListener("change", () => {
    desired = selector.value;
    if (ready && desired === applied) return;
    generation += 1;
    block();
    void refresh();
  });
  document.addEventListener("submit", event => {
    if (controls.contains(event.target)) {
      for (const field of controls.querySelectorAll('[name="visible_decision_index"]')) {
        field.value = selector.value;
      }
    }
    if (controls.contains(event.target) && (!ready || selector.value !== applied) ||
        event.target === language && !languageReady) {
      event.preventDefault();
      event.stopImmediatePropagation();
    }
  }, true);
  // A fully initialized enhancement alone exposes the selector and both independent
  // actions together. Native pages keep editable selection separate from ready actions.
  selectorForm.hidden = false;
  root.querySelectorAll("[data-native-selection], [data-native-change]")
    .forEach(element => { element.hidden = true; });
  if (ready) { controls.hidden = false; apply.hidden = true; }
  else {
    block();
    fail();
    // A freshly rendered error page already has a valid language-return binding.
    languageReady = true;
    language.querySelectorAll("button").forEach(button => {
      if (disabled.has(button)) button.disabled = disabled.get(button);
    });
  }
}

document.addEventListener("DOMContentLoaded", () => {
languageViewObserver?.disconnect();
restoreLanguageView();
for (const root of document.querySelectorAll("[data-match-selection]")) {
  initializeMatchDecisionSelection(root);
}

// Redundant accepted-outcome feedback only. No requests, storage or scrolling.
let captureFeedbackBudget = () => null, withdrawFeedback = () => {};
for (const notice of document.querySelectorAll("[data-operation-feedback]")) {
  if (notice.dataset.enhanced) continue;
  // Continued markup is inert unless this is the exact one-use language return.
  // Failed script loading leaves it hidden rather than regenerating native success.
  const navigation = performance.getEntriesByType("navigation")[0];
  if (("feedbackContinuation" in notice.dataset && !languageFeedbackReturn) ||
      ["reload", "back_forward"].includes(navigation?.type)) {
    notice.hidden = true;
    notice.setAttribute("aria-live", "off");
    continue;
  }
  let remaining = Number(notice.dataset.feedbackRemainingMs);
  if (!Number.isFinite(remaining) || remaining <= 0 || remaining > 8000) {
    notice.hidden = true;
    continue;
  }
  notice.hidden = false;
  notice.dataset.enhanced = "true";
  let started = null, timer = null, finished = false;
  let hovered = false, previousFocus = null, pointer = null;
  const dismiss = document.createElement("button");
  dismiss.type = "button";
  dismiss.className = "operation-dismiss";
  dismiss.textContent = notice.dataset.dismissLabel;
  notice.append(dismiss);
  const paused = () => document.hidden || hovered || notice.matches(":focus-within");
  const stop = () => {
    clearTimeout(timer);
    timer = null;
    if (started !== null) remaining -= performance.now() - started;
    started = null;
  };
  const hide = () => {
    stop();
    finished = true;
    notice.setAttribute("aria-live", "off");
    // Only an explicit dismissal/withdrawal of the focused button needs a handoff.
    // Automatic expiry cannot reach this branch while focus is within the receipt.
    if (notice.contains(document.activeElement)) {
      const usable = element => element?.isConnected && !element.disabled &&
        !notice.contains(element) && element.getClientRects().length > 0;
      const target = (usable(previousFocus) ? previousFocus : null) ||
        [...document.querySelectorAll('main input:not([type="hidden"]), main select, main button, main a[href]')]
          .find(usable) || document.querySelector("main");
      target?.focus({preventScroll: true});
    }
    notice.hidden = true;
  };
  const update = () => {
    stop();
    if (finished || paused()) return;
    if (remaining <= 0) { hide(); return; }
    started = performance.now();
    timer = setTimeout(update, remaining);
  };
  captureFeedbackBudget = () => {
    if (finished || notice.hidden || !notice.isConnected || !notice.getClientRects().length) return null;
    const budget = remaining - (started === null ? 0 : performance.now() - started);
    return budget > 0 ? budget : null;
  };
  withdrawFeedback = hide;
  const overlaps = (a, b) => a.left < b.right && a.right > b.left &&
    a.top < b.bottom && a.bottom > b.top;
  const protectControl = target => {
    const control = target?.closest?.('input, select, textarea, button, a[href], summary, label');
    if (!finished && control && !notice.contains(control) &&
        overlaps(notice.getBoundingClientRect(), control.getBoundingClientRect())) hide();
  };
  const updateHover = () => {
    const rect = notice.getBoundingClientRect();
    const inside = pointer === null ? notice.matches(":hover") :
      pointer.x >= rect.left && pointer.x <= rect.right && pointer.y >= rect.top && pointer.y <= rect.bottom;
    if (inside !== hovered) { hovered = inside; update(); }
  };
  const place = () => {
    if (finished) return;
    // Two bounded placements; the sole pointer-active area must not cover a control.
    const top = Math.max(12, (document.querySelector(".site-header")?.getBoundingClientRect().bottom || 0) + 8);
    notice.style.top = `${top}px`;
    const rect = notice.getBoundingClientRect();
    if (rect.height > innerHeight * 0.3 || rect.bottom > innerHeight - 12) { hide(); return; }
    const controls = [...document.querySelectorAll('input:not([type="hidden"]), select, textarea, button, a[href], summary')]
      .filter(control => !notice.contains(control));
    const blocked = () => controls.some(control =>
      overlaps(dismiss.getBoundingClientRect(), control.getBoundingClientRect()));
    if (blocked()) {
      notice.style.top = `${innerHeight - rect.height - 12}px`;
      if (blocked()) { hide(); return; }
    }
    protectControl(document.activeElement);
    updateHover();
  };
  dismiss.addEventListener("click", hide);
  document.addEventListener("pointermove", event => {
    if (finished) return;
    pointer = {x: event.clientX, y: event.clientY};
    updateHover();
    protectControl(event.target);
  });
  document.addEventListener("pointerdown", event => protectControl(event.target), true);
  document.addEventListener("pointerleave", () => { pointer = null; updateHover(); });
  document.addEventListener("focusin", event => {
    if (!notice.contains(event.target)) {
      previousFocus = event.target;
      protectControl(event.target);
    }
  });
  notice.addEventListener("focusin", update);
  notice.addEventListener("focusout", () => setTimeout(update, 0));
  document.addEventListener("visibilitychange", update);
  window.addEventListener("resize", place);
  window.addEventListener("scroll", place, {passive: true});
  // A restored cached document must not mint a fresh announcement or timer.
  window.addEventListener("pagehide", hide);
  window.addEventListener("pageshow", event => { if (event.persisted) hide(); });
  place();
  update();
}

for (const fieldset of document.querySelectorAll(".compact-cards")) {
  updateCardSelection(fieldset);
  fieldset.addEventListener("change", () => updateCardSelection(fieldset));
}

// Reveal only an invalid recorded-review technical field; native validation still owns focus.
document.addEventListener("invalid", (event) => {
  if (event.target.matches(".recorded-rollout-form .advanced-settings input")) {
    event.target.closest("details").open = true;
  }
}, true);

// Preserve presentation only during the explicit native language POST.
// Product operations, legality, and validation remain server-owned.
document.addEventListener("submit", (event) => {
  const languageForm = event.target;
  if (languageForm.dataset.confirm && !window.confirm(languageForm.dataset.confirm)) {
    event.preventDefault();
    return;
  }
  if (!languageForm.matches("form.language-selector")) return;
  try {
    // The native submitter supplies the only language value. Never toggle, fetch,
    // submit another form, or consult the failed POST URL for the return route.
    if (event.submitter?.name !== "language" ||
        !["de", "en"].includes(event.submitter.value)) throw new Error();
    const forms = [];
    for (const form of document.querySelectorAll("form[data-language-form]")) {
      forms.push({form: form.dataset.languageForm, values: safePresentationValues(form)});
    }
    const disclosures = Array.from(document.querySelectorAll("details"), details => details.open);
    const view = captureLanguageView(event.submitter.value);
    const presentation = {forms, disclosures, view};
    const budget = captureFeedbackBudget();
    if (budget !== null) presentation.feedback_remaining_ms = budget;
    const payload = JSON.stringify(presentation);
    if (forms.length > 256 || disclosures.length > 1024 ||
        new TextEncoder().encode(payload).length > 262144) throw new Error();
    const field = document.createElement("input");
    field.type = "hidden";
    field.name = "_frontend_language_values";
    field.value = payload;
    languageForm.querySelector('[name="_frontend_language_values"]')?.remove();
    languageForm.append(field);
    // Capture once at submission; navigation is not active display time. The new
    // document evaluates its own hover/focus/visibility instead of copying pauses.
    withdrawFeedback();
  } catch {
    event.preventDefault();
    withdrawFeedback();
    const message = languageForm.querySelector(".language-error");
    message.textContent = languageForm.dataset.preservationError;
    message.hidden = false;
    message.focus();
  }
});

});
