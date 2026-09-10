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
  const forms = [];
  for (const form of document.querySelectorAll("form[data-preserve-fields]")) {
    if (form === languageForm) continue;
    const allowed = new Set(form.dataset.preserveFields.split(" "));
    const values = {};
    let changed = false;
    for (const control of form.elements) {
      if (!allowed.has(control.name) || control.disabled ||
          ["hidden", "file", "password", "submit", "button"].includes(control.type)) continue;
      values[control.name] ??= [];
      if (["radio", "checkbox"].includes(control.type)) {
        changed ||= control.checked !== control.defaultChecked;
      } else if (control.tagName === "SELECT") {
        const initial = Array.from(control.options).find((option) => option.defaultSelected)
          ?? control.options[0];
        changed ||= control.value !== (initial?.value ?? "");
      } else {
        changed ||= control.value !== control.defaultValue;
      }
      if (["radio", "checkbox"].includes(control.type) && !control.checked) continue;
      values[control.name].push(control.value);
    }
    if (!changed) continue;
    const discriminator = {};
    for (const name of ["kind", "operation"]) {
      const control = form.elements.namedItem(name);
      if (control) discriminator[name] = control.value;
    }
    forms.push({action: new URL(form.action).pathname, discriminator,
      instance: Number(form.elements.namedItem("_frontend_form_instance")?.value ?? 0), values});
  }
  const opened = Array.from(document.querySelectorAll("details"))
    .flatMap((details, index) => details.open ? [index] : []);
  const active = document.querySelector("#session-app, #task-first-match, #task-first-learning");
  const revision = active?.querySelector('[name="expected_revision"]') ??
    active?.querySelector('[name="expected_catalog_revision"]') ??
    document.querySelector('#workflow-form [name="revision"]');
  const field = document.createElement("input");
  field.type = "hidden";
  field.name = "_frontend_language_values";
  const payload = JSON.stringify({forms, open_disclosures: opened,
    source_handle: active?.querySelector('[name="managed_handle"]')?.value ?? null,
    source_revision: revision?.value ?? null});
  languageForm.querySelector('[name="_frontend_language_values"]')?.remove();
  if ((!forms.length && !opened.length) || forms.length > 256 ||
      opened.some((index) => index >= 1024) || new TextEncoder().encode(payload).length > 262144) return;
  field.value = payload;
  languageForm.append(field);
});
