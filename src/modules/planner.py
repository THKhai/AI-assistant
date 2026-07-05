import json
from datetime import date, timedelta

from src.core import services
from src.core.llm import get_llm
from src.core.logger import get_logger

log = get_logger("planner")


def _this_month() -> str:
    return date.today().strftime("%Y-%m")


def _this_week() -> str:
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    return monday.strftime("%Y-W%W")


def _today() -> str:
    return date.today().isoformat()


SYSTEM_PROMPT = """You are a personal planning coach AI. Your job is to help the user plan and track their work.
Be concise, practical, and encouraging. Ask one focused question at a time.
When the user describes tasks, extract them clearly. Format responses for Telegram (use *bold* for emphasis).
Always check in on previous commitments before asking about new plans."""


def _call_llm(messages: list[dict]) -> str:
    from llama_index.core.llms import ChatMessage, MessageRole
    llm = get_llm()
    chat_messages = [
        ChatMessage(role=MessageRole.SYSTEM, content=SYSTEM_PROMPT)
    ] + [
        ChatMessage(
            role=MessageRole.USER if m["role"] == "user" else MessageRole.ASSISTANT,
            content=m["content"],
        )
        for m in messages
    ]
    log.info(f"DeepSeek call — turns={len(messages)}")
    response = llm.chat(chat_messages)
    log.debug(f"DeepSeek response length={len(response.message.content)} chars")
    return response.message.content


class PlannerSession:
    def __init__(self, session_type: str, session_id: str):
        self.session_type = session_type
        self.session_id = session_id
        self.turn = 0
        self.history: list[dict] = []

    def _save_turn(self, role: str, content: str):
        self.turn += 1
        self.history.append({"role": role, "content": content})
        services.conversations.save_turn(self.session_id, "planner", self.session_type, self.turn, role, content)

    def start(self) -> str:
        log.info(f"session started — type={self.session_type} id={self.session_id}")
        if self.session_type == "monthly":
            msg = self._start_monthly()
        elif self.session_type == "weekly":
            msg = self._start_weekly()
        elif self.session_type == "daily":
            msg = self._start_daily()
        elif self.session_type == "evening":
            msg = self._start_evening()
        else:
            msg = "Unknown session type."
        self._save_turn("assistant", msg)
        return msg

    def reply(self, user_input: str) -> str:
        self._save_turn("user", user_input)
        response = _call_llm(self.history)
        self._save_turn("assistant", response)
        return response

    def _start_monthly(self) -> str:
        period = _this_month()
        existing = services.plans.get("planner", "monthly", period)
        if existing:
            content = existing["content"]
            goals = content.get("goals", [])
            goal_list = "\n".join(f"• {g}" for g in goals) if goals else "_none recorded_"
            prompt = (
                f"*Monthly Review — {period}*\n\n"
                f"Last time you set these goals:\n{goal_list}\n\n"
                "How are these going? Would you like to update them or add new ones?"
            )
        else:
            prompt = (
                f"*Monthly Planning — {period}*\n\n"
                "Let's plan your month. What are your 3–5 main goals for this month? "
                "Think in terms of work, personal projects, health, learning, etc."
            )
        return prompt

    def _start_weekly(self) -> str:
        period = _this_week()
        today = date.today().strftime("%A, %B %d")
        monthly = services.plans.get("planner", "monthly", _this_month())
        context = ""
        if monthly:
            goals = monthly["content"].get("goals", [])
            if goals:
                context = "This month's goals:\n" + "\n".join(f"• {g}" for g in goals) + "\n\n"
        existing = services.plans.get("planner", "weekly", period)
        if existing:
            tasks = services.plans.get_tasks(existing["id"])
            done = sum(1 for t in tasks if t["status"] == "done")
            prompt = (
                f"*Weekly Check-in — {period}*\n\n"
                f"{context}"
                f"Last weekly plan had {len(tasks)} tasks, {done} completed.\n\n"
                "What's your focus for the rest of this week?"
            )
        else:
            prompt = (
                f"*Weekly Planning — {period}*\n"
                f"Today is {today}.\n\n"
                f"{context}"
                "What are your main priorities for this week? List the key things you want to accomplish."
            )
        return prompt

    def _start_daily(self) -> str:
        today = _today()
        day_name = date.today().strftime("%A, %B %d")
        weekly = services.plans.get("planner", "weekly", _this_week())
        context = ""
        if weekly:
            tasks = services.plans.get_tasks(weekly["id"])
            pending = [t for t in tasks if t["status"] == "pending"]
            if pending:
                task_lines = "\n".join(f"• {t['description']}" for t in pending[:5])
                context = f"Pending from this week's plan:\n{task_lines}\n\n"
        return (
            f"*Good morning! — {day_name}*\n\n"
            f"{context}"
            "What's your main focus for today? What are the 2–3 things you want to get done?"
        )

    def _start_evening(self) -> str:
        today = _today()
        daily = services.plans.get("planner", "daily", today)
        if daily:
            tasks = services.plans.get_tasks(daily["id"])
            pending = [t for t in tasks if t["status"] == "pending"]
            if pending:
                task_lines = "\n".join(f"• [{t['id']}] {t['description']}" for t in pending)
                return (
                    f"*Evening Check-in*\n\n"
                    f"Today you planned:\n{task_lines}\n\n"
                    "Which of these did you complete? (reply with numbers or 'all done' / describe what happened)"
                )
        return (
            "*Evening Check-in*\n\n"
            "How did your day go? What did you accomplish today, and is there anything to carry over to tomorrow?"
        )


def save_daily_plan(session_id: str, tasks: list[str]) -> int:
    today = _today()
    plan_id = services.plans.save("planner", "daily", today, {"tasks": tasks})
    services.plans.save_tasks(plan_id, "planner", tasks, due_date=today)
    return plan_id


def get_week_status() -> str:
    weekly = services.plans.get("planner", "weekly", _this_week())
    daily = services.plans.get("planner", "daily", _today())

    lines = [f"*Status — Week {_this_week()}*\n"]

    if weekly:
        tasks = services.plans.get_tasks(weekly["id"])
        done = sum(1 for t in tasks if t["status"] == "done")
        lines.append(f"Weekly tasks: {done}/{len(tasks)} done")

    if daily:
        tasks = services.plans.get_tasks(daily["id"])
        done = sum(1 for t in tasks if t["status"] == "done")
        lines.append(f"Today's tasks: {done}/{len(tasks)} done")
        for t in tasks:
            icon = "✅" if t["status"] == "done" else "⏳"
            lines.append(f"  {icon} {t['description']}")

    if len(lines) == 1:
        lines.append("No plans recorded yet. Use /daily to start!")

    return "\n".join(lines)
