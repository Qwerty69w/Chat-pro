const ADMIN_KEY = "minigram_admin_key";
const root = document.querySelector("#admin");
let adminKey = localStorage.getItem(ADMIN_KEY) || "";
let state = null;
let adminSection = "public-legal";
const ACTIVITY_METRICS = [
  ["stars_balance", "Звёзд на текущем балансе"], ["direct_chats", "Личных диалогов"],
  ["channels_joined", "Подписок на чужие каналы"], ["channel_subscriptions", "Подписок на каналы"], ["communities_joined", "Бесед"],
  ["channels_created", "Созданных каналов"], ["communities_created", "Созданных бесед"],
  ["channel_subscribers", "Подписчиков в одном своём канале"], ["community_subscribers", "Участников в одной своей беседе"],
  ["messages", "Отправленных сообщений"],
  ["posts", "Публикаций в профиле"], ["channel_comments_written", "Комментариев к постам в каналах"], ["stories", "Сторис"], ["reviews", "Отзывов"],
  ["donations_sent", "Отправленных донатов"], ["stars_donated", "Звёзд, отправленных в донатах за текущий месяц"],
  ["donations_received", "Полученных донатов"], ["login_streak", "Дней подряд в приложении"],
  ["completed_calls", "Принятых звонков"], ["call_partners", "Уникальных собеседников в принятых звонках"],
  ["chat_pro_review_video", "Ролик или пост о Chat-Pro в своём канале"],
];
const LEVEL_CRITERIA = ACTIVITY_METRICS;
const LEVEL_LIMITS = [
  ["maxStars", "Максимум звёзд на балансе"], ["messagesPerDay", "Сообщений в сутки"], ["postsPerDay", "Публикаций в сутки (профиль и каналы)"],
  ["storiesPerDay", "Сторис в день"], ["storiesPerMonth", "Сторис в месяц"],
  ["communitiesJoined", "Участий в беседах"], ["communitiesCreated", "Созданных бесед"],
  ["channelsJoined", "Подписок на каналы"], ["channelsCreated", "Созданных каналов"],
  ["savedAccounts", "Сохранённых аккаунтов"], ["autopostSourcesTotal", "Всех источников автопостинга"],
  ["autopostSourcesPerChannel", "Источников автопостинга на канал"],
];
let accountLevelsDraft = [];
let selectedAdminUserId = "";

start();

async function start() {
  if (!adminKey) {
    renderLogin();
    hidePageLoader();
    return;
  }
  try { await load(); renderAdmin(); }
  catch {
    localStorage.removeItem(ADMIN_KEY);
    adminKey = "";
    renderLogin();
  }
  hidePageLoader();
}

function hidePageLoader() { document.querySelector("#pageLoader")?.classList.add("page-loader--hidden"); }

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", "X-Admin-Key": adminKey, ...(options.headers || {}) },
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  const data = await response.json();
  if (!response.ok || data.ok === false) throw new Error(data.error || "Ошибка запроса");
  return data;
}

async function load() { state = await api("/api/admin/bootstrap"); }

function renderLogin() {
  root.innerHTML = `
    <main class="admin-login"><section class="admin-login__card">
      <div class="brand"><img class="brand-logo" src="icon.svg" width="64" height="64" alt="Логотип Chat-Pro"><div><h1>Админка Chat-Pro</h1><p>Введите ключ администратора, настроенный на сервере.</p></div></div>
      <form class="form" id="login"><label>Admin key<input name="key" required value="${esc(adminKey)}"></label><button class="button primary">Войти</button></form>
      <p class="muted">Ключ сохраняется в этом браузере только после успешного входа.</p>
    </section></main>`;
  root.querySelector("#login").addEventListener("submit", async (event) => {
    event.preventDefault();
    adminKey = String(new FormData(event.currentTarget).get("key") || "").trim();
    try {
      await load();
      localStorage.setItem(ADMIN_KEY, adminKey);
      renderAdmin();
    } catch (error) { toast(error.message === "Нет доступа." ? "Неверный ключ администратора." : error.message, true); }
  });
}

function renderAdmin() {
  accountLevelsDraft = cloneLevels(state.settings.account_levels || []);
  const sections = [
    ["star-packages", "Тарифы звёзд"], ["public-legal", "Реквизиты и условия"], ["users", "Пользователи"], ["boost", "Счётчики"],
    ["channel-money", "Комиссии и выплаты"], ["recommended", "Рекомендации"], ["automated-comments", "Автокомментарии"], ["activity-rewards", "Награды"],
    ["reports", "Обращения"], ["account-levels", "Уровни аккаунта"], ["settings", "Настройки"],
  ];
  const cards = {
    "star-packages": starPackagesCard, "public-legal": publicLegalCard, users: usersCard, boost: boostCard, "channel-money": channelMoneyCard, recommended: recommendedCard,
    "automated-comments": automatedCommentsCard, "activity-rewards": activityRewardsCard,
    reports: reportsCard, "account-levels": accountLevelsCard, settings: settingsCard,
  };
  root.innerHTML = `
    <main class="admin-shell">
      <header class="admin-head"><div><h1>Админка Chat-Pro</h1><p class="muted">Управление тарифами, пользователями, наградами за активность и счётчиками</p></div><button class="button" id="reload">Обновить</button></header>
      <nav class="admin-sections" aria-label="Разделы админки">${sections.map(([id, title]) => `<button type="button" class="admin-sections__button${id === adminSection ? " active" : ""}" data-admin-section="${id}">${title}</button>`).join("")}</nav>
      <section class="admin-grid">${cards[adminSection]()}</section>
    </main>`;
  bindAdmin();
}

function usersCard() {
  const selected = state.users.find((user) => user.id === selectedAdminUserId) || state.users[0];
  selectedAdminUserId = selected?.id || "";
  const levels = state.settings.account_levels || [];
  return `<article class="admin-card"><h2>Пользователи</h2><p class="muted">Найдите пользователя и выберите его в списке: звёзды и уровень будут назначены выбранному аккаунту.</p><label>Поиск по имени или username<input type="search" data-user-search placeholder="Введите имя или username без @" autocomplete="off"></label><div class="admin-list" data-user-list>${state.users.map((u) => `<button type="button" class="row" data-user-row data-select-user="${esc(u.id)}" data-user-search-value="${esc(`${u.name} ${u.username}`.toLowerCase())}"><div class="avatar avatar-tone-${avatarTone(u)}">${esc(initials(u.name))}</div><div class="row__body"><div class="row__title">${esc(u.name)} @${esc(u.username)}</div><div class="row__sub">★ ${u.stars} · уровень: ${esc(u.accountLevel?.title || "Обычный")}${u.id === selectedAdminUserId ? " · выбран" : ""}</div></div></button>`).join("") || '<p class="muted">Нет пользователей.</p>'}<p class="muted" data-user-search-empty hidden>Пользователи не найдены.</p></div>
    <form class="form" id="starsForm"><h3>Выдать звёзды</h3>${userSelect(selectedAdminUserId)}<label>Количество звёзд<input name="amount" type="number" value="100"></label><button class="button primary">Начислить</button></form><form class="form" id="accountLevelGrantForm"><h3>Выдать уровень аккаунта</h3>${userSelect(selectedAdminUserId)}<label>Уровень<select name="levelId">${levels.map((level) => `<option value="${esc(level.id)}">${esc(level.title)}</option>`).join("")}</select></label><button class="button primary" ${levels.length ? "" : "disabled"}>Выдать уровень</button></form></article>`;
}

function boostCard() {
  const chats = state.chats.filter((chat) => ["community", "channel"].includes(chat.type));
  const messages = state.messages.filter((message) => message.mediaType !== "system");
  const regulator = { enabled: true, viewRatePercent: 35, reactionRatePercent: 4, weeklyUnsubscribePercent: 1, initialUnsubscribeMonths: 3, settledWeeklyUnsubscribePercent: .1, ...(state.settings.channel_activity_regulator || {}) };
  return `<article class="admin-card"><h2>Демо-накрутка счётчиков</h2><p class="muted">Работает только внутри локального приложения. Не влияет на реальные Telegram, VK или другие сервисы. Пример: 10 реакций в минуту 5 часов = 3000 всего.</p>
    <form class="form" id="channelActivityRegulatorForm"><h3>Регулятор активности каналов</h3><p class="muted">Работает для каждого канала, где есть подписчики, независимо от уровня аккаунта владельца. Просмотры и реакции формируются за первые сутки после публикации. Отписки уменьшают только добавленные счётчиком подписки, не исключая реальных пользователей.</p><label><input name="enabled" type="checkbox"${regulator.enabled ? " checked" : ""}> Включить регулятор</label><div class="activity-reward-form__criteria"><label>Средние просмотры поста, % от подписчиков<input name="viewRatePercent" type="number" min="0" max="100" step="0.1" value="${Number(regulator.viewRatePercent)}" required></label><label>Средние реакции, % от просмотров<input name="reactionRatePercent" type="number" min="0" max="100" step="0.1" value="${Number(regulator.reactionRatePercent)}" required></label><label>Отписки в неделю, %<input name="weeklyUnsubscribePercent" type="number" min="0" max="100" step="0.01" value="${Number(regulator.weeklyUnsubscribePercent)}" required></label><label>Период первых отписок, месяцев<input name="initialUnsubscribeMonths" type="number" min="0" max="120" step="1" value="${Number(regulator.initialUnsubscribeMonths)}" required></label><label>Отписки после периода, % в неделю<input name="settledWeeklyUnsubscribePercent" type="number" min="0" max="100" step="0.01" value="${Number(regulator.settledWeeklyUnsubscribePercent)}" required></label></div><button class="button primary">Сохранить регулятор</button></form>
    <form class="form" id="boostForm">
      <label>Цель<select name="targetType" data-boost-type><option value="chat">Беседа или канал</option><option value="message">Публикация или сообщение</option></select></label>
      <label>Показатель<select name="metric" data-boost-metric><option value="subscribers">подписчики</option></select></label>
      <label>Конкретная цель<select name="targetId" data-boost-target required>${chats.map((chat) => `<option value="${chat.id}">${esc(chat.title)} · ${chat.type === "channel" ? "канал" : "беседа"}</option>`).join("") || '<option value="">Нет подходящих чатов</option>'}</select></label>
      <label>В минуту<input name="amountPerMinute" type="number" min="1" max="10000" value="10" required></label>
      <label>Минут<input name="durationMinutes" type="number" min="1" max="10080" value="60" required></label>
      <button class="button primary" ${chats.length ? "" : "disabled"}>Создать задание</button>
    </form>
    <h3>Доступные чаты</h3><div class="admin-list">${chats.map((chat) => `<p><b>${esc(chat.title)}</b><br>${chat.type === "channel" ? "Канал" : chat.type === "community" ? "Беседа" : "Группа"} · подписчики ${chat.subscriberCount}</p>`).join("") || '<p class="muted">Групп, бесед и каналов нет.</p>'}</div>
    <h3>Доступные публикации</h3><div class="admin-list">${messages.map((message) => `<p>${esc(message.text.slice(0, 80) || "Публикация с медиа")} · просмотры ${message.views} · реакции ${message.reactionTotal}</p>`).join("") || '<p class="muted">Публикаций нет.</p>'}</div>
    ${demoActivityCard()}
  </article>`;
}

function demoActivityFields(item = {}, accountLevels = []) {
  const value = (name, fallback) => esc(item[name] ?? fallback);
  return `<label>Название<input name="title" required maxlength="80" value="${value("title", "")}" placeholder="Стартовый рост"></label><div class="activity-reward-form__criteria"><label>Подписчиков в день<input name="subscribersPerDay" type="number" min="0" max="1000000" value="${value("subscribers_per_day", 0)}"></label><label>Просмотров в день<input name="viewsPerDay" type="number" min="0" max="1000000" value="${value("views_per_day", 0)}"></label><label>Реакций в день<input name="reactionsPerDay" type="number" min="0" max="1000000" value="${value("reactions_per_day", 0)}"></label><label>Комментариев в день<input name="commentsPerDay" type="number" min="0" max="1000000" value="${value("comments_per_day", 0)}"></label><input name="postLimit" type="hidden" value="1"><p class="muted">Просмотры, реакции и комментарии равномерно распределяются по всем публикациям канала.</p><label data-duration-days-field>Работать, дней<input name="durationDays" type="number" min="1" max="3650" value="${value("duration_days", 7)}"></label><label>Плавное затухание, дней<input name="fadeDurationDays" type="number" min="1" max="365" value="${value("fade_duration_days", 30)}"></label><label>Нет публикаций, дней<input name="inactivityDays" type="number" min="1" max="365" value="${value("inactivity_days", 3)}"></label><label>Цена, звёзды<input name="priceStars" type="number" min="0" max="1000000" value="${value("price_stars", 0)}"></label><label>Автоматически для уровня аккаунта<select name="requiredAccountLevelId"><option value="">Не подключать автоматически</option>${accountLevels.map((level) => `<option value="${esc(level.id)}"${item.required_account_level_id === level.id ? " selected" : ""}>${esc(level.title)}</option>`).join("")}</select></label><label>Донатов на публикацию<input name="donationCount" type="number" min="0" max="100" value="${value("donation_count", 0)}"></label><label>Каждые публикации<input name="donationPostInterval" type="number" min="1" max="1000" value="${value("donation_post_interval", 4)}"></label><label>Донат от, звёзды<input name="donationMinStars" type="number" min="0" max="1000000" value="${value("donation_min_stars", 1)}"></label><label>Донат до, звёзды<input name="donationMaxStars" type="number" min="0" max="1000000" value="${value("donation_max_stars", 5)}"></label></div><label><input name="indefinite" type="checkbox"${item.indefinite ? " checked" : ""}> Бессрочный пакет</label><label><input name="applyToNewChannels" type="checkbox"${item.apply_to_new_channels ? " checked" : ""}> Бесплатно подключать ко всем новым каналам</label>`;
}

function demoActivityPayload(form) {
  const values = Object.fromEntries(new FormData(form));
  return { ...values, subscribersPerDay: Number(values.subscribersPerDay), viewsPerDay: Number(values.viewsPerDay), reactionsPerDay: Number(values.reactionsPerDay), commentsPerDay: Number(values.commentsPerDay), postLimit: Number(values.postLimit), durationDays: values.indefinite === "on" ? 0 : Number(values.durationDays), fadeDurationDays: Number(values.fadeDurationDays), inactivityDays: Number(values.inactivityDays), priceStars: Number(values.priceStars), donationCount: Number(values.donationCount), donationPostInterval: Number(values.donationPostInterval), donationMinStars: Number(values.donationMinStars), donationMaxStars: Number(values.donationMaxStars), indefinite: values.indefinite === "on", applyToNewChannels: values.applyToNewChannels === "on", requiredAccountLevelId: values.requiredAccountLevelId || "" };
}

function demoActivityCard() {
  const packages = state.demoActivityPackages || [];
  const subscriptions = state.demoActivitySubscriptions || [];
  const channels = state.chats.filter((chat) => chat.type === "channel");
  const accountLevels = state.settings?.account_levels || [];
  const levelTitle = (levelId) => accountLevels.find((level) => level.id === levelId)?.title || levelId;
  const packageDetails = (item) => [`подписчики +${item.subscribers_per_day}/день`, `просмотры +${item.views_per_day}/день`, `реакции +${item.reactions_per_day}/день`, `комментарии +${item.comments_per_day}/день`, Number(item.donation_count) ? `донаты: ${item.donation_count} × ★${item.donation_min_stars}–${item.donation_max_stars} каждые ${item.donation_post_interval} публ.` : ""].filter((part) => part && !part.endsWith("+0/день")).join(" · ");
  return `<section class="admin-card"><h2>Пакеты локальной активности</h2><p class="muted">Пакеты меняют только счётчики и комментарии внутри Chat-Pro. Внешние Telegram, VK и другие сервисы не затрагиваются.</p>
    <form class="form" id="demoPackageForm"><h3>Новый пакет</h3>${demoActivityFields({}, accountLevels)}<p class="muted">Если новых публикаций нет указанное число дней, пакет плавно затухает в течение заданного срока, а затем отключается. Автодонаты начисляются автору публикации и растут с просмотрами и реакциями.</p><button class="button primary">Создать пакет</button></form>
    <div class="admin-list">${packages.map((item) => `<details class="admin-activity-reward"><summary><div><b>${esc(item.title)}</b>${item.apply_to_new_channels ? ' <span class="badge">Для новых каналов</span>' : ""}<p class="muted">${esc(packageDetails(item)) || "Нет показателей"}</p><small>${item.indefinite ? "Бессрочно" : `${item.duration_days} дн. + затухание ${item.fade_duration_days} дн.`} · без публикаций: ${item.inactivity_days ?? 3} дн. · ${item.price_stars ? `★ ${item.price_stars}` : "бесплатно"}${item.required_account_level_id ? ` · уровень: ${esc(levelTitle(item.required_account_level_id))}` : ""}</small></div><span class="button small">Редактировать</span></summary><form class="form" data-edit-demo-package="${esc(item.id)}"><h3>Редактировать пакет</h3>${demoActivityFields(item, accountLevels)}<p class="muted">Изменения применяются к новым и активным подключениям. Новая цена действует только для будущих подключений.</p><div class="admin-form-actions"><button class="button primary">Сохранить</button><button class="button danger small" type="button" data-delete-demo-package="${esc(item.id)}">Удалить</button></div></form></details>`).join("") || '<p class="muted">Пакетов пока нет.</p>'}</div>
    <form class="form" id="demoSubscriptionForm"><h3>Подключить пакет к каналу</h3><p class="muted">Если у пакета указана цена, она списывается со звёзд владельца выбранного канала.</p><label>Пакет<select name="packageId">${packages.map((item) => `<option value="${esc(item.id)}">${esc(item.title)}${item.price_stars ? ` · ★ ${item.price_stars}` : ""}</option>`).join("")}</select></label><label>Канал<select name="channelId">${channels.map((chat) => `<option value="${esc(chat.id)}">${esc(chat.title)}</option>`).join("")}</select></label><button class="button primary" ${packages.length && channels.length ? "" : "disabled"}>Подключить</button></form>
    <h3>Подключения</h3><div class="admin-list">${subscriptions.map((item) => `<div class="admin-activity-reward"><div><b>${esc(item.package_title)} · ${esc(item.channel_title)}</b><small>${item.active ? item.level_paused_at ? "Приостановлен: нет требуемого уровня" : `Активен до ${date(item.ends_at)}` : "Отключён"}</small></div>${item.active ? `<button class="button danger small" type="button" data-deactivate-demo-subscription="${esc(item.id)}">Отключить</button>` : ""}</div>`).join("") || '<p class="muted">Подключений пока нет.</p>'}</div>
  </section>`;
}
function channelMoneyCard() {
  const monetization = state.settings.channel_monetization || { starRateRubles: "0.50", tiers: [] };
  const payouts = state.payoutRequests || [];
  const tierRow = (tier = {}) => `<div class="activity-reward-form__criteria" data-channel-tier><label>От участников<input data-tier-min type="number" min="1" max="10000000" value="${esc(tier.minSubscribers ?? "")}" required></label><label>До участников, не включая<input data-tier-max type="number" min="1" max="10000000" value="${esc(tier.maxSubscribers ?? "")}" placeholder="Без ограничения"></label><label>Комиссия, %<input data-tier-percent type="number" min="1" max="100" value="${esc(tier.percent ?? "")}" required></label><button class="button danger small" type="button" data-delete-channel-tier>Удалить</button></div>`;
  return `<article class="admin-card"><h2>Комиссии каналов и бесед и выплаты</h2><p class="muted">При покупке звёзд через канал или беседу владелец получает денежное начисление: звёзды × курс × процент его уровня. Это отдельный учёт, не пополняющий баланс звёзд. Выплата создаёт заявку и не отправляет деньги автоматически.</p><form class="form" id="channelMonetizationForm"><label>Курс одной звезды, ₽<input name="starRateRubles" inputmode="decimal" value="${esc(monetization.starRateRubles)}" placeholder="0.50" required></label><div data-channel-tiers>${(monetization.tiers || []).map(tierRow).join("")}</div><button type="button" class="button small" data-add-channel-tier>Добавить уровень</button><button class="button primary">Сохранить комиссии</button></form><h3>Заявки на выплаты</h3><div class="admin-list">${payouts.map((item) => `<div class="admin-activity-reward"><div><b>${item.channel_type === "channel" ? "Канал" : item.channel_type === "group" ? "Группа" : "Беседа"} «${esc(item.channel_title)}» · ${esc(item.owner_name)}</b><small>@${esc(item.owner_username)} · ${item.amount_value} ₽ · ${date(item.created_at)} · ${item.status === "pending" ? "ожидает" : item.status === "paid" ? "выплачено" : "отклонено"}${item.admin_note ? ` · ${esc(item.admin_note)}` : ""}</small></div>${item.status === "pending" ? `<div class="admin-form-actions"><button class="button primary small" type="button" data-payout-update="paid" data-payout-request="${esc(item.id)}">Отметить выплаченной</button><button class="button danger small" type="button" data-payout-update="rejected" data-payout-request="${esc(item.id)}">Отклонить</button></div>` : ""}</div>`).join("") || '<p class="muted">Заявок пока нет.</p>'}</div></article>`;
}

function recommendedCard() {
  const channels = state.chats.filter((chat) => chat.type === "channel");
  const recommended = (state.recommended || []).map((rec) => ({ ...rec, chat: state.chats.find((chat) => chat.id === rec.chat_id) })).filter((rec) => rec.chat?.type === "channel");
  return `<article class="admin-card"><h2>Рекомендованные каналы</h2><p class="muted">Показываются всем пользователям только во вкладке «Каналы» после их собственных подписок.</p>${channels.length ? `<form class="form" id="recommendedForm"><label>Канал<select name="chatId">${channels.map((channel) => `<option value="${channel.id}">${esc(channel.title)}</option>`).join("")}</select></label><label>Позиция<input name="position" type="number" value="100" min="0"></label><button class="button primary">Добавить в рекомендации</button></form>` : '<p class="muted">Сначала создайте хотя бы один канал.</p>'}<div class="admin-list">${recommended.map((rec) => `<div class="admin-activity-reward"><div><b>${esc(rec.chat.title)}</b><small>Позиция: ${rec.position} · подписчики: ${rec.chat.subscriberCount}</small></div><button class="button danger small" type="button" data-delete-recommended="${esc(rec.chat_id)}">Убрать</button></div>`).join("") || '<p class="muted">Рекомендованных каналов пока нет.</p>'}</div></article>`;
}

function automatedCommentsCard() {
  const commenters = state.automatedCommenters || [];
  const rules = state.automatedCommentRules || [];
  const channels = state.chats.filter((chat) => chat.type === "channel");
  return `<article class="admin-card"><h2>Автокомментарии</h2><p class="muted">Комментарии публикуются только в локальном приложении и видны читателям с отметкой «Автокомментарий». Для видеокружков отправляется только сохранённый первый кадр: аудио и весь ролик не анализируются.</p>
    <form class="form" id="automatedCommenterForm"><h3>Автокомментатор</h3><label>Отображаемое имя<input name="name" required maxlength="80" placeholder="Например, Редакционный помощник"></label><label>Аватар (необязательно)<input name="avatar" type="file" accept="image/png,image/jpeg,image/webp"></label><button class="button primary">Создать автокомментатора</button></form>
    <div class="admin-list">${commenters.map((commenter) => `<form class="row" data-automated-commenter-edit="${esc(commenter.id)}">${commenter.avatar_data ? `<img class="avatar" src="${esc(commenter.avatar_data)}" alt="">` : `<div class="avatar">${esc(initials(commenter.name))}</div>`}<div class="row__body"><label>Имя<input name="name" required maxlength="80" value="${esc(commenter.name)}"></label><div class="row__sub">Автокомментатор · ${commenter.avatar_data ? "аватар загружен" : "без аватара"}</div><label>Новый аватар<input name="avatar" type="file" accept="image/png,image/jpeg,image/webp"></label></div><button class="button small" type="submit">Сохранить</button></form>`).join("") || '<p class="muted">Автокомментаторов пока нет.</p>'}</div>
    ${channels.length && commenters.length ? `<form class="form" id="automatedCommentRuleForm"><h3>Новое правило</h3><label>Канал<select name="channelId">${channels.map((channel) => `<option value="${esc(channel.id)}">${esc(channel.title)}</option>`).join("")}</select></label><label>Режим<select name="commentMode"><option value="ai">DeepSeek: комментарий по содержанию публикации</option><option value="circle_compliment">DeepSeek: безопасный комплимент к новому видеокружку</option></select></label><label data-automated-target-label>Публикация<select name="targetMessageId"></select></label><fieldset class="admin-automated-commenters"><legend>Кто комментирует</legend>${commenters.map((commenter) => `<label><input name="commenterId" type="checkbox" value="${esc(commenter.id)}"> ${esc(commenter.name)}</label>`).join("")}</fieldset><p class="muted" data-automated-ai-hint>DeepSeek создаёт отдельный содержательный комментарий по тексту или изображению публикации. Шаблоны и локальные фразы не используются.</p><p class="muted" data-circle-compliment-hint hidden>Выберите ровно одного автокомментатора. Правило работает только с новыми авторскими видеокружками, у которых есть первый кадр. Комментарий создаётся лишь если кадр подходит; внешность, возраст и другие личные признаки не оцениваются.</p><div class="activity-reward-form__criteria"><label>Минимальная пауза, минут<input name="minDelayMinutes" type="number" min="0" max="10080" value="10" required></label><label>Максимальная пауза, минут<input name="maxDelayMinutes" type="number" min="0" max="10080" value="90" required></label><label>Работать, дней<input name="durationDays" type="number" min="1" max="30" value="2" required></label></div><button class="button primary">Запустить правило</button></form>` : '<p class="muted">Для правила создайте хотя бы один канал и автокомментатора.</p>'}
    <h3>Правила</h3><div class="admin-list">${rules.map((rule) => `<div class="admin-activity-reward"><div><b>${esc(rule.channel_title || "Канал")}</b>${rule.active ? "" : ' <span class="badge">Отключено</span>'}<p class="muted">${rule.comment_mode === "circle_compliment" ? "DeepSeek: новые авторские видеокружки" : rule.target_message_id ? `DeepSeek: конкретная публикация: ${esc((rule.target_message_text || "удалённая публикация").slice(0, 90))}` : "DeepSeek: все новые публикации"}</p><small>Пауза ${Math.round(rule.min_delay_seconds / 60)}–${Math.round(rule.max_delay_seconds / 60)} мин. · до ${date(rule.ends_at)} · ожидает: ${rule.pending_count}</small></div>${rule.active ? `<button class="button danger small" type="button" data-deactivate-automated-comment-rule="${esc(rule.id)}">Отключить</button>` : ""}</div>`).join("") || '<p class="muted">Правил пока нет.</p>'}</div></article>`;
}

function activityRewardsCard() {
  const rewards = state.activityRewards || [];
  const rewardSummary = (reward = {}) => {
    const parts = [];
    if (Number(reward.stars)) parts.push(`★ ${Number(reward.stars)}`);
    if (Number(reward.premiumDays)) parts.push(`Premium ${Number(reward.premiumDays)} дн.`);
    if (Number(reward.recurringStars)) parts.push(`★ ${Number(reward.recurringStars)} раз в ${Number(reward.recurringIntervalDays)} дн. в течение ${Number(reward.recurringDurationDays)} дн.`);
    if (Number(reward.starPackageDiscountPercent)) parts.push(`Скидка ${Number(reward.starPackageDiscountPercent)}% на пакеты звёзд`);
    const limits = Object.entries(reward.limits || {}).filter(([, value]) => Number(value) > 0);
    if (limits.length) parts.push(`Личные лимиты: ${limits.map(([key, value]) => `${LEVEL_LIMITS.find(([id]) => id === key)?.[1] || key} — ${value}`).join(", ")}`);
    if (reward.accountLevelId) parts.push(`Уровень: ${state.settings.account_levels?.find((level) => level.id === reward.accountLevelId)?.title || reward.accountLevelId}`);
    if (reward.recommendOwnChannel) parts.push("Свой канал в рекомендациях");
    return parts.join(" · ") || "Награда не указана";
  };
  const levelOptions = (state.settings.account_levels || []).map((level) => `<option value="${esc(level.id)}">${esc(level.title)}</option>`).join("");
  const rewardFields = (prefix) => `<div class="activity-reward-form__criteria"><label>Разово, звёзды<input name="${prefix}.stars" type="number" min="0" max="1000000" step="1" value="0"></label><label>Дней Premium<input name="${prefix}.premiumDays" type="number" min="0" max="3650" step="1" value="0"></label><label>Периодически, звёзды за выплату<input name="${prefix}.recurringStars" type="number" min="0" max="1000000" step="1" value="0"></label><label>Интервал выплат, дней<input name="${prefix}.recurringIntervalDays" type="number" min="0" max="365" step="1" value="0"></label><label>Срок выплат, дней<input name="${prefix}.recurringDurationDays" type="number" min="0" max="3650" step="1" value="0"></label><label>Скидка на пакеты звёзд, %<input name="${prefix}.starPackageDiscountPercent" type="number" min="0" max="99" step="1" value="0"></label><label>Выдать уровень аккаунта<select name="${prefix}.accountLevelId"><option value="">Не выдавать</option>${levelOptions}</select></label><label><input name="${prefix}.recommendOwnChannel" type="checkbox"> Добавить выбранный пользователем канал в рекомендации</label></div><details><summary>Персонально повысить лимиты</summary><p class="muted">После получения награды эти значения сохраняются за пользователем и не понижаются при смене уровня.</p><div class="activity-reward-form__criteria">${LEVEL_LIMITS.map(([key, label]) => `<label>${esc(label)}<input name="${prefix}.limits.${key}" type="number" min="0" max="1000000" step="1" placeholder="Не менять"></label>`).join("")}</div></details>`;
  return `<article class="admin-card"><h2>Награды за активность</h2><p class="muted">Каждая награда выдаётся пользователю один раз. Прогресс и выполнение условий сервер проверяет по фактическим данным.</p>
    <form class="form" id="activityRewardForm">
      <label>Название<input name="title" required maxlength="120" placeholder="Первый вклад в сообщество"></label>
      <label>Описание<textarea name="description" maxlength="1000" placeholder="Расскажите, что нужно сделать"></textarea></label>
      <b>Условия (заполните одно или несколько)</b>
      <div class="activity-reward-form__criteria">${ACTIVITY_METRICS.map(([key, label]) => `<label>${esc(label)}<input name="criteria.${key}" type="number" min="0" step="1" placeholder="Не требуется"></label>`).join("")}</div>
      <h3>Награда</h3><p class="muted">Периодическая выплата впервые поступит после указанного интервала.</p>${rewardFields("reward")}
      <button class="button primary">Опубликовать награду</button>
    </form>
    <h3>Созданные награды</h3><div class="admin-list">${rewards.map((reward) => `<div class="admin-activity-reward"><div><b>${esc(reward.title)}</b>${reward.active ? "" : " <span class=\"badge\">Отключена</span>"}<p class="muted">${Object.entries(reward.criteria || {}).map(([key, value]) => `${esc(ACTIVITY_METRICS.find(([id]) => id === key)?.[1] || key)}: ${value}`).join(" · ")}</p><small>${esc(rewardSummary(reward.reward))} · получено: ${reward.claimsCount || 0}</small></div>${reward.active ? `<button class="button danger small" type="button" data-deactivate-activity-reward="${esc(reward.id)}">Отключить</button>` : ""}</div>`).join("") || '<p class="muted">Наград пока нет.</p>'}</div>
  </article>`;
}

function reportsCard() {
  const reports = state.reports || [];
  const submissions = state.shareSubmissions || [];
  const vkReviews = state.vkReviewSubmissions || [];
  const statusLabel = { pending: "Ожидает начисления", credited: "Награда начислена", rejected: "Отклонена", revoked: "Награда отменена" };
  const responseForm = (type, id, current = "") => `<form class="form" data-appeal-response data-appeal-type="${type}" data-appeal-id="${esc(id)}"><label>Ответ пользователю<textarea name="response" maxlength="2000" placeholder="Введите ответ администрации">${esc(current)}</textarea></label><button class="button small" type="submit">Отправить ответ</button></form>`;
  const reportItems = reports.map((report) => { const isPost = report.target_type === "group-post"; const isChannel = report.target_type === "channel"; return `<div class="admin-report"><div><b>Жалоба · ${esc(report.target_type === "story" ? "Сторис" : isPost ? `Пост · ${report.group_title || "группа"}` : isChannel ? `Канал · ${report.channel_title || "удалённый канал"}` : report.target_type)}</b><small>от ${esc(report.reporter_name || "удалённого пользователя")} · ${date(report.created_at)}</small><p>${esc(report.reason || "Причина не указана.")}</p>${report.target_type === "story" ? `<p class="muted">${report.story_caption ? esc(report.story_caption) : report.story_media_data ? "Сторис с медиа без подписи" : "Сторис уже удалена"}</p>` : ""}${isPost ? `<p class="muted">${esc(report.message_text || (report.message_media_type ? "Пост с медиа" : "Пост уже удалён"))}</p>` : ""}${responseForm("report", report.id, report.admin_response)}</div><div>${report.target_type === "story" && report.story_media_data ? `<button class="button danger small" type="button" data-delete-story="${report.target_id}">Удалить сторис</button>` : ""}${isPost ? `<button class="button ${report.message_deleted_by_admin ? "primary" : "danger"} small" type="button" data-moderate-message="${report.target_id}" data-restore="${report.message_deleted_by_admin ? "true" : "false"}">${report.message_deleted_by_admin ? "Восстановить пост" : "Удалить пост"}</button>` : ""}</div></div>`; });
  const submissionItems = submissions.map((submission) => `<div class="admin-report"><div><b>Награда за публикацию · ${esc(submission.channel_title)}</b><small>от ${esc(submission.submitter_name)} @${esc(submission.submitter_username)} · ${date(submission.created_at)}</small><p>Площадка: ${esc(submission.platform)} · <a href="${esc(submission.external_url)}" target="_blank" rel="noopener">открыть публикацию</a></p><p>Награда: ★ ${Number(submission.reward_stars)} · ${esc(statusLabel[submission.status] || submission.status)}</p>${submission.description ? `<p class="muted">${esc(submission.description)}</p>` : ""}<a href="${esc(submission.screenshot_data)}" target="_blank" rel="noopener"><img src="${esc(submission.screenshot_data)}" alt="Скриншот подтверждения" style="max-width:240px;max-height:180px;object-fit:contain"></a>${responseForm("submission", submission.id, submission.admin_response)}</div><div>${submission.status === "pending" ? `<button class="button primary small" type="button" data-share-submission-action="credit" data-share-submission="${submission.id}">Начислить сейчас</button><button class="button danger small" type="button" data-share-submission-action="reject" data-share-submission="${submission.id}">Отклонить</button>` : ""}${submission.status === "credited" ? `<button class="button danger small" type="button" data-share-submission-action="revoke" data-share-submission="${submission.id}">Отменить награду</button>` : ""}</div></div>`);
  const vkReviewItems = vkReviews.map((submission) => `<div class="admin-report"><div><b>Ролик или пост о Chat‑Pro в VK</b><small>от ${esc(submission.submitter_name)} @${esc(submission.submitter_username)} · ${date(submission.created_at)}</small><p><a href="${esc(submission.external_url)}" target="_blank" rel="noopener">Открыть ${submission.vk_kind === "video" ? "видео" : "пост"} VK</a></p><p>Проверено: ${Number(submission.likes_count)} лайков · награда ★ ${Number(submission.reward_stars)} · ${esc(statusLabel[submission.status] || submission.status)}</p><p class="muted">${esc(submission.verified_title)}</p>${responseForm("vk-review", submission.id, submission.admin_response)}</div><div>${submission.status === "pending" ? `<button class="button primary small" type="button" data-vk-review-action="credit" data-vk-review="${submission.id}">Начислить сейчас</button><button class="button danger small" type="button" data-vk-review-action="reject" data-vk-review="${submission.id}">Отклонить</button>` : ""}${submission.status === "credited" ? `<button class="button danger small" type="button" data-vk-review-action="revoke" data-vk-review="${submission.id}">Отменить за накрутку</button>` : ""}</div></div>`);
  return `<article class="admin-card"><h2>Обращения</h2><p class="muted">Здесь отображаются жалобы и заявки на награду. Награды начисляются автоматически через 10 минут, если их не отменить.</p><div class="admin-list">${[...vkReviewItems, ...submissionItems, ...reportItems].join("") || '<p class="muted">Обращений пока нет.</p>'}</div></article>`;
}

function accountLevelsCard() {
  return `<article class="admin-card admin-card--levels"><div class="admin-levels__header"><div><h2>Уровни аккаунта</h2><p class="muted">Это путь пользователя: он проходит или покупает только следующий уровень. Меняйте порядок кнопками — это изменит путь для всех пользователей.</p></div><button class="button" type="button" data-add-level>Добавить уровень</button></div>
    <form class="form" id="accountLevelsForm"><div class="admin-levels__list">${accountLevelsDraft.map(levelCard).join("")}</div><button class="button primary">Сохранить уровни</button></form>
  </article>`;
}

function levelCard(level, index) {
  const value = (object, key) => object?.[key] ?? "";
  const numberField = (path, label, current, hint = "", step = "1") => `<label>${esc(label)}<input data-level-field="${path}" type="number" min="0" max="1000000" step="${step}" value="${esc(current)}" placeholder="Не ограничивать">${hint ? `<small>${esc(hint)}</small>` : ""}</label>`;
  const rewardFields = (prefix, title, reward) => `<div class="admin-level-card__section"><h3>${esc(title)}</h3><div class="admin-level-card__grid">${numberField(`${prefix}.stars`, "Разово, звёзды", value(reward, "stars") || 0)}${numberField(`${prefix}.recurringStars`, "Периодически, звёзды за выплату", value(reward, "recurringStars") || 0)}${numberField(`${prefix}.recurringIntervalDays`, "Интервал выплат, дней", value(reward, "recurringIntervalDays") || 0)}${numberField(`${prefix}.recurringDurationDays`, "Срок выплат, дней", value(reward, "recurringDurationDays") || 0)}${numberField(`${prefix}.starPackageDiscountPercent`, "Скидка на пакеты звёзд, %", value(reward, "starPackageDiscountPercent") || 0)}</div><p class="muted">Периодическая выплата впервые поступит после указанного интервала. Скидка сохраняется за пользователем; при нескольких наградах действует наибольшая.</p><details><summary>Персонально повысить лимиты</summary><p class="muted">Полученный лимит остаётся за пользователем и имеет приоритет над меньшим лимитом уровня.</p><div class="admin-level-card__grid">${LEVEL_LIMITS.map(([key, label]) => numberField(`${prefix}.limits.${key}`, label, value(reward?.limits, key))).join("")}</div></details></div>`;
  return `<section class="admin-level-card" data-level-index="${index}">
    <div class="admin-level-card__head"><div><span class="badge">Уровень ${index + 1}</span><b>${esc(level.title || "Без названия")}</b></div><div class="admin-level-card__actions"><button class="button small" type="button" data-move-level="up" ${index === 0 ? "disabled" : ""}>Выше</button><button class="button small" type="button" data-move-level="down" ${index === accountLevelsDraft.length - 1 ? "disabled" : ""}>Ниже</button><button class="button danger small" type="button" data-delete-level ${accountLevelsDraft.length === 1 ? "disabled" : ""}>Удалить</button></div></div>
    <div class="admin-level-card__fields"><label>Название<input data-level-field="title" maxlength="120" required value="${esc(level.title)}" placeholder="Например, Активный"></label><label>Технический ID<input data-level-field="id" maxlength="40" required value="${esc(level.id)}" pattern="[a-z0-9_-]{2,40}" title="От 2 до 40 латинских букв, цифр, _ или -" placeholder="active"></label></div>
    <label>Описание<textarea data-level-field="description" maxlength="1000" placeholder="Что открывает этот уровень">${esc(level.description)}</textarea></label>
    <div class="admin-level-card__section"><h3>Что нужно сделать</h3><p class="muted">Оставьте поле пустым, если действие не требуется.</p><div class="admin-level-card__grid">${LEVEL_CRITERIA.map(([key, label]) => numberField(`criteria.${key}`, label, value(level.criteria, key))).join("")}</div></div>
    <div class="admin-level-card__section"><h3>Лимиты после получения уровня</h3><p class="muted">Пустое поле оставляет обычный лимит без изменения. Укажите 0, чтобы запретить действие на этом уровне.</p><div class="admin-level-card__grid">${LEVEL_LIMITS.map(([key, label]) => numberField(`limits.${key}`, label, value(level.limits, key))).join("")}</div></div>
    ${rewardFields("reward", "Награда за выполнение", level.reward || {})}
    <div class="admin-level-card__section"><h3>Подписка на уровень</h3><div class="admin-level-card__grid">${numberField("monthlyPrice", "Цена подписки в месяц, ₽", level.monthlyPrice || "0.00", "0 — подписка на этот уровень недоступна", "0.01")}</div><p class="muted">Первый платёж и автоматическое продление проходят через ЮKassa. Старые покупки за звёзды сохраняются у пользователей как бессрочный доступ.</p></div>
  </section>`;
}

function cloneLevels(levels) {
  return levels.map((level) => ({ ...level, criteria: { ...(level.criteria || {}) }, limits: { ...(level.limits || {}) }, reward: { ...(level.reward || {}) }, purchaseReward: { ...(level.purchaseReward || {}) } }));
}

function readAccountLevels() {
  root.querySelectorAll(".admin-level-card").forEach((card) => {
    const level = accountLevelsDraft[Number(card.dataset.levelIndex)];
    card.querySelectorAll("[data-level-field]").forEach((field) => {
      const path = field.dataset.levelField.split(".");
      if (path.length === 1) { level[path[0]] = ["title", "id", "description"].includes(path[0]) ? field.value.trim() : path[0] === "monthlyPrice" ? field.value.trim() || "0" : Number(field.value) || 0; return; }
      const key = path.pop();
      const target = path.reduce((current, part) => (current[part] ||= {}), level);
      if (field.value === "") delete target[key];
      else target[key] = Number(field.value) || 0;
    });
  });
  return accountLevelsDraft;
}

function newLevel() {
  const ids = new Set(accountLevelsDraft.map((level) => level.id));
  let number = accountLevelsDraft.length + 1;
  while (ids.has(`level_${number}`)) number += 1;
  return { id: `level_${number}`, title: `Уровень ${number}`, description: "", criteria: {}, limits: {}, reward: { stars: 0, limits: {}, recurringStars: 0, recurringIntervalDays: 0, recurringDurationDays: 0 }, monthlyPrice: "0.00" };
}

function renderLevelsEditor() {
  const card = root.querySelector(".admin-card--levels");
  card.outerHTML = accountLevelsCard();
  bindLevelEditor();
  bindAccountLevelsForm();
}

function settingsCard() {
  const appearance = { outlineColor: "#65ddf8", glowColor: "#21d5f0", glowIntensity: 35, ...(state.settings.ui_appearance || {}) };
  const branding = state.settings.public_branding || {};
  const hasLoginLogo = Boolean(branding.loginLogoData);
  return `<article class="admin-card"><h2>Настройки аккаунтов</h2><p class="muted">Права и лимиты пользователей настраиваются в разделе уровней аккаунта.</p>
    <form class="form admin-appearance-form" id="uiAppearanceForm"><h3>Подсветка ночного режима</h3><p class="muted">Эти значения используются по умолчанию для пользователей, которые не выбрали личную палитру.</p><div class="appearance-color-grid"><label>Цвет обводок<input name="outlineColor" type="color" value="${esc(appearance.outlineColor)}"></label><label>Цвет свечения<input name="glowColor" type="color" value="${esc(appearance.glowColor)}"></label></div><label class="night-glow-intensity">Яркость свечения <output data-admin-glow-intensity>${Number(appearance.glowIntensity)}%</output><input name="glowIntensity" type="range" min="0" max="100" step="1" value="${Number(appearance.glowIntensity)}"></label><button class="button primary">Сохранить подсветку</button></form>
    <form class="form" id="loginBrandingForm"><h3>Логотип страницы входа</h3><p class="muted">Загрузите PNG, JPG или WebP до 2,5 МБ. Файл хранится как есть, без обрезки, перекраски или преобразования.</p>${hasLoginLogo ? `<img class="brand-logo brand-logo--uploaded" src="${esc(branding.loginLogoData)}" width="64" height="64" alt="Текущий логотип">` : '<p class="muted">Сейчас используется стандартный icon.svg.</p>'}<label>Логотип<input name="loginLogo" type="file" accept="image/png,image/jpeg,image/webp,.png,.jpg,.jpeg,.webp" required></label><div class="admin-form-actions"><button class="button primary">Загрузить логотип</button>${hasLoginLogo ? '<button class="button danger" type="button" data-reset-login-logo>Вернуть стандартный</button>' : ""}</div></form>
  </article>`;
}

function publicLegalCard() {
  const legal = state.settings.public_legal || {};
  return `<article class="admin-card admin-card--legal"><h2>Реквизиты и условия</h2><p class="muted">Эти данные показываются на публичной странице <a href="/requisites" target="_blank" rel="noopener">/requisites</a>, доступны до входа и используются в ссылках согласия.</p>
    <form class="form" id="publicLegalForm">
      <div class="admin-legal-grid"><label>Статус продавца<input name="sellerStatus" maxlength="120" value="${esc(legal.sellerStatus || "")}" placeholder="самозанятый"></label><label>ФИО / наименование<input name="sellerName" maxlength="160" value="${esc(legal.sellerName || "")}" placeholder="Заполните реальное имя или наименование"></label><label>ИНН<input name="inn" inputmode="numeric" maxlength="12" value="${esc(legal.inn || "")}"></label><label>E-mail<input name="email" type="email" maxlength="254" value="${esc(legal.email || "")}"></label><label>Ссылка VK<input name="vkUrl" type="url" maxlength="500" value="${esc(legal.vkUrl || "")}"></label><label>Telegram<input name="telegram" maxlength="64" value="${esc(legal.telegram || "")}" placeholder="username без @"></label></div>
      <label>Описание покупки<textarea name="purchaseDescription" maxlength="1000">${esc(legal.purchaseDescription || "")}</textarea></label><label>Условия возврата средств<textarea name="refundTerms" maxlength="5000">${esc(legal.refundTerms || "")}</textarea></label>
      <div class="admin-legal-grid"><label>Ссылка на пользовательское соглашение<input name="userAgreementUrl" maxlength="500" value="${esc(legal.userAgreementUrl || "")}" placeholder="/requisites#user-agreement или https://..."></label><label>Ссылка на условия покупки<input name="purchaseTermsUrl" maxlength="500" value="${esc(legal.purchaseTermsUrl || "")}" placeholder="/requisites#purchase-terms или https://..."></label><label>Ссылка на политику данных<input name="privacyPolicyUrl" maxlength="500" value="${esc(legal.privacyPolicyUrl || "")}" placeholder="/requisites#privacy-policy или https://..."></label></div>
      <label>Текст пользовательского соглашения<textarea name="userAgreementText" maxlength="10000">${esc(legal.userAgreementText || "")}</textarea></label><label>Текст условий покупки<textarea name="purchaseTermsText" maxlength="10000">${esc(legal.purchaseTermsText || "")}</textarea></label><label>Политика обработки персональных данных<textarea name="privacyPolicyText" maxlength="10000">${esc(legal.privacyPolicyText || "")}</textarea></label>
      <button class="button primary">Сохранить публичную информацию</button>
    </form></article>`;
}

function starPackagesCard() {
  const legal = state.settings.public_legal || {};
  const starPackages = Array.isArray(legal.starPackages) ? legal.starPackages : [];
  return `<article class="admin-card admin-card--star-packages"><h2>Тарифы звёзд</h2><p class="muted">Настройте количество звёзд в пакете и его стоимость в рублях. Эти тарифы показываются пользователям и используются при оплате через ЮKassa.</p>
    <form class="form" id="starPackagesForm"><section class="star-package-editor" aria-labelledby="starPackagesTitle"><div class="star-package-editor__head"><h3 id="starPackagesTitle">Пакеты</h3><button type="button" class="button small" data-add-star-package>Добавить тариф</button></div><div class="star-package-editor__list" data-star-package-list>${starPackages.map(starPackageRow).join("")}</div></section><button class="button primary">Сохранить тарифы</button></form>
  </article>`;
}

function starPackageRow(package = {}) {
  return `<div class="star-package-row" data-star-package-row><input type="hidden" data-star-package-id value="${esc(package.id || "")}"><label>Количество звёзд<input data-star-package-stars type="number" inputmode="numeric" min="1" max="1000000" step="1" value="${esc(package.stars || "")}" required></label><label>Стоимость пакета, ₽<input data-star-package-price type="text" inputmode="decimal" placeholder="99.00" value="${esc(package.price || "")}" required></label><button type="button" class="button danger small" data-delete-star-package aria-label="Удалить тариф">Удалить</button></div>`;
}

function normalizeStarPackagePrice(value) {
  const match = String(value || "").trim().replace(",", ".").match(/^(0|[1-9]\d{0,6})(?:\.(\d{1,2}))?$/);
  if (!match || Number(match[0]) <= 0) throw new Error("Цена каждого тарифа должна быть положительной суммой в рублях, например 0.50.");
  return `${match[1]}.${(match[2] || "").padEnd(2, "0")}`;
}

function newStarPackageId(stars, usedIds) {
  const base = `stars-${stars}`;
  let id = base;
  let suffix = 2;
  while (usedIds.has(id)) id = `${base}-${suffix++}`;
  return id;
}

function readStarPackages(form) {
  const rows = [...form.querySelectorAll("[data-star-package-row]")];
  if (!rows.length) throw new Error("Добавьте хотя бы один тариф.");
  if (rows.length > 20) throw new Error("Можно указать не более 20 тарифов.");
  const usedIds = new Set();
  return rows.map((row) => {
    const stars = Number(row.querySelector("[data-star-package-stars]").value);
    if (!Number.isInteger(stars) || stars < 1 || stars > 1_000_000) throw new Error("Количество звёзд должно быть целым числом от 1 до 1 000 000.");
    let id = String(row.querySelector("[data-star-package-id]").value || "").trim().toLowerCase();
    if (!/^[a-z0-9_-]{3,40}$/.test(id) || usedIds.has(id)) id = newStarPackageId(stars, usedIds);
    usedIds.add(id);
    return { id, stars, price: normalizeStarPackagePrice(row.querySelector("[data-star-package-price]").value) };
  });
}

function bindAdmin() {
  root.querySelector("#reload").addEventListener("click", refresh);
  root.querySelectorAll("[data-admin-section]").forEach((button) => button.addEventListener("click", () => { adminSection = button.dataset.adminSection; renderAdmin(); }));
  root.querySelector("#starsForm")?.addEventListener("submit", submit("/api/admin/users/stars"));
  root.querySelector("#accountLevelGrantForm")?.addEventListener("submit", submit("/api/admin/users/account-level"));
  root.querySelector("#channelActivityRegulatorForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const form = event.currentTarget.elements;
      await api("/api/admin/settings", { method: "POST", body: { key: "channel_activity_regulator", value: {
        enabled: form.enabled.checked,
        viewRatePercent: Number(form.viewRatePercent.value),
        reactionRatePercent: Number(form.reactionRatePercent.value),
        weeklyUnsubscribePercent: Number(form.weeklyUnsubscribePercent.value),
        initialUnsubscribeMonths: Number(form.initialUnsubscribeMonths.value),
        settledWeeklyUnsubscribePercent: Number(form.settledWeeklyUnsubscribePercent.value),
      } } });
      await refresh("Регулятор активности каналов сохранён.");
    } catch (error) { toast(error.message, true); }
  });
  root.querySelectorAll("[data-select-user]").forEach((row) => row.addEventListener("click", () => {
    selectedAdminUserId = row.dataset.selectUser;
    root.querySelectorAll('select[name="userId"]').forEach((select) => { select.value = selectedAdminUserId; });
    root.querySelectorAll("[data-user-row]").forEach((item) => item.querySelector(".row__sub").textContent = item.dataset.selectUser === selectedAdminUserId ? `${item.querySelector(".row__sub").textContent.replace(" · выбран", "")} · выбран` : item.querySelector(".row__sub").textContent.replace(" · выбран", ""));
  }));
  root.querySelector("#recommendedForm")?.addEventListener("submit", submit("/api/admin/recommended"));
  const userSearch = root.querySelector("[data-user-search]");
  const applyUserSearch = () => {
    const query = String(userSearch?.value || "").trim().toLocaleLowerCase("ru-RU").replace(/^@/, "");
    let visible = 0;
    root.querySelectorAll("[data-user-row]").forEach((row) => {
      const match = !query || String(row.dataset.userSearchValue || "").toLocaleLowerCase("ru-RU").includes(query);
      row.hidden = !match;
      row.style.display = match ? "" : "none";
      if (match) visible += 1;
    });
    const empty = root.querySelector("[data-user-search-empty]");
    if (empty) empty.hidden = visible > 0;
  };
  userSearch?.addEventListener("input", applyUserSearch);
  userSearch?.addEventListener("search", applyUserSearch);
  root.querySelectorAll("#demoPackageForm, [data-edit-demo-package]").forEach((form) => {
    const indefinite = form.elements.indefinite;
    const durationField = form.querySelector("[data-duration-days-field]");
    const durationInput = form.elements.durationDays;
    const syncDuration = () => {
      const disabled = Boolean(indefinite.checked);
      durationField.hidden = disabled;
      durationInput.disabled = disabled;
      if (!disabled && !durationInput.value) durationInput.value = "7";
    };
    indefinite.addEventListener("change", syncDuration);
    syncDuration();
  });
  root.querySelector("#demoPackageForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      await api("/api/admin/demo-activity-packages", { method: "POST", body: demoActivityPayload(event.currentTarget) });
      await refresh("Демо-пакет создан.");
    } catch (error) { toast(error.message, true); }
  });
  root.querySelectorAll("[data-edit-demo-package]").forEach((form) => form.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      await api("/api/admin/demo-activity-packages/update", { method: "POST", body: { packageId: form.dataset.editDemoPackage, ...demoActivityPayload(form) } });
      await refresh("Пакет активности сохранён.");
    } catch (error) { toast(error.message, true); }
  }));
  root.querySelector("#demoSubscriptionForm")?.addEventListener("submit", submit("/api/admin/demo-activity-subscriptions"));
  root.querySelectorAll("[data-delete-demo-package]").forEach((button) => button.addEventListener("click", async () => {
    if (!window.confirm("Удалить демо-пакет?")) return;
    try { await api("/api/admin/demo-activity-packages/delete", { method: "POST", body: { packageId: button.dataset.deleteDemoPackage } }); await refresh("Демо-пакет удалён."); } catch (error) { toast(error.message, true); }
  }));
  root.querySelectorAll("[data-deactivate-demo-subscription]").forEach((button) => button.addEventListener("click", async () => {
    try { await api("/api/admin/demo-activity-subscriptions/deactivate", { method: "POST", body: { subscriptionId: button.dataset.deactivateDemoSubscription } }); await refresh("Подключение отключено."); } catch (error) { toast(error.message, true); }
  }));
  const channelMonetizationForm = root.querySelector("#channelMonetizationForm");
  const channelTierRow = (tier = {}) => `<div class="activity-reward-form__criteria" data-channel-tier><label>От подписчиков<input data-tier-min type="number" min="1" max="10000000" value="${esc(tier.minSubscribers ?? "")}" required></label><label>До подписчиков<input data-tier-max type="number" min="1" max="10000000" value="${esc(tier.maxSubscribers ?? "")}" placeholder="Без ограничения"></label><label>Комиссия, %<input data-tier-percent type="number" min="1" max="100" value="${esc(tier.percent ?? "")}" required></label><button class="button danger small" type="button" data-delete-channel-tier>Удалить</button></div>`;
  channelMonetizationForm?.querySelector("[data-add-channel-tier]")?.addEventListener("click", () => channelMonetizationForm.querySelector("[data-channel-tiers]").insertAdjacentHTML("beforeend", channelTierRow()));
  channelMonetizationForm?.querySelector("[data-channel-tiers]")?.addEventListener("click", (event) => { const button = event.target.closest("[data-delete-channel-tier]"); if (button) button.closest("[data-channel-tier]").remove(); });
  channelMonetizationForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const tiers = [...channelMonetizationForm.querySelectorAll("[data-channel-tier]")].map((row) => ({ minSubscribers: Number(row.querySelector("[data-tier-min]").value), maxSubscribers: row.querySelector("[data-tier-max]").value === "" ? null : Number(row.querySelector("[data-tier-max]").value), percent: Number(row.querySelector("[data-tier-percent]").value) }));
      await api("/api/admin/settings", { method: "POST", body: { key: "channel_monetization", value: { starRateRubles: channelMonetizationForm.elements.starRateRubles.value, tiers } } });
      await refresh("Комиссии каналов и бесед сохранены.");
    } catch (error) { toast(error.message, true); }
  });
  root.querySelectorAll("[data-payout-update]").forEach((button) => button.addEventListener("click", async () => {
    const status = button.dataset.payoutUpdate;
    const note = window.prompt(status === "paid" ? "Комментарий к выплате (необязательно):" : "Причина отклонения (необязательно):", "");
    if (note === null) return;
    try { await api("/api/admin/channel-payouts/update", { method: "POST", body: { requestId: button.dataset.payoutRequest, status, adminNote: note } }); await refresh(status === "paid" ? "Заявка отмечена выплаченной." : "Заявка отклонена, сумма снова доступна владельцу."); } catch (error) { toast(error.message, true); }
  }));
  const automatedCommenterForm = root.querySelector("#automatedCommenterForm");
  automatedCommenterForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const form = new FormData(automatedCommenterForm);
      const avatar = form.get("avatar");
      const avatarData = avatar?.size ? await fileToDataUrl(avatar, 1_800_000) : "";
      await api("/api/admin/automated-commenters", { method: "POST", body: { name: form.get("name"), avatarData } });
      await refresh("Автокомментатор создан.");
    } catch (error) { toast(error.message, true); }
  });
  root.querySelectorAll("[data-automated-commenter-edit]").forEach((form) => form.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const data = new FormData(form);
      const avatar = data.get("avatar");
      const avatarData = avatar?.size ? await fileToDataUrl(avatar, 1_800_000) : state.automatedCommenters.find((item) => item.id === form.dataset.automatedCommenterEdit)?.avatar_data || "";
      await api("/api/admin/automated-commenters/update", { method: "POST", body: { commenterId: form.dataset.automatedCommenterEdit, name: data.get("name"), avatarData } });
      await refresh("Автокомментатор обновлён.");
    } catch (error) { toast(error.message, true); }
  }));
  const automatedCommentRuleForm = root.querySelector("#automatedCommentRuleForm");
  const refreshAutomatedCommentTargets = () => {
    if (!automatedCommentRuleForm) return;
    const channelId = automatedCommentRuleForm.elements.channelId.value;
    const isCircleCompliment = automatedCommentRuleForm.elements.commentMode?.value === "circle_compliment";
    const target = automatedCommentRuleForm.elements.targetMessageId;
    const posts = state.messages.filter((message) => message.chatId === channelId && message.mediaType !== "system");
    target.innerHTML = isCircleCompliment
      ? '<option value="">Все новые авторские видеокружки</option>'
      : '<option value="">Все следующие публикации канала</option>' + posts.map((post) => `<option value="${esc(post.id)}">${esc(post.text.split(/\n\s*\n/)[0].slice(0, 90) || "Публикация с медиа")}</option>`).join("");
    target.disabled = isCircleCompliment;
    automatedCommentRuleForm.querySelector("[data-automated-target-label]").hidden = isCircleCompliment;
    automatedCommentRuleForm.querySelector("[data-automated-ai-hint]").hidden = isCircleCompliment;
    automatedCommentRuleForm.querySelector("[data-circle-compliment-hint]").hidden = !isCircleCompliment;
  };
  automatedCommentRuleForm?.elements.channelId.addEventListener("change", refreshAutomatedCommentTargets);
  automatedCommentRuleForm?.elements.commentMode?.addEventListener("change", refreshAutomatedCommentTargets);
  refreshAutomatedCommentTargets();
  automatedCommentRuleForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const form = new FormData(automatedCommentRuleForm);
      const commenterIds = [...automatedCommentRuleForm.querySelectorAll('input[name="commenterId"]:checked')].map((input) => input.value);
      await api("/api/admin/automated-comment-rules", { method: "POST", body: { channelId: form.get("channelId"), targetMessageId: form.get("targetMessageId"), commenterIds, commentMode: form.get("commentMode"), minDelayMinutes: Number(form.get("minDelayMinutes")), maxDelayMinutes: Number(form.get("maxDelayMinutes")), durationDays: Number(form.get("durationDays")) } });
      await refresh("Правило автокомментариев создано.");
    } catch (error) { toast(error.message, true); }
  });
  root.querySelector("#boostForm")?.addEventListener("submit", submit("/api/admin/boost-jobs"));
  const boostForm = root.querySelector("#boostForm");
  const refreshBoostTargets = () => {
    const targetType = boostForm.elements.targetType.value;
    const metric = boostForm.elements.metric;
    const target = boostForm.elements.targetId;
    const isChat = targetType === "chat";
    metric.innerHTML = isChat
      ? '<option value="subscribers">подписчики</option>'
      : '<option value="views">просмотры</option><option value="reactions">реакции</option>';
    const entries = isChat
      ? state.chats.filter((chat) => ["community", "channel"].includes(chat.type)).map((chat) => [chat.id, `${chat.title} · ${chat.type === "channel" ? "канал" : "беседа"}`])
      : state.messages.filter((message) => message.mediaType !== "system").map((message) => [message.id, `${message.text.slice(0, 90) || "Публикация с медиа"} · ${message.chatId}`]);
    target.innerHTML = entries.map(([id, label]) => `<option value="${esc(id)}">${esc(label)}</option>`).join("") || '<option value="">Нет доступных целей</option>';
    target.disabled = !entries.length;
    boostForm.querySelector("button[type=submit]").disabled = !entries.length;
  };
  boostForm?.querySelector("[data-boost-type]").addEventListener("change", refreshBoostTargets);
  root.querySelector("#activityRewardForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const form = Object.fromEntries(new FormData(event.currentTarget));
      const criteria = Object.fromEntries(Object.entries(form)
        .filter(([key, value]) => key.startsWith("criteria.") && Number(value) > 0)
        .map(([key, value]) => [key.slice("criteria.".length), Number(value)]));
      const reward = { stars: Number(form["reward.stars"]) || 0, recurringStars: Number(form["reward.recurringStars"]) || 0, recurringIntervalDays: Number(form["reward.recurringIntervalDays"]) || 0, recurringDurationDays: Number(form["reward.recurringDurationDays"]) || 0, starPackageDiscountPercent: Number(form["reward.starPackageDiscountPercent"]) || 0, accountLevelId: form["reward.accountLevelId"] || "", recommendOwnChannel: form["reward.recommendOwnChannel"] === "on", limits: Object.fromEntries(Object.entries(form).filter(([key, value]) => key.startsWith("reward.limits.") && Number(value) > 0).map(([key, value]) => [key.slice("reward.limits.".length), Number(value)])) };
      await api("/api/admin/activity-rewards", { method: "POST", body: { title: form.title, description: form.description, criteria, reward } });
      await refresh("Награда опубликована.");
    } catch (error) { toast(error.message, true); }
  });
  bindLevelEditor();
  bindAccountLevelsForm();
  const uiAppearanceForm = root.querySelector("#uiAppearanceForm");
  const adminGlowIntensity = uiAppearanceForm?.querySelector("[data-admin-glow-intensity]");
  uiAppearanceForm?.elements.glowIntensity.addEventListener("input", () => { adminGlowIntensity.value = `${uiAppearanceForm.elements.glowIntensity.value}%`; });
  uiAppearanceForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const values = new FormData(uiAppearanceForm);
      await api("/api/admin/settings", { method: "POST", body: { key: "ui_appearance", value: { outlineColor: values.get("outlineColor"), glowColor: values.get("glowColor"), glowIntensity: Number(values.get("glowIntensity")) } } });
      await refresh("Подсветка ночного режима сохранена.");
    } catch (error) { toast(error.message, true); }
  });
  root.querySelector("#loginBrandingForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const file = new FormData(event.currentTarget).get("loginLogo");
      if (!(file instanceof File) || !file.size) throw new Error("Выберите логотип.");
      if (!["image/png", "image/jpeg", "image/webp"].includes(fileMimeType(file))) throw new Error("Логотип должен быть в формате PNG, JPG или WebP.");
      const loginLogoData = await fileToDataUrl(file, 2_500_000);
      await api("/api/admin/settings", { method: "POST", body: { key: "public_branding", value: { loginLogoData } } });
      await refresh("Исходный логотип сохранён.");
    } catch (error) { toast(error.message, true); }
  });
  root.querySelector("[data-reset-login-logo]")?.addEventListener("click", async () => {
    try {
      await api("/api/admin/settings", { method: "POST", body: { key: "public_branding", value: { loginLogoData: "" } } });
      await refresh("Возвращён стандартный логотип.");
    } catch (error) { toast(error.message, true); }
  });
  const starPackagesForm = root.querySelector("#starPackagesForm");
  starPackagesForm?.querySelector("[data-add-star-package]")?.addEventListener("click", () => {
    const list = starPackagesForm.querySelector("[data-star-package-list]");
    if (list.children.length >= 20) return toast("Можно добавить не более 20 тарифов.", true);
    list.insertAdjacentHTML("beforeend", starPackageRow());
    list.lastElementChild.querySelector("[data-star-package-stars]").focus();
  });
  starPackagesForm?.querySelector("[data-star-package-list]")?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-delete-star-package]");
    if (!button) return;
    button.closest("[data-star-package-row]").remove();
  });
  starPackagesForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const legal = state.settings.public_legal || {};
      const value = { ...legal, starPackages: readStarPackages(starPackagesForm) };
      await api("/api/admin/settings", { method: "POST", body: { key: "public_legal", value } });
      await refresh("Тарифы звёзд сохранены.");
    } catch (error) { toast(error.message, true); }
  });
  root.querySelector("#publicLegalForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const value = Object.fromEntries(new FormData(event.currentTarget));
      value.starPackages = state.settings.public_legal?.starPackages || [];
      await api("/api/admin/settings", { method: "POST", body: { key: "public_legal", value } });
      await refresh("Публичная информация сохранена.");
    } catch (error) { toast(error.message, true); }
  });
  root.querySelectorAll("[data-appeal-response]").forEach((form) => form.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const response = String(new FormData(form).get("response") || "").trim();
      if (!response) throw new Error("Введите ответ пользователю.");
      await api("/api/admin/appeals/respond", { method: "POST", body: { appealType: form.dataset.appealType, appealId: form.dataset.appealId, response } });
      await refresh("Ответ отправлен пользователю.");
    } catch (error) { toast(error.message, true); }
  }));
  root.querySelectorAll("[data-share-submission-action]").forEach((button) => button.addEventListener("click", async () => {
    const action = button.dataset.shareSubmissionAction;
    const text = { credit: "Начислить награду сейчас?", reject: "Отклонить заявку и отменить начисление?", revoke: "Отменить начисленную награду? Будут списаны доступные звёзды." }[action];
    if (!window.confirm(text)) return;
    try { await api("/api/admin/channel-share-submissions/update", { method: "POST", body: { submissionId: button.dataset.shareSubmission, action } }); await refresh(action === "credit" ? "Награда начислена." : action === "reject" ? "Заявка отклонена." : "Награда отменена."); }
    catch (error) { toast(error.message, true); }
  }));
  root.querySelectorAll("[data-vk-review-action]").forEach((button) => button.addEventListener("click", async () => {
    const action = button.dataset.vkReviewAction;
    const text = { credit: "Начислить награду за ролик или пост VK сейчас?", reject: "Отклонить заявку на ролик или пост VK?", revoke: "Отменить награду из-за накрутки или нарушения? Будут списаны доступные звёзды." }[action];
    if (!window.confirm(text)) return;
    try { await api("/api/admin/vk-review-submissions/update", { method: "POST", body: { submissionId: button.dataset.vkReview, action } }); await refresh(action === "credit" ? "Награда начислена." : action === "reject" ? "Заявка отклонена." : "Награда отменена."); }
    catch (error) { toast(error.message, true); }
  }));
  root.querySelectorAll("[data-delete-story]").forEach((button) => button.addEventListener("click", async () => {
    if (!window.confirm("Удалить эту сторис?")) return;
    try {
      await api("/api/admin/stories/delete", { method: "POST", body: { storyId: button.dataset.deleteStory } });
      await refresh("Сторис удалена.");
    } catch (error) { toast(error.message, true); }
  }));
  root.querySelectorAll("[data-moderate-message]").forEach((button) => button.addEventListener("click", async () => {
    const restore = button.dataset.restore === "true";
    if (!window.confirm(restore ? "Восстановить этот пост?" : "Скрыть этот пост до восстановления из админки?")) return;
    try { await api("/api/admin/messages/moderate", { method: "POST", body: { messageId: button.dataset.moderateMessage, restore } }); await refresh(restore ? "Пост восстановлен." : "Пост скрыт."); }
    catch (error) { toast(error.message, true); }
  }));
  root.querySelectorAll("[data-deactivate-activity-reward]").forEach((button) => button.addEventListener("click", async () => {
    if (!window.confirm("Отключить эту награду? Уже получившие её пользователи сохранят награду.")) return;
    try { await api("/api/admin/activity-rewards/deactivate", { method: "POST", body: { rewardId: button.dataset.deactivateActivityReward } }); await refresh("Награда отключена."); }
    catch (error) { toast(error.message, true); }
  }));
  root.querySelectorAll("[data-delete-recommended]").forEach((button) => button.addEventListener("click", async () => {
    if (!window.confirm("Убрать канал из рекомендаций?")) return;
    try { await api("/api/admin/recommended/delete", { method: "POST", body: { chatId: button.dataset.deleteRecommended } }); await refresh("Канал убран из рекомендаций."); }
    catch (error) { toast(error.message, true); }
  }));
  root.querySelectorAll("[data-deactivate-automated-comment-rule]").forEach((button) => button.addEventListener("click", async () => {
    if (!window.confirm("Отключить правило и отменить ожидающие автокомментарии?")) return;
    try { await api("/api/admin/automated-comment-rules/deactivate", { method: "POST", body: { ruleId: button.dataset.deactivateAutomatedCommentRule } }); await refresh("Правило отключено."); }
    catch (error) { toast(error.message, true); }
  }));
}

function bindAccountLevelsForm() {
  root.querySelector("#accountLevelsForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const levels = readAccountLevels();
      if (!Array.isArray(levels) || !levels.length) throw new Error("Добавьте хотя бы один уровень.");
      if (levels.some((level) => !level.id || !level.title)) throw new Error("У каждого уровня должны быть id и название.");
      await api("/api/admin/settings", { method: "POST", body: { key: "account_levels", value: levels } });
      await refresh("Уровни аккаунта сохранены.");
    } catch (error) { toast(error.message, true); }
  });
}

function bindLevelEditor() {
  root.querySelector("[data-add-level]")?.addEventListener("click", () => { readAccountLevels(); accountLevelsDraft.push(newLevel()); renderLevelsEditor(); });
  root.querySelectorAll("[data-move-level]").forEach((button) => button.addEventListener("click", () => {
    readAccountLevels();
    const index = Number(button.closest(".admin-level-card").dataset.levelIndex);
    const target = button.dataset.moveLevel === "up" ? index - 1 : index + 1;
    [accountLevelsDraft[index], accountLevelsDraft[target]] = [accountLevelsDraft[target], accountLevelsDraft[index]];
    renderLevelsEditor();
  }));
  root.querySelectorAll("[data-delete-level]").forEach((button) => button.addEventListener("click", () => {
    if (accountLevelsDraft.length === 1) return toast("Нужен хотя бы один уровень.", true);
    readAccountLevels();
    accountLevelsDraft.splice(Number(button.closest(".admin-level-card").dataset.levelIndex), 1);
    renderLevelsEditor();
  }));
}

function submit(path) {
  return async (event) => {
    event.preventDefault();
    try { await api(path, { method: "POST", body: Object.fromEntries(new FormData(event.currentTarget)) }); await refresh("Готово."); }
    catch (error) { toast(error.message, true); }
  };
}

function fileMimeType(file) {
  const supplied = String(file?.type || "").toLowerCase();
  if (supplied === "image/jpg") return "image/jpeg";
  if (supplied) return supplied;
  const extension = String(file?.name || "").split(".").pop().toLowerCase();
  return { png: "image/png", jpg: "image/jpeg", jpeg: "image/jpeg", webp: "image/webp" }[extension] || "application/octet-stream";
}

async function fileToDataUrl(file, maxBytes) {
  if (!file || file.size > maxBytes) throw new Error(`Изображение должно быть не больше ${Math.floor(maxBytes / 1_000_000)} МБ.`);
  if (typeof file.arrayBuffer === "function") {
    try {
      const bytes = new Uint8Array(await file.arrayBuffer());
      let binary = "";
      for (let index = 0; index < bytes.length; index += 0x4000) binary += String.fromCharCode.apply(null, bytes.subarray(index, index + 0x4000));
      return `data:${fileMimeType(file)};base64,${btoa(binary)}`;
    } catch (_) { /* Older browsers continue through the FileReader fallback. */ }
  }
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(new Error("Не удалось прочитать изображение."));
    reader.readAsDataURL(file);
  });
}

async function refresh(message, preservePosition = true) {
  const position = preservePosition ? { x: window.scrollX, y: window.scrollY } : null;
  await load();
  renderAdmin();
  if (position) requestAnimationFrame(() => window.scrollTo(position.x, position.y));
  if (message) toast(message);
}
function userSelect(selectedId = "") { return `<label>Пользователь<select name="userId">${state.users.map((u) => `<option value="${u.id}"${u.id === selectedId ? " selected" : ""}>${esc(u.name)} @${esc(u.username)}</option>`).join("")}</select></label>`; }
function initials(name) { return String(name || "U").trim().split(/\s+/).slice(0,2).map((x) => x[0]?.toUpperCase() || "").join("") || "U"; }
function avatarTone(user) { const source = String(user?.id || user?.username || user?.name || "user"); let hash = 0; for (let index = 0; index < source.length; index += 1) hash = ((hash * 31) + source.charCodeAt(index)) | 0; return Math.abs(hash) % 8; }
function date(ts) { return new Intl.DateTimeFormat("ru-RU", { dateStyle: "short", timeStyle: "short" }).format(ts * 1000); }
function esc(value) { return String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;"); }
function toast(message, error = false) { document.querySelector(".toast")?.remove(); const el = document.createElement("div"); el.className = `toast${error ? " error" : ""}`; el.textContent = message; document.body.append(el); setTimeout(() => el.remove(), 3200); }
