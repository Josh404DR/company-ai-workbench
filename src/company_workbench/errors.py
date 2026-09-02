class WorkbenchError(Exception):
    """Base error with a stable diagnostic code."""

    code = "WB-000"


class NotFoundError(WorkbenchError):
    code = "WB-404"


class InvalidTransitionError(WorkbenchError):
    code = "WB-409"


class EvidenceRequiredError(WorkbenchError):
    code = "WB-422-EVIDENCE"


class AcceptanceRequiredError(WorkbenchError):
    code = "WB-422-ACCEPTANCE"


class RunnerLaunchError(WorkbenchError):
    code = "WB-502-RUNNER-LAUNCH"


class WorktreeError(WorkbenchError):
    code = "WB-500-WORKTREE"



class VerifierIndependenceError(WorkbenchError):
    """Verifier provider matches the builder provider (Invariant 11)."""

    code = "WB-422-VERIFIER-INDEPENDENCE"


class TicketImportError(WorkbenchError):
    code = "WB-422-IMPORT"
