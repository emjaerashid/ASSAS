import { useState, useEffect } from 'react';
import api, { resolveMediaUrl } from '../../utils/api';

const DAY_LABELS = {
  mon: 'Monday', tue: 'Tuesday', wed: 'Wednesday', thu: 'Thursday',
  fri: 'Friday', sat: 'Saturday', sun: 'Sunday',
};

const WEEKDAYS = [
  { key: 'mon', label: 'Mon' },
  { key: 'tue', label: 'Tue' },
  { key: 'wed', label: 'Wed' },
  { key: 'thu', label: 'Thu' },
  { key: 'fri', label: 'Fri' },
];

const SLOT_COLORS = ['red', 'sky', 'teal', 'green', 'amber'];
const COL_MINUTES = 30;
const DAY_LABEL_WIDTH = 56;
const ROW_HEIGHT = 70;

function timeToMinutes(t) {
  const [h, m] = t.split(':').map(Number);
  return h * 60 + m;
}

function WeeklyTimetableGrid({ slots }) {
  const weekdaySlots = slots.filter((s) => WEEKDAYS.some((d) => d.key === s.day_of_week));

  if (weekdaySlots.length === 0) {
    return (
      <p style={{ color: 'var(--gray-500)', fontSize: '13px' }}>
        No weekday time slots have been registered for your assigned subjects yet.
      </p>
    );
  }

  let minMinutes = Math.min(8 * 60, ...weekdaySlots.map((s) => timeToMinutes(s.start_time)));
  let maxMinutes = Math.max(18 * 60, ...weekdaySlots.map((s) => timeToMinutes(s.end_time)));
  minMinutes = Math.floor(minMinutes / 60) * 60;
  maxMinutes = Math.ceil(maxMinutes / 60) * 60;
  const totalCols = (maxMinutes - minMinutes) / COL_MINUTES;

  const hourMarks = [];
  for (let m = minMinutes; m < maxMinutes; m += 60) hourMarks.push(m);

  const colLine = (minutes) => Math.round((minutes - minMinutes) / COL_MINUTES) + 2; // col 1 is the day label

  const subjectColor = {};
  [...weekdaySlots]
    .sort((a, b) => a.subject_code.localeCompare(b.subject_code))
    .forEach((s) => {
      if (!(s.subject_code in subjectColor)) {
        subjectColor[s.subject_code] = SLOT_COLORS[Object.keys(subjectColor).length % SLOT_COLORS.length];
      }
    });

  return (
    <div>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: `${DAY_LABEL_WIDTH}px repeat(${totalCols}, minmax(0, 1fr))`,
          gridTemplateRows: `26px repeat(5, ${ROW_HEIGHT}px)`,
          width: '100%',
          border: '1px solid var(--gray-200)',
          borderRadius: 'var(--radius)',
          overflow: 'hidden',
          background: 'var(--white)',
        }}
      >
        <div style={{ gridColumn: 1, gridRow: 1, background: 'var(--gray-50)', borderBottom: '1px solid var(--gray-200)' }} />
        {WEEKDAYS.map((d, i) => (
          <div
            key={d.key}
            style={{
              gridColumn: 1, gridRow: i + 2, background: 'var(--gray-50)',
              borderTop: '1px solid var(--gray-200)', borderRight: '1px solid var(--gray-200)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontWeight: 600, fontSize: '14px', color: 'var(--gray-800)',
            }}
          >
            {d.label}
          </div>
        ))}

        {hourMarks.map((m) => (
          <div
            key={`label-${m}`}
            style={{
              gridRow: 1,
              gridColumn: `${colLine(m)} / span 2`,
              borderLeft: '1px solid var(--gray-100)',
              fontSize: '12px', color: 'var(--gray-500)',
              padding: '4px 0 0 4px',
            }}
          >
            {String(Math.floor(m / 60)).padStart(2, '0')}:00
          </div>
        ))}
        {/* Right edge of the last hour column doesn't get its own mark from the loop above
            (it's the end boundary, not a start), so label it explicitly - otherwise the grid
            looks like it stops an hour earlier than it actually does. */}
        <div
          key="label-end"
          style={{
            gridRow: 1,
            gridColumn: `${colLine(maxMinutes - 60)} / span 2`,
            fontSize: '12px', color: 'var(--gray-500)',
            padding: '4px 4px 0 0',
            textAlign: 'right',
          }}
        >
          {String(Math.floor(maxMinutes / 60)).padStart(2, '0')}:00
        </div>

        {WEEKDAYS.map((d, i) => hourMarks.map((m) => (
          <div
            key={`grid-${d.key}-${m}`}
            style={{
              gridRow: i + 2,
              gridColumn: `${colLine(m)} / span 2`,
              borderLeft: '1px solid var(--gray-100)',
              borderTop: '1px solid var(--gray-200)',
            }}
          />
        )))}

        {weekdaySlots.map((s) => {
          const dayIndex = WEEKDAYS.findIndex((d) => d.key === s.day_of_week);
          const color = subjectColor[s.subject_code];
          return (
            <div
              key={s.id}
              style={{
                gridRow: dayIndex + 2,
                gridColumn: `${colLine(timeToMinutes(s.start_time))} / ${colLine(timeToMinutes(s.end_time))}`,
                margin: '3px 2px',
                padding: '4px 8px',
                borderRadius: '6px',
                background: `var(--${color}-light)`,
                border: `1px solid var(--${color}-border)`,
                borderTop: `3px solid var(--${color})`,
                fontSize: '12px',
                lineHeight: 1.25,
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'center',
                gap: '2px',
                overflow: 'hidden',
                zIndex: 1,
              }}
              title={`${s.subject_code} - ${s.subject_name}\n${s.start_time.slice(0, 5)}–${s.end_time.slice(0, 5)}\n${s.venue || 'No venue'}`}
            >
              <div style={{ fontWeight: 600, color: `var(--${color}-dark)`, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {s.subject_code} - {s.subject_name}
              </div>
              <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--gray-800)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {s.start_time.slice(0, 5)}–{s.end_time.slice(0, 5)}
              </div>
              <div style={{ fontSize: '11px', color: 'var(--gray-600)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {s.venue || '—'}
              </div>
            </div>
          );
        })}
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px 16px', marginTop: '12px' }}>
        {Object.entries(subjectColor).map(([code, color]) => {
          const slot = weekdaySlots.find((s) => s.subject_code === code);
          return (
            <div key={code} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', color: 'var(--gray-700)' }}>
              <span style={{ width: '10px', height: '10px', borderRadius: '3px', background: `var(--${color})`, display: 'inline-block' }} />
              {code} - {slot?.subject_name}
            </div>
          );
        })}
      </div>
    </div>
  );
}

const DAY_ORDER = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'];

// Opens on today's weekday (falling back to the first day with classes) so
// students land on the schedule that matters right now.
function todayKey() {
  return DAY_ORDER[(new Date().getDay() + 6) % 7];
}

function MasterTimetable({ timetable: tt, defaultOpen }) {
  const [open, setOpen] = useState(defaultOpen);
  const slots = [...(tt.time_slots || [])].sort((a, b) => (
    DAY_ORDER.indexOf(a.day_of_week) - DAY_ORDER.indexOf(b.day_of_week)
    || a.start_time.localeCompare(b.start_time)
  ));
  const days = DAY_ORDER.filter((d) => slots.some((s) => s.day_of_week === d));
  const [day, setDay] = useState(() => (days.includes(todayKey()) ? todayKey() : days[0] || 'all'));
  const shown = day === 'all' ? slots : slots.filter((s) => s.day_of_week === day);

  return (
    <div className="card">
      <div className="card-header" style={{ cursor: 'pointer' }} onClick={() => setOpen((o) => !o)}>
        <div>
          <h3>{tt.title}</h3>
          <div style={{ fontSize: '12px', color: 'var(--gray-500)', marginTop: '2px' }}>
            Uploaded on {new Date(tt.uploaded_at).toLocaleDateString()} · {slots.length} classes
          </div>
        </div>
        <div className="btn-group" style={{ alignItems: 'center' }}>
          <span className="badge badge-blue">{tt.semester}</span>
          <span className="material-symbols-outlined" style={{ color: 'var(--gray-500)', transition: 'transform 0.2s', transform: open ? 'rotate(180deg)' : 'none' }}>
            expand_more
          </span>
        </div>
      </div>
      {open && (
        <>
          {tt.file && !tt.file.endsWith('.pdf') && (
            <div className="card-body">
              <img
                src={resolveMediaUrl(tt.file)}
                alt={tt.title}
                style={{ maxWidth: '100%', borderRadius: '8px', border: '1px solid var(--gray-200)' }}
              />
            </div>
          )}
          {slots.length > 0 && (
            <>
              <div className="tab-row">
                {days.map((d) => (
                  <button key={d} className={`tab-item${day === d ? ' active' : ''}`} onClick={() => setDay(d)}>
                    {DAY_LABELS[d]}
                    {d === todayKey() && <span className="badge badge-gray" style={{ marginLeft: '6px', padding: '0 6px' }}>Today</span>}
                  </button>
                ))}
                <button className={`tab-item${day === 'all' ? ' active' : ''}`} onClick={() => setDay('all')}>All days</button>
              </div>
              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      {day === 'all' && <th>Day</th>}
                      <th>Time</th>
                      <th>Subject</th>
                      <th>Venue</th>
                    </tr>
                  </thead>
                  <tbody>
                    {shown.map((s) => (
                      <tr key={s.id}>
                        {day === 'all' && <td>{DAY_LABELS[s.day_of_week]}</td>}
                        <td className="mono">{s.start_time.slice(0, 5)}–{s.end_time.slice(0, 5)}</td>
                        <td><strong className="mono">{s.subject_code}</strong> {s.subject_name}</td>
                        <td>{s.venue || '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}

export default function StudentTimetables() {
  const [timetables, setTimetables] = useState([]);
  const [loading, setLoading] = useState(true);
  const [myTimetable, setMyTimetable] = useState(null);
  const [myLoading, setMyLoading] = useState(true);

  useEffect(() => {
    api.get('/student/timetables/')
      .then(setTimetables)
      .catch(console.error)
      .finally(() => setLoading(false));

    api.get('/student/my-timetable/')
      .then(setMyTimetable)
      .catch(console.error)
      .finally(() => setMyLoading(false));
  }, []);

  return (
    <div>
      <div className="page-header">
        <h1>Timetables</h1>
        <p>Your personal class schedule and your programme's master timetables</p>
      </div>

      <div className="card" style={{ marginBottom: '16px' }}>
        <div className="card-header">
          <h3>My Timetable</h3>
          {myTimetable?.semester && <span className="badge badge-blue">{myTimetable.semester}</span>}
        </div>
        <div className="card-body">
          {myLoading ? (
            <div className="loading-screen">Loading your timetable...</div>
          ) : !myTimetable?.semester || myTimetable.slots.length === 0 ? (
            <p style={{ color: 'var(--gray-500)', fontSize: '13px' }}>
              You don't have any assigned subjects with a scheduled time slot yet. This appears
              automatically once subjects have been assigned to you and venues/times are set.
            </p>
          ) : (
            <WeeklyTimetableGrid slots={myTimetable.slots} />
          )}
        </div>
      </div>

      <div className="page-header">
        <h1>Faculty Timetables</h1>
        <p>View master timetables for your programme</p>
      </div>

      {loading ? (
        <div className="loading-screen">Loading timetables...</div>
      ) : timetables.length === 0 ? (
        <div className="card">
          <div className="card-body empty-state">
            <p>No timetables have been uploaded for your programme yet.</p>
          </div>
        </div>
      ) : (
        <div style={{ display: 'grid', gap: '16px' }}>
          {timetables.map((tt, i) => (
            <MasterTimetable key={tt.id} timetable={tt} defaultOpen={i === 0} />
          ))}
        </div>
      )}
    </div>
  );
}
