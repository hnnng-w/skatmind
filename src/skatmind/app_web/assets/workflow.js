"use strict";

// Run in the head: no in-flow first paint, even while the DOM is still loading.
document.documentElement.classList.add("operation-overlays");
document.addEventListener("DOMContentLoaded", () => {

// Redundant accepted-outcome feedback only. No requests, storage or scrolling.
for (const notice of document.querySelectorAll("[data-operation-feedback]")) {
  if (notice.dataset.enhanced) continue;
  notice.dataset.enhanced = "true";
  let remaining = 8000, started = null, timer = null, finished = false;
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
  const overlaps = (a, b) => a.left < b.right && a.right > b.left &&
    a.top < b.bottom && a.bottom > b.top;
  const protectControl = target => {
    const control = target?.closest?.('input, select, textarea, button, a[href], summary, label');
    if (!finished && control && !notice.contains(control) &&
        overlaps(notice.getBoundingClientRect(), control.getBoundingClientRect())) hide();
  };
  const updateHover = () => {
    const rect = notice.getBoundingClientRect();
    const inside = pointer !== null && pointer.x >= rect.left && pointer.x <= rect.right &&
      pointer.y >= rect.top && pointer.y <= rect.bottom;
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
for (const fieldset of document.querySelectorAll(".compact-cards")) {
  updateCardSelection(fieldset);
  fieldset.addEventListener("change", () => updateCardSelection(fieldset));
}

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
      const allowed = new Set(form.dataset.preserveFields.split(" "));
      const limits = JSON.parse(form.dataset.preserveLimits);
      const values = {};
      for (const control of form.elements) {
        if (!allowed.has(control.name) || control.disabled ||
            ["hidden", "file", "password", "submit", "button"].includes(control.type)) continue;
        values[control.name] ??= [];
        if (["radio", "checkbox"].includes(control.type) && !control.checked) continue;
        if (control.tagName === "SELECT" && control.multiple) {
          values[control.name].push(...Array.from(control.selectedOptions, option => option.value));
        } else {
          values[control.name].push(control.value);
        }
      }
      for (const [name, entries] of Object.entries(values)) {
        const [length, count] = limits[name];
        if (entries.length > count || entries.some(value => Array.from(value).length > length)) {
          throw new Error();
        }
      }
      forms.push({form: form.dataset.languageForm, values});
    }
    const disclosures = Array.from(document.querySelectorAll("details"), details => details.open);
    const payload = JSON.stringify({forms, disclosures});
    if (forms.length > 256 || disclosures.length > 1024 ||
        new TextEncoder().encode(payload).length > 262144) throw new Error();
    const field = document.createElement("input");
    field.type = "hidden";
    field.name = "_frontend_language_values";
    field.value = payload;
    languageForm.querySelector('[name="_frontend_language_values"]')?.remove();
    languageForm.append(field);
  } catch {
    event.preventDefault();
    const message = languageForm.querySelector(".language-error");
    message.textContent = languageForm.dataset.preservationError;
    message.hidden = false;
    message.focus();
  }
});
});
