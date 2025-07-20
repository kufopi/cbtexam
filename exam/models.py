# exam/models.py
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
import random

class Subject(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Question(models.Model):
    subject = models.ForeignKey(
        Subject, 
        on_delete=models.CASCADE,
        related_name='questions'
    )
    text = models.TextField()
    option_a = models.CharField(max_length=200)
    option_b = models.CharField(max_length=200)
    option_c = models.CharField(max_length=200)
    option_d = models.CharField(max_length=200)
    correct_answer = models.CharField(max_length=1, choices=[('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')])
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.text[:50]

class Exam(models.Model):
    subject = models.ForeignKey(
        Subject, 
        on_delete=models.CASCADE,
        related_name='exams'
    )
    title = models.CharField(max_length=200)
    number_of_questions = models.PositiveIntegerField()
    duration_minutes = models.PositiveIntegerField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    cutoff_score = models.PositiveIntegerField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.start_time >= self.end_time:
            raise ValidationError("End time must be after start time")
            
        if self.cutoff_score > self.number_of_questions:
            raise ValidationError("Cutoff score cannot exceed number of questions")

    def get_random_questions(self):
        questions = list(Question.objects.filter(
            created_by=self.created_by,
            subject=self.subject
        ))
        random.shuffle(questions)
        return questions[:self.number_of_questions]

    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

class ExamAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    score = models.PositiveIntegerField(default=0)
    start_time = models.DateTimeField(auto_now_add=True)
    completed = models.BooleanField(default=False)
    answers = models.JSONField(default=dict)
    completion_time = models.DateTimeField(null=True, blank=True)
    
    def calculate_score(self):
        score = 0
        for q_id, answer in self.answers.items():
            question = Question.objects.get(id=q_id)
            if question.correct_answer == answer:
                score += 1
        self.score = score
        self.save()
        return score

    def __str__(self):
        return f"{self.user.username} - {self.exam.title}"
    

import string
class ActivationCode(models.Model):
    code = models.CharField(max_length=15, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)
    used_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='used_codes'
    )
    
    def is_used(self):
        return self.used_at is not None
    
    def mark_used(self, user):
        self.used_at = timezone.now()
        self.used_by = user
        self.save()
    
    @classmethod
    def generate_valid_code(cls):
        # Required letters with their counts
        required_letters = {
            'B': 1, 'A': 3, 'K': 2, 
            'N': 1, 'U': 1, 'F': 1, 'O': 1
        }
        
        # Build the list of characters from the required letters
        chars = []
        for letter, count in required_letters.items():
            chars.extend([letter] * count)
        
        # We have 1+3+2+1+1+1+1 = 10 letters so far
        # We need 15 characters total -> 5 more
        # Add at least one digit and one special character
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?/"
        
        # Ensure we have at least one digit and one special character
        chars.append(random.choice(string.digits))
        chars.append(random.choice(special_chars))
        
        # Add 3 more random characters
        for _ in range(3):
            chars.append(random.choice(
                string.ascii_uppercase + string.digits + special_chars
            ))
        
        # Shuffle the list
        random.shuffle(chars)
        return ''.join(chars)
    
    @classmethod
    def create_new_code(cls):
        while True:
            code = cls.generate_valid_code()
            if not cls.objects.filter(code=code).exists():
                return cls.objects.create(code=code)
    
    def __str__(self):
        return f"{self.code} ({'Used' if self.used_at else 'Active'})"



# exam/models.py
from django.utils import timezone
from django.core.exceptions import ValidationError

class Subscription(models.Model):
    SYSTEM_ACTIVE = 'active'
    SYSTEM_EXPIRED = 'expired'
    SYSTEM_LOCKED = 'locked'
    
    STATUS_CHOICES = (
        (SYSTEM_ACTIVE, 'Active'),
        (SYSTEM_EXPIRED, 'Expired'),
        (SYSTEM_LOCKED, 'Locked'),
    )
    
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=SYSTEM_ACTIVE)
    activation_code = models.ForeignKey(
        ActivationCode,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subscription'
    )
    
    @classmethod
    def get_current_subscription(cls):
        sub = cls.objects.first()
        if not sub:
            # Create with initial code
            code = ActivationCode.create_new_code()
            sub = cls.objects.create(
                end_date=timezone.now() + timezone.timedelta(days=365),  # 1 year
                status=cls.SYSTEM_ACTIVE,
                activation_code=code
            )
        return sub
    
    class Meta:
        verbose_name = "System Subscription"
        verbose_name_plural = "System Subscriptions"
    
    def clean(self):
        if self.end_date < timezone.now():
            raise ValidationError("End date cannot be in the past")
    
    def save(self, *args, **kwargs):
        # Update status based on dates
        if self.end_date < timezone.now():
            self.status = self.SYSTEM_EXPIRED
        super().save(*args, **kwargs)
    
    
    
    def is_active(self):
        return self.status == self.SYSTEM_ACTIVE and self.end_date > timezone.now()
    
    def __str__(self):
        return f"Subscription until {self.end_date.strftime('%Y-%m-%d')} ({self.status})"

