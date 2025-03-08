from rest_framework.serializers import ModelSerializer
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
