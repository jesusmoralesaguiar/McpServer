import uuid
import hashlib
from django.db import models
from pgvector.django import VectorField, IvfflatIndex, HnswIndex


class Conversation(models.Model):
    """
    Represents a conversation thread between a user and the chatbot.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_message_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Conversation {self.id} - {self.title or 'Untitled'}"

    class Meta:
        ordering = ['-last_message_at']
        verbose_name = "Conversation"
        verbose_name_plural = "Conversations"


class ChatMessage(models.Model):
    """
    Represents individual messages within a conversation.
    """
    SENDER_CHOICES = (
        ('user', 'User'),
        ('bot', 'Bot'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation, 
        on_delete=models.CASCADE, 
        related_name='messages'
    )
    sender = models.CharField(max_length=10, choices=SENDER_CHOICES)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.sender}: {self.message[:50]}..."

    class Meta:
        ordering = ['timestamp']
        verbose_name = "Chat Message"
        verbose_name_plural = "Chat Messages"

# Create your models here.
class UserPreference(models.Model):
    """
    Stores user-specific preferences for the chatbot experience.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # In a real app, this would link to a User model
    user_identifier = models.CharField(max_length=255, unique=True)
    preferred_language = models.CharField(max_length=10, default='en')
    tone_preference = models.CharField(
        max_length=20,
        choices=[
            ('friendly', 'Friendly'),
            ('professional', 'Professional'),
            ('casual', 'Casual'),
        ],
        default='friendly'
    )
    enable_notifications = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Preferences for {self.user_identifier}"

    class Meta:
        verbose_name = "User Preference"
        verbose_name_plural = "User Preferences"


class BotConfiguration(models.Model):
    """
    Configuration settings for the chatbot behavior.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, default='Default Bot')
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    max_response_length = models.IntegerField(default=1000)
    temperature = models.FloatField(default=0.7)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Bot Configuration"
        verbose_name_plural = "Bot Configurations"


class Document(models.Model):
    """
    Represents an uploaded document whose text has been chunked and embedded.
    Acts as the root node when Neo4j is integrated (neo4j_node_id bridges both stores).
    """

    STATUS_CHOICES = (
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file_name = models.CharField(max_length=512)
    file_type = models.CharField(max_length=20, blank=True)  # e.g. .txt, .pdf
    file_size = models.PositiveIntegerField(default=0)       # bytes
    content_hash = models.CharField(max_length=64, unique=True, db_index=True)  # SHA-256

    embedding_model = models.CharField(max_length=100, default='nomic-embed-text')
    embedding_dim = models.PositiveIntegerField(default=768)
    total_chunks = models.PositiveIntegerField(default=0)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='processing')

    # Optional link to the conversation that triggered the upload
    conversation = models.ForeignKey(
        'Conversation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documents',
    )

    # Bridge field for future Neo4j integration
    neo4j_node_id = models.CharField(max_length=128, blank=True, null=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.file_name} ({self.status})"

    @staticmethod
    def compute_hash(content: str) -> str:
        """Return SHA-256 hex digest of the given text content."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Document'
        verbose_name_plural = 'Documents'


class DocumentChunk(models.Model):
    """
    A single text fragment of a Document together with its embedding vector.
    Maps 1-to-1 with a future Neo4j Chunk node (neo4j_node_id bridges both stores).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='chunks',
    )
    chunk_index = models.PositiveIntegerField()      # 0-based order within document
    text = models.TextField()
    char_count = models.PositiveIntegerField(default=0)

    # pgvector field — dimension matches nomic-embed-text (768)
    embedding = VectorField(dimensions=768, null=True, blank=True)

    # Bridge field for future Neo4j integration
    neo4j_node_id = models.CharField(max_length=128, blank=True, null=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        self.char_count = len(self.text)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.document.file_name} — chunk {self.chunk_index}"

    class Meta:
        ordering = ['document', 'chunk_index']
        unique_together = [['document', 'chunk_index']]
        verbose_name = 'Document Chunk'
        verbose_name_plural = 'Document Chunks'
        indexes = [
            # HNSW index for fast approximate nearest-neighbour search
            HnswIndex(
                name='chunk_embedding_hnsw_idx',
                fields=['embedding'],
                m=16,
                ef_construction=64,
                opclasses=['vector_cosine_ops'],
            ),
        ]