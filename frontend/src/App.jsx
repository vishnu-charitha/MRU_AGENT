import React, { useState, useRef, useEffect } from 'react';
import { Send, Minus, Maximize2, X, GraduationCap, Building2, Wallet, MapPin, Calendar, Briefcase, Paperclip, Phone, Share2, Search, ArrowRight, Menu, ExternalLink, RefreshCw } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const formatMessageContent = (text) => {
  if (!text) return null;
  // Simple markdown renderer for bold and line breaks
  const paragraphs = text.split('\n\n').filter(p => p.trim());
  return paragraphs.map((p, pIdx) => {
    // Handle bullet points
    if (p.includes('\n*') || p.startsWith('*')) {
      const items = p.split('\n').filter(i => i.trim());
      return (
        <ul key={pIdx} style={{ paddingLeft: '20px', margin: '8px 0' }}>
          {items.map((item, iIdx) => {
            let cleanItem = item.replace(/^\*\s*/, '');
            // bold text **text**
            const parts = cleanItem.split(/(\*\*.*?\*\*)/g);
            return (
              <li key={iIdx} style={{ marginBottom: '4px' }}>
                {parts.map((part, partIdx) => {
                  if (part.startsWith('**') && part.endsWith('**')) {
                    return <strong key={partIdx}>{part.slice(2, -2)}</strong>;
                  }
                  return part;
                })}
              </li>
            );
          })}
        </ul>
      );
    }
    
    // Normal paragraph with bold support
    const parts = p.split(/(\*\*.*?\*\*)/g);
    return (
      <p key={pIdx} style={{ margin: '8px 0' }}>
        {parts.map((part, partIdx) => {
          if (part.startsWith('**') && part.endsWith('**')) {
            return <strong key={partIdx}>{part.slice(2, -2)}</strong>;
          }
          return part;
        })}
      </p>
    );
  });
};

function App() {
  const initialWelcome = {
    id: 'welcome',
    role: 'assistant',
    content: 'Welcome to MRDU Assistant 👋\n\nI can help you find information about MRDU admissions, departments, fees, examinations, regulations, campus facilities and academic services.'
  };

  const [messages, setMessages] = useState([initialWelcome]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSend = async (question) => {
    if (!question.trim() || isLoading) return;
    
    const userMsg = { id: Date.now().toString(), role: 'user', content: question };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question })
      });
      
      if (!response.ok) throw new Error('Network response was not ok');
      
      const data = await response.json();
      
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: data.answer,
        sources: data.sources || [],
        out_of_scope: data.out_of_scope_detected
      }]);
    } catch (error) {
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'Unable to connect to MRDU Assistant. Please make sure the backend server is running.',
        isError: true
      }]);
    } finally {
      setIsLoading(false);
      // Give focus back to input on desktop
      if (window.innerWidth > 1024) {
        inputRef.current?.focus();
      }
    }
  };

  const resetChat = () => {
    if (messages.length > 2) {
      if (!window.confirm('Are you sure you want to clear this conversation?')) return;
    }
    setMessages([initialWelcome]);
    setInput('');
  };

  const quickQuestions = [
    { text: 'B.Tech Admissions', icon: <GraduationCap size={16} />, query: 'What are the B.Tech admission eligibility requirements?' },
    { text: 'Departments', icon: <Building2 size={16} />, query: 'What departments are available at MRDU?' },
    { text: 'Fees Structure', icon: <Wallet size={16} />, query: 'What are the B.Tech fees?' },
    { text: 'Tirupati Campus', icon: <MapPin size={16} />, query: 'What information is available about the Tirupati campus?' },
    { text: 'Examinations', icon: <Calendar size={16} />, query: 'What is the examination timetable?' },
    { text: 'Regulations', icon: <Briefcase size={16} />, query: 'What is the MR24 regulation?' },
  ];

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
            <a href="#" className="apply-btn" aria-label="Apply Now">APPLY NOW</a>
            <div className="social-icons" aria-label="Social Links">
              <Phone size={14} style={{ cursor: 'pointer' }} aria-label="Phone" />
              <Share2 size={14} style={{ cursor: 'pointer' }} aria-label="Share" />
              <Search size={14} style={{ cursor: 'pointer' }} aria-label="Search" />
            </div>
          </div>
        </div>
        
        <div className="main-nav">
          <div className="logo-section">
            <img src="/logo.jpg" alt="MRDU Official Logo" className="logo-img" />
            <div className="logo-text">
              <h1>Malla Reddy (MR)</h1>
              <p>DEEMED TO BE UNIVERSITY</p>
            </div>
          </div>
          
          <button 
            className="mobile-menu-btn" 
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            aria-label="Toggle Navigation Menu"
          >
            <Menu size={24} />
          </button>

          <nav className={`nav-links ${isMobileMenuOpen ? 'active' : ''}`} aria-label="Main Navigation">
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
          <h2 className="hero-subtitle">AI-Powered College Knowledge Assistant</h2>
          <p className="hero-desc">
            Get instant answers about admissions, departments, fees, examinations, regulations, campus information and academic services.
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
            <div className="stat-item">
              <p>Programs</p>
            </div>
            <div className="stat-item">
              <p>Students</p>
            </div>
            <div className="stat-item">
              <p>Placement</p>
            </div>
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
              <img src="/logo.jpg" alt="Avatar" className="chat-avatar" />
              <div className="chat-title">
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <h3>MRDU Assistant</h3>
                  <span className="status-indicator" title="Online"></span>
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
              <button aria-label="Minimize"><Minus size={16} /></button>
              <button aria-label="Maximize"><Maximize2 size={16} /></button>
              <button aria-label="Close"><X size={16} /></button>
            </div>
          </div>
          
          <div className="chat-body">
            <AnimatePresence>
              {messages.map((msg) => (
                <motion.div 
                  key={msg.id} 
                  className={`message ${msg.role}`}
                  initial={{ opacity: 0, y: 10, scale: 0.98 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  transition={{ duration: 0.2 }}
                >
                  <div className={`msg-bubble ${msg.isError ? 'error-bubble' : ''}`}>
                    {formatMessageContent(msg.content)}
                    
                    {msg.out_of_scope && (
                       <div className="out-of-scope-warning">
                         This topic is outside the current MRDU knowledge scope.
                       </div>
                    )}
                    
                    {msg.sources && msg.sources.length > 0 && (
                      <div className="sources-container">
                        <div className="sources-title">Sources</div>
                        <div className="sources-list">
                          {msg.sources.map((src, idx) => (
                            <a 
                              key={idx} 
                              href={src.url !== 'Unknown URL' ? src.url : '#'} 
                              target={src.url !== 'Unknown URL' ? "_blank" : "_self"} 
                              rel="noreferrer" 
                              className="source-chip"
                              title={src.title}
                            >
                              <span className="source-chip-text">{src.title}</span>
                              {src.url !== 'Unknown URL' && <ExternalLink size={10} />}
                            </a>
                          ))}
                        </div>
                      </div>
                    )}

                    {msg.isError && (
                      <button className="retry-btn" onClick={() => handleSend(messages[messages.length-2].content)}>
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
                {quickQuestions.map((q, idx) => (
                  <button key={idx} className="quick-q-btn" onClick={() => handleSend(q.query)}>
                    <span className="quick-q-icon">{q.icon}</span>
                    <span>{q.text}</span>
                  </button>
                ))}
              </motion.div>
            )}

            {isLoading && (
              <div className="message assistant">
                <div className="msg-bubble">
                  <div className="typing-indicator">
                    <div className="dot"></div>
                    <div className="dot"></div>
                    <div className="dot"></div>
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
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSend(input)}
                disabled={isLoading}
                aria-label="Chat input"
              />
              <Paperclip size={18} style={{ color: 'rgba(255,255,255,0.4)', margin: '0 10px', cursor: 'pointer' }} aria-label="Attach file" />
              <button 
                className="send-btn" 
                onClick={() => handleSend(input)} 
                disabled={isLoading || !input.trim()}
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
