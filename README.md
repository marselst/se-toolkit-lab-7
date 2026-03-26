# Lab 7 1— Build a Client with an AI Coding Agent

[Sync your fork](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/syncing-a-fork#syncing-a-fork-branch-from-the-command-line) regularly — the lab gets updated.

## Product brief

> Build a Telegram bot that lets users interact with the LMS backend through chat. Users should be able to check system health, browse labs and scores, and ask questions in plain language. The bot should use an LLM to understand what the user wants and fetch the right data. Deploy it alongside the existing backend on the VM.

This is what a customer might tell you. Your job is to turn it into a working product using an AI coding agent (Qwen Code) as your development partner.

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│  ┌──────────────┐     ┌──────────────────────────────────┐   │
│  │  Telegram    │────▶│  Your Bot                        │   │
│  │  User        │◀────│  (aiogram / python-telegram-bot) │   │
│  └──────────────┘     └──────┬───────────────────────────┘   │
│                              │                               │
│                              │ slash commands + plain text    │
│                              ├───────▶ /start, /help         │
│                              ├───────▶ /health, /labs        │
│                              ├───────▶ intent router ──▶ LLM │
│                              │                    │          │
│                              │                    ▼          │
│  ┌──────────────┐     ┌──────┴───────┐    tools/actions      │
│  │  Docker      │     │  LMS Backend │◀───── GET /items      │
│  │  Compose     │     │  (FastAPI)   │◀───── GET /analytics  │
│  │              │     │  + PostgreSQL│◀───── POST /sync      │
│  └──────────────┘     └──────────────┘                       │
└──────────────────────────────────────────────────────────────┘
```

## Requirements

### P0 — Must have

1. Testable handler architecture — handlers work without Telegram
2. CLI test mode: `cd bot && uv run bot.py --test "/command"` prints response to stdout
3. `/start` — welcome message
4. `/help` — lists all available commands
5. `/health` — calls backend, reports up/down status
6. `/labs` — lists available labs
7. `/scores <lab>` — per-task pass rates
8. Error handling — backend down produces a friendly message, not a crash

### P1 — Should have

1. Natural language intent routing — plain text interpreted by LLM
2. All 9 backend endpoints wrapped as LLM tools
3. Inline keyboard buttons for common actions
4. Multi-step reasoning (LLM chains multiple API calls)

### P2 — Nice to have

1. Rich formatting (tables, charts as images)
2. Response caching
3. Conversation context (multi-turn)

### P3 — Deployment

1. Bot containerized with Dockerfile
2. Added as service in `docker-compose.yml`
3. Deployed and running on VM
4. README documents deployment

## Learning advice

Notice the progression above: **product brief** (vague customer ask) → **prioritized requirements** (structured) → **task specifications** (precise deliverables + acceptance criteria). This is how engineering work flows.

You are not following step-by-step instructions — you are building a product with an AI coding agent. The learning comes from planning, building, testing, and debugging iteratively.

## Learning outcomes

By the end of this lab, you should be able to say:

1. I turned a vague product brief into a working Telegram bot.
2. I can ask it questions in plain language and it fetches the right data.
3. I used an AI coding agent to plan and build the whole thing.

## Tasks

### Prerequisites

1. Complete the [lab setup](./lab/setup/setup-simple.md#lab-setup)

> **Note**: First time in this course? Do the [full setup](./lab/setup/setup-full.md#lab-setup) instead.

### Required

1. [Plan and Scaffold](./lab/tasks/required/task-1.md) — P0: project structure + `--test` mode
2. [Backend Integration](./lab/tasks/required/task-2.md) — P0: slash commands + real data
3. [Intent-Based Natural Language Routing](./lab/tasks/required/task-3.md) — P1: LLM tool use
4. [Containerize and Document](./lab/tasks/required/task-4.md) — P3: containerize + deploy

## Deploy

This section explains how to deploy the bot alongside the LMS backend using Docker Compose.

### Prerequisites

- Docker and Docker Compose installed on the VM
- `.env.docker.secret` file configured with all required environment variables
- Bot token from @BotFather on Telegram

### Environment variables

The bot requires these variables in `.env.docker.secret`:

| Variable | Description | Example |
|----------|-------------|---------|
| `BOT_TOKEN` | Telegram bot token from @BotFather | `123456:ABC-DEF1234...` |
| `LMS_API_KEY` | API key for the LMS backend | `my-secret-api-key` |
| `LLM_API_KEY` | API key for the Qwen Code API | `my-secret-qwen-key` |
| `LLM_API_MODEL` | Model name for the LLM | `coder-model` |

Note: `LMS_API_URL` and `LLM_API_BASE_URL` are set in `docker-compose.yml` using Docker networking:
- Backend: `http://backend:8000` (Docker service name)
- LLM: `http://host.docker.internal:42005/v1` (host network via extra_hosts)

### Deploy commands

1. **Stop any running bot process** (from earlier development):
   ```bash
   pkill -f "bot.py" 2>/dev/null
   ```

2. **Navigate to the project directory**:
   ```bash
   cd ~/se-toolkit-lab-7
   ```

3. **Build and start all services**:
   ```bash
   docker compose --env-file .env.docker.secret up --build -d
   ```

4. **Check service status**:
   ```bash
   docker compose --env-file .env.docker.secret ps
   ```
   You should see `bot`, `backend`, `postgres`, `pgadmin`, and `caddy` running.

5. **View bot logs**:
   ```bash
   docker compose --env-file .env.docker.secret logs bot --tail 30
   ```
   Look for "Starting bot..." and no Python tracebacks.

### Verify deployment

1. **Check backend is healthy**:
   ```bash
   curl -sf http://localhost:42002/docs
   ```

2. **Test in Telegram**:
   - Send `/start` — should receive welcome message
   - Send `/health` — should show backend status
   - Send "what labs are available?" — should list labs (LLM-powered)
   - Send "which lab has the lowest pass rate?" — should compare all labs

3. **Check bot container**:
   ```bash
   docker compose --env-file .env.docker.secret ps bot
   ```

### Troubleshooting

| Symptom | Solution |
|---------|----------|
| Bot container restarting | Check logs: `docker compose logs bot`; verify `BOT_TOKEN` is valid |
| `/health` fails | Ensure `LMS_API_URL=http://backend:8000` (not localhost) |
| LLM queries fail | Ensure `LLM_API_BASE_URL` uses `host.docker.internal` |
| Build fails at `uv sync` | Verify `uv.lock` exists in bot directory |

### Redeploy after changes

```bash
cd ~/se-toolkit-lab-7
git pull
docker compose --env-file .env.docker.secret up --build -d
```
