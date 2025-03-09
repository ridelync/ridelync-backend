from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from django.contrib.auth import get_user_model, authenticate
from django.db.models import Q
from django.shortcuts import get_object_or_404
from .serializers import UserSerializer
import cloudinary
import cloudinary.uploader
import cloudinary.exceptions
from rides.models import Rating

User = get_user_model()


# Search users on search bar
@api_view(["GET"])
@permission_classes([AllowAny])
def search_users_view(request):
    """
    Search for users by username, first name, or last name.
    Returns a maximum of 10 active users, excluding the requesting user.
    """
    query = request.GET.get("query", "").strip()  # Get and clean the query
    print(request.user.is_authenticated)
    # print(request.user.user_id)

    if not query:
        return Response([], status=status.HTTP_200_OK)  # Return empty list if no query

    users = User.objects.filter(
        (
            Q(username__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
        )
        & Q(is_active=True)  # Ensure only active users
        & ~Q(id=request.user.id)  # Exclude the requesting user
    )[
        :10
    ]  # Limit to 10 results

    user_list = [
        {
            "id": user.id,
            "username": user.username,
            "full_name": user.get_full_name(),
            "profile_picture": (
                request.build_absolute_uri(user.profile_picture.url)
                if user.profile_picture
                else None
            ),
        }
        for user in users
    ]

    return Response(user_list, status=status.HTTP_200_OK)


# View profile of any user
@api_view(["GET"])
@permission_classes([AllowAny])
def public_profile_view(request, user_id):
    """
    Retrieve public profile information of a user.
    """
    user = get_object_or_404(User, id=user_id, is_active=True)

    # Prepare public profile data
    public_data = {
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "profile_picture": (
            request.build_absolute_uri(user.profile_picture.url)
            if user.profile_picture
            else None
        ),
        "city": user.city,
        "language": user.language,
        "email": user.email,
        "phone_number": user.phone_number,
        "dob": user.dob,
        "gender": user.gender,
        "pincode": user.pincode,
        "address": user.address,
        "total_rating": user.total_rating,
        "rating_count": user.rating_count,
        # Add any other public fields here
    }

    return Response(public_data, status=status.HTTP_200_OK)


# Checks if the credentials are already used
@api_view(["GET"])
@permission_classes([AllowAny])
def check_availability(request):
    name = request.GET.get("name")
    value = request.GET.get("value")

    if name in ["username", "email", "phone_number"] and value:
        exists = User.objects.filter(**{name: value}).exists()
        return Response({"is_available": not exists})

    return Response({"error": "Invalid request"}, status=400)


# Logging in the user with token & details
@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    username = request.data.get("username")
    password = request.data.get("password")
    user = authenticate(username=username, password=password)

    if user:
        # 🔹 Delete old token and create a new one
        Token.objects.filter(user=user).delete()  # Remove existing token
        token = Token.objects.create(user=user)  # Create a fresh token

        return Response(
            {
                "message": "Login successful",
                "token": token.key,
                "user_id": user.id,
                "fullname": user.get_full_name(),
                "username": user.username,
            },
            status=200,
        )

    return Response({"error": "Invalid credentials"}, status=400)


# Registration view
@api_view(["POST"])
@permission_classes([AllowAny])
def user_registration(request):
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(
            {"message": "User registered successfully"}, status=status.HTTP_201_CREATED
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def get_image_url(image_field, request):
    """Helper function to get absolute image URLs."""
    return request.build_absolute_uri(image_field.url) if image_field else None


# View which handles view-my-profile, update-my-profile, delete-my-profile
@api_view(["GET", "PUT", "DELETE"])
@permission_classes([IsAuthenticated])
def profile_view(request):
    user = request.user  # Authenticated user

    if request.method == "GET":
        # Retrieve user profile data
        user_data = UserSerializer(user).data
        user_data["profile_picture"] = get_image_url(user.profile_picture, request)
        user_data["drivers_license"] = get_image_url(user.drivers_license, request)
        user_data["identity_card"] = get_image_url(user.identity_card, request)
        print(user_data)
        return Response(user_data, status=status.HTTP_200_OK)

    elif request.method == "PUT":
        data = request.data.copy()
        file_fields = ["profile_picture", "drivers_license", "identity_card"]

        # Remove empty values from data
        data = {key: value for key, value in data.items() if value}

        for field in file_fields:
            if field in request.FILES:
                # Delete old file from Cloudinary
                old_file = getattr(user, field)
                if old_file:
                    try:
                        cloudinary.uploader.destroy(old_file.public_id)
                    except:
                        pass  # Ignore if file is not found

                # Upload new file to Cloudinary
                try:
                    upload_result = cloudinary.uploader.upload(request.FILES[field])
                    data[field] = upload_result["public_id"]
                except Exception as e:
                    return Response(
                        {"error": f"Failed to upload {field}: {str(e)}"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

        # Update user profile
        serializer = UserSerializer(user, data=data, partial=True)
        if serializer.is_valid():
            updated_user = serializer.save()
            return Response(
                UserSerializer(updated_user).data, status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == "DELETE":
        user.delete()
        return Response(
            {"message": "Profile deleted successfully"},
            status=status.HTTP_204_NO_CONTENT,
        )


# OTP for reset password
from django.core.mail import send_mail
from django.contrib.auth.hashers import make_password
import random

# Temporary storage for OTPs (use a database for production)
otp_storage = {}


# 📌 1. Send OTP to Email
@api_view(["POST"])
@permission_classes([AllowAny])
def send_otp(request):
    email = request.data.get("email")
    user = get_object_or_404(User, email=email)

    otp = random.randint(100000, 999999)  # Generate 6-digit OTP
    otp_storage[email] = otp  # Store OTP temporarily

    # Send OTP via email
    send_mail(
        "Password Reset OTP",
        f"Your OTP is {otp}",
        "ridelync00@gmail.com",
        [email],
        fail_silently=False,
    )

    return Response({"message": "OTP sent successfully!"})


# 📌 2. Verify OTP
@api_view(["POST"])
@permission_classes([AllowAny])
def verify_otp(request):
    email = request.data.get("email")
    otp = int(request.data.get("otp"))

    if email in otp_storage and otp_storage[email] == otp:
        return Response({"message": "OTP Verified!"})

    return Response({"error": "Invalid OTP"}, status=400)


# 📌 3. Reset Password
@api_view(["POST"])
@permission_classes([AllowAny])
def reset_password(request):
    email = request.data.get("email")
    new_password = request.data.get("new_password")

    user = get_object_or_404(User, email=email)
    user.password = make_password(new_password)
    user.save()

    # Remove OTP after successful reset
    otp_storage.pop(email, None)

    return Response({"message": "Password reset successful!"})


# ✅ Get list of all users (except the logged-in user)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_list(request):
    users = User.objects.exclude(id=request.user.id)
    serializer = UserSerializer(users, many=True)
    return Response(serializer.data)

# Show user reviews
@api_view(['GET'])
@permission_classes([AllowAny])
def get_user_reviews(request, user_id):
    try:
        # Get the user
        user = User.objects.get(id=user_id)
        
        # Find all ratings for bookings where this user was the driver
        driver_ratings = Rating.objects.filter(booking__ride__user=user)
        
        # Prepare the response
        reviews = []
        
        for rating in driver_ratings:
            booking = rating.booking
            reviewer = booking.booker
            ride = booking.ride
            
            review_data = {
                'id': rating.id,
                'rating': rating.rating,
                'comment': rating.comment,
                'rated_at': rating.rated_at,
                'reviewer': {
                    'id': reviewer.id,
                    'username': reviewer.username,
                    'first_name': reviewer.first_name,
                    'last_name': reviewer.last_name,
                    'profile_picture': reviewer.profile_picture.url if hasattr(reviewer, 'profile_picture') and reviewer.profile_picture else None,
                },
                'ride_details': {
                    'from': ride.from_location,
                    'to': ride.to_location,
                    'date': ride.date,
                }
            }
            
            reviews.append(review_data)
        
        return Response({
            'count': len(reviews),
            'reviews': reviews
        })
        
    except User.DoesNotExist:
        return Response(
            {'error': 'User not found.'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )