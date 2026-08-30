import { useState, useRef, useEffect } from 'react';
import { useSendMessage, useUploadFile } from './hooks/useChat';
import Spinner from './components/Spinner';

function App() {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const messagesEndRef = useRef(null);
  const { mutateAsync: sendMessage, isPending: isLoading } = useSendMessage();
  const { mutateAsync: uploadFile, isPending: isUploading } = useUploadFile();
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async () => {
    if (inputValue.trim() === '') return;

    // Add user message
    const userMessage = {
      id: Date.now(),
      text: inputValue,
      sender: 'user'
    };
    
    setMessages(prev => [...prev, userMessage]);
    setInputValue('');

    try {
      // Send message to backend using TanStack Query
      const data = await sendMessage(inputValue);
      
      // Add bot response
      const botMessage = {
        id: Date.now() + 1,
        text: data.response,
        sender: 'bot'
      };
      
      setMessages(prev => [...prev, botMessage]);
    } catch (error) {
      console.error('Error:', error);
      const errorMessage = {
        id: Date.now() + 1,
        text: error.message || 'Error al comunicarse con el servidor. Por favor, inténtalo de nuevo.',
        sender: 'bot'
      };
      setMessages(prev => [...prev, errorMessage]);
    }
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    // Add file info to messages
    const fileInfoMessage = {
      id: Date.now(),
      text: `Uploading file: ${file.name}`,
      sender: 'user'
    };
    
    setMessages(prev => [...prev, fileInfoMessage]);
    setSelectedFile(file);

    try {
      // Upload file to backend using TanStack Query
      const data = await uploadFile(file);

      const botMessage = {
        id: Date.now() + 1,
        sender: 'bot',
        type: 'embedding',
        embeddingData: data,
      };

      setMessages(prev => [...prev, botMessage]);
    } catch (error) {
      console.error('Error:', error);
      const errorMessage = {
        id: Date.now() + 1,
        text: error.message || 'Error al cargar el archivo. Por favor, inténtalo de nuevo.',
        sender: 'bot'
      };
      setMessages(prev => [...prev, errorMessage]);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="flex flex-col min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      {/* Header */}
      <header className="bg-white shadow-sm py-4 px-6">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-full bg-gradient-to-r from-blue-500 to-purple-600 flex items-center justify-center">
              <span className="text-white font-bold text-lg">C</span>
            </div>
            <h1 className="text-xl font-semibold text-gray-800">Chatbot</h1>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 rounded-full bg-green-500"></div>
            <span className="text-sm text-gray-500">En línea</span>
          </div>
        </div>
      </header>

      {/* Main chat area */}
      <main className="flex-1 py-6 px-4 max-w-4xl mx-auto w-full">
        <div className="bg-white rounded-2xl shadow-lg overflow-hidden flex flex-col h-[calc(100vh-180px)]">
          {/* Messages container */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gradient-to-b from-white to-gray-50">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center text-gray-500">
                <div className="w-16 h-16 rounded-full bg-gradient-to-r from-blue-500 to-purple-600 flex items-center justify-center mb-4 mx-auto">
                  <span className="text-white font-bold text-2xl">C</span>
                </div>
                <h2 className="text-2xl font-medium text-gray-700 mb-2">¡Hola! ¿En qué puedo ayudarte?</h2>
                <p className="text-gray-500 max-w-md">
                  Soy tu asistente virtual. Puedes preguntarme cualquier cosa y haré mi mejor esfuerzo por ayudarte.
                </p>
              </div>
            ) : (
              messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  {message.type === 'embedding' ? (
                    <div className="max-w-[90%] rounded-2xl rounded-bl-none bg-gray-100 text-gray-800 px-4 py-3 space-y-2">
                      <div className="flex items-center space-x-2">
                        <span className="text-green-600 font-semibold text-sm">✅ Documento procesado y guardado</span>
                        {message.embeddingData.deduplicated && (
                          <span className="text-xs bg-yellow-100 text-yellow-700 px-2 py-0.5 rounded-full">ya existía</span>
                        )}
                      </div>
                      <div className="text-xs text-gray-500 space-y-1">
                        <div><span className="font-medium text-gray-700">Archivo:</span> {message.embeddingData.file_name}</div>
                        <div><span className="font-medium text-gray-700">Chunks:</span> {message.embeddingData.chunks_count}</div>
                        <div><span className="font-medium text-gray-700">Dimensión del embedding:</span> {message.embeddingData.embedding_dim}</div>
                        <div className="font-mono text-[10px] text-gray-400 break-all">
                          ID: {message.embeddingData.document_id}
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div
                      className={`max-w-[85%] rounded-2xl px-4 py-3 ${
                        message.sender === 'user'
                          ? 'bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-br-none'
                          : 'bg-gray-100 text-gray-800 rounded-bl-none'
                      }`}
                    >
                      <div className="whitespace-pre-wrap">{message.text}</div>
                    </div>
                  )}
                </div>
              ))
            )}
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-gray-100 text-gray-800 rounded-2xl rounded-bl-none px-4 py-3 max-w-[85%]">
                  <Spinner />
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
          
          {/* Input area */}
          <div className="border-t border-gray-200 p-4 bg-white">
            <div className="flex items-end space-x-2">
              <label className="flex items-center justify-center h-12 w-12 rounded-full bg-gray-200 text-gray-400 hover:bg-gray-300 cursor-pointer transition-all duration-200">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
                  <path d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                </svg>
                <input
                  type="file"
                  className="hidden"
                  accept=".txt,.md,.csv,.log,.json,.xml"
                  onChange={handleFileUpload}
                  disabled={isUploading}
                />
              </label>
              <textarea
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Escribe tu mensaje aquí..."
                className="flex-1 border border-gray-300 rounded-2xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                rows="1"
              />
              <button
                onClick={handleSendMessage}
                disabled={!inputValue.trim() || isLoading}
                className={`h-12 w-12 rounded-full flex items-center justify-center ${
                  inputValue.trim() && !isLoading
                    ? 'bg-gradient-to-r from-blue-500 to-blue-600 text-white hover:from-blue-600 hover:to-blue-700'
                    : 'bg-gray-200 text-gray-400'
                } transition-all duration-200 ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
                  <path d="M3.478 2.405a.75.75 0 00-.926.94l2.432 7.905H13.5a.75.75 0 010 1.5H4.984l-2.432 7.905a.75.75 0 00.926.94 60.519 60.519 0 0018.445-8.986.75.75 0 000-1.218A60.517 60.517 0 003.478 2.405z" />
                </svg>
              </button>
            </div>
            <div className="mt-2 text-xs text-gray-500 text-center">
              Presiona Enter para enviar, Shift + Enter para nueva línea
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
