import { validatePrice } from "./validators/price";
import { PaymentBlockedError } from "./index";

export interface McpClient {
  execute: (request: unknown) => Promise<unknown>;
}
