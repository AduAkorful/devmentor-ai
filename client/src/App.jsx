import React, { useState, useEffect, useRef } from 'react';
import { PaperAirplaneIcon, ArrowLeftIcon, ArrowPathIcon } from '@heroicons/react/24/solid';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

// --- Helper Function ---
const fetchWithAuth = (url, options = {}) => {
  const token = localStorage.getItem('session_token');
  if (!token) {
    return Promise.reject(new Error('No session token found'));
  }
  const headers = { ...options.headers, 'Authorization': `Bearer ${token}` };
  return fetch(url, { ...options, headers });
};

// --- UI Components ---
const CodeBlock = ({ node, inline, className, children, ...props }) => {
  const match = /language-(\w+)/.exec(className || '');
  return !inline && match ? (
    <SyntaxHighlighter style={vscDarkPlus} language={match[1]} PreTag="div" {...props}>{String(children).replace(/\n$/, '')}</SyntaxHighlighter>
  ) : (
    <code className="bg-gray-800 text-indigo-400 px-1 rounded-md" {...props}>{children}</code>
  );
};
const UserMessage = ({ content }) => (<div className="flex justify-end my-4"><div className="bg-indigo-600 text-white rounded-lg p-3 max-w-lg shadow-md"><p>{content}</p></div></div>);
const BotMessage = ({ content }) => (<div className="flex justify-start my-4"><div className="bg-gray-700 text-gray-200 rounded-lg p-4 max-w-2xl w-full shadow-md"><ReactMarkdown components={{code: CodeBlock}}>{content}</ReactMarkdown></div></div>);
const LoadingIndicator = () => (<div className="flex justify-start my-4"><div className="bg-gray-700 rounded-lg p-4"><div className="flex items-center space-x-2"><div className="w-2 h-2 bg-indigo-400 rounded-full animate-pulse"></div><div className="w-2 h-2 bg-indigo-400 rounded-full animate-pulse delay-75"></div><div className="w-2 h-2 bg-indigo-400 rounded-full animate-pulse delay-150"></div></div></div></div>);

// --- Page Views ---
const LoginPage = ({ onLogin }) => (
  <div className="bg-gray-900 min-h-screen flex flex-col items-center justify-center text-white">
    <h1 className="text-4xl font-bold mb-4">DevMentor AI</h1>
    <p className="text-gray-400 mb-8">Your AI-powered engineering partner.</p>
    <button onClick={onLogin} className="bg-gray-700 hover:bg-gray-600 text-white font-bold py-3 px-6 rounded-lg flex items-center space-x-2">
      <svg className="w-6 h-6" viewBox="0 0 98 96" xmlns="http://www.w3.org/2000/svg"><path fillRule="evenodd" clipRule="evenodd" d="M48.854 0C21.839 0 0 22 0 49.217c0 21.756 13.993 40.172 33.405 46.69 2.427.49 3.316-1.059 3.316-2.362 0-1.141-.08-5.052-.08-9.127-13.59 2.934-16.42-5.867-16.42-5.867-2.2-5.703-5.4-7.227-5.4-7.227-4.4-3.003.3-2.94.3-2.94 4.8.3 7.4 5.002 7.4 5.002 4.2 7.203 11.2 5.103 13.9 3.897.4-3.024 1.7-5.103 3.1-6.279-10.6-.9-21.7-5.303-21.7-23.812 0-5.287 1.8-9.612 4.9-12.987-.5-1.059-2.2-6.143.5-12.822 0 0 4.01-1.303 13.2 5.002 3.8-1.059 7.9-1.587 12-1.587s8.2.528 12 1.587c9.2-6.305 13.2-5.002 13.2-5.002 2.7 6.679 1 11.763.5 12.822 3.1 3.375 4.9 7.7 4.9 12.987 0 18.509-11.1 22.909-21.7 23.812 1.7 1.5 3.3 4.402 3.3 8.887 0 6.403-.08 11.587-.08 13.117 0 1.302.9 2.852 3.3 2.362C84.007 89.39 97.993 70.972 97.993 49.217 97.993 22 75.823 0 48.854 0z" fill="#fff"/></svg>
      <span>Login with GitHub</span>
    </button>
  </div>
);

const DashboardPage = ({ user, onSelectRepo }) => {
  const [repos, setRepos] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetchWithAuth('http://127.0.0.1:8000/user/repos')
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) setRepos(data.filter(repo => !repo.fork));
      })
      .finally(() => setIsLoading(false));
  }, []);

  return (
    <div className="bg-gray-900 min-h-screen text-white">
      <header className="p-4 border-b border-gray-700 flex justify-between items-center">
        <h1 className="text-xl font-semibold">Select a Repository to Analyze</h1>
        <span>Welcome, {user}!</span>
      </header>
      <main className="p-8">
        {isLoading ? <p className="text-center">Fetching repositories...</p> : (
          <ul className="space-y-2 max-w-3xl mx-auto">
            {repos.map(repo => (
              <li key={repo.id} onClick={() => onSelectRepo(repo)} className="p-4 bg-gray-800 hover:bg-indigo-600 rounded-md cursor-pointer transition-colors flex justify-between items-center">
                <span className="font-semibold">{repo.full_name}</span>
                <span className="text-xs text-gray-400">{repo.language}</span>
              </li>
            ))}
          </ul>
        )}
      </main>
    </div>
  );
};

const ChatPage = ({ repo, onBack, onReIngest }) => {
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!query || isStreaming) return;

    setMessages(prev => [...prev, { role: 'user', content: query }]);
    setIsStreaming(true);
    setQuery('');
    
    // --- FINAL FIX FOR EventSource AUTH ---
    const token = localStorage.getItem('session_token');
    if (!token) {
        alert("Session expired. Please log in again.");
        window.location.href = '/';
        return;
    }

    const eventSource = new EventSource(`http://127.0.0.1:8000/concierge?repo_name=${encodeURIComponent(repo.full_name)}&user_query=${encodeURIComponent(query)}&token=${encodeURIComponent(token)}`);
    let botResponse = '';
    let firstChunk = true;

    eventSource.onmessage = (event) => {
      if (firstChunk) {
        setMessages(prev => [...prev, { role: 'bot', content: '' }]);
        firstChunk = false;
      }
      botResponse += event.data;
      setMessages(prev => {
        const newMessages = [...prev];
        newMessages[newMessages.length - 1].content = botResponse;
        return newMessages;
      });
    };
    eventSource.addEventListener('close', () => { setIsStreaming(false); eventSource.close(); });
    eventSource.onerror = () => { setIsStreaming(false); eventSource.close(); };
  };
  
  return (
    <div className="bg-gray-900 text-gray-100 min-h-screen flex flex-col font-mono">
      <header className="flex items-center justify-between p-4 border-b border-gray-700 shadow-md sticky top-0 bg-gray-900 z-10">
        <button onClick={onBack} className="flex items-center space-x-2 text-gray-400 hover:text-white"><ArrowLeftIcon className="h-5 w-5" /><span>Back</span></button>
        <h1 className="text-lg font-semibold tracking-wider text-center">{repo.full_name}</h1>
        <button onClick={onReIngest} className="flex items-center space-x-2 text-gray-400 hover:text-white" title="Re-ingest this repository"><ArrowPathIcon className="h-5 w-5" /></button>
      </header>
      <main className="flex-1 overflow-y-auto p-4 md:p-6"><div className="max-w-4xl mx-auto space-y-4">
        {messages.map((message, index) => message.role === 'user' ? <UserMessage key={index} content={message.content} /> : <BotMessage key={index} content={message.content} />)}
        {isStreaming && messages[messages.length - 1]?.role === 'user' && <LoadingIndicator />}
        <div ref={messagesEndRef} />
      </div></main>
      <footer className="p-4 bg-gray-900/80 backdrop-blur-sm sticky bottom-0"><div className="max-w-4xl mx-auto">
        <form onSubmit={handleSubmit} className="flex items-center bg-gray-800 border border-gray-700 rounded-lg p-2 shadow-lg">
          <input type="text" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Ask about this repo..." className="flex-1 bg-transparent border-none focus:ring-0 text-white placeholder-gray-500 px-2" disabled={isStreaming} />
          <button type="submit" className="bg-indigo-600 hover:bg-indigo-500 rounded-md p-2 ml-2 transition-colors disabled:bg-gray-600" disabled={!query || isStreaming}><PaperAirplaneIcon className="h-5 w-5 text-white" /></button>
        </form>
      </div></footer>
    </div>
  );
};

// --- Main App Controller ---
function App() {
  const [appState, setAppState] = useState('authenticating');
  const [user, setUser] = useState(null);
  const [activeRepo, setActiveRepo] = useState(null);

  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code');

    if (code) {
      setAppState('authenticating');
      fetch(`http://127.0.0.1:8000/auth/github/callback?code=${code}`)
        .then(res => res.ok ? res.json() : Promise.reject('GitHub callback failed'))
        .then(data => {
          localStorage.setItem('session_token', data.token);
          window.location.href = '/';
        })
        .catch(err => {
          console.error("Auth Error during callback:", err);
          window.location.href = '/';
        });
    } else {
      const token = localStorage.getItem('session_token');
      if (token) {
        fetchWithAuth('http://127.0.0.1:8000/user/me')
          .then(res => res.ok ? res.json() : Promise.reject('Invalid session'))
          .then(data => {
            setUser(data.login);
            setAppState('dashboard');
          })
          .catch(() => {
            localStorage.removeItem('session_token');
            setAppState('login');
          });
      } else {
        setAppState('login');
      }
    }
  }, []);

  const handleLogin = async () => {
    const res = await fetch('http://127.0.0.1:8000/login/github');
    const data = await res.json();
    window.location.href = data.url;
  };
  
  const handleSelectRepo = (repo) => {
    setActiveRepo(repo);
    setAppState('chat');
    fetchWithAuth('http://127.0.0.1:8000/ingest-repo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repo_name: repo.full_name, clone_url: repo.clone_url }),
    });
  };

  switch (appState) {
    case 'authenticating':
      return <div className="bg-gray-900 min-h-screen flex items-center justify-center text-white">Finalizing Authentication...</div>;
    case 'dashboard':
      return <DashboardPage user={user} onSelectRepo={handleSelectRepo} />;
    case 'chat':
      return <ChatPage repo={activeRepo} onBack={() => setAppState('dashboard')} onReIngest={() => handleSelectRepo(activeRepo)} />;
    case 'login':
    default:
      return <LoginPage onLogin={handleLogin} />;
  }
}

export default App;