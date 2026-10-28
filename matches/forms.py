from django import forms

from accounts.forms import StyledFormMixin
from accounts.models import User

from .models import Match, PottingSequence


class PlayerChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return obj.display_name


def eligible_players():
    return User.objects.filter(is_active=True, is_superuser=False, is_admin=False).order_by("first_name", "username")


class MatchForm(StyledFormMixin, forms.ModelForm):
    """Form for creating a match."""

    players = PlayerChoiceField(
        queryset=User.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=True,
        help_text="Pick everyone you're playing against.",
    )

    class Meta:
        model = Match
        fields = ["title", "location", "notes", "players"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "e.g. Friday night frames", "autofocus": True}),
            "location": forms.TextInput(attrs={"placeholder": "Club or hall (optional)"}),
            "notes": forms.Textarea(attrs={"rows": 3, "placeholder": "Anything worth remembering (optional)"}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        queryset = eligible_players()
        if self.user:
            queryset = queryset.exclude(id=self.user.id)
        self.fields["players"].queryset = queryset


class PottingSequenceForm(forms.ModelForm):
    """Records one visit/break for a player."""

    player_id = forms.IntegerField(widget=forms.HiddenInput())

    class Meta:
        model = PottingSequence
        fields = ["potted_balls", "player_id"]

    def clean_potted_balls(self):
        potted_balls = self.cleaned_data.get("potted_balls")
        if potted_balls is None:
            raise forms.ValidationError("Enter a score.")
        if potted_balls < -147:
            raise forms.ValidationError("Score cannot be less than -147.")
        if potted_balls > 147:
            raise forms.ValidationError("Score cannot exceed 147 (the maximum break).")
        return potted_balls
