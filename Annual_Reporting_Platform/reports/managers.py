from django.db import models
class ReportManager(models.Manager):
    def search(self,keyword):
        return self.filter(title__icontains=keyword)