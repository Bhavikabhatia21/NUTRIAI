from django.contrib import admin
from .models import UserProfile, DietPlan, MealLog, WeightLog


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'age', 'gender', 'weight_kg', 'height_cm', 'goal', 'diet_type', 'created_at']
    list_filter = ['gender', 'goal', 'diet_type', 'activity_level']
    search_fields = ['user__username', 'user__email']


@admin.register(DietPlan)
class DietPlanAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'duration_days', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['user__username', 'title']


@admin.register(MealLog)
class MealLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'meal_type', 'food_name', 'calories', 'date', 'created_at']
    list_filter = ['meal_type', 'date']
    search_fields = ['user__username', 'food_name']


@admin.register(WeightLog)
class WeightLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'weight_kg', 'date', 'created_at']
    search_fields = ['user__username']
