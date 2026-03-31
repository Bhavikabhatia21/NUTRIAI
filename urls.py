from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Auth
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Profile
    path('profile/', views.profile_view, name='profile'),
    path('profile/setup/', views.setup_profile, name='setup_profile'),
    
    # Diet Plans
    path('plan/generate/', views.generate_plan, name='generate_plan'),
    path('plan/<int:plan_id>/', views.view_plan, name='view_plan'),
    path('plan/<int:plan_id>/delete/', views.delete_plan, name='delete_plan'),
    path('plans/', views.my_plans, name='my_plans'),
    
    # Meal Logging
    path('meals/log/', views.log_meal, name='log_meal'),
    path('meals/history/', views.meal_history, name='meal_history'),
    path('meals/<int:meal_id>/delete/', views.delete_meal, name='delete_meal'),
    
    # Weight Tracking
    path('weight/log/', views.log_weight, name='log_weight'),
    path('weight/history/', views.weight_history, name='weight_history'),
    
    # AI Chat
    path('chat/', views.ai_chat, name='ai_chat'),
    path('api/chat/', views.ai_chat_api, name='ai_chat_api'),

    # Workout
    path('workout/', views.workout, name='workout'),
]
