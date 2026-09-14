"""Private reasons at authoritative declaration checks; English ValueError compatibility."""


class DeclarationValueError(ValueError):
    def __init__(self, message, *, reason, field_key, required_fields=()):
        super().__init__(message)
        self.reason = reason
        self.field_key = field_key
        self.required_fields = tuple(required_fields)
