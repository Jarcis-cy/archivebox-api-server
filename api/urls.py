from django.urls import path
from . import views

urlpatterns = [
    path('init', views.init_project, name='init_project'),
    path('sync', views.synchronization, name='synchronization'),
    path('add', views.add_urls, name='add_urls'),
    path('list', views.list_target, name='list_target'),
]
