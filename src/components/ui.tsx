import {
  createContext,
  createElement,
  useContext,
  useEffect,
  useId,
  useRef,
  useState,
  type ButtonHTMLAttributes,
  type HTMLAttributes,
  type InputHTMLAttributes,
  type KeyboardEvent as ReactKeyboardEvent,
  type ReactNode,
  type SelectHTMLAttributes,
} from "react";
import { createPortal } from "react-dom";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "light";
  children: ReactNode;
};

export function Button({
  variant = "primary",
  className = "",
  children,
  type = "button",
  ...props
}: ButtonProps) {
  return (
    <button
      className={`button button--${variant} ${className}`.trim()}
      type={type}
      {...props}
    >
      {children}
    </button>
  );
}

type CardProps = HTMLAttributes<HTMLElement> & {
  children: ReactNode;
  as?: "article" | "section" | "div";
};

export function Card({
  as = "section",
  className = "",
  children,
  ...props
}: CardProps) {
  return createElement(as, { className: `card ${className}`.trim(), ...props }, children);
}

export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "accent" | "success" | "warning";
}) {
  return <span className={`badge badge--${tone}`}>{children}</span>;
}

export function Chip({
  children,
  selected = false,
  onRemove,
}: {
  children: ReactNode;
  selected?: boolean;
  onRemove?: () => void;
}) {
  return (
    <span className={`chip ${selected ? "chip--selected" : ""}`}>
      {children}
      {onRemove && (
        <button
          className="chip__remove"
          type="button"
          aria-label={`Supprimer ${typeof children === "string" ? children : "cet élément"}`}
          onClick={onRemove}
        >
          ×
        </button>
      )}
    </span>
  );
}

export function Avatar({
  name,
  src,
  size = "medium",
}: {
  name: string;
  src?: string;
  size?: "small" | "medium" | "large";
}) {
  const [imageFailed, setImageFailed] = useState(false);
  const initials = name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => Array.from(part)[0] ?? "")
    .join("")
    .toLocaleUpperCase();

  return (
    <span className={`avatar avatar--${size}`} role="img" aria-label={name}>
      {src && !imageFailed ? (
        <img src={src} alt="" onError={() => setImageFailed(true)} />
      ) : (
        initials || "?"
      )}
    </span>
  );
}

export function Input({
  label,
  hint,
  error,
  id,
  ...props
}: InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  hint?: string;
  error?: string;
}) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  const messageId = `${inputId}-message`;
  const labelId = `${inputId}-label`;
  const message = error ?? hint;

  return (
    <div className="form-field">
      <label className="form-field__label" id={labelId} htmlFor={inputId}>
        {label}
      </label>
      <input
        id={inputId}
        className={`input ${error ? "input--error" : ""}`.trim()}
        aria-invalid={Boolean(error) || undefined}
        aria-describedby={message ? messageId : undefined}
        aria-labelledby={labelId}
        {...props}
      />
      {message && (
        <span
          id={messageId}
          className={error ? "form-field__error" : "form-field__hint"}
        >
          {message}
        </span>
      )}
    </div>
  );
}

export function Select({
  label,
  options,
  hint,
  id,
  ...props
}: SelectHTMLAttributes<HTMLSelectElement> & {
  label: string;
  options: Array<{ value: string; label: string }>;
  hint?: string;
}) {
  const generatedId = useId();
  const selectId = id ?? generatedId;
  const hintId = `${selectId}-hint`;
  const labelId = `${selectId}-label`;

  return (
    <div className="form-field">
      <label className="form-field__label" id={labelId} htmlFor={selectId}>
        {label}
      </label>
      <select
        id={selectId}
        className="select"
        aria-describedby={hint ? hintId : undefined}
        aria-labelledby={labelId}
        {...props}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      {hint && (
        <span id={hintId} className="form-field__hint">
          {hint}
        </span>
      )}
    </div>
  );
}

export function ProgressBar({
  value,
  label,
}: {
  value: number;
  label: string;
}) {
  const boundedValue = Number.isFinite(value) ? Math.min(100, Math.max(0, value)) : 0;
  return (
    <div
      className="progress"
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={boundedValue}
    >
      <span className="progress__fill" style={{ width: `${boundedValue}%` }} />
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  const titleId = useId();
  return (
    <div className="empty-state" role="status" aria-labelledby={titleId}>
      <h3 id={titleId}>{title}</h3>
      <p>{description}</p>
      {action}
    </div>
  );
}

export function Skeleton({
  width,
  height = "1rem",
  label = "Chargement",
}: {
  width?: string;
  height?: string;
  label?: string;
}) {
  return (
    <span
      className="skeleton"
      role="status"
      aria-label={label}
      style={{ width, height }}
    />
  );
}

export function Stepper({
  steps,
  currentStep,
}: {
  steps: string[];
  currentStep: number;
}) {
  return (
    <ol className="stepper" aria-label="Progression">
      {steps.map((step, index) => {
        const status =
          index < currentStep ? "completed" : index === currentStep ? "current" : "upcoming";
        return (
          <li
            className={`stepper__step stepper__step--${status}`}
            key={`${index}-${step}`}
            aria-current={status === "current" ? "step" : undefined}
          >
            <span className="stepper__marker" aria-hidden="true">
              {index < currentStep ? "✓" : index + 1}
            </span>
            <span>{step}</span>
          </li>
        );
      })}
    </ol>
  );
}

type TabItem = { id: string; label: string; content: ReactNode };

export function Tabs({
  tabs,
  label = "Sections",
}: {
  tabs: TabItem[];
  label?: string;
}) {
  const [activeId, setActiveId] = useState(tabs[0]?.id ?? "");
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([]);
  const baseId = useId();
  const activeTab = tabs.find((tab) => tab.id === activeId) ?? tabs[0];

  function handleKeyDown(event: ReactKeyboardEvent<HTMLButtonElement>, index: number) {
    let nextIndex: number | undefined;
    if (event.key === "ArrowRight") nextIndex = (index + 1) % tabs.length;
    if (event.key === "ArrowLeft") nextIndex = (index - 1 + tabs.length) % tabs.length;
    if (event.key === "Home") nextIndex = 0;
    if (event.key === "End") nextIndex = tabs.length - 1;
    if (nextIndex !== undefined) {
      event.preventDefault();
      const nextTab = tabs[nextIndex];
      setActiveId(nextTab.id);
      tabRefs.current[nextIndex]?.focus();
    }
  }

  if (!activeTab) return null;

  return (
    <div className="tabs">
      <div className="tabs__list" role="tablist" aria-label={label}>
        {tabs.map((tab, index) => (
          <button
            className="tabs__tab"
            id={`${baseId}-tab-${tab.id}`}
            key={tab.id}
            ref={(element) => {
              tabRefs.current[index] = element;
            }}
            type="button"
            role="tab"
            aria-selected={activeTab.id === tab.id}
            aria-controls={`${baseId}-panel`}
            tabIndex={activeTab.id === tab.id ? 0 : -1}
            onClick={() => setActiveId(tab.id)}
            onKeyDown={(event) => handleKeyDown(event, index)}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div
        className="tabs__panel"
        id={`${baseId}-panel`}
        role="tabpanel"
        aria-labelledby={`${baseId}-tab-${activeTab.id}`}
        tabIndex={0}
      >
        {activeTab.content}
      </div>
    </div>
  );
}

function getFocusableElements(container: HTMLElement) {
  return Array.from(
    container.querySelectorAll<HTMLElement>(
      'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
    ),
  ).filter(
    (element) =>
      !element.closest("[hidden], [aria-hidden='true']") &&
      getComputedStyle(element).display !== "none" &&
      getComputedStyle(element).visibility !== "hidden",
  );
}

export function Modal({
  open,
  title,
  onClose,
  children,
  variant = "modal",
}: {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
  variant?: "modal" | "drawer";
}) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const titleId = useId();
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  useEffect(() => {
    if (!open) return;
    const previousFocus = document.activeElement instanceof HTMLElement
      ? document.activeElement
      : null;
    const dialog = dialogRef.current;
    const focusable = dialog ? getFocusableElements(dialog) : [];
    (focusable[0] ?? dialog)?.focus();

    function onKeyDown(event: globalThis.KeyboardEvent) {
      if (event.key === "Escape") {
        onCloseRef.current();
        return;
      }
      if (event.key !== "Tab" || !dialog) return;

      const elements = getFocusableElements(dialog);
      if (elements.length === 0) {
        event.preventDefault();
        dialog.focus();
        return;
      }
      const first = elements[0];
      const last = elements[elements.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      previousFocus?.focus();
    };
  }, [open]);

  if (!open) return null;

  return createPortal(
    <div
      className={`modal-backdrop ${variant === "drawer" ? "modal-backdrop--drawer" : ""}`}
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onCloseRef.current();
      }}
    >
      <div
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        ref={dialogRef}
      >
        <div className="modal__header">
          <h2 id={titleId}>{title}</h2>
          <Button variant="ghost" aria-label="Fermer" onClick={onClose}>
            ×
          </Button>
        </div>
        <div className="modal__content">{children}</div>
      </div>
    </div>,
    document.body,
  );
}

export function Drawer(props: Omit<Parameters<typeof Modal>[0], "variant">) {
  return <Modal {...props} variant="drawer" />;
}

type ToastMessage = { id: number; message: string; tone: "info" | "success" | "error" };
type ToastContextValue = { showToast: (message: string, tone?: ToastMessage["tone"]) => void };
const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const nextId = useRef(0);

  const showToast: ToastContextValue["showToast"] = (message, tone = "info") => {
    const id = ++nextId.current;
    setToasts((current) => [...current, { id, message, tone }]);
  };

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <div className="toast-region" aria-live="polite" aria-relevant="additions">
        {toasts.map((toast) => (
          <div className={`toast toast--${toast.tone}`} role="status" key={toast.id}>
            <span>{toast.message}</span>
            <Button
              variant="ghost"
              aria-label="Fermer la notification"
              onClick={() => setToasts((current) => current.filter((item) => item.id !== toast.id))}
            >
              ×
            </Button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) throw new Error("useToast must be used within a ToastProvider");
  return context.showToast;
}

export type DataTableColumn<Row> = {
  id: string;
  header: string;
  cell: (row: Row) => ReactNode;
};

export function DataTable<Row>({
  columns,
  rows,
  getRowId,
  caption,
  emptyMessage = "Aucun élément à afficher.",
}: {
  columns: DataTableColumn<Row>[];
  rows: Row[];
  getRowId: (row: Row) => string;
  caption: string;
  emptyMessage?: string;
}) {
  return (
    <div className="data-table-wrap">
      <table className="data-table">
        <caption>{caption}</caption>
        <thead>
          <tr>
            {columns.map((column) => (
              <th scope="col" key={column.id}>
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td colSpan={columns.length}>{emptyMessage}</td>
            </tr>
          ) : (
            rows.map((row) => (
              <tr key={getRowId(row)}>
                {columns.map((column) => (
                  <td key={column.id}>{column.cell(row)}</td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

export function ChartFrame({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: ReactNode;
}) {
  const descriptionId = useId();
  return (
    <figure className="chart-frame">
      <figcaption className="chart-frame__caption">
        <strong>{title}</strong>
        <span id={descriptionId}>{description}</span>
      </figcaption>
      <div className="chart-frame__content" role="img" aria-labelledby={descriptionId}>
        {children}
      </div>
    </figure>
  );
}
