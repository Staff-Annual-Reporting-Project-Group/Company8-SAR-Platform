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

    DEFAULT_PIC = 'https://res.cloudinary.com/dop5fzjom/image/upload/v1775723467/images/profile_pictures/user_qift6z.png'
    ROBOT_PIC_ID = 'ai_robot-removebg-preview_yu6rgm'

    profilePic = models.ImageField(
        default=DEFAULT_PIC,
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

    @property
    def pic_url(self):
        """Return a usable image URL regardless of whether the stored value
        is already a full https:// URL (old scraper uploads) or a Cloudinary
        public_id (new uploads).  Templates should use profile_pic.pic_url."""
        name = str(self.profilePic)
        if not name:
            return ''
        if name.startswith('http'):
            return name
        try:
            return self.profilePic.url
        except Exception:
            return ''

    def __str__(self):
        return f"{self.user.username} Profile"