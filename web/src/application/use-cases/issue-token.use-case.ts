import { HarnessApiClientPort } from '@/application/ports/harness-api-client.port'
import { AccessTokenOrder } from '@/domain/access-token-order'
import { SecretRevealView } from '@/domain/secret-reveal-view'

export class IssueTokenUseCase {
  private readonly client: HarnessApiClientPort

  public constructor(client: HarnessApiClientPort) {
    this.client = client
  }

  public async execute(order: AccessTokenOrder): Promise<SecretRevealView> {
    const expiresAt = order.calculateExpiresAt()

    const ownerPayload =
      order.owner.kind === 'user'
        ? { user_id: order.owner.id }
        : { service_account_id: order.owner.id }

    const created = await this.client.createToken({
      name: order.name,
      ...ownerPayload,
      scopes: order.scopes.map((s) => s.value),
      project_keys: order.projectKeys,
      expires_at: expiresAt,
    })

    return SecretRevealView.create(created.token)
  }
}
