/** The small card shown when a citizen-report ring is clicked on the map. Built from DOM nodes with
 * textContent only, so a note can never inject markup. */
import { apiBase } from "../data/loaders";
import { ago, checklistPairs, type Report } from "./reports";

function el(tag: string, text: string | null, style: Partial<CSSStyleDeclaration> = {}): HTMLElement {
  const node = document.createElement(tag);
  if (text !== null) node.textContent = text;
  Object.assign(node.style, style);
  return node;
}

export function reportPopup(report: Report, onFlag?: (report: Report) => void): HTMLElement {
  const root = el("div", null, { fontFamily: "inherit", color: "var(--c-text)", lineHeight: "1.5", fontSize: "13.5px", paddingRight: "20px" });
  const head = el("div", `${report.author} \u00b7 ${ago(report.observed_at)}`, { fontWeight: "600", marginBottom: "2px", fontSize: "14px" });
  root.appendChild(head);
  root.appendChild(el("div", report.site_id ? `Near site ${report.site_id}` : "Not near one of our sites", { color: "var(--c-muted2)", marginBottom: "8px" }));
  for (const [question, answer] of checklistPairs(report.checklist)) {
    const row = el("div", null);
    row.appendChild(el("strong", `${question}: `));
    row.appendChild(document.createTextNode(answer));
    root.appendChild(row);
  }
  if (report.note) root.appendChild(el("div", `\u201c${report.note}\u201d`, { fontStyle: "italic", marginTop: "8px" }));
  if (report.photo_url) {
    const img = el("img", null, { marginTop: "8px", width: "100%", borderRadius: "6px", display: "block" }) as HTMLImageElement;
    img.src = `${apiBase()}${report.photo_url}`;
    img.alt = "Photo from this report";
    root.appendChild(img);
  }
  root.appendChild(el("div", report.is_sample ? "Sample report \u00b7 unverified" : "Citizen report \u00b7 unverified", { color: "var(--c-muted2)", marginTop: "10px", paddingTop: "8px", borderTop: "1px solid var(--c-border-subtle)", fontSize: "12px" }));
  if (onFlag && !report.is_sample && !report.mine) {
    const flag = el("button", "Flag this report", { marginTop: "6px", fontSize: "12px", textDecoration: "underline", background: "none", border: "none", padding: "0", cursor: "pointer", color: "var(--c-muted2)" });
    flag.addEventListener("click", () => onFlag(report));
    root.appendChild(flag);
  }
  return root;
}
