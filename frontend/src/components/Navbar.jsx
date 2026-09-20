import React from 'react';
import { BookOpen, CheckCircle2, GraduationCap, Home, RefreshCw, Sparkles, TrendingUp, User } from 'lucide-react';

const NAV_ITEMS = [
  { id: 'home', label: 'Overview', icon: Home },
  { id: 'learn', label: 'Learn', icon: BookOpen },
  { id: 'revise', label: 'Revise', icon: RefreshCw },
  { id: 'test', label: 'Test', icon: CheckCircle2 },
  { id: 'progress', label: 'Progress', icon: TrendingUp },
];

export default function Navbar({
  currentMode,
  setMode,
  studentId,
  setStudentId,
  learnerSummary,
  studentProfile,
  onOpenProfile,
}) {
  return (
    <header className="site-header">
      <nav className="navbar" aria-label="Primary navigation">
        <button className="brand" onClick={() => setMode('home')} aria-label="Go to overview">
          <span className="brand-mark"><GraduationCap size={22} strokeWidth={1.8} /></span>
          <span className="brand-copy">
            <strong>EduNexus</strong>
            <small>Adaptive learning workspace</small>
          </span>
        </button>

        <div className="nav-tabs" role="tablist" aria-label="Learning modes">
          {NAV_ITEMS.map(({ id, label, icon: Icon }) => (
            <button key={id} className={`nav-tab ${currentMode === id ? 'is-active' : ''}`} onClick={() => setMode(id)} role="tab" aria-selected={currentMode === id}>
              <Icon size={16} strokeWidth={2} /><span>{label}</span>
            </button>
          ))}
        </div>

        <div className="profile-cluster">
          {learnerSummary && (
            <div className="profile-stats" aria-label="Learning progress">
              <span className="stat-pill stat-pill--success"><CheckCircle2 size={14} /> {learnerSummary.mastered_subconcepts_count || 0}</span>
              {learnerSummary.active_misconceptions_count > 0 && (
                <span className="stat-pill stat-pill--attention"><Sparkles size={14} /> {learnerSummary.active_misconceptions_count}</span>
              )}
            </div>
          )}
          
          <button
            onClick={onOpenProfile}
            title={studentProfile?.name ? `Student Profile: ${studentProfile.name}` : 'Setup Student Profile'}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              padding: '6px 14px',
              borderRadius: '8px',
              background: 'linear-gradient(135deg, rgba(15, 27, 44, 0.95), rgba(20, 38, 60, 0.9))',
              border: '1px solid rgba(45, 212, 191, 0.35)',
              color: '#5eead4',
              cursor: 'pointer',
              fontSize: '0.82rem',
              fontWeight: 650,
              boxShadow: '0 2px 8px rgba(0, 0, 0, 0.3)',
              transition: 'all 0.2s ease'
            }}
          >
            <User size={15} color="#2dd4bf" />
            <span>{studentProfile?.name ? studentProfile.name : 'Setup Profile'}</span>
          </button>
        </div>
      </nav>
    </header>
  );
}

