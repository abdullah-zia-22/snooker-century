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
            name='PlayerStats',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('total_matches', models.IntegerField(default=0)),
                ('wins', models.IntegerField(default=0)),
                ('highest_break', models.IntegerField(default=0)),
                ('total_centuries', models.IntegerField(default=0)),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('player', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='stats', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='PlayerVsPlayerStats',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('player1_wins', models.IntegerField(default=0)),
                ('player2_wins', models.IntegerField(default=0)),
                ('total_matches', models.IntegerField(default=0)),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('player1', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stats_as_player1', to=settings.AUTH_USER_MODEL)),
                ('player2', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stats_as_player2', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Player vs Player Stats',
                'verbose_name_plural': 'Player vs Player Stats',
                'unique_together': {('player1', 'player2')},
            },
        ),
    ]
