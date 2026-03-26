"""Command handlers - pure functions that take input and return text.

These handlers have no dependency on Telegram. They can be called from:
- --test mode (CLI)
- Unit tests
- Telegram bot
"""

from config import load_config
from services.api_client import APIClient, APIError
from services.llm_client import LLMClient, IntentRouter, LLMError


def _get_client() -> APIClient:
    """Create an API client from config."""
    config = load_config()
    return APIClient(config.lms_api_url, config.lms_api_key)


def _get_llm_client() -> LLMClient:
    """Create an LLM client from config."""
    config = load_config()
    return LLMClient(
        api_key=config.llm_api_key,
        base_url=config.llm_api_base_url,
        model=config.llm_api_model,
    )


def _get_intent_router() -> IntentRouter:
    """Create an intent router with API and LLM clients."""
    api_client = _get_client()
    llm_client = _get_llm_client()
    return IntentRouter(api_client, llm_client)


def handle_start(args: str) -> str:
    """Handle /start command."""
    return """Welcome to the LMS Bot!

I can help you with:
- View available labs and tasks
- Check scores and pass rates
- See top learners and group performance
- Track completion rates

Use /help to see all commands, or just ask me a question like:
• "What labs are available?"
• "Show me scores for lab 4"
• "Which lab has the lowest pass rate?"
• "Who are the top 5 students in lab 04?"
"""


def handle_help(args: str) -> str:
    """Handle /help command."""
    return """Available commands:
/start - Welcome message
/help - Show this help message
/health - Check backend status
/labs - List available labs
/scores <lab_id> - Get scores for a lab

Or just ask me a question in plain English!
Examples:
• "What labs are available?"
• "Show me scores for lab 4"
• "Which lab has the lowest pass rate?"
• "Who are the top 5 students?"
"""


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


def handle_natural_language(message: str) -> str:
    """Handle natural language messages using LLM intent routing.

    Args:
        message: User's message text

    Returns:
        Response from the intent router
    """
    try:
        router = _get_intent_router()
        return router.route(message)
    except LLMError as e:
        return f"LLM error: {e}"
    except Exception as e:
        return f"Error processing your message: {e}"


def get_inline_keyboard() -> list:
    """Get inline keyboard buttons for common actions.

    Returns:
        List of inline keyboard rows with buttons
    """
    return [
        [
            {"text": "📚 Labs", "callback_data": "cmd_labs"},
            {"text": "📊 Scores", "callback_data": "cmd_scores"},
        ],
        [
            {"text": "💪 Top Students", "callback_data": "cmd_top"},
            {"text": "📈 Completion", "callback_data": "cmd_completion"},
        ],
    ]
