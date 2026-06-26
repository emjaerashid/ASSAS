import { useState, useEffect } from 'react';
import api from '../../utils/api';

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/admin/dashboard/')
      .then(setStats)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading-screen">Loading dashboard...</div>;

  return (
    <div>
      <div className="page-header">
        <h1>Admin Dashboard</h1>
        <p>Overview of the Automated Subject Assignment System</p>
      </div>

      <div className="stats-grid">
        <div className="stat-card sky">
          <div className="stat-label">Total Students</div>
          <div className="stat-value">{stats?.total_students || 0}</div>
        </div>
        <div className="stat-card sky">
          <div className="stat-label">Active Students</div>
          <div className="stat-value">{stats?.active_students || 0}</div>
        </div>
        <div className="stat-card red">
          <div className="stat-label">On Probation</div>
          <div className="stat-value">{stats?.probation_students || 0}</div>
        </div>
        <div className="stat-card sky">
          <div className="stat-label">Total Subjects</div>
          <div className="stat-value">{stats?.total_subjects || 0}</div>
        </div>
        <div className="stat-card red">
          <div className="stat-label">Pending Exceptions</div>
          <div className="stat-value">{stats?.pending_exceptions || 0}</div>
        </div>
        <div className="stat-card red">
          <div className="stat-label">Pending Add/Drop</div>
          <div className="stat-value">{stats?.pending_add_drop || 0}</div>
        </div>
      </div>
    </div>
  );
}
