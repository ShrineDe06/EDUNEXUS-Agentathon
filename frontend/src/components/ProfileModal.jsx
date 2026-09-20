import React, { useState } from 'react';
import { User, Mail, GraduationCap, Calendar, Clock, Droplets, X, Save, AlertCircle, Sparkles } from 'lucide-react';

export default function ProfileModal({ isOpen, onClose, studentProfile, onSaveProfile }) {
  if (!isOpen) return null;

  const [formData, setFormData] = useState({
    name: studentProfile?.name || '',
    email: studentProfile?.email || '',
    level: studentProfile?.level || 'College',
    study: studentProfile?.study || '',
    yearOfStudy: studentProfile?.yearOfStudy || '2nd Year',
    pomodoro: {
      enabled: studentProfile?.pomodoro?.enabled ?? true,
      studyTime: studentProfile?.pomodoro?.studyTime || 25,
      breakTime: studentProfile?.pomodoro?.breakTime || 5,
    },
    hydration: {
      enabled: studentProfile?.hydration?.enabled ?? true,
      interval: studentProfile?.hydration?.interval || 45,
    },
  });

  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    setErrorMsg('');
  };

  const handlePomodoroChange = (field, value) => {
    const num = parseInt(value, 10) || 1;
    setFormData(prev => ({
      ...prev,
      pomodoro: {
        ...prev.pomodoro,
        [field]: num,
      }
    }));
    setErrorMsg('');
  };

  const handleTogglePomodoro = (enabled) => {
    setFormData(prev => ({
      ...prev,
      pomodoro: { ...prev.pomodoro, enabled }
    }));
  };

  const handleHydrationChange = (value) => {
    const num = parseInt(value, 10) || 5;
    setFormData(prev => ({
      ...prev,
      hydration: {
        ...prev.hydration,
        interval: num,
      }
    }));
  };

  const handleToggleHydration = (enabled) => {
    setFormData(prev => ({
      ...prev,
      hydration: { ...prev.hydration, enabled }
    }));
  };

  const handleSave = (e) => {
    e.preventDefault();
    if (!formData.name.trim()) {
      setErrorMsg('Please enter student name.');
      return;
    }

    // Pomodoro validation: breakTime must be strictly less than studyTime
    if (formData.pomodoro.enabled) {
      if (formData.pomodoro.breakTime >= formData.pomodoro.studyTime) {
        setErrorMsg(`Break time (${formData.pomodoro.breakTime}m) must be strictly less than study time (${formData.pomodoro.studyTime}m).`);
        return;
      }
    }

    onSaveProfile(formData);
    setSuccessMsg('Profile and personal preferences saved successfully!');
    setTimeout(() => {
      setSuccessMsg('');
      onClose();
    }, 900);
  };

  return (
    <div className="modal-backdrop" onClick={onClose} style={{
      position: 'fixed',
      inset: 0,
      background: 'rgba(5, 10, 20, 0.75)',
      backdropFilter: 'blur(8px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 9999,
      padding: '20px'
    }}>
      <div
        className="profile-modal-card"
        onClick={(e) => e.stopPropagation()}
        style={{
          background: 'linear-gradient(135deg, #0d1829 0%, #0f223a 100%)',
          border: '1px solid rgba(45, 212, 191, 0.25)',
          boxShadow: '0 25px 60px -15px rgba(0, 0, 0, 0.8), 0 0 30px rgba(45, 212, 191, 0.1)',
          borderRadius: '16px',
          width: '100%',
          maxWidth: '560px',
          maxHeight: '90vh',
          overflowY: 'auto',
          color: '#e2e8f0',
          padding: '28px',
          position: 'relative'
        }}
      >
        {/* Close Button */}
        <button
          onClick={onClose}
          style={{
            position: 'absolute',
            top: '20px',
            right: '20px',
            background: 'rgba(255, 255, 255, 0.06)',
            border: 'none',
            color: '#94a3b8',
            borderRadius: '8px',
            padding: '6px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'all 0.2s ease'
          }}
          aria-label="Close modal"
        >
          <X size={20} />
        </button>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '20px' }}>
          <div style={{
            width: '44px',
            height: '44px',
            borderRadius: '12px',
            background: 'linear-gradient(135deg, #14b8a6, #0284c7)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 8px 16px rgba(20, 184, 166, 0.25)'
          }}>
            <User size={24} color="#ffffff" />
          </div>
          <div>
            <h2 style={{ fontSize: '1.3rem', fontWeight: 700, margin: 0, color: '#f8fafc' }}>
              Student Profile & Personalisation
            </h2>
            <p style={{ margin: 0, fontSize: '0.85rem', color: '#94a3b8' }}>
              Configure your academic details and mindful study habits
            </p>
          </div>
        </div>

        {errorMsg && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '10px 14px',
            marginBottom: '16px',
            borderRadius: '8px',
            background: 'rgba(239, 68, 68, 0.15)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            color: '#fca5a5',
            fontSize: '0.85rem'
          }}>
            <AlertCircle size={16} />
            <span>{errorMsg}</span>
          </div>
        )}

        {successMsg && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '10px 14px',
            marginBottom: '16px',
            borderRadius: '8px',
            background: 'rgba(16, 185, 129, 0.15)',
            border: '1px solid rgba(16, 185, 129, 0.3)',
            color: '#6ee7b7',
            fontSize: '0.85rem'
          }}>
            <Sparkles size={16} />
            <span>{successMsg}</span>
          </div>
        )}

        <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
          {/* Academic Info Section */}
          <div style={{
            background: 'rgba(15, 23, 42, 0.5)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            borderRadius: '12px',
            padding: '16px',
            display: 'flex',
            flexDirection: 'column',
            gap: '14px'
          }}>
            <div style={{ fontSize: '0.9rem', fontWeight: 650, color: '#38bdf8', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <GraduationCap size={16} /> Academic Profile
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '4px' }}>
                  Full Name *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Alex Rivera"
                  value={formData.name}
                  onChange={(e) => handleChange('name', e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: '8px',
                    background: 'rgba(30, 41, 59, 0.8)',
                    border: '1px solid rgba(255, 255, 255, 0.12)',
                    color: '#f8fafc',
                    fontSize: '0.88rem'
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '4px' }}>
                  Email (for Alerts)
                </label>
                <input
                  type="email"
                  placeholder="student@example.com"
                  value={formData.email}
                  onChange={(e) => handleChange('email', e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: '8px',
                    background: 'rgba(30, 41, 59, 0.8)',
                    border: '1px solid rgba(255, 255, 255, 0.12)',
                    color: '#f8fafc',
                    fontSize: '0.88rem'
                  }}
                />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '10px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '4px' }}>
                  Level
                </label>
                <select
                  value={formData.level}
                  onChange={(e) => handleChange('level', e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 10px',
                    borderRadius: '8px',
                    background: '#1e293b',
                    border: '1px solid rgba(255, 255, 255, 0.12)',
                    color: '#f8fafc',
                    fontSize: '0.85rem'
                  }}
                >
                  <option value="College">College / Univ</option>
                  <option value="School">School (K-12)</option>
                  <option value="Self-Taught">Self-Taught / Professional</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '4px' }}>
                  Course / Major
                </label>
                <input
                  type="text"
                  placeholder="e.g. Computer Science"
                  value={formData.study}
                  onChange={(e) => handleChange('study', e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 10px',
                    borderRadius: '8px',
                    background: 'rgba(30, 41, 59, 0.8)',
                    border: '1px solid rgba(255, 255, 255, 0.12)',
                    color: '#f8fafc',
                    fontSize: '0.85rem'
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '4px' }}>
                  Year of Study
                </label>
                <input
                  type="text"
                  placeholder="e.g. 3rd Year / Grade 11"
                  value={formData.yearOfStudy}
                  onChange={(e) => handleChange('yearOfStudy', e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 10px',
                    borderRadius: '8px',
                    background: 'rgba(30, 41, 59, 0.8)',
                    border: '1px solid rgba(255, 255, 255, 0.12)',
                    color: '#f8fafc',
                    fontSize: '0.85rem'
                  }}
                />
              </div>
            </div>
          </div>

          {/* Personalisation Subsection */}
          <div style={{
            background: 'rgba(15, 23, 42, 0.5)',
            border: '1px solid rgba(45, 212, 191, 0.2)',
            borderRadius: '12px',
            padding: '16px',
            display: 'flex',
            flexDirection: 'column',
            gap: '16px'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ fontSize: '0.9rem', fontWeight: 650, color: '#2dd4bf', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Clock size={16} /> Personalisation & Wellness
              </div>
              <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
                Active in Learn & Revise only
              </span>
            </div>

            {/* Pomodoro settings */}
            <div style={{
              background: 'rgba(30, 41, 59, 0.6)',
              padding: '12px',
              borderRadius: '10px',
              border: '1px solid rgba(255, 255, 255, 0.05)'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '0.85rem', fontWeight: 600, color: '#f1f5f9' }}>
                  <input
                    type="checkbox"
                    checked={formData.pomodoro.enabled}
                    onChange={(e) => handleTogglePomodoro(e.target.checked)}
                    style={{ accentColor: '#14b8a6', width: '16px', height: '16px' }}
                  />
                  <span>🍅 Pomodoro Study Timer</span>
                </label>
                <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                  {formData.pomodoro.enabled ? 'Enabled' : 'Disabled'}
                </span>
              </div>

              {formData.pomodoro.enabled && (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginTop: '6px' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.75rem', color: '#94a3b8', marginBottom: '4px' }}>
                      Study Interval (minutes)
                    </label>
                    <input
                      type="number"
                      min="5"
                      max="180"
                      value={formData.pomodoro.studyTime}
                      onChange={(e) => handlePomodoroChange('studyTime', e.target.value)}
                      style={{
                        width: '100%',
                        padding: '6px 10px',
                        borderRadius: '6px',
                        background: '#0f172a',
                        border: '1px solid rgba(255, 255, 255, 0.1)',
                        color: '#f8fafc',
                        fontSize: '0.85rem'
                      }}
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.75rem', color: '#94a3b8', marginBottom: '4px' }}>
                      Break Interval (minutes)
                    </label>
                    <input
                      type="number"
                      min="1"
                      max="60"
                      value={formData.pomodoro.breakTime}
                      onChange={(e) => handlePomodoroChange('breakTime', e.target.value)}
                      style={{
                        width: '100%',
                        padding: '6px 10px',
                        borderRadius: '6px',
                        background: '#0f172a',
                        border: formData.pomodoro.breakTime >= formData.pomodoro.studyTime ? '1px solid #ef4444' : '1px solid rgba(255, 255, 255, 0.1)',
                        color: '#f8fafc',
                        fontSize: '0.85rem'
                      }}
                    />
                    <small style={{ fontSize: '0.7rem', color: formData.pomodoro.breakTime >= formData.pomodoro.studyTime ? '#f87171' : '#64748b' }}>
                      Must be strictly less than study time
                    </small>
                  </div>
                </div>
              )}
            </div>

            {/* Hydration / Walk reminder */}
            <div style={{
              background: 'rgba(30, 41, 59, 0.6)',
              padding: '12px',
              borderRadius: '10px',
              border: '1px solid rgba(255, 255, 255, 0.05)'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: formData.hydration.enabled ? '10px' : '0' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '0.85rem', fontWeight: 600, color: '#f1f5f9' }}>
                  <input
                    type="checkbox"
                    checked={formData.hydration.enabled}
                    onChange={(e) => handleToggleHydration(e.target.checked)}
                    style={{ accentColor: '#38bdf8', width: '16px', height: '16px' }}
                  />
                  <span>💧 Hydration & Walk Alert</span>
                </label>
                <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                  {formData.hydration.enabled ? 'Enabled' : 'Disabled'}
                </span>
              </div>

              {formData.hydration.enabled && (
                <div style={{ marginTop: '6px' }}>
                  <label style={{ display: 'block', fontSize: '0.75rem', color: '#94a3b8', marginBottom: '4px' }}>
                    Reminder Interval (minutes after study)
                  </label>
                  <input
                    type="number"
                    min="10"
                    max="180"
                    value={formData.hydration.interval}
                    onChange={(e) => handleHydrationChange(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '6px 10px',
                      borderRadius: '6px',
                      background: '#0f172a',
                      border: '1px solid rgba(255, 255, 255, 0.1)',
                      color: '#f8fafc',
                      fontSize: '0.85rem'
                    }}
                  />
                </div>
              )}
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '6px' }}>
            <button
              type="button"
              onClick={onClose}
              style={{
                padding: '8px 16px',
                borderRadius: '8px',
                background: 'rgba(255, 255, 255, 0.08)',
                border: 'none',
                color: '#cbd5e1',
                fontSize: '0.85rem',
                cursor: 'pointer'
              }}
            >
              Cancel
            </button>
            <button
              type="submit"
              style={{
                padding: '8px 20px',
                borderRadius: '8px',
                background: 'linear-gradient(135deg, #0d9488, #0284c7)',
                border: 'none',
                color: '#ffffff',
                fontWeight: 600,
                fontSize: '0.88rem',
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                boxShadow: '0 4px 12px rgba(13, 148, 136, 0.3)'
              }}
            >
              <Save size={16} /> Save Profile & Settings
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
