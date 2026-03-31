from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    GENDER_CHOICES = [('M', 'Male'), ('F', 'Female'), ('O', 'Other')]
    ACTIVITY_CHOICES = [
        ('sedentary', 'Sedentary (little/no exercise)'),
        ('light', 'Light (1-3 days/week)'),
        ('moderate', 'Moderate (3-5 days/week)'),
        ('active', 'Active (6-7 days/week)'),
        ('very_active', 'Very Active (twice/day)'),
    ]
    GOAL_CHOICES = [
        ('lose_weight', 'Lose Weight'),
        ('maintain', 'Maintain Weight'),
        ('gain_muscle', 'Gain Muscle'),
        ('improve_health', 'Improve Overall Health'),
        ('manage_condition', 'Manage Health Condition'),
    ]
    DIET_CHOICES = [
        ('none', 'No Restriction'),
        ('vegetarian', 'Vegetarian'),
        ('vegan', 'Vegan'),
        ('keto', 'Ketogenic'),
        ('paleo', 'Paleo'),
        ('gluten_free', 'Gluten-Free'),
        ('diabetic', 'Diabetic-Friendly'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    age = models.PositiveIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    height_cm = models.FloatField(null=True, blank=True, help_text='Height in cm')
    weight_kg = models.FloatField(null=True, blank=True, help_text='Weight in kg')
    activity_level = models.CharField(max_length=20, choices=ACTIVITY_CHOICES, default='moderate')
    goal = models.CharField(max_length=30, choices=GOAL_CHOICES, default='maintain')
    diet_type = models.CharField(max_length=20, choices=DIET_CHOICES, default='none')
    allergies = models.TextField(blank=True, help_text='Comma-separated list')
    health_conditions = models.TextField(blank=True, help_text='e.g. diabetes, hypertension')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

    @property
    def bmi(self):
        if self.height_cm and self.weight_kg:
            h = self.height_cm / 100
            return round(self.weight_kg / (h * h), 1)
        return None

    @property
    def bmi_category(self):
        bmi = self.bmi
        if bmi is None:
            return "N/A"
        if bmi < 18.5:
            return "Underweight"
        elif bmi < 25:
            return "Normal"
        elif bmi < 30:
            return "Overweight"
        else:
            return "Obese"


class DietPlan(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='diet_plans')
    title = models.CharField(max_length=200)
    plan_content = models.TextField()
    calories_target = models.IntegerField(null=True, blank=True)
    protein_target = models.FloatField(null=True, blank=True)
    carbs_target = models.FloatField(null=True, blank=True)
    fat_target = models.FloatField(null=True, blank=True)
    duration_days = models.IntegerField(default=7)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.title}"


class MealLog(models.Model):
    MEAL_TYPES = [
        ('breakfast', 'Breakfast'),
        ('lunch', 'Lunch'),
        ('dinner', 'Dinner'),
        ('snack', 'Snack'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='meal_logs')
    meal_type = models.CharField(max_length=20, choices=MEAL_TYPES)
    food_name = models.CharField(max_length=200)
    calories = models.FloatField(default=0)
    protein = models.FloatField(default=0)
    carbs = models.FloatField(default=0)
    fat = models.FloatField(default=0)
    quantity = models.CharField(max_length=100, default='1 serving')
    date = models.DateField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.meal_type} - {self.food_name}"


class WeightLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='weight_logs')
    weight_kg = models.FloatField()
    date = models.DateField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.user.username} - {self.weight_kg}kg on {self.date}"
