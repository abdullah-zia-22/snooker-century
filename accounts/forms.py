from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import User

MAX_PICTURE_BYTES = 3 * 1024 * 1024  # 3 MB


class StyledFormMixin:
    """Adds Bootstrap/Design-system CSS classes to every widget and flags invalid fields."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                css = "form-check-input"
            elif isinstance(widget, (forms.CheckboxSelectMultiple, forms.RadioSelect)):
                continue
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                css = "form-select"
            else:
                css = "form-control"
            widget.attrs["class"] = f"{widget.attrs.get('class', '')} {css}".strip()

    def full_clean(self):
        super().full_clean()
        if self.is_bound:
            for name in self.errors:
                if name in self.fields:
                    widget = self.fields[name].widget
                    widget.attrs["class"] = f"{widget.attrs.get('class', '')} is-invalid".strip()


def _validate_picture(picture):
    if picture and hasattr(picture, "size") and picture.size > MAX_PICTURE_BYTES:
        raise forms.ValidationError("Profile picture must be 3 MB or smaller.")
    return picture


class StyledAuthenticationForm(StyledFormMixin, AuthenticationForm):
    remember_me = forms.BooleanField(required=False, initial=True, label="Keep me signed in")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({"autocomplete": "username", "autofocus": True, "autocapitalize": "none"})
        self.fields["password"].widget.attrs.update({"autocomplete": "current-password"})


class UserRegistrationForm(StyledFormMixin, UserCreationForm):
    """Used for public sign-up and for admins creating users."""

    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    bio = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False)
    profile_picture = forms.ImageField(required=False, widget=forms.FileInput(attrs={"accept": "image/*"}))

    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "password1", "password2", "bio", "profile_picture")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].widget.attrs["autocomplete"] = "email"
        self.fields["first_name"].widget.attrs["autocomplete"] = "given-name"
        self.fields["last_name"].widget.attrs["autocomplete"] = "family-name"
        self.fields["password1"].widget.attrs["autocomplete"] = "new-password"
        self.fields["password2"].widget.attrs["autocomplete"] = "new-password"

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_profile_picture(self):
        return _validate_picture(self.cleaned_data.get("profile_picture"))


# Backwards-compatible alias (the old code had two identical forms)
CustomUserCreationForm = UserRegistrationForm


class UserUpdateForm(StyledFormMixin, forms.ModelForm):
    """Admin form for editing an existing user."""

    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    bio = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False)
    profile_picture = forms.ImageField(required=False, widget=forms.FileInput(attrs={"accept": "image/*"}))
    is_active = forms.BooleanField(required=False, label="Account is active")

    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "bio", "profile_picture", "is_active")

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Another account already uses this email.")
        return email

    def clean_profile_picture(self):
        return _validate_picture(self.cleaned_data.get("profile_picture"))
