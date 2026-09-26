import { RestHarnessApiClient } from '@/infrastructure/api/rest-harness-api-client'
import { HarnessApiClientPort } from '@/application/ports/harness-api-client.port'

export class ClientFactory {
  private static instance: HarnessApiClientPort | null = null

  public static getHarnessClient(): HarnessApiClientPort {
    if (!ClientFactory.instance) {
      const baseUrl = process.env.HARNESS_API_URL || 'http://localhost:8080'
      const adminToken = process.env.API_ADMIN_TOKEN || ''
      ClientFactory.instance = new RestHarnessApiClient(baseUrl, adminToken)
    }
    return ClientFactory.instance
  }
}
