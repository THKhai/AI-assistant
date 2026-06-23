def bold(text: str) -> str:
    return f"*{text}*"


def code(text: str) -> str:
    return f"`{text}`"


def task_line(description: str, status: str) -> str:
    icon = {"done": "✅", "pending": "⏳", "skipped": "⏭️"}.get(status, "•")
    return f"{icon} {description}"


def task_list(tasks: list[dict]) -> str:
    if not tasks:
        return "_No tasks_"
    return "\n".join(task_line(t["description"], t["status"]) for t in tasks)


def completion_summary(tasks: list[dict]) -> str:
    if not tasks:
        return "No tasks tracked."
    done = sum(1 for t in tasks if t["status"] == "done")
    total = len(tasks)
    pct = int(done / total * 100)
    return f"Completion: {done}/{total} ({pct}%)"
