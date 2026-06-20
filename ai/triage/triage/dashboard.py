from __future__ import annotations

import sys
from datetime import datetime, timezone

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, OptionList
from textual.widgets.option_list import Option

from . import kitty
from . import state as state_module
from .state import SessionRow, State


def humanize_age(iso_ts: str | None) -> str:
    if not iso_ts:
        return "?"
    try:
        dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    except ValueError:
        return "?"
    now = datetime.now(timezone.utc)
    delta = (now - dt).total_seconds()
    if delta < 0:
        delta = 0
    if delta < 60:
        return f"{int(delta)}s"
    if delta < 3600:
        return f"{int(delta / 60)}m"
    return f"{int(delta / 3600)}h"


class TriageApp(App):
    CSS = """
    Screen { background: $background; }
    OptionList { height: 1fr; border: none; }
    """

    BINDINGS = [
        Binding("q", "quit", "quit"),
        Binding("r", "refresh", "refresh"),
        Binding("j", "cursor_down", "down", show=False),
        Binding("k", "cursor_up", "up", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield OptionList(id="sessions")
        yield Footer()

    def on_mount(self) -> None:
        self.title = "triage"
        self.sub_title = "j/k move  ↵ jump  r refresh  q quit"
        self.set_interval(0.5, self.refresh_data)
        self.refresh_data()

    def refresh_data(self) -> None:
        ds = state_module.read_state()
        sessions = ds.sessions if ds else []
        needs = [s for s in sessions if s.state == State.NEEDS_YOU]
        running = [s for s in sessions if s.state == State.RUNNING]

        tab_counts: dict[int, int] = {}
        for s in sessions:
            tab_counts[s.tab_id] = tab_counts.get(s.tab_id, 0) + 1

        ol = self.query_one("#sessions", OptionList)
        prev_index = ol.highlighted

        opts: list[Option] = []
        if not (needs or running):
            opts.append(Option("  no codex sessions detected", disabled=True))
        else:
            if needs:
                opts.append(
                    Option(f"[b red]NEEDS YOU ({len(needs)})[/]", disabled=True)
                )
                for s in needs:
                    opts.append(
                        Option(
                            self._format_row(s, idle=True, tab_counts=tab_counts),
                            id=f"win-{s.window_id}",
                        )
                    )
            if running:
                if needs:
                    opts.append(Option("", disabled=True))
                opts.append(
                    Option(f"[b green]RUNNING ({len(running)})[/]", disabled=True)
                )
                for s in running:
                    opts.append(
                        Option(
                            self._format_row(s, idle=False, tab_counts=tab_counts),
                            id=f"win-{s.window_id}",
                        )
                    )

        ol.clear_options()
        ol.add_options(opts)

        if prev_index is not None and prev_index < ol.option_count:
            ol.highlighted = prev_index
        else:
            for i in range(ol.option_count):
                opt = ol.get_option_at_index(i)
                if not opt.disabled:
                    ol.highlighted = i
                    break

    @staticmethod
    def _format_row(
        s: SessionRow, idle: bool, tab_counts: dict[int, int]
    ) -> str:
        verb = "idle" if idle else "last ev"
        age = humanize_age(s.last_event_at)
        suffix = "ago" if not idle else ""
        title = s.tab_title or "(untitled)"
        loc = (
            f"tab {s.tab_id}·w{s.window_id}"
            if tab_counts.get(s.tab_id, 0) > 1
            else f"tab {s.tab_id}"
        )
        return f"  [{loc}]  {title}    {verb} {age}{(' ' + suffix) if suffix else ''}"

    def action_refresh(self) -> None:
        self.refresh_data()

    def on_option_list_option_selected(
        self, event: OptionList.OptionSelected
    ) -> None:
        opt_id = event.option.id
        if not opt_id or not opt_id.startswith("win-"):
            return
        try:
            window_id = int(opt_id.split("-", 1)[1])
        except ValueError:
            return
        kitty.focus_window(window_id)


def main(argv: list[str] | None = None) -> int:
    TriageApp().run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
