from django.urls import path
from . import views

urlpatterns = [
    # Chat functionality
    path('chat/', views.chat, name='chat'),
    
    # Conversation history
    path('history/', views.history, name='history'),
    path('history/clear/', views.clear_history, name='clear_history'),
    
    # Conversation management
    path('conversations/', views.create_conversation, name='create_conversation'),
    path('conversations/<uuid:conversation_id>/', views.conversation_detail, name='conversation_detail'),
    path('conversations/<uuid:conversation_id>/update/', views.update_conversation, name='update_conversation'),
    
    # User preferences
    path('preferences/<str:user_identifier>/', views.user_preferences, name='user_preferences'),
    path('preferences/<str:user_identifier>/update/', views.update_user_preferences, name='update_user_preferences'),
    
    # Bot configuration
    path('config/', views.bot_configuration, name='bot_configuration'),
    path('config/update/', views.update_bot_configuration, name='update_bot_configuration'),
    
    # File upload
    path('upload-text-file/', views.upload_text_file, name='upload_text_file'),
]