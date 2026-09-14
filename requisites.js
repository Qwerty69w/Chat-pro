const legalPage = document.querySelector("#legalPage");

start();

async function start() {
  try {
    const response = await fetch("/api/public/legal");
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.error || "Не удалось загрузить информацию.");
    render(data.legal || {});
  } catch (error) {
    legalPage.innerHTML = `<section class="legal-page__card"><h1>Информация</h1><p class="muted">${esc(error.message)}</p><a class="button" href="/">Вернуться в Chat-Pro</a></section>`;
  }
}

function render(legal) {
  const telegramUrl = legal.telegram ? `https://t.me/${encodeURIComponent(String(legal.telegram).replace(/^@/, ""))}` : "";
  const packages = Array.isArray(legal.starPackages) ? legal.starPackages : [];
  const seller = [legal.sellerStatus, legal.sellerName].filter(Boolean).join(" · ");
  legalPage.innerHTML = `
    <header class="legal-page__head"><a class="brand" href="/"><img class="brand-logo" src="icon.svg" width="64" height="64" alt="Логотип Chat-Pro"><div><b>Chat-Pro</b><span>Информация</span></div></a><a class="button small" href="/">К приложению</a></header>
    <section class="legal-page__hero"><p>Публичная информация</p><h1>Информация</h1><span>Реквизиты, условия и контакты для пользователей сервиса Chat-Pro.</span></section>
    <section class="legal-page__grid">
      <article class="legal-page__card"><h2>Продавец</h2><dl>${seller ? `<div><dt>Статус</dt><dd>${esc(seller)}</dd></div>` : ""}${legal.inn ? `<div><dt>ИНН</dt><dd>${esc(legal.inn)}</dd></div>` : ""}</dl></article>
      <article class="legal-page__card"><h2>Контакты</h2><dl>${legal.email ? `<div><dt>E-mail</dt><dd><a href="mailto:${esc(legal.email)}">${esc(legal.email)}</a></dd></div>` : ""}${legal.vkUrl ? `<div><dt>VK</dt><dd><a href="${esc(url(legal.vkUrl))}" target="_blank" rel="noopener">${esc(legal.vkUrl)}</a></dd></div>` : ""}${telegramUrl ? `<div><dt>Telegram</dt><dd><a href="${esc(telegramUrl)}" target="_blank" rel="noopener">@${esc(String(legal.telegram).replace(/^@/, ""))}</a></dd></div>` : ""}</dl></article>
      <article class="legal-page__card legal-page__card--wide"><h2>Что покупает пользователь</h2><p>${esc(legal.purchaseDescription || "")}</p></article>
      <article class="legal-page__card legal-page__card--wide"><h2>Пакеты звёзд</h2><div class="legal-package-list">${packages.map((item) => `<div><b>★ ${Number(item.stars)}</b><span>${esc(item.price)} ₽</span></div>`).join("") || '<p class="muted">Пакеты пока не опубликованы.</p>'}</div></article>
      <article class="legal-page__card legal-page__card--wide"><h2>Возврат средств</h2><p class="legal-page__text">${esc(legal.refundTerms || "")}</p></article>
      <article class="legal-page__card legal-page__card--wide" id="user-agreement"><h2>Пользовательское соглашение</h2>${legal.userAgreementUrl && legal.userAgreementUrl !== "/requisites#user-agreement" ? `<p><a href="${esc(url(legal.userAgreementUrl))}" target="_blank" rel="noopener">Открыть пользовательское соглашение</a></p>` : ""}<p class="legal-page__text">${esc(legal.userAgreementText || "")}</p></article>
      <article class="legal-page__card legal-page__card--wide" id="purchase-terms"><h2>Условия покупки</h2>${legal.purchaseTermsUrl && legal.purchaseTermsUrl !== "/requisites#purchase-terms" ? `<p><a href="${esc(url(legal.purchaseTermsUrl))}" target="_blank" rel="noopener">Открыть условия покупки</a></p>` : ""}<p class="legal-page__text">${esc(legal.purchaseTermsText || "")}</p></article>
      <article class="legal-page__card legal-page__card--wide" id="privacy-policy"><h2>Политика обработки персональных данных</h2>${legal.privacyPolicyUrl && legal.privacyPolicyUrl !== "/requisites#privacy-policy" ? `<p><a href="${esc(url(legal.privacyPolicyUrl))}" target="_blank" rel="noopener">Открыть политику обработки данных</a></p>` : ""}<p class="legal-page__text">${esc(legal.privacyPolicyText || "")}</p></article>
    </section>`;
}

function url(value) { return String(value || "").startsWith("/") ? value : String(value || ""); }
function esc(value) { return String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;"); }
