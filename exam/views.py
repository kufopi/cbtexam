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
from django.shortcuts import get_object_or_404


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
    completed_attempts = ExamAttempt.objects.filter(
        exam__created_by=request.user,
        completed=True
    )
    
    total_completed = completed_attempts.count()
    passed_attempts = completed_attempts.filter(
        score__gte=F('exam__cutoff_score')
    ).count()
    
    average_pass_rate = round(
        (passed_attempts / total_completed * 100), 2
    ) if total_completed > 0 else 0
    
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


# exam/views.py
from .models import Subscription
from django.utils import timezone
from datetime import timedelta

@login_required
def subscription_expired(request):
    subscription = Subscription.get_current_subscription()
    return render(request, 'subscription_expired.html', {
        'subscription': subscription
    })

from .models import ActivationCode
# exam/views.py
@login_required
def activate_subscription(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Access denied.")
    
    subscription = Subscription.get_current_subscription()
    error = None
    success = None
    current_code = subscription.activation_code.code if subscription.activation_code else "NO-CODE"
    
    if request.method == 'POST':
        code = request.POST.get('code', '').strip().upper()
        
        # Validate code format
        is_valid, validation_msg = validate_activation_code(code)
        
        if not is_valid:
            error = f"Invalid code format: {validation_msg}"
        else:
            try:
                activation_code = ActivationCode.objects.get(code=code)
                
                if activation_code.is_used():
                    error = "This code has already been used"
                else:
                    # Extend subscription by 1 year
                    subscription.end_date = timezone.now() + timedelta(days=365)  #change later 365
                    subscription.status = Subscription.SYSTEM_ACTIVE
                    
                    # Mark code as used
                    activation_code.mark_used(request.user)
                    
                    # Generate new code for next activation
                    new_code = ActivationCode.create_new_code()
                    subscription.activation_code = new_code
                    subscription.save()
                    
                    success = (
                        "Subscription extended by 1 year!<br>"
                        f"<strong>New Activation Code:</strong> {new_code.code}<br>"
                        "Save this code for future renewals"
                    )
            except ActivationCode.DoesNotExist:
                error = "Invalid activation code: Code not found in system"
    
    return render(request, 'activate_subscription.html', {
        'subscription': subscription,
        'error': error,
        'success': success,
        'current_code': current_code
    })


from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import random
import string
from collections import Counter
def validate_activation_code(code):
    """
    Validate activation code format:
    - Exactly 15 characters
    """
    code = code.strip().upper()
    
    # 1. Length check
    if len(code) != 15:
        return False, "Wrong code"
    
    # 2. Digit check
    if not any(char.isdigit() for char in code):
        return False, "Entry of invalid code can ruin database integrity"
    
    # 3. Special character check
    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?/"
    if not any(char in special_chars for char in code):
        return False, "Invalid code: Your database is at risk"
    
    # 4. Required letters check with EXACT counts
    required_letters = {
        'B': 1, 'A': 3, 'K': 2, 
        'N': 1, 'U': 1, 'F': 1, 'O': 1
    }
    
    letter_counts = {}
    for char in code:
        if char.isalpha():
            letter_counts[char] = letter_counts.get(char, 0) + 1
    
    # Check for EXACT required counts
    for letter, required_count in required_letters.items():
        if letter_counts.get(letter, 0) < required_count:
            return False, f"Code requires {required_count} '{letter}' character(s)"
    
    return True, "Valid code"



# Preview View
@login_required
def preview_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id, created_by=request.user)
    questions = exam.get_random_questions()
    return render(request, 'preview_exam.html', {
        'exam': exam,
        'questions': questions
    })

# Results Report View
@login_required
def exam_results_report(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id, created_by=request.user)
    attempts = ExamAttempt.objects.filter(exam=exam, completed=True).select_related('user')
    
    # Calculate statistics
    total_attempts = attempts.count()
    passed_attempts = attempts.filter(score__gte=exam.cutoff_score).count()
    pass_rate = round((passed_attempts / total_attempts * 100), 2) if total_attempts > 0 else 0
    average_score = attempts.aggregate(avg_score=Avg('score'))['avg_score'] or 0

    return render(request, 'exam_results_report.html', {
        'exam': exam,
        'attempts': attempts,
        'total_attempts': total_attempts,
        'passed_attempts': passed_attempts,
        'pass_rate': pass_rate,
        'average_score': round(average_score, 1)
    })

# Add this to your exam/views.py

@login_required
def download_questions_template(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Access denied.")
    
    # Create CSV template
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="questions_upload_template.csv"'
    
    writer = csv.writer(response)
    # Header row
    writer.writerow(['question', 'option_a', 'option_b', 'option_c', 'option_d', 'correct_answer'])
    
    # Sample data rows
    writer.writerow([
        'What is the capital of France?',
        'London',
        'Berlin',
        'Paris',
        'Madrid',
        'C'
    ])
    writer.writerow([
        'Which planet is known as the Red Planet?',
        'Venus',
        'Mars',
        'Jupiter',
        'Saturn',
        'B'
    ])
    writer.writerow([
        'What is 2 + 2?',
        '3',
        '4',
        '5',
        '6',
        'B'
    ])
    writer.writerow([
        'Who wrote "Romeo and Juliet"?',
        'Charles Dickens',
        'William Shakespeare',
        'Jane Austen',
        'Mark Twain',
        'B'
    ])
    writer.writerow([
        'What is the chemical symbol for gold?',
        'Go',
        'Gd',
        'Au',
        'Ag',
        'C'
    ])
    
    return response