from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SecurityFailureResponse:
    status_code: int
    code: str
    headers: dict[str, str]
    message: str

    def to_dict(self) -> dict[str, object]:
        return {
            "status_code": self.status_code,
            "code": self.code,
            "headers": dict(self.headers),
            "message": self.message,
        }


class SecurityFailureMapper:
    def map(self, error: Exception, required_scope: str | None = None) -> SecurityFailureResponse:
        if required_scope is None:
            required_scope = getattr(error, "required_scope", None)
            if required_scope is None:
                scopes = getattr(error, "scopes", None) or getattr(error, "required_scopes", None)
                if scopes:
                    required_scope = str(next(iter(scopes)))
        if required_scope:
            return self.authorization(required_scope)
        return self.authentication(getattr(error, "reason_code", "invalid_token"))

    def authentication(self, reason_code: str = "invalid_token") -> SecurityFailureResponse:
        return SecurityFailureResponse(
            status_code=401,
            code=reason_code,
            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
            message="authentication required",
        )

    def authorization(self, required_scope: str) -> SecurityFailureResponse:
        return SecurityFailureResponse(
            status_code=403,
            code="insufficient_scope",
            headers={
                "WWW-Authenticate": (
                    f'Bearer error="insufficient_scope", scope="{required_scope}"'
                )
            },
            message="insufficient scope",
        )


def map_authentication_failure(reason_code: str = "invalid_token") -> SecurityFailureResponse:
    return SecurityFailureMapper().authentication(reason_code)


def map_authorization_failure(required_scope: str) -> SecurityFailureResponse:
    return SecurityFailureMapper().authorization(required_scope)


MapSecurityFailure = SecurityFailureMapper
