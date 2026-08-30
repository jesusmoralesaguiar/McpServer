import pytest
import uuid
from ..models import ChatMessage, Conversation, UserPreference, BotConfiguration

@pytest.mark.django_db
class TestConversationModel:
    def test_conversation_creation(self):
        conversation = Conversation.objects.create(title="Test Conversation")
        assert isinstance(conversation, Conversation)
        assert isinstance(conversation.id, uuid.UUID)
        assert conversation.title == "Test Conversation"
        assert conversation.is_active is True
        
    def test_conversation_string_representation(self):
        conversation = Conversation.objects.create(title="Test Conversation")
        expected_str = f"Conversation {conversation.id} - Test Conversation"
        assert str(conversation) == expected_str
        
    def test_conversation_without_title(self):
        conversation = Conversation.objects.create()
        expected_str = f"Conversation {conversation.id} - Untitled"
        assert str(conversation) == expected_str

@pytest.mark.django_db
class TestChatMessageModel:
    def setup_method(self):
        self.conversation = Conversation.objects.create(title="Test Conversation")
        
    def test_chat_message_creation(self):
        message = ChatMessage.objects.create(
            conversation=self.conversation,
            sender='user',
            message='Test message'
        )
        assert isinstance(message, ChatMessage)
        assert isinstance(message.id, uuid.UUID)
        assert message.sender == 'user'
        assert message.message == 'Test message'
        assert message.is_read is False
        
    def test_chat_message_string_representation(self):
        message = ChatMessage.objects.create(
            conversation=self.conversation,
            sender='bot',
            message='This is a test message that is longer than fifty characters to test the truncation'
        )
        expected_str = "bot: This is a test message that is longer than fift..."
        assert str(message) == expected_str

@pytest.mark.django_db
class TestUserPreferenceModel:
    def test_user_preference_creation(self):
        preference = UserPreference.objects.create(
            user_identifier='test_user_123',
            preferred_language='es',
            tone_preference='professional'
        )
        assert isinstance(preference, UserPreference)
        assert isinstance(preference.id, uuid.UUID)
        assert preference.user_identifier == 'test_user_123'
        assert preference.preferred_language == 'es'
        assert preference.tone_preference == 'professional'
        assert preference.enable_notifications is True
        
    def test_user_preference_default_values(self):
        preference = UserPreference.objects.create(user_identifier='test_user_456')
        assert preference.preferred_language == 'en'
        assert preference.tone_preference == 'friendly'
        assert preference.enable_notifications is True

@pytest.mark.django_db
class TestBotConfigurationModel:
    def test_bot_configuration_creation(self):
        config = BotConfiguration.objects.create(
            name='Test Bot',
            description='A test bot configuration',
            max_response_length=1500,
            temperature=0.8
        )
        assert isinstance(config, BotConfiguration)
        assert isinstance(config.id, uuid.UUID)
        assert config.name == 'Test Bot'
        assert config.description == 'A test bot configuration'
        assert config.is_active is True
        assert config.max_response_length == 1500
        assert config.temperature == 0.8
        
    def test_bot_configuration_default_values(self):
        config = BotConfiguration.objects.create(name='Default Bot')
        assert config.description == ''
        assert config.is_active is True
        assert config.max_response_length == 1000
        assert config.temperature == 0.7