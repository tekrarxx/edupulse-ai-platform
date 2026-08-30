import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { SkillProgressCard } from "@/components/skill-progress-card";

const fetchSkillExplanationMock = jest.fn();
jest.mock("@/lib/ai", () => ({
  fetchSkillExplanation: (...args: unknown[]) => fetchSkillExplanationMock(...args),
}));

const skill = {
  skill_id: "s1",
  skill_name: "Newton'un İkinci Yasası",
  mastery_label: "İyi öğreniyorsun",
  is_weak: false,
  is_strong: true,
  next_action_label: null,
  pending_retention_checkpoints: 0,
};

describe("SkillProgressCard", () => {
  beforeEach(() => {
    fetchSkillExplanationMock.mockReset();
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
