"use strict";

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
