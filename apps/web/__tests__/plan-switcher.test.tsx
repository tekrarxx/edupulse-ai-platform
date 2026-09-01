import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { PlanSwitcher } from "@/components/plan-switcher";

const fetchPlansMock = jest.fn();
const switchTenantPlanMock = jest.fn();
jest.mock("@/lib/plan", () => ({
  fetchPlans: (...args: unknown[]) => fetchPlansMock(...args),
  switchTenantPlan: (...args: unknown[]) => switchTenantPlanMock(...args),
}));

describe("PlanSwitcher", () => {
  beforeEach(() => {
    fetchPlansMock.mockReset();
    switchTenantPlanMock.mockReset();
  });

  it("lists the available plans and switches to the selected one", async () => {
    fetchPlansMock.mockResolvedValueOnce([
      { id: "p1", slug: "free", name: "Free" },
      { id: "p2", slug: "school", name: "Okul" },
    ]);
    switchTenantPlanMock.mockResolvedValueOnce({ id: "p2", slug: "school", name: "Okul" });
    const onSwitched = jest.fn();

    render(<PlanSwitcher accessToken="fake-token" currentPlanName="Free" onSwitched={onSwitched} />);

    await screen.findByText("Şu anki plan: Free.");
    fireEvent.change(screen.getByLabelText("Plan değiştir:"), { target: { value: "school" } });
    fireEvent.click(screen.getByRole("button", { name: "Değiştir" }));

    await waitFor(() => expect(switchTenantPlanMock).toHaveBeenCalledWith("fake-token", "school"));
    expect(onSwitched).toHaveBeenCalled();
    expect(await screen.findByText(/Plan değiştirildi: Okul/)).toBeInTheDocument();
  });

  it("shows an honest error message when the switch fails", async () => {
    fetchPlansMock.mockResolvedValueOnce([{ id: "p1", slug: "free", name: "Free" }]);
    switchTenantPlanMock.mockRejectedValueOnce(new Error("insufficient_role"));

    render(<PlanSwitcher accessToken="fake-token" currentPlanName="Free" onSwitched={jest.fn()} />);

    await screen.findByText("Şu anki plan: Free.");
    fireEvent.click(screen.getByRole("button", { name: "Değiştir" }));

    expect(await screen.findByText("Plan değiştirilemedi.")).toBeInTheDocument();
  });

  it("renders nothing while there are no plans to choose from", async () => {
    fetchPlansMock.mockResolvedValueOnce([]);
    render(<PlanSwitcher accessToken="fake-token" currentPlanName="Free" onSwitched={jest.fn()} />);
    await waitFor(() => expect(fetchPlansMock).toHaveBeenCalled());
    expect(screen.queryByRole("button", { name: "Değiştir" })).not.toBeInTheDocument();
  });
});
