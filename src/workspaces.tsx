import { useEffect, useRef, useState, type FormEvent } from "react";
import {
  BriefcaseBusiness,
  Check,
  Compass,
  MapPin,
  MessagesSquare,
  Mic,
  Plus,
  Send,
  Sparkles,
  Square,
  Target,
  Trash2,
} from "lucide-react";
import { Badge, Button, Card } from "./components/ui";
import {
  ApiError,
  applyToJob,
  createCandidateAssistantSession,
  createEmployerOffer,
  deleteCandidateAssistantSession,
  fetchCandidateAssistantSession,
  fetchCandidateAssistantSessions,
  fetchCandidateMatches,
  fetchCandidateApplications,
  fetchCandidateRoadmap,
  fetchCandidateProfile,
  fetchEmployerOffers,
  sendCandidateAssistantMessage,
  sendCandidateAssistantSessionMessage,
  synthesizeCandidateSpeech,
  transcribeCandidateAudio,
  updateCandidateRoadmapStep,
  updateCandidateProfile,
  type CandidateAssistantMessage,
  type CandidateProfileDraft,
  type CandidateAssistantSession,
  type CandidateAssistantSessionSummary,
  type CandidateRoadmap,
  type JobMatch,
  type JobOffer,
} from "./auth";

function errorMessage(error: unknown): string {
  return error instanceof ApiError
    ? error.message
    : "Impossible de joindre le service. Vérifiez votre connexion.";
}

function splitSkills(value: string): string[] {
  return value
    .split(/[,\n]/)
    .map((skill) => skill.trim())
    .filter(Boolean);
}

type CandidateProfileForm = {
  full_name: string;
  phone: string;
  location: string;
  education: string;
  experience: string;
  skills: string;
};

const emptyCandidateProfile: CandidateProfileForm = {
  full_name: "",
  phone: "",
  location: "",
  education: "",
  experience: "",
  skills: "",
};

export function CandidateProfilePage({ token }: { token: string }) {
  const [profile, setProfile] = useState(emptyCandidateProfile);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [messages, setMessages] = useState<CandidateAssistantMessage[]>([
    {
      role: "assistant",
      content: "Aslema ! Je peux t’aider à compléter ton profil, en Derja, en arabe ou en français. Qu’est-ce que tu aimerais me dire sur toi ?",
    },
  ]);
  const [chatText, setChatText] = useState("");
  const [chatError, setChatError] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [voiceError, setVoiceError] = useState("");
  const recorderRef = useRef<MediaRecorder | null>(null);
  const audioStreamRef = useRef<MediaStream | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  useEffect(() => {
    let cancelled = false;
    fetchCandidateProfile(token)
      .then((profile) => {
        if (!cancelled) {
          setProfile({
            full_name: profile.full_name ?? "",
            phone: profile.phone ?? "",
            location: profile.location ?? "",
            education: profile.education ?? "",
            experience: profile.experience ?? "",
            skills: profile.skills.join(", "),
          });
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

  async function saveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSaving(true);
    setError("");
    setNotice("");
    try {
      const saved = await updateCandidateProfile(token, {
        full_name: profile.full_name,
        phone: profile.phone,
        location: profile.location,
        education: profile.education,
        experience: profile.experience,
        skills: splitSkills(profile.skills),
      });
      setProfile({
        full_name: saved.full_name ?? "",
        phone: saved.phone ?? "",
        location: saved.location ?? "",
        education: saved.education ?? "",
        experience: saved.experience ?? "",
        skills: saved.skills.join(", "),
      });
      setNotice("Votre profil a été enregistré. Vous pouvez le modifier à tout moment.");
    } catch (cause: unknown) {
      setError(errorMessage(cause));
    } finally {
      setIsSaving(false);
    }
  }

  async function sendMessage(text = chatText) {
    const content = text.trim();
    if (!content || isSending) return;
    const nextMessages = [...messages, { role: "user" as const, content }].slice(-24);
    setChatText("");
    setChatError("");
    setIsSending(true);
    try {
      const result = await sendCandidateAssistantMessage(token, nextMessages);
      setMessages([...nextMessages, { role: "assistant", content: result.reply }]);
      setProfile((current) => applyProfileUpdates(current, result.profile_updates));
      void speakReply(result.reply);
    } catch (cause: unknown) {
      setChatText(content);
      setChatError(errorMessage(cause));
    } finally {
      setIsSending(false);
    }
  }

  async function speakReply(text: string) {
    try {
      const speech = await synthesizeCandidateSpeech(token, text);
      const audioUrl = URL.createObjectURL(speech);
      const audio = new Audio(audioUrl);
      audio.addEventListener("ended", () => URL.revokeObjectURL(audioUrl), { once: true });
      audio.addEventListener("error", () => URL.revokeObjectURL(audioUrl), { once: true });
      try {
        await audio.play();
        setVoiceError("");
      } catch (cause: unknown) {
        URL.revokeObjectURL(audioUrl);
        throw cause;
      }
    } catch (cause: unknown) {
      setVoiceError(
        cause instanceof ApiError
          ? `La réponse écrite est disponible. ${errorMessage(cause)}`
          : "La réponse écrite est disponible, mais la lecture vocale est indisponible.",
      );
    }
  }

  async function transcribeRecording(audio: Blob) {
    setIsTranscribing(true);
    setVoiceError("");
    try {
      const result = await transcribeCandidateAudio(token, audio);
      await sendMessage(result.text);
    } catch (cause: unknown) {
      setVoiceError(errorMessage(cause));
    } finally {
      setIsTranscribing(false);
    }
  }

  async function startRecording() {
    setVoiceError("");
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      setVoiceError("L’enregistrement audio n’est pas pris en charge par ce navigateur. Vous pouvez écrire votre message.");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      audioStreamRef.current = stream;
      recorderRef.current = recorder;
      audioChunksRef.current = [];
      recorder.addEventListener("dataavailable", (event) => {
        if (event.data.size) audioChunksRef.current.push(event.data);
      });
      recorder.addEventListener("stop", () => {
        stream.getTracks().forEach((track) => track.stop());
        audioStreamRef.current = null;
        const recording = new Blob(audioChunksRef.current, {
          type: recorder.mimeType || "audio/webm",
        });
        if (recording.size) void transcribeRecording(recording);
        else setVoiceError("Aucune voix n’a été enregistrée. Vous pouvez réessayer ou écrire votre message.");
      }, { once: true });
      recorder.start();
      setIsRecording(true);
    } catch (cause: unknown) {
      setVoiceError(
        cause instanceof DOMException && cause.name === "NotAllowedError"
          ? "L’accès au microphone a été refusé. Autorisez-le ou écrivez votre message."
          : "Impossible d’accéder au microphone. Vérifiez son autorisation ou écrivez votre message.",
      );
    }
  }

  function stopRecording() {
    if (recorderRef.current?.state === "recording") recorderRef.current.stop();
    setIsRecording(false);
  }

  useEffect(() => () => {
    if (recorderRef.current?.state === "recording") recorderRef.current.stop();
    audioStreamRef.current?.getTracks().forEach((track) => track.stop());
  }, []);

  return (
    <section className="workspace-page">
      <div className="eyebrow">VOTRE PROFIL</div>
      <h1>Complétez votre profil avec l’assistant</h1>
      <p className="workspace-page__intro">
        Répondez à votre rythme, par écrit ou à la voix. Vérifiez et modifiez chaque information avant de l’enregistrer.
      </p>
      <Card className="workspace-panel">
        {isLoading ? (
          <p aria-live="polite">Chargement de votre profil…</p>
        ) : (
          <>
            <div className="profile-assistant">
              <div className="assistant-workspace__heading">
                <span className="assistant-workspace__icon"><Sparkles size={20} aria-hidden="true" /></span>
                <div>
                  <h2>Parlons de votre parcours</h2>
                  <p>L’assistant comprend le Derja tunisien, l’arabe et le français.</p>
                </div>
              </div>
              <div className="profile-assistant__messages" aria-live="polite" aria-label="Conversation avec l’assistant">
                {messages.map((message, index) => (
                  <p
                    className={`profile-assistant__message profile-assistant__message--${message.role}`}
                    key={`${message.role}-${index}`}
                  >
                    {message.content}
                  </p>
                ))}
                {isSending && <p className="profile-assistant__pending">L’assistant prépare sa réponse…</p>}
              </div>
              <form
                className="profile-assistant__composer"
                onSubmit={(event) => {
                  event.preventDefault();
                  void sendMessage();
                }}
              >
                  <input
                    id="candidate-assistant-message"
                    className="input"
                    aria-label="Votre message"
                  value={chatText}
                  onChange={(event) => setChatText(event.target.value)}
                  placeholder="Écrivez en Derja, en arabe ou en français…"
                  maxLength={3000}
                  disabled={isSending || isTranscribing}
                />
                <Button
                  type="button"
                  variant={isRecording ? "secondary" : "ghost"}
                  aria-label={isRecording ? "Arrêter l’enregistrement" : "Enregistrer un message vocal"}
                  disabled={isSending || isTranscribing}
                  onClick={() => isRecording ? stopRecording() : void startRecording()}
                >
                  {isRecording ? <Square size={17} aria-hidden="true" /> : <Mic size={18} aria-hidden="true" />}
                </Button>
                <Button type="submit" aria-label="Envoyer le message" disabled={isSending || isTranscribing || !chatText.trim()}>
                  <Send size={17} aria-hidden="true" />
                </Button>
              </form>
              {isTranscribing && <p className="workspace-assistant-status" role="status">Transcription de votre message…</p>}
              {chatError && <p className="workspace-error" role="alert">{chatError}</p>}
              {voiceError && <p className="workspace-assistant-status" role="status">{voiceError}</p>}
              <p className="assistant-disclaimer">
                Les informations proposées restent modifiables et ne sont enregistrées qu’après votre validation.
                L’audio n’est pas conservé.
              </p>
            </div>
            <form className="workspace-form profile-editor" onSubmit={(event) => void saveProfile(event)}>
              <h2>Vérifiez vos informations</h2>
              <ProfileTextField
                label="Nom complet"
                value={profile.full_name}
                maxLength={200}
                onChange={(value) => setProfile({ ...profile, full_name: value })}
              />
              <ProfileTextField
                label="Téléphone"
                value={profile.phone}
                maxLength={40}
                onChange={(value) => setProfile({ ...profile, phone: value })}
              />
              <ProfileTextField
                label="Lieu de résidence"
                value={profile.location}
                maxLength={120}
                onChange={(value) => setProfile({ ...profile, location: value })}
              />
              <ProfileTextField
                label="Études et formations"
                value={profile.education}
                maxLength={5000}
                multiline
                onChange={(value) => setProfile({ ...profile, education: value })}
              />
              <ProfileTextField
                label="Expérience professionnelle"
                value={profile.experience}
                maxLength={5000}
                multiline
                onChange={(value) => setProfile({ ...profile, experience: value })}
              />
              <ProfileTextField
                label="Compétences"
                value={profile.skills}
                maxLength={2200}
                multiline
                hint="Séparez les compétences par des virgules."
                onChange={(value) => setProfile({ ...profile, skills: value })}
              />
              {error && <p className="workspace-error" role="alert">{error}</p>}
              {notice && <p className="workspace-success" role="status">{notice}</p>}
              <Button type="submit" disabled={isSaving}>
                {isSaving ? "Enregistrement…" : "Enregistrer mon profil"}
              </Button>
            </form>
          </>
        )}
      </Card>
    </section>
  );
}

function applyProfileUpdates(
  current: CandidateProfileForm,
  updates: Partial<CandidateProfileDraft>,
): CandidateProfileForm {
  return {
    ...current,
    full_name: updates.full_name ?? current.full_name,
    phone: updates.phone ?? current.phone,
    location: updates.location ?? current.location,
    education: updates.education ?? current.education,
    experience: updates.experience ?? current.experience,
    skills: updates.skills ? updates.skills.join(", ") : current.skills,
  };
}

function ProfileTextField({
  label,
  value,
  maxLength,
  multiline = false,
  hint,
  onChange,
}: {
  label: string;
  value: string;
  maxLength: number;
  multiline?: boolean;
  hint?: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="form-field">
      <span className="form-field__label">{label}</span>
      {multiline ? (
        <textarea
          className="input workspace-textarea workspace-textarea--short"
          aria-label={label}
          value={value}
          maxLength={maxLength}
          onChange={(event) => onChange(event.target.value)}
        />
      ) : (
        <input
          className="input"
          aria-label={label}
          value={value}
          maxLength={maxLength}
          onChange={(event) => onChange(event.target.value)}
        />
      )}
      {hint && <span className="form-field__hint">{hint}</span>}
    </label>
  );
}

export function CandidateAssistantPage({
  token,
  onNavigate,
}: {
  token: string;
  onNavigate: (page: string) => void;
}) {
  const [sessions, setSessions] = useState<CandidateAssistantSessionSummary[]>([]);
  const [activeSession, setActiveSession] = useState<CandidateAssistantSession | null>(null);
  const [chatText, setChatText] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [isOpening, setIsOpening] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    async function loadSessions() {
      try {
        const history = await fetchCandidateAssistantSessions(token);
        if (cancelled) return;
        setSessions(history);
        if (history.length) {
          const firstSession = await fetchCandidateAssistantSession(token, history[0].id);
          if (!cancelled) setActiveSession(firstSession);
        } else {
          const created = await createCandidateAssistantSession(token);
          if (!cancelled) {
            setActiveSession(created);
            setSessions([created]);
          }
        }
      } catch (cause: unknown) {
        if (!cancelled) setError(errorMessage(cause));
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }
    void loadSessions();
    return () => {
      cancelled = true;
    };
  }, [token]);

  async function createSession() {
    setError("");
    setIsOpening(true);
    try {
      const created = await createCandidateAssistantSession(token);
      setActiveSession(created);
      setSessions((current) => [created, ...current]);
    } catch (cause: unknown) {
      setError(errorMessage(cause));
    } finally {
      setIsOpening(false);
    }
  }

  async function openSession(sessionId: string) {
    setError("");
    setIsOpening(true);
    try {
      setActiveSession(await fetchCandidateAssistantSession(token, sessionId));
    } catch (cause: unknown) {
      setError(errorMessage(cause));
    } finally {
      setIsOpening(false);
    }
  }

  async function sendMessage(text = chatText) {
    const content = text.trim();
    if (!content || isSending || !activeSession) return;
    setChatText("");
    setError("");
    setIsSending(true);
    try {
      const updated = await sendCandidateAssistantSessionMessage(
        token,
        activeSession.id,
        content,
      );
      setActiveSession(updated);
      setSessions((current) => [
        { id: updated.id, title: updated.title, created_at: updated.created_at, updated_at: updated.updated_at },
        ...current.filter((item) => item.id !== updated.id),
      ]);
    } catch (cause: unknown) {
      setChatText(content);
      setError(errorMessage(cause));
    } finally {
      setIsSending(false);
    }
  }

  async function deleteSession(sessionId: string) {
    setError("");
    setIsOpening(true);
    try {
      await deleteCandidateAssistantSession(token, sessionId);
      const remaining = sessions.filter((item) => item.id !== sessionId);
      setSessions(remaining);
      if (activeSession?.id === sessionId) {
        if (remaining.length) {
          setActiveSession(await fetchCandidateAssistantSession(token, remaining[0].id));
        }
        else {
          const created = await createCandidateAssistantSession(token);
          setActiveSession(created);
          setSessions([created]);
        }
      }
    } catch (cause: unknown) {
      setError(errorMessage(cause));
    } finally {
      setIsOpening(false);
    }
  }

  const messages = activeSession?.messages ?? [];

  return (
    <section className="workspace-page">
      <div className="eyebrow">ASSISTANT CARRIÈRE</div>
      <h1>Votre assistant carrière</h1>
      <p className="workspace-page__intro">
        Posez vos questions en Derja, en arabe ou en français. Vos conversations sont enregistrées dans votre espace et peuvent être supprimées.
      </p>
      <div className="career-assistant-layout">
        <Card className="career-assistant-history">
          <div className="career-assistant-history__heading">
            <h2>Historique</h2>
            <Button
              type="button"
              variant="secondary"
              aria-label="Nouvelle conversation"
              disabled={isLoading || isOpening || isSending}
              onClick={() => void createSession()}
            >
              <Plus size={16} aria-hidden="true" />
              Nouveau
            </Button>
          </div>
          {isLoading ? (
            <p aria-live="polite">Chargement de vos conversations…</p>
          ) : sessions.length ? (
            <ul className="career-assistant-history__list">
              {sessions.map((item) => (
                <li key={item.id}>
                  <button
                    className={`career-assistant-history__item${activeSession?.id === item.id ? " career-assistant-history__item--active" : ""}`}
                    type="button"
                    disabled={isOpening}
                    aria-current={activeSession?.id === item.id ? "page" : undefined}
                    onClick={() => void openSession(item.id)}
                  >
                    <MessagesSquare size={16} aria-hidden="true" />
                    <span>{item.title}</span>
                  </button>
                  <button
                    className="icon-button career-assistant-history__delete"
                    type="button"
                    aria-label={`Supprimer ${item.title}`}
                    disabled={isOpening || isSending}
                    onClick={() => void deleteSession(item.id)}
                  >
                    <Trash2 size={15} aria-hidden="true" />
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p>Aucune conversation enregistrée.</p>
          )}
        </Card>
        <Card className="career-assistant-chat">
          <div className="assistant-workspace__heading">
            <span className="assistant-workspace__icon"><Sparkles size={20} aria-hidden="true" /></span>
            <div>
              <h2>Parlons de votre avenir</h2>
              <p>Un échange bienveillant pour explorer vos prochaines étapes.</p>
            </div>
          </div>
          <div className="profile-assistant__messages career-assistant-chat__messages" aria-live="polite" aria-label="Conversation avec l’assistant carrière">
            {isLoading || isOpening ? (
              <p aria-live="polite">Chargement de la conversation…</p>
            ) : messages.length ? (
              messages.map((message, index) => (
                <p
                  className={`profile-assistant__message profile-assistant__message--${message.role}`}
                  key={`${message.role}-${index}`}
                >
                  {message.content}
                </p>
              ))
            ) : (
              <p className="profile-assistant__message profile-assistant__message--assistant">
                Aslema ! Nجم نحكيو على مهاراتك، الخدمة، ولا التكوين. شنوة تحب تعرف؟
              </p>
            )}
            {isSending && <p className="profile-assistant__pending">L’assistant prépare sa réponse…</p>}
          </div>
          {!messages.length && !isLoading && (
            <div className="career-assistant-prompts">
              <Button type="button" variant="secondary" disabled={isSending || isOpening || isLoading} onClick={() => void sendMessage("Comment obtenir de meilleures correspondances avec mes compétences ?")}>
                Comment obtenir de meilleures correspondances ?
              </Button>
              <Button type="button" variant="secondary" disabled={isSending || isOpening || isLoading} onClick={() => void sendMessage("Quelles compétences puis-je développer pour trouver un emploi ?")}>
                Quelles compétences développer ?
              </Button>
            </div>
          )}
          <form
            className="profile-assistant__composer"
            onSubmit={(event) => {
              event.preventDefault();
              void sendMessage();
            }}
          >
            <input
              className="input"
              aria-label="Votre message"
              value={chatText}
              onChange={(event) => setChatText(event.target.value)}
              placeholder="Écrivez en Derja, en arabe ou en français…"
              maxLength={3000}
              disabled={isLoading || isOpening || isSending || !activeSession}
            />
            <Button type="submit" aria-label="Envoyer le message" disabled={isLoading || isOpening || isSending || !chatText.trim() || !activeSession}>
              <Send size={17} aria-hidden="true" />
            </Button>
          </form>
          {error && (
            <p className="career-assistant-error" role="alert">{error}</p>
          )}
          <Button
            type="button"
            className="career-assistant-manual"
            variant="secondary"
            onClick={() => onNavigate("Mon profil")}
          >
            Compléter mon profil manuellement
          </Button>
          <p className="assistant-disclaimer">
            L’assistant peut se tromper. Vérifiez les informations importantes. Vous pouvez aussi modifier votre profil manuellement.
          </p>
        </Card>
      </div>
    </section>
  );
}

export function CandidateRoadmapPage({
  token,
  onNavigate,
}: {
  token: string;
  onNavigate: (page: string) => void;
}) {
  const [roadmap, setRoadmap] = useState<CandidateRoadmap | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [savingSkill, setSavingSkill] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    fetchCandidateRoadmap(token)
      .then((result) => {
        if (!cancelled) setRoadmap(result);
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

  async function toggleStep(skill: string, completed: boolean) {
    setSavingSkill(skill);
    setError("");
    try {
      setRoadmap(await updateCandidateRoadmapStep(token, skill, completed));
    } catch (cause: unknown) {
      setError(errorMessage(cause));
    } finally {
      setSavingSkill("");
    }
  }

  return (
    <section className="workspace-page roadmap-page">
      <div className="eyebrow">VOTRE PROGRESSION</div>
      <h1>Mon parcours professionnel</h1>
      <p className="workspace-page__intro">
        Un plan d’étapes déterministe basé sur les compétences demandées dans les offres et celles
        déjà renseignées dans votre profil.
      </p>
      {isLoading && <p aria-live="polite">Préparation de votre parcours…</p>}
      {error && <p className="workspace-error" role="alert">{error}</p>}
      {!isLoading && roadmap && roadmap.steps.length > 0 && (
        <>
          <Card className="roadmap-progress">
            <div className="roadmap-progress__copy">
              <span className="roadmap-progress__icon" aria-hidden="true"><Compass size={20} /></span>
              <div>
                <strong>Votre progression</strong>
                <p>{roadmap.completed_steps} étape{roadmap.completed_steps === 1 ? "" : "s"} sur {roadmap.total_steps} validée{roadmap.total_steps === 1 ? "" : "s"}</p>
              </div>
              <strong className="roadmap-progress__percent">{roadmap.progress_percent}%</strong>
            </div>
            <div
              className="roadmap-progress__track"
              role="progressbar"
              aria-label="Progression du parcours"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={roadmap.progress_percent}
            >
              <span style={{ width: `${roadmap.progress_percent}%` }} />
            </div>
          </Card>
          <ol className="roadmap-steps">
            {roadmap.steps.map((step, index) => (
              <li className={`roadmap-step ${step.completed ? "roadmap-step--completed" : ""}`} key={step.skill_key}>
                <span className="roadmap-step__marker" aria-hidden="true">
                  {step.completed ? <Check size={17} /> : index + 1}
                </span>
                <Card className="roadmap-step__card">
                  <div className="roadmap-step__heading">
                    <div>
                      <span className="eyebrow">ÉTAPE {index + 1}</span>
                      <h2>{step.skill}</h2>
                    </div>
                    <Badge tone={step.completed ? "success" : "accent"}>
                      {step.completed ? "Terminée" : "À développer"}
                    </Badge>
                  </div>
                  <p className="roadmap-step__evidence">
                    Demandée dans {step.offer_count} offre{step.offer_count === 1 ? "" : "s"}
                    {step.required_by.length > 0 && <> : {step.required_by.join(", ")}</>}.
                  </p>
                  <p className="roadmap-step__action">
                    Travaillez cette compétence et suivez votre progression. Mettez ensuite à jour votre profil pour actualiser vos correspondances.
                  </p>
                  <Button
                    variant={step.completed ? "secondary" : "primary"}
                    className="roadmap-step__button"
                    disabled={savingSkill !== ""}
                    onClick={() => void toggleStep(step.skill, !step.completed)}
                  >
                    {savingSkill === step.skill
                      ? "Enregistrement…"
                      : step.completed
                        ? "Réouvrir l’étape"
                        : "Marquer l’étape comme terminée"}
                  </Button>
                </Card>
              </li>
            ))}
          </ol>
        </>
      )}
      {!isLoading && roadmap?.steps.length === 0 && (
        <Card className="workspace-empty">
          <Target size={25} aria-hidden="true" />
          <h2>Aucune étape à proposer pour le moment</h2>
          <p>
            Ajoutez vos compétences ou consultez les offres disponibles. Le parcours se construit
            à partir des compétences manquantes dans ces offres.
          </p>
          <div className="roadmap-empty__actions">
            <Button variant="secondary" onClick={() => onNavigate("Mon profil")}>Compléter mon profil</Button>
            <Button onClick={() => onNavigate("Mes opportunités")}>Voir les opportunités</Button>
          </div>
        </Card>
      )}
    </section>
  );
}

export function CandidateMatchesPage({
  token,
  onNavigate,
}: {
  token: string;
  onNavigate: (page: string) => void;
}) {
  const [matches, setMatches] = useState<JobMatch[]>([]);
  const [appliedOfferIds, setAppliedOfferIds] = useState<Set<string>>(new Set());
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    Promise.all([fetchCandidateMatches(token), fetchCandidateApplications(token)])
      .then(([results, applications]) => {
        if (!cancelled) {
          setMatches(results);
          setAppliedOfferIds(new Set(applications.map((application) => application.job_offer_id)));
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

  return (
    <section className="workspace-page">
      <div className="eyebrow">OPPORTUNITÉS POUR VOUS</div>
      <h1>Offres compatibles avec vos compétences</h1>
      <p className="workspace-page__intro">
        Le score compare uniquement les compétences renseignées aux compétences demandées.
      </p>
      {isLoading && <p aria-live="polite">Recherche des offres…</p>}
      {error && <p className="workspace-error" role="alert">{error}</p>}
      {!isLoading && !error && matches.length === 0 && (
        <Card className="workspace-empty">
          <BriefcaseBusiness size={24} aria-hidden="true" />
          <h2>Aucune offre à afficher pour le moment</h2>
          <p>Complétez votre profil ou revenez plus tard pour découvrir les nouvelles offres.</p>
          <Button variant="secondary" onClick={() => onNavigate("Mon profil")}>
            Ajouter mes compétences
          </Button>
        </Card>
      )}
      <div className="workspace-list">
        {matches.map((match) => (
          <MatchCard
            key={match.id}
            match={match}
            token={token}
            isApplied={appliedOfferIds.has(match.id)}
            onApplied={() =>
              setAppliedOfferIds((current) => new Set([...current, match.id]))
            }
          />
        ))}
      </div>
    </section>
  );
}

function MatchCard({
  match,
  token,
  isApplied,
  onApplied,
}: {
  match: JobMatch;
  token: string;
  isApplied: boolean;
  onApplied: () => void;
}) {
  const [isApplying, setIsApplying] = useState(false);
  const [error, setError] = useState("");

  async function apply() {
    setIsApplying(true);
    setError("");
    try {
      await applyToJob(token, match.id);
      onApplied();
    } catch (cause: unknown) {
      setError(errorMessage(cause));
    } finally {
      setIsApplying(false);
    }
  }

  return (
    <Card className="offer-card">
      <div className="offer-card__top">
        <div>
          <h2>{match.title}</h2>
          <p className="offer-card__location"><MapPin size={15} aria-hidden="true" />{match.location}</p>
        </div>
        <Badge tone={match.match_score >= 60 ? "success" : "neutral"}>
          {match.match_score}% de correspondance
        </Badge>
      </div>
      <p className="offer-card__description">{match.description}</p>
      <SkillList label="Compétences correspondantes" skills={match.matched_skills} tone="matched" />
      <SkillList label="À développer" skills={match.missing_skills} tone="missing" />
      {error && <p className="workspace-error" role="alert">{error}</p>}
      <Button disabled={isApplied || isApplying} onClick={() => void apply()}>
        {isApplying
          ? "Envoi de la candidature…"
          : isApplied
            ? "Candidature envoyée"
            : "Candidater"}
      </Button>
    </Card>
  );
}

function SkillList({
  label,
  skills,
  tone,
}: {
  label: string;
  skills: string[];
  tone: "matched" | "missing";
}) {
  return (
    <div className="skill-list">
      <strong>{label}</strong>
      {skills.length ? (
        <ul className={`skill-list__items skill-list__items--${tone}`}>
          {skills.map((skill) => <li key={skill}>{skill}</li>)}
        </ul>
      ) : (
        <span className="skill-list__none">Aucune</span>
      )}
    </div>
  );
}

type OfferForm = {
  title: string;
  description: string;
  location: string;
  requiredSkills: string;
};

const emptyOffer: OfferForm = {
  title: "",
  description: "",
  location: "",
  requiredSkills: "",
};

export function EmployerOffersPage({ token }: { token: string }) {
  const [offers, setOffers] = useState<JobOffer[]>([]);
  const [form, setForm] = useState(emptyOffer);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    let cancelled = false;
    fetchEmployerOffers(token)
      .then((results) => {
        if (!cancelled) setOffers(results);
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

  async function publishOffer(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSaving(true);
    setError("");
    setNotice("");
    try {
      const created = await createEmployerOffer(token, {
        title: form.title.trim(),
        description: form.description.trim(),
        location: form.location.trim(),
        required_skills: splitSkills(form.requiredSkills),
      });
      setOffers((current) => [created, ...current]);
      setForm(emptyOffer);
      setNotice("Votre offre est publiée et peut maintenant être proposée aux candidats.");
    } catch (cause: unknown) {
      setError(errorMessage(cause));
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <section className="workspace-page">
      <div className="eyebrow">ESPACE EMPLOYEUR</div>
      <h1>Mes offres d’emploi</h1>
      <p className="workspace-page__intro">
        Décrivez le poste et ses compétences clés pour aider les candidats à trouver les offres pertinentes.
      </p>
      <Card className="workspace-panel">
        <h2>Créer une offre</h2>
        <form className="workspace-form" onSubmit={(event) => void publishOffer(event)}>
          <label className="form-field">
            <span className="form-field__label">Intitulé du poste</span>
            <input
              className="input"
              required
              minLength={2}
              maxLength={160}
              value={form.title}
              onChange={(event) => setForm({ ...form, title: event.target.value })}
            />
          </label>
          <label className="form-field">
            <span className="form-field__label">Lieu</span>
            <input
              className="input"
              required
              minLength={2}
              maxLength={120}
              value={form.location}
              onChange={(event) => setForm({ ...form, location: event.target.value })}
            />
          </label>
          <label className="form-field">
            <span className="form-field__label">Description</span>
            <textarea
              className="input workspace-textarea"
              required
              minLength={10}
              maxLength={5000}
              value={form.description}
              onChange={(event) => setForm({ ...form, description: event.target.value })}
            />
          </label>
          <label className="form-field">
            <span className="form-field__label">Compétences requises</span>
            <textarea
              className="input workspace-textarea workspace-textarea--short"
              aria-label="Compétences requises"
              placeholder="Ex. Excel, gestion de projet, français"
              required
              value={form.requiredSkills}
              onChange={(event) => setForm({ ...form, requiredSkills: event.target.value })}
            />
            <span className="form-field__hint">Séparez les compétences par une virgule.</span>
          </label>
          {error && <p className="workspace-error" role="alert">{error}</p>}
          {notice && <p className="workspace-success" role="status">{notice}</p>}
          <Button type="submit" disabled={isSaving}>
            {isSaving ? "Publication…" : "Publier l’offre"}
          </Button>
        </form>
      </Card>
      <div className="workspace-list-heading">
        <h2>Offres publiées</h2>
        <Badge>{offers.length}</Badge>
      </div>
      {isLoading && <p aria-live="polite">Chargement de vos offres…</p>}
      {error && isLoading && <p className="workspace-error" role="alert">{error}</p>}
      {!isLoading && offers.length === 0 && (
        <Card className="workspace-empty">
          <BriefcaseBusiness size={24} aria-hidden="true" />
          <h2>Vous n’avez pas encore publié d’offre</h2>
          <p>Votre première offre apparaîtra ici après sa publication.</p>
        </Card>
      )}
      <div className="workspace-list">
        {offers.map((offer) => <OfferCard key={offer.id} offer={offer} />)}
      </div>
    </section>
  );
}

function OfferCard({ offer }: { offer: JobOffer }) {
  return (
    <Card className="offer-card">
      <div className="offer-card__top">
        <div>
          <h2>{offer.title}</h2>
          <p className="offer-card__location"><MapPin size={15} aria-hidden="true" />{offer.location}</p>
        </div>
        <Badge>Publiée</Badge>
      </div>
      <p className="offer-card__description">{offer.description}</p>
      <SkillList label="Compétences requises" skills={offer.required_skills} tone="matched" />
    </Card>
  );
}

export function RoleAssistant({
  role,
  onNavigate,
}: {
  role: "candidate" | "employer";
  onNavigate: (page: string) => void;
}) {
  const [selected, setSelected] = useState(0);
  const isCandidate = role === "candidate";
  const prompts = isCandidate
    ? [
        {
          question: "Comment obtenir de meilleures correspondances ?",
          answer: "Ajoutez à votre profil des compétences précises que vous maîtrisez réellement. Le score compare ces compétences avec celles demandées dans chaque offre.",
          action: "Mettre à jour mon profil",
          page: "Mon profil",
        },
        {
          question: "Comment lire le score d’une offre ?",
          answer: "Le pourcentage indique la part des compétences demandées que vous avez renseignées. Il ne prédit pas vos chances d’être recruté : l’expérience, la motivation et les autres critères comptent aussi.",
          action: "Voir mes opportunités",
          page: "Mes opportunités",
        },
        {
          question: "Quelles compétences ajouter ?",
          answer: "Pensez aux outils, méthodes et savoir-faire que vous utilisez dans vos expériences, vos études ou vos projets. N’ajoutez pas une compétence uniquement parce qu’elle apparaît dans une offre.",
          action: "Ajouter mes compétences",
          page: "Mon profil",
        },
      ]
    : [
        {
          question: "Comment rédiger une offre claire ?",
          answer: "Commencez par les missions concrètes, précisez le lieu et distinguez les compétences indispensables des atouts. Évitez les exigences qui ne sont pas nécessaires au poste.",
          action: "Créer une offre",
          page: "Mes offres",
        },
        {
          question: "Quelles compétences indiquer ?",
          answer: "Choisissez quelques compétences observables et directement utiles au poste : outils maîtrisés, méthodes de travail et savoir-faire métier. Des libellés simples facilitent les correspondances.",
          action: "Créer une offre",
          page: "Mes offres",
        },
        {
          question: "Comment rendre l’offre plus inclusive ?",
          answer: "Utilisez un langage accueillant, concentrez-vous sur les responsabilités réelles et indiquez clairement les conditions du poste. Distinguez les exigences indispensables des compétences qui peuvent s’acquérir.",
          action: "Créer une offre",
          page: "Mes offres",
        },
      ];

  return (
    <section className="workspace-page">
      <div className="eyebrow">ASSISTANT MAHARA MATCH</div>
      <h1>{isCandidate ? "Votre assistant carrière" : "Votre assistant recrutement"}</h1>
      <p className="workspace-page__intro">
        {isCandidate
          ? "Des conseils pratiques pour valoriser vos compétences et explorer des offres."
          : "Des repères pour rédiger des offres plus claires et mieux décrire les compétences recherchées."}
      </p>
      <Card className="assistant-workspace">
        <div className="assistant-workspace__heading">
          <span className="assistant-workspace__icon"><Sparkles size={20} aria-hidden="true" /></span>
          <div>
            <h2>Comment puis-je vous aider ?</h2>
            <p>Choisissez un sujet pour obtenir un conseil adapté à votre espace.</p>
          </div>
        </div>
        <div className="assistant-prompts" role="group" aria-label="Sujets d’aide">
          {prompts.map((prompt, index) => (
            <button
              className={`assistant-prompt ${selected === index ? "assistant-prompt--active" : ""}`}
              key={prompt.question}
              type="button"
              aria-pressed={selected === index}
              onClick={() => setSelected(index)}
            >
              {prompt.question}
            </button>
          ))}
        </div>
        <div className="assistant-answer" aria-live="polite">
          <Badge tone="accent">Conseil</Badge>
          <p>{prompts[selected].answer}</p>
          <Button variant="secondary" onClick={() => onNavigate(prompts[selected].page)}>
            {prompts[selected].action} <Check size={15} aria-hidden="true" />
          </Button>
        </div>
        <p className="assistant-disclaimer">
          Ces conseils sont informatifs et ne remplacent pas un accompagnement professionnel.
        </p>
      </Card>
    </section>
  );
}
