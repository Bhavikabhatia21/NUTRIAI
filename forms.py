from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import UserProfile, MealLog, WeightLog


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=50, required=True)
    last_name = forms.CharField(max_length=50, required=True)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'
            field.widget.attrs['autocomplete'] = 'off'
        self.fields['username'].widget.attrs['placeholder'] = 'Choose a username'
        self.fields['email'].widget.attrs['placeholder'] = 'Your email address'
        self.fields['first_name'].widget.attrs['placeholder'] = 'First name'
        self.fields['last_name'].widget.attrs['placeholder'] = 'Last name'
        self.fields['password1'].widget.attrs['placeholder'] = 'Create password'
        self.fields['password2'].widget.attrs['placeholder'] = 'Confirm password'

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Username'})
        self.fields['password'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Password'})


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['age', 'gender', 'height_cm', 'weight_kg', 'activity_level',
                  'goal', 'diet_type', 'allergies', 'health_conditions']
        widgets = {
            'age': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Your age', 'min': 10, 'max': 100}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'height_cm': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Height in cm', 'step': '0.1'}),
            'weight_kg': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Weight in kg', 'step': '0.1'}),
            'activity_level': forms.Select(attrs={'class': 'form-select'}),
            'goal': forms.Select(attrs={'class': 'form-select'}),
            'diet_type': forms.Select(attrs={'class': 'form-select'}),
            'allergies': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. nuts, dairy, shellfish'}),
            'health_conditions': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. diabetes, hypertension'}),
        }


class MealLogForm(forms.ModelForm):
    class Meta:
        model = MealLog
        fields = ['meal_type', 'food_name', 'calories', 'protein', 'carbs', 'fat', 'quantity', 'date', 'notes']
        widgets = {
            'meal_type': forms.Select(attrs={'class': 'form-select'}),
            'food_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Food name'}),
            'calories': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': '0'}),
            'protein': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': '0g'}),
            'carbs': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': '0g'}),
            'fat': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': '0g'}),
            'quantity': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '1 serving'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Optional notes'}),
        }


class WeightLogForm(forms.ModelForm):
    class Meta:
        model = WeightLog
        fields = ['weight_kg', 'date', 'notes']
        widgets = {
            'weight_kg': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': 'Weight in kg'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Optional notes'}),
        }
