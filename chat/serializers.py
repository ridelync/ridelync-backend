from rest_framework import serializers
from .models import ChatMessage, GroupChat, GroupMessage
from django.contrib.auth import get_user_model
import cloudinary.uploader

User = get_user_model()


class ChatMessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.ReadOnlyField(source="sender.username")
    receiver_username = serializers.ReadOnlyField(source="receiver.username")
    media_url = serializers.SerializerMethodField()

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
            "media_file",
            "media_type",
            "media_content_type",
            "media_url",
        ]
    
    def get_media_url(self, obj):
        if obj.media_file:
            return obj.media_file.url
        return None


class GroupChatSerializer(serializers.ModelSerializer):
    members = serializers.StringRelatedField(many=True)

    class Meta:
        model = GroupChat
        fields = ["id", "name", "members", "created_at"]


class GroupMessageSerializer(serializers.ModelSerializer):
    fullname = serializers.CharField(source="sender.get_full_name")
    media_url = serializers.SerializerMethodField()

    class Meta:
        model = GroupMessage
        fields = [
            "id",
            "message",
            "timestamp",
            "fullname",
            "media_file",
            "media_type",
            "media_content_type",
            "media_url",
        ]
    
    def get_media_url(self, obj):
        if obj.media_file:
            return obj.media_file.url
        return None