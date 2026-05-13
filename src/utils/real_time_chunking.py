"""Real-time chunking utilities for policy deployment."""

import threading

import numpy as np


class RealTimeChunkingBuffer:
    """Thread-safe buffer that fuses overlapping action chunks online."""

    def __init__(self, chunk_size, exp_weight_factor=0.3, debug=False):
        self.chunk_size = chunk_size
        self.exp_weight_factor = exp_weight_factor
        self.debug = debug
        self.control_t = 0
        self.chunks = {}
        self.generation = 0
        self.lock = threading.Lock()

    def clear(self):
        """Reset control time, cached action chunks, and invalidate old producers."""
        with self.lock:
            self.control_t = 0
            self.chunks = {}
            self.generation += 1

    def set_control_time(self, control_t):
        """Update the currently executed control step."""
        with self.lock:
            self.control_t = control_t

    def get_control_time(self):
        """Return the latest control step."""
        with self.lock:
            return self.control_t

    def get_generation(self):
        """Return the current buffer generation."""
        with self.lock:
            return self.generation

    def has_chunk(self, cursor):
        """Check whether an action chunk has already been produced for a cursor."""
        with self.lock:
            return cursor in self.chunks

    def enqueue(self, chunk, cursor, generation=None):
        """Insert a model action chunk if it belongs to the current generation."""
        with self.lock:
            if generation is not None and generation != self.generation:
                if self.debug:
                    print(
                        f"[action_chunks] drop stale chunk cursor={cursor} "
                        f"generation={generation} current={self.generation}"
                    )
                return False
            self.chunks[cursor] = chunk
            return True

    def get_action(self, current_time):
        """Fuse all cached action predictions that cover the current control step."""
        with self.lock:
            relevant = {}
            expired = []
            before_keys = sorted(self.chunks.keys())

            for cursor, chunk in self.chunks.items():
                end = cursor + self.chunk_size
                if cursor <= current_time < end:
                    relevant[cursor] = chunk[current_time - cursor]
                elif end <= current_time:
                    expired.append(cursor)

            for cursor in expired:
                del self.chunks[cursor]

            if self.debug:
                print(
                    f"[action_chunks] t={current_time} before={before_keys} "
                    f"delete={sorted(expired)} after={sorted(self.chunks.keys())}"
                )

            if not relevant:
                return None

            sorted_items = sorted(relevant.items(), key=lambda item: item[0])
            candidate_actions = np.asarray([action for _, action in sorted_items])

        exp_weights = np.exp(self.exp_weight_factor * np.arange(len(candidate_actions)))
        exp_weights = (exp_weights / exp_weights.sum())[:, None]
        return (candidate_actions * exp_weights).sum(axis=0)
