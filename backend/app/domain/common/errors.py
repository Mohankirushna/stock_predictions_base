"""Domain-level errors. The API layer maps InvariantViolation → 422
(DomainRuleError) so domain code never imports HTTP concepts."""


class InvariantViolation(Exception):
    """A domain rule was broken while constructing or mutating an object."""
