import { useState, useEffect } from 'react';
import api, { resolveMediaUrl } from '../../utils/api';
import { useFeedback } from '../../context/FeedbackContext';

const emptyForm = {
  semester_intake: '', intake_day: '', full_name: '', ic_passport: '',
  programme_code: '', current_semester: 1,
  status: 'active', is_repeat: false, is_transfer: false,
};

const DAY_LABELS = {
  mon: 'Monday', tue: 'Tuesday', wed: 'Wednesday', thu: 'Thursday',
  fri: 'Friday', sat: 'Saturday', sun: 'Sunday',
};

export default function Students() {
  const { toast, confirm } = useFeedback();
  const [students, setStudents] = useState([]);
  const [programmes, setProgrammes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [photo, setPhoto] = useState(null);
  const [photoPreview, setPhotoPreview] = useState(null);
  const [error, setError] = useState('');

  const [editStudent, setEditStudent] = useState(null);
  const [editForm, setEditForm] = useState(null);
  const [editPhoto, setEditPhoto] = useState(null);
  const [editPhotoPreview, setEditPhotoPreview] = useState(null);
  const [editSaving, setEditSaving] = useState(false);
  const [editError, setEditError] = useState('');

  const [detailStudent, setDetailStudent] = useState(null);
  const [detailSubjects, setDetailSubjects] = useState([]);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailSelectedSemester, setDetailSelectedSemester] = useState('');

  const filteredStudents = students.filter((s) =>
    s.user.student_id.toLowerCase().includes(search.trim().toLowerCase())
  );

  const openDetail = (student) => {
    setDetailStudent(student);
    setDetailSubjects([]);
    setDetailSelectedSemester('');
    setDetailLoading(true);
    api.get(`/admin/students/${student.user.student_id}/subjects/`)
      .then((data) => {
        setDetailSubjects(data);
        // The current semester is the most recent one with active
        // (assigned/in_progress) subjects, so the modal opens on "this
        // semester" rather than the student's full history.
        const active = data.filter((e) => ['assigned', 'in_progress'].includes(e.status));
        const pool = active.length ? active : data;
        const current = pool.reduce((latest, e) => (e.semester > latest ? e.semester : latest), '');
        setDetailSelectedSemester(current);
      })
      .catch(console.error)
      .finally(() => setDetailLoading(false));
  };

  const closeDetail = () => {
    setDetailStudent(null);
    setDetailSubjects([]);
    setDetailSelectedSemester('');
  };

  const fetchStudents = () => {
    setLoading(true);
    api.get('/admin/students/')
      .then(setStudents)
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(fetchStudents, []);

  useEffect(() => {
    api.get('/programmes/')
      .then((data) => {
        setProgrammes(data);
        if (data.length > 0) {
          setForm((f) => ({ ...f, programme_code: data[0].programme_code }));
        }
      })
      .catch(console.error);
  }, []);

  const closeModal = () => {
    setShowModal(false);
    setForm({ ...emptyForm, programme_code: programmes[0]?.programme_code || '' });
    setPhoto(null);
    setPhotoPreview(null);
  };

  const handlePhotoChange = (e) => {
    const file = e.target.files[0] || null;
    setPhoto(file);
    setPhotoPreview(file ? URL.createObjectURL(file) : null);
  };

  const handleDelete = async (student) => {
    if (!(await confirm({ title: `Delete student ${student.user.student_id} (${student.user.full_name})?`, message: 'This cannot be undone.', confirmLabel: 'Delete', danger: true }))) return;
    try {
      await api.delete(`/admin/students/${student.user.student_id}/`);
      fetchStudents();
    } catch (err) {
      toast.error(err.message);
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    setError('');
    try {
      const formData = new FormData();
      Object.entries(form).forEach(([key, value]) => formData.append(key, value));
      if (photo) formData.append('photo', photo);

      await api.post('/admin/students/create/', formData);
      toast.success('Student created.');
      closeModal();
      fetchStudents();
    } catch (err) {
      setError(err.message);
    }
  };

  const openEditModal = (student) => {
    setEditStudent(student);
    setEditForm({
      full_name: student.user.full_name,
      ic_passport: student.user.ic_passport,
      programme_code: student.programme.programme_code,
      current_semester: student.current_semester,
      status: student.status,
      is_repeat: student.is_repeat,
      is_transfer: student.is_transfer,
    });
    setEditPhoto(null);
    setEditPhotoPreview(student.photo ? resolveMediaUrl(student.photo) : null);
    setEditError('');
  };

  const closeEditModal = () => {
    setEditStudent(null);
    setEditForm(null);
    setEditPhoto(null);
    setEditPhotoPreview(null);
  };

  const handleEditPhotoChange = (e) => {
    const file = e.target.files[0] || null;
    setEditPhoto(file);
    if (file) setEditPhotoPreview(URL.createObjectURL(file));
  };

  const handleEditSave = async (e) => {
    e.preventDefault();
    setEditSaving(true);
    setEditError('');
    try {
      const formData = new FormData();
      Object.entries(editForm).forEach(([key, value]) => formData.append(key, value));
      if (editPhoto) formData.append('photo', editPhoto);
      await api.put(`/admin/students/${editStudent.user.student_id}/`, formData);
      closeEditModal();
      fetchStudents();
    } catch (err) {
      setEditError(err.message);
    } finally {
      setEditSaving(false);
    }
  };

  const statusBadge = (status) => {
    const map = {
      active: 'badge-green',
      probation: 'badge-red',
      graduated: 'badge-blue',
      suspended: 'badge-yellow',
    };
    return <span className={`badge ${map[status] || 'badge-gray'}`}>{status}</span>;
  };

  const resultBadge = (grade) => {
    if (!grade) return <span className="badge badge-gray">—</span>;
    return grade === 'F'
      ? <span className="badge badge-red">Failed</span>
      : <span className="badge badge-green">Passed</span>;
  };

  return (
    <div>
      <div className="page-header flex-between">
        <div>
          <h1>Student Management</h1>
          <p>View and manage student accounts</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowModal(true)}>
          <span className="material-symbols-outlined">add</span>Add Student
        </button>
      </div>


      <div className="mb-16" style={{ maxWidth: '320px' }}>
        <input className="form-control" value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by Student ID..." />
      </div>

      <div className="card">
        <div className="table-container">
          {loading ? (
            <div className="loading-screen">Loading students...</div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th></th>
                  <th>Student ID</th>
                  <th>Name</th>
                  <th>Programme</th>
                  <th>Semester</th>
                  <th>Status</th>
                  <th>Credits Earned</th>
                  <th>CGPA</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredStudents.map((s) => (
                  <tr key={s.id}>
                    <td>
                      {s.photo ? (
                        <img className="student-photo" src={resolveMediaUrl(s.photo)} alt="" />
                      ) : (
                        <span className="student-photo student-photo-placeholder">
                          <span className="material-symbols-outlined">person</span>
                        </span>
                      )}
                    </td>
                    <td><strong>{s.user.student_id}</strong></td>
                    <td>{s.user.full_name}</td>
                    <td>{s.programme.programme_code}</td>
                    <td>{s.current_semester}</td>
                    <td>{statusBadge(s.status)}</td>
                    <td>{s.total_credits_earned}</td>
                    <td>{s.cgpa}</td>
                    <td>
                      <div className="btn-group">
                        <button className="btn btn-secondary btn-sm" onClick={() => openDetail(s)}>
                          View
                        </button>
                        <button className="btn btn-secondary btn-sm" onClick={() => openEditModal(s)}>
                          Edit
                        </button>
                        <button className="btn btn-danger btn-sm" onClick={() => handleDelete(s)}>
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {filteredStudents.length === 0 && (
                  <tr><td colSpan="9" className="empty-state">No students found</td></tr>
                )}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {showModal && (
        <div className="modal-overlay" onClick={closeModal}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Add New Student</h3>
              <button className="close-btn" onClick={closeModal}>&times;</button>
            </div>
            <form onSubmit={handleCreate}>
              <div className="modal-body">
                {error && <div className="alert alert-error">{error}</div>}
                <div className="form-group">
                  <label>Passport-size Photo</label>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    {photoPreview ? (
                      <img className="student-photo student-photo-lg" src={photoPreview} alt="Preview" />
                    ) : (
                      <span className="student-photo student-photo-lg student-photo-placeholder">
                        <span className="material-symbols-outlined">person</span>
                      </span>
                    )}
                    <input type="file" accept="image/*" className="form-control" onChange={handlePhotoChange} />
                  </div>
                </div>
                <div className="grid-2">
                  <div className="form-group">
                    <label>Semester Intake</label>
                    <input className="form-control" value={form.semester_intake} placeholder="e.g. 202401"
                      pattern="\d{6}" maxLength={6} title="6 digits, e.g. 202401"
                      onChange={(e) => setForm({...form, semester_intake: e.target.value.replace(/\D/g, '').slice(0, 6)})} required />
                  </div>
                  <div className="form-group">
                    <label>Day of Intake</label>
                    <input className="form-control" value={form.intake_day} placeholder="e.g. 02"
                      pattern="\d{2}" maxLength={2} title="2 digits, e.g. 02"
                      onChange={(e) => setForm({...form, intake_day: e.target.value.replace(/\D/g, '').slice(0, 2)})} required />
                  </div>
                </div>
                <small className="mb-16" style={{ display: 'block', color: 'var(--gray-400)' }}>
                  Student ID will be auto-generated, e.g. {form.semester_intake || '202401'}{form.intake_day || '02'}0001
                </small>
                <div className="grid-2">
                  <div className="form-group">
                    <label>Full Name</label>
                    <input className="form-control" value={form.full_name}
                      onChange={(e) => setForm({...form, full_name: e.target.value})} required />
                  </div>
                  <div className="form-group">
                    <label>IC / Passport Number</label>
                    <input className="form-control" value={form.ic_passport}
                      onChange={(e) => setForm({...form, ic_passport: e.target.value})} required />
                  </div>
                </div>
                <div className="form-group">
                  <label>Programme</label>
                  <select className="form-control" value={form.programme_code}
                    onChange={(e) => setForm({...form, programme_code: e.target.value})} required>
                    {programmes.map((p) => (
                      <option key={p.programme_code} value={p.programme_code}>
                        {p.programme_code} - {p.programme_name}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label>Semester</label>
                  <select className="form-control" value={form.current_semester}
                    onChange={(e) => setForm({...form, current_semester: parseInt(e.target.value)})}>
                    {Array.from(
                      { length: programmes.find((p) => p.programme_code === form.programme_code)?.total_semesters || 9 },
                      (_, i) => i + 1
                    ).map(s => <option key={s} value={s}>Semester {s}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label>Status</label>
                  <select className="form-control" value={form.status}
                    onChange={(e) => setForm({...form, status: e.target.value})}>
                    <option value="active">Active</option>
                    <option value="probation">On Probation</option>
                  </select>
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-outline" onClick={closeModal}>Cancel</button>
                <button type="submit" className="btn btn-primary">Create Student</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {editStudent && editForm && (
        <div className="modal-overlay" onClick={closeEditModal}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Edit Student &mdash; {editStudent.user.student_id}</h3>
              <button className="close-btn" onClick={closeEditModal}>&times;</button>
            </div>
            <form onSubmit={handleEditSave}>
              <div className="modal-body">
                {editError && <div className="alert alert-error">{editError}</div>}
                <div className="form-group">
                  <label>Passport-size Photo</label>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    {editPhotoPreview ? (
                      <img className="student-photo student-photo-lg" src={editPhotoPreview} alt="Preview" />
                    ) : (
                      <span className="student-photo student-photo-lg student-photo-placeholder">
                        <span className="material-symbols-outlined">person</span>
                      </span>
                    )}
                    <input type="file" accept="image/*" className="form-control" onChange={handleEditPhotoChange} />
                  </div>
                </div>
                <div className="grid-2">
                  <div className="form-group">
                    <label>Full Name</label>
                    <input className="form-control" value={editForm.full_name}
                      onChange={(e) => setEditForm({ ...editForm, full_name: e.target.value })} required />
                  </div>
                  <div className="form-group">
                    <label>IC / Passport Number</label>
                    <input className="form-control" value={editForm.ic_passport}
                      onChange={(e) => setEditForm({ ...editForm, ic_passport: e.target.value })} required />
                  </div>
                </div>
                <div className="form-group">
                  <label>Programme</label>
                  <select className="form-control" value={editForm.programme_code}
                    onChange={(e) => setEditForm({ ...editForm, programme_code: e.target.value })} required>
                    {programmes.map((p) => (
                      <option key={p.programme_code} value={p.programme_code}>
                        {p.programme_code} - {p.programme_name}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="grid-2">
                  <div className="form-group">
                    <label>Semester</label>
                    <select className="form-control" value={editForm.current_semester}
                      onChange={(e) => setEditForm({ ...editForm, current_semester: parseInt(e.target.value) })}>
                      {Array.from(
                        { length: programmes.find((p) => p.programme_code === editForm.programme_code)?.total_semesters || 9 },
                        (_, i) => i + 1
                      ).map(s => <option key={s} value={s}>Semester {s}</option>)}
                    </select>
                  </div>
                  <div className="form-group">
                    <label>Status</label>
                    <select className="form-control" value={editForm.status}
                      onChange={(e) => setEditForm({ ...editForm, status: e.target.value })}>
                      <option value="active">Active</option>
                      <option value="probation">On Probation</option>
                      <option value="graduated">Graduated</option>
                      <option value="suspended">Suspended</option>
                    </select>
                  </div>
                </div>
                <div className="grid-2">
                  <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 'normal' }}>
                    <input type="checkbox" checked={editForm.is_repeat}
                      onChange={(e) => setEditForm({ ...editForm, is_repeat: e.target.checked })} />
                    Repeat Student
                  </label>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 'normal' }}>
                    <input type="checkbox" checked={editForm.is_transfer}
                      onChange={(e) => setEditForm({ ...editForm, is_transfer: e.target.checked })} />
                    Transfer Student
                  </label>
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-outline" onClick={closeEditModal}>Cancel</button>
                <button type="submit" className="btn btn-primary" disabled={editSaving}>
                  {editSaving ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {detailStudent && (
        <div className="modal-overlay" onClick={closeDetail}>
          <div className="modal" style={{ maxWidth: '760px' }} onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{detailStudent.user.full_name}</h3>
              <button className="close-btn" onClick={closeDetail}>&times;</button>
            </div>
            <div className="modal-body">
              <div style={{ display: 'flex', gap: '20px', marginBottom: '24px' }}>
                {detailStudent.photo ? (
                  <img className="student-photo student-photo-lg" src={resolveMediaUrl(detailStudent.photo)} alt="" />
                ) : (
                  <span className="student-photo student-photo-lg student-photo-placeholder">
                    <span className="material-symbols-outlined">person</span>
                  </span>
                )}
                <div className="grid-2" style={{ flex: 1, gap: '8px 20px' }}>
                  <div><strong>Student ID:</strong> {detailStudent.user.student_id}</div>
                  <div><strong>IC / Passport:</strong> {detailStudent.user.ic_passport}</div>
                  <div><strong>Programme:</strong> {detailStudent.programme.programme_code} - {detailStudent.programme.programme_name}</div>
                  <div><strong>Semester:</strong> {detailStudent.current_semester}</div>
                  <div><strong>Status:</strong> {statusBadge(detailStudent.status)}</div>
                  <div><strong>CGPA:</strong> {detailStudent.cgpa}</div>
                  <div><strong>Credits Earned:</strong> {detailStudent.total_credits_earned}</div>
                  <div>
                    {detailStudent.is_repeat && <span className="badge badge-yellow" style={{ marginRight: '6px' }}>Repeat</span>}
                    {detailStudent.is_transfer && <span className="badge badge-blue">Transfer</span>}
                    {!detailStudent.is_repeat && !detailStudent.is_transfer && '—'}
                  </div>
                </div>
              </div>

              {(() => {
                const semesterCodes = [...new Set(detailSubjects.map((e) => e.semester))].sort().reverse();
                const semesterSubjects = detailSubjects.filter((e) => e.semester === detailSelectedSemester);
                return (
                  <>
                    <div className="flex-between mb-16">
                      <h4>Assigned Subjects</h4>
                      {detailSelectedSemester && <span className="badge badge-blue">{detailSelectedSemester}</span>}
                    </div>
                    {semesterCodes.length > 1 && (
                      <div className="tab-row mb-16">
                        {semesterCodes.map((code) => (
                          <button
                            key={code}
                            className={`tab-item${code === detailSelectedSemester ? ' active' : ''}`}
                            onClick={() => setDetailSelectedSemester(code)}
                          >
                            {code}
                          </button>
                        ))}
                      </div>
                    )}
                    {detailLoading ? (
                      <div className="loading-screen">Loading subjects...</div>
                    ) : (
                      <div className="table-container">
                        <table>
                          <thead>
                            <tr>
                              <th>Subject</th>
                              <th>Credits</th>
                              <th>Status</th>
                              <th>Result</th>
                              <th>Day</th>
                              <th>Time</th>
                              <th>Venue</th>
                            </tr>
                          </thead>
                          <tbody>
                            {semesterSubjects.map((e) => (
                              e.time_slots.length > 0 ? e.time_slots.map((slot) => (
                                <tr key={`${e.id}-${slot.id}`}>
                                  <td>{e.subject.subject_code} - {e.subject.subject_name}</td>
                                  <td>{e.subject.credit_hours}</td>
                                  <td>{e.status}</td>
                                  <td>{resultBadge(e.grade)}</td>
                                  <td>{DAY_LABELS[slot.day_of_week]}</td>
                                  <td>{slot.start_time.slice(0, 5)}–{slot.end_time.slice(0, 5)}</td>
                                  <td>{slot.venue || '—'}</td>
                                </tr>
                              )) : (
                                <tr key={e.id}>
                                  <td>{e.subject.subject_code} - {e.subject.subject_name}</td>
                                  <td>{e.subject.credit_hours}</td>
                                  <td>{e.status}</td>
                                  <td>{resultBadge(e.grade)}</td>
                                  <td colSpan="3" style={{ color: 'var(--gray-400)' }}>No time slot scheduled</td>
                                </tr>
                              )
                            ))}
                            {semesterSubjects.length === 0 && (
                              <tr><td colSpan="7" className="empty-state">No subjects assigned yet</td></tr>
                            )}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </>
                );
              })()}
            </div>
            <div className="modal-footer">
              <button type="button" className="btn btn-outline" onClick={closeDetail}>Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
