import { TokenScope } from '@/domain/token-scope'
import { UserTokenOwner } from '@/domain/user-token-owner'

export type ServiceAccountTokenOwner = Readonly<{
  kind: 'service-account'
  id: string
  name: string
  tenantId: string
  tenantName: string
}>

export type TokenOwner = UserTokenOwner | ServiceAccountTokenOwner

export interface CreateAccessTokenOrderProps {
  name: string
  owner?: TokenOwner
  serviceAccountId?: string
  scopes: TokenScope[]
  projectKeys: string[]
  lifetimeDays?: number
}

export class AccessTokenOrder {
  private readonly _name: string
  private readonly _owner: TokenOwner
  private readonly _scopes: TokenScope[]
  private readonly _projectKeys: string[]
  private readonly _lifetimeDays?: number

  private constructor(
    name: string,
    owner: TokenOwner,
    scopes: TokenScope[],
    projectKeys: string[],
    lifetimeDays?: number
  ) {
    this._name = name
    this._owner = owner
    this._scopes = [...scopes]
    this._projectKeys = [...projectKeys]
    this._lifetimeDays = lifetimeDays
  }

  public static create(props: CreateAccessTokenOrderProps): AccessTokenOrder {
    const trimmedName = props.name.trim()
    if (!trimmedName) {
      throw new Error('Token name cannot be empty')
    }

    const owner = AccessTokenOrder.resolveOwner(props)

    if (!props.scopes || props.scopes.length === 0) {
      throw new Error('At least one scope must be selected')
    }

    const cleanedProjects = Array.from(
      new Set((props.projectKeys || []).map((p) => p.trim()).filter((p) => p.length > 0))
    )
    if (props.projectKeys?.length && cleanedProjects.length === 0) {
      throw new Error('At least one project must be selected')
    }

    AccessTokenOrder.validateLifetime(owner, props.lifetimeDays)

    return new AccessTokenOrder(
      trimmedName,
      owner,
      props.scopes,
      cleanedProjects,
      props.lifetimeDays
    )
  }

  private static resolveOwner(props: CreateAccessTokenOrderProps): TokenOwner {
    if (props.owner && props.serviceAccountId) {
      throw new Error('Exactly one token owner must be selected')
    }

    if (props.owner) {
      if (!props.owner.id.trim()) {
        throw new Error('Token owner ID cannot be empty')
      }
      if (props.owner.kind === 'user' && !props.owner.name.trim()) {
        throw new Error('User owner name cannot be empty')
      }
      if (props.owner.kind === 'user') {
        return Object.freeze({
          kind: 'user',
          id: props.owner.id.trim(),
          name: props.owner.name.trim(),
        })
      }
      if (props.owner.kind === 'service-account') {
        if (!props.owner.name.trim()) {
          throw new Error('Service-account owner name cannot be empty')
        }
        if (!props.owner.tenantId.trim()) {
          throw new Error('Service-account organization ID cannot be empty')
        }
        if (!props.owner.tenantName.trim()) {
          throw new Error('Service-account organization name cannot be empty')
        }
        return Object.freeze({
          kind: 'service-account',
          id: props.owner.id.trim(),
          name: props.owner.name.trim(),
          tenantId: props.owner.tenantId.trim(),
          tenantName: props.owner.tenantName.trim(),
        })
      }
      throw new Error('Token owner type is invalid')
    }

    if (!props.serviceAccountId?.trim()) {
      throw new Error('Service account ID cannot be empty')
    }

    return Object.freeze({
      kind: 'service-account',
      id: props.serviceAccountId.trim(),
      name: 'Service account',
      tenantId: '',
      tenantName: '',
    })
  }

  private static validateLifetime(owner: TokenOwner, lifetimeDays?: number): void {
    if (owner.kind === 'user') {
      if (lifetimeDays !== 30 && lifetimeDays !== 90) {
        throw new Error('User token lifetime must be 30 or 90 days')
      }
      return
    }

    if (lifetimeDays === 91) {
      throw new Error('Lifetime cannot exceed 90 days')
    }
    if (lifetimeDays !== undefined && lifetimeDays !== 30 && lifetimeDays !== 90) {
      throw new Error('Service-account token lifetime must be 30 or 90 days')
    }
  }

  public get name(): string {
    return this._name
  }

  public get serviceAccountId(): string | undefined {
    return this._owner.kind === 'service-account' ? this._owner.id : undefined
  }

  public get owner(): TokenOwner {
    return this._owner
  }

  public get userId(): string | undefined {
    return this._owner.kind === 'user' ? this._owner.id : undefined
  }

  public get scopes(): TokenScope[] {
    return [...this._scopes]
  }

  public get projectKeys(): string[] {
    return [...this._projectKeys]
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
