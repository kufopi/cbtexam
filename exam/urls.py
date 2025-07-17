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
]