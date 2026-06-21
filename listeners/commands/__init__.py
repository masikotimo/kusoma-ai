from slack_bolt.async_app import AsyncApp

from .kusoma_scan import handle_kusoma_command


def register(app: AsyncApp):
    app.command("/kusoma")(handle_kusoma_command)
