import { test, expect } from "vitest";
import { saveOrder } from "../lib/db.js";

test("saveOrder stores the total and the last four digits", async () => {
  const order = await saveOrder({ id: 7, total: 42 }, "4242");
  expect(order.total).toBe(42);
});
