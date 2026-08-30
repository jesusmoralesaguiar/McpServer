from django.contrib import admin
from .models import ChatMessage, Conversation, UserPreference, BotConfiguration

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'created_at', 'last_message_at', 'is_active')
    list_filter = ('created_at', 'last_message_at', 'is_active')
    search_fields = ('title', 'id')
    ordering = ('-last_message_at',)

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('conversation', 'sender', 'message_preview', 'timestamp')
    list_filter = ('sender', 'timestamp')
    search_fields = ('message', 'conversation__id')
    ordering = ('timestamp',)
    
    def message_preview(self, obj):
        return obj.message[:50] + ('...' if len(obj.message) > 50 else '')
    message_preview.short_description = 'Message Preview'

@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user_identifier', 'preferred_language', 'tone_preference', 'enable_notifications')
    list_filter = ('preferred_language', 'tone_preference', 'enable_notifications')
    search_fields = ('user_identifier',)

@admin.register(BotConfiguration)
class BotConfigurationAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'temperature', 'max_response_length', 'updated_at')
    list_filter = ('is_active', 'temperature')
    search_fields = ('name', 'description')
