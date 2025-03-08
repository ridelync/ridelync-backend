from django.contrib.auth.models import AbstractUser
from django.db import models
from cloudinary.models import CloudinaryField
from django.core.exceptions import ValidationError


class UserProfile(AbstractUser):
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    dob = models.DateField(null=True, blank=True)
    gender = models.CharField(
        max_length=10,
        choices=[("male", "Male"), ("female", "Female"), ("other", "Other")],
        null=True,
        blank=True,
    )
    language = models.CharField(max_length=20, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    city = models.CharField(max_length=50, null=True, blank=True)
    pincode = models.CharField(max_length=12, null=True, blank=True)
    emergency_email = models.EmailField(
        default="ridelync00@gmail.com", null=True, blank=True
    )

    # Store images in Cloudinary
    profile_picture = CloudinaryField("profile_picture", null=True, blank=True)
    drivers_license = CloudinaryField("drivers_license", null=True, blank=True)
    identity_card = CloudinaryField("identity_card", null=True, blank=True)

    # Add fields for driver's rating
    total_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    rating_count = models.PositiveIntegerField(default=0)

    def update_rating(self, new_rating, old_rating=None):
        # Ensure the new rating is between 1 and 5
        if not (1 <= new_rating <= 5):
            raise ValidationError("Rating must be between 1 and 5.")

        total_rating = self.total_rating * self.rating_count

        # Checks if there exist an old rating for the booking
        if old_rating is not None:
            # If old_rating is provided, subtract the old rating first
            total_rating -= old_rating  # Remove the old rating
            self.rating_count -= 1

        # Add the new rating
        total_rating += new_rating
        self.rating_count += 1

        # The rating count stays the same because it's an update (not a new rating)
        # Calculate the new average rating
        new_total_rating = (
            (total_rating / self.rating_count) if self.rating_count > 0 else new_rating
        )

        # Clamp the result to the range [0, 5]
        clamped_rating = max(0, min(5, new_total_rating))

        # Update the user's total rating
        self.total_rating = clamped_rating
        self.save()  # Save the driver model to persist the new total_rating
