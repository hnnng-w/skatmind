"""Private validation-phase feedback for the existing Learning Report-file form."""

from skatmind.corpus_web.uploads import _UploadedFileTypeError, _UploadedJSONError

from .validation_contracts import FrontendValidationIssueV1


class ReportFileError(ValueError):
    def __init__(self, phase):
        if phase not in {"format", "attachment"}:
            raise ValueError("Unknown Report-file validation phase.")
        self.phase = phase
        super().__init__("Report-file validation failed.")


def report_file_validation_issues(error, *, status):
    field = "report_source_file"
    if status == 409:
        field = None
        key = ("validation.message.persistence_conflict" if isinstance(error, FileExistsError)
               else "validation.message.stale")
    elif status == 413:
        key = "validation.message.upload_size"
    elif status == 415 or isinstance(error, _UploadedFileTypeError):
        key = "validation.message.upload_type"
    elif isinstance(error, _UploadedJSONError):
        key = "validation.report_file.json"
    elif isinstance(error, ReportFileError):
        key = "validation.report_file." + error.phase
        if error.phase == "attachment":
            field = "match_snapshot_id"
    else:
        key = "validation.message.invalid_upload"
    return (FrontendValidationIssueV1(field_key=field, message_key=key),)
