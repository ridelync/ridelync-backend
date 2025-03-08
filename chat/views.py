from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from .models import ChatMessage
from .serializers import ChatMessageSerializer
from django.contrib.auth import get_user_model
from django.db.models import Q
from .models import ChatMessage, GroupChat, GroupMessage
from .serializers import (
    ChatMessageSerializer,
    GroupChatSerializer,
    GroupMessageSerializer,
)


User = get_user_model()


# Get personal messages
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_messages(request, user_id):
    """Fetch chat messages between logged-in user and another user, excluding deleted messages"""

    try:
        other_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({"error": "User not found"}, status=404)

    messages = ChatMessage.objects.filter(
        (
            Q(sender=request.user, receiver=other_user, user1_deleted=False)
            | Q(sender=other_user, receiver=request.user, user2_deleted=False)
        )
    ).order_by("timestamp")

    serializer = ChatMessageSerializer(messages, many=True)
    return Response(serializer.data)


# Send personal messages
@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def send_message(request):
    """Send a message with optional media to another user"""
    sender = request.user
    receiver_id = request.data.get("receiver")
    message_text = request.data.get("message", "")
    media_file = request.FILES.get("media_file")
    media_type = request.data.get("media_type")

    try:
        receiver = User.objects.get(id=receiver_id)
        
        message = ChatMessage(
            sender=sender, 
            receiver=receiver, 
            message=message_text
        )
        
        # Handle media file if present
        if media_file:
            message.media_file = media_file
            message.media_type = media_type
            message.media_content_type = media_file.content_type
        
        message.save()
        
        return Response(
            ChatMessageSerializer(message).data, status=status.HTTP_201_CREATED
        )
    except User.DoesNotExist:
        return Response({"error": "User not found"}, status=status.HTTP_400_BAD_REQUEST)


# Clears chat
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def clear_chat(request, receiver_id):
    sender = request.user  # Current user who clicked "Clear Chat"

    # Find all messages between sender and receiver
    messages = ChatMessage.objects.filter(
        (
            Q(sender=sender, receiver_id=receiver_id)
            | Q(sender_id=receiver_id, receiver=sender)
        )
    )

    if not messages.exists():
        return Response({"error": "No messages found"}, status=404)

    # Mark messages as deleted for the user who clicked the button
    for msg in messages:
        if msg.sender == sender:
            msg.user1_deleted = True  # Sender cleared chat
        else:
            msg.user2_deleted = True  # Receiver cleared chat
        msg.save()

    # Completely delete messages if both users have cleared chat
    messages.filter(user1_deleted=True, user2_deleted=True).delete()

    return Response({"message": "Chat cleared successfully"}, status=200)


# Group Chat Views


# Create a group
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_group(request):
    """Create a new group chat"""
    # Extract data from the request
    name = request.data.get("name")
    member_ids = request.data.get("members", [])

    # Add the requesting user to the list of members
    user = request.user
    if user.id not in member_ids:
        member_ids.append(user.id)

    # Check if the group name and members are valid
    if not name:
        return Response(
            {"error": "Group name is required"}, status=status.HTTP_400_BAD_REQUEST
        )

    if not member_ids:
        return Response(
            {"error": "At least one member is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Retrieve users based on the provided member IDs
    members = User.objects.filter(id__in=member_ids)

    if members.count() != len(member_ids):  # Check if all members are valid
        return Response(
            {"error": "Some members are invalid"}, status=status.HTTP_400_BAD_REQUEST
        )

    # Create the group and assign members
    group = GroupChat.objects.create(name=name)
    group.members.set(members)
    group.save()  # Save group after setting members

    # Serialize and return the group data
    serializer = GroupChatSerializer(group)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


# Show the groups
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_user_groups(request):
    """Get all groups the logged-in user is a member of"""
    # Adding .distinct() to avoid duplicate entries from ManyToManyField
    groups = GroupChat.objects.filter(members=request.user).distinct()
    serializer = GroupChatSerializer(groups, many=True)
    return Response(serializer.data)


# Send message in group
@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def send_group_message(request):
    """Send a message with optional media in a group chat"""
    sender = request.user
    group_id = request.data.get("group")
    message_text = request.data.get("message", "")
    media_file = request.FILES.get("media_file")
    media_type = request.data.get("media_type")

    try:
        group = GroupChat.objects.get(id=group_id, members=sender)
        
        message = GroupMessage(
            group=group, 
            sender=sender, 
            message=message_text
        )
        
        # Handle media file if present
        if media_file:
            message.media_file = media_file
            message.media_type = media_type
            message.media_content_type = media_file.content_type
        
        message.save()
        
        return Response(
            GroupMessageSerializer(message).data, status=status.HTTP_201_CREATED
        )
    except GroupChat.DoesNotExist:
        return Response(
            {"error": "Group not found or access denied"},
            status=status.HTTP_403_FORBIDDEN,
        )


# Get messages in group
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_group_messages(request, group_id):
    """Fetch all messages in a group chat"""
    try:
        group = GroupChat.objects.get(id=group_id, members=request.user)
        messages = GroupMessage.objects.filter(group=group).order_by("timestamp")
        serializer = GroupMessageSerializer(messages, many=True)
        return Response(serializer.data)
    except GroupChat.DoesNotExist:
        return Response(
            {"error": "Group not found or access denied"},
            status=status.HTTP_403_FORBIDDEN,
        )


# Add members to group
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_group_members(request):
    try:
        group_id = request.data.get("group_id")
        user_ids = request.data.get("users", [])  # Expecting a list of user IDs

        group = GroupChat.objects.get(id=group_id)

        # Fetch all users whose IDs are in the provided list
        users = User.objects.filter(id__in=user_ids)

        # Filter out users who are already members
        new_users = [user for user in users if user not in group.members.all()]

        if not new_users:
            return Response(
                {
                    "message": "No new members were added. All users are already in the group."
                },
                status=status.HTTP_200_OK,
            )

        # Add only the new users to the group
        group.members.add(*new_users)

        return Response(
            {"message": f"{len(new_users)} new members added successfully"},
            status=status.HTTP_200_OK,
        )
    except GroupChat.DoesNotExist:
        return Response({"error": "Group not found"}, status=status.HTTP_404_NOT_FOUND)


# Delete a group
@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_group(request, group_id):
    try:
        group = GroupChat.objects.get(id=group_id)

        # Ensure only an authorized user can delete (Optional: Check if the request.user is the group creator)
        if request.user not in group.members.all():
            return Response(
                {"error": "You are not a member of this group."},
                status=status.HTTP_403_FORBIDDEN,
            )

        group.delete()  # Deletes the group and all associated messages due to CASCADE

        return Response(
            {"message": "Group and all associated messages deleted successfully"},
            status=status.HTTP_200_OK,
        )
    except GroupChat.DoesNotExist:
        return Response({"error": "Group not found"}, status=status.HTTP_404_NOT_FOUND)


# Add these to your views.py


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def update_group(request, group_id):
    """Update group name"""
    try:
        group = GroupChat.objects.get(id=group_id, members=request.user)
        name = request.data.get("name")

        if not name:
            return Response(
                {"error": "Group name is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        group.name = name
        group.save()

        return Response(GroupChatSerializer(group).data, status=status.HTTP_200_OK)
    except GroupChat.DoesNotExist:
        return Response(
            {"error": "Group not found or access denied"},
            status=status.HTTP_404_NOT_FOUND,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def remove_group_member(request, group_id):
    """Remove a member from the group"""
    try:
        group = GroupChat.objects.get(id=group_id, members=request.user)
        username = request.data.get("username")

        if not username:
            return Response(
                {"error": "Username is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            member = User.objects.get(username=username)
            if member not in group.members.all():
                return Response(
                    {"error": "User is not a member of this group"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            group.members.remove(member)
            return Response(
                {"message": f"{username} has been removed from the group"},
                status=status.HTTP_200_OK,
            )
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )

    except GroupChat.DoesNotExist:
        return Response(
            {"error": "Group not found or access denied"},
            status=status.HTTP_404_NOT_FOUND,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def leave_group(request, group_id):
    """Leave a group"""
    try:
        group = GroupChat.objects.get(id=group_id, members=request.user)

        # Remove the user from the group
        group.members.remove(request.user)

        # If no members left, delete the group
        if group.members.count() == 0:
            group.delete()
            return Response(
                {"message": "You were the last member. Group has been deleted."},
                status=status.HTTP_200_OK,
            )

        return Response(
            {"message": "You have left the group successfully"},
            status=status.HTTP_200_OK,
        )
    except GroupChat.DoesNotExist:
        return Response(
            {"error": "Group not found or you are not a member"},
            status=status.HTTP_404_NOT_FOUND,
        )
