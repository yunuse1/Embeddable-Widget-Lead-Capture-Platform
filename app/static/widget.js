(() => {
  "use strict";

  const script = document.currentScript;
  if (!script) return;

  const widgetId = script.dataset.widgetId || new URL(script.src).searchParams.get("id");
  if (!widgetId) return;

  const apiBase = new URL(script.src).origin;
  const mount = document.querySelector(`[data-lead-widget="${CSS.escape(widgetId)}"]`);
  if (!mount) return;

  fetch(`${apiBase}/public/widgets/${encodeURIComponent(widgetId)}/config`)
    .then((response) => {
      if (!response.ok) throw new Error("Unable to load widget configuration");
      return response.json();
    })
    .then((config) => {
      const form = document.createElement("form");
      const wrapper = document.createElement("div");
      wrapper.style.maxWidth = "420px";
      wrapper.style.padding = "20px";
      wrapper.style.border = "1px solid #ddd";
      wrapper.style.borderRadius = "12px";
      wrapper.style.fontFamily = "Arial, sans-serif";

      const title = document.createElement("h3");
      title.textContent = config.title || "Lead capture";
      wrapper.appendChild(title);

      if (config.description) {
        const description = document.createElement("p");
        description.textContent = config.description;
        wrapper.appendChild(description);
      }

      (config.fields || []).forEach((field) => {
        const label = document.createElement("label");
        label.textContent = field.label || field.name || "Field";
        label.style.display = "block";
        label.style.marginTop = "12px";

        const input = document.createElement("input");
        input.type = field.type || "text";
        input.name = field.name || "field";
        input.required = Boolean(field.required);
        input.style.display = "block";
        input.style.width = "100%";
        input.style.boxSizing = "border-box";
        input.style.marginTop = "6px";
        input.style.padding = "10px";
        label.appendChild(input);
        form.appendChild(label);
      });

      const honeypot = document.createElement("input");
      honeypot.type = "text";
      honeypot.name = "website";
      honeypot.tabIndex = -1;
      honeypot.autocomplete = "off";
      honeypot.style.position = "absolute";
      honeypot.style.left = "-9999px";
      form.appendChild(honeypot);

      const button = document.createElement("button");
      button.type = "submit";
      button.textContent = config.button_text || "Submit";
      button.style.marginTop = "16px";
      button.style.padding = "10px 16px";
      form.appendChild(button);

      const status = document.createElement("p");
      status.setAttribute("aria-live", "polite");
      form.appendChild(status);

      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        button.disabled = true;
        status.textContent = "Sending...";

        const data = {};
        (config.fields || []).forEach((field) => {
          const input = form.elements.namedItem(field.name || "field");
          if (input) data[field.name || "field"] = input.value;
        });

        try {
          const response = await fetch(`${apiBase}/public/widgets/${encodeURIComponent(widgetId)}/submissions`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ data, honeypot: honeypot.value }),
          });
          if (!response.ok) throw new Error("Submission failed");
          status.textContent = "Thanks! Your information was submitted.";
          form.reset();
        } catch (error) {
          status.textContent = "Unable to submit. Please try again.";
          console.error("Lead capture widget error:", error);
        } finally {
          button.disabled = false;
        }
      });

      wrapper.appendChild(form);
      mount.replaceChildren(wrapper);
    })
    .catch((error) => console.error("Lead capture widget error:", error));
})();
