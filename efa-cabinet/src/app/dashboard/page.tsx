import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { createProject } from "./actions";
import { statusLabel } from "@/lib/statusLabels";

const ROADMAP_STEPS = [
  { num: "0", label: "Создать проект" },
  { num: "1", label: "SWOT-анализ" },
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
                                  <div className="dot">{s.num}</div>div>
                                  <div className="rlabel">{s.label}</div>div>
                      </div>div>
                    ))}
                </div>div>
          </div>div>
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
                <p className="eyebrow">Личный кабинет EfA</p>p>
                <h1>Приветствую Вас в личном кабинете на платформе EfA!</h1>h1>
          
                <div className="author-line">
                        <div className="author-avatar">
                                  <img
                                                src="https://static.tildacdn.com/tild3664-3765-4261-b035-626632353436/rustem_avatar.jpg"
                                                alt="Рустем Мухамадиев"
                                              />
                        </div>div>
                        <p>
                                  Я - <b>Рустем Мухамадиев</b>b>, основатель платформы.
                        </p>p>
                </div>div>
          
                <p className="lead">
                        На этой платформе я помогу Вам провести глубокую диагностику Вашего бизнеса,
                        разработать и внедрить эффективные решения для развития и роста прибыли.
                </p>p>
                <p className="lead">
                        Далее — дорожная карта: что Вас здесь ждёт и какие Вы получите результаты.
                </p>p>
          
                <p className="roadmap-title first">Дорожная карта</p>p>
                <Roadmap active={0} />
          
                <div className="step-card" style={{ marginTop: 24 }}>
                        <div className="step-head">
                                  <div className="step-num">0</div>div>
                                  <h2>Создайте проект</h2>h2>
                        </div>
                        <p>Внутри проекта — работа с одной организацией, одним бизнесом.</p>p>
                        <form action={createProject}>
                                  <label htmlFor="title-0">Название проекта</label>label>
                                  <input type="text" id="title-0" name="title" placeholder="Например: ООО «Ромашка»" required />
                                  <button className="btn" type="submit">Создать проект</button>button>
                        </form>form>
                </div>div>
          
                <p className="roadmap-title">Дорожная карта</p>p>
                <Roadmap active={1} />
          
                <div className="step-card">
                        <div className="step-head">
                                  <div className="step-num">1</div>div>
                                  <h2>Узнайте сильные и слабые стороны своего бизнеса</h2>h2>
                        </div>div>
                        <p>
                                  Получите SWOT-анализ, который расскажет, как выглядит ваш бизнес среди 1000
                                  конкурентов и 1000 клиентов. Какие есть возможности и угрозы.
                        </p>p>
                        <p>Это анализ связки: Продукт — Клиент — Конкурент.</p>p>
                        <p>
                                  <b style={{ color: "var(--white)" }}>Результат:</b>b> отчёт о том, как потенциальные
                                  клиенты и инвесторы видят вашу компанию, как они принимают решения в вашу пользу
                                  прежде чем прийти к вам.
                        </p>p>
                        <p>
                                  ИИ-агент «Бизнес-архитектор» возьмёт данные о вашей компании, оценит сегмент рынка,
                                  проанализирует ваши продукты и продукты 1000 конкурентов, сравнит позиционирование
                                  и рейтинги, проанализирует возможную клиентскую базу из 1000 потенциальных клиентов —
                                  и на основе полученных данных сформирует отчёт.
                        </p>p>
                        <p style={{ fontSize: 13, color: "var(--muted-2)", marginTop: 14 }}>
                                  Вы оцените полученный результат, и если примете решение о дальнейшей глубокой
                                  проработке — переходим к шагу №2.
                        </p>p>
                        <div className="step-meta">
                                  <span className="pill">
                                              <b>Стоимость:</b>b>&nbsp;1 000 ₽
                                  </span>span>
                                  <span className="pill muted">
                                              <b>Длительность:</b>b>&nbsp;2–3 дня
                                  </span>span>
                        </div>div>
                </div>div>
          
                <p className="roadmap-title">Дорожная карта</p>p>
                <Roadmap active={2} />
          
                <div className="step-card">
                        <div className="step-head">
                                  <div className="step-num">2</div>div>
                                  <h2>Проведение интервью</h2>h2>
                        </div>div>
                        <p>
                                  Чтобы предложить вам эффективные решения, необходимо провести глубокую диагностику
                                  внутренней и внешней среды организации. Для этого нужно собрать данные, а носители
                                  ценнейшей и уникальной информации — это сотрудники организации.
                        </p>p>
                        <p>
                                  Мы проведём интервьюирование сотрудников. На основании этих данных сформируем
                                  бизнес-архитектуру, разработаем и предложим вам решения. Для формирования опроса мне
                                  понадобится штатное расписание организации.
                        </p>p>
                        <p>
                                  На этом этапе мы знакомимся лично, подписываем NDA, заключаем договор. Получаем от вас
                                  штатное расписание — в ответ пришлём табличку со ссылками для каждого сотрудника, где
                                  они пройдут автоматизированное интервью.
                        </p>p>
                        <p>
                                  Вы, как владелец, получите общую таблицу. Она будет содержать все вопросы, которые
                                  будут заданы сотрудникам, и впоследствии — все ответы на эти вопросы.
                        </p>p>
                        <ul>
                                  <li>На одного сотрудника приходится примерно 60–100 вопросов</li>li>
                                  <li>Интервью сотрудники проходят в комфортное для себя, свободное от работы время</li>li>
                        </ul>ul>
                        <div className="step-meta">
                                  <span className="pill">
                                              <b>Стоимость:</b>b>&nbsp;10 000 ₽ — независимо от количества сотрудников
                                  </span>span>
                                  <span className="pill muted">
                                              <b>Длительность:</b>b>&nbsp;~1 неделя
                                  </span>span>
                        </div>div>
                </div>div>
          
                <p className="roadmap-title">Дорожная карта</p>p>
                <Roadmap active={3} />
          
                <div className="step-card">
                        <div className="step-head">
                                  <div className="step-num">3</div>div>
                                  <h2>Бизнес-моделирование</h2>h2>
                        </div>div>
                        <p>
                                  На основании полученных ответов сотрудников и, возможно, предоставленных вами
                                  актуальных регламентов организации, ИИ-агент «Бизнес-архитектор» сформирует
                                  бизнес-архитектуру вашей организации «как есть». Образец бизнес-архитектуры вы видели
                                  на сайте, на главной странице.
                        </p>p>
                        <p style={{ color: "var(--white)", fontWeight: 700, marginBottom: 8 }}>
                                  Результат бизнес-архитектуры:
                        </p>p>
                        <ul>
                                  <li>
                                              Полная и актуальная база знаний «как есть» с должностными инструкциями и
                                              регламентами всех бизнес-процессов организации. Содержит 12 разделов, указанных в
                                              демо-версии.
                                  </li>li>
                                  <li>
                                              Аналитический отчёт, концепция решений для развития и концепция решений для
                                              автоматизации бизнес-процессов с помощью ИИ-агентов.
                                  </li>li>
                        </ul>ul>
                        <p>
                                  После того как вы утвердите концепцию решений, ИИ-агент «Бизнес-архитектор»
                                  сформирует бизнес-архитектуру «как должно быть» и дорожную карту внедрения решений.
                        </p>p>
                        <div className="step-meta">
                                  <span className="pill">
                                              <b>Стоимость «как есть»:</b>b>&nbsp;100 000 ₽
                                  </span>span>
                                  <span className="pill">
                                              <b>Стоимость «как должно быть»:</b>b>&nbsp;500 000 ₽
                                  </span>span>
                                  <span className="pill muted">
                                              <b>Длительность:</b>b>&nbsp;1–2 недели
                                  </span>span>
                        </div>div>
                </div>div>
          
                <p className="roadmap-title">Дорожная карта</p>p>
                <Roadmap active={4} />
          
                <div className="step-card" style={{ marginBottom: 0 }}>
                        <div className="step-head">
                                  <div className="step-num">4</div>div>
                                  <h2>Разработка и внедрение ИИ-агентов</h2>h2>
                        </div>div>
                        <p>Согласно утверждённой дорожной карте разрабатываем и внедряем ИИ-агентов.</p>p>
                        <div className="step-meta">
                                  <span className="pill muted">Стоимость и сроки — индивидуально</span>span>
                        </div>div>
                </div>div>
          
                <div className="cta-heading">
                        <div className="big">ИТАК, ПОГНАЛИ!</div>div>
                        <div className="small">Создаём проект!</div>div>
                </div>div>
          
                <div className="step-card">
                        <div className="step-head">
                                  <div className="step-num">0</div>div>
                                  <h2>Создайте проект</h2>h2>
                        </div>div>
                        <p>Внутри проекта — работа с одной организацией, одним бизнесом.</p>p>
                        <form action={createProject}>
                                  <label htmlFor="title-cta">Название проекта</label>label>
                                  <input type="text" id="title-cta" name="title" placeholder="Например: ООО «Ромашка»" required />
                                  <button className="btn" type="submit">Создать проект</button>button>
                        </form>form>
                </div>div>
          
                <p className="eyebrow" style={{ marginTop: 56 }}>Ваши проекты</p>p>
          
            {!projects || projects.length === 0 ? (
                    <p className="empty">Проектов пока нет — создайте первый выше.</p>p>
                  ) : (
                    projects.map((p) => (
                                <Link key={p.id} href={`/dashboard/${p.id}`} style={{ textDecoration: "none", color: "inherit" }}>
                                            <div className="card">
                                                          <div className="card-row">
                                                                          <div>
                                                                                            <p className="card-title">{p.title}</p>p>
                                                                                            <span className={`badge ${p.status}`}>{statusLabel(p.status)}</span>span>
                                                                          </div>div>
                                                                          <span style={{ color: "var(--muted-2)", fontSize: 13 }}>→</span>span>
                                                          </div>div>
                                            </div>div>
                                </Link>Link>
                              ))
                  )}
          </>>
        );
}
</></div>
