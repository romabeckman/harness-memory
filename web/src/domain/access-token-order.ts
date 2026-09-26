import { TokenScope } from '@/domain/token-scope'

export interface CreateAccessTokenOrderProps {
  name: string
  serviceAccountId: string
  scopes: TokenScope[]
  projectKeys: string[]
  lifetimeDays?: number
}

export class AccessTokenOrder {
  private readonly _name: string
  private readonly _serviceAccountId: string
  private readonly _scopes: TokenScope[]
  private readonly _projectKeys: string[]
  private readonly _lifetimeDays?: number

  private constructor(
    name: string,
    serviceAccountId: string,
    scopes: TokenScope[],
    projectKeys: string[],
    lifetimeDays?: number
  ) {
    this._name = name
    this._serviceAccountId = serviceAccountId
    this._scopes = scopes
    this._projectKeys = projectKeys
    this._lifetimeDays = lifetimeDays
  }

  public static create(props: CreateAccessTokenOrderProps): AccessTokenOrder {
    const trimmedName = props.name.trim()
    if (!trimmedName) {
      throw new Error('Token name cannot be empty')
    }

    if (!props.serviceAccountId || !props.serviceAccountId.trim()) {
      throw new Error('Service account ID cannot be empty')
    }

    if (!props.scopes || props.scopes.length === 0) {
      throw new Error('At least one scope must be selected')
    }

    const cleanedProjects = Array.from(
      new Set((props.projectKeys || []).map((p) => p.trim()).filter((p) => p.length > 0))
    )
    if (props.projectKeys?.length && cleanedProjects.length === 0) {
      throw new Error('At least one project must be selected')
    }

    if (props.lifetimeDays !== undefined) {
      if (props.lifetimeDays < 1 || props.lifetimeDays > 90) {
        throw new Error('Lifetime cannot exceed 90 days')
      }
    }

    return new AccessTokenOrder(
      trimmedName,
      props.serviceAccountId,
      props.scopes,
      cleanedProjects,
      props.lifetimeDays
    )
  }

  public get name(): string {
    return this._name
  }

  public get serviceAccountId(): string {
    return this._serviceAccountId
  }

  public get scopes(): TokenScope[] {
    return this._scopes
  }

  public get projectKeys(): string[] {
    return this._projectKeys
  }

  public get lifetimeDays(): number | undefined {
    return this._lifetimeDays
  }

  public calculateExpiresAt(baseDate: Date = new Date()): string | null {
    if (this._lifetimeDays === undefined) {
      return null
    }

    const expiry = new Date(baseDate.getTime() + this._lifetimeDays * 24 * 60 * 60 * 1000)
    return expiry.toISOString()
  }
}
