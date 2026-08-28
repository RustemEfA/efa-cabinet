// Клиент ЮKassa (yookassa.ru) — создание платежа и проверка его статуса.
// shopId/secretKey берутся из ЛК ЮKassa: Настройки -> API ключи.
const API_BASE = "https://api.yookassa.ru/v3";

function authHeader() {
  const shopId = process.env.YOOKASSA_SHOP_ID;
  const secretKey = process.env.YOOKASSA_SECRET_KEY;
  if (!shopId || !secretKey) {
    throw new Error("ЮKassa не настроена: нет YOOKASSA_SHOP_ID / YOOKASSA_SECRET_KEY");
  }
  return "Basic " + Buffer.from(`${shopId}:${secretKey}`).toString("base64");
}

export type YookassaPayment = {
  id: string;
  status: string;
  metadata?: Record<string, string>;
  amount?: { value: string; currency: string };
  confirmation?: { confirmation_url?: string };
};

// Создаёт платёж с редиректом на страницу оплаты ЮKassa.
// idempotenceKey должен быть уникален для КАЖДОЙ попытки оплаты (не для
// заказа целиком) — иначе повторный клик "Оплатить" после отменённого
// платежа вернёт тот же (уже нерабочий) платёж вместо нового.
export async function createYookassaPayment(params: {
  amount: number;
  description: string;
  returnUrl: string;
  metadata: Record<string, string>;
  idempotenceKey: string;
}): Promise<YookassaPayment> {
  const res = await fetch(`${API_BASE}/payments`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": authHeader(),
      "Idempotence-Key": params.idempotenceKey
    },
    body: JSON.stringify({
      amount: { value: params.amount.toFixed(2), currency: "RUB" },
      capture: true,
      confirmation: { type: "redirect", return_url: params.returnUrl },
      description: params.description,
      metadata: params.metadata
    })
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`ЮKassa: не удалось создать платёж (${res.status}): ${text}`);
  }

  return res.json();
}

// Перепроверяет статус платежа напрямую в ЮKassa по его id — уведомление
// (вебхук) не подписано криптографически, поэтому телу не доверяем и
// всегда сверяемся с API своим секретным ключом перед тем, как отметить
// заказ оплаченным.
export async function fetchYookassaPayment(paymentId: string): Promise<YookassaPayment> {
  const res = await fetch(`${API_BASE}/payments/${paymentId}`, {
    headers: { "Authorization": authHeader() }
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`ЮKassa: не удалось получить платёж ${paymentId} (${res.status}): ${text}`);
  }

  return res.json();
}
