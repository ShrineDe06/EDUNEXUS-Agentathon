import React, { useState, useEffect } from 'react';
import {
  ArrowLeft,
  BookOpen,
  CheckCircle2,
  Sparkles,
  AlertCircle,
  Layers,
  HelpCircle,
  RefreshCw,
  Plus,
  Trash2,
  Clock,
  History,
  Check,
  ChevronRight,
  Calendar
} from 'lucide-react';
import FlashcardDeck from '../components/FlashcardDeck';
import FormattedText from '../components/FormattedText';
import ScheduleModal from '../components/ScheduleModal';

function RevisionThinkingIndicator() {
  const [stage, setStage] = useState(0);
  const stages = [
    'Inspecting chat history & question patterns...',
    'Analyzing repeated concepts & self-explanations...',
    'Cross-referencing quiz mistakes & misconceptions...',
    'Synthesizing targeted explanation & interactive flashcards...',
    'Saving revision session locally under this topic...',
  ];

  useEffect(() => {
    const timers = [
      setTimeout(() => setStage(1), 1600),
      setTimeout(() => setStage(2), 3400),
      setTimeout(() => setStage(3), 5600),
      setTimeout(() => setStage(4), 8000),
    ];
    return () => timers.forEach(clearTimeout);
  }, []);

  return (
    <div style={{ padding: '60px 20px', textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px' }}>
      <div className="shimmer-indicator-bubble shimmer-indicator-bubble--flashcards">
        <div className="generation-skeleton" aria-hidden="true">
          <i />
          <i />
          <i />
        </div>
        <span key={stage} className="thinking-text shimmer-stage-animate">
          {stages[stage]}
        </span>
      </div>
      <p style={{ fontSize: '0.82rem', color: '#94a3b8', maxWidth: '420px', margin: '0 auto' }}>
        EduNexus is evaluating your chat interaction patterns and test history to build and store your personalized revision session.
      </p>
    </div>
  );
}

function formatRelativeTime(dateString) {
  if (!dateString) return '';
  const date = new Date(dateString);
  const now = new Date();
  const diffSec = Math.floor((now - date) / 1000);
  if (diffSec < 60) return 'Just now';
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHours = Math.floor(diffMin / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

export default function Revise({ studentId, studentProfile, onRefreshProfile }) {
  const [topics, setTopics] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedTopic, setSelectedTopic] = useState(null);
  const [showScheduleModal, setShowScheduleModal] = useState(false);

  // Topic sessions state
  const [topicSessions, setTopicSessions] = useState([]);
  const [selectedSessionId, setSelectedSessionId] = useState(null);
  const [loadingSession, setLoadingSession] = useState(false);

  // Active revision session data
  const [revisionData, setRevisionData] = useState(null);
  const [revisionLoading, setRevisionLoading] = useState(false);
  const [answers, setAnswers] = useState({});
  const [verifyResult, setVerifyResult] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    fetchTopics();
  }, [studentId]);

  const fetchTopics = async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/revise/topics/${studentId}`);
      const data = await res.json();
      setTopics(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Error fetching revision topics:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectTopic = async (topicName) => {
    setSelectedTopic(topicName);
    setRevisionData(null);
    setSelectedSessionId(null);
    setVerifyResult(null);
    setAnswers({});
    setLoadingSession(true);

    try {
      const res = await fetch(`/api/revise/sessions/${studentId}/${encodeURIComponent(topicName)}`);
      const sessions = await res.json();
      const sessionList = Array.isArray(sessions) ? sessions : [];
      setTopicSessions(sessionList);

      if (sessionList.length > 0) {
        // Load the most recent session
        await loadSession(sessionList[0].id);
      } else {
        // No sessions exist yet for this topic -> generate the first one automatically
        await handleGenerateNewRevision(topicName);
      }
    } catch (err) {
      console.error('Error loading topic revision sessions:', err);
    } finally {
      setLoadingSession(false);
    }
  };

  const loadSession = async (sessionId) => {
    setLoadingSession(true);
    try {
      const res = await fetch(`/api/revise/session/${sessionId}`);
      if (!res.ok) throw new Error('Could not fetch revision session');
      const data = await res.json();
      setRevisionData(data);
      setSelectedSessionId(sessionId);
      setAnswers(data.answers || {});
      setVerifyResult(data.verify_result || null);
    } catch (err) {
      console.error('Error fetching session details:', err);
      alert(`Error loading session: ${err.message}`);
    } finally {
      setLoadingSession(false);
    }
  };

  const handleGenerateNewRevision = async (topicName = selectedTopic) => {
    if (!topicName) return;
    setRevisionLoading(true);
    setVerifyResult(null);
    setAnswers({});

    try {
      const res = await fetch('/api/revise/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ student_id: studentId, topic: topicName })
      });
      if (!res.ok) throw new Error('Revision generation failed');
      const savedSession = await res.json();

      // Update state with newly saved session
      setRevisionData(savedSession);
      setSelectedSessionId(savedSession.id);

      // Prepend to topicSessions list
      setTopicSessions((prev) => {
        const filtered = prev.filter((s) => s.id !== savedSession.id);
        return [savedSession, ...filtered];
      });

      // Refresh topics list to reflect incremented revision count
      fetchTopics();
    } catch (err) {
      console.error('Error generating revision:', err);
      alert(`Error starting revision: ${err.message}`);
    } finally {
      setRevisionLoading(false);
    }
  };

  const handleDeleteSession = async (e, sessionId) => {
    e.stopPropagation();
    if (!window.confirm('Are you sure you want to delete this revision session?')) {
      return;
    }

    try {
      const res = await fetch(`/api/revise/session/${sessionId}`, {
        method: 'DELETE',
      });
      if (!res.ok) throw new Error('Failed to delete session');

      const updated = topicSessions.filter((s) => s.id !== sessionId);
      setTopicSessions(updated);
      fetchTopics();

      // If we deleted the active session, switch to next available or generate/reset
      if (selectedSessionId === sessionId) {
        if (updated.length > 0) {
          loadSession(updated[0].id);
        } else {
          setRevisionData(null);
          setSelectedSessionId(null);
        }
      }
    } catch (err) {
      alert(`Could not delete session: ${err.message}`);
    }
  };

  const handleVerify = async () => {
    if (!revisionData?.questions) return;
    setSubmitting(true);
    try {
      const res = await fetch('/api/revise/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          student_id: studentId,
          topic: selectedTopic,
          answers: answers,
          questions: revisionData.questions,
          session_id: revisionData.id
        })
      });
      const data = await res.json();
      setVerifyResult(data);

      // Update active session locally
      setRevisionData((prev) => ({
        ...prev,
        answers: answers,
        verify_result: data,
        passed: data.passed,
        score: data.score
      }));

      // Update session status in pills list
      setTopicSessions((prev) =>
        prev.map((s) =>
          s.id === revisionData.id
            ? { ...s, passed: data.passed, score: data.score }
            : s
        )
      );

      onRefreshProfile?.();
      fetchTopics();
    } catch (err) {
      alert(`Verification error: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  const diagnosis = revisionData?.diagnosis;
  const hasSignals = diagnosis?.has_signals;

  return (
    <div style={{ maxWidth: '1020px', margin: '0 auto', padding: '30px 20px' }}>
      {/* Header */}
      <div className="glass-card" style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 700, marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <RefreshCw size={22} style={{ color: '#818cf8' }} />
            Revise mode — Memory & Chat-Driven Learning
          </h2>
          <p style={{ fontSize: '0.88rem', color: '#94a3b8', margin: 0 }}>
            Deeply inspects your Learn chat questions, self-explanations, and quiz attempts to target exact weak points.
            All revision sessions and flashcard decks are stored locally under their topic.
          </p>
        </div>

        <button
          onClick={() => setShowScheduleModal(true)}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            padding: '8px 16px',
            borderRadius: '8px',
            background: 'linear-gradient(135deg, #0d9488, #0284c7)',
            border: 'none',
            color: '#ffffff',
            fontSize: '0.85rem',
            fontWeight: 650,
            cursor: 'pointer',
            boxShadow: '0 4px 12px rgba(13, 148, 136, 0.3)',
            flexShrink: 0
          }}
        >
          <Calendar size={15} /> Schedule Revision
        </button>
      </div>

      {!selectedTopic ? (
        /* TOPICS DASHBOARD */
        <div>
          <h3 style={{ fontSize: '1.1rem', color: '#818cf8', marginBottom: '16px' }}>
            Available Topics for Revision ({topics.length})
          </h3>

          {loading ? (
            <div className="glass-card" style={{ textAlign: 'center', padding: '30px' }}>
              <span className="skeleton-shimmer-text">Loading learner memory & topics...</span>
            </div>
          ) : topics.length === 0 ? (
            <div className="glass-card" style={{ textAlign: 'center', padding: '40px' }}>
              <p style={{ fontSize: '1.1rem', color: '#94a3b8' }}>
                No active topics found from your Learn workspace for <strong>{studentId}</strong> yet.
              </p>
              <p style={{ fontSize: '0.9rem', color: '#64748b', marginTop: '8px' }}>
                Go to <strong>LEARN</strong> mode to create a chat session and start studying!
              </p>
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '20px' }}>
              {topics.map((t, idx) => (
                <div
                  key={idx}
                  className="glass-card"
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    transition: 'transform 0.2s, border-color 0.2s',
                    cursor: 'pointer'
                  }}
                  onClick={() => handleSelectTopic(t.topic)}
                >
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                      <h4 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#f8fafc' }}>
                        {t.topic}
                      </h4>
                      <span className={`badge ${t.status === 'MASTERED' ? 'badge-mastered' : 'badge-revision'}`}>
                        {t.status}
                      </span>
                    </div>

                    {t.document_name && (
                      <div style={{ fontSize: '0.78rem', color: '#38bdf8', marginBottom: '8px' }}>
                        Source: {t.document_name}
                      </div>
                    )}

                    {/* Revision Sessions Count Badge */}
                    <div style={{ marginBottom: '10px' }}>
                      <span
                        style={{
                          fontSize: '0.75rem',
                          color: '#a5b4fc',
                          background: 'rgba(99, 102, 241, 0.12)',
                          border: '1px solid rgba(129, 140, 248, 0.25)',
                          padding: '3px 8px',
                          borderRadius: '6px',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '5px'
                        }}
                      >
                        <History size={12} />
                        {t.revision_count > 0
                          ? `${t.revision_count} Saved Revision${t.revision_count > 1 ? 's' : ''}`
                          : 'No revisions yet'}
                      </span>
                    </div>

                    {t.misconceptions && t.misconceptions.length > 0 && (
                      <div style={{ background: 'rgba(239, 68, 68, 0.12)', padding: '10px 12px', borderRadius: '8px', marginBottom: '12px', border: '1px solid rgba(239, 68, 68, 0.25)' }}>
                        <div style={{ fontSize: '0.72rem', color: '#f87171', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '5px' }}>
                          <AlertCircle size={13} /> ACTIVE MISCONCEPTION
                        </div>
                        <div style={{ fontSize: '0.82rem', color: '#fca5a5', marginTop: '3px' }}>
                          {t.misconceptions[0].misconception}
                        </div>
                      </div>
                    )}

                    {t.weak_subconcepts && t.weak_subconcepts.length > 0 && (
                      <div style={{ fontSize: '0.82rem', color: '#f87171', marginBottom: '12px' }}>
                        Weak Areas: {t.weak_subconcepts.join(', ')}
                      </div>
                    )}
                  </div>

                  <button
                    className="btn-primary"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleSelectTopic(t.topic);
                    }}
                    style={{
                      width: '100%',
                      justifyContent: 'center',
                      marginTop: '16px',
                      background: 'linear-gradient(90deg, #6366f1, #818cf8)',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px'
                    }}
                  >
                    Open Revisions for {t.topic} <ChevronRight size={15} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : (
        /* REVISION TOPIC WORKSPACE & SESSIONS */
        <div>
          {/* Top navigation and action bar */}
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '12px',
              marginBottom: '20px'
            }}
          >
            <button
              className="btn-secondary"
              onClick={() => {
                setSelectedTopic(null);
                setRevisionData(null);
                setSelectedSessionId(null);
              }}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
            >
              <ArrowLeft size={16} /> Back to Revision Topics
            </button>

            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <button
                className="btn-primary"
                onClick={() => handleGenerateNewRevision(selectedTopic)}
                disabled={revisionLoading}
                style={{
                  background: 'linear-gradient(90deg, #6366f1, #a855f7)',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  boxShadow: '0 4px 14px rgba(99, 102, 241, 0.3)'
                }}
              >
                <Plus size={16} />
                Generate New Revision in {selectedTopic}
              </button>
            </div>
          </div>

          {/* Local Revision Sessions Selector (Tabs / Pills) */}
          <div
            className="glass-card"
            style={{
              padding: '16px 18px',
              marginBottom: '24px',
              background: 'rgba(15, 23, 42, 0.65)'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <History size={16} style={{ color: '#818cf8' }} />
                <span style={{ fontSize: '0.88rem', fontWeight: 700, color: '#f8fafc' }}>
                  Saved Sessions for {selectedTopic}
                </span>
                <span style={{ fontSize: '0.78rem', color: '#94a3b8' }}>
                  ({topicSessions.length})
                </span>
              </div>
              <span style={{ fontSize: '0.74rem', color: '#64748b' }}>
                Saved locally as "Revision 'n' in {selectedTopic}"
              </span>
            </div>

            {topicSessions.length === 0 && !revisionLoading ? (
              <div style={{ textAlign: 'center', padding: '16px', color: '#94a3b8', fontSize: '0.86rem' }}>
                No revision sessions saved for this topic yet. Click <strong>Generate New Revision</strong> above.
              </div>
            ) : (
              <div
                style={{
                  display: 'flex',
                  gap: '10px',
                  overflowX: 'auto',
                  paddingBottom: '6px',
                  scrollbarWidth: 'thin'
                }}
              >
                {topicSessions.map((s) => {
                  const isActive = s.id === selectedSessionId;
                  const isPassed = s.passed === true;
                  const isFailed = s.passed === false;

                  return (
                    <div
                      key={s.id}
                      onClick={() => !isActive && loadSession(s.id)}
                      style={{
                        padding: '8px 14px',
                        borderRadius: '10px',
                        cursor: isActive ? 'default' : 'pointer',
                        background: isActive
                          ? 'linear-gradient(135deg, rgba(99, 102, 241, 0.35), rgba(168, 85, 247, 0.25))'
                          : 'rgba(30, 41, 59, 0.7)',
                        border: isActive
                          ? '1px solid rgba(129, 140, 248, 0.6)'
                          : '1px solid rgba(148, 163, 184, 0.16)',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '10px',
                        flexShrink: 0,
                        transition: 'all 0.2s ease',
                        boxShadow: isActive ? '0 4px 15px rgba(99, 102, 241, 0.2)' : 'none'
                      }}
                    >
                      <div>
                        <div style={{ fontSize: '0.86rem', fontWeight: 650, color: isActive ? '#f8fafc' : '#cbd5e1' }}>
                          {s.title}
                        </div>
                        <div style={{ fontSize: '0.7rem', color: '#94a3b8', display: 'flex', alignItems: 'center', gap: '6px', marginTop: '2px' }}>
                          <span>{formatRelativeTime(s.created_at)}</span>
                          {isPassed && (
                            <span style={{ color: '#34d399', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '3px' }}>
                              <Check size={11} /> Mastered
                            </span>
                          )}
                          {isFailed && (
                            <span style={{ color: '#f87171', fontWeight: 700 }}>
                              Remediation
                            </span>
                          )}
                          {s.passed === null && (
                            <span style={{ color: '#fbbf24' }}>
                              In Progress
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Delete Session Button */}
                      <button
                        onClick={(e) => handleDeleteSession(e, s.id)}
                        title="Delete this revision session"
                        style={{
                          background: 'transparent',
                          border: 'none',
                          color: '#64748b',
                          padding: '4px',
                          borderRadius: '6px',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          cursor: 'pointer',
                          transition: 'color 0.2s'
                        }}
                        onMouseEnter={(e) => (e.currentTarget.style.color = '#ef4444')}
                        onMouseLeave={(e) => (e.currentTarget.style.color = '#64748b')}
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Revision Content or Shimmer Loading */}
          {revisionLoading ? (
            <RevisionThinkingIndicator />
          ) : loadingSession ? (
            <div className="glass-card" style={{ textAlign: 'center', padding: '40px' }}>
              <span className="skeleton-shimmer-text">Loading revision session...</span>
            </div>
          ) : revisionData ? (
            <div>
              {/* Session Banner */}
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginBottom: '16px',
                  padding: '12px 16px',
                  borderRadius: '10px',
                  background: 'rgba(30, 27, 75, 0.4)',
                  border: '1px solid rgba(129, 140, 248, 0.2)'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Sparkles size={18} style={{ color: '#818cf8' }} />
                  <span style={{ fontSize: '1rem', fontWeight: 700, color: '#f1f5f9' }}>
                    {revisionData.title}
                  </span>
                  <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                    (Saved locally on {new Date(revisionData.created_at).toLocaleString()})
                  </span>
                </div>

                {verifyResult && (
                  <span className={`badge ${verifyResult.passed ? 'badge-mastered' : 'badge-revision'}`}>
                    {verifyResult.passed ? '✓ MASTERED' : 'NEEDS REMEDIATION'}
                  </span>
                )}
              </div>

              {/* Weakness Diagnosis Report */}
              {hasSignals && diagnosis && (
                <div
                  style={{
                    background: 'linear-gradient(145deg, rgba(30, 27, 75, 0.8), rgba(15, 23, 42, 0.9))',
                    border: '1px solid rgba(129, 140, 248, 0.3)',
                    borderRadius: '14px',
                    padding: '20px',
                    marginBottom: '24px',
                    boxShadow: '0 8px 30px rgba(0,0,0,0.3)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#a5b4fc', fontSize: '0.85rem', fontWeight: 700, marginBottom: '8px' }}>
                    <Sparkles size={16} /> LEARNER WEAKNESS ANALYSIS (FROM CHAT & TESTS)
                  </div>
                  <p style={{ fontSize: '0.98rem', color: '#e2e8f0', lineHeight: 1.55, marginBottom: '14px' }}>
                    {diagnosis.diagnosis_summary}
                  </p>

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '10px' }}>
                    {diagnosis.repeated_questions && diagnosis.repeated_questions.length > 0 && (
                      <div style={{ background: 'rgba(51, 65, 85, 0.5)', padding: '10px 12px', borderRadius: '8px', border: '1px solid rgba(148, 163, 184, 0.15)' }}>
                        <strong style={{ fontSize: '0.72rem', color: '#38bdf8', textTransform: 'uppercase', display: 'block', marginBottom: '4px' }}>
                          Repeated Chat Questions
                        </strong>
                        <ul style={{ margin: 0, paddingLeft: '16px', fontSize: '0.82rem', color: '#cbd5e1' }}>
                          {diagnosis.repeated_questions.map((q, i) => <li key={i}>{q}</li>)}
                        </ul>
                      </div>
                    )}

                    {diagnosis.faulty_explanations && diagnosis.faulty_explanations.length > 0 && (
                      <div style={{ background: 'rgba(239, 68, 68, 0.1)', padding: '10px 12px', borderRadius: '8px', border: '1px solid rgba(239, 68, 68, 0.2)' }}>
                        <strong style={{ fontSize: '0.72rem', color: '#f87171', textTransform: 'uppercase', display: 'block', marginBottom: '4px' }}>
                          Detected Misconceptions in Chat
                        </strong>
                        <ul style={{ margin: 0, paddingLeft: '16px', fontSize: '0.82rem', color: '#fca5a5' }}>
                          {diagnosis.faulty_explanations.map((e, i) => <li key={i}>{e}</li>)}
                        </ul>
                      </div>
                    )}

                    {diagnosis.quiz_errors && diagnosis.quiz_errors.length > 0 && (
                      <div style={{ background: 'rgba(245, 158, 11, 0.1)', padding: '10px 12px', borderRadius: '8px', border: '1px solid rgba(245, 158, 11, 0.2)' }}>
                        <strong style={{ fontSize: '0.72rem', color: '#fbbf24', textTransform: 'uppercase', display: 'block', marginBottom: '4px' }}>
                          Test Pitfalls to Resolve
                        </strong>
                        <ul style={{ margin: 0, paddingLeft: '16px', fontSize: '0.82rem', color: '#fde68a' }}>
                          {diagnosis.quiz_errors.map((qe, i) => <li key={i}>{qe}</li>)}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Targeted Revision Text */}
              <div className="glass-card" style={{ marginBottom: '24px' }}>
                <h3 style={{ fontSize: '1.25rem', color: '#818cf8', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <BookOpen size={20} /> Targeted Revision Lesson: {selectedTopic}
                </h3>
                <div style={{ background: 'rgba(15, 23, 42, 0.75)', padding: '22px', borderRadius: '12px', borderLeft: '4px solid #818cf8' }}>
                  <FormattedText content={revisionData.revision_lesson} />
                </div>
              </div>

              {/* Interactive Flashcard Deck (At the end of text generation) */}
              {revisionData.flashcards && revisionData.flashcards.cards && revisionData.flashcards.cards.length > 0 && (
                <div className="glass-card" style={{ marginBottom: '28px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
                    <Layers size={20} style={{ color: '#a78bfa' }} />
                    <h3 style={{ fontSize: '1.15rem', color: '#a78bfa', margin: 0 }}>
                      Quick Lesson Revision Deck
                    </h3>
                  </div>
                  <p style={{ fontSize: '0.82rem', color: '#94a3b8', marginBottom: '16px' }}>
                    Flip each card to reinforce core formulas, worked examples, and key ideas before taking your verification quiz.
                  </p>
                  <div style={{ display: 'flex', justifyContent: 'center' }}>
                    <FlashcardDeck data={revisionData.flashcards} />
                  </div>
                </div>
              )}

              {/* 2-Question Revision Verification Quiz */}
              {revisionData.questions && revisionData.questions.length > 0 && (
                <div className="glass-card">
                  <h4 style={{ fontSize: '1.15rem', color: '#f8fafc', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <HelpCircle size={18} style={{ color: '#38bdf8' }} />
                    Mastery Verification Quiz ({revisionData.questions.length} questions)
                  </h4>
                  <p style={{ fontSize: '0.82rem', color: '#94a3b8', marginBottom: '18px' }}>
                    Demonstrate that you have resolved the prior misconceptions to achieve MASTERED status.
                  </p>

                  {revisionData.questions.map((q, qIdx) => {
                    const qId = q.id || `rq${qIdx + 1}`;
                    const selectedAnswer = answers[qId] || '';
                    const isSubmitted = Boolean(verifyResult);

                    return (
                      <div
                        key={qId}
                        style={{
                          background: 'rgba(30, 41, 59, 0.6)',
                          padding: '16px',
                          borderRadius: '10px',
                          marginBottom: '16px'
                        }}
                      >
                        <p style={{ fontWeight: 600, marginBottom: '10px', fontSize: '0.92rem', color: '#f1f5f9' }}>
                          Q{qIdx + 1} <span style={{ color: '#38bdf8', fontWeight: 500 }}>({q.sub_concept})</span>: {q.question}
                        </p>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                          {q.options.map((opt, optIdx) => (
                            <label
                              key={optIdx}
                              style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '8px',
                                cursor: isSubmitted ? 'default' : 'pointer',
                                fontSize: '0.88rem',
                                color: '#cbd5e1',
                                padding: '6px 8px',
                                borderRadius: '6px',
                                background: selectedAnswer === opt ? 'rgba(99, 102, 241, 0.15)' : 'transparent'
                              }}
                            >
                              <input
                                type="radio"
                                name={qId}
                                value={opt}
                                checked={selectedAnswer === opt}
                                disabled={isSubmitted}
                                onChange={() => setAnswers((prev) => ({ ...prev, [qId]: opt }))}
                              />
                              <span>{opt}</span>
                            </label>
                          ))}
                        </div>
                      </div>
                    );
                  })}

                  {!verifyResult ? (
                    <button
                      className="btn-primary"
                      onClick={handleVerify}
                      disabled={submitting || Object.keys(answers).length < revisionData.questions.length}
                      style={{ marginTop: '8px' }}
                    >
                      {submitting ? 'Verifying...' : 'Submit Verification Quiz'}
                    </button>
                  ) : (
                    <div style={{ marginTop: '20px' }}>
                      <div
                        className={`badge ${verifyResult.passed ? 'badge-mastered' : 'badge-revision'}`}
                        style={{ fontSize: '1rem', padding: '8px 16px', marginBottom: '14px' }}
                      >
                        {verifyResult.passed ? '✓ MASTERED' : '⚠ NEEDS REMEDIATION'}
                      </div>
                      <p style={{ fontSize: '0.95rem', marginBottom: '16px', color: '#e2e8f0' }}>
                        {verifyResult.message}
                      </p>

                      {verifyResult.remediation && (
                        <div
                          style={{
                            background: 'rgba(15, 23, 42, 0.9)',
                            padding: '18px',
                            borderRadius: '12px',
                            borderLeft: '4px solid #f87171'
                          }}
                        >
                          <h5 style={{ color: '#f87171', marginBottom: '8px', fontWeight: 700 }}>
                            Remediation Strategy:
                          </h5>
                          <p style={{ color: '#cbd5e1', fontSize: '0.9rem', lineHeight: 1.55 }}>
                            {verifyResult.remediation.explanation || verifyResult.remediation.content}
                          </p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div className="glass-card" style={{ textAlign: 'center', padding: '40px' }}>
              <p style={{ color: '#94a3b8', fontSize: '0.95rem' }}>
                Click <strong>Generate New Revision</strong> to create a personalized revision session.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Scheduling Modal */}
      <ScheduleModal
        isOpen={showScheduleModal}
        onClose={() => setShowScheduleModal(false)}
        studentId={studentId}
        studentProfile={studentProfile}
        mode="revise"
        defaultTopic={selectedTopic || ''}
        availableTopics={topics.map((t) => t.topic)}
      />
    </div>
  );
}
