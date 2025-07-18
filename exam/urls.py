# exam/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('examiner/', views.examiner_dashboard, name='examiner_dashboard'),
    path('student/', views.student_dashboard, name='student_dashboard'),
    path('upload-questions/', views.upload_questions, name='upload_questions'),
    path('create-exam/', views.create_exam, name='create_exam'),
    path('exam/<int:exam_id>/', views.start_exam, name='start_exam'),
    path('exam/<int:exam_id>/submit/', views.submit_exam, name='submit_exam'),
    path('exam/<int:exam_id>/results/', views.exam_results, name='exam_results'),
    path('manage-subjects/', views.manage_subjects, name='manage_subjects'),
    path('add-subject/', views.add_subject, name='add_subject'),
    path('delete-subject/<int:subject_id>/', views.delete_subject, name='delete_subject'),
    path('bulk-upload-students/', views.bulk_upload_students, name='bulk_upload_students'),
    path('download-student-template/', views.download_student_template, name='download_student_template'),
]