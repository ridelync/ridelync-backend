from django.db import models
from django.contrib.auth import get_user_model
from cloudinary.models import CloudinaryField

User = get_user_model()


class ChatMessage(models.Model):
    sender = models.ForeignKey(
        User, related_name="sent_messages", on_delete=models.CASCADE
    )
    receiver = models.ForeignKey(
        User, related_name="received_messages", on_delete=models.CASCADE
    )
    message = models.TextField(
        blank=True, null=True
    )  # Made optional for media-only messages
    timestamp = models.DateTimeField(auto_now_add=True)
    user1_deleted = models.BooleanField(default=False)  # If sender clears chat
    user2_deleted = models.BooleanField(default=False)  # If receiver clears chat

    # Media fields
    media_file = CloudinaryField("media", blank=True, null=True, resource_type="auto")
    media_type = models.CharField(
        max_length=10, blank=True, null=True
    )  # 'image', 'video', 'audio'
    media_content_type = models.CharField(
        max_length=100, blank=True, null=True
    )  # MIME type

    class Meta:
        ordering = ["timestamp"]


class GroupChat(models.Model):
    name = models.CharField(max_length=255)  # Group Name
    members = models.ManyToManyField(User, related_name="group_chats")  # Group Members
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class GroupMessage(models.Model):
    group = models.ForeignKey(
        GroupChat, related_name="messages", on_delete=models.CASCADE
    )
    sender = models.ForeignKey(
        User, related_name="group_messages", on_delete=models.CASCADE
    )
    message = models.TextField(
        blank=True, null=True
    )  # Made optional for media-only messages
    timestamp = models.DateTimeField(auto_now_add=True)

    # Media fields
    media_file = CloudinaryField("media", blank=True, null=True, resource_type="auto")
    media_type = models.CharField(
        max_length=10, blank=True, null=True
    )  # 'image', 'video', 'audio'
    media_content_type = models.CharField(
        max_length=100, blank=True, null=True
    )  # MIME type

    class Meta:
        ordering = ["timestamp"]

    def __str__(self):
        return (
            f"{self.sender.username}: {self.message[:50] if self.message else 'Media'}"
        )
