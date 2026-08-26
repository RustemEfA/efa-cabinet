export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <div className="topbar">
        <div className="brand">EfA<span>.</span> Личный кабинет</div>
        <form action="/api/logout" method="post">
          <button className="btn secondary" type="submit" style={{ marginTop: 0 }}>
            Выйти
          </button>
        </form>
      </div>
      <div className="wrap">{children}</div>
    </>
  );
}
