import type { PublicationResult } from "../../../domain/contracts.js";
import type { PhaseOutcome, PublicationPhaseContext } from "./publication-phase-context.js";

export abstract class AbstractPublicationPhase {
  private nextPhase?: AbstractPublicationPhase;

  public setNext(phase: AbstractPublicationPhase): AbstractPublicationPhase {
    this.nextPhase = phase;
    return phase;
  }

  public async handle(context: PublicationPhaseContext): Promise<PublicationResult> {
    const result = await this.execute(context);
    if (result !== undefined) return result;
    if (this.nextPhase) return this.nextPhase.handle(context);
    throw new Error("Publication phase chain ended without a result");
  }

  protected abstract execute(context: PublicationPhaseContext): Promise<PhaseOutcome> | PhaseOutcome;
}
