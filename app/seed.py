from app.database import SessionLocal
from app.models import Tenant, User, Widget
from app.security import hash_password


def seed() -> None:
    db = SessionLocal()
    try:
        tenant = db.query(Tenant).filter(Tenant.email == "demo@example.com").first()
        if tenant is None:
            tenant = Tenant(name="Demo Tenant", email="demo@example.com")
            db.add(tenant)
            db.flush()

        user = db.query(User).filter(User.email == "demo@example.com").first()
        if user is None:
            db.add(User(
                tenant_id=tenant.id,
                email="demo@example.com",
                password_hash=hash_password("DemoPassword123!"),
            ))

        widget = db.query(Widget).filter(Widget.public_id == "demo-widget").first()
        if widget is None:
            db.add(Widget(
                tenant_id=tenant.id,
                public_id="demo-widget",
                widget_type="lead_capture",
                title="Contact us",
                description="Leave your details and we will get back to you.",
                button_text="Send",
                fields=[
                    {"name": "name", "label": "Name", "type": "text", "required": True},
                    {"name": "email", "label": "Email", "type": "email", "required": True},
                ],
                display_options={},
                is_active=True,
            ))

        db.commit()
        print("Seed complete: demo@example.com / DemoPassword123! / demo-widget")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
