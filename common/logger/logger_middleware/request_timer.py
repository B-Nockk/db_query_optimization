import time
from contextlib import contextmanager


class RequestTimer:
    def __init__(self):
        self.timings = {}

    @contextmanager
    def capture(self, name: str):
        start = time.perf_counter()
        yield
        duration = (time.perf_counter() - start) * 1000
        # Store duration; append if the same name is used multiple times
        self.timings[name] = self.timings.get(name, 0) + duration

    def format_server_timing(self) -> str:
        # Formats into: db;dur=10.5, auth;dur=5.2
        return ", ".join(
            [f"{name};dur={dur:.2f}" for name, dur in self.timings.items()]
        )


__all__ = ["RequestTimer"]
