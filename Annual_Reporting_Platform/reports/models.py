from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver


class StaffProfile(models.Model):
    """
    One-to-one extension of Django's built-in User.
    Handles approval state for new registrations.
    Admin approves by ticking `is_approved` in the Django admin,
    which also re-enables the User's `is_active` flag.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    is_approved = models.BooleanField(default=False)
    requested_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} — {'approved' if self.is_approved else 'pending'}"

    # Flip User.is_active whenever approval status changes
    def save(self, *args, **kwargs):
        self.user.is_active = self.is_approved
        self.user.save(update_fields=['is_active'])
        super().save(*args, **kwargs)


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    """Auto-create a StaffProfile whenever a new User is created."""
    if created:
        StaffProfile.objects.get_or_create(user=instance)


class Participant(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=200)
    regex = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Categories'


class Committee(models.Model):
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class Report(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()
    participants = models.ManyToManyField(Participant, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, default=1, null=True)
    committee = models.ForeignKey(Committee, on_delete=models.SET_NULL, null=True, blank=True)
    feature_image = models.ImageField(default='default_image.jpg', upload_to='report_images')
    date_of_report = models.DateField(default=timezone.now)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_of_report', '-created', '-updated']

    def __str__(self):
        return f"{self.user.username} — {self.title}"
