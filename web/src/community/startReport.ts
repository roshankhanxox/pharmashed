/** Entry point for every "Report" button: sign in first, then choose a nickname, then open the form. */
import { useCommunity } from "./store";
import { useReports, type Spot } from "./reportsStore";

export function startReportFlow(spot: Spot | null = null): void {
  const community = useCommunity.getState();
  if (community.availability !== "ready") return;
  if (!community.signedIn) return community.openAuthDialog("signin");
  if (!community.profile) return community.openNicknameDialog();
  useReports.getState().startReport(spot);
}
