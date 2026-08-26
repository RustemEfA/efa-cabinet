import Link from "next/link";
import { signUp } from "./actions";

export default function RegisterPage({
  searchParams
}: {
  searchParams: { error?: string };
}) {
  return (
    <div className="auth-wrap">
      <p className="eyebrow">Эффективная Автоматизация</p>
      <h1>Регистрация</h1>
      <p className="lead">Заведите аккаунт, чтобы начать проект: загрузить регламенты и получить ссылку на опрос сотрудников.</p>

      <form action={signUp}>
        <label htmlFor="company_name">Компания</label>
        <input type="text" id="company_name" name="company_name" required />

        <label htmlFor="contact_name">Контактное лицо</label>
        <input type="text" id="contact_name" name="contact_name" required />

        <label htmlFor="email">Email</label>
        <input type="email" id="email" name="email" required autoComplete="email" />

        <label htmlFor="password">Пароль</label>
        <input type="password" id="password" name="password" required minLength={6} autoComplete="new-password" />

        {searchParams.error ? <p className="error">{searchParams.error}</p> : null}

        <button className="btn" type="submit">Зарегистрироваться</button>
      </form>

      <p className="hint">
        Уже есть аккаунт? <Link href="/login">Войти</Link>
      </p>
    </div>
  );
}
