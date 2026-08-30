import pytest
from unittest.mock import patch, MagicMock


class TestLangChainService:
    def test_import_langchain_service(self):
        """Test that we can import the LangChainService without errors."""
        try:
            from ..services.langchain_service import LangChainService
            service_class = LangChainService
            assert service_class is not None
        except ImportError as e:
            pytest.skip(f"LangChain not available: {e}")
            
    @patch('chatbot_app.services.langchain_service.ChatOpenAI')
    @patch('chatbot_app.services.langchain_service.PromptTemplate')
    @patch('chatbot_app.services.langchain_service.ConversationBufferMemory')
    @patch('chatbot_app.services.langchain_service.LLMChain')
    def test_langchain_service_initialization(self, mock_chain, mock_memory, mock_prompt, mock_llm):
        """Test that LangChainService initializes correctly with mocks."""
        mock_llm_instance = MagicMock()
        mock_llm.return_value = mock_llm_instance
        
        mock_prompt_instance = MagicMock()
        mock_prompt.from_template.return_value = mock_prompt_instance
        
        mock_memory_instance = MagicMock()
        mock_memory.return_value = mock_memory_instance
        
        mock_chain_instance = MagicMock()
        mock_chain.return_value = mock_chain_instance
        
        # Import after patching
        from ..services.langchain_service import LangChainService
        service = LangChainService()
        
        # Verify that the components were created
        assert service.llm == mock_llm_instance
        assert service.memory == mock_memory_instance
        assert service.chain == mock_chain_instance
        
    @patch('chatbot_app.services.langchain_service.ChatOpenAI')
    @patch('chatbot_app.services.langchain_service.PromptTemplate')
    @patch('chatbot_app.services.langchain_service.ConversationBufferMemory')
    @patch('chatbot_app.services.langchain_service.LLMChain')
    def test_get_response_success(self, mock_chain, mock_memory, mock_prompt, mock_llm):
        """Test successful response generation."""
        # Setup mocks
        mock_chain_instance = MagicMock()
        mock_chain_instance.run.return_value = "Test response"
        mock_chain.return_value = mock_chain_instance
        
        # Import and create service
        from ..services.langchain_service import LangChainService
        service = LangChainService()
        
        # Test the method
        response = service.get_response("Hello")
        assert response == "Test response"
        
    @patch('chatbot_app.services.langchain_service.ChatOpenAI')
    @patch('chatbot_app.services.langchain_service.PromptTemplate')
    @patch('chatbot_app.services.langchain_service.ConversationBufferMemory')
    @patch('chatbot_app.services.langchain_service.LLMChain')
    def test_get_response_with_exception(self, mock_chain, mock_memory, mock_prompt, mock_llm):
        """Test response generation when an exception occurs."""
        # Setup mocks to raise an exception
        mock_chain_instance = MagicMock()
        mock_chain_instance.run.side_effect = Exception("Test error")
        mock_chain.return_value = mock_chain_instance
        
        # Import and create service
        from ..services.langchain_service import LangChainService
        service = LangChainService()
        
        # Test the method
        response = service.get_response("Hello")
        assert "I apologize, but I encountered an error processing your request" in response