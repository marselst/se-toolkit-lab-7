"""Command handlers - pure functions that take input and return text.

These handlers have no dependency on Telegram. They can be called from:
- --test mode (CLI)
- Unit tests
- Telegram bot
"""

from config import load_config
from services.api_client import APIClient, APIError


def _get_client() -> APIClient:
    """Create an API client from config."""
    config = load_config()
    return APIClient(config.lms_api_url, config.lms_api_key)


def handle_start(args: str) -> str:
    """Handle /start command."""
    config = load_config()
    return f"Welcome to the LMS Bot! Use /help to see available commands."


def handle_help(args: str) -> str:
    """Handle /help command."""
    return """Available commands:
/start - Welcome message
/help - Show this help message
/health - Check backend status
/labs - List available labs
/scores <lab_id> - Get scores for a lab"""


def handle_health(args: str) -> str:
    """Handle /health command."""
    try:
        client = _get_client()
        is_healthy, message, count = client.check_health()
        return message
    except APIError as e:
        return f"Backend error: {e.message}"


def handle_labs(args: str) -> str:
    """Handle /labs command."""
    try:
        client = _get_client()
        items = client.get_items()
        # Filter only labs (not tasks)
        labs = [item for item in items if item.type == "lab"]
        if not labs:
            return "No labs found in the backend."
        lines = ["Available labs:"]
        for lab in labs:
            lines.append(f"- {lab.title}")
        return "\n".join(lines)
    except APIError as e:
        return f"Backend error: {e.message}"


def handle_scores(args: str) -> str:
    """Handle /scores command."""
    if not args.strip():
        return "Please specify a lab ID. Usage: /scores lab-04"

    lab_id = args.strip()

    try:
        client = _get_client()
        pass_rates = client.get_pass_rates(lab_id)
        if not pass_rates:
            return f"No pass rate data found for {lab_id}."

        lines = [f"Pass rates for {lab_id}:"]
        for pr in pass_rates:
            lines.append(f"- {pr.task}: {pr.avg_score:.1f}% ({pr.attempts} attempts)")
        return "\n".join(lines)
    except APIError as e:
        return f"Backend error: {e.message}"
