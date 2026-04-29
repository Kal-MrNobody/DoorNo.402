import { writeFileSync, appendFileSync } from "fs";
import { validatePrice, ValidationResult } from "./validators/price";

export { extractPrice, validatePrice, ValidationResult } from "./validators/price";

export class PaymentBlockedError extends Error {
  constructor(public result: ValidationResult) {
    super(result.reason);
    this.name = "PaymentBlockedError";
  }
}
