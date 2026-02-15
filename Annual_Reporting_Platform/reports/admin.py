from django.contrib import admin
from .models import Report,Participant,Category,Committee
# Register your models here.
admin.site.register(Report)
admin.site.register(Participant)
admin.site.register(Category)
admin.site.register(Committee)