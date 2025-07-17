# exam/models.py
from django.db import models
from django.contrib.auth.models import User
import random

class Question(models.Model):
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
    title = models.CharField(max_length=200)
    number_of_questions = models.PositiveIntegerField()
    duration_minutes = models.PositiveIntegerField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    cutoff_score = models.PositiveIntegerField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def get_random_questions(self):
        questions = list(Question.objects.filter(created_by=self.created_by))
        random.shuffle(questions)
        return questions[:self.number_of_questions]

    def __str__(self):
        return self.title

class ExamAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    score = models.PositiveIntegerField(default=0)
    start_time = models.DateTimeField(auto_now_add=True)
    completed = models.BooleanField(default=False)
    answers = models.JSONField(default=dict)

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