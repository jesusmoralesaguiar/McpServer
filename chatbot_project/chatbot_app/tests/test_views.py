import pytest
import uuid
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from ..models import ChatMessage, Conversation

@pytest.mark.django_db
class TestChatViews:
    def setup_method(self):
        self.client = APIClient()
        self.conversation = Conversation.objects.create(title="Test Conversation")
        
    def test_chat_endpoint(self):
        url = reverse('chat')
        data = {'message': 'Hello, world!'}
        response = self.client.post(url, data, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert 'response' in response.data
        assert 'conversation_id' in response.data
        
    def test_history_endpoint_with_conversation_id(self):
        # Create some test messages
        ChatMessage.objects.create(
            conversation=self.conversation,
            sender='user',
            message='Hello'
        )
        ChatMessage.objects.create(
            conversation=self.conversation,
            sender='bot',
            message='Hi there!'
        )
        
        url = reverse('history')
        response = self.client.get(url, {'conversation_id': self.conversation.id})
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2
        
    def test_history_endpoint_without_conversation_id(self):
        url = reverse('history')
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)
        
    def test_clear_history_endpoint_with_conversation_id(self):
        # Create some test messages
        ChatMessage.objects.create(
            conversation=self.conversation,
            sender='user',
            message='Hello'
        )
        
        url = reverse('clear_history')
        data = {'conversation_id': str(self.conversation.id)}
        response = self.client.delete(url, data, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert not Conversation.objects.filter(id=self.conversation.id).exists()
        
    def test_clear_history_endpoint_without_conversation_id(self):
        # Create some test messages
        conversation2 = Conversation.objects.create(title="Test Conversation 2")
        ChatMessage.objects.create(
            conversation=self.conversation,
            sender='user',
            message='Hello'
        )
        ChatMessage.objects.create(
            conversation=conversation2,
            sender='user',
            message='Hello again'
        )
        
        url = reverse('clear_history')
        response = self.client.delete(url, {}, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert Conversation.objects.count() == 0


@pytest.mark.django_db
class TestConversationViews:
    def setup_method(self):
        self.client = APIClient()
        
    def test_create_conversation(self):
        url = reverse('create_conversation')
        data = {'title': 'New Test Conversation'}
        response = self.client.post(url, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['title'] == 'New Test Conversation'
        
    def test_conversation_detail(self):
        conversation = Conversation.objects.create(title="Test Conversation")
        url = reverse('conversation_detail', kwargs={'conversation_id': conversation.id})
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == str(conversation.id)
        
    def test_update_conversation(self):
        conversation = Conversation.objects.create(title="Original Title")
        url = reverse('update_conversation', kwargs={'conversation_id': conversation.id})
        data = {'title': 'Updated Title'}
        response = self.client.put(url, data, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['title'] == 'Updated Title'


@pytest.mark.django_db
class TestConfigurationViews:
    def setup_method(self):
        self.client = APIClient()
        
    def test_bot_configuration(self):
        url = reverse('bot_configuration')
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert 'name' in response.data
        
    def test_update_bot_configuration(self):
        url = reverse('update_bot_configuration')
        data = {'temperature': 0.8, 'max_response_length': 1500}
        response = self.client.put(url, data, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['temperature'] == 0.8