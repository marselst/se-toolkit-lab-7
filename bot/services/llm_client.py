"""LLM client for intent-based routing."""

import json
import sys
from typing import Any

import httpx

from .api_client import APIClient


# Tool definitions for the LLM
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_items",
            "description": "Get list of all labs and tasks. Use this to discover what labs exist.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_learners",
            "description": "Get list of enrolled students and their groups.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_scores",
            "description": "Get score distribution (4 buckets) for a specific lab.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {
                        "type": "string",
                        "description": "Lab identifier, e.g. 'lab-01', 'lab-04'",
                    }
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_pass_rates",
            "description": "Get per-task average scores and attempt counts for a lab.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {
                        "type": "string",
                        "description": "Lab identifier, e.g. 'lab-01', 'lab-04'",
                    }
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_timeline",
            "description": "Get submissions per day for a lab to see activity over time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {
                        "type": "string",
                        "description": "Lab identifier, e.g. 'lab-01', 'lab-04'",
                    }
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_groups",
            "description": "Get per-group scores and student counts for a lab.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {
                        "type": "string",
                        "description": "Lab identifier, e.g. 'lab-01', 'lab-04'",
                    }
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_learners",
            "description": "Get top N learners by score for a lab.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {
                        "type": "string",
                        "description": "Lab identifier, e.g. 'lab-01', 'lab-04'",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of top learners to return, default 5",
                    },
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_completion_rate",
            "description": "Get completion rate percentage for a lab.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {
                        "type": "string",
                        "description": "Lab identifier, e.g. 'lab-01', 'lab-04'",
                    }
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "trigger_sync",
            "description": "Trigger ETL sync to refresh data from autochecker.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
]

SYSTEM_PROMPT = """You are an LMS assistant that helps students and teachers get information about labs, scores, and learners.

You have access to tools that can fetch data from the LMS backend. When a user asks a question:
1. Think about what data you need to answer
2. Call the appropriate tools to get that data
3. Use the tool results to formulate a helpful answer

If the user's message is a greeting (like "hello", "hi"), respond warmly and mention what you can help with.
If the user's message is unclear or gibberish, politely ask for clarification and suggest what you can do.
If the user mentions a lab without specifying what they want, ask what information they need about that lab.

Always be helpful and provide specific data when available. If a tool call fails, explain what went wrong.
"""


class LLMError(Exception):
    """Exception raised when LLM request fails."""

    pass


class LLMClient:
    """Client for LLM API with tool calling support."""

    def __init__(self, api_key: str, base_url: str, model: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=60.0,
        )

    def chat(
        self, messages: list[dict], tools: list[dict] | None = None
    ) -> dict:
        """Send a chat request to the LLM.

        Args:
            messages: List of message dicts with 'role' and 'content'
            tools: Optional list of tool definitions

        Returns:
            LLM response dict
        """
        payload = {
            "model": self.model,
            "messages": messages,
        }
        if tools:
            payload["tools"] = tools

        try:
            response = self._client.post("/chat/completions", json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise LLMError(f"HTTP {e.response.status_code}: {e.response.text}")
        except httpx.ConnectError as e:
            raise LLMError(f"Connection refused to LLM at {self.base_url}")
        except Exception as e:
            raise LLMError(f"LLM error: {e}")

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()


class IntentRouter:
    """Routes user messages to tools via LLM."""

    def __init__(self, api_client: APIClient, llm_client: LLMClient):
        self.api_client = api_client
        self.llm_client = llm_client
        self.tool_map = {
            "get_items": self._get_items,
            "get_learners": self._get_learners,
            "get_scores": self._get_scores,
            "get_pass_rates": self._get_pass_rates,
            "get_timeline": self._get_timeline,
            "get_groups": self._get_groups,
            "get_top_learners": self._get_top_learners,
            "get_completion_rate": self._get_completion_rate,
            "trigger_sync": self._trigger_sync,
        }

    def _debug(self, message: str) -> None:
        """Print debug message to stderr."""
        print(f"[intent] {message}", file=sys.stderr)

    def _execute_tool(self, name: str, args: dict) -> Any:
        """Execute a tool and return result."""
        self._debug(f"Executing tool: {name}({args})")
        try:
            if name not in self.tool_map:
                return f"Unknown tool: {name}"
            return self.tool_map[name](**args)
        except Exception as e:
            return f"Error executing {name}: {e}"

    def _get_items(self) -> list:
        """Get all items."""
        items = self.api_client.get_items()
        return [{"id": i.id, "title": i.title, "type": i.type} for i in items]

    def _get_learners(self) -> list:
        """Get all learners."""
        try:
            data = self.api_client._request("GET", "/learners/")
            return data
        except Exception as e:
            return [f"Error: {e}"]

    def _get_scores(self, lab: str) -> list:
        """Get score distribution for a lab."""
        try:
            data = self.api_client._request("GET", "/analytics/scores", params={"lab": lab})
            return data
        except Exception as e:
            return [f"Error: {e}"]

    def _get_pass_rates(self, lab: str) -> list:
        """Get pass rates for a lab."""
        pass_rates = self.api_client.get_pass_rates(lab)
        return [{"task": pr.task, "avg_score": pr.avg_score, "attempts": pr.attempts} for pr in pass_rates]

    def _get_timeline(self, lab: str) -> list:
        """Get timeline for a lab."""
        try:
            data = self.api_client._request("GET", "/analytics/timeline", params={"lab": lab})
            return data
        except Exception as e:
            return [f"Error: {e}"]

    def _get_groups(self, lab: str) -> list:
        """Get groups for a lab."""
        try:
            data = self.api_client._request("GET", "/analytics/groups", params={"lab": lab})
            return data
        except Exception as e:
            return [f"Error: {e}"]

    def _get_top_learners(self, lab: str, limit: int = 5) -> list:
        """Get top learners for a lab."""
        try:
            data = self.api_client._request(
                "GET", "/analytics/top-learners", params={"lab": lab, "limit": limit}
            )
            return data
        except Exception as e:
            return [f"Error: {e}"]

    def _get_completion_rate(self, lab: str) -> dict:
        """Get completion rate for a lab."""
        try:
            data = self.api_client._request("GET", "/analytics/completion-rate", params={"lab": lab})
            return data
        except Exception as e:
            return {"error": str(e)}

    def _trigger_sync(self) -> dict:
        """Trigger ETL sync."""
        try:
            data = self.api_client._request("POST", "/pipeline/sync", params={})
            return data
        except Exception as e:
            return {"error": str(e)}

    def route(self, message: str) -> str:
        """Route a message through the LLM and return a response.

        Args:
            message: User's message text

        Returns:
            Response text
        """
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ]

        max_iterations = 5
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            self._debug(f"Iteration {iteration}")

            try:
                response = self.llm_client.chat(messages, tools=TOOLS)
            except LLMError as e:
                return f"LLM error: {e}"

            choice = response.get("choices", [{}])[0].get("message", {})

            # Check if LLM wants to call tools
            tool_calls = choice.get("tool_calls", [])

            if not tool_calls:
                # LLM provided a final answer
                content = choice.get("content", "I don't have a response for that.")
                self._debug(f"Final answer: {content[:100]}...")
                return content

            # Execute tool calls
            self._debug(f"LLM called {len(tool_calls)} tool(s)")

            # Add assistant's message to conversation
            messages.append({"role": "assistant", "content": None, "tool_calls": tool_calls})

            # Execute each tool call
            for tool_call in tool_calls:
                function = tool_call.get("function", {})
                name = function.get("name", "")
                args_str = function.get("arguments", "{}")

                try:
                    args = json.loads(args_str) if args_str else {}
                except json.JSONDecodeError:
                    args = {}

                self._debug(f"Tool: {name}({args})")

                result = self._execute_tool(name, args)
                self._debug(f"Result: {str(result)[:200]}...")

                # Add tool result to conversation
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.get("id", ""),
                    "content": json.dumps(result, default=str),
                })

            self._debug(f"Feeding {len(tool_calls)} tool result(s) back to LLM")

        return "I'm having trouble processing this request. Please try rephrasing."
