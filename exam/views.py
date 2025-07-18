# exam/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.utils import timezone
from .models import Question, Exam, ExamAttempt, Subject
import csv
from django.contrib import messages
import json
from django.db.models import Case, When, F, IntegerField, Sum
from django.db.models import Avg

@login_required
def dashboard(request):
    if request.user.is_superuser:
        return redirect('examiner_dashboard')
    return redirect('student_dashboard')

# views.py - update examiner_dashboard view
@login_required
def examiner_dashboard(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Access denied.")
    
    # Get all exams created by the current user
    exams = Exam.objects.filter(created_by=request.user)
    
    # Calculate statistics
    total_questions = Question.objects.filter(created_by=request.user).count()
    total_exams = exams.count()
    
    # Calculate total exam attempts across all exams
    total_attempts = ExamAttempt.objects.filter(exam__created_by=request.user).count()
    
    # Calculate average pass rate
    passed_attempts = ExamAttempt.objects.filter(
        exam__created_by=request.user,
        completed=True
    ).annotate(
        passed=Case(
            When(score__gte=F('exam__cutoff_score'), then=1),
            default=0,
            output_field=IntegerField()
        )
    ).aggregate(passed=Sum('passed'))['passed'] or 0
    
    average_pass_rate = round((passed_attempts / total_attempts * 100), 2) if total_attempts > 0 else 0
    
    # Calculate exam statuses and additional metrics
    current_time = timezone.now()
    for exam in exams:
        # Determine exam status
        if exam.start_time <= current_time <= exam.end_time:
            exam.status = "active"
            exam.status_class = "status-active"
        elif current_time < exam.start_time:
            exam.status = "upcoming"
            exam.status_class = "status-upcoming"
        else:
            exam.status = "completed"
            exam.status_class = "status-completed"
        
        # Calculate completion rate for active exams
        exam_attempts = ExamAttempt.objects.filter(exam=exam)
        total_attempts_for_exam = exam_attempts.count()
        completed_attempts = exam_attempts.filter(completed=True).count()
        
        exam.completion_rate = round((completed_attempts / total_attempts_for_exam * 100), 2) if total_attempts_for_exam > 0 else 0
        
        # Calculate average score for completed exams
        if exam.status == "completed" and completed_attempts > 0:
            avg_score = exam_attempts.filter(completed=True).aggregate(avg_score=Avg('score'))['avg_score']
            exam.average_score = round(avg_score, 1) if avg_score else 0
            exam.average_score_percentage = round((exam.average_score / exam.number_of_questions) * 100)
        else:
            exam.average_score = 0
            exam.average_score_percentage = 0

    return render(request, 'examiner_dashboard.html', {
        'exams': exams,
        'total_questions': total_questions,
        'total_exams': total_exams,
        'total_attempts': total_attempts,
        'average_pass_rate': average_pass_rate
    })

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
    
    # Get all subjects for the dropdown
    subjects = Subject.objects.all()
    
    if request.method == 'POST':
        subject_id = request.POST.get('subject')
        csv_file = request.FILES.get('csv_file')
        
        try:
            subject = Subject.objects.get(id=subject_id)
        except Subject.DoesNotExist:
            messages.error(request, 'Invalid subject selected.')
            return redirect('upload_questions')
        
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Please upload a CSV file.')
            return redirect('upload_questions')
        
        try:
            decoded_file = csv_file.read().decode('utf-8').splitlines()
            csv_reader = csv.DictReader(decoded_file)
            for row in csv_reader:
                Question.objects.create(
                    subject=subject,  # Use the subject instance
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
    
    return render(request, 'upload_questions.html', {
        'subjects': subjects  # Pass subjects to template
    })

@login_required
def create_exam(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Access denied.")
    
    # Get all subjects for the dropdown
    subjects = Subject.objects.all()
    
    if request.method == 'POST':
        title = request.POST['title']
        subject_id = request.POST['subject']  # Get subject ID
        number_of_questions = int(request.POST['number_of_questions'])
        duration_minutes = int(request.POST['duration_minutes'])
        start_time = request.POST['start_time']
        end_time = request.POST['end_time']
        cutoff_score = int(request.POST['cutoff_score'])
        
        try:
            subject = Subject.objects.get(id=subject_id)
        except Subject.DoesNotExist:
            messages.error(request, 'Invalid subject selected.')
            return redirect('create_exam')
        
        Exam.objects.create(
            title=title,
            subject=subject,  # Use the subject instance
            number_of_questions=number_of_questions,
            duration_minutes=duration_minutes,
            start_time=start_time,
            end_time=end_time,
            cutoff_score=cutoff_score,
            created_by=request.user
        )
        messages.success(request, 'Exam created successfully.')
        return redirect('examiner_dashboard')
    
    return render(request, 'create_exam.html', {
        'subjects': subjects  # Pass subjects to template
    })

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
            try:
                answers = json.loads(request.POST.get('answers', '{}'))
            except json.JSONDecodeError:
                answers = {}
                
            attempt.answers = answers
            attempt.completed = True
            attempt.completion_time = timezone.now()  # Set completion time
            attempt.save()
            attempt.calculate_score()

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


@login_required
def manage_subjects(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Access denied.")
    
    subjects = Subject.objects.all()
    return render(request, 'manage_subjects.html', {
        'subjects': subjects
    })

@login_required
def add_subject(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Access denied.")
    
    if request.method == 'POST':
        name = request.POST['name']
        code = request.POST['code']
        
        try:
            Subject.objects.create(
                name=name,
                code=code.upper(),
                created_by=request.user
            )
            messages.success(request, 'Subject added successfully.')
        except Exception as e:
            messages.error(request, f'Error adding subject: {str(e)}')
        
        return redirect('manage_subjects')
    
    return redirect('manage_subjects')

@login_required
def delete_subject(request, subject_id):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Access denied.")
    
    try:
        subject = Subject.objects.get(id=subject_id)
        
        # Prevent deletion if subject has questions or exams
        if subject.questions.exists() or subject.exams.exists():
            messages.error(request, 'Cannot delete subject with associated questions or exams.')
        else:
            subject.delete()
            messages.success(request, 'Subject deleted successfully.')
    except Subject.DoesNotExist:
        messages.error(request, 'Subject not found.')
    
    return redirect('manage_subjects')

# exam/views.py
from django.contrib.auth.models import User
from django.db import IntegrityError

@login_required
def bulk_upload_students(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Access denied.")
    
    success_count = 0
    error_messages = []
    
    if request.method == 'POST':
        csv_file = request.FILES.get('csv_file')
        
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Please upload a CSV file.')
            return redirect('bulk_upload_students')
        
        try:
            decoded_file = csv_file.read().decode('utf-8').splitlines()
            csv_reader = csv.DictReader(decoded_file)
            
            for row_num, row in enumerate(csv_reader, 2):  # Start at 2 for header row
                try:
                    username = row['username'].strip()
                    first_name = row.get('first_name', '').strip()
                    last_name = row.get('last_name', '').strip()
                    password = row.get('password', 'defaultpassword').strip()
                    
                    # Create user
                    user = User.objects.create_user(
                        username=username,
                        password=password,
                        first_name=first_name,
                        last_name=last_name,
                        is_staff=False,
                        is_superuser=False
                    )
                    success_count += 1
                    
                except KeyError as e:
                    error_messages.append(f"Row {row_num}: Missing column - {str(e)}")
                except IntegrityError:
                    error_messages.append(f"Row {row_num}: Username '{username}' already exists")
                except Exception as e:
                    error_messages.append(f"Row {row_num}: {str(e)}")
            
            if success_count > 0:
                messages.success(request, f'Successfully created {success_count} student accounts')
            if error_messages:
                messages.warning(request, f'Completed with {len(error_messages)} errors')
                request.session['bulk_upload_errors'] = error_messages
            
        except Exception as e:
            messages.error(request, f'Error processing file: {str(e)}')
        
        return redirect('bulk_upload_students')
    
    # Get errors from session if any
    errors = request.session.pop('bulk_upload_errors', [])
    
    return render(request, 'bulk_upload_students.html', {
        'errors': errors
    })

# exam/views.py
from django.http import HttpResponse

@login_required
def download_student_template(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Access denied.")
    
    # Create CSV template
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="student_upload_template.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['username', 'first_name', 'last_name', 'password'])
    writer.writerow(['student1', 'John', 'Doe', 'pass123'])
    writer.writerow(['student2', 'Jane', 'Smith', 'pass456'])
    writer.writerow(['student3', 'Alex', 'Jones', 'pass789'])
    
    return response