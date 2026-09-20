import React, { useState, useEffect } from 'react';
import { Calendar, Clock, Mail, Plus, Trash2, X, Check, Bell, AlertCircle, ExternalLink, Settings, ChevronDown, ChevronUp, Save, Send } from 'lucide-react';

export default function ScheduleModal({
  isOpen,
  onClose,
  studentId,
  studentProfile,
  mode = 'revise', // 'revise' | 'test'
  defaultTopic = '',
  availableTopics = [],
  onScheduleCreated,
}) {
  if (!isOpen) return null;

  const todayStr = new Date().toISOString().split('T')[0];

  const [topic, setTopic] = useState(defaultTopic || (availableTopics[0] || 'Python Foundations'));
  const [date, setDate] = useState(todayStr);
  const [timeInput, setTimeInput] = useState('10:00');
  const [timeSlots, setTimeSlots] = useState(['10:00', '16:00']);
  const [email, setEmail] = useState(studentProfile?.email || '');
  const [note, setNote] = useState('');
  const [existingSchedules, setExistingSchedules] = useState([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState({ type: '', msg: '' });
  const [previewUrl, setPreviewUrl] = useState('');

  // Email service status
  const [emailServiceStatus, setEmailServiceStatus] = useState({ configured: false, smtp_user: '' });
  const [showSmtpConfig, setShowSmtpConfig] = useState(false);
  const [smtpHost, setSmtpHost] = useState('smtp.gmail.com');
  const [smtpPort, setSmtpPort] = useState(587);
  const [smtpUser, setSmtpUser] = useState('');
  const [smtpPass, setSmtpPass] = useState('');
  const [savingSmtp, setSavingSmtp] = useState(false);
  const [testingSmtp, setTestingSmtp] = useState(false);
  const [smtpMsg, setSmtpMsg] = useState('');

  useEffect(() => {
    if (defaultTopic) setTopic(defaultTopic);
    else if (availableTopics.length > 0 && !topic) setTopic(availableTopics[0]);
  }, [defaultTopic, availableTopics]);

  useEffect(() => {
    if (studentProfile?.email && !email) {
      setEmail(studentProfile.email);
    }
    if (studentProfile?.email && !smtpUser) {
      setSmtpUser(studentProfile.email);
    }
  }, [studentProfile]);

  useEffect(() => {
    if (isOpen) {
      loadSchedules();
      fetchEmailStatus();
    }
  }, [isOpen, studentId]);

  const fetchEmailStatus = async () => {
    try {
      const res = await fetch('/api/email/status');
      if (res.ok) {
        const data = await res.json();
        setEmailServiceStatus(data);
        if (data.smtp_user && !smtpUser) {
          setSmtpUser(data.smtp_user);
        }
      }
    } catch (err) {
      console.error('Failed to fetch email status:', err);
    }
  };

  const loadSchedules = async () => {
    try {
      setLoading(true);
      const res = await fetch(`/api/schedule/list/${studentId}`);
      if (res.ok) {
        const data = await res.json();
        // Handle both direct array and { schedules: [...] } shape
        const list = Array.isArray(data) ? data : (data.schedules || []);
        setExistingSchedules(list.filter(s => !mode || s.mode === mode));
      }
    } catch (err) {
      console.error('Failed to load schedules:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAddTimeSlot = () => {
    if (!timeInput) return;
    if (!timeSlots.includes(timeInput)) {
      setTimeSlots([...timeSlots, timeInput].sort());
    }
  };

  const handleRemoveTimeSlot = (slotToRemove) => {
    setTimeSlots(timeSlots.filter(t => t !== slotToRemove));
  };

  const handleCreateSchedule = async (e) => {
    e.preventDefault();
    if (!topic.trim()) {
      setFeedback({ type: 'error', msg: 'Please enter or select a topic.' });
      return;
    }
    if (!date) {
      setFeedback({ type: 'error', msg: 'Please choose a study day.' });
      return;
    }
    if (timeSlots.length === 0) {
      setFeedback({ type: 'error', msg: 'Please add at least one alert time slot.' });
      return;
    }

    try {
      setSaving(true);
      setFeedback({ type: '', msg: '' });
      setPreviewUrl('');

      const res = await fetch('/api/schedule/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          student_id: studentId,
          student_name: studentProfile?.name || 'Student',
          topic: topic.trim(),
          mode: mode,
          date: date,
          time_slots: timeSlots,
          email: email.trim(),
          note: note.trim(),
          send_notification: true
        }),
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Failed to create schedule');
      }

      const resData = await res.json();
      const delivery = resData.email_delivery || resData.email_result;
      
      // Immediately add the new schedule to local state so existing count updates without delay
      if (resData.schedule) {
        setExistingSchedules(prev => {
          const filtered = prev.filter(s => s.id !== resData.schedule.id);
          return [resData.schedule, ...filtered];
        });
      }

      let msgText = `Successfully scheduled ${mode === 'revise' ? 'Revision' : 'Test'} for '${topic}'!`;
      if (delivery?.preview_url) {
        setPreviewUrl(delivery.preview_url);
        msgText += ` Real email sent via Live SMTP.`;
      } else if (delivery?.delivered) {
        msgText += ` Real email delivered to ${email}!`;
      } else {
        msgText += ` Reminder alert registered for ${email || 'student'}.`;
      }

      setFeedback({
        type: 'success',
        msg: msgText
      });

      loadSchedules();
      if (onScheduleCreated) onScheduleCreated();
    } catch (err) {
      setFeedback({ type: 'error', msg: err.message || 'Error saving schedule' });
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteSchedule = async (scheduleId) => {
    try {
      const res = await fetch(`/api/schedule/${scheduleId}`, { method: 'DELETE' });
      if (res.ok) {
        setExistingSchedules(prev => prev.filter(s => s.id !== scheduleId));
        if (onScheduleCreated) onScheduleCreated();
      }
    } catch (err) {
      console.error('Failed to cancel schedule:', err);
    }
  };

  const handleSaveSmtp = async (e) => {
    e.preventDefault();
    if (!smtpUser.trim() || !smtpPass.trim()) {
      setSmtpMsg('Please provide your email and 16-character App Password.');
      return;
    }

    try {
      setSavingSmtp(true);
      setSmtpMsg('');
      const res = await fetch('/api/email/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          smtp_host: smtpHost.trim(),
          smtp_port: parseInt(smtpPort, 10) || 587,
          smtp_user: smtpUser.trim(),
          smtp_pass: smtpPass.trim(),
          smtp_from: smtpUser.trim()
        })
      });

      if (!res.ok) throw new Error('Failed to update SMTP settings');
      
      // Auto test the new credentials
      setSmtpMsg('Testing connection and sending verification email...');
      const testRes = await fetch('/api/email/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ recipient_email: smtpUser.trim() })
      });
      const testData = await testRes.json();

      if (testData.delivered) {
        setSmtpMsg(`✅ Verified! Test email successfully sent to ${smtpUser.trim()}!`);
        fetchEmailStatus();
      } else {
        setSmtpMsg(`Settings saved, but test delivery returned: ${testData.error || testData.message}`);
      }
    } catch (err) {
      setSmtpMsg(`Error: ${err.message}`);
    } finally {
      setSavingSmtp(false);
    }
  };

  const handleSendTestEmail = async () => {
    const target = email || smtpUser;
    if (!target) {
      alert('Please enter an email address first.');
      return;
    }
    try {
      setTestingSmtp(true);
      const res = await fetch('/api/email/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ recipient_email: target.trim() })
      });
      const data = await res.json();
      if (data.delivered) {
        alert(`Success! Test reminder was dispatched to ${target}.\n${data.preview_url ? 'Web inbox: ' + data.preview_url : ''}`);
      } else {
        alert(`Test email could not be delivered: ${data.error || 'Check SMTP credentials'}`);
      }
    } catch (err) {
      alert(`Error sending test email: ${err.message}`);
    } finally {
      setTestingSmtp(false);
    }
  };

  const isRevise = mode === 'revise';
  const themeColor = isRevise ? '#2dd4bf' : '#a855f7';
  const modeTitle = isRevise ? 'Revision Session' : 'Test Assessment';

  return (
    <div
      className="modal-backdrop"
      onClick={onClose}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        width: '100vw',
        height: '100vh',
        background: 'rgba(5, 10, 20, 0.82)',
        backdropFilter: 'blur(8px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 99999,
        padding: '20px',
        boxSizing: 'border-box'
      }}
    >
      <div
        className="schedule-modal-card"
        onClick={(e) => e.stopPropagation()}
        style={{
          background: 'linear-gradient(135deg, #0d192c 0%, #10243e 100%)',
          border: `1px solid ${isRevise ? 'rgba(45, 212, 191, 0.35)' : 'rgba(168, 85, 247, 0.35)'}`,
          boxShadow: '0 25px 60px -15px rgba(0, 0, 0, 0.9), 0 0 30px rgba(0, 0, 0, 0.4)',
          borderRadius: '16px',
          width: '100%',
          maxWidth: '680px',
          maxHeight: '85vh',
          display: 'flex',
          flexDirection: 'column',
          color: '#e2e8f0',
          position: 'relative',
          boxSizing: 'border-box',
          overflow: 'hidden'
        }}
      >
        {/* Sticky Header */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '18px 24px',
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
          background: 'rgba(13, 25, 44, 0.9)',
          flexShrink: 0
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <div
              style={{
                width: '42px',
                height: '42px',
                borderRadius: '12px',
                background: isRevise
                  ? 'linear-gradient(135deg, #0d9488, #0284c7)'
                  : 'linear-gradient(135deg, #9333ea, #4f46e5)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: `0 6px 16px ${isRevise ? 'rgba(13, 148, 136, 0.3)' : 'rgba(147, 51, 234, 0.3)'}`
              }}
            >
              <Calendar size={22} color="#ffffff" />
            </div>
            <div>
              <h2 style={{ fontSize: '1.2rem', fontWeight: 700, margin: 0, color: '#f8fafc' }}>
                Schedule {modeTitle}
              </h2>
              <p style={{ margin: '2px 0 0 0', fontSize: '0.82rem', color: '#94a3b8' }}>
                Pick calendar day & alert times. Reminders are dispatched directly to your email.
              </p>
            </div>
          </div>

          {/* Close Button */}
          <button
            onClick={onClose}
            style={{
              background: 'rgba(255, 255, 255, 0.06)',
              border: 'none',
              color: '#94a3b8',
              borderRadius: '8px',
              padding: '6px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
            aria-label="Close modal"
          >
            <X size={20} />
          </button>
        </div>

        {/* Scrollable Content Body */}
        <div style={{
          padding: '20px 24px 24px',
          overflowY: 'auto',
          flex: 1
        }}>

        {/* Feedback alert */}
        {feedback.msg && (
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '6px',
              padding: '12px 14px',
              marginBottom: '16px',
              borderRadius: '8px',
              background: feedback.type === 'error' ? 'rgba(239, 68, 68, 0.15)' : 'rgba(16, 185, 129, 0.15)',
              border: feedback.type === 'error' ? '1px solid rgba(239, 68, 68, 0.3)' : '1px solid rgba(16, 185, 129, 0.3)',
              color: feedback.type === 'error' ? '#fca5a5' : '#6ee7b7',
              fontSize: '0.85rem'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              {feedback.type === 'error' ? <AlertCircle size={16} /> : <Check size={16} />}
              <span style={{ fontWeight: 600 }}>{feedback.msg}</span>
            </div>

            {previewUrl && (
              <div style={{ marginTop: '4px', paddingLeft: '24px' }}>
                <a
                  href={previewUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '6px',
                    color: '#38bdf8',
                    textDecoration: 'underline',
                    fontWeight: 700,
                    fontSize: '0.82rem'
                  }}
                >
                  <ExternalLink size={14} /> Open & View Delivered Email in Browser
                </a>
              </div>
            )}
          </div>
        )}

        {/* Schedule Form */}
        <form onSubmit={handleCreateSchedule} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Topic selection */}
          <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '5px' }}>
                Topic to {isRevise ? 'Revise' : 'Test'} *
              </label>
              {availableTopics.length > 0 ? (
                <div style={{ display: 'flex', gap: '8px' }}>
                  <select
                    value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                    style={{
                      flex: 1,
                      padding: '8px 12px',
                      borderRadius: '8px',
                      background: '#1e293b',
                      border: '1px solid rgba(255, 255, 255, 0.12)',
                      color: '#f8fafc',
                      fontSize: '0.88rem'
                    }}
                  >
                    {availableTopics.map((t, idx) => (
                      <option key={idx} value={t}>{t}</option>
                    ))}
                  </select>
                </div>
              ) : (
                <input
                  type="text"
                  required
                  placeholder="e.g. Python Foundations"
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: '8px',
                    background: '#1e293b',
                    border: '1px solid rgba(255, 255, 255, 0.12)',
                    color: '#f8fafc',
                    fontSize: '0.88rem'
                  }}
                />
              )}
            </div>

            {/* Date selection */}
            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '5px' }}>
                Study Day (Date) *
              </label>
              <input
                type="date"
                min={todayStr}
                required
                value={date}
                onChange={(e) => setDate(e.target.value)}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  borderRadius: '8px',
                  background: '#1e293b',
                  border: '1px solid rgba(255, 255, 255, 0.12)',
                  color: '#f8fafc',
                  fontSize: '0.88rem'
                }}
              />
            </div>
          </div>

          {/* Multi-time alert slots */}
          <div style={{
            background: 'rgba(15, 23, 42, 0.5)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            borderRadius: '10px',
            padding: '14px'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <label style={{ fontSize: '0.82rem', fontWeight: 650, color: themeColor, display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Clock size={15} /> Alert Times for This Day (Multi-Time Scheduling)
              </label>
              <span style={{ fontSize: '0.74rem', color: '#64748b' }}>
                Pick multiple times to receive reminders
              </span>
            </div>

            <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '12px' }}>
              <input
                type="time"
                value={timeInput}
                onChange={(e) => setTimeInput(e.target.value)}
                style={{
                  padding: '6px 10px',
                  borderRadius: '6px',
                  background: '#1e293b',
                  border: '1px solid rgba(255, 255, 255, 0.12)',
                  color: '#f8fafc',
                  fontSize: '0.85rem'
                }}
              />
              <button
                type="button"
                onClick={handleAddTimeSlot}
                style={{
                  padding: '6px 14px',
                  borderRadius: '6px',
                  background: 'rgba(255, 255, 255, 0.08)',
                  border: '1px solid rgba(255, 255, 255, 0.15)',
                  color: '#f8fafc',
                  fontSize: '0.82rem',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px'
                }}
              >
                <Plus size={14} /> Add Time Slot
              </button>

              {/* Quick presets */}
              <div style={{ display: 'flex', gap: '6px', marginLeft: 'auto' }}>
                {['09:00', '14:00', '18:30', '21:00'].map((preset) => (
                  <button
                    key={preset}
                    type="button"
                    onClick={() => {
                      if (!timeSlots.includes(preset)) setTimeSlots([...timeSlots, preset].sort());
                    }}
                    style={{
                      padding: '4px 8px',
                      borderRadius: '4px',
                      background: 'rgba(30, 41, 59, 0.8)',
                      border: '1px solid rgba(255, 255, 255, 0.08)',
                      color: '#94a3b8',
                      fontSize: '0.74rem',
                      cursor: 'pointer'
                    }}
                  >
                    +{preset}
                  </button>
                ))}
              </div>
            </div>

            {/* List of active time slots */}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              {timeSlots.length === 0 ? (
                <span style={{ fontSize: '0.78rem', color: '#f87171' }}>
                  No time slots added. Please add at least one alert time.
                </span>
              ) : (
                timeSlots.map((slot) => (
                  <span
                    key={slot}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '6px',
                      padding: '4px 10px',
                      borderRadius: '20px',
                      background: `${themeColor}1a`,
                      border: `1px solid ${themeColor}40`,
                      color: themeColor,
                      fontSize: '0.82rem',
                      fontWeight: 600
                    }}
                  >
                    <Clock size={12} />
                    {slot}
                    <button
                      type="button"
                      onClick={() => handleRemoveTimeSlot(slot)}
                      style={{
                        background: 'none',
                        border: 'none',
                        padding: '0',
                        color: 'inherit',
                        cursor: 'pointer',
                        display: 'flex'
                      }}
                      title="Remove time"
                    >
                      <X size={12} />
                    </button>
                  </span>
                ))
              )}
            </div>
          </div>

          {/* Email & Notes */}
          <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '12px' }}>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                <label style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                  Alert Email (from Profile) *
                </label>
                {emailServiceStatus.configured ? (
                  <span style={{ fontSize: '0.72rem', color: '#34d399', fontWeight: 650 }}>
                    ✓ Real Gmail SMTP Active
                  </span>
                ) : (
                  <button
                    type="button"
                    onClick={() => setShowSmtpConfig(true)}
                    style={{ background: 'none', border: 'none', color: '#fbbf24', fontSize: '0.72rem', cursor: 'pointer', textDecoration: 'underline', padding: 0 }}
                  >
                    ⚙️ Setup Gmail Inbox Delivery
                  </button>
                )}
              </div>
              <div style={{ position: 'relative' }}>
                <input
                  type="email"
                  required
                  placeholder="student@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 12px 8px 34px',
                    borderRadius: '8px',
                    background: '#1e293b',
                    border: '1px solid rgba(255, 255, 255, 0.12)',
                    color: '#f8fafc',
                    fontSize: '0.88rem'
                  }}
                />
                <Mail size={15} style={{ position: 'absolute', left: '10px', top: '10px', color: '#64748b' }} />
              </div>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '4px' }}>
                Study Goal / Note (optional)
              </label>
              <input
                type="text"
                placeholder="e.g. Master loops before exam"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  borderRadius: '8px',
                  background: '#1e293b',
                  border: '1px solid rgba(255, 255, 255, 0.12)',
                  color: '#f8fafc',
                  fontSize: '0.88rem'
                }}
              />
            </div>
          </div>

          {/* Submit button */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '4px' }}>
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
              disabled={saving}
              style={{
                padding: '8px 22px',
                borderRadius: '8px',
                background: isRevise
                  ? 'linear-gradient(135deg, #0d9488, #0284c7)'
                  : 'linear-gradient(135deg, #9333ea, #6366f1)',
                border: 'none',
                color: '#ffffff',
                fontWeight: 650,
                fontSize: '0.88rem',
                cursor: saving ? 'wait' : 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                boxShadow: `0 4px 14px ${isRevise ? 'rgba(13, 148, 136, 0.35)' : 'rgba(147, 51, 234, 0.35)'}`
              }}
            >
              <Bell size={16} />
              {saving ? 'Scheduling & Dispatching Alert...' : `Confirm & Send Email Alert`}
            </button>
          </div>
        </form>

        {/* Collapsible SMTP Configuration Option */}
        <div style={{ marginTop: '16px', borderTop: '1px solid rgba(255, 255, 255, 0.08)', paddingTop: '12px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <button
              type="button"
              onClick={() => setShowSmtpConfig(!showSmtpConfig)}
              style={{
                background: 'none',
                border: 'none',
                color: '#94a3b8',
                fontSize: '0.8rem',
                fontWeight: 650,
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '0'
              }}
            >
              <Settings size={14} />
              <span>⚙️ Real Email Inbox Settings (Gmail / Brevo SMTP)</span>
              {showSmtpConfig ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            </button>

            {emailServiceStatus.configured && (
              <button
                type="button"
                onClick={handleSendTestEmail}
                disabled={testingSmtp}
                style={{
                  background: 'rgba(56, 189, 248, 0.15)',
                  border: '1px solid rgba(56, 189, 248, 0.3)',
                  color: '#38bdf8',
                  padding: '3px 10px',
                  borderRadius: '6px',
                  fontSize: '0.74rem',
                  fontWeight: 650,
                  cursor: 'pointer',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px'
                }}
              >
                <Send size={11} /> {testingSmtp ? 'Sending...' : 'Send Test Verification Email'}
              </button>
            )}
          </div>

          {showSmtpConfig && (
            <form onSubmit={handleSaveSmtp} style={{
              marginTop: '10px',
              padding: '14px',
              background: 'rgba(15, 23, 42, 0.65)',
              borderRadius: '10px',
              border: '1px solid rgba(45, 212, 191, 0.2)',
              display: 'flex',
              flexDirection: 'column',
              gap: '10px'
            }}>
              <div style={{ fontSize: '0.8rem', color: '#f1f5f9', fontWeight: 650 }}>
                How to receive study alerts directly in your personal Gmail inbox:
              </div>
              <p style={{ margin: 0, fontSize: '0.76rem', color: '#94a3b8', lineHeight: 1.5 }}>
                1. Open <a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noopener noreferrer" style={{ color: '#38bdf8', textDecoration: 'underline' }}>Google App Passwords</a>.<br />
                2. Type app name "EduNexus" and generate a 16-character code.<br />
                3. Paste the code below and click "Save & Verify".
              </p>

              <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '8px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.72rem', color: '#94a3b8' }}>SMTP Host</label>
                  <input
                    type="text"
                    value={smtpHost}
                    onChange={(e) => setSmtpHost(e.target.value)}
                    placeholder="smtp.gmail.com"
                    style={{
                      width: '100%',
                      padding: '6px 8px',
                      borderRadius: '6px',
                      background: '#1e293b',
                      border: '1px solid rgba(255, 255, 255, 0.1)',
                      color: '#f8fafc',
                      fontSize: '0.8rem'
                    }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.72rem', color: '#94a3b8' }}>Port</label>
                  <input
                    type="number"
                    value={smtpPort}
                    onChange={(e) => setSmtpPort(e.target.value)}
                    placeholder="587"
                    style={{
                      width: '100%',
                      padding: '6px 8px',
                      borderRadius: '6px',
                      background: '#1e293b',
                      border: '1px solid rgba(255, 255, 255, 0.1)',
                      color: '#f8fafc',
                      fontSize: '0.8rem'
                    }}
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.72rem', color: '#94a3b8' }}>Your Gmail Address</label>
                  <input
                    type="email"
                    value={smtpUser}
                    onChange={(e) => setSmtpUser(e.target.value)}
                    placeholder="you@gmail.com"
                    style={{
                      width: '100%',
                      padding: '6px 8px',
                      borderRadius: '6px',
                      background: '#1e293b',
                      border: '1px solid rgba(255, 255, 255, 0.1)',
                      color: '#f8fafc',
                      fontSize: '0.8rem'
                    }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.72rem', color: '#94a3b8' }}>Google 16-Letter App Password</label>
                  <input
                    type="password"
                    value={smtpPass}
                    onChange={(e) => setSmtpPass(e.target.value)}
                    placeholder="e.g. abcd efgh ijkl mnop"
                    style={{
                      width: '100%',
                      padding: '6px 8px',
                      borderRadius: '6px',
                      background: '#1e293b',
                      border: '1px solid rgba(255, 255, 255, 0.1)',
                      color: '#f8fafc',
                      fontSize: '0.8rem'
                    }}
                  />
                </div>
              </div>

              {smtpMsg && (
                <div style={{
                  padding: '6px 10px',
                  borderRadius: '6px',
                  background: smtpMsg.startsWith('Error') ? 'rgba(239, 68, 68, 0.15)' : 'rgba(16, 185, 129, 0.15)',
                  border: smtpMsg.startsWith('Error') ? '1px solid rgba(239, 68, 68, 0.3)' : '1px solid rgba(16, 185, 129, 0.3)',
                  fontSize: '0.76rem',
                  color: smtpMsg.startsWith('Error') ? '#fca5a5' : '#6ee7b7'
                }}>
                  {smtpMsg}
                </div>
              )}

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
                <button
                  type="submit"
                  disabled={savingSmtp}
                  style={{
                    padding: '6px 16px',
                    borderRadius: '6px',
                    background: 'linear-gradient(135deg, #0d9488, #0284c7)',
                    border: 'none',
                    color: '#ffffff',
                    fontSize: '0.8rem',
                    fontWeight: 650,
                    cursor: 'pointer',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '6px',
                    boxShadow: '0 2px 8px rgba(13, 148, 136, 0.3)'
                  }}
                >
                  <Save size={13} /> {savingSmtp ? 'Verifying & Saving...' : 'Save & Verify Email'}
                </button>
              </div>
            </form>
          )}
        </div>

        {/* Existing schedules list */}
        <div style={{ marginTop: '20px', borderTop: '1px solid rgba(255, 255, 255, 0.08)', paddingTop: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <h4 style={{ fontSize: '0.9rem', fontWeight: 650, margin: 0, color: '#cbd5e1' }}>
              Existing Scheduled {modeTitle}s ({existingSchedules.length})
            </h4>
            <button
              type="button"
              onClick={loadSchedules}
              style={{
                background: 'none',
                border: 'none',
                color: '#2dd4bf',
                fontSize: '0.74rem',
                cursor: 'pointer',
                textDecoration: 'underline'
              }}
            >
              Refresh
            </button>
          </div>

          {loading && existingSchedules.length === 0 ? (
            <div style={{ fontSize: '0.82rem', color: '#94a3b8' }}>Loading schedules...</div>
          ) : existingSchedules.length === 0 ? (
            <div style={{ fontSize: '0.82rem', color: '#64748b' }}>
              No upcoming {mode} sessions scheduled yet.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '180px', overflowY: 'auto' }}>
              {existingSchedules.map((item) => {
                const slots = Array.isArray(item.time_slots)
                  ? item.time_slots
                  : (typeof item.time_slots === 'string' && item.time_slots.startsWith('[')
                    ? JSON.parse(item.time_slots)
                    : [item.time_slots]);

                return (
                  <div
                    key={item.id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '8px 12px',
                      borderRadius: '8px',
                      background: 'rgba(15, 23, 42, 0.6)',
                      border: '1px solid rgba(255, 255, 255, 0.06)'
                    }}
                  >
                    <div>
                      <div style={{ fontSize: '0.86rem', fontWeight: 600, color: '#f1f5f9' }}>
                        {item.topic}
                      </div>
                      <div style={{ fontSize: '0.76rem', color: '#94a3b8', display: 'flex', gap: '10px', marginTop: '2px', flexWrap: 'wrap' }}>
                        <span>📅 {item.date}</span>
                        <span>⏰ {Array.isArray(slots) ? slots.join(', ') : slots}</span>
                        {item.email && <span>✉️ {item.email}</span>}
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={() => handleDeleteSchedule(item.id)}
                      style={{
                        background: 'none',
                        border: 'none',
                        color: '#ef4444',
                        cursor: 'pointer',
                        padding: '6px',
                        borderRadius: '4px'
                      }}
                      title="Cancel schedule"
                    >
                      <Trash2 size={15} />
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
      </div>
    </div>
  );
}
