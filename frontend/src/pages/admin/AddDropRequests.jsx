import { useState, useEffect } from 'react';
import api from '../../utils/api';

export default function AddDropRequests() {
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('pending');
  const [actionLoading, setActionLoading] = useState(null);
  const [remarks, setRemarks] = useState({});

  const fetchRequests = () => {
    setLoading(true);
    const query = filter ? `?status=${filter}` : '';
    api.get(`/admin/add-drop-requests/${query}`)
      .then(setRequests)
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(fetchRequests, [filter]);

  const handleResolve = async (id, status) => {
    setActionLoading(id);
    try {
      await api.put(`/admin/add-drop-requests/${id}/resolve/`, {
        status,
        admin_remarks: remarks[id] || '',
      });
      fetchRequests();
    } catch (err) {
      alert(err.message);
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div>
      <div className="page-header">
        <h1>Add/Drop Requests</h1>
        <p>Review student requests to add or drop subjects</p>
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
            <div className="loading-screen">Loading requests...</div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Student</th>
                  <th>Action</th>
                  <th>Subject</th>
                  <th>Reason</th>
                  <th>Semester</th>
                  <th>Status</th>
                  <th>Admin Remarks / Actions</th>
                </tr>
              </thead>
              <tbody>
                {requests.map((req) => (
                  <tr key={req.id}>
                    <td>
                      <strong>{req.student_id_display}</strong>
                      <br /><span style={{ fontSize: '12px', color: 'var(--gray-500)' }}>{req.student_name}</span>
                    </td>
                    <td>
                      <span className={`badge ${req.action === 'add' ? 'badge-green' : 'badge-red'}`}>
                        {req.action.toUpperCase()}
                      </span>
                    </td>
                    <td>
                      <strong>{req.subject.subject_code}</strong>
                      <br /><span style={{ fontSize: '12px', color: 'var(--gray-500)' }}>{req.subject.subject_name}</span>
                    </td>
                    <td style={{ fontSize: '13px', maxWidth: '200px' }}>{req.reason}</td>
                    <td>{req.semester}</td>
                    <td>
                      {req.status === 'pending' && <span className="badge badge-yellow">Pending</span>}
                      {req.status === 'approved' && <span className="badge badge-green">Approved</span>}
                      {req.status === 'rejected' && <span className="badge badge-red">Rejected</span>}
                    </td>
                    <td>
                      {req.status === 'pending' ? (
                        <div>
                          <input
                            className="form-control mb-16"
                            placeholder="Admin remarks (optional)"
                            value={remarks[req.id] || ''}
                            onChange={(e) => setRemarks({ ...remarks, [req.id]: e.target.value })}
                            style={{ fontSize: '12px', marginBottom: '6px' }}
                          />
                          <div className="btn-group">
                            <button className="btn btn-success btn-sm" disabled={actionLoading === req.id}
                              onClick={() => handleResolve(req.id, 'approved')}>Approve</button>
                            <button className="btn btn-danger btn-sm" disabled={actionLoading === req.id}
                              onClick={() => handleResolve(req.id, 'rejected')}>Reject</button>
                          </div>
                        </div>
                      ) : (
                        <span style={{ fontSize: '13px', color: 'var(--gray-500)' }}>{req.admin_remarks || '—'}</span>
                      )}
                    </td>
                  </tr>
                ))}
                {requests.length === 0 && (
                  <tr><td colSpan="7" className="empty-state">No requests found</td></tr>
                )}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
