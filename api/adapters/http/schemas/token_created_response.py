from api.adapters.http.schemas.token_response import TokenResponse


class TokenCreatedResponse(TokenResponse):
    token: str
