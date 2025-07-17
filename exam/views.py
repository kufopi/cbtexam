# exam/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.utils import timezone
from .models import Question, Exam, ExamAttempt
import csv
from django.contrib import messages
import json

@login_required
def dashboard(request):
    if request.user.is_superuser:
        return redirect('examiner_dashboard')
    return redirect('student_dashboard')

@login_required
def examiner_dashboard(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Access denied.")
    exams = Exam.objects.filter(created_by=request.user)
    return render(request, 'examiner_dashboard.html', {'exams': exams})

@login_required
def student_dashboard(request):
    if request.user.is_superuser:
        return redirect('examiner_dashboard')
    current_time = timezone.now()
    exams = Exam.objects.filter(
        start_time__lte=current_time,
        end_time__gte=current_time
    )
    attempts = ExamAttempt.objects.filter(user=request.user)
    completed_exams = {attempt.exam.id for attempt in attempts.filter(completed=True)}
    return render(request, 'student_dashboard.html', {
        'exams': exams,
        'completed_exams': completed_exams
    })

@login_required
def upload_questions(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Access denied.")
    if request.method == 'POST':
        csv_file = request.FILES.get('csv_file')
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Please upload a CSV file.')
            return redirect('upload_questions')
        
        try:
            decoded_file = csv_file.read().decode('utf-8').splitlines()
            csv_reader = csv.DictReader(decoded_file)
            for row in csv_reader:
                Question.objects.create(
                    text=row['question'],
                    option_a=row['option_a'],
                    option_b=row['option_b'],
                    option_c=row['option_c'],
                    option_d=row['option_d'],
                    correct_answer=row['correct_answer'].upper(),
                    created_by=request.user
                )
            messages.success(request, 'Questions uploaded successfully.')
        except Exception as e:
            messages.error(request, f'Error uploading questions: {str(e)}')
        return redirect('examiner_dashboard')
    
    return render(request, 'upload_questions.html')

@login_required
def create_exam(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Access denied.")
    if request.method == 'POST':
        title = request.POST['title']
        number_of_questions = int(request.POST['number_of_questions'])
        duration_minutes = int(request.POST['duration_minutes'])
        start_time = request.POST['start_time']
        end_time = request.POST['end_time']
        cutoff_score = int(request.POST['cutoff_score'])
        
        Exam.objects.create(
            title=title,
            number_of_questions=number_of_questions,
            duration_minutes=duration_minutes,
            start_time=start_time,
            end_time=end_time,
            cutoff_score=cutoff_score,
            created_by=request.user
        )
        messages.success(request, 'Exam created successfully.')
        return redirect('examiner_dashboard')
    
    return render(request, 'create_exam.html')

@login_required
def start_exam(request, exam_id):
    exam = Exam.objects.get(id=exam_id)
    current_time = timezone.now()
    
    # Check if exam is available
    if not (exam.start_time <= current_time <= exam.end_time):
        return HttpResponseForbidden("This exam is not available at this time.")
    
    # Check if user has already completed this exam
    if ExamAttempt.objects.filter(user=request.user, exam=exam, completed=True).exists():
        return redirect('exam_results', exam_id=exam_id)
    
    # Create new attempt if needed
    attempt, created = ExamAttempt.objects.get_or_create(
        user=request.user,
        exam=exam,
        defaults={'answers': {}}
    )
    
    if attempt.completed:
        return redirect('exam_results', exam_id=exam_id)
    
    questions = exam.get_random_questions()
    return render(request, 'student_exam.html', {
        'exam': exam,
        'questions': questions,
        'attempt': attempt
    })

@login_required
def submit_exam(request, exam_id):
    if request.method == 'POST':
        exam = Exam.objects.get(id=exam_id)
        attempt = ExamAttempt.objects.get(user=request.user, exam=exam)
        
        if not attempt.completed:
            answers = json.loads(request.POST.get('answers', '{}'))
            attempt.answers = answers
            attempt.completed = True
            score = attempt.calculate_score()
            attempt;

        return redirect('exam_results', exam_id=exam_id)
    
    return redirect('start_exam', exam_id=exam_id)

@login_required
def exam_results(request, exam_id):
    exam = Exam.objects.get(id=exam_id)
    attempt = ExamAttempt.objects.get(user=request.user, exam=exam)
    return render(request, 'exam_results.html', {
        'exam': exam,
        'attempt': attempt
    })