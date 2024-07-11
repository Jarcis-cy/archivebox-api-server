from django.urls import path
from . import views

urlpatterns = [
    path('init', views.init_project, name='init_project'),
    path('add', views.add_urls, name='add_urls'),
]
