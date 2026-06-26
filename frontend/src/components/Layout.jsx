import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const isAdmin = user?.role === 'admin';

  return (
    <div className="app-layout">
      <nav className="sidebar">
        <div className="sidebar-header">
          <h2>ASSAS</h2>
          <p className="sidebar-subtitle">Subject Assignment System</p>
        </div>

        <div className="sidebar-nav">
          {isAdmin ? (
            <>
              <NavLink to="/admin" end>Dashboard</NavLink>
              <NavLink to="/admin/students">Students</NavLink>
              <NavLink to="/admin/assign">Assign Subjects</NavLink>
              <NavLink to="/admin/exceptions">Exceptions</NavLink>
              <NavLink to="/admin/add-drop">Add/Drop Requests</NavLink>
              <NavLink to="/admin/timetables">Timetables</NavLink>
              <NavLink to="/admin/subjects">Subjects</NavLink>
            </>
          ) : (
            <>
              <NavLink to="/student" end>My Subjects</NavLink>
              <NavLink to="/student/progress">Progress</NavLink>
              <NavLink to="/student/add-drop">Add/Drop Request</NavLink>
              <NavLink to="/student/exceptions">Exceptions</NavLink>
              <NavLink to="/student/timetables">Timetables</NavLink>
            </>
          )}
        </div>

        <div className="sidebar-footer">
          <div className="user-info">
            <span className="user-name">{user?.full_name}</span>
            <span className="user-role">{user?.role === 'admin' ? 'Administrator' : user?.student_id}</span>
          </div>
          <button className="btn btn-outline btn-sm" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </nav>

      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}
