from django.urls import path
from .views import (
    get_messages,
    send_message,
    clear_chat,
    get_user_groups,
    add_group_members,
    get_group_messages,
    create_group,
    send_group_message,
    delete_group,
    update_group,
    remove_group_member,
    leave_group,
)

urlpatterns = [
    path("messages/<int:user_id>/", get_messages, name="get_messages"),
    path("send/", send_message, name="send_message"),
    path("clear_chat/<int:receiver_id>/", clear_chat, name="clear_chat"),
    path("groups/", get_user_groups, name="groups"),
    path("groups/add_members/", add_group_members, name="add-to-group"),
    path(
        "group-messages/<int:group_id>/", get_group_messages, name="get-group-message"
    ),
    path("group-message/send/", send_group_message, name="send-group-message"),
    path("groups/create/", create_group, name="create-group"),
    path("groups/delete_group/<int:group_id>/", delete_group, name="delete-group"),
    path("groups/<int:group_id>/update/", update_group, name="update_group"),
    path(
        "groups/<int:group_id>/remove-member/",
        remove_group_member,
        name="remove_group_member",
    ),
    path("groups/<int:group_id>/leave/", leave_group, name="leave_group"),
]
