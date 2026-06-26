import { useState, useEffect } from 'react';
import api from '../../utils/api';

export default function Progress() {
  const [progress, setProgress] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/student/progress/')
      .then(setProgress)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading-screen">Loading progress...</div>;
  if (!progress) return <div className="loading-screen">Failed to load progress</div>;

  const { student, total_programme_subjects, completed_subjects, total_credits_earned, total_credits_required, progress_percentage } = progress;

  return (
    <div>
      <div className="page-header">
        <h1>Academic Progress</h1>
        <p>Track your programme completion and credit accumulation</p>
      </div>

      <div className="stats-grid">
        <div className="stat-card sky">
          <div className="stat-label">Programme</div>
          <div className="stat-value" style={{ fontSize: '16px' }}>{student.programme.programme_name}</div>
        </div>
        <div className="stat-card sky">
          <div className="stat-label">Current Position</div>
          <div className="stat-value">Y{student.current_year} S{student.current_semester}</div>
        </div>
        <div className="stat-card sky">
          <div className="stat-label">Status</div>
          <div className="stat-value" style={{ fontSize: '18px', textTransform: 'capitalize' }}>{student.status}</div>
        </div>
        <div className="stat-card sky">
          <div className="stat-label">CGPA</div>
          <div className="stat-value">{student.cgpa}</div>
        </div>
      </div>

      <div className="card mb-24">
        <div className="card-header">
          <h3>Credit Progress</h3>
          <span>{total_credits_earned} / {total_credits_required} credits</span>
        </div>
        <div className="card-body">
          <div className="progress-bar-container" style={{ height: '24px', marginBottom: '12px' }}>
            <div className="progress-bar-fill sky" style={{ width: `${Math.min(progress_percentage, 100)}%` }}></div>
          </div>
          <div className="flex-between">
            <span style={{ fontSize: '13px', color: 'var(--gray-500)' }}>
              {progress_percentage}% Complete
            </span>
            <span style={{ fontSize: '13px', color: 'var(--gray-500)' }}>
              {total_credits_required - total_credits_earned} credits remaining
            </span>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h3>Subject Completion</h3>
          <span>{completed_subjects} / {total_programme_subjects} subjects passed</span>
        </div>
        <div className="card-body">
          <div className="progress-bar-container" style={{ height: '24px', marginBottom: '12px' }}>
            <div className="progress-bar-fill red"
              style={{ width: `${total_programme_subjects > 0 ? (completed_subjects / total_programme_subjects * 100) : 0}%` }}>
            </div>
          </div>
          <div className="flex-between">
            <span style={{ fontSize: '13px', color: 'var(--gray-500)' }}>
              {total_programme_subjects > 0 ? Math.round(completed_subjects / total_programme_subjects * 100) : 0}% Complete
            </span>
            <span style={{ fontSize: '13px', color: 'var(--gray-500)' }}>
              {total_programme_subjects - completed_subjects} subjects remaining
            </span>
          </div>
        </div>
      </div>

      <div className="card" style={{ marginTop: '24px' }}>
        <div className="card-header">
          <h3>Profile Details</h3>
        </div>
        <div className="card-body">
          <table>
            <tbody>
              <tr><td><strong>Student ID</strong></td><td>{student.user.student_id}</td></tr>
              <tr><td><strong>Full Name</strong></td><td>{student.user.full_name}</td></tr>
              <tr><td><strong>Programme Code</strong></td><td>{student.programme.programme_code}</td></tr>
              <tr><td><strong>Max Credits/Semester</strong></td><td>{student.effective_credit_cap}</td></tr>
              <tr><td><strong>Repeat Student</strong></td><td>{student.is_repeat ? 'Yes' : 'No'}</td></tr>
              <tr><td><strong>Transfer Student</strong></td><td>{student.is_transfer ? 'Yes' : 'No'}</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
