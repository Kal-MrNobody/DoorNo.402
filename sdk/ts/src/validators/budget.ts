/**
 * Daily budget tracker for x402 payment protection.
 *
 * Tracks cumulative spending per calendar day (UTC).
 * If the next payment would exceed the daily limit, the SDK blocks it.
 */

import type { BudgetStatus } from "../types";

function todayUTC(): string {
  return new Date().toISOString().slice(0, 10);
}

export class BudgetTracker {
  private dailyLimit: number;
  private spent: number = 0;
  private currentDay: string;

  constructor(dailyLimit: number) {
    this.dailyLimit = dailyLimit;
    this.currentDay = todayUTC();
  }

  private rotateIfNewDay(): void {
    const today = todayUTC();
    if (today !== this.currentDay) {
      this.spent = 0;
      this.currentDay = today;
    }
  }

  check(amountUsd: number): BudgetStatus {
    this.rotateIfNewDay();
    const remaining = this.dailyLimit - this.spent;

    if (amountUsd > remaining) {
      return {
        allowed: false,
        dailyLimit: this.dailyLimit,
        spentToday: this.spent,
        remaining,
        requested: amountUsd,
        reason:
          `[DoorNo.402] BLOCKED -- daily budget exceeded: ` +
          `spent $${this.spent.toFixed(2)} / $${this.dailyLimit.toFixed(2)}, ` +
          `remaining $${remaining.toFixed(2)}, ` +
          `requested $${amountUsd.toFixed(2)}`,
      };
    }

    return {
      allowed: true,
      dailyLimit: this.dailyLimit,
      spentToday: this.spent,
      remaining,
      requested: amountUsd,
      reason: "within budget",
    };
  }

  record(amountUsd: number): void {
    this.rotateIfNewDay();
    this.spent += amountUsd;
  }

  getSpentToday(): number {
    this.rotateIfNewDay();
    return this.spent;
  }

  getRemaining(): number {
    this.rotateIfNewDay();
    return this.dailyLimit - this.spent;
  }
}
