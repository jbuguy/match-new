import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import {
  Avatar,
  Badge,
  Button,
  ChartFrame,
  Chip,
  DataTable,
  Drawer,
  EmptyState,
  Input,
  Modal,
  ProgressBar,
  Select,
  Skeleton,
  Stepper,
  Tabs,
  ToastProvider,
  useToast,
} from "./ui";

describe("shared UI primitives", () => {
  it("uses safe button defaults and displays badges and removable chips", () => {
    const onRemove = vi.fn();
    render(
      <>
        <Button>Continue</Button>
        <Badge tone="success">Validé</Badge>
        <Chip onRemove={onRemove}>Français</Chip>
      </>,
    );

    expect(screen.getByRole("button", { name: "Continue" })).toHaveAttribute("type", "button");
    expect(screen.getByText("Validé")).toHaveClass("badge--success");
    fireEvent.click(screen.getByRole("button", { name: "Supprimer Français" }));
    expect(onRemove).toHaveBeenCalledOnce();
  });

  it("labels inputs and exposes validation messages", () => {
    render(<Input label="Adresse e-mail" error="Adresse invalide" />);

    const input = screen.getByRole("textbox", { name: "Adresse e-mail" });
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(input).toHaveAccessibleDescription("Adresse invalide");
  });

  it("renders a labelled select and handles empty data states", () => {
    render(
      <>
        <Select
          label="Gouvernorat"
          options={[
            { value: "", label: "Choisir" },
            { value: "tunis", label: "Tunis" },
          ]}
        />
        <DataTable
          caption="Offres"
          columns={[{ id: "title", header: "Titre", cell: () => "—" }]}
          rows={[]}
          getRowId={() => "row"}
          emptyMessage="Aucune offre."
        />
      </>,
    );

    expect(screen.getByRole("combobox", { name: "Gouvernorat" })).toBeVisible();
    expect(screen.getByText("Aucune offre.")).toBeVisible();
  });

  it("provides an accessible avatar fallback when the image fails", () => {
    render(<Avatar name="Amel Ben Ali" src="/missing-avatar.png" />);

    const avatar = screen.getByRole("img", { name: "Amel Ben Ali" });
    const image = avatar.querySelector("img");
    expect(image).not.toBeNull();
    if (image) fireEvent.error(image);
    expect(avatar).toHaveTextContent("AB");
  });

  it("keeps tabs keyboard-operable and updates the panel", () => {
    render(
      <Tabs
        label="Profil"
        tabs={[
          { id: "skills", label: "Compétences", content: "Contenu compétences" },
          { id: "experience", label: "Expérience", content: "Contenu expérience" },
        ]}
      />,
    );

    const firstTab = screen.getByRole("tab", { name: "Compétences" });
    firstTab.focus();
    fireEvent.keyDown(firstTab, { key: "ArrowRight" });

    expect(screen.getByRole("tab", { name: "Expérience" })).toHaveFocus();
    expect(screen.getByRole("tabpanel")).toHaveTextContent("Contenu expérience");
  });

  it("traps modal focus and closes it on Escape", () => {
    const onClose = vi.fn();
    render(
      <Modal open title="Confirmer" onClose={onClose}>
        <Button>Confirmer</Button>
        <Button>Annuler</Button>
      </Modal>,
    );

    const dialog = screen.getByRole("dialog", { name: "Confirmer" });
    const confirmButton = within(dialog).getByRole("button", { name: "Confirmer" });
    const cancelButton = within(dialog).getByRole("button", { name: "Annuler" });
    const closeButton = within(dialog).getByRole("button", { name: "Fermer" });
    cancelButton.focus();
    fireEvent.keyDown(document, { key: "Tab" });
    expect(closeButton).toHaveFocus();
    fireEvent.keyDown(document, { key: "Tab", shiftKey: true });
    expect(cancelButton).toHaveFocus();
    expect(confirmButton).toBeVisible();

    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("renders the drawer variant with dialog semantics", () => {
    render(
      <Drawer open title="Filtres" onClose={() => undefined}>
        <p>Contenu</p>
      </Drawer>,
    );

    expect(screen.getByRole("dialog", { name: "Filtres" })).toBeVisible();
    expect(document.querySelector(".modal-backdrop--drawer")).toBeInTheDocument();
  });

  it("announces toasts and lets the user dismiss them", () => {
    function ToastTrigger() {
      const showToast = useToast();
      return <Button onClick={() => showToast("Enregistré", "success")}>Enregistrer</Button>;
    }

    render(
      <ToastProvider>
        <ToastTrigger />
      </ToastProvider>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Enregistrer" }));

    expect(screen.getByRole("status")).toHaveTextContent("Enregistré");
    fireEvent.click(screen.getByRole("button", { name: "Fermer la notification" }));
    expect(screen.queryByText("Enregistré")).not.toBeInTheDocument();
  });

  it("announces empty, loading, step, progress, and chart states accessibly", () => {
    render(
      <>
        <EmptyState title="Aucun résultat" description="Essayez une autre recherche." />
        <Skeleton label="Chargement des offres" />
        <Stepper steps={["Profil", "Compétences", "Préférences"]} currentStep={1} />
        <ProgressBar value={150} label="Profil complété" />
        <ChartFrame title="Tendance" description="Aucune donnée de tendance disponible.">
          <EmptyState title="Indisponible" description="Aucune donnée." />
        </ChartFrame>
      </>,
    );

    expect(screen.getByRole("status", { name: "Aucun résultat" })).toBeVisible();
    expect(screen.getByRole("status", { name: "Chargement des offres" })).toBeVisible();
    expect(screen.getByRole("list", { name: "Progression" })).toBeVisible();
    expect(screen.getByRole("listitem", { current: "step" })).toHaveTextContent("Compétences");
    expect(screen.getByRole("progressbar", { name: "Profil complété" })).toHaveAttribute(
      "aria-valuenow",
      "100",
    );
    expect(screen.getByRole("img", { name: "Aucune donnée de tendance disponible." })).toBeVisible();
  });
});
