"""Render docs/hero.svg: the TUI with sample (travel) data."""

import asyncio
from datetime import date, timedelta
from pathlib import Path

from zktatr import app as app_mod
from zktatr.models import Task

TODAY = date.today()
OUT = Path(__file__).resolve().parent.parent / "docs" / "hero.svg"


def t(slug, title, tags=(), priority=50, due=None, done=False, depends=()):
    return Task(
        path=f"tasks/{slug}.md",
        title=title,
        status="done" if done else "open",
        priority=priority,
        due=due,
        done=TODAY if done else None,
        modified=TODAY,
        tags=list(tags),
        depends=list(depends),
    )


TASKS = [
    t("japan", "Plan Japan trip", ["japan", "trip"], 100, depends=["flights", "rail", "ryokan"]),
    t("flights", "Book flights to Tokyo", ["japan", "trip"], 100, TODAY - timedelta(days=1)),
    t("rail", "Buy Japan Rail Pass", ["japan", "trip"], 50, depends=["visa"]),
    t("visa", "Check visa requirements", ["japan", "trip"], 50, done=True),
    t("ryokan", "Reserve ryokan in Kyoto", ["japan", "trip"]),
    t("austria", "Plan Austria trip", ["austria", "trip"], 50, depends=["vienna", "hallstatt"]),
    t("vienna", "Book opera tickets in Vienna", ["austria", "trip"]),
    t("hallstatt", "Reserve lake hotel in Hallstatt", ["austria", "trip"]),
    t("passport", "Renew passport", ["admin"], 100),
    t("insurance", "Compare travel insurance", ["admin"]),
    t("yen", "Exchange some yen", ["admin"]),
    t("pack", "Pack carry-on only", []),
    t("guide", "Download offline maps", [], done=True),
    t("sim", "Order eSIM", ["admin"], done=True),
]

app_mod.load_tasks = lambda *a, **k: TASKS
app_mod.TaskApp._fingerprint = lambda self: ("hero",)


async def main() -> None:
    app = app_mod.TaskApp(group="tag")
    async with app.run_test(size=(100, 44)) as pilot:
        await pilot.pause()
        OUT.parent.mkdir(exist_ok=True)
        OUT.write_text(app.export_screenshot(title="todo"))
    print(f"wrote {OUT}")


asyncio.run(main())
