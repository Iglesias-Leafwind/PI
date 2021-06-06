"""project URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from app import views


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.landingpage, name='landingpage'),
    path('results', views.index, name='index'),
    path('updateTags/<int:hash>', views.updateTags, name='updateTags'),
    path('folders', views.managefolders, name='managefolders'),
    path('delete/<path:path>', views.delete, name='uploadDelete'),
    path('update', views.updateFolders, name='updateFolders'),
    path('people', views.managepeople, name='managepeople'),
    path('upload', views.upload, name='uploadFolder'),
    path('searchtag', views.searchtag, name='searchtag'),
    path('update_faces', views.update_faces, name='update_faces'),
    path('change_filters', views.change_filters, name='change_filters'),
    path('dashboard', views.dashboard, name='dashboard'),
    path('objects', views.objectsGallery, name='objectsGallery'),
    path('people', views.peopleGallery, name='pplGallery'),
    path('scenes', views.scenesGallery, name='scenesGallery'),
    path('locations', views.locationsGallery, name='locationsGallery'),
    path('gallery', views.calendarGallery, name='gallery'),
]
