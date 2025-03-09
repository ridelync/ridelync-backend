from django.db import connection
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.core.mail import EmailMessage
from django.template.loader import render_to_string


# 🚀 View all rides with user details
@api_view(["GET"])
@permission_classes([AllowAny])  # Anyone can access this API
def all_rides(request):
    # Get the authenticated user's email (if available)
    user_email = request.user.email if request.user.is_authenticated else None

    with connection.cursor() as cursor:
        # SQL Query with INNER JOIN and condition to exclude rides for the authenticated user
        query = """
            SELECT lm.mapping_id, lm.vehicle_number, lm.detection_date, lm.start_loc, lm.end_loc,
                   od.name, od.contact_no, od.email
            FROM LOCATION_MAPPING lm
            INNER JOIN OWNER_DETAILS od ON lm.vehicle_number = od.vehicle_number
            WHERE od.email != %s OR %s IS NULL
        """
        cursor.execute(query, [user_email, user_email])
        rows = cursor.fetchall()

    # Formatting data
    ride_data = []
    for row in rows:
        ride_data.append(
            {
                "mapping_id": row[0],
                "vehicle_number": row[1],
                "detection_date": row[2],
                "start_loc": row[3],
                "end_loc": row[4],
                "rider_name": row[5],  # User's full name
                "rider_contact": row[6],
                "rider_email": row[7],
            }
        )

    return Response(
        {"total": len(ride_data), "rides": ride_data}, status=status.HTTP_200_OK
    )

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def req_mail(request):
    try:
        # Extract data from the request
        sender_name = request.user.get_full_name()
        sender_email = request.user.email
        receiver_email = request.data.get("receiver_email")
        receiver_name = request.data.get("receiver_name")
        start_loc = request.data.get("start_loc")
        end_loc = request.data.get("end_loc")
        webapp_url = request.data.get("webapp_url")

        # Validate required fields
        if not all(
            [
                receiver_email,
                receiver_name,
                sender_name,
                start_loc,
                end_loc,
                webapp_url,
            ]
        ):
            return Response(
                {"status": "error", "message": "Missing required fields"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Render the email template with dynamic data
        email_html_message = render_to_string(
            "email_template.html",
            {
                "receiver_name": receiver_name,
                "sender_name": sender_name,
                "start_loc": start_loc,
                "end_loc": end_loc,
                "webapp_url": webapp_url,
            },
        )

        # Create and send the email
        email = EmailMessage(
            subject=f"{sender_name} Wants to Share a Ride with You!",
            body=email_html_message,
            from_email=sender_email,  # Sender's email
            to=[receiver_email],  # Recipient's email
        )
        email.content_subtype = "html"  # Set email content type to HTML
        email.send()

        return Response(
            {"status": "success", "message": "Email sent successfully"},
            status=status.HTTP_200_OK,
        )
    except Exception as e:
        return Response(
            {"status": "error", "message": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

