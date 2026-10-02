/** What the reports feature stores, who can see it, and how to delete it. Plain language, and accurate to the code. */
import { Modal, primaryButton } from "./Modal";
import { useCommunity } from "./store";

const SECTIONS: { title: string; lines: string[] }[] = [
  {
    title: "What we keep about you",
    lines: [
      "Your email address and name: held by our sign-in service in the same database. They are never shown to anyone else.",
      "Your nickname, and your home city if you choose one.",
      "Each report you file: the spot you pinned, when you visited, your answers, your note (and the tidied version if you used it), and your photo if you add one.",
      "Your points, badges, and any flags you raise on other people's reports.",
    ],
  },
  {
    title: "Who can see it",
    lines: [
      "Anyone can see an approved report, with your nickname, on the map and on the site page. That includes the exact spot you pinned, so do not pin your home. Your email and name are never shown.",
      "The leaderboard shows nicknames only, and only if you chose to appear.",
      "The FHIR export of reports has no nickname and no note text, and points at the nearest site instead of your pin.",
    ],
  },
  {
    title: "Photos and the AI helpers",
    lines: [
      "Photos are re-saved without location or camera data, checked by an AI model for people and number plates, and stored privately. They are only shown on approved reports and are deleted if a report is hidden or you delete your account.",
      "When you tidy a note or add a photo, that text or picture is sent to OpenAI to produce the result.",
      "Please do not photograph people or number plates. The check is a screen, not a guarantee.",
    ],
  },
  {
    title: "Review and removal",
    lines: [
      "Reports that look like they contain personal details, have a flagged photo, or are flagged by three different people are held for a moderator before they are shown.",
      "You can delete your account from the menu at the top right. That removes your profile, reports, photos, points, badges and sign-in. It cannot be undone.",
    ],
  },
];

export function PrivacyDialog() {
  const open = useCommunity((s) => s.privacyOpen);
  const close = useCommunity((s) => s.closePrivacy);
  if (!open) return null;
  return (
    <Modal title="Privacy" size="lg" onClose={close}>
      <p className="text-sm mb-4" style={{ color: "var(--c-muted)" }}>
        PharmaShed is a research prototype. This is exactly what the reports feature does with your data.
      </p>
      {SECTIONS.map((s) => (
        <section key={s.title} className="mb-4">
          <h3 className="font-semibold mb-1">{s.title}</h3>
          <ul className="list-disc pl-5 flex flex-col gap-1 text-sm" style={{ color: "var(--c-muted)" }}>
            {s.lines.map((l) => <li key={l}>{l}</li>)}
          </ul>
        </section>
      ))}
      <button onClick={close} className="w-full px-4 py-2.5 rounded-lg font-semibold mt-2" style={primaryButton}>Close</button>
    </Modal>
  );
}
