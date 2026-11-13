// POST /api/pay: checks the cart and the card, saves the order, writes a thank-you note.
import { loadCart, saveOrder } from "../lib/db.js";
import { cardLooksValid } from "../lib/card.js";
import { ai } from "../lib/ai.js";

export async function POST(req) {
  const { cartId, card } = await req.json();
  const cart = await loadCart(cartId);
  if (!cart || cart.items.length === 0) {
    return Response.json({ error: "Your cart is empty." }, { status: 400 });
  }
  if (!cardLooksValid(card)) {
    return Response.json({ error: "That card number doesn't look right." }, { status: 402 });
  }
  const order = await saveOrder(cart, card.last4);
  const note = await ai.write(`A two-line thank-you note for an order of ${cart.items.length} items.`);
  return Response.json({ order, note });
}
