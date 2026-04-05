from django.db import models
from django.contrib.auth.models import User
# Create your models here.

class UserProfilePic(models.Model):
    user = models.OneToOneField(User,null=False,blank=False ,on_delete=models.CASCADE,unique=True,related_name='profile_pic')
    profilePic = models.ImageField(default="profile_pictures/user.png",upload_to='profile_pictures')

    def __str__(self):
        return self.user.username + " Profile Picture"