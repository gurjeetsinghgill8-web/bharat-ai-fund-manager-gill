// src/App.jsx — Main app shell with sidebar and routing
import { useState } from 'react';
import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import Gurjas1 from './pages/Gurjas1';
import Gurjas2 from './pages/Gurjas2';
import Momentum from './pages/Momentum';
import Sectors from './pages/Sectors';
import './index.css';

const NAV = [
  { path: '/',         icon: '📊', label: 'Portfolio Dashboard' },
  { path: '/gurjas1',  icon: '🔍', label: 'GURJAS 1 Screener' },
  { path: '/gurjas2',  icon: '🎯', label: 'GURJAS 2 Screener' },
  { path: '/momentum', icon: '⚡', label: 'Momentum & Breakout' },
  { path: '/sectors',  icon: '🏭', label: 'Sectors & Industries' },
];

export default function App() {
  const [user] = useState({ name: 'Gurjas', id: 1 });

  return (
    <BrowserRouter>
      <div className="sidebar">
        {/* Logo */}
        <div className="sidebar-logo">
          <div style={{ fontSize: 28, marginBottom: 6 }}>⚡</div>
          <div className="logo-title">Bharat AI Gill</div>
          <div className="logo-sub">Jarvis Fund Core v2.0</div>
        </div>

        {/* Navigation */}
        <nav className="sidebar-nav">
          <div className="nav-section-label">Navigation</div>
          {NAV.map(({ path, icon, label }) => (
            <NavLink
              key={path}
              to={path}
              end={path === '/'}
              className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
            >
              <span className="nav-icon">{icon}</span>
              {label}
            </NavLink>
          ))}
        </nav>

        {/* User */}
        <div className="sidebar-user">
          <div className="user-avatar">{user.name[0]}</div>
          <div className="user-info">
            <div className="user-name">{user.name}</div>
            <div className="user-role">Fund Manager</div>
          </div>
        </div>
      </div>

      <div className="main-content">
        <Routes>
          <Route path="/"         element={<Dashboard userId={user.id} />} />
          <Route path="/gurjas1"  element={<Gurjas1 />} />
          <Route path="/gurjas2"  element={<Gurjas2 />} />
          <Route path="/momentum" element={<Momentum />} />
          <Route path="/sectors"  element={<Sectors />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}
