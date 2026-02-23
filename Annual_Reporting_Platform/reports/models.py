from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver


class StaffProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    is_approved = models.BooleanField(default=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    bio = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} — {'approved' if self.is_approved else 'pending'}"

    def save(self, *args, **kwargs):
        # self.user.is_active = self.is_approved
        # self.user.save(update_fields=['is_active'])
        super().save(*args, **kwargs)


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        StaffProfile.objects.get_or_create(user=instance)


class Participant(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class Category(models.Model):
    name  = models.CharField(max_length=200)
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
    committees = models.ManyToManyField(Committee, blank=True)   # ← M2M (was FK)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, default=1, null=True)
    feature_image = models.ImageField(null=True, blank=True, upload_to='report_images')
    date_of_report = models.DateField(default=timezone.now)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_of_report', '-created', '-updated']

    def __str__(self):
        return f"{self.user.username} — {self.title}"
