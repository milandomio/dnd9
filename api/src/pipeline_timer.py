"""Pipeline timing utility — records elapsed time for each pipeline step."""

import time
from datetime import datetime
from pathlib import Path


class PipelineTimer:
    def __init__(self, log_dir: Path | str | None = None):
        self.steps: list[tuple[str, float]] = []
        self._start: float | None = None
        self._current_label: str | None = None
        self._start_time = datetime.now()
        self._log_dir = Path(log_dir) if log_dir else None

    def start_step(self, label: str):
        """Start a new step (auto-ends previous)."""
        if self._current_label:
            self.end_step()
        self._current_label = label
        self._start = time.perf_counter()

    def end_step(self):
        """End the current step and record elapsed time."""
        if self._current_label and self._start is not None:
            elapsed = time.perf_counter() - self._start
            self.steps.append((self._current_label, elapsed))
            self._current_label = None
            self._start = None

    def summary(self) -> str:
        """Return a formatted timing summary table."""
        total = sum(t for _, t in self.steps)
        lines = ["", "=" * 60, "Pipeline Timing Summary", "=" * 60]
        for label, elapsed in self.steps:
            pct = (elapsed / total * 100) if total else 0
            lines.append(f"  {label:<40} {elapsed:>8.2f}s  ({pct:>5.1f}%)")
        lines.append("-" * 60)
        lines.append(f"  {'TOTAL':<40} {total:>8.2f}s")
        lines.append("=" * 60)
        return "\n".join(lines)

    def save_log(self) -> Path | None:
        """Save timing log to file. Returns the log file path."""
        if not self._log_dir:
            return None
        self._log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = self._start_time.strftime("%Y%m%d_%H%M%S")
        log_file = self._log_dir / f"pipeline_{timestamp}.log"

        total = sum(t for _, t in self.steps)
        lines = [
            f"Pipeline Run: {self._start_time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total Duration: {total:.2f}s",
            "",
            "Steps:",
        ]
        for label, elapsed in self.steps:
            pct = (elapsed / total * 100) if total else 0
            lines.append(f"  {label}: {elapsed:.2f}s ({pct:.1f}%)")

        log_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return log_file
