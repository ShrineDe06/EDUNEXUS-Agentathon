import React, { useState, useEffect } from 'react';
import { 
  BarChart3, 
  CheckCircle2, 
  Sparkles, 
  RefreshCw, 
  Calendar, 
  TrendingUp, 
  BookOpen, 
  GraduationCap, 
  Clock, 
  Award,
  Trash2,
  Zap,
  Check,
  AlertCircle,
  Target,
  AlertTriangle,
  ArrowRight
} from 'lucide-react';
import FormattedText from '../components/FormattedText';

export default function Progress({ studentId, studentProfile, setMode }) {
  const [data, setData] = useState(null);
  const [hasReport, setHasReport] = useState(false);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [generatingStage, setGeneratingStage] = useState(0);
  const [notification, setNotification] = useState('');
  const [error, setError] = useState(null);

  const stages = [
    'Aggregating chat patterns, self-explanations & misconception signals...',
    'Evaluating diagnostic test scores & per-question hesitation timings...',
    'Cross-referencing revision deck completions & retention stability...',
    'Formulating cognitive diagnostic feedback & study timetable...',
  ];

  // Load latest report on mount
  useEffect(() => {
    fetchLatestReport();
  }, [studentId]);

  const fetchLatestReport = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch(`/api/progress/latest/${studentId}`);
      if (!res.ok) throw new Error('Failed to load progress data');
      const json = await res.json();
      if (json.has_report && json.report) {
        setData(json.report);
        setHasReport(true);
      } else {
        setData(null);
        setHasReport(false);
      }
    } catch (err) {
      console.error(err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Generate latest report on demand
  const handleGenerateLatestReport = async () => {
    try {
      setGenerating(true);
      setGeneratingStage(0);
      setError(null);

      const stageTimer1 = setTimeout(() => setGeneratingStage(1), 1400);
      const stageTimer2 = setTimeout(() => setGeneratingStage(2), 3000);
      const stageTimer3 = setTimeout(() => setGeneratingStage(3), 4800);

      const res = await fetch(`/api/progress/generate/${studentId}`, {
        method: 'POST',
      });

      clearTimeout(stageTimer1);
      clearTimeout(stageTimer2);
      clearTimeout(stageTimer3);

      if (!res.ok) throw new Error('Failed to generate progress report');
      const json = await res.json();
      if (json.report) {
        setData(json.report);
        setHasReport(true);
        setNotification('Latest progress report synthesized and saved!');
        setTimeout(() => setNotification(''), 4000);
      }
    } catch (err) {
      console.error(err);
      setError(err.message);
    } finally {
      setGenerating(false);
    }
  };

  const handleDeleteSchedule = async (scheduleId) => {
    try {
      const res = await fetch(`/api/schedule/${scheduleId}`, { method: 'DELETE' });
      if (res.ok) {
        // Update local data
        setData(prev => {
          if (!prev) return prev;
          const updatedSchedules = (prev.scheduled_timetable || prev.schedules || []).filter(s => s.id !== scheduleId);
          return {
            ...prev,
            scheduled_timetable: updatedSchedules,
            schedules: updatedSchedules
          };
        });
      }
    } catch (err) {
      console.error('Failed to cancel schedule:', err);
    }
  };

  const metrics = data?.metrics || data?.summary || {};
  const topicReports = data?.topics_breakdown || data?.topic_reports || [];
  const testHistory = data?.test_history || [];
  const schedules = data?.scheduled_timetable || data?.schedules || [];
  const feedback = data?.feedback || data?.diagnostic_feedback || '';
  const createdAt = data?.created_at ? new Date(data.created_at).toLocaleString() : '';

  // Actionable focus areas: from API or synthesized from topicReports & testHistory
  const rawImprovementAreas = data?.improvement_areas || [];
  let improvementAreas = [...rawImprovementAreas];

  // Fallback synthesis if report was saved before server added improvement_areas
  if (improvementAreas.length === 0 && topicReports.length > 0) {
    topicReports.forEach(tb => {
      // 1. Misconceptions
      (tb.active_misconceptions || []).forEach(m => {
        const desc = typeof m === 'string' ? m : (m.details || m.misconception || 'Flagged misconception during practice.');
        improvementAreas.push({
          priority: 'HIGH',
          type: 'misconception',
          topic: tb.topic,
          title: `Resolve Misconception in '${tb.topic}'`,
          description: desc,
          action_mode: 'revise',
          action_label: `Revise ${tb.topic}`
        });
      });

      // 2. Low test scores (< 75%)
      const tScore = tb.test?.latest_score ?? (tb.test?.best_score ?? 0);
      const tCount = tb.test?.tests_count ?? 0;
      if (tCount > 0 && tScore < 0.75) {
        const scorePct = Math.round(tScore <= 1 ? tScore * 100 : tScore);
        improvementAreas.push({
          priority: scorePct < 60 ? 'HIGH' : 'MEDIUM',
          type: 'low_score',
          topic: tb.topic,
          title: `Strengthen Foundations in '${tb.topic}'`,
          description: `Latest assessment accuracy is ${scorePct}%. Practice targeted flashcard drills to lift score above 80%.`,
          action_mode: 'revise',
          action_label: `Revise ${tb.topic}`
        });
      } else if ((tb.learn?.sessions_count > 0 || tb.learn_chats_count > 0) && tCount === 0) {
        // 3. Untested
        improvementAreas.push({
          priority: 'MEDIUM',
          type: 'untested',
          topic: tb.topic,
          title: `Validate Mastery in '${tb.topic}'`,
          description: `Concept was explored in Learn sessions, but no diagnostic test has been attempted yet to prove retention.`,
          action_mode: 'test',
          action_label: `Take ${tb.topic} Test`
        });
      }
    });

    if (improvementAreas.length === 0 && topicReports.length > 0) {
      improvementAreas.push({
        priority: 'MAINTAIN',
        type: 'maintenance',
        topic: topicReports[0].topic,
        title: 'Maintain Strong Spaced Recall',
        description: 'All your studied topics are exhibiting strong retention (>80%). Keep performing periodic flashcard reviews to secure long-term memory.',
        action_mode: 'revise',
        action_label: 'Schedule Spaced Revision'
      });
    }
  }

  // SVG progression chart calculations
  const chartWidth = 600;
  const chartHeight = 160;
  const paddingX = 40;
  const paddingY = 24;

  let points = [];
  if (testHistory.length > 1) {
    const stepX = (chartWidth - paddingX * 2) / (testHistory.length - 1);
    points = testHistory.map((t, idx) => {
      const x = paddingX + idx * stepX;
      const score = Math.max(0, Math.min(100, t.score_pct ?? (t.score ? t.score * 100 : 0)));
      const y = chartHeight - paddingY - (score / 100) * (chartHeight - paddingY * 2);
      return { x, y, score, label: t.topic, date: (t.created_at || '').substring(5, 10) };
    });
  }

  const pathD = points.length > 1
    ? points.reduce((acc, p, idx) => `${acc} ${idx === 0 ? 'M' : 'L'} ${p.x} ${p.y}`, '')
    : '';

  const areaD = points.length > 1
    ? `${pathD} L ${points[points.length - 1].x} ${chartHeight - paddingY} L ${points[0].x} ${chartHeight - paddingY} Z`
    : '';

  if (loading && !data) {
    return (
      <div className="page-shell" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '60vh' }}>
        <div style={{ textAlign: 'center', color: '#94a3b8' }}>
          <RefreshCw size={32} style={{ animation: 'spin 1.5s linear infinite', color: '#2dd4bf', marginBottom: '12px' }} />
          <p style={{ fontSize: '1rem', fontWeight: 600 }}>Loading saved progress report...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="page-shell" style={{ maxWidth: '1200px', margin: '0 auto', padding: '24px 20px 60px' }}>
      <style>{`
        @keyframes spin { 100% { transform: rotate(360deg); } }
        @keyframes pulseGlow {
          0%, 100% { box-shadow: 0 0 15px rgba(45, 212, 191, 0.2); }
          50% { box-shadow: 0 0 25px rgba(45, 212, 191, 0.45); }
        }
      `}</style>

      {/* Header Banner */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', flexWrap: 'wrap', gap: '14px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '4px' }}>
            <div style={{
              width: '38px',
              height: '38px',
              borderRadius: '10px',
              background: 'linear-gradient(135deg, #0d9488, #3b82f6)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#fff'
            }}>
              <TrendingUp size={22} />
            </div>
            <h1 style={{ margin: 0, fontSize: '1.75rem', fontWeight: 800, color: '#f8fafc' }}>
              Progress & Mastery Intelligence
            </h1>
          </div>
          <p style={{ margin: 0, color: '#94a3b8', fontSize: '0.9rem' }}>
            Multi-topic analytics, test progression curves, diagnostic insights, and scheduled study agenda for <strong style={{ color: '#5eead4' }}>{studentProfile?.name || 'your account'}</strong>
          </p>
        </div>

        {/* Generate Latest Report Button */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {hasReport && createdAt && (
            <span style={{ fontSize: '0.78rem', color: '#64748b' }}>
              Report: <strong style={{ color: '#94a3b8' }}>{createdAt}</strong>
            </span>
          )}
          <button
            onClick={handleGenerateLatestReport}
            disabled={generating}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              padding: '10px 20px',
              borderRadius: '10px',
              background: 'linear-gradient(135deg, #0d9488, #0284c7)',
              border: 'none',
              color: '#ffffff',
              fontSize: '0.88rem',
              fontWeight: 700,
              cursor: generating ? 'wait' : 'pointer',
              boxShadow: '0 4px 15px rgba(13, 148, 136, 0.35)',
              transition: 'all 0.2s ease'
            }}
          >
            {generating ? (
              <>
                <RefreshCw size={16} style={{ animation: 'spin 1.5s linear infinite' }} />
                <span>Synthesizing Report...</span>
              </>
            ) : (
              <>
                <Zap size={16} color="#fbbf24" fill="#fbbf24" />
                <span>Generate Latest Report</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Notification Toast */}
      {notification && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          padding: '10px 16px',
          marginBottom: '20px',
          borderRadius: '8px',
          background: 'rgba(16, 185, 129, 0.15)',
          border: '1px solid rgba(16, 185, 129, 0.35)',
          color: '#6ee7b7',
          fontSize: '0.88rem',
          fontWeight: 600
        }}>
          <Check size={16} />
          <span>{notification}</span>
        </div>
      )}

      {/* Error Alert */}
      {error && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          padding: '10px 16px',
          marginBottom: '20px',
          borderRadius: '8px',
          background: 'rgba(239, 68, 68, 0.15)',
          border: '1px solid rgba(239, 68, 68, 0.35)',
          color: '#fca5a5',
          fontSize: '0.88rem'
        }}>
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      {/* Generating Progress State */}
      {generating && (
        <div style={{
          background: 'rgba(15, 23, 42, 0.8)',
          border: '1px solid rgba(45, 212, 191, 0.35)',
          borderRadius: '16px',
          padding: '30px',
          marginBottom: '24px',
          textAlign: 'center',
          animation: 'pulseGlow 2s infinite ease-in-out'
        }}>
          <Sparkles size={28} color="#2dd4bf" style={{ marginBottom: '10px', animation: 'spin 3s linear infinite' }} />
          <h3 style={{ margin: '0 0 6px 0', fontSize: '1.1rem', color: '#f8fafc', fontWeight: 700 }}>
            Synthesizing Latest Learning & Test Patterns
          </h3>
          <p style={{ margin: 0, fontSize: '0.88rem', color: '#5eead4', fontWeight: 600 }}>
            {stages[generatingStage]}
          </p>
        </div>
      )}

      {/* Empty State: Prompt to generate report */}
      {!hasReport && !generating ? (
        <div style={{
          background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.85) 0%, rgba(13, 27, 44, 0.95) 100%)',
          border: '1px solid rgba(45, 212, 191, 0.25)',
          borderRadius: '16px',
          padding: '60px 24px',
          textAlign: 'center',
          boxShadow: '0 20px 50px rgba(0,0,0,0.5)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '16px'
        }}>
          <div style={{
            width: '64px',
            height: '64px',
            borderRadius: '20px',
            background: 'linear-gradient(135deg, #0d9488, #0284c7)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 10px 25px rgba(13, 148, 136, 0.35)'
          }}>
            <Sparkles size={32} color="#ffffff" />
          </div>

          <div style={{ maxWidth: '520px' }}>
            <h2 style={{ fontSize: '1.4rem', fontWeight: 700, color: '#f8fafc', margin: '0 0 8px 0' }}>
              Generate Your Cognitive Progress Report
            </h2>
            <p style={{ fontSize: '0.9rem', color: '#94a3b8', lineHeight: 1.6, margin: 0 }}>
              EduNexus analyzes all your Learn chat conversations, flashcard drill sessions, test scores, and hesitation patterns on demand to synthesize a high-value diagnostic report.
            </p>
          </div>

          <button
            onClick={handleGenerateLatestReport}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '10px',
              padding: '12px 28px',
              borderRadius: '12px',
              background: 'linear-gradient(135deg, #0d9488, #0284c7)',
              border: 'none',
              color: '#ffffff',
              fontSize: '1rem',
              fontWeight: 700,
              cursor: 'pointer',
              boxShadow: '0 6px 20px rgba(13, 148, 136, 0.4)',
              marginTop: '8px'
            }}
          >
            <Zap size={18} color="#fbbf24" fill="#fbbf24" />
            Generate Latest Report Now
          </button>
        </div>
      ) : (
        /* Report View: Render Previous / Newly Generated Report */
        <div>
          {/* Top Metric Cards */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
            gap: '14px',
            marginBottom: '26px'
          }}>
            {/* Concepts Studied */}
            <div style={{
              background: 'rgba(15, 23, 42, 0.7)',
              border: '1px solid rgba(45, 212, 191, 0.25)',
              borderRadius: '14px',
              padding: '16px',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.78rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Concepts Studied</span>
                <BookOpen size={16} color="#2dd4bf" />
              </div>
              <div style={{ fontSize: '1.8rem', fontWeight: 800, color: '#f8fafc' }}>
                {metrics.total_topics || topicReports.length}
              </div>
              <span style={{ fontSize: '0.75rem', color: '#5eead4' }}>Active syllabus modules</span>
            </div>

            {/* Subconcepts Mastered */}
            <div style={{
              background: 'rgba(15, 23, 42, 0.7)',
              border: '1px solid rgba(16, 185, 129, 0.25)',
              borderRadius: '14px',
              padding: '16px',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.78rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Mastered Topics</span>
                <CheckCircle2 size={16} color="#10b981" />
              </div>
              <div style={{ fontSize: '1.8rem', fontWeight: 800, color: '#34d399' }}>
                {metrics.mastered_topics || 0}
              </div>
              <span style={{ fontSize: '0.75rem', color: '#6ee7b7' }}>High recall certainty</span>
            </div>

            {/* Revisions Completed */}
            <div style={{
              background: 'rgba(15, 23, 42, 0.7)',
              border: '1px solid rgba(56, 189, 248, 0.25)',
              borderRadius: '14px',
              padding: '16px',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.78rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Revisions Completed</span>
                <RefreshCw size={16} color="#38bdf8" />
              </div>
              <div style={{ fontSize: '1.8rem', fontWeight: 800, color: '#38bdf8' }}>
                {metrics.total_revisions || 0}
              </div>
              <span style={{ fontSize: '0.75rem', color: '#7dd3fc' }}>Flashcards & drills</span>
            </div>

            {/* Tests Taken */}
            <div style={{
              background: 'rgba(15, 23, 42, 0.7)',
              border: '1px solid rgba(168, 85, 247, 0.25)',
              borderRadius: '14px',
              padding: '16px',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.78rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Tests Taken</span>
                <GraduationCap size={16} color="#c084fc" />
              </div>
              <div style={{ fontSize: '1.8rem', fontWeight: 800, color: '#c084fc' }}>
                {metrics.total_tests || 0}
              </div>
              <span style={{ fontSize: '0.75rem', color: '#d8b4fe' }}>Diagnostic tests recorded</span>
            </div>

            {/* Average Test Score */}
            <div style={{
              background: 'rgba(15, 23, 42, 0.7)',
              border: '1px solid rgba(251, 191, 36, 0.25)',
              borderRadius: '14px',
              padding: '16px',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.78rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Average Test Score</span>
                <Award size={16} color="#fbbf24" />
              </div>
              <div style={{ fontSize: '1.8rem', fontWeight: 800, color: '#fbbf24' }}>
                {metrics.average_test_accuracy !== undefined ? `${metrics.average_test_accuracy}%` : 'N/A'}
              </div>
              <span style={{ fontSize: '0.75rem', color: '#fde68a' }}>Overall test accuracy</span>
            </div>
          </div>

          {/* Grid: Charts & AI Diagnostic Feedback */}
          <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: '20px', marginBottom: '26px' }}>
            {/* Visual Charts Container */}
            <div style={{
              background: 'rgba(15, 23, 42, 0.65)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              borderRadius: '16px',
              padding: '20px',
              display: 'flex',
              flexDirection: 'column',
              gap: '16px'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, color: '#f1f5f9', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <BarChart3 size={18} color="#2dd4bf" /> Test Score Progression Over Time
                </h3>
                <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>{testHistory.length} assessments</span>
              </div>

              {testHistory.length === 0 ? (
                <div style={{
                  height: '160px',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  background: 'rgba(15, 23, 42, 0.4)',
                  borderRadius: '10px',
                  color: '#64748b',
                  fontSize: '0.85rem'
                }}>
                  <span>No tests recorded in this report.</span>
                  <button
                    onClick={() => setMode('test')}
                    style={{
                      marginTop: '8px',
                      background: 'rgba(45, 212, 191, 0.15)',
                      border: '1px solid rgba(45, 212, 191, 0.3)',
                      color: '#5eead4',
                      padding: '4px 12px',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      fontSize: '0.78rem'
                    }}
                  >
                    Take a test in Test mode
                  </button>
                </div>
              ) : testHistory.length === 1 ? (
                <div style={{
                  height: '160px',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  background: 'rgba(15, 23, 42, 0.4)',
                  borderRadius: '10px',
                  color: '#94a3b8',
                  fontSize: '0.88rem'
                }}>
                  <span style={{ color: '#fbbf24', fontSize: '1.4rem', fontWeight: 700 }}>
                    {testHistory[0].score_pct}%
                  </span>
                  <span>First score recorded in <strong>{testHistory[0].topic}</strong></span>
                  <small style={{ color: '#64748b', marginTop: '4px' }}>Complete more tests to view dynamic score progression</small>
                </div>
              ) : (
                <div style={{ width: '100%', overflowX: 'auto' }}>
                  <svg viewBox={`0 0 ${chartWidth} ${chartHeight}`} style={{ width: '100%', height: 'auto', display: 'block' }}>
                    <defs>
                      <linearGradient id="scoreAreaGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#2dd4bf" stopOpacity="0.35" />
                        <stop offset="100%" stopColor="#2dd4bf" stopOpacity="0.0" />
                      </linearGradient>
                    </defs>

                    {/* Horizontal reference lines */}
                    {[0, 25, 50, 75, 100].map((val) => {
                      const y = chartHeight - paddingY - (val / 100) * (chartHeight - paddingY * 2);
                      return (
                        <g key={val}>
                          <line x1={paddingX} y1={y} x2={chartWidth - paddingX} y2={y} stroke="rgba(255,255,255,0.06)" strokeDasharray="3 3" />
                          <text x={paddingX - 8} y={y + 3} fill="#64748b" fontSize="9" textAnchor="end">{val}%</text>
                        </g>
                      );
                    })}

                    {/* Shaded Area */}
                    <path d={areaD} fill="url(#scoreAreaGradient)" />

                    {/* Score Curve Line */}
                    <path d={pathD} fill="none" stroke="#2dd4bf" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />

                    {/* Data Points */}
                    {points.map((p, idx) => (
                      <g key={idx}>
                        <circle cx={p.x} cy={p.y} r="4.5" fill="#0f172a" stroke="#2dd4bf" strokeWidth="2" />
                        <text x={p.x} y={p.y - 8} fill="#f1f5f9" fontSize="10" fontWeight="700" textAnchor="middle">
                          {p.score}%
                        </text>
                        <text x={p.x} y={chartHeight - 6} fill="#94a3b8" fontSize="8" textAnchor="middle">
                          {p.label.length > 10 ? p.label.slice(0, 8) + '…' : p.label}
                        </text>
                      </g>
                    ))}
                  </svg>
                </div>
              )}

              {/* Mini Mastery Distribution Bars */}
              <div style={{ marginTop: '8px', borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: '12px' }}>
                <span style={{ fontSize: '0.78rem', color: '#94a3b8', fontWeight: 650, display: 'block', marginBottom: '8px' }}>
                  Topic Mastery Index
                </span>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {topicReports.slice(0, 4).map((t, idx) => (
                    <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <span style={{ width: '130px', fontSize: '0.78rem', color: '#cbd5e1', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {t.topic}
                      </span>
                      <div style={{ flex: 1, height: '8px', background: 'rgba(255,255,255,0.06)', borderRadius: '4px', overflow: 'hidden' }}>
                        <div
                          style={{
                            width: `${t.mastery_score || 50}%`,
                            height: '100%',
                            background: (t.mastery_score || 50) >= 80 ? '#10b981' : (t.mastery_score || 50) >= 50 ? '#38bdf8' : '#f59e0b',
                            borderRadius: '4px',
                            transition: 'width 0.4s ease'
                          }}
                        />
                      </div>
                      <span style={{ width: '40px', fontSize: '0.78rem', color: '#94a3b8', textAlign: 'right', fontWeight: 600 }}>
                        {t.mastery_score || 50}%
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* AI Diagnostic Feedback Card */}
            <div style={{
              background: 'linear-gradient(145deg, rgba(13, 27, 42, 0.8) 0%, rgba(15, 34, 58, 0.9) 100%)',
              border: '1px solid rgba(45, 212, 191, 0.25)',
              borderRadius: '16px',
              padding: '20px',
              display: 'flex',
              flexDirection: 'column',
              boxShadow: '0 10px 25px rgba(0,0,0,0.3)'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
                <div style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '8px',
                  background: 'linear-gradient(135deg, #14b8a6, #0284c7)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}>
                  <Sparkles size={16} color="#ffffff" />
                </div>
                <div>
                  <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, color: '#f8fafc' }}>
                    AI Learning Diagnostics
                  </h3>
                  <span style={{ fontSize: '0.74rem', color: '#5eead4' }}>Continuous cognitive pattern analysis</span>
                </div>
              </div>

              <div style={{
                flex: 1,
                background: 'rgba(15, 23, 42, 0.5)',
                border: '1px solid rgba(255, 255, 255, 0.06)',
                borderRadius: '12px',
                padding: '16px',
                color: '#cbd5e1',
                fontSize: '0.88rem',
                lineHeight: 1.6,
                overflowY: 'auto',
                maxHeight: '260px'
              }}>
                <FormattedText text={feedback || 'No diagnostic feedback available yet.'} />
              </div>

              <div style={{ display: 'flex', gap: '10px', marginTop: '14px' }}>
                <button
                  onClick={() => setMode('revise')}
                  style={{
                    flex: 1,
                    padding: '8px 12px',
                    borderRadius: '8px',
                    background: 'rgba(45, 212, 191, 0.15)',
                    border: '1px solid rgba(45, 212, 191, 0.3)',
                    color: '#5eead4',
                    fontSize: '0.8rem',
                    fontWeight: 600,
                    cursor: 'pointer'
                  }}
                >
                  🔄 Revise Weak Concepts
                </button>
                <button
                  onClick={() => setMode('test')}
                  style={{
                    flex: 1,
                    padding: '8px 12px',
                    borderRadius: '8px',
                    background: 'rgba(168, 85, 247, 0.15)',
                    border: '1px solid rgba(168, 85, 247, 0.3)',
                    color: '#d8b4fe',
                    fontSize: '0.8rem',
                    fontWeight: 650,
                    cursor: 'pointer'
                  }}
                >
                  ✍️ Take Readiness Test
                </button>
              </div>
            </div>
          </div>

          {/* Priority Focus: What You Need to Work On */}
          <div style={{
            background: 'linear-gradient(145deg, rgba(17, 24, 39, 0.88) 0%, rgba(15, 23, 42, 0.95) 100%)',
            border: '1px solid rgba(245, 158, 11, 0.28)',
            boxShadow: '0 12px 32px rgba(0, 0, 0, 0.35)',
            borderRadius: '16px',
            padding: '22px 24px',
            marginBottom: '26px'
          }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <div style={{
                  width: '38px',
                  height: '38px',
                  borderRadius: '10px',
                  background: 'linear-gradient(135deg, #f59e0b, #ef4444)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  boxShadow: '0 4px 14px rgba(245, 158, 11, 0.35)'
                }}>
                  <Target size={20} color="#ffffff" />
                </div>
                <div>
                  <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700, color: '#f8fafc' }}>
                    Priority Focus: What You Need to Work On
                  </h3>
                  <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                    Actionable roadmap targeting your identified misconceptions, weak test concepts, and untested learning modules
                  </span>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{
                  fontSize: '0.78rem',
                  fontWeight: 700,
                  padding: '4px 12px',
                  borderRadius: '16px',
                  background: improvementAreas.some(i => i.priority === 'HIGH') ? 'rgba(239, 68, 68, 0.18)' : 'rgba(45, 212, 191, 0.15)',
                  border: improvementAreas.some(i => i.priority === 'HIGH') ? '1px solid rgba(239, 68, 68, 0.35)' : '1px solid rgba(45, 212, 191, 0.3)',
                  color: improvementAreas.some(i => i.priority === 'HIGH') ? '#fca5a5' : '#5eead4'
                }}>
                  {improvementAreas.length} {improvementAreas.length === 1 ? 'Action Item' : 'Action Items'}
                </span>
              </div>
            </div>

            {/* Improvement Items Grid */}
            {improvementAreas.length === 0 ? (
              <div style={{
                textAlign: 'center',
                padding: '30px 20px',
                background: 'rgba(15, 23, 42, 0.4)',
                borderRadius: '12px',
                border: '1px dashed rgba(255, 255, 255, 0.1)',
                color: '#94a3b8',
                fontSize: '0.9rem'
              }}>
                <CheckCircle2 size={24} color="#10b981" style={{ marginBottom: '8px' }} />
                <p style={{ margin: 0, fontWeight: 600, color: '#f1f5f9' }}>No urgent weaknesses identified!</p>
                <p style={{ margin: '4px 0 0', fontSize: '0.82rem', color: '#64748b' }}>
                  All your active topics are above target mastery levels. Continue spaced revisions or explore new syllabus concepts.
                </p>
              </div>
            ) : (
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(310px, 1fr))',
                gap: '14px'
              }}>
                {improvementAreas.map((item, idx) => {
                  const isHigh = item.priority === 'HIGH';
                  const isMedium = item.priority === 'MEDIUM';
                  const isMaintain = item.priority === 'MAINTAIN';
                  const isRevise = item.action_mode === 'revise';
                  const isTest = item.action_mode === 'test';

                  const badgeStyle = isHigh
                    ? { bg: 'rgba(239, 68, 68, 0.15)', border: '1px solid rgba(239, 68, 68, 0.35)', text: '#f87171', label: '⚡ HIGH PRIORITY' }
                    : isMedium
                    ? { bg: 'rgba(245, 158, 11, 0.15)', border: '1px solid rgba(245, 158, 11, 0.35)', text: '#fbbf24', label: '📌 RECOMMENDED FOCUS' }
                    : isMaintain
                    ? { bg: 'rgba(16, 185, 129, 0.15)', border: '1px solid rgba(16, 185, 129, 0.35)', text: '#34d399', label: '✨ ON TRACK' }
                    : { bg: 'rgba(56, 189, 248, 0.15)', border: '1px solid rgba(56, 189, 248, 0.35)', text: '#38bdf8', label: '🚀 NEXT STEP' };

                  return (
                    <div
                      key={idx}
                      style={{
                        background: 'rgba(15, 23, 42, 0.65)',
                        border: isHigh ? '1px solid rgba(239, 68, 68, 0.28)' : '1px solid rgba(255, 255, 255, 0.08)',
                        borderRadius: '12px',
                        padding: '16px 18px',
                        display: 'flex',
                        flexDirection: 'column',
                        justifyContent: 'space-between',
                        transition: 'transform 0.2s ease, border-color 0.2s ease',
                      }}
                    >
                      <div>
                        {/* Top row with badge & topic */}
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px', flexWrap: 'wrap' }}>
                          <span style={{
                            fontSize: '0.72rem',
                            fontWeight: 700,
                            padding: '2px 8px',
                            borderRadius: '6px',
                            background: badgeStyle.bg,
                            border: badgeStyle.border,
                            color: badgeStyle.text
                          }}>
                            {badgeStyle.label}
                          </span>
                          <span style={{
                            fontSize: '0.73rem',
                            color: '#94a3b8',
                            background: 'rgba(255, 255, 255, 0.05)',
                            padding: '2px 8px',
                            borderRadius: '4px'
                          }}>
                            {item.topic}
                          </span>
                        </div>

                        {/* Title */}
                        <h4 style={{
                          margin: '10px 0 6px 0',
                          fontSize: '0.94rem',
                          fontWeight: 700,
                          color: '#f8fafc',
                          lineHeight: 1.4
                        }}>
                          {item.title}
                        </h4>

                        {/* Description */}
                        <p style={{
                          margin: '0 0 14px 0',
                          fontSize: '0.83rem',
                          color: '#cbd5e1',
                          lineHeight: 1.55
                        }}>
                          {item.description}
                        </p>
                      </div>

                      {/* Action CTA Button */}
                      <button
                        onClick={() => setMode(item.action_mode || 'revise')}
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          gap: '8px',
                          width: '100%',
                          padding: '9px 14px',
                          borderRadius: '8px',
                          border: isRevise
                            ? '1px solid rgba(45, 212, 191, 0.4)'
                            : isTest
                            ? '1px solid rgba(168, 85, 247, 0.4)'
                            : '1px solid rgba(56, 189, 248, 0.4)',
                          background: isRevise
                            ? 'linear-gradient(135deg, rgba(13, 148, 136, 0.25), rgba(2, 132, 199, 0.25))'
                            : isTest
                            ? 'linear-gradient(135deg, rgba(147, 51, 234, 0.25), rgba(79, 70, 229, 0.25))'
                            : 'linear-gradient(135deg, rgba(56, 189, 248, 0.25), rgba(59, 130, 246, 0.25))',
                          color: isRevise ? '#5eead4' : isTest ? '#d8b4fe' : '#7dd3fc',
                          fontSize: '0.82rem',
                          fontWeight: 700,
                          cursor: 'pointer',
                          transition: 'all 0.2s ease'
                        }}
                      >
                        <span>{item.action_label || (isRevise ? 'Revise Concept' : isTest ? 'Take Readiness Test' : 'Open Topic')}</span>
                        <ArrowRight size={15} />
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Topic-by-Topic Learning & Retention Breakdown */}
          <div style={{
            background: 'rgba(15, 23, 42, 0.65)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            borderRadius: '16px',
            padding: '20px',
            marginBottom: '26px'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div>
                <h3 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 700, color: '#f8fafc' }}>
                  Topic-by-Topic Learning & Retention Breakdown
                </h3>
                <span style={{ fontSize: '0.78rem', color: '#94a3b8' }}>
                  Tracks whether you've engaged in Learn sessions, generated flashcards/drills, or passed assessments
                </span>
              </div>
              <span style={{ fontSize: '0.78rem', color: '#2dd4bf', fontWeight: 650 }}>
                {topicReports.length} Topics Analyzed
              </span>
            </div>

            {topicReports.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '30px', color: '#64748b', fontSize: '0.9rem' }}>
                No topics explored yet. Start in the <strong>Learn</strong> section to initiate concept mastery!
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {topicReports.map((t, idx) => {
                  const statusColors = {
                    MASTERED: { bg: 'rgba(16, 185, 129, 0.15)', text: '#34d399', border: 'rgba(16, 185, 129, 0.3)', label: 'Mastered' },
                    REVISION_NEEDED: { bg: 'rgba(245, 158, 11, 0.15)', text: '#fbbf24', border: 'rgba(245, 158, 11, 0.3)', label: 'Revision Recommended' },
                    IN_PROGRESS: { bg: 'rgba(56, 189, 248, 0.15)', text: '#38bdf8', border: 'rgba(56, 189, 248, 0.3)', label: 'In Progress' },
                    LEARNED: { bg: 'rgba(148, 163, 184, 0.15)', text: '#cbd5e1', border: 'rgba(148, 163, 184, 0.3)', label: 'Learned' }
                  };
                  const status = statusColors[t.status] || statusColors.LEARNED;

                  return (
                    <div
                      key={idx}
                      style={{
                        background: 'rgba(30, 41, 59, 0.45)',
                        border: '1px solid rgba(255, 255, 255, 0.06)',
                        borderRadius: '12px',
                        padding: '14px 18px',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '10px'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                          <span style={{ fontSize: '0.95rem', fontWeight: 700, color: '#f8fafc' }}>
                            {t.topic}
                          </span>
                          <span
                            style={{
                              fontSize: '0.72rem',
                              fontWeight: 700,
                              padding: '2px 8px',
                              borderRadius: '12px',
                              background: status.bg,
                              color: status.text,
                              border: `1px solid ${status.border}`
                            }}
                          >
                            {status.label}
                          </span>
                        </div>

                        <div style={{ display: 'flex', gap: '16px', fontSize: '0.8rem', color: '#94a3b8' }}>
                          <span>💬 Learn: <strong style={{ color: '#e2e8f0' }}>{t.learn_chats_count || 0} chats</strong></span>
                          <span>🔄 Revise: <strong style={{ color: '#e2e8f0' }}>{t.revision_sessions_count || 0} sessions</strong></span>
                          <span>✍️ Test: <strong style={{ color: '#e2e8f0' }}>{t.test_attempts_count || 0} attempts</strong></span>
                        </div>
                      </div>

                      {/* Mastered & Misconception Tags */}
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', alignItems: 'center' }}>
                        {t.mastered_subconcepts && t.mastered_subconcepts.length > 0 && (
                          <>
                            <span style={{ fontSize: '0.72rem', color: '#10b981', fontWeight: 650 }}>Mastered:</span>
                            {t.mastered_subconcepts.slice(0, 3).map((sub, i) => (
                              <span
                                key={i}
                                style={{
                                  fontSize: '0.7rem',
                                  padding: '2px 6px',
                                  borderRadius: '4px',
                                  background: 'rgba(16, 185, 129, 0.1)',
                                  color: '#34d399',
                                  border: '1px solid rgba(16, 185, 129, 0.2)'
                                }}
                              >
                                ✓ {sub}
                              </span>
                            ))}
                          </>
                        )}

                        {t.active_misconceptions && t.active_misconceptions.length > 0 && (
                          <>
                            <span style={{ fontSize: '0.72rem', color: '#f59e0b', fontWeight: 650, marginLeft: '6px' }}>Needs Work:</span>
                            {t.active_misconceptions.slice(0, 2).map((misc, i) => (
                              <span
                                key={i}
                                style={{
                                  fontSize: '0.7rem',
                                  padding: '2px 6px',
                                  borderRadius: '4px',
                                  background: 'rgba(245, 158, 11, 0.1)',
                                  color: '#fbbf24',
                                  border: '1px solid rgba(245, 158, 11, 0.2)'
                                }}
                              >
                                ⚠ {misc}
                              </span>
                            ))}
                          </>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Scheduled Study Timetable */}
          <div style={{
            background: 'rgba(15, 23, 42, 0.65)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            borderRadius: '16px',
            padding: '20px'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <div style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '8px',
                  background: 'linear-gradient(135deg, #6366f1, #a855f7)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}>
                  <Calendar size={18} color="#ffffff" />
                </div>
                <div>
                  <h3 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 700, color: '#f8fafc' }}>
                    Scheduled Study Timetable & Calendar Agenda
                  </h3>
                  <span style={{ fontSize: '0.78rem', color: '#94a3b8' }}>
                    All revision sessions & test alerts configured in Revise and Test sections
                  </span>
                </div>
              </div>
              <span style={{ fontSize: '0.8rem', color: '#c084fc', fontWeight: 600 }}>
                {schedules.length} Sessions Scheduled
              </span>
            </div>

            {schedules.length === 0 ? (
              <div style={{
                textAlign: 'center',
                padding: '28px',
                background: 'rgba(15, 23, 42, 0.4)',
                borderRadius: '12px',
                color: '#64748b',
                fontSize: '0.88rem'
              }}>
                <Calendar size={28} style={{ opacity: 0.4, marginBottom: '6px' }} />
                <p style={{ margin: '0 0 6px 0' }}>No scheduled revision or test sessions yet.</p>
                <small style={{ color: '#94a3b8' }}>
                  Head to <strong>Revise</strong> or <strong>Test</strong> and click <strong>"📅 Schedule"</strong> to book reminder alerts!
                </small>
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '14px' }}>
                {schedules.map((sch) => {
                  const isRev = sch.mode === 'revise';
                  const slots = Array.isArray(sch.time_slots) ? sch.time_slots : [sch.time_slots];

                  return (
                    <div
                      key={sch.id}
                      style={{
                        background: 'rgba(30, 41, 59, 0.5)',
                        border: `1px solid ${isRev ? 'rgba(45, 212, 191, 0.25)' : 'rgba(168, 85, 247, 0.25)'}`,
                        borderRadius: '12px',
                        padding: '14px',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '10px',
                        position: 'relative'
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                        <div>
                          <span
                            style={{
                              fontSize: '0.7rem',
                              fontWeight: 700,
                              padding: '2px 8px',
                              borderRadius: '10px',
                              background: isRev ? 'rgba(45, 212, 191, 0.15)' : 'rgba(168, 85, 247, 0.15)',
                              color: isRev ? '#5eead4' : '#d8b4fe',
                              textTransform: 'uppercase'
                            }}
                          >
                            {isRev ? 'Revision' : 'Test Assessment'}
                          </span>
                          <h4 style={{ margin: '6px 0 0 0', fontSize: '0.94rem', fontWeight: 700, color: '#f8fafc' }}>
                            {sch.topic}
                          </h4>
                        </div>

                        <button
                          onClick={() => handleDeleteSchedule(sch.id)}
                          title="Cancel schedule"
                          style={{
                            background: 'none',
                            border: 'none',
                            color: '#ef4444',
                            cursor: 'pointer',
                            padding: '4px',
                            borderRadius: '4px'
                          }}
                        >
                          <Trash2 size={15} />
                        </button>
                      </div>

                      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '0.8rem', color: '#94a3b8' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <Calendar size={14} color="#94a3b8" />
                          <span>Date: <strong style={{ color: '#f1f5f9' }}>{sch.date}</strong></span>
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                          <Clock size={14} color="#94a3b8" />
                          <span>Alert Times:</span>
                          {slots.map((t, idx) => (
                            <span
                              key={idx}
                              style={{
                                fontSize: '0.72rem',
                                padding: '1px 6px',
                                borderRadius: '4px',
                                background: 'rgba(255,255,255,0.06)',
                                color: '#e2e8f0'
                              }}
                            >
                              {t}
                            </span>
                          ))}
                        </div>

                        {sch.email && (
                          <div style={{ fontSize: '0.74rem', color: '#64748b', marginTop: '2px' }}>
                            ✉️ Reminder: {sch.email}
                          </div>
                        )}
                      </div>

                      {sch.note && (
                        <div style={{
                          fontSize: '0.76rem',
                          fontStyle: 'italic',
                          color: '#cbd5e1',
                          background: 'rgba(0,0,0,0.2)',
                          padding: '6px 8px',
                          borderRadius: '6px'
                        }}>
                          "{sch.note}"
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
