/* Phone fields: tap a field that already has text and it opens empty, ready to type in (owner request 2026-10-14).
   Leave it empty and the old text comes back, so a stray tap never loses anything. Only a person's tap or Tab clears:
   a sheet that focuses its first field by itself leaves the values alone. Dates, pickers, passwords, selects and
   anything marked data-keep-text are left as they are. */
(() => {
  const SKIP_TYPES = new Set(["hidden", "checkbox", "radio", "date", "month", "time", "datetime-local", "password",
    "file", "range", "color", "submit", "button", "reset", "image"]);
  let lastPerson = 0;
  const person = () => { lastPerson = Date.now(); };
  document.addEventListener("pointerdown", person, true);
  document.addEventListener("touchstart", person, true);
  document.addEventListener("keydown", (event) => { if (event.key === "Tab") person(); }, true);

  const eligible = (el) => el instanceof HTMLElement && !el.readOnly && !el.disabled && !el.hasAttribute("data-keep-text")
    && ((el instanceof HTMLTextAreaElement) || (el instanceof HTMLInputElement && !SKIP_TYPES.has(el.type)));
  const putBack = (el) => {
    delete el.dataset.fieldTyped;
    if (el.dataset.fieldWas === undefined) return;
    if (el.value === "") el.value = el.dataset.fieldWas;
    delete el.dataset.fieldWas;
  };
  const open = (el) => {
    if (!eligible(el) || el.value === "" || el.dataset.fieldTyped) return;
    el.dataset.fieldWas = el.value;
    el.value = "";
  };

  document.addEventListener("focusin", (event) => { if (Date.now() - lastPerson <= 600) open(event.target); });
  // A tap on a field that is already focused (a picker closed and left it so) opens it empty too, unless text was typed in it.
  document.addEventListener("pointerdown", (event) => { if (event.target === document.activeElement) open(event.target); }, true);
  document.addEventListener("input", (event) => { if (event.isTrusted && event.target instanceof HTMLElement) event.target.dataset.fieldTyped = "1"; }, true);  // the page's own events do not count as typing
  document.addEventListener("focusout", (event) => { if (event.target instanceof HTMLElement) putBack(event.target); });
  // Enter on an empty field submits the old value, not nothing.
  document.addEventListener("submit", (event) => {
    event.target.querySelectorAll?.("[data-field-was]").forEach(putBack);
  }, true);
})();

/* Phone tables (guideline C12): CSS stacks every table row; each cell carries its column's heading as a label. */
(() => {
  document.querySelectorAll("table").forEach((table) => {
    const heads = [...table.querySelectorAll("thead th")].map((th) => th.textContent.trim());
    if (!heads.some(Boolean)) return;
    table.querySelectorAll("tbody tr").forEach((row) => {
      [...row.cells].forEach((cell, i) => { if (heads[i] && cell.textContent.trim() && !cell.dataset.label) cell.dataset.label = heads[i]; });
    });
  });
})();

/* Phone dates (guideline C12: a date is a picker, never typed): a date field is read-only so no keyboard opens; app.js opens the calendar on tap. */
(() => {
  const control = (target) => target.closest?.(".iso-date-control");
  const field = (target) => (target.matches?.("input[data-smart-date]") && control(target)) ? target : null;
  document.addEventListener("focusin", (event) => {
    const input = field(event.target);
    if (input) { input.readOnly = true; input.inputMode = "none"; }
  });
})();
