from datetime import datetime
from pathlib import Path


class _StepContext:
    def __init__(self, pipe, label, step_num, total):
        self.pipe = pipe
        self.label = label
        self.step_num = step_num
        self.total = total
        self._result_msg = ""

    def set_result(self, msg: str):
        self._result_msg = msg

    def __enter__(self):
        if self.total:
            self._prefix = f"[{self.step_num}/{self.total}]"
        else:
            self._prefix = ""
        self.pipe.timer.start_step(f"{self._prefix} {self.label}".strip())
        self.pipe.log(f"{self._prefix} {self.label} START".strip())
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            msg = f"{self._prefix} {self.label} DONE"
            if self._result_msg:
                msg += f" -> {self._result_msg}"
            self.pipe.log(msg.strip())
        return False


class Pipeline:
    def __init__(self, log_dir: Path | None = None):
        from pipeline_timer import PipelineTimer

        self.timer = PipelineTimer(log_dir)
        self._step_count = 0
        self._log_file = None
        if log_dir:
            log_dir.mkdir(parents=True, exist_ok=True)
            self._log_file = open(  # noqa: SIM115
                log_dir / f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
                "w",
                encoding="utf-8",
            )

    def log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        print(line, flush=True)
        if self._log_file:
            self._log_file.write(line + "\n")
            self._log_file.flush()

    def step(self, label: str) -> _StepContext:
        self._step_count += 1
        return _StepContext(self, label, self._step_count, None)

    def phase(self, label: str, total: int) -> _StepContext:
        self._step_count += 1
        return _StepContext(self, label, self._step_count, total)

    def close(self):
        if self._log_file:
            self._log_file.close()
            self._log_file = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
