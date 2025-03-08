from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, required=False, style={"input_type": "password"}
    )

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "phone_number",
            "password",
            "first_name",
            "last_name",
            "dob",
            "gender",
            "language",
            "address",
            "city",
            "pincode",
            "emergency_email",
            "profile_picture",
            "drivers_license",
            "identity_card",
            "total_rating",
            "rating_count",
        ]
        extra_kwargs = {
            "username": {"read_only": True},  # Cannot be changed during update
            "email": {"read_only": True},  # Cannot be changed during update
            "password": {"write_only": True},  # Hide password from responses
        }

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        user = User.objects.create(**validated_data)
        if password:
            user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        # Prevent username/email from being updated
        validated_data.pop("username", None)
        validated_data.pop("email", None)

        # If password is being updated, hash it
        password = validated_data.pop("password", None)
        if password:
            instance.set_password(password)

        # Update the rest of the fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance
