from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
import logging
from pgvector.django import CosineDistance

logger = logging.getLogger(__name__)

SEMANTIC_SEARCH_TOP_K = 4
SEMANTIC_SEARCH_MAX_DISTANCE = 0.25  # cosine distance threshold — only use chunks with high semantic similarity
from django.shortcuts import get_object_or_404
from .models import ChatMessage, Conversation, UserPreference, BotConfiguration, Document, DocumentChunk
from .serializers import (
    ChatRequestSerializer, 
    ChatResponseSerializer, 
    ChatMessageSerializer, 
    ConversationSerializer,
    UserPreferenceSerializer,
    BotConfigurationSerializer
)
from .services.langchain_service import LangChainService
import uuid
from django.utils import timezone
from django.db import transaction
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import tempfile
import os


@api_view(['POST'])
def chat(request):
    """
    Send a message to the chatbot and receive a response.
    """
    serializer = ChatRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    message = serializer.validated_data['message']
    conversation_id = serializer.validated_data.get('conversation_id')
    
    # Get or create conversation
    if conversation_id:
        conversation = get_object_or_404(Conversation, id=conversation_id)
    else:
        conversation = Conversation.objects.create(
            title=f"Conversation {timezone.now().strftime('%Y-%m-%d %H:%M')}"
        )
    
    # Save user message
    user_message = ChatMessage.objects.create(
        conversation=conversation,
        sender='user',
        message=message
    )
    
    # Get response from LangChain service
    try:
        langchain_service = LangChainService()
        conversation_id_str = str(conversation.id)

        # --- Cold-start seed: last N Postgres messages for Redis miss ---
        recent_pg = (
            ChatMessage.objects
            .filter(conversation=conversation)
            .order_by('-timestamp')[:langchain_service.memory_window]
        )
        db_messages = [
            {"role": "user" if m.sender == "user" else "assistant", "content": m.message}
            for m in reversed(list(recent_pg))
        ]

        # --- Semantic search: embed the question and retrieve relevant chunks ---
        context_chunks = []
        if Document.objects.filter(status='completed').exists():
            try:
                query_embedding = langchain_service.generate_embedding(message)
                similar_chunks = (
                    DocumentChunk.objects
                    .annotate(distance=CosineDistance('embedding', query_embedding))
                    .filter(distance__lte=SEMANTIC_SEARCH_MAX_DISTANCE)
                    .order_by('distance')
                    .select_related('document')
                    [:SEMANTIC_SEARCH_TOP_K]
                )
                context_chunks = [
                    {
                        'text': c.text,
                        'file_name': c.document.file_name,
                        'chunk_index': c.chunk_index,
                        'distance': round(c.distance, 4),
                    }
                    for c in similar_chunks
                ]
                if context_chunks:
                    logger.info(f"RAG: {len(context_chunks)} chunks recuperados para la consulta")
            except Exception as e:
                logger.warning(f"Semantic search failed, falling back to plain LLM: {str(e)}")

        # --- Generate response (RAG or plain), both use Redis memory ---
        if context_chunks:
            bot_response_text = langchain_service.get_response_with_context(
                message, context_chunks,
                conversation_id=conversation_id_str,
                db_messages=db_messages,
            )
        else:
            bot_response_text = langchain_service.get_response(
                message,
                conversation_id=conversation_id_str,
                db_messages=db_messages,
            )
    except Exception as e:
        # Fallback response in case of error
        bot_response_text = "I apologize, but I encountered an error processing your request. Could you please try again?"
    
    # Save bot response
    bot_message = ChatMessage.objects.create(
        conversation=conversation,
        sender='bot',
        message=bot_response_text
    )
    
    # Update conversation's last message timestamp
    conversation.last_message_at = timezone.now()
    conversation.save()
    
    # Prepare response
    response_data = {
        'response': bot_response_text,
        'conversation_id': conversation.id,
        'timestamp': bot_message.timestamp
    }
    
    response_serializer = ChatResponseSerializer(response_data)
    return Response(response_serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
def history(request):
    """
    Retrieve the chat history for a specific conversation or all conversations.
    """
    conversation_id = request.query_params.get('conversation_id')
    
    if conversation_id:
        conversation = get_object_or_404(Conversation, id=conversation_id)
        messages = ChatMessage.objects.filter(conversation=conversation)
        serializer = ChatMessageSerializer(messages, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    else:
        # Return all conversations with metadata
        conversations = Conversation.objects.all()
        serializer = ConversationSerializer(conversations, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['DELETE'])
def clear_history(request):
    """
    Delete chat history for a specific conversation or all conversations.
    """
    conversation_id = request.data.get('conversation_id')
    
    if conversation_id:
        conversation = get_object_or_404(Conversation, id=conversation_id)
        deleted_count = conversation.messages.count()
        conversation.delete()
        return Response({
            'message': 'Chat history cleared successfully',
            'deleted_count': deleted_count
        }, status=status.HTTP_200_OK)
    else:
        # Clear all conversations
        deleted_count = ChatMessage.objects.count()
        Conversation.objects.all().delete()
        return Response({
            'message': 'All chat history cleared successfully',
            'deleted_count': deleted_count
        }, status=status.HTTP_200_OK)


@api_view(['GET'])
def conversation_detail(request, conversation_id):
    """
    Get details of a specific conversation including all messages.
    """
    conversation = get_object_or_404(Conversation, id=conversation_id)
    serializer = ConversationSerializer(conversation)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
def create_conversation(request):
    """
    Create a new conversation with optional title.
    """
    title = request.data.get('title', f"Conversation {timezone.now().strftime('%Y-%m-%d %H:%M')}")
    conversation = Conversation.objects.create(title=title)
    serializer = ConversationSerializer(conversation)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['PUT'])
def update_conversation(request, conversation_id):
    """
    Update conversation details.
    """
    conversation = get_object_or_404(Conversation, id=conversation_id)
    title = request.data.get('title')
    
    if title:
        conversation.title = title
        conversation.save()
    
    serializer = ConversationSerializer(conversation)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
def user_preferences(request, user_identifier):
    """
    Get user preferences.
    """
    try:
        preferences = UserPreference.objects.get(user_identifier=user_identifier)
    except UserPreference.DoesNotExist:
        # Create default preferences
        preferences = UserPreference.objects.create(
            user_identifier=user_identifier,
            preferred_language='en',
            tone_preference='friendly'
        )
    
    serializer = UserPreferenceSerializer(preferences)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['PUT'])
def update_user_preferences(request, user_identifier):
    """
    Update user preferences.
    """
    try:
        preferences = UserPreference.objects.get(user_identifier=user_identifier)
    except UserPreference.DoesNotExist:
        preferences = UserPreference.objects.create(user_identifier=user_identifier)
    
    serializer = UserPreferenceSerializer(preferences, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def bot_configuration(request):
    """
    Get the current bot configuration.
    """
    # Get the active configuration or create default
    config = BotConfiguration.objects.filter(is_active=True).first()
    if not config:
        config = BotConfiguration.objects.create(
            name='Default Bot',
            description='Default chatbot configuration',
            is_active=True,
            max_response_length=1000,
            temperature=0.7
        )
    
    serializer = BotConfigurationSerializer(config)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['PUT'])
def update_bot_configuration(request):
    """
    Update bot configuration.
    """
    config = BotConfiguration.objects.filter(is_active=True).first()
    if not config:
        config = BotConfiguration.objects.create(
            name='Default Bot',
            is_active=True
        )
    
    serializer = BotConfigurationSerializer(config, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def upload_text_file(request):
    """
    Upload a text file and process its content with the chatbot.
    """
    if 'file' not in request.FILES:
        return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)
    
    uploaded_file = request.FILES['file']
    
    # Check if file is a text file
    allowed_extensions = ['.txt', '.md', '.csv', '.log', '.json', '.xml']
    file_extension = os.path.splitext(uploaded_file.name)[1].lower()
    
    if file_extension not in allowed_extensions:
        return Response({'error': f'File type {file_extension} not allowed. Allowed types: {", ".join(allowed_extensions)}'},
                        status=status.HTTP_400_BAD_REQUEST)
    
    # Check file size (limit to 5MB)
    if uploaded_file.size > 5 * 1024 * 1024:
        return Response({'error': 'File size exceeds 5MB limit'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Read file content
    try:
        # Decode file content
        file_content = uploaded_file.read().decode('utf-8')
    except UnicodeDecodeError:
        return Response({'error': 'Invalid text file encoding. Please ensure file is UTF-8 encoded.'},
                        status=status.HTTP_400_BAD_REQUEST)
    
    # Process file content with LangChain service
    try:
        langchain_service = LangChainService()

        # --- Deduplication via content hash ---
        content_hash = Document.compute_hash(file_content)
        existing = Document.objects.filter(content_hash=content_hash).first()
        if existing and existing.status == 'completed':
            logger.info(f"Document already processed: {existing.id}")
            response_data = {
                'document_id': str(existing.id),
                'file_name': existing.file_name,
                'chunks_count': existing.total_chunks,
                'embedding_dim': existing.embedding_dim,
                'deduplicated': True,
            }
            return Response(response_data, status=status.HTTP_200_OK)

        # --- Create Document record (status=processing) ---
        document = Document.objects.create(
            file_name=uploaded_file.name,
            file_type=file_extension,
            file_size=uploaded_file.size,
            content_hash=content_hash,
            embedding_model=langchain_service.embedding_model,
            status='processing',
        )

        try:
            result = langchain_service.process_file_content(file_content)

            if 'error' in result:
                document.status = 'failed'
                document.save(update_fields=['status', 'updated_at'])
                return Response({'error': result['error']}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

            # --- Bulk-create DocumentChunk records ---
            chunk_objects = [
                DocumentChunk(
                    document=document,
                    chunk_index=item['chunk_index'],
                    text=item['text'],
                    embedding=item['embedding'],
                )
                for item in result['embeddings']
            ]
            DocumentChunk.objects.bulk_create(chunk_objects)

            # --- Mark Document as completed ---
            document.total_chunks = result['chunks_count']
            document.embedding_dim = result['embedding_dim']
            document.status = 'completed'
            document.save(update_fields=['total_chunks', 'embedding_dim', 'status', 'updated_at'])

            response_data = {
                'document_id': str(document.id),
                'file_name': document.file_name,
                'chunks_count': document.total_chunks,
                'embedding_dim': document.embedding_dim,
                'deduplicated': False,
            }
            return Response(response_data, status=status.HTTP_201_CREATED)

        except Exception as e:
            document.status = 'failed'
            document.save(update_fields=['status', 'updated_at'])
            raise e

    except Exception as e:
        return Response({'error': f'Error processing file: {str(e)}'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)
