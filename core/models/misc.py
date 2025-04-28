from django.db import models

from .base import TimestampMixin


class LangGraphCheckpoint(TimestampMixin):
    thread_id = models.CharField(max_length=255, db_index=True)
    checkpoint = models.BinaryField()  # Store the serialized checkpoint
    parent_ts = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    # Add other fields if needed based on LangGraph checkpoint structure

    class Meta:
        ordering = ["-updated_at"]  # Get latest first by default
        verbose_name = "LangGraph Checkpoint"
        verbose_name_plural = "LangGraph Checkpoints"

    def __str__(self):
        # Use updated_at from TimestampMixin
        ts = self.updated_at.isoformat() if self.updated_at else "N/A"
        return f"Checkpoint for thread {self.thread_id} @ {ts}"
