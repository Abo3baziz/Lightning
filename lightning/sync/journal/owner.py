"""Independent owner signing key, wrapped under each pair of owner secrets.

Uses the profile's existing bounded Argon2id/AES-GCM wrapping implementation;
it neither changes the data-key locks nor invents a secret-sharing primitive.
This construction requires independent security review before production use.
"""
from __future__ import annotations

from itertools import combinations

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from lightning.security.keys import (_lock, _unlock, _password_bytes,
                                    normalize_answer, normalize_recovery_key,
                                    RECOVERY_MEMORY_KIB, RECOVERY_ITERATIONS)
from .codec import JournalError, canonical, fields, uuid

NAMES = ("answer", "password", "recovery")


def public_key(identity):
    key = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), bytes.fromhex(identity.public_key))
    return key.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint).hex()


def _secret(name, value):
    if name == "answer":
        return normalize_answer(value)
    if name == "recovery":
        return normalize_recovery_key(value)
    _password_bytes(value)
    return value


class OwnerCredential:
    def __init__(self, key):
        self._key = key

    @property
    def public_key(self):
        return self._key.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint).hex()

    def sign(self, data):
        return self._key.sign(data, ec.ECDSA(hashes.SHA256())).hex()

    @classmethod
    def create(cls, profile, *, password, recovery, answer):
        uuid(profile)
        values = dict(password=password, recovery=recovery, answer=answer)
        normalized = {name: _secret(name, value) for name, value in values.items()}
        credential = cls(ec.generate_private_key(ec.SECP256R1()))
        context = canonical(dict(type="journal-owner", version=1, profile=profile, public_key=credential.public_key))
        scalar = credential._key.private_numbers().private_value.to_bytes(32, "big")
        wraps = {}
        for pair in combinations(NAMES, 2):
            label = "+".join(pair)
            wraps[label] = _lock(scalar, canonical({name: normalized[name] for name in pair}),
                                "journal-owner:" + label, RECOVERY_MEMORY_KIB, RECOVERY_ITERATIONS, context)
        return credential, dict(version=1, profile=profile, public_key=credential.public_key, wraps=wraps)

    @classmethod
    def unlock(cls, document, proofs, *, guard):
        """Caller supplies the persistent AttemptGuard; a lone secret never opens a slot."""
        guard.check()
        try:
            fields(document, ("version", "profile", "public_key", "wraps"))
            uuid(document["profile"])
            if document["version"] != 1 or type(proofs) is not dict or len(proofs) != 2 or not set(proofs) <= set(NAMES):
                raise JournalError("Supply two different owner secrets")
            label = "+".join(sorted(proofs))
            fields(document["wraps"], ("answer+password", "answer+recovery", "password+recovery"))
            context = canonical(dict(type="journal-owner", version=1, profile=document["profile"], public_key=document["public_key"]))
            secret = canonical({name: _secret(name, value) for name, value in proofs.items()})
            scalar = _unlock(document["wraps"][label], secret, "journal-owner:" + label, context)
            result = cls(ec.derive_private_key(int.from_bytes(scalar, "big"), ec.SECP256R1()))
            if result.public_key != document["public_key"]:
                raise JournalError("Owner credential mismatch")
        except (ValueError, TypeError, KeyError) as error:
            guard.failed()
            raise JournalError("Owner secrets did not unlock the authority credential") from error
        guard.succeeded()
        return result
