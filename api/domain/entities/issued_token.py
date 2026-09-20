from dataclasses import dataclass

from api.domain.entities.access_token import AccessToken


@dataclass(frozen=True, slots=True)
class IssuedToken:
    token: AccessToken
    plaintext: str
