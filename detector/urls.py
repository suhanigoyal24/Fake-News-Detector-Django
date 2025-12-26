from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('submit_review/', views.submit_review, name='submit_review'),
    path('check_news/', views.check_news, name='check_news'),
]
