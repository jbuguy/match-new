import { useEffect, useState, type FormEvent } from "react";
import {
  ArrowUpRight,
  BriefcaseBusiness,
  Building2,
  ChevronDown,
  ClipboardList,
  Compass,
  ClipboardCheck,
  GraduationCap,
  LayoutDashboard,
  LogOut,
  Menu,
  MessageCircle,
  Moon,
  Settings2,
  Sparkles,
  Sun,
  UserRound,
  X,
} from "lucide-react";
import { Badge, Button, Card, ProgressBar } from "./components/ui";
import {
  AdminDashboardPage,
  CandidateApplicationsPage,
  CandidateCoursesPage,
  EmployerApplicationsPage,
  TrainingProviderDashboardPage,
} from "./marketplace";
import {
  CandidateAssistantPage,
  CandidateInterviewPreparationPage,
  CandidateMatchesPage,
  CandidateProfilePage,
  CandidateRoadmapPage,
  EmployerOffersPage,
  RoleAssistant,
} from "./workspaces";
import {
  ApiError,
  demoAccounts,
  fetchCurrentUser,
  login,
  registerCandidate,
  type AuthUser,
  type Role,
} from "./auth";

const roleConfiguration: Record<
  Role,
  {
    label: string;
    navigation: { label: string; icon: typeof LayoutDashboard }[];
    dashboardTitle: string;
    dashboardDescription: string;
  }
> = {
  candidate: {
    label: "Candidat",
    navigation: [
      { label: "Vue d’ensemble", icon: LayoutDashboard },
      { label: "Mes opportunités", icon: BriefcaseBusiness },
      { label: "Mon parcours", icon: Compass },
      { label: "Préparer un entretien", icon: ClipboardCheck },
      { label: "Formations", icon: GraduationCap },
      { label: "Mes candidatures", icon: ClipboardList },
      { label: "Assistant", icon: MessageCircle },
      { label: "Mon profil", icon: UserRound },
    ],
    dashboardTitle: "Votre espace candidat",
    dashboardDescription: "Vos compétences ouvrent des portes vers des emplois et des formations.",
  },
  employer: {
    label: "Employeur",
    navigation: [
      { label: "Vue d’ensemble", icon: LayoutDashboard },
      { label: "Mes offres", icon: BriefcaseBusiness },
      { label: "Candidatures", icon: UserRound },
      { label: "Assistant", icon: MessageCircle },
      { label: "Mon organisation", icon: Building2 },
    ],
    dashboardTitle: "Votre espace employeur",
    dashboardDescription: "Gérez les offres de votre organisation et suivez les candidatures reçues.",
  },
  ministry_admin: {
    label: "Administration",
    navigation: [{ label: "Vue d’ensemble", icon: LayoutDashboard }],
    dashboardTitle: "Espace administration",
    dashboardDescription: "Suivez les indicateurs agrégés de la plateforme et les résultats déclarés.",
  },
  training_provider: {
    label: "Organisme de formation",
    navigation: [
      { label: "Vue d’ensemble", icon: LayoutDashboard },
      { label: "Catalogue de formations", icon: GraduationCap },
    ],
    dashboardTitle: "Espace organisme de formation",
    dashboardDescription: "Gérez votre catalogue de formations liées aux compétences validées.",
  },
  operator: {
    label: "Opérations",
    navigation: [
      { label: "Vue d’ensemble", icon: LayoutDashboard },
      { label: "Services", icon: Settings2 },
      { label: "Journaux d’audit", icon: ClipboardList },
    ],
    dashboardTitle: "Espace opérations",
    dashboardDescription: "Suivez les services et journaux sans accéder aux données personnelles.",
  },
};

export default function App() {
  const [activePage, setActivePage] = useState("Vue d’ensemble");
  const [menuOpen, setMenuOpen] = useState(false);
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const [accessToken, setAccessToken] = useState<string | null>(() =>
    sessionStorage.getItem("mahara-match-token"),
  );
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(Boolean(accessToken));
  const [authError, setAuthError] = useState("");
  const isDashboard = activePage === "Vue d’ensemble";

  useEffect(() => {
    if (!accessToken) {
      setIsLoading(false);
      return;
    }

    let cancelled = false;
    fetchCurrentUser(accessToken)
      .then((authenticatedUser) => {
        if (!cancelled) {
          setUser(authenticatedUser);
          if (!user) {
            setActivePage(roleConfiguration[authenticatedUser.role].navigation[0].label);
          }
          setIsLoading(false);
        }
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        if (error instanceof ApiError && error.status === 401) {
          sessionStorage.removeItem("mahara-match-token");
          setAccessToken(null);
        }
        setAuthError(
          error instanceof ApiError
            ? error.message
            : "Impossible de joindre le service. Vérifiez votre connexion.",
        );
        setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [accessToken]);

  async function handleAuthentication(
    event: FormEvent<HTMLFormElement>,
    email: string,
    password: string,
    isRegistration: boolean,
  ) {
    event.preventDefault();
    setAuthError("");
    try {
      const result = isRegistration
        ? await registerCandidate(email, password)
        : await login(email, password);
      sessionStorage.setItem("mahara-match-token", result.access_token);
      setAccessToken(result.access_token);
      setUser(result.user);
      setActivePage(
        isRegistration
          ? "Mon profil"
          : roleConfiguration[result.user.role].navigation[0].label,
      );
    } catch (error: unknown) {
      setAuthError(
        error instanceof ApiError
          ? error.message
          : "Impossible de joindre le service. Vérifiez votre connexion.",
      );
    }
  }

  function handleLogout() {
    sessionStorage.removeItem("mahara-match-token");
    setAccessToken(null);
    setUser(null);
    setAuthError("");
    setActivePage("Vue d’ensemble");
  }

  if (isLoading) {
    return (
      <div className="app-shell" data-theme={theme}>
        <main className="auth-page" aria-live="polite">
          <p>Vérification de votre session…</p>
        </main>
      </div>
    );
  }

  if (!user || !accessToken) {
    return (
      <div className="app-shell" data-theme={theme}>
        <LoginPage
          error={authError}
          theme={theme}
          onToggleTheme={() => setTheme(theme === "light" ? "dark" : "light")}
          onAuthenticate={handleAuthentication}
        />
      </div>
    );
  }

  const configuration = roleConfiguration[user.role];
  const isCandidate = user.role === "candidate";

  return (
    <div className="app-shell" data-theme={theme}>
      <aside className={`sidebar ${menuOpen ? "sidebar--open" : ""}`}>
        <div className="brand-row">
          <a
            className="brand"
            href="#accueil"
            aria-label="Mahara Match, accueil"
            onClick={() => setActivePage("Vue d’ensemble")}
          >
            <span className="brand__mark" aria-hidden="true">
              m
            </span>
            <span className="brand__name">
              mahara<span>match</span>
            </span>
          </a>
          <button
            className="icon-button sidebar__close"
            type="button"
            aria-label="Fermer le menu"
            onClick={() => setMenuOpen(false)}
          >
            <X size={20} />
          </button>
        </div>

        <div className="sidebar__label">ESPACE {configuration.label.toLocaleUpperCase("fr-FR")}</div>
        <nav className="nav-list" aria-label="Navigation principale">
          {configuration.navigation.map(({ label, icon: Icon }) => (
            <button
              className={`nav-item ${activePage === label ? "nav-item--active" : ""}`}
              key={label}
              type="button"
              aria-label={label}
              aria-current={activePage === label ? "page" : undefined}
              onClick={() => {
                setActivePage(label);
                setMenuOpen(false);
              }}
            >
              <Icon size={19} strokeWidth={1.8} aria-hidden="true" />
              <span>{label}</span>
              {isCandidate && label === "Assistant" && (
                <span className="nav-item__new">Nouveau</span>
              )}
            </button>
          ))}
        </nav>

        {isCandidate && (
          <Card className="sidebar-tip">
            <span className="sidebar-tip__icon">
              <Sparkles size={17} aria-hidden="true" />
            </span>
            <strong>Vos compétences ouvrent des portes.</strong>
            <p>Complétez votre profil pour découvrir les prochaines étapes.</p>
            <Button
              variant="secondary"
              className="sidebar-tip__button"
              onClick={() => setActivePage("Mon profil")}
            >
              Compléter mon profil <ArrowUpRight size={15} aria-hidden="true" />
            </Button>
          </Card>
        )}

        <div className="account-switcher">
          <span className="avatar" aria-hidden="true">
            {configuration.label.slice(0, 1)}
          </span>
          <span className="account-switcher__text">
            <strong>{user.email}</strong>
            <small>{configuration.label}</small>
          </span>
          <ChevronDown size={16} aria-hidden="true" />
        </div>
      </aside>

      {menuOpen && (
        <button
          className="sidebar-scrim"
          type="button"
          aria-label="Fermer le menu"
          onClick={() => setMenuOpen(false)}
        />
      )}

      <main className="main-area">
        <header className="topbar">
          <button
            className="icon-button menu-toggle"
            type="button"
            aria-label="Ouvrir le menu"
            onClick={() => setMenuOpen(true)}
          >
            <Menu size={21} />
          </button>
          <div className="breadcrumbs">
            <span>Mon espace</span>
            <span aria-hidden="true">/</span>
            <strong>{activePage}</strong>
          </div>
          <div className="topbar__actions">
            <button
              className="icon-button"
              type="button"
              aria-label={theme === "light" ? "Activer le thème sombre" : "Activer le thème clair"}
              onClick={() => setTheme(theme === "light" ? "dark" : "light")}
            >
              {theme === "light" ? <Moon size={18} /> : <Sun size={18} />}
            </button>
            <span className="topbar__divider" />
            <span className="avatar avatar--small" aria-hidden="true">
              {configuration.label.slice(0, 1)}
            </span>
            <span className="topbar__account">{configuration.label}</span>
            <button className="icon-button" type="button" aria-label="Se déconnecter" onClick={handleLogout}>
              <LogOut size={18} />
            </button>
          </div>
        </header>

        <div className="page-content">
          {isDashboard ? (
            isCandidate ? (
              <Dashboard onNavigate={setActivePage} />
            ) : user.role === "ministry_admin" ? (
              <AdminDashboardPage token={accessToken} />
            ) : user.role === "training_provider" ? (
              <TrainingProviderDashboardPage token={accessToken} />
            ) : (
              <RoleDashboard
                title={configuration.dashboardTitle}
                description={configuration.dashboardDescription}
                role={configuration.label}
                onNavigate={setActivePage}
              />
            )
          ) : isCandidate && activePage === "Mon profil" ? (
            <CandidateProfilePage token={accessToken} />
          ) : isCandidate && activePage === "Mes opportunités" ? (
            <CandidateMatchesPage token={accessToken} onNavigate={setActivePage} />
          ) : isCandidate && activePage === "Mon parcours" ? (
            <CandidateRoadmapPage token={accessToken} onNavigate={setActivePage} />
          ) : isCandidate && activePage === "Préparer un entretien" ? (
            <CandidateInterviewPreparationPage token={accessToken} onNavigate={setActivePage} />
          ) : isCandidate && activePage === "Assistant" ? (
            <CandidateAssistantPage token={accessToken} onNavigate={setActivePage} />
          ) : isCandidate && activePage === "Formations" ? (
            <CandidateCoursesPage token={accessToken} />
          ) : isCandidate && activePage === "Mes candidatures" ? (
            <CandidateApplicationsPage token={accessToken} />
          ) : user.role === "employer" && activePage === "Mes offres" ? (
            <EmployerOffersPage token={accessToken} />
          ) : user.role === "employer" && activePage === "Candidatures" ? (
            <EmployerApplicationsPage token={accessToken} />
          ) : user.role === "employer" && activePage === "Assistant" ? (
            <RoleAssistant role="employer" onNavigate={setActivePage} />
          ) : user.role === "training_provider" && activePage === "Catalogue de formations" ? (
            <TrainingProviderDashboardPage token={accessToken} />
          ) : (
            <section className="page-placeholder">
              <Badge>En préparation</Badge>
              <h1>{activePage}</h1>
              <p>
                Cet espace n’est pas encore disponible. Aucune information n’est
                simulée ; vos données apparaîtront ici lorsque la fonctionnalité
                sera prête.
              </p>
              <Button variant="secondary" onClick={() => setActivePage("Vue d’ensemble")}>
                Retour à la vue d’ensemble
              </Button>
            </section>
          )}
        </div>
      </main>
    </div>
  );
}

function LoginPage({
  error,
  theme,
  onToggleTheme,
  onAuthenticate,
}: {
  error: string;
  theme: "light" | "dark";
  onToggleTheme: () => void;
  onAuthenticate: (
    event: FormEvent<HTMLFormElement>,
    email: string,
    password: string,
    isRegistration: boolean,
  ) => Promise<void>;
}) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isRegistering, setIsRegistering] = useState(false);

  return (
    <main className="auth-page">
      <div className="auth-toolbar">
        <a className="brand" href="#accueil" aria-label="Mahara Match, accueil">
          <span className="brand__mark" aria-hidden="true">m</span>
          <span className="brand__name">mahara<span>match</span></span>
        </a>
        <button
          className="icon-button"
          type="button"
          aria-label={theme === "light" ? "Activer le thème sombre" : "Activer le thème clair"}
          onClick={onToggleTheme}
        >
          {theme === "light" ? <Moon size={18} /> : <Sun size={18} />}
        </button>
      </div>
      <section className="auth-card" aria-labelledby="login-title">
        <Badge tone="accent">Mahara Match</Badge>
        <h1 id="login-title">
          {isRegistering ? "Créez votre espace candidat" : "Connectez-vous à votre espace"}
        </h1>
        <p>
          {isRegistering
            ? "Créez votre compte, puis complétez votre profil avec l’assistant."
            : "Chaque compte accède uniquement aux fonctions de son rôle."}
        </p>
        <form
          className="auth-form"
          onSubmit={(event) => void onAuthenticate(event, email, password, isRegistering)}
        >
          <label>
            <span>Adresse e-mail</span>
            <input
              autoComplete={isRegistering ? "email" : "username"}
              type="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </label>
          <label>
            <span>Mot de passe</span>
            <input
              autoComplete={isRegistering ? "new-password" : "current-password"}
              type="password"
              required
              minLength={isRegistering ? 12 : undefined}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>
          {isRegistering && (
            <p className="auth-password-hint">Utilisez au moins 12 caractères.</p>
          )}
          {error && <p className="auth-error" role="alert">{error}</p>}
          <Button type="submit" className="auth-submit">
            {isRegistering ? "Créer mon compte" : "Se connecter"}
          </Button>
        </form>
        <button
          className="auth-mode-toggle"
          type="button"
          onClick={() => setIsRegistering(!isRegistering)}
        >
          {isRegistering ? "J’ai déjà un compte" : "Créer un compte candidat"}
        </button>
        {!isRegistering && <div className="demo-account-list">
          <strong>Comptes de démonstration</strong>
          <p>Choisissez un compte pour remplir son adresse e-mail. Le mot de passe est fourni lors du seed local.</p>
          <div className="demo-account-list__buttons">
            {demoAccounts.map((account) => (
              <button
                key={account.role}
                type="button"
                onClick={() => setEmail(account.email)}
              >
                {account.label}
              </button>
            ))}
          </div>
        </div>}
      </section>
    </main>
  );
}

function RoleDashboard({
  title,
  description,
  role,
  onNavigate,
}: {
  title: string;
  description: string;
  role: string;
  onNavigate: (page: string) => void;
}) {
  return (
    <section className="role-dashboard">
      <div className="eyebrow">{role.toLocaleUpperCase("fr-FR")}</div>
      <h1>{title}</h1>
      <p className="role-dashboard__description">{description}</p>
      <Card className="role-dashboard__empty">
        {role === "Employeur" ? (
          <>
            <Badge>Gestion des offres</Badge>
            <h2>Publiez une offre pour trouver les bons profils</h2>
            <p>Décrivez le poste et ses compétences clés pour la proposer aux candidats.</p>
            <Button onClick={() => onNavigate("Mes offres")}>Créer une offre</Button>
          </>
        ) : (
          <>
            <Badge>En préparation</Badge>
            <h2>Votre espace est prêt à être configuré</h2>
            <p>
              Les fonctions de ce rôle ne sont pas encore disponibles. Aucune offre,
              candidature, formation ou statistique n’est simulée.
            </p>
          </>
        )}
      </Card>
    </section>
  );
}

function Dashboard({ onNavigate }: { onNavigate: (page: string) => void }) {
  return (
    <>
      <section className="welcome-row">
        <div>
          <div className="eyebrow">
            {new Intl.DateTimeFormat("fr-FR", {
              weekday: "long",
              day: "numeric",
              month: "long",
            }).format(new Date()).toLocaleUpperCase("fr-FR")}
          </div>
          <h1>Bonjour et bienvenue</h1>
          <p className="welcome-row__subtitle">
            Votre prochain projet professionnel commence ici.
          </p>
        </div>
        <Button onClick={() => onNavigate("Mon profil")}>
          <UserRound size={17} aria-hidden="true" />
          Compléter mon profil
        </Button>
      </section>

      <section className="profile-card" aria-labelledby="profile-title">
        <div className="profile-card__content">
          <div className="profile-card__heading">
            <div>
              <div className="eyebrow eyebrow--light">VOTRE PROFIL</div>
              <h2 id="profile-title">Faites briller vos compétences</h2>
            </div>
            <div className="profile-score" aria-label="Profil à compléter">
              <span>—</span>
              <small>à compléter</small>
            </div>
          </div>
          <p>
            Quelques informations suffisent pour commencer à explorer des
            opportunités qui vous ressemblent.
          </p>
          <div className="profile-card__footer">
            <div className="profile-progress">
              <div className="profile-progress__label">
                <span>Profil en cours de création</span>
                <span>Ajoutez vos premières informations</span>
              </div>
              <ProgressBar value={0} label="Profil en cours de création" />
            </div>
            <Button variant="light" onClick={() => onNavigate("Mon profil")}>
              Démarrer <ArrowUpRight size={16} aria-hidden="true" />
            </Button>
          </div>
        </div>
        <div className="profile-card__art" aria-hidden="true">
          <div className="orbit orbit--one" />
          <div className="orbit orbit--two" />
          <div className="art-spark art-spark--one">✳</div>
          <div className="art-spark art-spark--two">✦</div>
          <div className="art-center">
            <span>m</span>
            <i />
          </div>
        </div>
      </section>

      <section className="section-heading">
        <div>
          <div className="eyebrow">VOTRE ESPACE</div>
          <h2>Un premier pas à la fois</h2>
        </div>
        <Badge tone="accent">Bienvenue</Badge>
      </section>

      <section className="overview-grid" aria-label="Aperçu de votre espace">
        <Card className="overview-card">
          <div className="overview-card__top">
            <span className="overview-icon overview-icon--blue">
              <BriefcaseBusiness size={19} aria-hidden="true" />
            </span>
            <span className="overview-card__arrow" aria-hidden="true">
              <ArrowUpRight size={17} />
            </span>
          </div>
          <h3>Opportunités</h3>
          <p>Vos pistes professionnelles apparaîtront ici lorsque votre profil sera prêt.</p>
          <button className="text-link" type="button" onClick={() => onNavigate("Mes opportunités")}>
            En savoir plus <ArrowUpRight size={14} aria-hidden="true" />
          </button>
        </Card>

        <Card className="overview-card">
          <div className="overview-card__top">
            <span className="overview-icon overview-icon--mint">
              <Compass size={19} aria-hidden="true" />
            </span>
            <span className="overview-card__arrow" aria-hidden="true">
              <ArrowUpRight size={17} />
            </span>
          </div>
          <h3>Mon parcours</h3>
          <p>Explorez des étapes adaptées à votre expérience après avoir renseigné vos compétences.</p>
          <button className="text-link" type="button" onClick={() => onNavigate("Mon parcours")}>
            En savoir plus <ArrowUpRight size={14} aria-hidden="true" />
          </button>
        </Card>

        <Card className="assistant-card">
          <span className="assistant-card__glow" aria-hidden="true" />
          <div className="assistant-card__icon">
            <Sparkles size={20} aria-hidden="true" />
          </div>
          <Badge tone="accent">À votre rythme</Badge>
          <h3>Besoin d’un coup de main ?</h3>
          <p>Obtenez des conseils pour valoriser vos compétences et mieux explorer les offres.</p>
          <Button
            variant="secondary"
            className="assistant-card__button"
            onClick={() => onNavigate("Assistant")}
          >
            Découvrir l’assistant <ArrowUpRight size={15} aria-hidden="true" />
          </Button>
        </Card>
      </section>

      <footer className="page-footer">
        <span>Mahara Match</span>
        <span>Vos compétences, votre avenir.</span>
      </footer>
    </>
  );
}
