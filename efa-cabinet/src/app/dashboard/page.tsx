import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { createProject } from "./actions";
import { statusLabel } from "@/lib/statusLabels";

const ROADMAP_STEPS = [
  { num: "0", label: "Создать проект" },
  { num: "1", label: "Скан репутации" },
  { num: "2", label: "Интервью сотрудников" },
  { num: "3", label: "Бизнес-архитектура" },
  { num: "4", label: "Внедрение ИИ-агентов" },
];

function Roadmap({ active }: { active: number }) {
  return (
    <div className="roadmap">
      <div className="roadmap-line" />
      <div className="roadmap-steps">
        {ROADMAP_STEPS.map((s, i) => (
          <div key={s.num} className={`rstep${i === active ? " active" : ""}`}>
            <div className="dot">{s.num}</div>
            <div className="rlabel">{s.label}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default async function DashboardPage() {
  const supabase = createClient();

  const { data: projects } = await supabase
    .from("projects")
    .select("id, title, status, created_at")
    .order("created_at", { ascending: false });

  return (
    <>
      <p className="eyebrow">Личный кабинет EfA</p>
      <h1>Приветствую Вас в личном кабинете на платформе EfA!</h1>

      <div className="author-line">
        <div className="author-avatar">
          <img
            src="https://static.tildacdn.com/tild3664-3765-4261-b035-626632353436/rustem_avatar.jpg"
            alt="Рустем Мухамадиев"
          />
        </div>
        <p>
          Я - <b>Рустем Мухамадиев</b>, основатель платформы.
        </p>
      </div>

      <p className="lead">
        На этой платформе я помогу Вам провести глубокую диагностику Вашего бизнеса,
        разработать и внедрить эффективные решения для развития и роста прибыли.
      </p>
      <p className="lead">
        Далее — дорожная карта: что Вас здесь ждёт и какие Вы получите результаты.
      </p>

      <p className="roadmap-title first">Дорожная карта</p>
      <Roadmap active={0} />

      <div className="step-card" style={{ marginTop: 24 }}>
        <div className="step-head">
          <div className="step-num">0</div>
          <h2>Создайте проект</h2>
        </div>
        <p>Внутри проекта — работа с одной организацией, одним бизнесом.</p>
        <form action={createProject}>
          <label htmlFor="title-0">Название проекта</label>
          <input type="text" id="title-0" name="title" placeholder="Например: ООО «Ромашка»" required />
          <button className="btn" type="submit">Создать проект</button>
        </form>
      </div>

      <p className="roadmap-title">Дорожная карта</p>
      <Roadmap active={1} />

      <div className="step-card">
        <div className="step-head">
          <div className="step-num">1</div>
          <h2>Узнайте, как вас видят клиенты, конкуренты и поисковики</h2>
        </div>
        <p>
          Экспресс-скан репутации и цифрового следа: соберём объективную картину того,
          как ваша компания выглядит со стороны — по открытым и официальным источникам,
          без вашего участия.
        </p>
        <p>
          Мы проверим: юридический профиль (ЕГРЮЛ, ФССП, арбитраж), сайт и его видимость
          в поиске, рейтинг и отзывы на картах в сравнении с 2–3 ближайшими конкурентами,
          активность в соцсетях.
        </p>
        <p style={{ fontSize: 13, color: "var(--muted-2)", marginTop: 14 }}>
          Результат — короткий отчёт с конкретными цифрами и честными выводами, без общих
          фраз. Сейчас каждый отчёт проверяется вручную перед отправкой, поэтому срок —
          до 2 дней; в дальнейшем будем делать быстрее.
        </p>
        <div className="step-meta">
          <span className="pill">
            <b>Стоимость:</b>&nbsp;990 ₽
          </span>
          <span className="pill muted">
            <b>Длительность:</b>&nbsp;до 2 дней
          </span>
        </div>
      </div>

      <p className="roadmap-title">Дорожная карта</p>
      <Roadmap active={2} />

      <div className="step-card">
        <div className="step-head">
          <div className="step-num">2</div>
          <h2>Проведение интервью</h2>
        </div>
        <p>
          Чтобы предложить вам эффективные решения, необходимо провести глубокую диагностику
          внутренней и внешней среды организации. Для этого нужно собрать данные, а носители
          ценнейшей и уникальной информации — это сотрудники организации.
        </p>
        <p>
          Мы проведём интервьюирование сотрудников. На основании этих данных сформируем
          бизнес-архитектуру, разработаем и предложим вам решения. Для формирования опроса мне
          понадобится штатное расписание организации.
        </p>
        <p>
          На этом этапе мы знакомимся лично, подписываем NDA, заключаем договор. Получаем от вас
          штатное расписание — в ответ пришлём табличку со ссылками для каждого сотрудника, где
          они пройдут автоматизированное интервью.
        </p>
        <p>
          Вы, как владелец, получите общую таблицу. Она будет содержать все вопросы, которые
          будут заданы сотрудникам, и впоследствии — все ответы на эти вопросы.
        </p>
        <ul>
          <li>На одного сотрудника приходится примерно 60–100 вопросов</li>
          <li>Интервью сотрудники проходят в комфортное для себя, свободное от работы время</li>
        </ul>
        <div className="step-meta">
          <span className="pill">
            <b>Стоимость:</b>&nbsp;10 000 ₽ — независимо от количества сотрудников
          </span>
          <span className="pill muted">
            <b>Длительность:</b>&nbsp;~1 неделя
          </span>
        </div>
      </div>

      <p className="roadmap-title">Дорожная карта</p>
      <Roadmap active={3} />

      <div className="step-card">
        <div className="step-head">
          <div className="step-num">3</div>
          <h2>Бизнес-моделирование</h2>
        </div>
        <p>
          На основании полученных ответов сотрудников и, возможно, предоставленных вами
          актуальных регламентов организации, ИИ-агент «Бизнес-архитектор» сформирует
          бизнес-архитектуру вашей организации «как есть». Образец бизнес-архитектуры вы видели
          на сайте, на главной странице.
        </p>
        <p style={{ color: "var(--white)", fontWeight: 700, marginBottom: 8 }}>
          Результат бизнес-архитектуры:
        </p>
        <ul>
          <li>
            Полная и актуальная база знаний «как есть» с должностными инструкциями и
            регламентами всех бизнес-процессов организации. Содержит 12 разделов, указанных в
            демо-версии.
          </li>
          <li>
            Аналитический отчёт, концепция решений для развития и концепция решений для
            автоматизации бизнес-процессов с помощью ИИ-агентов.
          </li>
        </ul>
        <p>
          После того как вы утвердите концепцию решений, ИИ-агент «Бизнес-архитектор»
          сформирует бизнес-архитектуру «как должно быть» и дорожную карту внедрения решений.
        </p>
        <div className="step-meta">
          <span className="pill">
            <b>Стоимость «как есть»:</b>&nbsp;100 000 ₽
          </span>
          <span className="pill">
            <b>Стоимость «как должно быть»:</b>&nbsp;500 000 ₽
          </span>
          <span className="pill muted">
            <b>Длительность:</b>&nbsp;1–2 недели
          </span>
        </div>
      </div>

      <p className="roadmap-title">Дорожная карта</p>
      <Roadmap active={4} />

      <div className="step-card" style={{ marginBottom: 0 }}>
        <div className="step-head">
          <div className="step-num">4</div>
          <h2>Разработка и внедрение ИИ-агентов</h2>
        </div>
        <p>Согласно утверждённой дорожной карте разрабатываем и внедряем ИИ-агентов.</p>
        <div className="step-meta">
          <span className="pill muted">Стоимость и сроки — индивидуально</span>
        </div>
      </div>

      <div className="cta-heading">
        <div className="big">ИТАК, ПОГНАЛИ!</div>
        <div className="small">Создаём проект!</div>
      </div>

      <div className="step-card">
        <div className="step-head">
          <div className="step-num">0</div>
          <h2>Создайте проект</h2>
        </div>
        <p>Внутри проекта — работа с одной организацией, одним бизнесом.</p>
        <form action={createProject}>
          <label htmlFor="title-cta">Название проекта</label>
          <input type="text" id="title-cta" name="title" placeholder="Например: ООО «Ромашка»" required />
          <button className="btn" type="submit">Создать проект</button>
        </form>
      </div>

      <p id="projects" className="eyebrow" style={{ marginTop: 56, scrollMarginTop: 24 }}>Ваши проекты</p>

      {!projects || projects.length === 0 ? (
        <p className="empty">Проектов пока нет — создайте первый выше.</p>
      ) : (
        projects.map((p) => (
          <Link key={p.id} href={`/dashboard/${p.id}`} style={{ textDecoration: "none", color: "inherit" }}>
            <div className="card">
              <div className="card-row">
                <div>
                  <p className="card-title">{p.title}</p>
                  <span className={`badge ${p.status}`}>{statusLabel(p.status)}</span>
                </div>
                <span style={{ color: "var(--teal)", fontSize: 14, fontWeight: 700, display: "flex", alignItems: "center", gap: 6, whiteSpace: "nowrap" }}>
                  Войти в проект <span style={{ fontSize: 18 }}>→</span>
                </span>
              </div>
            </div>
          </Link>
        ))
      )}
    </>
  );
}
