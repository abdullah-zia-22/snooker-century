from django.urls import path
from . import views

urlpatterns = [
    # Authentication URLs
    path('sign_up/', views.sign_up, name='sign_up'),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    
    # Admin portal URLs
    path("admin/", views.admin_dashboard, name="admin_dashboard"),
    path("admin/users/", views.admin_user_list, name="admin_user_list"),
    path("admin/users/create/", views.admin_user_create, name="admin_user_create"),
    path("admin/users/<int:user_id>/edit/", views.admin_user_edit, name="admin_user_edit"),
    path("admin/users/<int:user_id>/delete/", views.admin_user_delete, name="admin_user_delete"),
    
    # Home URL (now points to landing page)
    path("", views.landing_page, name="home"),
]
