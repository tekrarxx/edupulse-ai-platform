import { render, screen, waitFor } from "@testing-library/react";
import AdminDashboardPage from "@/app/dashboard/admin/page";

const replaceMock = jest.fn();
const pushMock = jest.fn();
jest.mock("next/navigation", () => ({
  useRouter: () => ({ replace: replaceMock, push: pushMock }),
}));

const logoutMock = jest.fn();
// A stable object reference — see teacher-dashboard-page.test.tsx for why.
const adminUser = {
  id: "a1",
  tenant_id: "tenant1",
  email: "a@example.com",
  display_name: "Yönetici",
  role: "SUPER_ADMIN",
  is_active: true,
};
const useAuthMock = jest.fn(() => ({
  user: adminUser,
  accessToken: "fake-token",
  status: "authenticated",
  logout: logoutMock,
}));
jest.mock("@/lib/auth-context", () => ({
  useAuth: () => useAuthMock(),
}));

const fetchAdminDashboardMock = jest.fn();
jest.mock("@/lib/dashboard", () => ({
  fetchAdminDashboard: (...args: unknown[]) => fetchAdminDashboardMock(...args),
}));

// PlanSwitcher fetches on mount unconditionally — mocked here so this
// page's own tests never make a real network call for it.
jest.mock("@/lib/plan", () => ({
  fetchPlans: jest.fn().mockResolvedValue([]),
  switchTenantPlan: jest.fn(),
}));

const dashboardResponse = {
  tenant_id: "tenant1",
  active_student_count: 12,
  active_teacher_count: 3,
  students_needing_attention_count: 2,
  weak_skill_student_count: 4,
  forgetting_student_count: 1,
  misconception_student_count: 0,
  escalated_student_count: 1,
  retention_pending_count: 5,
  retention_supported_count: 3,
  retention_not_supported_count: 1,
  retention_inconclusive_count: 0,
  decisions_total_count: 40,
  decisions_allowed_count: 35,
  decisions_escalated_count: 3,
  decisions_rejected_count: 2,
  ai_requests_total_count: 10,
  ai_requests_success_count: 7,
  ai_requests_failed_count: 3,
  plan_name: "Free",
  ai_explanations_used_this_month: 4,
  ai_explanations_monthly_limit: 10,
  tenant_user_count: 3,
  tenant_user_limit: 5,
};

describe("AdminDashboardPage", () => {
  beforeEach(() => {
    fetchAdminDashboardMock.mockReset();
    replaceMock.mockReset();
    useAuthMock.mockReturnValue({
      user: adminUser,
      accessToken: "fake-token",
      status: "authenticated",
      logout: logoutMock,
    });
  });

  it("renders tenant-wide counts for an admin", async () => {
    fetchAdminDashboardMock.mockResolvedValueOnce(dashboardResponse);

    render(<AdminDashboardPage />);

    expect(await screen.findByText("12")).toBeInTheDocument();
    expect(screen.getByText("Aktif öğrenci")).toBeInTheDocument();
    expect(screen.getByText("Aktif öğretmen")).toBeInTheDocument();
    expect(screen.getByText("Yapay zeka sistem sağlığı")).toBeInTheDocument();
    expect(screen.getByText("Plan: Free")).toBeInTheDocument();
    expect(screen.getByText(/4 AI açıklaması kullanıldı \/ 10 limit/)).toBeInTheDocument();
    expect(screen.getByText(/3 kullanıcı \/ 5 kullanıcı limiti/)).toBeInTheDocument();
  });

  it("shows 'sınırsız' for a plan with no configured AI-explanation or seat limit", async () => {
    fetchAdminDashboardMock.mockResolvedValueOnce({
      ...dashboardResponse,
      plan_name: "Okul",
      ai_explanations_monthly_limit: null,
      tenant_user_limit: null,
    });

    render(<AdminDashboardPage />);

    expect(await screen.findByText("Plan: Okul")).toBeInTheDocument();
    expect(screen.getAllByText(/\(sınırsız\)/)).toHaveLength(2);
  });

  it("redirects a STUDENT away from the admin dashboard", () => {
    useAuthMock.mockReturnValue({
      user: { id: "s1", tenant_id: "tenant1", email: "s@example.com", display_name: "Öğrenci", role: "STUDENT", is_active: true },
      accessToken: "fake-token",
      status: "authenticated",
      logout: logoutMock,
    });

    render(<AdminDashboardPage />);

    expect(replaceMock).toHaveBeenCalledWith("/dashboard");
    expect(fetchAdminDashboardMock).not.toHaveBeenCalled();
  });

  it("shows an error message if the request fails", async () => {
    fetchAdminDashboardMock.mockRejectedValueOnce(new Error("network error"));

    render(<AdminDashboardPage />);

    await waitFor(() => expect(screen.getByText("Pano yüklenirken bir sorun oluştu.")).toBeInTheDocument());
  });
});
