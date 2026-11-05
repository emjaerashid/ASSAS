import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';

// App-wide replacements for window.alert / window.confirm and the ad-hoc
// "setTimeout(() => setSuccess(''), 3000)" banners: toasts dismiss themselves,
// and confirm() resolves a promise so callers keep their early-return shape:
//   if (!(await confirm({ title: 'Delete?' }))) return;

const FeedbackContext = createContext(null);

const TOAST_ICONS = { success: 'check_circle', error: 'error', info: 'info' };
const TOAST_DURATION = { success: 3500, info: 4500, error: 6500 };

let nextToastId = 1;

function Toast({ toast, onDismiss }) {
  const [leaving, setLeaving] = useState(false);
  const duration = TOAST_DURATION[toast.type];

  useEffect(() => {
    const leave = setTimeout(() => setLeaving(true), duration);
    return () => clearTimeout(leave);
  }, [duration]);

  useEffect(() => {
    if (!leaving) return;
    const remove = setTimeout(() => onDismiss(toast.id), 200);
    return () => clearTimeout(remove);
  }, [leaving, onDismiss, toast.id]);

  return (
    <div className={`toast ${toast.type}${leaving ? ' leaving' : ''}`} role={toast.type === 'error' ? 'alert' : 'status'}>
      <span className="material-symbols-outlined">{TOAST_ICONS[toast.type]}</span>
      <div className="toast-text">{toast.message}</div>
      <button className="toast-close" onClick={() => setLeaving(true)} aria-label="Dismiss">
        <span className="material-symbols-outlined">close</span>
      </button>
      <div className="toast-timer" style={{ animationDuration: `${duration}ms` }} />
    </div>
  );
}

function ConfirmDialog({ request, onClose }) {
  const confirmRef = useRef(null);
  const { title, message, confirmLabel = 'Confirm', cancelLabel = 'Cancel', danger = false } = request;

  useEffect(() => {
    confirmRef.current?.focus();
    const onKey = (e) => e.key === 'Escape' && onClose(false);
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <div className="modal-overlay" onClick={() => onClose(false)}>
      <div className="modal confirm-dialog" role="alertdialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
        <div className="modal-body">
          <div className={`confirm-icon${danger ? ' danger' : ''}`}>
            <span className="material-symbols-outlined">{danger ? 'delete' : 'help'}</span>
          </div>
          <div>
            <div className="confirm-title">{title}</div>
            {message && <div className="confirm-message">{message}</div>}
          </div>
        </div>
        <div className="modal-footer">
          <button className="btn btn-outline" onClick={() => onClose(false)}>{cancelLabel}</button>
          <button ref={confirmRef} className={`btn ${danger ? 'btn-danger-solid' : 'btn-primary'}`} onClick={() => onClose(true)}>
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

export function FeedbackProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const [confirmRequest, setConfirmRequest] = useState(null);

  const dismiss = useCallback((id) => setToasts((list) => list.filter((t) => t.id !== id)), []);

  const push = useCallback((type, message) => {
    const id = nextToastId++;
    setToasts((list) => [...list.slice(-3), { id, type, message }]);
  }, []);

  const toast = useRef({
    success: (m) => push('success', m),
    error: (m) => push('error', m),
    info: (m) => push('info', m),
  }).current;

  const confirm = useCallback((options) => new Promise((resolve) => {
    setConfirmRequest({ ...options, resolve });
  }), []);

  const closeConfirm = useCallback((result) => {
    confirmRequest?.resolve(result);
    setConfirmRequest(null);
  }, [confirmRequest]);

  return (
    <FeedbackContext.Provider value={{ toast, confirm }}>
      {children}
      <div className="toast-stack">
        {toasts.map((t) => <Toast key={t.id} toast={t} onDismiss={dismiss} />)}
      </div>
      {confirmRequest && <ConfirmDialog request={confirmRequest} onClose={closeConfirm} />}
    </FeedbackContext.Provider>
  );
}

export function useFeedback() {
  const context = useContext(FeedbackContext);
  if (!context) throw new Error('useFeedback must be used within FeedbackProvider');
  return context;
}

// Pages that change pending exception / add-drop counts call this so the
// sidebar badges refresh immediately instead of waiting for the next poll.
export const COUNTS_CHANGED_EVENT = 'assas:counts-changed';
export function notifyCountsChanged() {
  window.dispatchEvent(new Event(COUNTS_CHANGED_EVENT));
}
