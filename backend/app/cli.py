import click

from .extensions import db
from .models import Role, User


def register_cli(app):
    @app.cli.command("create-user")
    @click.option("--username", prompt=True)
    @click.option("--email", prompt=True)
    @click.option("--role", type=click.Choice([r.value for r in Role]), default=Role.ADMIN.value, show_default=True)
    @click.password_option()
    def create_user(username, email, role, password):
        """Create a user (use this to bootstrap the first Admin)."""
        if db.session.execute(db.select(User).filter((User.username == username) | (User.email == email))).first():
            raise click.ClickException("A user with that username or email already exists")
        user = User(username=username, email=email, role=Role(role))
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"Created {role} '{username}' (id={user.user_id})")
