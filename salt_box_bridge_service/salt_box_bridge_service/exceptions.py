from __future__ import annotations


class StopProcessing(Exception):
    """
    Raising of StopProcessing is signal a message is no need further processing
    """


class CreateJobError(Exception): ...
