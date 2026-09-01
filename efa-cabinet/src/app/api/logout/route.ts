import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

export async function POST(request: Request) {
  const supabase = createClient();
  await supabase.auth.signOut();
    const origin = process.env.NEXT_PUBLIC_SITE_URL ?? "https://app.ef-a.ru";
    return NextResponse.redirect(new URL("/login", origin));
}
