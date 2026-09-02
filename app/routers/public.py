from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Widget


router = APIRouter(prefix="/public", tags=["Public Widget"])


@router.get("/widgets/{public_id}/config")
def get_widget_config(public_id: str, db: Session = Depends(get_db)):
    widget = db.scalar(select(Widget).where(Widget.public_id == public_id, Widget.is_active.is_(True)))
    if widget is None:
        raise HTTPException(status_code=404, detail="Widget not found")
    return Response(
        content=__import__("json").dumps({
            "public_id": widget.public_id,
            "widget_type": widget.widget_type,
            "title": widget.title,
            "description": widget.description,
            "button_text": widget.button_text,
            "fields": widget.fields,
            "display_options": widget.display_options,
            "version": "1",
        }),
        media_type="application/json",
        headers={"Cache-Control": "public, max-age=300, must-revalidate", "Vary": "Origin"},
    )


@router.get("/widgets/{public_id}/embed")
def get_embed_snippet(public_id: str, request: Request, db: Session = Depends(get_db)):
    widget = db.scalar(select(Widget).where(Widget.public_id == public_id, Widget.is_active.is_(True)))
    if widget is None:
        raise HTTPException(status_code=404, detail="Widget not found")
    base_url = str(request.base_url).rstrip("/")
    script_url = f"{base_url}/public/widget/v1/widget.js"
    snippet = f'<div data-lead-widget="{widget.public_id}"></div>\n<script src="{script_url}" data-widget-id="{widget.public_id}" async></script>'
    return {"public_id": widget.public_id, "script_url": script_url, "snippet": snippet}


@router.get("/widget/v1/widget.js", response_class=PlainTextResponse)
def widget_script():
    script = '''(() => {
  "use strict";
  const script = document.currentScript;
  if (!script) return;
  const widgetId = script.dataset.widgetId;
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
      honeypot.autocomplete = "off";
      honeypot.tabIndex = -1;
      honeypot.style.position = "absolute";
      honeypot.style.left = "-10000px";
      honeypot.setAttribute("aria-hidden", "true");
      form.appendChild(honeypot);
      const button = document.createElement("button");
      button.type = "submit";
      button.textContent = config.button_text || "Submit";
      button.style.marginTop = "16px";
      button.style.padding = "10px 16px";
      form.appendChild(button);
      const message = document.createElement("p");
      message.setAttribute("role", "status");
      form.appendChild(message);
      wrapper.appendChild(form);
      mount.replaceChildren(wrapper);

      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        if (!form.reportValidity()) return;
        button.disabled = true;
        message.textContent = "Submitting...";
        const data = {};
        (config.fields || []).forEach((field) => {
          const input = form.elements.namedItem(field.name || "field");
          if (input) data[input.name] = input.value;
        });
        try {
          const response = await fetch(`${apiBase}/public/widgets/${encodeURIComponent(widgetId)}/submissions`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ data, honeypot: honeypot.value }),
          });
          const result = await response.json().catch(() => ({}));
          if (!response.ok) throw new Error(result.detail || "Submission failed");
          message.textContent = "Thanks! Your submission was received.";
          form.reset();
        } catch (error) {
          message.textContent = error.message || "Submission failed";
        } finally {
          button.disabled = false;
        }
      });
    })
    .catch((error) => console.error("Lead capture widget error:", error));
})();'''
    return PlainTextResponse(content=script, media_type="application/javascript", headers={"Cache-Control": "public, max-age=86400", "X-Widget-Version": "v1"})
