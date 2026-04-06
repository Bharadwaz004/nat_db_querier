import React, { useState, useEffect, useRef, useCallback } from 'react';
import Sidebar from './components/Sidebar';
import ChatMessage from './components/ChatMessage';
import ConnectionModal from './components/ConnectionModal';
import {
  loginAsGuest,
  setToken,
  createSession,
  sendQuery,
  getSchema,
  connectDb,
  uploadDb,
} from './hooks/api';

const EXAMPLE_QUERIES = [
  'What are the top 5 best-selling products?',
  'Show me customers who spent more than $500',
  'Which product category has the highest average rating?',
  'List orders from last month with their items',
  'What is the total revenue by payment method?',
  'Which products are running low on inventory?',
];

export default function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [schema, setSchema] = useState(null);
  const [connected, setConnected] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [showModal, setShowModal] = useState(true);
  const [initError, setInitError] = useState('');
  const chatRef = useRef(null);
  const inputRef = useRef(null);

  // Auto-scroll chat to bottom
  useEffect(() => {
    if (chatRef.current) {
      chatRef.current.scrollTop = chatRef.current.scrollHeight;
    }
  }, [messages, loading]);

  // Initialize: get guest token
  const init = useCallback(async () => {
    try {
      const authData = await loginAsGuest();
      setToken(authData.token);
      const sess = await createSession();
      setSessionId(sess.sessionId);
    } catch (e) {
      setInitError('Failed to connect to API gateway. Is the server running?');
    }
  }, []);

  useEffect(() => {
    init();
  }, [init]);

  // Load schema after connection
  const loadSchema = async () => {
    try {
      const data = await getSchema();
      setSchema(data.tables);
      setConnected(true);
    } catch (e) {
      console.error('Schema load failed:', e);
    }
  };

  // Handle DB connection options
  const handleUseSample = async () => {
    setShowModal(false);
    await loadSchema();
  };

  const handleConnect = async (path) => {
    await connectDb(path);
    setShowModal(false);
    await loadSchema();
  };

  const handleUpload = async (file) => {
    await uploadDb(file);
    setShowModal(false);
    await loadSchema();
  };

  // Send query
  const handleSend = async (queryText) => {
    const query = (queryText || input).trim();
    if (!query || loading) return;

    // Add user message
    setMessages((prev) => [...prev, { role: 'user', content: query }]);
    setInput('');
    setLoading(true);

    try {
      const result = await sendQuery(query, sessionId);
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', data: result },
      ]);
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', data: { error: e.message, nl_answer: '', sql: '', explanation: '', results: {}, tables_used: [], retries: 0 } },
      ]);
    }

    setLoading(false);
    inputRef.current?.focus();
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="app-container">
      {showModal && (
        <ConnectionModal
          onConnect={handleConnect}
          onUpload={handleUpload}
          onUseSample={handleUseSample}
        />
      )}

      <Sidebar schema={schema} connected={connected} />

      <main className="main-area">
        <div className="chat-container" ref={chatRef}>
          {initError && (
            <div className="error-msg" style={{ margin: 20 }}>{initError}</div>
          )}

          {messages.length === 0 && !loading && (
            <div className="welcome-screen">
              <h2>Ask your database anything</h2>
              <p>
                Type a natural language question and the AI will generate SQL,
                execute it, and explain the results — all powered by hybrid
                vector + graph RAG retrieval.
              </p>
              <div className="example-queries">
                {EXAMPLE_QUERIES.map((q) => (
                  <button
                    key={q}
                    className="example-btn"
                    onClick={() => handleSend(q)}
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <ChatMessage key={i} message={msg} />
          ))}

          {loading && (
            <div className="message message-assistant">
              <div className="loading-dots">
                <span /><span /><span />
              </div>
            </div>
          )}
        </div>

        <div className="input-area">
          <div className="input-wrapper">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={connected ? 'Ask a question about your database…' : 'Connect a database to get started…'}
              disabled={!connected || loading}
              rows={1}
            />
            <button
              className="send-btn"
              onClick={() => handleSend()}
              disabled={!connected || loading || !input.trim()}
            >
              {loading ? '⏳' : 'Send'}
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
