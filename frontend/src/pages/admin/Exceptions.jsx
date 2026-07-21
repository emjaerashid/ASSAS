import { useState, useEffect } from 'react';
import api from '../../utils/api';

export default function Exceptions() {
  const [exceptions, setExceptions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('pending');
  const [actionLoading, setActionLoading] = useState(null);
  const [editingId, setEditingId] = useState(null);

  const fetchExceptions = () => {
    setLoading(true);
    const query = filter ? `?status=${filter}` : '';
    api.get(`/admin/exceptions/${query}`)
      .then(setExceptions)
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(fetchExceptions, [filter]);

  const handleResolve = async (id, status, semester) => {
    setActionLoading(id);
    try {
      await api.put(`/admin/exceptions/${id}/resolve/`, { status, semester });
      setEditingId(null);
      fetchExceptions();
    } catch (err) {
      alert(err.message);
    } finally {
      setActionLoading(null);
    }
  };

  const handleUndo = async (id) => {
    if (!confirm('Undo this decision and return the exception to pending?')) return;
    setActionLoading(id);
    try {
      await api.post(`/admin/exceptions/${id}/undo/`, {});
      setEditingId(null);
      fetchExceptions();
    } catch (err) {
      alert(err.message);
    } finally {
      setActionLoading(null);
    }
  };

  const reasonLabel = (reason) => reason.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

  return (
    <div>
      <div className="page-header">
        <h1>Exception Management</h1>
        <p>Review and resolve flagged exceptions from the rule engine</p>
      </div>

      <div className="mb-16 btn-group">
        {['pending', 'approved', 'rejected', ''].map((f) => (
          <button
            key={f}
            className={`btn btn-sm ${filter === f ? 'btn-primary' : 'btn-outline'}`}
            onClick={() => setFilter(f)}
          >
            {f || 'All'}
          </button>
        ))}
      </div>

      <div className="card">
        <div className="table-container">
          {loading ? (
            <div className="loading-screen">Loading exceptions...</div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Student</th>
                  <th>Subject</th>
                  <th>Reason</th>
                  <th>Details</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {exceptions.map((ex) => (
                  <tr key={ex.id}>
                    <td>
                      <strong>{ex.student_id_display}</strong>
                      <br /><span style={{ fontSize: '12px', color: 'var(--gray-500)' }}>{ex.student_name}</span>
                    </td>
                    <td>
                      <strong>{ex.subject.subject_code}</strong>
                      <br /><span style={{ fontSize: '12px', color: 'var(--gray-500)' }}>{ex.subject.subject_name}</span>
                    </td>
                    <td><span className="badge badge-yellow">{reasonLabel(ex.reason)}</span></td>
                    <td style={{ fontSize: '13px', maxWidth: '250px' }}>{ex.details}</td>
                    <td>
                      {ex.status === 'pending' && <span className="badge badge-yellow">Pending</span>}
                      {ex.status === 'approved' && <span className="badge badge-green">Approved</span>}
                      {ex.status === 'rejected' && <span className="badge badge-red">Rejected</span>}
                    </td>
                    <td>
                      {(ex.status === 'pending' || editingId === ex.id) ? (
                        <div className="btn-group">
                          <button
                            className="btn btn-success btn-sm"
                            disabled={actionLoading === ex.id}
                            onClick={() => handleResolve(ex.id, 'approved', '202601')}
                          >
                            Approve
                          </button>
                          <button
                            className="btn btn-danger btn-sm"
                            disabled={actionLoading === ex.id}
                            onClick={() => handleResolve(ex.id, 'rejected')}
                          >
                            Reject
                          </button>
                          {editingId === ex.id && (
                            <button className="btn btn-outline btn-sm" disabled={actionLoading === ex.id}
                              onClick={() => setEditingId(null)}>Cancel</button>
                          )}
                        </div>
                      ) : (
                        <div className="btn-group">
                          <button className="btn btn-secondary btn-sm" disabled={actionLoading === ex.id}
                            onClick={() => setEditingId(ex.id)}>Edit</button>
                          <button className="btn btn-outline btn-sm" disabled={actionLoading === ex.id}
                            onClick={() => handleUndo(ex.id)}>Undo</button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
                {exceptions.length === 0 && (
                  <tr><td colSpan="6" className="empty-state">No exceptions found</td></tr>
                )}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
