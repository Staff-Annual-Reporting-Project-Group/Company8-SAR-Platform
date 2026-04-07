from django.db import models
from django.contrib.auth.models import User


class UserProfilePic(models.Model):
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile_pic',
        unique=True
    )

    profilePic = models.ImageField(
        default="profile_pictures/user.png",
        upload_to='profile_pictures'
    )

    phone = models.CharField(
        max_length=30,
        blank=True,
        null=True
    )

    gender = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES,
        blank=True,
        null=True
    )

    def __str__(self):
        return f"{self.user.username} Profile"