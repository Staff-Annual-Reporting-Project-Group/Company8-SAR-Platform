from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Participant(models.Model):
    user = models.ForeignKey(User,on_delete=models.SET_NULL,null=True,blank=True)
    name = models.CharField(max_length=200,blank=False,null=False)

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
    user = models.ForeignKey(User,on_delete=models.CASCADE,null=False)
    title = models.CharField(max_length=200,blank=False,null=False)
    description = models.TextField(null=False,blank=False)
    #category
    participants = models.ManyToManyField(Participant)
    category = models.ForeignKey(Category,on_delete=models.SET_NULL,default=1,null=True)
    committee= models.ForeignKey(Committee,on_delete=models.SET_NULL,null=True,blank=True)
    feature_image = models.ImageField(default='default_image.jpg',upload_to='report_images')
    date_of_report= models.DateField(blank=False,null=False,default=timezone.now().date())
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_of_report','-created','-updated']

    def __str__(self):
        return f"{self.user.username} created {self.title} "
    

