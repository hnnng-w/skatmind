"use strict";

// Redundant accepted-outcome feedback only. No requests, storage, focus or scrolling.
for (const notice of document.querySelectorAll("[data-operation-feedback]")) {
  if (notice.dataset.enhanced) continue;
  notice.dataset.enhanced = "true";
  let remaining = 8000, started = null, timer = null, finished = false;
  const dismiss = document.createElement("button");
  dismiss.type = "button";
  dismiss.className = "operation-dismiss";
  dismiss.textContent = notice.dataset.dismissLabel;
  notice.append(dismiss);
  const paused = () => document.hidden || notice.matches(":hover, :focus-within");
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
    // Preserve normal-flow geometry so the next input never jumps on disappearance.
    notice.style.visibility = "hidden";
  };
  const update = () => {
    stop();
    if (finished || paused()) return;
    if (remaining <= 0) { hide(); return; }
    started = performance.now();
    timer = setTimeout(update, remaining);
  };
  dismiss.addEventListener("click", () => {
    stop();
    finished = true;
    notice.setAttribute("aria-live", "off");
    notice.querySelector("span").style.visibility = "hidden";
    if (document.activeElement === dismiss) {
      // An explicit dismissal leaves its focused control usable until focus leaves.
      dismiss.textContent = notice.dataset.dismissedLabel;
      dismiss.setAttribute("aria-disabled", "true");
    } else hide();
  });
  notice.addEventListener("pointerenter", update);
  notice.addEventListener("pointerleave", update);
  notice.addEventListener("focusin", update);
  notice.addEventListener("focusout", () => setTimeout(() => {
    if (finished && !notice.contains(document.activeElement)) hide();
    else update();
  }, 0));
  document.addEventListener("visibilitychange", update);
  // A restored cached document must not mint a fresh announcement or timer.
  window.addEventListener("pagehide", hide);
  window.addEventListener("pageshow", event => { if (event.persisted) hide(); });
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
