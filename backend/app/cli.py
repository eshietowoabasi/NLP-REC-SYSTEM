import click

from .extensions import db
from .models import Role, User


def register_cli(app):
    from .evaluation.cli import eval_cli

    app.cli.add_command(eval_cli)

    @app.cli.command("create-user")
    @click.option("--username", prompt=True)
    @click.option("--email", prompt=True)
    @click.option("--role", type=click.Choice([r.value for r in Role]), default=Role.ADMIN.value, show_default=True)
    @click.password_option()
    def create_user(username, email, role, password):
        """Create a user (use this to bootstrap the first Admin)."""
        if len(password) < 8:
            raise click.ClickException("Password must be at least 8 characters")
        if db.session.execute(db.select(User).filter((User.username == username) | (User.email == email))).first():
            raise click.ClickException("A user with that username or email already exists")
        user = User(username=username, email=email, role=Role(role))
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"Created {role} '{username}' (id={user.user_id})")

    @app.cli.command("fail-stale-runs")
    @click.option("--minutes", type=int, help="Heartbeat age that counts as stale (default: STALE_RUN_MINUTES).")
    def fail_stale_runs_command(minutes):
        """Mark analyses whose worker stopped responding as Failed (so they can be retried)."""
        from .services.analysis import fail_stale_runs

        failed = fail_stale_runs(minutes or app.config["STALE_RUN_MINUTES"])
        click.echo(f"Marked {len(failed)} stale session(s) as failed" + (f": {failed}" if failed else ""))
