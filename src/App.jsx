// src/App.jsx

import { useState } from 'react';
import MedicalChatbot from './components/MedicalChatbot';
import AdminPanel from './components/AdminPanel';
import './App.css';

function App() {
  const [view, setView] = useState('chat'); // 'chat' or 'admin'

  return (
    <div className="app">
      {/* Toggle Button */}
      <button 
        className="view-toggle"
        onClick={() => setView(view === 'chat' ? 'admin' : 'chat')}
      >
        {view === 'chat' ? '📊 Admin Panel' : '💬 Chat'}
      </button>

      {/* Render current view */}
      {view === 'chat' ? <MedicalChatbot /> : <AdminPanel />}
    </div>
  );
}

export default App;