export class SecretRevealView {
  private readonly _plaintextToken: string
  private readonly _maskedPreview: string
  private _isAcknowledged: boolean

  private constructor(plaintextToken: string, maskedPreview: string) {
    this._plaintextToken = plaintextToken
    this._maskedPreview = maskedPreview
    this._isAcknowledged = false
  }

  public static create(plaintextToken: string): SecretRevealView {
    if (!plaintextToken || !plaintextToken.startsWith('hm_')) {
      throw new Error('Plaintext token must start with "hm_"')
    }

    const prefix = plaintextToken.slice(0, 7)
    const suffix = plaintextToken.length > 11 ? plaintextToken.slice(-4) : '...'
    const masked = `${prefix}...${suffix}`

    return new SecretRevealView(plaintextToken, masked)
  }

  public get plaintextToken(): string {
    return this._plaintextToken
  }

  public get maskedPreview(): string {
    return this._maskedPreview
  }

  public get isAcknowledged(): boolean {
    return this._isAcknowledged
  }

  public acknowledge(): void {
    this._isAcknowledged = true
  }
}
