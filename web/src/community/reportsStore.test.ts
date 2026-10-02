import { beforeEach, describe, expect, it, vi } from "vitest";

const postReport = vi.fn();
const fetchReports = vi.fn();
vi.mock("./reports", async (orig) => ({ ...(await orig<typeof import("./reports")>()), postReport, fetchReports }));

const { useReports } = await import("./reportsStore");
const report = { id: "r1", lat: 1, lon: 2, site_id: "TLS-01", city: "TLS", observed_at: "2026-06-01T00:00:00Z",
  checklist: { foam: "none" }, note: "", is_sample: false, author: "Pat", mine: true };

beforeEach(() => {
  postReport.mockReset();
  fetchReports.mockReset();
  useReports.setState({ reports: [], layerOn: true, picking: false, dialogOpen: false, spot: null, busy: false, error: null, justSent: null });
});

describe("filing flow", () => {
  it("opens at a given spot, or picks one on the map and comes back", () => {
    useReports.getState().startReport({ lat: 1, lon: 2 });
    expect(useReports.getState()).toMatchObject({ dialogOpen: true, spot: { lat: 1, lon: 2 } });
    useReports.getState().startPicking();
    expect(useReports.getState()).toMatchObject({ dialogOpen: false, picking: true });
    useReports.getState().pickSpot({ lat: 3, lon: 4 });
    expect(useReports.getState()).toMatchObject({ dialogOpen: true, picking: false, spot: { lat: 3, lon: 4 } });
  });

  it("refuses to send without a spot", async () => {
    expect(await useReports.getState().submit({ observed_at: "x", checklist: { foam: "none" }, note: "" })).toBe(false);
    expect(useReports.getState().error).toMatch(/where you are/);
    expect(postReport).not.toHaveBeenCalled();
  });

  it("sends the spot with the answers, adds the report to the list and turns the layer on", async () => {
    postReport.mockResolvedValue(report);
    useReports.setState({ spot: { lat: 1, lon: 2 }, layerOn: false });
    expect(await useReports.getState().submit({ observed_at: "t", checklist: { foam: "none" }, note: "n" })).toBe(true);
    expect(postReport).toHaveBeenCalledWith({ observed_at: "t", checklist: { foam: "none" }, note: "n", lat: 1, lon: 2 });
    expect(useReports.getState()).toMatchObject({ reports: [report], justSent: report, layerOn: true, busy: false });
  });

  it("shows the server's message and keeps the dialog open on failure", async () => {
    postReport.mockRejectedValue(new Error("Please leave links out of the note."));
    useReports.setState({ spot: { lat: 1, lon: 2 }, dialogOpen: true });
    expect(await useReports.getState().submit({ observed_at: "t", checklist: { foam: "none" }, note: "" })).toBe(false);
    expect(useReports.getState()).toMatchObject({ error: "Please leave links out of the note.", dialogOpen: true, busy: false });
  });

  it("a failed load leaves existing reports alone", async () => {
    useReports.setState({ reports: [report] });
    fetchReports.mockRejectedValue(new Error("down"));
    await useReports.getState().load();
    expect(useReports.getState().reports).toEqual([report]);
  });
});

describe("flagging", () => {
  it("flag state opens and closes", () => {
    useReports.getState().startFlag(report);
    expect(useReports.getState()).toMatchObject({ flagging: report, flagDone: false });
    useReports.getState().closeFlag();
    expect(useReports.getState()).toMatchObject({ flagging: null, flagDone: false });
  });
});
