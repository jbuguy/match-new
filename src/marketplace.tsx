import { useEffect, useState, type FormEvent } from "react";
import { Badge, Button, Card, ChartFrame, DataTable, EmptyState } from "./components/ui";
import {
  ApiError,
  createTrainingCourse,
  enrollInCourse,
  fetchAdminIndicators,
  fetchCandidateApplications,
  fetchCandidateEnrollments,
  fetchEmployerApplications,
  fetchProviderCourseEnrollments,
  fetchPublishedCourses,
  fetchTrainingCourses,
  updateCourseEnrollmentStatus,
  updateEmployerApplicationStatus,
  updateTrainingCourse,
  type AdminIndicators,
  type CourseDeliveryMode,
  type CourseEnrollment,
  type CourseEnrollmentStatus,
  type EmployerApplication,
  type JobApplication,
  type JobApplicationStatus,
  type ProviderCourseEnrollment,
  type TrainingCourse,
  type TrainingCourseDraft,
} from "./auth";

function errorMessage(error: unknown): string {
  return error instanceof ApiError
    ? error.message
    : "Impossible de joindre le service. Vérifiez votre connexion.";
}

const applicationStatusLabels: Record<JobApplicationStatus, string> = {
  submitted: "Reçue",
  reviewing: "À l’étude",
  interview: "Entretien",
  hired: "Recrutée",
  rejected: "Non retenue",
};

const enrollmentStatusLabels: Record<CourseEnrollmentStatus, string> = {
  enrolled: "Inscrit",
  completed: "Terminée",
  withdrawn: "Désinscrit",
};

const deliveryLabels: Record<CourseDeliveryMode, string> = {
  online: "À distance",
  in_person: "En présentiel",
  hybrid: "Hybride",
};

function formatDate(value: string | null): string {
  if (!value) return "À définir";
  return new Date(`${value.slice(0, 10)}T12:00:00`).toLocaleDateString("fr-FR");
}

function MetricCard({
  label,
  value,
  detail,
}: {
  label: string;
  value: string | number;
  detail: string;
}) {
  return (
    <Card className="market-metric">
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </Card>
  );
}

export function AdminDashboardPage({ token }: { token: string }) {
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [appliedRange, setAppliedRange] = useState({ startDate: "", endDate: "" });
  const [indicators, setIndicators] = useState<AdminIndicators | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    setError("");
    fetchAdminIndicators(token, appliedRange.startDate, appliedRange.endDate)
      .then((result) => {
        if (!cancelled) setIndicators(result);
      })
      .catch((cause: unknown) => {
        if (!cancelled) setError(errorMessage(cause));
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token, appliedRange]);

  function applyDateRange(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAppliedRange({ startDate, endDate });
  }

  const maxStatusCount = Math.max(
    1,
    ...(indicators?.applications_by_status.map((item) => item.count) ?? []),
  );
  const maxSkillCount = Math.max(1, ...(indicators?.top_skills.map((item) => item.offer_count) ?? []));

  return (
    <section className="market-page">
      <div className="eyebrow">PILOTAGE AGRÉGÉ</div>
      <h1>Tableau de bord administration</h1>
      <p className="market-page__intro">
        Suivez l’activité, les compétences demandées et les résultats déclarés par les employeurs.
        Les données présentées sont agrégées et ne contiennent pas de profils individuels.
      </p>

      <form className="market-filter" onSubmit={applyDateRange}>
        <label className="form-field">
          <span className="form-field__label">Du</span>
          <input
            className="input"
            type="date"
            value={startDate}
            max={endDate || undefined}
            onChange={(event) => setStartDate(event.target.value)}
          />
        </label>
        <label className="form-field">
          <span className="form-field__label">Au</span>
          <input
            className="input"
            type="date"
            value={endDate}
            min={startDate || undefined}
            onChange={(event) => setEndDate(event.target.value)}
          />
        </label>
        <Button type="submit" disabled={isLoading}>Appliquer la période</Button>
      </form>

      {error && <p className="workspace-error" role="alert">{error}</p>}
      {isLoading && <p aria-live="polite">Chargement des indicateurs…</p>}
      {!isLoading && !error && indicators && (
        <>
          <p className="market-range">
            Période : {indicators.start_date ? formatDate(indicators.start_date) : "sans limite"}
            {" — "}
            {indicators.end_date ? formatDate(indicators.end_date) : "aujourd’hui"}
          </p>
          <div className="market-metrics">
            <MetricCard
              label="Candidats inscrits"
              value={indicators.candidate_registrations}
              detail="Comptes candidats créés pendant la période"
            />
            <MetricCard
              label="Offres publiées"
              value={indicators.published_job_offers}
              detail="Offres de la plateforme pendant la période"
            />
            <MetricCard
              label="Candidatures"
              value={indicators.applications_total}
              detail="Tous les statuts confondus"
            />
            <MetricCard
              label="Taux d’embauche déclaré"
              value={
                indicators.hire_rate_percent === null
                  ? "—"
                  : `${indicators.hire_rate_percent.toLocaleString("fr-FR")} %`
              }
              detail={`${indicators.hired_applications} embauches sur ${indicators.closed_applications} candidatures clôturées`}
            />
            <MetricCard
              label="Organisations"
              value={indicators.organisations}
              detail="Organisations enregistrées pendant la période"
            />
            <MetricCard
              label="Formations publiées"
              value={indicators.published_courses}
              detail="Catalogue visible aux candidats"
            />
            <MetricCard
              label="Inscriptions actives"
              value={indicators.active_enrollments}
              detail="Inscriptions non clôturées"
            />
            <MetricCard
              label="Formations terminées"
              value={indicators.course_completions}
              detail="Achèvements enregistrés pendant la période"
            />
          </div>

          <div className="market-charts">
            <ChartFrame
              title="État des candidatures"
              description="Répartition des candidatures par statut. Les recrutements sont comptés uniquement après déclaration par l’employeur."
            >
              <div className="market-bars">
                {indicators.applications_by_status.length ? (
                  indicators.applications_by_status.map((item) => (
                    <div className="market-bar" key={item.status}>
                      <div className="market-bar__label">
                        <span>{applicationStatusLabels[item.status]}</span>
                        <strong>{item.count}</strong>
                      </div>
                      <div className="market-bar__track">
                        <span style={{ width: `${(item.count / maxStatusCount) * 100}%` }} />
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="market-empty">Aucune candidature pour cette période.</p>
                )}
              </div>
            </ChartFrame>
            <ChartFrame
              title="Compétences les plus demandées"
              description="Nombre d’offres publiées pendant la période qui demandent chaque compétence."
            >
              <div className="market-bars">
                {indicators.top_skills.length ? (
                  indicators.top_skills.map((item) => (
                    <div className="market-bar" key={item.skill}>
                      <div className="market-bar__label">
                        <span>{item.skill}</span>
                        <strong>{item.offer_count}</strong>
                      </div>
                      <div className="market-bar__track">
                        <span style={{ width: `${(item.offer_count / maxSkillCount) * 100}%` }} />
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="market-empty">Aucune compétence déclarée dans les offres.</p>
                )}
              </div>
            </ChartFrame>
          </div>
          <div className="market-charts">
            <DataTable
              caption="Candidatures par statut"
              rows={indicators.applications_by_status}
              getRowId={(row) => row.status}
              emptyMessage="Aucune candidature pour cette période."
              columns={[
                { id: "status", header: "Statut", cell: (row) => applicationStatusLabels[row.status] },
                { id: "count", header: "Nombre", cell: (row) => row.count },
              ]}
            />
            <DataTable
              caption="Offres par compétence demandée"
              rows={indicators.top_skills}
              getRowId={(row) => row.skill}
              emptyMessage="Aucune compétence déclarée dans les offres."
              columns={[
                { id: "skill", header: "Compétence", cell: (row) => row.skill },
                { id: "offers", header: "Nombre d’offres", cell: (row) => row.offer_count },
              ]}
            />
          </div>
          <p className="market-footnote">
            Le taux d’embauche est calculé comme les candidatures marquées « recrutée » divisées
            par les candidatures clôturées (« recrutée » ou « non retenue »). C’est un résultat
            déclaré, pas une mesure indépendante de l’insertion professionnelle.
          </p>
        </>
      )}
    </section>
  );
}

type CourseFormValues = {
  title: string;
  summary: string;
  skills: string;
  delivery_mode: CourseDeliveryMode;
  location: string;
  starts_on: string;
  ends_on: string;
  duration_hours: string;
  capacity: string;
  price_tnd: string;
  status: TrainingCourseDraft["status"];
};

const emptyCourseForm: CourseFormValues = {
  title: "",
  summary: "",
  skills: "",
  delivery_mode: "online",
  location: "",
  starts_on: "",
  ends_on: "",
  duration_hours: "1",
  capacity: "20",
  price_tnd: "",
  status: "draft",
};

function courseDraft(values: CourseFormValues): TrainingCourseDraft {
  return {
    title: values.title.trim(),
    summary: values.summary.trim(),
    skills: values.skills.split(/[,\n]/).map((skill) => skill.trim()).filter(Boolean),
    delivery_mode: values.delivery_mode,
    location: values.location.trim() || null,
    starts_on: values.starts_on || null,
    ends_on: values.ends_on || null,
    duration_hours: Number(values.duration_hours),
    capacity: Number(values.capacity),
    price_tnd: values.price_tnd.trim() || null,
    status: values.status,
  };
}

function valuesFromCourse(course: TrainingCourse): CourseFormValues {
  return {
    title: course.title,
    summary: course.summary,
    skills: course.skills.join(", "),
    delivery_mode: course.delivery_mode,
    location: course.location ?? "",
    starts_on: course.starts_on ?? "",
    ends_on: course.ends_on ?? "",
    duration_hours: String(course.duration_hours),
    capacity: String(course.capacity),
    price_tnd: course.price_tnd ?? "",
    status: course.status,
  };
}

export function TrainingProviderDashboardPage({ token }: { token: string }) {
  const [courses, setCourses] = useState<TrainingCourse[]>([]);
  const [form, setForm] = useState<CourseFormValues>(emptyCourseForm);
  const [editingCourseId, setEditingCourseId] = useState<string | null>(null);
  const [selectedCourseId, setSelectedCourseId] = useState("");
  const [enrollments, setEnrollments] = useState<ProviderCourseEnrollment[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  async function loadCourses() {
    const results = await fetchTrainingCourses(token);
    setCourses(results);
    if (!selectedCourseId && results.length) setSelectedCourseId(results[0].id);
  }

  async function loadEnrollments(courseId: string) {
    setEnrollments(await fetchProviderCourseEnrollments(token, courseId));
  }

  useEffect(() => {
    let cancelled = false;
    fetchTrainingCourses(token)
      .then((results) => {
        if (!cancelled) {
          setCourses(results);
          setSelectedCourseId((current) => current || results[0]?.id || "");
        }
      })
      .catch((cause: unknown) => {
        if (!cancelled) setError(errorMessage(cause));
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  useEffect(() => {
    if (!selectedCourseId) {
      setEnrollments([]);
      return;
    }
    let cancelled = false;
    fetchProviderCourseEnrollments(token, selectedCourseId)
      .then((results) => {
        if (!cancelled) setEnrollments(results);
      })
      .catch((cause: unknown) => {
        if (!cancelled) setError(errorMessage(cause));
      });
    return () => {
      cancelled = true;
    };
  }, [token, selectedCourseId]);

  async function saveCourse(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSaving(true);
    setError("");
    setNotice("");
    try {
      const payload = courseDraft(form);
      const saved = editingCourseId
        ? await updateTrainingCourse(token, editingCourseId, payload)
        : await createTrainingCourse(token, payload);
      await loadCourses();
      setSelectedCourseId(saved.id);
      setEditingCourseId(null);
      setForm(emptyCourseForm);
      setNotice(editingCourseId ? "La formation a été mise à jour." : "La formation a été créée.");
    } catch (cause: unknown) {
      setError(errorMessage(cause));
    } finally {
      setIsSaving(false);
    }
  }

  function editCourse(course: TrainingCourse) {
    setEditingCourseId(course.id);
    setSelectedCourseId(course.id);
    setForm(valuesFromCourse(course));
    setNotice("");
    setError("");
  }

  async function updateEnrollment(
    enrollmentId: string,
    nextStatus: CourseEnrollmentStatus,
  ) {
    setError("");
    try {
      await updateCourseEnrollmentStatus(token, enrollmentId, nextStatus);
      await Promise.all([loadCourses(), loadEnrollments(selectedCourseId)]);
    } catch (cause: unknown) {
      setError(errorMessage(cause));
    }
  }

  const activeEnrollments = courses.reduce((total, course) => total + course.enrollment_count, 0);
  const completions = courses.reduce((total, course) => total + course.completed_count, 0);

  return (
    <section className="market-page">
      <div className="eyebrow">ORGANISME DE FORMATION</div>
      <h1>Votre catalogue de formations</h1>
      <p className="market-page__intro">
        Publiez des formations reliées aux compétences et suivez les inscriptions ainsi que les
        achèvements de vos cours.
      </p>
      <div className="market-metrics market-metrics--three">
        <MetricCard label="Formations" value={courses.length} detail="Brouillons, publiées et archivées" />
        <MetricCard label="Inscriptions actives" value={activeEnrollments} detail="Participants actuellement inscrits" />
        <MetricCard label="Achèvements" value={completions} detail="Formations marquées terminées" />
      </div>

      <Card className="market-panel">
        <div className="market-panel__heading">
          <div>
            <h2>{editingCourseId ? "Modifier la formation" : "Créer une formation"}</h2>
            <p>Les cours en brouillon ne sont pas visibles des candidats.</p>
          </div>
          {editingCourseId && (
            <Button
              variant="secondary"
              onClick={() => {
                setEditingCourseId(null);
                setForm(emptyCourseForm);
              }}
            >
              Annuler la modification
            </Button>
          )}
        </div>
        <form className="workspace-form market-course-form" onSubmit={(event) => void saveCourse(event)}>
          <label className="form-field market-field--wide">
            <span className="form-field__label">Titre</span>
            <input className="input" required minLength={2} maxLength={160} value={form.title}
              onChange={(event) => setForm({ ...form, title: event.target.value })} />
          </label>
          <label className="form-field market-field--wide">
            <span className="form-field__label">Résumé</span>
            <textarea className="input workspace-textarea" required minLength={10} maxLength={5000}
              value={form.summary} onChange={(event) => setForm({ ...form, summary: event.target.value })} />
          </label>
          <label className="form-field market-field--wide">
            <span className="form-field__label">Compétences enseignées</span>
            <input className="input" required placeholder="Ex. Excel, analyse de données"
              value={form.skills} onChange={(event) => setForm({ ...form, skills: event.target.value })} />
            <span className="form-field__hint">Séparez les compétences par une virgule.</span>
          </label>
          <label className="form-field">
            <span className="form-field__label">Mode</span>
            <select className="select" value={form.delivery_mode}
              onChange={(event) => setForm({ ...form, delivery_mode: event.target.value as CourseDeliveryMode })}>
              <option value="online">À distance</option>
              <option value="in_person">En présentiel</option>
              <option value="hybrid">Hybride</option>
            </select>
          </label>
          <label className="form-field">
            <span className="form-field__label">Lieu (obligatoire en présentiel/hybride)</span>
            <input className="input" maxLength={120} value={form.location}
              onChange={(event) => setForm({ ...form, location: event.target.value })} />
          </label>
          <label className="form-field">
            <span className="form-field__label">Date de début</span>
            <input className="input" type="date" value={form.starts_on}
              onChange={(event) => setForm({ ...form, starts_on: event.target.value })} />
          </label>
          <label className="form-field">
            <span className="form-field__label">Date de fin</span>
            <input className="input" type="date" min={form.starts_on || undefined} value={form.ends_on}
              onChange={(event) => setForm({ ...form, ends_on: event.target.value })} />
          </label>
          <label className="form-field">
            <span className="form-field__label">Durée (heures)</span>
            <input className="input" type="number" min={1} max={2000} required value={form.duration_hours}
              onChange={(event) => setForm({ ...form, duration_hours: event.target.value })} />
          </label>
          <label className="form-field">
            <span className="form-field__label">Capacité</span>
            <input className="input" type="number" min={1} max={10000} required value={form.capacity}
              onChange={(event) => setForm({ ...form, capacity: event.target.value })} />
          </label>
          <label className="form-field">
            <span className="form-field__label">Prix (TND, facultatif)</span>
            <input className="input" type="number" min={0} step="0.01" value={form.price_tnd}
              onChange={(event) => setForm({ ...form, price_tnd: event.target.value })} />
          </label>
          <label className="form-field">
            <span className="form-field__label">Statut</span>
            <select className="select" value={form.status}
              onChange={(event) => setForm({ ...form, status: event.target.value as TrainingCourseDraft["status"] })}>
              <option value="draft">Brouillon</option>
              <option value="published">Publiée</option>
              <option value="archived">Archivée</option>
            </select>
          </label>
          {error && <p className="workspace-error market-field--wide" role="alert">{error}</p>}
          {notice && <p className="workspace-success market-field--wide" role="status">{notice}</p>}
          <div className="market-field--wide">
            <Button type="submit" disabled={isSaving}>
              {isSaving ? "Enregistrement…" : editingCourseId ? "Enregistrer les changements" : "Créer la formation"}
            </Button>
          </div>
        </form>
      </Card>

      <div className="market-section-heading">
        <h2>Vos formations</h2>
        <Badge>{courses.length}</Badge>
      </div>
      {isLoading && <p aria-live="polite">Chargement des formations…</p>}
      {!isLoading && courses.length === 0 && (
        <Card className="market-panel">
          <EmptyState
            title="Aucune formation pour le moment"
            description="Créez un cours et publiez-le pour le rendre visible aux candidats."
          />
        </Card>
      )}
      <div className="market-course-grid">
        {courses.map((course) => (
          <Card className="market-course-card" key={course.id}>
            <div className="market-panel__heading">
              <div>
                <Badge tone={course.status === "published" ? "success" : "neutral"}>
                  {course.status === "published" ? "Publiée" : course.status === "draft" ? "Brouillon" : "Archivée"}
                </Badge>
                <h3>{course.title}</h3>
              </div>
              <Button variant="secondary" onClick={() => editCourse(course)}>Modifier</Button>
            </div>
            <p>{course.summary}</p>
            <ul className="market-course-meta">
              <li>{deliveryLabels[course.delivery_mode]}{course.location ? ` · ${course.location}` : ""}</li>
              <li>{formatDate(course.starts_on)} – {formatDate(course.ends_on)} · {course.duration_hours} h</li>
              <li>{course.enrollment_count} / {course.capacity} inscrits actifs · {course.completed_count} terminés</li>
              <li>{course.price_tnd === null ? "Prix non renseigné" : `${Number(course.price_tnd).toLocaleString("fr-FR")} TND`}</li>
              <li>Compétences : {course.skills.join(", ")}</li>
            </ul>
            <Button
              variant={selectedCourseId === course.id ? "primary" : "secondary"}
              onClick={() => setSelectedCourseId(course.id)}
            >
              {selectedCourseId === course.id ? "Liste sélectionnée" : "Voir les inscrits"}
            </Button>
          </Card>
        ))}
      </div>

      {selectedCourseId && (
        <Card className="market-panel" as="section">
          <div className="market-section-heading">
            <h2>Participants</h2>
            <Badge>{enrollments.length}</Badge>
          </div>
          {error && <p className="workspace-error" role="alert">{error}</p>}
          <DataTable<ProviderCourseEnrollment>
            caption="Participants inscrits à la formation sélectionnée"
            rows={enrollments}
            getRowId={(row) => row.id}
            emptyMessage="Aucune inscription pour cette formation."
            columns={[
              { id: "name", header: "Participant", cell: (row) => row.candidate_name || "Nom non renseigné" },
              { id: "location", header: "Lieu", cell: (row) => row.candidate_location || "Non renseigné" },
              { id: "skills", header: "Compétences", cell: (row) => row.candidate_skills.join(", ") || "Non renseignées" },
              { id: "status", header: "Statut", cell: (row) => enrollmentStatusLabels[row.status] },
              {
                id: "action",
                header: "Action",
                cell: (row) => row.status === "enrolled" ? (
                  <div className="market-row-actions">
                    <Button variant="secondary" onClick={() => void updateEnrollment(row.id, "completed")}>
                      Marquer terminée
                    </Button>
                    <Button variant="ghost" onClick={() => void updateEnrollment(row.id, "withdrawn")}>
                      Désinscrire
                    </Button>
                  </div>
                ) : "—",
              },
            ]}
          />
        </Card>
      )}
    </section>
  );
}

export function CandidateCoursesPage({ token }: { token: string }) {
  const [courses, setCourses] = useState<TrainingCourse[]>([]);
  const [enrollments, setEnrollments] = useState<CourseEnrollment[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [busyCourseId, setBusyCourseId] = useState("");

  async function refresh() {
    const [available, mine] = await Promise.all([
      fetchPublishedCourses(token),
      fetchCandidateEnrollments(token),
    ]);
    setCourses(available);
    setEnrollments(mine);
  }

  useEffect(() => {
    let cancelled = false;
    Promise.all([fetchPublishedCourses(token), fetchCandidateEnrollments(token)])
      .then(([available, mine]) => {
        if (!cancelled) {
          setCourses(available);
          setEnrollments(mine);
        }
      })
      .catch((cause: unknown) => {
        if (!cancelled) setError(errorMessage(cause));
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  async function enroll(course: TrainingCourse) {
    setBusyCourseId(course.id);
    setError("");
    try {
      await enrollInCourse(token, course.id);
      await refresh();
    } catch (cause: unknown) {
      setError(errorMessage(cause));
    } finally {
      setBusyCourseId("");
    }
  }

  const enrollmentByCourse = new Map(enrollments.map((item) => [item.course_id, item]));

  return (
    <section className="market-page">
      <div className="eyebrow">APPRENDRE ET PROGRESSER</div>
      <h1>Formations disponibles</h1>
      <p className="market-page__intro">Consultez les informations des organismes et inscrivez-vous aux cours publiés.</p>
      {error && <p className="workspace-error" role="alert">{error}</p>}
      {isLoading && <p aria-live="polite">Chargement du catalogue…</p>}
      {!isLoading && courses.length === 0 && (
        <Card className="market-panel">
          <EmptyState
            title="Aucune formation publiée pour le moment"
            description="Les formations apparaîtront ici lorsqu’un organisme les publiera."
          />
        </Card>
      )}
      <div className="market-course-grid">
        {courses.map((course) => {
          const enrollment = enrollmentByCourse.get(course.id);
          const isFull = course.enrollment_count >= course.capacity;
          return (
            <Card className="market-course-card" key={course.id}>
              <div className="market-panel__heading">
                <div>
                  <Badge tone="accent">{deliveryLabels[course.delivery_mode]}</Badge>
                  <h2>{course.title}</h2>
                </div>
                <Badge>{course.price_tnd === null ? "Prix à confirmer" : `${Number(course.price_tnd).toLocaleString("fr-FR")} TND`}</Badge>
              </div>
              <p>{course.summary}</p>
              <ul className="market-course-meta">
                <li>{course.location || "À distance"} · {formatDate(course.starts_on)} – {formatDate(course.ends_on)}</li>
                <li>{course.duration_hours} heures · {course.enrollment_count} / {course.capacity} places occupées</li>
                <li>Compétences : {course.skills.join(", ")}</li>
              </ul>
              <Button
                disabled={Boolean(enrollment) || isFull || busyCourseId === course.id}
                onClick={() => void enroll(course)}
              >
                {busyCourseId === course.id
                  ? "Inscription…"
                  : enrollment
                    ? enrollmentStatusLabels[enrollment.status]
                    : isFull
                      ? "Complet"
                      : "M’inscrire"}
              </Button>
            </Card>
          );
        })}
      </div>
    </section>
  );
}

export function CandidateApplicationsPage({ token }: { token: string }) {
  const [applications, setApplications] = useState<JobApplication[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    fetchCandidateApplications(token)
      .then((results) => {
        if (!cancelled) setApplications(results);
      })
      .catch((cause: unknown) => {
        if (!cancelled) setError(errorMessage(cause));
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  return (
    <section className="market-page">
      <div className="eyebrow">SUIVI PERSONNEL</div>
      <h1>Mes candidatures</h1>
      <p className="market-page__intro">Consultez l’état des candidatures que vous avez envoyées.</p>
      {error && <p className="workspace-error" role="alert">{error}</p>}
      {isLoading && <p aria-live="polite">Chargement des candidatures…</p>}
      {!isLoading && applications.length === 0 && (
        <Card className="market-panel">
          <EmptyState title="Aucune candidature" description="Vos candidatures envoyées apparaîtront ici." />
        </Card>
      )}
      <div className="market-list">
        {applications.map((application) => (
          <Card className="market-list-card" key={application.id}>
            <div>
              <h2>{application.job_title}</h2>
              <p>{application.location} · Envoyée le {formatDate(application.created_at)}</p>
            </div>
            <Badge tone={application.status === "hired" ? "success" : "neutral"}>
              {applicationStatusLabels[application.status]}
            </Badge>
          </Card>
        ))}
      </div>
    </section>
  );
}

export function EmployerApplicationsPage({ token }: { token: string }) {
  const [applications, setApplications] = useState<EmployerApplication[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState("");

  useEffect(() => {
    let cancelled = false;
    fetchEmployerApplications(token)
      .then((results) => {
        if (!cancelled) setApplications(results);
      })
      .catch((cause: unknown) => {
        if (!cancelled) setError(errorMessage(cause));
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  async function updateStatus(
    application: EmployerApplication,
    nextStatus: Exclude<JobApplicationStatus, "submitted">,
  ) {
    setBusyId(application.id);
    setError("");
    try {
      const updated = await updateEmployerApplicationStatus(token, application.id, nextStatus);
      setApplications((current) =>
        current.map((item) => item.id === updated.id ? { ...item, status: updated.status } : item),
      );
    } catch (cause: unknown) {
      setError(errorMessage(cause));
    } finally {
      setBusyId("");
    }
  }

  return (
    <section className="market-page">
      <div className="eyebrow">RECRUTEMENT</div>
      <h1>Candidatures reçues</h1>
      <p className="market-page__intro">
        Consultez les candidatures liées à vos offres et enregistrez une décision explicite pour
        suivre les résultats.
      </p>
      {error && <p className="workspace-error" role="alert">{error}</p>}
      {isLoading && <p aria-live="polite">Chargement des candidatures…</p>}
      {!isLoading && applications.length === 0 && (
        <Card className="market-panel">
          <EmptyState title="Aucune candidature reçue" description="Les candidatures envoyées à vos offres apparaîtront ici." />
        </Card>
      )}
      <div className="market-list">
        {applications.map((application) => {
          const closed = application.status === "hired" || application.status === "rejected";
          return (
            <Card className="market-applicant-card" key={application.id}>
              <div className="market-panel__heading">
                <div>
                  <Badge tone={application.status === "hired" ? "success" : "neutral"}>
                    {applicationStatusLabels[application.status]}
                  </Badge>
                  <h2>{application.candidate_name || "Candidat sans nom renseigné"}</h2>
                  <p>{application.job_title} · {application.candidate_location || "Lieu non renseigné"}</p>
                </div>
                {!closed && (
                  <label className="form-field market-status-control">
                    <span className="form-field__label">Mettre à jour le statut</span>
                    <select
                      className="select"
                      aria-label={`Statut de la candidature de ${application.candidate_name || "ce candidat"}`}
                      value={application.status}
                      disabled={busyId === application.id}
                      onChange={(event) =>
                        void updateStatus(
                          application,
                          event.target.value as Exclude<JobApplicationStatus, "submitted">,
                        )
                      }
                    >
                      {application.status === "submitted" && <option value="submitted">Reçue</option>}
                      <option value="reviewing">À l’étude</option>
                      <option value="interview">Entretien</option>
                      <option value="hired">Recrutée</option>
                      <option value="rejected">Non retenue</option>
                    </select>
                  </label>
                )}
              </div>
              <p className="market-applicant-skills">
                Compétences du profil : {application.candidate_skills.length
                  ? application.candidate_skills.join(", ")
                  : "Non renseignées"}
              </p>
              {closed && <p className="market-footnote">Décision clôturée et enregistrée.</p>}
            </Card>
          );
        })}
      </div>
    </section>
  );
}
