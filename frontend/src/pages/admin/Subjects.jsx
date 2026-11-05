import { useState, useEffect } from 'react';
import api from '../../utils/api';
import { useFeedback } from '../../context/FeedbackContext';

const emptyForm = {
  subject_code: '', subject_name: '', credit_hours: 3,
  programme_codes: [], semester: 1, prerequisite_codes: [],
};

export default function Subjects() {
  const { toast, confirm } = useFeedback();
  const [subjects, setSubjects] = useState([]);
  const [programmes, setProgrammes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [programmeFilter, setProgrammeFilter] = useState('');
  const [semFilter, setSemFilter] = useState('');

  const [showModal, setShowModal] = useState(false);
  const [editingCode, setEditingCode] = useState(null);
  const [form, setForm] = useState(emptyForm);
  const [error, setError] = useState('');
  const [prerequisiteOptions, setPrerequisiteOptions] = useState([]);

  useEffect(() => {
    api.get('/programmes/')
      .then((data) => {
        setProgrammes(data);
        if (data.length > 0) {
          setProgrammeFilter(data[0].programme_code);
          setForm((f) => ({ ...f, programme_codes: [data[0].programme_code] }));
        }
      })
      .catch(console.error);
  }, []);

  const fetchSubjects = () => {
    if (!programmeFilter) return;
    setLoading(true);
    let query = `?programme=${programmeFilter}`;
    if (semFilter) query += `&semester=${semFilter}`;

    api.get(`/subjects/${query}`)
      .then(setSubjects)
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(fetchSubjects, [programmeFilter, semFilter]);

  useEffect(() => {
    if (!showModal || !programmeFilter) {
      setPrerequisiteOptions([]);
      return;
    }
    api.get(`/subjects/?programme=${programmeFilter}`)
      .then(setPrerequisiteOptions)
      .catch(console.error);
  }, [showModal, programmeFilter]);

  const selectedProgramme = programmes.find((p) => p.programme_code === programmeFilter);

  const openCreateModal = () => {
    setEditingCode(null);
    const defaultCode = programmeFilter || (programmes[0]?.programme_code ?? '');
    setForm({ ...emptyForm, programme_codes: defaultCode ? [defaultCode] : [] });
    setError('');
    setShowModal(true);
  };

  const openEditModal = (s) => {
    setEditingCode(s.subject_code);
    setForm({
      subject_code: s.subject_code,
      subject_name: s.subject_name,
      credit_hours: s.credit_hours,
      programme_codes: s.programmes.map((p) => p.programme_code),
      semester: s.semester,
      prerequisite_codes: s.prerequisites.map((p) => p.subject_code),
    });
    setError('');
    setShowModal(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (form.programme_codes.length === 0) {
      setError('Select at least one programme.');
      return;
    }
    try {
      if (editingCode) {
        await api.put(`/admin/subjects/${editingCode}/`, form);
        toast.success('Subject updated.');
      } else {
        await api.post('/admin/subjects/', form);
        toast.success('Subject created.');
      }
      setShowModal(false);
      fetchSubjects();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDelete = async (code) => {
    if (!(await confirm({ title: `Delete subject ${code}?`, message: 'This cannot be undone.', confirmLabel: 'Delete', danger: true }))) return;
    try {
      await api.delete(`/admin/subjects/${code}/`);
      fetchSubjects();
    } catch (err) {
      toast.error(err.message);
    }
  };

  const eligiblePrerequisites = prerequisiteOptions.filter((s) => s.subject_code !== form.subject_code);

  return (
    <div>
      <div className="page-header flex-between">
        <div>
          <h1>Subject Catalogue</h1>
          <p>{selectedProgramme ? `${selectedProgramme.programme_name} subjects and prerequisites` : 'Programme subjects and prerequisites'}</p>
        </div>
        <button className="btn btn-primary" onClick={openCreateModal}>
          <span className="material-symbols-outlined">add</span>Add Subject
        </button>
      </div>


      <div className="mb-16" style={{ display: 'flex', gap: '12px' }}>
        <select className="form-control" style={{ width: '220px' }} value={programmeFilter}
          onChange={(e) => setProgrammeFilter(e.target.value)}>
          {programmes.map((p) => (
            <option key={p.programme_code} value={p.programme_code}>{p.programme_code} - {p.programme_name}</option>
          ))}
        </select>
        <select className="form-control" style={{ width: '180px' }} value={semFilter}
          onChange={(e) => setSemFilter(e.target.value)}>
          <option value="">All Semesters</option>
          {Array.from({ length: selectedProgramme?.total_semesters || 9 }, (_, i) => i + 1).map((s) => (
            <option key={s} value={s}>Semester {s}</option>
          ))}
        </select>
      </div>

      <div className="card">
        <div className="table-container">
          {loading ? (
            <div className="loading-screen">Loading subjects...</div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Code</th>
                  <th>Subject Name</th>
                  <th>Credits</th>
                  <th>Semester</th>
                  <th>Programmes</th>
                  <th>Prerequisites</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {subjects.map((s) => (
                  <tr key={s.subject_code}>
                    <td><strong>{s.subject_code}</strong></td>
                    <td>{s.subject_name}</td>
                    <td>{s.credit_hours}</td>
                    <td>{s.semester}</td>
                    <td>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                        {s.programmes.map((p) => (
                          <span key={p.programme_code} className="badge badge-gray" title={p.programme_name}>
                            {p.programme_code}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td>
                      {s.prerequisites.length > 0 ? (
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                          {s.prerequisites.map((p) => (
                            <span key={p.subject_code} className="badge badge-blue" title={p.subject_name}>
                              {p.subject_code}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span style={{ color: 'var(--gray-400)' }}>None</span>
                      )}
                    </td>
                    <td>
                      <div className="btn-group">
                        <button className="btn btn-secondary btn-sm" onClick={() => openEditModal(s)}>
                          Edit
                        </button>
                        <button className="btn btn-danger btn-sm" onClick={() => handleDelete(s.subject_code)}>
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {subjects.length === 0 && (
                  <tr><td colSpan="7" className="empty-state">No subjects found</td></tr>
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
              <h3>{editingCode ? `Edit Subject ${editingCode}` : 'Add New Subject'}</h3>
              <button className="close-btn" onClick={() => setShowModal(false)}>&times;</button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="modal-body">
                {error && <div className="alert alert-error">{error}</div>}
                <div className="grid-2">
                  <div className="form-group">
                    <label>Subject Code</label>
                    <input className="form-control" value={form.subject_code}
                      onChange={(e) => setForm({ ...form, subject_code: e.target.value })}
                      disabled={!!editingCode} required />
                  </div>
                  <div className="form-group">
                    <label>Subject Name</label>
                    <input className="form-control" value={form.subject_name}
                      onChange={(e) => setForm({ ...form, subject_name: e.target.value })} required />
                  </div>
                </div>
                <div className="form-group">
                  <label>Programmes</label>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', maxHeight: '140px', overflowY: 'auto' }}>
                    {programmes.map((p) => (
                      <label key={p.programme_code} style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 'normal' }}>
                        <input
                          type="checkbox"
                          checked={form.programme_codes.includes(p.programme_code)}
                          onChange={(e) => setForm({
                            ...form,
                            programme_codes: e.target.checked
                              ? [...form.programme_codes, p.programme_code]
                              : form.programme_codes.filter((c) => c !== p.programme_code),
                          })}
                        />
                        {p.programme_code} - {p.programme_name}
                      </label>
                    ))}
                  </div>
                  <small style={{ color: 'var(--gray-400)' }}>
                    A subject shared across programmes (e.g. faculty-wide core courses) can belong to more than one
                  </small>
                </div>
                <div className="grid-2">
                  <div className="form-group">
                    <label>Credit Hours</label>
                    <input type="number" min="1" className="form-control" value={form.credit_hours}
                      onChange={(e) => setForm({ ...form, credit_hours: parseInt(e.target.value) })} required />
                  </div>
                  <div className="form-group">
                    <label>Semester</label>
                    <select className="form-control" value={form.semester}
                      onChange={(e) => setForm({ ...form, semester: parseInt(e.target.value) })}>
                      {Array.from(
                        {
                          length: Math.max(
                            9,
                            ...form.programme_codes.map(
                              (code) => programmes.find((p) => p.programme_code === code)?.total_semesters || 9
                            )
                          ),
                        },
                        (_, i) => i + 1
                      ).map((s) => <option key={s} value={s}>Semester {s}</option>)}
                    </select>
                  </div>
                </div>
                <div className="form-group">
                  <label>Prerequisites</label>
                  <select multiple className="form-control" style={{ height: '120px' }}
                    value={form.prerequisite_codes}
                    onChange={(e) => setForm({
                      ...form,
                      prerequisite_codes: Array.from(e.target.selectedOptions, (o) => o.value),
                    })}>
                    {eligiblePrerequisites.map((s) => (
                      <option key={s.subject_code} value={s.subject_code}>
                        {s.subject_code} - {s.subject_name}
                      </option>
                    ))}
                  </select>
                  <small style={{ color: 'var(--gray-400)' }}>Hold Ctrl/Cmd to select multiple</small>
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-outline" onClick={() => setShowModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">
                  {editingCode ? 'Save Changes' : 'Create Subject'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
