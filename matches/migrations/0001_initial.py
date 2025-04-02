# Generated by Django 5.0.6 on 2025-03-31 21:31

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Match',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('date', models.DateTimeField(auto_now_add=True)),
                ('location', models.CharField(blank=True, max_length=255)),
                ('notes', models.TextField(blank=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='created_matches', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Match',
                'verbose_name_plural': 'Matches',
                'ordering': ['-date'],
            },
        ),
        migrations.CreateModel(
            name='MatchPlayer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('total_score', models.IntegerField(default=0)),
                ('highest_break', models.IntegerField(default=0)),
                ('is_winner', models.BooleanField(blank=True, null=True)),
                ('match', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='players', to='matches.match')),
                ('player', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='matches', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('match', 'player')},
            },
        ),
        migrations.CreateModel(
            name='PottingSequence',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('potted_balls', models.IntegerField()),
                ('sequence_number', models.IntegerField()),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('match_player', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='potting_sequences', to='matches.matchplayer')),
            ],
            options={
                'ordering': ['match_player', 'sequence_number'],
            },
        ),
    ]
