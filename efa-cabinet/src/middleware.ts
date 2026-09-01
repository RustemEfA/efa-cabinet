// Middleware защищает /dashboard/* от неавторизованного доступа и обновляет
// (refresh) сессию Supabase на каждом запросе, чтобы токен не протухал.
//
// getUser() ходит в Supabase Auth по сети — если Supabase отвечает медленно
// (например, во время деградации их API Gateway), запрос без таймаута висит
// бесконечно и вся навигация в /dashboard/* "зависает" для пользователя.
// Поэтому оборачиваем вызов в таймаут: если Supabase не ответил за отведённое
// время, считаем сессию неподтверждённой и отправляем на /login с понятной
// причиной, вместо вечного ожидания.
import { createServerClient, type CookieOptions } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

const AUTH_CHECK_TIMEOUT_MS = 8000;

export async function middleware(request: NextRequest) {
  let response = NextResponse.next({ request: { headers: request.headers } });

  const isDashboard = request.nextUrl.pathname.startsWith("/dashboard");

  if (!isDashboard) {
    return response;
  }

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        get(name: string) {
          return request.cookies.get(name)?.value;
        },
        set(name: string, value: string, options: CookieOptions) {
          response = NextResponse.next({ request: { headers: request.headers } });
          response.cookies.set({ name, value, ...options });
        },
        remove(name: string, options: CookieOptions) {
          response = NextResponse.next({ request: { headers: request.headers } });
          response.cookies.set({ name, value: "", ...options });
        }
      }
    }
  );

  let user = null;
  let timedOut = false;

  try {
    const result = await Promise.race([
      supabase.auth.getUser(),
      new Promise<never>((_, reject) =>
        setTimeout(() => reject(new Error("TIMEOUT")), AUTH_CHECK_TIMEOUT_MS)
      )
    ]);
    user = result.data.user;
  } catch (e) {
    timedOut = true;
  }

  if (timedOut) {
        const redirectUrl = new URL("/login", process.env.NEXT_PUBLIC_SITE_URL ?? "https://app.ef-a.ru");
    redirectUrl.searchParams.set("next", request.nextUrl.pathname);
    redirectUrl.searchParams.set(
      "error",
      "Сервис входа сейчас отвечает медленнее обычного (сбой у поставщика авторизации Supabase). Попробуйте ещё раз через минуту."
    );
    return NextResponse.redirect(redirectUrl);
  }

  if (!user) {
        const redirectUrl = new URL("/login", process.env.NEXT_PUBLIC_SITE_URL ?? "https://app.ef-a.ru");
    redirectUrl.searchParams.set("next", request.nextUrl.pathname);
    return NextResponse.redirect(redirectUrl);
  }

  return response;
}

export const config = {
  matcher: ["/dashboard/:path*"]
};
