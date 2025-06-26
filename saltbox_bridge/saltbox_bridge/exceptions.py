from __future__ import annotations


class SaltBoxBridgeError(RuntimeError): ...


class CreateJobError(SaltBoxBridgeError): ...


class CoreConnectionTimeoutError(SaltBoxBridgeError, TimeoutError): ...


class StopProcessing(SaltBoxBridgeError):
    """
    Raising of StopProcessing is signal a message is no need further processing
    """


class CryptError(Exception): ...


class CreateSignError(CryptError): ...


class VerifySignError(CryptError): ...
