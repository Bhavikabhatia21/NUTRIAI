import json
import random
from datetime import date, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Sum
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import UserProfile, DietPlan, MealLog, WeightLog
from .forms import RegisterForm, LoginForm, UserProfileForm, MealLogForm, WeightLogForm


# ─── Auth Views ────────────────────────────────────────────────────────────────

def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.create(user=user)
            login(request, user)
            messages.success(request, f'Welcome, {user.first_name}! Complete your profile to get started.')
            return redirect('setup_profile')
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        form = RegisterForm()
    return render(request, 'registration/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name or user.username}!')
            return redirect(request.GET.get('next', 'dashboard'))
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = LoginForm()
    return render(request, 'registration/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('login')


# ─── Profile Views ──────────────────────────────────────────────────────────────

@login_required
def setup_profile(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated! Generating your AI diet plan...')
            return redirect('generate_plan')
    else:
        form = UserProfileForm(instance=profile)
    return render(request, 'diet/setup_profile.html', {'form': form, 'profile': profile})


@login_required
def profile_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=profile)
    return render(request, 'diet/profile.html', {'form': form, 'profile': profile})


# ─── Dashboard ──────────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    today = date.today()
    
    # Today's meals
    today_meals = MealLog.objects.filter(user=request.user, date=today)
    today_calories = today_meals.aggregate(Sum('calories'))['calories__sum'] or 0
    today_protein = today_meals.aggregate(Sum('protein'))['protein__sum'] or 0
    today_carbs = today_meals.aggregate(Sum('carbs'))['carbs__sum'] or 0
    today_fat = today_meals.aggregate(Sum('fat'))['fat__sum'] or 0

    # Active plan
    active_plan = DietPlan.objects.filter(user=request.user, is_active=True).first()

    # Weight trend (last 7 entries)
    weight_logs = WeightLog.objects.filter(user=request.user)[:7]
    weight_data = list(reversed([{'date': str(w.date), 'weight': w.weight_kg} for w in weight_logs]))

    # Weekly meal summary
    week_start = today - timedelta(days=6)
    weekly_meals = MealLog.objects.filter(user=request.user, date__range=[week_start, today])
    weekly_calories = weekly_meals.aggregate(Sum('calories'))['calories__sum'] or 0

    context = {
        'profile': profile,
        'today_meals': today_meals,
        'today_calories': round(today_calories),
        'today_protein': round(today_protein, 1),
        'today_carbs': round(today_carbs, 1),
        'today_fat': round(today_fat, 1),
        'active_plan': active_plan,
        'weight_data': json.dumps(weight_data),
        'weekly_calories': round(weekly_calories),
        'today': today,
        'meal_form': MealLogForm(initial={'date': today}),
        'weight_form': WeightLogForm(initial={'date': today}),
    }
    return render(request, 'diet/dashboard.html', context)


# ─── Diet Plan Generator (Rule-Based, No API) ───────────────────────────────────

def calculate_calories(profile):
    """Harris-Benedict BMR formula."""
    if not profile.weight_kg or not profile.height_cm or not profile.age:
        return 2000
    w, h, a = profile.weight_kg, profile.height_cm, profile.age
    if profile.gender == 'M':
        bmr = 10 * w + 6.25 * h - 5 * a + 5
    else:
        bmr = 10 * w + 6.25 * h - 5 * a - 161

    activity_mult = {
        'sedentary': 1.2, 'light': 1.375, 'moderate': 1.55,
        'active': 1.725, 'very_active': 1.9
    }.get(profile.activity_level, 1.55)

    tdee = bmr * activity_mult

    goal_adj = {
        'lose_weight': -500, 'maintain': 0,
        'gain_muscle': +300, 'improve_health': -200, 'manage_condition': -100
    }.get(profile.goal, 0)

    return max(1200, round(tdee + goal_adj))


MEAL_DB = {
    'none': {
        'breakfast': [
            ('🥣 Oatmeal with Banana & Nuts', 'Oats 1 cup + banana 1 + mixed nuts 1 handful + milk 1 cup'),
            ('🍳 Eggs & Toast', '2 boiled eggs + whole wheat toast 2 slices + 1 glass milk'),
            ('🥞 Besan Chilla with Curd', 'Besan chilla 2 + green chutney + curd 1 cup'),
            ('🫓 Poha with Peanuts', 'Poha 1.5 cups + peanuts + curry leaves + lemon'),
            ('🥗 Upma with Sambar', 'Semolina upma 1 cup + sambar 1 bowl + green chutney'),
            ('🍚 Idli Sambhar', '4 idlis + sambar 1 bowl + coconut chutney'),
            ('🥙 Paratha with Curd', '2 whole wheat parathas + curd 1 cup + pickle'),
        ],
        'lunch': [
            ('🍛 Dal Chawal with Sabzi', 'Toor dal 1 bowl + rice 1 cup + mixed veg sabzi + salad'),
            ('🫓 Roti with Paneer Curry', '3 rotis + paneer curry 1 bowl + cucumber raita'),
            ('🥘 Rajma Chawal', 'Rajma 1 bowl + rice 1 cup + onion salad + pickle'),
            ('🍜 Chole with Puri', 'Chole 1 bowl + 2 puris + onion salad + lemon'),
            ('🍲 Kadhi Chawal', 'Kadhi 1 bowl + rice 1 cup + papad + salad'),
            ('🥗 Chicken Rice Bowl', 'Grilled chicken 150g + rice 1 cup + stir-fried veg + dal'),
            ('🫕 Palak Paneer with Roti', '2 rotis + palak paneer 1 bowl + boondi raita'),
        ],
        'dinner': [
            ('🍲 Moong Dal Khichdi', 'Moong dal khichdi 1.5 cups + curd + pickle + papad'),
            ('🥘 Sabzi Roti', '2 rotis + seasonal sabzi + dal soup + salad'),
            ('🍛 Light Rice & Dal', 'Rice 3/4 cup + dal 1 bowl + stir-fried greens + salad'),
            ('🥗 Grilled Chicken Salad', 'Grilled chicken 120g + mixed salad + olive oil dressing + roti 1'),
            ('🫕 Vegetable Soup & Toast', 'Mixed veg soup 2 bowls + whole wheat toast 2 slices'),
            ('🍜 Dal Makhani with Roti', '2 rotis + dal makhani 1 bowl + onion salad'),
            ('🥙 Paneer Bhurji with Roti', '2 rotis + paneer bhurji + green chutney + salad'),
        ],
        'snack1': [
            '🍎 Apple + 10 almonds',
            '🥜 Roasted chana 1 cup + green tea',
            '🍌 Banana + peanut butter 1 tsp',
            '🥛 Buttermilk (chaas) 1 glass + murmura',
            '🫐 Mixed berries + yogurt 100g',
            '🥕 Carrot & cucumber sticks + hummus',
            '🧀 Paneer cubes 50g + lemon + chaat masala',
        ],
        'snack2': [
            '🥤 Protein shake / milk 1 glass',
            '🍊 Orange or seasonal fruit',
            '🫓 Rice cakes with peanut butter',
            '🥛 Warm turmeric milk (haldi doodh)',
            '🥜 Handful of walnuts + dates 2',
            '🍵 Green tea + digestive biscuits 2',
            '🧆 Boiled corn with lemon & salt',
        ],
    },
    'vegetarian': {
        'breakfast': [
            ('🥛 Milk Oats with Fruits', 'Oats 1 cup + milk 1 cup + apple + honey'),
            ('🍳 Paneer Scramble & Toast', 'Paneer 100g scrambled + toast 2 + chai 1 cup'),
            ('🥞 Besan Chilla', 'Besan chilla 3 + mint chutney + curd'),
            ('🫓 Poha with Peanuts', 'Poha 1.5 cups + peanuts + pomegranate seeds'),
            ('🥗 Sprouts Salad & Idli', '2 idlis + sprouts salad 1 bowl + sambar'),
            ('🍚 Vermicelli Upma', 'Semiya upma 1 bowl + coriander chutney + chai'),
            ('🧇 Methi Thepla', '2 methi theplas + curd + pickle'),
        ],
        'lunch': [
            ('🍛 Dal Chawal & Sabzi', 'Moong dal + rice + seasonal sabzi + salad'),
            ('🫕 Paneer Tikka Roti', '3 rotis + paneer tikka masala + raita'),
            ('🥘 Rajma Chawal', 'Rajma curry + rice + onion salad'),
            ('🍲 Kadhi Pakoda', 'Kadhi pakoda + rice + papad'),
            ('🥗 Chole Bhature', 'Chole + 2 bhaturas + onion salad'),
            ('🫕 Palak Dal Roti', '3 rotis + palak dal + boondi raita'),
            ('🥙 Mixed Veg Pulao', 'Veg pulao 1.5 cups + raita + papad'),
        ],
        'dinner': [
            ('🍲 Moong Dal Khichdi', 'Khichdi 1.5 cups + ghee 1 tsp + pickle + curd'),
            ('🥘 Lauki Sabzi Roti', '2 rotis + lauki sabzi + dal + salad'),
            ('🫕 Palak Paneer Roti', '2 rotis + palak paneer + cucumber'),
            ('🥗 Veg Soup & Toast', 'Tomato soup + whole wheat toast 2 + fruit'),
            ('🍛 Light Dal Rice', 'Toor dal + rice 3/4 cup + stir-fried greens'),
            ('🧆 Stuffed Paratha', '2 stuffed parathas + curd + salad'),
            ('🥙 Paneer Bhurji Roti', '2 rotis + paneer bhurji + green chutney'),
        ],
        'snack1': [
            '🍎 Apple + 10 almonds',
            '🥜 Roasted chana 1 cup',
            '🥛 Buttermilk 1 glass',
            '🫐 Fruit bowl with yogurt',
            '🧀 Paneer cubes 50g + chaat masala',
            '🥕 Veggies + hummus',
            '🌽 Roasted corn 1 cup',
        ],
        'snack2': [
            '🥛 Warm haldi doodh',
            '🍊 Seasonal fruit',
            '🥜 Walnuts + dates 2',
            '🍵 Green tea + fox nuts (makhana)',
            '🧇 Small dhokla 2 pieces',
            '🥛 Curd 1 cup + honey',
            '🍌 Banana + peanut butter',
        ],
    },
    'vegan': {
        'breakfast': [
            ('🥣 Oat Porridge with Almond Milk', 'Oats 1 cup + almond milk + banana + chia seeds'),
            ('🥞 Besan Chilla', 'Besan chilla 3 + green chutney + coconut yogurt'),
            ('🫓 Poha with Peanuts', 'Poha + peanuts + lemon + curry leaves'),
            ('🥗 Smoothie Bowl', 'Blended banana + mango + granola + seeds'),
            ('🍚 Upma', 'Semolina upma + vegetables + lemon'),
            ('🥙 Ragi Dosa', 'Ragi dosa 2 + sambar + coconut chutney'),
            ('🧇 Vegetable Sandwich', 'Whole wheat bread + veggies + hummus'),
        ],
        'lunch': [
            ('🍛 Dal Rice & Sabzi', 'Moong dal + rice + seasonal sabzi + salad'),
            ('🥘 Chole Roti', 'Chole + 3 rotis + onion salad'),
            ('🥗 Tofu Stir Fry Rice', 'Tofu + mixed veg + brown rice 1 cup'),
            ('🫕 Rajma Roti', 'Rajma + 3 rotis + cucumber raita (coconut yogurt)'),
            ('🍲 Veg Pulao & Dal', 'Veg pulao + moong dal soup'),
            ('🥙 Buddha Bowl', 'Chickpeas + quinoa + roasted veg + tahini'),
            ('🫕 Masoor Dal Roti', '3 rotis + masoor dal + green sabzi'),
        ],
        'dinner': [
            ('🍲 Khichdi', 'Moong dal khichdi + pickle + salad'),
            ('🥗 Lentil Soup & Toast', 'Red lentil soup + whole wheat toast'),
            ('🥘 Sabzi Roti', '2 rotis + seasonal sabzi + dal'),
            ('🍛 Brown Rice & Dal', 'Brown rice + toor dal + stir-fried greens'),
            ('🫕 Tofu Palak', 'Tofu palak + 2 rotis + salad'),
            ('🥙 Veg Curry Rice', 'Mixed veg curry + rice 3/4 cup'),
            ('🧆 Stuffed Roti', 'Stuffed roti 2 + coconut yogurt + salad'),
        ],
        'snack1': [
            '🍎 Apple + almond butter',
            '🥜 Mixed nuts + dried fruits',
            '🫐 Berry smoothie (almond milk)',
            '🥕 Veggies + hummus',
            '🌽 Roasted chana + seeds',
            '🍌 Banana + peanut butter',
            '🧆 Roasted makhana (fox nuts)',
        ],
        'snack2': [
            '🍵 Green tea + dark chocolate 1 square',
            '🥛 Soy milk warm',
            '🍊 Orange + walnuts',
            '🥜 Handful mixed nuts',
            '🫐 Coconut yogurt + berries',
            '🍌 Dates 3 + almonds 5',
            '🥤 Coconut water 1 glass',
        ],
    },
    'keto': {
        'breakfast': [
            ('🍳 Eggs & Avocado', '3 scrambled eggs + avocado half + butter + coffee/tea'),
            ('🧀 Paneer Omelette', '3 egg omelette + paneer 50g + spinach + ghee'),
            ('🥓 Egg Bhurji', 'Egg bhurji 3 eggs + capsicum + ghee + green chutney'),
            ('🥗 Chia Pudding', 'Chia seeds 3 tbsp + coconut milk + nuts'),
            ('🍳 Masala Omelette', '3 egg omelette + tomato + onion + cheese'),
            ('🥑 Bulletproof Coffee', 'Black coffee + coconut oil 1 tsp + heavy cream (+ nuts)'),
            ('🧆 Cheese Egg Muffins', 'Egg muffins 3 + cheese + capsicum + herbs'),
        ],
        'lunch': [
            ('🥗 Grilled Chicken Salad', 'Chicken 200g + greens + olive oil + feta'),
            ('🍗 Chicken Curry (no rice)', 'Chicken curry 200g + cauliflower rice + salad'),
            ('🥘 Paneer Tikka', 'Paneer tikka 150g + capsicum + onion + mint chutney'),
            ('🫕 Mutton Keema', 'Mutton keema 150g + boiled egg + salad'),
            ('🥗 Tuna Salad', 'Tuna 150g + olives + cucumber + lemon mayo'),
            ('🍗 Baked Fish', 'Fish 200g + roasted vegetables + garlic butter'),
            ('🥙 Egg Salad Wrap (lettuce)', 'Egg salad + lettuce wrap + avocado'),
        ],
        'dinner': [
            ('🥘 Grilled Mutton & Veg', 'Mutton 150g + stir-fried low-carb veg + salad'),
            ('🍗 Chicken with Butter Sauce', 'Chicken 180g + cream sauce + sautéed spinach'),
            ('🥗 Paneer Palak', 'Paneer 150g + palak gravy + cucumber salad'),
            ('🍳 Egg Curry', 'Egg curry 3 eggs + coconut cream + cauliflower rice'),
            ('🥙 Fish Tikka', 'Fish tikka 180g + green salad + lemon'),
            ('🫕 Shrimp Stir Fry', 'Shrimp 150g + capsicum + zucchini + ghee'),
            ('🥘 Lamb Chops', 'Lamb chops 2 + roasted cauliflower + salad'),
        ],
        'snack1': [
            '🧀 Cheese cubes + olives',
            '🥜 Macadamia nuts + walnuts',
            '🥑 Avocado with salt & pepper',
            '🍳 Hard boiled egg + mayo',
            '🫙 Pork rinds + guacamole',
            '🧀 Paneer 50g + herbs',
            '🥥 Coconut chips + almonds',
        ],
        'snack2': [
            '🥛 Heavy cream tea/coffee',
            '🥜 Pecans + dark chocolate (90%)',
            '🧀 String cheese',
            '🥑 Guacamole + cucumber',
            '🍳 Deviled eggs 2',
            '🫙 Cream cheese + celery',
            '🥥 Coconut milk kefir',
        ],
    },
    'diabetic': {
        'breakfast': [
            ('🥣 Steel-Cut Oats', 'Steel-cut oats 1/2 cup + cinnamon + flaxseeds + nuts'),
            ('🍳 Egg White Omelette', '3 egg whites + 1 yolk + spinach + tomato + toast 1'),
            ('🥞 Besan Chilla (low oil)', 'Besan chilla 2 + green chutney + low-fat curd'),
            ('🫓 Poha (brown rice)', 'Brown rice poha + peanuts + vegetables'),
            ('🥗 Ragi Dosa', 'Ragi dosa 2 + sambar + coconut chutney (less)'),
            ('🥛 Greek Yogurt & Berries', 'Low-fat Greek yogurt 150g + berries + chia'),
            ('🧇 Methi Paratha (small)', '1 small methi paratha + low-fat curd'),
        ],
        'lunch': [
            ('🍛 Brown Rice Dal Sabzi', 'Brown rice 1/2 cup + dal + sabzi + salad (big)'),
            ('🫕 Multigrain Roti & Dal', '2 multigrain rotis + moong dal + stir-fried veg'),
            ('🥗 Chickpea Salad', 'Chickpeas 1 cup + veggies + lemon + olive oil'),
            ('🍲 Barley Khichdi', 'Barley khichdi 1 cup + curd + salad'),
            ('🥘 Palak Dal Roti', '2 rotis + palak moong dal + cucumber raita'),
            ('🥙 Quinoa Veg Bowl', 'Quinoa 1/2 cup + roasted veg + paneer 50g'),
            ('🫕 Grilled Fish Roti', '1 roti + grilled fish + salad'),
        ],
        'dinner': [
            ('🍲 Light Moong Khichdi', 'Moong khichdi 1 cup + pickle + salad'),
            ('🥘 Sabzi & Small Roti', '1 roti + seasonal sabzi + dal + big salad'),
            ('🥗 Grilled Chicken Veg', 'Grilled chicken 100g + roasted veg + salad'),
            ('🫕 Dal Soup & Toast', 'Moong dal soup + 1 whole wheat toast'),
            ('🍛 Low-GI Rice Dal', 'Low-GI rice 1/3 cup + toor dal + greens'),
            ('🥙 Paneer Stir Fry', 'Paneer 100g + capsicum + onion + roti 1'),
            ('🥗 Methi Sabzi & Roti', '1 roti + methi sabzi + curd'),
        ],
        'snack1': [
            '🥜 Roasted chana 1/2 cup',
            '🍎 Small apple + cinnamon',
            '🥕 Raw vegetables sticks',
            '🥛 Low-fat buttermilk',
            '🫐 Berries 1/2 cup',
            '🧆 Flaxseed crackers + hummus',
            '🥜 Walnuts 5 + cucumber',
        ],
        'snack2': [
            '🍵 Cinnamon green tea',
            '🧀 Low-fat paneer 30g',
            '🥛 Warm low-fat milk + turmeric',
            '🥜 Almonds 8',
            '🥗 Small sprouts salad',
            '🍊 Half orange or guava',
            '🫙 Low-fat curd 1/2 cup',
        ],
    },
    'gluten_free': {
        'breakfast': [
            ('🥣 Quinoa Porridge', 'Quinoa 1/2 cup + almond milk + banana + honey'),
            ('🍳 Eggs & Potato Hash', '2 eggs + potato 1 small + capsicum + spinach'),
            ('🥞 Rice Flour Dosa', 'Rice flour dosa 2 + sambar + coconut chutney'),
            ('🫓 Poha (GF)', 'Poha 1.5 cups + peanuts + lemon + curry leaves'),
            ('🥗 Ragi Porridge', 'Ragi porridge + milk + jaggery + nuts'),
            ('🍚 Idli & Sambar', '4 idlis + sambar + coconut chutney'),
            ('🥛 Smoothie Bowl', 'Banana + mango + almond milk + seeds'),
        ],
        'lunch': [
            ('🍛 Rice Dal Sabzi', 'Rice 1 cup + dal + sabzi + salad'),
            ('🥘 Rajma Chawal', 'Rajma + rice + onion salad'),
            ('🥗 Quinoa Veg Bowl', 'Quinoa + roasted veg + paneer + lemon'),
            ('🍲 Sabudana Khichdi', 'Sabudana khichdi + peanuts + curd'),
            ('🫕 Rice Flour Roti & Dal', 'Rice roti 2 + dal + sabzi'),
            ('🥙 Grilled Chicken Rice', 'Grilled chicken + rice + stir-fried veg'),
            ('🫕 Palak Dal Rice', 'Rice + palak dal + salad'),
        ],
        'dinner': [
            ('🍲 Moong Dal Khichdi', 'Moong khichdi + curd + pickle'),
            ('🥘 Light Rice & Sabzi', 'Rice 3/4 cup + sabzi + dal'),
            ('🥗 Grilled Veg & Rice', 'Grilled vegetables + rice + dal soup'),
            ('🍛 Chicken Curry Rice', 'Chicken curry + rice 3/4 cup + salad'),
            ('🫕 Ragi Roti & Dal', 'Ragi roti 2 + dal + greens'),
            ('🥙 Fish Curry Rice', 'Fish curry + rice + salad'),
            ('🥗 Egg Curry Roti', 'Rice roti + egg curry + salad'),
        ],
        'snack1': [
            '🍎 Apple + rice cakes',
            '🥜 Mixed nuts + seeds',
            '🥛 Buttermilk + roasted chana',
            '🫐 Fruit bowl',
            '🧆 Makhana (fox nuts) roasted',
            '🥕 Veggies + hummus',
            '🌽 Roasted corn',
        ],
        'snack2': [
            '🍵 Green tea + dark chocolate',
            '🥛 Warm turmeric milk',
            '🍌 Banana + peanut butter',
            '🥜 Dates + almonds',
            '🫐 Coconut yogurt + berries',
            '🍊 Seasonal fruit',
            '🥛 Rice milk + nuts',
        ],
    },
    'paleo': {
        'breakfast': [
            ('🍳 Eggs & Bacon', '3 eggs + bacon 2 strips + sautéed spinach + black coffee'),
            ('🥑 Egg & Avocado', '2 eggs + avocado half + tomato + coconut oil'),
            ('🍌 Banana Pancakes', 'Banana + eggs pancake + berries + honey'),
            ('🥗 Smoked Salmon Salad', 'Smoked salmon 100g + greens + cucumber + lemon'),
            ('🥜 Nut & Seed Bowl', 'Mixed nuts + seeds + coconut flakes + berries'),
            ('🍳 Sweet Potato Hash', 'Sweet potato + eggs + capsicum + herbs'),
            ('🥥 Coconut Chia Pudding', 'Coconut milk + chia + mango + nuts'),
        ],
        'lunch': [
            ('🥗 Grilled Chicken Salad', 'Grilled chicken 200g + mixed greens + olive oil'),
            ('🍗 Roast Chicken Veg', 'Chicken 200g + roasted sweet potato + salad'),
            ('🥘 Lamb Stew', 'Lamb 150g + vegetables + herbs (no grains)'),
            ('🥗 Tuna Salad', 'Tuna 150g + avocado + greens + lemon'),
            ('🍗 Turkey Wrap (lettuce)', 'Turkey 150g + lettuce + tomato + mustard'),
            ('🥩 Beef Stir Fry', 'Beef 150g + mixed vegetables + coconut aminos'),
            ('🫕 Salmon & Veg', 'Salmon 180g + roasted vegetables + lemon'),
        ],
        'dinner': [
            ('🥘 Grilled Lamb Chops', 'Lamb 180g + sweet potato mash + salad'),
            ('🍗 Baked Chicken Thighs', 'Chicken 200g + roasted veg + herbs'),
            ('🥗 Fish Curry (coconut)', 'Fish 180g + coconut curry + cauliflower rice'),
            ('🥩 Grass-Fed Beef Steak', 'Steak 150g + grilled veg + herb butter'),
            ('🫕 Prawn Stir Fry', 'Prawns 180g + vegetables + coconut oil + herbs'),
            ('🍗 Turkey Meatballs', 'Turkey meatballs 150g + zucchini noodles + marinara'),
            ('🥘 Duck Confit', 'Duck 150g + sautéed greens + sweet potato'),
        ],
        'snack1': [
            '🥜 Mixed nuts + dried fruit',
            '🍎 Apple + almond butter',
            '🥑 Guacamole + veggie sticks',
            '🥥 Coconut chips',
            '🍌 Banana + walnut',
            '🫐 Berries + coconut cream',
            '🧆 Primal beef jerky',
        ],
        'snack2': [
            '🥛 Coconut milk + seeds',
            '🥜 Macadamia nuts',
            '🍊 Orange + almonds',
            '🍵 Herbal tea + dates 2',
            '🥑 Avocado with salt',
            '🫐 Berry smoothie',
            '🥥 Coconut water',
        ],
    },
}


def get_meal_db(diet_type):
    """Return meals for the given diet type, fallback to 'none'."""
    return MEAL_DB.get(diet_type, MEAL_DB['none'])


NUTRITION_TIPS = {
    'lose_weight': [
        "Eat slowly — it takes 20 minutes for your brain to register fullness.",
        "Start every meal with a glass of water and a salad.",
        "Avoid liquid calories (juice, soda, chai with sugar).",
        "Use smaller plates to control portion sizes naturally.",
        "Fill half your plate with vegetables at every meal.",
    ],
    'gain_muscle': [
        "Eat protein within 30 minutes after every workout.",
        "Aim for 1.6–2.2g protein per kg of body weight daily.",
        "Don't skip breakfast — it sets your anabolic window.",
        "Include leucine-rich foods: eggs, paneer, dal, chicken.",
        "Eat every 3–4 hours to keep muscle protein synthesis active.",
    ],
    'maintain': [
        "Maintain meal consistency — same times every day.",
        "Track calories once a week to stay aware.",
        "Balance your macros: 40% carbs, 30% protein, 30% fat.",
        "Stay active with at least 30 minutes of movement daily.",
        "Cook at home more often to control ingredients.",
    ],
    'improve_health': [
        "Add one extra serving of vegetables to every meal.",
        "Replace refined grains with whole grains (brown rice, oats).",
        "Eat a rainbow of fruits and vegetables for micronutrients.",
        "Limit processed foods and packaged snacks.",
        "Cook with minimal oil using heart-healthy methods.",
    ],
    'manage_condition': [
        "Monitor your blood sugar / BP before and after meals.",
        "Avoid high-GI foods: white rice, maida, sugar, potatoes.",
        "Eat 5–6 small meals instead of 3 large ones.",
        "Include bitter foods: karela, methi, jamun for blood sugar.",
        "Consult your doctor before making major dietary changes.",
    ],
}

FOODS_TO_AVOID = {
    'lose_weight': ['Fried foods (samosa, pakoda)', 'Sugary drinks & juices', 'White bread & maida items', 'Ice cream & desserts', 'Alcohol', 'Packaged chips & namkeen'],
    'gain_muscle': ['Alcohol (inhibits protein synthesis)', 'Excessive sugar', 'Trans fats (vanaspati)', 'Skipping meals', 'Low-protein junk foods'],
    'maintain': ['Excess sugar', 'Deep fried foods', 'Processed meats', 'Excess salt', 'Refined carbohydrates'],
    'improve_health': ['Trans fats & vanaspati', 'Excess salt & pickles', 'White sugar', 'Processed & packaged foods', 'Refined oils in excess'],
    'manage_condition': ['White rice in excess', 'Maida items', 'Sweet fruits (mango, banana)', 'Sugar & sweets', 'Alcohol', 'Deep-fried snacks', 'Fruit juices'],
}

FOODS_TO_EMPHASIZE = {
    'lose_weight': ['Green vegetables (spinach, broccoli)', 'Lean proteins (dal, eggs, chicken)', 'Fibre-rich foods (oats, barley)', 'Whole fruits', 'Green tea', 'Water'],
    'gain_muscle': ['Eggs & paneer', 'Dal & legumes', 'Chicken & fish', 'Whole grains (brown rice, oats)', 'Milk & curd', 'Nuts & seeds'],
    'maintain': ['Balanced whole foods', 'Seasonal vegetables & fruits', 'Whole grains', 'Lean proteins', 'Healthy fats (nuts, ghee in moderation)'],
    'improve_health': ['Leafy greens (spinach, methi)', 'Whole grains', 'Legumes & pulses', 'Olive oil & nuts', 'Berries & amla', 'Turmeric, ginger, garlic'],
    'manage_condition': ['Bitter gourd (karela)', 'Fenugreek (methi)', 'Oats & barley', 'Leafy greens', 'Low-GI fruits (guava, jamun)', 'Cinnamon & turmeric'],
}

SUPPLEMENTS = {
    'lose_weight': ['Vitamin D3 (if deficient)', 'Magnesium (aids sleep & metabolism)', 'Green tea extract (optional)'],
    'gain_muscle': ['Whey protein powder', 'Creatine monohydrate (5g/day)', 'Vitamin D3', 'Omega-3 fish oil'],
    'maintain': ['Multivitamin (once daily)', 'Vitamin D3 (if deficient)', 'Omega-3 (2g/day)'],
    'improve_health': ['Omega-3 fish oil (2g/day)', 'Vitamin D3', 'Multivitamin', 'Probiotics'],
    'manage_condition': ['Chromium picolinate (blood sugar)', 'Magnesium', 'Vitamin D3', 'Alpha lipoic acid (consult doctor)'],
}


def generate_diet_plan_text(profile):
    """Generate a complete 7-day diet plan as formatted text — no API needed."""
    calories = calculate_calories(profile)
    goal = profile.goal or 'maintain'
    diet_type = profile.diet_type or 'none'
    db = get_meal_db(diet_type)

    # Macro split by goal
    macro_splits = {
        'lose_weight':      (0.35, 0.40, 0.25),
        'gain_muscle':      (0.30, 0.45, 0.25),
        'maintain':         (0.30, 0.45, 0.25),
        'improve_health':   (0.30, 0.45, 0.25),
        'manage_condition': (0.30, 0.40, 0.30),
    }
    fat_r, carb_r, prot_r = macro_splits.get(goal, (0.30, 0.45, 0.25))
    protein_g = round(calories * prot_r / 4)
    carbs_g   = round(calories * carb_r / 4)
    fat_g     = round(calories * fat_r / 9)

    water_ml = round((profile.weight_kg or 70) * 35)

    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    day_emojis = ['🌟', '🔥', '💪', '⚡', '🌿', '🌈', '🎯']

    lines = []
    lines.append(f"# 🥗 Your Personalized 7-Day Diet Plan")
    lines.append(f"**Generated for:** {profile.user.get_full_name() or profile.user.username}  ")
    lines.append(f"**Goal:** {profile.get_goal_display()}  |  **Diet:** {profile.get_diet_type_display()}")
    if profile.bmi:
        lines.append(f"**BMI:** {profile.bmi} ({profile.bmi_category})  |  **Weight:** {profile.weight_kg}kg  |  **Height:** {profile.height_cm}cm")
    lines.append("")

    lines.append("---")
    lines.append("## 📊 Your Daily Targets")
    lines.append(f"| Nutrient | Daily Target |")
    lines.append(f"|---|---|")
    lines.append(f"| 🔥 Calories | **{calories} kcal** |")
    lines.append(f"| 💪 Protein | **{protein_g}g** |")
    lines.append(f"| ⚡ Carbohydrates | **{carbs_g}g** |")
    lines.append(f"| 🥑 Fat | **{fat_g}g** |")
    lines.append(f"| 💧 Water | **{water_ml}ml (~{round(water_ml/250)} glasses)** |")
    lines.append("")

    lines.append("---")
    lines.append("## 📅 7-Day Meal Plan")
    lines.append("")

    random.seed(profile.user.id)
    b_idx = random.sample(range(len(db['breakfast'])), 7)
    l_idx = random.sample(range(len(db['lunch'])), 7)
    d_idx = random.sample(range(len(db['dinner'])), 7)
    s1_idx = random.sample(range(len(db['snack1'])), 7)
    s2_idx = random.sample(range(len(db['snack2'])), 7)

    for i, day in enumerate(days):
        b = db['breakfast'][b_idx[i]]
        l = db['lunch'][l_idx[i]]
        d = db['dinner'][d_idx[i]]
        s1 = db['snack1'][s1_idx[i]]
        s2 = db['snack2'][s2_idx[i]]

        lines.append(f"### {day_emojis[i]} {day}")
        lines.append(f"**🌅 Breakfast:** {b[0]}")
        lines.append(f"  - {b[1]}")
        lines.append(f"**🍎 Morning Snack:** {s1}")
        lines.append(f"**☀️ Lunch:** {l[0]}")
        lines.append(f"  - {l[1]}")
        lines.append(f"**🌿 Evening Snack:** {s2}")
        lines.append(f"**🌙 Dinner:** {d[0]}")
        lines.append(f"  - {d[1]}")
        lines.append("")

    lines.append("---")
    lines.append("## ✅ Foods to Emphasize")
    for f in FOODS_TO_EMPHASIZE.get(goal, FOODS_TO_EMPHASIZE['maintain']):
        lines.append(f"- ✅ {f}")
    lines.append("")

    lines.append("## ❌ Foods to Avoid")
    for f in FOODS_TO_AVOID.get(goal, FOODS_TO_AVOID['maintain']):
        lines.append(f"- ❌ {f}")
    lines.append("")

    lines.append("## 💡 Key Nutrition Tips")
    for tip in NUTRITION_TIPS.get(goal, NUTRITION_TIPS['maintain']):
        lines.append(f"- 💡 {tip}")
    lines.append("")

    lines.append("## 💧 Hydration Guidelines")
    lines.append(f"- Drink **{water_ml}ml of water daily** ({round(water_ml/250)} glasses)")
    lines.append("- Start your day with 1 glass of warm water + lemon")
    lines.append("- Drink a glass of water 30 min before each meal")
    lines.append("- Avoid sugary drinks, soda, and packaged juices")
    lines.append("- Herbal teas (green tea, chamomile) count towards hydration")
    lines.append("")

    lines.append("## 💊 Supplement Suggestions")
    for s in SUPPLEMENTS.get(goal, SUPPLEMENTS['maintain']):
        lines.append(f"- 💊 {s}")
    lines.append("")
    lines.append("*⚠️ Always consult your doctor before starting any supplements.*")
    lines.append("")
    lines.append("---")
    lines.append("*This plan is generated based on your profile. For medical conditions, please consult a registered dietitian.*")

    return '\n'.join(lines), calories, protein_g, carbs_g, fat_g


@login_required
def generate_plan(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if not profile.age or not profile.weight_kg:
        messages.warning(request, 'Please complete your profile first.')
        return redirect('setup_profile')

    if request.method == 'POST':
        plan_text, calories, protein_g, carbs_g, fat_g = generate_diet_plan_text(profile)

        # Deactivate old plans
        DietPlan.objects.filter(user=request.user, is_active=True).update(is_active=False)

        plan = DietPlan.objects.create(
            user=request.user,
            title=f"Diet Plan - {date.today().strftime('%B %d, %Y')}",
            plan_content=plan_text,
            calories_target=calories,
            protein_target=protein_g,
            carbs_target=carbs_g,
            fat_target=fat_g,
            duration_days=7,
            is_active=True,
        )
        messages.success(request, 'Your personalized diet plan has been generated!')
        return redirect('view_plan', plan_id=plan.id)

    plans = DietPlan.objects.filter(user=request.user)
    return render(request, 'diet/generate_plan.html', {'profile': profile, 'plans': plans})


@login_required
def view_plan(request, plan_id):
    plan = get_object_or_404(DietPlan, id=plan_id, user=request.user)
    return render(request, 'diet/view_plan.html', {'plan': plan})


@login_required
def my_plans(request):
    plans = DietPlan.objects.filter(user=request.user)
    return render(request, 'diet/my_plans.html', {'plans': plans})


@login_required
def delete_plan(request, plan_id):
    plan = get_object_or_404(DietPlan, id=plan_id, user=request.user)
    if request.method == 'POST':
        plan.delete()
        messages.success(request, 'Diet plan deleted.')
    return redirect('my_plans')


# ─── Meal Logging ───────────────────────────────────────────────────────────────

@login_required
def log_meal(request):
    if request.method == 'POST':
        form = MealLogForm(request.POST)
        if form.is_valid():
            meal = form.save(commit=False)
            meal.user = request.user
            meal.save()
            messages.success(request, f'{meal.food_name} logged successfully!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Please fix the form errors.')
    else:
        form = MealLogForm(initial={'date': date.today()})
    return render(request, 'diet/log_meal.html', {'form': form})


@login_required
def meal_history(request):
    meals = MealLog.objects.filter(user=request.user)
    
    # Date filter
    filter_date = request.GET.get('date')
    if filter_date:
        meals = meals.filter(date=filter_date)
    
    # Group by date
    meal_data = {}
    for meal in meals[:50]:
        d = str(meal.date)
        if d not in meal_data:
            meal_data[d] = {'meals': [], 'total_cal': 0, 'total_protein': 0, 'total_carbs': 0, 'total_fat': 0}
        meal_data[d]['meals'].append(meal)
        meal_data[d]['total_cal'] += meal.calories
        meal_data[d]['total_protein'] += meal.protein
        meal_data[d]['total_carbs'] += meal.carbs
        meal_data[d]['total_fat'] += meal.fat

    return render(request, 'diet/meal_history.html', {'meal_data': meal_data, 'filter_date': filter_date})


@login_required
def delete_meal(request, meal_id):
    meal = get_object_or_404(MealLog, id=meal_id, user=request.user)
    if request.method == 'POST':
        meal.delete()
        messages.success(request, 'Meal deleted.')
    return redirect('meal_history')


# ─── Weight Tracking ────────────────────────────────────────────────────────────

@login_required
def log_weight(request):
    if request.method == 'POST':
        form = WeightLogForm(request.POST)
        if form.is_valid():
            log = form.save(commit=False)
            log.user = request.user
            log.save()
            # Update profile weight
            profile, _ = UserProfile.objects.get_or_create(user=request.user)
            profile.weight_kg = log.weight_kg
            profile.save()
            messages.success(request, f'Weight {log.weight_kg}kg logged!')
            return redirect('dashboard')
    else:
        form = WeightLogForm(initial={'date': date.today()})
    return render(request, 'diet/log_weight.html', {'form': form})


@login_required
def weight_history(request):
    logs = WeightLog.objects.filter(user=request.user)
    chart_data = list(reversed([{'date': str(w.date), 'weight': w.weight_kg} for w in logs[:30]]))
    return render(request, 'diet/weight_history.html', {
        'logs': logs,
        'chart_data': json.dumps(chart_data)
    })


# ─── Rule-Based Nutrition Chat ──────────────────────────────────────────────────

@login_required
def ai_chat(request):
    return render(request, 'diet/ai_chat.html')


CHAT_RESPONSES = {
    'protein': [
        "Great question! High-protein foods include: **dal, eggs, paneer, chicken, fish, curd, sprouts, and soya**. Aim for {protein}g protein daily based on your profile.",
        "For your goal, focus on these protein sources: **moong dal (24g/100g), eggs (13g each), paneer (18g/100g), chicken breast (31g/100g)**. Include protein in every meal!",
        "Top vegetarian proteins: **Rajma, chole, moong, toor dal, paneer, tofu, curd, and peanuts**. Try to spread your protein intake across all meals for best results.",
    ],
    'calorie': [
        "Based on your profile, your daily calorie target is approximately **{calories} kcal**. This is calculated using the Harris-Benedict formula adjusted for your activity level and goal.",
        "Your estimated daily calorie need is **{calories} kcal**. To track easily: breakfast ~{b}kcal, lunch ~{l}kcal, dinner ~{d}kcal, snacks ~{s}kcal.",
        "Calorie targets vary by goal. Yours is **{calories} kcal/day**. Focus on food quality — not just quantity. Whole foods keep you full longer!",
    ],
    'weight': [
        "For sustainable weight loss: **500 calorie deficit per day** = ~0.5kg loss/week. Don't go below 1200 kcal. Focus on protein, fibre, and staying hydrated.",
        "Weight loss tips: Eat slowly, use smaller plates, start meals with water and salad, avoid liquid calories (juice, chai with sugar), and sleep 7-8 hours.",
        "The best diet for weight loss is one you can stick to! Focus on whole foods, reduce oil & sugar, eat more vegetables, and be consistent.",
    ],
    'breakfast': [
        "Great Indian breakfasts: **Poha, Upma, Idli-Sambar, Besan Chilla, Oats porridge, Eggs, or Sprouts salad**. Include protein in your breakfast to stay full till lunch.",
        "A balanced breakfast has protein + complex carbs + some fat. Try: **2 eggs + 1 roti** or **Oats + milk + nuts** or **Besan chilla + curd**.",
        "Never skip breakfast! It boosts metabolism and reduces overeating later. Aim for 300-400 kcal in the morning with good protein.",
    ],
    'lunch': [
        "A balanced Indian lunch: **Dal + roti/rice + sabzi + salad + curd**. This gives you protein, carbs, fibre, and probiotics in one meal!",
        "For a filling lunch: fill **half your plate with vegetables**, quarter with protein (dal/chicken), and quarter with carbs (roti/rice). Add curd for probiotics.",
        "Good lunch options: **Rajma chawal, Dal roti sabzi, Chole bhature (once a week), Paneer curry + roti, or Brown rice + dal + greens**.",
    ],
    'dinner': [
        "Dinner should be your lightest meal. Try: **Khichdi, Light dal + 1-2 rotis, Grilled chicken salad, or Vegetable soup + toast**. Eat 2-3 hours before sleeping.",
        "For better digestion and sleep: keep dinner light and eat by 8pm. Good options: **Moong dal khichdi, Sabzi + roti, or Grilled protein + salad**.",
        "Avoid heavy, fried, or sugary foods at dinner. Your body slows down at night — lighter meals mean better sleep and less fat storage.",
    ],
    'water': [
        "Drink **{water}ml of water daily** — that's about {glasses} glasses. Start your day with a glass of warm water, drink before each meal, and sip throughout the day.",
        "Hydration tips: Water aids digestion, metabolism, and skin health. Add lemon, mint, or cucumber to make it more appealing. Avoid sugary drinks!",
        "Signs of dehydration: fatigue, headache, dark urine, and hunger (thirst is often mistaken for hunger!). Keep a water bottle handy at all times.",
    ],
    'snack': [
        "Healthy Indian snacks: **Roasted chana, Makhana, Sprouts, Fruits + nuts, Curd, Buttermilk, Dhokla, or Carrot sticks with hummus**.",
        "Best pre-workout snack: banana + peanut butter. Best post-workout: curd or protein shake. For evening: nuts + fruit or buttermilk.",
        "Avoid: chips, namkeen, biscuits, and fried snacks. These are high in sodium, trans fats, and empty calories. Choose whole food snacks instead.",
    ],
    'diabetes': [
        "Diabetic-friendly eating: Choose **low-GI foods** (oats, barley, ragi, brown rice), eat 5-6 small meals, avoid white rice/maida/sugar, and include bitter foods (karela, methi).",
        "For blood sugar control: pair carbs with protein and fibre to slow absorption. Try: **dal + roti** instead of plain rice. Walk 10 minutes after meals.",
        "Key diabetic superfoods: **Karela, Methi, Jamun, Amla, Cinnamon, Turmeric, Oats, and Legumes**. Monitor your blood sugar regularly.",
    ],
    'exercise': [
        "Diet + exercise is the best combo! For weight loss: **cardio 3-4x/week + strength training 2-3x/week**. Exercise boosts metabolism and muscle mass.",
        "You don't need a gym! Walking 10,000 steps/day, yoga, cycling, or home bodyweight exercises are all very effective.",
        "Best time to eat around exercise: eat a light snack 1 hour before (banana/toast), and protein within 30 min after (eggs/curd/whey protein).",
    ],
    'default': [
        "That's a great nutrition question! In general: focus on **whole foods, balanced macros, adequate hydration, and consistency**. Small daily habits create big results over time.",
        "My top nutrition advice: eat more vegetables, reduce processed foods, drink enough water, don't skip meals, and sleep well. These basics cover 80% of your health goals!",
        "For personalized advice, always consult a registered dietitian. But as a general rule: **eat real food, not too much, mostly plants** — and stay consistent!",
    ],
}

KEYWORDS = {
    'protein': ['protein', 'protien', 'muscle', 'amino', 'paneer', 'dal', 'egg', 'chicken'],
    'calorie': ['calori', 'kcal', 'calorie', 'how much to eat', 'energy', 'intake'],
    'weight': ['weight loss', 'lose weight', 'fat', 'slim', 'reduce weight', 'wajan', 'motapa'],
    'breakfast': ['breakfast', 'morning', 'nashta', 'subah'],
    'lunch': ['lunch', 'afternoon', 'dopahar', 'midday'],
    'dinner': ['dinner', 'night', 'raat', 'evening meal', 'supper'],
    'water': ['water', 'hydrat', 'pani', 'drink', 'thirst'],
    'snack': ['snack', 'namkeen', 'munchies', 'between meals', 'hunger', 'bhuook'],
    'diabetes': ['diabet', 'sugar', 'blood sugar', 'insulin', 'glucose', 'madhumeh'],
    'exercise': ['exercise', 'workout', 'gym', 'walk', 'yoga', 'run', 'fitness', 'vyayam'],
}


@login_required
@csrf_exempt
def ai_chat_api(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)

    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').lower()

        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        calories = calculate_calories(profile)
        water_ml = round((profile.weight_kg or 70) * 35)

        _, protein_g, _, _ = (0, 0, 0, 0)
        if calories:
            goal = profile.goal or 'maintain'
            prot_r = {'lose_weight': 0.25, 'gain_muscle': 0.30, 'maintain': 0.25}.get(goal, 0.25)
            protein_g = round(calories * prot_r / 4)

        # Match keyword
        matched_key = 'default'
        for key, kws in KEYWORDS.items():
            if any(kw in user_message for kw in kws):
                matched_key = key
                break

        templates = CHAT_RESPONSES[matched_key]
        reply = random.choice(templates)

        # Fill template placeholders
        b = round(calories * 0.25)
        l = round(calories * 0.35)
        d = round(calories * 0.25)
        s = round(calories * 0.15)
        reply = reply.format(
            calories=calories,
            protein=protein_g,
            water=water_ml,
            glasses=round(water_ml / 250),
            b=b, l=l, d=d, s=s,
        )

        return JsonResponse({'reply': reply})
    except Exception as e:
        return JsonResponse({'reply': 'Sorry, something went wrong. Please try again!'}, status=200)

# ─── Workout Planner ────────────────────────────────────────────────────────────

WORKOUT_DB = {
    'lose_weight': {
        'label': 'Fat Loss',
        'color': '#e63946',
        'icon': '🔥',
        'weekly_plan': [
            {
                'day': 'Monday',
                'focus': 'Full Body Cardio',
                'icon': '🏃',
                'duration': '45 min',
                'intensity': 'Moderate',
                'exercises': [
                    {'name': 'Brisk Walking / Jogging', 'sets': '1', 'reps': '20 min', 'rest': '—', 'cal': 180, 'tip': 'Maintain pace where you can talk but feel breathless'},
                    {'name': 'Jumping Jacks', 'sets': '3', 'reps': '30', 'rest': '30s', 'cal': 30, 'tip': 'Land softly to protect knees'},
                    {'name': 'Bodyweight Squats', 'sets': '3', 'reps': '15', 'rest': '45s', 'cal': 25, 'tip': 'Keep knees behind toes'},
                    {'name': 'Push-ups (or knee push-ups)', 'sets': '3', 'reps': '10–12', 'rest': '45s', 'cal': 20, 'tip': 'Keep core tight throughout'},
                    {'name': 'Mountain Climbers', 'sets': '3', 'reps': '20 each leg', 'rest': '30s', 'cal': 35, 'tip': 'Drive knees towards chest quickly'},
                    {'name': 'Cool Down Stretch', 'sets': '1', 'reps': '5 min', 'rest': '—', 'cal': 10, 'tip': 'Hold each stretch 20–30 seconds'},
                ]
            },
            {
                'day': 'Tuesday',
                'focus': 'Active Rest / Yoga',
                'icon': '🧘',
                'duration': '30 min',
                'intensity': 'Low',
                'exercises': [
                    {'name': 'Surya Namaskar (Sun Salutation)', 'sets': '5', 'reps': 'rounds', 'rest': '30s', 'cal': 60, 'tip': 'Sync breath with each movement'},
                    {'name': 'Cat-Cow Stretch', 'sets': '2', 'reps': '10', 'rest': '—', 'cal': 5, 'tip': 'Slow and controlled'},
                    {'name': 'Child\'s Pose', 'sets': '2', 'reps': '30s hold', 'rest': '—', 'cal': 3, 'tip': 'Breathe deeply into your back'},
                    {'name': 'Leg Raises', 'sets': '3', 'reps': '12', 'rest': '30s', 'cal': 20, 'tip': 'Keep lower back pressed to floor'},
                    {'name': 'Seated Forward Bend', 'sets': '2', 'reps': '30s hold', 'rest': '—', 'cal': 5, 'tip': 'Don\'t force — go to your comfortable limit'},
                ]
            },
            {
                'day': 'Wednesday',
                'focus': 'HIIT Training',
                'icon': '⚡',
                'duration': '30 min',
                'intensity': 'High',
                'exercises': [
                    {'name': 'Warm Up Jog in Place', 'sets': '1', 'reps': '5 min', 'rest': '—', 'cal': 40, 'tip': 'Gradually increase pace'},
                    {'name': 'Burpees', 'sets': '4', 'reps': '10', 'rest': '45s', 'cal': 60, 'tip': 'Most effective fat-burning exercise!'},
                    {'name': 'High Knees', 'sets': '4', 'reps': '30s', 'rest': '30s', 'cal': 40, 'tip': 'Pump arms for extra calorie burn'},
                    {'name': 'Jump Squats', 'sets': '3', 'reps': '12', 'rest': '45s', 'cal': 35, 'tip': 'Land softly bending knees'},
                    {'name': 'Plank Hold', 'sets': '3', 'reps': '30–45s', 'rest': '30s', 'cal': 15, 'tip': 'Don\'t let hips sag'},
                    {'name': 'Cool Down Walk', 'sets': '1', 'reps': '5 min', 'rest': '—', 'cal': 20, 'tip': 'Slow your heart rate gradually'},
                ]
            },
            {
                'day': 'Thursday',
                'focus': 'Rest Day',
                'icon': '😴',
                'duration': '—',
                'intensity': 'Rest',
                'exercises': [
                    {'name': 'Light Walk', 'sets': '1', 'reps': '20–30 min', 'rest': '—', 'cal': 100, 'tip': 'Gentle movement aids recovery'},
                    {'name': 'Foam Rolling / Self Massage', 'sets': '1', 'reps': '10 min', 'rest': '—', 'cal': 10, 'tip': 'Focus on tight areas (quads, calves, back)'},
                    {'name': 'Deep Breathing / Meditation', 'sets': '1', 'reps': '10 min', 'rest': '—', 'cal': 5, 'tip': 'Reduces cortisol — important for fat loss'},
                ]
            },
            {
                'day': 'Friday',
                'focus': 'Lower Body + Core',
                'icon': '🦵',
                'duration': '40 min',
                'intensity': 'Moderate-High',
                'exercises': [
                    {'name': 'Sumo Squats', 'sets': '4', 'reps': '15', 'rest': '45s', 'cal': 35, 'tip': 'Wide stance, toes pointing out'},
                    {'name': 'Reverse Lunges', 'sets': '3', 'reps': '12 each leg', 'rest': '45s', 'cal': 30, 'tip': 'Keep front knee over ankle'},
                    {'name': 'Glute Bridges', 'sets': '4', 'reps': '20', 'rest': '30s', 'cal': 25, 'tip': 'Squeeze glutes at the top'},
                    {'name': 'Bicycle Crunches', 'sets': '3', 'reps': '20 each side', 'rest': '30s', 'cal': 20, 'tip': 'Slow and controlled — feel the obliques'},
                    {'name': 'Plank to Downward Dog', 'sets': '3', 'reps': '10', 'rest': '30s', 'cal': 20, 'tip': 'Full body engagement'},
                    {'name': 'Wall Sit', 'sets': '3', 'reps': '30–45s', 'rest': '45s', 'cal': 20, 'tip': 'Thighs parallel to floor'},
                ]
            },
            {
                'day': 'Saturday',
                'focus': 'Cardio + Upper Body',
                'icon': '💪',
                'duration': '45 min',
                'intensity': 'Moderate',
                'exercises': [
                    {'name': 'Cycling / Skipping Rope', 'sets': '1', 'reps': '15 min', 'rest': '—', 'cal': 140, 'tip': 'Skipping burns ~10 cal/min!'},
                    {'name': 'Diamond Push-ups', 'sets': '3', 'reps': '10', 'rest': '45s', 'cal': 20, 'tip': 'Hands close together — targets triceps'},
                    {'name': 'Tricep Dips (using chair)', 'sets': '3', 'reps': '12', 'rest': '45s', 'cal': 20, 'tip': 'Keep elbows pointing back'},
                    {'name': 'Superman Hold', 'sets': '3', 'reps': '10', 'rest': '30s', 'cal': 15, 'tip': 'Strengthens lower back'},
                    {'name': 'Side Plank', 'sets': '3', 'reps': '20s each side', 'rest': '30s', 'cal': 10, 'tip': 'Stack feet or stagger for easier version'},
                ]
            },
            {
                'day': 'Sunday',
                'focus': 'Complete Rest',
                'icon': '🌿',
                'duration': '—',
                'intensity': 'Rest',
                'exercises': [
                    {'name': 'Leisurely Walk (optional)', 'sets': '1', 'reps': '20 min', 'rest': '—', 'cal': 80, 'tip': 'Enjoy nature — mental health matters too!'},
                    {'name': 'Stretching Routine', 'sets': '1', 'reps': '15 min', 'rest': '—', 'cal': 15, 'tip': 'Full body flexibility maintenance'},
                ]
            },
        ],
        'tips': [
            '🔥 Combine cardio with strength training for best fat loss results',
            '🍽️ Eat a light snack 1hr before workout (banana or toast)',
            '💧 Drink water before, during, and after exercise',
            '😴 Sleep 7–8 hours — poor sleep increases fat-storing hormones',
            '📅 Consistency beats intensity — show up every week!',
        ],
        'weekly_calories': 1800,
    },

    'gain_muscle': {
        'label': 'Muscle Building',
        'color': '#f4a261',
        'icon': '💪',
        'weekly_plan': [
            {
                'day': 'Monday',
                'focus': 'Chest + Triceps',
                'icon': '🏋️',
                'duration': '50 min',
                'intensity': 'High',
                'exercises': [
                    {'name': 'Push-ups (Progressive)', 'sets': '4', 'reps': '12–15', 'rest': '60s', 'cal': 40, 'tip': 'Increase reps weekly — aim for 20+ before adding difficulty'},
                    {'name': 'Wide Push-ups', 'sets': '3', 'reps': '12', 'rest': '60s', 'cal': 30, 'tip': 'Wider grip targets chest more'},
                    {'name': 'Pike Push-ups', 'sets': '3', 'reps': '10', 'rest': '60s', 'cal': 25, 'tip': 'Mimics overhead press — great for shoulders'},
                    {'name': 'Tricep Dips', 'sets': '4', 'reps': '12', 'rest': '60s', 'cal': 25, 'tip': 'Use two chairs or a stable bench'},
                    {'name': 'Diamond Push-ups', 'sets': '3', 'reps': '10', 'rest': '60s', 'cal': 20, 'tip': 'Best bodyweight tricep exercise'},
                    {'name': 'Plank Hold', 'sets': '3', 'reps': '45s', 'rest': '30s', 'cal': 15, 'tip': 'Engage core — do not hold breath'},
                ]
            },
            {
                'day': 'Tuesday',
                'focus': 'Back + Biceps',
                'icon': '🦾',
                'duration': '50 min',
                'intensity': 'High',
                'exercises': [
                    {'name': 'Pull-ups / Chin-ups', 'sets': '4', 'reps': '6–10', 'rest': '90s', 'cal': 40, 'tip': 'Best back exercise! Use a door bar or park bar'},
                    {'name': 'Inverted Rows (under table)', 'sets': '3', 'reps': '12', 'rest': '60s', 'cal': 30, 'tip': 'Keep body straight like a plank'},
                    {'name': 'Superman Back Extension', 'sets': '4', 'reps': '15', 'rest': '45s', 'cal': 20, 'tip': 'Hold for 2 seconds at top'},
                    {'name': 'Resistance Band Bicep Curl', 'sets': '4', 'reps': '12', 'rest': '60s', 'cal': 20, 'tip': 'Slow on the way down (eccentric) for more growth'},
                    {'name': 'Hammer Curl (resistance band)', 'sets': '3', 'reps': '12', 'rest': '60s', 'cal': 15, 'tip': 'Palms facing each other'},
                ]
            },
            {
                'day': 'Wednesday',
                'focus': 'Legs + Glutes',
                'icon': '🦵',
                'duration': '55 min',
                'intensity': 'High',
                'exercises': [
                    {'name': 'Bulgarian Split Squats', 'sets': '4', 'reps': '10 each', 'rest': '75s', 'cal': 50, 'tip': 'Rear foot elevated — most effective leg exercise!'},
                    {'name': 'Jump Squats', 'sets': '3', 'reps': '12', 'rest': '60s', 'cal': 40, 'tip': 'Explode upward, land softly'},
                    {'name': 'Single Leg Romanian Deadlift', 'sets': '3', 'reps': '10 each', 'rest': '60s', 'cal': 30, 'tip': 'Hinge at hip — targets hamstrings'},
                    {'name': 'Glute Bridge (weighted)', 'sets': '4', 'reps': '15', 'rest': '45s', 'cal': 25, 'tip': 'Place a backpack on hips for resistance'},
                    {'name': 'Calf Raises', 'sets': '4', 'reps': '20', 'rest': '30s', 'cal': 20, 'tip': 'Do on a step for full range of motion'},
                    {'name': 'Wall Sit', 'sets': '3', 'reps': '45s', 'rest': '45s', 'cal': 20, 'tip': 'Thighs parallel to floor'},
                ]
            },
            {
                'day': 'Thursday',
                'focus': 'Active Recovery',
                'icon': '🧘',
                'duration': '25 min',
                'intensity': 'Low',
                'exercises': [
                    {'name': 'Light Yoga / Stretching', 'sets': '1', 'reps': '20 min', 'rest': '—', 'cal': 50, 'tip': 'Focus on muscles worked this week'},
                    {'name': 'Foam Rolling', 'sets': '1', 'reps': '10 min', 'rest': '—', 'cal': 10, 'tip': 'Aids recovery and reduces soreness'},
                ]
            },
            {
                'day': 'Friday',
                'focus': 'Shoulders + Core',
                'icon': '🎯',
                'duration': '50 min',
                'intensity': 'High',
                'exercises': [
                    {'name': 'Pike Push-ups (slow)', 'sets': '4', 'reps': '12', 'rest': '60s', 'cal': 30, 'tip': 'The bodyweight overhead press'},
                    {'name': 'Lateral Raises (water bottles)', 'sets': '4', 'reps': '15', 'rest': '45s', 'cal': 20, 'tip': 'Arms slightly bent, raise to shoulder height'},
                    {'name': 'Front Raises', 'sets': '3', 'reps': '12', 'rest': '45s', 'cal': 15, 'tip': 'Controlled movement — no swinging'},
                    {'name': 'Plank Shoulder Taps', 'sets': '3', 'reps': '20 each', 'rest': '30s', 'cal': 20, 'tip': 'Minimize hip rotation'},
                    {'name': 'Russian Twists', 'sets': '4', 'reps': '20 each side', 'rest': '30s', 'cal': 25, 'tip': 'Lean back 45° for best effect'},
                    {'name': 'Hanging Knee Raises', 'sets': '3', 'reps': '12', 'rest': '45s', 'cal': 20, 'tip': 'Use a pull-up bar — amazing for abs'},
                ]
            },
            {
                'day': 'Saturday',
                'focus': 'Full Body Compound',
                'icon': '🏆',
                'duration': '55 min',
                'intensity': 'High',
                'exercises': [
                    {'name': 'Burpee Pull-ups', 'sets': '4', 'reps': '8', 'rest': '90s', 'cal': 60, 'tip': 'Combines full body cardio + pull strength'},
                    {'name': 'Squat to Press (water bottles)', 'sets': '4', 'reps': '12', 'rest': '60s', 'cal': 40, 'tip': 'Squat down, press up as you stand'},
                    {'name': 'Renegade Rows', 'sets': '3', 'reps': '8 each', 'rest': '60s', 'cal': 30, 'tip': 'In plank position, alternate rowing'},
                    {'name': 'Pistol Squat (assisted)', 'sets': '3', 'reps': '6 each', 'rest': '75s', 'cal': 30, 'tip': 'Hold doorframe for balance if needed'},
                    {'name': 'L-Sit (between chairs)', 'sets': '3', 'reps': '15s', 'rest': '60s', 'cal': 15, 'tip': 'Advanced core + shoulder exercise'},
                ]
            },
            {
                'day': 'Sunday',
                'focus': 'Complete Rest',
                'icon': '🌿',
                'duration': '—',
                'intensity': 'Rest',
                'exercises': [
                    {'name': 'Protein-rich meal focus', 'sets': '—', 'reps': '—', 'rest': '—', 'cal': 0, 'tip': 'Rest day nutrition is as important as workout days'},
                    {'name': 'Light stretching (optional)', 'sets': '1', 'reps': '15 min', 'rest': '—', 'cal': 15, 'tip': 'Maintain flexibility for next week'},
                ]
            },
        ],
        'tips': [
            '💪 Progressive overload — add reps or difficulty every week',
            '🍗 Eat protein within 30 min post-workout for muscle repair',
            '😴 Muscles grow during sleep — 7–9 hours is essential',
            '💧 Drink 3–4 litres of water on training days',
            '⏳ Be patient — visible muscle takes 8–12 weeks of consistency',
        ],
        'weekly_calories': 2200,
    },

    'maintain': {
        'label': 'Maintenance & Fitness',
        'color': '#4361ee',
        'icon': '⚖️',
        'weekly_plan': [
            {'day': 'Monday', 'focus': 'Cardio + Core', 'icon': '🏃', 'duration': '40 min', 'intensity': 'Moderate',
             'exercises': [
                 {'name': 'Jogging / Brisk Walk', 'sets': '1', 'reps': '20 min', 'rest': '—', 'cal': 160, 'tip': 'Maintain a steady comfortable pace'},
                 {'name': 'Plank', 'sets': '3', 'reps': '45s', 'rest': '30s', 'cal': 15, 'tip': 'Keep hips level'},
                 {'name': 'Crunches', 'sets': '3', 'reps': '20', 'rest': '30s', 'cal': 15, 'tip': 'Lift shoulders, not neck'},
                 {'name': 'Leg Raises', 'sets': '3', 'reps': '15', 'rest': '30s', 'cal': 15, 'tip': 'Slow and controlled'},
             ]},
            {'day': 'Tuesday', 'focus': 'Upper Body', 'icon': '💪', 'duration': '40 min', 'intensity': 'Moderate',
             'exercises': [
                 {'name': 'Push-ups', 'sets': '3', 'reps': '15', 'rest': '45s', 'cal': 30, 'tip': 'Full range of motion'},
                 {'name': 'Tricep Dips', 'sets': '3', 'reps': '12', 'rest': '45s', 'cal': 20, 'tip': 'Keep elbows pointed back'},
                 {'name': 'Pull-ups or Rows', 'sets': '3', 'reps': '10', 'rest': '60s', 'cal': 25, 'tip': 'Squeeze back at top'},
                 {'name': 'Shoulder Press (bottles)', 'sets': '3', 'reps': '12', 'rest': '45s', 'cal': 20, 'tip': 'Don\'t lock elbows at top'},
             ]},
            {'day': 'Wednesday', 'focus': 'Yoga / Flexibility', 'icon': '🧘', 'duration': '30 min', 'intensity': 'Low',
             'exercises': [
                 {'name': 'Surya Namaskar', 'sets': '5', 'reps': 'rounds', 'rest': '30s', 'cal': 60, 'tip': 'Morning practice is most beneficial'},
                 {'name': 'Warrior Pose', 'sets': '2', 'reps': '30s each side', 'rest': '—', 'cal': 10, 'tip': 'Hold for balance and strength'},
                 {'name': 'Downward Dog', 'sets': '3', 'reps': '30s', 'rest': '—', 'cal': 8, 'tip': 'Push heels toward floor'},
             ]},
            {'day': 'Thursday', 'focus': 'Lower Body', 'icon': '🦵', 'duration': '40 min', 'intensity': 'Moderate',
             'exercises': [
                 {'name': 'Squats', 'sets': '4', 'reps': '15', 'rest': '45s', 'cal': 35, 'tip': 'Parallel or below parallel'},
                 {'name': 'Lunges', 'sets': '3', 'reps': '12 each', 'rest': '45s', 'cal': 30, 'tip': 'Step forward far enough'},
                 {'name': 'Glute Bridge', 'sets': '3', 'reps': '20', 'rest': '30s', 'cal': 20, 'tip': 'Squeeze at the top'},
                 {'name': 'Calf Raises', 'sets': '3', 'reps': '20', 'rest': '30s', 'cal': 15, 'tip': 'Full range on a step'},
             ]},
            {'day': 'Friday', 'focus': 'HIIT', 'icon': '⚡', 'duration': '30 min', 'intensity': 'High',
             'exercises': [
                 {'name': 'Burpees', 'sets': '3', 'reps': '10', 'rest': '45s', 'cal': 50, 'tip': 'Full effort for full benefit'},
                 {'name': 'High Knees', 'sets': '3', 'reps': '30s', 'rest': '30s', 'cal': 35, 'tip': 'Pump arms to go faster'},
                 {'name': 'Jump Squats', 'sets': '3', 'reps': '12', 'rest': '45s', 'cal': 30, 'tip': 'Explode and land softly'},
                 {'name': 'Mountain Climbers', 'sets': '3', 'reps': '20 each', 'rest': '30s', 'cal': 25, 'tip': 'Keep hips low'},
             ]},
            {'day': 'Saturday', 'focus': 'Outdoor Activity', 'icon': '🚴', 'duration': '45 min', 'intensity': 'Moderate',
             'exercises': [
                 {'name': 'Cycling / Swimming / Sport', 'sets': '1', 'reps': '30–45 min', 'rest': '—', 'cal': 250, 'tip': 'Do what you enjoy — fun = consistency'},
                 {'name': 'Cool Down Stretch', 'sets': '1', 'reps': '10 min', 'rest': '—', 'cal': 15, 'tip': 'Post-activity stretch prevents stiffness'},
             ]},
            {'day': 'Sunday', 'focus': 'Rest', 'icon': '🌿', 'duration': '—', 'intensity': 'Rest',
             'exercises': [
                 {'name': 'Complete Rest or Light Walk', 'sets': '1', 'reps': '20 min', 'rest': '—', 'cal': 60, 'tip': 'Let your body fully recover'},
             ]},
        ],
        'tips': [
            '⚖️ Mix cardio + strength for balanced fitness',
            '🧘 Include yoga/flexibility work to prevent injury',
            '🎯 Try a new sport or activity each month to stay motivated',
            '💧 Hydrate well — even mild dehydration reduces performance by 10%',
            '📊 Track workouts to see progress over time',
        ],
        'weekly_calories': 1500,
    },

    'improve_health': {
        'label': 'Health & Wellness',
        'color': '#52b788',
        'icon': '🌿',
        'weekly_plan': [
            {'day': 'Monday', 'focus': 'Morning Walk + Stretching', 'icon': '🌅', 'duration': '35 min', 'intensity': 'Low',
             'exercises': [
                 {'name': 'Brisk Morning Walk', 'sets': '1', 'reps': '25 min', 'rest': '—', 'cal': 120, 'tip': 'Morning walk boosts metabolism all day'},
                 {'name': 'Full Body Stretch', 'sets': '1', 'reps': '10 min', 'rest': '—', 'cal': 15, 'tip': 'Hold each stretch 20–30 seconds'},
             ]},
            {'day': 'Tuesday', 'focus': 'Yoga for Health', 'icon': '🧘', 'duration': '40 min', 'intensity': 'Low-Moderate',
             'exercises': [
                 {'name': 'Surya Namaskar', 'sets': '8', 'reps': 'rounds', 'rest': '30s', 'cal': 90, 'tip': 'Best all-round health exercise in yoga'},
                 {'name': 'Bhujangasana (Cobra)', 'sets': '3', 'reps': '30s', 'rest': '—', 'cal': 8, 'tip': 'Strengthens spine, opens chest'},
                 {'name': 'Vrikshasana (Tree Pose)', 'sets': '3', 'reps': '30s each', 'rest': '—', 'cal': 8, 'tip': 'Improves balance and focus'},
                 {'name': 'Anulom Vilom Pranayama', 'sets': '1', 'reps': '10 min', 'rest': '—', 'cal': 5, 'tip': 'Reduces stress and blood pressure'},
             ]},
            {'day': 'Wednesday', 'focus': 'Light Cardio', 'icon': '🚶', 'duration': '35 min', 'intensity': 'Low-Moderate',
             'exercises': [
                 {'name': 'Walking / Light Jogging', 'sets': '1', 'reps': '30 min', 'rest': '—', 'cal': 150, 'tip': '10,000 steps/day = excellent heart health'},
                 {'name': 'Deep Breathing', 'sets': '1', 'reps': '5 min', 'rest': '—', 'cal': 5, 'tip': 'Box breathing: in 4s, hold 4s, out 4s'},
             ]},
            {'day': 'Thursday', 'focus': 'Strength for Seniors/Beginners', 'icon': '💪', 'duration': '35 min', 'intensity': 'Low',
             'exercises': [
                 {'name': 'Chair Squats', 'sets': '3', 'reps': '12', 'rest': '60s', 'cal': 20, 'tip': 'Sit down and stand up from chair — builds leg strength'},
                 {'name': 'Wall Push-ups', 'sets': '3', 'reps': '15', 'rest': '45s', 'cal': 15, 'tip': 'Easier than floor push-ups — great starting point'},
                 {'name': 'Standing Calf Raises', 'sets': '3', 'reps': '20', 'rest': '30s', 'cal': 15, 'tip': 'Improves circulation in legs'},
                 {'name': 'Seated Leg Extensions', 'sets': '3', 'reps': '15', 'rest': '30s', 'cal': 10, 'tip': 'Strengthens knees and quads'},
             ]},
            {'day': 'Friday', 'focus': 'Meditation + Walk', 'icon': '🧠', 'duration': '40 min', 'intensity': 'Low',
             'exercises': [
                 {'name': 'Evening Walk', 'sets': '1', 'reps': '25 min', 'rest': '—', 'cal': 100, 'tip': 'After-dinner walk helps blood sugar control'},
                 {'name': 'Guided Meditation', 'sets': '1', 'reps': '10 min', 'rest': '—', 'cal': 5, 'tip': 'Use apps like Headspace or YouTube for guidance'},
                 {'name': 'Kapalabhati Pranayama', 'sets': '1', 'reps': '5 min', 'rest': '—', 'cal': 8, 'tip': 'Powerful breathing exercise — improves lung capacity'},
             ]},
            {'day': 'Saturday', 'focus': 'Outdoor Fun', 'icon': '🌳', 'duration': '45 min', 'intensity': 'Moderate',
             'exercises': [
                 {'name': 'Nature Walk / Hiking', 'sets': '1', 'reps': '40 min', 'rest': '—', 'cal': 200, 'tip': 'Being in nature reduces stress hormones significantly'},
                 {'name': 'Stretching', 'sets': '1', 'reps': '5 min', 'rest': '—', 'cal': 10, 'tip': 'Cool down after activity'},
             ]},
            {'day': 'Sunday', 'focus': 'Rest & Reflection', 'icon': '🌿', 'duration': '—', 'intensity': 'Rest',
             'exercises': [
                 {'name': 'Rest fully', 'sets': '—', 'reps': '—', 'rest': '—', 'cal': 0, 'tip': 'Physical and mental rest is equally important'},
             ]},
        ],
        'tips': [
            '🌿 Even 30 min of walking daily dramatically improves health',
            '🧘 Yoga + pranayama reduce stress which causes 80% of modern diseases',
            '😴 Quality sleep is the most underrated health habit',
            '🤸 Flexibility training prevents falls and injuries as you age',
            '❤️ Exercise is the best medicine — it improves every health marker',
        ],
        'weekly_calories': 1200,
    },

    'manage_condition': {
        'label': 'Therapeutic Exercise',
        'color': '#9b59b6',
        'icon': '🏥',
        'weekly_plan': [
            {'day': 'Monday', 'focus': 'Gentle Walk + Breathing', 'icon': '🚶', 'duration': '30 min', 'intensity': 'Low',
             'exercises': [
                 {'name': 'Post-Meal Walk (after lunch)', 'sets': '1', 'reps': '15 min', 'rest': '—', 'cal': 60, 'tip': 'Walking after meals lowers blood sugar by 20–30%'},
                 {'name': 'Diaphragmatic Breathing', 'sets': '1', 'reps': '10 min', 'rest': '—', 'cal': 5, 'tip': 'Reduces blood pressure and stress hormones'},
                 {'name': 'Gentle Neck & Shoulder Rolls', 'sets': '2', 'reps': '10 each', 'rest': '—', 'cal': 3, 'tip': 'Relieves tension headaches'},
             ]},
            {'day': 'Tuesday', 'focus': 'Chair Exercises', 'icon': '🪑', 'duration': '30 min', 'intensity': 'Low',
             'exercises': [
                 {'name': 'Seated Marching', 'sets': '3', 'reps': '20 each', 'rest': '30s', 'cal': 20, 'tip': 'Lifts knees alternately — great low-impact cardio'},
                 {'name': 'Seated Leg Extensions', 'sets': '3', 'reps': '15', 'rest': '30s', 'cal': 15, 'tip': 'Strengthens quads — helps with knee pain'},
                 {'name': 'Seated Side Bends', 'sets': '2', 'reps': '10 each', 'rest': '—', 'cal': 8, 'tip': 'Stretches obliques and reduces back tension'},
                 {'name': 'Ankle Rotations', 'sets': '2', 'reps': '10 each', 'rest': '—', 'cal': 3, 'tip': 'Improves circulation in feet and ankles'},
             ]},
            {'day': 'Wednesday', 'focus': 'Yoga Therapy', 'icon': '🧘', 'duration': '35 min', 'intensity': 'Low',
             'exercises': [
                 {'name': 'Anulom Vilom (Alternate Nostril)', 'sets': '1', 'reps': '10 min', 'rest': '—', 'cal': 5, 'tip': 'Proven to reduce blood pressure and anxiety'},
                 {'name': 'Shavasana (Relaxation)', 'sets': '1', 'reps': '10 min', 'rest': '—', 'cal': 3, 'tip': 'Complete body relaxation — reduces cortisol'},
                 {'name': 'Gentle Cat-Cow', 'sets': '2', 'reps': '10', 'rest': '—', 'cal': 5, 'tip': 'Aids digestion and back pain relief'},
                 {'name': 'Supported Child\'s Pose', 'sets': '2', 'reps': '1 min', 'rest': '—', 'cal': 5, 'tip': 'Calming — good for anxiety'},
             ]},
            {'day': 'Thursday', 'focus': 'Water Walk / Light Activity', 'icon': '💧', 'duration': '30 min', 'intensity': 'Low',
             'exercises': [
                 {'name': 'Walking (flat ground)', 'sets': '1', 'reps': '25 min', 'rest': '—', 'cal': 100, 'tip': 'Gentle on joints — great for diabetes and BP'},
                 {'name': 'Heel-Toe Raise', 'sets': '3', 'reps': '15', 'rest': '30s', 'cal': 10, 'tip': 'Improves balance and foot circulation'},
             ]},
            {'day': 'Friday', 'focus': 'Meditation + Stretching', 'icon': '🧠', 'duration': '35 min', 'intensity': 'Low',
             'exercises': [
                 {'name': 'Guided Meditation', 'sets': '1', 'reps': '15 min', 'rest': '—', 'cal': 5, 'tip': 'Regular meditation lowers HbA1c in diabetics'},
                 {'name': 'Full Body Gentle Stretch', 'sets': '1', 'reps': '15 min', 'rest': '—', 'cal': 20, 'tip': 'Hold each stretch, breathe deeply'},
                 {'name': 'Progressive Muscle Relaxation', 'sets': '1', 'reps': '10 min', 'rest': '—', 'cal': 5, 'tip': 'Tense and release each muscle group'},
             ]},
            {'day': 'Saturday', 'focus': 'Light Outdoor Walk', 'icon': '🌳', 'duration': '35 min', 'intensity': 'Low',
             'exercises': [
                 {'name': 'Leisurely Walk', 'sets': '1', 'reps': '30 min', 'rest': '—', 'cal': 100, 'tip': 'Fresh air and sunlight boost Vitamin D'},
                 {'name': 'Stretching', 'sets': '1', 'reps': '5 min', 'rest': '—', 'cal': 10, 'tip': 'Light post-walk stretching'},
             ]},
            {'day': 'Sunday', 'focus': 'Rest', 'icon': '🌿', 'duration': '—', 'intensity': 'Rest',
             'exercises': [
                 {'name': 'Complete Rest', 'sets': '—', 'reps': '—', 'rest': '—', 'cal': 0, 'tip': 'Allow your body to heal and recover'},
             ]},
        ],
        'tips': [
            '🏥 Always consult your doctor before starting any exercise program',
            '📊 Monitor blood sugar before and after exercise',
            '⚠️ Stop immediately if you feel chest pain, dizziness, or shortness of breath',
            '🚶 Even 10 min walks 3x per day can significantly improve health markers',
            '💊 Exercise can reduce medication needs over time — with doctor guidance',
        ],
        'weekly_calories': 800,
    },
}


@login_required
def workout(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    goal = profile.goal or 'maintain'

    # Map goal to workout plan
    plan_key = goal if goal in WORKOUT_DB else 'maintain'
    workout_plan = WORKOUT_DB[plan_key]

    # Calculate total weekly calories burned
    total_cal = sum(
        sum(ex.get('cal', 0) for ex in day['exercises'])
        for day in workout_plan['weekly_plan']
    )

    context = {
        'profile': profile,
        'workout_plan': workout_plan,
        'total_weekly_cal': total_cal,
        'goal_label': workout_plan['label'],
        'is_rest_days': json.dumps([d['intensity'] == 'Rest' for d in workout_plan['weekly_plan']]),
        'ex_counts': json.dumps([len(d['exercises']) for d in workout_plan['weekly_plan']]),
    }
    return render(request, 'diet/workout.html', context)
