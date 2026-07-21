import { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import api from '../../utils/api';

export default function MySubjects() {
  const { user } = useAuth();
  const [allEnrolments, setAllEnrolments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [semesterFilter, setSemesterFilter] = useState('');

  useEffect(() => {
    api.get('/student/subjects/')
      .then((data) => {
        setAllEnrolments(data);
        // Default to the most recent semester with active (assigned/in_progress)
        // subjects, so the page opens on "this semester" rather than full history.
        const active = data.filter((e) => e.status === 'assigned' || e.status === 'in_progress');
        const pool = active.length ? active : data;
        const current = pool.reduce((latest, e) => (e.semester > latest ? e.semester : latest), '');
        setSemesterFilter(current);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const semesters = [...new Set(allEnrolments.map((e) => e.semester))].sort();
  const enrolments = semesterFilter ? allEnrolments.filter((e) => e.semester === semesterFilter) : allEnrolments;

  const statusBadge = (status) => {
    const map = {
      assigned: 'badge-blue',
      passed: 'badge-green',
      failed: 'badge-red',
      dropped: 'badge-gray',
      in_progress: 'badge-yellow',
    };
    return <span className={`badge ${map[status] || 'badge-gray'}`}>{status}</span>;
  };

  const totalCredits = enrolments
    .filter(e => e.status === 'assigned' || e.status === 'in_progress')
    .reduce((sum, e) => sum + e.subject.credit_hours, 0);

  return (
    <div>
      <div className="page-header">
        <h1>My Assigned Subjects</h1>
        <p>Welcome, {user?.full_name}</p>
      </div>

      <div className="stats-grid">
        <div className="stat-card sky">
          <div className="stat-label">Current Semester Subjects</div>
          <div className="stat-value">
            {enrolments.filter(e => e.status === 'assigned' || e.status === 'in_progress').length}
          </div>
        </div>
        <div className="stat-card sky">
          <div className="stat-label">Current Semester Credits</div>
          <div className="stat-value">{totalCredits}</div>
        </div>
        <div className="stat-card red">
          <div className="stat-label">Repeat Subjects</div>
          <div className="stat-value">{enrolments.filter(e => e.is_repeat).length}</div>
        </div>
      </div>

      <div className="mb-16">
        <select className="form-control" style={{ width: '200px' }} value={semesterFilter}
          onChange={(e) => setSemesterFilter(e.target.value)}>
          <option value="">All Semesters</option>
          {semesters.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>

      <div className="card">
        <div className="table-container">
          {loading ? (
            <div className="loading-screen">Loading subjects...</div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Code</th>
                  <th>Subject Name</th>
                  <th>Credits</th>
                  <th>Semester</th>
                  <th>Status</th>
                  <th>Grade</th>
                  <th>Repeat</th>
                </tr>
              </thead>
              <tbody>
                {enrolments.map((e) => (
                  <tr key={e.id}>
                    <td><strong>{e.subject.subject_code}</strong></td>
                    <td>{e.subject.subject_name}</td>
                    <td>{e.subject.credit_hours}</td>
                    <td>{e.semester}</td>
                    <td>{statusBadge(e.status)}</td>
                    <td>{e.grade || '—'}</td>
                    <td>{e.is_repeat ? <span className="badge badge-yellow">Yes</span> : '—'}</td>
                  </tr>
                ))}
                {enrolments.length === 0 && (
                  <tr><td colSpan="7" className="empty-state">No subjects assigned yet</td></tr>
                )}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
