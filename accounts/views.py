from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from .models import User
from matches.models import Match,MatchPlayer
from .forms import UserRegistrationForm, UserUpdateForm, CustomUserCreationForm
from stats.models import PlayerStats, PlayerVsPlayerStats
from django.db import models

def sign_up(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Account created successfully!')
            return redirect('login')  # Redirect to the login page after successful signup
        else:
            for error in form.errors.values():
                for message in error:
                    messages.error(request, message)
    else:
        form = CustomUserCreationForm()

    return render(request, 'sign_up.html', {'form': form})

def login_view(request):
    """View for user login"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"Welcome back, {username}!")
                return redirect('dashboard')
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

@login_required
def dashboard(request):
    if request.user.is_authenticated:
        if request.user.is_superuser or request.user.is_admin:
            return redirect('admin_dashboard')
    """User dashboard view"""
    # Ensure player stats exist
    stats, created = PlayerStats.objects.get_or_create(player=request.user)
    if created or request.GET.get('refresh_stats'):
        stats.update_stats()
    
    context = {
        'stats': stats,
        'recent_matches': request.user.matches.order_by('-match__date')[:5],
    }
    return render(request, 'dashboard.html', context)

def logout_view(request):
    """View for user logout"""
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect('login')

# Admin views
def is_admin(user):
    """Check if user is an admin"""
    return user.is_authenticated and (user.is_admin or user.is_superuser)

@user_passes_test(is_admin)
def admin_dashboard(request):
    """Admin dashboard view"""
    context = {
        'total_users': User.objects.count(),
        'active_users': User.objects.filter(is_active=True).exclude(id=request.user.id).count(),
        'admin_users': User.objects.filter(is_superuser=True).count(),
        'recent_users': User.objects.order_by('-date_joined').exclude(id=request.user.id)[:5],
    }
    return render(request, 'admin_dashboard.html', context)

@user_passes_test(is_admin)
def admin_user_list(request):
    """Admin view for listing all users"""
    # Start with all users except the current user
    users = User.objects.all().exclude(id=request.user.id)
    
    # Process search parameter
    search_query = request.GET.get('search', '')
    if search_query:
        users = users.filter(
            models.Q(username__icontains=search_query) |
            models.Q(first_name__icontains=search_query) |
            models.Q(last_name__icontains=search_query) |
            models.Q(email__icontains=search_query)
        )
    
    # Process status filter
    status = request.GET.get('status', '')
    if status == 'active':
        users = users.filter(is_active=True, is_superuser=False, is_admin=False)
    elif status == 'inactive':
        users = users.filter(is_active=False)
    elif status == 'admin':
        users = users.filter(models.Q(is_superuser=True) | models.Q(is_admin=True))
    
    # Process sorting
    sort = request.GET.get('sort', 'newest')
    if sort == 'newest':
        users = users.order_by('-date_joined')
    elif sort == 'oldest':
        users = users.order_by('date_joined')
    elif sort == 'username':
        users = users.order_by('username')
    
    context = {
        'users': users,
        'search_query': search_query,
        'status': status,
        'sort': sort
    }
    
    return render(request, 'user_list.html', context)

@user_passes_test(is_admin)
def admin_user_create(request):
    """Admin view for creating a new user"""
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            # Create stats instance for the new user
            PlayerStats.objects.create(player=user)
            messages.success(request, f"User {user.username} was created successfully!")
            return redirect('admin_user_list')
    else:
        form = UserRegistrationForm()
    return render(request, 'user_form.html', {'form': form, 'title': 'Create User'})

@user_passes_test(is_admin)
def admin_user_edit(request, user_id):
    """Admin view for editing a user"""
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, f"User {user.username} was updated successfully!")
            return redirect('admin_user_list')
    else:
        form = UserUpdateForm(instance=user)
    return render(request, 'user_form.html', {'form': form, 'user': user, 'title': 'Edit User'})

@user_passes_test(is_admin)
def admin_user_delete(request, user_id):
    """Admin view for deleting a user"""
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        # First, manually clean up related objects that might not cascade properly
        try:
            # Explicitly delete PlayerVsPlayerStats entries
            PlayerVsPlayerStats.objects.filter(player1=user).delete()
            PlayerVsPlayerStats.objects.filter(player2=user).delete()
            
            # If there are any other problematic relationships, delete them here
            
            # Now delete the user which will cascade to other related models
            username = user.username
            user.delete()
            messages.success(request, f"User {username} was deleted successfully!")
        except Exception as e:
            messages.error(request, f"Error deleting user: {str(e)}")
        return redirect('admin_user_list')
    return render(request, 'user_confirm_delete.html', {'user': user})

def landing_page(request):
    """View for the landing/home page"""
    if request.user.is_authenticated:
        # Redirect based on user role (assuming you have these flags)
        # Using hasattr is safer in case these attributes don't exist on all user types
        is_admin = hasattr(request.user, 'is_superuser') and request.user.is_superuser
        is_staff = hasattr(request.user, 'is_staff') and request.user.is_staff # Django's built-in staff flag

        if is_admin or is_staff: # Simplified check
            return redirect('admin_dashboard') # Make sure 'admin_dashboard' URL name exists
        else:
            return redirect('dashboard') # Make sure 'dashboard' URL name exists

    # --- Calculate Stats for Landing Page ---
    try:
        # Count active, non-staff/admin users as 'players'
        player_count = User.objects.filter(is_active=True, is_staff=False, is_superuser=False).count()
    except User.DoesNotExist: 
        player_count = 0 

    try:
        match_count =Match.objects.filter().count()
    except Match.DoesNotExist:
        match_count = 0

    try:
        century_count = MatchPlayer.objects.filter(highest_break__gte=100).count()
    except MatchPlayer.DoesNotExist:
        century_count = 0

    context = {
        'player_count': player_count,
        'match_count': match_count,
        'century_count': century_count,
    }
    return render(request, 'landing.html', context)
