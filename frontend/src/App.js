import { useEffect, useState } from "react";
import axios from "axios";
import { QRCodeSVG } from "qrcode.react";
import {
  Activity,
  Award,
  BarChart3,
  Briefcase,
  Check,
  ChevronRight,
  Clock3,
  Download,
  GraduationCap,
  LayoutDashboard,
  LogOut,
  MapPin,
  Pencil,
  Plus,
  QrCode,
  ScanLine,
  Search,
  Sparkles,
  Target,
  Trash2,
  UserCog,
  Users,
  X,
} from "lucide-react";
import "@/App.css";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const api = axios.create({ baseURL: API, withCredentials: true });

function SignIn({ onLogin }) {
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({ username: "maya", password: "maya1234", name: "", role: "volunteer", department: "" });
  const [skillsInput, setSkillsInput] = useState("Python, Design");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const body =
        mode === "login"
          ? { username: form.username, password: form.password }
          : { ...form, skills: skillsInput.split(",").map((s) => s.trim()).filter(Boolean) };
      const { data } = await api.post(`/auth/${mode}`, body);
      onLogin(data);
    } catch (err) {
      setError(err.response?.data?.detail || "Please check your details and try again.");
    } finally {
      setBusy(false);
    }
  };
  return (
    <main className="auth-shell">
      <div className="auth-image">
        <div className="auth-caption">
          <span className="eyebrow">MIT-WPU · CAMPUS LIFE, MATCHED</span>
          <h1>
            Make your mark<br />
            <em>on campus.</em>
          </h1>
          <p>Find meaningful ways to contribute, meet your people, and leave every event better than you found it.</p>
        </div>
      </div>
      <section className="auth-panel">
        <div className="brand">
          <span className="brand-mark">
            <Sparkles size={17} />
          </span>
          <span>skill<span>match</span></span>
        </div>
        <div className="auth-copy">
          <span className="eyebrow">WELCOME BACK</span>
          <h2>{mode === "login" ? "Your next contribution starts here." : "Join the campus network."}</h2>
          <p>{mode === "login" ? "Sign in to discover events built for your strengths." : "Create a student profile and find your fit."}</p>
        </div>
        <form onSubmit={submit} data-testid="auth-form">
          {mode === "register" && (
            <>
              <Field label="Full name">
                <input data-testid="register-name-input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Alex Johnson" required />
              </Field>
              <Field label="Department">
                <input data-testid="register-department-input" value={form.department} onChange={(e) => setForm({ ...form, department: e.target.value })} placeholder="Computer Science" required />
              </Field>
              <Field label="Role">
                <select data-testid="register-role-select" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
                  <option value="volunteer">Student volunteer</option>
                  <option value="organizer">Event organizer</option>
                </select>
              </Field>
              <Field label="Skills (comma separated)">
                <input data-testid="register-skills-input" value={skillsInput} onChange={(e) => setSkillsInput(e.target.value)} placeholder="Python, Design, Photography" />
              </Field>
            </>
          )}
          <Field label="Username">
            <input data-testid="auth-username-input" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} placeholder="e.g. maya" required />
          </Field>
          <Field label="Password">
            <input data-testid="auth-password-input" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} placeholder="••••••••" required />
          </Field>
          {error && (
            <p className="form-error" data-testid="auth-error">
              {error}
            </p>
          )}
          <button className="primary-btn full" data-testid="auth-submit-button" disabled={busy}>
            {busy ? "Opening your space…" : mode === "login" ? "Enter SkillMatch" : "Create my profile"}
            <ChevronRight size={17} />
          </button>
        </form>
        <button className="text-btn" data-testid="auth-mode-toggle" onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); }}>
          {mode === "login" ? "New to SkillMatch? Create an account" : "Already have an account? Sign in"}
        </button>
        <p className="demo-hint">
          Demo access: <b>maya / maya1234</b> · organizer: <b>campusadmin / admin1234</b>
        </p>
      </section>
    </main>
  );
}

function Field({ label, children }) {
  return (
    <label>
      {label}
      {children}
    </label>
  );
}

function App() {
  const [user, setUser] = useState(null);
  const [events, setEvents] = useState([]);
  const [apps, setApps] = useState([]);
  const [certificates, setCertificates] = useState([]);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState("discover");
  const [modal, setModal] = useState(null); // {type: 'create'|'edit'|'profile'|'qr'|'checkin', payload}
  const [toast, setToast] = useState("");
  const [loading, setLoading] = useState(true);

  const load = async (current) => {
    if (!current) return;
    const [eventRes, extraRes] = await Promise.all([
      api.get("/events"),
      api.get(current.role === "volunteer" ? "/certificates" : "/organizer/applicants"),
    ]);
    setEvents(eventRes.data);
    if (current.role === "volunteer") setCertificates(extraRes.data);
    else setApps(extraRes.data);
  };

  useEffect(() => {
    api.get("/auth/me").then((res) => setUser(res.data)).catch(() => {}).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (user) load(user);
  }, [user]);

  const notify = (message) => {
    setToast(message);
    window.setTimeout(() => setToast(""), 3000);
  };

  const logout = async () => {
    await api.post("/auth/logout");
    setUser(null);
    setEvents([]);
  };

  if (loading) return <div className="loading">Loading your campus…</div>;
  if (!user) return <SignIn onLogin={setUser} />;

  const filtered = events.filter((item) =>
    `${item.title} ${item.description} ${item.location} ${item.required_skills.join(" ")}`.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div className="app-frame">
      <Sidebar
        user={user}
        active={active}
        setActive={setActive}
        certificates={certificates}
        onLogout={logout}
        onSwitch={() => setUser({ ...user, role: user.role === "organizer" ? "volunteer" : "organizer" })}
        onProfile={() => setModal({ type: "profile" })}
      />
      <main className="main-content">
        <header className="topbar">
          <div className="mobile-brand">
            <span className="brand-mark">
              <Sparkles size={15} />
            </span>{" "}
            skillmatch
          </div>
          <div className="topbar-right">
            <span className="campus-pill">
              <span className="live-dot" /> MIT-WPU · Spring 2026
            </span>
            <button className="avatar small avatar-btn" data-testid="open-profile-button" onClick={() => setModal({ type: "profile" })}>
              {user.name[0]}
            </button>
          </div>
        </header>
        {active === "discover" && (
          <Discover
            user={user}
            events={filtered}
            query={query}
            setQuery={setQuery}
            onCreate={() => setModal({ type: "create" })}
            onEdit={(item) => setModal({ type: "edit", payload: item })}
            onDelete={async (item) => {
              if (!window.confirm(`Delete "${item.title}"? This cannot be undone.`)) return;
              try {
                await api.delete(`/events/${item.id}`);
                notify("Event deleted.");
                load(user);
              } catch (err) {
                notify(err.response?.data?.detail || "Could not delete event");
              }
            }}
            onShowQr={(item) => setModal({ type: "qr", payload: item })}
            onCheckin={(item) => setModal({ type: "checkin", payload: item })}
            onApply={async (item) => {
              try {
                await api.post(`/events/${item.id}/apply`);
                notify("You're on the list — the organizer will be in touch.");
                load(user);
              } catch (err) {
                notify(err.response?.data?.detail || "Could not join this event");
              }
            }}
          />
        )}
        {active === "certificates" && <Certificates certificates={certificates} />}
        {active === "insights" && <Insights user={user} />}
        {active === "manage" && (
          <Manage
            apps={apps}
            onUpdate={async (eventId, username, status) => {
              await api.patch(`/applications/${eventId}/${username}`, { status });
              notify(`Application ${status}.`);
              load(user);
            }}
            onComplete={async (eventId, username) => {
              try {
                await api.post(`/events/${eventId}/complete`, { username, hours: 4, notes: "Completed campus contribution" });
                notify("Completion recorded — certificate is ready.");
                load(user);
              } catch (err) {
                notify(err.response?.data?.detail || "Could not record completion");
              }
            }}
            onViewProfile={(username) => setModal({ type: "view-profile", payload: username })}
          />
        )}
        {modal?.type === "create" && (
          <EventModal
            title="Create a campus event"
            eyebrow="NEW OPPORTUNITY"
            onClose={() => setModal(null)}
            onSubmit={async (data) => {
              await api.post("/events", data);
              setModal(null);
              notify("Event published to campus.");
              load(user);
            }}
          />
        )}
        {modal?.type === "edit" && (
          <EventModal
            title="Edit this event"
            eyebrow="UPDATE DETAILS"
            initial={modal.payload}
            onClose={() => setModal(null)}
            onSubmit={async (data) => {
              await api.patch(`/events/${modal.payload.id}`, data);
              setModal(null);
              notify("Event updated.");
              load(user);
            }}
          />
        )}
        {modal?.type === "profile" && (
          <ProfileModal
            user={user}
            onClose={() => setModal(null)}
            onSave={async (data) => {
              const { data: updated } = await api.patch("/auth/me", data);
              setUser(updated);
              setModal(null);
              notify("Profile updated.");
            }}
          />
        )}
        {modal?.type === "qr" && <QrModal event={modal.payload} onClose={() => setModal(null)} />}
        {modal?.type === "view-profile" && (
          <VolunteerProfileModal username={modal.payload} onClose={() => setModal(null)} />
        )}
        {modal?.type === "checkin" && (
          <CheckinModal
            event={modal.payload}
            onClose={() => setModal(null)}
            onCheckin={async (code) => {
              try {
                await api.post(`/events/${modal.payload.id}/checkin`, { code });
                setModal(null);
                notify("Checked in! Your certificate is ready.");
                load(user);
              } catch (err) {
                throw new Error(err.response?.data?.detail || "Could not check in");
              }
            }}
          />
        )}
        {toast && (
          <div className="toast" data-testid="toast-message">
            <Check size={17} /> {toast}
          </div>
        )}
      </main>
    </div>
  );
}

function Sidebar({ user, active, setActive, certificates, onLogout, onSwitch, onProfile }) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <span className="brand-mark">
          <Sparkles size={17} />
        </span>
        <span>skill<span>match</span></span>
      </div>
      <div className="side-profile">
        <div className="avatar">{user.name[0]}</div>
        <div>
          <b>{user.name}</b>
          <small>{user.role === "organizer" ? "Event organizer" : "Student volunteer"}</small>
        </div>
      </div>
      <nav>
        <NavButton active={active === "discover"} test="nav-discover-button" onClick={() => setActive("discover")} icon={<LayoutDashboard size={18} />}>
          Discover
        </NavButton>
        <NavButton active={active === "insights"} test="nav-insights-button" onClick={() => setActive("insights")} icon={<BarChart3 size={18} />}>
          Insights
        </NavButton>
        {user.role === "volunteer" && (
          <NavButton active={active === "certificates"} test="nav-certificates-button" onClick={() => setActive("certificates")} icon={<GraduationCap size={18} />}>
            My certificates {certificates.length > 0 && <i>{certificates.length}</i>}
          </NavButton>
        )}
        {user.role === "organizer" && (
          <NavButton active={active === "manage"} test="nav-manage-button" onClick={() => setActive("manage")} icon={<Users size={18} />}>
            Manage volunteers
          </NavButton>
        )}
        <NavButton test="nav-profile-button" onClick={onProfile} icon={<UserCog size={18} />}>
          Edit profile
        </NavButton>
      </nav>
      <div className="sidebar-bottom">
        <div className="role-note">
          <span className="live-dot" /> {user.role === "organizer" ? "Organizer mode" : "Volunteer mode"}
          <button data-testid="switch-role-button" onClick={onSwitch}>
            <ChevronRight size={14} />
          </button>
        </div>
        <button className="logout-btn" data-testid="logout-button" onClick={onLogout}>
          <LogOut size={16} /> Sign out
        </button>
      </div>
    </aside>
  );
}

function NavButton({ active, test, onClick, icon, children }) {
  return (
    <button className={active ? "nav-active" : ""} data-testid={test} onClick={onClick}>
      {icon}
      {children}
    </button>
  );
}

function Discover({ user, events, query, setQuery, onCreate, onEdit, onDelete, onShowQr, onCheckin, onApply }) {
  return (
    <>
      <section className="welcome">
        <div>
          <span className="eyebrow">{user.role === "organizer" ? "YOUR CAMPUS, YOUR STAGE" : `GOOD MORNING, ${user.name.split(" ")[0].toUpperCase()}`}</span>
          {user.role === "organizer" ? (
            <h1>
              Bring your next idea<br />
              to <em>life.</em>
            </h1>
          ) : (
            <h1>
              Find where you <em>belong.</em>
            </h1>
          )}
          <p>
            {user.role === "organizer"
              ? "Create events, find the right people, and make every moment count."
              : "Opportunities that match what you're good at — and what you want to become."}
          </p>
        </div>
        <div className="welcome-stat">
          <b>{events.length}</b>
          <span>
            active events<br />
            this semester
          </span>
        </div>
      </section>
      <section className="hero-strip">
        <div>
          <span className="eyebrow light">FEATURED · MIT-WPU PUNE</span>
          <h2>
            Small actions.<br />
            <em>Big campus energy.</em>
          </h2>
          <p>Volunteers make the moments people remember.</p>
          <button className="light-btn" data-testid="hero-browse-button" onClick={() => document.getElementById("event-list")?.scrollIntoView({ behavior: "smooth" })}>
            Browse opportunities <ChevronRight size={16} />
          </button>
        </div>
        <div className="hero-visual" />
      </section>
      <section className="content-section" id="event-list">
        <div className="section-head">
          <div>
            <span className="eyebrow">OPEN OPPORTUNITIES</span>
            <h2>Find your next event</h2>
          </div>
          {user.role === "organizer" && (
            <button className="primary-btn" data-testid="create-event-button" onClick={onCreate}>
              <Plus size={17} /> Create event
            </button>
          )}
        </div>
        <div className="filters">
          <div className="search-box">
            <Search size={17} />
            <input data-testid="event-search-input" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search events, skills, or places…" />
          </div>
          <span className="result-count" data-testid="event-count">
            {events.length} events
          </span>
        </div>
        <div className="event-grid">
          {events.map((item, index) => (
            <EventCard
              key={item.id}
              event={item}
              user={user}
              onApply={() => onApply(item)}
              onEdit={() => onEdit(item)}
              onDelete={() => onDelete(item)}
              onShowQr={() => onShowQr(item)}
              onCheckin={() => onCheckin(item)}
              index={index}
            />
          ))}
        </div>
        {events.length === 0 && (
          <div className="empty">
            <Search size={25} />
            <b>No events found</b>
            <span>Try a different search term.</span>
          </div>
        )}
      </section>
    </>
  );
}

function EventCard({ event, user, onApply, onEdit, onDelete, onShowQr, onCheckin, index }) {
  const joined = ["pending", "accepted", "completed"].includes(event.application);
  const isMine = user.role === "organizer" && event.organizer === user.username;
  const canCheckIn = user.role === "volunteer" && event.application === "accepted";
  return (
    <article className={`event-card card-${index % 3}`} data-testid={`event-card-${event.id}`}>
      <div className="event-card-top">
        <span className="date-block">
          <b>{new Date(`${event.date}T12:00:00`).getDate()}</b>
          <small>{new Date(`${event.date}T12:00:00`).toLocaleDateString("en-US", { month: "short" }).toUpperCase()}</small>
        </span>
        <span className="match-badge">
          {event.match ? (
            <>
              <Sparkles size={12} /> Great match
            </>
          ) : (
            "Open to all"
          )}
        </span>
      </div>
      <div className="event-info">
        <span className="event-type">{event.title.includes("Festival") ? "CAMPUS CULTURE" : event.title.includes("Green") ? "COMMUNITY" : "LEARNING"}</span>
        <h3>{event.title}</h3>
        <p>{event.description}</p>
        <div className="event-meta">
          <span>
            <Clock3 size={14} /> {event.time}
          </span>
          <span>
            <MapPin size={14} /> {event.location}
          </span>
        </div>
      </div>
      <div className="event-footer">
        <div className="skill-list">
          {event.required_skills.slice(0, 2).map((skill) => (
            <span key={skill}>{skill}</span>
          ))}
        </div>
        {user.role === "volunteer" ? (
          <div className="card-actions">
            {canCheckIn && (
              <button className="icon-chip" data-testid={`event-checkin-${event.id}-button`} onClick={onCheckin} title="Check in">
                <ScanLine size={14} />
              </button>
            )}
            <button
              className={joined ? "joined-btn" : "arrow-btn"}
              data-testid={`event-apply-${event.id}-button`}
              onClick={onApply}
              disabled={joined}
            >
              {joined ? (
                <>
                  <Check size={14} /> {event.application}
                </>
              ) : (
                <>
                  Join event <ChevronRight size={16} />
                </>
              )}
            </button>
          </div>
        ) : (
          <div className="card-actions">
            {isMine && (
              <>
                <button className="icon-chip" data-testid={`event-qr-${event.id}-button`} onClick={onShowQr} title="Show check-in QR">
                  <QrCode size={14} />
                </button>
                <button className="icon-chip" data-testid={`event-edit-${event.id}-button`} onClick={onEdit} title="Edit event">
                  <Pencil size={14} />
                </button>
                <button className="icon-chip danger" data-testid={`event-delete-${event.id}-button`} onClick={onDelete} title="Delete event">
                  <Trash2 size={14} />
                </button>
              </>
            )}
            <span className="capacity">
              <Users size={14} /> {event.volunteers}/{event.capacity}
            </span>
          </div>
        )}
      </div>
    </article>
  );
}

function Certificates({ certificates }) {
  return (
    <section className="content-section standalone">
      <div className="section-head">
        <div>
          <span className="eyebrow">YOUR IMPACT</span>
          <h2>Certificates earned</h2>
          <p className="section-sub">Every hour you give becomes part of your campus story — now exported as a printable PDF.</p>
        </div>
      </div>
      {certificates.length ? (
        <div className="certificate-grid">
          {certificates.map((cert) => (
            <div className="certificate" key={cert.event_id} data-testid={`certificate-${cert.event_id}`}>
              <div className="cert-seal">
                <GraduationCap size={24} />
              </div>
              <span className="eyebrow">CERTIFICATE OF COMPLETION</span>
              <h3>{cert.title}</h3>
              <p>
                Thank you for contributing <b>{cert.hours} hours</b> to your campus community.
              </p>
              <a
                className="download-btn"
                data-testid={`certificate-download-${cert.event_id}`}
                href={`${API}/certificates/${cert.event_id}`}
                target="_blank"
                rel="noreferrer"
              >
                <Download size={15} /> Download PDF
              </a>
            </div>
          ))}
        </div>
      ) : (
        <div className="empty">
          <GraduationCap size={25} />
          <b>Your first certificate is waiting</b>
          <span>Complete an event to see it here.</span>
        </div>
      )}
    </section>
  );
}

function Manage({ apps, onUpdate, onComplete, onViewProfile }) {
  return (
    <section className="content-section standalone">
      <div className="section-head">
        <div>
          <span className="eyebrow">ORGANIZER DESK</span>
          <h2>Manage volunteers</h2>
          <p className="section-sub">Review applications and celebrate the people who show up. Tap any name to see their campus story.</p>
        </div>
      </div>
      <div className="app-table">
        {apps.length ? (
          apps.map((app) => (
            <div className="app-row" key={`${app.event_id}-${app.username}`} data-testid={`applicant-row-${app.username}`}>
              <button
                className="avatar avatar-btn"
                data-testid={`view-profile-avatar-${app.username}-button`}
                onClick={() => onViewProfile(app.username)}
                title={`View ${app.name}'s profile`}
              >
                {app.name[0]}
              </button>
              <button
                className="applicant applicant-btn"
                data-testid={`view-profile-${app.username}-button`}
                onClick={() => onViewProfile(app.username)}
              >
                <b>{app.name}</b>
                <span>
                  {app.event_title} · {app.skills.join(" · ") || "Campus contributor"}
                </span>
              </button>
              <span className={`status ${app.status}`}>{app.status}</span>
              {app.status === "pending" && (
                <div className="row-actions">
                  <button data-testid={`accept-${app.username}-button`} onClick={() => onUpdate(app.event_id, app.username, "accepted")}>
                    <Check size={15} />
                  </button>
                  <button data-testid={`reject-${app.username}-button`} onClick={() => onUpdate(app.event_id, app.username, "rejected")}>
                    <X size={15} />
                  </button>
                </div>
              )}
              {app.status === "accepted" && (
                <button className="complete-btn" data-testid={`complete-${app.username}-button`} onClick={() => onComplete(app.event_id, app.username)}>
                  Mark complete <ChevronRight size={14} />
                </button>
              )}
            </div>
          ))
        ) : (
          <div className="empty">
            <Users size={25} />
            <b>No applications yet</b>
            <span>New volunteer applications will appear here.</span>
          </div>
        )}
      </div>
    </section>
  );
}

function EventModal({ title, eyebrow, initial, onClose, onSubmit }) {
  const [data, setData] = useState(
    initial
      ? {
          title: initial.title,
          description: initial.description,
          date: initial.date,
          time: initial.time,
          location: initial.location,
          capacity: initial.capacity,
        }
      : { title: "", description: "", date: "2026-03-15", time: "10:00 AM", location: "", capacity: 20 }
  );
  const [skills, setSkills] = useState(initial ? (initial.required_skills || []).join(", ") : "");
  const [busy, setBusy] = useState(false);
  const update = (key, value) => setData({ ...data, [key]: value });
  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    try {
      await onSubmit({
        ...data,
        capacity: Number(data.capacity),
        required_skills: skills.split(",").map((item) => item.trim()).filter(Boolean),
      });
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="modal-backdrop">
      <form className="modal" onSubmit={submit}>
        <button type="button" className="modal-close" data-testid="close-create-modal-button" onClick={onClose}>
          <X size={18} />
        </button>
        <span className="eyebrow">{eyebrow}</span>
        <h2>{title}</h2>
        <Field label="Event title">
          <input data-testid="create-title-input" value={data.title} onChange={(e) => update("title", e.target.value)} required placeholder="e.g. Design thinking workshop" />
        </Field>
        <Field label="Description">
          <textarea data-testid="create-description-input" value={data.description} onChange={(e) => update("description", e.target.value)} required placeholder="What will volunteers help make happen?" />
        </Field>
        <div className="two-col">
          <Field label="Date">
            <input data-testid="create-date-input" type="date" value={data.date} onChange={(e) => update("date", e.target.value)} required />
          </Field>
          <Field label="Time">
            <input data-testid="create-time-input" value={data.time} onChange={(e) => update("time", e.target.value)} required />
          </Field>
        </div>
        <div className="two-col">
          <Field label="Location">
            <input data-testid="create-location-input" value={data.location} onChange={(e) => update("location", e.target.value)} required placeholder="Student center" />
          </Field>
          <Field label="Volunteer spots">
            <input data-testid="create-capacity-input" type="number" min="1" value={data.capacity} onChange={(e) => update("capacity", e.target.value)} required />
          </Field>
        </div>
        <Field label="Skills needed">
          <input data-testid="create-skills-input" value={skills} onChange={(e) => setSkills(e.target.value)} placeholder="Design, Communication" />
        </Field>
        <button className="primary-btn full" data-testid="create-submit-button" disabled={busy}>
          {busy ? "Saving…" : initial ? "Save changes" : "Publish event"} <ChevronRight size={17} />
        </button>
      </form>
    </div>
  );
}

function ProfileModal({ user, onClose, onSave }) {
  const [data, setData] = useState({
    name: user.name,
    department: user.department,
    skills: (user.skills || []).join(", "),
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await onSave({
        name: data.name,
        department: data.department,
        skills: data.skills.split(",").map((s) => s.trim()).filter(Boolean),
      });
    } catch (err) {
      setError(err.response?.data?.detail || "Could not save profile");
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="modal-backdrop">
      <form className="modal" onSubmit={submit}>
        <button type="button" className="modal-close" data-testid="close-profile-modal-button" onClick={onClose}>
          <X size={18} />
        </button>
        <span className="eyebrow">YOUR PROFILE</span>
        <h2>Keep your details fresh</h2>
        <Field label="Full name">
          <input data-testid="profile-name-input" value={data.name} onChange={(e) => setData({ ...data, name: e.target.value })} required />
        </Field>
        <Field label="Department">
          <input data-testid="profile-department-input" value={data.department} onChange={(e) => setData({ ...data, department: e.target.value })} required />
        </Field>
        <Field label="Skills (comma separated)">
          <input data-testid="profile-skills-input" value={data.skills} onChange={(e) => setData({ ...data, skills: e.target.value })} placeholder="Python, Design, Photography" />
        </Field>
        {error && <p className="form-error">{error}</p>}
        <button className="primary-btn full" data-testid="profile-save-button" disabled={busy}>
          {busy ? "Saving…" : "Save profile"} <ChevronRight size={17} />
        </button>
      </form>
    </div>
  );
}

function QrModal({ event, onClose }) {
  const code = event.checkin_code || "—";
  const payload = `SKILLMATCH|${event.id}|${code}`;
  return (
    <div className="modal-backdrop">
      <div className="modal qr-modal">
        <button type="button" className="modal-close" data-testid="close-qr-modal-button" onClick={onClose}>
          <X size={18} />
        </button>
        <span className="eyebrow">EVENT DAY CHECK-IN</span>
        <h2>{event.title}</h2>
        <p className="section-sub">Volunteers scan this QR or type the code below to mark their attendance — a certificate is issued the moment they check in.</p>
        <div className="qr-wrap" data-testid="qr-code-box">
          <QRCodeSVG value={payload} size={220} bgColor="#f7f8f5" fgColor="#125c4f" />
        </div>
        <div className="qr-code" data-testid="qr-checkin-code">
          {code}
        </div>
        <p className="section-sub">Share this screen at the venue or print it on a flyer.</p>
      </div>
    </div>
  );
}

function CheckinModal({ event, onClose, onCheckin }) {
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await onCheckin(code);
    } catch (err) {
      setError(err.message || "Could not check in");
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="modal-backdrop">
      <form className="modal" onSubmit={submit}>
        <button type="button" className="modal-close" data-testid="close-checkin-modal-button" onClick={onClose}>
          <X size={18} />
        </button>
        <span className="eyebrow">EVENT DAY CHECK-IN</span>
        <h2>{event.title}</h2>
        <p className="section-sub">Ask the organizer for the 6-character code at the venue, enter it below, and your certificate is yours.</p>
        <Field label="Check-in code">
          <input
            data-testid="checkin-code-input"
            value={code}
            onChange={(e) => setCode(e.target.value.toUpperCase())}
            placeholder="ABC123"
            maxLength={12}
            required
            autoFocus
          />
        </Field>
        {error && (
          <p className="form-error" data-testid="checkin-error">
            {error}
          </p>
        )}
        <button className="primary-btn full" data-testid="checkin-submit-button" disabled={busy}>
          {busy ? "Checking in…" : "Confirm attendance"} <ChevronRight size={17} />
        </button>
      </form>
    </div>
  );
}

function Insights({ user }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => {
    const endpoint = user.role === "organizer" ? "/insights/organizer" : "/insights/volunteer";
    api
      .get(endpoint)
      .then((res) => setData(res.data))
      .catch((err) => setError(err.response?.data?.detail || "Could not load insights"));
  }, [user.role]);
  if (error) return <section className="content-section standalone"><div className="empty"><Activity size={25} /><b>{error}</b></div></section>;
  if (!data) return <section className="content-section standalone"><div className="empty"><Activity size={25} /><b>Gathering your numbers…</b></div></section>;
  return user.role === "organizer" ? <OrganizerInsights data={data} /> : <VolunteerInsights data={data} />;
}

function StatCard({ icon, label, value, suffix, testid }) {
  return (
    <div className="stat-card" data-testid={testid}>
      <div className="stat-icon">{icon}</div>
      <b>
        {value}
        {suffix && <small>{suffix}</small>}
      </b>
      <span>{label}</span>
    </div>
  );
}

function OrganizerInsights({ data }) {
  return (
    <section className="content-section standalone" data-testid="organizer-insights">
      <div className="section-head">
        <div>
          <span className="eyebrow">ORGANIZER INSIGHTS</span>
          <h2>Your campus impact</h2>
          <p className="section-sub">A living snapshot of your events, volunteers, and the skills your team covers.</p>
        </div>
      </div>
      <div className="stat-grid">
        <StatCard testid="stat-events" icon={<Briefcase size={18} />} label="Events hosted" value={data.total_events} />
        <StatCard testid="stat-volunteers" icon={<Users size={18} />} label="Unique volunteers" value={data.total_volunteers} />
        <StatCard testid="stat-hours" icon={<Clock3 size={18} />} label="Hours contributed" value={data.total_hours} suffix=" hrs" />
        <StatCard testid="stat-pending" icon={<Activity size={18} />} label="Pending applications" value={data.pending_applications} />
      </div>

      <div className="insight-split">
        <div className="insight-card">
          <span className="eyebrow">SKILL COVERAGE</span>
          <h3>Required skills vs. available volunteers</h3>
          {data.skill_coverage.length ? (
            <div className="skill-coverage">
              {data.skill_coverage.map((row) => {
                const pct = row.required_in_events > 0 ? Math.min(100, (row.available_volunteers / row.required_in_events) * 100) : 0;
                return (
                  <div className="coverage-row" key={row.skill} data-testid={`coverage-${row.skill.replace(/\s+/g, "-").toLowerCase()}`}>
                    <div className="coverage-head">
                      <b>{row.skill}</b>
                      <span>
                        {row.available_volunteers} available · needed in {row.required_in_events}
                      </span>
                    </div>
                    <div className="coverage-bar">
                      <div className="coverage-fill" style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="empty mini">
              <Target size={22} /> <b>No required skills yet</b>
            </div>
          )}
        </div>

        <div className="insight-card">
          <span className="eyebrow">TOP VOLUNTEERS</span>
          <h3>Hours contributed leaderboard</h3>
          {data.top_volunteers.length ? (
            <div className="leaderboard">
              {data.top_volunteers.map((v, i) => (
                <div className="leader-row" key={v.username} data-testid={`leader-${v.username}`}>
                  <span className="leader-rank">{i + 1}</span>
                  <div className="avatar">{v.name[0]}</div>
                  <div className="leader-meta">
                    <b>{v.name}</b>
                    <span>{v.department || "Campus contributor"}</span>
                  </div>
                  <b className="leader-hours">{v.hours} h</b>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty mini">
              <Users size={22} /> <b>No completed events yet</b>
            </div>
          )}
        </div>
      </div>

      <div className="insight-card">
        <span className="eyebrow">PER-EVENT BREAKDOWN</span>
        <h3>How each event is tracking</h3>
        <div className="event-breakdown">
          {data.event_summary.length ? (
            data.event_summary.map((e) => (
              <div className="breakdown-row" key={e.id} data-testid={`breakdown-${e.id}`}>
                <div>
                  <b>{e.title}</b>
                  <span>
                    {e.date} · capacity {e.capacity}
                  </span>
                </div>
                <div className="breakdown-badges">
                  <span className="status accepted">{e.accepted} accepted</span>
                  <span className="status completed">{e.completed} completed</span>
                  {e.pending > 0 && <span className="status">{e.pending} pending</span>}
                </div>
              </div>
            ))
          ) : (
            <div className="empty mini">
              <Briefcase size={22} /> <b>Create your first event to see it here</b>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

function VolunteerInsights({ data }) {
  const all = [...data.events_by_status.pending, ...data.events_by_status.accepted, ...data.events_by_status.completed];
  return (
    <section className="content-section standalone" data-testid="volunteer-insights">
      <div className="section-head">
        <div>
          <span className="eyebrow">YOUR CAMPUS JOURNEY</span>
          <h2>Insights & milestones</h2>
          <p className="section-sub">Where you've shown up, what you've earned, and what's a great match next.</p>
        </div>
      </div>
      <div className="stat-grid">
        <StatCard testid="stat-applied" icon={<Target size={18} />} label="Events applied" value={data.events_applied} />
        <StatCard testid="stat-hours" icon={<Clock3 size={18} />} label="Hours contributed" value={data.total_hours} suffix=" hrs" />
        <StatCard testid="stat-certificates" icon={<Award size={18} />} label="Certificates earned" value={data.certificates_earned} />
        <StatCard testid="stat-matches" icon={<Sparkles size={18} />} label="Matching opportunities" value={data.matching_opportunities} />
      </div>

      <div className="insight-split">
        <div className="insight-card">
          <span className="eyebrow">YOUR SKILLS</span>
          <h3>What the campus knows about you</h3>
          <p className="section-sub" style={{ marginTop: 4 }}>
            Department · <b>{data.department || "—"}</b>
          </p>
          <div className="chip-list">
            {(data.skills || []).length ? (
              data.skills.map((s) => (
                <span className="chip" key={s} data-testid={`insight-skill-${s}`}>
                  {s}
                </span>
              ))
            ) : (
              <span className="section-sub">Add skills in your profile so organizers can find you.</span>
            )}
          </div>
        </div>

        <div className="insight-card">
          <span className="eyebrow">STATUS BREAKDOWN</span>
          <h3>Where each event stands</h3>
          <div className="status-breakdown">
            <StatBar label="Pending" value={data.events_pending} total={data.events_applied || 1} tone="pending" />
            <StatBar label="Accepted" value={data.events_accepted} total={data.events_applied || 1} tone="accepted" />
            <StatBar label="Completed" value={data.events_completed} total={data.events_applied || 1} tone="completed" />
          </div>
        </div>
      </div>

      <div className="insight-card">
        <span className="eyebrow">RECENT ACTIVITY</span>
        <h3>Every event you've touched</h3>
        {all.length ? (
          <div className="event-breakdown">
            {all.map((e, i) => (
              <div className="breakdown-row" key={`${e.id}-${i}`} data-testid={`recent-${e.id}`}>
                <div>
                  <b>{e.title}</b>
                  <span>
                    {e.date} · {e.location || "Campus"}
                  </span>
                </div>
                <div className="breakdown-badges">
                  {e.hours > 0 && <span className="status completed">{e.hours} hrs</span>}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty mini">
            <Activity size={22} /> <b>Join your first event to start the story</b>
          </div>
        )}
      </div>
    </section>
  );
}

function StatBar({ label, value, total, tone }) {
  const pct = total ? Math.round((value / total) * 100) : 0;
  return (
    <div className="statbar-row">
      <div className="statbar-head">
        <b>{label}</b>
        <span>{value}</span>
      </div>
      <div className="coverage-bar">
        <div className={`coverage-fill tone-${tone}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function VolunteerProfileModal({ username, onClose }) {
  const [profile, setProfile] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => {
    api
      .get(`/users/${username}`)
      .then((res) => setProfile(res.data))
      .catch((err) => setError(err.response?.data?.detail || "Could not load profile"));
  }, [username]);
  return (
    <div className="modal-backdrop">
      <div className="modal profile-view-modal" data-testid="volunteer-profile-modal">
        <button type="button" className="modal-close" data-testid="close-profile-view-button" onClick={onClose}>
          <X size={18} />
        </button>
        {error && <p className="form-error">{error}</p>}
        {!profile && !error && <p className="section-sub">Loading campus story…</p>}
        {profile && (
          <>
            <div className="profile-head">
              <div className="avatar big">{profile.name[0]}</div>
              <div>
                <span className="eyebrow">{profile.role === "organizer" ? "ORGANIZER" : "STUDENT VOLUNTEER"}</span>
                <h2>{profile.name}</h2>
                <p className="section-sub">
                  {profile.department || "Campus community"} · @{profile.username}
                </p>
              </div>
            </div>
            <div className="profile-stats">
              <div data-testid="profile-stat-events">
                <b>{profile.events_completed}</b>
                <span>Events completed</span>
              </div>
              <div data-testid="profile-stat-hours">
                <b>{profile.total_hours}</b>
                <span>Hours contributed</span>
              </div>
              <div data-testid="profile-stat-certs">
                <b>{profile.certificates_earned}</b>
                <span>Certificates earned</span>
              </div>
            </div>
            <div>
              <span className="eyebrow">SKILLS</span>
              <div className="chip-list" style={{ marginTop: 10 }}>
                {(profile.skills || []).length ? (
                  profile.skills.map((s) => (
                    <span className="chip" key={s}>
                      {s}
                    </span>
                  ))
                ) : (
                  <span className="section-sub">No skills listed yet.</span>
                )}
              </div>
            </div>
            <div style={{ marginTop: 18 }}>
              <span className="eyebrow">COMPLETED EVENTS</span>
              {profile.completed_events.length ? (
                <div className="event-breakdown" style={{ marginTop: 10 }}>
                  {profile.completed_events.map((e) => (
                    <div className="breakdown-row" key={e.event_id} data-testid={`profile-event-${e.event_id}`}>
                      <div>
                        <b>{e.title}</b>
                        <span>
                          {e.date} · {e.location || "Campus"}
                        </span>
                      </div>
                      <div className="breakdown-badges">
                        <span className="status completed">{e.hours} hrs</span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="empty mini" style={{ marginTop: 10 }}>
                  <Award size={22} /> <b>No completed events yet</b>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default App;
