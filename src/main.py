import click
from src.utils.config import load_config, get_env
from src.integrations.weather_api import OpenWeatherClient
from src.integrations.n8n_api import N8NClient
from src.integrations.calendar_api import CalendarClient
from src.agent.types import ToolContext
from src.agent.coordinator import run_task

@click.command()
@click.option("--user", "user_id", default="me", help="User ID for this session")
def cli(user_id: str):
    load_config()
    ow_key = get_env("OPENAI_API_KEY")
    if not ow_key:
        click.echo("Warning: OPENAI_API_KEY missing; agent will not run.")
    w_key = get_env("OPENWEATHERMAP_API_KEY")
    n8n_url = get_env("N8N_WEBHOOK_URL")

    weather_client = OpenWeatherClient(api_key=w_key) if w_key else None
    n8n_client = N8NClient(webhook_url=n8n_url) if n8n_url else None
    calendar_client = CalendarClient(user_id=user_id)

    ctx = ToolContext(
        weather_client=weather_client,
        n8n_client=n8n_client,
        calendar_client=calendar_client,
    )

    click.echo("Agent ready. Type your request (Ctrl+C to exit).")
    while True:
        try:
            prompt = click.prompt("> ")
            if not prompt.strip():
                continue
            result = run_task(ctx, prompt)
            click.echo(result)
        except KeyboardInterrupt:
            click.echo("\nBye!")
            break

if __name__ == "__main__":
    cli()