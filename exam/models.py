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