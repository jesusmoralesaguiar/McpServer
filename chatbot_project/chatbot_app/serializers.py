from rest_framework import serializers
from .models import ChatMessage, Conversation, UserPreference, BotConfiguration
import uuid


class ConversationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversation
        fields = ['id', 'title', 'created_at', 'last_message_at', 'is_active']
        read_only_fields = ['id', 'created_at', 'last_message_at']


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['id', 'conversation', 'sender', 'message', 'timestamp', 'is_read']
        read_only_fields = ['id', 'timestamp']


class ChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=1000)
    conversation_id = serializers.UUIDField(required=False)


class ChatResponseSerializer(serializers.Serializer):
    response = serializers.CharField()
    conversation_id = serializers.UUIDField()
    timestamp = serializers.DateTimeField()


class UserPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPreference
        fields = ['id', 'user_identifier', 'preferred_language', 'tone_preference', 
                  'enable_notifications', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class BotConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = BotConfiguration
        fields = ['id', 'name', 'description', 'is_active', 'max_response_length', 
                  'temperature', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']