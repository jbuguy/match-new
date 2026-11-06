import { useState } from "react";
import {
  ArrowUpRight,
  BriefcaseBusiness,
  ChevronDown,
  Compass,
  GraduationCap,
  LayoutDashboard,
  Menu,
  MessageCircle,
  Moon,
  Sparkles,
  Sun,
  UserRound,
  X,
} from "lucide-react";
import { Badge, Button, Card, ProgressBar } from "./components/ui";

const navigation = [
  { label: "Vue d’ensemble", icon: LayoutDashboard },
  { label: "Mes opportunités", icon: BriefcaseBusiness },
  { label: "Mon parcours", icon: Compass },
  { label: "Formations", icon: GraduationCap },
  { label: "Assistant", icon: MessageCircle },
  { label: "Mon profil", icon: UserRound },
];

export default function App() {
  const [activePage, setActivePage] = useState("Vue d’ensemble");
  const [menuOpen, setMenuOpen] = useState(false);
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const isDashboard = activePage === "Vue d’ensemble";

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

        <div className="sidebar__label">ESPACE CANDIDAT</div>
        <nav className="nav-list" aria-label="Navigation principale">
          {navigation.map(({ label, icon: Icon }) => (
            <button
              className={`nav-item ${activePage === label ? "nav-item--active" : ""}`}
              key={label}
              type="button"
              aria-current={activePage === label ? "page" : undefined}
              onClick={() => {
                setActivePage(label);
                setMenuOpen(false);
              }}
            >
              <Icon size={19} strokeWidth={1.8} aria-hidden="true" />
              <span>{label}</span>
              {label === "Assistant" && <span className="nav-item__new">Nouveau</span>}
            </button>
          ))}
        </nav>

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

        <div className="account-switcher">
          <span className="avatar" aria-hidden="true">
            C
          </span>
          <span className="account-switcher__text">
            <strong>Mon espace</strong>
            <small>Candidat</small>
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
              C
            </span>
            <span className="topbar__account">Mon compte</span>
          </div>
        </header>

        <div className="page-content">
          {isDashboard ? (
            <Dashboard onNavigate={setActivePage} />
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
          <p>L’assistant sera disponible ici dès que le service sera prêt.</p>
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
