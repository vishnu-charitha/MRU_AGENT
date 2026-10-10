import React, { useState, useRef, useEffect } from 'react';
import {
  Send,
  Minus,
  Maximize2,
  X,
  GraduationCap,
  Building2,
  Wallet,
  MapPin,
  Calendar,
  Briefcase,
  Paperclip,
  Phone,
  Share2,
  Search,
  ArrowRight,
  Menu,
  ExternalLink,
  RefreshCw,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import './App.css';

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

const formatMessageContent = (text) => {
  if (!text) return null;

  const paragraphs = text.split(/\n\s*\n/).filter((p) => p.trim());

  const renderBoldText = (value) => {
    const parts = value.split(/(\*\*.*?\*\*)/g);

    return parts.map((part, index) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={index}>{part.slice(2, -2)}</strong>;
      }
      return part;
    });
  };

  return paragraphs.map((paragraph, paragraphIndex) => {
    const lines = paragraph.split('\n').filter((line) => line.trim());

    const isBulletList = lines.every((line) =>
      /^\s*[-*•]\s+/.test(line)
    );

    if (isBulletList) {
      return (
        <ul
          key={paragraphIndex}
          style={{ paddingLeft: '20px', margin: '8px 0' }}
        >
          {lines.map((line, index) => (
            <li key={index} style={{ marginBottom: '4px' }}>
              {renderBoldText(line.replace(/^\s*[-*•]\s+/, ''))}
            </li>
          ))}
        </ul>
      );
    }

    return (
      <p key={paragraphIndex} style={{ margin: '8px 0' }}>
        {lines.map((line, index) => (
          <React.Fragment key={index}>
            {index > 0 && <br />}
            {renderBoldText(line)}
          </React.Fragment>
        ))}
      </p>
    );
  });
};

function App() {
  const initialWelcome = {
    id: 'welcome',
    role: 'assistant',
    content:
      'Welcome to MRDU Assistant 👋\n\nI can help you find information about MRDU admissions, departments, fees, examinations, regulations, campus facilities and academic services.',
  };

  const [messages, setMessages] = useState([initialWelcome]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const requestInProgressRef = useRef(false);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading, isStreaming]);

  const handleSend = async (question) => {
    const trimmedQuestion = question.trim();

    if (!trimmedQuestion || requestInProgressRef.current) return;

    requestInProgressRef.current = true;

    const chatHistory = messages
      .filter((message) => message.id !== 'welcome' && !message.isError)
      .map((message) => ({
        role: message.role,
        content: message.content,
        followUpQuestions: message.followUpQuestions || undefined,
      }));

    const userMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: trimmedQuestion,
    };

    const assistantMessageId = `${Date.now() + 1}`;

    setMessages((previous) => [...previous, userMessage]);
    setInput('');
    setIsLoading(true);
    setIsStreaming(false);

    let accumulatedContent = '';
    let accumulatedSources = [];
    let accumulatedFollowUps = [];

    const updateAssistantMessage = ({
      content = accumulatedContent,
      sources = accumulatedSources,
      followUpQuestions = accumulatedFollowUps,
      outOfScope,
      isError = false,
    } = {}) => {
      accumulatedContent = content;
      accumulatedSources = sources;
      accumulatedFollowUps = followUpQuestions;

      const assistantMessage = {
        id: assistantMessageId,
        role: 'assistant',
        content: accumulatedContent,
        sources: accumulatedSources,
        followUpQuestions: accumulatedFollowUps,
        isError,
      };

      if (typeof outOfScope === 'boolean') {
        assistantMessage.out_of_scope = outOfScope;
      }

      setMessages((previous) => {
        const exists = previous.some(
          (message) => message.id === assistantMessageId
        );

        if (!exists) {
          return [...previous, assistantMessage];
        }

        return previous.map((message) =>
          message.id === assistantMessageId
            ? assistantMessage
            : message
        );
      });
    };

    try {
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: trimmedQuestion,
          history: chatHistory,
        }),
      });

      if (!response.ok) {
        let errorMessage =
          'Unable to connect to MRDU Assistant. Please try again later.';

        try {
          const errorData = await response.json();

          if (errorData.detail) {
            errorMessage =
              typeof errorData.detail === 'string'
                ? errorData.detail
                : JSON.stringify(errorData.detail);
          } else if (errorData.error) {
            errorMessage = errorData.error;
          }
        } catch {
          // Use the default error message.
        }

        throw new Error(errorMessage);
      }

      if (!response.body) {
        throw new Error('The server returned an empty response stream.');
      }

      setIsLoading(false);
      setIsStreaming(true);

      updateAssistantMessage();

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      const processLine = (line) => {
        if (!line.trim()) return;

        try {
          const data = JSON.parse(line);

          if (data.error || data.detail) {
            const errorText = data.error || data.detail;

            updateAssistantMessage({
              content:
                typeof errorText === 'string'
                  ? errorText
                  : JSON.stringify(errorText),
              sources: [],
              followUpQuestions: [],
              isError: true,
            });

            return;
          }

          if (
            data.type === 'followup_questions' &&
            Array.isArray(data.questions)
          ) {
            accumulatedFollowUps = data.questions;
          }

          if (Array.isArray(data.sources)) {
            accumulatedSources = data.sources;
          }

          if (data.clear_sources) {
            accumulatedSources = [];
            accumulatedFollowUps = [];
          }

          if (typeof data.out_of_scope === 'boolean') {
            updateAssistantMessage({
              outOfScope: data.out_of_scope,
            });
          }

          if (typeof data.answer === 'string') {
            accumulatedContent = data.answer;
          } else if (typeof data.answer_chunk === 'string') {
            accumulatedContent += data.answer_chunk;
          }

          updateAssistantMessage();
        } catch (error) {
          console.error('Error parsing chatbot response line:', error, line);
        }
      };

      while (true) {
        const { value, done } = await reader.read();

        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          processLine(line);
        }
      }

      buffer += decoder.decode();

      if (buffer.trim()) {
        processLine(buffer);
      }
    } catch (error) {
      console.error('MRDU Assistant error:', error);

      const errorMessage =
        error instanceof Error
          ? error.message
          : 'Unable to connect to MRDU Assistant. Please make sure the backend server is running.';

      setMessages((previous) => [
        ...previous,
        {
          id: `${Date.now()}-error`,
          role: 'assistant',
          content: errorMessage,
          isError: true,
        },
      ]);
    } finally {
      setIsLoading(false);
      setIsStreaming(false);
      requestInProgressRef.current = false;

      if (window.innerWidth > 1024) {
        setTimeout(() => inputRef.current?.focus(), 100);
      }
    }
  };

  const resetChat = () => {
    if (messages.length > 2) {
      if (!window.confirm('Are you sure you want to clear this conversation?')) {
        return;
      }
    }

    setMessages([initialWelcome]);
    setInput('');
  };

  const quickQuestions = [
    {
      text: 'B.Tech Admissions',
      icon: <GraduationCap size={16} />,
      query: 'What are the B.Tech admission eligibility requirements?',
    },
    {
      text: 'Departments',
      icon: <Building2 size={16} />,
      query: 'What departments are available at MRDU?',
    },
    {
      text: 'Fees Structure',
      icon: <Wallet size={16} />,
      query: 'What are the B.Tech fees?',
    },
    {
      text: 'Tirupati Campus',
      icon: <MapPin size={16} />,
      query: 'What information is available about the Tirupati campus?',
    },
    {
      text: 'Examinations',
      icon: <Calendar size={16} />,
      query: 'What is the examination timetable?',
    },
    {
      text: 'Regulations',
      icon: <Briefcase size={16} />,
      query: 'What is the MR24 regulation?',
    },
  ];

  const lastUserMessage = [...messages]
    .reverse()
    .find((message) => message.role === 'user');

  const handleRetry = () => {
    if (lastUserMessage) {
      handleSend(lastUserMessage.content);
    }
  };

  return (
    <>
      <header>
        <div className="top-nav">
          <div className="top-nav-left">
            <a href="#">Home</a>
            <a href="#">About</a>
            <a href="#">Placements</a>
            <a href="#">Alumni</a>
            <a href="#">Contact</a>
          </div>

          <div className="top-nav-right">
            <a href="#" className="apply-btn" aria-label="Apply Now">
              APPLY NOW
            </a>

            <div className="social-icons" aria-label="Social Links">
              <Phone size={14} style={{ cursor: 'pointer' }} aria-label="Phone" />
              <Share2 size={14} style={{ cursor: 'pointer' }} aria-label="Share" />
              <Search size={14} style={{ cursor: 'pointer' }} aria-label="Search" />
            </div>
          </div>
        </div>

        <div className="main-nav">
          <div className="logo-section">
            <img
              src="/mrdu-logo.svg"
              alt="MRDU Official Logo"
              className="logo-img"
            />

            <div className="logo-text">
              <h1>Malla Reddy (MR)</h1>
              <p>DEEMED TO BE UNIVERSITY</p>
            </div>
          </div>

          <button
            className="mobile-menu-btn"
            onClick={() => setIsMobileMenuOpen((open) => !open)}
            aria-label="Toggle Navigation Menu"
            aria-expanded={isMobileMenuOpen}
          >
            <Menu size={24} />
          </button>

          <nav
            className={`nav-links ${isMobileMenuOpen ? 'active' : ''}`}
            aria-label="Main Navigation"
          >
            <a href="#">Governance</a>
            <a href="#">Accreditations</a>
            <a href="#">Academics</a>
            <a href="#">Admissions</a>
            <a href="#">Research</a>
            <a href="#">Examinations</a>
            <a href="#">Life @ MRDU</a>
            <a href="#">Archives</a>
            <a href="#">Campuses</a>
          </nav>
        </div>
      </header>

      <main className="hero-container">
        <video
          className="hero-video"
          autoPlay
          loop
          muted
          playsInline
          preload="auto"
          aria-hidden="true"
        >
          <source src="/video.mp4" type="video/mp4" />
        </video>

        <div className="hero-video-overlay"></div>

        <motion.div
          className="hero-content"
          initial={{ opacity: 0, x: -30 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6 }}
        >
          <div className="hero-label">MRDU OFF CAMPUS</div>

          <h1 className="hero-title">
            <span>TIRUPATI</span>
          </h1>

          <h2 className="hero-subtitle">
            AI-Powered College Knowledge Assistant
          </h2>

          <p className="hero-desc">
            Get instant answers about admissions, departments, fees,
            examinations, regulations, campus information and academic services.
          </p>

          <div className="hero-buttons">
            <button className="btn-primary" aria-label="Explore MRDU">
              Explore MRDU <ArrowRight size={18} />
            </button>

            <button className="btn-secondary" aria-label="Ask MRDU Assistant">
              Ask MRDU Assistant
            </button>
          </div>

          <div className="hero-stats">
            <div className="stat-item"><p>Programs</p></div>
            <div className="stat-item"><p>Students</p></div>
            <div className="stat-item"><p>Placement</p></div>
          </div>
        </motion.div>

        <motion.div
          className="chatbot-panel"
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          aria-label="Chatbot Assistant"
        >
          <div className="chatbot-header">
            <div className="chat-header-left">
              <img src="/mrdu-logo.svg" alt="Avatar" className="chat-avatar" />

              <div className="chat-title">
                <div className="chat-title-row">
                  <h3>MRDU Assistant</h3>
                  <span className="status-indicator" title="Online" />
                </div>
                <p>Your College Knowledge Assistant</p>
              </div>
            </div>

            <div className="chat-header-right">
              <button
                className="new-chat-btn"
                onClick={resetChat}
                title="Start a new conversation"
                aria-label="New Chat"
              >
                <RefreshCw size={16} />
              </button>

              <button aria-label="Minimize" type="button">
                <Minus size={16} />
              </button>
              <button aria-label="Maximize" type="button">
                <Maximize2 size={16} />
              </button>
              <button aria-label="Close" type="button">
                <X size={16} />
              </button>
            </div>
          </div>

          <div className="chat-body">
            <AnimatePresence>
              {messages.map((message) => (
                <motion.div
                  key={message.id}
                  className={`message ${message.role}`}
                  initial={{ opacity: 0, y: 10, scale: 0.98 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  transition={{ duration: 0.2 }}
                >
                  <div
                    className={`msg-bubble ${
                      message.isError ? 'error-bubble' : ''
                    }`}
                  >
                    {formatMessageContent(message.content)}

                    {message.out_of_scope && (
                      <div className="out-of-scope-warning">
                        This topic is outside the current MRDU knowledge scope.
                      </div>
                    )}

                    {message.sources && message.sources.length > 0 && (
                      <div className="sources-container">
                        <div className="sources-title">Sources</div>

                        <div className="sources-list">
                          {message.sources.map((source, index) => {
                            const hasUrl =
                              source.url &&
                              source.url !== 'Unknown URL' &&
                              source.url !== '#';

                            return (
                              <a
                                key={index}
                                href={hasUrl ? source.url : '#'}
                                target={hasUrl ? '_blank' : '_self'}
                                rel="noreferrer"
                                className="source-chip"
                                title={source.title || 'Source'}
                                onClick={(event) => {
                                  if (!hasUrl) event.preventDefault();
                                }}
                              >
                                <span className="source-chip-text">
                                  {source.title || 'Source'}
                                </span>
                                {hasUrl && <ExternalLink size={10} />}
                              </a>
                            );
                          })}
                        </div>
                      </div>
                    )}

                    {message.followUpQuestions &&
                      message.followUpQuestions.length > 0 && (
                        <div className="followups-container">
                          <div className="followups-title">
                            Suggested questions
                          </div>

                          <div className="followups-list">
                            {message.followUpQuestions.map((question, index) => (
                              <button
                                key={index}
                                className="followup-chip"
                                onClick={() => handleSend(question)}
                                disabled={isLoading || isStreaming}
                              >
                                {question}
                              </button>
                            ))}
                          </div>
                        </div>
                      )}

                    {message.isError && (
                      <button
                        className="retry-btn"
                        onClick={handleRetry}
                        disabled={isLoading || isStreaming || !lastUserMessage}
                      >
                        Retry
                      </button>
                    )}
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>

            {messages.length === 1 && (
              <motion.div
                className="quick-questions-grid"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.3 }}
              >
                {quickQuestions.map((question, index) => (
                  <button
                    key={index}
                    className="quick-q-btn"
                    onClick={() => handleSend(question.query)}
                    disabled={isLoading || isStreaming}
                  >
                    <span className="quick-q-icon">{question.icon}</span>
                    <span>{question.text}</span>
                  </button>
                ))}
              </motion.div>
            )}

            {isLoading && (
              <div className="message assistant">
                <div className="msg-bubble">
                  <div className="typing-indicator">
                    <div className="dot" />
                    <div className="dot" />
                    <div className="dot" />
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          <div className="chat-input-area">
            <div className="input-wrapper">
              <input
                ref={inputRef}
                type="text"
                placeholder="Ask about admissions, fees, departments, exams..."
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') {
                    handleSend(input);
                  }
                }}
                disabled={isLoading || isStreaming}
                aria-label="Chat input"
              />

              <Paperclip
                size={18}
                className="attachment-icon"
                aria-label="Attach file"
              />

              <button
                className="send-btn"
                onClick={() => handleSend(input)}
                disabled={isLoading || isStreaming || !input.trim()}
                aria-label="Send message"
              >
                <Send size={16} />
              </button>
            </div>
          </div>
        </motion.div>
      </main>
    </>
  );
}

export default App;