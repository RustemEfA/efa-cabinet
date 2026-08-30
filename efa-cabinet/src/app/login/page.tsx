import Link from "next/link";
import { signIn } from "./actions";
import { SubmitButton } from "./submit-button";

export default function LoginPage({
  searchParams
}: {
  searchParams: { error?: string; next?: string };
}) {
  return (
    <div className="auth-wrap">
      <p className="eyebrow">Эффективная Автоматизация</p>
      <h1>Вход в личный кабинет</h1>
      <p className="lead">Загрузите регламенты, получите ссылку на опрос сотрудников и скачайте готовую бизнес-архитектуру.</p>

      <form action={signIn}>
        <input type="hidden" name="next" value={searchParams.next || "/dashboard"} />
        <label htmlFor="email">Email</label>
        <input type="email" id="email" name="email" required autoComplete="email" />

        <label htmlFor="password">Пароль</label>
        <input type="password" id="password" name="password" required autoComplete="current-password" />

        {searchParams.error ? <p className="error">{searchParams.error}</p> : null}

        <SubmitButton>Войти</SubmitButton>
      </form>

      <p className="hint">
        Нет аккаунта? <Link href="/register">Зарегистрироваться</Link>
      </p>
    </div>
  );
}
