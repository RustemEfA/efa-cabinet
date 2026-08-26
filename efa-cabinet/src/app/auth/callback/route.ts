import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

// Supabase шлёт сюда пользователя после клика по ссылке подтверждения email.
export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");

  if (code) {
    const supabase = createClient();
    await supabase.auth.exchangeCodeForSession(code);
  }

  return NextResponse.redirect(`${origin}/dashboard`);
}
