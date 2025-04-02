from django import forms
from .models import Match, MatchPlayer, PottingSequence
from accounts.models import User

class MatchForm(forms.ModelForm):
    """
    Form for creating a match
    """
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields['players'].queryset = User.objects.filter(
                is_active=True
            ).exclude(
                is_superuser=True
            ).exclude(
                is_admin=True
            ).exclude(
                id=self.user.id
            )

    players = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(is_active=True).exclude(is_superuser=True).exclude(is_admin=True),
        widget=forms.CheckboxSelectMultiple,
        required=True,
        help_text="Select players to participate in this match"
    )
    
    class Meta:
        model = Match
        fields = ['title', 'location', 'notes', 'players']
        
class PottingSequenceForm(forms.ModelForm):
    """
    Form for recording potting sequences
    """
    player_id = forms.IntegerField(widget=forms.HiddenInput())
    
    class Meta:
        model = PottingSequence
        fields = ['potted_balls', 'player_id']
        
    def clean_potted_balls(self):
        """
        Validate that potted_balls is between -147 and 147
        """
        potted_balls = self.cleaned_data.get('potted_balls')
        if potted_balls < -147:
            raise forms.ValidationError("Potted balls cannot be less than -147")
        if potted_balls > 147:
            raise forms.ValidationError("Potted balls cannot exceed 147 (maximum break in snooker)")
        return potted_balls
