import { beforeEach, describe, expect, it } from "vitest";
import { cityOfSite, useStore } from "./store";

const reset = () => useStore.setState({ selectedCity: null, selectedSiteId: null, expandedDrug: null });

describe("city and site selection", () => {
  beforeEach(reset);

  it("reads the city from a site id", () => {
    expect(cityOfSite("TLS-01")).toBe("TLS");
    expect(cityOfSite("OSL-21")).toBe("OSL");
  });

  it("drops the selected site when switching to a different city", () => {
    useStore.getState().setSelectedSiteId("TLS-01");
    useStore.setState({ expandedDrug: "citalopram" });
    useStore.getState().setSelectedCity("GNT");
    const s = useStore.getState();
    expect(s.selectedCity).toBe("GNT");
    expect(s.selectedSiteId).toBeNull();
    expect(s.expandedDrug).toBeNull();
  });

  it("keeps the selected site when the city does not change", () => {
    useStore.getState().setSelectedSiteId("TLS-01");
    useStore.getState().setSelectedCity("TLS");
    expect(useStore.getState().selectedSiteId).toBe("TLS-01");
  });

  it("keeps the selected site when the city filter is cleared", () => {
    useStore.getState().setSelectedSiteId("TLS-01");
    useStore.getState().setSelectedCity(null);
    expect(useStore.getState().selectedSiteId).toBe("TLS-01");
  });

  it("moves the city filter to a newly selected site's city", () => {
    useStore.getState().setSelectedCity("GNT");
    useStore.getState().setSelectedSiteId("BNV-03");
    const s = useStore.getState();
    expect(s.selectedSiteId).toBe("BNV-03");
    expect(s.selectedCity).toBe("BNV");
  });

  it("clearing the site leaves the city filter alone", () => {
    useStore.getState().setSelectedSiteId("TLS-01");
    useStore.getState().setSelectedSiteId(null);
    expect(useStore.getState().selectedCity).toBe("TLS");
  });
});
