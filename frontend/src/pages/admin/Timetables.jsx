import { useState, useEffect } from 'react';
import api, { resolveMediaUrl } from '../../utils/api';
import { useFeedback } from '../../context/FeedbackContext';
import SemesterFields from '../../components/SemesterFields';
import { buildSemesterCode, currentAcademicYear } from '../../utils/semester';

const DAYS = [
  { value: 'mon', label: 'Monday' },
  { value: 'tue', label: 'Tuesday' },
  { value: 'wed', label: 'Wednesday' },
  { value: 'thu', label: 'Thursday' },
  { value: 'fri', label: 'Friday' },
  { value: 'sat', label: 'Saturday' },
  { value: 'sun', label: 'Sunday' },
];
const DAY_LABELS = Object.fromEntries(DAYS.map((d) => [d.value, d.label]));
const emptySlotForm = { subject: '', day_of_week: 'mon', start_time: '', end_time: '', venue: '' };

export default function Timetables() {
  const { toast, confirm } = useFeedback();
  const [timetables, setTimetables] = useState([]);
  const [programmes, setProgrammes] = useState([]);
  const [venues, setVenues] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [title, setTitle] = useState('');
  const [semester, setSemester] = useState(buildSemesterCode(currentAcademicYear(), 1));
  const [programmeCodes, setProgrammeCodes] = useState([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const [slotsTimetable, setSlotsTimetable] = useState(null);
  const [slotSubjects, setSlotSubjects] = useState([]);
  const [slotForm, setSlotForm] = useState(emptySlotForm);
  const [slotError, setSlotError] = useState('');
  const [slotSaving, setSlotSaving] = useState(false);
  const [editingSlotId, setEditingSlotId] = useState(null);

  const subjectsBySemester = slotSubjects
    .slice()
    .sort((a, b) => a.semester - b.semester || a.subject_code.localeCompare(b.subject_code))
    .reduce((acc, s) => {
      (acc[s.semester] ||= []).push(s);
      return acc;
    }, {});

  const fetchTimetables = () => {
    setLoading(true);
    api.get('/admin/timetables/')
      .then(setTimetables)
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(fetchTimetables, []);

  useEffect(() => {
    api.get('/programmes/')
      .then((data) => {
        setProgrammes(data);
        if (data.length > 0) setProgrammeCodes((codes) => (codes.length ? codes : [data[0].programme_code]));
      })
      .catch(console.error);
  }, []);

  useEffect(() => {
    api.get('/admin/venues/').then(setVenues).catch(console.error);
  }, []);

  const openSlotsModal = (tt) => {
    setSlotsTimetable(tt);
    setSlotForm(emptySlotForm);
    setEditingSlotId(null);
    setSlotError('');
    Promise.all(tt.programmes.map((p) => api.get(`/subjects/?programme=${p.programme_code}`)))
      .then((results) => {
        const byCode = new Map();
        results.flat().forEach((s) => byCode.set(s.subject_code, s));
        setSlotSubjects([...byCode.values()]);
      })
      .catch(console.error);
  };

  const closeSlotsModal = () => {
    setSlotsTimetable(null);
    setSlotSubjects([]);
    setEditingSlotId(null);
  };

  const handleEditSlot = (slot) => {
    setEditingSlotId(slot.id);
    setSlotForm({
      subject: slot.subject_code,
      day_of_week: slot.day_of_week,
      start_time: slot.start_time.slice(0, 5),
      end_time: slot.end_time.slice(0, 5),
      venue: slot.venue,
    });
    setSlotError('');
  };

  const handleCancelEditSlot = () => {
    setEditingSlotId(null);
    setSlotForm(emptySlotForm);
    setSlotError('');
  };

  const handleAddSlot = async (e) => {
    e.preventDefault();
    setSlotError('');
    setSlotSaving(true);
    try {
      if (editingSlotId) {
        await api.put(`/admin/timetables/${slotsTimetable.id}/slots/${editingSlotId}/`, slotForm);
      } else {
        await api.post(`/admin/timetables/${slotsTimetable.id}/slots/`, slotForm);
      }
      setSlotForm({ ...emptySlotForm, day_of_week: slotForm.day_of_week });
      setEditingSlotId(null);
      const updated = await api.get('/admin/timetables/');
      setTimetables(updated);
      setSlotsTimetable(updated.find((t) => t.id === slotsTimetable.id));
    } catch (err) {
      setSlotError(err.message);
    } finally {
      setSlotSaving(false);
    }
  };

  const handleDeleteSlot = async (slotId) => {
    try {
      await api.delete(`/admin/timetables/${slotsTimetable.id}/slots/${slotId}/`);
      if (editingSlotId === slotId) handleCancelEditSlot();
      const updated = await api.get('/admin/timetables/');
      setTimetables(updated);
      setSlotsTimetable(updated.find((t) => t.id === slotsTimetable.id));
    } catch (err) {
      toast.error(err.message);
    }
  };

  const openCreateModal = () => {
    setEditingId(null);
    setTitle('');
    setSemester(buildSemesterCode(currentAcademicYear(), 1));
    setProgrammeCodes(programmes[0] ? [programmes[0].programme_code] : []);
    setError('');
    setShowModal(true);
  };

  const openEditModal = (tt) => {
    setEditingId(tt.id);
    setTitle(tt.title);
    setSemester(tt.semester);
    setProgrammeCodes(tt.programmes.map((p) => p.programme_code));
    setError('');
    setShowModal(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (programmeCodes.length === 0) {
      setError('Select at least one programme.');
      return;
    }
    setSaving(true);

    try {
      const payload = { title, semester, programme_codes: programmeCodes };
      if (editingId) {
        await api.put(`/admin/timetables/${editingId}/`, payload);
      } else {
        await api.post('/admin/timetables/', payload);
      }
      setShowModal(false);
      setTitle('');
      fetchTimetables();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id) => {
    if (!(await confirm({ title: 'Delete this timetable?', confirmLabel: 'Delete', danger: true }))) return;
    try {
      await api.delete(`/admin/timetables/${id}/`);
      fetchTimetables();
    } catch (err) {
      toast.error(err.message);
    }
  };

  return (
    <div>
      <div className="page-header flex-between">
        <div>
          <h1>Timetable Management</h1>
          <p>Create and manage faculty master timetables</p>
        </div>
        <button className="btn btn-primary" onClick={openCreateModal}>
          <span className="material-symbols-outlined">add</span>New Timetable
        </button>
      </div>

      <div className="card">
        <div className="table-container">
          {loading ? (
            <div className="loading-screen">Loading timetables...</div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Programme</th>
                  <th>Semester</th>
                  <th>Time Slots</th>
                  <th>Uploaded By</th>
                  <th>Date</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {timetables.map((tt) => (
                  <tr key={tt.id}>
                    <td><strong>{tt.title}</strong></td>
                    <td>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                        {tt.programmes.map((p) => (
                          <span key={p.programme_code} className="badge badge-gray" title={p.programme_name}>
                            {p.programme_code}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td>{tt.semester}</td>
                    <td>{tt.time_slots?.length || 0}</td>
                    <td>{tt.uploaded_by_name || '—'}</td>
                    <td>{new Date(tt.uploaded_at).toLocaleDateString()}</td>
                    <td>
                      <div className="btn-group">
                        <button className="btn btn-secondary btn-sm" onClick={() => openSlotsModal(tt)}>
                          Time Slots
                        </button>
                        {tt.file && (
                          <a href={resolveMediaUrl(tt.file)} target="_blank" rel="noreferrer" className="btn btn-secondary btn-sm">
                            View File
                          </a>
                        )}
                        <button className="btn btn-secondary btn-sm" onClick={() => openEditModal(tt)}>
                          Edit
                        </button>
                        <button className="btn btn-danger btn-sm" onClick={() => handleDelete(tt.id)}>
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {timetables.length === 0 && (
                  <tr><td colSpan="7" className="empty-state">No timetables uploaded</td></tr>
                )}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{editingId ? 'Edit Timetable' : 'Create Timetable'}</h3>
              <button className="close-btn" onClick={() => setShowModal(false)}>&times;</button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="modal-body">
                {error && <div className="alert alert-error">{error}</div>}
                <div className="form-group">
                  <label>Title</label>
                  <input className="form-control" value={title}
                    onChange={(e) => setTitle(e.target.value)} required
                    placeholder="e.g. BCSSE Semester 1 2026 Timetable" />
                </div>
                <SemesterFields value={semester} onChange={setSemester} />
                <div className="form-group">
                  <label>Programmes</label>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', maxHeight: '140px', overflowY: 'auto' }}>
                    {programmes.map((p) => (
                      <label key={p.programme_code} style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 'normal' }}>
                        <input
                          type="checkbox"
                          checked={programmeCodes.includes(p.programme_code)}
                          onChange={(e) => setProgrammeCodes(
                            e.target.checked
                              ? [...programmeCodes, p.programme_code]
                              : programmeCodes.filter((c) => c !== p.programme_code)
                          )}
                        />
                        {p.programme_code} - {p.programme_name}
                      </label>
                    ))}
                  </div>
                  <small style={{ color: 'var(--gray-400)' }}>
                    One timetable and its time slots can serve several programmes at once
                  </small>
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-outline" onClick={() => setShowModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary" disabled={saving}>
                  {saving ? 'Saving...' : editingId ? 'Save Changes' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {slotsTimetable && (() => {
        const sortedSlots = [...slotsTimetable.time_slots].sort((a, b) => {
          const dayDiff = DAYS.findIndex((d) => d.value === a.day_of_week) - DAYS.findIndex((d) => d.value === b.day_of_week);
          return dayDiff !== 0 ? dayDiff : a.start_time.localeCompare(b.start_time);
        });
        return (
        <div className="modal-overlay" onClick={closeSlotsModal}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Time Slots — {slotsTimetable.title}</h3>
              <button className="close-btn" onClick={closeSlotsModal}>&times;</button>
            </div>
            <div className="modal-body">
              <div className="table-container mb-16">
                <table>
                  <thead>
                    <tr>
                      <th>Day</th>
                      <th>Time</th>
                      <th>Subject</th>
                      <th>Semester</th>
                      <th>Venue</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortedSlots.map((s) => (
                      <tr key={s.id}>
                        <td>{DAY_LABELS[s.day_of_week]}</td>
                        <td>{s.start_time.slice(0, 5)}–{s.end_time.slice(0, 5)}</td>
                        <td>{s.subject_code} - {s.subject_name}</td>
                        <td>{s.subject_semester}</td>
                        <td>{s.venue || '—'}</td>
                        <td>
                          <div className="btn-group">
                            <button className="btn btn-secondary btn-sm" onClick={() => handleEditSlot(s)}>
                              Edit
                            </button>
                            <button className="btn btn-danger btn-sm" onClick={() => handleDeleteSlot(s.id)}>
                              Delete
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                    {slotsTimetable.time_slots.length === 0 && (
                      <tr><td colSpan="6" className="empty-state">No time slots added yet</td></tr>
                    )}
                  </tbody>
                </table>
              </div>

              <form onSubmit={handleAddSlot}>
                {slotError && <div className="alert alert-error">{slotError}</div>}
                <div className="grid-2">
                  <div className="form-group">
                    <label>Subject</label>
                    <select className="form-control" value={slotForm.subject}
                      onChange={(e) => setSlotForm({ ...slotForm, subject: e.target.value })} required>
                      <option value="">Select a subject</option>
                      {Object.keys(subjectsBySemester).sort((a, b) => a - b).map((sem) => (
                        <optgroup key={sem} label={`Semester ${sem}`}>
                          {subjectsBySemester[sem].map((s) => (
                            <option key={s.subject_code} value={s.subject_code}>
                              {s.subject_code} - {s.subject_name}
                            </option>
                          ))}
                        </optgroup>
                      ))}
                    </select>
                  </div>
                  <div className="form-group">
                    <label>Day</label>
                    <select className="form-control" value={slotForm.day_of_week}
                      onChange={(e) => setSlotForm({ ...slotForm, day_of_week: e.target.value })}>
                      {DAYS.map((d) => <option key={d.value} value={d.value}>{d.label}</option>)}
                    </select>
                  </div>
                </div>
                <div className="grid-2">
                  <div className="form-group">
                    <label>Start Time</label>
                    <input type="time" className="form-control" value={slotForm.start_time}
                      onChange={(e) => setSlotForm({ ...slotForm, start_time: e.target.value })} required />
                  </div>
                  <div className="form-group">
                    <label>End Time</label>
                    <input type="time" className="form-control" value={slotForm.end_time}
                      onChange={(e) => setSlotForm({ ...slotForm, end_time: e.target.value })} required />
                  </div>
                </div>
                <div className="form-group">
                  <label>Venue</label>
                  <select className="form-control" value={slotForm.venue}
                    onChange={(e) => setSlotForm({ ...slotForm, venue: e.target.value })}>
                    <option value="">Select a venue</option>
                    {venues.map((v) => (
                      <option key={v.name} value={v.name}>{v.name} ({v.capacity} seats)</option>
                    ))}
                  </select>
                </div>
                <div className="btn-group">
                  <button type="submit" className="btn btn-primary" disabled={slotSaving}>
                    {slotSaving ? 'Saving...' : editingSlotId ? 'Save Changes' : '+ Add Time Slot'}
                  </button>
                  {editingSlotId && (
                    <button type="button" className="btn btn-outline" onClick={handleCancelEditSlot}>
                      Cancel
                    </button>
                  )}
                </div>
              </form>
            </div>
            <div className="modal-footer">
              <button type="button" className="btn btn-outline" onClick={closeSlotsModal}>Close</button>
            </div>
          </div>
        </div>
        );
      })()}
    </div>
  );
}
