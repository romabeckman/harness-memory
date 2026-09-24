import { HarnessApiClientPort } from '@/application/ports/harness-api-client.port'

export class RevokeTokenUseCase {
  private readonly client: HarnessApiClientPort

  public constructor(client: HarnessApiClientPort) {
    this.client = client
  }

  public async execute(tokenId: string): Promise<void> {
    const trimmedId = tokenId.trim()
    if (!trimmedId) {
      throw new Error('Token ID cannot be empty')
    }

    await this.client.revokeToken(trimmedId)
  }
}
