from django.contrib import admin
from django.urls import path
from .views import *
urlpatterns = [
    path('topic', TopicAPIView.as_view(), name='topics'),
    path('upload-pdf', UploadPdfAPIView.as_view(), name='upload-pdf'),
    path('question', QuestionAPIView.as_view(), name='question'),
    path('clear-session', SessionClearAPIView.as_view(), name='clear-session'),
]
