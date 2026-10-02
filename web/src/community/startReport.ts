/** Entry point for every "Report" button: sign in first, then choose a nickname, then open the form. */
import { useCommunity } from "./store";
import type { Report } from "./reports";
import { useReports, type Spot } from "./reportsStore";

export function startReportFlow(spot: Spot | null = null): void {
  const community = useCommunity.getState();
  if (community.availability !== "ready") return;
  if (!community.signedIn) return community.openAuthDialog("signin");
  if (!community.profile) return community.openNicknameDialog();
  useReports.getState().startReport(spot);
}

/** Flag a report: sign in first (flags need an account), then open the flag dialog. */
export function startFlagFlow(report: Report): void {
  const community = useCommunity.getState();
  if (community.availability !== "ready") return;
  if (!community.signedIn) return community.openAuthDialog("signin");
  useReports.getState().startFlag(report);
}
