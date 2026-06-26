import { useState, useEffect } from 'react';
import api from '../../utils/api';

export default function AddDrop() {
  const [requests, setRequests] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ subject_code: '', action: 'add', reason: '', semester: '202601' });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const fetchData = () => {
    setLoading(true);
    Promise.all([
      api.get('/student/add-drop/history/'),
      api.get('/subjects/?programme=BCSSE'),
    ])
      .then(([reqs, subs]) => {
        setRequests(reqs);
        setSubjects(subs);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(fetchData, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSubmitting(true);

    try {
      await api.post('/student/add-drop/', form);
      setSuccess('Request submitted successfully!');
      setShowForm(false);
      setForm({ subject_code: '', action: 'add', reason: '', semester: '202601' });
      fetchData();
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      <div className="page-header flex-between">
        <div>
          <h1>Add/Drop Request</h1>
          <p>Submit requests to add or drop subjects for admin approval</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>
          {showForm ? 'Cancel' : '+ New Request'}
        </button>
      </div>

      {success && <div className="alert alert-success">{success}</div>}

      {showForm && (
        <div className="card mb-24">
          <div className="card-header"><h3>Submit Request</h3></div>
          <div className="card-body">
            <form onSubmit={handleSubmit}>
              {error && <div className="alert alert-error">{error}</div>}
              <div className="grid-2">
                <div className="form-group">
                  <label>Action</label>
                  <select className="form-control" value={form.action}
                    onChange={(e) => setForm({ ...form, action: e.target.value })}>
                    <option value="add">Add Subject</option>
                    <option value="drop">Drop Subject</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Semester</label>
                  <input className="form-control" value={form.semester}
                    onChange={(e) => setForm({ ...form, semester: e.target.value })} required />
                </div>
              </div>
              <div className="form-group">
                <label>Subject</label>
                <select className="form-control" value={form.subject_code}
                  onChange={(e) => setForm({ ...form, subject_code: e.target.value })} required>
                  <option value="">Select a subject</option>
                  {subjects.map((s) => (
                    <option key={s.subject_code} value={s.subject_code}>
                      {s.subject_code} - {s.subject_name} ({s.credit_hours} cr)
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Reason</label>
                <textarea className="form-control" value={form.reason}
                  onChange={(e) => setForm({ ...form, reason: e.target.value })}
                  placeholder="Explain why you want to add/drop this subject" required />
              </div>
              <button type="submit" className="btn btn-primary" disabled={submitting}>
                {submitting ? 'Submitting...' : 'Submit Request'}
              </button>
            </form>
          </div>
        </div>
      )}

      <div className="card">
        <div className="card-header"><h3>Request History</h3></div>
        <div className="table-container">
          {loading ? (
            <div className="loading-screen">Loading requests...</div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Action</th>
                  <th>Subject</th>
                  <th>Reason</th>
                  <th>Status</th>
                  <th>Admin Remarks</th>
                </tr>
              </thead>
              <tbody>
                {requests.map((r) => (
                  <tr key={r.id}>
                    <td>{new Date(r.created_at).toLocaleDateString()}</td>
                    <td>
                      <span className={`badge ${r.action === 'add' ? 'badge-green' : 'badge-red'}`}>
                        {r.action.toUpperCase()}
                      </span>
                    </td>
                    <td>
                      <strong>{r.subject.subject_code}</strong>
                      <br /><span style={{ fontSize: '12px', color: 'var(--gray-500)' }}>{r.subject.subject_name}</span>
                    </td>
                    <td style={{ fontSize: '13px', maxWidth: '200px' }}>{r.reason}</td>
                    <td>
                      {r.status === 'pending' && <span className="badge badge-yellow">Pending</span>}
                      {r.status === 'approved' && <span className="badge badge-green">Approved</span>}
                      {r.status === 'rejected' && <span className="badge badge-red">Rejected</span>}
                    </td>
                    <td style={{ fontSize: '13px', color: 'var(--gray-500)' }}>{r.admin_remarks || '—'}</td>
                  </tr>
                ))}
                {requests.length === 0 && (
                  <tr><td colSpan="6" className="empty-state">No requests submitted yet</td></tr>
                )}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
