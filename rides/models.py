from django.db import models
from django.conf import settings  # Import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()


class Available(models.Model):
    STATUS_CHOICES = [
        ("OPEN", "Open"),
        ("FULL", "Full"),
        ("COMPLETED", "Completed"),
        ("CLOSED", "Closed"),
        ("ONGOING", "Ongoing"),
    ]

    from_location = models.CharField(max_length=100)
    to_location = models.CharField(max_length=100)
    date = models.DateField()
    time = models.TimeField()
    seats = models.PositiveSmallIntegerField()
    price = models.DecimalField(max_digits=7, decimal_places=2)
    vehicle_type = models.CharField(
        max_length=5, choices=[("Car", "Car"), ("Bike", "Bike")], default="Car"
    )
    license = models.CharField(max_length=100, blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="OPEN")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="rides"
    )

    def __str__(self):
        return (
            f"{self.from_location} to {self.to_location} on {self.date} at {self.time}"
        )


class Booking(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("ACCEPTED", "Accepted"),
        ("REJECTED", "Rejected"),
        ("CANCELLED_BY_PASSENGER", "Cancelled by Passenger"),
        ("CANCELLED_BY_DRIVER", "Cancelled by Driver"),
        ("IN_PROGRESS", "In Progress"),
        ("COMPLETED", "Completed"),
    ]

    booker = models.ForeignKey(
        User, on_delete=models.CASCADE
    )  # The one who booked the ride
    ride = models.ForeignKey(
        Available, on_delete=models.CASCADE, related_name="bookings"
    )
    pickup_note = models.TextField(blank=True, null=True)
    passenger_count = models.IntegerField(default=1)
    payment_method = models.CharField(
        max_length=50, choices=[("cash", "Cash"), ("online", "Online")]
    )
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default="PENDING")

    def __str__(self):
        return f"Booking {self.id} - {self.booker.username} ({self.status})"


class Rating(models.Model):
    RATING_CHOICES = [
        (1, "1 - Poor"),
        (2, "2 - Fair"),
        (3, "3 - Good"),
        (4, "4 - Very Good"),
        (5, "5 - Excellent"),
    ]

    booking = models.OneToOneField(
        Booking, on_delete=models.CASCADE, related_name="rating"
    )
    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES)
    comment = models.TextField(blank=True, null=True)
    rated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Rating {self.rating} for Booking {self.booking.id}"

    def save(self, *args, **kwargs):
        # Ensure the rating value is between 1 and 5
        if not (1 <= self.rating <= 5):
            raise ValidationError("Rating must be between 1 and 5.")

        # If this is an update (existing rating), get the previous rating
        previous_rating_value = None
        if self.pk:
            try:
                previous_rating = Rating.objects.get(pk=self.pk)
                previous_rating_value = previous_rating.rating
            except Rating.DoesNotExist:
                previous_rating_value = (
                    None  # Handle cases where the previous rating doesn't exist
                )

        super().save(*args, **kwargs)  # Save the new rating

        # Get the driver from the booking
        driver = self.booking.ride.user
        if driver:
            if previous_rating_value is not None:
                # Updating an existing rating, adjust the rating properly
                driver.update_rating(
                    new_rating=self.rating, old_rating=previous_rating_value
                )
            else:
                # New rating, increase rating count
                driver.update_rating(new_rating=self.rating, old_rating=None)
                driver.save()
