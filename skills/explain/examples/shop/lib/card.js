// A quick check that a card number could be real (the Luhn check). It never charges anything.
export function cardLooksValid(card) {
  const digits = String(card?.number ?? "").replace(/\D/g, "");
  if (digits.length < 12) return false;
  let sum = 0;
  for (let i = 0; i < digits.length; i++) {
    let d = Number(digits[digits.length - 1 - i]);
    if (i % 2 === 1) d = d * 2 > 9 ? d * 2 - 9 : d * 2;
    sum += d;
  }
  return sum % 10 === 0;
}
