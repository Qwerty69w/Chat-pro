const ADMIN_KEY = "minigram_admin_key";
const root = document.querySelector("#admin");
let adminKey = localStorage.getItem(ADMIN_KEY) || "";
let state = null;
const ACTIVITY_METRICS = [
  ["stars_balance", "Звёзд на текущем балансе"], ["direct_chats", "Личных диалогов"],
  ["channels_joined", "Подписок на чужие каналы"], ["communities_joined", "Бесед"], ["groups_joined", "Групп"],
  ["channels_created", "Созданных каналов"], ["communities_created", "Созданных бесед"], ["groups_created", "Созданных групп"],
  ["channel_subscribers", "Подписчиков в одном своём канале"], ["community_subscribers", "Участников в одной своей беседе"],
  ["group_subscribers", "Участников в одной своей группе"], ["messages", "Отправленных сообщений"],
  ["posts", "Публикаций в профиле"], ["stories", "Сторис"], ["reviews", "Отзывов"],
  ["donations_sent", "Отправленных донатов"], ["stars_donated", "Звёзд, отправленных в донатах"],
  ["donations_received", "Полученных донатов"], ["login_streak", "Дней подряд в приложении"],
];
const LEVEL_CRITERIA = [
  ["messages", "Отправленные сообщения"], ["posts", "Публикации в профиле"], ["stories", "Сторис"],
  ["reviews", "Отзывы"], ["groups", "Созданные группы"], ["communities", "Созданные беседы"], ["channels", "Созданные каналы"],
];
const LEVEL_LIMITS = [
  ["maxStars", "Максимум звёзд на балансе"], ["postsPerDay", "Публикаций в день"],
  ["storiesPerDay", "Сторис в день"], ["storiesPerMonth", "Сторис в месяц"],
  ["groupsJoined", "Подписок на группы"], ["groupsCreated", "Созданных групп"],
  ["communitiesJoined", "Участий в беседах"], ["communitiesCreated", "Созданных бесед"],
  ["channelsJoined", "Подписок на каналы"], ["channelsCreated", "Созданных каналов"],
  ["savedAccounts", "Сохранённых аккаунтов"],
];
let accountLevelsDraft = [];

start();

async function start() {
  if (!adminKey) {
    renderLogin();
    hidePageLoader();
    return;
  }
  try { await load(); renderAdmin(); } catch { renderLogin(); }
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
      <div class="brand"><div class="logo">CP</div><div><h1>Админка Chat-Pro</h1><p>Ключ по умолчанию: <b>admin123</b></p></div></div>
      <form class="form" id="login"><label>Admin key<input name="key" required value="${esc(adminKey)}"></label><button class="button primary">Войти</button></form>
      <p class="muted">Для смены ключа запустите сервер так: MINIGRAM_ADMIN_KEY=вашключ python3 server.py</p>
    </section></main>`;
  root.querySelector("#login").addEventListener("submit", async (event) => {
    event.preventDefault();
    adminKey = new FormData(event.currentTarget).get("key");
    localStorage.setItem(ADMIN_KEY, adminKey);
    try { await load(); renderAdmin(); } catch (error) { toast(error.message, true); }
  });
}

function renderAdmin() {
  accountLevelsDraft = cloneLevels(state.settings.account_levels || []);
  root.innerHTML = `
    <main class="admin-shell">
      <header class="admin-head"><div><h1>Админка Chat-Pro</h1><p class="muted">Управление пользователями, наградами за активность, статусами и демо-счётчиками</p></div><button class="button" id="reload">Обновить</button></header>
      <section class="admin-grid">
        ${usersCard()}
        ${boostCard()}
        ${recommendedCard()}
        ${automatedCommentsCard()}
        ${activityRewardsCard()}
        ${statusesCard()}
        ${reportsCard()}
        ${accountLevelsCard()}
        ${settingsCard()}
      </section>
    </main>`;
  bindAdmin();
}

function usersCard() {
  return `<article class="admin-card"><h2>Пользователи</h2><div class="admin-list">${state.users.map((u) => `<div class="row"><div class="avatar">${esc(initials(u.name))}</div><div class="row__body"><div class="row__title">${esc(u.name)} @${esc(u.username)}</div><div class="row__sub">★ ${u.stars} · premium: ${u.premiumUntil ? date(u.premiumUntil) : "нет"}</div></div></div>`).join("") || '<p class="muted">Нет пользователей.</p>'}</div>
    <form class="form" id="starsForm"><h3>Выдать звёзды</h3>${userSelect()}<label>Количество звёзд<input name="amount" type="number" value="100"></label><button class="button primary">Начислить</button></form>
    <form class="form" id="premiumForm"><h3>Выдать премиум</h3>${userSelect()}<label>Дней<input name="days" type="number" value="30"></label><button class="button primary">Выдать</button></form></article>`;
}

function boostCard() {
  const chats = state.chats.filter((chat) => ["group", "community", "channel"].includes(chat.type));
  const messages = state.messages.filter((message) => message.mediaType !== "system");
  return `<article class="admin-card"><h2>Демо-накрутка счётчиков</h2><p class="muted">Работает только внутри локального приложения. Не влияет на реальные Telegram, VK или другие сервисы. Пример: 10 реакций в минуту 5 часов = 3000 всего.</p>
    <form class="form" id="boostForm">
      <label>Цель<select name="targetType" data-boost-type><option value="chat">Группа, беседа или канал</option><option value="message">Публикация или сообщение</option></select></label>
      <label>Показатель<select name="metric" data-boost-metric><option value="subscribers">подписчики</option></select></label>
      <label>Конкретная цель<select name="targetId" data-boost-target required>${chats.map((chat) => `<option value="${chat.id}">${esc(chat.title)} · ${chat.type === "channel" ? "канал" : chat.type === "community" ? "беседа" : "группа"}</option>`).join("") || '<option value="">Нет подходящих чатов</option>'}</select></label>
      <label>В минуту<input name="amountPerMinute" type="number" min="1" max="10000" value="10" required></label>
      <label>Минут<input name="durationMinutes" type="number" min="1" max="10080" value="60" required></label>
      <button class="button primary" ${chats.length ? "" : "disabled"}>Создать задание</button>
    </form>
    <h3>Доступные чаты</h3><div class="admin-list">${chats.map((chat) => `<p><b>${esc(chat.title)}</b><br>${chat.type === "channel" ? "Канал" : chat.type === "community" ? "Беседа" : "Группа"} · подписчики ${chat.subscriberCount}</p>`).join("") || '<p class="muted">Групп, бесед и каналов нет.</p>'}</div>
    <h3>Доступные публикации</h3><div class="admin-list">${messages.map((message) => `<p>${esc(message.text.slice(0, 80) || "Публикация с медиа")} · просмотры ${message.views} · реакции ${message.reactionTotal}</p>`).join("") || '<p class="muted">Публикаций нет.</p>'}</div>
  </article>`;
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
  return `<article class="admin-card"><h2>Автокомментарии RSS</h2><p class="muted">Комментарии публикуются только в локальном приложении и видны читателям с отметкой «Автокомментарий». Правило можно привязать к одному RSS-посту либо ко всем следующим RSS-постам канала.</p>
    <form class="form" id="automatedCommenterForm"><h3>Автокомментатор</h3><label>Отображаемое имя<input name="name" required maxlength="80" placeholder="Например, Редакционный помощник"></label><label>Аватар (необязательно)<input name="avatar" type="file" accept="image/png,image/jpeg,image/webp"></label><button class="button primary">Создать автокомментатора</button></form>
    <div class="admin-list">${commenters.map((commenter) => `<div class="row">${commenter.avatar_data ? `<img class="avatar" src="${esc(commenter.avatar_data)}" alt="">` : `<div class="avatar">${esc(initials(commenter.name))}</div>`}<div class="row__body"><div class="row__title">${esc(commenter.name)}</div><div class="row__sub">Автокомментатор · ${commenter.avatar_data ? "аватар загружен" : "без аватара"}</div></div></div>`).join("") || '<p class="muted">Автокомментаторов пока нет.</p>'}</div>
    ${channels.length && commenters.length ? `<form class="form" id="automatedCommentRuleForm"><h3>Новое правило</h3><label>Канал<select name="channelId">${channels.map((channel) => `<option value="${esc(channel.id)}">${esc(channel.title)}</option>`).join("")}</select></label><label>RSS-публикация<select name="targetMessageId"></select></label><fieldset class="admin-automated-commenters"><legend>Кто комментирует</legend>${commenters.map((commenter) => `<label><input name="commenterId" type="checkbox" value="${esc(commenter.id)}"> ${esc(commenter.name)}</label>`).join("")}</fieldset><label>Тексты комментариев<textarea name="texts" required maxlength="10000" placeholder="Один вариант на строку&#10;Интересный материал, спасибо за подборку."></textarea><small>Варианты распределяются между выбранными автокомментаторами.</small></label><div class="activity-reward-form__criteria"><label>Минимальная пауза, минут<input name="minDelayMinutes" type="number" min="0" max="10080" value="10" required></label><label>Максимальная пауза, минут<input name="maxDelayMinutes" type="number" min="0" max="10080" value="90" required></label><label>Работать, дней<input name="durationDays" type="number" min="1" max="30" value="2" required></label></div><button class="button primary">Запустить правило</button></form>` : '<p class="muted">Для правила создайте хотя бы один канал и автокомментатора.</p>'}
    <h3>Правила</h3><div class="admin-list">${rules.map((rule) => `<div class="admin-activity-reward"><div><b>${esc(rule.channel_title || "Канал")}</b>${rule.active ? "" : ' <span class="badge">Отключено</span>'}<p class="muted">${rule.target_message_id ? `Конкретный RSS-пост: ${esc((rule.target_message_text || "удалённая публикация").slice(0, 90))}` : "Все новые RSS-посты"}</p><small>Пауза ${Math.round(rule.min_delay_seconds / 60)}–${Math.round(rule.max_delay_seconds / 60)} мин. · до ${date(rule.ends_at)} · ожидает: ${rule.pending_count}</small></div>${rule.active ? `<button class="button danger small" type="button" data-deactivate-automated-comment-rule="${esc(rule.id)}">Отключить</button>` : ""}</div>`).join("") || '<p class="muted">Правил пока нет.</p>'}</div></article>`;
}

function activityRewardsCard() {
  const rewards = state.activityRewards || [];
  return `<article class="admin-card"><h2>Награды за активность</h2><p class="muted">Каждая награда выдаётся пользователю один раз. Прогресс и выполнение условий сервер проверяет по фактическим данным.</p>
    <form class="form" id="activityRewardForm">
      <label>Название<input name="title" required maxlength="120" placeholder="Первый вклад в сообщество"></label>
      <label>Описание<textarea name="description" maxlength="1000" placeholder="Расскажите, что нужно сделать"></textarea></label>
      <b>Условия (заполните одно или несколько)</b>
      <div class="activity-reward-form__criteria">${ACTIVITY_METRICS.map(([key, label]) => `<label>${esc(label)}<input name="criteria.${key}" type="number" min="0" step="1" placeholder="Не требуется"></label>`).join("")}</div>
      <div class="activity-reward-form__criteria"><label>Награда, звёзды<input name="rewardStars" type="number" min="0" step="1" value="100"></label><label>Награда, дней Premium<input name="premiumDays" type="number" min="0" step="1" value="0"></label></div>
      <button class="button primary">Опубликовать награду</button>
    </form>
    <h3>Созданные награды</h3><div class="admin-list">${rewards.map((reward) => `<div class="admin-activity-reward"><div><b>${esc(reward.title)}</b>${reward.active ? "" : " <span class=\"badge\">Отключена</span>"}<p class="muted">${Object.entries(reward.criteria || {}).map(([key, value]) => `${esc(ACTIVITY_METRICS.find(([id]) => id === key)?.[1] || key)}: ${value}`).join(" · ")}</p><small>★ ${reward.reward_stars}${reward.premium_days ? ` · Premium ${reward.premium_days} дн.` : ""} · получено: ${reward.claimsCount || 0}</small></div>${reward.active ? `<button class="button danger small" type="button" data-deactivate-activity-reward="${esc(reward.id)}">Отключить</button>` : ""}</div>`).join("") || '<p class="muted">Наград пока нет.</p>'}</div>
  </article>`;
}

function statusesCard() {
  return `<article class="admin-card"><h2>Статусы-иконки</h2><form class="form" id="statusForm">
    <label>Иконка<select name="icon"><option>🏅</option><option>🏆</option><option>⭐</option><option>💎</option><option>🚀</option><option>🔥</option><option>👑</option></select></label>
    <label>Название<input name="title" required placeholder="Амбассадор"></label>
    <label>Описание<textarea name="description" placeholder="За что получен статус"></textarea></label>
    <label>Мин. звёзд на балансе<input name="minStars" type="number" value="0"></label>
    <label>Мин. отзывов<input name="minReviews" type="number" value="0"></label>
    <label>Награда звёздами<input name="rewardStars" type="number" value="0"></label>
    <label>Награда премиум дней<input name="rewardPremiumDays" type="number" value="0"></label>
    <button class="button primary">Создать статус</button>
  </form><div class="admin-list">${state.statuses.map((s) => `<p>${esc(s.icon)} <b>${esc(s.title)}</b><br>${esc(s.description)}</p>`).join("") || '<p class="muted">Нет статусов.</p>'}</div></article>`;
}

function reportsCard() {
  const reports = state.reports || [];
  return `<article class="admin-card"><h2>Жалобы</h2><p class="muted">Жалобы поступают сюда на рассмотрение. Удаление публикации обратимо.</p><div class="admin-list">${reports.map((report) => { const isPost = report.target_type === "group-post"; const isChannel = report.target_type === "channel"; return `<div class="admin-report"><div><b>${esc(report.target_type === "story" ? "Сторис" : isPost ? `Пост · ${report.group_title || "группа"}` : isChannel ? `Канал · ${report.channel_title || "удалённый канал"}` : report.target_type)}</b><small>от ${esc(report.reporter_name || "удалённого пользователя")} · ${date(report.created_at)}</small><p>${esc(report.reason || "Причина не указана.")}</p>${report.target_type === "story" ? `<p class="muted">${report.story_caption ? esc(report.story_caption) : report.story_media_data ? "Сторис с медиа без подписи" : "Сторис уже удалена"}</p>` : ""}${isPost ? `<p class="muted">${esc(report.message_text || (report.message_media_type ? "Пост с медиа" : "Пост уже удалён"))}</p>` : ""}</div>${report.target_type === "story" && report.story_media_data ? `<button class="button danger small" type="button" data-delete-story="${report.target_id}">Удалить сторис</button>` : ""}${isPost ? `<button class="button ${report.message_deleted_by_admin ? "primary" : "danger"} small" type="button" data-moderate-message="${report.target_id}" data-restore="${report.message_deleted_by_admin ? "true" : "false"}">${report.message_deleted_by_admin ? "Восстановить пост" : "Удалить пост"}</button>` : ""}</div>`; }).join("") || '<p class="muted">Жалоб пока нет.</p>'}</div></article>`;
}

function accountLevelsCard() {
  return `<article class="admin-card admin-card--levels"><div class="admin-levels__header"><div><h2>Уровни аккаунта</h2><p class="muted">Это путь пользователя: он проходит или покупает только следующий уровень. Меняйте порядок кнопками — это изменит путь для всех пользователей.</p></div><button class="button" type="button" data-add-level>Добавить уровень</button></div>
    <form class="form" id="accountLevelsForm"><div class="admin-levels__list">${accountLevelsDraft.map(levelCard).join("")}</div><button class="button primary">Сохранить уровни</button></form>
  </article>`;
}

function levelCard(level, index) {
  const value = (object, key) => object?.[key] ?? "";
  const numberField = (path, label, current, hint = "") => `<label>${esc(label)}<input data-level-field="${path}" type="number" min="0" max="1000000" step="1" value="${esc(current)}" placeholder="Не ограничивать">${hint ? `<small>${esc(hint)}</small>` : ""}</label>`;
  return `<section class="admin-level-card" data-level-index="${index}">
    <div class="admin-level-card__head"><div><span class="badge">Уровень ${index + 1}</span><b>${esc(level.title || "Без названия")}</b></div><div class="admin-level-card__actions"><button class="button small" type="button" data-move-level="up" ${index === 0 ? "disabled" : ""}>Выше</button><button class="button small" type="button" data-move-level="down" ${index === accountLevelsDraft.length - 1 ? "disabled" : ""}>Ниже</button><button class="button danger small" type="button" data-delete-level ${accountLevelsDraft.length === 1 ? "disabled" : ""}>Удалить</button></div></div>
    <div class="admin-level-card__fields"><label>Название<input data-level-field="title" maxlength="120" required value="${esc(level.title)}" placeholder="Например, Активный"></label><label>Технический ID<input data-level-field="id" maxlength="40" required value="${esc(level.id)}" pattern="[a-z0-9_-]{2,40}" title="От 2 до 40 латинских букв, цифр, _ или -" placeholder="active"></label></div>
    <label>Описание<textarea data-level-field="description" maxlength="1000" placeholder="Что открывает этот уровень">${esc(level.description)}</textarea></label>
    <div class="admin-level-card__section"><h3>Что нужно сделать</h3><p class="muted">Оставьте поле пустым, если действие не требуется.</p><div class="admin-level-card__grid">${LEVEL_CRITERIA.map(([key, label]) => numberField(`criteria.${key}`, label, value(level.criteria, key))).join("")}</div></div>
    <div class="admin-level-card__section"><h3>Лимиты после получения уровня</h3><p class="muted">Пустое поле оставляет обычный лимит без изменения. Укажите 0, чтобы запретить действие на этом уровне.</p><div class="admin-level-card__grid">${LEVEL_LIMITS.map(([key, label]) => numberField(`limits.${key}`, label, value(level.limits, key))).join("")}</div></div>
    <div class="admin-level-card__section"><h3>Награды и покупка</h3><div class="admin-level-card__grid">${numberField("reward.stars", "Награда за выполнение, звёзды", value(level.reward, "stars") || 0)}${numberField("reward.premiumDays", "Награда за выполнение, дней Premium", value(level.reward, "premiumDays") || 0)}${numberField("starsPrice", "Цена покупки, звёзды", level.starsPrice || 0, "0 — купить нельзя")}${numberField("purchaseReward.stars", "Бонус при покупке, звёзды", value(level.purchaseReward, "stars") || 0)}${numberField("purchaseReward.premiumDays", "Бонус при покупке, дней Premium", value(level.purchaseReward, "premiumDays") || 0)}</div></div>
  </section>`;
}

function cloneLevels(levels) {
  return levels.map((level) => ({ ...level, criteria: { ...(level.criteria || {}) }, limits: { ...(level.limits || {}) }, reward: { ...(level.reward || {}) }, purchaseReward: { ...(level.purchaseReward || {}) } }));
}

function readAccountLevels() {
  root.querySelectorAll(".admin-level-card").forEach((card) => {
    const level = accountLevelsDraft[Number(card.dataset.levelIndex)];
    card.querySelectorAll("[data-level-field]").forEach((field) => {
      const [group, key] = field.dataset.levelField.split(".");
      if (!key) { level[group] = group === "title" || group === "id" || group === "description" ? field.value.trim() : Number(field.value) || 0; return; }
      level[group] ||= {};
      if (field.value === "") delete level[group][key];
      else level[group][key] = Number(field.value) || 0;
    });
  });
  return accountLevelsDraft;
}

function newLevel() {
  const ids = new Set(accountLevelsDraft.map((level) => level.id));
  let number = accountLevelsDraft.length + 1;
  while (ids.has(`level_${number}`)) number += 1;
  return { id: `level_${number}`, title: `Уровень ${number}`, description: "", criteria: {}, limits: {}, reward: { stars: 0, premiumDays: 0 }, starsPrice: 0, purchaseReward: { stars: 0, premiumDays: 0 } };
}

function renderLevelsEditor() {
  const card = root.querySelector(".admin-card--levels");
  card.outerHTML = accountLevelsCard();
  bindLevelEditor();
  bindAccountLevelsForm();
}

function settingsCard() {
  const appearance = { outlineColor: "#65ddf8", glowColor: "#21d5f0", glowIntensity: 35, ...(state.settings.ui_appearance || {}) };
  return `<article class="admin-card"><h2>Лимиты и настройки аккаунтов</h2><p class="muted">Здесь можно вручную определить, что можно обычному и премиум аккаунту.</p>
    <form class="form" id="limitsForm"><label>JSON лимитов<textarea name="limits" style="min-height:260px">${esc(JSON.stringify(state.settings.limits, null, 2))}</textarea></label><button class="button primary">Сохранить лимиты</button></form>
    <form class="form" id="premiumSettingsForm"><label>JSON премиума<textarea name="premium" style="min-height:120px">${esc(JSON.stringify(state.settings.premium, null, 2))}</textarea></label><button class="button primary">Сохранить премиум</button></form>
    <form class="form admin-appearance-form" id="uiAppearanceForm"><h3>Подсветка ночного режима</h3><p class="muted">Эти значения используются по умолчанию для пользователей, которые не выбрали личную палитру.</p><div class="appearance-color-grid"><label>Цвет обводок<input name="outlineColor" type="color" value="${esc(appearance.outlineColor)}"></label><label>Цвет свечения<input name="glowColor" type="color" value="${esc(appearance.glowColor)}"></label></div><label class="night-glow-intensity">Яркость свечения <output data-admin-glow-intensity>${Number(appearance.glowIntensity)}%</output><input name="glowIntensity" type="range" min="0" max="100" step="1" value="${Number(appearance.glowIntensity)}"></label><button class="button primary">Сохранить подсветку</button></form>
  </article>`;
}

function bindAdmin() {
  root.querySelector("#reload").addEventListener("click", refresh);
  root.querySelector("#starsForm").addEventListener("submit", submit("/api/admin/users/stars"));
  root.querySelector("#premiumForm").addEventListener("submit", submit("/api/admin/users/premium"));
  root.querySelector("#recommendedForm")?.addEventListener("submit", submit("/api/admin/recommended"));
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
  const automatedCommentRuleForm = root.querySelector("#automatedCommentRuleForm");
  const refreshAutomatedCommentTargets = () => {
    if (!automatedCommentRuleForm) return;
    const channelId = automatedCommentRuleForm.elements.channelId.value;
    const target = automatedCommentRuleForm.elements.targetMessageId;
    const posts = state.messages.filter((message) => message.chatId === channelId && message.sourceType === "rss");
    target.innerHTML = '<option value="">Все следующие RSS-посты канала</option>' + posts.map((post) => `<option value="${esc(post.id)}">${esc(post.text.split(/\n\s*\n/)[0].slice(0, 90) || "RSS-публикация")}</option>`).join("");
  };
  automatedCommentRuleForm?.elements.channelId.addEventListener("change", refreshAutomatedCommentTargets);
  refreshAutomatedCommentTargets();
  automatedCommentRuleForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const form = new FormData(automatedCommentRuleForm);
      const commenterIds = [...automatedCommentRuleForm.querySelectorAll('input[name="commenterId"]:checked')].map((input) => input.value);
      const texts = String(form.get("texts") || "").split("\n").map((text) => text.trim()).filter(Boolean);
      await api("/api/admin/automated-comment-rules", { method: "POST", body: { channelId: form.get("channelId"), targetMessageId: form.get("targetMessageId"), commenterIds, texts, minDelayMinutes: Number(form.get("minDelayMinutes")), maxDelayMinutes: Number(form.get("maxDelayMinutes")), durationDays: Number(form.get("durationDays")) } });
      await refresh("Правило автокомментариев создано.");
    } catch (error) { toast(error.message, true); }
  });
  root.querySelector("#boostForm").addEventListener("submit", submit("/api/admin/boost-jobs"));
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
      ? state.chats.filter((chat) => ["group", "community", "channel"].includes(chat.type)).map((chat) => [chat.id, `${chat.title} · ${chat.type === "channel" ? "канал" : chat.type === "community" ? "беседа" : "группа"}`])
      : state.messages.filter((message) => message.mediaType !== "system").map((message) => [message.id, `${message.text.slice(0, 90) || "Публикация с медиа"} · ${message.chatId}`]);
    target.innerHTML = entries.map(([id, label]) => `<option value="${esc(id)}">${esc(label)}</option>`).join("") || '<option value="">Нет доступных целей</option>';
    target.disabled = !entries.length;
    boostForm.querySelector("button[type=submit]").disabled = !entries.length;
  };
  boostForm.querySelector("[data-boost-type]").addEventListener("change", refreshBoostTargets);
  root.querySelector("#activityRewardForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const form = Object.fromEntries(new FormData(event.currentTarget));
      const criteria = Object.fromEntries(Object.entries(form)
        .filter(([key, value]) => key.startsWith("criteria.") && Number(value) > 0)
        .map(([key, value]) => [key.slice("criteria.".length), Number(value)]));
      await api("/api/admin/activity-rewards", { method: "POST", body: { title: form.title, description: form.description, criteria, rewardStars: Number(form.rewardStars), premiumDays: Number(form.premiumDays) } });
      await refresh("Награда опубликована.");
    } catch (error) { toast(error.message, true); }
  });
  root.querySelector("#statusForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = Object.fromEntries(new FormData(event.currentTarget));
    await api("/api/admin/statuses", { method: "POST", body: { icon: form.icon, title: form.title, description: form.description, criteria: { minStars: Number(form.minStars), minReviews: Number(form.minReviews) }, reward: { stars: Number(form.rewardStars), premiumDays: Number(form.rewardPremiumDays) } } });
    await refresh("Статус создан.");
  });
  bindLevelEditor();
  bindAccountLevelsForm();
  root.querySelector("#limitsForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    await api("/api/admin/settings", { method: "POST", body: { key: "limits", value: JSON.parse(new FormData(event.currentTarget).get("limits")) } });
    await refresh("Лимиты сохранены.");
  });
  root.querySelector("#premiumSettingsForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    await api("/api/admin/settings", { method: "POST", body: { key: "premium", value: JSON.parse(new FormData(event.currentTarget).get("premium")) } });
    await refresh("Премиум сохранён.");
  });
  const uiAppearanceForm = root.querySelector("#uiAppearanceForm");
  const adminGlowIntensity = uiAppearanceForm.querySelector("[data-admin-glow-intensity]");
  uiAppearanceForm.elements.glowIntensity.addEventListener("input", () => { adminGlowIntensity.value = `${uiAppearanceForm.elements.glowIntensity.value}%`; });
  uiAppearanceForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const values = new FormData(uiAppearanceForm);
      await api("/api/admin/settings", { method: "POST", body: { key: "ui_appearance", value: { outlineColor: values.get("outlineColor"), glowColor: values.get("glowColor"), glowIntensity: Number(values.get("glowIntensity")) } } });
      await refresh("Подсветка ночного режима сохранена.");
    } catch (error) { toast(error.message, true); }
  });
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

function fileToDataUrl(file, maxBytes) {
  if (!file || file.size > maxBytes) throw new Error(`Изображение должно быть не больше ${Math.floor(maxBytes / 1_000_000)} МБ.`);
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(new Error("Не удалось прочитать изображение."));
    reader.readAsDataURL(file);
  });
}

async function refresh(message) { await load(); renderAdmin(); if (message) toast(message); }
function userSelect() { return `<label>Пользователь<select name="userId">${state.users.map((u) => `<option value="${u.id}">${esc(u.name)} @${esc(u.username)}</option>`).join("")}</select></label>`; }
function initials(name) { return String(name || "U").trim().split(/\s+/).slice(0,2).map((x) => x[0]?.toUpperCase() || "").join("") || "U"; }
function date(ts) { return new Intl.DateTimeFormat("ru-RU", { dateStyle: "short", timeStyle: "short" }).format(ts * 1000); }
function esc(value) { return String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;"); }
function toast(message, error = false) { document.querySelector(".toast")?.remove(); const el = document.createElement("div"); el.className = `toast${error ? " error" : ""}`; el.textContent = message; document.body.append(el); setTimeout(() => el.remove(), 3200); }
