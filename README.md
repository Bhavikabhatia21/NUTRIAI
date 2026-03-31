# 🥗 NutriAI — AI-Powered Diet Planner

A full-stack Django web application with AI-generated personalized diet plans 

---

## 🚀 Features

- **User Authentication** — Register, login, logout with full validation
- **Profile Setup** — Age, height, weight, activity level, goals, diet type, allergies, health conditions
- **BMI Calculator** — Auto-calculated with category (Underweight / Normal / Overweight / Obese)
- **AI Diet Plan Generator** — 7-day personalized meal plan via Claude API
- **AI Nutrition Coach (Chat)** — Real-time chatbot for diet & nutrition questions
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
| AI | Anthropic Claude API (claude-sonnet-4) |

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

### 4. Set Your Anthropic API Key
Open `ai_diet_plan/settings.py` and update:
```python
ANTHROPIC_API_KEY = 'sk-ant-your-key-here'
```

Or set as environment variable:
```bash
export ANTHROPIC_API_KEY='sk-ant-your-key-here'   # Linux/Mac
set ANTHROPIC_API_KEY=sk-ant-your-key-here         # Windows
```

Get your API key at: https://console.anthropic.com

### 5. Setup Database & Run
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

### 6. Open in Browser
- **App:** http://127.0.0.1:8000
- **Admin:** http://127.0.0.1:8000/admin

---

## 📁 Project Structure

```
ai_diet_plan/
├── ai_diet_plan/
│   ├── settings.py          # Django settings + API key
│   ├── urls.py              # Main URL config
│   └── wsgi.py
├── diet/
│   ├── models.py            # UserProfile, DietPlan, MealLog, WeightLog
│   ├── views.py             # All views including AI generation
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
│       └── ai_chat.html     # Real-time AI chat
├── manage.py
├── requirements.txt
└── setup_and_run.sh
```

---

## 🔑 API Key Configuration

The app uses the Anthropic Claude API for:
1. **Plan Generation** — Creates a full 7-day diet plan based on your profile
2. **AI Chat** — Answers nutrition questions with profile context

Without an API key, the UI still works fully — you just won't be able to generate AI plans or use chat.

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
- Real-time typing animation in AI chat
- Print-friendly diet plan view

---

## 📝 License

MIT License — Free for personal and commercial use.
