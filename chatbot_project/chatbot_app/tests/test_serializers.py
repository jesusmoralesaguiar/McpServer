import pytest
import uuid
from datetime import datetime
from ..models import ChatMessage, Conversation, UserPreference, BotConfiguration
from ..serializers import (
    ChatMessageSerializer, 
    ConversationSerializer, 
    ChatRequestSerializer,
    ChatResponseSerializer,
    UserPreferenceSerializer,
    BotConfigurationSerializer
)

@pytest.mark.django_db
class TestConversationSerializer:
    def setup_method(self):
        self.conversation_attributes = {
            'title': 'Test Conversation',
            'is_active': True
        }
        self.conversation = Conversation.objects.create(**self.conversation_attributes)
        
    def test_conversation_serializer_contains_expected_fields(self):
        serializer = ConversationSerializer(instance=self.conversation)
        data = serializer.data
        expected_fields = ['id', 'title', 'created_at', 'last_message_at', 'is_active']
        for field in expected_fields:
            assert field in data
            
    def test_conversation_serializer_field_content(self):
        serializer = ConversationSerializer(instance=self.conversation)
        data = serializer.data
        assert data['title'] == self.conversation_attributes['title']
        assert data['is_active'] == self.conversation_attributes['is_active']
        
    def test_conversation_serializer_read_only_fields(self):
        serializer = ConversationSerializer()
        expected_read_only_fields = ['id', 'created_at', 'last_message_at']
        for field in expected_read_only_fields:
            assert field in serializer.fields
            assert serializer.fields[field].read_only is True

@pytest.mark.django_db
class TestChatMessageSerializer:
    def setup_method(self):
        self.conversation = Conversation.objects.create(title="Test Conversation")
        self.message_attributes = {
            'conversation': self.conversation,
            'sender': 'user',
            'message': 'Test message',
            'is_read': False
        }
        self.message = ChatMessage.objects.create(**self.message_attributes)
        
    def test_chat_message_serializer_contains_expected_fields(self):
        serializer = ChatMessageSerializer(instance=self.message)
        data = serializer.data
        expected_fields = ['id', 'conversation', 'sender', 'message', 'timestamp', 'is_read']
        for field in expected_fields:
            assert field in data
            
    def test_chat_message_serializer_field_content(self):
        serializer = ChatMessageSerializer(instance=self.message)
        data = serializer.data
        assert str(data['conversation']) == str(self.message_attributes['conversation'].id)
        assert data['sender'] == self.message_attributes['sender']
        assert data['message'] == self.message_attributes['message']
        
    def test_chat_message_serializer_read_only_fields(self):
        serializer = ChatMessageSerializer()
        expected_read_only_fields = ['id', 'timestamp']
        for field in expected_read_only_fields:
            assert field in serializer.fields
            assert serializer.fields[field].read_only is True

class TestChatRequestSerializer:
    def test_chat_request_serializer_valid_data(self):
        valid_data = {
            'message': 'Hello, world!',
            'conversation_id': str(uuid.uuid4())
        }
        serializer = ChatRequestSerializer(data=valid_data)
        assert serializer.is_valid()
        
    def test_chat_request_serializer_valid_data_without_conversation_id(self):
        valid_data = {
            'message': 'Hello, world!'
        }
        serializer = ChatRequestSerializer(data=valid_data)
        assert serializer.is_valid()
        
    def test_chat_request_serializer_invalid_data(self):
        invalid_data = {
            'message': ''  # Empty message
        }
        serializer = ChatRequestSerializer(data=invalid_data)
        assert not serializer.is_valid()
        
    def test_chat_request_serializer_message_max_length(self):
        invalid_data = {
            'message': 'x' * 1001  # Exceeds max length
        }
        serializer = ChatRequestSerializer(data=invalid_data)
        assert not serializer.is_valid()

class TestChatResponseSerializer:
    def test_chat_response_serializer_valid_data(self):
        valid_data = {
            'response': 'Hello, user!',
            'conversation_id': str(uuid.uuid4()),
            'timestamp': datetime.now().isoformat()
        }
        serializer = ChatResponseSerializer(data=valid_data)
        assert serializer.is_valid()
        
    def test_chat_response_serializer_invalid_data(self):
        invalid_data = {
            'response': '',  # Empty response
            'conversation_id': 'invalid-uuid'
        }
        serializer = ChatResponseSerializer(data=invalid_data)
        assert not serializer.is_valid()

@pytest.mark.django_db
class TestUserPreferenceSerializer:
    def setup_method(self):
        self.preference_attributes = {
            'user_identifier': 'test_user_123',
            'preferred_language': 'es',
            'tone_preference': 'professional',
            'enable_notifications': True
        }
        self.preference = UserPreference.objects.create(**self.preference_attributes)
        
    def test_user_preference_serializer_contains_expected_fields(self):
        serializer = UserPreferenceSerializer(instance=self.preference)
        data = serializer.data
        expected_fields = ['id', 'user_identifier', 'preferred_language', 'tone_preference', 
                          'enable_notifications', 'created_at', 'updated_at']
        for field in expected_fields:
            assert field in data
            
    def test_user_preference_serializer_field_content(self):
        serializer = UserPreferenceSerializer(instance=self.preference)
        data = serializer.data
        assert data['user_identifier'] == self.preference_attributes['user_identifier']
        assert data['preferred_language'] == self.preference_attributes['preferred_language']
        assert data['tone_preference'] == self.preference_attributes['tone_preference']
        assert data['enable_notifications'] == self.preference_attributes['enable_notifications']

@pytest.mark.django_db
class TestBotConfigurationSerializer:
    def setup_method(self):
        self.config_attributes = {
            'name': 'Test Bot',
            'description': 'A test bot',
            'is_active': True,
            'max_response_length': 1500,
            'temperature': 0.8
        }
        self.config = BotConfiguration.objects.create(**self.config_attributes)
        
    def test_bot_configuration_serializer_contains_expected_fields(self):
        serializer = BotConfigurationSerializer(instance=self.config)
        data = serializer.data
        expected_fields = ['id', 'name', 'description', 'is_active', 'max_response_length', 
                          'temperature', 'created_at', 'updated_at']
        for field in expected_fields:
            assert field in data
            
    def test_bot_configuration_serializer_field_content(self):
        serializer = BotConfigurationSerializer(instance=self.config)
        data = serializer.data
        assert data['name'] == self.config_attributes['name']
        assert data['description'] == self.config_attributes['description']
        assert data['is_active'] == self.config_attributes['is_active']
        assert data['max_response_length'] == self.config_attributes['max_response_length']
        assert data['temperature'] == self.config_attributes['temperature']