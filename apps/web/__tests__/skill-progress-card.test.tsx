import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { SkillProgressCard } from "@/components/skill-progress-card";

const fetchSkillExplanationMock = jest.fn();
jest.mock("@/lib/ai", () => ({
  fetchSkillExplanation: (...args: unknown[]) => fetchSkillExplanationMock(...args),
}));

const fetchDecisionTaskMock = jest.fn();
const submitAttemptMock = jest.fn();
jest.mock("@/lib/task", () => {
  class MockTaskApiError extends Error {
    constructor(public status: number, message: string) {
      super(message);
    }
  }
  return {
    fetchDecisionTask: (...args: unknown[]) => fetchDecisionTaskMock(...args),
    submitAttempt: (...args: unknown[]) => submitAttemptMock(...args),
    TaskApiError: MockTaskApiError,
  };
});
const { TaskApiError: MockTaskApiError } = jest.requireMock("@/lib/task") as {
  TaskApiError: new (status: number, message: string) => Error & { status: number };
};

const skill = {
  skill_id: "s1",
  skill_name: "Newton'un İkinci Yasası",
  mastery_label: "İyi öğreniyorsun",
  is_weak: false,
  is_strong: true,
  next_action_label: null,
  next_action_decision_id: null,
  pending_retention_checkpoints: 0,
};

describe("SkillProgressCard", () => {
  beforeEach(() => {
    fetchSkillExplanationMock.mockReset();
    fetchDecisionTaskMock.mockReset();
    submitAttemptMock.mockReset();
  });

  it("fetches and displays an AI explanation when the button is clicked", async () => {
    fetchSkillExplanationMock.mockResolvedValueOnce({
      skill_id: "s1",
      explanation: "F = m*a, kuvvet kütle ile ivmenin çarpımıdır.",
      key_points: ["Kuvvet birimi Newton'dur."],
      provider: "ollama",
      model: "llama3.2:1b",
      prompt_name: "skill_explanation",
      prompt_version: "v1",
      generated_at: "2026-08-30T00:00:00Z",
    });

    render(<SkillProgressCard skill={skill} accessToken="fake-token" />);
    fireEvent.click(screen.getByRole("button", { name: "Bu konuyu açıkla" }));

    await waitFor(() => expect(fetchSkillExplanationMock).toHaveBeenCalledWith("fake-token", "s1"));
    expect(await screen.findByText(/F = m\*a/)).toBeInTheDocument();
    expect(screen.getByText("Kuvvet birimi Newton'dur.")).toBeInTheDocument();
  });

  it("shows an honest failure message when the AI Gateway call fails", async () => {
    fetchSkillExplanationMock.mockRejectedValueOnce(new Error("ai request failed with status 503"));

    render(<SkillProgressCard skill={skill} accessToken="fake-token" />);
    fireEvent.click(screen.getByRole("button", { name: "Bu konuyu açıkla" }));

    expect(await screen.findByText(/Açıklama şu anda oluşturulamadı/)).toBeInTheDocument();
  });
});

describe("SkillProgressCard execution layer (§113 P8+)", () => {
  const skillWithDecision = { ...skill, next_action_label: "Bildiğini farklı bir bağlamda uygula", next_action_decision_id: "d1" };

  beforeEach(() => {
    fetchSkillExplanationMock.mockReset();
    fetchDecisionTaskMock.mockReset();
    submitAttemptMock.mockReset();
  });

  it("does not show a Başla button when there is no decision yet", () => {
    render(<SkillProgressCard skill={skill} accessToken="fake-token" canExecute />);
    expect(screen.queryByRole("button", { name: "Başla" })).not.toBeInTheDocument();
  });

  it("does not show a Başla button for a viewer other than the skill's own student (e.g. a parent), even with a real decision", () => {
    // §51/§90: a parent viewing their child's card would always get a 403
    // from GET /decisions/{id}/task — canExecute defaults to false so this
    // shared component never shows a button that can't work for the viewer.
    render(<SkillProgressCard skill={skillWithDecision} accessToken="fake-token" />);
    expect(screen.queryByRole("button", { name: "Başla" })).not.toBeInTheDocument();
    expect(fetchDecisionTaskMock).not.toHaveBeenCalled();
  });

  it("fetches and answers the real task behind the decision, then shows the result", async () => {
    fetchDecisionTaskMock.mockResolvedValueOnce({
      decision_id: "d1",
      skill_id: "s1",
      skill_name: "Newton'un İkinci Yasası",
      selected_action: "transfer_task",
      assessment_type: "transfer",
      question_id: "q1",
      prompt: "Bir cismin kütlesi 4 kg, ivmesi 2 m/s² ise net kuvvet nedir?",
      difficulty: 0.6,
    });
    submitAttemptMock.mockResolvedValueOnce({
      id: "a1",
      question_id: "q1",
      assessment_type: "transfer",
      is_correct: true,
      evaluation_method: "automatic",
      evaluation_confidence: 1.0,
      submitted_at: "2026-09-01T00:00:00Z",
      evaluated_at: "2026-09-01T00:00:01Z",
    });

    render(<SkillProgressCard skill={skillWithDecision} accessToken="fake-token" canExecute />);
    fireEvent.click(screen.getByRole("button", { name: "Başla" }));

    await waitFor(() => expect(fetchDecisionTaskMock).toHaveBeenCalledWith("fake-token", "d1"));
    expect(await screen.findByText(/net kuvvet nedir/)).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText("Cevabın"), { target: { value: "8 N" } });
    fireEvent.click(screen.getByRole("button", { name: "Gönder" }));

    await waitFor(() =>
      expect(submitAttemptMock).toHaveBeenCalledWith("fake-token", { question_id: "q1", assessment_type: "transfer", learner_response: "8 N" })
    );
    expect(await screen.findByText(/Doğru!/)).toBeInTheDocument();
  });

  it("shows a specific message when the decision has no answerable task", async () => {
    fetchDecisionTaskMock.mockRejectedValueOnce(new MockTaskApiError(404, "action_has_no_task"));

    render(<SkillProgressCard skill={skillWithDecision} accessToken="fake-token" canExecute />);
    fireEvent.click(screen.getByRole("button", { name: "Başla" }));

    expect(await screen.findByText(/bir soru çözerek yapılabilecek bir görev değil/)).toBeInTheDocument();
  });
});
