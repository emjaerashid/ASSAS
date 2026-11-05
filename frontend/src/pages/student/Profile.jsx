import { useAuth } from '../../context/AuthContext';
import { resolveMediaUrl } from '../../utils/api';

function ReadOnlyField({ label, value, mono = false }) {
  return (
    <div className="form-group">
      <label>{label}</label>
      <input className={`form-control profile-readonly${mono ? ' mono' : ''}`} value={value ?? '—'} readOnly tabIndex={-1} />
    </div>
  );
}

export default function Profile() {
  const { user } = useAuth();
  const student = user?.student_profile;
  const programme = student?.programme;

  if (!student) return <div className="loading-screen">Loading profile...</div>;

  return (
    <div>
      <div className="page-header">
        <h1>My Profile</h1>
        <p>Your student record — contact the faculty office if any details are incorrect</p>
      </div>

      <div className="card mb-24">
        <div className="card-header profile-section-bar"><h3>Personal Details</h3></div>
        <div className="card-body profile-details">
          <div className="profile-fields">
            <ReadOnlyField label="Name" value={user.full_name} />
            <div className="grid-2">
              <ReadOnlyField label="NRIC / Passport No." value={user.ic_passport} mono />
              <ReadOnlyField label="Student No." value={user.student_id} mono />
            </div>
            <div className="grid-2">
              <ReadOnlyField label="Current Semester" value={`Semester ${student.current_semester}`} />
              <ReadOnlyField label="Status" value={student.status ? student.status[0].toUpperCase() + student.status.slice(1) : '—'} />
            </div>
            <div className="grid-2">
              <ReadOnlyField label="CGPA" value={student.cgpa} />
              <ReadOnlyField label="Credits Earned" value={`${student.total_credits_earned} / ${programme?.total_credits ?? '—'}`} />
            </div>
            <div className="grid-2">
              <ReadOnlyField label="Credit Cap per Semester" value={student.effective_credit_cap} />
              <ReadOnlyField label="Registered Since" value={user.date_joined ? new Date(user.date_joined).toLocaleDateString() : '—'} />
            </div>
          </div>
          <div className="profile-photo">
            {student.photo ? (
              <img src={resolveMediaUrl(student.photo)} alt={user.full_name} />
            ) : (
              <span className="material-symbols-outlined">person</span>
            )}
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header"><h3>Programme</h3></div>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Programme Code</th>
                <th>Programme Name</th>
                <th>Faculty</th>
                <th>Current Status</th>
                <th>Student Type</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><strong className="mono">{programme?.programme_code}</strong></td>
                <td>{programme?.programme_name}</td>
                <td>{programme?.faculty_name || programme?.faculty || '—'}</td>
                <td style={{ textTransform: 'capitalize' }}>{student.status}</td>
                <td>{[student.is_repeat && 'Repeat', student.is_transfer && 'Transfer'].filter(Boolean).join(', ') || 'Regular'}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
}
