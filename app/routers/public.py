from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse
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
    return {
        "public_id": widget.public_id,
        "widget_type": widget.widget_type,
        "title": widget.title,
        "description": widget.description,
        "button_text": widget.button_text,
        "fields": widget.fields,
        "display_options": widget.display_options,
        "version": "1",
    }


@router.get("/widgets/{public_id}/embed")
def get_embed_snippet(public_id: str, request: Request, db: Session = Depends(get_db)):
    widget = db.scalar(select(Widget).where(Widget.public_id == public_id, Widget.is_active.is_(True)))
    if widget is None:
        raise HTTPException(status_code=404, detail="Widget not found")
    base_url = str(request.base_url).rstrip("/")
    script_url = f"{base_url}/widget/v1/widget.js"
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
      const wrapper = document.createElement("div");
      wrapper.style.maxWidth = "420px";
      wrapper.style.padding = "20px";
      wrapper.style.border = "1px solid #ddd";
      wrapper.style.borderRadius = "12px";
      wrapper.style.fontFamily = "Arial, sans-serif";
      const title = document.createElement("h3");
      title.textContent = config.title;
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
        wrapper.appendChild(label);
      });
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = config.button_text || "Submit";
      button.style.marginTop = "16px";
      button.style.padding = "10px 16px";
      wrapper.appendChild(button);
      mount.replaceChildren(wrapper);
    })
    .catch((error) => console.error("Lead capture widget error:", error));
})();'''
    return PlainTextResponse(content=script, media_type="application/javascript", headers={"Cache-Control": "public, max-age=3600", "X-Widget-Version": "v1"})
