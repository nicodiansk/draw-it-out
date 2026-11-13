// The database: carts in, orders out.
import { sql } from "./sql.js";

export async function loadCart(id) {
  return sql`select * from carts where id = ${id}`.first();
}

export async function saveOrder(cart, last4) {
  const [order] = await sql`
    insert into orders (cart_id, total, card_last4)
    values (${cart.id}, ${cart.total}, ${last4})
    returning id, total`;
  return order;
}
