import requests
from sqlalchemy import event

from flask import Blueprint, request, redirect, url_for, flash, render_template_string
from CTFd.models import Solves, Challenges, Users, Teams, Configs, db
from CTFd.utils.decorators import admins_only
from CTFd.utils.config import get_config

def send_discord_webhook(message):
    webhook = get_config("FIRST_BLOOD_WEBHOOK")
    if not webhook:
        return

    try:
        requests.post(webhook, json={"content": message}, timeout=5)
    except Exception:
        pass


@event.listens_for(Solves, "after_insert")
def first_blood_listener(mapper, connection, solve):
    challenge_id = solve.challenge_id

    result = connection.execute(
        Solves.__table__.select().where(
            Solves.challenge_id == challenge_id
        )
    )

    solves = result.fetchall()
    if len(solves) != 1:
        return

    challenge = Challenges.query.get(challenge_id)
    user = Users.query.get(solve.user_id)
    team = Teams.query.get(solve.team_id) if solve.team_id else None

    solver_name = team.name if team else user.name

    message = (
        f"🩸 **FIRST BLOOD!** 🩸\n"
        f"**Challenge:** {challenge.name}\n"
        f"**Solved by:** {solver_name}"
    )

    send_discord_webhook(message)


admin_blueprint = Blueprint(
    "first_blood_admin",
    __name__,
)


@admin_blueprint.route("/admin/first-blood", methods=["GET", "POST"])
@admins_only
def first_blood_settings():
    if request.method == "POST":
        webhook = request.form.get("webhook", "").strip()
        Configs.set("FIRST_BLOOD_WEBHOOK", webhook)
        db.session.commit()
        flash("First Blood webhook saved", "success")
        return redirect(url_for("first_blood_admin.first_blood_settings"))

    webhook = get_config("FIRST_BLOOD_WEBHOOK") or ""

    return render_template_string(
        """
{% extends "admin/base.html" %}
{% block content %}
<div class="container">
  <h1>First Blood Settings</h1>

  <form method="post">

    <div class="form-group">
      <label>Discord Webhook URL</label>
      <input
        type="text"
        class="form-control"
        name="webhook"
        placeholder="https://discord.com/api/webhooks/..."
        value="{{ webhook }}"
      >
    </div>

    <button type="submit" class="btn btn-primary mt-3">
      Save Webhook
    </button>

    <a href="{{ url_for('first_blood_admin.test_webhook') }}"
       class="btn btn-secondary mt-3 ml-2">
      Test Webhook
    </a>
  </form>
</div>
{% endblock %}
""",
        webhook=webhook,
    )


@admin_blueprint.route("/admin/first-blood/test")
@admins_only
def test_webhook():
    send_discord_webhook("🩸 First Blood test message from CTFd")
    flash("Test message sent (if webhook is valid)", "info")
    return redirect(url_for("first_blood_admin.first_blood_settings"))


def load(app):
    app.register_blueprint(admin_blueprint)
    app.logger.info("First Blood plugin loaded")
