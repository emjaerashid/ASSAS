import { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import api from '../../utils/api';

export default function MySubjects() {
  const { user } = useAuth();
  const [allEnrolments, setAllEnrolments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [currentSemester, setCurrentSemester] = useState('');
  const [selectedPrevious, setSelectedPrevious] = useState('');

  useEffect(() => {
    api.get('/student/subjects/')
      .then((data) => {
        setAllEnrolments(data);
        // The current semester is the most recent one with active
        // (assigned/in_progress) subjects, so the page opens on "this semester"
        // rather than full history.
        const active = data.filter((e) => e.status === 'assigned' || e.status === 'in_progress');
        const pool = active.length ? active : data;
        const current = pool.reduce((latest, e) => (e.semester > latest ? e.semester : latest), '');
        setCurrentSemester(current);

        const previous = [...new Set(data.map((e) => e.semester))]
          .filter((s) => s !== current)
          .sort()
          .reverse();
        setSelectedPrevious(previous[0] || '');
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const statusBadge = (status) => {
    const map = {
      assigned: 'badge-green',
      passed: 'badge-green',
      failed: 'badge-red',
      dropped: 'badge-red',
      in_progress: 'badge-yellow',
    };
    return <span className={`badge ${map[status] || 'badge-gray'}`}>{status}</span>;
  };

  const currentEnrolments = allEnrolments.filter((e) => e.semester === currentSemester);
  const currentActive = currentEnrolments.filter(e => e.status === 'assigned' || e.status === 'in_progress');
  const currentCredits = currentActive.reduce((sum, e) => sum + e.subject.credit_hours, 0);
  const repeatCount = currentEnrolments.filter(e => e.is_repeat).length;

  const previousSemesters = [...new Set(allEnrolments.map((e) => e.semester))]
    .filter((s) => s !== currentSemester)
    .sort()
    .reverse();

  const creditCap = user?.student_profile?.effective_credit_cap;
  const creditPct = creditCap ? Math.min(100, Math.round((currentCredits / creditCap) * 100)) : 0;

  const renderTable = (enrolments) => (
    <div className="table-container">
      <table>
        <thead>
          <tr>
            <th>Code</th>
            <th>Subject Name</th>
            <th>Credits</th>
            <th>Status</th>
            <th>Repeat</th>
          </tr>
        </thead>
        <tbody>
          {enrolments.map((e) => (
            <tr key={e.id}>
              <td><strong className="mono">{e.subject.subject_code}</strong></td>
              <td>{e.subject.subject_name}</td>
              <td className="mono">{e.subject.credit_hours}</td>
              <td>{statusBadge(e.status)}</td>
              <td>{e.is_repeat ? <span className="badge badge-yellow">Yes</span> : '—'}</td>
            </tr>
          ))}
          {enrolments.length === 0 && (
            <tr><td colSpan="5" className="empty-state">No subjects assigned yet</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );

  return (
    <div>
      <div className="page-header">
        <h1>My Assigned Subjects</h1>
        <p>Welcome, {user?.full_name}{currentSemester ? ` · Semester ${currentSemester}` : ''}</p>
      </div>

      <div className="stats-grid">
        <div className="stat-card sky">
          <div className="stat-card-head">
            <div className="stat-label">Current Semester Subjects</div>
            <div className="stat-icon sky"><span className="material-symbols-outlined">assignment</span></div>
          </div>
          <div className="stat-value-row"><div className="stat-value">{currentActive.length}</div></div>
        </div>
        <div className="stat-card sky">
          <div className="stat-card-head">
            <div className="stat-label">Current Semester Credits</div>
            <div className="stat-icon sky"><span className="material-symbols-outlined">donut_small</span></div>
          </div>
          <div className="stat-value-row">
            <div className="stat-value">{currentCredits}</div>
            {creditCap && <div className="stat-sub">/ {creditCap} cap</div>}
          </div>
          {creditCap && (
            <div className="progress-bar-container">
              <div className="progress-bar-fill sky" style={{ width: `${creditPct}%` }} />
            </div>
          )}
        </div>
        <div className={`stat-card ${repeatCount > 0 ? 'red' : 'sky'}`}>
          <div className="stat-card-head">
            <div className="stat-label">Repeat Subjects</div>
            <div className={`stat-icon ${repeatCount > 0 ? 'red' : 'sky'}`}><span className="material-symbols-outlined">replay</span></div>
          </div>
          <div className="stat-value-row"><div className="stat-value">{repeatCount}</div></div>
        </div>
      </div>

      <div className="card mb-24">
        <div className="card-header">
          <h3>Current Semester</h3>
          {currentSemester && <span className="badge badge-blue">{currentSemester}</span>}
        </div>
        {loading ? (
          <div className="loading-screen">Loading subjects...</div>
        ) : renderTable(currentEnrolments)}
      </div>

      {!loading && previousSemesters.length > 0 && (() => {
        const semEnrolments = allEnrolments.filter((e) => e.semester === selectedPrevious);
        const semCredits = semEnrolments
          .filter((e) => e.status === 'passed')
          .reduce((sum, e) => sum + e.subject.credit_hours, 0);
        const repeats = semEnrolments.filter((e) => e.is_repeat);

        return (
          <div>
            <h3 className="mb-16">Previous Semesters</h3>
            <div className="card">
              <div className="tab-row">
                {previousSemesters.map((s) => (
                  <button
                    key={s}
                    className={`tab-item${s === selectedPrevious ? ' active' : ''}`}
                    onClick={() => setSelectedPrevious(s)}
                  >
                    {s}
                  </button>
                ))}
              </div>
              <div className="card-header">
                <h3>{selectedPrevious}</h3>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <span className="badge badge-blue">{semEnrolments.length} subject(s)</span>
                  <span className="badge badge-green">{semCredits} credits</span>
                  {repeats.length > 0 && (
                    <span className="badge badge-yellow">{repeats.length} repeat(s)</span>
                  )}
                </div>
              </div>
              {renderTable(semEnrolments)}
            </div>
          </div>
        );
      })()}
    </div>
  );
}
