import type { PublicationResult } from "../../../domain/contracts.js";
import type { PhaseOutcome, PublicationPhaseContext } from "./publication-phase-context.js";

export abstract class AbstractPublicationPhase {
  private nextPhase?: AbstractPublicationPhase;

  public setNext(phase: AbstractPublicationPhase): AbstractPublicationPhase {
    this.nextPhase = phase;
    return phase;
  }

  public async handle(context: PublicationPhaseContext): Promise<PublicationResult> {
    const phase = this.getProgressLabel(context);
    context.onProgress?.({ phase, state: "started" });

    let result: PhaseOutcome;
    try {
      result = await this.execute(context);
    } catch (error) {
      context.onProgress?.({ phase, state: "failed" });
      throw error;
    }

    context.onProgress?.({ phase, state: "completed" });
    if (result !== undefined) return result;
    if (this.nextPhase) return this.nextPhase.handle(context);
    throw new Error("Publication phase chain ended without a result");
  }

  protected abstract getProgressLabel(context: PublicationPhaseContext): string;

  protected abstract execute(context: PublicationPhaseContext): Promise<PhaseOutcome> | PhaseOutcome;
}
