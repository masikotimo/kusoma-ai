from dataclasses import dataclass, field


@dataclass
class CurriculumRow:
    learner_id: str
    display_name: str
    expected_module: int
    current_module: int
    last_submission_date: str
    prior_experience: str
    assigned_mentor: str
    coordinator: str

    @property
    def behind(self) -> bool:
        return self.current_module < self.expected_module


@dataclass
class ClassificationResult:
    learner_id: str
    message_excerpt: str
    risk_types: list[str]
    confidence: str  # "low" | "medium" | "high" | "n/a"
    reasoning: str


@dataclass
class RoutedAction:
    audience: str          # "mentor" | "coordinator" | "none"
    recipient: str         # mentor/coordinator id
    message: str
    risk_types: list[str] = field(default_factory=list)
