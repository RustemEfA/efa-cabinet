import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { linkPartnerAccount } from "@/lib/linkPartner";

// Supabase redirects the user here after they click the email confirmation link.
export async function GET(request: Request) {
        const { searchParams } = new URL(request.url);
        const origin = process.env.NEXT_PUBLIC_SITE_URL ?? "https://app.ef-a.ru";
        const code = searchParams.get("code");

  if (code) {
        const supabase = createClient();
        const { data } = await supabase.auth.exchangeCodeForSession(code);
        if (data.user) {
                await linkPartnerAccount(data.user.id, data.user.email);
        }
  }

  return NextResponse.redirect(`${origin}/dashboard`);
}
