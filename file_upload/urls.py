"""
URL configuration for file_upload project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
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

from django.urls import path
from file_app import views

urlpatterns = [
   
    path('', views.upload_file, name='upload_file'),
    path('success/', views.show_results, name='show_results'),
    path('download/', views.download_results, name='download_results'),
    path('upload_pdf/', views.upload_pdf, name='upload_pdf'),
    path('extract/', views.extract_subtitles, name='extract_subtitles'),
    path('download_subtitles/', views.download_subtitles, name='download_subtitles'),
    path('download_subtitles_btf/', views.download_subtitles, name='download_subtitles_btf'),
    path('download_subtitles_bav/', views.download_subtitles, name='download_subtitles_bav'),
    path('extract/', views.extract, name='extract'),
]
    

