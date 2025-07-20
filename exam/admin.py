# exam/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import Question, Exam, ExamAttempt, Subject, Subscription
from django.http import HttpResponse
import csv
from django.urls import path, reverse
from django.utils.html import format_html

class CustomUserAdmin(UserAdmin):
    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            obj.is_superuser = False
            obj.is_staff = False
        super().save_model(request, obj, form, change)

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'created_by', 'created_at')
    search_fields = ('name', 'code')
    list_filter = ('created_by',)

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'subject', 'created_by', 'created_at')
    list_filter = ('subject', 'created_by')
    search_fields = ('text',)

@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'start_time', 'end_time', 'created_by', 'export_button')
    list_filter = ('subject', 'created_by')
    search_fields = ('title',)
    
    def export_button(self, obj):
        return format_html(
            '<a class="button" href="{}">Export Results</a>',
            reverse('admin:export_exam_results', args=[obj.id])
        )
    export_button.short_description = 'Export'
    export_button.allow_tags = True
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<path:object_id>/export/',
                 self.admin_site.admin_view(self.export_single_exam),
                 name='export_exam_results'),
        ]
        return custom_urls + urls
    
    def export_single_exam(self, request, object_id):
        exam = self.get_object(request, object_id)
        return export_exam_results(self, request, Exam.objects.filter(id=exam.id))

def export_exam_results(modeladmin, request, queryset):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="exam_results.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Exam Title', 'Subject', 'Student', 'Score', 
        'Total Questions', 'Passing Threshold', 'Passed',
        'Start Time', 'Completion Time'
    ])
    
    for exam in queryset:
        attempts = ExamAttempt.objects.filter(exam=exam)
        for attempt in attempts:
            writer.writerow([
                exam.title,
                exam.subject.name,
                attempt.user.username,
                attempt.score,
                exam.number_of_questions,
                exam.cutoff_score,
                'Yes' if attempt.score >= exam.cutoff_score else 'No',
                attempt.start_time.strftime("%Y-%m-%d %H:%M:%S"),
                attempt.completion_time.strftime("%Y-%m-%d %H:%M:%S") if attempt.completed else 'Not Completed'
            ])
    
    return response
export_exam_results.short_description = "Export selected exams' results to CSV"

@admin.register(ExamAttempt)
class ExamAttemptAdmin(admin.ModelAdmin):
    list_display = ('user', 'exam', 'score', 'completed', 'start_time')
    list_filter = ('completed', 'exam__subject')
    search_fields = ('user__username', 'exam__title')

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

# exam/admin.py
@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('status', 'start_date', 'end_date', 'days_remaining')
    readonly_fields = ('status', 'days_remaining')
    
    def days_remaining(self, obj):
        from django.utils import timezone
        if obj.end_date > timezone.now():
            return (obj.end_date - timezone.now()).days
        return 0
    days_remaining.short_description = 'Days Remaining'