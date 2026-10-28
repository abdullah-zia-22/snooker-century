from functools import wraps
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from matches.models import MatchPlayer, PottingSequence
from matches.services import result_for
from stats.models import PlayerStats

from .forms import StyledAuthenticationForm, UserRegistrationForm, UserUpdateForm
from .models import User

USERS_PER_PAGE = 12
PICTURE_WARNING = (
    "Profile pictures can't be stored on this deployment right now, "
    "so the account was saved without one."
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def home_for(user):
    return "admin_dashboard" if user.is_site_admin else "dashboard"


def admin_required(view):
    """Logged-in admins only. Others get a friendly redirect instead of a login loop."""

    @login_required
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_site_admin:
            messages.error(request, "You don't have access to that page.")
            return redirect("dashboard")
        return view(request, *args, **kwargs)

    return wrapper


def save_user_form(request, form):
    """Save a user form. Serverless hosts (e.g. Vercel) have a read-only disk, so if the
    picture can't be written we save the account without it instead of crashing."""
    try:
        return form.save()
    except OSError:
        form.instance.profile_picture = None
        messages.warning(request, PICTURE_WARNING)
        return form.save()


def can_manage(request, target):
    """Only superusers may modify other superusers."""
    return not target.is_superuser or request.user.is_superuser


def serve_profile_picture(request, filename):
    profile_pictures = (Path(settings.MEDIA_ROOT) / "profile_pics").resolve()
    image_path = (profile_pictures / filename).resolve()
    if image_path.parent != profile_pictures or not image_path.is_file():
        raise Http404
    return FileResponse(image_path.open("rb"))


# ---------------------------------------------------------------------------
# Public pages
# ---------------------------------------------------------------------------
def landing_page(request):
    if request.user.is_authenticated:
        return redirect(home_for(request.user))

    context = {
        "player_count": User.objects.filter(is_active=True, is_staff=False, is_superuser=False, is_admin=False).count(),
        "match_count": MatchPlayer.objects.values("match_id").distinct().count(),
        "century_count": PottingSequence.objects.filter(
            potted_balls__gte=100, match_player__match__is_active=False
        ).count(),
    }
    return render(request, "landing.html", context)


def sign_up(request):
    if request.user.is_authenticated:
        return redirect(home_for(request.user))

    if request.method == "POST":
        form = UserRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            save_user_form(request, form)
            messages.success(request, "Account created! Sign in to get started.")
            return redirect("login")
        messages.error(request, "Please fix the highlighted fields below.")
    else:
        form = UserRegistrationForm()
    return render(request, "sign_up.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect(home_for(request.user))

    next_url = request.POST.get("next") or request.GET.get("next") or ""
    form = StyledAuthenticationForm(request, data=request.POST or None)

    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        login(request, user)
        if not form.cleaned_data.get("remember_me"):
            request.session.set_expiry(0)  # session cookie only
        messages.success(request, f"Welcome back, {user.display_name}!")
        if next_url and url_has_allowed_host_and_scheme(
            next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
        ):
            return redirect(next_url)
        return redirect(home_for(user))

    return render(request, "login.html", {"form": form, "next": next_url})


@require_POST
def logout_view(request):
    """Logging out changes state, so it must be a POST (prevents CSRF logout via <img src>)."""
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect("login")


# ---------------------------------------------------------------------------
# Player dashboard
# ---------------------------------------------------------------------------
@login_required
def dashboard(request):
    if request.user.is_site_admin:
        return redirect("admin_dashboard")

    stats, created = PlayerStats.objects.get_or_create(player=request.user)
    if created or request.GET.get("refresh_stats"):
        stats.update_stats()

    entries = list(
        MatchPlayer.objects.filter(player=request.user)
        .select_related("match")
        .prefetch_related("match__players")
        .order_by("-match__date")[:6]
    )
    rows = [{"match": e.match, "result": result_for(e)} for e in entries]

    context = {
        "stats": stats,
        "recent_matches": rows[:5],
        "live_matches": [r for r in rows if r["result"] == "live"],
    }
    return render(request, "dashboard.html", context)


# ---------------------------------------------------------------------------
# Admin portal
# ---------------------------------------------------------------------------
@admin_required
def admin_dashboard(request):
    others = User.objects.exclude(id=request.user.id)
    context = {
        "total_users": User.objects.count(),
        "active_users": others.filter(is_active=True, is_superuser=False, is_admin=False).count(),
        "admin_users": User.objects.filter(Q(is_superuser=True) | Q(is_admin=True)).count(),
        "recent_users": others.order_by("-date_joined")[:5],
    }
    return render(request, "admin_dashboard.html", context)


@admin_required
def admin_user_list(request):
    users = User.objects.exclude(id=request.user.id)

    search_query = request.GET.get("search", "").strip()
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query)
            | Q(first_name__icontains=search_query)
            | Q(last_name__icontains=search_query)
            | Q(email__icontains=search_query)
        )

    status = request.GET.get("status", "")
    if status == "active":
        users = users.filter(is_active=True, is_superuser=False, is_admin=False)
    elif status == "inactive":
        users = users.filter(is_active=False)
    elif status == "admin":
        users = users.filter(Q(is_superuser=True) | Q(is_admin=True))

    sort = request.GET.get("sort", "newest")
    users = users.order_by({"oldest": "date_joined", "username": "username"}.get(sort, "-date_joined"))

    page_obj = Paginator(users, USERS_PER_PAGE).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)

    context = {
        "page_obj": page_obj,
        "users": page_obj.object_list,
        "total_count": page_obj.paginator.count,
        "search_query": search_query,
        "status": status,
        "sort": sort,
        "querystring": params.urlencode(),
    }
    return render(request, "user_list.html", context)


@admin_required
def admin_user_create(request):
    if request.method == "POST":
        form = UserRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = save_user_form(request, form)
            PlayerStats.objects.get_or_create(player=user)
            messages.success(request, f"User {user.username} was created successfully!")
            return redirect("admin_user_list")
        messages.error(request, "Please fix the highlighted fields below.")
    else:
        form = UserRegistrationForm()
    return render(request, "user_form.html", {"form": form, "title": "Create User", "is_create": True})


@admin_required
def admin_user_edit(request, user_id):
    # NB: never pass the edited user to the template as "user" — that would shadow request.user.
    target = get_object_or_404(User, id=user_id)
    if not can_manage(request, target):
        messages.error(request, "Only a superuser can edit another superuser.")
        return redirect("admin_user_list")

    if request.method == "POST":
        form = UserUpdateForm(request.POST, request.FILES, instance=target)
        if target == request.user:
            form.fields["is_active"].disabled = True  # don't let admins lock themselves out
        if form.is_valid():
            save_user_form(request, form)
            messages.success(request, f"User {target.username} was updated successfully!")
            return redirect("admin_user_list")
        messages.error(request, "Please fix the highlighted fields below.")
    else:
        form = UserUpdateForm(instance=target)
        if target == request.user:
            form.fields["is_active"].disabled = True
    return render(request, "user_form.html", {"form": form, "target_user": target, "title": "Edit User", "is_create": False})


@admin_required
def admin_user_delete(request, user_id):
    target = get_object_or_404(User, id=user_id)

    problem = None
    if target == request.user:
        problem = "You can't delete your own account."
    elif not can_manage(request, target):
        problem = "Only a superuser can delete another superuser."
    created_count = target.created_matches.count()

    if problem:
        messages.error(request, problem)
        return redirect("admin_user_list")

    if request.method == "POST":
        if created_count:
            messages.error(
                request,
                f"{target.username} created {created_count} match(es); deleting the account would erase them for "
                "every other player too. Deactivate the account instead.",
            )
            return redirect("admin_user_list")

        username = target.username
        # Remember opponents so their stats can be recalculated once this player's results are gone.
        affected = list(User.objects.filter(matches__match__players__player=target).exclude(id=target.id).distinct())
        target.delete()
        for opponent in affected:
            stats, _ = PlayerStats.objects.get_or_create(player=opponent)
            stats.update_stats()
        messages.success(request, f"User {username} was deleted successfully!")
        return redirect("admin_user_list")

    return render(request, "user_confirm_delete.html", {"target_user": target, "created_count": created_count})
