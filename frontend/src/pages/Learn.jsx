import React, { useEffect, useRef, useState } from 'react';
import {
  ArrowLeft, BookOpen, CheckCircle2, Clock3, FileText, Layers, Loader2,
  MessageSquare, Paperclip, Play, Plus, Search, Send, Settings2, Sparkles, Trash2, Type, X,
} from 'lucide-react';
import FlashcardDeck from '../components/FlashcardDeck';
import Visualizer from '../components/Visualizer';

const formatDate = (value) => {
  if (!value) return '';
  const date = new Date(value);
  const today = new Date();
  if (date.toDateString() === today.toDateString()) {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }
  return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
};

const fileSize = (bytes = 0) => bytes < 1024 * 1024
  ? `${Math.max(1, Math.round(bytes / 1024))} KB`
  : `${(bytes / (1024 * 1024)).toFixed(1)} MB`;

const DEFAULT_LEARN_SETTINGS = {
  chat_style: 'auto',
  chat_custom_instruction: '',
  animation_style: 'auto',
  animation_content: 'auto',
  animation_engine: 'auto',
  animation_custom_instruction: '',
  flashcard_style: 'auto',
  flashcard_content: 'auto',
  flashcard_custom_instruction: '',
};

const loadLearnSettings = () => {
  try {
    const saved = JSON.parse(localStorage.getItem('edunexus:learn-settings') || '{}');
    return { ...DEFAULT_LEARN_SETTINGS, ...saved };
  } catch {
    return { ...DEFAULT_LEARN_SETTINGS };
  }
};

function SettingChoice({ label, description, value, options, onChange }) {
  return (
    <div className="learn-setting-row">
      <div className="learn-setting-row__copy"><strong>{label}</strong>{description && <small>{description}</small>}</div>
      <div className="learn-setting-options" role="group" aria-label={label}>
        {options.map((option) => (
          <button key={option.value} type="button" className={value === option.value ? 'is-active' : ''} onClick={() => onChange(option.value)}>{option.label}</button>
        ))}
      </div>
    </div>
  );
}

function LearnSettingsDialog({ draft, setDraft, onClose, onSave, onReset }) {
  const setValue = (key, value) => setDraft((previous) => ({ ...previous, [key]: value }));
  const standardStyles = [{ value: 'auto', label: 'Auto' }, { value: 'simple', label: 'Simple' }, { value: 'vibrant', label: 'Vibrant' }];

  return (
    <div className="learn-settings-overlay" role="dialog" aria-modal="true" aria-labelledby="learn-settings-title" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <form className="learn-settings-dialog" onSubmit={(event) => { event.preventDefault(); onSave(); }}>
        <header className="learn-settings-dialog__header">
          <span className="learn-settings-dialog__icon"><Settings2 size={20} /></span>
          <div><span>Learning workspace</span><h2 id="learn-settings-title">Response settings</h2><p>Personalize replies generated inside Learn. Auto keeps the current behavior.</p></div>
          <button type="button" className="icon-button" onClick={onClose} aria-label="Close settings"><X size={18} /></button>
        </header>

        <div className="learn-settings-body">
          <section className="learn-settings-section">
            <div className="learn-settings-section__title"><Type size={16} /><div><strong>Chat responses</strong><small>Used when “Text” is selected.</small></div></div>
            <SettingChoice label="Chat style" value={draft.chat_style} options={[{ value: 'auto', label: 'Auto' }, { value: 'crisp', label: 'Crisp' }, { value: 'detailed', label: 'Detailed' }]} onChange={(value) => setValue('chat_style', value)} />
            <label className="learn-settings-field"><span>Custom instruction for chat</span><textarea rows="3" maxLength="2000" value={draft.chat_custom_instruction} onChange={(event) => setValue('chat_custom_instruction', event.target.value)} placeholder="e.g. Explain with Python examples and avoid unnecessary jargon." /></label>
          </section>

          <section className="learn-settings-section">
            <div className="learn-settings-section__title"><Play size={16} /><div><strong>Animated videos</strong><small>Controls storyboard detail and visual treatment.</small></div></div>
            <SettingChoice label="Animation style" value={draft.animation_style} options={standardStyles} onChange={(value) => setValue('animation_style', value)} />
            <SettingChoice label="Animation content" value={draft.animation_content} options={[{ value: 'auto', label: 'Auto' }, { value: 'less', label: 'Less' }, { value: 'more', label: 'More' }]} onChange={(value) => setValue('animation_content', value)} />
            <SettingChoice label="Animation engine" description="Auto chooses the best engine for the topic and still uses backups if rendering fails." value={draft.animation_engine} options={[{ value: 'auto', label: 'Auto' }, { value: 'manim', label: 'Manim' }, { value: 'motion_graphics', label: 'Motion graphics' }]} onChange={(value) => setValue('animation_engine', value)} />
            <label className="learn-settings-field"><span>Custom instruction for animation</span><textarea rows="3" maxLength="2000" value={draft.animation_custom_instruction} onChange={(event) => setValue('animation_custom_instruction', event.target.value)} placeholder="e.g. Use a dark background and pause on every algorithm state." /></label>
          </section>

          <section className="learn-settings-section">
            <div className="learn-settings-section__title"><Layers size={16} /><div><strong>Flashcards</strong><small>Controls card design and explanation depth.</small></div></div>
            <SettingChoice label="Flashcard style" value={draft.flashcard_style} options={standardStyles} onChange={(value) => setValue('flashcard_style', value)} />
            <SettingChoice label="Flashcard content" value={draft.flashcard_content} options={[{ value: 'auto', label: 'Auto' }, { value: 'crisp', label: 'Crisp' }, { value: 'detailed', label: 'Detailed' }]} onChange={(value) => setValue('flashcard_content', value)} />
            <label className="learn-settings-field"><span>Custom instruction for flashcards</span><textarea rows="3" maxLength="2000" value={draft.flashcard_custom_instruction} onChange={(event) => setValue('flashcard_custom_instruction', event.target.value)} placeholder="e.g. Add one practical example and a quick recall question to every card." /></label>
          </section>
        </div>

        <footer className="learn-settings-actions"><button type="button" className="btn-secondary" onClick={onReset}>Reset to Auto</button><div><button type="button" className="btn-secondary" onClick={onClose}>Cancel</button><button type="submit" className="btn-primary">Save settings</button></div></footer>
      </form>
    </div>
  );
}

function ThinkingIndicator({ mode = 'text' }) {
  const [stage, setStage] = useState(0);
  const stageSets = {
    text: ['Thinking...', 'Preparing...', 'Final drafting...'],
    flashcards: ['Planning cards...', 'Designing visuals...', 'Building your deck...'],
    video: ['Writing storyboard...', 'Rendering scenes...', 'Finalizing animation...'],
  };
  const stages = stageSets[mode] || stageSets.text;

  useEffect(() => {
    const timer1 = setTimeout(() => setStage(1), 2400);
    const timer2 = setTimeout(() => setStage(2), 5200);

    return () => {
      clearTimeout(timer1);
      clearTimeout(timer2);
    };
  }, []);

  return (
    <div className={`shimmer-indicator-bubble shimmer-indicator-bubble--${mode}`}>
      <div className="generation-skeleton" aria-hidden="true"><i /><i /><i /></div>
      <span key={stage} className="thinking-text shimmer-stage-animate">{stages[stage]}</span>
    </div>
  );
}



function AnimatedLesson({ data }) {
  if (!data?.media_url) return null;
  return (
    <div className="animated-lesson">
      {data.mime_type === 'video/mp4'
        ? <video src={data.media_url} controls autoPlay playsInline preload="metadata" />
        : <img src={data.media_url} alt={data.title || 'Animated lesson'} />}
    </div>
  );
}

function parseInline(text) {
  if (!text) return text;
  const parts = [];
  const regex = /(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*)/g;
  let lastIndex = 0;
  let match;
  let key = 0;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    const token = match[0];
    if (token.startsWith('`') && token.endsWith('`')) {
      parts.push(<code key={key++} className="md-inline-code">{token.slice(1, -1)}</code>);
    } else if (token.startsWith('**') && token.endsWith('**')) {
      parts.push(<strong key={key++} className="md-bold">{token.slice(2, -2)}</strong>);
    } else if (token.startsWith('*') && token.endsWith('*')) {
      parts.push(<em key={key++} className="md-italic">{token.slice(1, -1)}</em>);
    }
    lastIndex = regex.lastIndex;
  }
  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }
  return parts.length > 0 ? parts : text;
}

function FormattedText({ content }) {
  if (!content) return null;
  const blocks = [];
  const lines = content.split('\n');
  let inCodeBlock = false;
  let codeBuffer = [];
  let listBuffer = [];
  let listType = null;
  let blockKey = 0;

  const flushList = () => {
    if (listBuffer.length > 0) {
      const items = listBuffer.map((item, idx) => (
        <li key={idx} className="md-list-item">{parseInline(item)}</li>
      ));
      if (listType === 'ol') {
        blocks.push(<ol key={blockKey++} className="md-ol">{items}</ol>);
      } else {
        blocks.push(<ul key={blockKey++} className="md-ul">{items}</ul>);
      }
      listBuffer = [];
      listType = null;
    }
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    if (line.trim().startsWith('```')) {
      flushList();
      if (!inCodeBlock) {
        inCodeBlock = true;
        codeBuffer = [];
      } else {
        inCodeBlock = false;
        blocks.push(
          <pre key={blockKey++} className="md-pre">
            <code className="md-code-block">{codeBuffer.join('\n')}</code>
          </pre>
        );
        codeBuffer = [];
      }
      continue;
    }

    if (inCodeBlock) {
      codeBuffer.push(line);
      continue;
    }

    const headingMatch = line.match(/^(#{1,4})\s+(.+)$/);
    if (headingMatch) {
      flushList();
      const level = headingMatch[1].length;
      const headingText = headingMatch[2];
      if (level <= 2) {
        blocks.push(<h3 key={blockKey++} className="md-h2">{parseInline(headingText)}</h3>);
      } else {
        blocks.push(<h4 key={blockKey++} className="md-h3">{parseInline(headingText)}</h4>);
      }
      continue;
    }

    const ulMatch = line.match(/^(\*|-)\s+(.+)$/);
    if (ulMatch) {
      if (listType !== 'ul') flushList();
      listType = 'ul';
      listBuffer.push(ulMatch[2]);
      continue;
    }

    const olMatch = line.match(/^(\d+)\.\s+(.+)$/);
    if (olMatch) {
      if (listType !== 'ol') flushList();
      listType = 'ol';
      listBuffer.push(olMatch[2]);
      continue;
    }

    flushList();
    if (line.trim() === '') {
      blocks.push(<div key={blockKey++} className="md-spacer" />);
    } else {
      blocks.push(<p key={blockKey++} className="md-p">{parseInline(line)}</p>);
    }
  }

  flushList();
  if (inCodeBlock && codeBuffer.length > 0) {
    blocks.push(
      <pre key={blockKey++} className="md-pre">
        <code className="md-code-block">{codeBuffer.join('\n')}</code>
      </pre>
    );
  }

  return <div className="formatted-markdown">{blocks}</div>;
}

function ProgressiveMessageText({ text, isNew = false, onProgress }) {
  const [displayedLength, setDisplayedLength] = useState(isNew ? 0 : (text ? text.length : 0));

  useEffect(() => {
    if (!isNew || !text) {
      setDisplayedLength(text ? text.length : 0);
      return;
    }

    const tokens = text.split(/(\s+)/);
    let index = 0;
    const chunkSize = 2;
    const intervalMs = 26;

    const timer = setInterval(() => {
      index += chunkSize;
      if (index >= tokens.length) {
        setDisplayedLength(text.length);
        clearInterval(timer);
        onProgress?.();
      } else {
        const currentSlice = tokens.slice(0, index).join('');
        setDisplayedLength(currentSlice.length);
        onProgress?.();
      }
    }, intervalMs);

    return () => clearInterval(timer);
  }, [text, isNew]);

  const visibleContent = isNew ? text.slice(0, displayedLength) : text;
  const isTyping = isNew && displayedLength < text.length;

  return (
    <div className={`message-text ${isTyping ? 'is-streaming' : ''}`}>
      <FormattedText content={visibleContent} />
      {isTyping && <span className="progressive-cursor" />}
    </div>
  );
}

export default function Learn({ studentId, onRefreshProfile }) {
  const [sessions, setSessions] = useState([]);
  const [activeSession, setActiveSession] = useState(null);
  const [loadingSessions, setLoadingSessions] = useState(true);
  const [openingSession, setOpeningSession] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [sessionSearch, setSessionSearch] = useState('');
  const [newLesson, setNewLesson] = useState({ title: '', description: '' });
  const [creating, setCreating] = useState(false);
  const [inputMsg, setInputMsg] = useState('');
  const [responseMode, setResponseMode] = useState('text');
  const [learnSettings, setLearnSettings] = useState(loadLearnSettings);
  const [settingsDraft, setSettingsDraft] = useState(loadLearnSettings);
  const [showSettings, setShowSettings] = useState(false);
  const [sending, setSending] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [streamingMessageId, setStreamingMessageId] = useState(null);
  const [checkQuiz, setCheckQuiz] = useState(null);
  const [userAnswers, setUserAnswers] = useState({});
  const [quizResult, setQuizResult] = useState(null);
  const messageEndRef = useRef(null);
  const fileInputRef = useRef(null);

  const openSettings = () => {
    setSettingsDraft({ ...learnSettings });
    setShowSettings(true);
  };

  const saveSettings = () => {
    setLearnSettings(settingsDraft);
    localStorage.setItem('edunexus:learn-settings', JSON.stringify(settingsDraft));
    setShowSettings(false);
  };

  const resetSettings = () => setSettingsDraft({ ...DEFAULT_LEARN_SETTINGS });

  const loadSessions = async (preferredId) => {
    setLoadingSessions(true);
    setError('');
    try {
      const res = await fetch(`/api/learn/sessions/${encodeURIComponent(studentId)}`);
      if (!res.ok) throw new Error('Could not load your chats.');
      const data = await res.json();
      setSessions(data.sessions || []);
      const remembered = preferredId || localStorage.getItem(`edunexus:last-chat:${studentId}`);
      if (remembered && data.sessions?.some((session) => session.id === remembered)) {
        await openSession(remembered, false);
      } else {
        setActiveSession(null);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingSessions(false);
    }
  };

  const openSession = async (sessionId, closeMobile = true) => {
    setOpeningSession(true);
    setError('');
    setStreamingMessageId(null);
    setCheckQuiz(null);
    setQuizResult(null);
    try {
      const res = await fetch(`/api/learn/session/${sessionId}`);
      if (!res.ok) throw new Error('Could not open this chat.');
      const session = await res.json();
      setActiveSession(session);
      localStorage.setItem(`edunexus:last-chat:${studentId}`, sessionId);
      if (closeMobile && window.innerWidth <= 760) setSidebarOpen(false);
    } catch (err) {
      setError(err.message);
    } finally {
      setOpeningSession(false);
    }
  };

  const deleteSession = async (sessionId, event) => {
    event?.stopPropagation();
    event?.preventDefault();
    if (!window.confirm('Are you sure you want to delete this chat session?')) return;

    try {
      const res = await fetch(`/api/learn/session/${sessionId}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Could not delete chat session.');

      const remaining = sessions.filter((s) => s.id !== sessionId);
      setSessions(remaining);

      if (activeSession?.id === sessionId) {
        if (remaining.length > 0) {
          await openSession(remaining[0].id, false);
        } else {
          setActiveSession(null);
          localStorage.removeItem(`edunexus:last-chat:${studentId}`);
        }
      }
      onRefreshProfile?.();
    } catch (err) {
      setError(err.message);
    }
  };

  useEffect(() => { loadSessions(); }, [studentId]);
  useEffect(() => { messageEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [activeSession?.messages, sending]);

  const createSession = async (event) => {
    event.preventDefault();
    if (!newLesson.title.trim() || !newLesson.description.trim()) return;
    setCreating(true);
    setError('');
    try {
      const res = await fetch('/api/learn/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ student_id: studentId, ...newLesson }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Could not create the chat.');
      setActiveSession(data);
      setSessions((previous) => [{ ...data, message_count: 0, attachment_count: 0 }, ...previous]);
      localStorage.setItem(`edunexus:last-chat:${studentId}`, data.id);
      setNewLesson({ title: '', description: '' });
      setShowCreate(false);
      setSidebarOpen(window.innerWidth > 760);
    } catch (err) {
      setError(err.message);
    } finally {
      setCreating(false);
    }
  };

  const sendMessage = async (event) => {
    event?.preventDefault();
    const text = inputMsg.trim();
    if (!text || sending || !activeSession) return;
    const optimistic = { id: `pending-${Date.now()}`, sender: 'user', text, requested_mode: responseMode, created_at: new Date().toISOString() };
    setActiveSession((previous) => ({ ...previous, messages: [...previous.messages, optimistic] }));
    setInputMsg('');
    setSending(true);
    setError('');
    try {
      const res = await fetch('/api/learn/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          student_id: studentId,
          session_id: activeSession.id,
          topic: activeSession.title,
          message: text,
          response_mode: responseMode,
          preferences: learnSettings,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'The tutor could not respond.');
      const tutorMessage = data.message || {
        id: `reply-${Date.now()}`,
        sender: 'tutor',
        text: data.response,
        visualization: data.visualization,
        content_type: data.content_type || responseMode,
        content_data: data.content_data,
        is_grounded: data.is_grounded,
        created_at: new Date().toISOString(),
      };
      setStreamingMessageId(tutorMessage.id);
      setActiveSession((previous) => ({ ...previous, messages: [...previous.messages, tutorMessage] }));
      setSessions((previous) => previous.map((session) => session.id === activeSession.id
        ? { ...session, updated_at: new Date().toISOString(), message_count: (session.message_count || 0) + 2 }
        : session).sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at)));
      onRefreshProfile?.();
    } catch (err) {
      setError(err.message);
      setActiveSession((previous) => ({ ...previous, messages: previous.messages.filter((message) => message.id !== optimistic.id) }));
      setInputMsg(text);
    } finally {
      setSending(false);
    }
  };

  const uploadFile = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file || !activeSession) return;
    setUploading(true);
    setError('');
    const body = new FormData();
    body.append('file', file);
    try {
      const res = await fetch(`/api/learn/session/${activeSession.id}/documents`, { method: 'POST', body });
      const attachment = await res.json();
      if (!res.ok) throw new Error(attachment.detail || 'Could not upload the document.');
      setActiveSession((previous) => ({ ...previous, attachments: [...previous.attachments, attachment] }));
      setSessions((previous) => previous.map((session) => session.id === activeSession.id
        ? { ...session, attachment_count: (session.attachment_count || 0) + 1, updated_at: new Date().toISOString() }
        : session));
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  const checkUnderstanding = async () => {
    if (!activeSession) return;
    setSending(true);
    setQuizResult(null);
    setUserAnswers({});
    try {
      const res = await fetch('/api/learn/check_understanding', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          student_id: studentId,
          topic: activeSession.title,
          document_name: activeSession.attachments[0]?.stored_name || null,
        }),
      });
      if (!res.ok) throw new Error('Could not create a knowledge check.');
      const data = await res.json();
      setCheckQuiz(data.questions);
    } catch (err) {
      setError(err.message);
    } finally {
      setSending(false);
    }
  };

  const submitQuiz = () => {
    const score = checkQuiz.reduce((total, question) => {
      const answer = userAnswers[question.id];
      const correct = question.correct_answer?.replace(/^Option \d+:\s*/i, '');
      return total + (answer?.toLowerCase() === correct?.toLowerCase() ? 1 : 0);
    }, 0);
    const passed = score === checkQuiz.length;
    setQuizResult({ score, passed });
    fetch('/api/learn/save_event', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        student_id: studentId, topic: activeSession.title,
        source_type: activeSession.attachments.length ? 'uploaded_document' : 'freeform',
        document_name: activeSession.attachments[0]?.display_name || null,
        mode: 'learn', status: passed ? 'LEARNED' : 'EXPOSED',
      }),
    });
    onRefreshProfile?.();
  };

  const filteredSessions = sessions.filter((session) =>
    `${session.title} ${session.description}`.toLowerCase().includes(sessionSearch.toLowerCase())
  );

  return (
    <div className="learn-workspace">
      <aside className={`chat-sidebar ${sidebarOpen ? 'is-open' : ''}`}>
        <div className="chat-sidebar__header">
          <div><span>Learning workspace</span><strong>Your chats</strong></div>
          <div className="chat-sidebar__tools">
            <button className="icon-button" onClick={openSettings} title="Learn settings" aria-label="Open Learn settings"><Settings2 size={17} /></button>
            <button className="icon-button mobile-sidebar-close" onClick={() => setSidebarOpen(false)} aria-label="Close sidebar"><X size={18} /></button>
          </div>
        </div>
        <button className="new-chat-button" onClick={() => setShowCreate(true)}><Plus size={17} /> New chat</button>
        <label className="chat-search"><Search size={15} /><input value={sessionSearch} onChange={(event) => setSessionSearch(event.target.value)} placeholder="Search chats" /></label>
        <div className="session-list">
          {loadingSessions ? <div className="sidebar-status"><Loader2 className="spin" size={18} /> <span className="skeleton-shimmer-text">Loading chats…</span></div> : filteredSessions.length ? filteredSessions.map((session) => (
            <button key={session.id} className={`session-item ${activeSession?.id === session.id ? 'is-active' : ''}`} onClick={() => openSession(session.id)}>
              <span className="session-item__icon"><MessageSquare size={16} /></span>
              <span className="session-item__copy"><strong>{session.title}</strong><small>{session.description}</small><em><Clock3 size={11} /> {formatDate(session.updated_at)}{session.attachment_count > 0 && <> · {session.attachment_count} file{session.attachment_count > 1 ? 's' : ''}</>}</em></span>
              <span className="session-item__delete" onClick={(e) => deleteSession(session.id, e)} title="Delete chat" aria-label="Delete chat"><Trash2 size={13} /></span>
            </button>
          )) : <div className="sidebar-empty">No chats yet.<br />Create one to begin learning.</div>}
        </div>
        <div className="sidebar-storage"><CheckCircle2 size={14} /><span><strong>Saved locally</strong><small>Chats and files stay on this device</small></span></div>
      </aside>

      <section className="chat-panel">
        {error && <div className="chat-error"><span>{error}</span><button onClick={() => setError('')}><X size={15} /></button></div>}
        {openingSession ? (
          <div className="chat-loading"><Loader2 className="spin" size={24} /> <span className="skeleton-shimmer-text">Opening chat…</span></div>
        ) : !activeSession ? (
          <div className="chat-zero-state">
            <span className="zero-state-icon"><BookOpen size={30} /></span>
            <span>Persistent learning chats</span>
            <h2>What would you like to learn?</h2>
            <p>Create a lesson workspace. Your conversation and uploaded course files will be here when you return.</p>
            <button className="btn-primary" onClick={() => setShowCreate(true)}><Plus size={17} /> Create your first chat</button>
          </div>
        ) : (
          <>
            <header className="chat-header">
              <button className="icon-button sidebar-toggle" onClick={() => setSidebarOpen(true)} aria-label="Show chats"><ArrowLeft size={18} /></button>
              <div className="chat-heading"><span>Lesson</span><h2>{activeSession.title}</h2><p>{activeSession.description}</p></div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <button className="icon-button learn-header-settings" onClick={openSettings} title="Learn settings" aria-label="Open Learn settings"><Settings2 size={17} /></button>
                <button className="knowledge-button" onClick={checkUnderstanding} disabled={sending}><Sparkles size={16} /><span>Check understanding</span></button>
                <button className="icon-button chat-delete-button" onClick={(e) => deleteSession(activeSession.id, e)} title="Delete this chat" aria-label="Delete this chat"><Trash2 size={16} /></button>
              </div>
            </header>

            {activeSession.attachments.length > 0 && (
              <div className="attachment-bar"><span className="attachment-bar__label">Sources</span>{activeSession.attachments.map((attachment) => (
                <a className="attachment-chip" key={attachment.id} href={attachment.download_url} target="_blank" rel="noreferrer"><FileText size={15} /><span><strong>{attachment.display_name}</strong><small>{fileSize(attachment.size)}</small></span></a>
              ))}</div>
            )}

            <div className="message-stream">
              {activeSession.messages.length === 0 && (
                <div className="lesson-welcome"><span><Sparkles size={20} /></span><div><strong>Ready to explore {activeSession.title}</strong><p>Ask a question below, or attach a PDF so the tutor can answer from your own material.</p></div></div>
              )}
              {activeSession.messages.map((message) => (
                <div className={`message-row message-row--${message.sender}`} key={message.id}>
                  {message.sender === 'tutor' && <span className="tutor-avatar"><Sparkles size={15} /></span>}
                  <div className="message-bubble">
                    {message.is_grounded && <span className="grounded-label"><FileText size={12} /> Answered from your sources</span>}
                    {message.sender === 'tutor' && message.content_type === 'flashcards' ? (
                      <FlashcardDeck data={message.content_data} />
                    ) : message.sender === 'tutor' && message.content_type === 'video' ? (
                      <AnimatedLesson data={message.content_data} />
                    ) : message.sender === 'tutor' ? (
                      <ProgressiveMessageText
                        text={message.text}
                        isNew={message.id === streamingMessageId}
                        onProgress={() => messageEndRef.current?.scrollIntoView({ behavior: 'smooth' })}
                      />
                    ) : (
                      <div className="message-text">
                        <FormattedText content={message.text} />
                      </div>
                    )}
                    <time>{formatDate(message.created_at)}</time>
                  </div>
                </div>
              ))}
              {sending && (
                <div className="message-row message-row--tutor">
                  <span className="tutor-avatar"><Sparkles size={15} /></span>
                  <ThinkingIndicator mode={responseMode} />
                </div>
              )}
              <div ref={messageEndRef} />
            </div>

            <div className="composer-wrap">
              <div className="response-mode-picker" aria-label="Response format">
                <span>Respond with</span>
                <button type="button" className={responseMode === 'text' ? 'is-active' : ''} onClick={() => setResponseMode('text')}><Type size={14} /> Text</button>
                <button type="button" className={responseMode === 'flashcards' ? 'is-active' : ''} onClick={() => setResponseMode('flashcards')}><Layers size={14} /> Flashcards</button>
                <button type="button" className={responseMode === 'video' ? 'is-active' : ''} onClick={() => setResponseMode('video')}><Play size={14} /> Animated video</button>
              </div>
              <form className="chat-composer" onSubmit={sendMessage}>
                <input ref={fileInputRef} type="file" accept=".pdf,.txt" onChange={uploadFile} hidden />
                <button type="button" className="composer-tool" onClick={() => fileInputRef.current?.click()} disabled={uploading} aria-label="Attach PDF or text file">{uploading ? <Loader2 className="spin" size={19} /> : <Paperclip size={19} />}</button>
                <textarea rows="1" value={inputMsg} onChange={(event) => setInputMsg(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); sendMessage(); } }} placeholder={`Message your ${activeSession.title} tutor…`} />
                <button className="composer-send" type="submit" disabled={!inputMsg.trim() || sending} aria-label="Send message"><Send size={18} /></button>
              </form>
              <p>Choose a response format, then ask your question. Enter to send · Shift + Enter for a new line.</p>
            </div>

            {checkQuiz && (
              <div className="quiz-overlay" role="dialog" aria-modal="true" aria-label="Knowledge check">
                <div className="quiz-dialog">
                  <div className="quiz-dialog__header"><div><span>Knowledge check</span><h3>{activeSession.title}</h3></div><button className="icon-button" onClick={() => setCheckQuiz(null)}><X size={18} /></button></div>
                  {checkQuiz.map((question, index) => (
                    <div className="quiz-question" key={question.id}><strong>{index + 1}. {question.question}</strong>{question.options.map((option) => <label key={option}><input type="radio" name={question.id} checked={userAnswers[question.id] === option} onChange={() => setUserAnswers((previous) => ({ ...previous, [question.id]: option }))} /><span>{option}</span></label>)}</div>
                  ))}
                  {quizResult ? <div className={`quiz-result ${quizResult.passed ? 'is-passed' : ''}`}><CheckCircle2 size={18} /><span><strong>{quizResult.score}/{checkQuiz.length} correct</strong>{quizResult.passed ? 'Excellent—this lesson is looking strong.' : 'Keep going. Ask the tutor to revisit the questions you missed.'}</span></div> : <button className="btn-primary" onClick={submitQuiz}>Submit answers</button>}
                </div>
              </div>
            )}
          </>
        )}
      </section>

      {showSettings && <LearnSettingsDialog draft={settingsDraft} setDraft={setSettingsDraft} onClose={() => setShowSettings(false)} onSave={saveSettings} onReset={resetSettings} />}

      {showCreate && (
        <div className="create-chat-overlay" role="dialog" aria-modal="true" aria-labelledby="create-chat-title">
          <form className="create-chat-dialog" onSubmit={createSession}>
            <button type="button" className="icon-button create-chat-close" onClick={() => setShowCreate(false)}><X size={18} /></button>
            <span className="create-chat-icon"><BookOpen size={23} /></span>
            <span className="create-chat-eyebrow">New learning chat</span>
            <h2 id="create-chat-title">What are you going to learn?</h2>
            <p>Set a clear focus now. You can add course material once the chat is created.</p>
            <label><span>Lesson or topic</span><input autoFocus maxLength="120" value={newLesson.title} onChange={(event) => setNewLesson((previous) => ({ ...previous, title: event.target.value }))} placeholder="e.g. Introduction to thermodynamics" required /></label>
            <label><span>Short description</span><textarea rows="3" maxLength="500" value={newLesson.description} onChange={(event) => setNewLesson((previous) => ({ ...previous, description: event.target.value }))} placeholder="What do you want to understand or accomplish?" required /></label>
            <div className="create-chat-actions"><button type="button" className="btn-secondary" onClick={() => setShowCreate(false)}>Cancel</button><button className="btn-primary" disabled={creating || !newLesson.title.trim() || !newLesson.description.trim()}>{creating ? <><Loader2 className="spin" size={16} /> Creating…</> : <>Create chat <Plus size={16} /></>}</button></div>
          </form>
        </div>
      )}
    </div>
  );
}
