import { useState, useEffect } from 'react';
import api from '../../utils/api';
import { useFeedback, notifyCountsChanged } from '../../context/FeedbackContext';
import { currentSemesterCode } from '../../utils/semester';

const FILTERS = [
  { value: 'pending', label: 'Pending' },
  { value: 'approved', label: 'Approved' },
  { value: 'rejected', label: 'Rejected' },
  { value: '', label: 'All' },
];

const STATUS_BADGE = {
  pending: 'badge-yellow',
  approved: 'badge-green',
  rejected: 'badge-red',
};

const DAY_LABELS = {
  mon: 'Mon', tue: 'Tue', wed: 'Wed', thu: 'Thu', fri: 'Fri', sat: 'Sat', sun: 'Sun',
};

function formatTimeSlots(slots) {
  if (!slots || slots.length === 0) return 'no time slot';
  return slots
    .map((s) => `${DAY_LABELS[s.day_of_week] || s.day_of_week} ${s.start_time.slice(0, 5)}-${s.end_time.slice(0, 5)}`)
    .join(', ');
}

function initials(name) {
  if (!name) return '?';
  const parts = name.trim().split(/\s+/);
  return (parts[0][0] + (parts[1]?.[0] || '')).toUpperCase();
}

function formatDate(iso) {
  if (!iso) return '';
  return new Date(iso).toLocaleString(undefined, {
    day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
  });
}

export default function Exceptions() {
  const { toast, confirm } = useFeedback();
  const [exceptions, setExceptions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('pending');
  const [actionLoading, setActionLoading] = useState(null);
  const [editingId, setEditingId] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  const [selectedStudentId, setSelectedStudentId] = useState(null);
  const [replacementOptions, setReplacementOptions] = useState([]);
  const [replacementLoading, setReplacementLoading] = useState(false);
  const [replacementSubject, setReplacementSubject] = useState('');
  const [replacementError, setReplacementError] = useState('');

  const fetchExceptions = () => {
    setLoading(true);
    const query = filter ? `?status=${filter}` : '';
    api.get(`/admin/exceptions/${query}`)
      .then((data) => {
        setExceptions(data);

        const stillHasStudent = selectedStudentId != null && data.some((e) => e.student === selectedStudentId);
        const nextStudentId = stillHasStudent ? selectedStudentId : null;
        setSelectedStudentId(nextStudentId);

        if (selectedId != null && data.some((e) => e.id === selectedId)) {
          // keep current selection
        } else if (nextStudentId != null) {
          const first = data.find((e) => e.student === nextStudentId);
          setSelectedId(first ? first.id : null);
        } else {
          setSelectedId(null);
        }
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(fetchExceptions, [filter]);

  const handleResolve = async (id, status, semester) => {
    setActionLoading(id);
    try {
      await api.put(`/admin/exceptions/${id}/resolve/`, { status, semester });
      toast.success(`Exception ${status}.`);
      notifyCountsChanged();
      setEditingId(null);
      fetchExceptions();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setActionLoading(null);
    }
  };

  const handleUndo = async (id) => {
    if (!(await confirm({ title: 'Undo this decision?', message: 'The exception will return to pending.', confirmLabel: 'Undo decision' }))) return;
    setActionLoading(id);
    try {
      await api.post(`/admin/exceptions/${id}/undo/`, {});
      toast.info('Decision undone — back to pending.');
      notifyCountsChanged();
      setEditingId(null);
      fetchExceptions();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setActionLoading(null);
    }
  };

  const reasonLabel = (reason) => reason.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

  const studentGroups = exceptions.reduce((acc, ex) => {
    (acc[ex.student] ||= {
      student: ex.student,
      student_name: ex.student_name,
      student_id_display: ex.student_id_display,
      student_semester: ex.student_semester,
      items: [],
    }).items.push(ex);
    return acc;
  }, {});
  const students = Object.values(studentGroups).sort((a, b) => a.student_name.localeCompare(b.student_name));
  const selectedStudent = selectedStudentId != null ? studentGroups[selectedStudentId] : null;

  const openStudent = (group) => {
    setSelectedStudentId(group.student);
    setSelectedId(group.items[0]?.id ?? null);
  };

  const selected = exceptions.find((e) => e.id === selectedId) || null;
  const canDecide = selected && (selected.status === 'pending' || editingId === selected.id);
  const isConflict = selected?.reason === 'conflict';

  useEffect(() => {
    if (!selected || !isConflict || !canDecide) {
      setReplacementOptions([]);
      setReplacementSubject('');
      setReplacementError('');
      return;
    }
    setReplacementLoading(true);
    setReplacementError('');
    setReplacementSubject('');
    api.get(`/admin/exceptions/${selected.id}/replacement-options/?semester=${currentSemesterCode()}`)
      .then(setReplacementOptions)
      .catch((err) => setReplacementError(err.message))
      .finally(() => setReplacementLoading(false));
    // Depend on selected.id (not the object) so a fetchExceptions() refresh that
    // returns an equal-but-new exception object doesn't re-trigger this fetch.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected?.id, isConflict, canDecide]);

  const replacementsBySemester = replacementOptions.reduce((acc, o) => {
    (acc[o.semester] ||= []).push(o);
    return acc;
  }, {});

  const handleAssignReplacement = async () => {
    if (!replacementSubject) return;
    setActionLoading(selected.id);
    try {
      await api.post(`/admin/exceptions/${selected.id}/replace/`, {
        subject_code: replacementSubject,
        semester: currentSemesterCode(),
      });
      toast.success(`Replacement ${replacementSubject} assigned.`);
      notifyCountsChanged();
      setEditingId(null);
      fetchExceptions();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div>
      <div className="page-header">
        <h1>Exception Management</h1>
        <p>Review and resolve flagged exceptions from the rule engine</p>
      </div>

      <div className="card" style={{ display: 'flex', minHeight: '520px', overflow: 'hidden' }}>
        <div style={{ width: '360px', flex: 'none', borderRight: '1px solid var(--gray-200)', display: 'flex', flexDirection: 'column' }}>
          <div style={{ padding: '16px 16px 12px', borderBottom: '1px solid var(--gray-200)', display: 'flex', gap: '7px', flexWrap: 'wrap' }}>
            {FILTERS.map((f) => (
              <button
                key={f.value}
                className={`filter-pill${filter === f.value ? ' active' : ''}`}
                onClick={() => setFilter(f.value)}
              >
                {f.label}
              </button>
            ))}
          </div>
          <div style={{ overflowY: 'auto', flex: 1 }}>
            {loading ? (
              <div className="loading-screen">Loading...</div>
            ) : selectedStudent ? (
              <>
                <div
                  onClick={() => setSelectedStudentId(null)}
                  style={{
                    display: 'flex', alignItems: 'center', gap: '7px', padding: '12px 16px',
                    borderBottom: '1px solid var(--gray-200)', cursor: 'pointer',
                    background: 'var(--gray-50)', color: 'var(--gray-700)',
                  }}
                >
                  <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>arrow_back</span>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ font: '400 13px var(--font)' }}>{selectedStudent.student_name}</div>
                    <div className="mono" style={{ fontSize: '11px', color: 'var(--gray-500)' }}>
                      {selectedStudent.student_id_display} &middot; Semester {selectedStudent.student_semester} &middot; {selectedStudent.items.length} exception(s)
                    </div>
                  </div>
                </div>
                {selectedStudent.items.map((ex) => (
                  <div
                    key={ex.id}
                    onClick={() => setSelectedId(ex.id)}
                    style={{
                      display: 'flex', flexDirection: 'column', gap: '3px', padding: '13px 16px 13px 41px',
                      borderBottom: '1px solid var(--gray-200)', cursor: 'pointer',
                      background: selectedId === ex.id ? 'var(--red-light)' : 'transparent',
                      boxShadow: selectedId === ex.id ? 'inset 3px 0 0 var(--red)' : 'none',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'baseline', gap: '7px' }}>
                      <div style={{ fontSize: '13px', color: 'var(--gray-800)' }}>{reasonLabel(ex.reason)}</div>
                      <div className="mono" style={{ fontSize: '11px', color: 'var(--gray-500)' }}>EX-{ex.id}</div>
                    </div>
                    <div style={{ fontSize: '12px', color: 'var(--gray-700)' }}>{ex.subject.subject_code}</div>
                    <div style={{ display: 'flex', gap: '6px', marginTop: '2px', alignItems: 'center' }}>
                      <span className={`badge ${STATUS_BADGE[ex.status]}`}>{ex.status}</span>
                      <span className="mono" style={{ fontSize: '10.5px', color: 'var(--gray-500)' }}>{formatDate(ex.created_at)}</span>
                    </div>
                  </div>
                ))}
              </>
            ) : students.length === 0 ? (
              <div className="empty-state"><p>No exceptions found</p></div>
            ) : (
              students.map((group) => (
                <div
                  key={group.student}
                  onClick={() => openStudent(group)}
                  style={{
                    display: 'flex', gap: '11px', padding: '13px 16px',
                    borderBottom: '1px solid var(--gray-200)', cursor: 'pointer',
                  }}
                >
                  <div style={{
                    width: '34px', height: '34px', flex: 'none', borderRadius: '50%',
                    background: 'var(--sky-light)', color: 'var(--sky)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    font: '400 11.5px var(--font)',
                  }}>{initials(group.student_name)}</div>
                  <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: '3px' }}>
                    <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: '7px' }}>
                      <div style={{ font: '400 13px var(--font)' }}>{group.student_name}</div>
                      <span className="badge badge-gray">{group.items.length}</span>
                    </div>
                    <div className="mono" style={{ fontSize: '11px', color: 'var(--gray-500)' }}>
                      {group.student_id_display} &middot; Semester {group.student_semester}
                    </div>
                  </div>
                  <span className="material-symbols-outlined" style={{ color: 'var(--gray-400)', fontSize: '19px', alignSelf: 'center' }}>
                    chevron_right
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

        <div style={{ flex: 1, minWidth: 0, padding: '22px 24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {!selected ? (
            <div className="empty-state"><p>Select an exception from the list to review it</p></div>
          ) : (
            <>
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '16px' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '9px' }}>
                    <div style={{ font: '700 20px var(--font)' }}>{reasonLabel(selected.reason)}</div>
                    <span className={`badge ${STATUS_BADGE[selected.status]}`}>{selected.status}</span>
                  </div>
                  <div className="mono" style={{ fontSize: '12.5px', color: 'var(--gray-600)' }}>
                    EX-{selected.id} &middot; raised {formatDate(selected.created_at)}
                    {selected.reviewed_at && ` · reviewed by ${selected.reviewed_by_name || '—'} on ${formatDate(selected.reviewed_at)}`}
                  </div>
                </div>
              </div>

              <div style={{
                display: 'flex', gap: '14px', padding: '16px', background: '#fff',
                border: '1px solid var(--gray-300)', borderRadius: 'var(--radius-lg)', boxShadow: 'var(--shadow)',
              }}>
                <div style={{
                  width: '44px', height: '44px', flex: 'none', borderRadius: '50%',
                  background: 'var(--sky-light)', color: 'var(--sky)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', font: '400 14px var(--font)',
                }}>{initials(selected.student_name)}</div>
                <div style={{ flex: 1, display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '14px' }}>
                  <div>
                    <div style={{ font: '400 10.5px var(--font)', letterSpacing: '.07em', color: 'var(--gray-600)' }}>STUDENT</div>
                    <div style={{ font: '400 13px var(--font)' }}>{selected.student_name}</div>
                    <div className="mono" style={{ fontSize: '11.5px', color: 'var(--gray-600)' }}>
                      {selected.student_id_display} &middot; Semester {selected.student_semester}
                    </div>
                  </div>
                  <div>
                    <div style={{ font: '400 10.5px var(--font)', letterSpacing: '.07em', color: 'var(--gray-600)' }}>SUBJECT</div>
                    <div className="mono" style={{ font: '400 13px var(--font)', color: 'var(--sky)' }}>{selected.subject.subject_code}</div>
                    <div style={{ fontSize: '11.5px', color: 'var(--gray-600)' }}>{selected.subject.subject_name} &middot; {selected.subject.credit_hours} cr</div>
                  </div>
                  <div>
                    <div style={{ font: '400 10.5px var(--font)', letterSpacing: '.07em', color: 'var(--gray-600)' }}>REASON</div>
                    <div style={{ font: '400 13px var(--font)' }}>{reasonLabel(selected.reason)}</div>
                  </div>
                </div>
              </div>

              <div style={{
                background: '#fff', border: '1px solid var(--gray-300)', borderRadius: 'var(--radius-lg)',
                boxShadow: 'var(--shadow)', overflow: 'hidden',
              }}>
                <div style={{
                  display: 'flex', alignItems: 'center', gap: '9px', padding: '14px 16px',
                  borderBottom: '1px solid var(--gray-200)', background: 'var(--gray-50)',
                }}>
                  <span className="material-symbols-outlined" style={{ color: 'var(--sky)', fontSize: '19px' }}>description</span>
                  <div style={{ font: '700 14.5px var(--font)' }}>Details</div>
                </div>
                <div style={{ padding: '14px 16px', fontSize: '13px', color: 'var(--gray-800)' }}>
                  {selected.details || <span style={{ color: 'var(--gray-500)' }}>No additional details provided.</span>}
                </div>
              </div>

              <div style={{
                background: '#fff', border: '1px solid var(--gray-300)', borderRadius: 'var(--radius-lg)',
                boxShadow: 'var(--shadow)', padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px', marginTop: 'auto',
              }}>
                <div style={{ font: '700 14.5px var(--font)' }}>Coordinator decision</div>
                {canDecide && isConflict ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    <p style={{ fontSize: '12.5px', color: 'var(--gray-600)', margin: 0 }}>
                      {selected.subject.subject_code} couldn't be assigned due to a scheduling conflict.
                      Pick a clash-free subject from another semester to assign instead.
                    </p>
                    {replacementError && <div className="alert alert-error">{replacementError}</div>}
                    <select className="form-control" value={replacementSubject}
                      disabled={replacementLoading}
                      onChange={(e) => setReplacementSubject(e.target.value)}>
                      <option value="">
                        {replacementLoading ? 'Loading clash-free subjects...' : 'Select a replacement subject'}
                      </option>
                      {Object.keys(replacementsBySemester).sort((a, b) => a - b).map((sem) => (
                        <optgroup key={sem} label={`Semester ${sem}`}>
                          {replacementsBySemester[sem].map((o) => (
                            <option key={o.subject_code} value={o.subject_code}>
                              {o.subject_code} - {o.subject_name} ({formatTimeSlots(o.time_slots)})
                            </option>
                          ))}
                        </optgroup>
                      ))}
                    </select>
                    {!replacementLoading && replacementOptions.length === 0 && !replacementError && (
                      <p style={{ fontSize: '12px', color: 'var(--gray-500)', margin: 0 }}>
                        No clash-free replacement subjects are available for this student right now.
                      </p>
                    )}
                    <div className="btn-group">
                      <button
                        className="btn btn-success"
                        disabled={actionLoading === selected.id || !replacementSubject}
                        onClick={handleAssignReplacement}
                      >
                        <span className="material-symbols-outlined">task_alt</span>Assign Replacement
                      </button>
                      <button
                        className="btn btn-danger"
                        disabled={actionLoading === selected.id}
                        onClick={() => handleResolve(selected.id, 'rejected')}
                      >
                        <span className="material-symbols-outlined">block</span>Reject
                      </button>
                      {editingId === selected.id && (
                        <button className="btn btn-outline" disabled={actionLoading === selected.id}
                          onClick={() => setEditingId(null)}>Cancel</button>
                      )}
                    </div>
                  </div>
                ) : canDecide ? (
                  <div className="btn-group">
                    <button
                      className="btn btn-success"
                      disabled={actionLoading === selected.id}
                      onClick={() => handleResolve(selected.id, 'approved', currentSemesterCode())}
                    >
                      <span className="material-symbols-outlined">task_alt</span>Approve
                    </button>
                    <button
                      className="btn btn-danger"
                      disabled={actionLoading === selected.id}
                      onClick={() => handleResolve(selected.id, 'rejected')}
                    >
                      <span className="material-symbols-outlined">block</span>Reject
                    </button>
                    {editingId === selected.id && (
                      <button className="btn btn-outline" disabled={actionLoading === selected.id}
                        onClick={() => setEditingId(null)}>Cancel</button>
                    )}
                  </div>
                ) : (
                  <div className="btn-group">
                    <button className="btn btn-secondary" disabled={actionLoading === selected.id}
                      onClick={() => setEditingId(selected.id)}>
                      <span className="material-symbols-outlined">edit</span>Edit decision
                    </button>
                    <button className="btn btn-outline" disabled={actionLoading === selected.id}
                      onClick={() => handleUndo(selected.id)}>
                      <span className="material-symbols-outlined">undo</span>Undo
                    </button>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
