export type AllowedScope = 'memory:read' | 'memory:publish' | 'memory:impact'

export class TokenScope {
  public static readonly ALLOWED_SCOPES: readonly AllowedScope[] = [
    'memory:read',
    'memory:publish',
    'memory:impact',
  ]

  private readonly _value: AllowedScope

  private constructor(value: AllowedScope) {
    this._value = value
  }

  public static isValid(scope: string): scope is AllowedScope {
    return TokenScope.ALLOWED_SCOPES.includes(scope as AllowedScope)
  }

  public static create(value: string): TokenScope {
    if (!TokenScope.isValid(value)) {
      throw new Error(
        `Invalid scope: "${value}". Allowed scopes: ${TokenScope.ALLOWED_SCOPES.join(', ')}`
      )
    }
    return new TokenScope(value)
  }

  public get value(): AllowedScope {
    return this._value
  }
}
