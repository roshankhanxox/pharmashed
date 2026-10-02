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

export function reportPopup(report: Report): HTMLElement {
  const root = el("div", null, { fontFamily: "inherit", color: "#1c1917", lineHeight: "1.4", fontSize: "13px" });
  const head = el("div", `${report.author} \u00b7 ${ago(report.observed_at)}`, { fontWeight: "600", marginBottom: "2px" });
  root.appendChild(head);
  root.appendChild(el("div", report.site_id ? `Near site ${report.site_id}` : "Not near one of our sites", { color: "#57534e", marginBottom: "6px" }));
  for (const [question, answer] of checklistPairs(report.checklist)) {
    const row = el("div", null);
    row.appendChild(el("strong", `${question}: `));
    row.appendChild(document.createTextNode(answer));
    root.appendChild(row);
  }
  if (report.note) root.appendChild(el("div", `\u201c${report.note}\u201d`, { fontStyle: "italic", marginTop: "6px" }));
  if (report.photo_url) {
    const img = el("img", null, { marginTop: "8px", width: "100%", borderRadius: "6px", display: "block" }) as HTMLImageElement;
    img.src = `${apiBase()}${report.photo_url}`;
    img.alt = "Photo from this report";
    root.appendChild(img);
  }
  root.appendChild(el("div", report.is_sample ? "Sample report \u00b7 unverified" : "Citizen report \u00b7 unverified", { color: "#78716c", marginTop: "8px", fontSize: "12px" }));
  return root;
}
