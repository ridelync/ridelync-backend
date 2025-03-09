import random
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from .serializers import RideSerializer
from django.contrib.auth import get_user_model
from .models import Available, Booking, Rating
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.shortcuts import get_object_or_404
from django.core.mail import send_mail
from .serializers import RatingSerializer, RideDetailSerializer

User = get_user_model()


def get_image_url(image_field, request):
    """Helper function to get absolute image URLs."""
    return request.build_absolute_uri(image_field.url) if image_field else None


# Posting a ride
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_ride(request):
    data = request.data.copy()  # Copy request data to modify it
    data["user"] = request.user.id  # Assign the logged-in user ID

    serializer = RideSerializer(data=data)
    print(data)
    if serializer.is_valid():
        serializer.save()  # Saves the ride with the user
        return Response(
            {"message": "Ride offered successfully"},
            status=status.HTTP_201_CREATED,
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Searching for rides
@api_view(["GET"])
@permission_classes([AllowAny])  # 🚀 Anyone can access this API
def find_ride(request):
    # Extract query parameters
    from_location = request.GET.get("from_location")
    to_location = request.GET.get("to_location")
    date = request.GET.get("date")
    seats = request.GET.get("seats")

    # Fetch all rides and optimize query using select_related
    rides = Available.objects.select_related("user").filter(status="OPEN")

    # Apply filters if parameters are provided
    if from_location:
        rides = rides.filter(from_location__icontains=from_location)
    if to_location:
        rides = rides.filter(to_location__icontains=to_location)
    if date:
        rides = rides.filter(date=date)
    if seats:
        rides = rides.filter(seats__gte=int(seats))  # Ensure enough seats

    # Serialize rides
    serializer = RideSerializer(rides, many=True)
    ride_data = serializer.data

    # Add full name of the user manually
    for index, ride in enumerate(rides):
        ride_data[index]["rider_name"] = ride.user.get_full_name()
        ride_data[index]["rider_profile"] = get_image_url(
            ride.user.profile_picture, request
        )
        ride_data[index]["rider_rating"] = ride.user.total_rating

    return Response(
        {"total": rides.count(), "rides": ride_data},
        status=status.HTTP_200_OK,
    )


# View all rides
@api_view(["GET"])
@permission_classes([AllowAny])  # 🚀 Anyone can access this API
def all_rides(request):
    # Get all available rides with user information
    rides = Available.objects.select_related("user").filter(status="OPEN")

    # Serialize rides
    serializer = RideSerializer(rides, many=True)
    ride_data = serializer.data

    # Add full name of the user manually
    for index, ride in enumerate(rides):
        ride_data[index]["rider_name"] = ride.user.get_full_name()
        ride_data[index]["rider_profile"] = get_image_url(
            ride.user.profile_picture, request
        )
        ride_data[index]["rider_rating"] = ride.user.total_rating

    return Response(
        {"total": rides.count(), "rides": ride_data},
        status=status.HTTP_200_OK,
    )


# View my posted rides
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_rides(request):
    try:
        rides = Available.objects.filter(user=request.user).select_related("user")
        serialized_rides = RideSerializer(rides, many=True).data

        # Fetch count of bookings where status is "ACCEPTED" and get booker user IDs
        for ride, serialized_ride in zip(rides, serialized_rides):
            accepted_bookings = Booking.objects.filter(ride=ride, status="ACCEPTED")
            accepted_booking_count = accepted_bookings.count()

            # Get the list of booker user IDs
            booker_user_ids = accepted_bookings.values_list("booker_id", flat=True)
            booker_user_names = accepted_bookings.values_list(
                "booker__username", flat=True
            )
            print(booker_user_names)

            # Add data to response
            serialized_ride["total_bookings"] = accepted_booking_count
            serialized_ride["booker_user_ids"] = list(
                booker_user_ids
            )  # Convert to list
            serialized_ride["booker_user_names"] = list(
                booker_user_names
            )  # Convert to list

        return Response(
            {"total": rides.count(), "rides": serialized_rides},
            status=status.HTTP_200_OK,
        )
    except Exception as e:
        return Response(
            {"error": f"Failed to fetch rides: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# Delete my posted rides
@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_ride(request, ride_id):
    ride = get_object_or_404(Available, id=ride_id)

    # Ensure only the ride owner can delete it
    if ride.user != request.user:
        return Response(
            {"error": "You are not authorized to delete this ride"},
            status=status.HTTP_403_FORBIDDEN,
        )

    ride.delete()
    return Response({"message": "Ride deleted successfully"}, status=status.HTTP_200_OK)


# Book a ride
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def book_ride(request):
    user = request.user
    ride_id = request.data.get("ride_id")
    pickup_note = request.data.get("pickup_note", "").strip()  # Strip extra spaces
    passenger_count = int(request.data.get("passenger_count", 1))
    payment_method = request.data.get("payment_method", "cash")

    try:
        ride = Available.objects.get(id=ride_id)
        if ride.seats < passenger_count:
            return Response({"error": "Not enough seats available"}, status=400)

        # Check if the user already has a booking for this ride
        existing_booking = Booking.objects.filter(booker=user, ride=ride).first()

        if existing_booking:
            # Update existing booking
            new_passenger_count = existing_booking.passenger_count + passenger_count
            if new_passenger_count > ride.seats:
                return Response(
                    {"error": "Not enough seats available after update"}, status=400
                )

            existing_booking.passenger_count = new_passenger_count
            existing_booking.pickup_note = (
                f"{existing_booking.pickup_note}\n{pickup_note}".strip()
                if pickup_note
                else existing_booking.pickup_note
            )  # Append new pickup note
            existing_booking.payment_method = (
                payment_method  # Update payment method if needed
            )
            existing_booking.save()

            return Response(
                {
                    "message": "Booking updated successfully",
                    "booking_id": existing_booking.id,
                    "passenger_count": existing_booking.passenger_count,
                    "pickup_note": existing_booking.pickup_note,
                    "status": existing_booking.status,
                },
                status=200,
            )
        else:
            # Create a new booking if the user doesn't have one
            booking = Booking.objects.create(
                booker=user,
                ride=ride,
                pickup_note=pickup_note,
                passenger_count=passenger_count,
                payment_method=payment_method,
                status="PENDING",
            )

            return Response(
                {
                    "message": "Ride requested successfully",
                    "booking_id": booking.id,
                    "passenger_count": booking.passenger_count,
                    "pickup_note": booking.pickup_note,
                    "status": booking.status,
                },
                status=201,
            )

    except Available.DoesNotExist:
        return Response({"error": "Ride not found"}, status=404)


# View my booked rides
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def booked_rides(request):
    user = request.user
    bookings = Booking.objects.filter(booker_id=user).select_related(
        "ride", "ride__user"
    )
    response_data = [
        {
            "id": booking.id,
            "pickup_note": booking.pickup_note,
            "passenger_count": booking.passenger_count,
            "payment_method": booking.payment_method,
            "status": booking.status,
            "ride": {
                "start_location": booking.ride.from_location,
                "end_location": booking.ride.to_location,
                "ride_owner": booking.ride.user.get_full_name(),
            },
        }
        for booking in bookings
    ]

    return Response(response_data, status=200)


# Accept the ride request
@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def accept_ride(request, book_id):
    try:
        booking = Booking.objects.get(id=book_id)

        if booking.ride.user != request.user:
            return Response({"error": "Unauthorized action"}, status=403)

        booking.status = "ACCEPTED"
        booking.save()

        # Reduce available seats in the ride
        booking.ride.seats -= booking.passenger_count
        if booking.ride.seats == 0:
            booking.ride.status = "FULL"
        booking.ride.save()

        return Response({"message": "Ride request accepted"}, status=200)
    except Booking.DoesNotExist:
        return Response({"error": "Booking not found"}, status=404)


# Reject the ride request
@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def reject_ride(request, book_id):
    try:
        booking = Booking.objects.get(id=book_id)

        if booking.ride.user != request.user:
            return Response({"error": "Unauthorized action"}, status=403)

        booking.status = "REJECTED"
        booking.save()
        return Response({"message": "Ride request accepted"}, status=200)
    except Booking.DoesNotExist:
        return Response({"error": "Booking not found"}, status=404)


# View all ride requests for your ride
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def ride_requests(request, ride_id):
    ride_requests = Booking.objects.filter(ride_id=ride_id).select_related("booker")
    response_data = [
        {
            "id": req.id,
            "booker_id": req.booker_id,
            "booker_name": req.booker.get_full_name(),
            "booker_username": req.booker.username,
            "pickup_note": req.pickup_note,
            "passenger_count": req.passenger_count,
            "payment_method": req.payment_method,
            "status": req.status,
        }
        for req in ride_requests
    ]

    return Response(response_data, status=200)


# Delete a ride request
@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_request(request, book_id):
    ride_request = Booking.objects.filter(id=book_id).select_related("ride").first()

    # Ensure only the ride owner can delete it
    if ride_request.booker_id != request.user.id:
        return Response(
            {"error": "You are not authorized to delete this ride"},
            status=status.HTTP_403_FORBIDDEN,
        )

    if ride_request.status == "ACCEPTED":
        ride_request.ride.seats += ride_request.passenger_count
        ride_request.ride.save()

    ride_request.delete()
    return Response({"message": "Ride deleted successfully"}, status=status.HTTP_200_OK)


# Starting a ride
@api_view(["PUT"])
@permission_classes([IsAuthenticated])  # Only authenticated users can start a journey
def start_journey(request, ride_id):
    """
    Start a journey by changing the ride's status to ONGOING
    and updating all related ride requests to IN_PROGRESS.
    """

    # Fetch the ride or return 404 if not found
    ride = get_object_or_404(Available, id=ride_id, user=request.user)

    # Ensure the ride is already "ONGOING" before starting
    if ride.status == "ONGOING":
        return Response(
            {"error": "Ride is already in progress."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Update ride status to "ONGOING"
    ride.status = "ONGOING"
    ride.save()

    # Update all related ride requests to "IN_PROGRESS"
    Booking.objects.filter(ride=ride).update(status="IN_PROGRESS")

    return Response(
        {"message": "Journey started successfully!"}, status=status.HTTP_200_OK
    )


# Update the ride status
@api_view(["PUT"])
@permission_classes([IsAuthenticated])  # Only authenticated users can start a journey
def update_ride_status(request, ride_id):
    try:
        ride = Available.objects.get(id=ride_id)
        new_status = request.data.get("status")
        ride.status = new_status
        ride.save()
        return Response({"message": "Ride status updated successfully"}, status=200)
    except Available.DoesNotExist:
        return Response({"error": "Ride not found"}, status=404)


# Ending a ride
@api_view(["PUT"])
@permission_classes([IsAuthenticated])  # Only authenticated users can start a journey
def end_journey(request, ride_id):
    """
    Start a journey by changing the ride's status to ONGOING
    and updating all related ride requests to IN_PROGRESS.
    """
    # Fetch the ride or return 404 if not found
    ride = get_object_or_404(Available, id=ride_id, user=request.user)

    # Ensure the ride is already "ONGOING" before ending
    if ride.status != "ONGOING":
        return Response(
            {"error": "Ride has not started yet."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Update ride status to "COMPLETED"
    ride.status = "COMPLETED"
    ride.save()

    # Update all related ride requests to "COMPLETED"
    Booking.objects.filter(ride=ride).update(status="COMPLETED")

    return Response(
        {"message": "Journey started successfully!"}, status=status.HTTP_200_OK
    )


# OTP for starting ride
otp_storage = {}  # Temporary storage for OTPs


# Send OTP to bookers
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def send_otp_to_booker(request):
    try:
        # Extract the booker ID from the request
        booker_id = request.data.get("booker_id")
        if not booker_id:
            return Response(
                {"error": "No booker ID provided"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Fetch user email based on booker ID
        booker = get_object_or_404(User, id=booker_id)

        # Generate and send OTP
        otp = random.randint(100000, 999999)  # Generate 6-digit OTP
        otp_storage[booker.email] = otp  # Store OTP temporarily

        # Send OTP via email
        send_mail(
            "Ride Confirmation OTP",
            f"Hello {booker.username},\n\nYour OTP for the ride is: {otp}\n\nThank you for using RideLync!",
            "ridelync00@gmail.com",
            [booker.email],
            fail_silently=False,
        )

        return Response(
            {"success": True, "message": "OTP sent successfully!"},
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        return Response(
            {"error": f"Failed to send OTP: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# Verify the OTP given by the bookers
@api_view(["POST"])
@permission_classes([AllowAny])
def verify_otp(request):
    print("debugging.....")
    booker_id = request.data.get("booker_id")
    otp_entered = request.data.get("otp")

    if not booker_id or not otp_entered:
        return Response(
            {"success": False, "message": "Missing booker_id or OTP"}, status=400
        )

    # Fetch user based on booker_id
    user = get_object_or_404(User, id=booker_id)
    email = user.email  # Assuming each booker has a registered email

    # Check if OTP exists and matches
    if email in otp_storage and otp_storage[email] == int(otp_entered):
        del otp_storage[email]  # Remove OTP after successful verification
        return Response({"success": True, "message": "OTP Verified Successfully!"})

    return Response({"success": False, "message": "Invalid OTP"}, status=400)


# Send emergency email
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def send_emergency_email(request):
    data = request.data.copy()  # Copy request data to modify it
    data["user"] = request.user.id  # Assign the logged-in user ID

    booking = data.get("booking")
    message = data.get("message")
    location = data.get("location", "Location not available")
    print(booking)
    if not booking or not message:
        return Response(
            {"error": "Ride ID and message are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    driver = booking["ride"]["ride_owner"]

    # Get authenticated user's email
    user_email = request.user.email

    rider = request.user.get_full_name()

    receiver = request.user.emergency_email

    # Construct email content
    email_subject = f"🚨 Emergency Alert for {driver}'s Ride"
    email_body = f"""
    Emergency Alert!

    Passenger: {rider}

    Message: {message}

    Location: {location}

    Alert sent by: {user_email}

    Please take immediate action.
    """

    # Send email
    send_mail(
        subject=email_subject,
        message=email_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[receiver],  # Change to the correct recipient
        fail_silently=False,
    )

    return Response(
        {"message": "Emergency alert sent successfully"},
        status=status.HTTP_200_OK,
    )


# Rating a ride
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def rate_ride(request, book_id):
    # Retrieve the booking associated with the user
    booking = get_object_or_404(Booking, id=book_id, booker=request.user)

    # Check if the booking is completed
    if booking.status != "COMPLETED":
        return Response(
            {"detail": "You can only rate completed rides."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Check if the ride has already been rated
    if hasattr(booking, "rating"):
        # If the user has already rated, update the existing rating
        rating = booking.rating
        serializer = RatingSerializer(rating, data=request.data)

        if serializer.is_valid():
            serializer.save()  # Save the updated rating
            return Response(
                {"detail": "Your rating has been updated!"},
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    else:
        # If the user hasn't rated yet, create a new rating
        serializer = RatingSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(booking=booking)  # Save new rating
            return Response(
                {"detail": "Thank you for rating your ride!"},
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Show ride comments
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def ride_comments(request, ride_id):
    ride = get_object_or_404(Available, id=ride_id, user=request.user)

    ratings = Rating.objects.filter(
        booking__ride=ride
    )  # Selects all rating of the corresponding ride
    print(ratings)
    print(ratings[0].booking.booker)

    response_data = [
        {
            "id": rate.id,
            "rater_id": rate.booking.booker.id,
            "rater": rate.booking.booker.get_full_name(),
            "rater_username": rate.booking.booker.username,
            "stars": rate.rating,
            "comment": rate.comment,
            "time": rate.rated_at,
            "profile": get_image_url(rate.booking.booker.profile_picture, request),
        }
        for rate in ratings
    ]

    return Response(response_data, status=200)

@api_view(["GET"])
@permission_classes([AllowAny])
def ride_details(request, ride_id):
    try:
        ride = Available.objects.get(id=ride_id)
        serializer = RideDetailSerializer(ride)
        return Response(serializer.data)
    except Available.DoesNotExist:
        return Response(
            {"detail": "Ride not found"}, 
            status=status.HTTP_404_NOT_FOUND
        )