from rest_framework.serializers import ModelSerializer, SerializerMethodField
from .models import Available, Rating


class RideSerializer(ModelSerializer):
    class Meta:
        model = Available  # Connects to the Available model
        fields = "__all__"  # Automatically includes all fields in the model


class RatingSerializer(ModelSerializer):
    class Meta:
        model = Rating
        fields = ["rating", "comment"]
        extra_kwargs = {"comment": {"required": False}}  # Comment is optional


class RideDetailSerializer(ModelSerializer):
    rider_profile = SerializerMethodField()
    rider_name = SerializerMethodField()
    rider_rating = SerializerMethodField()

    class Meta:
        model = Available
        fields = [
            "id",
            "from_location",
            "to_location",
            "date",
            "time",
            "seats",
            "price",
            "vehicle_type",
            "license",
            "status",
            "user",
            "rider_profile",
            "rider_name",
            "rider_rating",
        ]

    def get_rider_profile(self, obj):
        if obj.user.profile_picture:
            return obj.user.profile_picture.url
        return None

    def get_rider_name(self, obj):
        return obj.user.username

    def get_rider_rating(self, obj):
        return obj.user.total_rating
