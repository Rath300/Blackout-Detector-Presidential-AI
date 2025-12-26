from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('home/', views.home_view, name='home'),
    path('data-overview/', views.data_overview_view, name='data_overview'),
    path('anomalies/', views.anomalies_view, name='anomalies'),
    path('forecasting/', views.forecasting_view, name='forecasting'),
    path('upload/', views.upload_file, name='upload_file'),
    path('update-settings/', views.update_settings, name='update_settings'),
]

