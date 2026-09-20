import React, { useState, useEffect, useRef } from 'react';
import {
  BookOpen,
  FileText,
  Upload,
  CheckCircle2,
  AlertCircle,
  Sparkles,
  Clock,
  ArrowLeft,
  ArrowRight,
  RotateCcw,
  Layers,
  HelpCircle,
  Trash2,
  History,
  ChevronRight,
  Plus,
  Play,
  Check,
  Calendar
} from 'lucide-react';
import FlashcardDeck from '../components/FlashcardDeck';
import FormattedText from '../components/FormattedText';
import ScheduleModal from '../components/ScheduleModal';

function formatSeconds(sec) {
  if (!sec || isNaN(sec)) return '0s';
  const m = Math.floor(sec / 60);
  const s = Math.round(sec % 60);
  if (m === 0) return `${s}s`;
  return `${m}m ${s}s`;
}

function TestThinkingIndicator({ topic, questionCount }) {
  const [stage, setStage] = useState(0);
  const stages = [
    `Configuring ${questionCount}-question diagnostic assessment for '${topic}'...`,
    'Cross-referencing chat history & revision sessions...',
    'Analyzing prior misconceptions & answer patterns...',
    'Synthesizing deterministic questions with pitfall explanations...',
    'Initializing per-question timing & session store...',
  ];

  useEffect(() => {
    const timers = [
      setTimeout(() => setStage(1), 1600),
      setTimeout(() => setStage(2), 3400),
      setTimeout(() => setStage(3), 5400),
      setTimeout(() => setStage(4), 7800),
    ];
    return () => timers.forEach(clearTimeout);
  }, []);

  return (
    <div className="mode-thinking-state">
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
      <p style={{ fontSize: '0.82rem', color: '#94a3b8', maxWidth: '440px', margin: '0 auto' }}>
        EduNexus is compiling a custom test targeting your exact learning signals and conceptual boundary rules.
      </p>
    </div>
  );
}

export default function Test({ studentId, studentProfile, onRefreshProfile }) {
  // Main subsection tabs
  const [activeTab, setActiveTab] = useState('studied_concept'); // 'studied_concept' | 'uploaded_file'
  const [showScheduleModal, setShowScheduleModal] = useState(false);

  // Studied concepts state
  const [topics, setTopics] = useState([]);
  const [loadingTopics, setLoadingTopics] = useState(true);
  const [selectedTopic, setSelectedTopic] = useState(null);

  // Uploaded files state
  const [uploadedFile, setUploadedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [availableDocs, setAvailableDocs] = useState([]);

  // Question count selector (min 5, max 25)
  const [questionCount, setQuestionCount] = useState(5);

  // Quiz running state
  const [loadingQuiz, setLoadingQuiz] = useState(false);
  const [quizData, setQuizData] = useState(null);
  const [currentQIndex, setCurrentQIndex] = useState(0);
  const [answers, setAnswers] = useState({});

  // Timing tracking per question
  const [questionTimings, setQuestionTimings] = useState({}); // { [qId]: seconds }
  const activeQTimerRef = useRef(null);
  const activeQStartRef = useRef(null);
  const [currentElapsed, setCurrentElapsed] = useState(0);

  // Submission & Results state
  const [submitting, setSubmitting] = useState(false);
  const [submitResult, setSubmitResult] = useState(null);

  // Adaptive Loop states:
  // Step 1: 'ask_revise' (Yes / No)
  // Step 2: 'choose_format' ('text' vs 'flashcards')
  // Step 3: 'view_remediation' (displays formatted text or deck)
  // Step 4: 'ask_next_quiz' (Yes / No)
  const [loopStep, setLoopStep] = useState(null);
  const [reviewMode, setReviewMode] = useState(null); // 'text' | 'flashcards'
  const [reviewLoading, setReviewLoading] = useState(false);
  const [reviewData, setReviewData] = useState(null);
  const [loopRound, setLoopRound] = useState(1);

  // Saved test sessions list for current topic/document and all student sessions
  const [savedSessions, setSavedSessions] = useState([]);
  const [allSavedSessions, setAllSavedSessions] = useState([]);
  const [viewingSavedSession, setViewingSavedSession] = useState(null);

  // Fetch topics and all saved sessions on load
  useEffect(() => {
    fetchTopics();
    fetchAllSavedSessions();
  }, [studentId]);

  const fetchTopics = async () => {
    setLoadingTopics(true);
    try {
      const res = await fetch(`/api/revise/topics/${studentId}`);
      const data = await res.json();
      const topicList = Array.isArray(data) ? data : [];
      setTopics(topicList);

      // Collect available document names from sessions
      const docs = [];
      topicList.forEach((t) => {
        if (t.document_name && !docs.includes(t.document_name)) {
          docs.push(t.document_name);
        }
      });
      setAvailableDocs(docs);
    } catch (err) {
      console.error('Error fetching studied topics for test:', err);
    } finally {
      setLoadingTopics(false);
    }
  };

  const fetchAllSavedSessions = async () => {
    try {
      const res = await fetch(`/api/test/sessions/${studentId}`);
      const data = await res.json();
      setAllSavedSessions(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Error fetching all saved test sessions:', err);
    }
  };

  const fetchSavedSessions = async (topicName, subsection) => {
    try {
      const params = new URLSearchParams({ topic: topicName, subsection });
      const res = await fetch(`/api/test/sessions/${studentId}?${params.toString()}`);
      const data = await res.json();
      setSavedSessions(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Error fetching saved test sessions:', err);
    }
  };

  // Open and load a saved test session (either completed or in-progress)
  const handleOpenSavedSession = async (sessionSummary) => {
    try {
      setLoadingQuiz(true);
      const res = await fetch(`/api/test/session/${sessionSummary.id}`);
      if (!res.ok) throw new Error('Could not load test session');
      const session = await res.json();

      setViewingSavedSession(session);
      setSelectedTopic(session.topic);
      if (session.subsection) {
        setActiveTab(session.subsection);
      }
      if (session.document_name) {
        setUploadedFile(session.document_name);
      }

      const qList = session.questions || [];
      const userAnswers = session.answers || {};
      const timings = session.timing || {};

      setQuizData({
        session_id: session.id,
        attempt_id: session.id,
        topic: session.topic,
        document_name: session.document_name,
        subsection: session.subsection,
        questions: qList,
      });
      setAnswers(userAnswers);
      setQuestionTimings(timings);
      setLoopRound(session.loop_round || 1);

      if (session.status === 'COMPLETED' || session.score !== null) {
        // Reconstruct question breakdown results
        const reconstructedResults = qList.map((q) => {
          const uAns = userAnswers[q.id] || '';
          const isCorr = uAns === q.correct_answer;
          const timeSpent = timings[q.id] || 0;
          return {
            question_id: q.id,
            sub_concept: q.sub_concept,
            question: q.question,
            user_answer: uAns,
            correct_answer: q.correct_answer,
            is_correct: isCorr,
            explanation: q.explanation,
            time_spent_seconds: timeSpent,
            is_hesitant: timeSpent > 30,
          };
        });

        const totalQ = qList.length;
        const correctCount = reconstructedResults.filter((r) => r.is_correct).length;
        const accuracy = session.score !== null ? session.score : (totalQ > 0 ? correctCount / totalQ : 0);
        const avgTime = session.total_time_seconds && totalQ > 0
          ? session.total_time_seconds / totalQ
          : (timings && totalQ > 0 ? Object.values(timings).reduce((a, b) => a + b, 0) / totalQ : 0);

        setSubmitResult({
          attempt_id: session.id,
          session_id: session.id,
          topic: session.topic,
          score: accuracy,
          marks: session.marks !== null ? session.marks : correctCount,
          total: totalQ,
          passed: Boolean(session.passed),
          status: session.passed ? 'MASTERED' : 'WEAKNESS_DETECTED',
          results: reconstructedResults,
          timing: timings,
          total_time_seconds: session.total_time_seconds || 0,
          average_time_per_question: avgTime,
          flagged_hesitations: reconstructedResults.filter((r) => r.is_hesitant).map((r) => r.question_id),
          failed_results: reconstructedResults.filter((r) => !r.is_correct),
        });

        if (session.review_content) {
          setReviewMode(session.review_mode || 'text');
          setReviewData({
            review_mode: session.review_mode || 'text',
            content: session.review_content,
          });
          setLoopStep('view_remediation');
        } else {
          setReviewData(null);
          setReviewMode(null);
          setLoopStep(null);
        }
      } else {
        // In-progress: resume test questions
        setSubmitResult(null);
        setCurrentQIndex(0);
        setLoopStep(null);
        setReviewData(null);
        setReviewMode(null);
      }
    } catch (err) {
      alert(`Error loading test session: ${err.message}`);
    } finally {
      setLoadingQuiz(false);
    }
  };

  // Timer logic for active question
  const recordCurrentQTime = () => {
    if (activeQStartRef.current !== null && quizData?.questions?.[currentQIndex]) {
      const qId = quizData.questions[currentQIndex].id;
      const elapsed = (Date.now() - activeQStartRef.current) / 1000;
      setQuestionTimings((prev) => ({
        ...prev,
        [qId]: (prev[qId] || 0) + elapsed,
      }));
    }
    activeQStartRef.current = Date.now();
    setCurrentElapsed(0);
  };

  useEffect(() => {
    if (quizData && !submitResult) {
      activeQStartRef.current = Date.now();
      setCurrentElapsed(0);
      if (activeQTimerRef.current) clearInterval(activeQTimerRef.current);

      activeQTimerRef.current = setInterval(() => {
        if (activeQStartRef.current) {
          const sec = Math.floor((Date.now() - activeQStartRef.current) / 1000);
          setCurrentElapsed(sec);
        }
      }, 500);

      return () => {
        if (activeQTimerRef.current) clearInterval(activeQTimerRef.current);
      };
    }
  }, [currentQIndex, quizData, submitResult]);

  const handleSelectQuestion = (nextIndex) => {
    recordCurrentQTime();
    setCurrentQIndex(nextIndex);
  };

  // Start test
  const handleStartTest = async (topicName = selectedTopic, docName = uploadedFile, round = 1) => {
    const targetTopic = topicName || docName || 'General Knowledge';
    setLoadingQuiz(true);
    setSubmitResult(null);
    setAnswers({});
    setQuestionTimings({});
    setCurrentQIndex(0);
    setLoopStep(null);
    setReviewData(null);
    setReviewMode(null);
    setViewingSavedSession(null);

    const clampedCount = Math.max(5, Math.min(25, Number(questionCount) || 5));

    try {
      const res = await fetch('/api/test/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          student_id: studentId,
          topic: targetTopic,
          subsection: activeTab,
          document_name: activeTab === 'uploaded_file' ? docName : null,
          question_count: clampedCount,
          loop_round: round,
        }),
      });

      if (!res.ok) throw new Error('Test generation failed');
      const data = await res.json();
      setQuizData(data);
      setLoopRound(round);
      fetchSavedSessions(targetTopic, activeTab);
    } catch (err) {
      alert(`Error starting test: ${err.message}`);
    } finally {
      setLoadingQuiz(false);
    }
  };

  // Upload file for Subsection B
  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch('/api/documents/upload', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (res.ok) {
        setUploadedFile(data.document_name);
        if (!availableDocs.includes(data.document_name)) {
          setAvailableDocs((prev) => [data.document_name, ...prev]);
        }
      } else {
        alert(`Upload error: ${data.detail || 'Upload failed'}`);
      }
    } catch (err) {
      alert(`Upload error: ${err.message}`);
    } finally {
      setUploading(false);
    }
  };

  // Submit test
  const handleSubmitQuiz = async () => {
    recordCurrentQTime();
    if (activeQTimerRef.current) clearInterval(activeQTimerRef.current);
    setSubmitting(true);

    // Calculate final timing map including latest question
    const qId = quizData.questions[currentQIndex]?.id;
    const finalElapsed = activeQStartRef.current ? (Date.now() - activeQStartRef.current) / 1000 : 0;
    const finalTimings = {
      ...questionTimings,
      [qId]: (questionTimings[qId] || 0) + finalElapsed,
    };

    try {
      const res = await fetch('/api/test/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          student_id: studentId,
          topic: quizData.topic,
          attempt_id: quizData.attempt_id,
          session_id: quizData.session_id,
          answers: answers,
          questions: quizData.questions,
          timing: finalTimings,
        }),
      });

      if (!res.ok) throw new Error('Failed to submit test');
      const data = await res.json();
      setSubmitResult(data);
      setQuestionTimings(finalTimings);
      setLoopStep('ask_revise'); // Prompt user: Do you want to revise and make concept strong?
      onRefreshProfile?.();
      fetchAllSavedSessions();
      fetchSavedSessions(quizData.topic, activeTab);
    } catch (err) {
      alert(`Submission error: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  // Adaptive Loop Handler: Generate remediation review (Text or Flashcards)
  const handleGenerateReview = async (mode) => {
    setReviewMode(mode);
    setReviewLoading(true);

    try {
      const res = await fetch('/api/test/review', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          student_id: studentId,
          topic: quizData.topic,
          session_id: quizData.session_id,
          review_mode: mode,
          failed_results: submitResult?.failed_results || [],
          timings: questionTimings,
        }),
      });

      if (!res.ok) throw new Error('Remediation review generation failed');
      const data = await res.json();
      setReviewData(data);
      setLoopStep('view_remediation');
      fetchAllSavedSessions();
    } catch (err) {
      alert(`Error generating review: ${err.message}`);
    } finally {
      setReviewLoading(false);
    }
  };

  // Delete saved session
  const handleDeleteSession = async (e, sessionId) => {
    e.stopPropagation();
    if (!window.confirm('Delete this test session?')) return;

    try {
      await fetch(`/api/test/session/${sessionId}`, { method: 'DELETE' });
      fetchAllSavedSessions();
      const target = quizData?.topic || selectedTopic || uploadedFile;
      if (target) fetchSavedSessions(target, activeTab);
      if (viewingSavedSession?.id === sessionId || quizData?.session_id === sessionId) {
        setViewingSavedSession(null);
        setQuizData(null);
        setSubmitResult(null);
      }
    } catch (err) {
      alert(`Error deleting test session: ${err.message}`);
    }
  };

  return (
    <div className="mode-workspace test-workspace">
      {/* Header */}
      <div className="glass-card mode-hero mode-hero--test" style={{ marginBottom: '24px' }}>
        <h2 className="mode-hero__title" style={{ fontSize: '1.4rem', fontWeight: 700, marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <HelpCircle size={22} style={{ color: '#c084fc' }} />
          Test mode — Adaptive Mastery Engine
        </h2>
        <p style={{ fontSize: '0.88rem', color: '#94a3b8' }}>
          Configurable 5 to 25 question diagnostic tests with per-question timing analysis, pattern remediation (Text & Flashcards), and dynamic quiz looping.
        </p>

        {/* 2 Subsections Navigation Tabs & Schedule Button */}
        <div className="test-mode-tabs" style={{ display: 'flex', gap: '10px', marginTop: '18px', borderTop: '1px solid rgba(148, 163, 184, 0.15)', paddingTop: '16px', alignItems: 'center', flexWrap: 'wrap' }}>
          <button
            className={`btn-secondary test-mode-tab ${activeTab === 'studied_concept' ? 'is-active' : ''}`}
            onClick={() => {
              setActiveTab('studied_concept');
              setQuizData(null);
              setSubmitResult(null);
              setViewingSavedSession(null);
            }}
            style={{
              borderColor: activeTab === 'studied_concept' ? '#c084fc' : 'rgba(255, 255, 255, 0.1)',
              background: activeTab === 'studied_concept' ? 'rgba(168, 85, 247, 0.15)' : 'rgba(19, 34, 54, 0.72)',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px'
            }}
          >
            <BookOpen size={16} style={{ color: activeTab === 'studied_concept' ? '#c084fc' : '#94a3b8' }} />
            1. Test on Studied Concept
          </button>

          <button
            className={`btn-secondary test-mode-tab ${activeTab === 'uploaded_file' ? 'is-active' : ''}`}
            onClick={() => {
              setActiveTab('uploaded_file');
              setQuizData(null);
              setSubmitResult(null);
              setViewingSavedSession(null);
            }}
            style={{
              borderColor: activeTab === 'uploaded_file' ? '#c084fc' : 'rgba(255, 255, 255, 0.1)',
              background: activeTab === 'uploaded_file' ? 'rgba(168, 85, 247, 0.15)' : 'rgba(19, 34, 54, 0.72)',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px'
            }}
          >
            <Upload size={16} style={{ color: activeTab === 'uploaded_file' ? '#c084fc' : '#94a3b8' }} />
            2. Upload File to Test on Any Concept
          </button>

          <button className="mode-schedule-button mode-schedule-button--test"
            onClick={() => setShowScheduleModal(true)}
            style={{
              marginLeft: 'auto',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              padding: '8px 16px',
              borderRadius: '8px',
              background: 'linear-gradient(135deg, #9333ea, #6366f1)',
              border: 'none',
              color: '#ffffff',
              fontSize: '0.85rem',
              fontWeight: 650,
              cursor: 'pointer',
              boxShadow: '0 4px 12px rgba(147, 51, 234, 0.35)'
            }}
          >
            <Calendar size={15} /> Schedule Test
          </button>
        </div>
      </div>

      {/* QUESTION COUNT SELECTOR (Min: 5, Max: 25) */}
      {!quizData && (
        <div className="glass-card assessment-config" style={{ marginBottom: '24px', padding: '18px 22px', background: 'rgba(15, 23, 42, 0.75)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
            <div>
              <span style={{ fontSize: '0.92rem', fontWeight: 650, color: '#f8fafc', display: 'block' }}>
                Assessment Length (Min: 5, Max: 25 questions)
              </span>
              <span style={{ fontSize: '0.78rem', color: '#94a3b8' }}>
                Configure the number of targeted questions generated for your quiz.
              </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              {[5, 10, 15, 20, 25].map((cnt) => (
                <button
                  key={cnt}
                  type="button"
                  className={`question-count-pill ${questionCount === cnt ? 'is-active' : ''}`}
                  onClick={() => setQuestionCount(cnt)}
                  style={{
                    padding: '6px 12px',
                    borderRadius: '8px',
                    fontSize: '0.82rem',
                    fontWeight: 700,
                    cursor: 'pointer',
                    background: questionCount === cnt ? 'linear-gradient(135deg, #a855f7, #c084fc)' : 'rgba(30, 41, 59, 0.8)',
                    color: questionCount === cnt ? '#ffffff' : '#cbd5e1',
                    border: questionCount === cnt ? '1px solid #c084fc' : '1px solid rgba(148, 163, 184, 0.2)',
                    transition: 'all 0.15s ease'
                  }}
                >
                  {cnt} Qs
                </button>
              ))}

              <input
                type="number"
                className="question-count-input"
                min="5"
                max="25"
                value={questionCount}
                onChange={(e) => setQuestionCount(Math.max(5, Math.min(25, Number(e.target.value) || 5)))}
                style={{
                  width: '64px',
                  padding: '6px 8px',
                  borderRadius: '8px',
                  background: 'rgba(15, 23, 42, 0.9)',
                  border: '1px solid rgba(148, 163, 184, 0.3)',
                  color: '#c084fc',
                  fontWeight: 700,
                  fontSize: '0.85rem',
                  textAlign: 'center'
                }}
              />
            </div>
          </div>
        </div>
      )}

      {/* SAVED TEST SESSIONS DRAWER / SHELF */}
      {!quizData && allSavedSessions.length > 0 && (
        <div className="glass-card mode-session-shelf mode-session-shelf--test" style={{ marginBottom: '26px', background: 'rgba(15, 23, 42, 0.85)', border: '1px solid rgba(192, 132, 252, 0.3)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px', flexWrap: 'wrap', gap: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <History size={18} style={{ color: '#c084fc' }} />
              <h4 style={{ fontSize: '1rem', fontWeight: 700, color: '#f8fafc', margin: 0 }}>
                Saved Test Sessions ({allSavedSessions.length})
              </h4>
            </div>
            <span style={{ fontSize: '0.78rem', color: '#94a3b8' }}>
              Click any session to open & review questions, answers, and timings
            </span>
          </div>

          <div className="saved-test-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '12px' }}>
            {allSavedSessions.map((s) => {
              const isCompleted = s.status === 'COMPLETED' || s.score !== null;
              return (
                <div className="saved-test-card"
                  key={s.id}
                  onClick={() => handleOpenSavedSession(s)}
                  style={{
                    padding: '12px 14px',
                    borderRadius: '10px',
                    background: 'rgba(30, 41, 59, 0.75)',
                    border: '1px solid rgba(192, 132, 252, 0.25)',
                    cursor: 'pointer',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    gap: '10px',
                    transition: 'all 0.15s ease'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = '#c084fc';
                    e.currentTarget.style.transform = 'translateY(-2px)';
                    e.currentTarget.style.boxShadow = '0 6px 18px rgba(168, 85, 247, 0.18)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = 'rgba(192, 132, 252, 0.25)';
                    e.currentTarget.style.transform = 'translateY(0)';
                    e.currentTarget.style.boxShadow = 'none';
                  }}
                >
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px' }}>
                      <span style={{ fontSize: '0.9rem', fontWeight: 700, color: '#f8fafc' }}>
                        {s.title}
                      </span>
                      <span
                        className={`badge ${s.passed ? 'badge-mastered' : isCompleted ? 'badge-revision' : 'badge-learning'}`}
                        style={{ fontSize: '0.7rem', padding: '2px 7px' }}
                      >
                        {isCompleted ? (s.passed ? '✓ Mastered' : 'Remediation') : 'In Progress'}
                      </span>
                    </div>

                    <div style={{ fontSize: '0.76rem', color: '#94a3b8', marginTop: '3px' }}>
                      {s.subsection === 'uploaded_file' ? `📄 ${s.document_name || s.topic}` : `📚 ${s.topic}`}
                    </div>

                    <div style={{ fontSize: '0.75rem', color: '#cbd5e1', display: 'flex', gap: '10px', marginTop: '8px', flexWrap: 'wrap' }}>
                      <span>{s.question_count} Qs</span>
                      {s.score !== null && (
                        <span style={{ color: s.passed ? '#34d399' : '#f87171', fontWeight: 700 }}>
                          {Math.round(s.score * 100)}% ({s.marks} Correct)
                        </span>
                      )}
                      {s.total_time_seconds ? (
                        <span>⏱ {formatSeconds(s.total_time_seconds)}</span>
                      ) : null}
                    </div>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid rgba(148, 163, 184, 0.12)', paddingTop: '8px' }}>
                    <span style={{ fontSize: '0.78rem', color: '#c084fc', fontWeight: 650, display: 'flex', alignItems: 'center', gap: '3px' }}>
                      Open Test <ChevronRight size={13} />
                    </span>

                    <button
                      onClick={(e) => handleDeleteSession(e, s.id)}
                      title="Delete test session"
                      style={{
                        background: 'transparent',
                        border: 'none',
                        color: '#64748b',
                        padding: '4px',
                        borderRadius: '4px',
                        cursor: 'pointer'
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.color = '#ef4444')}
                      onMouseLeave={(e) => (e.currentTarget.style.color = '#64748b')}
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* QUIZ NOT RUNNING: SUBSECTION VIEWS */}
      {!quizData && (
        <div>
          {/* SUBSECTION A: TEST ON STUDIED CONCEPT */}
          {activeTab === 'studied_concept' && (
            <div>
              <h3 className="mode-section-title" style={{ fontSize: '1.1rem', color: '#c084fc', marginBottom: '16px' }}>
                Select a Studied Concept from Learn ({topics.length})
              </h3>

              {loadingTopics ? (
                <div className="glass-card mode-state-card" style={{ textAlign: 'center', padding: '30px' }}>
                  <span className="skeleton-shimmer-text">Loading studied concepts from memory...</span>
                </div>
              ) : topics.length === 0 ? (
                <div className="glass-card mode-state-card mode-state-card--empty" style={{ textAlign: 'center', padding: '40px' }}>
                  <p style={{ fontSize: '1rem', color: '#94a3b8' }}>
                    No active studied concepts found in <strong>{studentProfile?.name ? `${studentProfile.name}'s` : 'your'}</strong> Learn workspace yet.
                  </p>
                  <p style={{ fontSize: '0.85rem', color: '#64748b', marginTop: '8px' }}>
                    Go to <strong>LEARN</strong> to start a lesson or upload notes!
                  </p>
                </div>
              ) : (
                <div className="mode-topic-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '20px' }}>
                  {topics.map((t, idx) => {
                    const topicSessions = allSavedSessions.filter(
                      (s) => s.topic?.toLowerCase().trim() === t.topic?.toLowerCase().trim()
                    );

                    return (
                      <div
                        key={idx}
                        className="glass-card mode-topic-card mode-topic-card--test"
                        style={{
                          display: 'flex',
                          flexDirection: 'column',
                          justifyContent: 'space-between',
                          cursor: 'pointer'
                        }}
                        onClick={() => {
                          setSelectedTopic(t.topic);
                          fetchSavedSessions(t.topic, 'studied_concept');
                        }}
                      >
                        <div>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                            <h4 style={{ fontSize: '1.12rem', fontWeight: 700, color: '#f8fafc' }}>
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

                          {topicSessions.length > 0 && (
                            <div
                              onClick={(e) => {
                                e.stopPropagation();
                                handleOpenSavedSession(topicSessions[0]);
                              }}
                              style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '6px',
                                fontSize: '0.76rem',
                                color: '#c084fc',
                                background: 'rgba(192, 132, 252, 0.12)',
                                border: '1px solid rgba(192, 132, 252, 0.25)',
                                padding: '3px 8px',
                                borderRadius: '6px',
                                marginBottom: '10px',
                                cursor: 'pointer'
                              }}
                              title="Click to open latest saved test"
                            >
                              <History size={12} /> {topicSessions.length} Saved Test{topicSessions.length > 1 ? 's' : ''} (Open Latest →)
                            </div>
                          )}

                          {t.misconceptions && t.misconceptions.length > 0 && (
                            <div style={{ background: 'rgba(239, 68, 68, 0.12)', padding: '10px 12px', borderRadius: '8px', marginBottom: '12px', border: '1px solid rgba(239, 68, 68, 0.25)' }}>
                              <div style={{ fontSize: '0.72rem', color: '#f87171', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '5px' }}>
                                <AlertCircle size={13} /> KNOWN WEAKNESS
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
                            setSelectedTopic(t.topic);
                            handleStartTest(t.topic, null, 1);
                          }}
                          style={{
                            width: '100%',
                            justifyContent: 'center',
                            marginTop: '16px',
                            background: 'linear-gradient(135deg, #a855f7, #c084fc)'
                          }}
                        >
                          Start {questionCount}-Question Test on {t.topic} →
                        </button>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* SUBSECTION B: UPLOAD FILE TO TEST ON ANY CONCEPT */}
          {activeTab === 'uploaded_file' && (
            <div>
              <div className="glass-card test-upload-card" style={{ marginBottom: '24px' }}>
                <h3 style={{ fontSize: '1.15rem', color: '#c084fc', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <FileText size={18} /> Upload Document to Test Concept
                </h3>
                <p style={{ fontSize: '0.85rem', color: '#94a3b8', marginBottom: '18px' }}>
                  Questions will be generated strictly and exclusively from the uploaded document content.
                </p>

                <div style={{ display: 'flex', gap: '14px', alignItems: 'center', flexWrap: 'wrap' }}>
                  <label
                    className="btn-secondary"
                    style={{
                      cursor: 'pointer',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '8px',
                      padding: '12px 20px',
                      background: 'rgba(30, 41, 59, 0.8)',
                      borderColor: '#c084fc'
                    }}
                  >
                    <Upload size={16} style={{ color: '#c084fc' }} />
                    <span>{uploading ? 'Uploading & parsing...' : 'Choose PDF or TXT File'}</span>
                    <input type="file" accept=".pdf,.txt" onChange={handleFileUpload} style={{ display: 'none' }} />
                  </label>

                  {uploadedFile && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#34d399', fontSize: '0.9rem', fontWeight: 600 }}>
                      <CheckCircle2 size={16} /> Ready: {uploadedFile}
                    </div>
                  )}
                </div>

                {availableDocs.length > 0 && (
                  <div style={{ marginTop: '20px' }}>
                    <span style={{ fontSize: '0.8rem', color: '#94a3b8', display: 'block', marginBottom: '8px' }}>
                      Or choose from previously uploaded documents:
                    </span>
                    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                      {availableDocs.map((doc, idx) => (
                        <button
                          key={idx}
                          type="button"
                          onClick={() => {
                            setUploadedFile(doc);
                            fetchSavedSessions(doc, 'uploaded_file');
                          }}
                          style={{
                            padding: '6px 12px',
                            borderRadius: '8px',
                            fontSize: '0.82rem',
                            cursor: 'pointer',
                            background: uploadedFile === doc ? 'rgba(168, 85, 247, 0.3)' : 'rgba(30, 41, 59, 0.6)',
                            border: uploadedFile === doc ? '1px solid #c084fc' : '1px solid rgba(148, 163, 184, 0.2)',
                            color: uploadedFile === doc ? '#f8fafc' : '#cbd5e1'
                          }}
                        >
                          📄 {doc}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {uploadedFile && (
                  <div style={{ marginTop: '24px' }}>
                    <button
                      className="btn-primary"
                      onClick={() => handleStartTest(uploadedFile, uploadedFile, 1)}
                      style={{ background: 'linear-gradient(135deg, #a855f7, #c084fc)' }}
                    >
                      Start {questionCount}-Question Test on {uploadedFile} →
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* SAVED TEST SESSIONS SECTION FOR ACTIVE TOPIC/DOCUMENT */}
          {savedSessions.length > 0 && (
            <div className="glass-card mode-session-shelf mode-session-shelf--test" style={{ marginTop: '30px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
                <History size={18} style={{ color: '#c084fc' }} />
                <h4 style={{ fontSize: '1rem', fontWeight: 700, color: '#f8fafc', margin: 0 }}>
                  Saved Test Sessions for {selectedTopic || uploadedFile} ({savedSessions.length})
                </h4>
              </div>

              <div style={{ display: 'flex', gap: '10px', overflowX: 'auto', paddingBottom: '8px' }}>
                {savedSessions.map((s) => (
                  <div
                    key={s.id}
                    onClick={() => handleOpenSavedSession(s)}
                    style={{
                      padding: '10px 14px',
                      borderRadius: '10px',
                      background: 'rgba(30, 41, 59, 0.7)',
                      border: '1px solid rgba(148, 163, 184, 0.2)',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '12px',
                      flexShrink: 0,
                      cursor: 'pointer',
                      transition: 'all 0.15s ease'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.borderColor = '#c084fc';
                      e.currentTarget.style.background = 'rgba(30, 41, 59, 0.9)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.borderColor = 'rgba(148, 163, 184, 0.2)';
                      e.currentTarget.style.background = 'rgba(30, 41, 59, 0.7)';
                    }}
                  >
                    <div>
                      <div style={{ fontSize: '0.86rem', fontWeight: 650, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '4px' }}>
                        {s.title} <ChevronRight size={12} style={{ color: '#c084fc' }} />
                      </div>
                      <div style={{ fontSize: '0.72rem', color: '#94a3b8', display: 'flex', gap: '8px', marginTop: '3px' }}>
                        <span>{s.question_count} Qs</span>
                        {s.score !== null && (
                          <span style={{ color: s.passed ? '#34d399' : '#f87171', fontWeight: 700 }}>
                            {Math.round(s.score * 100)}% ({s.marks} Correct)
                          </span>
                        )}
                        {s.total_time_seconds && (
                          <span>⏱ {formatSeconds(s.total_time_seconds)}</span>
                        )}
                      </div>
                    </div>

                    <button
                      onClick={(e) => handleDeleteSession(e, s.id)}
                      title="Delete test session"
                      style={{
                        background: 'transparent',
                        border: 'none',
                        color: '#64748b',
                        padding: '4px',
                        cursor: 'pointer'
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.color = '#ef4444')}
                      onMouseLeave={(e) => (e.currentTarget.style.color = '#64748b')}
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* QUIZ LOADING INDICATOR */}
      {loadingQuiz && (
        <TestThinkingIndicator
          topic={selectedTopic || uploadedFile || 'Concept'}
          questionCount={questionCount}
        />
      )}

      {/* ACTIVE QUIZ EXECUTION RUNNER */}
      {quizData && !submitResult && !loadingQuiz && (
        <div className="active-test-runner">
          {/* Top Bar: Back, Quiz Title, Live Timer */}
          <div className="active-test-toolbar" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px', flexWrap: 'wrap', gap: '10px' }}>
            <button
              className="btn-secondary"
              onClick={() => {
                if (window.confirm('Leave test? Current progress will be lost.')) {
                  setQuizData(null);
                  if (activeQTimerRef.current) clearInterval(activeQTimerRef.current);
                }
              }}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
            >
              <ArrowLeft size={16} /> Exit Test
            </button>

            <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
              <div className="test-live-timer"
                style={{
                  background: 'rgba(30, 41, 59, 0.8)',
                  padding: '6px 14px',
                  borderRadius: '99px',
                  border: '1px solid rgba(192, 132, 252, 0.3)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  fontSize: '0.84rem',
                  fontWeight: 650,
                  color: '#c084fc'
                }}
              >
                <Clock size={15} /> Question Time: {formatSeconds(currentElapsed)}
              </div>

              <span className="badge badge-learning" style={{ fontSize: '0.84rem' }}>
                Round {loopRound} • Q {currentQIndex + 1} of {quizData.questions.length}
              </span>
            </div>
          </div>

          {/* Question Index Progress Pills */}
          <div className="question-progress-rail" style={{ display: 'flex', gap: '6px', overflowX: 'auto', marginBottom: '20px', paddingBottom: '6px' }}>
            {quizData.questions.map((q, idx) => {
              const isAnswered = Boolean(answers[q.id]);
              const isCurrent = idx === currentQIndex;
              return (
                <button
                  key={q.id || idx}
                  type="button"
                  className={`question-progress-pill ${isCurrent ? 'is-current' : ''} ${isAnswered ? 'is-answered' : ''}`}
                  onClick={() => handleSelectQuestion(idx)}
                  style={{
                    width: '36px',
                    height: '36px',
                    borderRadius: '8px',
                    fontWeight: 700,
                    fontSize: '0.85rem',
                    cursor: 'pointer',
                    background: isCurrent
                      ? 'linear-gradient(135deg, #a855f7, #c084fc)'
                      : isAnswered
                      ? 'rgba(52, 211, 153, 0.2)'
                      : 'rgba(30, 41, 59, 0.7)',
                    border: isCurrent
                      ? '2px solid #ffffff'
                      : isAnswered
                      ? '1px solid rgba(52, 211, 153, 0.4)'
                      : '1px solid rgba(148, 163, 184, 0.2)',
                    color: isCurrent ? '#ffffff' : isAnswered ? '#6ee7b7' : '#94a3b8',
                    flexShrink: 0
                  }}
                >
                  {idx + 1}
                </button>
              );
            })}
          </div>

          {/* Current Question Card */}
          {quizData.questions[currentQIndex] && (() => {
            const q = quizData.questions[currentQIndex];
            const qId = q.id;
            const selectedOpt = answers[qId] || '';

            return (
              <div className="glass-card active-question-card" style={{ padding: '26px', marginBottom: '20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                  <span style={{ fontSize: '0.8rem', color: '#c084fc', textTransform: 'uppercase', fontWeight: 700, letterSpacing: '0.04em' }}>
                    Concept: {q.sub_concept}
                  </span>
                  <span style={{ fontSize: '0.78rem', color: '#94a3b8' }}>
                    Time spent: {formatSeconds(questionTimings[qId] || 0 + currentElapsed)}
                  </span>
                </div>

                <h3 style={{ fontSize: '1.15rem', color: '#f8fafc', lineHeight: 1.5, marginBottom: '22px' }}>
                  {q.question}
                </h3>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {q.options.map((opt, optIdx) => {
                    const isChecked = selectedOpt === opt;
                    return (
                      <label className={`test-answer-option ${isChecked ? 'is-selected' : ''}`}
                        key={optIdx}
                        onClick={() => setAnswers((prev) => ({ ...prev, [qId]: opt }))}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '12px',
                          cursor: 'pointer',
                          padding: '12px 16px',
                          borderRadius: '10px',
                          background: isChecked ? 'rgba(168, 85, 247, 0.18)' : 'rgba(30, 41, 59, 0.6)',
                          border: isChecked ? '1px solid #c084fc' : '1px solid rgba(148, 163, 184, 0.18)',
                          transition: 'all 0.15s ease',
                          color: isChecked ? '#f8fafc' : '#cbd5e1',
                          fontSize: '0.94rem'
                        }}
                      >
                        <input
                          type="radio"
                          name={qId}
                          value={opt}
                          checked={isChecked}
                          onChange={() => setAnswers((prev) => ({ ...prev, [qId]: opt }))}
                        />
                        <span>{opt}</span>
                      </label>
                    );
                  })}
                </div>

                {/* Question Navigation & Submit */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '28px' }}>
                  <button
                    className="btn-secondary"
                    disabled={currentQIndex === 0}
                    onClick={() => handleSelectQuestion(currentQIndex - 1)}
                    style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                  >
                    <ArrowLeft size={16} /> Previous
                  </button>

                  <div style={{ display: 'flex', gap: '12px' }}>
                    {currentQIndex < quizData.questions.length - 1 ? (
                      <button
                        className="btn-primary"
                        onClick={() => handleSelectQuestion(currentQIndex + 1)}
                        style={{ background: 'linear-gradient(135deg, #a855f7, #c084fc)', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                      >
                        Next <ArrowRight size={16} />
                      </button>
                    ) : (
                      <button
                        className="btn-primary"
                        onClick={handleSubmitQuiz}
                        disabled={submitting}
                        style={{ background: 'linear-gradient(135deg, #22c55e, #16a34a)', boxShadow: '0 4px 14px rgba(34, 197, 94, 0.3)' }}
                      >
                        {submitting ? 'Analyzing & Scoring...' : 'Submit All Answers'}
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })()}
        </div>
      )}

      {/* TEST SUBMISSION RESULTS & ADAPTIVE REMEDIATION LOOP */}
      {submitResult && (
        <div className="test-results-workspace">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '10px' }}>
            <button
              className="btn-secondary"
              onClick={() => {
                setSubmitResult(null);
                setQuizData(null);
                setViewingSavedSession(null);
                fetchTopics();
                fetchAllSavedSessions();
              }}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
            >
              <ArrowLeft size={16} /> Return to Tests Menu
            </button>

            {viewingSavedSession && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'rgba(192, 132, 252, 0.15)', border: '1px solid rgba(192, 132, 252, 0.35)', padding: '6px 14px', borderRadius: '8px' }}>
                <History size={14} style={{ color: '#c084fc' }} />
                <span style={{ fontSize: '0.82rem', color: '#f3e8ff', fontWeight: 650 }}>
                  Viewing: {viewingSavedSession.title}
                </span>
              </div>
            )}
          </div>

          {/* 1. Score, Marks, and Timing Analysis Card */}
          <div className="glass-card test-score-card" style={{ marginBottom: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '10px' }}>
              <div>
                <span className={`badge ${submitResult.passed ? 'badge-mastered' : 'badge-revision'}`} style={{ fontSize: '1rem', padding: '6px 14px', marginBottom: '8px', display: 'inline-block' }}>
                  {submitResult.passed ? '✓ MASTERED' : '⚠ WEAKNESS DETECTED'}
                </span>
                <h3 style={{ fontSize: '1.4rem', fontWeight: 700, color: '#f8fafc' }}>
                  Marks: {submitResult.marks} / {submitResult.total} ({Math.round(submitResult.score * 100)}%)
                </h3>
              </div>

              {/* Timing Analysis Metric Pills */}
              <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                <div style={{ background: 'rgba(30, 41, 59, 0.7)', padding: '8px 14px', borderRadius: '10px', border: '1px solid rgba(148, 163, 184, 0.15)' }}>
                  <span style={{ fontSize: '0.72rem', color: '#94a3b8', textTransform: 'uppercase', display: 'block' }}>
                    Total Time
                  </span>
                  <span style={{ fontSize: '1rem', fontWeight: 700, color: '#f8fafc' }}>
                    {formatSeconds(submitResult.total_time_seconds)}
                  </span>
                </div>

                <div style={{ background: 'rgba(30, 41, 59, 0.7)', padding: '8px 14px', borderRadius: '10px', border: '1px solid rgba(148, 163, 184, 0.15)' }}>
                  <span style={{ fontSize: '0.72rem', color: '#94a3b8', textTransform: 'uppercase', display: 'block' }}>
                    Average / Question
                  </span>
                  <span style={{ fontSize: '1rem', fontWeight: 700, color: '#38bdf8' }}>
                    {formatSeconds(submitResult.average_time_per_question)}
                  </span>
                </div>
              </div>
            </div>

            {submitResult.flagged_hesitations && submitResult.flagged_hesitations.length > 0 && (
              <div style={{ background: 'rgba(245, 158, 11, 0.12)', padding: '10px 14px', borderRadius: '8px', border: '1px solid rgba(245, 158, 11, 0.25)', color: '#fbbf24', fontSize: '0.84rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Clock size={16} />
                Notice: Long hesitation was measured on {submitResult.flagged_hesitations.length} question(s). These are highlighted below as priority review points.
              </div>
            )}
          </div>

          {/* 2. ADAPTIVE REMEDIATION LOOP PROMPTS */}
          {/* STEP A: Ask user if they want to revise and make concept strong */}
          {loopStep === 'ask_revise' && (
            <div
              className="glass-card remediation-card"
              style={{
                marginBottom: '28px',
                padding: '24px',
                background: 'linear-gradient(145deg, rgba(30, 27, 75, 0.7), rgba(15, 23, 42, 0.9))',
                border: '1px solid rgba(192, 132, 252, 0.4)',
                boxShadow: '0 8px 30px rgba(0,0,0,0.35)'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: '#c084fc', marginBottom: '8px' }}>
                <Sparkles size={20} />
                <h4 style={{ fontSize: '1.15rem', fontWeight: 700, margin: 0 }}>
                  Do you want to revise and make your concept strong?
                </h4>
              </div>
              <p style={{ fontSize: '0.9rem', color: '#cbd5e1', lineHeight: 1.5, marginBottom: '20px' }}>
                EduNexus can analyze your test answer patterns and synthesize a personalized review to eliminate any misunderstandings before you test again.
              </p>

              <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                <button
                  className="btn-primary"
                  onClick={() => setLoopStep('choose_format')}
                  style={{ background: 'linear-gradient(135deg, #a855f7, #c084fc)', display: 'inline-flex', alignItems: 'center', gap: '8px' }}
                >
                  <Check size={16} /> Yes, Revise & Strengthen Concepts
                </button>

                <button
                  className="btn-secondary"
                  onClick={() => setLoopStep(null)}
                  style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}
                >
                  No, I'm Done
                </button>
              </div>
            </div>
          )}

          {/* STEP B: Ask user whether they want Text Concept or Flashcards */}
          {loopStep === 'choose_format' && (
            <div
              className="glass-card remediation-card"
              style={{
                marginBottom: '28px',
                padding: '24px',
                background: 'linear-gradient(145deg, rgba(30, 27, 75, 0.7), rgba(15, 23, 42, 0.9))',
                border: '1px solid rgba(192, 132, 252, 0.4)'
              }}
            >
              <h4 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#f8fafc', marginBottom: '8px' }}>
                How would you like to review your weak areas?
              </h4>
              <p style={{ fontSize: '0.88rem', color: '#94a3b8', marginBottom: '18px' }}>
                Select your preferred learning modality to analyze your test patterns:
              </p>

              <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
                <button
                  className="btn-secondary"
                  onClick={() => handleGenerateReview('text')}
                  disabled={reviewLoading}
                  style={{
                    padding: '16px 20px',
                    borderColor: '#818cf8',
                    background: 'rgba(30, 41, 59, 0.8)',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'flex-start',
                    gap: '6px',
                    flex: '1 1 220px'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#818cf8', fontWeight: 700 }}>
                    <BookOpen size={18} /> Text Concept Explanation
                  </div>
                  <span style={{ fontSize: '0.78rem', color: '#94a3b8', textAlign: 'left' }}>
                    Detailed walkthrough breaking down your exact test pitfalls and explaining the correct logic.
                  </span>
                </button>

                <button
                  className="btn-secondary"
                  onClick={() => handleGenerateReview('flashcards')}
                  disabled={reviewLoading}
                  style={{
                    padding: '16px 20px',
                    borderColor: '#a855f7',
                    background: 'rgba(30, 41, 59, 0.8)',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'flex-start',
                    gap: '6px',
                    flex: '1 1 220px'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#c084fc', fontWeight: 700 }}>
                    <Layers size={18} /> Interactive Flashcards Deck
                  </div>
                  <span style={{ fontSize: '0.78rem', color: '#94a3b8', textAlign: 'left' }}>
                    Bite-sized cards with formulas, worked examples, and pitfalls for rapid memory reinforcement.
                  </span>
                </button>
              </div>

              {reviewLoading && (
                <div style={{ marginTop: '16px', textAlign: 'center' }}>
                  <span className="thinking-text">
                    Analyzing test answer patterns and synthesizing your {reviewMode}...
                  </span>
                </div>
              )}
            </div>
          )}

          {/* STEP C: Display the generated remediation (Text or Flashcards) & Prompt for Next Quiz */}
          {loopStep === 'view_remediation' && reviewData && (
            <div style={{ marginBottom: '28px' }}>
              {reviewMode === 'text' ? (
                <div className="glass-card mode-content-card" style={{ marginBottom: '20px' }}>
                  <h4 style={{ fontSize: '1.2rem', color: '#818cf8', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <BookOpen size={20} /> Targeted Concept Remediation
                  </h4>
                  <div style={{ background: 'rgba(15, 23, 42, 0.75)', padding: '20px', borderRadius: '12px', borderLeft: '4px solid #818cf8' }}>
                    <FormattedText content={reviewData.content} />
                  </div>
                </div>
              ) : (
                <div className="glass-card mode-content-card mode-content-card--flashcards" style={{ marginBottom: '20px' }}>
                  <h4 style={{ fontSize: '1.2rem', color: '#c084fc', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Layers size={20} /> Test Remediation Flashcards
                  </h4>
                  <div style={{ display: 'flex', justifyContent: 'center' }}>
                    <FlashcardDeck data={reviewData.content} />
                  </div>
                </div>
              )}

              {/* STEP D: Ask user if ready for another quiz (Loop continuation) */}
              <div
                className="glass-card remediation-card remediation-card--success"
                style={{
                  padding: '22px',
                  background: 'linear-gradient(145deg, rgba(30, 27, 75, 0.7), rgba(15, 23, 42, 0.9))',
                  border: '1px solid rgba(52, 211, 153, 0.35)'
                }}
              >
                <h4 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#34d399', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Sparkles size={18} /> Are you ready for another quiz?
                </h4>
                <p style={{ fontSize: '0.88rem', color: '#cbd5e1', marginBottom: '16px' }}>
                  Reinforce your newly strengthened understanding with the next diagnostic quiz round.
                </p>

                <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                  <button
                    className="btn-primary"
                    onClick={() => handleStartTest(quizData.topic, quizData.document_name, loopRound + 1)}
                    style={{ background: 'linear-gradient(135deg, #10b981, #059669)', display: 'inline-flex', alignItems: 'center', gap: '8px' }}
                  >
                    <Play size={16} /> Yes, Start Quiz Round {loopRound + 1}
                  </button>

                  <button
                    className="btn-secondary"
                    onClick={() => setLoopStep(null)}
                    style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}
                  >
                    No, Finish & Exit
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* 3. Detailed Question-by-Question Review */}
          <div className="glass-card detailed-results-card">
            <h4 style={{ fontSize: '1.15rem', color: '#f8fafc', marginBottom: '16px' }}>
              Detailed Question Review & Explanations ({submitResult.results.length} questions)
            </h4>

            {submitResult.results.map((r, idx) => {
              const isCorrect = r.is_correct;
              const isHesitant = r.is_hesitant;
              return (
                <div
                  key={idx}
                  style={{
                    background: 'rgba(30, 41, 59, 0.6)',
                    padding: '16px 18px',
                    borderRadius: '12px',
                    marginBottom: '14px',
                    borderLeft: isCorrect ? '4px solid #34d399' : '4px solid #f87171'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                    <span style={{ fontSize: '0.84rem', fontWeight: 700, color: isCorrect ? '#34d399' : '#f87171' }}>
                      {isCorrect ? '✓ CORRECT' : '✕ INCORRECT'} • Q{idx + 1} ({r.sub_concept})
                    </span>

                    <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                      {isHesitant && (
                        <span style={{ fontSize: '0.72rem', color: '#fbbf24', background: 'rgba(245, 158, 11, 0.15)', padding: '2px 6px', borderRadius: '4px' }}>
                          Slow Response
                        </span>
                      )}
                      <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                        ⏱ {formatSeconds(r.time_spent_seconds)}
                      </span>
                    </div>
                  </div>

                  <p style={{ fontSize: '0.94rem', fontWeight: 600, color: '#f1f5f9', marginBottom: '10px' }}>
                    {r.question}
                  </p>

                  <div style={{ fontSize: '0.86rem', display: 'flex', flexDirection: 'column', gap: '4px', marginBottom: '10px' }}>
                    <div>
                      <span style={{ color: '#94a3b8' }}>Your Answer: </span>
                      <span style={{ color: isCorrect ? '#34d399' : '#f87171', fontWeight: 600 }}>
                        {r.user_answer || '(No answer provided)'}
                      </span>
                    </div>

                    {!isCorrect && (
                      <div>
                        <span style={{ color: '#94a3b8' }}>Correct Answer: </span>
                        <span style={{ color: '#34d399', fontWeight: 600 }}>{r.correct_answer}</span>
                      </div>
                    )}
                  </div>

                  {r.explanation && (
                    <div style={{ fontSize: '0.82rem', color: '#cbd5e1', background: 'rgba(15, 23, 42, 0.5)', padding: '8px 12px', borderRadius: '8px' }}>
                      <strong>Explanation: </strong> {r.explanation}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Scheduling Modal */}
      <ScheduleModal
        isOpen={showScheduleModal}
        onClose={() => setShowScheduleModal(false)}
        studentId={studentId}
        studentProfile={studentProfile}
        mode="test"
        defaultTopic={selectedTopic || ''}
        availableTopics={topics.map((t) => t.topic)}
      />
    </div>
  );
}
