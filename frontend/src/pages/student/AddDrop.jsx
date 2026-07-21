import { useState, useEffect } from 'react';
import api from '../../utils/api';
import { useAuth } from '../../context/AuthContext';

export default function AddDrop() {
  const { user } = useAuth();
  const [requests, setRequests] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [enrolments, setEnrolments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ subject_code: '', action: 'add', reason: '', semester: '202601' });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [editingId, setEditingId] = useState(null);
  const [actionLoading, setActionLoading] = useState(null);

  const programmeCode = user?.student_profile?.programme?.programme_code;

  const fetchData = () => {
    if (!programmeCode) return;
    setLoading(true);
    Promise.all([
      api.get('/student/add-drop/history/'),
      api.get(`/subjects/?programme=${programmeCode}`),
      api.get('/student/subjects/'),
    ])
      .then(([reqs, subs, enrolled]) => {
        setRequests(reqs);
        setSubjects(subs);
        setEnrolments(enrolled);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(fetchData, [programmeCode]);

  const completedCodes = new Set(
    enrolments.filter((e) => e.status === 'passed').map((e) => e.subject.subject_code)
  );
  const assignedCodesForSemester = new Set(
    enrolments
      .filter((e) => e.semester === form.semester && ['assigned', 'in_progress'].includes(e.status))
      .map((e) => e.subject.subject_code)
  );
  const subjectOptions = form.action === 'drop'
    ? subjects.filter((s) => assignedCodesForSemester.has(s.subject_code))
    : subjects.filter((s) => !assignedCodesForSemester.has(s.subject_code) && !completedCodes.has(s.subject_code));

  const resetForm = () => {
    setForm({ subject_code: '', action: 'add', reason: '', semester: '202601' });
    setEditingId(null);
    setShowForm(false);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSubmitting(true);

    try {
      if (editingId) {
        await api.put(`/student/add-drop/${editingId}/`, form);
        setSuccess('Request updated successfully!');
      } else {
        await api.post('/student/add-drop/', form);
        setSuccess('Request submitted successfully!');
      }
      resetForm();
      fetchData();
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const startEditing = (req) => {
    setForm({
      subject_code: req.subject.subject_code,
      action: req.action,
      reason: req.reason,
      semester: req.semester,
    });
    setEditingId(req.id);
    setShowForm(true);
  };

  const handleWithdraw = async (id) => {
    if (!confirm('Withdraw this request?')) return;
    setActionLoading(id);
    try {
      await api.post(`/student/add-drop/${id}/withdraw/`, {});
      fetchData();
    } catch (err) {
      alert(err.message);
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div>
      <div className="page-header flex-between">
        <div>
          <h1>Add/Drop Request</h1>
          <p>Submit requests to add or drop subjects for admin approval</p>
        </div>
        <button className="btn btn-primary" onClick={() => (showForm ? resetForm() : setShowForm(true))}>
          {showForm ? 'Cancel' : '+ New Request'}
        </button>
      </div>

      {success && <div className="alert alert-success">{success}</div>}

      {showForm && (
        <div className="card mb-24">
          <div className="card-header"><h3>{editingId ? 'Edit Request' : 'Submit Request'}</h3></div>
          <div className="card-body">
            <form onSubmit={handleSubmit}>
              {error && <div className="alert alert-error">{error}</div>}
              <div className="grid-2">
                <div className="form-group">
                  <label>Action</label>
                  <select className="form-control" value={form.action}
                    onChange={(e) => setForm({ ...form, action: e.target.value, subject_code: '' })}>
                    <option value="add">Add Subject</option>
                    <option value="drop">Drop Subject</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Semester</label>
                  <input className="form-control" value={form.semester}
                    onChange={(e) => setForm({ ...form, semester: e.target.value, subject_code: '' })} required />
                </div>
              </div>
              <div className="form-group">
                <label>Subject</label>
                <select className="form-control" value={form.subject_code}
                  onChange={(e) => setForm({ ...form, subject_code: e.target.value })} required>
                  <option value="">Select a subject</option>
                  {subjectOptions.map((s) => (
                    <option key={s.subject_code} value={s.subject_code}>
                      {s.subject_code} - {s.subject_name} ({s.credit_hours} cr)
                    </option>
                  ))}
                </select>
                {subjectOptions.length === 0 && (
                  <p style={{ fontSize: '12px', color: 'var(--gray-500)', marginTop: '4px' }}>
                    {form.action === 'drop'
                      ? 'No subjects are currently assigned to you for this semester.'
                      : 'No eligible subjects to add for this semester (already assigned or completed).'}
                  </p>
                )}
              </div>
              <div className="form-group">
                <label>Reason</label>
                <textarea className="form-control" value={form.reason}
                  onChange={(e) => setForm({ ...form, reason: e.target.value })}
                  placeholder="Explain why you want to add/drop this subject" required />
              </div>
              <button type="submit" className="btn btn-primary" disabled={submitting}>
                {submitting ? 'Saving...' : editingId ? 'Save Changes' : 'Submit Request'}
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
                  <th>Actions</th>
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
                    <td>
                      {r.status === 'pending' && (
                        <div className="btn-group">
                          <button className="btn btn-secondary btn-sm" disabled={actionLoading === r.id}
                            onClick={() => startEditing(r)}>Edit</button>
                          <button className="btn btn-outline btn-sm" disabled={actionLoading === r.id}
                            onClick={() => handleWithdraw(r.id)}>Undo</button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
                {requests.length === 0 && (
                  <tr><td colSpan="7" className="empty-state">No requests submitted yet</td></tr>
                )}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
