import { useEffect, useMemo, useRef, useState, type ChangeEvent, type FormEvent } from "react";
import {
  BriefcaseBusiness,
  Check,
  ClipboardCheck,
  Compass,
  MapPin,
  MessagesSquare,
  Mic,
  Plus,
  Search,
  Send,
  Sparkles,
  Square,
  Target,
  Trash2,
} from "lucide-react";
import { Badge, Button, Card, Select } from "./components/ui";
import {
  ApiError,
  applyToJob,
  createCandidateAssistantSession,
  createEmployerOffer,
  deleteCandidateAssistantSession,
  fetchCandidateAssistantSession,
  fetchCandidateAssistantSessions,
  fetchCandidateMatches,
  fetchCandidateInterviewPreparationProfile,
  fetchCandidateInterviewRoles,
  startCandidateTechnicalAssessment,
  startCandidateBehavioralAssessment,
  fetchCandidateInterviewTranscription,
  submitCandidateBehavioralAssessmentAnswer,
  submitCandidateTechnicalAssessmentAnswer,
  uploadCandidateInterviewAudio,
  fetchCandidateApplications,
  fetchCandidateRoadmap,
  fetchCandidateProfile,
  fetchEmployerOffers,
  sendCandidateAssistantMessage,
  sendCandidateAssistantSessionMessage,
  renameCandidateAssistantSession,
  synthesizeCandidateSpeech,
  transcribeCandidateAudio,
  updateCandidateRoadmapStep,
  updateCandidateProfile,
  uploadCandidateCv,
  type CandidateAssistantMessage,
  type CandidateProfileDraft,
  type CandidateAssistantSession,
  type CandidateAssistantSessionSummary,
  type CandidateInterviewPreparationProfile,
  type CandidateInterviewRole,
  type CandidateTechnicalAssessment,
  type CandidateBehavioralAssessment,
  type Role,
  type TechnicalAssessmentQuestion,
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

export function summarizeInterviewProgress({
  technicalAssessment,
  behavioralAssessment,
}: {
  technicalAssessment: CandidateTechnicalAssessment | null;
  behavioralAssessment: CandidateBehavioralAssessment | null;
}) {
  const technicalQuestions = technicalAssessment?.questions.length ?? 0;
  const behavioralQuestions = behavioralAssessment?.questions.length ?? 0;
  const technicalAnswers = technicalAssessment?.answers ?? [];
  const behavioralAnswers = behavioralAssessment?.answers ?? [];
  const answeredQuestions = technicalAnswers.length + behavioralAnswers.length;
  const totalQuestions = technicalQuestions + behavioralQuestions;
  const globalProgress =
    totalQuestions > 0 ? Math.round((answeredQuestions / totalQuestions) * 100) : 0;

  const technicalAverage =
    technicalAnswers.length > 0
      ? Math.round(
          technicalAnswers.reduce(
            (sum, answer) => sum + (answer.evaluation.score / answer.evaluation.max_score) * 100,
            0,
          ) / technicalAnswers.length,
        )
      : 0;

  const behavioralAverage =
    behavioralAnswers.length > 0
      ? Math.round(
          behavioralAnswers.reduce(
            (sum, answer) => sum + (answer.evaluation.score / answer.evaluation.max_score) * 100,
            0,
          ) / behavioralAnswers.length,
        )
      : 0;

  const averageScore =
    answeredQuestions > 0
      ? Math.round(
          (technicalAverage * technicalAnswers.length +
            behavioralAverage * behavioralAnswers.length) /
            answeredQuestions,
        )
      : 0;
  const completedAssessments = [technicalAssessment, behavioralAssessment].filter(
    (assessment) => Boolean(assessment && assessment.answers.length > 0),
  ).length;

  const recommendations: string[] = [];
  if (globalProgress < 45) {
    recommendations.push(
      "Complétez votre première réponse technique ou comportementale pour construire un premier rapport.",
    );
  }
  if (technicalAverage < 70 && technicalAssessment) {
    recommendations.push(
      "Reprenez vos réponses techniques en ciblant la structure, l’exemple concret et la vérification du résultat.",
    );
  }
  if (behavioralAverage < 70 && behavioralAssessment) {
    recommendations.push(
      "Travaillez la clarté et le résultat dans vos réponses comportementales pour gagner en confiance.",
    );
  }
  if (recommendations.length === 0) {
    recommendations.push(
      "Votre préparation est stable. Réservez un dernier exercice pour consolider votre confiance.",
    );
  }

  return {
    totalQuestions,
    answeredQuestions,
    globalProgress,
    technicalAverage,
    behavioralAverage,
    averageScore,
    completedAssessments,
    recommendations,
  };
}

export function analyzeCommunicationSignals(value: string): {
  score: number;
  signals: { label: string; detail: string; tone: "good" | "watch" }[];
  exercises: { title: string; prompt: string }[];
} {
  const trimmed = value.trim();
  if (!trimmed) {
    return {
      score: 0,
      signals: [
        { label: "Structure", detail: "Ajoutez une réponse structurée en 3 étapes.", tone: "watch" },
        { label: "Exemple concret", detail: "Donnez un exemple précis pour illustrer votre point.", tone: "watch" },
        { label: "Résultat", detail: "Mettez en avant le résultat et la leçon apprise.", tone: "watch" },
      ],
      exercises: [
        { title: "Structure simple", prompt: "Rédigez votre réponse en 3 phrases : contexte, action, résultat." },
        { title: "Exemple concret", prompt: "Ajoutez un exemple précis tiré de votre travail, étude ou bénévolat." },
        { title: "Résultat clair", prompt: "Terminez par le résultat et ce que vous avez appris." },
      ],
    };
  }

  const words = trimmed.split(/\s+/).filter(Boolean);
  const sentenceCount = (trimmed.match(/[.!?]+/g) ?? []).length || 1;
  const hasStructure = /\b(?:d'abord|ensuite|puis|finalement|premièrement|en premier|donc|par exemple|en résumé)\b/i.test(trimmed);
  const hasConcreteExample = /\b(?:par exemple|lorsque|quand|dans mon travail|dans un projet|dans l'équipe|dans une situation|exemple)\b/i.test(trimmed);
  const hasResult = /\b(?:résultat|impact|effet|gain|amélioration|outil|solution|objectif)\b/i.test(trimmed);
  const hasFirstPerson = /\b(?:je|nous|j'ai|nous avons)\b/i.test(trimmed);
  const fillerMatches = trimmed.match(/\b(?:euh|hum|basiquement|genre|voilà|en gros|donc)\b/gi) ?? [];
  const wordCount = words.length;

  let score = 50;
  if (hasStructure) score += 15;
  if (hasConcreteExample) score += 15;
  if (hasResult) score += 10;
  if (hasFirstPerson) score += 8;
  if (wordCount >= 30 && wordCount <= 150) score += 10;
  if (sentenceCount >= 2) score += 5;
  if (fillerMatches.length > 4) score -= 20;
  if (wordCount < 18) score -= 10;
  if (wordCount > 220) score -= 10;
  score = Math.max(0, Math.min(100, score));

  const signals: { label: string; detail: string; tone: "good" | "watch" }[] = [
    {
      label: "Structure",
      detail: hasStructure
        ? "Votre réponse suit une logique claire et est facile à suivre."
        : "Ajoutez une progression simple : contexte, action, résultat.",
      tone: hasStructure ? "good" : "watch",
    },
    {
      label: "Exemple concret",
      detail: hasConcreteExample
        ? "Vous donnez un exemple crédible et précis."
        : "Illustrez votre réponse avec un exemple concret et identifiable.",
      tone: hasConcreteExample ? "good" : "watch",
    },
    {
      label: "Résultat",
      detail: hasResult
        ? "Votre réponse met en avant le résultat et l’effet."
        : "Concluez en décrivant le résultat, l’impact ou la leçon.",
      tone: hasResult ? "good" : "watch",
    },
  ];

  const exercises = [
    {
      title: "Structure simple",
      prompt: hasStructure
        ? "Répétez votre réponse en 3 phrases nettes : situation, action, résultat."
        : "Rédigez votre réponse en 3 phrases : contexte, action, résultat.",
    },
    {
      title: "Exemple concret",
      prompt: hasConcreteExample
        ? "Ajoutez un détail précis qui permet à l’interlocuteur de visualiser la situation."
        : "Ajoutez un exemple réaliste tiré d’un projet, d’un cours ou d’une expérience de groupe.",
    },
    {
      title: "Résultat clair",
      prompt: hasResult
        ? "Terminez par le résultat et ce que vous avez appris."
        : "Terminez par le résultat, le bénéfice et la leçon que vous en tirez.",
    },
  ];

  return { score, signals, exercises };
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
  const [isUploadingCv, setIsUploadingCv] = useState(false);
  const [cvDraft, setCvDraft] = useState<CandidateProfileForm | null>(null);
  const [cvFilename, setCvFilename] = useState("");
  const [cvError, setCvError] = useState("");
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
  const cvDialogRef = useRef<HTMLDialogElement | null>(null);
  const cvFileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    const dialog = cvDialogRef.current;
    if (!cvDraft || !dialog || dialog.open) return;
    if (typeof dialog.showModal === "function") dialog.showModal();
    else dialog.setAttribute("open", "");
  }, [cvDraft]);

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

  async function handleCvUpload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setIsUploadingCv(true);
    setError("");
    setNotice("");
    setCvError("");
    try {
      const extracted = await uploadCandidateCv(token, file);
      setCvDraft({
        full_name: extracted.full_name ?? "",
        phone: extracted.phone ?? "",
        location: extracted.location ?? "",
        education: extracted.education ?? "",
        experience: extracted.experience ?? "",
        skills: extracted.skills.join(", "),
      });
      setCvFilename(file.name);
    } catch (cause: unknown) {
      setError(errorMessage(cause));
    } finally {
      setIsUploadingCv(false);
      event.target.value = "";
    }
  }

  function updateCvDraft(field: keyof CandidateProfileForm, value: string) {
    setCvDraft((current) => current ? { ...current, [field]: value } : current);
  }

  async function saveCvDraft() {
    if (!cvDraft || isSaving) return;
    setIsSaving(true);
    setCvError("");
    setError("");
    setNotice("");
    try {
      const saved = await updateCandidateProfile(token, {
        full_name: cvDraft.full_name,
        phone: cvDraft.phone,
        location: cvDraft.location,
        education: cvDraft.education,
        experience: cvDraft.experience,
        skills: splitSkills(cvDraft.skills),
      });
      setProfile({
        full_name: saved.full_name ?? "",
        phone: saved.phone ?? "",
        location: saved.location ?? "",
        education: saved.education ?? "",
        experience: saved.experience ?? "",
        skills: saved.skills.join(", "),
      });
      setCvDraft(null);
      setNotice("Votre profil extrait du CV a été enregistré.");
    } catch (cause: unknown) {
      setCvError(errorMessage(cause));
    } finally {
      setIsSaving(false);
    }
  }

  function discardCvDraft() {
    setCvDraft(null);
    setCvError("");
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
      <h1>Mon profil professionnel</h1>
      <p className="workspace-page__intro">
        Vérifiez vos informations et complétez les détails de votre parcours à votre rythme.
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
                  <h2>Votre assistant profil</h2>
                  <p>Parlez en Derja tunisien, en arabe ou en français de vos compétences, études et expériences. Vous vérifierez chaque suggestion avant de l’enregistrer.</p>
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
            <div className="workspace-form profile-editor">
              <div className="profile-upload">
                <div>
                  <h2>Mon profil</h2>
                  <p>Importez un CV pour extraire les informations à vérifier.</p>
                </div>
                <div>
                  <input
                    id="candidate-cv-upload"
                    ref={cvFileInputRef}
                    type="file"
                    accept=".pdf,.docx,.txt,.md"
                    className="cv-file-input"
                    aria-label="Sélectionner un CV"
                    tabIndex={-1}
                    onChange={(event) => void handleCvUpload(event)}
                  />
                  <Button type="button" variant="secondary" disabled={isUploadingCv} onClick={() => cvFileInputRef.current?.click()}>
                    {isUploadingCv ? "Analyse du CV…" : "Importer un CV"}
                  </Button>
                </div>
              </div>
              <form onSubmit={(event) => void saveProfile(event)}>
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
            </div>
          </>
        )}
      </Card>
      {cvDraft && (
        <dialog
          ref={cvDialogRef}
          className="cv-review-dialog"
          aria-labelledby="cv-review-title"
          onCancel={(event) => {
            event.preventDefault();
            discardCvDraft();
          }}
          onClick={(event) => {
            if (event.target === event.currentTarget) discardCvDraft();
          }}
        >
          <div className="cv-review-dialog__content">
            <header className="cv-review-dialog__header">
              <div>
                <div className="eyebrow">VÉRIFICATION DU CV</div>
                <h2 id="cv-review-title">Vérifiez les informations extraites</h2>
                <p>
                  {cvFilename} — corrigez les champs si nécessaire. Rien ne sera enregistré avant votre confirmation.
                </p>
              </div>
              <Button type="button" variant="ghost" aria-label="Fermer la vérification du CV" onClick={discardCvDraft}>
                ×
              </Button>
            </header>
            <div className="cv-review-dialog__fields">
              <ProfileTextField
                label="Nom complet"
                value={cvDraft.full_name}
                maxLength={200}
                onChange={(value) => updateCvDraft("full_name", value)}
              />
              <ProfileTextField
                label="Téléphone"
                value={cvDraft.phone}
                maxLength={40}
                onChange={(value) => updateCvDraft("phone", value)}
              />
              <ProfileTextField
                label="Lieu de résidence"
                value={cvDraft.location}
                maxLength={120}
                onChange={(value) => updateCvDraft("location", value)}
              />
              <ProfileTextField
                label="Études et formations"
                value={cvDraft.education}
                maxLength={5000}
                multiline
                onChange={(value) => updateCvDraft("education", value)}
              />
              <ProfileTextField
                label="Expérience professionnelle"
                value={cvDraft.experience}
                maxLength={5000}
                multiline
                onChange={(value) => updateCvDraft("experience", value)}
              />
              <ProfileTextField
                label="Compétences"
                value={cvDraft.skills}
                maxLength={2200}
                multiline
                hint="Séparez les compétences par des virgules."
                onChange={(value) => updateCvDraft("skills", value)}
              />
            </div>
            {cvError && <p className="workspace-error" role="alert">{cvError}</p>}
            <footer className="cv-review-dialog__actions">
              <Button type="button" variant="secondary" disabled={isSaving} onClick={discardCvDraft}>
                Ignorer les informations
              </Button>
              <Button type="button" disabled={isSaving} onClick={() => void saveCvDraft()}>
                {isSaving ? "Enregistrement…" : "Enregistrer le profil"}
              </Button>
            </footer>
          </div>
        </dialog>
      )}
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
  role,
}: {
  token: string;
  onNavigate: (page: string) => void;
  role: Role;
}) {
  const [sessions, setSessions] = useState<CandidateAssistantSessionSummary[]>([]);
  const [activeSession, setActiveSession] = useState<CandidateAssistantSession | null>(null);
  const [chatText, setChatText] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [isOpening, setIsOpening] = useState(false);
  const [error, setError] = useState("");
  const [sessionSearch, setSessionSearch] = useState("");

  useEffect(() => {
    let cancelled = false;
    async function loadSessions() {
      try {
        const history = await fetchCandidateAssistantSessions(token);
        if (cancelled) return;
        setSessions(history);
        const preferredId = sessionStorage.getItem("mahara-assistant-session");
        const preferred = history.find((item) => item.id === preferredId) ?? history[0];
        if (preferred) {
          const firstSession = await fetchCandidateAssistantSession(token, preferred.id);
          if (!cancelled) {
            setActiveSession(firstSession);
            sessionStorage.setItem("mahara-assistant-session", firstSession.id);
          }
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
      sessionStorage.setItem("mahara-assistant-session", created.id);
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
      const opened = await fetchCandidateAssistantSession(token, sessionId);
      setActiveSession(opened);
      sessionStorage.setItem("mahara-assistant-session", opened.id);
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
      sessionStorage.setItem("mahara-assistant-session", updated.id);
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
  const assistantTitle = role === "employer" ? "Votre assistant recrutement" : role === "candidate" ? "Votre assistant carrière" : "Votre assistant Mahara Match";

  return (
    <section className="workspace-page">
      <div className="eyebrow">ASSISTANT CARRIÈRE</div>
      <h1>{assistantTitle}</h1>
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
          <label className="assistant-search"><Search size={16} aria-hidden="true"/><input className="input" aria-label="Rechercher une conversation" placeholder="Rechercher" value={sessionSearch} onChange={(event) => setSessionSearch(event.target.value)}/></label>
          {isLoading ? (
            <p aria-live="polite">Chargement de vos conversations…</p>
          ) : sessions.length ? (
            <ul className="career-assistant-history__list">
              {sessions.filter((item) => item.title.toLocaleLowerCase().includes(sessionSearch.toLocaleLowerCase())).map((item) => (
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
                    className="icon-button"
                    type="button"
                    aria-label={`Renommer ${item.title}`}
                    disabled={isOpening || isSending}
                    onClick={async () => {
                      const title = window.prompt("Nouveau titre de conversation", item.title)?.trim();
                      if (!title) return;
                      try {
                        const updated = await renameCandidateAssistantSession(token, item.id, title);
                        setSessions((current) => current.map((entry) => entry.id === item.id ? { ...entry, title: updated.title, updated_at: updated.updated_at } : entry));
                        if (activeSession?.id === item.id) setActiveSession(updated);
                      } catch (cause) { setError(errorMessage(cause)); }
                    }}
                  >
                    <span aria-hidden="true">✎</span>
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
              {(role === "employer"
                ? ["Comment rédiger une offre claire ?", "Quelles compétences indiquer ?"]
                : role === "candidate"
                  ? ["Comment obtenir de meilleures correspondances ?", "Quelles compétences développer pour trouver un emploi ?"]
                  : ["Comment utiliser mon espace ?", "Aidez-moi à comprendre les indicateurs disponibles."]
              ).map((prompt) => <Button key={prompt} type="button" variant="secondary" disabled={isSending || isOpening || isLoading} onClick={() => void sendMessage(prompt)}>{prompt}</Button>)}
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
          {role === "candidate" && <Button
            type="button"
            className="career-assistant-manual"
            variant="secondary"
            onClick={() => onNavigate("Mon profil")}
          >
            Compléter mon profil manuellement
          </Button>}
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

export function CandidateInterviewPreparationPage({
  token,
  onNavigate,
}: {
  token: string;
  onNavigate: (page: string) => void;
}) {
  const [roles, setRoles] = useState<CandidateInterviewRole[]>([]);
  const [selectedOfferId, setSelectedOfferId] = useState("");
  const [preparation, setPreparation] =
    useState<CandidateInterviewPreparationProfile | null>(null);
  const [isLoadingRoles, setIsLoadingRoles] = useState(true);
  const [isLoadingProfile, setIsLoadingProfile] = useState(false);
  const [assessment, setAssessment] = useState<CandidateTechnicalAssessment | null>(null);
  const [behavioralAssessment, setBehavioralAssessment] =
    useState<CandidateBehavioralAssessment | null>(null);
  const mockInterviewPlan = useMemo(() => {
    if (!preparation) return null;

    const focusSkill =
      preparation.required_competencies.find(
        (competency) => competency.candidate_evidence !== "self_reported",
      ) ??
      preparation.required_competencies[0] ??
      preparation.suggested_competencies[0] ??
      null;

    const coachingFocus =
      preparation.suggested_competencies.find(
        (competency) => competency.candidate_evidence === "not_assessed",
      ) ??
      preparation.suggested_competencies[0] ??
      null;

    const technicalQuestion =
      focusSkill && focusSkill.category === "hard"
        ? `Présentez votre approche sur ${focusSkill.name} en 2 minutes : contexte, action, résultat.`
        : "Expliquez une compétence clé de l’offre et montrez comment vous l’avez mise en pratique.";

    const behavioralQuestion =
      coachingFocus && coachingFocus.category === "communication"
        ? `Décrivez une situation où vous avez dû expliquer une idée complexe à un collègue ou un manager.`
        : coachingFocus
          ? `Parlez d’une situation où ${coachingFocus.name.toLowerCase()} a été crucial pour votre travail.`
          : "Racontez une situation qui montre votre capacité à travailler avec des personnes et des contraintes variées.";

    const readiness = summarizeInterviewProgress({
      technicalAssessment: assessment,
      behavioralAssessment,
    });

    const priorityLabel = readiness.averageScore >= 70 ? "Très bonne préparation" : "Priorité de travail";
    const summary = focusSkill
      ? `Le prochain exercice met l’accent sur ${focusSkill.name}, une compétence demandée par l’offre et encore à renforcer.`
      : "Vous pouvez renforcer votre confiance avec un exercice ciblé sur votre préparation globale.";

    if (focusSkill && focusSkill.category === "hard") {
      return {
        title: "Simulation d’entretien adaptative",
        priorityLabel,
        summary,
        question: technicalQuestion,
        guidance: [
          "Parlez de votre contexte en 30 secondes.",
          "Montrez l’action concrète que vous avez menée.",
          "Terminez avec le résultat et la leçon apprise.",
        ],
        buttonLabel: `Lancer une simulation ${focusSkill.name}`,
        onStart: () => void beginAssessment(focusSkill.name),
      };
    }

    return {
      title: "Simulation d’entretien adaptative",
      priorityLabel,
      summary,
      question: behavioralQuestion,
      guidance: [
        "Donnez un exemple précis tiré d’un projet ou d’une situation réelle.",
        "Expliquez la difficulté, votre rôle et la décision prise.",
        "Concluez sur le résultat et ce que vous avez appris.",
      ],
      buttonLabel: coachingFocus ? `Lancer une simulation ${coachingFocus.name}` : "Lancer une simulation",
      onStart: coachingFocus
        ? () => void beginBehavioralAssessment(coachingFocus.id)
        : undefined,
    };
  }, [assessment, behavioralAssessment, preparation]);
  const [startingCompetency, setStartingCompetency] = useState("");
  const [startingSkill, setStartingSkill] = useState("");
  const [isSubmittingAnswer, setIsSubmittingAnswer] = useState(false);
  const [isSubmittingBehavioralAnswer, setIsSubmittingBehavioralAnswer] = useState(false);
  const [draftAnswer, setDraftAnswer] = useState("");
  const [behavioralDraftAnswer, setBehavioralDraftAnswer] = useState("");
  const [selectedOptionId, setSelectedOptionId] = useState("");
  const [voiceTranscript, setVoiceTranscript] = useState("");
  const [isRecordingAnswer, setIsRecordingAnswer] = useState(false);
  const [isTranscribingAnswer, setIsTranscribingAnswer] = useState(false);
  const [voiceError, setVoiceError] = useState("");
  const [error, setError] = useState("");
  const communicationText =
    voiceTranscript || draftAnswer || behavioralDraftAnswer || "";
  const communicationSignals = communicationText.trim()
    ? analyzeCommunicationSignals(communicationText)
    : null;
  const progressReport = summarizeInterviewProgress({
    technicalAssessment: assessment,
    behavioralAssessment,
  });
  const interviewRecorderRef = useRef<MediaRecorder | null>(null);
  const interviewAudioStreamRef = useRef<MediaStream | null>(null);
  const interviewAudioChunksRef = useRef<Blob[]>([]);
  const interviewAudioTargetRef = useRef<{
    assessmentType: "technical" | "behavioral";
    assessmentId: string;
    questionId: string;
    format: TechnicalAssessmentQuestion["format"] | "star_text";
  } | null>(null);
  const discardInterviewRecordingRef = useRef(false);
  const transcriptionPollingRef = useRef(true);

  useEffect(() => {
    let cancelled = false;
    fetchCandidateInterviewRoles(token)
      .then((result) => {
        if (!cancelled) {
          setRoles(result);
          setSelectedOfferId(result[0]?.id ?? "");
        }
      })
      .catch((cause: unknown) => {
        if (!cancelled) setError(errorMessage(cause));
      })
      .finally(() => {
        if (!cancelled) setIsLoadingRoles(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  useEffect(() => {
    if (!selectedOfferId) {
      setPreparation(null);
      return;
    }

    let cancelled = false;
    setPreparation(null);
    setAssessment(null);
    setBehavioralAssessment(null);
    setIsLoadingProfile(true);
    setError("");
    fetchCandidateInterviewPreparationProfile(token, selectedOfferId)
      .then((result) => {
        if (!cancelled) setPreparation(result);
      })
      .catch((cause: unknown) => {
        if (!cancelled) setError(errorMessage(cause));
      })
      .finally(() => {
        if (!cancelled) setIsLoadingProfile(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedOfferId, token]);

  useEffect(
    () => () => {
      transcriptionPollingRef.current = false;
      discardInterviewRecordingRef.current = true;
      if (interviewRecorderRef.current?.state === "recording") {
        interviewRecorderRef.current.stop();
      }
      interviewAudioStreamRef.current?.getTracks().forEach((track) => track.stop());
    },
    [],
  );

  async function transcribeInterviewRecording(audio: Blob) {
    const target = interviewAudioTargetRef.current;
    if (!target || !audio.size) {
      setVoiceError("Aucune voix n’a été enregistrée. Réessayez ou saisissez votre réponse.");
      return;
    }
    if (audio.size > 20 * 1024 * 1024) {
      setVoiceError("L’enregistrement dépasse la limite de 20 Mo. Réessayez ou saisissez votre réponse.");
      return;
    }

    setIsTranscribingAnswer(true);
    setVoiceError("");
    setVoiceTranscript("");
    try {
      const queued = await uploadCandidateInterviewAudio(
        token,
        target.assessmentType,
        target.assessmentId,
        target.questionId,
        audio,
      );
      let transcription = queued;
      for (let attempt = 0; attempt < 120; attempt += 1) {
        if (!transcriptionPollingRef.current) return;
        if (transcription.status === "completed" && transcription.transcript) {
          setVoiceTranscript(transcription.transcript);
          if (target.assessmentType === "behavioral") {
            setBehavioralDraftAnswer(transcription.transcript);
          } else if (target.format !== "multiple_choice") {
            setDraftAnswer(transcription.transcript);
          }
          setVoiceError("");
          return;
        }
        if (transcription.status === "failed") {
          throw new ApiError(
            transcription.error_message ??
              "La transcription a échoué. Réessayez ou saisissez votre réponse.",
            502,
          );
        }
        await new Promise((resolve) => window.setTimeout(resolve, 1000));
        if (!transcriptionPollingRef.current) return;
        transcription = await fetchCandidateInterviewTranscription(token, transcription.id);
      }
      throw new ApiError(
        "La transcription prend trop de temps. Réessayez ou saisissez votre réponse.",
        504,
      );
    } catch (cause: unknown) {
      if (transcriptionPollingRef.current) setVoiceError(errorMessage(cause));
    } finally {
      if (transcriptionPollingRef.current) setIsTranscribingAnswer(false);
    }
  }

  async function startInterviewRecording(
    assessmentType: "technical" | "behavioral",
    assessmentId: string,
    questionId: string,
    format: TechnicalAssessmentQuestion["format"] | "star_text",
  ) {
    setVoiceError("");
    setVoiceTranscript("");
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      setVoiceError(
        "L’enregistrement audio n’est pas pris en charge par ce navigateur. Vous pouvez saisir votre réponse.",
      );
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      transcriptionPollingRef.current = true;
      discardInterviewRecordingRef.current = false;
      interviewAudioTargetRef.current = {
        assessmentType,
        assessmentId,
        questionId,
        format,
      };
      interviewAudioStreamRef.current = stream;
      interviewRecorderRef.current = recorder;
      interviewAudioChunksRef.current = [];
      recorder.addEventListener("dataavailable", (event) => {
        if (event.data.size) interviewAudioChunksRef.current.push(event.data);
      });
      recorder.addEventListener(
        "stop",
        () => {
          stream.getTracks().forEach((track) => track.stop());
          interviewAudioStreamRef.current = null;
          setIsRecordingAnswer(false);
          if (discardInterviewRecordingRef.current) return;
          const recording = new Blob(interviewAudioChunksRef.current, {
            type: recorder.mimeType || "audio/webm",
          });
          void transcribeInterviewRecording(recording);
        },
        { once: true },
      );
      recorder.start();
      setIsRecordingAnswer(true);
    } catch (cause: unknown) {
      setVoiceError(
        cause instanceof DOMException && cause.name === "NotAllowedError"
          ? "L’accès au microphone a été refusé. Autorisez-le ou saisissez votre réponse."
          : "Impossible d’accéder au microphone. Vérifiez son autorisation ou saisissez votre réponse.",
      );
    }
  }

  function stopInterviewRecording() {
    if (interviewRecorderRef.current?.state === "recording") {
      interviewRecorderRef.current.stop();
    }
  }

  function isRecordingOtherAnswer(
    assessmentType: "technical" | "behavioral",
    assessmentId: string,
    questionId: string,
  ): boolean {
    const target = interviewAudioTargetRef.current;
    return Boolean(
      isRecordingAnswer &&
        target &&
        (target.assessmentType !== assessmentType ||
          target.assessmentId !== assessmentId ||
          target.questionId !== questionId),
    );
  }

  async function beginAssessment(skill: string) {
    if (!preparation) return;
    setStartingSkill(skill);
    setError("");
    setAssessment(null);
    setBehavioralAssessment(null);
    setDraftAnswer("");
    setSelectedOptionId("");
    try {
      setAssessment(
        await startCandidateTechnicalAssessment(token, preparation.role.id, skill),
      );
    } catch (cause: unknown) {
      setError(errorMessage(cause));
    } finally {
      setStartingSkill("");
    }
  }

  async function submitAnswer() {
    if (!assessment) return;
    const answeredQuestionIds = new Set(assessment.answers.map((answer) => answer.question_id));
    const question = assessment.questions.find((item) => !answeredQuestionIds.has(item.id));
    if (!question) return;
    const answerPayload =
      question.format === "multiple_choice"
        ? { question_id: question.id, selected_option_id: selectedOptionId }
        : { question_id: question.id, answer: draftAnswer };
    setIsSubmittingAnswer(true);
    setError("");
    try {
      setAssessment(
        await submitCandidateTechnicalAssessmentAnswer(token, assessment.id, answerPayload),
      );
      setDraftAnswer("");
      setSelectedOptionId("");
    } catch (cause: unknown) {
      setError(errorMessage(cause));
    } finally {
      setIsSubmittingAnswer(false);
    }
  }

  async function beginBehavioralAssessment(competencyId: string) {
    if (!preparation) return;
    setStartingCompetency(competencyId);
    setError("");
    setBehavioralAssessment(null);
    setAssessment(null);
    setBehavioralDraftAnswer("");
    try {
      setBehavioralAssessment(
        await startCandidateBehavioralAssessment(
          token,
          preparation.role.id,
          competencyId,
        ),
      );
    } catch (cause: unknown) {
      setError(errorMessage(cause));
    } finally {
      setStartingCompetency("");
    }
  }

  async function submitBehavioralAnswer() {
    if (!behavioralAssessment) return;
    const answeredQuestionIds = new Set(
      behavioralAssessment.answers.map((answer) => answer.question_id),
    );
    const question = behavioralAssessment.questions.find(
      (item) => !answeredQuestionIds.has(item.id),
    );
    if (!question) return;
    setIsSubmittingBehavioralAnswer(true);
    setError("");
    try {
      setBehavioralAssessment(
        await submitCandidateBehavioralAssessmentAnswer(
          token,
          behavioralAssessment.id,
          question.id,
          behavioralDraftAnswer,
        ),
      );
      setBehavioralDraftAnswer("");
    } catch (cause: unknown) {
      setError(errorMessage(cause));
    } finally {
      setIsSubmittingBehavioralAnswer(false);
    }
  }

  return (
    <section className="workspace-page interview-prep-page">
      <div className="eyebrow">PRÉPARATION À L’ENTRETIEN</div>
      <h1>Préparer un entretien</h1>
      <p className="workspace-page__intro">
        Choisissez une offre pour revoir ses compétences techniques demandées et vous entraîner
        aux compétences comportementales utiles en entretien.
      </p>
      {roles.length > 0 && (
        <Select
          label="Offre ciblée"
          value={selectedOfferId}
          options={roles.map((role) => ({
            value: role.id,
            label: `${role.title} — ${role.location}`,
          }))}
          onChange={(event) => setSelectedOfferId(event.target.value)}
        />
      )}
      {isLoadingRoles && <p aria-live="polite">Chargement des offres…</p>}
      {isLoadingProfile && <p aria-live="polite">Préparation de votre profil…</p>}
      {error && <p className="workspace-error" role="alert">{error}</p>}
      {!isLoadingRoles && roles.length === 0 && !error && (
        <Card className="workspace-empty">
          <ClipboardCheck size={25} aria-hidden="true" />
          <h2>Aucune offre disponible pour le moment</h2>
          <p>Les exigences réelles d’une offre apparaîtront ici dès qu’une offre sera publiée.</p>
          <Button onClick={() => onNavigate("Mes opportunités")}>Voir les opportunités</Button>
        </Card>
      )}
      {preparation && (
        <>
          <Card className="interview-prep-summary">
            <div className="interview-prep-summary__heading">
              <div>
                <span className="eyebrow">OFFRE DE L’EMPLOYEUR</span>
                <h2>{preparation.role.title}</h2>
              </div>
              <Badge tone="accent">{preparation.role.location}</Badge>
            </div>
            <p>{preparation.role.description}</p>
            <p className="form-field__hint">
              Les compétences techniques ci-dessous proviennent des exigences publiées. Aucun
              niveau ou poids qui n’est pas indiqué dans l’offre n’est supposé.
            </p>
          </Card>

          {mockInterviewPlan && (
            <section className="interview-prep-section" aria-labelledby="mock-interview-plan">
              <div>
                <h2 id="mock-interview-plan">{mockInterviewPlan.title}</h2>
                <p>Une piste de pratique adaptée à votre préparation actuelle et aux compétences ciblées.</p>
              </div>
              <div className="interview-prep-grid">
                <Card className="interview-prep-card">
                  <div className="interview-prep-card__heading">
                    <h3>Priorité suivante</h3>
                    <Badge tone="accent">{mockInterviewPlan.priorityLabel}</Badge>
                  </div>
                  <p>{mockInterviewPlan.summary}</p>
                  {mockInterviewPlan.onStart && (
                    <Button onClick={() => void mockInterviewPlan.onStart?.()}>
                      {mockInterviewPlan.buttonLabel}
                    </Button>
                  )}
                </Card>
                <Card className="interview-prep-card">
                  <div className="interview-prep-card__heading">
                    <h3>Question de simulation</h3>
                  </div>
                  <p>{mockInterviewPlan.question}</p>
                  <ul>
                    {mockInterviewPlan.guidance.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </Card>
              </div>
            </section>
          )}

          <section className="interview-prep-section" aria-labelledby="interview-progress-report">
            <div>
              <h2 id="interview-progress-report">Rapport de progression</h2>
              <p>Suivez votre avancement et identifiez les prochaines priorités de préparation.</p>
            </div>
            <div className="interview-prep-grid">
              <Card className="interview-prep-card">
                <div className="interview-prep-card__heading">
                  <h3>Questions répondues</h3>
                  <Badge tone="accent">{progressReport.answeredQuestions}/{progressReport.totalQuestions}</Badge>
                </div>
                <p>Nombre total de réponses enregistrées sur les exercices et questions de l’offre.</p>
              </Card>
              <Card className="interview-prep-card">
                <div className="interview-prep-card__heading">
                  <h3>Score moyen</h3>
                  <Badge tone="success">{progressReport.averageScore}/100</Badge>
                </div>
                <p>Score moyen calculé à partir des évaluations déjà reçues.</p>
              </Card>
              <Card className="interview-prep-card">
                <div className="interview-prep-card__heading">
                  <h3>Évaluations complètes</h3>
                  <Badge tone="accent">{progressReport.completedAssessments}</Badge>
                </div>
                <p>Nombre d’évaluations avec au moins une réponse validée.</p>
              </Card>
            </div>
            <Card className="interview-prep-card">
              <div className="interview-prep-card__heading">
                <h3>Progression globale</h3>
                <Badge tone="accent">{progressReport.globalProgress}%</Badge>
              </div>
              <div className="progress" role="progressbar" aria-label="Progression du rapport d’entraînement" aria-valuemin={0} aria-valuemax={100} aria-valuenow={progressReport.globalProgress}>
                <span className="progress__fill" style={{ width: `${progressReport.globalProgress}%` }} />
              </div>
              <ul>
                {progressReport.recommendations.map((recommendation) => (
                  <li key={recommendation}>{recommendation}</li>
                ))}
              </ul>
            </Card>
          </section>

          {communicationSignals && (
            <section className="interview-prep-section" aria-labelledby="interview-communication-signals">
              <div>
                <h2 id="interview-communication-signals">Signaux de communication</h2>
                <p>
                  Analyse de votre réponse actuelle. Ce repérage est un outil de coaching, pas un
                  score de sélection.
                </p>
              </div>
              <div className="interview-prep-grid">
                {communicationSignals.signals.map((signal) => (
                  <Card className="interview-prep-card" key={signal.label}>
                    <div className="interview-prep-card__heading">
                      <h3>{signal.label}</h3>
                      <Badge tone={signal.tone === "good" ? "success" : "accent"}>
                        {signal.tone === "good" ? "Bon" : "À améliorer"}
                      </Badge>
                    </div>
                    <p>{signal.detail}</p>
                  </Card>
                ))}
              </div>
              <Card className="interview-prep-card">
                <div className="interview-prep-card__heading">
                  <h3>Exercices de pratique</h3>
                  <Badge tone="accent">{communicationSignals.score}/100</Badge>
                </div>
                <ol>
                  {communicationSignals.exercises.map((exercise) => (
                    <li key={exercise.title}>
                      <strong>{exercise.title}</strong> : {exercise.prompt}
                    </li>
                  ))}
                </ol>
              </Card>
            </section>
          )}

          <section className="interview-prep-section" aria-labelledby="interview-hard-skills">
            <div>
              <h2 id="interview-hard-skills">Compétences techniques de l’offre</h2>
              <p>Préparez un exemple concret et votre façon de vérifier le résultat.</p>
            </div>
            {preparation.required_competencies.length > 0 ? (
              <div className="interview-prep-grid">
                {preparation.required_competencies.map((competency) => (
                  <Card className="interview-prep-card" key={competency.id}>
                    <div className="interview-prep-card__heading">
                      <h3>{competency.name}</h3>
                      <Badge tone={competency.candidate_evidence === "self_reported" ? "success" : "warning"}>
                        {competency.candidate_evidence === "self_reported"
                          ? "Déclarée dans votre profil"
                          : "À préparer"}
                      </Badge>
                    </div>
                    <p>{competency.description}</p>
                    <ul>
                      {competency.assessment_criteria.map((criterion) => (
                        <li key={criterion}>{criterion}</li>
                      ))}
                    </ul>
                    <span className="form-field__hint">
                      Indication du profil, non vérifiée par une évaluation.
                    </span>
                    <Button
                      variant="secondary"
                      disabled={startingSkill !== "" || isSubmittingAnswer}
                      onClick={() => void beginAssessment(competency.name)}
                    >
                      {startingSkill === competency.name
                        ? "Préparation…"
                        : `Évaluer ${competency.name}`}
                    </Button>
                  </Card>
                ))}
              </div>
            ) : (
              <Card className="workspace-empty">
                <p>Cette offre ne précise pas de compétence technique requise.</p>
              </Card>
            )}
          </section>

          {assessment && (
            <Card className="interview-assessment">
              <div className="interview-assessment__heading">
                <div>
                  <span className="eyebrow">ÉVALUATION TECHNIQUE</span>
                  <h2>{assessment.skill} — {assessment.offer_title}</h2>
                </div>
                <Badge tone={assessment.status === "completed" ? "success" : "accent"}>
                  {assessment.status === "completed" ? "Terminée" : "En cours"}
                </Badge>
              </div>
              <p className="form-field__hint">
                Questions de connaissance, exercices textuels et mises en situation. Le code
                éventuellement saisi est évalué comme du texte et n’est jamais exécuté.
              </p>
              {assessment.answers.map((answer) => {
                const question = assessment.questions.find(
                  (item) => item.id === answer.question_id,
                );
                return (
                  <div className="interview-assessment-result" key={answer.question_id}>
                    <div className="interview-assessment-result__heading">
                      <strong>{question?.type === "knowledge" ? "Connaissance" : question?.type === "practical" ? "Exercice pratique" : "Mise en situation"}</strong>
                      <Badge tone={answer.evaluation.score > 0 ? "success" : "warning"}>
                        {answer.evaluation.score}/{answer.evaluation.max_score}
                      </Badge>
                    </div>
                    <p>{answer.evaluation.explanation}</p>
                    {answer.evaluation.strengths.length > 0 && (
                      <p><strong>Points forts :</strong> {answer.evaluation.strengths.join(" ")}</p>
                    )}
                    {answer.evaluation.weaknesses.length > 0 && (
                      <p><strong>À approfondir :</strong> {answer.evaluation.weaknesses.join(" ")}</p>
                    )}
                    {answer.evaluation.suggested_improvements.length > 0 && (
                      <p><strong>Pour progresser :</strong> {answer.evaluation.suggested_improvements.join(" ")}</p>
                    )}
                    <ul>
                      {answer.evaluation.criteria_scores.map((criterion) => (
                        <li key={criterion.criterion_id}>
                          {criterion.label} : {criterion.score}/{criterion.max_score}
                        </li>
                      ))}
                    </ul>
                  </div>
                );
              })}
              {assessment.status === "completed" ? (
                <p role="status">Toutes les questions de cette évaluation ont été traitées.</p>
              ) : (
                (() => {
                  const answeredIds = new Set(assessment.answers.map((answer) => answer.question_id));
                  const question = assessment.questions.find((item) => !answeredIds.has(item.id));
                  if (!question) return null;
                  return (
                    <div className="interview-assessment-question">
                      <span className="eyebrow">
                        QUESTION {assessment.answers.length + 1} SUR {assessment.questions.length}
                      </span>
                      <h3>{question.prompt}</h3>
                      {question.format === "multiple_choice" ? (
                        <fieldset className="interview-assessment-options">
                          <legend>Choisissez une réponse</legend>
                          {question.options.map((option) => (
                            <label key={option.id}>
                              <input
                                type="radio"
                                name={`assessment-${assessment.id}-${question.id}`}
                                value={option.id}
                                checked={selectedOptionId === option.id}
                                onChange={() => setSelectedOptionId(option.id)}
                              />
                              <span>{option.label}</span>
                            </label>
                          ))}
                        </fieldset>
                      ) : (
                        <label className="interview-assessment-text">
                          <span>Votre réponse</span>
                          <textarea
                            className="input"
                            value={draftAnswer}
                            maxLength={10000}
                            rows={5}
                            onChange={(event) => setDraftAnswer(event.target.value)}
                          />
                        </label>
                      )}
                      <div className="interview-voice-controls">
                        <Button
                          type="button"
                          variant={isRecordingAnswer ? "secondary" : "ghost"}
                          disabled={
                            isTranscribingAnswer ||
                            isRecordingOtherAnswer("technical", assessment.id, question.id)
                          }
                          onClick={() =>
                            isRecordingAnswer
                              ? stopInterviewRecording()
                              : void startInterviewRecording(
                                  "technical",
                                  assessment.id,
                                  question.id,
                                  question.format,
                                )
                          }
                        >
                          {isRecordingAnswer ? (
                            <><Square size={16} aria-hidden="true" /> Arrêter l’enregistrement</>
                          ) : (
                            <><Mic size={16} aria-hidden="true" /> Enregistrer une réponse vocale</>
                          )}
                        </Button>
                        {isTranscribingAnswer && (
                          <span role="status">Transcription en cours…</span>
                        )}
                      </div>
                      {voiceTranscript && (
                        <p className="interview-voice-transcript" role="status">
                          <strong>Transcription à vérifier :</strong> {voiceTranscript}
                          {question.format === "multiple_choice" &&
                            " Choisissez ensuite l’option correspondante."}
                        </p>
                      )}
                      {voiceError && <p className="workspace-error" role="alert">{voiceError}</p>}
                      <Button
                        disabled={
                          isSubmittingAnswer ||
                          isRecordingAnswer ||
                          isTranscribingAnswer ||
                          (question.format === "multiple_choice"
                            ? !selectedOptionId
                            : !draftAnswer.trim())
                        }
                        onClick={() => void submitAnswer()}
                      >
                        {isSubmittingAnswer ? "Évaluation…" : "Envoyer ma réponse"}
                      </Button>
                    </div>
                  );
                })()
              )}
            </Card>
          )}

          <section className="interview-prep-section" aria-labelledby="interview-soft-skills">
            <div>
              <h2 id="interview-soft-skills">Pistes pour les compétences comportementales</h2>
              <p>
                Conseils généraux de préparation Mahara Match — ils ne sont pas présentés comme
                des exigences de cet employeur.
              </p>
            </div>
            <div className="interview-prep-grid">
              {preparation.suggested_competencies.map((competency) => (
                <Card className="interview-prep-card" key={competency.id}>
                  <div className="interview-prep-card__heading">
                    <h3>{competency.name}</h3>
                    <Badge>{competency.category === "communication" ? "Communication" : "Suggestion"}</Badge>
                  </div>
                  <p>{competency.description}</p>
                  <ul>
                    {competency.assessment_criteria.map((criterion) => (
                      <li key={criterion}>{criterion}</li>
                    ))}
                  </ul>
                  <Button
                    variant="secondary"
                    disabled={startingCompetency !== "" || isSubmittingBehavioralAnswer}
                    onClick={() => void beginBehavioralAssessment(competency.id)}
                  >
                    {startingCompetency === competency.id
                      ? "Préparation…"
                      : `S’entraîner : ${competency.name}`}
                  </Button>
                </Card>
              ))}
            </div>
          </section>

          {behavioralAssessment && (
            <Card className="interview-assessment">
              <div className="interview-assessment__heading">
              <div>
                <span className="eyebrow">ENTRAÎNEMENT COMPORTEMENTAL</span>
                <h2>{behavioralAssessment.competency_name} — {behavioralAssessment.offer_title}</h2>
              </div>
              <Badge tone={behavioralAssessment.status === "completed" ? "success" : "accent"}>
                {behavioralAssessment.status === "completed" ? "Terminée" : "En cours"}
              </Badge>
              </div>
              <p className="form-field__hint">
              Entraînement général, et non critère de sélection de l’employeur. Les exemples
              professionnels, scolaires, personnels, bénévoles ou de groupe sont tous recevables.
              Cette évaluation porte sur le contenu décrit, pas sur votre personnalité.
              </p>
              {behavioralAssessment.answers.map((answer) => {
              const question = behavioralAssessment.questions.find(
                (item) => item.id === answer.question_id,
              );
              return (
                <div className="interview-assessment-result" key={answer.question_id}>
                  <div className="interview-assessment-result__heading">
                    <strong>{question?.type === "behavioral" ? "Réponse STAR" : "Question de mise en situation"}</strong>
                    <Badge tone="success">
                      {answer.evaluation.score}/{answer.evaluation.max_score}
                    </Badge>
                  </div>
                  <p>{answer.evaluation.explanation}</p>
                  {Object.entries(answer.evaluation.star_scores).length > 0 && (
                    <ul>
                      {Object.entries(answer.evaluation.star_scores).map(([component, score]) => (
                        <li key={component}>
                          {component.toLocaleUpperCase("fr-FR")} : {score.score}/{score.max_score}
                          {score.evidence ? ` — ${score.evidence}` : ""}
                        </li>
                      ))}
                    </ul>
                  )}
                  {answer.evaluation.strengths.length > 0 && (
                    <p><strong>Points forts :</strong> {answer.evaluation.strengths.join(" ")}</p>
                  )}
                  {answer.evaluation.weaknesses.length > 0 && (
                    <p><strong>À approfondir :</strong> {answer.evaluation.weaknesses.join(" ")}</p>
                  )}
                  {answer.evaluation.suggested_improvements.length > 0 && (
                    <p><strong>Pour progresser :</strong> {answer.evaluation.suggested_improvements.join(" ")}</p>
                  )}
                  <ul>
                    {answer.evaluation.criteria_scores.map((criterion) => (
                      <li key={criterion.criterion_id}>
                        {criterion.label} : {criterion.score}/{criterion.max_score}
                      </li>
                    ))}
                  </ul>
                </div>
              );
              })}
              {behavioralAssessment.status === "completed" ? (
              <p role="status">Les réponses comportementales ont été enregistrées.</p>
              ) : (
              (() => {
                const answeredIds = new Set(
                  behavioralAssessment.answers.map((answer) => answer.question_id),
                );
                const question = behavioralAssessment.questions.find(
                  (item) => !answeredIds.has(item.id),
                );
                if (!question) return null;
                return (
                  <div className="interview-assessment-question">
                    <span className="eyebrow">
                      QUESTION {behavioralAssessment.answers.length + 1} SUR {behavioralAssessment.questions.length}
                    </span>
                    <h3>{question.prompt}</h3>
                    {question.type === "behavioral" && (
                      <p className="form-field__hint">
                        Structurez votre exemple : Situation, Tâche, Action, Résultat (STAR).
                      </p>
                    )}
                    <label className="interview-assessment-text">
                      <span>Votre réponse</span>
                      <textarea
                        className="input"
                        value={behavioralDraftAnswer}
                        maxLength={10000}
                        rows={5}
                        onChange={(event) => setBehavioralDraftAnswer(event.target.value)}
                      />
                    </label>
                    <div className="interview-voice-controls">
                      <Button
                        type="button"
                        variant={isRecordingAnswer ? "secondary" : "ghost"}
                        disabled={
                          isTranscribingAnswer ||
                          isRecordingOtherAnswer(
                            "behavioral",
                            behavioralAssessment.id,
                            question.id,
                          )
                        }
                        onClick={() =>
                          isRecordingAnswer
                            ? stopInterviewRecording()
                            : void startInterviewRecording(
                                "behavioral",
                                behavioralAssessment.id,
                                question.id,
                                "star_text",
                              )
                        }
                      >
                        {isRecordingAnswer ? (
                          <><Square size={16} aria-hidden="true" /> Arrêter l’enregistrement</>
                        ) : (
                          <><Mic size={16} aria-hidden="true" /> Enregistrer une réponse vocale</>
                        )}
                      </Button>
                      {isTranscribingAnswer && (
                        <span role="status">Transcription en cours…</span>
                      )}
                    </div>
                    {voiceTranscript && (
                      <p className="interview-voice-transcript" role="status">
                        <strong>Transcription à vérifier :</strong> {voiceTranscript}
                      </p>
                    )}
                    {voiceError && <p className="workspace-error" role="alert">{voiceError}</p>}
                    <Button
                      disabled={
                        isSubmittingBehavioralAnswer ||
                        isRecordingAnswer ||
                        isTranscribingAnswer ||
                        !behavioralDraftAnswer.trim()
                      }
                      onClick={() => void submitBehavioralAnswer()}
                    >
                      {isSubmittingBehavioralAnswer ? "Évaluation…" : "Envoyer ma réponse"}
                    </Button>
                  </div>
                );
              })()
              )}
            </Card>
          )}

          <details className="interview-prep-levels">
            <summary>Repères de niveaux de maîtrise</summary>
            <ol>
              {preparation.proficiency_levels.map((level) => (
                <li key={level.level}>
                  <strong>{level.level} — {level.name} :</strong> {level.description}
                </li>
              ))}
            </ol>
            <p className="form-field__hint">
              Ces repères sont généraux. L’offre sélectionnée ne fournit pas de niveau requis.
            </p>
          </details>
        </>
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
