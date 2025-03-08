from rest_framework import serializers
from .models import ChatMessage
from .models import GroupChat, GroupMessage
from django.contrib.auth import get_user_model

User = get_user_model()


class ChatMessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.ReadOnlyField(source="sender.username")
    receiver_username = serializers.ReadOnlyField(source="receiver.username")

    class Meta:
        model = ChatMessage
        fields = [
            "id",
            "sender",
            "receiver",
            "message",
            "timestamp",
            "sender_username",
            "receiver_username",
        ]


class GroupChatSerializer(serializers.ModelSerializer):
    # Use Nested Serializer to include the usernames of members instead of just IDs
    members = serializers.StringRelatedField(
        many=True
    )  # This will display the usernames of the members

    class Meta:
        model = GroupChat
        fields = ["id", "name", "members", "created_at"]


class GroupMessageSerializer(serializers.ModelSerializer):
    fullname = serializers.CharField(
        source="sender.get_full_name"
    )  # Include the sender's username

    class Meta:
        model = GroupMessage
        fields = [
            "id",
            "message",
            "timestamp",
            "fullname",
        ]  # Add the username field to the response
