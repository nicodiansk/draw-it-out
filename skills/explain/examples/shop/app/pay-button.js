// The Pay button on the checkout page.
import { showOrder, showError } from "./screens.js";

export function PayButton({ cart }) {
  async function onClick() {
    const res = await fetch("/api/pay", {
      method: "POST",
      body: JSON.stringify({ cartId: cart.id, card: cart.card }),
    });
    const body = await res.json();
    if (!res.ok) return showError(body.error);
    showOrder(body.order, body.note);
  }
  return `<button onclick="${onClick}">Pay ${cart.total}</button>`;
}
