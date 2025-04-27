"""
Chat models
"""

from django.db import models

from core.models.base import TimestampMixin


class ChatConversation(TimestampMixin):
    """
    Model to store chat conversations.
    """

    user = models.ForeignKey(
        "auth.User", on_delete=models.CASCADE, related_name="chat_conversations"
    )
    title = models.CharField(max_length=200, blank=True)
    job_listing = models.ForeignKey(
        "JobListing",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chat_conversations",
    )

    def __str__(self):
        return f"{self.user.username}'s conversation: {self.title or 'Untitled'}"


class ChatMessage(TimestampMixin):
    """
    Model to store chat messages.
    """

    ROLE_CHOICES = [
        ("user", "User"),
        ("assistant", "Assistant"),
        ("system", "System"),
    ]

    conversation = models.ForeignKey(
        ChatConversation, on_delete=models.CASCADE, related_name="messages"
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()

    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."

    class Meta:
        ordering = ["created_at"]
