# 🥗 NutriAI — AI-Powered Diet Planner

A full-stack Django web application with rule-based personalized diet plans and nutrition tracking.

---

## 🚀 Features

- **User Authentication** — Register, login, logout with full validation
- **Profile Setup** — Age, height, weight, activity level, goals, diet type, allergies, health conditions
- **BMI Calculator** — Auto-calculated with category (Underweight / Normal / Overweight / Obese)
- **Diet Plan Generator** — 7-day personalized meal plan generated using rule-based logic
- **Nutrition Coach (Chat)** — Interactive chatbot for diet & nutrition questions
- **Meal Logger** — Log breakfast, lunch, dinner, snacks with full macros
- **Calorie & Macro Tracker** — Daily totals with visual progress bars
- **Weight Tracker** — Log & visualize weight trend with Chart.js
- **Meal History** — Browse all logged meals by date
- **Admin Panel** — Django admin for full data management
- **SQLite Database** — Zero-config, production-ready with Django ORM

---

## 📦 Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.x + Django 4.2 |
| Database | SQLite (Django ORM) |
| Frontend | HTML5 + CSS3 + JavaScript |
| UI Framework | Bootstrap 5.3 |
| Charts | Chart.js 4.4 |
| Icons | Bootstrap Icons |
| Fonts | Google Fonts (Playfair Display + DM Sans) |

---

## ⚡ Quick Start

### 1. Clone / Extract Project
```bash
cd ai_diet_plan
```

### 2. Create Virtual Environment (Recommended)
```bash
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Setup Database & Run
```bash
python manage.py makemigrations diet
python manage.py migrate
python manage.py createsuperuser   # Optional: create admin
python manage.py runserver
```

Or simply run:
```bash
bash setup_and_run.sh
```

### 5. Open in Browser
- **App:** http://127.0.0.1:8000
- **Admin:** http://127.0.0.1:8000/admin

---

## 📁 Project Structure

```
ai_diet_plan/
├── ai_diet_plan/
│   ├── settings.py          # Django settings
│   ├── urls.py              # Main URL config
│   └── wsgi.py
├── diet/
│   ├── models.py            # UserProfile, DietPlan, MealLog, WeightLog
│   ├── views.py             # All views including plan generation
│   ├── forms.py             # Auth + profile + logging forms
│   ├── urls.py              # App URL patterns
│   └── admin.py             # Django admin
├── templates/
│   ├── base.html            # Sidebar layout + navigation
│   ├── registration/
│   │   ├── login.html
│   │   └── register.html
│   └── diet/
│       ├── dashboard.html   # Main dashboard with stats + charts
│       ├── setup_profile.html
│       ├── profile.html
│       ├── generate_plan.html
│       ├── view_plan.html
│       ├── my_plans.html
│       ├── log_meal.html
│       ├── meal_history.html
│       ├── log_weight.html
│       ├── weight_history.html
│       └── ai_chat.html     # Nutrition chat
├── manage.py
├── requirements.txt
└── setup_and_run.sh
```

---

## ⚙️ How Diet Plan Generation Works

The diet plan generator uses **rule-based logic** — no external API required:

- User profile data (age, weight, height, activity level, goal, diet type) is used to calculate daily calorie needs
- Meals are selected from a curated database of food items based on the user's diet type (Vegetarian, Vegan, Non-Vegetarian, etc.)
- Allergies and health conditions are factored in to filter out unsuitable foods
- A complete 7-day plan with breakfast, lunch, dinner, and snacks is generated instantly

---

## 👤 Default Admin Login
After running `setup_and_run.sh`:
- Username: `admin`
- Password: `admin123`

---

## 🎨 UI Highlights

- Responsive sidebar layout (collapses on mobile)
- Dark green + warm amber color scheme
- Playfair Display serif headings for elegance
- Smooth fade-in animations throughout
- Chart.js line charts for weight trends
- Print-friendly diet plan view

---

## 📝 License

MIT License — Free for personal and commercial use.
