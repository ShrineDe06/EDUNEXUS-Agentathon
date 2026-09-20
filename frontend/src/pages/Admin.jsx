import React, { useEffect, useMemo, useState } from 'react';
import { Activity, AlertTriangle, ArrowDownToLine, BarChart3, BookOpen, ChevronDown, ChevronUp, ClipboardCheck, GraduationCap, LogOut, RefreshCw, Search, ShieldCheck, Sparkles, Users } from 'lucide-react';

const formatDateTime = (value) => {
  if (!value) return 'No activity yet';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' });
};
const csvCell = (value) => `"${String(value ?? '').replaceAll('"', '""')}"`;

export default function Admin({ account, onLogout }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');
  const [standing, setStanding] = useState('all');
  const [expandedId, setExpandedId] = useState(null);

  const loadOverview = async (quiet = false) => {
    quiet ? setRefreshing(true) : setLoading(true);
    setError('');
    try {
      const response = await fetch('/api/admin/overview');
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || 'Could not load student analytics.');
      setData(payload);
    } catch (loadError) {
      setError(loadError.message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => { loadOverview(); }, []);

  const students = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return (data?.students || []).filter((student) => {
      const matchesStanding = standing === 'all' || student.standing === standing;
      const searchable = [student.name, student.username, student.email, student.course_year, ...(student.progress?.topic_names || [])].join(' ').toLowerCase();
      return matchesStanding && (!normalized || searchable.includes(normalized));
    });
  }, [data, query, standing]);

  const exportCsv = () => {
    const headers = ['Username', 'Tester Name', 'Tester Type', 'Course/Year', 'Prior Knowledge', 'Test Number', 'Date', 'Start Time', 'End Time', 'Learning Material Used', 'Topic Selected', 'Concept Being Tested', 'Facilitator', 'Observer', 'Technical Monitor', 'Topics', 'Learn Chats', 'Revisions', 'Tests', 'Average Score', 'Pass Rate', 'Mastered', 'Weak', 'Misconceptions', 'Standing'];
    const rows = students.map((student) => {
      const walk = student.walkthrough;
      const progress = student.progress;
      return [student.username, walk.tester_name, walk.tester_type, walk.course_year, walk.prior_knowledge, walk.test_number, walk.date, walk.start_time, walk.end_time, walk.learning_material, walk.topic_selected, walk.concept_being_tested, walk.facilitator, walk.observer, walk.technical_monitor, progress.topics, progress.chat_sessions, progress.revision_sessions, progress.completed_tests, `${progress.average_score}%`, `${progress.pass_rate}%`, progress.mastered, progress.weak, progress.misconceptions, student.standing];
    });
    const csv = [headers, ...rows].map((row) => row.map(csvCell).join(',')).join('\n');
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `edunexus-students-${new Date().toISOString().slice(0, 10)}.csv`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const summary = data?.summary || {};
  return (
    <div className="admin-shell">
      <header className="admin-topbar">
        <div className="admin-topbar__brand"><span><GraduationCap size={22} /></span><div><strong>EduNexus</strong><small>Top Teacher Console</small></div></div>
        <div className="admin-topbar__account"><span className="admin-role-pill"><ShieldCheck size={14} /> Administrator</span><div><strong>{account.profile?.name || 'Top Teacher'}</strong><small>@{account.username}</small></div><button onClick={onLogout} title="Sign out" aria-label="Sign out"><LogOut size={17} /></button></div>
      </header>

      <main className="admin-main">
        <section className="admin-heading">
          <div><span className="admin-eyebrow"><Activity size={14} /> Live local analytics</span><h1>Student progress command center</h1><p>Review learning activity, assessment performance, mastery signals, and evaluator walkthrough information across every student account.</p></div>
          <button className="admin-refresh" onClick={() => loadOverview(true)} disabled={refreshing}><RefreshCw size={16} className={refreshing ? 'spin' : ''} /> {refreshing ? 'Refreshing…' : 'Refresh data'}</button>
        </section>
        {error && <div className="admin-error"><AlertTriangle size={18} /><span>{error}</span><button onClick={() => loadOverview()}>Try again</button></div>}

        {loading ? <div className="admin-loading"><span className="admin-loading__orb"><BarChart3 size={24} /></span><div className="generation-skeleton"><i /><i /><i /></div><strong>Aggregating student workspaces…</strong></div> : <>
          <section className="admin-metrics" aria-label="Student overview">
            <article><span className="metric-icon metric-icon--cyan"><Users size={19} /></span><div><small>Total students</small><strong>{summary.total_students || 0}</strong><em>{summary.active_students || 0} have started</em></div></article>
            <article><span className="metric-icon metric-icon--violet"><ClipboardCheck size={19} /></span><div><small>Tests completed</small><strong>{summary.tests_completed || 0}</strong><em>{summary.topics_explored || 0} topic journeys</em></div></article>
            <article><span className="metric-icon metric-icon--green"><BarChart3 size={19} /></span><div><small>Cohort average</small><strong>{summary.average_score || 0}%</strong><em>Across completed tests</em></div></article>
            <article><span className="metric-icon metric-icon--rose"><AlertTriangle size={19} /></span><div><small>Needs attention</small><strong>{summary.needs_attention || 0}</strong><em>Students below 60%</em></div></article>
          </section>

          <section className="admin-table-card">
            <div className="admin-table-heading"><div><span><Sparkles size={15} /> Student data register</span><h2>All student records</h2><p>One row per student. Scroll horizontally for the complete evaluator walkthrough.</p></div><button onClick={exportCsv} disabled={!students.length}><ArrowDownToLine size={16} /> Export CSV</button></div>
            <div className="admin-table-tools"><label><Search size={15} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search name, username, course or topic…" /></label><select value={standing} onChange={(event) => setStanding(event.target.value)} aria-label="Filter by standing"><option value="all">All standings</option><option>Excelling</option><option>On track</option><option>Needs attention</option><option>Not started</option></select><span>{students.length} of {data?.students?.length || 0} students</span></div>
            <div className="admin-table-scroll"><table className="admin-student-table">
              <thead><tr><th className="is-sticky">Student account</th><th>Standing</th><th>Overall progress</th><th>Test number</th><th>Date</th><th>Start time</th><th>End time</th><th>Tester name</th><th>Tester type</th><th>Course / Year</th><th>Prior knowledge</th><th>Learning material used</th><th>Topic selected</th><th>Concept being tested</th><th>Facilitator</th><th>Observer</th><th>Technical monitor</th><th aria-label="Expand row" /></tr></thead>
              <tbody>{students.map((student) => {
                const walk = student.walkthrough; const progress = student.progress; const isExpanded = expandedId === student.id;
                const progressValue = progress.completed_tests ? progress.average_score : Math.min(100, progress.topics * 20);
                return <React.Fragment key={student.id}>
                  <tr className={isExpanded ? 'is-expanded' : ''}>
                    <td className="is-sticky"><div className="student-identity"><span>{student.name.slice(0, 1).toUpperCase()}</span><div><strong>{student.name}</strong><small>@{student.username}</small></div></div></td>
                    <td><span className={`standing-badge standing-badge--${student.standing.toLowerCase().replaceAll(' ', '-')}`}>{student.standing}</span></td>
                    <td><div className="table-progress"><span><i style={{ width: `${progressValue}%` }} /></span><small>{progress.completed_tests ? `${progress.average_score}% test average` : `${progress.topics} topics explored`}</small></div></td>
                    <td>{walk.test_number}</td><td>{walk.date}</td><td>{walk.start_time}</td><td>{walk.end_time}</td><td>{walk.tester_name}</td><td>{walk.tester_type}</td><td>{walk.course_year}</td><td>{walk.prior_knowledge}</td><td className="admin-wide-cell">{walk.learning_material}</td><td>{walk.topic_selected}</td><td className="admin-wide-cell">{walk.concept_being_tested}</td><td>{walk.facilitator}</td><td>{walk.observer}</td><td>{walk.technical_monitor}</td>
                    <td><button className="row-expand" onClick={() => setExpandedId(isExpanded ? null : student.id)} aria-label={`${isExpanded ? 'Collapse' : 'Expand'} ${student.name}`}>{isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}</button></td>
                  </tr>
                  {isExpanded && <tr className="student-detail-row"><td colSpan="18"><div className="student-detail-grid">
                    <div className="student-detail-profile"><span><BookOpen size={16} /> Student context</span><strong>{student.course_year}</strong><p>{student.learning_goal || 'No learning goal has been added yet.'}</p><small>Last activity: {formatDateTime(student.last_activity)}</small></div>
                    <div className="student-detail-stats"><div><small>Learn chats</small><strong>{progress.chat_sessions}</strong></div><div><small>Revisions</small><strong>{progress.revision_sessions}</strong></div><div><small>Tests</small><strong>{progress.completed_tests}</strong></div><div><small>Pass rate</small><strong>{progress.pass_rate}%</strong></div><div><small>Mastered</small><strong>{progress.mastered}</strong></div><div><small>Needs work</small><strong>{progress.weak}</strong></div><div><small>Misconceptions</small><strong>{progress.misconceptions}</strong></div><div><small>Scheduled</small><strong>{progress.scheduled}</strong></div></div>
                    <div className="student-topic-list"><span>Topics explored</span><div>{progress.topic_names.length ? progress.topic_names.map((topic) => <em key={topic}>{topic}</em>) : <small>No topics recorded</small>}</div></div>
                  </div></td></tr>}
                </React.Fragment>;
              })}{!students.length && <tr><td colSpan="18"><div className="admin-empty"><Users size={23} /><strong>No matching students</strong><span>Try clearing the search or standing filter.</span></div></td></tr>}</tbody>
            </table></div>
          </section>
        </>}
      </main>
    </div>
  );
}
