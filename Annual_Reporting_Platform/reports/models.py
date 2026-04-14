from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from .managers import ReportQuerySet

class Participant(models.Model):
    user = models.ForeignKey(User,on_delete=models.SET_NULL,null=True,blank=True)
    name = models.CharField(max_length=500,blank=False,null=False)

    def __str__(self):
        return self.name

class Category(models.Model):
    name = models.CharField(max_length=200,blank=False,null= False)
    regex = models.TextField(blank=True,null=True)

    def __str__(self):
        return self.name

class Committee(models.Model):
    name = models.CharField(max_length=200,blank=False,null=False)
    def __str__(self):
        return self.name

# Create your models here.
class Report(models.Model):
    DEFAULT_IMAGE = 'https://res.cloudinary.com/dop5fzjom/image/upload/v1775723804/images/report_images/uwi_zocrhc.jpg'

    #Report States
    user = models.ForeignKey(User,on_delete=models.CASCADE,null=False,related_name='reports')
    title = models.CharField(max_length=200,blank=False,null=False, db_index=True)
    description = models.TextField(null=False,blank=False)
    #category
    participants = models.ManyToManyField(Participant,blank=True)
    category = models.ForeignKey(Category,on_delete=models.SET_NULL,default=1,null=True)
    committees= models.ManyToManyField(Committee,blank=True)
    feature_image = models.ImageField(default=DEFAULT_IMAGE, upload_to='report_images')
    date_of_report= models.DateField(blank=False,null=False,default=timezone.now)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    isActive = models.BooleanField(auto_created=True,default=True)

    objects = ReportQuerySet.as_manager()#Custom manager

    @property
    def feature_img_url(self):
        """Return a usable URL regardless of whether feature_image stores a
        full https:// URL or a Cloudinary public_id."""
        name = str(self.feature_image)
        if not name:
            return self.DEFAULT_IMAGE
        if name.startswith('http'):
            return name
        try:
            return self.feature_image.url
        except Exception:
            return self.DEFAULT_IMAGE

    class Meta:
        ordering = ['-date_of_report','-created','-updated']

    def __str__(self):
        return f"{self.user.username} created {self.title} "
    

