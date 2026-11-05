import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import api from '../../utils/api';
import { useFeedback } from '../../context/FeedbackContext';
import { useAuth } from '../../context/AuthContext';
import SemesterFields from '../../components/SemesterFields';
import { semesterIntake } from '../../utils/semester';

export default function AddDrop() {
  const { toast, confirm } = useFeedback();
  const { user } = useAuth();
  const [requests, setRequests] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [enrolments, setEnrolments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ subject_code: '', action: 'add', reason: '', semester: '' });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [editingId, setEditingId] = useState(null);
  const [actionLoading, setActionLoading] = useState(null);

  const [searchParams, setSearchParams] = useSearchParams();
  const profile = user?.student_profile;
  const programmeCode = profile?.programme?.programme_code;

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

  // The registration period a student is actively enrolled in - the most
  // recent semester code with active (assigned/in_progress) enrolments -
  // is what add/drop requests should default to and match against.
  const activeSemesterCode = (() => {
    const active = enrolments.filter((e) => ['assigned', 'in_progress'].includes(e.status));
    const pool = active.length ? active : enrolments;
    return pool.reduce((latest, e) => (e.semester > latest ? e.semester : latest), '');
  })();

  const completedCodes = new Set(
    enrolments.filter((e) => e.status === 'passed').map((e) => e.subject.subject_code)
  );
  const assignedCodesForSemester = new Set(
    enrolments
      .filter((e) => e.semester === form.semester && ['assigned', 'in_progress'].includes(e.status))
      .map((e) => e.subject.subject_code)
  );
  // Adding: any subject in the programme not already assigned this semester
  // or already passed. Dropping: only subjects currently assigned this semester.
  const subjectOptions = form.action === 'drop'
    ? subjects.filter((s) => assignedCodesForSemester.has(s.subject_code))
    : subjects.filter((s) =>
        !assignedCodesForSemester.has(s.subject_code) &&
        !completedCodes.has(s.subject_code)
      );

  const openNewRequest = () => {
    setForm({ subject_code: '', action: 'add', reason: '', semester: activeSemesterCode });
    setEditingId(null);
    setShowForm(true);
  };

  // "New Add/Drop" shortcuts (topbar, quick rail) link here with ?new=1 so
  // the form is already open, pre-filled with the active semester.
  useEffect(() => {
    if (loading || searchParams.get('new') !== '1') return;
    openNewRequest();
    setSearchParams({}, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loading, searchParams]);

  const activeCredits = enrolments
    .filter((e) => e.semester === activeSemesterCode && ['assigned', 'in_progress'].includes(e.status))
    .reduce((sum, e) => sum + e.subject.credit_hours, 0);
  const activeSubjectCount = enrolments
    .filter((e) => e.semester === activeSemesterCode && ['assigned', 'in_progress'].includes(e.status)).length;
  const creditCap = profile?.effective_credit_cap;
  const intake = semesterIntake(activeSemesterCode);
  const pendingCount = requests.filter((r) => r.status === 'pending').length;

  const resetForm = () => {
    setForm({ subject_code: '', action: 'add', reason: '', semester: activeSemesterCode });
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
        toast.success('Request updated.');
      } else {
        await api.post('/student/add-drop/', form);
        toast.success('Request submitted.');
      }
      resetForm();
      fetchData();
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
    if (!(await confirm({ title: 'Withdraw this request?', confirmLabel: 'Withdraw', danger: true }))) return;
    setActionLoading(id);
    try {
      await api.post(`/student/add-drop/${id}/withdraw/`, {});
      fetchData();
    } catch (err) {
      toast.error(err.message);
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
        <button className="btn btn-primary" onClick={() => (showForm ? resetForm() : openNewRequest())}>
          {showForm ? 'Cancel' : <><span className="material-symbols-outlined">add</span>New Request</>}
        </button>
      </div>


      {!loading && (
        <ol className="rules-panel">
          {activeSemesterCode && (
            <li>
              Your active registration semester is <strong className="mono">{activeSemesterCode}</strong>
              {intake && <> ({intake.label}, {intake.durationWeeks} weeks)</>}.
            </li>
          )}
          {creditCap != null && (
            <li>
              You are registered for <strong>{activeCredits} of {creditCap} credit hours</strong>
              {profile?.status === 'probation' && ' (probation cap)'}
              {' '}— up to <strong>{Math.max(0, creditCap - activeCredits)} more</strong> can be added.
            </li>
          )}
          {intake && (
            <li>
              This semester allows <strong>
                {intake.minSubjects === intake.maxSubjects ? intake.maxSubjects : `${intake.minSubjects}–${intake.maxSubjects}`} subjects
              </strong>; you currently have <strong>{activeSubjectCount}</strong>.
            </li>
          )}
          <li>
            {pendingCount > 0
              ? <>You have <strong>{pendingCount} pending request{pendingCount === 1 ? '' : 's'}</strong> awaiting admin review.</>
              : 'You have no pending requests.'}
            {' '}Pending requests can be edited or withdrawn until they are reviewed.
          </li>
          <li>Subjects you have already passed or are already registered for are hidden from the list automatically.</li>
        </ol>
      )}

      <div className="info-note">
        Note: every add/drop request is reviewed by the faculty administrator. A subject is only added to or
        removed from your timetable once the request is approved.
      </div>

      {showForm && (
        <div className="card mb-24">
          <div className="card-header"><h3>{editingId ? 'Edit Request' : 'Submit Request'}</h3></div>
          <div className="card-body">
            <form onSubmit={handleSubmit}>
              {error && <div className="alert alert-error">{error}</div>}
              <div className={form.action === 'drop' ? 'grid-2' : undefined}>
                <div className="form-group">
                  <label>Action</label>
                  <select className="form-control" value={form.action}
                    onChange={(e) => {
                      const action = e.target.value;
                      setForm({
                        ...form, action, subject_code: '',
                        semester: action === 'add' ? activeSemesterCode : form.semester,
                      });
                    }}>
                    <option value="add">Add Subject</option>
                    <option value="drop">Drop Subject</option>
                  </select>
                </div>
                {form.action === 'drop' && (
                  <SemesterFields value={form.semester}
                    onChange={(semester) => setForm({ ...form, semester, subject_code: '' })} />
                )}
              </div>
              <div className="form-group">
                <label>Subject</label>
                <select className="form-control" value={form.subject_code}
                  onChange={(e) => setForm({ ...form, subject_code: e.target.value })} required>
                  <option value="">Select a subject</option>
                  {subjectOptions.map((s) => (
                    <option key={s.subject_code} value={s.subject_code}>
                      {s.subject_code} - {s.subject_name}
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
