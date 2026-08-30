import os
import json
import redis
from dotenv import load_dotenv
import logging
from langchain_text_splitters import RecursiveCharacterTextSplitter
import requests
from typing import List, Dict, Any, Optional

# Load environment variables
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

class LangChainService:
    def __init__(self):
        """
        Initialize LangChain service with Ollama as the primary LLM backend.
        """
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = os.getenv("OLLAMA_MODEL", "llama3")
        self.embedding_model = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
        self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))
        self.max_tokens = int(os.getenv("LLM_MAX_TOKENS", "1000"))

        # Redis memory settings
        redis_url = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
        self.memory_ttl = int(os.getenv("CONVERSATION_MEMORY_TTL", "1800"))   # 30 min
        self.memory_window = int(os.getenv("CONVERSATION_MEMORY_WINDOW", "20"))  # last N messages
        self._redis = redis.from_url(redis_url, decode_responses=True)

        # Fallback in-memory history (used when no conversation_id is provided)
        self.conversation_history: List[Dict[str, str]] = []

        # Verify Ollama connection
        self._verify_ollama_connection()

        # Text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100,
            separators=["\n\n", "\n", " ", ""]
        )

    # ------------------------------------------------------------------
    # Redis memory helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _redis_key(conversation_id: str) -> str:
        return f"chat:history:{conversation_id}"

    def _load_memory(self, conversation_id: str, db_messages: Optional[List[Dict]] = None) -> List[Dict[str, str]]:
        """
        Load conversation history for *conversation_id*.

        Strategy:
          1. Try Redis (hot path) – O(1), sub-millisecond.
          2. On cache miss, seed from *db_messages* (Postgres cold start) and push to Redis.

        Args:
            conversation_id: UUID string of the conversation.
            db_messages: Postgres ChatMessage queryset already serialised as
                         [{'role': 'user'|'assistant', 'content': '...'}].
                         Pass the most recent *memory_window* records to keep the
                         payload small.
        Returns:
            List of {role, content} dicts (sliding window).
        """
        key = self._redis_key(conversation_id)
        try:
            raw = self._redis.get(key)
            if raw:
                logger.debug(f"Memory cache HIT for conversation {conversation_id}")
                return json.loads(raw)
        except redis.RedisError as e:
            logger.warning(f"Redis read error: {e} — falling back to db_messages")

        # Cache miss – seed from Postgres
        history = db_messages or []
        history = history[-self.memory_window:]  # enforce window
        self._save_memory(conversation_id, history)
        logger.debug(f"Memory cache MISS for conversation {conversation_id} — seeded from DB ({len(history)} msgs)")
        return history

    def _save_memory(self, conversation_id: str, history: List[Dict[str, str]]) -> None:
        """
        Persist *history* to Redis with a sliding-window cap and TTL reset.
        """
        windowed = history[-self.memory_window:]
        key = self._redis_key(conversation_id)
        try:
            self._redis.setex(key, self.memory_ttl, json.dumps(windowed))
        except redis.RedisError as e:
            logger.warning(f"Redis write error: {e}")

    def invalidate_memory(self, conversation_id: str) -> None:
        """Delete the Redis cache entry for a conversation (e.g. on reset)."""
        try:
            self._redis.delete(self._redis_key(conversation_id))
        except redis.RedisError as e:
            logger.warning(f"Redis delete error: {e}")
    
    def split_user_input(self, long_text: str) -> List[str]:
        """
        Divide un texto largo en trozos manejables
        """
        chunks = self.text_splitter.split_text(long_text)
        logger.info(f"Texto dividido en {len(chunks)} fragmentos")
        return chunks
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate an embedding vector for the given text using nomic-embed-text.

        Args:
            text (str): Text to embed

        Returns:
            List[float]: Embedding vector

        Raises:
            Exception: If the Ollama embeddings API call fails
        """
        try:
            payload = {
                "model": self.embedding_model,
                "prompt": text
            }
            response = requests.post(
                f"{self.base_url}/api/embeddings",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                embedding = data.get("embedding", [])
                logger.info(f"Embedding generado: {len(embedding)} dimensiones")
                return embedding
            else:
                raise Exception(
                    f"Ollama embeddings API returned status {response.status_code}: {response.text}"
                )
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling Ollama embeddings API: {str(e)}")
            raise Exception(f"Failed to generate embedding: {str(e)}")

    def generate_embeddings_for_chunks(self, chunks: List[str]) -> List[Dict[str, Any]]:
        """
        Generate embeddings for a list of text chunks.

        Args:
            chunks (List[str]): List of text chunks

        Returns:
            List[Dict]: Each item contains 'chunk_index', 'text', and 'embedding'
        """
        results = []
        for i, chunk in enumerate(chunks):
            embedding = self.generate_embedding(chunk)
            results.append({
                "chunk_index": i,
                "text": chunk,
                "embedding": embedding
            })
            logger.info(f"Embedding generado para chunk {i + 1}/{len(chunks)}")
        return results

    def process_file_content(self, file_content: str) -> Dict[str, Any]:
        """
        Process the content of a text file: split it into chunks and generate
        an embedding vector for each chunk using nomic-embed-text.

        Args:
            file_content (str): The content of the uploaded text file

        Returns:
            Dict with 'chunks_count', 'embedding_dim', and 'embeddings' list
        """
        try:
            if not file_content.strip():
                return {"error": "The uploaded file is empty."}

            # Split into manageable chunks
            chunks = self.split_user_input(file_content)

            # Generate embeddings for every chunk
            embeddings_data = self.generate_embeddings_for_chunks(chunks)

            embedding_dim = len(embeddings_data[0]["embedding"]) if embeddings_data else 0
            logger.info(
                f"Procesados {len(embeddings_data)} chunks, dimensión de embedding: {embedding_dim}"
            )

            return {
                "chunks_count": len(embeddings_data),
                "embedding_dim": embedding_dim,
                "embeddings": embeddings_data
            }

        except Exception as e:
            logger.error(f"Error processing file content: {str(e)}")
            return {"error": f"Error procesando el archivo: {str(e)}"}
    
    def _verify_ollama_connection(self):
        """
        Verify that Ollama is running and accessible.
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                logger.info("Successfully connected to Ollama")
                return True
            else:
                logger.warning(f"Ollama connection failed with status code: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to connect to Ollama: {str(e)}")
            return False
    
    def _format_history(self, history: List[Dict[str, str]]) -> str:
        """Format a history list into a readable string for the prompt."""
        formatted = ""
        for message in history:
            if message['role'] == 'user':
                formatted += f"Human: {message['content']}\n"
            elif message['role'] == 'assistant':
                formatted += f"AI Assistant: {message['content']}\n"
        return formatted

    def _format_conversation_history(self) -> str:
        """Format in-memory history (backward-compat helper)."""
        return self._format_history(self.conversation_history)
    
    def _generate_prompt(self, user_input: str, history: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Generate the complete prompt with conversation history.
        """
        formatted = self._format_history(history or self.conversation_history)

        prompt = f"""You are an AI assistant helping users with their questions and tasks.
Your responses should be:
1. Accurate and informative
2. Friendly and approachable
3. Concise but complete
4. Relevant to the user's question

Current conversation:
{formatted}
Human: {user_input}
AI Assistant:"""
        return prompt.strip()
    
    def _call_ollama_api(self, prompt: str) -> str:
        """
        Call the Ollama API to generate a response.
        
        Args:
            prompt (str): The complete prompt for the LLM
            
        Returns:
            str: Response from the LLM
            
        Raises:
            Exception: If the API call fails
        """
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens
                }
            }
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("response", "").strip()
            else:
                raise Exception(f"Ollama API returned status code {response.status_code}: {response.text}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling Ollama API: {str(e)}")
            raise Exception(f"Failed to communicate with Ollama: {str(e)}")
        except Exception as e:
            logger.error(f"Error processing Ollama response: {str(e)}")
            raise e
    
    def get_response_with_context(
        self,
        user_input: str,
        context_chunks: List[Dict[str, Any]],
        conversation_id: Optional[str] = None,
        db_messages: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """
        Generate a response using retrieved document chunks as context (RAG).

        Args:
            user_input: The user’s question.
            context_chunks: Relevant chunks from the vector store.
                Each dict must have at least ‘text’ and optionally ‘file_name’.
            conversation_id: Optional UUID string; used to read/write Redis memory.
            db_messages: Postgres cold-start seed (only used on Redis miss).

        Returns:
            The AI’s response grounded on the provided context.
        """
        try:
            # Load memory (Redis → Postgres fallback)
            if conversation_id:
                history = self._load_memory(conversation_id, db_messages)
            else:
                history = self.conversation_history

            # Build numbered context block
            context_block = ""
            for i, chunk in enumerate(context_chunks, start=1):
                source = chunk.get("file_name", "documento")
                context_block += f"[{i}] (fuente: {source})\n{chunk['text']}\n\n"

            formatted_history = self._format_history(history)

            prompt = f"""Eres un asistente experto que responde preguntas basándose EXCLUSIVAMENTE en los fragmentos de documentos proporcionados a continuación.
Si la respuesta no se encuentra en los fragmentos, indícalo claramente en lugar de inventar información.
Cita la fuente entre corchetes cuando uses información de un fragmento específico.

FRAGMENTOS RELEVANTES:
{context_block}
CONVERSACIÓN ACTUAL:
{formatted_history}
Pregunta del usuario: {user_input}
Respuesta:"""

            response = self._call_ollama_api(prompt.strip())

            # Update memory
            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": response})
            if conversation_id:
                self._save_memory(conversation_id, history)
            else:
                self.conversation_history = history

            return response

        except Exception as e:
            logger.error(f"Error in get_response_with_context: {str(e)}")
            return "Lo siento, ocurrió un error al procesar tu pregunta con el contexto disponible."

    def get_response(
        self,
        user_input: str,
        conversation_id: Optional[str] = None,
        db_messages: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """
        Process user input and generate a response using Ollama.

        Args:
            user_input: The user’s message.
            conversation_id: Optional UUID string; used to read/write Redis memory.
            db_messages: Postgres cold-start seed (only used on Redis miss).

        Returns:
            The AI’s response.
        """
        try:
            # Load memory (Redis → Postgres fallback)
            if conversation_id:
                history = self._load_memory(conversation_id, db_messages)
            else:
                history = self.conversation_history

            prompt = self._generate_prompt(user_input, history)
            response = self._call_ollama_api(prompt)

            # Update memory
            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": response})
            if conversation_id:
                self._save_memory(conversation_id, history)
            else:
                self.conversation_history = history

            return response

        except Exception as e:
            logger.error(f"Error in LangChainService.get_response: {str(e)}")
            return "I apologize, but I encountered an error processing your request. Could you please try again?"
    
    def reset_conversation(self, conversation_id: Optional[str] = None):
        """
        Reset conversation memory.
        Clears Redis entry if conversation_id is provided, otherwise clears in-memory history.
        """
        if conversation_id:
            self.invalidate_memory(conversation_id)
            logger.info(f"Redis memory cleared for conversation {conversation_id}")
        else:
            self.conversation_history = []
            logger.info("In-memory conversation history reset")
    
    def set_temperature(self, temperature: float):
        """
        Update the LLM temperature setting.
        
        Args:
            temperature (float): New temperature value (0.0 to 1.0)
        """
        self.temperature = max(0.0, min(1.0, temperature))  # Clamp between 0 and 1
        logger.info(f"Temperature set to {self.temperature}")
    
    def set_max_tokens(self, max_tokens: int):
        """
        Update the LLM max tokens setting.
        
        Args:
            max_tokens (int): New max tokens value
        """
        self.max_tokens = max(1, min(4096, max_tokens))  # Clamp between 1 and 4096
        logger.info(f"Max tokens set to {self.max_tokens}")
    
    def set_model(self, model: str):
        """
        Update the LLM model setting.
        
        Args:
            model (str): New model name
        """
        self.model = model
        logger.info(f"Model set to {self.model}")