# exam/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import Question, Exam, ExamAttempt

# Customize UserAdmin to prevent students from being superusers or staff
class CustomUserAdmin(UserAdmin):
    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            obj.is_superuser = False
            obj.is_staff = False
        super().save_model(request, obj, form, change)

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
admin.site.register(Question)
admin.site.register(Exam)
admin.site.register(ExamAttempt)