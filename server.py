#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Chat-Pro local backend with admin panel.

Run: python3 server.py
Open: http://localhost:8000
Admin: http://localhost:8000/admin

This is a local demo backend. Counters, boosts and reviews work only inside this
application and do not affect real Telegram/VK/web pages.
"""

from __future__ import annotations

import base64
import binascii
import datetime
import hashlib
import hmac
import ipaddress
import json
import math
import mimetypes
import os
import re
import secrets
import socket
import sqlite3
import smtplib
import threading
import time
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from email.message import EmailMessage
from html import unescape
from http import HTTPStatus
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib import error as urlerror
from urllib.parse import parse_qs, quote, urlencode, urljoin, urlparse, urlunparse
from urllib import request as urlrequest
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "minigram.sqlite3"
HOST = os.environ.get("CHAT_PRO_HOST", "127.0.0.1")
PORT = int(os.environ.get("CHAT_PRO_PORT", "8000"))
ADMIN_KEY = os.environ.get("MINIGRAM_ADMIN_KEY", "admin123")
TELEGRAM_POLL_INTERVAL = 15
TELEGRAM_MEDIA_MAX_BYTES = 2_500_000
RSS_POLL_INTERVAL = 300
RSS_MAX_BYTES = 512_000
RSS_MAX_ENTRIES = 100
RSS_IMAGE_MAX_BYTES = 2_500_000
CIRCLE_PREVIEW_MAX_BYTES = 400_000
VK_POLL_INTERVAL = 300
VK_API_VERSION = "5.199"
VK_OAUTH_CLIENT_ID = os.environ.get("VK_OAUTH_CLIENT_ID", "").strip()
VK_OAUTH_CLIENT_SECRET = os.environ.get("VK_OAUTH_CLIENT_SECRET", "").strip()
VK_OAUTH_REDIRECT_URI = os.environ.get("VK_OAUTH_REDIRECT_URI", "").strip()
VK_OAUTH_SCOPE = os.environ.get("VK_OAUTH_SCOPE", "").strip()
VK_ID_SERVICE_TOKEN = os.environ.get("VK_ID_SERVICE_TOKEN", "").strip()
AUTH_CODE_TTL = 600
AUTH_CODE_MAX_ATTEMPTS = 5
CHAT_ACTIVITY_TTL = 6
chat_activities: dict[tuple[str, str], tuple[str, float]] = {}
chat_activities_lock = threading.Lock()
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM = os.environ.get("SMTP_FROM", SMTP_USERNAME)
SMTP_USE_SSL = os.environ.get("SMTP_USE_SSL", "").strip().lower() in {"1", "true", "yes"}
YOOKASSA_SHOP_ID = os.environ.get("YOOKASSA_SHOP_ID", "")
YOOKASSA_SECRET_KEY = os.environ.get("YOOKASSA_SECRET_KEY", "")
YOOKASSA_RETURN_URL = os.environ.get("YOOKASSA_RETURN_URL", "").rstrip("/")


def read_genapi_settings() -> dict[str, str]:
    settings: dict[str, str] = {}
    try:
        for line in Path("/etc/chat-pro/genapi.env").read_text(encoding="utf-8").splitlines():
            key, separator, value = line.strip().partition("=")
            if separator and key in {"GENAPI_API_KEY", "GENAPI_BASE_URL", "GENAPI_MODEL", "GENAPI_ADMIN_MODEL"}:
                settings[key] = value.strip()
    except OSError:
        pass
    return settings


GENAPI_SETTINGS = read_genapi_settings()
GENAPI_API_KEY = os.environ.get("GENAPI_API_KEY", GENAPI_SETTINGS.get("GENAPI_API_KEY", "")).strip()
GENAPI_BASE_URL = os.environ.get("GENAPI_BASE_URL", GENAPI_SETTINGS.get("GENAPI_BASE_URL", "https://proxy.gen-api.ru/v1")).strip().rstrip("/")
GENAPI_MODEL = os.environ.get("GENAPI_MODEL", GENAPI_SETTINGS.get("GENAPI_MODEL", "deepseek-v4-flash")).strip()
GENAPI_ADMIN_MODEL = os.environ.get("GENAPI_ADMIN_MODEL", GENAPI_SETTINGS.get("GENAPI_ADMIN_MODEL", GENAPI_MODEL)).strip()


DIALOG_APPEARANCE_FIELDS = (
    "theme", "dialog_color", "other_dialog_color", "dialog_panel_color", "dialog_panel_style",
    "dialog_bubble_style", "dialog_font", "text_scale", "chat_background", "chat_background_data",
)
DIALOG_APPEARANCE_FALLBACK = {
    "theme": "dark",
    "dialog_color": "#004d65",
    "other_dialog_color": "#004d65",
    "dialog_panel_color": "#f4f8fc",
    "dialog_panel_style": "custom",
    "dialog_bubble_style": "custom",
    "dialog_font": "rounded",
    "text_scale": "system",
    "chat_background": "jade",
    "chat_background_data": None,
}


def dialog_appearance_defaults(con: sqlite3.Connection) -> dict:
    source = con.execute(
        f"SELECT {', '.join(DIALOG_APPEARANCE_FIELDS)} FROM users WHERE lower(username) = 'andrei'"
    ).fetchone()
    if not source:
        return DIALOG_APPEARANCE_FALLBACK.copy()
    appearance = {field: source[field] for field in DIALOG_APPEARANCE_FIELDS}
    appearance["chat_background"] = "jade"
    appearance["chat_background_data"] = None
    return appearance


def genapi_configuration(admin: bool = False) -> tuple[str, str, str]:
    settings = read_genapi_settings()
    api_key = settings.get("GENAPI_API_KEY", "").strip() or GENAPI_API_KEY
    base_url = settings.get("GENAPI_BASE_URL", "").strip().rstrip("/") or GENAPI_BASE_URL
    model = (settings.get("GENAPI_ADMIN_MODEL", "").strip() or GENAPI_ADMIN_MODEL) if admin else (settings.get("GENAPI_MODEL", "").strip() or GENAPI_MODEL)
    return api_key, base_url, model


GENAPI_ADDITIONAL_MODELS = {
    "gemini-3-1-pro": {"label": "Gemini 3.1 Pro", "description": "Модель Google для подготовки текстов и управления каналами."},
    "claude-sonnet-5-5": {"label": "Claude Sonnet 5.5", "description": "Модель Anthropic для подготовки текстов и управления каналами."},
    "gpt-5-4": {"label": "GPT-5.4", "description": "Модель OpenAI для подготовки текстов и управления каналами."},
}


def genapi_configuration_for_profile(profile_id, admin: bool = False) -> tuple[str, str, str]:
    if profile_id in GENAPI_ADDITIONAL_MODELS:
        api_key, base_url, _ = genapi_configuration()
        return api_key, base_url, profile_id
    return genapi_configuration(admin=admin if profile_id is None else profile_id == "extended")


def genapi_model_profiles() -> list[dict[str, str]]:
    default_model = genapi_configuration()[2]
    extended_model = genapi_configuration(admin=True)[2]
    profiles = [{
        "id": "default",
        "label": "DeepSeek",
        "description": "Основная модель, настроенная для вашего аккаунта.",
    }]
    profiles.extend({"id": profile_id, **metadata} for profile_id, metadata in GENAPI_ADDITIONAL_MODELS.items())
    if extended_model and extended_model != default_model:
        profiles.append({
            "id": "extended",
            "label": "Расширенная модель",
            "description": "Дополнительный серверный профиль для более сложных задач ИИ.",
        })
    return profiles


def normalize_genapi_model_profile(value) -> str:
    profile_id = str(value or "").strip().casefold()
    return profile_id if profile_id in {profile["id"] for profile in genapi_model_profiles()} else "default"


def read_s3_settings() -> dict[str, str]:
    allowed = {"S3_ENDPOINT", "S3_BUCKET", "S3_ACCESS_KEY", "S3_SECRET_KEY", "S3_REGION"}
    settings: dict[str, str] = {}
    try:
        for line in Path("/etc/chat-pro/s3.env").read_text(encoding="utf-8").splitlines():
            key, separator, value = line.strip().partition("=")
            if separator and key in allowed:
                settings[key] = value.strip()
    except OSError:
        pass
    return settings


def s3_configuration() -> dict[str, str]:
    settings = read_s3_settings()
    return {
        "endpoint": settings.get("S3_ENDPOINT", "").strip().rstrip("/"),
        "bucket": settings.get("S3_BUCKET", "").strip(),
        "access_key": settings.get("S3_ACCESS_KEY", "").strip(),
        "secret_key": settings.get("S3_SECRET_KEY", "").strip(),
        "region": settings.get("S3_REGION", "us-east-1").strip() or "us-east-1",
    }


def s3_is_configured() -> bool:
    config = s3_configuration()
    endpoint = urlparse(config["endpoint"])
    return bool(config["bucket"] and config["access_key"] and config["secret_key"] and endpoint.scheme == "https" and endpoint.netloc)


def s3_quote(value: str) -> str:
    return quote(str(value), safe="~-._/")


def s3_query_quote(value: str) -> str:
    return quote(str(value), safe="~-._")


def s3_signing_key(secret_key: str, date_stamp: str, region: str) -> bytes:
    date_key = hmac.new(("AWS4" + secret_key).encode("utf-8"), date_stamp.encode("utf-8"), hashlib.sha256).digest()
    region_key = hmac.new(date_key, region.encode("utf-8"), hashlib.sha256).digest()
    service_key = hmac.new(region_key, b"s3", hashlib.sha256).digest()
    return hmac.new(service_key, b"aws4_request", hashlib.sha256).digest()


def s3_object_url(config: dict[str, str], key: str) -> tuple[str, str, str]:
    endpoint = urlparse(config["endpoint"])
    canonical_uri = s3_quote(f"/{config['bucket']}/{key}")
    return config["endpoint"] + canonical_uri, endpoint.netloc, canonical_uri


def s3_presigned_url(method: str, key: str, expires_in: int = 900, content_type: str | None = None) -> tuple[str, dict[str, str]]:
    config = s3_configuration()
    if not s3_is_configured():
        raise ValueError("S3-хранилище пока не подключено.")
    current = datetime.datetime.now(datetime.timezone.utc)
    amz_date = current.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = current.strftime("%Y%m%d")
    credential_scope = f"{date_stamp}/{config['region']}/s3/aws4_request"
    url, host, canonical_uri = s3_object_url(config, key)
    canonical_headers = f"host:{host}\n"
    signed_headers = "host"
    headers: dict[str, str] = {}
    if content_type:
        canonical_headers = f"content-type:{content_type}\n" + canonical_headers
        signed_headers = "content-type;host"
        headers["Content-Type"] = content_type
    query = {
        "X-Amz-Algorithm": "AWS4-HMAC-SHA256",
        "X-Amz-Credential": f"{config['access_key']}/{credential_scope}",
        "X-Amz-Date": amz_date,
        "X-Amz-Expires": str(max(60, min(expires_in, 3600))),
        "X-Amz-SignedHeaders": signed_headers,
    }
    canonical_query = "&".join(f"{s3_query_quote(name)}={s3_query_quote(query[name])}" for name in sorted(query))
    canonical_request = "\n".join((method, canonical_uri, canonical_query, canonical_headers, signed_headers, "UNSIGNED-PAYLOAD"))
    string_to_sign = "\n".join(("AWS4-HMAC-SHA256", amz_date, credential_scope, hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()))
    signature = hmac.new(s3_signing_key(config["secret_key"], date_stamp, config["region"]), string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{url}?{canonical_query}&X-Amz-Signature={signature}", headers


def s3_object_metadata(key: str) -> tuple[int, str]:
    config = s3_configuration()
    if not s3_is_configured():
        raise ValueError("S3-хранилище пока не подключено.")
    current = datetime.datetime.now(datetime.timezone.utc)
    amz_date = current.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = current.strftime("%Y%m%d")
    credential_scope = f"{date_stamp}/{config['region']}/s3/aws4_request"
    url, host, canonical_uri = s3_object_url(config, key)
    canonical_headers = f"host:{host}\nx-amz-content-sha256:UNSIGNED-PAYLOAD\nx-amz-date:{amz_date}\n"
    signed_headers = "host;x-amz-content-sha256;x-amz-date"
    canonical_request = "\n".join(("HEAD", canonical_uri, "", canonical_headers, signed_headers, "UNSIGNED-PAYLOAD"))
    string_to_sign = "\n".join(("AWS4-HMAC-SHA256", amz_date, credential_scope, hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()))
    signature = hmac.new(s3_signing_key(config["secret_key"], date_stamp, config["region"]), string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
    authorization = f"AWS4-HMAC-SHA256 Credential={config['access_key']}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}"
    request = urlrequest.Request(url, method="HEAD", headers={"Authorization": authorization, "x-amz-content-sha256": "UNSIGNED-PAYLOAD", "x-amz-date": amz_date})
    try:
        with urlrequest.urlopen(request, timeout=15) as response:
            return int(response.headers.get("Content-Length", "0")), response.headers.get_content_type()
    except (OSError, ValueError) as error:
        raise ValueError("Не удалось проверить загруженный файл в S3.") from error


CHANNEL_MANAGER_ROLES = {"owner", "admin", "author"}
LEVEL_LIMIT_KEYS = {
    "maxStars", "messagesPerDay", "storiesPerDay", "storiesPerMonth", "postsPerDay",
    "communitiesJoined", "communitiesCreated",
    "channelsJoined", "channelsCreated", "savedAccounts", "autopostSourcesTotal", "autopostSourcesPerChannel",
}
ACTIVITY_METRIC_KEYS = {
    "stars_balance", "direct_chats", "channels_joined", "channel_subscriptions", "communities_joined",
    "channels_created", "communities_created", "channel_subscribers",
    "community_subscribers", "messages", "posts", "channel_comments_written", "stories", "reviews",
    "donations_sent", "stars_donated", "donations_received", "login_streak", "completed_calls",
    "call_partners", "chat_pro_review_video",
}
LEVEL_CRITERIA_KEYS = ACTIVITY_METRIC_KEYS | {"communities", "channels"}
DEFAULT_UI_APPEARANCE = {"outlineColor": "#65ddf8", "glowColor": "#21d5f0", "glowIntensity": 35}
DEFAULT_PUBLIC_BRANDING = {"loginLogoData": ""}
LOGIN_LOGO_MAX_BYTES = 2_500_000
CHANNEL_REACTION_OPTIONS = ("👍", "❤️", "🔥", "👏", "🤩", "⚡", "🎉", "😍", "😢", "🤔", "👎", "💯")
DEFAULT_CHANNEL_REACTIONS = ("👍", "❤️", "🔥", "👏", "🤩", "⚡")
DEFAULT_STAR_PACKAGES = [
    {"id": "stars-100", "stars": 100, "price": "99.00"},
    {"id": "stars-550", "stars": 550, "price": "449.00"},
    {"id": "stars-1200", "stars": 1200, "price": "899.00"},
]
DEFAULT_CHANNEL_MONETIZATION = {
    "starRateRubles": "0.50",
    "tiers": [
        {"minSubscribers": 1, "maxSubscribers": 101, "percent": 1},
        {"minSubscribers": 101, "maxSubscribers": 501, "percent": 10},
        {"minSubscribers": 501, "maxSubscribers": None, "percent": 20},
    ],
}
DEFAULT_CHANNEL_ACTIVITY_REGULATOR = {
    "enabled": True,
    "viewRatePercent": 35.0,
    "reactionRatePercent": 4.0,
    "weeklyUnsubscribePercent": 1.0,
    "initialUnsubscribeMonths": 3,
    "settledWeeklyUnsubscribePercent": 0.1,
}
MONETIZED_CHAT_TYPES = ("channel", "group", "community")
DEFAULT_PUBLIC_LEGAL = {
    "sellerStatus": "самозанятый", "sellerName": "Ковнерев Андрей Александрович", "inn": "440601014935",
    "vkUrl": "https://vk.ru/id_ne_naidi", "telegram": "Qwerty248i", "email": "andreikovnerev333@gmail.com",
    "purchaseDescription": "Пользователь приобретает внутренние звёзды Chat-Pro для доступа к доступным функциям аккаунта: Premium, повышению уровня аккаунта, увеличению лимитов и функциям автопостинга в соцсети. Доступность, стоимость и лимиты конкретных функций устанавливаются в интерфейсе сервиса.",
    "refundTerms": "Обращение по возврату принимается на andreikovnerev333@gmail.com. Возврат рассматривается, если деньги были списаны, но звёзды не начислены, либо оплаченная функция не предоставлена по вине сервиса. Если платёж не был успешно завершён и списание не произошло, возврат не требуется. При технической ошибке сервиса средства возвращаются или звёзды начисляются после проверки платежа.",
    "userAgreementUrl": "/requisites#user-agreement", "purchaseTermsUrl": "/requisites#purchase-terms", "privacyPolicyUrl": "/requisites#privacy-policy",
    "userAgreementText": "ПОЛЬЗОВАТЕЛЬСКОЕ СОГЛАШЕНИЕ CHAT-PRO\n\nДата публикации: 21 августа 2026 года\n\n1. ОБЩИЕ ПОЛОЖЕНИЯ\n1.1. Настоящее соглашение определяет условия использования сервиса Chat-Pro (далее — Сервис), доступного по адресу chat-pro-ru.space. Администратор Сервиса — самозанятый Ковнерев Андрей Александрович, ИНН 440601014935 (далее — Администратор).\n1.2. Регистрация, вход в аккаунт или фактическое использование Сервиса означает принятие настоящего соглашения. Если пользователь не согласен с его условиями, он обязан прекратить использование Сервиса.\n1.3. Сервис предоставляет функции обмена сообщениями, создания групп, сообществ и каналов, публикации материалов, работы со звёздами, уровнями аккаунта, Premium и иными доступными функциями. Состав функций может изменяться.\n\n2. ВОЗРАСТ И АККАУНТ\n2.1. Самостоятельно пользоваться Сервисом могут лица, достигшие 14 лет. Пользователь от 14 до 18 лет подтверждает, что при необходимости получил согласие законного представителя.\n2.2. Пользователь обязан указывать достоверные данные, обеспечивать сохранность пароля и не передавать доступ к аккаунту третьим лицам. Все действия, совершённые через аккаунт до сообщения о его компрометации, считаются действиями пользователя.\n2.3. Администратор вправе ограничить, приостановить или удалить аккаунт при нарушении настоящего соглашения, требований закона, прав третьих лиц или безопасности Сервиса.\n\n3. ПРАВИЛА ИСПОЛЬЗОВАНИЯ\n3.1. Пользователь самостоятельно отвечает за сообщения, файлы, публикации, ссылки и иные материалы, которые он размещает или направляет через Сервис.\n3.2. Запрещается размещать незаконные материалы, нарушать авторские и иные права третьих лиц, распространять вредоносное ПО, спам, персональные данные третьих лиц без основания, угрозы, оскорбления, материалы с призывами к противоправным действиям, а также обходить технические ограничения Сервиса.\n3.3. При использовании автопостинга пользователь подтверждает наличие прав и законных оснований на подключение источника и публикацию импортируемых материалов.\n3.4. Администратор не является автором пользовательских материалов и не несёт ответственности за их содержание, однако вправе удалить или ограничить доступ к материалу при получении обоснованной жалобы или выявлении нарушения.\n\n4. ДОСТУПНОСТЬ И БЕЗОПАСНОСТЬ\n4.1. Сервис предоставляется по принципу «как есть». Администратор принимает разумные меры для его работоспособности, но не гарантирует отсутствие технических перерывов, ошибок или совместимость со всеми устройствами и программами.\n4.2. Передача данных между браузером и Сервисом выполняется по защищённому соединению HTTPS. Сквозное шифрование сообщений не заявляется, если оно прямо не обозначено в интерфейсе отдельной функции.\n4.3. Пользователь обязан самостоятельно создавать резервные копии значимых материалов, если это допускает функциональность Сервиса.\n\n5. ЗВЁЗДЫ И ПЛАТНЫЕ ФУНКЦИИ\n5.1. Звёзды являются внутренними цифровыми единицами Сервиса, не являются денежными средствами, электронной валютой или банковским счётом. Порядок их покупки и использования установлен условиями покупки.\n5.2. Лимиты функций, стоимость звёзд, Premium и уровней аккаунта отображаются в интерфейсе Сервиса и могут меняться для будущих операций.\n\n6. ОБРАБОТКА ДАННЫХ И ОБРАЩЕНИЯ\n6.1. Порядок обработки данных изложен в Политике обработки персональных данных, являющейся частью настоящего соглашения.\n6.2. По вопросам Сервиса, платежей, возвратов и нарушений можно обратиться по адресу andreikovnerev333@gmail.com.\n\n7. ЗАКЛЮЧИТЕЛЬНЫЕ ПОЛОЖЕНИЯ\n7.1. Администратор может изменять настоящее соглашение. Новая редакция публикуется на этой странице и применяется с момента публикации, если не указан иной срок.\n7.2. К отношениям сторон применяется законодательство Российской Федерации с учётом обязательных норм страны пользователя, если они применимы.",
    "purchaseTermsText": "УСЛОВИЯ ПОКУПКИ ЗВЁЗД CHAT-PRO\n\nДата публикации: 21 августа 2026 года\n\n1. ПРЕДМЕТ ПОКУПКИ\n1.1. Пользователь приобретает внутренние звёзды Chat-Pro в количестве и по цене, указанным на странице оплаты перед её подтверждением. Продавец — самозанятый Ковнерев Андрей Александрович, ИНН 440601014935.\n1.2. Звёзды могут использоваться только внутри Chat-Pro для доступных функций аккаунта, включая Premium, уровни аккаунта, увеличение лимитов и функции автопостинга, если такие функции доступны пользователю. Конкретные лимиты и стоимость определяются настройками Сервиса и показываются пользователю до совершения операции.\n1.3. Звёзды не являются деньгами, не обмениваются на наличные или безналичные денежные средства, не подлежат переводу за пределы Сервиса и не предоставляют имущественных прав вне Chat-Pro.\n\n2. ОПЛАТА И НАЧИСЛЕНИЕ\n2.1. Оплата проводится на защищённой странице платёжного партнёра. Сервис не получает и не хранит реквизиты банковской карты пользователя.\n2.2. Звёзды начисляются только после подтверждения успешной оплаты платёжным сервисом. Время начисления может зависеть от обработки платежа и технических обстоятельств.\n2.3. До подтверждения оплаты пользователь видит количество звёзд, цену в рублях и ссылку на условия покупки. Нажатие кнопки перехода к оплате после принятия условий означает согласие с этими условиями.\n\n3. ИСПОЛЬЗОВАНИЕ ЗВЁЗД\n3.1. После списания звёзд за цифровую функцию результат операции отображается в интерфейсе Сервиса.\n3.2. Если функция временно недоступна по технической причине, пользователь может обратиться в поддержку для проверки операции.\n3.3. Стоимость будущих пакетов и функций может меняться. Изменение не влияет на уже начисленные звёзды и уже оплаченные операции, кроме случаев исправления очевидной технической ошибки.\n\n4. ВОЗВРАТ И РАССМОТРЕНИЕ ОБРАЩЕНИЙ\n4.1. Обращение по вопросам оплаты и возврата направляется на andreikovnerev333@gmail.com с описанием проблемы, датой, суммой и, при наличии, идентификатором платежа. Не направляйте полные данные банковской карты.\n4.2. Возврат рассматривается, если денежные средства были списаны, но звёзды не начислены, либо оплаченная цифровая функция не была предоставлена по вине Сервиса. Перед решением Администратор вправе сверить статус платежа с платёжным сервисом.\n4.3. Если платёж не был завершён и списания денежных средств не произошло, возврат не требуется. Если банк временно зарезервировал сумму, сроки её разблокировки определяются банком или платёжным сервисом.\n4.4. Решение по обращению принимается в разумный срок после получения данных, необходимых для проверки. Права пользователя, предусмотренные применимым законодательством, не ограничиваются настоящими условиями.\n\n5. ЗАКЛЮЧИТЕЛЬНЫЕ ПОЛОЖЕНИЯ\n5.1. Эти условия являются частью пользовательского соглашения Chat-Pro.\n5.2. Актуальная редакция всегда размещается на этой странице. Для будущих покупок применяется редакция, опубликованная на момент перехода к оплате.",
    "privacyPolicyText": "ПОЛИТИКА ОБРАБОТКИ ПЕРСОНАЛЬНЫХ ДАННЫХ CHAT-PRO\n\nДата публикации: 21 августа 2026 года\n\n1. ОПЕРАТОР И ОБЛАСТЬ ПРИМЕНЕНИЯ\n1.1. Оператором персональных данных является самозанятый Ковнерев Андрей Александрович, ИНН 440601014935, e-mail: andreikovnerev333@gmail.com (далее — Оператор).\n1.2. Политика применяется к данным пользователей сайта и Сервиса Chat-Pro.\n\n2. КАКИЕ ДАННЫЕ ОБРАБАТЫВАЮТСЯ\n2.1. Оператор может обрабатывать: имя, username, адрес e-mail или номер телефона, пароль в защищённом виде, сообщения, файлы и иные материалы, которые пользователь размещает в Сервисе, сведения о действиях в Сервисе, IP-адрес, сведения браузера и устройства, технические журналы, а также данные обращений в поддержку.\n2.2. Платёжные реквизиты банковских карт не обрабатываются и не хранятся Оператором; оплату обрабатывает платёжный партнёр на своей защищённой странице.\n\n3. ЦЕЛИ И ОСНОВАНИЯ ОБРАБОТКИ\n3.1. Данные используются для регистрации и работы аккаунта, подтверждения контакта, предоставления функций Сервиса, обеспечения безопасности, предотвращения нарушений, ответа на обращения, исполнения пользовательского соглашения, выполнения требований законодательства и урегулирования споров.\n3.2. Основанием обработки являются согласие пользователя, исполнение договора с пользователем, законный интерес Оператора по защите Сервиса, а также обязанности, установленные применимым законодательством.\n\n4. ХРАНЕНИЕ И ЗАЩИТА\n4.1. Данные хранятся в течение срока, необходимого для работы Сервиса, исполнения соглашения, рассмотрения обращений и выполнения обязанностей, предусмотренных законом. Сообщения, файлы и технические журналы могут храниться в том числе для обеспечения безопасности и исполнения требований законодательства; при наличии соответствующей обязанности срок хранения может составлять до 6 месяцев или иной срок, установленный законом.\n4.2. Оператор применяет организационные и технические меры защиты, включая разграничение доступа и защищённое HTTPS-соединение при передаче данных. Сквозное шифрование сообщений не заявляется, если это прямо не обозначено в интерфейсе отдельной функции.\n4.3. Пользователь понимает, что абсолютная безопасность в сети Интернет не может быть гарантирована.\n\n5. ПЕРЕДАЧА ДАННЫХ\n5.1. Данные могут быть переданы лицам, которые обеспечивают техническую работу Сервиса, хостинг, доставку e-mail, обработку платежей или поддержку, только в объёме, необходимом для соответствующей цели и при наличии правового основания.\n5.2. Данные также могут быть предоставлены государственным органам в случаях и порядке, предусмотренных законодательством.\n5.3. Сервис доступен пользователям за пределами России. При использовании Сервиса пользователь понимает, что обработка может затрагивать трансграничную передачу данных, если это необходимо для работы используемой инфраструктуры и допускается применимым законодательством.\n\n6. ПРАВА ПОЛЬЗОВАТЕЛЯ\n6.1. Пользователь вправе запросить сведения об обработке своих данных, уточнить их, отозвать согласие в случаях, когда обработка основана на согласии, а также обратиться с вопросом или жалобой по адресу andreikovnerev333@gmail.com.\n6.2. Удаление аккаунта или отдельных данных может быть ограничено, если их хранение необходимо для исполнения закона, предотвращения злоупотреблений, защиты прав Оператора или третьих лиц.\n\n7. ИЗМЕНЕНИЕ ПОЛИТИКИ\n7.1. Оператор может обновлять Политику. Новая редакция публикуется на этой странице и действует с момента публикации, если не указан иной срок.",
    "starPackages": DEFAULT_STAR_PACKAGES,
}


def nonnegative_int(value, field_name: str, maximum: int = 1_000_000) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"Поле «{field_name}» должно быть целым числом.") from None
    if parsed < 0 or parsed > maximum:
        raise ValueError(f"Поле «{field_name}» должно быть от 0 до {maximum}.")
    return parsed


def normalize_channel_reactions(value) -> list[str]:
    if not isinstance(value, list):
        raise ValueError("Реакции каналов должны быть списком.")
    reactions = []
    for item in value:
        emoji = str(item)
        if emoji not in CHANNEL_REACTION_OPTIONS:
            raise ValueError("Выбрана неподдерживаемая реакция канала.")
        if emoji not in reactions:
            reactions.append(emoji)
    if not reactions:
        raise ValueError("Выберите хотя бы одну реакцию для каналов.")
    return reactions


def channel_reaction_emojis(con: sqlite3.Connection) -> tuple[str, ...]:
    row = con.execute("SELECT value FROM settings WHERE key = 'channel_reactions'").fetchone()
    try:
        reactions = normalize_channel_reactions(loads(row["value"], []) if row else list(DEFAULT_CHANNEL_REACTIONS))
    except ValueError:
        reactions = list(DEFAULT_CHANNEL_REACTIONS)
    return tuple(reactions)


def normalize_channel_activity_regulator(value) -> dict:
    if not isinstance(value, dict):
        raise ValueError("Настройки регулятора активности должны быть объектом.")
    allowed = set(DEFAULT_CHANNEL_ACTIVITY_REGULATOR)
    unknown = set(value) - allowed
    if unknown:
        raise ValueError("В настройках регулятора активности есть неподдерживаемые поля.")

    def percentage(key: str) -> float:
        try:
            result = float(value.get(key, DEFAULT_CHANNEL_ACTIVITY_REGULATOR[key]))
        except (TypeError, ValueError):
            raise ValueError(f"Поле «{key}» должно быть числом.") from None
        if not math.isfinite(result) or result < 0 or result > 100:
            raise ValueError(f"Поле «{key}» должно быть от 0 до 100.")
        return round(result, 2)

    return {
        "enabled": bool(value.get("enabled", DEFAULT_CHANNEL_ACTIVITY_REGULATOR["enabled"])),
        "viewRatePercent": percentage("viewRatePercent"),
        "reactionRatePercent": percentage("reactionRatePercent"),
        "weeklyUnsubscribePercent": percentage("weeklyUnsubscribePercent"),
        "initialUnsubscribeMonths": nonnegative_int(
            value.get("initialUnsubscribeMonths", DEFAULT_CHANNEL_ACTIVITY_REGULATOR["initialUnsubscribeMonths"]),
            "initialUnsubscribeMonths", 120,
        ),
        "settledWeeklyUnsubscribePercent": percentage("settledWeeklyUnsubscribePercent"),
    }


def channel_activity_regulator_settings(con: sqlite3.Connection) -> dict:
    row = con.execute("SELECT value FROM settings WHERE key = 'channel_activity_regulator'").fetchone()
    try:
        return normalize_channel_activity_regulator(loads(row["value"], {}) if row else DEFAULT_CHANNEL_ACTIVITY_REGULATOR)
    except ValueError:
        return DEFAULT_CHANNEL_ACTIVITY_REGULATOR.copy()


def normalize_ui_appearance(value) -> dict:
    if not isinstance(value, dict):
        raise ValueError("Настройки подсветки должны быть объектом.")
    unknown = set(value) - {"outlineColor", "glowColor", "glowIntensity"}
    if unknown:
        raise ValueError("В настройках подсветки есть неподдерживаемые поля.")
    outline_color = str(value.get("outlineColor", DEFAULT_UI_APPEARANCE["outlineColor"]))
    glow_color = str(value.get("glowColor", DEFAULT_UI_APPEARANCE["glowColor"]))
    if not all(re.fullmatch(r"#[0-9a-fA-F]{6}", color) for color in (outline_color, glow_color)):
        raise ValueError("Выберите корректные цвета подсветки.")
    return {
        "outlineColor": outline_color.lower(),
        "glowColor": glow_color.lower(),
        "glowIntensity": nonnegative_int(value.get("glowIntensity", DEFAULT_UI_APPEARANCE["glowIntensity"]), "glowIntensity", 100),
    }


def normalize_image_data(value, maximum_bytes: int, field_name: str) -> str:
    data = str(value or "").strip()
    match = re.fullmatch(r"data:image/(png|jpe?g|webp);base64,([A-Za-z0-9+/]*={0,2})", data, re.IGNORECASE)
    if not match:
        raise ValueError(f"{field_name} должен быть в формате PNG, JPG или WebP.")
    image_type = "jpeg" if match.group(1).lower() in ("jpg", "jpeg") else match.group(1).lower()
    try:
        image = base64.b64decode(match.group(2), validate=True)
    except (ValueError, binascii.Error):
        raise ValueError(f"Не удалось прочитать {field_name.lower()}.") from None
    if len(image) > maximum_bytes:
        raise ValueError(f"Размер файла не должен превышать {maximum_bytes / 1_000_000:g} МБ.")
    signatures = {
        "png": b"\x89PNG\r\n\x1a\n",
        "jpeg": b"\xff\xd8\xff",
        "webp": b"RIFF",
    }
    valid = image.startswith(signatures[image_type])
    if image_type == "webp":
        valid = valid and image[8:12] == b"WEBP"
    if not valid:
        raise ValueError(f"Файл не является корректным изображением {image_type.upper()}.")
    return f"data:image/{image_type};base64,{match.group(2)}"


def normalize_public_branding(value) -> dict:
    if value in (None, ""):
        value = {}
    if not isinstance(value, dict) or set(value) - set(DEFAULT_PUBLIC_BRANDING):
        raise ValueError("Настройки логотипа содержат неподдерживаемые поля.")
    logo_data = str(value.get("loginLogoData", "")).strip()
    if not logo_data:
        return DEFAULT_PUBLIC_BRANDING.copy()
    return {"loginLogoData": normalize_image_data(logo_data, LOGIN_LOGO_MAX_BYTES, "Логотип")}


def normalize_star_packages(value) -> list[dict]:
    if not isinstance(value, list) or not value or len(value) > 20:
        raise ValueError("Укажите от одного до 20 пакетов звёзд.")
    normalized, package_ids = [], set()
    for package in value:
        if not isinstance(package, dict):
            raise ValueError("Каждый пакет звёзд должен быть объектом.")
        package_id = str(package.get("id", "")).strip().lower()
        stars = nonnegative_int(package.get("stars"), "stars", 1_000_000)
        price = normalize_money(package.get("price"), "Цена пакета", 9_999_999)
        if not re.fullmatch(r"[a-z0-9_-]{3,40}", package_id) or package_id in package_ids or not stars:
            raise ValueError("Некорректный ID или количество звёзд в пакете.")
        package_ids.add(package_id)
        normalized.append({"id": package_id, "stars": stars, "price": price})
    return normalized


def normalize_money(value, field_name: str, maximum: int = 9_999_999) -> str:
    raw = str(value if value is not None else "").strip().replace(",", ".")
    if not re.fullmatch(r"\d{1,7}(?:\.\d{1,2})?", raw):
        raise ValueError(f"Поле «{field_name}» должно быть положительной суммой в рублях, например 0.50.")
    try:
        amount = Decimal(raw)
    except InvalidOperation:
        raise ValueError(f"Поле «{field_name}» содержит некорректную сумму.") from None
    if not amount.is_finite() or amount <= 0 or amount > maximum:
        raise ValueError(f"Поле «{field_name}» должно быть больше нуля и не превышать {maximum} ₽.")
    return str(amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def normalize_channel_monetization(value) -> dict:
    if value in (None, ""):
        value = DEFAULT_CHANNEL_MONETIZATION
    if not isinstance(value, dict) or set(value) - {"starRateRubles", "tiers"}:
        raise ValueError("Настройки монетизации каналов содержат неподдерживаемые поля.")
    rate = normalize_money(value.get("starRateRubles", DEFAULT_CHANNEL_MONETIZATION["starRateRubles"]), "Цена звезды")
    raw_tiers = value.get("tiers", DEFAULT_CHANNEL_MONETIZATION["tiers"])
    if not isinstance(raw_tiers, list) or not raw_tiers or len(raw_tiers) > 30:
        raise ValueError("Укажите от одного до 30 уровней комиссии.")
    tiers, previous_max = [], None
    for index, raw_tier in enumerate(raw_tiers):
        if not isinstance(raw_tier, dict) or set(raw_tier) - {"minSubscribers", "maxSubscribers", "percent"}:
            raise ValueError("Каждый уровень комиссии должен содержать границы и процент.")
        minimum = nonnegative_int(raw_tier.get("minSubscribers"), "minSubscribers", 10_000_000)
        maximum_value = raw_tier.get("maxSubscribers")
        maximum = None if maximum_value in (None, "") else nonnegative_int(maximum_value, "maxSubscribers", 10_000_000)
        percent = nonnegative_int(raw_tier.get("percent"), "percent", 100)
        if minimum < 1 or not percent or (maximum is not None and maximum <= minimum):
            raise ValueError("Проверьте границы и процент комиссии канала.")
        if previous_max is not None and minimum < previous_max:
            raise ValueError("Уровни комиссии не должны пересекаться.")
        if maximum is None and index != len(raw_tiers) - 1:
            raise ValueError("Уровень без верхней границы должен быть последним.")
        tiers.append({"minSubscribers": minimum, "maxSubscribers": maximum, "percent": percent})
        previous_max = maximum
    return {"starRateRubles": rate, "tiers": tiers}


def normalize_public_url(value, field_name: str) -> str:
    value = str(value or "").strip()
    if not value:
        return ""
    if value.startswith("/") or urlparse(value).scheme in {"http", "https"}:
        return value[:500]
    raise ValueError(f"Поле «{field_name}» должно содержать ссылку http(s) или путь сайта.")


def normalize_public_legal(value) -> dict:
    if not isinstance(value, dict):
        raise ValueError("Публичная информация должна быть объектом.")
    unknown = set(value) - set(DEFAULT_PUBLIC_LEGAL)
    if unknown:
        raise ValueError("В публичной информации есть неподдерживаемые поля.")
    legal = {**DEFAULT_PUBLIC_LEGAL, **value}
    normalized = {
        "sellerStatus": str(legal["sellerStatus"]).strip()[:120], "sellerName": str(legal["sellerName"]).strip()[:160],
        "inn": str(legal["inn"]).strip()[:20], "vkUrl": normalize_public_url(legal["vkUrl"], "vkUrl"),
        "telegram": str(legal["telegram"]).strip().lstrip("@")[:64], "email": str(legal["email"]).strip()[:254],
        "purchaseDescription": str(legal["purchaseDescription"]).strip()[:1000], "refundTerms": str(legal["refundTerms"]).strip()[:5000],
        "userAgreementUrl": normalize_public_url(legal["userAgreementUrl"], "userAgreementUrl"),
        "purchaseTermsUrl": normalize_public_url(legal["purchaseTermsUrl"], "purchaseTermsUrl"), "privacyPolicyUrl": normalize_public_url(legal["privacyPolicyUrl"], "privacyPolicyUrl"),
        "userAgreementText": str(legal["userAgreementText"]).strip()[:10000], "purchaseTermsText": str(legal["purchaseTermsText"]).strip()[:10000],
        "privacyPolicyText": str(legal["privacyPolicyText"]).strip()[:10000],
        "starPackages": normalize_star_packages(legal["starPackages"]),
    }
    if normalized["email"] and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", normalized["email"]):
        raise ValueError("Укажите корректный e-mail для публичной страницы.")
    if normalized["inn"] and not re.fullmatch(r"\d{10}|\d{12}", normalized["inn"]):
        raise ValueError("ИНН должен состоять из 10 или 12 цифр.")
    return normalized


def normalize_level_reward(value, field_name: str) -> dict:
    if value in (None, ""):
        value = {}
    if not isinstance(value, dict):
        raise ValueError(f"Поле «{field_name}» должно быть объектом.")
    unknown = set(value) - {"stars", "premiumDays", "limits", "recurringStars", "recurringIntervalDays", "recurringDurationDays", "accountLevelId", "recommendOwnChannel", "starPackageDiscountPercent"}
    if unknown:
        raise ValueError("В награде указаны неподдерживаемые поля.")
    limits = value.get("limits", {})
    if not isinstance(limits, dict) or set(limits) - LEVEL_LIMIT_KEYS:
        raise ValueError("В награде указаны неподдерживаемые лимиты.")
    recurring_stars = nonnegative_int(value.get("recurringStars", 0), "recurringStars")
    recurring_interval_days = nonnegative_int(value.get("recurringIntervalDays", 0), "recurringIntervalDays", 365)
    recurring_duration_days = nonnegative_int(value.get("recurringDurationDays", 0), "recurringDurationDays", 3650)
    if recurring_stars and (not recurring_interval_days or not recurring_duration_days):
        raise ValueError("Для периодических звёзд укажите интервал и срок действия.")
    if (recurring_interval_days or recurring_duration_days) and not recurring_stars:
        raise ValueError("Укажите количество периодических звёзд.")
    account_level_id = str(value.get("accountLevelId", "") or "").strip().lower()
    if account_level_id and not re.fullmatch(r"[a-z0-9_-]{2,40}", account_level_id):
        raise ValueError("ID уровня в награде указан некорректно.")
    recommend_own_channel = value.get("recommendOwnChannel", False)
    if not isinstance(recommend_own_channel, bool):
        raise ValueError("Параметр рекомендации канала должен быть логическим значением.")
    return {
        "stars": nonnegative_int(value.get("stars", 0), "stars"),
        "premiumDays": nonnegative_int(value.get("premiumDays", 0), "premiumDays", 3650),
        "limits": {key: nonnegative_int(limits[key], key) for key in limits},
        "recurringStars": recurring_stars,
        "recurringIntervalDays": recurring_interval_days,
        "recurringDurationDays": recurring_duration_days,
        "accountLevelId": account_level_id,
        "recommendOwnChannel": recommend_own_channel,
        "starPackageDiscountPercent": nonnegative_int(value.get("starPackageDiscountPercent", 0), "starPackageDiscountPercent", 99),
    }


def normalize_account_levels(value) -> list[dict]:
    if not isinstance(value, list) or not value:
        raise ValueError("Укажите от одного до 20 уровней аккаунта.")
    if len(value) > 20:
        raise ValueError("Можно настроить не более 20 уровней аккаунта.")
    levels = []
    ids = set()
    for raw_level in value:
        if not isinstance(raw_level, dict):
            raise ValueError("Каждый уровень должен быть объектом.")
        level_id = str(raw_level.get("id", "")).strip().lower()
        if not re.fullmatch(r"[a-z0-9_-]{2,40}", level_id):
            raise ValueError("ID уровня: от 2 до 40 латинских символов, цифр, _ или -.")
        if level_id in ids:
            raise ValueError("ID уровней не должны повторяться.")
        ids.add(level_id)
        title = str(raw_level.get("title", "")).strip()
        if not title or len(title) > 120:
            raise ValueError("Название уровня должно содержать от 1 до 120 символов.")
        description = str(raw_level.get("description", "")).strip()
        if len(description) > 1000:
            raise ValueError("Описание уровня не должно превышать 1000 символов.")
        criteria = raw_level.get("criteria", {})
        limits = raw_level.get("limits", {})
        if not isinstance(criteria, dict) or not isinstance(limits, dict):
            raise ValueError("Критерии и лимиты уровня должны быть объектами.")
        unknown_criteria = set(criteria) - LEVEL_CRITERIA_KEYS - {"groups", "groups_created", "groups_joined", "group_subscribers"}
        unknown_limits = set(limits) - LEVEL_LIMIT_KEYS - {"groupsJoined", "groupsCreated"}
        if unknown_criteria or unknown_limits:
            raise ValueError("В уровне есть неподдерживаемые критерии или лимиты.")
        normalized_criteria = {
            key: nonnegative_int(criteria[key], key)
            for key in criteria if key in LEVEL_CRITERIA_KEYS and nonnegative_int(criteria[key], key)
        }
        normalized_limits = {key: nonnegative_int(limits[key], key) for key in limits if key in LEVEL_LIMIT_KEYS}
        monthly_price_raw = str(raw_level.get("monthlyPrice", "0") if raw_level.get("monthlyPrice") is not None else "").strip().replace(",", ".")
        if not monthly_price_raw:
            monthly_price = "0.00"
        else:
            try:
                is_zero_monthly_price = Decimal(monthly_price_raw) == 0
            except InvalidOperation:
                monthly_price = normalize_money(monthly_price_raw, "monthlyPrice")
            else:
                monthly_price = "0.00" if is_zero_monthly_price else normalize_money(monthly_price_raw, "monthlyPrice")
        levels.append({
            "id": level_id,
            "title": title,
            "description": description,
            "criteria": normalized_criteria,
            "limits": normalized_limits,
            "reward": normalize_level_reward(raw_level.get("reward", {}), "reward"),
            "starsPrice": nonnegative_int(raw_level.get("starsPrice", 0), "starsPrice"),
            "monthlyPrice": monthly_price,
            "purchaseReward": normalize_level_reward(raw_level.get("purchaseReward", {}), "purchaseReward"),
        })
    return levels


def now() -> int:
    return int(time.time())


CHANNEL_POSTS_PER_DAY = 5


def channel_post_limit_reached(con: sqlite3.Connection, channel_id: str, current: int | None = None) -> bool:
    current = current or now()
    start_of_day = int(datetime.datetime.fromtimestamp(current).replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
    published = con.execute(
        """SELECT count(*) AS count FROM messages
           WHERE chat_id = ? AND created_at >= ? AND deleted_by_admin = 0
             AND COALESCE(media_type, '') != 'system'""",
        (channel_id, start_of_day),
    ).fetchone()["count"]
    return published >= CHANNEL_POSTS_PER_DAY


def enforce_channel_post_limit(con: sqlite3.Connection, channel_id: str, current: int | None = None) -> None:
    if channel_post_limit_reached(con, channel_id, current):
        raise ValueError(f"В канале можно публиковать до {CHANNEL_POSTS_PER_DAY} постов за текущий день.")


def connect() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH, timeout=10)
    con.row_factory = sqlite3.Row
    con.create_function("casefold", 1, lambda value: str(value or "").casefold())
    con.execute("PRAGMA foreign_keys = ON")
    return con


def dumps(value) -> str:
    return json.dumps(value, ensure_ascii=False)


def loads(value, default=None):
    if value in (None, ""):
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def yookassa_star_packages(con: sqlite3.Connection | None = None) -> list[dict]:
    if con:
        row = con.execute("SELECT value FROM settings WHERE key = 'public_legal'").fetchone()
        legal = loads(row["value"], {}) if row else {}
        if isinstance(legal, dict) and legal.get("starPackages"):
            return normalize_star_packages(legal["starPackages"])
    raw_packages = os.environ.get("YOOKASSA_STAR_PACKAGES", "")
    return normalize_star_packages(loads(raw_packages, None) if raw_packages else DEFAULT_STAR_PACKAGES)


def discounted_price(price: str, discount_percent: int) -> str:
    amount = Decimal(price)
    multiplier = Decimal(100 - discount_percent) / Decimal(100)
    return str((amount * multiplier).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def yookassa_configured() -> bool:
    return bool(YOOKASSA_SHOP_ID and YOOKASSA_SECRET_KEY and YOOKASSA_RETURN_URL)


def yookassa_request(path: str, method: str = "GET", payload: dict | None = None, idempotence_key: str | None = None) -> dict:
    if not yookassa_configured():
        raise ValueError("Оплата ЮKassa пока не настроена на сервере.")
    credentials = base64.b64encode(f"{YOOKASSA_SHOP_ID}:{YOOKASSA_SECRET_KEY}".encode("utf-8")).decode("ascii")
    data = dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Authorization": f"Basic {credentials}", "Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    if idempotence_key:
        headers["Idempotence-Key"] = idempotence_key
    request = urlrequest.Request(f"https://api.yookassa.ru/v3{path}", data=data, headers=headers, method=method)
    try:
        with urlrequest.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urlerror.URLError, urlerror.HTTPError, json.JSONDecodeError) as error:
        raise ValueError("Не удалось подтвердить операцию в ЮKassa. Попробуйте позже.") from error


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 210_000)
    return f"pbkdf2_sha256${salt.hex()}${digest.hex()}"


def password_matches(stored: str, candidate: str) -> bool:
    if not stored.startswith("pbkdf2_sha256$"):
        return secrets.compare_digest(stored, candidate)
    try:
        _, salt_hex, digest_hex = stored.split("$", 2)
        expected = bytes.fromhex(digest_hex)
        actual = hashlib.pbkdf2_hmac("sha256", candidate.encode("utf-8"), bytes.fromhex(salt_hex), 210_000)
        return secrets.compare_digest(expected, actual)
    except ValueError:
        return False


def normalize_email(value) -> str:
    email = str(value or "").strip().lower()
    if len(email) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise ValueError("Введите корректный e-mail.")
    return email


def generate_auth_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def deliver_email_code(email: str, code: str, purpose: str) -> None:
    subject = "Код подтверждения Chat-Pro"
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = SMTP_FROM
    message["To"] = email
    message.set_content(f"{purpose}\n\nВаш код: {code}\nОн действует 10 минут. Никому не сообщайте этот код.")
    if not all((SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD, SMTP_FROM)):
        raise ValueError("Отправка e-mail пока не настроена. Обратитесь к администрации сайта.")
    try:
        client_class = smtplib.SMTP_SSL if SMTP_USE_SSL else smtplib.SMTP
        with client_class(SMTP_HOST, SMTP_PORT, timeout=15) as client:
            if not SMTP_USE_SSL:
                client.starttls()
            client.login(SMTP_USERNAME, SMTP_PASSWORD)
            client.send_message(message)
    except (OSError, smtplib.SMTPException) as error:
        raise ValueError("Не удалось отправить код на e-mail. Попробуйте позже.") from error


def public_user(row: sqlite3.Row | dict | None) -> dict | None:
    if not row:
        return None
    return {
        "id": row["id"],
        "name": row["name"],
        "username": row["username"],
        "stars": row["stars"],
        "theme": row["theme"],
        "siteColor": row["site_color"],
        "siteBackground": row["site_background"],
        "siteBackgroundData": row["site_background_data"],
        "dialogColor": row["dialog_color"],
        "otherDialogColor": row["other_dialog_color"],
        "dialogPanelColor": row["dialog_panel_color"],
        "dialogPanelStyle": row["dialog_panel_style"],
        "dialogBubbleStyle": row["dialog_bubble_style"],
        "dialogFont": row["dialog_font"],
        "textScale": row["text_scale"] if "text_scale" in row.keys() else "system",
        "chatBackground": row["chat_background"],
        "chatBackgroundData": row["chat_background_data"],
        "sidebarBackgroundData": row["sidebar_background_data"],
        "nightAppearanceCustom": bool(row["night_appearance_custom"]) if "night_appearance_custom" in row.keys() else False,
        "nightOutlineColor": row["night_outline_color"] if "night_outline_color" in row.keys() else None,
        "nightGlowColor": row["night_glow_color"] if "night_glow_color" in row.keys() else None,
        "nightGlowIntensity": row["night_glow_intensity"] if "night_glow_intensity" in row.keys() else None,
        "callRingtone": row["call_ringtone"] if "call_ringtone" in row.keys() else "classic",
        "hiddenStatusIds": loads(row["hidden_status_ids"], []),
        "groupInvitePrivacy": row["group_invite_privacy"] if "group_invite_privacy" in row.keys() else "contacts",
        "directMessagePrivacy": row["direct_message_privacy"] if "direct_message_privacy" in row.keys() else "everyone",
        "profileDescription": row["profile_description"] if "profile_description" in row.keys() else "",
        "avatarData": row["avatar_data"],
        "createdAt": row["created_at"],
    }


def chat_to_dict(row: sqlite3.Row) -> dict:
    settings = loads(row["settings_json"], {})
    return {
        "id": row["id"],
        "type": row["type"],
        "title": row["title"],
        "description": row["description"],
        "avatarData": row["avatar_data"] if "avatar_data" in row.keys() else None,
        "inviteCode": row["invite_code"] if "invite_code" in row.keys() else None,
        "ownerId": row["owner_id"],
        "settings": settings,
        "subscriberCount": row["subscriber_count"] + row["subscriber_boost"],
        "subscriberBoost": row["subscriber_boost"],
        "pinned": bool(row["pinned"]) if "pinned" in row.keys() else False,
        "archived": bool(row["archived"]) if "archived" in row.keys() else False,
        "unreadCount": int(row["unread_count"]) if "unread_count" in row.keys() else 0,
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
    }


def message_to_dict(row: sqlite3.Row) -> dict:
    reactions = loads(row["reactions_json"], {}) or {}
    return {
        "id": row["id"],
        "chatId": row["chat_id"],
        "senderId": row["sender_id"],
        "profileUserId": row["profile_user_id"] if "profile_user_id" in row.keys() else None,
        "text": row["text"],
        "mediaType": row["media_type"],
        "hasMedia": bool(row["has_media"]) if "has_media" in row.keys() else bool(row["media_data"]) if "media_data" in row.keys() else False,
        "mediaEmbedUrl": row["media_embed_url"] if "media_embed_url" in row.keys() else None,
        "voiceWaveform": loads(row["voice_waveform_json"], []) if "voice_waveform_json" in row.keys() else [],
        "views": int(row["views"] or 0) + int(row["views_boost"] or 0) if "views" in row.keys() else 0,
        "reactions": reactions,
        "reactionTotal": sum(int(v) for v in reactions.values()),
        "pinned": bool(row["pinned"]),
        "pinHidden": bool(row["pin_hidden"]) if "pin_hidden" in row.keys() else False,
        "forwardedFrom": row["forwarded_from"] if "forwarded_from" in row.keys() else None,
        "forwardedFromUserId": row["forwarded_from_user_id"] if "forwarded_from_user_id" in row.keys() else None,
        "sourceType": row["source_type"] if "source_type" in row.keys() else None,
        "sourceId": row["source_id"] if "source_id" in row.keys() else None,
        "aiAgent": bool(row["ai_agent"]) if "ai_agent" in row.keys() else False,
        "replyToId": row["reply_to_id"] if "reply_to_id" in row.keys() else None,
        "editedAt": row["edited_at"] if "edited_at" in row.keys() else None,
        "unread": bool(row["is_unread"]) if "is_unread" in row.keys() else False,
        "readByRecipient": bool(row["is_read_by_recipient"]) if "is_read_by_recipient" in row.keys() else False,
        "createdAt": row["created_at"],
    }


def init_db() -> None:
    with connect() as con:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
              id TEXT PRIMARY KEY,
              name TEXT NOT NULL,
              username TEXT NOT NULL UNIQUE,
              password TEXT NOT NULL,
              email TEXT,
              phone TEXT,
              email_verified INTEGER NOT NULL DEFAULT 0,
              phone_verified INTEGER NOT NULL DEFAULT 0,
              stars INTEGER NOT NULL DEFAULT 0,
              premium_until INTEGER,
              theme TEXT NOT NULL DEFAULT 'light',
              site_color TEXT NOT NULL DEFAULT '#2aabee',
              site_background TEXT NOT NULL DEFAULT 'default',
              site_background_data TEXT,
              dialog_color TEXT NOT NULL DEFAULT '#dff9f9',
              other_dialog_color TEXT NOT NULL DEFAULT '#dff9f9',
              dialog_panel_color TEXT NOT NULL DEFAULT '#f4f8fc',
              dialog_panel_style TEXT NOT NULL DEFAULT 'interactive-light',
              dialog_bubble_style TEXT NOT NULL DEFAULT 'custom',
              dialog_font TEXT NOT NULL DEFAULT 'business',
              text_scale TEXT NOT NULL DEFAULT 'system',
              chat_background TEXT NOT NULL DEFAULT 'cyan',
              chat_background_data TEXT,
              sidebar_background_data TEXT,
              night_appearance_custom INTEGER NOT NULL DEFAULT 0,
              night_outline_color TEXT,
              night_glow_color TEXT,
              night_glow_intensity INTEGER,
               call_ringtone TEXT NOT NULL DEFAULT 'classic',
               call_ringtone_data TEXT,
               hidden_status_ids TEXT NOT NULL DEFAULT '[]',
              group_invite_privacy TEXT NOT NULL DEFAULT 'contacts',
              direct_message_privacy TEXT NOT NULL DEFAULT 'everyone',
              avatar_data TEXT,
              last_login_day TEXT,
              login_streak INTEGER NOT NULL DEFAULT 0,
              agreement_accepted_at INTEGER,
              deletion_requested_at INTEGER,
              deletion_due_at INTEGER,
              created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
              token TEXT PRIMARY KEY,
              user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS oauth_identities (
              provider TEXT NOT NULL,
              provider_user_id TEXT NOT NULL,
              user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              created_at INTEGER NOT NULL,
              updated_at INTEGER NOT NULL,
              PRIMARY KEY (provider, provider_user_id),
              UNIQUE (provider, user_id)
            );

            CREATE TABLE IF NOT EXISTS oauth_states (
              state TEXT PRIMARY KEY,
              provider TEXT NOT NULL,
              user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
              agreement_accepted INTEGER NOT NULL DEFAULT 0,
              code_verifier TEXT,
              expires_at INTEGER NOT NULL,
              created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS auth_challenges (
              id TEXT PRIMARY KEY,
              purpose TEXT NOT NULL,
              email TEXT,
              phone TEXT,
              user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
              payload_json TEXT NOT NULL DEFAULT '{}',
              email_code_hash TEXT,
              phone_code_hash TEXT,
              email_verified INTEGER NOT NULL DEFAULT 0,
              phone_verified INTEGER NOT NULL DEFAULT 0,
              attempts INTEGER NOT NULL DEFAULT 0,
              expires_at INTEGER NOT NULL,
              created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS chats (
              id TEXT PRIMARY KEY,
              type TEXT NOT NULL,
              title TEXT NOT NULL,
              description TEXT NOT NULL DEFAULT '',
              avatar_data TEXT,
              invite_code TEXT UNIQUE,
              owner_id TEXT REFERENCES users(id) ON DELETE SET NULL,
              settings_json TEXT NOT NULL DEFAULT '{}',
              subscriber_count INTEGER NOT NULL DEFAULT 0,
              subscriber_boost INTEGER NOT NULL DEFAULT 0,
              created_at INTEGER NOT NULL,
              updated_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS chat_members (
              chat_id TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
              user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              role TEXT NOT NULL DEFAULT 'member',
              created_at INTEGER NOT NULL,
              PRIMARY KEY (chat_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS channel_join_requests (
              channel_id TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
              user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              status TEXT NOT NULL CHECK(status IN ('pending', 'approved', 'rejected')) DEFAULT 'pending',
              created_at INTEGER NOT NULL,
              resolved_at INTEGER,
              resolved_by TEXT REFERENCES users(id) ON DELETE SET NULL,
              PRIMARY KEY (channel_id, user_id)
            );
            CREATE INDEX IF NOT EXISTS channel_join_requests_pending_idx ON channel_join_requests(channel_id, status, created_at);

            CREATE TABLE IF NOT EXISTS pinned_chats (
              chat_id TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
              user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              pinned_at INTEGER NOT NULL,
              PRIMARY KEY (chat_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS archived_chats (
              chat_id TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
              user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              archived_at INTEGER NOT NULL,
              PRIMARY KEY (chat_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS hidden_chats (
              chat_id TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
              user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              created_at INTEGER NOT NULL,
              PRIMARY KEY (chat_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS secret_chats (
              chat_id TEXT PRIMARY KEY REFERENCES chats(id) ON DELETE CASCADE,
              password_hash TEXT NOT NULL,
              created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS secret_chat_unlocks (
              chat_id TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
              user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              unlocked_at INTEGER NOT NULL,
              PRIMARY KEY (chat_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS messages (
              id TEXT PRIMARY KEY,
              chat_id TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
              sender_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              text TEXT NOT NULL,
              media_type TEXT,
              media_data TEXT,
              media_embed_url TEXT,
               circle_preview_data TEXT,
              voice_waveform_json TEXT,
              profile_user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
              views INTEGER NOT NULL DEFAULT 0,
              views_boost INTEGER NOT NULL DEFAULT 0,
              reactions_json TEXT NOT NULL DEFAULT '{}',
              pinned INTEGER NOT NULL DEFAULT 0,
              forwarded_from TEXT,
              forwarded_from_user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
              reply_to_id TEXT REFERENCES messages(id) ON DELETE SET NULL,
              edited_at INTEGER,
              ai_agent INTEGER NOT NULL DEFAULT 0,
              created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS ai_agent_settings (
              user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
              instruction TEXT NOT NULL DEFAULT '',
              style TEXT NOT NULL DEFAULT 'friendly',
              model_profile TEXT NOT NULL DEFAULT 'default',
              autopilot_enabled INTEGER NOT NULL DEFAULT 0,
              allowed_chat_ids_json TEXT NOT NULL DEFAULT '[]',
              template_message_ids_json TEXT NOT NULL DEFAULT '[]',
              agent_name TEXT NOT NULL DEFAULT 'ИИ-администратор',
              booking_config_json TEXT NOT NULL DEFAULT '{}',
              updated_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS ai_agent_tasks (
              id TEXT PRIMARY KEY,
              user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              title TEXT NOT NULL,
              instruction TEXT NOT NULL DEFAULT '',
              scope TEXT NOT NULL CHECK(scope IN ('all_direct', 'selected_direct')),
              chat_ids_json TEXT NOT NULL DEFAULT '[]',
              enabled INTEGER NOT NULL DEFAULT 1,
              created_at INTEGER NOT NULL,
              updated_at INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS ai_agent_tasks_user_enabled
              ON ai_agent_tasks(user_id, enabled, updated_at DESC);

            CREATE TABLE IF NOT EXISTS ai_agent_bookings (
              id TEXT PRIMARY KEY,
              owner_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              customer_user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
              source_chat_id TEXT REFERENCES chats(id) ON DELETE SET NULL,
              customer_name TEXT NOT NULL,
              contact TEXT NOT NULL DEFAULT '',
              booking_type TEXT NOT NULL,
              resource_name TEXT NOT NULL,
              start_at INTEGER NOT NULL,
              end_at INTEGER NOT NULL,
              details_json TEXT NOT NULL DEFAULT '{}',
              status TEXT NOT NULL CHECK(status IN ('pending', 'confirmed', 'cancelled')) DEFAULT 'pending',
              created_at INTEGER NOT NULL,
              updated_at INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS ai_agent_bookings_owner_time
              ON ai_agent_bookings(owner_id, start_at, resource_name);

            CREATE TABLE IF NOT EXISTS ai_agent_processed_messages (
              message_id TEXT PRIMARY KEY REFERENCES messages(id) ON DELETE CASCADE,
              processed_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS ai_agent_global_instructions (
              id TEXT PRIMARY KEY,
              title TEXT NOT NULL,
              instruction TEXT NOT NULL,
              created_by TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              created_at INTEGER NOT NULL,
              updated_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS ai_agent_conversation_messages (
              id TEXT PRIMARY KEY,
              user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
              text TEXT NOT NULL,
              created_at INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS ai_agent_conversation_messages_user_created
              ON ai_agent_conversation_messages(user_id, created_at, id);

            CREATE TABLE IF NOT EXISTS ai_agent_channel_rules (
              user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
              enabled INTEGER NOT NULL DEFAULT 0,
              target_channel_id TEXT REFERENCES chats(id) ON DELETE SET NULL,
              source_channel_ids_json TEXT NOT NULL DEFAULT '[]',
              rewrite_posts INTEGER NOT NULL DEFAULT 0,
              created_at INTEGER NOT NULL,
              updated_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS ai_agent_channel_processed_posts (
              rule_user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              message_id TEXT NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
              processed_at INTEGER NOT NULL,
              PRIMARY KEY (rule_user_id, message_id)
            );

            CREATE TABLE IF NOT EXISTS notifications (
              id TEXT PRIMARY KEY,
              user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              kind TEXT NOT NULL,
              text TEXT NOT NULL,
              target_id TEXT,
              created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS scheduled_posts (
              id TEXT PRIMARY KEY,
              chat_id TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
              sender_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              text TEXT NOT NULL DEFAULT '',
              media_type TEXT,
              media_data TEXT,
              publish_at INTEGER NOT NULL,
              created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS channel_comments (
              id TEXT PRIMARY KEY,
              message_id TEXT NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
              user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              text TEXT NOT NULL,
              media_data TEXT,
              automated INTEGER NOT NULL DEFAULT 0,
              created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS ai_agent_comment_moderation_rules (
              user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              channel_id TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
              blocked_words_json TEXT NOT NULL DEFAULT '[]',
              created_at INTEGER NOT NULL,
              updated_at INTEGER NOT NULL,
              PRIMARY KEY (user_id, channel_id)
            );

            CREATE TABLE IF NOT EXISTS ai_agent_moderated_comments (
              comment_id TEXT PRIMARY KEY,
              user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              moderated_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS ai_agent_pending_actions (
              id TEXT PRIMARY KEY,
              user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              action TEXT NOT NULL,
              payload_json TEXT NOT NULL DEFAULT '{}',
              summary TEXT NOT NULL,
              created_at INTEGER NOT NULL,
              expires_at INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS ai_agent_pending_actions_user_created
              ON ai_agent_pending_actions(user_id, created_at DESC);

            CREATE TABLE IF NOT EXISTS ai_agent_action_log (
              id TEXT PRIMARY KEY,
              user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              action TEXT NOT NULL,
              status TEXT NOT NULL,
              summary TEXT NOT NULL,
              payload_json TEXT NOT NULL DEFAULT '{}',
              result_text TEXT NOT NULL DEFAULT '',
              created_at INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS ai_agent_action_log_user_created
              ON ai_agent_action_log(user_id, created_at DESC);

            CREATE TABLE IF NOT EXISTS ai_agent_moderation_events (
              id TEXT PRIMARY KEY,
              user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              channel_id TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
              target_type TEXT NOT NULL,
              target_id TEXT NOT NULL,
              source TEXT NOT NULL DEFAULT 'chat-pro',
              text TEXT NOT NULL DEFAULT '',
              decision TEXT NOT NULL,
              reason TEXT NOT NULL DEFAULT '',
              confidence REAL,
              created_at INTEGER NOT NULL,
              resolved_at INTEGER
            );
            CREATE INDEX IF NOT EXISTS ai_agent_moderation_events_user_created
              ON ai_agent_moderation_events(user_id, created_at DESC);

            CREATE TABLE IF NOT EXISTS automated_commenters (
              id TEXT PRIMARY KEY,
              user_id TEXT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
              created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS automated_commenter_rotations (
              scope_key TEXT PRIMARY KEY,
              commenter_ids_json TEXT NOT NULL DEFAULT '[]',
              order_json TEXT NOT NULL DEFAULT '[]',
              position INTEGER NOT NULL DEFAULT 0,
              last_commenter_id TEXT,
              updated_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS avatar_history (
              id TEXT PRIMARY KEY,
              user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              avatar_data TEXT NOT NULL,
              created_at INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS avatar_history_user_created_idx ON avatar_history(user_id, created_at DESC);

            CREATE TABLE IF NOT EXISTS automated_comment_rules (
              id TEXT PRIMARY KEY,
              channel_id TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
              target_message_id TEXT REFERENCES messages(id) ON DELETE CASCADE,
              target_scope TEXT NOT NULL DEFAULT 'future',
              commenter_ids_json TEXT NOT NULL DEFAULT '[]',
              texts_json TEXT NOT NULL DEFAULT '[]',
              comment_mode TEXT NOT NULL DEFAULT 'manual',
              categories_json TEXT NOT NULL DEFAULT '[]',
              min_delay_seconds INTEGER NOT NULL DEFAULT 300,
              max_delay_seconds INTEGER NOT NULL DEFAULT 1800,
              distribution_seconds INTEGER NOT NULL DEFAULT 43200,
              starts_at INTEGER NOT NULL,
              ends_at INTEGER NOT NULL,
              active INTEGER NOT NULL DEFAULT 1,
              created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS automated_comment_jobs (
              id TEXT PRIMARY KEY,
              rule_id TEXT NOT NULL REFERENCES automated_comment_rules(id) ON DELETE CASCADE,
              message_id TEXT NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
              commenter_id TEXT NOT NULL REFERENCES automated_commenters(id) ON DELETE CASCADE,
              text TEXT NOT NULL,
              publish_at INTEGER NOT NULL,
              created_at INTEGER NOT NULL,
              UNIQUE(rule_id, message_id, commenter_id)
            );

            CREATE TABLE IF NOT EXISTS activity_comment_jobs (
              id TEXT PRIMARY KEY,
              source_key TEXT NOT NULL,
              message_id TEXT NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
              commenter_id TEXT NOT NULL REFERENCES automated_commenters(id) ON DELETE CASCADE,
              categories_json TEXT NOT NULL DEFAULT '[]',
              publish_at INTEGER NOT NULL,
              created_at INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS activity_comment_jobs_publish_idx
              ON activity_comment_jobs(publish_at);

            CREATE TABLE IF NOT EXISTS media_uploads (
              key TEXT PRIMARY KEY,
              user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              chat_id TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
              media_type TEXT NOT NULL,
              file_name TEXT NOT NULL DEFAULT '',
              content_type TEXT NOT NULL,
              size_bytes INTEGER NOT NULL,
              expires_at INTEGER NOT NULL,
              created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS channel_links (
              channel_id TEXT PRIMARY KEY REFERENCES chats(id) ON DELETE CASCADE,
              target_chat_id TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
              created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS chat_read_states (
              chat_id TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
              user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              read_at INTEGER NOT NULL DEFAULT 0,
              read_rowid INTEGER NOT NULL DEFAULT 0,
              PRIMARY KEY (chat_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS message_reactions (
              message_id TEXT NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
              user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              emoji TEXT NOT NULL,
              created_at INTEGER NOT NULL,
              PRIMARY KEY (message_id, user_id, emoji)
            );

            CREATE TABLE IF NOT EXISTS hidden_pinned_messages (
              message_id TEXT NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
              user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              created_at INTEGER NOT NULL,
              PRIMARY KEY (message_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS reviews (
              id TEXT PRIMARY KEY,
              url TEXT NOT NULL,
              source_type TEXT NOT NULL DEFAULT 'website',
              rating INTEGER NOT NULL,
              comment TEXT NOT NULL DEFAULT '',
              city TEXT NOT NULL DEFAULT '',
              links_json TEXT NOT NULL DEFAULT '[]',
              media_data TEXT,
              created_by TEXT REFERENCES users(id) ON DELETE SET NULL,
              created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS reports (
              id TEXT PRIMARY KEY,
              target_type TEXT NOT NULL,
              target_id TEXT NOT NULL,
              reason TEXT NOT NULL DEFAULT '',
              created_by TEXT REFERENCES users(id) ON DELETE SET NULL,
              admin_response TEXT NOT NULL DEFAULT '',
              responded_at INTEGER,
              responded_by TEXT,
              created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS channel_share_submissions (
              id TEXT PRIMARY KEY,
              channel_id TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
              submitter_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              platform TEXT NOT NULL,
              external_url TEXT NOT NULL UNIQUE,
              description TEXT NOT NULL DEFAULT '',
              screenshot_data TEXT NOT NULL,
              reward_stars INTEGER NOT NULL,
              status TEXT NOT NULL CHECK(status IN ('pending', 'credited', 'rejected', 'revoked')) DEFAULT 'pending',
              eligible_at INTEGER NOT NULL,
              credited_at INTEGER,
              rejected_at INTEGER,
              admin_response TEXT NOT NULL DEFAULT '',
              responded_at INTEGER,
              responded_by TEXT,
              created_at INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS channel_share_submissions_due_idx ON channel_share_submissions(status, eligible_at);
            CREATE INDEX IF NOT EXISTS channel_share_submissions_channel_idx ON channel_share_submissions(channel_id, created_at DESC);

            CREATE TABLE IF NOT EXISTS vk_review_submissions (
              id TEXT PRIMARY KEY,
              channel_id TEXT REFERENCES chats(id) ON DELETE SET NULL,
              submitter_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              vk_target_id TEXT REFERENCES vk_channel_targets(id) ON DELETE SET NULL,
              external_url TEXT NOT NULL UNIQUE,
              vk_kind TEXT NOT NULL CHECK(vk_kind IN ('post', 'video')),
              vk_owner_id INTEGER NOT NULL,
              vk_item_id INTEGER NOT NULL,
              verified_title TEXT NOT NULL,
              likes_count INTEGER NOT NULL,
              reward_stars INTEGER NOT NULL,
              status TEXT NOT NULL CHECK(status IN ('pending', 'credited', 'rejected', 'revoked')) DEFAULT 'pending',
              eligible_at INTEGER NOT NULL,
              credited_at INTEGER,
              rejected_at INTEGER,
              admin_response TEXT NOT NULL DEFAULT '',
              responded_at INTEGER,
              responded_by TEXT,
              created_at INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS vk_review_submissions_due_idx ON vk_review_submissions(status, eligible_at);
            CREATE INDEX IF NOT EXISTS vk_review_submissions_channel_idx ON vk_review_submissions(channel_id, created_at DESC);

            CREATE TABLE IF NOT EXISTS promotions (
              id TEXT PRIMARY KEY,
              title TEXT NOT NULL,
              description TEXT NOT NULL,
              action_type TEXT NOT NULL,
              target_count INTEGER NOT NULL DEFAULT 1,
              reward_type TEXT NOT NULL DEFAULT 'stars',
              reward_amount INTEGER NOT NULL DEFAULT 0,
              premium_days INTEGER NOT NULL DEFAULT 0,
              daily_limit INTEGER NOT NULL DEFAULT 1,
              active INTEGER NOT NULL DEFAULT 1,
              created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS promotion_claims (
              promotion_id TEXT NOT NULL REFERENCES promotions(id) ON DELETE CASCADE,
              user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              count INTEGER NOT NULL DEFAULT 0,
              claimed_at INTEGER NOT NULL,
              PRIMARY KEY (promotion_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS statuses (
              id TEXT PRIMARY KEY,
              icon TEXT NOT NULL,
              title TEXT NOT NULL,
              description TEXT NOT NULL,
              criteria_json TEXT NOT NULL DEFAULT '{}',
              reward_json TEXT NOT NULL DEFAULT '{}',
              active INTEGER NOT NULL DEFAULT 1,
              created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS user_statuses (
              status_id TEXT NOT NULL REFERENCES statuses(id) ON DELETE CASCADE,
              user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              created_at INTEGER NOT NULL,
              PRIMARY KEY (status_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS recommended_groups (
              chat_id TEXT PRIMARY KEY REFERENCES chats(id) ON DELETE CASCADE,
              position INTEGER NOT NULL DEFAULT 100,
              created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS settings (
              key TEXT PRIMARY KEY,
              value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS boost_jobs (
              id TEXT PRIMARY KEY,
              target_type TEXT NOT NULL,
              target_id TEXT NOT NULL,
              metric TEXT NOT NULL,
              amount_per_minute INTEGER NOT NULL,
              remaining INTEGER NOT NULL,
              active INTEGER NOT NULL DEFAULT 1,
              last_tick INTEGER NOT NULL,
              created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS channel_growth_jobs (
              id TEXT PRIMARY KEY,
              channel_id TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
              subscribers_per_hour INTEGER NOT NULL DEFAULT 0,
              views_per_hour INTEGER NOT NULL DEFAULT 0,
              reactions_per_hour INTEGER NOT NULL DEFAULT 0,
              comments_per_hour INTEGER NOT NULL DEFAULT 0,
              starts_at INTEGER NOT NULL,
              ends_at INTEGER NOT NULL,
              subscribers_added INTEGER NOT NULL DEFAULT 0,
              views_added INTEGER NOT NULL DEFAULT 0,
              reactions_added INTEGER NOT NULL DEFAULT 0,
              comments_added INTEGER NOT NULL DEFAULT 0,
              active INTEGER NOT NULL DEFAULT 1,
              created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS channel_activity_regulator_state (
              channel_id TEXT PRIMARY KEY REFERENCES chats(id) ON DELETE CASCADE,
              unsubscribe_progress REAL NOT NULL DEFAULT 0,
              last_unsubscribe_tick_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS demo_activity_packages (
              id TEXT PRIMARY KEY,
              title TEXT NOT NULL,
              subscribers_per_day INTEGER NOT NULL DEFAULT 0,
              views_per_day INTEGER NOT NULL DEFAULT 0,
              reactions_per_day INTEGER NOT NULL DEFAULT 0,
              comments_per_day INTEGER NOT NULL DEFAULT 0,
              post_limit INTEGER NOT NULL DEFAULT 1,
              duration_days INTEGER NOT NULL DEFAULT 7,
              fade_duration_days INTEGER NOT NULL DEFAULT 30,
              indefinite INTEGER NOT NULL DEFAULT 0,
              price_stars INTEGER NOT NULL DEFAULT 0,
              apply_to_new_channels INTEGER NOT NULL DEFAULT 0,
              required_account_level_id TEXT NOT NULL DEFAULT '',
              commenter_ids_json TEXT NOT NULL DEFAULT '[]',
              donation_count INTEGER NOT NULL DEFAULT 0,
              donation_post_interval INTEGER NOT NULL DEFAULT 4,
              donation_min_stars INTEGER NOT NULL DEFAULT 0,
              donation_max_stars INTEGER NOT NULL DEFAULT 0,
              inactivity_days INTEGER NOT NULL DEFAULT 3,
              created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS demo_activity_donations (
              subscription_id TEXT NOT NULL REFERENCES demo_activity_subscriptions(id) ON DELETE CASCADE,
              message_id TEXT NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
              donation_number INTEGER NOT NULL,
              recipient_user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              amount INTEGER NOT NULL,
              created_at INTEGER NOT NULL,
              PRIMARY KEY (subscription_id, message_id, donation_number)
            );

            CREATE TABLE IF NOT EXISTS demo_activity_subscriptions (
              id TEXT PRIMARY KEY,
              package_id TEXT NOT NULL REFERENCES demo_activity_packages(id) ON DELETE CASCADE,
              channel_id TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
              starts_at INTEGER NOT NULL,
              ends_at INTEGER NOT NULL,
              auto_renew INTEGER NOT NULL DEFAULT 0,
              subscribers_added INTEGER NOT NULL DEFAULT 0,
              views_added INTEGER NOT NULL DEFAULT 0,
              reactions_added INTEGER NOT NULL DEFAULT 0,
              comments_added INTEGER NOT NULL DEFAULT 0,
              active INTEGER NOT NULL DEFAULT 1,
              level_paused_at INTEGER,
              activity_last_tick_at INTEGER,
              activity_progress_json TEXT NOT NULL DEFAULT '{}',
              metric_variation_json TEXT NOT NULL DEFAULT '{}',
              spike_multiplier INTEGER NOT NULL DEFAULT 1,
              spike_starts_at INTEGER,
              spike_ends_at INTEGER,
              next_spike_at INTEGER,
              created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS calls (
              id TEXT PRIMARY KEY,
              chat_id TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
              caller_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              receiver_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              call_type TEXT NOT NULL,
              offer_sdp TEXT NOT NULL,
              answer_sdp TEXT,
              status TEXT NOT NULL DEFAULT 'ringing',
              created_at INTEGER NOT NULL,
              updated_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS profile_posts (
              id TEXT PRIMARY KEY,
              user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              text TEXT NOT NULL,
              media_data TEXT,
              created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS profile_post_reactions (
              post_id TEXT NOT NULL REFERENCES profile_posts(id) ON DELETE CASCADE,
              user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              emoji TEXT NOT NULL,
              created_at INTEGER NOT NULL,
              PRIMARY KEY (post_id, user_id, emoji)
            );

            CREATE TABLE IF NOT EXISTS stories (
              id TEXT PRIMARY KEY,
              user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              media_data TEXT NOT NULL,
              caption TEXT NOT NULL DEFAULT '',
              created_at INTEGER NOT NULL,
              expires_at INTEGER NOT NULL,
              permanent INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS story_views (
              story_id TEXT NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
              user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              viewed_at INTEGER NOT NULL,
              PRIMARY KEY (story_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS story_reactions (
              story_id TEXT NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
              user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              emoji TEXT NOT NULL,
              created_at INTEGER NOT NULL,
              PRIMARY KEY (story_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS hidden_story_authors (
              user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              author_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              created_at INTEGER NOT NULL,
              PRIMARY KEY (user_id, author_id)
            );

            CREATE TABLE IF NOT EXISTS story_privacy_blocks (
              owner_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              blocked_user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              created_at INTEGER NOT NULL,
              PRIMARY KEY (owner_id, blocked_user_id)
            );

            CREATE TABLE IF NOT EXISTS user_blocks (
              owner_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              blocked_user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              created_at INTEGER NOT NULL,
              PRIMARY KEY (owner_id, blocked_user_id),
              CHECK (owner_id != blocked_user_id)
            );
            CREATE INDEX IF NOT EXISTS user_blocks_blocked_user_idx ON user_blocks(blocked_user_id);

            CREATE TABLE IF NOT EXISTS account_level_rewards (
              user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              level_id TEXT NOT NULL,
              claimed_at INTEGER NOT NULL,
              PRIMARY KEY (user_id, level_id)
            );

            CREATE TABLE IF NOT EXISTS account_level_purchases (
              user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              level_id TEXT NOT NULL,
              purchased_at INTEGER NOT NULL,
              PRIMARY KEY (user_id, level_id)
            );

            CREATE TABLE IF NOT EXISTS account_level_achievements (
              user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
              highest_level_index INTEGER NOT NULL DEFAULT 0,
              updated_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS account_level_subscriptions (
              id TEXT PRIMARY KEY,
              user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              level_id TEXT NOT NULL,
              monthly_price TEXT NOT NULL,
              payment_method_id TEXT,
              active_until INTEGER NOT NULL,
              next_charge_at INTEGER NOT NULL,
              status TEXT NOT NULL CHECK(status IN ('active', 'cancelled', 'payment_failed')) DEFAULT 'active',
              terms_accepted_at INTEGER NOT NULL,
              created_at INTEGER NOT NULL,
              updated_at INTEGER NOT NULL,
              UNIQUE(user_id, level_id)
            );
            CREATE INDEX IF NOT EXISTS account_level_subscriptions_due_idx ON account_level_subscriptions(status, next_charge_at);
            CREATE TABLE IF NOT EXISTS account_level_subscription_payments (
              id TEXT PRIMARY KEY,
              subscription_id TEXT NOT NULL REFERENCES account_level_subscriptions(id) ON DELETE CASCADE,
              amount_value TEXT NOT NULL,
              yookassa_payment_id TEXT UNIQUE,
              status TEXT NOT NULL DEFAULT 'creating',
              paid_at INTEGER,
              created_at INTEGER NOT NULL,
              updated_at INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS account_level_subscription_payments_subscription_idx ON account_level_subscription_payments(subscription_id, created_at DESC);

            CREATE TABLE IF NOT EXISTS account_level_reward_grants (
              user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              level_id TEXT NOT NULL,
              reward_id TEXT NOT NULL REFERENCES activity_rewards(id) ON DELETE CASCADE,
              granted_at INTEGER NOT NULL,
              PRIMARY KEY (user_id, reward_id)
            );

            CREATE TABLE IF NOT EXISTS admin_account_level_grants (
              user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
              level_id TEXT NOT NULL,
              granted_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS telegram_channel_links (
              channel_id TEXT PRIMARY KEY REFERENCES chats(id) ON DELETE CASCADE,
              source_chat_ref TEXT NOT NULL,
              source_chat_id TEXT,
              bot_token TEXT NOT NULL,
              last_update_id INTEGER NOT NULL DEFAULT 0,
              next_poll_at INTEGER NOT NULL DEFAULT 0,
              last_sync_at INTEGER,
              last_error TEXT,
              created_by TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS telegram_imported_posts (
              channel_id TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
              telegram_message_id INTEGER NOT NULL,
              imported_at INTEGER NOT NULL,
              PRIMARY KEY (channel_id, telegram_message_id)
            );

            CREATE TABLE IF NOT EXISTS rss_channel_links (
              channel_id TEXT PRIMARY KEY REFERENCES chats(id) ON DELETE CASCADE,
              feed_url TEXT NOT NULL,
              feed_title TEXT NOT NULL DEFAULT '',
              next_poll_at INTEGER NOT NULL DEFAULT 0,
              last_sync_at INTEGER,
              last_error TEXT,
              created_by TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS rss_imported_posts (
              channel_id TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
              entry_id TEXT NOT NULL,
              imported_at INTEGER NOT NULL,
              PRIMARY KEY (channel_id, entry_id)
            );

            CREATE TABLE IF NOT EXISTS rss_channel_sources (
              id TEXT PRIMARY KEY,
              channel_id TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
              feed_url TEXT NOT NULL,
              feed_title TEXT NOT NULL DEFAULT '',
              next_poll_at INTEGER NOT NULL DEFAULT 0,
              last_sync_at INTEGER,
              last_error TEXT,
              created_by TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              created_at INTEGER NOT NULL,
              UNIQUE(channel_id, feed_url)
            );

            CREATE TABLE IF NOT EXISTS rss_source_imported_posts (
              source_id TEXT NOT NULL REFERENCES rss_channel_sources(id) ON DELETE CASCADE,
              entry_id TEXT NOT NULL,
              imported_at INTEGER NOT NULL,
              PRIMARY KEY (source_id, entry_id)
            );

            CREATE TABLE IF NOT EXISTS vk_channel_sources (
              id TEXT PRIMARY KEY,
              channel_id TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
              source_url TEXT NOT NULL,
              source_ref TEXT NOT NULL,
              source_title TEXT NOT NULL DEFAULT '',
              owner_id INTEGER NOT NULL,
              access_token TEXT NOT NULL,
              keywords_json TEXT NOT NULL DEFAULT '[]',
              next_poll_at INTEGER NOT NULL DEFAULT 0,
              last_sync_at INTEGER,
              last_error TEXT,
              created_by TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              created_at INTEGER NOT NULL,
              UNIQUE(channel_id, source_url)
            );

            CREATE TABLE IF NOT EXISTS vk_source_imported_posts (
              source_id TEXT NOT NULL REFERENCES vk_channel_sources(id) ON DELETE CASCADE,
              post_id INTEGER NOT NULL,
              imported_at INTEGER NOT NULL,
              PRIMARY KEY (source_id, post_id)
            );

            CREATE TABLE IF NOT EXISTS vk_source_published_messages (
              source_id TEXT NOT NULL REFERENCES vk_channel_sources(id) ON DELETE CASCADE,
              message_id TEXT NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
              vk_post_id INTEGER,
              status TEXT NOT NULL DEFAULT 'pending',
              last_error TEXT,
              published_at INTEGER NOT NULL,
              PRIMARY KEY (source_id, message_id)
            );

            CREATE TABLE IF NOT EXISTS vk_source_moderated_comments (
              source_id TEXT NOT NULL REFERENCES vk_channel_sources(id) ON DELETE CASCADE,
              post_id INTEGER NOT NULL,
              comment_id INTEGER NOT NULL,
              decision TEXT NOT NULL DEFAULT 'allow',
              last_error TEXT,
              moderated_at INTEGER NOT NULL,
              PRIMARY KEY (source_id, post_id, comment_id)
            );

            CREATE TABLE IF NOT EXISTS vk_proposed_posts (
              id TEXT PRIMARY KEY,
              source_id TEXT NOT NULL REFERENCES vk_channel_sources(id) ON DELETE CASCADE,
              channel_id TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
              proposer_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              text TEXT NOT NULL,
              status TEXT NOT NULL DEFAULT 'pending',
              vk_post_id INTEGER,
              decision_reason TEXT NOT NULL DEFAULT '',
              last_error TEXT,
              created_at INTEGER NOT NULL,
              reviewed_by TEXT REFERENCES users(id) ON DELETE SET NULL,
              reviewed_at INTEGER,
              published_at INTEGER
            );
            CREATE INDEX IF NOT EXISTS vk_proposed_posts_channel_status
              ON vk_proposed_posts(channel_id, status, created_at DESC);

            CREATE TABLE IF NOT EXISTS vk_channel_targets (
              id TEXT PRIMARY KEY,
              channel_id TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
              target_url TEXT NOT NULL,
              target_ref TEXT NOT NULL,
              target_title TEXT NOT NULL DEFAULT '',
              owner_id INTEGER NOT NULL,
              access_token TEXT NOT NULL,
              publish_enabled INTEGER NOT NULL DEFAULT 1,
              moderation_enabled INTEGER NOT NULL DEFAULT 0,
              last_publish_at INTEGER,
              last_moderation_sync_at INTEGER,
              last_error TEXT,
              created_by TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              created_at INTEGER NOT NULL,
              UNIQUE(channel_id, target_url)
            );
            CREATE INDEX IF NOT EXISTS vk_channel_targets_channel_idx
              ON vk_channel_targets(channel_id, created_at);

            CREATE TABLE IF NOT EXISTS vk_target_published_messages (
              target_id TEXT NOT NULL REFERENCES vk_channel_targets(id) ON DELETE CASCADE,
              message_id TEXT NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
              vk_post_id INTEGER,
              status TEXT NOT NULL DEFAULT 'pending',
              last_error TEXT,
              published_at INTEGER NOT NULL,
              PRIMARY KEY (target_id, message_id)
            );

            CREATE TABLE IF NOT EXISTS vk_target_moderated_comments (
              target_id TEXT NOT NULL REFERENCES vk_channel_targets(id) ON DELETE CASCADE,
              post_id INTEGER NOT NULL,
              comment_id INTEGER NOT NULL,
              decision TEXT NOT NULL DEFAULT 'review',
              last_error TEXT,
              moderated_at INTEGER NOT NULL,
              PRIMARY KEY (target_id, post_id, comment_id)
            );

            CREATE TABLE IF NOT EXISTS star_transactions (
              id TEXT PRIMARY KEY,
              user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              amount INTEGER NOT NULL,
              kind TEXT NOT NULL,
              description TEXT NOT NULL,
              created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS yookassa_payments (
              id TEXT PRIMARY KEY,
              user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              package_id TEXT NOT NULL,
              stars INTEGER NOT NULL,
              amount_value TEXT NOT NULL,
              channel_id TEXT REFERENCES chats(id) ON DELETE SET NULL,
              channel_bonus_type TEXT,
              channel_bonus_amount TEXT,
              yookassa_payment_id TEXT UNIQUE,
              status TEXT NOT NULL DEFAULT 'created',
              terms_accepted_at INTEGER,
              credited_at INTEGER,
              created_at INTEGER NOT NULL,
              updated_at INTEGER NOT NULL
            );

            CREATE INDEX IF NOT EXISTS yookassa_payments_user_idx ON yookassa_payments(user_id, created_at DESC);

            CREATE TABLE IF NOT EXISTS channel_star_purchases (
              id TEXT PRIMARY KEY,
              payment_id TEXT NOT NULL UNIQUE REFERENCES yookassa_payments(id) ON DELETE CASCADE,
              channel_id TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
              buyer_user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              stars INTEGER NOT NULL,
              bonus_type TEXT NOT NULL,
              bonus_amount TEXT NOT NULL,
              buyer_gift_stars INTEGER NOT NULL DEFAULT 0,
              buyer_message TEXT NOT NULL DEFAULT '',
              created_at INTEGER NOT NULL
            );

            CREATE INDEX IF NOT EXISTS channel_star_purchases_channel_idx ON channel_star_purchases(channel_id, created_at DESC);

            CREATE TABLE IF NOT EXISTS channel_payout_accruals (
              id TEXT PRIMARY KEY,
              purchase_id TEXT NOT NULL UNIQUE REFERENCES channel_star_purchases(id) ON DELETE CASCADE,
              channel_id TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
              owner_user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              amount_value TEXT NOT NULL,
              commission_percent INTEGER NOT NULL,
              star_rate_rubles TEXT NOT NULL,
              created_at INTEGER NOT NULL
            );

            CREATE INDEX IF NOT EXISTS channel_payout_accruals_owner_idx ON channel_payout_accruals(owner_user_id, channel_id, created_at DESC);

            CREATE TABLE IF NOT EXISTS channel_payout_requests (
              id TEXT PRIMARY KEY,
              channel_id TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
              owner_user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              amount_value TEXT NOT NULL,
              status TEXT NOT NULL DEFAULT 'pending',
              admin_note TEXT NOT NULL DEFAULT '',
              created_at INTEGER NOT NULL,
              processed_at INTEGER
            );

            CREATE INDEX IF NOT EXISTS channel_payout_requests_owner_idx ON channel_payout_requests(owner_user_id, channel_id, created_at DESC);

            CREATE TABLE IF NOT EXISTS activity_rewards (
              id TEXT PRIMARY KEY,
              title TEXT NOT NULL,
              description TEXT NOT NULL DEFAULT '',
              criteria_json TEXT NOT NULL DEFAULT '{}',
              reward_stars INTEGER NOT NULL DEFAULT 0,
              premium_days INTEGER NOT NULL DEFAULT 0,
              reward_json TEXT NOT NULL DEFAULT '{}',
              active INTEGER NOT NULL DEFAULT 1,
              created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS activity_reward_claims (
              reward_id TEXT NOT NULL REFERENCES activity_rewards(id) ON DELETE CASCADE,
              user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              claimed_at INTEGER NOT NULL,
              PRIMARY KEY (reward_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS personal_limit_rewards (
              user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              source_type TEXT NOT NULL,
              source_id TEXT NOT NULL,
              limits_json TEXT NOT NULL,
              created_at INTEGER NOT NULL,
              PRIMARY KEY (user_id, source_type, source_id)
            );

            CREATE TABLE IF NOT EXISTS personal_star_package_discounts (
              user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              source_type TEXT NOT NULL,
              source_id TEXT NOT NULL,
              discount_percent INTEGER NOT NULL,
              created_at INTEGER NOT NULL,
              PRIMARY KEY (user_id, source_type, source_id)
            );

            CREATE TABLE IF NOT EXISTS recurring_star_rewards (
              user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              source_type TEXT NOT NULL,
              source_id TEXT NOT NULL,
              title TEXT NOT NULL,
              stars INTEGER NOT NULL,
              interval_seconds INTEGER NOT NULL,
              ends_at INTEGER NOT NULL,
              next_credit_at INTEGER NOT NULL,
              created_at INTEGER NOT NULL,
              PRIMARY KEY (user_id, source_type, source_id)
            );
            """
        )
        # Migrate the obsolete one-source RSS table only once. Afterwards the new
        # source table is authoritative, including an intentionally empty list.
        rss_migration_key = "rss_sources_migration_v1"
        migrated = con.execute("SELECT 1 FROM settings WHERE key = ?", (rss_migration_key,)).fetchone()
        if not migrated:
            existing_sources = {row["channel_id"] for row in con.execute("SELECT channel_id FROM rss_channel_sources").fetchall()}
            legacy_links = con.execute("SELECT * FROM rss_channel_links").fetchall()
            for legacy in legacy_links:
                if legacy["channel_id"] in existing_sources:
                    continue
                source_id = uid("rss")
                con.execute(
                    """INSERT INTO rss_channel_sources(id,channel_id,feed_url,feed_title,next_poll_at,last_sync_at,last_error,created_by,created_at)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (source_id, legacy["channel_id"], legacy["feed_url"], legacy["feed_title"], legacy["next_poll_at"], legacy["last_sync_at"], legacy["last_error"], legacy["created_by"], legacy["created_at"]),
                )
                legacy_posts = con.execute("SELECT entry_id, imported_at FROM rss_imported_posts WHERE channel_id = ?", (legacy["channel_id"],)).fetchall()
                con.executemany(
                    "INSERT OR IGNORE INTO rss_source_imported_posts(source_id,entry_id,imported_at) VALUES (?,?,?)",
                    [(source_id, post["entry_id"], post["imported_at"]) for post in legacy_posts],
                )
            con.execute("INSERT INTO settings(key,value) VALUES (?,?)", (rss_migration_key, dumps({"completedAt": now()})))
        columns = {row["name"] for row in con.execute("PRAGMA table_info(users)").fetchall()}
        if "email" not in columns:
            con.execute("ALTER TABLE users ADD COLUMN email TEXT")
        if "phone" not in columns:
            con.execute("ALTER TABLE users ADD COLUMN phone TEXT")
        if "email_verified" not in columns:
            con.execute("ALTER TABLE users ADD COLUMN email_verified INTEGER NOT NULL DEFAULT 0")
        if "phone_verified" not in columns:
            con.execute("ALTER TABLE users ADD COLUMN phone_verified INTEGER NOT NULL DEFAULT 0")
        if "avatar_data" not in columns:
            con.execute("ALTER TABLE users ADD COLUMN avatar_data TEXT")
        if "site_color" not in columns:
            con.execute("ALTER TABLE users ADD COLUMN site_color TEXT NOT NULL DEFAULT '#2aabee'")
        if "site_background" not in columns:
            con.execute("ALTER TABLE users ADD COLUMN site_background TEXT NOT NULL DEFAULT 'default'")
        if "site_background_data" not in columns:
            con.execute("ALTER TABLE users ADD COLUMN site_background_data TEXT")
        ai_agent_columns = {row["name"] for row in con.execute("PRAGMA table_info(ai_agent_settings)").fetchall()}
        if "model_profile" not in ai_agent_columns:
            con.execute("ALTER TABLE ai_agent_settings ADD COLUMN model_profile TEXT NOT NULL DEFAULT 'default'")
        if "agent_name" not in ai_agent_columns:
            con.execute("ALTER TABLE ai_agent_settings ADD COLUMN agent_name TEXT NOT NULL DEFAULT 'ИИ-администратор'")
        if "booking_config_json" not in ai_agent_columns:
            con.execute("ALTER TABLE ai_agent_settings ADD COLUMN booking_config_json TEXT NOT NULL DEFAULT '{}'")
        if "autopilot_all_direct" not in ai_agent_columns:
            con.execute("ALTER TABLE ai_agent_settings ADD COLUMN autopilot_all_direct INTEGER NOT NULL DEFAULT 0")
        task_migration_key = "ai_agent_tasks_migration_v1"
        if not con.execute("SELECT 1 FROM settings WHERE key = ?", (task_migration_key,)).fetchone():
            for legacy in con.execute("SELECT * FROM ai_agent_settings WHERE autopilot_enabled = 1").fetchall():
                scope = "all_direct" if legacy["autopilot_all_direct"] else "selected_direct"
                chat_ids = [] if scope == "all_direct" else loads(legacy["allowed_chat_ids_json"], [])
                if scope == "all_direct" or chat_ids:
                    title = "Отвечать на все новые входящие" if scope == "all_direct" else "Отвечать в выбранных диалогах"
                    con.execute(
                        "INSERT INTO ai_agent_tasks(id,user_id,title,instruction,scope,chat_ids_json,enabled,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
                        (uid("ai_task"), legacy["user_id"], title, legacy["instruction"], scope, dumps(chat_ids), 1, legacy["updated_at"], legacy["updated_at"]),
                    )
            con.execute("UPDATE ai_agent_settings SET autopilot_enabled = 0, autopilot_all_direct = 0, allowed_chat_ids_json = '[]'")
            con.execute("INSERT INTO settings(key,value) VALUES (?,?)", (task_migration_key, dumps({"completedAt": now()})))
        channel_rule_columns = {row["name"] for row in con.execute("PRAGMA table_info(ai_agent_channel_rules)").fetchall()}
        if "rewrite_posts" not in channel_rule_columns:
            con.execute("ALTER TABLE ai_agent_channel_rules ADD COLUMN rewrite_posts INTEGER NOT NULL DEFAULT 0")
        if "chat_background" not in columns:
            con.execute("ALTER TABLE users ADD COLUMN chat_background TEXT NOT NULL DEFAULT 'cyan'")
        if "dialog_bubble_style" not in columns:
            con.execute("ALTER TABLE users ADD COLUMN dialog_bubble_style TEXT NOT NULL DEFAULT 'custom'")
        if "dialog_font" not in columns:
            con.execute("ALTER TABLE users ADD COLUMN dialog_font TEXT NOT NULL DEFAULT 'system'")
        if "other_dialog_color" not in columns:
            con.execute("ALTER TABLE users ADD COLUMN other_dialog_color TEXT NOT NULL DEFAULT '#dff9f9'")
        if "dialog_panel_color" not in columns:
            con.execute("ALTER TABLE users ADD COLUMN dialog_panel_color TEXT NOT NULL DEFAULT '#f4f8fc'")
        if "dialog_panel_style" not in columns:
            con.execute("ALTER TABLE users ADD COLUMN dialog_panel_style TEXT NOT NULL DEFAULT 'custom'")
        if "chat_background_data" not in columns:
            con.execute("ALTER TABLE users ADD COLUMN chat_background_data TEXT")
        if "sidebar_background_data" not in columns:
            con.execute("ALTER TABLE users ADD COLUMN sidebar_background_data TEXT")
        if "group_invite_privacy" not in columns:
            con.execute("ALTER TABLE users ADD COLUMN group_invite_privacy TEXT NOT NULL DEFAULT 'contacts'")
        if "direct_message_privacy" not in columns:
            con.execute("ALTER TABLE users ADD COLUMN direct_message_privacy TEXT NOT NULL DEFAULT 'everyone'")
        channel_purchase_columns = {row["name"] for row in con.execute("PRAGMA table_info(channel_star_purchases)").fetchall()}
        if "buyer_gift_stars" not in channel_purchase_columns:
            con.execute("ALTER TABLE channel_star_purchases ADD COLUMN buyer_gift_stars INTEGER NOT NULL DEFAULT 0")
        if "buyer_message" not in channel_purchase_columns:
            con.execute("ALTER TABLE channel_star_purchases ADD COLUMN buyer_message TEXT NOT NULL DEFAULT ''")
        payment_columns = {row["name"] for row in con.execute("PRAGMA table_info(yookassa_payments)").fetchall()}
        if "buyer_gift_stars" not in payment_columns:
            con.execute("ALTER TABLE yookassa_payments ADD COLUMN buyer_gift_stars INTEGER NOT NULL DEFAULT 0")
        message_columns = {row["name"] for row in con.execute("PRAGMA table_info(messages)").fetchall()}
        if "circle_preview_data" not in message_columns:
            con.execute("ALTER TABLE messages ADD COLUMN circle_preview_data TEXT")
        if "source_channel_id" not in message_columns:
            con.execute("ALTER TABLE messages ADD COLUMN source_channel_id TEXT REFERENCES chats(id) ON DELETE SET NULL")
        automated_comment_rule_columns = {row["name"] for row in con.execute("PRAGMA table_info(automated_comment_rules)").fetchall()}
        if "target_scope" not in automated_comment_rule_columns:
            con.execute("ALTER TABLE automated_comment_rules ADD COLUMN target_scope TEXT NOT NULL DEFAULT 'future'")
        if "distribution_seconds" not in automated_comment_rule_columns:
            con.execute("ALTER TABLE automated_comment_rules ADD COLUMN distribution_seconds INTEGER NOT NULL DEFAULT 43200")
        if "comment_mode" not in automated_comment_rule_columns:
            con.execute("ALTER TABLE automated_comment_rules ADD COLUMN comment_mode TEXT NOT NULL DEFAULT 'manual'")
        if "categories_json" not in automated_comment_rule_columns:
            con.execute("ALTER TABLE automated_comment_rules ADD COLUMN categories_json TEXT NOT NULL DEFAULT '[]'")
        # Old templates and local phrase generation made comments visibly repetitive.
        # Every automated text now goes through the configured DeepSeek profile instead.
        con.execute("UPDATE automated_comment_rules SET comment_mode = 'ai', texts_json = '[]' WHERE comment_mode IN ('manual', 'local')")
        if "night_appearance_custom" not in columns:
            con.execute("ALTER TABLE users ADD COLUMN night_appearance_custom INTEGER NOT NULL DEFAULT 0")
        if "night_outline_color" not in columns:
            con.execute("ALTER TABLE users ADD COLUMN night_outline_color TEXT")
        if "night_glow_color" not in columns:
            con.execute("ALTER TABLE users ADD COLUMN night_glow_color TEXT")
        if "night_glow_intensity" not in columns:
            con.execute("ALTER TABLE users ADD COLUMN night_glow_intensity INTEGER")
        if "call_ringtone" not in columns:
            con.execute("ALTER TABLE users ADD COLUMN call_ringtone TEXT NOT NULL DEFAULT 'classic'")
        if "call_ringtone_data" not in columns:
            con.execute("ALTER TABLE users ADD COLUMN call_ringtone_data TEXT")
        if "text_scale" not in columns:
            con.execute("ALTER TABLE users ADD COLUMN text_scale TEXT NOT NULL DEFAULT 'system'")
        appearance_migration_key = "dialog_appearance_defaults_from_andrei_20260920"
        if not con.execute("SELECT 1 FROM settings WHERE key = ?", (appearance_migration_key,)).fetchone():
            appearance = dialog_appearance_defaults(con)
            assignments = ", ".join(f"{field} = ?" for field in DIALOG_APPEARANCE_FIELDS)
            con.execute(
                f"UPDATE users SET {assignments} WHERE lower(username) != 'andrei'",
                tuple(appearance[field] for field in DIALOG_APPEARANCE_FIELDS),
            )
            con.execute("INSERT INTO settings(key,value) VALUES (?,?)", (appearance_migration_key, dumps({"completedAt": now()})))
        message_columns = {row["name"] for row in con.execute("PRAGMA table_info(messages)").fetchall()}
        if "ai_agent" not in message_columns:
            con.execute("ALTER TABLE messages ADD COLUMN ai_agent INTEGER NOT NULL DEFAULT 0")
        chat_columns = {row["name"] for row in con.execute("PRAGMA table_info(chats)").fetchall()}
        if "invite_code" not in chat_columns:
            con.execute("ALTER TABLE chats ADD COLUMN invite_code TEXT")
        for chat in con.execute("SELECT id FROM chats WHERE invite_code IS NULL OR invite_code = ''").fetchall():
            con.execute("UPDATE chats SET invite_code = ? WHERE id = ?", (secrets.token_urlsafe(12), chat["id"]))
        if "avatar_data" not in chat_columns:
            con.execute("ALTER TABLE chats ADD COLUMN avatar_data TEXT")
        demo_package_columns = {row["name"] for row in con.execute("PRAGMA table_info(demo_activity_packages)").fetchall()}
        if "fade_duration_days" not in demo_package_columns:
            con.execute("ALTER TABLE demo_activity_packages ADD COLUMN fade_duration_days INTEGER NOT NULL DEFAULT 30")
        if "indefinite" not in demo_package_columns:
            con.execute("ALTER TABLE demo_activity_packages ADD COLUMN indefinite INTEGER NOT NULL DEFAULT 0")
        if "price_stars" not in demo_package_columns:
            con.execute("ALTER TABLE demo_activity_packages ADD COLUMN price_stars INTEGER NOT NULL DEFAULT 0")
        if "apply_to_new_channels" not in demo_package_columns:
            con.execute("ALTER TABLE demo_activity_packages ADD COLUMN apply_to_new_channels INTEGER NOT NULL DEFAULT 0")
        if "commenter_ids_json" not in demo_package_columns:
            con.execute("ALTER TABLE demo_activity_packages ADD COLUMN commenter_ids_json TEXT NOT NULL DEFAULT '[]'")
        if "required_account_level_id" not in demo_package_columns:
            con.execute("ALTER TABLE demo_activity_packages ADD COLUMN required_account_level_id TEXT NOT NULL DEFAULT ''")
        for column, definition in (
            ("donation_count", "INTEGER NOT NULL DEFAULT 0"),
            ("donation_post_interval", "INTEGER NOT NULL DEFAULT 4"),
            ("donation_min_stars", "INTEGER NOT NULL DEFAULT 0"),
            ("donation_max_stars", "INTEGER NOT NULL DEFAULT 0"),
            ("inactivity_days", "INTEGER NOT NULL DEFAULT 3"),
        ):
            if column not in demo_package_columns:
                con.execute(f"ALTER TABLE demo_activity_packages ADD COLUMN {column} {definition}")
        demo_subscription_columns = {row["name"] for row in con.execute("PRAGMA table_info(demo_activity_subscriptions)").fetchall()}
        for column, definition in (
            ("level_paused_at", "INTEGER"),
            ("activity_last_tick_at", "INTEGER"),
            ("activity_progress_json", "TEXT NOT NULL DEFAULT '{}'"),
            ("metric_variation_json", "TEXT NOT NULL DEFAULT '{}'"),
            ("spike_multiplier", "INTEGER NOT NULL DEFAULT 1"),
            ("spike_starts_at", "INTEGER"),
            ("spike_ends_at", "INTEGER"),
            ("next_spike_at", "INTEGER"),
            ("content_paused_at", "INTEGER"),
            ("inactivity_fade_started_at", "INTEGER"),
        ):
            if column not in demo_subscription_columns:
                con.execute(f"ALTER TABLE demo_activity_subscriptions ADD COLUMN {column} {definition}")
        # «Автор» was the former channel-manager role. Keep its permissions as a
        # compatibility fallback, but normalize stored rows to the current name.
        con.execute(
            """UPDATE chat_members SET role = 'admin'
               WHERE role = 'author' AND chat_id IN (
                   SELECT id FROM chats WHERE type = 'channel'
               )"""
        )
        message_columns = {row["name"] for row in con.execute("PRAGMA table_info(messages)").fetchall()}
        if "media_type" not in message_columns:
            con.execute("ALTER TABLE messages ADD COLUMN media_type TEXT")
        if "media_data" not in message_columns:
            con.execute("ALTER TABLE messages ADD COLUMN media_data TEXT")
        if "media_embed_url" not in message_columns:
            con.execute("ALTER TABLE messages ADD COLUMN media_embed_url TEXT")
        if "profile_user_id" not in message_columns:
            con.execute("ALTER TABLE messages ADD COLUMN profile_user_id TEXT REFERENCES users(id) ON DELETE SET NULL")
        if "pinned" not in message_columns:
            con.execute("ALTER TABLE messages ADD COLUMN pinned INTEGER NOT NULL DEFAULT 0")
        if "forwarded_from" not in message_columns:
            con.execute("ALTER TABLE messages ADD COLUMN forwarded_from TEXT")
        if "forwarded_from_user_id" not in message_columns:
            con.execute("ALTER TABLE messages ADD COLUMN forwarded_from_user_id TEXT REFERENCES users(id) ON DELETE SET NULL")
        if "reply_to_id" not in message_columns:
            con.execute("ALTER TABLE messages ADD COLUMN reply_to_id TEXT REFERENCES messages(id) ON DELETE SET NULL")
        if "edited_at" not in message_columns:
            con.execute("ALTER TABLE messages ADD COLUMN edited_at INTEGER")
        if "source_type" not in message_columns:
            con.execute("ALTER TABLE messages ADD COLUMN source_type TEXT")
        if "source_id" not in message_columns:
            con.execute("ALTER TABLE messages ADD COLUMN source_id TEXT")
        if "voice_waveform_json" not in message_columns:
            con.execute("ALTER TABLE messages ADD COLUMN voice_waveform_json TEXT")
        if "deleted_by_admin" not in message_columns:
            con.execute("ALTER TABLE messages ADD COLUMN deleted_by_admin INTEGER NOT NULL DEFAULT 0")
        comment_columns = {row["name"] for row in con.execute("PRAGMA table_info(channel_comments)").fetchall()}
        if "media_data" not in comment_columns:
            con.execute("ALTER TABLE channel_comments ADD COLUMN media_data TEXT")
        if "automated" not in comment_columns:
            con.execute("ALTER TABLE channel_comments ADD COLUMN automated INTEGER NOT NULL DEFAULT 0")
        moderation_rule_columns = {row["name"] for row in con.execute("PRAGMA table_info(ai_agent_comment_moderation_rules)").fetchall()}
        for column, definition in (
            ("semantic_rules_json", "TEXT NOT NULL DEFAULT '[]'"),
            ("action_mode", "TEXT NOT NULL DEFAULT 'delete'"),
            ("notify_owner", "INTEGER NOT NULL DEFAULT 1"),
            ("target_scope", "TEXT NOT NULL DEFAULT 'comments'"),
            ("ai_enabled", "INTEGER NOT NULL DEFAULT 0"),
        ):
            if column not in moderation_rule_columns:
                con.execute(f"ALTER TABLE ai_agent_comment_moderation_rules ADD COLUMN {column} {definition}")
        vk_source_columns = {row["name"] for row in con.execute("PRAGMA table_info(vk_channel_sources)").fetchall()}
        for column, definition in (
            ("publish_enabled", "INTEGER NOT NULL DEFAULT 1"),
            ("moderation_enabled", "INTEGER NOT NULL DEFAULT 0"),
            ("moderation_rules_json", "TEXT NOT NULL DEFAULT '{}'"),
        ):
            if column not in vk_source_columns:
                con.execute(f"ALTER TABLE vk_channel_sources ADD COLUMN {column} {definition}")
        published_message_columns = {row["name"] for row in con.execute("PRAGMA table_info(vk_source_published_messages)").fetchall()}
        for column, definition in (
            ("status", "TEXT NOT NULL DEFAULT 'pending'"),
            ("last_error", "TEXT"),
        ):
            if column not in published_message_columns:
                con.execute(f"ALTER TABLE vk_source_published_messages ADD COLUMN {column} {definition}")
        con.execute(
            """INSERT OR IGNORE INTO chat_read_states(chat_id, user_id, read_at)
               SELECT cm.chat_id, cm.user_id, COALESCE(MAX(m.created_at), 0)
               FROM chat_members cm
               LEFT JOIN messages m ON m.chat_id = cm.chat_id
               GROUP BY cm.chat_id, cm.user_id"""
        )
        read_state_columns = {row["name"] for row in con.execute("PRAGMA table_info(chat_read_states)").fetchall()}
        if "read_rowid" not in read_state_columns:
            con.execute("ALTER TABLE chat_read_states ADD COLUMN read_rowid INTEGER NOT NULL DEFAULT 0")
        con.execute(
            """UPDATE chat_read_states
               SET read_rowid = COALESCE((SELECT MAX(m.rowid) FROM messages m WHERE m.chat_id = chat_read_states.chat_id AND m.created_at <= chat_read_states.read_at), 0)
               WHERE read_rowid = 0"""
        )
        report_columns = {row["name"] for row in con.execute("PRAGMA table_info(reports)").fetchall()}
        for column, definition in (("admin_response", "TEXT NOT NULL DEFAULT ''"), ("responded_at", "INTEGER"), ("responded_by", "TEXT")):
            if column not in report_columns:
                con.execute(f"ALTER TABLE reports ADD COLUMN {column} {definition}")
        vk_review_columns = {row["name"]: row for row in con.execute("PRAGMA table_info(vk_review_submissions)").fetchall()}
        if vk_review_columns and (vk_review_columns["channel_id"]["notnull"] or vk_review_columns["vk_target_id"]["notnull"]):
            con.execute("DROP INDEX IF EXISTS vk_review_submissions_due_idx")
            con.execute("DROP INDEX IF EXISTS vk_review_submissions_channel_idx")
            con.execute("""CREATE TABLE vk_review_submissions_new (
              id TEXT PRIMARY KEY,
              channel_id TEXT REFERENCES chats(id) ON DELETE SET NULL,
              submitter_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              vk_target_id TEXT REFERENCES vk_channel_targets(id) ON DELETE SET NULL,
              external_url TEXT NOT NULL UNIQUE,
              vk_kind TEXT NOT NULL CHECK(vk_kind IN ('post', 'video')),
              vk_owner_id INTEGER NOT NULL,
              vk_item_id INTEGER NOT NULL,
              verified_title TEXT NOT NULL,
              likes_count INTEGER NOT NULL,
              reward_stars INTEGER NOT NULL,
              status TEXT NOT NULL CHECK(status IN ('pending', 'credited', 'rejected', 'revoked')) DEFAULT 'pending',
              eligible_at INTEGER NOT NULL,
              credited_at INTEGER, rejected_at INTEGER,
              admin_response TEXT NOT NULL DEFAULT '', responded_at INTEGER, responded_by TEXT,
              created_at INTEGER NOT NULL
            )""")
            con.execute("""INSERT INTO vk_review_submissions_new SELECT id, channel_id, submitter_id, vk_target_id, external_url, vk_kind, vk_owner_id, vk_item_id, verified_title, likes_count, reward_stars, status, eligible_at, credited_at, rejected_at, admin_response, responded_at, responded_by, created_at FROM vk_review_submissions""")
            con.execute("DROP TABLE vk_review_submissions")
            con.execute("ALTER TABLE vk_review_submissions_new RENAME TO vk_review_submissions")
            con.execute("CREATE INDEX IF NOT EXISTS vk_review_submissions_due_idx ON vk_review_submissions(status, eligible_at)")
            con.execute("CREATE INDEX IF NOT EXISTS vk_review_submissions_channel_idx ON vk_review_submissions(channel_id, created_at DESC)")
        review_columns = {row["name"] for row in con.execute("PRAGMA table_info(reviews)").fetchall()}
        if "media_data" not in review_columns:
            con.execute("ALTER TABLE reviews ADD COLUMN media_data TEXT")
        if "source_type" not in review_columns:
            con.execute("ALTER TABLE reviews ADD COLUMN source_type TEXT NOT NULL DEFAULT 'website'")
        if "city" not in review_columns:
            con.execute("ALTER TABLE reviews ADD COLUMN city TEXT NOT NULL DEFAULT ''")
        user_columns = {row["name"] for row in con.execute("PRAGMA table_info(users)").fetchall()}
        if "agreement_accepted_at" not in user_columns:
            con.execute("ALTER TABLE users ADD COLUMN agreement_accepted_at INTEGER")
        if "deletion_requested_at" not in user_columns:
            con.execute("ALTER TABLE users ADD COLUMN deletion_requested_at INTEGER")
        if "deletion_due_at" not in user_columns:
            con.execute("ALTER TABLE users ADD COLUMN deletion_due_at INTEGER")
        if "profile_description" not in user_columns:
            con.execute("ALTER TABLE users ADD COLUMN profile_description TEXT NOT NULL DEFAULT ''")
        con.execute("CREATE INDEX IF NOT EXISTS users_deletion_due_at_idx ON users(deletion_due_at) WHERE deletion_due_at IS NOT NULL")
        oauth_state_columns = {row["name"] for row in con.execute("PRAGMA table_info(oauth_states)").fetchall()}
        if "code_verifier" not in oauth_state_columns:
            con.execute("ALTER TABLE oauth_states ADD COLUMN code_verifier TEXT")
        level_columns = {row["name"] for row in con.execute("PRAGMA table_info(account_level_subscriptions)").fetchall()}
        # The table is created above for both fresh and existing databases.
        yookassa_payment_columns = {row["name"] for row in con.execute("PRAGMA table_info(yookassa_payments)").fetchall()}
        if "terms_accepted_at" not in yookassa_payment_columns:
            con.execute("ALTER TABLE yookassa_payments ADD COLUMN terms_accepted_at INTEGER")
        if "channel_id" not in yookassa_payment_columns:
            con.execute("ALTER TABLE yookassa_payments ADD COLUMN channel_id TEXT REFERENCES chats(id) ON DELETE SET NULL")
        if "channel_bonus_type" not in yookassa_payment_columns:
            con.execute("ALTER TABLE yookassa_payments ADD COLUMN channel_bonus_type TEXT")
        if "channel_bonus_amount" not in yookassa_payment_columns:
            con.execute("ALTER TABLE yookassa_payments ADD COLUMN channel_bonus_amount TEXT")
        activity_reward_columns = {row["name"] for row in con.execute("PRAGMA table_info(activity_rewards)").fetchall()}
        if "reward_json" not in activity_reward_columns:
            con.execute("ALTER TABLE activity_rewards ADD COLUMN reward_json TEXT NOT NULL DEFAULT '{}'")
        story_columns = {row["name"] for row in con.execute("PRAGMA table_info(stories)").fetchall()}
        if "permanent" not in story_columns:
            con.execute("ALTER TABLE stories ADD COLUMN permanent INTEGER NOT NULL DEFAULT 0")
        con.execute(
            """CREATE TABLE IF NOT EXISTS hidden_messages (
              message_id TEXT NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
              user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              created_at INTEGER NOT NULL,
              PRIMARY KEY (message_id, user_id)
            )"""
        )
        post_columns = {row["name"] for row in con.execute("PRAGMA table_info(profile_posts)").fetchall()}
        if "media_data" not in post_columns:
            con.execute("ALTER TABLE profile_posts ADD COLUMN media_data TEXT")
        con.execute("CREATE INDEX IF NOT EXISTS profile_post_reactions_post_id ON profile_post_reactions(post_id)")
        duplicate_usernames = con.execute(
            "SELECT 1 FROM users GROUP BY lower(username) HAVING count(*) > 1 LIMIT 1"
        ).fetchone()
        if not duplicate_usernames:
            con.execute("CREATE UNIQUE INDEX IF NOT EXISTS users_username_nocase_unique ON users(username COLLATE NOCASE)")
        con.execute("CREATE UNIQUE INDEX IF NOT EXISTS users_email_nocase_unique ON users(email COLLATE NOCASE) WHERE email IS NOT NULL")
        con.execute("CREATE UNIQUE INDEX IF NOT EXISTS users_phone_unique ON users(phone) WHERE phone IS NOT NULL")

        defaults = {
            "account_levels": [
                {"id": "starter", "title": "Начальный", "description": "Первый уровень после регистрации.", "criteria": {"messages": 0}, "limits": {"postsPerDay": 3, "storiesPerDay": 2, "communitiesCreated": 1, "channelsCreated": 1, "communitiesJoined": 10, "channelsJoined": 10}, "reward": {"stars": 0}, "starsPrice": 0, "purchaseReward": {"stars": 0}},
                {"id": "active", "title": "Активный", "description": "Общайтесь и наполняйте свой профиль.", "criteria": {"messages": 20, "posts": 2, "stories": 1}, "limits": {"postsPerDay": 10, "storiesPerDay": 8, "communitiesCreated": 3, "channelsCreated": 3, "communitiesJoined": 50, "channelsJoined": 50}, "reward": {"stars": 50}, "starsPrice": 120, "purchaseReward": {"stars": 0}},
                {"id": "pro", "title": "Профи", "description": "Для постоянных участников сообщества.", "criteria": {"messages": 100, "posts": 10, "reviews": 2}, "limits": {"postsPerDay": 30, "storiesPerDay": 20, "communitiesCreated": 10, "channelsCreated": 10, "communitiesJoined": 200, "channelsJoined": 200}, "reward": {"stars": 200}, "starsPrice": 300, "purchaseReward": {"stars": 0}},
            ],
            "features": {
                "communities": True, "reviews": True, "donations": True,
            },
            "ui_appearance": DEFAULT_UI_APPEARANCE,
            "channel_reactions": list(DEFAULT_CHANNEL_REACTIONS),
            "channel_monetization": DEFAULT_CHANNEL_MONETIZATION,
            "channel_activity_regulator": DEFAULT_CHANNEL_ACTIVITY_REGULATOR,
            "public_branding": DEFAULT_PUBLIC_BRANDING,
            "public_legal": DEFAULT_PUBLIC_LEGAL,
        }
        for key, value in defaults.items():
            con.execute("INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)", (key, dumps(value)))
        levels_row = con.execute("SELECT value FROM settings WHERE key = 'account_levels'").fetchone()
        try:
            normalized_levels = normalize_account_levels(loads(levels_row["value"], []) if levels_row else defaults["account_levels"])
        except ValueError:
            normalized_levels = defaults["account_levels"]
        if not levels_row or loads(levels_row["value"], []) != normalized_levels:
            con.execute("INSERT OR REPLACE INTO settings(key, value) VALUES ('account_levels', ?)", (dumps(normalized_levels),))
        appearance_row = con.execute("SELECT value FROM settings WHERE key = 'ui_appearance'").fetchone()
        try:
            normalized_appearance = normalize_ui_appearance(loads(appearance_row["value"], {}) if appearance_row else DEFAULT_UI_APPEARANCE)
        except ValueError:
            normalized_appearance = DEFAULT_UI_APPEARANCE
        if not appearance_row or loads(appearance_row["value"], {}) != normalized_appearance:
            con.execute("INSERT OR REPLACE INTO settings(key, value) VALUES ('ui_appearance', ?)", (dumps(normalized_appearance),))
        monetization_row = con.execute("SELECT value FROM settings WHERE key = 'channel_monetization'").fetchone()
        try:
            normalized_monetization = normalize_channel_monetization(loads(monetization_row["value"], {}) if monetization_row else DEFAULT_CHANNEL_MONETIZATION)
        except ValueError:
            normalized_monetization = DEFAULT_CHANNEL_MONETIZATION
        if not monetization_row or loads(monetization_row["value"], {}) != normalized_monetization:
            con.execute("INSERT OR REPLACE INTO settings(key, value) VALUES ('channel_monetization', ?)", (dumps(normalized_monetization),))
        regulator_row = con.execute("SELECT value FROM settings WHERE key = 'channel_activity_regulator'").fetchone()
        try:
            normalized_regulator = normalize_channel_activity_regulator(loads(regulator_row["value"], {}) if regulator_row else DEFAULT_CHANNEL_ACTIVITY_REGULATOR)
        except ValueError:
            normalized_regulator = DEFAULT_CHANNEL_ACTIVITY_REGULATOR
        if not regulator_row or loads(regulator_row["value"], {}) != normalized_regulator:
            con.execute("INSERT OR REPLACE INTO settings(key, value) VALUES ('channel_activity_regulator', ?)", (dumps(normalized_regulator),))
        branding_row = con.execute("SELECT value FROM settings WHERE key = 'public_branding'").fetchone()
        try:
            normalized_branding = normalize_public_branding(loads(branding_row["value"], {}) if branding_row else DEFAULT_PUBLIC_BRANDING)
        except ValueError:
            normalized_branding = DEFAULT_PUBLIC_BRANDING
        if not branding_row or loads(branding_row["value"], {}) != normalized_branding:
            con.execute("INSERT OR REPLACE INTO settings(key, value) VALUES ('public_branding', ?)", (dumps(normalized_branding),))
        legal_row = con.execute("SELECT value FROM settings WHERE key = 'public_legal'").fetchone()
        try:
            normalized_legal = normalize_public_legal(loads(legal_row["value"], {}) if legal_row else DEFAULT_PUBLIC_LEGAL)
        except ValueError:
            normalized_legal = DEFAULT_PUBLIC_LEGAL
        if not legal_row or loads(legal_row["value"], {}) != normalized_legal:
            con.execute("INSERT OR REPLACE INTO settings(key, value) VALUES ('public_legal', ?)", (dumps(normalized_legal),))

        if not con.execute("SELECT 1 FROM promotions LIMIT 1").fetchone():
            add_promotion(con, "Пригласить друга", "Откройте сайт по реферальной ссылке и получите звёзды.", "referral_open", 1, 25, 1)
            add_promotion(con, "Написать отзыв", "Оставьте отзыв о странице ВК, ТГ или сайте.", "review_created", 1, 15, 3)
            add_promotion(con, "Создать группу с 10 участниками", "Создайте группу и пригласите участников.", "group_members", 10, 100, 1)
        if not con.execute("SELECT 1 FROM activity_rewards LIMIT 1").fetchone():
            add_activity_reward(
                con,
                "Активный участник",
                "Откройте новые возможности Chat-Pro и получите звёзды.",
                {"direct_chats": 5, "channels_joined": 5, "communities_joined": 5},
                {"stars": 100, "premiumDays": 0},
            )
        review_reward_key = "activity_reward_chat_pro_review_v1"
        if not con.execute("SELECT 1 FROM settings WHERE key = ?", (review_reward_key,)).fetchone():
            add_activity_reward(
                con,
                "Ролик или пост о Chat‑Pro",
                "Опубликуйте ролик или пост в своём канале и добавьте «Chat-Pro» или «Чат-Про» в текст или подпись.",
                {"chat_pro_review_video": 1},
                {"stars": 100, "premiumDays": 0},
            )
            con.execute("INSERT INTO settings(key, value) VALUES (?, ?)", (review_reward_key, dumps({"createdAt": now()})))
        vk_review_transition_key = "vk_review_reward_transition_v1"
        if not con.execute("SELECT 1 FROM settings WHERE key = ?", (vk_review_transition_key,)).fetchone():
            # The former fixed 100-star local-channel reward is replaced by VK verification and like-based rewards.
            con.execute("UPDATE activity_rewards SET active = 0 WHERE title IN ('Видеообзор Chat‑Pro', 'Ролик или пост о Chat‑Pro') AND criteria_json LIKE '%chat_pro_review_video%'")
            con.execute("INSERT INTO settings(key, value) VALUES (?, ?)", (vk_review_transition_key, dumps({"createdAt": now()})))


def uid(prefix: str) -> str:
    return f"{prefix}_{secrets.token_urlsafe(10)}"


def secret_password_hash(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def add_promotion(con, title, description, action_type, target_count, reward_amount, daily_limit):
    con.execute(
        """INSERT INTO promotions(id,title,description,action_type,target_count,reward_amount,daily_limit,created_at)
           VALUES (?,?,?,?,?,?,?,?)""",
        (uid("promo"), title, description, action_type, target_count, reward_amount, daily_limit, now()),
    )


def add_activity_reward(con, title, description, criteria, reward):
    con.execute(
        """INSERT INTO activity_rewards(id,title,description,criteria_json,reward_stars,premium_days,reward_json,active,created_at)
           VALUES (?,?,?,?,?,?,?,1,?)""",
        (
            uid("activity_reward"),
            title,
            description,
            dumps(criteria),
            reward["stars"],
            reward["premiumDays"],
            dumps(reward),
            now(),
        ),
    )


def get_user_by_token(con: sqlite3.Connection, headers) -> sqlite3.Row | None:
    auth = headers.get("Authorization", "")
    token = auth.replace("Bearer ", "", 1).strip() if auth.startswith("Bearer ") else ""
    if not token:
        return None
    return con.execute(
        "SELECT users.* FROM users JOIN sessions ON sessions.user_id = users.id WHERE sessions.token = ? AND users.deletion_due_at IS NULL",
        (token,),
    ).fetchone()


ACCOUNT_DELETION_GRACE_SECONDS = 7 * 24 * 60 * 60


def cleanup_expired_deleted_accounts(con: sqlite3.Connection, current: int | None = None) -> int:
    timestamp = now() if current is None else current
    return con.execute(
        "DELETE FROM users WHERE deletion_due_at IS NOT NULL AND deletion_due_at <= ?",
        (timestamp,),
    ).rowcount


def username_taken(con: sqlite3.Connection, username: str, exclude_user_id: str | None = None) -> bool:
    query = "SELECT 1 FROM users WHERE username = ? COLLATE NOCASE"
    params = [username]
    if exclude_user_id:
        query += " AND id != ?"
        params.append(exclude_user_id)
    return bool(con.execute(query, params).fetchone())


def tick_boosts(con: sqlite3.Connection) -> None:
    current = now()
    jobs = con.execute("SELECT * FROM boost_jobs WHERE active = 1 AND remaining > 0").fetchall()
    for job in jobs:
        minutes = max(0, (current - job["last_tick"]) // 60)
        if minutes <= 0:
            continue
        add_count = min(job["remaining"], minutes * job["amount_per_minute"])
        if add_count <= 0:
            continue
        if job["target_type"] == "chat" and job["metric"] == "subscribers":
            con.execute("UPDATE chats SET subscriber_boost = subscriber_boost + ? WHERE id = ?", (add_count, job["target_id"]))
        elif job["target_type"] == "message" and job["metric"] == "views":
            con.execute("UPDATE messages SET views_boost = views_boost + ? WHERE id = ?", (add_count, job["target_id"]))
        elif job["target_type"] == "message" and job["metric"] == "reactions":
            row = con.execute("SELECT reactions_json FROM messages WHERE id = ?", (job["target_id"],)).fetchone()
            if row:
                reactions = loads(row["reactions_json"], {}) or {}
                reactions["⭐"] = int(reactions.get("⭐", 0)) + add_count
                con.execute("UPDATE messages SET reactions_json = ? WHERE id = ?", (dumps(reactions), job["target_id"]))
        remaining = job["remaining"] - add_count
        con.execute(
            "UPDATE boost_jobs SET remaining = ?, active = ?, last_tick = ? WHERE id = ?",
            (remaining, 1 if remaining > 0 else 0, current, job["id"]),
        )


def weighted_channel_post(con: sqlite3.Connection, channel_id: str) -> sqlite3.Row | None:
    posts = con.execute(
        """SELECT id, text, media_type, reactions_json FROM messages
           WHERE chat_id = ? AND media_type != 'system' AND deleted_by_admin = 0
           ORDER BY created_at DESC, rowid DESC LIMIT 500""",
        (channel_id,),
    ).fetchall()
    if not posts:
        return None
    total_weight = sum((len(posts) - index) ** 2 for index in range(len(posts)))
    selected = secrets.randbelow(total_weight)
    for index, post in enumerate(posts):
        selected -= (len(posts) - index) ** 2
        if selected < 0:
            return post
    return posts[0]


def automated_commenter_pool(con: sqlite3.Connection, commenter_ids=None) -> list[sqlite3.Row]:
    requested = []
    if isinstance(commenter_ids, list):
        requested = list(dict.fromkeys(str(item).strip() for item in commenter_ids if str(item).strip()))
    if requested:
        placeholders = ",".join("?" for _ in requested)
        rows = con.execute(
            f"SELECT id, user_id FROM automated_commenters WHERE id IN ({placeholders})",
            requested,
        ).fetchall()
        by_id = {row["id"]: row for row in rows}
        return [by_id[item] for item in requested if item in by_id]
    return con.execute("SELECT id, user_id FROM automated_commenters ORDER BY created_at, id").fetchall()


def next_automated_commenter(con: sqlite3.Connection, scope_key: str, commenters: list[sqlite3.Row]) -> sqlite3.Row | None:
    if not commenters:
        return None
    commenter_ids = [row["id"] for row in commenters]
    current = con.execute(
        "SELECT * FROM automated_commenter_rotations WHERE scope_key = ?",
        (scope_key,),
    ).fetchone()
    stored_ids = loads(current["commenter_ids_json"], []) if current else []
    order = loads(current["order_json"], []) if current else []
    if stored_ids != commenter_ids or not isinstance(order, list) or set(order) != set(commenter_ids):
        order = commenter_ids[:]
        secrets.SystemRandom().shuffle(order)
        position = 0
        last_commenter_id = None
    else:
        position = max(0, min(int(current["position"] or 0), len(order) - 1))
        last_commenter_id = current["last_commenter_id"]
    if len(order) > 1 and order[position] == last_commenter_id:
        position = (position + 1) % len(order)
    selected_id = order[position]
    next_position = position + 1
    if next_position >= len(order):
        secrets.SystemRandom().shuffle(order)
        if len(order) > 1 and order[0] == selected_id:
            order[0], order[1] = order[1], order[0]
        next_position = 0
    con.execute(
        """INSERT INTO automated_commenter_rotations(scope_key,commenter_ids_json,order_json,position,last_commenter_id,updated_at)
           VALUES (?,?,?,?,?,?)
           ON CONFLICT(scope_key) DO UPDATE SET commenter_ids_json=excluded.commenter_ids_json,
             order_json=excluded.order_json, position=excluded.position,
             last_commenter_id=excluded.last_commenter_id, updated_at=excluded.updated_at""",
        (scope_key, dumps(commenter_ids), dumps(order), next_position, selected_id, now()),
    )
    return next(row for row in commenters if row["id"] == selected_id)


def queue_ai_activity_comment(con: sqlite3.Connection, source_key: str, message_id: str, commenter_id: str, current: int) -> None:
    con.execute(
        """INSERT INTO activity_comment_jobs(id,source_key,message_id,commenter_id,categories_json,publish_at,created_at)
           VALUES (?,?,?,?,?,?,?)""",
        (uid("activitycomment"), source_key, message_id, commenter_id,
         dumps(["support", "opinion", "question"]), current, current),
    )


def tick_channel_activity_regulator(con: sqlite3.Connection) -> None:
    """Maintain organic-looking channel counters without requiring an account level."""
    settings = channel_activity_regulator_settings(con)
    if not settings["enabled"]:
        return
    current = now()
    reactions = channel_reaction_emojis(con)
    channels = con.execute(
        """SELECT id, created_at, subscriber_count, subscriber_boost
           FROM chats WHERE type = 'channel' AND subscriber_count + subscriber_boost > 0"""
    ).fetchall()
    for channel in channels:
        subscribers = max(0, int(channel["subscriber_count"] or 0) + int(channel["subscriber_boost"] or 0))
        posts = con.execute(
            """SELECT id, created_at, views, views_boost, reactions_json FROM messages
               WHERE chat_id = ? AND media_type != 'system' AND deleted_by_admin = 0
               ORDER BY created_at DESC, rowid DESC LIMIT 500""",
            (channel["id"],),
        ).fetchall()
        for post in posts:
            age_ratio = min(1.0, max(0.0, current - int(post["created_at"] or current)) / 86400)
            target_views = math.ceil(subscribers * settings["viewRatePercent"] / 100 * age_ratio)
            current_views = max(0, int(post["views"] or 0) + int(post["views_boost"] or 0))
            if target_views > current_views:
                con.execute("UPDATE messages SET views_boost = views_boost + ? WHERE id = ?", (target_views - current_views, post["id"]))
                current_views = target_views
            target_reactions = math.floor(current_views * settings["reactionRatePercent"] / 100)
            current_reactions = sum(max(0, int(value or 0)) for value in (loads(post["reactions_json"], {}) or {}).values())
            if target_reactions > current_reactions:
                reaction_map = loads(post["reactions_json"], {}) or {}
                for _ in range(target_reactions - current_reactions):
                    emoji = reactions[secrets.randbelow(len(reactions))]
                    reaction_map[emoji] = int(reaction_map.get(emoji, 0)) + 1
                con.execute("UPDATE messages SET reactions_json = ? WHERE id = ?", (dumps(reaction_map), post["id"]))
        state = con.execute(
            "SELECT unsubscribe_progress, last_unsubscribe_tick_at FROM channel_activity_regulator_state WHERE channel_id = ?",
            (channel["id"],),
        ).fetchone()
        if not state:
            con.execute(
                "INSERT INTO channel_activity_regulator_state(channel_id,unsubscribe_progress,last_unsubscribe_tick_at) VALUES (?,?,?)",
                (channel["id"], 0, current),
            )
            continue
        elapsed = max(0, current - int(state["last_unsubscribe_tick_at"] or current))
        initial_period = settings["initialUnsubscribeMonths"] * 30 * 86400
        channel_age = max(0, current - int(channel["created_at"] or current))
        weekly_percent = settings["weeklyUnsubscribePercent"] if channel_age < initial_period else settings["settledWeeklyUnsubscribePercent"]
        progress = float(state["unsubscribe_progress"] or 0) + subscribers * weekly_percent / 100 * elapsed / (7 * 86400)
        remove_count = min(max(0, int(channel["subscriber_boost"] or 0)), int(progress))
        if remove_count:
            con.execute("UPDATE chats SET subscriber_boost = subscriber_boost - ? WHERE id = ?", (remove_count, channel["id"]))
            progress -= remove_count
        con.execute(
            "UPDATE channel_activity_regulator_state SET unsubscribe_progress = ?, last_unsubscribe_tick_at = ? WHERE channel_id = ?",
            (progress, current, channel["id"]),
        )


def tick_channel_growth(con: sqlite3.Connection) -> None:
    current = now()
    jobs = con.execute("SELECT * FROM channel_growth_jobs WHERE active = 1").fetchall()
    reaction_icons = channel_reaction_emojis(con)
    commenters = automated_commenter_pool(con)
    for job in jobs:
        elapsed = max(0, min(current, job["ends_at"]) - job["starts_at"])
        targets = {metric: elapsed * job[f"{metric}_per_hour"] // 3600 for metric in ("subscribers", "views", "reactions", "comments")}
        additions = {metric: targets[metric] - job[f"{metric}_added"] for metric in targets}
        if additions["subscribers"] > 0:
            con.execute("UPDATE chats SET subscriber_boost = subscriber_boost + ? WHERE id = ?", (additions["subscribers"], job["channel_id"]))
        for _ in range(max(0, additions["views"])):
            post = weighted_channel_post(con, job["channel_id"])
            if post:
                con.execute("UPDATE messages SET views_boost = views_boost + 1 WHERE id = ?", (post["id"],))
        for _ in range(max(0, additions["reactions"])):
            post = weighted_channel_post(con, job["channel_id"])
            if post:
                reactions = loads(post["reactions_json"], {}) or {}
                icon = reaction_icons[secrets.randbelow(len(reaction_icons))]
                reactions[icon] = int(reactions.get(icon, 0)) + 1
                con.execute("UPDATE messages SET reactions_json = ? WHERE id = ?", (dumps(reactions), post["id"]))
        if additions["comments"] > 0 and commenters:
            for _ in range(additions["comments"]):
                post = weighted_channel_post(con, job["channel_id"])
                if post:
                    commenter = next_automated_commenter(con, f"channel-growth:{job['id']}", commenters)
                    if not commenter:
                        continue
                    queue_ai_activity_comment(con, f"channel-growth:{job['id']}", post["id"], commenter["id"], current)
        con.execute("UPDATE channel_growth_jobs SET subscribers_added = ?, views_added = ?, reactions_added = ?, comments_added = ?, active = ? WHERE id = ?", (targets["subscribers"], targets["views"], targets["reactions"], targets["comments"], 1 if current < job["ends_at"] else 0, job["id"]))


def demo_activity_post(con: sqlite3.Connection, channel_id: str, metric: str = "views") -> sqlite3.Row | None:
    """Choose an eligible post with the lowest activity for the requested metric."""
    posts = con.execute(
        """SELECT message.id, message.text, message.media_type, message.reactions_json, message.views_boost,
                  (SELECT count(*) FROM channel_comments comment WHERE comment.message_id = message.id) AS comments_count
           FROM messages message
           WHERE message.chat_id = ? AND message.media_type != 'system' AND message.deleted_by_admin = 0
           ORDER BY message.created_at, message.rowid""",
        (channel_id,),
    ).fetchall()
    if not posts:
        return None
    if metric == "views":
        scores = [max(0, int(post["views_boost"] or 0)) for post in posts]
    elif metric == "reactions":
        scores = [sum(max(0, int(value or 0)) for value in (loads(post["reactions_json"], {}) or {}).values()) for post in posts]
    elif metric == "comments":
        scores = [max(0, int(post["comments_count"] or 0)) for post in posts]
    else:
        raise ValueError("Неизвестный показатель активности.")
    lowest = min(scores)
    candidates = [post for post, score in zip(posts, scores) if score == lowest]
    return candidates[secrets.randbelow(len(candidates))]


def account_level_available_for_user(con: sqlite3.Connection, user_id: str, required_level_id: str) -> bool:
    required_level_id = str(required_level_id or "").strip()
    if not required_level_id:
        return True
    processor = object.__new__(Handler)
    data = processor.account_level_data(con, user_id)
    levels = data.get("levels", [])
    indexes = {level["id"]: index for index, level in enumerate(levels)}
    return required_level_id in indexes and indexes.get(data.get("current", {}).get("id"), -1) >= indexes[required_level_id]


def demo_activity_variations() -> dict[str, float]:
    return {metric: round(.86 + secrets.randbelow(29) / 100, 2) for metric in ("subscribers", "views", "reactions", "comments")}


def apply_demo_activity_donations(con: sqlite3.Connection, subscription, current: int) -> None:
    count = int(subscription["donation_count"] or 0)
    minimum = int(subscription["donation_min_stars"] or 0)
    maximum = int(subscription["donation_max_stars"] or 0)
    if not count or minimum <= 0 or maximum < minimum:
        return
    interval = max(1, int(subscription["donation_post_interval"] or 1))
    posts = con.execute(
        """SELECT id, sender_id, text, views, views_boost, reactions_json FROM messages
           WHERE chat_id = ? AND media_type != 'system' AND deleted_by_admin = 0 AND created_at >= ?
           ORDER BY created_at, rowid""",
        (subscription["channel_id"], subscription["starts_at"]),
    ).fetchall()
    for index, post in enumerate(posts, start=1):
        if index % interval:
            continue
        reactions = sum(max(0, int(value or 0)) for value in (loads(post["reactions_json"], {}) or {}).values())
        views = max(0, int(post["views"] or 0) + int(post["views_boost"] or 0))
        engagement = min(1.0, views / 1000 + reactions / 100)
        for donation_number in range(1, count + 1):
            if con.execute("SELECT 1 FROM demo_activity_donations WHERE subscription_id = ? AND message_id = ? AND donation_number = ?", (subscription["id"], post["id"], donation_number)).fetchone():
                continue
            spread = maximum - minimum
            variation = .80 + secrets.randbelow(41) / 100
            amount = minimum + int(round(spread * min(1, (.2 + .8 * engagement) * variation)))
            try:
                Handler.credit_stars(object.__new__(Handler), con, post["sender_id"], amount)
            except ValueError:
                continue
            con.execute("INSERT INTO demo_activity_donations(subscription_id,message_id,donation_number,recipient_user_id,amount,created_at) VALUES (?,?,?,?,?,?)", (subscription["id"], post["id"], donation_number, post["sender_id"], amount, current))
            Handler.record_star_transaction(object.__new__(Handler), con, post["sender_id"], amount, "demo_activity_donation", f"Автодонат за публикацию «{post['text'][:60] or post['id']}»")


def sync_account_level_activity_packages(con: sqlite3.Connection) -> None:
    """Attach free level-gated packages to every eligible channel with a post."""
    packages = con.execute(
        """SELECT * FROM demo_activity_packages
           WHERE required_account_level_id != '' AND price_stars = 0"""
    ).fetchall()
    current = now()
    for package in packages:
        channels = con.execute(
            """SELECT channel.id, channel.owner_id FROM chats channel
               WHERE channel.type = 'channel' AND channel.owner_id IS NOT NULL
                 AND EXISTS (SELECT 1 FROM messages post
                             WHERE post.chat_id = channel.id AND post.media_type != 'system' AND post.deleted_by_admin = 0)"""
        ).fetchall()
        for channel in channels:
            if not account_level_available_for_user(con, channel["owner_id"], package["required_account_level_id"]):
                continue
            exists = con.execute(
                "SELECT 1 FROM demo_activity_subscriptions WHERE package_id = ? AND channel_id = ? AND active = 1",
                (package["id"], channel["id"]),
            ).fetchone()
            if exists:
                continue
            con.execute(
                """INSERT INTO demo_activity_subscriptions(id,package_id,channel_id,starts_at,ends_at,auto_renew,activity_last_tick_at,created_at)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (uid("demosubscription"), package["id"], channel["id"], current,
                 current + max(1, package["duration_days"]) * 86400, 1 if package["indefinite"] else 0, current, current),
            )


def tick_demo_activity(con: sqlite3.Connection) -> None:
    current = now()
    reaction_icons = channel_reaction_emojis(con)
    rows = con.execute(
        """SELECT subscription.*, package.subscribers_per_day, package.views_per_day, package.reactions_per_day,
                  package.comments_per_day, package.post_limit, package.duration_days, package.fade_duration_days,
                  package.indefinite, package.commenter_ids_json, package.required_account_level_id,
                   package.donation_count, package.donation_post_interval, package.donation_min_stars,
                   package.donation_max_stars, package.inactivity_days, chat.owner_id
           FROM demo_activity_subscriptions subscription
           JOIN demo_activity_packages package ON package.id = subscription.package_id
           JOIN chats chat ON chat.id = subscription.channel_id
           WHERE subscription.active = 1"""
    ).fetchall()
    for row in rows:
        required_level_id = str(row["required_account_level_id"] or "")
        if required_level_id and not account_level_available_for_user(con, row["owner_id"], required_level_id):
            if row["level_paused_at"] is None:
                con.execute("UPDATE demo_activity_subscriptions SET level_paused_at = ? WHERE id = ?", (current, row["id"]))
            continue
        if row["level_paused_at"] is not None:
            paused_for = max(0, current - int(row["level_paused_at"]))
            con.execute("""UPDATE demo_activity_subscriptions
                           SET starts_at = starts_at + ?, ends_at = ends_at + ?, level_paused_at = ?, activity_last_tick_at = ?
                           WHERE id = ?""", (paused_for, paused_for, None, current, row["id"]))
            continue
        latest_post = con.execute(
            """SELECT created_at FROM messages
               WHERE chat_id = ? AND media_type != 'system' AND deleted_by_admin = 0
               ORDER BY created_at DESC, rowid DESC LIMIT 1""",
            (row["channel_id"],),
        ).fetchone()
        inactivity_days = max(1, int(row["inactivity_days"] or 3))
        inactivity_fade_started_at = None
        if latest_post is None:
            inactivity_fade_started_at = int(row["starts_at"]) + inactivity_days * 86400
        elif current >= int(latest_post["created_at"]) + inactivity_days * 86400:
            inactivity_fade_started_at = int(latest_post["created_at"]) + inactivity_days * 86400
        if inactivity_fade_started_at is not None:
            fade_duration = int(row["fade_duration_days"] or 0) * 86400
            if not fade_duration or current >= inactivity_fade_started_at + fade_duration:
                con.execute("UPDATE demo_activity_subscriptions SET active = 0, inactivity_fade_started_at = ? WHERE id = ?", (inactivity_fade_started_at, row["id"]))
                continue
            con.execute("UPDATE demo_activity_subscriptions SET inactivity_fade_started_at = ? WHERE id = ?", (inactivity_fade_started_at, row["id"]))
        elif row["inactivity_fade_started_at"] is not None:
            con.execute("UPDATE demo_activity_subscriptions SET inactivity_fade_started_at = NULL WHERE id = ?", (row["id"],))
        in_fade = inactivity_fade_started_at is not None
        if not row["indefinite"] and current >= row["ends_at"]:
            if row["auto_renew"]:
                duration = row["duration_days"] * 86400
                con.execute("""UPDATE demo_activity_subscriptions
                               SET starts_at=?, ends_at=?, subscribers_added=0, views_added=0, reactions_added=0,
                                   comments_added=0, activity_last_tick_at=?, activity_progress_json='{}'
                               WHERE id=?""", (current, current + duration, current, row["id"]))
                continue
            fade_duration = row["fade_duration_days"] * 86400
            if not fade_duration or current >= row["ends_at"] + fade_duration:
                con.execute("UPDATE demo_activity_subscriptions SET active = 0 WHERE id = ?", (row["id"],))
                continue
            in_fade = True
        last_tick = int(row["activity_last_tick_at"] or row["starts_at"] or current)
        elapsed = max(0, current - last_tick)
        if not elapsed:
            continue
        multiplier = 1
        stored_multiplier = max(1, int(row["spike_multiplier"] or 1))
        spike_starts = row["spike_starts_at"]
        spike_ends = row["spike_ends_at"]
        next_spike = row["next_spike_at"]
        if spike_starts and spike_ends and int(spike_starts) <= current < int(spike_ends):
            multiplier = stored_multiplier
        elif not next_spike or current >= int(next_spike):
            spike_starts = current + (15 + secrets.randbelow(346)) * 60
            spike_ends = int(spike_starts) + (2 + secrets.randbelow(5)) * 3600
            next_spike = int(spike_ends) + (12 + secrets.randbelow(49)) * 3600
            stored_multiplier = (3, 4, 5, 10)[secrets.randbelow(4)]
        progress = loads(row["activity_progress_json"], {}) or {}
        variations = loads(row["metric_variation_json"], {}) or demo_activity_variations()
        fade_started_at = inactivity_fade_started_at if inactivity_fade_started_at is not None else row["ends_at"]
        fade_factor = 1.0 if not in_fade else max(.12, 1 - (current - fade_started_at) / max(1, row["fade_duration_days"] * 86400))
        additions = {}
        for metric in ("subscribers", "views", "reactions", "comments"):
            previous = float(progress.get(metric, 0))
            increment = row[f"{metric}_per_day"] * elapsed / 86400 * float(variations.get(metric, 1)) * multiplier * fade_factor
            updated = previous + increment
            additions[metric] = max(0, int(updated) - int(previous))
            progress[metric] = updated
        if additions["subscribers"]:
            con.execute("UPDATE chats SET subscriber_boost = subscriber_boost + ? WHERE id = ?", (additions["subscribers"], row["channel_id"]))
        apply_demo_activity_donations(con, row, current)
        commenters = automated_commenter_pool(con)
        applied = {"subscribers": additions["subscribers"], "views": 0, "reactions": 0, "comments": 0}
        for metric in ("views", "reactions", "comments"):
            for _ in range(additions[metric]):
                post = demo_activity_post(con, row["channel_id"], metric)
                if not post:
                    break
                if metric == "views":
                    con.execute("UPDATE messages SET views_boost = views_boost + 1 WHERE id = ?", (post["id"],))
                elif metric == "reactions":
                    reactions = loads(post["reactions_json"], {}) or {}
                    icon = reaction_icons[secrets.randbelow(len(reaction_icons))]
                    reactions[icon] = int(reactions.get(icon, 0)) + 1
                    con.execute("UPDATE messages SET reactions_json = ? WHERE id = ?", (dumps(reactions), post["id"]))
                elif not commenters:
                    break
                else:
                    author = next_automated_commenter(con, f"demo-package:{row['id']}", commenters)
                    if not author:
                        break
                    queue_ai_activity_comment(con, f"demo-package:{row['id']}", post["id"], author["id"], current)
                applied[metric] += 1
        con.execute(
            """UPDATE demo_activity_subscriptions
               SET subscribers_added=subscribers_added + ?, views_added=views_added + ?, reactions_added=reactions_added + ?,
                   comments_added=comments_added + ?, activity_last_tick_at=?, activity_progress_json=?, metric_variation_json=?,
                   spike_multiplier=?, spike_starts_at=?, spike_ends_at=?, next_spike_at=? WHERE id=?""",
            (applied["subscribers"], applied["views"], applied["reactions"], applied["comments"], current, dumps(progress), dumps(variations), stored_multiplier, spike_starts, spike_ends, next_spike, row["id"]),
        )

def publish_scheduled_posts(con: sqlite3.Connection) -> None:
    due_posts = con.execute("SELECT * FROM scheduled_posts WHERE publish_at <= ? ORDER BY publish_at, created_at", (now(),)).fetchall()
    for post in due_posts:
        if channel_post_limit_reached(con, post["chat_id"]):
            continue
        message_id = uid("msg")
        con.execute(
            "INSERT INTO messages(id,chat_id,sender_id,text,media_type,media_data,views,created_at) VALUES (?,?,?,?,?,?,?,?)",
            (message_id, post["chat_id"], post["sender_id"], post["text"], post["media_type"], post["media_data"], 1, now()),
        )
        schedule_automated_comments(con, message_id, post["chat_id"])
        con.execute("UPDATE chats SET updated_at = ? WHERE id = ?", (now(), post["chat_id"]))
        link = con.execute("SELECT target_chat_id FROM channel_links WHERE channel_id = ?", (post["chat_id"],)).fetchone()
        if link:
            channel = con.execute("SELECT title FROM chats WHERE id = ?", (post["chat_id"],)).fetchone()
            con.execute(
                "INSERT INTO messages(id,chat_id,sender_id,text,media_type,media_data,views,forwarded_from,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (uid("msg"), link["target_chat_id"], post["sender_id"], post["text"], post["media_type"], post["media_data"], 1, channel["title"] if channel else "Канал", post["publish_at"]),
            )
            con.execute("UPDATE chats SET updated_at = ? WHERE id = ?", (post["publish_at"], link["target_chat_id"]))
        con.execute("DELETE FROM scheduled_posts WHERE id = ?", (post["id"],))


def telegram_api(bot_token: str, method: str, payload: dict | None = None) -> dict:
    request = urlrequest.Request(
        f"https://api.telegram.org/bot{bot_token}/{method}",
        data=dumps(payload or {}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlrequest.urlopen(request, timeout=12) as response:
            result = loads(response.read().decode("utf-8"), {})
    except (urlerror.URLError, TimeoutError, json.JSONDecodeError) as error:
        raise ValueError("Не удалось связаться с Telegram. Проверьте токен и подключение.") from error
    if not isinstance(result, dict) or not result.get("ok"):
        description = str(result.get("description", "") if isinstance(result, dict) else "")
        if "webhook" in description.lower():
            raise ValueError("У бота настроен webhook. Отключите его, чтобы получать публикации через getUpdates.")
        raise ValueError("Telegram отклонил запрос. Проверьте токен и права бота в исходном канале.")
    return result.get("result", {})


def telegram_photo_data(bot_token: str, photo_sizes: list) -> str | None:
    for photo in reversed(photo_sizes if isinstance(photo_sizes, list) else []):
        if not isinstance(photo, dict) or int(photo.get("file_size", 0) or 0) > TELEGRAM_MEDIA_MAX_BYTES:
            continue
        file_id = str(photo.get("file_id", ""))
        if not file_id:
            continue
        try:
            file_info = telegram_api(bot_token, "getFile", {"file_id": file_id})
            file_path = str(file_info.get("file_path", ""))
            if not file_path:
                continue
            with urlrequest.urlopen(
                f"https://api.telegram.org/file/bot{bot_token}/{file_path}", timeout=15
            ) as response:
                image = response.read(TELEGRAM_MEDIA_MAX_BYTES + 1)
                content_type = response.headers.get_content_type()
            if len(image) > TELEGRAM_MEDIA_MAX_BYTES or not content_type.startswith("image/"):
                continue
            return f"data:{content_type};base64,{base64.b64encode(image).decode('ascii')}"
        except (ValueError, urlerror.URLError, TimeoutError):
            continue
    return None


def rss_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", value or ""))).strip()


def xml_child_text(entry: ElementTree.Element, names: tuple[str, ...]) -> str:
    for child in entry:
        local_name = child.tag.rsplit("}", 1)[-1].lower()
        if local_name in names:
            return rss_text("".join(child.itertext()))
    return ""


def xml_entry_link(entry: ElementTree.Element) -> str:
    for child in entry:
        if child.tag.rsplit("}", 1)[-1].lower() != "link":
            continue
        href = str(child.attrib.get("href", "")).strip()
        if href:
            return href
        text = rss_text("".join(child.itertext()))
        if text:
            return text
    return ""


def xml_entry_image(entry: ElementTree.Element, entry_link: str) -> str:
    candidates = []
    for child in entry:
        local_name = child.tag.rsplit("}", 1)[-1].lower()
        media_type = str(child.attrib.get("type", child.attrib.get("medium", ""))).lower()
        if local_name == "enclosure" and media_type and not media_type.startswith("image/"):
            continue
        if local_name in {"enclosure", "content", "thumbnail", "image"}:
            candidates.extend((child.attrib.get("url", ""), child.attrib.get("href", "")))
        if local_name in {"description", "summary", "content", "encoded"}:
            candidates.extend(re.findall(r"<img\b[^>]*\bsrc\s*=\s*['\"]([^'\"]+)", "".join(child.itertext()), flags=re.IGNORECASE))
    for candidate in candidates:
        candidate = str(candidate).strip()
        if candidate:
            return urljoin(entry_link, candidate)
    return ""


def validate_rss_url(value) -> str:
    url = str(value or "").strip()
    parsed = urlparse(url)
    if len(url) > 2048 or parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Укажите корректный публичный URL RSS-ленты по HTTP или HTTPS.")
    try:
        addresses = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)
    except socket.gaierror as error:
        raise ValueError("Не удалось найти сервер RSS-ленты.") from error
    for _, _, _, _, address in addresses:
        if not ipaddress.ip_address(address[0]).is_global:
            raise ValueError("RSS-лента должна находиться на публичном сервере.")
    return url


class SafeRssRedirect(urlrequest.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        validate_rss_url(newurl)
        return super().redirect_request(request, fp, code, msg, headers, newurl)


def fetch_rss_article_metadata(article_url: str) -> tuple[str, str]:
    if not article_url:
        return "", ""
    try:
        article_url = validate_rss_url(article_url)
        request = urlrequest.Request(article_url, headers={"User-Agent": "Chat-Pro RSS importer/1.0", "Accept": "text/html", "Accept-Encoding": "identity", "Connection": "close"})
        with urlrequest.build_opener(SafeRssRedirect).open(request, timeout=12) as response:
            page = response.read(RSS_MAX_BYTES + 1).decode("utf-8", "replace")
        if len(page) > RSS_MAX_BYTES:
            return "", ""
        metadata = {}
        for tag in re.findall(r"<meta\b[^>]*>", page, flags=re.IGNORECASE):
            property_name = re.search(r"\b(?:property|name)\s*=\s*['\"]([^'\"]+)", tag, flags=re.IGNORECASE)
            content = re.search(r"\bcontent\s*=\s*['\"]([^'\"]+)", tag, flags=re.IGNORECASE)
            if property_name and content:
                metadata.setdefault(property_name.group(1).lower(), rss_text(unescape(content.group(1))))
        description = next((metadata[name] for name in ("og:description", "twitter:description", "description") if metadata.get(name)), "")[:8_000]
        image_url = next((metadata[name] for name in ("og:image", "twitter:image") if metadata.get(name)), "")
        return description, urljoin(article_url, image_url) if image_url else ""
    except (ValueError, urlerror.URLError, socket.timeout, TimeoutError, OSError):
        return "", ""


def fetch_rss_image(image_url: str) -> str | None:
    if not image_url:
        return None
    try:
        image_url = validate_rss_url(image_url)
        request = urlrequest.Request(image_url, headers={"User-Agent": "Chat-Pro RSS importer/1.0", "Accept": "image/*", "Accept-Encoding": "identity", "Connection": "close"})
        with urlrequest.build_opener(SafeRssRedirect).open(request, timeout=15) as response:
            content_type = response.headers.get_content_type()
            image = response.read(RSS_IMAGE_MAX_BYTES + 1)
        if not content_type.startswith("image/") or len(image) > RSS_IMAGE_MAX_BYTES:
            return None
        return f"data:{content_type};base64,{base64.b64encode(image).decode('ascii')}"
    except (ValueError, urlerror.URLError, socket.timeout, TimeoutError, OSError):
        return None


def validate_vk_group_url(value) -> tuple[str, str]:
    source_url = str(value or "").strip()
    parsed = urlparse(source_url)
    if parsed.scheme != "https" or parsed.hostname not in {"vk.com", "www.vk.com", "m.vk.com", "vk.ru", "www.vk.ru", "m.vk.ru"}:
        raise ValueError("Укажите ссылку на публичную группу VK вида https://vk.com/имя_группы или https://vk.ru/имя_группы.")
    source_ref = parsed.path.strip("/").split("/", 1)[0]
    if not re.fullmatch(r"[A-Za-z0-9_.-]{2,80}", source_ref):
        raise ValueError("В ссылке VK не найдено корректное имя публичной группы.")
    return f"https://vk.com/{source_ref}", source_ref


def normalize_vk_keywords(value) -> list[str]:
    values = value.splitlines() if isinstance(value, str) else value if isinstance(value, list) else None
    if values is None:
        raise ValueError("Ключевые слова должны быть строкой или списком.")
    keywords = []
    for item in values:
        keyword = " ".join(str(item).split()).casefold()
        if keyword and keyword not in keywords:
            keywords.append(keyword[:120])
    if len(keywords) > 30:
        raise ValueError("Можно указать до 30 ключевых слов.")
    return keywords


def vk_api(access_token: str, method: str, params: dict | None = None):
    query = urlencode({**(params or {}), "access_token": access_token, "v": VK_API_VERSION})
    request = urlrequest.Request(f"https://api.vk.com/method/{method}?{query}", headers={"User-Agent": "Chat-Pro VK importer/1.0", "Accept": "application/json"})
    try:
        with urlrequest.urlopen(request, timeout=15) as response:
            payload = loads(response.read(RSS_MAX_BYTES + 1).decode("utf-8"), {})
    except (urlerror.URLError, socket.timeout, TimeoutError, OSError, json.JSONDecodeError) as error:
        raise ValueError("Не удалось связаться с VK. Проверьте подключение и токен.") from error
    if not isinstance(payload, dict) or "error" in payload:
        message = str(payload.get("error", {}).get("error_msg", "") if isinstance(payload, dict) else "")
        raise ValueError(f"VK отклонил запрос{f': {message}' if message else ''}. Проверьте токен и доступ к группе.")
    return payload.get("response")


def vk_group_data(access_token: str, source_ref: str) -> tuple[int, str]:
    groups = vk_api(access_token, "groups.getById", {"group_id": source_ref})
    if isinstance(groups, dict):
        groups = groups.get("groups", [])
    group = groups[0] if isinstance(groups, list) and groups else None
    group_id = int(group.get("id", 0) or 0) if isinstance(group, dict) else 0
    if not group_id:
        raise ValueError("VK не нашёл доступную публичную группу по этой ссылке.")
    return -group_id, str(group.get("name", source_ref))[:120]


def vk_target_message_text(message) -> str:
    text = " ".join(str(message["text"] or "").split())
    if str(message["source_type"] or "") == "vk":
        original_url = str(message["source_id"] or "").strip()
        if original_url.startswith("https://vk.") and original_url not in text:
            text = f"{text}\n\nИсточник: {original_url}".strip()
    return text[:10_000]


def vk_post_image_url(post: dict) -> str:
    for attachment in post.get("attachments", []) if isinstance(post.get("attachments"), list) else []:
        photo = attachment.get("photo") if isinstance(attachment, dict) and attachment.get("type") == "photo" else None
        sizes = photo.get("sizes") if isinstance(photo, dict) else None
        images = [item for item in sizes if isinstance(item, dict) and item.get("url")] if isinstance(sizes, list) else []
        if images:
            return str(max(images, key=lambda item: int(item.get("width", 0) or 0) * int(item.get("height", 0) or 0))["url"])
    return ""


def vk_official_video_player_url(access_token: str, video: dict, fallback_owner_id: int) -> str:
    try:
        owner_id = int(video.get("owner_id", fallback_owner_id) or fallback_owner_id)
        video_id = int(video.get("id", 0) or 0)
    except (TypeError, ValueError):
        return ""
    if not owner_id or video_id <= 0:
        return ""
    access_key = str(video.get("access_key", "") or "")
    video_ref = f"{owner_id}_{video_id}" + (f"_{access_key}" if re.fullmatch(r"[A-Za-z0-9_-]{1,128}", access_key) else "")
    try:
        result = vk_api(access_token, "video.get", {"videos": video_ref})
    except ValueError:
        return ""
    items = result.get("items", []) if isinstance(result, dict) else []
    player_url = str(items[0].get("player", "") or "") if items and isinstance(items[0], dict) else ""
    parsed = urlparse(player_url)
    params = parse_qs(parsed.query)
    if (
        parsed.scheme == "https"
        and parsed.hostname in {"vk.com", "www.vk.com", "vkvideo.ru", "www.vkvideo.ru"}
        and parsed.path == "/video_ext.php"
        and params.get("oid")
        and params.get("id")
        and params.get("hash")
    ):
        return player_url
    return ""


def vk_post_video(access_token: str, post: dict) -> tuple[bool, str, str]:
    for attachment in post.get("attachments", []) if isinstance(post.get("attachments"), list) else []:
        video = attachment.get("video") if isinstance(attachment, dict) and attachment.get("type") == "video" else None
        if not isinstance(video, dict):
            continue
        thumbnail_url = ""
        for field in ("image", "first_frame"):
            images = video.get(field)
            candidates = [item for item in images if isinstance(item, dict) and item.get("url")] if isinstance(images, list) else []
            if candidates:
                thumbnail = max(candidates, key=lambda item: int(item.get("width", 0) or 0) * int(item.get("height", 0) or 0))
                thumbnail_url = str(thumbnail["url"])
                break
        return True, thumbnail_url, vk_official_video_player_url(access_token, video, int(post.get("owner_id", 0) or 0))
    return False, "", ""


def discover_rss_feed(site_url: str) -> str:
    """Find a public RSS/Atom URL advertised by a site's HTML page."""
    site_url = validate_rss_url(site_url)
    request = urlrequest.Request(
        site_url,
        headers={"User-Agent": "Chat-Pro RSS importer/1.0", "Accept": "text/html,application/xhtml+xml", "Accept-Encoding": "identity", "Connection": "close"},
    )
    try:
        with urlrequest.build_opener(SafeRssRedirect).open(request, timeout=15) as response:
            page = response.read(RSS_MAX_BYTES + 1).decode("utf-8", "replace")
    except (urlerror.URLError, socket.timeout, TimeoutError, OSError) as error:
        raise ValueError("Не удалось открыть сайт и найти его RSS-ленту.") from error
    if len(page.encode("utf-8")) > RSS_MAX_BYTES:
        raise ValueError("Страница сайта слишком большая для поиска RSS-ленты.")
    candidates = []
    for tag in re.findall(r"<(?:link|a)\b[^>]*>", page, flags=re.IGNORECASE):
        href = re.search(r"\bhref\s*=\s*['\"]([^'\"]+)", tag, flags=re.IGNORECASE)
        if not href:
            continue
        relation = re.search(r"\brel\s*=\s*['\"]([^'\"]+)", tag, flags=re.IGNORECASE)
        content_type = re.search(r"\btype\s*=\s*['\"]([^'\"]+)", tag, flags=re.IGNORECASE)
        candidate = urljoin(site_url, unescape(href.group(1).strip()))
        if ((relation and "alternate" in relation.group(1).casefold()) or (content_type and "xml" in content_type.group(1).casefold()) or re.search(r"(?:rss|feed|\.xml)(?:[/?#]|$)", candidate, re.IGNORECASE)):
            candidates.append(candidate)
    # Some sites do not advertise their feed, but use a conventional public path.
    candidates.extend([urljoin(site_url, path) for path in ("/rss", "/rss/", "/feed", "/feed/", "/feed.xml", "/rss.xml")])
    for candidate in list(dict.fromkeys(candidates))[:12]:
        try:
            candidate = validate_rss_url(candidate)
            _, entries = fetch_rss_feed(candidate)
            if entries:
                return candidate
        except ValueError:
            continue
    raise ValueError("На сайте не удалось найти доступную RSS-ленту. Пришлите её прямую ссылку или выберите другой источник.")


def fetch_rss_feed(feed_url: str) -> tuple[str, list[dict]]:
    request = urlrequest.Request(feed_url, headers={"User-Agent": "Chat-Pro RSS importer/1.0", "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml", "Accept-Encoding": "identity", "Connection": "close"})
    try:
        with urlrequest.build_opener(SafeRssRedirect).open(request, timeout=20) as response:
            data = response.read(RSS_MAX_BYTES + 1)
    except (urlerror.URLError, socket.timeout, TimeoutError, OSError) as error:
        raise ValueError("RSS-лента не ответила вовремя или недоступна. Попробуйте другой публичный RSS-адрес.") from error
    if len(data) > RSS_MAX_BYTES:
        raise ValueError("RSS-лента слишком большая: допустимо до 500 КБ.")
    try:
        root = ElementTree.fromstring(data)
    except ElementTree.ParseError as error:
        raise ValueError("Сервер вернул некорректную RSS или Atom-ленту.") from error
    root_name = root.tag.rsplit("}", 1)[-1].lower()
    channel = next((child for child in root if child.tag.rsplit("}", 1)[-1].lower() == "channel"), root)
    feed_title = xml_child_text(channel, ("title",))[:120] or urlparse(feed_url).hostname or "RSS"
    entry_tag = "entry" if root_name == "feed" else "item"
    entries = []
    for entry in channel.iter():
        if entry.tag.rsplit("}", 1)[-1].lower() != entry_tag:
            continue
        title = xml_child_text(entry, ("title",))[:500]
        summary = xml_child_text(entry, ("description", "summary", "content", "encoded"))[:8_000]
        link = xml_entry_link(entry)
        image_url = xml_entry_image(entry, link)
        source_id = xml_child_text(entry, ("guid", "id")) or link or f"{title}\n{summary}"
        if source_id and (title or summary):
            entries.append({"id": source_id[:2_000], "title": title, "summary": summary, "link": link[:2_000], "imageUrl": image_url[:2_000]})
        if len(entries) >= RSS_MAX_ENTRIES:
            break
    if not entries:
        raise ValueError("В RSS-ленте не найдены публикации.")
    return feed_title, entries


def poll_rss_channels(con: sqlite3.Connection) -> None:
    current = now()
    due_sources = con.execute("SELECT * FROM rss_channel_sources WHERE next_poll_at <= ? ORDER BY next_poll_at LIMIT 20", (current,)).fetchall()
    for source in due_sources:
        claimed = con.execute(
            "UPDATE rss_channel_sources SET next_poll_at = ? WHERE id = ? AND next_poll_at <= ?",
            (current + RSS_POLL_INTERVAL, source["id"], current),
        ).rowcount
        if not claimed:
            continue
        # Do not retain SQLite's write lock while the external RSS server responds.
        # This lets a channel owner disconnect the source immediately, even mid-poll.
        con.commit()
        try:
            feed_title, entries = fetch_rss_feed(source["feed_url"])
            sender = con.execute("SELECT id FROM users WHERE id = ?", (source["created_by"],)).fetchone()
            if not sender:
                sender = con.execute("SELECT owner_id AS id FROM chats WHERE id = ?", (source["channel_id"],)).fetchone()
            if sender and sender["id"]:
                for entry in reversed(entries):
                    # The source could have been disconnected while its feed was loading.
                    # Re-check before every import so no new posts appear after disconnect.
                    if not con.execute("SELECT 1 FROM rss_channel_sources WHERE id = ? AND channel_id = ?", (source["id"], source["channel_id"])).fetchone():
                        break
                    if channel_post_limit_reached(con, source["channel_id"], current):
                        break
                    imported = con.execute(
                        "INSERT OR IGNORE INTO rss_source_imported_posts(source_id,entry_id,imported_at) VALUES (?,?,?)",
                        (source["id"], entry["id"], current),
                    ).rowcount
                    if not imported:
                        continue
                    page_summary, page_image_url = fetch_rss_article_metadata(entry["link"]) if not entry["summary"] or not entry["imageUrl"] else ("", "")
                    summary = entry["summary"] or page_summary
                    text = "\n\n".join(part for part in (entry["title"], summary) if part)[:10_000]
                    media_data = fetch_rss_image(entry["imageUrl"] or page_image_url)
                    if not media_data and entry["link"]:
                        # An RSS image URL can be stale, oversized or blocked by a CDN.
                        # In that case, use the article's og:image as a verified fallback.
                        if not page_image_url:
                            fallback_summary, page_image_url = fetch_rss_article_metadata(entry["link"])
                            if not summary:
                                summary = fallback_summary
                                text = "\n\n".join(part for part in (entry["title"], summary) if part)[:10_000]
                        if page_image_url and page_image_url != entry["imageUrl"]:
                            media_data = fetch_rss_image(page_image_url)
                    message_id = uid("msg")
                    con.execute(
                        """INSERT INTO messages(id,chat_id,sender_id,text,media_type,media_data,views,forwarded_from,source_type,source_id,created_at)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                        (message_id, source["channel_id"], sender["id"], text, "photo" if media_data else None, media_data, 1, f"RSS · {feed_title}", "rss", entry["link"] or entry["id"], current),
                    )
                    schedule_automated_comments(con, message_id, source["channel_id"], current)
                    con.execute("UPDATE chats SET updated_at = ? WHERE id = ?", (current, source["channel_id"]))
            con.execute("UPDATE rss_channel_sources SET feed_title = ?, last_sync_at = ?, last_error = NULL WHERE id = ?", (feed_title, current, source["id"]))
        except ValueError as error:
            con.execute("UPDATE rss_channel_sources SET last_sync_at = ?, last_error = ? WHERE id = ?", (current, str(error)[:300], source["id"]))


def poll_vk_channels(con: sqlite3.Connection, moderator=None) -> None:
    current = now()
    due_sources = con.execute("SELECT * FROM vk_channel_sources WHERE next_poll_at <= ? ORDER BY next_poll_at LIMIT 20", (current,)).fetchall()
    for source in due_sources:
        claimed = con.execute(
            "UPDATE vk_channel_sources SET next_poll_at = ? WHERE id = ? AND next_poll_at <= ?",
            (current + VK_POLL_INTERVAL, source["id"], current),
        ).rowcount
        if not claimed:
            continue
        con.commit()
        try:
            wall = vk_api(source["access_token"], "wall.get", {"owner_id": source["owner_id"], "count": 30, "filter": "owner"})
            posts = wall.get("items", []) if isinstance(wall, dict) else []
            sender = con.execute("SELECT id FROM users WHERE id = ?", (source["created_by"],)).fetchone()
            if not sender:
                sender = con.execute("SELECT owner_id AS id FROM chats WHERE id = ?", (source["channel_id"],)).fetchone()
            keywords = loads(source["keywords_json"], [])
            if sender and sender["id"]:
                for post in reversed(posts if isinstance(posts, list) else []):
                    if not isinstance(post, dict) or str(post.get("post_type", "post")) != "post":
                        continue
                    post_id = int(post.get("id", 0) or 0)
                    if not post_id or not con.execute("SELECT 1 FROM vk_channel_sources WHERE id = ? AND channel_id = ?", (source["id"], source["channel_id"])).fetchone():
                        continue
                    text = str(post.get("text", "")).strip()[:10_000]
                    if keywords and not any(keyword in text.casefold() for keyword in keywords):
                        continue
                    has_video, video_thumbnail_url, video_embed_url = vk_post_video(source["access_token"], post)
                    image_url = "" if has_video else vk_post_image_url(post)
                    if not text and not image_url and not has_video:
                        continue
                    if channel_post_limit_reached(con, source["channel_id"], current):
                        break
                    owner_id = int(post.get("owner_id", source["owner_id"]) or source["owner_id"])
                    original_url = f"https://vk.com/wall{owner_id}_{post_id}"
                    imported = con.execute(
                        "INSERT OR IGNORE INTO vk_source_imported_posts(source_id,post_id,imported_at) VALUES (?,?,?)",
                        (source["id"], post_id, current),
                    ).rowcount
                    if not imported:
                        if has_video and video_embed_url:
                            con.execute(
                                """UPDATE messages SET media_embed_url = ?
                                   WHERE source_type = 'vk' AND source_id = ? AND media_type = 'vk_video'
                                     AND COALESCE(media_embed_url, '') != ?""",
                                (video_embed_url, original_url, video_embed_url),
                            )
                        continue
                    media_data = fetch_rss_image(video_thumbnail_url if has_video else image_url)
                    message_id = uid("msg")
                    con.execute(
                        """INSERT INTO messages(id,chat_id,sender_id,text,media_type,media_data,media_embed_url,views,forwarded_from,source_type,source_id,created_at)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (message_id, source["channel_id"], sender["id"], text, "vk_video" if has_video else "photo" if media_data else None, media_data, video_embed_url or None, 1,
                         f"VK · {source['source_title']}", "vk", original_url, current),
                    )
                    schedule_automated_comments(con, message_id, source["channel_id"], current)
                    con.execute("UPDATE chats SET updated_at = ? WHERE id = ?", (current, source["channel_id"]))
            if moderator and source["moderation_enabled"]:
                moderate_vk_source_comments(con, source, posts if isinstance(posts, list) else [], current, moderator)
            con.execute("UPDATE vk_channel_sources SET last_sync_at = ?, last_error = NULL WHERE id = ?", (current, source["id"]))
        except ValueError as error:
            con.execute("UPDATE vk_channel_sources SET last_sync_at = ?, last_error = ? WHERE id = ?", (current, str(error)[:300], source["id"]))


def moderate_vk_source_comments(con: sqlite3.Connection, source, posts: list[dict], current: int, moderator) -> None:
    rule = con.execute(
        "SELECT * FROM ai_agent_comment_moderation_rules WHERE user_id = ? AND channel_id = ?",
        (source["created_by"], source["channel_id"]),
    ).fetchone()
    if not rule or rule["target_scope"] not in {"comments", "all"}:
        return
    words = [str(word).casefold() for word in loads(rule["blocked_words_json"], []) if str(word).strip()]
    semantic_rules = [str(item) for item in loads(rule["semantic_rules_json"], []) if str(item).strip()]
    model_profile = moderator.ai_agent_settings(con, source["created_by"])["modelProfile"]
    semantic_budget = 1
    for post in posts[:5]:
        if not isinstance(post, dict):
            continue
        post_id = int(post.get("id", 0) or 0)
        if not post_id:
            continue
        comments = vk_api(source["access_token"], "wall.getComments", {"owner_id": source["owner_id"], "post_id": post_id, "count": 100, "sort": "desc"})
        items = comments.get("items", []) if isinstance(comments, dict) else []
        for comment in items if isinstance(items, list) else []:
            if not isinstance(comment, dict):
                continue
            comment_id = int(comment.get("id", 0) or 0)
            target_text = " ".join(str(comment.get("text", "") or "").split())[:10_000]
            if not comment_id or not target_text:
                continue
            claimed = con.execute(
                "INSERT OR IGNORE INTO vk_source_moderated_comments(source_id,post_id,comment_id,decision,last_error,moderated_at) VALUES (?,?,?,'pending',NULL,?)",
                (source["id"], post_id, comment_id, current),
            ).rowcount
            if not claimed:
                continue
            matched_word = next((word for word in words if word in target_text.casefold()), None)
            if matched_word:
                decision = rule["action_mode"] if rule["action_mode"] in {"delete", "review"} else "delete"
                reason = f"Совпадение с правилом: {matched_word}"
                confidence = 1.0
            elif rule["ai_enabled"] and semantic_rules and semantic_budget > 0:
                semantic_budget -= 1
                decision, reason, confidence = moderator.ai_agent_semantic_moderation(target_text, semantic_rules, model_profile)
            else:
                decision, reason, confidence = "allow", "Нарушение не обнаружено", 0.0
            source_ref = f"vk:{source['id']}:{post_id}"
            if decision == "delete":
                try:
                    vk_api(source["access_token"], "wall.deleteComment", {"owner_id": source["owner_id"], "comment_id": comment_id})
                except ValueError as error:
                    con.execute(
                        "UPDATE vk_source_moderated_comments SET decision = 'failed', last_error = ? WHERE source_id = ? AND post_id = ? AND comment_id = ?",
                        (str(error)[:300], source["id"], post_id, comment_id),
                    )
                    continue
            con.execute(
                "UPDATE vk_source_moderated_comments SET decision = ?, last_error = NULL WHERE source_id = ? AND post_id = ? AND comment_id = ?",
                (decision, source["id"], post_id, comment_id),
            )
            if decision != "allow":
                moderator.record_ai_moderation_event(
                    con, rule, source["channel_id"], "comment", str(comment_id), target_text, decision, reason, confidence,
                    source=source_ref,
                )


def publish_vk_channel_posts(con: sqlite3.Connection) -> None:
    current = now()
    sources = con.execute(
        "SELECT * FROM vk_channel_sources WHERE publish_enabled = 1 ORDER BY created_at LIMIT 20"
    ).fetchall()
    for source in sources:
        posts = con.execute(
            """SELECT m.id, m.text FROM messages m
               WHERE m.chat_id = ? AND m.created_at >= ? AND COALESCE(m.media_type, '') != 'system'
                 AND m.deleted_by_admin = 0 AND COALESCE(m.source_type, '') != 'vk'
                 AND NOT EXISTS(
                     SELECT 1 FROM vk_source_published_messages p
                     WHERE p.source_id = ? AND p.message_id = m.id
                 )
               ORDER BY m.created_at, m.rowid LIMIT 10""",
            (source["channel_id"], source["created_at"], source["id"]),
        ).fetchall()
        for message in posts:
            claimed = con.execute(
                "INSERT OR IGNORE INTO vk_source_published_messages(source_id,message_id,vk_post_id,status,last_error,published_at) VALUES (?,?,NULL,'pending',NULL,?)",
                (source["id"], message["id"], current),
            ).rowcount
            if not claimed:
                continue
            text = " ".join(str(message["text"] or "").split())[:10_000]
            if not text:
                con.execute("UPDATE vk_source_published_messages SET status = 'published' WHERE source_id = ? AND message_id = ?", (source["id"], message["id"]))
                continue
            try:
                result = vk_api(source["access_token"], "wall.post", {"owner_id": source["owner_id"], "message": text})
                vk_post_id = int(result.get("post_id", 0) or 0) if isinstance(result, dict) else int(result or 0)
                if not vk_post_id:
                    raise ValueError("VK не вернул ID опубликованного поста.")
                con.execute(
                    "UPDATE vk_source_published_messages SET vk_post_id = ?, status = 'published' WHERE source_id = ? AND message_id = ?",
                    (vk_post_id, source["id"], message["id"]),
                )
                con.execute("UPDATE vk_channel_sources SET last_error = NULL WHERE id = ?", (source["id"],))
            except (ValueError, TypeError) as error:
                con.execute(
                    "UPDATE vk_source_published_messages SET status = 'failed', last_error = ? WHERE source_id = ? AND message_id = ?",
                    (str(error)[:300], source["id"], message["id"]),
                )
                con.execute("UPDATE vk_channel_sources SET last_error = ? WHERE id = ?", (str(error)[:300], source["id"]))
                break


def publish_vk_channel_targets(con: sqlite3.Connection) -> None:
    current = now()
    targets = con.execute("SELECT * FROM vk_channel_targets WHERE publish_enabled = 1 ORDER BY created_at LIMIT 20").fetchall()
    for target in targets:
        posts = con.execute(
            """SELECT m.id, m.text, m.source_type, m.source_id FROM messages m
               WHERE m.chat_id = ? AND m.created_at >= ? AND COALESCE(m.media_type, '') != 'system'
                 AND m.deleted_by_admin = 0 AND NOT EXISTS(
                   SELECT 1 FROM vk_target_published_messages p WHERE p.target_id = ? AND p.message_id = m.id
                 ) ORDER BY m.created_at, m.rowid LIMIT 10""",
            (target["channel_id"], target["created_at"], target["id"]),
        ).fetchall()
        for message in posts:
            claimed = con.execute(
                "INSERT OR IGNORE INTO vk_target_published_messages(target_id,message_id,vk_post_id,status,last_error,published_at) VALUES (?,?,NULL,'pending',NULL,?)",
                (target["id"], message["id"], current),
            ).rowcount
            if not claimed:
                continue
            text = vk_target_message_text(message)
            if not text:
                con.execute(
                    "UPDATE vk_target_published_messages SET status = 'skipped', last_error = 'Пустая публикация без ссылки на оригинал.' WHERE target_id = ? AND message_id = ?",
                    (target["id"], message["id"]),
                )
                continue
            try:
                result = vk_api(target["access_token"], "wall.post", {"owner_id": target["owner_id"], "message": text})
                vk_post_id = int(result.get("post_id", 0) or 0) if isinstance(result, dict) else int(result or 0)
                if not vk_post_id:
                    raise ValueError("VK не вернул ID опубликованного поста.")
                con.execute(
                    "UPDATE vk_target_published_messages SET vk_post_id = ?, status = 'published', last_error = NULL WHERE target_id = ? AND message_id = ?",
                    (vk_post_id, target["id"], message["id"]),
                )
                con.execute("UPDATE vk_channel_targets SET last_publish_at = ?, last_error = NULL WHERE id = ?", (current, target["id"]))
            except (ValueError, TypeError) as error:
                message_error = str(error)[:300]
                con.execute(
                    "UPDATE vk_target_published_messages SET status = 'failed', last_error = ? WHERE target_id = ? AND message_id = ?",
                    (message_error, target["id"], message["id"]),
                )
                con.execute("UPDATE vk_channel_targets SET last_error = ? WHERE id = ?", (message_error, target["id"]))
                break


def moderate_vk_target_comments(con: sqlite3.Connection, target, current: int, moderator) -> None:
    rule = con.execute(
        "SELECT * FROM ai_agent_comment_moderation_rules WHERE user_id = ? AND channel_id = ?",
        (target["created_by"], target["channel_id"]),
    ).fetchone()
    if not rule or rule["target_scope"] not in {"comments", "all"}:
        return
    wall = vk_api(target["access_token"], "wall.get", {"owner_id": target["owner_id"], "count": 30, "filter": "owner"})
    posts = wall.get("items", []) if isinstance(wall, dict) else []
    words = [str(word).casefold() for word in loads(rule["blocked_words_json"], []) if str(word).strip()]
    semantic_rules = [str(item) for item in loads(rule["semantic_rules_json"], []) if str(item).strip()]
    model_profile = moderator.ai_agent_settings(con, target["created_by"])["modelProfile"]
    semantic_budget = 1
    for post in posts[:5] if isinstance(posts, list) else []:
        if not isinstance(post, dict):
            continue
        post_id = int(post.get("id", 0) or 0)
        if not post_id:
            continue
        comments = vk_api(target["access_token"], "wall.getComments", {"owner_id": target["owner_id"], "post_id": post_id, "count": 100, "sort": "desc"})
        for comment in comments.get("items", []) if isinstance(comments, dict) else []:
            if not isinstance(comment, dict):
                continue
            comment_id = int(comment.get("id", 0) or 0)
            target_text = " ".join(str(comment.get("text", "") or "").split())[:10_000]
            if not comment_id or not target_text:
                continue
            claimed = con.execute(
                "INSERT OR IGNORE INTO vk_target_moderated_comments(target_id,post_id,comment_id,decision,last_error,moderated_at) VALUES (?,?,?,'pending',NULL,?)",
                (target["id"], post_id, comment_id, current),
            ).rowcount
            if not claimed:
                continue
            matched_word = next((word for word in words if word in target_text.casefold()), None)
            if matched_word:
                decision = rule["action_mode"] if rule["action_mode"] in {"delete", "review"} else "review"
                reason, confidence = f"Совпадение с правилом: {matched_word}", 1.0
            elif rule["ai_enabled"] and semantic_rules and semantic_budget > 0:
                semantic_budget -= 1
                decision, reason, confidence = moderator.ai_agent_semantic_moderation(target_text, semantic_rules, model_profile)
            else:
                decision, reason, confidence = "allow", "Нарушение не обнаружено", 0.0
            if decision == "delete":
                try:
                    vk_api(target["access_token"], "wall.deleteComment", {"owner_id": target["owner_id"], "comment_id": comment_id})
                except ValueError as error:
                    con.execute(
                        "UPDATE vk_target_moderated_comments SET decision = 'failed', last_error = ? WHERE target_id = ? AND post_id = ? AND comment_id = ?",
                        (str(error)[:300], target["id"], post_id, comment_id),
                    )
                    continue
            con.execute(
                "UPDATE vk_target_moderated_comments SET decision = ?, last_error = NULL WHERE target_id = ? AND post_id = ? AND comment_id = ?",
                (decision, target["id"], post_id, comment_id),
            )
            if decision != "allow":
                moderator.record_ai_moderation_event(
                    con, rule, target["channel_id"], "comment", str(comment_id), target_text, decision, reason, confidence,
                    source=f"vk-target:{target['id']}:{post_id}",
                )


def moderate_vk_channel_targets(con: sqlite3.Connection, moderator) -> None:
    current = now()
    targets = con.execute("SELECT * FROM vk_channel_targets WHERE moderation_enabled = 1 ORDER BY COALESCE(last_moderation_sync_at, 0) LIMIT 20").fetchall()
    for target in targets:
        try:
            moderate_vk_target_comments(con, target, current, moderator)
            con.execute("UPDATE vk_channel_targets SET last_moderation_sync_at = ?, last_error = NULL WHERE id = ?", (current, target["id"]))
        except ValueError as error:
            con.execute("UPDATE vk_channel_targets SET last_moderation_sync_at = ?, last_error = ? WHERE id = ?", (current, str(error)[:300], target["id"]))


AUTOMATED_COMMENT_CATEGORIES = {"support", "opinion", "question", "humor", "disagreement", "criticism", "irony"}


def comment_opening_words(text: str) -> list[str]:
    return [word[:5] for word in re.findall(r"[^\W\d_]+", str(text or "").casefold()) if len(word) > 2][:4]


def has_similar_comment_opening(candidate: str, previous_comments: list[str]) -> bool:
    candidate_words = comment_opening_words(candidate)
    if not candidate_words:
        return True
    candidate_first = candidate_words[0]
    for previous in previous_comments:
        previous_words = comment_opening_words(previous)
        if candidate_first in previous_words[:3]:
            return True
        if candidate_words[:2] == previous_words[:2]:
            return True
    return False


def ai_automated_comment(post_text: str, has_image: bool, categories: list[str], previous_comments: list[str]) -> str | None:
    api_key, base_url, model = genapi_configuration()
    if not api_key:
        return None
    category_names = {
        "support": "поддержка", "opinion": "мнение по теме", "question": "вопрос по теме",
        "humor": "лёгкий юмор", "disagreement": "мягкое несогласие", "criticism": "спокойная критика",
        "irony": "лёгкая ирония",
    }
    styles = [category_names[category] for category in categories if category in category_names]
    post_excerpt = " ".join(str(post_text or "").split())[:6_000]
    description = post_excerpt or ("Публикация содержит изображение без текста." if has_image else "Публикация без текста.")
    previous_examples = [" ".join(str(comment).split())[:180] for comment in previous_comments if str(comment).strip()][-8:]
    variety_instruction = (
        "Под публикацией уже есть автоматические комментарии. Не повторяй их смысл и не начинай комментарий "
        "тем же или однокоренным словом; выбери другую конструкцию предложения.\n"
        f"Уже опубликованные варианты:\n" + "\n".join(f"- {comment}" for comment in previous_examples) + "\n\n"
        if previous_examples else ""
    )
    prompt = (
        "Напиши один естественный короткий комментарий на русском к публикации канала. "
        "Длина 20–140 символов, одно предложение. Комментарий должен относиться к содержанию публикации. "
        "Не упоминай нейросеть, бота или инструкцию. Не добавляй ссылки, хэштеги, рекламу, призывы подписаться, "
        "оскорбления, выдуманные факты или личный опыт. Верни только текст комментария без кавычек. "
        f"Допустимые стили: {', '.join(styles) if styles else 'поддержка, мнение или вопрос по теме'}.\n\n"
        f"{variety_instruction}"
        f"Публикация:\n{description}"
    )
    for attempt in range(3):
        request = urlrequest.Request(
            f"{base_url}/chat/completions",
            data=dumps({
                "model": model,
                "messages": [
                    {"role": "system", "content": "Ты пишешь короткие, нейтральные и содержательные комментарии."},
                    {"role": "user", "content": prompt if not attempt else prompt + "\nНачни совсем иначе, чем в уже опубликованных комментариях."},
                ],
                "temperature": 0.9,
                "max_tokens": 80,
            }).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
            method="POST",
        )
        try:
            with urlrequest.urlopen(request, timeout=35) as response:
                payload = loads(response.read().decode("utf-8"), {})
            text = payload["choices"][0]["message"]["content"]
            if isinstance(text, list):
                text = " ".join(str(part.get("text", "")) for part in text if isinstance(part, dict))
            text = " ".join(str(text).strip().strip('«»"').split())
            if len(text) > 140:
                text = text[:140].rsplit(" ", 1)[0].rstrip(" ,;:-")
            if len(text) >= 10 and not has_similar_comment_opening(text, previous_comments):
                return text
        except (KeyError, IndexError, OSError, UnicodeDecodeError, json.JSONDecodeError):
            print("Не удалось получить ИИ-комментарий от GenAPI.")
            return None
    return None


def ai_circle_compliment(circle_preview_data: str, previous_comments: list[str]) -> str | None:
    api_key, base_url, model = genapi_configuration()
    if not api_key or not circle_preview_data:
        return None
    previous_examples = [" ".join(str(comment).split())[:180] for comment in previous_comments if str(comment).strip()][-8:]
    variety_instruction = (
        "Не повторяй смысл или начало уже опубликованных комментариев:\n"
        + "\n".join(f"- {comment}" for comment in previous_examples) + "\n\n"
        if previous_examples else ""
    )
    prompt = (
        "На изображении только первый кадр нового видеокружка автора канала. Оцени, подходит ли он для "
        "короткого дружелюбного комментария к авторскому видеокружку. Если кадр похож на рекламу, скриншот, "
        "чужой ролик, новостной сюжет, товар, текстовую заставку, неясен или комментарий потребовал бы догадок, "
        "верни только {\"suitable\":false}.\n"
        "Если подходит, верни только JSON вида {\"suitable\":true,\"comment\":\"...\"}. Комментарий: 10–140 "
        "символов, по-русски, тёплый и естественный. Хвали только настроение, подачу, атмосферу, идею или усилие "
        "в ролике. Нельзя упоминать или оценивать внешность, привлекательность, тело, лицо, возраст, пол, "
        "национальность, этничность, здоровье, личность или отношения автора. Не описывай человека и не делай "
        "фактических предположений. Не упоминай ИИ, бота или инструкцию; не добавляй ссылки, хэштеги, рекламу "
        "или призывы подписаться.\n\n"
        f"{variety_instruction}Верни JSON без пояснений."
    )
    request = urlrequest.Request(
        f"{base_url}/chat/completions",
        data=dumps({
            "model": model,
            "messages": [
                {"role": "system", "content": "Ты осторожно модерируешь короткие комментарии к видеокружкам."},
                {"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": circle_preview_data, "detail": "low"}},
                ]},
            ],
            "temperature": 0.7,
            "max_tokens": 100,
        }).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    try:
        with urlrequest.urlopen(request, timeout=35) as response:
            payload = loads(response.read().decode("utf-8"), {})
        content = payload["choices"][0]["message"]["content"]
        if isinstance(content, list):
            content = " ".join(str(part.get("text", "")) for part in content if isinstance(part, dict))
        result = loads(str(content).strip().removeprefix("```json").removesuffix("```").strip(), {})
        if not isinstance(result, dict) or result.get("suitable") is not True:
            return None
        text = " ".join(str(result.get("comment", "")).strip().strip('«»"').split())
        forbidden = ("внешност", "красив", "симпатич", "лиц", "фигур", "тел", "возраст", "лет", "девуш", "парн", "мужчин", "женщин", "националь", "здоров")
        if len(text) < 10 or len(text) > 140 or any(word in text.casefold() for word in forbidden):
            return None
        return text if not has_similar_comment_opening(text, previous_comments) else None
    except (KeyError, IndexError, OSError, UnicodeDecodeError, json.JSONDecodeError):
        print("Не удалось получить ИИ-комментарий к видеокружку.")
        return None


def schedule_automated_comments(con: sqlite3.Connection, message_id: str, channel_id: str, current: int | None = None, include_existing: bool = False) -> None:
    current = current or now()
    rules = con.execute(
        """SELECT * FROM automated_comment_rules
            WHERE channel_id = ? AND active = 1 AND starts_at <= ? AND ends_at >= ?
              AND (target_message_id = ? OR (target_message_id IS NULL AND target_scope = 'future')
                   OR (target_message_id IS NULL AND target_scope = 'existing' AND ?))""",
        (channel_id, current, current, message_id, 1 if include_existing else 0),
    ).fetchall()
    for rule in rules:
        commenter_ids = loads(rule["commenter_ids_json"], [])
        mode = "circle_compliment" if rule["comment_mode"] == "circle_compliment" else "ai"
        categories = loads(rule["categories_json"], [])
        if not isinstance(categories, list):
            categories = []
        if not categories:
            categories = ["support", "opinion", "question"]
        if not isinstance(commenter_ids, list):
            continue
        if mode == "circle_compliment":
            post = con.execute(
                "SELECT media_type, circle_preview_data FROM messages WHERE id = ? AND chat_id = ?",
                (message_id, channel_id),
            ).fetchone()
            if not post or post["media_type"] != "circle" or not post["circle_preview_data"]:
                continue
        minimum = max(0, int(rule["min_delay_seconds"]))
        maximum = max(minimum, int(rule["max_delay_seconds"]))
        distribution = max(0, int(rule["distribution_seconds"]))
        latest_publish_at = min(int(rule["ends_at"]), current + distribution)
        commenter_count = len(commenter_ids)
        for position, commenter_id in enumerate(commenter_ids):
            commenter = con.execute("SELECT id FROM automated_commenters WHERE id = ?", (str(commenter_id),)).fetchone()
            if not commenter:
                continue
            if latest_publish_at < current + maximum:
                continue
            denominator = max(1, commenter_count - 1)
            lower = current + minimum + (latest_publish_at - current - minimum) * position // denominator
            upper = current + maximum + (latest_publish_at - current - maximum) * position // denominator
            publish_at = lower + secrets.randbelow(upper - lower + 1)
            con.execute(
                """INSERT OR IGNORE INTO automated_comment_jobs(id,rule_id,message_id,commenter_id,text,publish_at,created_at)
                   VALUES (?,?,?,?,?,?,?)""",
                (uid("autocomment"), rule["id"], message_id, commenter["id"], "", publish_at, current),
            )


def publish_automated_comments(con: sqlite3.Connection) -> None:
    current = now()
    con.execute("DELETE FROM automated_comment_jobs WHERE rule_id IN (SELECT id FROM automated_comment_rules WHERE active = 0 OR ends_at < ?)", (current,))
    jobs = con.execute(
        """SELECT job.*, commenter.user_id, chat.settings_json, rule.comment_mode, rule.categories_json,
                  message.text AS message_text, message.media_type AS message_media_type,
                  message.circle_preview_data AS circle_preview_data
           FROM automated_comment_jobs job
           JOIN automated_comment_rules rule ON rule.id = job.rule_id
           JOIN automated_commenters commenter ON commenter.id = job.commenter_id
           JOIN messages message ON message.id = job.message_id
           JOIN chats chat ON chat.id = message.chat_id
           WHERE job.publish_at <= ? AND rule.active = 1 AND rule.starts_at <= ? AND rule.ends_at >= ?
             AND message.chat_id = rule.channel_id
           ORDER BY job.publish_at LIMIT 30""",
        (current, current, current),
    ).fetchall()
    for job in jobs:
        claimed = con.execute(
            """DELETE FROM automated_comment_jobs
               WHERE id = ? AND EXISTS (
                 SELECT 1 FROM automated_comment_rules
                 WHERE id = ? AND active = 1 AND starts_at <= ? AND ends_at >= ?
               )""",
            (job["id"], job["rule_id"], current, current),
        ).rowcount
        if not claimed:
            continue
        if not loads(job["settings_json"], {}).get("commentsEnabled", True):
            continue
        text = job["text"]
        if job["comment_mode"] != "circle_compliment":
            categories = loads(job["categories_json"], [])
            previous_comments = [row["text"] for row in con.execute(
                "SELECT text FROM channel_comments WHERE message_id = ? AND automated = 1 ORDER BY created_at DESC LIMIT 8",
                (job["message_id"],),
            ).fetchall()]
            con.commit()
            text = ai_automated_comment(
                job["message_text"],
                job["message_media_type"] == "photo",
                categories if isinstance(categories, list) else [],
                previous_comments,
            )
            if not text:
                con.execute(
                    "INSERT INTO automated_comment_jobs(id,rule_id,message_id,commenter_id,text,publish_at,created_at) VALUES (?,?,?,?,?,?,?)",
                    (job["id"], job["rule_id"], job["message_id"], job["commenter_id"], "", current + 60, job["created_at"]),
                )
                continue
        elif job["comment_mode"] == "circle_compliment":
            previous_comments = [row["text"] for row in con.execute(
                "SELECT text FROM channel_comments WHERE message_id = ? AND automated = 1 ORDER BY created_at DESC LIMIT 8",
                (job["message_id"],),
            ).fetchall()]
            con.commit()
            text = ai_circle_compliment(job["circle_preview_data"], previous_comments)
            if not text:
                continue
        if con.execute("SELECT 1 FROM channel_comments WHERE message_id = ? AND text = ?", (job["message_id"], text)).fetchone():
            continue
        con.execute(
            "INSERT INTO channel_comments(id,message_id,user_id,text,media_data,automated,created_at) VALUES (?,?,?,?,?,?,?)",
            (uid("comment"), job["message_id"], job["user_id"], text, None, 1, current),
        )


def publish_activity_comments(con: sqlite3.Connection) -> None:
    current = now()
    jobs = con.execute(
        """SELECT job.*, commenter.user_id, message.text AS message_text, message.media_type AS message_media_type
           FROM activity_comment_jobs job
           JOIN automated_commenters commenter ON commenter.id = job.commenter_id
           JOIN messages message ON message.id = job.message_id
           WHERE job.publish_at <= ?
           ORDER BY job.publish_at LIMIT 30""",
        (current,),
    ).fetchall()
    for job in jobs:
        if not con.execute("DELETE FROM activity_comment_jobs WHERE id = ?", (job["id"],)).rowcount:
            continue
        previous_comments = [row["text"] for row in con.execute(
            "SELECT text FROM channel_comments WHERE message_id = ? AND automated = 1 ORDER BY created_at DESC LIMIT 8",
            (job["message_id"],),
        ).fetchall()]
        con.commit()
        categories = loads(job["categories_json"], [])
        text = ai_automated_comment(
            job["message_text"],
            job["message_media_type"] == "photo",
            categories if isinstance(categories, list) else [],
            previous_comments,
        )
        if not text:
            con.execute(
                """INSERT INTO activity_comment_jobs(id,source_key,message_id,commenter_id,categories_json,publish_at,created_at)
                   VALUES (?,?,?,?,?,?,?)""",
                (job["id"], job["source_key"], job["message_id"], job["commenter_id"],
                 job["categories_json"], current + 60, job["created_at"]),
            )
            continue
        if con.execute("SELECT 1 FROM channel_comments WHERE message_id = ? AND text = ?", (job["message_id"], text)).fetchone():
            continue
        con.execute(
            "INSERT INTO channel_comments(id,message_id,user_id,text,media_data,automated,created_at) VALUES (?,?,?,?,?,?,?)",
            (uid("comment"), job["message_id"], job["user_id"], text, None, 1, current),
        )


def poll_telegram_channels(con: sqlite3.Connection) -> None:
    current = now()
    due_links = con.execute(
        "SELECT * FROM telegram_channel_links WHERE next_poll_at <= ? ORDER BY next_poll_at LIMIT 10", (current,)
    ).fetchall()
    for link in due_links:
        claimed = con.execute(
            "UPDATE telegram_channel_links SET next_poll_at = ? WHERE channel_id = ? AND next_poll_at <= ?",
            (current + TELEGRAM_POLL_INTERVAL, link["channel_id"], current),
        ).rowcount
        if not claimed:
            continue
        # Do not keep a SQLite write lock while Telegram responds.
        con.commit()
        try:
            updates = telegram_api(link["bot_token"], "getUpdates", {
                "offset": int(link["last_update_id"]) + 1,
                "limit": 100,
                "timeout": 0,
                "allowed_updates": ["channel_post"],
            })
            max_update_id = int(link["last_update_id"])
            for update in updates if isinstance(updates, list) else []:
                if not isinstance(update, dict):
                    continue
                max_update_id = max(max_update_id, int(update.get("update_id", 0) or 0))
                post = update.get("channel_post")
                if not isinstance(post, dict) or not isinstance(post.get("chat"), dict):
                    continue
                source_chat = post["chat"]
                source_id = str(source_chat.get("id", ""))
                source_username = f"@{str(source_chat.get('username', '')).lower()}" if source_chat.get("username") else ""
                if source_id != str(link["source_chat_id"] or "") and source_username != str(link["source_chat_ref"]).lower():
                    continue
                telegram_message_id = int(post.get("message_id", 0) or 0)
                if not telegram_message_id:
                    continue
                text = str(post.get("text") or post.get("caption") or "").strip()[:10000]
                media_data = telegram_photo_data(link["bot_token"], post.get("photo", [])) if post.get("photo") else None
                if not text and not media_data:
                    continue
                if channel_post_limit_reached(con, link["channel_id"], current):
                    break
                imported = con.execute(
                    "INSERT OR IGNORE INTO telegram_imported_posts(channel_id,telegram_message_id,imported_at) VALUES (?,?,?)",
                    (link["channel_id"], telegram_message_id, current),
                ).rowcount
                if not imported:
                    continue
                sender = con.execute("SELECT id FROM users WHERE id = ?", (link["created_by"],)).fetchone()
                if not sender:
                    sender = con.execute("SELECT owner_id AS id FROM chats WHERE id = ?", (link["channel_id"],)).fetchone()
                if not sender or not sender["id"]:
                    continue
                source_title = str(source_chat.get("title", "Telegram"))[:120]
                message_id = uid("msg")
                con.execute(
                    """INSERT INTO messages(id,chat_id,sender_id,text,media_type,media_data,views,forwarded_from,source_type,source_id,created_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (message_id, link["channel_id"], sender["id"], text, "photo" if media_data else None,
                     media_data, 1, f"Telegram · {source_title}", "telegram", str(telegram_message_id), current),
                )
                schedule_automated_comments(con, message_id, link["channel_id"], current)
                con.execute("UPDATE chats SET updated_at = ? WHERE id = ?", (current, link["channel_id"]))
            con.execute(
                "UPDATE telegram_channel_links SET last_update_id = ?, last_sync_at = ?, last_error = NULL WHERE channel_id = ?",
                (max_update_id, current, link["channel_id"]),
            )
        except (ValueError, urlerror.URLError, TimeoutError) as error:
            con.execute(
                "UPDATE telegram_channel_links SET last_sync_at = ?, last_error = ? WHERE channel_id = ?",
                (current, str(error)[:300], link["channel_id"]),
            )


class Handler(BaseHTTPRequestHandler):
    server_version = "Chat-Pro/2.0"

    def do_GET(self):
        self.route("GET")

    def do_HEAD(self):
        self.route("HEAD")

    def do_POST(self):
        self.route("POST")

    def route(self, method: str):
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            if path.startswith("/api/"):
                with connect() as con:
                    cleanup_expired_deleted_accounts(con)
                    return self.handle_api(con, method, path, parse_qs(parsed.query))
            if method in {"GET", "HEAD"} and path.startswith("/media/messages/"):
                with connect() as con:
                    cleanup_expired_deleted_accounts(con)
                    media_user = get_user_by_token(con, self.headers)
                    media_token = parse_qs(parsed.query).get("token", [""])[0]
                    if not media_user and media_token:
                        media_user = con.execute(
                            "SELECT users.* FROM users JOIN sessions ON sessions.user_id = users.id WHERE sessions.token = ? AND users.deletion_due_at IS NULL",
                            (media_token,),
                        ).fetchone()
                    self.require_user(media_user)
                    message_id = path.removeprefix("/media/messages/").removesuffix(".m4a").removesuffix(".mp4")
                    return self.send_message_media(con, media_user, message_id)
            if path in {"/admin", "/admin/"}:
                return self.send_file(ROOT / "admin.html")
            if path == "/auth/vk/callback" and method == "GET":
                with connect() as con:
                    cleanup_expired_deleted_accounts(con)
                    return self.complete_vk_oauth(con, parse_qs(parsed.query))
            if path == "/requisites":
                return self.send_file(ROOT / "requisites.html")
            if path == "/" or path == "/payment-return" or path.startswith("/invite/") or path.startswith("/channel/"):
                return self.send_file(ROOT / "index.html")
            return self.send_file(ROOT / path.lstrip("/"))
        except ConnectionError:
            return
        except ValueError as error:
            return self.json({"ok": False, "error": str(error)}, HTTPStatus.BAD_REQUEST)
        except PermissionError as error:
            return self.json({"ok": False, "error": str(error) or "Нет доступа."}, HTTPStatus.FORBIDDEN)
        except Exception as error:  # Keep local demo debuggable.
            return self.json({"ok": False, "error": f"Ошибка сервера: {error}"}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def handle_api(self, con: sqlite3.Connection, method: str, path: str, query):
        body = self.read_json() if method == "POST" else {}
        user = get_user_by_token(con, self.headers)

        if path == "/api/yookassa/webhook" and method == "POST":
            return self.handle_yookassa_webhook(con, body)
        if path == "/api/register" and method == "POST":
            return self.register(con, body)
        if path == "/api/register/verify" and method == "POST":
            return self.verify_registration(con, body)
        if path == "/api/auth-challenges/resend" and method == "POST":
            return self.resend_auth_challenge(con, body)
        if path == "/api/login" and method == "POST":
            return self.login(con, body)
        if path == "/api/auth/vk/start" and method == "POST":
            return self.start_vk_oauth(con, user, body)
        if path == "/api/password-reset/request" and method == "POST":
            return self.request_password_reset(con, body)
        if path == "/api/password-reset/confirm" and method == "POST":
            return self.confirm_password_reset(con, body)
        if path == "/api/public/legal" and method == "GET":
            legal_row = con.execute("SELECT value FROM settings WHERE key = 'public_legal'").fetchone()
            branding_row = con.execute("SELECT value FROM settings WHERE key = 'public_branding'").fetchone()
            return self.json({
                "ok": True,
                "legal": normalize_public_legal(loads(legal_row["value"], {})) if legal_row else DEFAULT_PUBLIC_LEGAL,
                "branding": normalize_public_branding(loads(branding_row["value"], {})) if branding_row else DEFAULT_PUBLIC_BRANDING,
            })
        if path == "/api/bootstrap" and method == "GET":
            self.require_user(user)
            return self.bootstrap(con, user)
        if path == "/api/channel-feed" and method == "GET":
            self.require_user(user)
            return self.channel_feed(con, user, query)
        if path == "/api/ai-agent/settings" and method == "POST":
            self.require_user(user)
            return self.update_ai_agent_settings(con, user, body)
        if path == "/api/ai-agent/tasks" and method == "GET":
            self.require_user(user)
            return self.json({"ok": True, "tasks": self.ai_agent_tasks(con, user["id"])})
        if path == "/api/ai-agent/tasks" and method == "POST":
            self.require_user(user)
            return self.save_ai_agent_task(con, user, body)
        if path == "/api/ai-agent/tasks/toggle" and method == "POST":
            self.require_user(user)
            return self.toggle_ai_agent_task(con, user, body)
        if path == "/api/ai-agent/tasks/delete" and method == "POST":
            self.require_user(user)
            return self.delete_ai_agent_task(con, user, body)
        if path == "/api/ai-agent/model-profile" and method == "POST":
            self.require_user(user)
            return self.update_ai_agent_model_profile(con, user, body)
        if path == "/api/ai-agent/global-instructions" and method == "POST":
            self.require_user(user)
            return self.update_ai_agent_global_instruction(con, user, body)
        if path == "/api/ai-agent/global-instructions/delete" and method == "POST":
            self.require_user(user)
            return self.delete_ai_agent_global_instruction(con, user, body)
        if path == "/api/ai-agent/ask" and method == "POST":
            self.require_user(user)
            return self.ask_ai_agent(con, user, body)
        if path == "/api/ai-agent/bookings" and method == "POST":
            self.require_user(user)
            return self.create_ai_agent_booking(con, user, body)
        if path == "/api/ai-agent/bookings/status" and method == "POST":
            self.require_user(user)
            return self.update_ai_agent_booking_status(con, user, body)
        if path == "/api/ai-agent/control" and method == "POST":
            self.require_user(user)
            return self.control_ai_agent(con, user, body)
        if path == "/api/ai-agent/draft" and method == "POST":
            self.require_user(user)
            return self.draft_ai_agent_reply(con, user, body)
        if path == "/api/ai-agent/private-search" and method == "GET":
            self.require_user(user)
            return self.ai_agent_private_search(con, user, query)
        if path == "/api/ai-agent/channel-rule" and method == "POST":
            self.require_user(user)
            return self.update_ai_agent_channel_rule(con, user, body)
        if path == "/api/ai-agent/confirm" and method == "POST":
            self.require_user(user)
            return self.confirm_ai_agent_action(con, user, body)
        if path == "/api/ai-agent/moderation/resolve" and method == "POST":
            self.require_user(user)
            return self.resolve_ai_agent_moderation_event(con, user, body)
        if path == "/api/ai-agent/moderation/events" and method == "GET":
            self.require_user(user)
            return self.ai_agent_moderation_events(con, user, query)
        if path == "/api/ai-agent/moderation/rules" and method == "GET":
            self.require_user(user)
            return self.ai_agent_moderation_rules(con, user)
        if path == "/api/ai-agent/moderation/rules" and method == "POST":
            self.require_user(user)
            return self.update_ai_agent_moderation_rule(con, user, body)
        if path == "/api/ai-agent/action-log" and method == "GET":
            self.require_user(user)
            return self.ai_agent_action_logs(con, user, query)
        if path == "/api/media/messages/upload" and method == "POST":
            self.require_user(user)
            return self.prepare_message_media_upload(con, user, body)
        if path == "/api/users" and method == "GET":
            self.require_user(user)
            q = (query.get("q", [""])[0] or "").lower().replace("@", "")
            rows = con.execute(
                "SELECT * FROM users WHERE id != ? AND (username LIKE ? OR lower(name) LIKE ?) ORDER BY username LIMIT 12",
                (user["id"], f"%{q}%", f"%{q}%"),
            ).fetchall()
            return self.json({"ok": True, "users": [public_user(r) for r in rows]})
        if path == "/api/messages/search" and method == "GET":
            self.require_user(user)
            return self.search_messages(con, user, query)
        if path == "/api/username" and method == "POST":
            self.require_user(user)
            username = normalize_username(body.get("username"))
            validate_username(username)
            if username_taken(con, username, user["id"]):
                raise ValueError("Этот username уже занят. Выберите другой.")
            con.execute("UPDATE users SET username = ? WHERE id = ?", (username, user["id"]))
            return self.json({"ok": True})
        if path == "/api/account/delete" and method == "POST":
            self.require_user(user)
            return self.request_account_deletion(con, user, body)
        if path == "/api/preferences" and method == "POST":
            self.require_user(user)
            theme = str(body.get("theme", "light"))
            if theme not in {"light", "dark"}:
                raise ValueError("Неизвестный режим оформления.")
            background = str(body.get("chatBackground", "default"))
            allowed_backgrounds = {"default", "whatsapp", "mint", "aurora", "noir", "cyan", "mist", "sunset", "ocean", "lavender", "forest", "midnight", "ember", "iris", "jade", "violet", "cobalt", "amber", "prism", "live", "custom"}
            if background not in allowed_backgrounds:
                raise ValueError("Неизвестный вариант фона.")
            background_data = str(body.get("chatBackgroundData", "")) or None
            if background == "custom":
                if not background_data.startswith("data:image/") or len(background_data) > 3_500_000:
                    raise ValueError("Загрузите фоновое изображение до 2,5 МБ.")
            else:
                background_data = None
            sidebar_background_data = str(body.get("sidebarBackgroundData", "")) or None
            if sidebar_background_data and (not sidebar_background_data.startswith("data:image/") or len(sidebar_background_data) > 3_500_000):
                raise ValueError("Загрузите изображение левой панели до 2,5 МБ.")
            site_color = str(body.get("siteColor", "#2aabee"))
            if not re.fullmatch(r"#[0-9a-fA-F]{6}", site_color):
                raise ValueError("Выберите корректный цвет сайта.")
            dialog_bubble_style = str(body.get("dialogBubbleStyle", "custom"))
            if dialog_bubble_style != "custom":
                raise ValueError("Неизвестный стиль сообщений.")
            dialog_color = str(body.get("dialogColor", "#dff9f9"))
            other_dialog_color = str(body.get("otherDialogColor", "#ffffff"))
            dialog_panel_color = str(body.get("dialogPanelColor", "#f4f8fc"))
            if not all(re.fullmatch(r"#[0-9a-fA-F]{6}", color) for color in (dialog_color, other_dialog_color, dialog_panel_color)):
                raise ValueError("Выберите корректный цвет сообщений.")
            dialog_panel_style = str(body.get("dialogPanelStyle", "custom"))
            if dialog_panel_style not in {"custom", "pearl", "sky", "mint", "sunset", "lavender", "midnight", "noir", "aurora", "live", "interactive", "interactive-light", "ember"}:
                raise ValueError("Неизвестный стиль панелей диалога.")
            dialog_font = str(body.get("dialogFont", "system"))
            if dialog_font not in {"system", "business", "classic", "script", "rounded", "serif", "mono", "humanist", "condensed", "typewriter", "elegant"}:
                raise ValueError("Неизвестный шрифт сообщений.")
            text_scale = str(body.get("textScale", "system"))
            if text_scale not in {"system", "110", "120", "130"}:
                raise ValueError("Неизвестный размер текста.")
            night_appearance_custom = body.get("nightAppearanceCustom", False)
            if not isinstance(night_appearance_custom, bool):
                raise ValueError("Неверная настройка личной подсветки.")
            night_appearance = normalize_ui_appearance({
                "outlineColor": body.get("nightOutlineColor", DEFAULT_UI_APPEARANCE["outlineColor"]),
                "glowColor": body.get("nightGlowColor", DEFAULT_UI_APPEARANCE["glowColor"]),
                "glowIntensity": body.get("nightGlowIntensity", DEFAULT_UI_APPEARANCE["glowIntensity"]),
            }) if night_appearance_custom else None
            group_invite_privacy = str(body.get("groupInvitePrivacy", "contacts"))
            if group_invite_privacy not in {"everyone", "contacts", "nobody"}:
                raise ValueError("Неизвестная настройка добавления в группы.")
            direct_message_privacy = str(body.get("directMessagePrivacy", "everyone"))
            if direct_message_privacy not in {"everyone", "contacts", "nobody"}:
                raise ValueError("Неизвестная настройка личных сообщений.")
            call_ringtone = str(body.get("callRingtone", "classic"))
            if call_ringtone not in {"classic", "custom"}:
                raise ValueError("Неизвестная мелодия звонка.")
            call_ringtone_data = None
            if call_ringtone == "custom":
                self.require_enhanced_account_level(con, user["id"])
                call_ringtone_data = str(body.get("callRingtoneData", "")).strip()
                if not call_ringtone_data:
                    existing_ringtone = con.execute("SELECT call_ringtone_data FROM users WHERE id = ?", (user["id"],)).fetchone()
                    call_ringtone_data = existing_ringtone["call_ringtone_data"] if existing_ringtone else ""
                allowed_ringtone_types = {"audio/mpeg", "audio/mp4", "audio/ogg", "audio/wav", "audio/webm"}
                match = re.fullmatch(r"data:([^;,]+);base64,([A-Za-z0-9+/=]+)", call_ringtone_data)
                if not match or match.group(1).lower() not in allowed_ringtone_types:
                    raise ValueError("Загрузите мелодию в формате MP3, M4A, OGG, WAV или WebM.")
                try:
                    ringtone_bytes = base64.b64decode(match.group(2), validate=True)
                except (ValueError, binascii.Error):
                    raise ValueError("Не удалось прочитать мелодию звонка.")
                if not ringtone_bytes or len(ringtone_bytes) > 2_000_000:
                    raise ValueError("Мелодия звонка должна быть не больше 2 МБ.")
            site_background = str(body.get("siteBackground", "default"))
            if site_background not in allowed_backgrounds:
                raise ValueError("Неизвестный вариант фона сайта.")
            site_background_data = str(body.get("siteBackgroundData", "")) or None
            if site_background == "custom":
                if not site_background_data.startswith("data:image/") or len(site_background_data) > 3_500_000:
                    raise ValueError("Загрузите фоновое изображение сайта до 2,5 МБ.")
            else:
                site_background_data = None
            con.execute(
                "UPDATE users SET theme = ?, site_color = ?, site_background = ?, site_background_data = ?, dialog_color = ?, other_dialog_color = ?, dialog_panel_color = ?, dialog_panel_style = ?, dialog_bubble_style = ?, dialog_font = ?, text_scale = ?, chat_background = ?, chat_background_data = ?, sidebar_background_data = ?, hidden_status_ids = ?, group_invite_privacy = ?, direct_message_privacy = ?, night_appearance_custom = ?, night_outline_color = ?, night_glow_color = ?, night_glow_intensity = ?, call_ringtone = ?, call_ringtone_data = ? WHERE id = ?",
                (theme, site_color, site_background, site_background_data, dialog_color, other_dialog_color, dialog_panel_color, dialog_panel_style, dialog_bubble_style, dialog_font, text_scale, background, background_data, sidebar_background_data, dumps(body.get("hiddenStatusIds", [])), group_invite_privacy, direct_message_privacy, int(night_appearance_custom), night_appearance["outlineColor"] if night_appearance else None, night_appearance["glowColor"] if night_appearance else None, night_appearance["glowIntensity"] if night_appearance else None, call_ringtone, call_ringtone_data, user["id"]),
            )
            return self.json({"ok": True})
        if path == "/api/profile/avatar" and method == "POST":
            self.require_user(user)
            return self.update_avatar(con, user, body)
        if path == "/api/profile/description" and method == "POST":
            self.require_user(user)
            return self.update_profile_description(con, user, body)
        if path == "/api/profile/channels/visibility" and method == "POST":
            self.require_user(user)
            return self.update_profile_channel_visibility(con, user, body)
        if path == "/api/profile/block" and method == "POST":
            self.require_user(user)
            return self.set_user_block(con, user, body)
        if path == "/api/my-reactions" and method == "GET":
            self.require_user(user)
            return self.my_reactions(con, user)
        if path == "/api/profile/posts" and method == "POST":
            self.require_user(user)
            return self.create_profile_post(con, user, body)
        if path == "/api/profile/posts/edit" and method == "POST":
            self.require_user(user)
            return self.edit_profile_post(con, user, body)
        if path == "/api/profile/posts/delete" and method == "POST":
            self.require_user(user)
            return self.delete_profile_post(con, user, body)
        if path == "/api/profile/posts/react" and method == "POST":
            self.require_user(user)
            return self.react_to_profile_post(con, user, body)
        if path == "/api/profile/stories" and method == "POST":
            self.require_user(user)
            return self.create_story(con, user, body)
        if path == "/api/stories/view" and method == "POST":
            self.require_user(user)
            return self.view_story(con, user, body)
        if path == "/api/stories/react" and method == "POST":
            self.require_user(user)
            return self.react_to_story(con, user, body)
        if path == "/api/stories/permanent" and method == "POST":
            self.require_user(user)
            return self.save_story_permanent(con, user, body)
        if path == "/api/stories/hide-author" and method == "POST":
            self.require_user(user)
            return self.hide_story_author(con, user, body)
        if path == "/api/stories/privacy" and method == "POST":
            self.require_user(user)
            return self.update_story_privacy(con, user, body)
        if path == "/api/stories/reply" and method == "POST":
            self.require_user(user)
            return self.reply_to_story(con, user, body)
        if path == "/api/stories/share" and method == "POST":
            self.require_user(user)
            return self.share_story(con, user, body)
        if path == "/api/chats" and method == "POST":
            self.require_user(user)
            return self.create_chat(con, user, body)
        if path == "/api/secret-chats/unlock" and method == "POST":
            self.require_user(user)
            return self.unlock_secret_chats(con, user, body.get("password"))
        if path == "/api/chats/join" and method == "POST":
            self.require_user(user)
            return self.join_chat(con, user, body.get("chatId"))
        if path == "/api/invites/join" and method == "POST":
            self.require_user(user)
            return self.join_chat_by_invite(con, user, body.get("code"))
        if path == "/api/channels/join-requests" and method == "GET":
            self.require_user(user)
            return self.channel_join_requests(con, user)
        if path == "/api/channels/join-requests/resolve" and method == "POST":
            self.require_user(user)
            return self.resolve_channel_join_request(con, user, body)
        if path == "/api/chats/members" and method == "POST":
            self.require_user(user)
            return self.add_chat_member(con, user, body)
        if path == "/api/chats/update" and method == "POST":
            self.require_user(user)
            return self.update_group_chat(con, user, body)
        if path == "/api/channels/schedule" and method == "POST":
            self.require_user(user)
            return self.schedule_channel_post(con, user, body)
        if path == "/api/channels/link" and method == "POST":
            self.require_user(user)
            return self.update_channel_link(con, user, body)
        if path == "/api/channels/telegram" and method == "POST":
            self.require_user(user)
            return self.update_telegram_channel_link(con, user, body)
        if path == "/api/channels/rss" and method == "POST":
            self.require_user(user)
            return self.update_rss_channel_link(con, user, body)
        if path == "/api/channels/vk" and method == "POST":
            self.require_user(user)
            return self.update_vk_channel_link(con, user, body)
        if path == "/api/channels/vk/targets" and method == "POST":
            self.require_user(user)
            return self.update_vk_channel_target(con, user, body)
        if path == "/api/channels/vk/proposals" and method in {"GET", "POST"}:
            self.require_user(user)
            return self.vk_proposed_posts(con, user, method, query, body)
        if path == "/api/channels/vk/proposals/resolve" and method == "POST":
            self.require_user(user)
            return self.resolve_vk_proposed_post(con, user, body)
        if path == "/api/channels/appearance" and method == "POST":
            self.require_user(user)
            return self.update_channel_appearance(con, user, body)
        if path == "/api/channels/comments" and method == "POST":
            self.require_user(user)
            return self.add_channel_comment(con, user, body)
        if path == "/api/channels/comments/delete" and method == "POST":
            self.require_user(user)
            return self.delete_channel_comment(con, user, body)
        if path == "/api/chats/members/role" and method == "POST":
            self.require_user(user)
            return self.update_chat_member_role(con, user, body)
        if path == "/api/chats/members/remove" and method == "POST":
            self.require_user(user)
            return self.remove_chat_member(con, user, body)
        if path == "/api/chats/leave" and method == "POST":
            self.require_user(user)
            return self.leave_chat(con, user, body.get("chatId"))
        if path == "/api/chats/pin" and method == "POST":
            self.require_user(user)
            return self.toggle_chat_pin(con, user, body.get("chatId"))
        if path == "/api/chats/archive" and method == "POST":
            self.require_user(user)
            return self.toggle_chat_archive(con, user, body.get("chatId"), body.get("archived"))
        if path == "/api/chats/delete" and method == "POST":
            self.require_user(user)
            return self.delete_chat(con, user, body.get("chatId"), body.get("scope"))
        if path == "/api/messages" and method == "POST":
            self.require_user(user)
            return self.add_message(con, user, body)
        if path == "/api/chats/activity" and method == "POST":
            self.require_user(user)
            return self.update_chat_activity(con, user, body)
        if path == "/api/group-content/share" and method == "POST":
            self.require_user(user)
            return self.share_content_to_group(con, user, body)
        if path == "/api/messages/source-delete" and method == "POST":
            self.require_user(user)
            return self.delete_source_repost(con, user, body.get("messageId"))
        if path == "/api/messages/edit" and method == "POST":
            self.require_user(user)
            return self.edit_message(con, user, body)
        if path == "/api/messages/read" and method == "POST":
            self.require_user(user)
            return self.mark_messages_read(con, user, body.get("chatId"))
        if path == "/api/messages/pin" and method == "POST":
            self.require_user(user)
            return self.toggle_message_pin(con, user, body.get("messageId"))
        if path == "/api/messages/pin/hide" and method == "POST":
            self.require_user(user)
            return self.hide_pinned_message(con, user, body.get("messageId"))
        if path == "/api/messages/delete" and method == "POST":
            self.require_user(user)
            return self.delete_message(con, user, body)
        if path == "/api/messages/bulk" and method == "POST":
            self.require_user(user)
            return self.bulk_messages(con, user, body)
        if path == "/api/react" and method == "POST":
            self.require_user(user)
            return self.react(con, user, body)
        if path == "/api/donate" and method == "POST":
            self.require_user(user)
            return self.donate(con, user, body)
        if path == "/api/yookassa/payments" and method == "POST":
            self.require_user(user)
            return self.create_yookassa_payment(con, user, body)
        if path == "/api/yookassa/payments/status" and method == "POST":
            self.require_user(user)
            return self.check_yookassa_payment(con, user, body)
        if path == "/api/account-level/subscriptions" and method == "POST":
            self.require_user(user)
            return self.create_account_level_subscription(con, user, body)
        if path == "/api/account-level/subscriptions/status" and method == "POST":
            self.require_user(user)
            return self.check_account_level_subscription_payment(con, user, body)
        if path == "/api/account-level/subscriptions/cancel" and method == "POST":
            self.require_user(user)
            return self.cancel_account_level_subscription(con, user, body)
        if path == "/api/channel-payouts" and method == "POST":
            self.require_user(user)
            return self.create_channel_payout_request(con, user, body)
        if path == "/api/demo-activity-packages/purchase" and method == "POST":
            self.require_user(user)
            return self.purchase_demo_activity_package(con, user, body)
        if path == "/api/reviews" and method == "POST":
            self.require_user(user)
            return self.add_review(con, user, body)
        if path == "/api/reports" and method == "POST":
            self.require_user(user)
            return self.add_report(con, user, body)
        if path == "/api/channel-share-submissions" and method == "POST":
            self.require_user(user)
            return self.add_channel_share_submission(con, user, body)
        if path == "/api/vk-review-submissions" and method == "POST":
            self.require_user(user)
            return self.add_vk_review_submission(con, user, body)
        if path == "/api/promotions/claim" and method == "POST":
            self.require_user(user)
            return self.claim_promotion(con, user, body.get("promotionId"))
        if path == "/api/activity-rewards/claim" and method == "POST":
            self.require_user(user)
            return self.claim_activity_reward(con, user, body.get("rewardId"), body.get("channelId"))
        if path == "/api/account-level/claim" and method == "POST":
            self.require_user(user)
            return self.claim_account_level_reward(con, user, body.get("levelId"))
        if path == "/api/calls/start" and method == "POST":
            self.require_user(user)
            return self.start_call(con, user, body)
        if path == "/api/calls/poll" and method == "GET":
            self.require_user(user)
            return self.poll_calls(con, user)
        if path == "/api/calls/answer" and method == "POST":
            self.require_user(user)
            return self.answer_call(con, user, body)
        if path == "/api/calls/end" and method == "POST":
            self.require_user(user)
            return self.end_call(con, user, body)

        if path.startswith("/api/admin/"):
            self.require_admin()
            return self.handle_admin(con, method, path, body)

        return self.json({"ok": False, "error": "API не найден."}, HTTPStatus.NOT_FOUND)

    def handle_admin(self, con: sqlite3.Connection, method: str, path: str, body):
        if path == "/api/admin/bootstrap" and method == "GET":
            return self.admin_bootstrap(con)
        if path == "/api/admin/settings" and method == "POST":
            key = str(body.get("key", ""))
            if key == "account_levels":
                value = normalize_account_levels(body.get("value"))
            elif key == "features":
                value = body.get("value")
                if not isinstance(value, dict):
                    raise ValueError("Настройки функций должны быть объектом.")
            elif key == "ui_appearance":
                value = normalize_ui_appearance(body.get("value"))
            elif key == "channel_reactions":
                value = normalize_channel_reactions(body.get("value"))
            elif key == "channel_monetization":
                value = normalize_channel_monetization(body.get("value"))
            elif key == "channel_activity_regulator":
                value = normalize_channel_activity_regulator(body.get("value"))
            elif key == "public_branding":
                value = normalize_public_branding(body.get("value"))
            elif key == "public_legal":
                value = normalize_public_legal(body.get("value"))
            else:
                raise ValueError("Этот раздел настроек нельзя изменять через админку.")
            con.execute("INSERT OR REPLACE INTO settings(key,value) VALUES (?,?)", (key, dumps(value)))
            return self.json({"ok": True})
        if path == "/api/admin/users/stars" and method == "POST":
            amount = int(body.get("amount", 0))
            user_id = str(body.get("userId", ""))
            if amount > 0:
                self.credit_stars(con, user_id, amount)
            elif amount < 0:
                before = con.execute("SELECT stars FROM users WHERE id = ?", (user_id,)).fetchone()
                if not before:
                    raise ValueError("Пользователь не найден.")
                con.execute("UPDATE users SET stars = MAX(0, stars + ?) WHERE id = ?", (amount, user_id))
                after = con.execute("SELECT stars FROM users WHERE id = ?", (user_id,)).fetchone()
                amount = int(after["stars"]) - int(before["stars"])
            if amount:
                self.record_star_transaction(con, user_id, amount, "admin", "Корректировка баланса администрацией")
            return self.json({"ok": True})
        if path == "/api/admin/users/account-level" and method == "POST":
            user_id = str(body.get("userId", "")).strip()
            level_id = str(body.get("levelId", "")).strip()
            if not con.execute("SELECT 1 FROM users WHERE id = ?", (user_id,)).fetchone():
                raise ValueError("Пользователь не найден.")
            levels_row = con.execute("SELECT value FROM settings WHERE key = 'account_levels'").fetchone()
            levels = normalize_account_levels(loads(levels_row["value"], []) if levels_row else [])
            if level_id not in {level["id"] for level in levels}:
                raise ValueError("Выберите существующий уровень аккаунта.")
            con.execute(
                "INSERT INTO admin_account_level_grants(user_id,level_id,granted_at) VALUES (?,?,?) ON CONFLICT(user_id) DO UPDATE SET level_id = excluded.level_id, granted_at = excluded.granted_at",
                (user_id, level_id, now()),
            )
            return self.json({"ok": True})
        if path == "/api/admin/appeals/respond" and method == "POST":
            return self.respond_to_appeal(con, body)
        if path == "/api/admin/channel-share-submissions/update" and method == "POST":
            return self.update_channel_share_submission(con, body)
        if path == "/api/admin/vk-review-submissions/update" and method == "POST":
            return self.update_vk_review_submission(con, body)
        if path == "/api/admin/channel-payouts/update" and method == "POST":
            request_id = str(body.get("requestId", "")).strip()
            status = str(body.get("status", "")).strip()
            note = " ".join(str(body.get("adminNote", "")).split())[:500]
            if status not in {"paid", "rejected"}:
                raise ValueError("Выберите результат обработки заявки.")
            updated = con.execute(
                "UPDATE channel_payout_requests SET status = ?, admin_note = ?, processed_at = ? WHERE id = ? AND status = 'pending'",
                (status, note, now(), request_id),
            ).rowcount
            if not updated:
                raise ValueError("Заявка уже обработана или не найдена.")
            return self.json({"ok": True})
        if path == "/api/admin/recommended" and method == "POST":
            chat_id = str(body.get("chatId", ""))
            channel = con.execute("SELECT id FROM chats WHERE id = ? AND type = 'channel'", (chat_id,)).fetchone()
            if not channel:
                raise ValueError("Для рекомендации можно выбрать только канал.")
            con.execute("INSERT OR REPLACE INTO recommended_groups(chat_id,position,created_at) VALUES (?,?,?)", (chat_id, int(body.get("position", 100)), now()))
            return self.json({"ok": True})
        if path == "/api/admin/recommended/delete" and method == "POST":
            con.execute("DELETE FROM recommended_groups WHERE chat_id = ?", (str(body.get("chatId", "")),))
            return self.json({"ok": True})
        if path == "/api/admin/promotions" and method == "POST":
            con.execute(
                """INSERT INTO promotions(id,title,description,action_type,target_count,reward_type,reward_amount,premium_days,daily_limit,active,created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (uid("promo"), body.get("title", "Акция"), body.get("description", ""), body.get("actionType", "manual"), int(body.get("targetCount", 1)), body.get("rewardType", "stars"), int(body.get("rewardAmount", 0)), int(body.get("premiumDays", 0)), int(body.get("dailyLimit", 1)), 1, now()),
            )
            return self.json({"ok": True})
        if path == "/api/admin/activity-rewards" and method == "POST":
            criteria = self.normalize_activity_criteria(body.get("criteria", {}))
            if not criteria:
                raise ValueError("Укажите хотя бы одно условие активности.")
            title = str(body.get("title", "")).strip()
            if not title:
                raise ValueError("Введите название награды.")
            reward = normalize_level_reward(body.get("reward", {"stars": body.get("rewardStars", 0)}), "reward")
            levels_row = con.execute("SELECT value FROM settings WHERE key = 'account_levels'").fetchone()
            configured_levels = normalize_account_levels(loads(levels_row["value"], []) if levels_row else []) if levels_row else []
            if reward["accountLevelId"] and reward["accountLevelId"] not in {level["id"] for level in configured_levels}:
                raise ValueError("Выберите существующий уровень аккаунта для награды.")
            if not any((reward["stars"], reward["premiumDays"], reward["limits"], reward["recurringStars"], reward["starPackageDiscountPercent"], reward["accountLevelId"], reward["recommendOwnChannel"])):
                raise ValueError("Укажите хотя бы один вид награды.")
            add_activity_reward(con, title[:120], str(body.get("description", "")).strip()[:1000], criteria, reward)
            return self.json({"ok": True})
        if path == "/api/admin/activity-rewards/deactivate" and method == "POST":
            con.execute("UPDATE activity_rewards SET active = 0 WHERE id = ?", (str(body.get("rewardId", "")),))
            return self.json({"ok": True})
        if path == "/api/admin/statuses" and method == "POST":
            con.execute(
                """INSERT INTO statuses(id,icon,title,description,criteria_json,reward_json,active,created_at)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (uid("status"), body.get("icon", "🏅"), body.get("title", "Статус"), body.get("description", ""), dumps(body.get("criteria", {})), dumps(body.get("reward", {})), 1, now()),
            )
            return self.json({"ok": True})
        if path == "/api/admin/demo-activity-packages" and method == "POST":
            title = " ".join(str(body.get("title", "")).split())[:80]
            if not title:
                raise ValueError("Введите название демо-пакета.")
            existing = con.execute("SELECT count(*) AS count FROM demo_activity_packages").fetchone()["count"]
            if existing >= 6:
                raise ValueError("Можно создать не более шести демо-пакетов.")
            values = {
                metric: nonnegative_int(body.get(f"{metric}PerDay", 0), f"{metric}PerDay", 1_000_000)
                for metric in ("subscribers", "views", "reactions", "comments")
            }
            post_limit = nonnegative_int(body.get("postLimit", 1), "postLimit", 10)
            duration_days = nonnegative_int(body.get("durationDays", 7), "durationDays", 3650)
            indefinite = bool(body.get("indefinite"))
            fade_duration_days = nonnegative_int(body.get("fadeDurationDays", 30), "fadeDurationDays", 365)
            price_stars = nonnegative_int(body.get("priceStars", 0), "priceStars", 1_000_000)
            donation_count = nonnegative_int(body.get("donationCount", 0), "donationCount", 100)
            donation_post_interval = nonnegative_int(body.get("donationPostInterval", 4), "donationPostInterval", 1_000)
            donation_min_stars = nonnegative_int(body.get("donationMinStars", 0), "donationMinStars", 1_000_000)
            donation_max_stars = nonnegative_int(body.get("donationMaxStars", 0), "donationMaxStars", 1_000_000)
            inactivity_days = nonnegative_int(body.get("inactivityDays", 3), "inactivityDays", 365)
            if not inactivity_days:
                raise ValueError("Укажите число дней без публикаций до затухания пакета.")
            if donation_count and (not donation_post_interval or not donation_min_stars or donation_max_stars < donation_min_stars):
                raise ValueError("Для автодонатов укажите интервал и корректный диапазон звёзд.")
            apply_to_new_channels = bool(body.get("applyToNewChannels"))
            required_account_level_id = str(body.get("requiredAccountLevelId", "") or "").strip().lower()
            levels_row = con.execute("SELECT value FROM settings WHERE key = 'account_levels'").fetchone()
            configured_levels = normalize_account_levels(loads(levels_row["value"], []) if levels_row else []) if levels_row else []
            if required_account_level_id and required_account_level_id not in {level["id"] for level in configured_levels}:
                raise ValueError("Выберите существующий уровень аккаунта для пакета.")
            commenter_ids = []
            if not any(values.values()):
                raise ValueError("Укажите хотя бы один дневной показатель.")
            if not indefinite and not duration_days:
                raise ValueError("Укажите срок действия пакета или включите бессрочный режим.")
            if not indefinite and not fade_duration_days:
                raise ValueError("Укажите длительность плавного затухания или включите бессрочный режим.")
            if required_account_level_id and price_stars:
                raise ValueError("Автоматический пакет по уровню аккаунта должен быть бесплатным.")
            if apply_to_new_channels and price_stars:
                raise ValueError("Пакет для всех новых каналов должен быть бесплатным: списать звёзды у ещё не созданного канала невозможно.")
            if apply_to_new_channels:
                con.execute("UPDATE demo_activity_packages SET apply_to_new_channels = 0")
            con.execute(
                """INSERT INTO demo_activity_packages(id,title,subscribers_per_day,views_per_day,reactions_per_day,comments_per_day,post_limit,duration_days,fade_duration_days,indefinite,price_stars,apply_to_new_channels,required_account_level_id,commenter_ids_json,donation_count,donation_post_interval,donation_min_stars,donation_max_stars,inactivity_days,created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (uid("demopackage"), title, values["subscribers"], values["views"], values["reactions"], values["comments"], post_limit, duration_days, fade_duration_days, 1 if indefinite else 0, price_stars, 1 if apply_to_new_channels else 0, required_account_level_id, dumps(commenter_ids), donation_count, donation_post_interval or 4, donation_min_stars, donation_max_stars, inactivity_days, now()),
            )
            return self.json({"ok": True})
        if path == "/api/admin/demo-activity-packages/update" and method == "POST":
            package_id = str(body.get("packageId", "")).strip()
            if not con.execute("SELECT 1 FROM demo_activity_packages WHERE id = ?", (package_id,)).fetchone():
                raise ValueError("Демо-пакет не найден.")
            title = " ".join(str(body.get("title", "")).split())[:80]
            if not title:
                raise ValueError("Введите название демо-пакета.")
            values = {
                metric: nonnegative_int(body.get(f"{metric}PerDay", 0), f"{metric}PerDay", 1_000_000)
                for metric in ("subscribers", "views", "reactions", "comments")
            }
            post_limit = nonnegative_int(body.get("postLimit", 1), "postLimit", 10)
            duration_days = nonnegative_int(body.get("durationDays", 7), "durationDays", 3650)
            indefinite = bool(body.get("indefinite"))
            fade_duration_days = nonnegative_int(body.get("fadeDurationDays", 30), "fadeDurationDays", 365)
            price_stars = nonnegative_int(body.get("priceStars", 0), "priceStars", 1_000_000)
            donation_count = nonnegative_int(body.get("donationCount", 0), "donationCount", 100)
            donation_post_interval = nonnegative_int(body.get("donationPostInterval", 4), "donationPostInterval", 1_000)
            donation_min_stars = nonnegative_int(body.get("donationMinStars", 0), "donationMinStars", 1_000_000)
            donation_max_stars = nonnegative_int(body.get("donationMaxStars", 0), "donationMaxStars", 1_000_000)
            inactivity_days = nonnegative_int(body.get("inactivityDays", 3), "inactivityDays", 365)
            if not any(values.values()):
                raise ValueError("Укажите хотя бы один дневной показатель.")
            if not inactivity_days:
                raise ValueError("Укажите число дней без публикаций до затухания пакета.")
            if not indefinite and not duration_days:
                raise ValueError("Укажите срок действия пакета или включите бессрочный режим.")
            if not indefinite and not fade_duration_days:
                raise ValueError("Укажите длительность плавного затухания или включите бессрочный режим.")
            if donation_count and (not donation_post_interval or not donation_min_stars or donation_max_stars < donation_min_stars):
                raise ValueError("Для автодонатов укажите интервал и корректный диапазон звёзд.")
            apply_to_new_channels = bool(body.get("applyToNewChannels"))
            required_account_level_id = str(body.get("requiredAccountLevelId", "") or "").strip().lower()
            levels_row = con.execute("SELECT value FROM settings WHERE key = 'account_levels'").fetchone()
            configured_levels = normalize_account_levels(loads(levels_row["value"], []) if levels_row else []) if levels_row else []
            if required_account_level_id and required_account_level_id not in {level["id"] for level in configured_levels}:
                raise ValueError("Выберите существующий уровень аккаунта для пакета.")
            if required_account_level_id and price_stars:
                raise ValueError("Автоматический пакет по уровню аккаунта должен быть бесплатным.")
            if apply_to_new_channels and price_stars:
                raise ValueError("Пакет для всех новых каналов должен быть бесплатным: списать звёзды у ещё не созданного канала невозможно.")
            if apply_to_new_channels:
                con.execute("UPDATE demo_activity_packages SET apply_to_new_channels = 0 WHERE id != ?", (package_id,))
            con.execute(
                """UPDATE demo_activity_packages SET title=?, subscribers_per_day=?, views_per_day=?, reactions_per_day=?,
                   comments_per_day=?, post_limit=?, duration_days=?, fade_duration_days=?, indefinite=?, price_stars=?,
                   apply_to_new_channels=?, required_account_level_id=?, donation_count=?, donation_post_interval=?,
                   donation_min_stars=?, donation_max_stars=?, inactivity_days=? WHERE id=?""",
                (title, values["subscribers"], values["views"], values["reactions"], values["comments"], post_limit,
                 duration_days, fade_duration_days, 1 if indefinite else 0, price_stars, 1 if apply_to_new_channels else 0,
                 required_account_level_id, donation_count, donation_post_interval or 4, donation_min_stars,
                 donation_max_stars, inactivity_days, package_id),
            )
            return self.json({"ok": True})
        if path == "/api/admin/demo-activity-packages/delete" and method == "POST":
            package_id = str(body.get("packageId", "")).strip()
            if con.execute("SELECT 1 FROM demo_activity_subscriptions WHERE package_id = ? AND active = 1", (package_id,)).fetchone():
                raise ValueError("Сначала отключите активные подключения этого пакета.")
            con.execute("DELETE FROM demo_activity_packages WHERE id = ?", (package_id,))
            return self.json({"ok": True})
        if path == "/api/admin/demo-activity-subscriptions" and method == "POST":
            package_id = str(body.get("packageId", "")).strip()
            channel_id = str(body.get("channelId", "")).strip()
            package = con.execute("SELECT * FROM demo_activity_packages WHERE id = ?", (package_id,)).fetchone()
            if not package or not con.execute("SELECT 1 FROM chats WHERE id = ? AND type = 'channel'", (channel_id,)).fetchone():
                raise ValueError("Выберите существующий пакет и канал.")
            if (package["views_per_day"] or package["reactions_per_day"] or package["comments_per_day"]) and not demo_activity_post(con, channel_id):
                raise ValueError("Для этого пакета в канале должна быть хотя бы одна публикация.")
            if package["comments_per_day"] and not automated_commenter_pool(con):
                raise ValueError("Для комментариев сначала добавьте служебные аккаунты в раздел «Автокомментарии».")
            owner_id = con.execute("SELECT owner_id FROM chats WHERE id = ?", (channel_id,)).fetchone()["owner_id"]
            if not account_level_available_for_user(con, owner_id, package["required_account_level_id"]):
                raise ValueError("У владельца канала нет требуемого уровня аккаунта для этого пакета.")
            price_stars = int(package["price_stars"] or 0)
            if price_stars:
                charged = con.execute("UPDATE users SET stars = stars - ? WHERE id = ? AND stars >= ?", (price_stars, owner_id, price_stars)).rowcount
                if not charged:
                    raise ValueError("У владельца канала недостаточно звёзд для этого пакета.")
                self.record_star_transaction(con, owner_id, -price_stars, "demo_activity_package", f"Демо-пакет «{package['title']}» для канала")
            current = now()
            con.execute(
                """INSERT INTO demo_activity_subscriptions(id,package_id,channel_id,starts_at,ends_at,auto_renew,created_at)
                   VALUES (?,?,?,?,?,?,?)""",
                (uid("demosubscription"), package_id, channel_id, current, current + max(1, package["duration_days"]) * 86400, 0 if package["indefinite"] else 1 if body.get("autoRenew") else 0, current),
            )
            return self.json({"ok": True})
        if path == "/api/admin/demo-activity-packages/default" and method == "POST":
            package_id = str(body.get("packageId", "")).strip()
            enabled = bool(body.get("enabled", True))
            package = con.execute("SELECT price_stars FROM demo_activity_packages WHERE id = ?", (package_id,)).fetchone()
            if enabled and not package:
                raise ValueError("Демо-пакет не найден.")
            if enabled and int(package["price_stars"] or 0):
                raise ValueError("Пакет для всех новых каналов должен быть бесплатным.")
            if enabled:
                con.execute("UPDATE demo_activity_packages SET apply_to_new_channels = 0")
            con.execute("UPDATE demo_activity_packages SET apply_to_new_channels = ? WHERE id = ?", (1 if enabled else 0, package_id))
            return self.json({"ok": True})
        if path == "/api/admin/demo-activity-subscriptions/deactivate" and method == "POST":
            con.execute("UPDATE demo_activity_subscriptions SET active = 0 WHERE id = ?", (str(body.get("subscriptionId", "")),))
            return self.json({"ok": True})
        if path == "/api/admin/boost-jobs" and method == "POST":
            target_type = str(body.get("targetType", ""))
            target_id = str(body.get("targetId", ""))
            metric = str(body.get("metric", ""))
            amount_per_minute = nonnegative_int(body.get("amountPerMinute", 1), "amountPerMinute", 10_000)
            duration = nonnegative_int(body.get("durationMinutes", 1), "durationMinutes", 10_080)
            if not amount_per_minute or not duration:
                raise ValueError("Скорость и длительность накрутки должны быть больше нуля.")
            if target_type == "chat" and metric == "subscribers":
                target = con.execute("SELECT 1 FROM chats WHERE id = ? AND type IN ('group','community','channel')", (target_id,)).fetchone()
            elif target_type == "message" and metric in {"views", "reactions"}:
                target = con.execute("SELECT 1 FROM messages WHERE id = ?", (target_id,)).fetchone()
            else:
                raise ValueError("Выберите поддерживаемую цель и показатель.")
            if not target:
                raise ValueError("Цель накрутки не найдена.")
            total = amount_per_minute * duration
            con.execute(
                """INSERT INTO boost_jobs(id,target_type,target_id,metric,amount_per_minute,remaining,active,last_tick,created_at)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (uid("boost"), target_type, target_id, metric, amount_per_minute, total, 1, now(), now()),
            )
            return self.json({"ok": True})
        if path == "/api/admin/channel-growth-jobs" and method == "POST":
            channel_id = str(body.get("channelId", "")).strip()
            subscribers_per_hour = nonnegative_int(body.get("subscribersPerHour", 0), "subscribersPerHour", 100_000)
            views_per_hour = nonnegative_int(body.get("viewsPerHour", 0), "viewsPerHour", 100_000)
            reactions_per_hour = nonnegative_int(body.get("reactionsPerHour", 0), "reactionsPerHour", 100_000)
            comments_per_hour = nonnegative_int(body.get("commentsPerHour", 0), "commentsPerHour", 1_000)
            duration_hours = nonnegative_int(body.get("durationHours", 0), "durationHours", 720)
            if not duration_hours or not any((subscribers_per_hour, views_per_hour, reactions_per_hour, comments_per_hour)):
                raise ValueError("Укажите длительность и хотя бы одну ненулевую скорость.")
            if not con.execute("SELECT 1 FROM chats WHERE id = ? AND type = 'channel'", (channel_id,)).fetchone():
                raise ValueError("Выберите существующий канал.")
            if (views_per_hour or reactions_per_hour or comments_per_hour) and not weighted_channel_post(con, channel_id):
                raise ValueError("Для просмотров, реакций или комментариев в канале должна быть хотя бы одна публикация.")
            if comments_per_hour and not con.execute("SELECT 1 FROM automated_commenters LIMIT 1").fetchone():
                raise ValueError("Для ИИ-комментариев сначала добавьте аккаунты в пул автокомментаторов.")
            starts_at = now()
            con.execute(
                """INSERT INTO channel_growth_jobs(
                       id,channel_id,subscribers_per_hour,views_per_hour,reactions_per_hour,comments_per_hour,
                       starts_at,ends_at,subscribers_added,views_added,reactions_added,comments_added,active,created_at
                   ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (uid("channel_growth"), channel_id, subscribers_per_hour, views_per_hour, reactions_per_hour, comments_per_hour,
                 starts_at, starts_at + duration_hours * 3600, 0, 0, 0, 0, 1, starts_at),
            )
            return self.json({"ok": True})
        if path == "/api/admin/automated-commenters" and method == "POST":
            return self.create_automated_commenter(con, body)
        if path == "/api/admin/automated-commenters/update" and method == "POST":
            return self.update_automated_commenter(con, body)
        if path == "/api/admin/automated-commenters/create-pool" and method == "POST":
            return self.create_automated_commenter_pool(con)
        if path == "/api/admin/automated-commenters/password" and method == "POST":
            return self.reset_automated_commenter_password(con, body)
        if path == "/api/admin/automated-comment-rules" and method == "POST":
            return self.create_automated_comment_rule(con, body)
        if path == "/api/admin/automated-comment-rules/deactivate" and method == "POST":
            rule_id = str(body.get("ruleId", ""))
            con.execute("UPDATE automated_comment_rules SET active = 0 WHERE id = ?", (rule_id,))
            con.execute("DELETE FROM automated_comment_jobs WHERE rule_id = ?", (rule_id,))
            return self.json({"ok": True})
        if path == "/api/admin/stories/delete" and method == "POST":
            story_id = str(body.get("storyId", ""))
            if not con.execute("SELECT 1 FROM stories WHERE id = ?", (story_id,)).fetchone():
                raise ValueError("Сторис не найдена.")
            con.execute("DELETE FROM stories WHERE id = ?", (story_id,))
            return self.json({"ok": True})
        if path == "/api/admin/messages/moderate" and method == "POST":
            return self.moderate_message_admin(con, body)
        return self.json({"ok": False, "error": "Admin API не найден."}, HTTPStatus.NOT_FOUND)

    def register(self, con, body):
        username = normalize_username(body.get("username"))
        validate_username(username)
        if username_taken(con, username):
            raise ValueError("Этот username уже занят. Выберите другой.")
        name = str(body.get("name", "")).strip()
        password = str(body.get("password", ""))
        email = normalize_email(body.get("email"))
        if body.get("agreementAccepted") is not True and str(body.get("agreementAccepted", "")).lower() != "true":
            raise ValueError("Для регистрации необходимо принять пользовательское соглашение.")
        if not name:
            raise ValueError("Введите имя.")
        if len(password) < 8:
            raise ValueError("Пароль должен быть не короче 8 символов.")
        if con.execute("SELECT 1 FROM users WHERE email = ? COLLATE NOCASE", (email,)).fetchone():
            raise ValueError("Этот e-mail уже используется.")
        challenge_id = self.create_auth_challenge(
            con, "register", email, None, None,
            {"name": name[:80], "username": username, "password": hash_password(password), "agreementAcceptedAt": now()},
            "Подтверждение регистрации",
        )
        return self.json({"ok": True, "challengeId": challenge_id, "message": "Код подтверждения отправлен."})

    def verify_registration(self, con, body):
        challenge = self.verify_auth_challenge(con, body, "register")
        payload = loads(challenge["payload_json"], {})
        username = str(payload.get("username", ""))
        if not username or username_taken(con, username):
            raise ValueError("Username уже занят. Начните регистрацию заново.")
        if con.execute("SELECT 1 FROM users WHERE email = ? COLLATE NOCASE", (challenge["email"],)).fetchone():
            raise ValueError("Этот e-mail уже используется.")
        user_id = uid("user")
        appearance = dialog_appearance_defaults(con)
        con.execute(
            """INSERT INTO users(id,name,username,password,email,email_verified,stars,theme,dialog_color,other_dialog_color,dialog_panel_color,dialog_panel_style,dialog_bubble_style,dialog_font,text_scale,chat_background,chat_background_data,agreement_accepted_at,created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (user_id, payload["name"], username, payload["password"], challenge["email"], 1, 50, *(appearance[field] for field in DIALOG_APPEARANCE_FIELDS), payload.get("agreementAcceptedAt") or now(), now()),
        )
        con.execute("DELETE FROM auth_challenges WHERE id = ?", (challenge["id"],))
        self.ensure_saved(con, user_id)
        return self.issue_token(con, user_id)

    def login(self, con, body):
        cleanup_expired_deleted_accounts(con)
        login = str(body.get("login", body.get("username", ""))).strip()
        if "@" in login:
            email = normalize_email(login)
            user = con.execute("SELECT * FROM users WHERE email = ? COLLATE NOCASE", (email,)).fetchone()
        else:
            username = normalize_username(login)
            user = con.execute("SELECT * FROM users WHERE username = ? COLLATE NOCASE", (username,)).fetchone()
        if not user or not password_matches(user["password"], str(body.get("password", ""))):
            raise ValueError("Неверный username, e-mail или пароль.")
        if not user["password"].startswith("pbkdf2_sha256$"):
            con.execute("UPDATE users SET password = ? WHERE id = ?", (hash_password(str(body.get("password", ""))), user["id"]))
        self.restore_deleted_account(con, user["id"])
        self.update_login_streak(con, user["id"])
        self.ensure_saved(con, user["id"])
        return self.issue_token(con, user["id"])

    def request_account_deletion(self, con, user, body):
        if str(body.get("confirmation", "")).strip() != "УДАЛИТЬ":
            raise ValueError("Для удаления введите слово «УДАЛИТЬ».")
        password = str(body.get("password", ""))
        has_vk_identity = bool(con.execute(
            "SELECT 1 FROM oauth_identities WHERE provider = 'vk' AND user_id = ?",
            (user["id"],),
        ).fetchone())
        if password and not password_matches(user["password"], password):
            raise ValueError("Текущий пароль введён неверно.")
        if not password and not has_vk_identity:
            raise ValueError("Введите текущий пароль для удаления страницы.")
        timestamp = now()
        deletion_due_at = timestamp + ACCOUNT_DELETION_GRACE_SECONDS
        con.execute(
            "UPDATE users SET deletion_requested_at = ?, deletion_due_at = ? WHERE id = ?",
            (timestamp, deletion_due_at, user["id"]),
        )
        con.execute("DELETE FROM sessions WHERE user_id = ?", (user["id"],))
        return self.json({"ok": True, "deletionDueAt": deletion_due_at})

    def restore_deleted_account(self, con, user_id):
        con.execute(
            "UPDATE users SET deletion_requested_at = NULL, deletion_due_at = NULL WHERE id = ? AND deletion_due_at IS NOT NULL",
            (user_id,),
        )

    def create_auth_challenge(self, con, purpose, email, phone, user_id, payload, message) -> str:
        current = now()
        con.execute("DELETE FROM auth_challenges WHERE expires_at < ? OR (purpose = ? AND email = ? AND phone = ?)", (current, purpose, email, phone))
        email_code = generate_auth_code()
        challenge_id = uid("auth")
        con.execute(
            """INSERT INTO auth_challenges(id,purpose,email,phone,user_id,payload_json,email_code_hash,phone_code_hash,expires_at,created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (challenge_id, purpose, email, None, user_id, dumps(payload), hash_password(email_code), None, current + AUTH_CODE_TTL, current),
        )
        deliver_email_code(email, email_code, message)
        return challenge_id

    def verify_auth_challenge(self, con, body, purpose):
        challenge_id = str(body.get("challengeId", ""))
        challenge = con.execute("SELECT * FROM auth_challenges WHERE id = ? AND purpose = ?", (challenge_id, purpose)).fetchone()
        if not challenge or challenge["expires_at"] < now():
            raise ValueError("Код истёк. Запросите новые коды.")
        if challenge["attempts"] >= AUTH_CODE_MAX_ATTEMPTS:
            raise ValueError("Слишком много неверных попыток. Запросите новые коды.")
        code = str(body.get("code", ""))
        code_hash = challenge["email_code_hash"]
        valid = bool(code_hash) and password_matches(code_hash, code)
        if not valid:
            con.execute("UPDATE auth_challenges SET attempts = attempts + 1 WHERE id = ?", (challenge_id,))
            raise ValueError("Один или оба кода неверны.")
        return challenge

    def resend_auth_challenge(self, con, body):
        challenge_id = str(body.get("challengeId", ""))
        purpose = str(body.get("purpose", ""))
        if purpose not in {"register", "password_reset"}:
            raise ValueError("Неизвестный тип подтверждения.")
        challenge = con.execute("SELECT * FROM auth_challenges WHERE id = ? AND purpose = ?", (challenge_id, purpose)).fetchone()
        if not challenge or challenge["expires_at"] < now():
            raise ValueError("Срок действия кода истёк. Начните подтверждение заново.")
        retry_after = 60 - (now() - challenge["created_at"])
        if retry_after > 0:
            raise ValueError(f"Повторный код можно запросить через {retry_after} с.")
        code = generate_auth_code()
        message = "Подтверждение регистрации" if purpose == "register" else "Восстановление пароля"
        con.execute(
            "UPDATE auth_challenges SET email_code_hash = ?, attempts = 0, expires_at = ?, created_at = ? WHERE id = ?",
            (hash_password(code), now() + AUTH_CODE_TTL, now(), challenge_id),
        )
        deliver_email_code(challenge["email"], code, message)
        return self.json({"ok": True, "message": "Новый код отправлен на тот же контакт."})

    def request_password_reset(self, con, body):
        contact = str(body.get("contact", "")).strip()
        try:
            normalized_contact = normalize_email(contact)
        except ValueError:
            return self.json({"ok": True, "message": "Если контакт найден, инструкции по восстановлению отправлены."})
        user = con.execute("SELECT * FROM users WHERE email = ? COLLATE NOCASE", (normalized_contact,)).fetchone()
        if user:
            challenge_id = self.create_auth_challenge(con, "password_reset", user["email"], None, user["id"], {}, "Восстановление пароля")
            return self.json({"ok": True, "challengeId": challenge_id, "message": "Если контакт найден, код отправлен."})
        return self.json({"ok": True, "message": "Если контакт найден, инструкции по восстановлению отправлены."})

    def confirm_password_reset(self, con, body):
        challenge = self.verify_auth_challenge(con, body, "password_reset")
        password = str(body.get("password", ""))
        if len(password) < 8:
            raise ValueError("Новый пароль должен быть не короче 8 символов.")
        con.execute("UPDATE users SET password = ? WHERE id = ?", (hash_password(password), challenge["user_id"]))
        con.execute("DELETE FROM sessions WHERE user_id = ?", (challenge["user_id"],))
        con.execute("DELETE FROM auth_challenges WHERE id = ?", (challenge["id"],))
        return self.json({"ok": True, "message": "Пароль изменён. Войдите с новым паролем."})

    def create_session_token(self, con, user_id):
        token = secrets.token_urlsafe(24)
        con.execute("INSERT INTO sessions(token,user_id,created_at) VALUES (?,?,?)", (token, user_id, now()))
        return token

    def issue_token(self, con, user_id):
        token = self.create_session_token(con, user_id)
        user = con.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return self.json({"ok": True, "token": token, "user": public_user(user)})

    def vk_oauth_configured(self):
        return bool(VK_OAUTH_CLIENT_ID and VK_OAUTH_REDIRECT_URI.startswith("https://"))

    def start_vk_oauth(self, con, user, body):
        if not self.vk_oauth_configured():
            raise ValueError("Вход через VK ещё не настроен на сервере.")
        linking = bool(body.get("link"))
        if linking:
            self.require_user(user)
        agreement_accepted = bool(body.get("agreementAccepted"))
        if not linking and not agreement_accepted:
            raise ValueError("Для первого входа через VK примите пользовательское соглашение.")
        state = secrets.token_urlsafe(32)
        code_verifier = secrets.token_urlsafe(64)
        code_challenge = base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode("ascii")).digest()).decode("ascii").rstrip("=")
        timestamp = now()
        con.execute("DELETE FROM oauth_states WHERE expires_at < ?", (timestamp,))
        con.execute(
            "INSERT INTO oauth_states(state,provider,user_id,agreement_accepted,code_verifier,expires_at,created_at) VALUES (?,?,?,?,?,?,?)",
            (state, "vk", user["id"] if linking else None, int(agreement_accepted), code_verifier, timestamp + 600, timestamp),
        )
        params = {
            "response_type": "code",
            "client_id": VK_OAUTH_CLIENT_ID,
            "redirect_uri": VK_OAUTH_REDIRECT_URI,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        if VK_OAUTH_SCOPE:
            params["scope"] = VK_OAUTH_SCOPE
        return self.json({"ok": True, "authorizationUrl": f"https://id.vk.ru/authorize?{urlencode(params)}"})

    def vk_oauth_redirect(self, params):
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", "/#" + urlencode(params))
        self.end_headers()

    def vk_oauth_profile(self, code, device_id, state, code_verifier):
        payload = {
            "grant_type": "authorization_code",
            "code_verifier": code_verifier,
            "redirect_uri": VK_OAUTH_REDIRECT_URI,
            "code": code,
            "client_id": VK_OAUTH_CLIENT_ID,
            "device_id": device_id,
            "state": state,
        }
        if VK_ID_SERVICE_TOKEN:
            payload["service_token"] = VK_ID_SERVICE_TOKEN
        try:
            request = urlrequest.Request(
                "https://id.vk.ru/oauth2/auth",
                data=urlencode(payload).encode("utf-8"),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                method="POST",
            )
            with urlrequest.urlopen(request, timeout=15) as response:
                token_data = loads(response.read().decode("utf-8"), {})
            access_token = str(token_data.get("access_token", ""))
            vk_user_id = str(token_data.get("user_id", ""))
            if not access_token or not vk_user_id or str(token_data.get("state", "")) != state:
                raise ValueError
            profile_request = urlrequest.Request(
                "https://id.vk.ru/oauth2/user_info",
                data=urlencode({"client_id": VK_OAUTH_CLIENT_ID, "access_token": access_token}).encode("utf-8"),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                method="POST",
            )
            with urlrequest.urlopen(profile_request, timeout=15) as response:
                profile_data = loads(response.read().decode("utf-8"), {})
            profile = profile_data.get("user") if isinstance(profile_data, dict) else None
            if not isinstance(profile, dict):
                raise ValueError
            return vk_user_id, profile
        except (OSError, ValueError, TypeError, urlerror.HTTPError):
            raise ValueError("VK ID не подтвердил вход. Попробуйте ещё раз.") from None

    def create_vk_user(self, con, vk_user_id, profile, agreement_accepted):
        if not agreement_accepted:
            raise ValueError("Для создания аккаунта примите пользовательское соглашение.")
        base_username = re.sub(r"[^a-z0-9_]", "", f"vk_{vk_user_id}".lower())[:20]
        username = base_username or "vk_user"
        suffix = 1
        while username_taken(con, username):
            suffix_text = str(suffix)
            username = f"{base_username[:20 - len(suffix_text)]}{suffix_text}"
            suffix += 1
        name = " ".join(str(profile.get(key, "")) for key in ("first_name", "last_name")).strip()[:80] or "Пользователь VK"
        appearance = dialog_appearance_defaults(con)
        user_id = uid("user")
        con.execute(
            """INSERT INTO users(id,name,username,password,stars,theme,dialog_color,other_dialog_color,dialog_panel_color,dialog_panel_style,dialog_bubble_style,dialog_font,text_scale,chat_background,chat_background_data,agreement_accepted_at,created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (user_id, name, username, hash_password(secrets.token_urlsafe(32)), 50, *(appearance[field] for field in DIALOG_APPEARANCE_FIELDS), now(), now()),
        )
        self.ensure_saved(con, user_id)
        return user_id

    def complete_vk_oauth(self, con, query):
        if not self.vk_oauth_configured():
            return self.vk_oauth_redirect({"vk_error": "Вход через VK не настроен."})
        state_value = str((query.get("state") or [""])[0])
        code = str((query.get("code") or [""])[0])
        device_id = str((query.get("device_id") or [""])[0])
        state = con.execute("SELECT * FROM oauth_states WHERE state = ? AND provider = 'vk' AND expires_at >= ?", (state_value, now())).fetchone()
        con.execute("DELETE FROM oauth_states WHERE state = ?", (state_value,))
        if not state or not code or not device_id or not state["code_verifier"]:
            return self.vk_oauth_redirect({"vk_error": "Вход через VK отменён или ссылка устарела."})
        try:
            vk_user_id, profile = self.vk_oauth_profile(code, device_id, state_value, state["code_verifier"])
            identity = con.execute("SELECT user_id FROM oauth_identities WHERE provider = 'vk' AND provider_user_id = ?", (vk_user_id,)).fetchone()
            requested_user_id = state["user_id"]
            if requested_user_id and identity and identity["user_id"] != requested_user_id:
                raise ValueError("Этот VK-аккаунт уже привязан к другому профилю.")
            if requested_user_id:
                user_id = requested_user_id
            elif identity:
                user_id = identity["user_id"]
            else:
                user_id = self.create_vk_user(con, vk_user_id, profile, bool(state["agreement_accepted"]))
            con.execute(
                """INSERT INTO oauth_identities(provider,provider_user_id,user_id,created_at,updated_at) VALUES ('vk',?,?,?,?)
                   ON CONFLICT(provider,provider_user_id) DO UPDATE SET user_id=excluded.user_id, updated_at=excluded.updated_at""",
                (vk_user_id, user_id, now(), now()),
            )
            self.restore_deleted_account(con, user_id)
            self.update_login_streak(con, user_id)
            token = self.create_session_token(con, user_id)
            return self.vk_oauth_redirect({"vk_token": token})
        except ValueError as error:
            return self.vk_oauth_redirect({"vk_error": str(error)[:300]})

    def update_login_streak(self, con, user_id):
        today = time.strftime("%Y-%m-%d")
        yesterday = time.strftime("%Y-%m-%d", time.localtime(time.time() - 86400))
        user = con.execute("SELECT last_login_day, login_streak FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user or user["last_login_day"] == today:
            return
        streak = int(user["login_streak"] or 0) + 1 if user["last_login_day"] == yesterday else 1
        con.execute("UPDATE users SET last_login_day = ?, login_streak = ? WHERE id = ?", (today, streak, user_id))

    def users_are_blocked(self, con, first_user_id, second_user_id):
        return bool(con.execute(
            "SELECT 1 FROM user_blocks WHERE (owner_id = ? AND blocked_user_id = ?) OR (owner_id = ? AND blocked_user_id = ?) LIMIT 1",
            (first_user_id, second_user_id, second_user_id, first_user_id),
        ).fetchone())

    def bootstrap(self, con, user):
        self.ensure_saved(con, user["id"])
        self.evaluate_statuses(con, user["id"])
        users = [public_user(r) for r in con.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()]
        avatar_history = {}
        for row in con.execute("SELECT user_id, avatar_data FROM avatar_history ORDER BY created_at DESC, id DESC").fetchall():
            avatar_history.setdefault(row["user_id"], []).append(row["avatar_data"])
        for public in users:
            public["avatarHistory"] = avatar_history.get(public["id"], [])
        chats = [chat_to_dict(r) for r in con.execute(
            """SELECT c.*,
                      EXISTS(SELECT 1 FROM pinned_chats pc WHERE pc.chat_id = c.id AND pc.user_id = ?) AS pinned,
                      EXISTS(SELECT 1 FROM archived_chats ac WHERE ac.chat_id = c.id AND ac.user_id = ?) AS archived,
                       (SELECT COUNT(*) FROM messages m
                        WHERE m.chat_id = c.id AND m.sender_id != ?
                          AND m.deleted_by_admin = 0
                          AND m.rowid > COALESCE((SELECT crs.read_rowid FROM chat_read_states crs WHERE crs.chat_id = c.id AND crs.user_id = ?), 0)
                          AND NOT EXISTS(SELECT 1 FROM hidden_messages hm WHERE hm.message_id = m.id AND hm.user_id = ?)) AS unread_count
               FROM chats c
               WHERE NOT EXISTS(SELECT 1 FROM hidden_chats hc WHERE hc.chat_id = c.id AND hc.user_id = ?)
                  AND NOT EXISTS(SELECT 1 FROM user_blocks ub WHERE ub.owner_id = c.owner_id AND ub.blocked_user_id = ?)
                  AND NOT (c.type = 'direct' AND EXISTS(SELECT 1 FROM chat_members other WHERE other.chat_id = c.id AND other.user_id != ? AND EXISTS(SELECT 1 FROM user_blocks ub WHERE (ub.owner_id = ? AND ub.blocked_user_id = other.user_id) OR (ub.owner_id = other.user_id AND ub.blocked_user_id = ?))))
                  AND (c.type != 'channel' OR EXISTS(SELECT 1 FROM chat_members cm WHERE cm.chat_id = c.id AND cm.user_id = ?) OR COALESCE(json_extract(c.settings_json, '$.isPublic'), 1) = 1)
                  AND (c.type != 'secret' OR EXISTS(SELECT 1 FROM secret_chat_unlocks scu WHERE scu.chat_id = c.id AND scu.user_id = ?))
               ORDER BY updated_at DESC""",
            (user["id"], user["id"], user["id"], user["id"], user["id"], user["id"], user["id"], user["id"], user["id"], user["id"], user["id"], user["id"]),
        ).fetchall()]
        members = [dict(r) for r in con.execute(
            """SELECT cm.* FROM chat_members cm
               JOIN chats c ON c.id = cm.chat_id
               WHERE (c.type != 'secret' OR EXISTS(
                       SELECT 1 FROM secret_chat_unlocks scu
                       WHERE scu.chat_id = c.id AND scu.user_id = ?
                   ))
                 AND (
                       c.type != 'channel'
                        OR cm.user_id = ?
                        OR cm.role IN ('owner', 'admin', 'author')
                 )""",
            (user["id"], user["id"]),
        ).fetchall()]
        scheduled_posts = [dict(r) for r in con.execute(
            "SELECT id, chat_id, text, media_type, publish_at FROM scheduled_posts WHERE sender_id = ? ORDER BY publish_at", (user["id"],)
        ).fetchall()]
        channel_links = [dict(r) for r in con.execute(
            """SELECT cl.* FROM channel_links cl
               WHERE EXISTS(
                   SELECT 1 FROM chat_members cm
                   WHERE cm.chat_id = cl.channel_id
                     AND cm.user_id = ?
                     AND cm.role IN ('owner', 'admin', 'author')
               )""",
            (user["id"],),
        ).fetchall()]
        telegram_channel_links = [dict(r) for r in con.execute(
            """SELECT tl.channel_id, tl.source_chat_ref, tl.source_chat_id, tl.last_sync_at, tl.last_error, tl.created_at
               FROM telegram_channel_links tl JOIN chats c ON c.id = tl.channel_id
               WHERE c.owner_id = ?""",
            (user["id"],),
        ).fetchall()]
        rss_channel_links = [dict(r) for r in con.execute(
            """SELECT rs.id, rs.channel_id, rs.feed_url, rs.feed_title, rs.last_sync_at, rs.last_error, rs.created_at
               FROM rss_channel_sources rs JOIN chats c ON c.id = rs.channel_id
               WHERE c.owner_id = ?""",
            (user["id"],),
        ).fetchall()]
        vk_channel_links = [dict(r) for r in con.execute(
            """SELECT vs.id, vs.channel_id, vs.source_url, vs.source_title, vs.keywords_json, vs.publish_enabled, vs.moderation_enabled, vs.last_sync_at, vs.last_error, vs.created_at
               FROM vk_channel_sources vs JOIN chats c ON c.id = vs.channel_id
               WHERE EXISTS(
                   SELECT 1 FROM chat_members cm
                   WHERE cm.chat_id = vs.channel_id AND cm.user_id = ?
               )""",
            (user["id"],),
        ).fetchall()]
        for link in vk_channel_links:
            link["keywords"] = loads(link.pop("keywords_json"), [])
        vk_channel_targets = [dict(r) for r in con.execute(
            """SELECT vt.id, vt.channel_id, vt.target_url, vt.target_title, vt.publish_enabled, vt.moderation_enabled,
                      vt.last_publish_at, vt.last_moderation_sync_at, vt.last_error, vt.created_at
               FROM vk_channel_targets vt JOIN chats c ON c.id = vt.channel_id
               WHERE EXISTS(
                   SELECT 1 FROM chat_members cm
                   WHERE cm.chat_id = vt.channel_id AND cm.user_id = ?
               )""",
            (user["id"],),
        ).fetchall()]
        channel_comments = [dict(r) for r in con.execute(
            """SELECT cc.* FROM channel_comments cc
               JOIN messages m ON m.id = cc.message_id
               JOIN chats c ON c.id = m.chat_id
               WHERE c.type IN ('channel', 'group', 'community')
                 AND EXISTS(SELECT 1 FROM chat_members cm WHERE cm.chat_id = c.id AND cm.user_id = ?)
               ORDER BY cc.created_at""",
            (user["id"],),
        ).fetchall()]
        payout_summaries = [self.channel_payout_summary(con, user["id"], row["id"]) for row in con.execute(
            "SELECT id FROM chats WHERE owner_id = ? AND type IN ('channel', 'group', 'community')", (user["id"],)
        ).fetchall()]
        demo_activity_packages = [dict(row) for row in con.execute(
            "SELECT * FROM demo_activity_packages ORDER BY created_at DESC"
        ).fetchall()]
        channel_payout_requests = [dict(r) for r in con.execute(
            "SELECT * FROM channel_payout_requests WHERE owner_user_id = ? ORDER BY created_at DESC LIMIT 100", (user["id"],)
        ).fetchall()]
        channel_share_submissions = [dict(r) for r in con.execute(
            """SELECT submission.*, chat.title AS channel_title
               FROM channel_share_submissions submission JOIN chats chat ON chat.id = submission.channel_id
               WHERE submission.submitter_id = ? OR EXISTS(
                 SELECT 1 FROM chat_members cm WHERE cm.chat_id = submission.channel_id
                   AND cm.user_id = ? AND cm.role IN ('owner', 'admin', 'author')
               )
               ORDER BY submission.created_at DESC LIMIT 100""", (user["id"], user["id"])
        ).fetchall()]
        vk_review_submissions = [dict(r) for r in con.execute(
            """SELECT * FROM vk_review_submissions
               WHERE submitter_id = ?
               ORDER BY created_at DESC LIMIT 100""", (user["id"],)
        ).fetchall()]
        channel_star_purchases = [dict(r) for r in con.execute(
            """SELECT csp.*, u.name AS buyer_name, u.username AS buyer_username
               FROM channel_star_purchases csp
               JOIN chats c ON c.id = csp.channel_id
               JOIN users u ON u.id = csp.buyer_user_id
               WHERE c.owner_id = ?
               ORDER BY csp.created_at DESC
               LIMIT 100""",
            (user["id"],),
        ).fetchall()]
        notifications = [dict(r) for r in con.execute("SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT 30", (user["id"],)).fetchall()]
        channel_join_requests = [dict(r) for r in con.execute(
            """SELECT cjr.channel_id, cjr.user_id, cjr.created_at, u.name AS user_name, u.username
               FROM channel_join_requests cjr JOIN users u ON u.id = cjr.user_id
               WHERE cjr.status = 'pending' AND EXISTS(SELECT 1 FROM chat_members cm WHERE cm.chat_id = cjr.channel_id AND cm.user_id = ? AND cm.role IN ('owner', 'admin', 'author'))
               ORDER BY cjr.created_at""", (user["id"],)
        ).fetchall()]
        messages = [message_to_dict(r) for r in con.execute(
            """SELECT m.id, m.chat_id, m.sender_id, m.profile_user_id, m.text, m.media_type, m.media_data IS NOT NULL AS has_media, m.media_embed_url, m.voice_waveform_json, m.views, m.views_boost, m.reactions_json, m.pinned, m.forwarded_from, m.forwarded_from_user_id, m.source_type, m.source_id, m.ai_agent, m.reply_to_id, m.edited_at, m.created_at,
                      EXISTS(SELECT 1 FROM hidden_pinned_messages hpm WHERE hpm.message_id = m.id AND hpm.user_id = ?) AS pin_hidden,
                      (m.sender_id != ? AND m.rowid > COALESCE((SELECT crs.read_rowid FROM chat_read_states crs WHERE crs.chat_id = m.chat_id AND crs.user_id = ?), 0)) AS is_unread,
                      EXISTS(
                        SELECT 1 FROM chat_members recipient
                        JOIN chat_read_states recipient_state
                          ON recipient_state.chat_id = m.chat_id AND recipient_state.user_id = recipient.user_id
                        WHERE recipient.chat_id = m.chat_id
                          AND c.type = 'direct'
                          AND recipient.user_id != m.sender_id
                          AND recipient_state.read_rowid >= m.rowid
                      ) AS is_read_by_recipient
               FROM messages m
               JOIN chats c ON c.id = m.chat_id
                WHERE m.deleted_by_admin = 0
                  AND NOT EXISTS(SELECT 1 FROM hidden_messages hm WHERE hm.message_id = m.id AND hm.user_id = ?)
                  AND NOT EXISTS(SELECT 1 FROM user_blocks ub WHERE ub.owner_id = c.owner_id AND ub.blocked_user_id = ?)
                  AND NOT (c.type = 'direct' AND EXISTS(SELECT 1 FROM chat_members other WHERE other.chat_id = c.id AND other.user_id != ? AND EXISTS(SELECT 1 FROM user_blocks ub WHERE (ub.owner_id = ? AND ub.blocked_user_id = other.user_id) OR (ub.owner_id = other.user_id AND ub.blocked_user_id = ?))))
                  AND (c.type != 'channel' OR EXISTS(SELECT 1 FROM chat_members cm WHERE cm.chat_id = c.id AND cm.user_id = ?) OR COALESCE(json_extract(c.settings_json, '$.isPublic'), 1) = 1)
                  AND (c.type != 'secret' OR EXISTS(SELECT 1 FROM secret_chat_unlocks scu WHERE scu.chat_id = c.id AND scu.user_id = ?))
               ORDER BY m.created_at""",
            (user["id"], user["id"], user["id"], user["id"], user["id"], user["id"], user["id"], user["id"], user["id"], user["id"]),
        ).fetchall()]
        posts = [dict(r) for r in con.execute("SELECT * FROM profile_posts ORDER BY created_at DESC").fetchall()]
        for post in posts:
            post["reactions"] = {
                item["emoji"]: item["count"]
                for item in con.execute(
                    "SELECT emoji, count(*) AS count FROM profile_post_reactions WHERE post_id = ? GROUP BY emoji",
                    (post["id"],),
                ).fetchall()
            }
        stories = [self.story_to_dict(con, r, user["id"]) for r in con.execute(
            """SELECT * FROM stories
               WHERE (permanent = 1 OR expires_at > ?)
                 AND NOT EXISTS(SELECT 1 FROM hidden_story_authors hsa WHERE hsa.user_id = ? AND hsa.author_id = stories.user_id)
                 AND NOT EXISTS(SELECT 1 FROM story_privacy_blocks spb WHERE spb.owner_id = stories.user_id AND spb.blocked_user_id = ?)
               ORDER BY created_at DESC""",
            (now(), user["id"], user["id"]),
        ).fetchall()]
        reviews = [dict(r) for r in con.execute("SELECT * FROM reviews ORDER BY created_at DESC").fetchall()]
        for review in reviews:
            review["links"] = loads(review.pop("links_json"), [])
            review["mediaData"] = review.pop("media_data", None)
            review["sourceType"] = review.pop("source_type", "website")
            review["city"] = review.get("city", "")
        settings = {r["key"]: loads(r["value"], {}) for r in con.execute("SELECT * FROM settings").fetchall()}
        account_level = self.account_level_data(con, user["id"], settings.get("account_levels", []))
        star_package_discount = self.star_package_discount_percent(con, user["id"])
        promotions = [dict(r) for r in con.execute("SELECT * FROM promotions WHERE active = 1 ORDER BY created_at DESC").fetchall()]
        activity_rewards = self.activity_rewards_data(con, user["id"])
        statuses = [dict(r) for r in con.execute("SELECT * FROM statuses WHERE active = 1 ORDER BY created_at DESC").fetchall()]
        for status in statuses:
            status["criteria"] = loads(status.pop("criteria_json"), {})
            status["reward"] = loads(status.pop("reward_json"), {})
        user_statuses = [dict(r) for r in con.execute("SELECT * FROM user_statuses").fetchall()]
        recommended = [dict(r) for r in con.execute("SELECT * FROM recommended_groups ORDER BY position").fetchall()]
        star_transactions = [dict(r) for r in con.execute("SELECT * FROM star_transactions WHERE user_id = ? ORDER BY created_at DESC LIMIT 100", (user["id"],)).fetchall()]
        me = public_user(con.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone())
        me["avatarHistory"] = avatar_history.get(me["id"], [])
        me["hiddenStoryAuthorIds"] = [r["author_id"] for r in con.execute("SELECT author_id FROM hidden_story_authors WHERE user_id = ? ORDER BY created_at DESC", (user["id"],)).fetchall()]
        me["storyHiddenFromIds"] = [r["blocked_user_id"] for r in con.execute("SELECT blocked_user_id FROM story_privacy_blocks WHERE owner_id = ? ORDER BY created_at DESC", (user["id"],)).fetchall()]
        me["blockedUserIds"] = [r["blocked_user_id"] for r in con.execute("SELECT blocked_user_id FROM user_blocks WHERE owner_id = ? ORDER BY created_at DESC", (user["id"],)).fetchall()]
        activities = self.visible_chat_activities(con, chats, user["id"])
        packages = [{**item, "originalPrice": item["price"], "price": discounted_price(item["price"], star_package_discount)} for item in yookassa_star_packages(con)]
        ai_agent = self.ai_agent_settings(con, user["id"])
        ai_agent_bookings = self.ai_agent_bookings(con, user["id"])
        ai_agent_conversation = self.ai_agent_conversation(con, user["id"])
        return self.json({"ok": True, "me": me, "users": users, "chats": chats, "members": members, "messages": messages, "activities": activities, "scheduledPosts": scheduled_posts, "channelLinks": channel_links, "telegramChannelLinks": telegram_channel_links, "rssChannelLinks": rss_channel_links, "vkChannelLinks": vk_channel_links, "vkChannelTargets": vk_channel_targets, "channelComments": channel_comments, "channelStarPurchases": channel_star_purchases, "channelPayoutSummaries": payout_summaries, "channelPayoutRequests": channel_payout_requests, "channelShareSubmissions": channel_share_submissions, "vkReviewSubmissions": vk_review_submissions, "demoActivityPackages": demo_activity_packages, "notifications": notifications, "channelJoinRequests": [{"channelId": row["channel_id"], "userId": row["user_id"], "userName": row["user_name"], "username": row["username"], "createdAt": row["created_at"]} for row in channel_join_requests], "posts": posts, "stories": stories, "reviews": reviews, "settings": settings, "accountLevel": account_level, "aiAgent": ai_agent, "aiAgentBookings": ai_agent_bookings, "aiAgentConversation": ai_agent_conversation, "promotions": promotions, "activityRewards": activity_rewards, "statuses": statuses, "userStatuses": user_statuses, "recommended": recommended, "starTransactions": star_transactions, "mediaS3Enabled": s3_is_configured(), "yookassa": {"available": yookassa_configured(), "discountPercent": star_package_discount, "packages": packages}})

    def channel_feed_owner_level_rank(self, con, user_id, levels, current_time):
        """Return the owner's current configured account-level index without mutating progress."""
        activity = self.activity_metrics(con, user_id)
        activity.update({"communities": activity["communities_created"], "channels": activity["channels_created"]})
        earned_index = -1
        for index, level in enumerate(levels):
            criteria = level.get("criteria", {}) or {}
            if index == 0 or all(activity.get(key, 0) >= value for key, value in criteria.items()):
                earned_index = index
            else:
                break
        achievement = con.execute(
            "SELECT highest_level_index FROM account_level_achievements WHERE user_id = ?", (user_id,)
        ).fetchone()
        highest_achievement_index = int(achievement["highest_level_index"]) if achievement else 0
        achievement_lost = highest_achievement_index > earned_index
        purchased_ids = {row["level_id"] for row in con.execute(
            "SELECT level_id FROM account_level_purchases WHERE user_id = ?", (user_id,)
        ).fetchall()}
        granted_ids = {row["level_id"] for row in con.execute(
            "SELECT level_id FROM account_level_reward_grants WHERE user_id = ?", (user_id,)
        ).fetchall()}
        admin_grant = con.execute(
            "SELECT level_id FROM admin_account_level_grants WHERE user_id = ?", (user_id,)
        ).fetchone()
        if admin_grant:
            granted_ids.add(admin_grant["level_id"])
        subscribed_ids = {row["level_id"] for row in con.execute(
            """SELECT level_id FROM account_level_subscriptions
               WHERE user_id = ? AND status IN ('active', 'cancelled', 'payment_failed') AND active_until > ?""",
            (user_id, current_time),
        ).fetchall()}
        current_index = -1
        for index, level in enumerate(levels):
            paid_access = level["id"] in purchased_ids or level["id"] in granted_ids or level["id"] in subscribed_ids
            if index == 0 or (not achievement_lost and index <= earned_index) or paid_access:
                current_index = index
        return current_index

    def channel_feed(self, con, user, query):
        offset = nonnegative_int((query.get("offset", ["0"])[0] or "0"), "Смещение")
        # The feed is capped here: clients receive no more than 15 channels per request.
        limit = min(15, max(1, nonnegative_int((query.get("limit", ["15"])[0] or "15"), "Размер страницы")))
        settings_row = con.execute("SELECT value FROM settings WHERE key = 'account_levels'").fetchone()
        try:
            levels = normalize_account_levels(loads(settings_row["value"], []) if settings_row else [])
        except ValueError:
            levels = []
        current_time = now()
        rows = con.execute(
            """SELECT c.*,
                      COALESCE((SELECT MAX(m.created_at) FROM messages m
                                WHERE m.chat_id = c.id AND COALESCE(m.media_type, '') != 'system' AND m.deleted_by_admin = 0), 0) AS latest_post_at,
                      COALESCE((SELECT MAX(COALESCE(s.activity_last_tick_at, s.starts_at, s.created_at))
                                FROM demo_activity_subscriptions s
                                WHERE s.channel_id = c.id AND s.active = 1), 0) AS activity_package_at,
                      COALESCE((SELECT MAX(p.created_at) FROM channel_star_purchases p
                                WHERE p.channel_id = c.id), 0) AS star_purchase_at
                 FROM chats c
                WHERE c.type = 'channel'
                  AND NOT EXISTS(SELECT 1 FROM user_blocks ub WHERE ub.owner_id = c.owner_id AND ub.blocked_user_id = ?)
                  AND (COALESCE(json_extract(c.settings_json, '$.isPublic'), 1) = 1
                       OR EXISTS(SELECT 1 FROM chat_members cm WHERE cm.chat_id = c.id AND cm.user_id = ?))""",
            (user["id"], user["id"]),
        ).fetchall()
        owner_ranks = {}
        for owner_id in {row["owner_id"] for row in rows if row["owner_id"]}:
            owner_ranks[owner_id] = self.channel_feed_owner_level_rank(con, owner_id, levels, current_time)
        ranked_rows = sorted(
            rows,
            key=lambda row: (
                -owner_ranks.get(row["owner_id"], -1),
                -max(int(row["latest_post_at"] or 0), int(row["activity_package_at"] or 0), int(row["star_purchase_at"] or 0)),
                -int(row["latest_post_at"] or 0),
                -int(row["updated_at"] or 0),
                row["id"],
            ),
        )
        page = ranked_rows[offset:offset + limit]
        return self.json({
            "ok": True,
            "channels": [chat_to_dict(row) for row in page],
            "nextOffset": offset + len(page),
            "hasMore": offset + len(page) < len(ranked_rows),
        })

    def my_reactions(self, con, user):
        reactions = []
        for row in con.execute(
            """SELECT mr.emoji, mr.created_at, m.id AS target_id, m.chat_id AS target_chat_id,
                      m.text AS target_text, m.media_type AS target_media_type, m.media_data AS target_media_data,
                      c.title AS target_title
               FROM message_reactions mr JOIN messages m ON m.id = mr.message_id JOIN chats c ON c.id = m.chat_id
                WHERE mr.user_id = ? ORDER BY mr.created_at DESC LIMIT 150""", (user["id"],)
        ).fetchall():
            reactions.append({"type": "message", "emoji": row["emoji"], "createdAt": row["created_at"], "targetId": row["target_id"], "chatId": row["target_chat_id"], "title": row["target_title"], "text": row["target_text"], "mediaType": row["target_media_type"], "mediaData": row["target_media_data"]})
        for row in con.execute(
            """SELECT pr.emoji, pr.created_at, p.id AS target_id, p.text AS target_text, u.name AS target_title
               FROM profile_post_reactions pr JOIN profile_posts p ON p.id = pr.post_id JOIN users u ON u.id = p.user_id
               WHERE pr.user_id = ? ORDER BY pr.created_at DESC LIMIT 150""", (user["id"],)
        ).fetchall():
            reactions.append({"type": "post", "emoji": row["emoji"], "createdAt": row["created_at"], "targetId": row["target_id"], "title": row["target_title"], "text": row["target_text"]})
        for row in con.execute(
            """SELECT sr.emoji, sr.created_at, s.id AS target_id, s.caption AS target_text, u.name AS target_title
               FROM story_reactions sr JOIN stories s ON s.id = sr.story_id JOIN users u ON u.id = s.user_id
               WHERE sr.user_id = ? ORDER BY sr.created_at DESC LIMIT 150""", (user["id"],)
        ).fetchall():
            reactions.append({"type": "story", "emoji": row["emoji"], "createdAt": row["created_at"], "targetId": row["target_id"], "title": row["target_title"], "text": row["target_text"]})
        reactions.sort(key=lambda item: item["createdAt"], reverse=True)
        return self.json({"ok": True, "reactions": reactions[:200]})

    def search_messages(self, con, user, query):
        text = " ".join((query.get("q", [""])[0] or "").split())
        chat_id = str(query.get("chatId", [""])[0] or "").strip()
        if len(text) < 2:
            raise ValueError("Введите не менее двух символов для поиска.")
        if len(text) > 120:
            raise ValueError("Поисковый запрос не должен быть длиннее 120 символов.")
        if chat_id and not self.has_chat_access(con, user["id"], chat_id):
            raise PermissionError("Нет доступа к этому диалогу.")
        rows = con.execute(
            """SELECT m.id, m.chat_id, m.text, m.media_type, m.created_at, c.title AS chat_title, c.type AS chat_type
               FROM messages m
               JOIN chats c ON c.id = m.chat_id
               WHERE m.deleted_by_admin = 0
                 AND m.text IS NOT NULL AND trim(m.text) != ''
                  AND casefold(m.text) LIKE ?
                 AND (? = '' OR m.chat_id = ?)
                 AND NOT EXISTS(SELECT 1 FROM hidden_messages hm WHERE hm.message_id = m.id AND hm.user_id = ?)
                 AND EXISTS(SELECT 1 FROM chat_members cm WHERE cm.chat_id = c.id AND cm.user_id = ?)
                 AND (c.type != 'secret' OR EXISTS(
                   SELECT 1 FROM secret_chat_unlocks scu WHERE scu.chat_id = c.id AND scu.user_id = ?
                 ))
               ORDER BY m.created_at DESC LIMIT 100""",
            (f"%{text.casefold()}%", chat_id, chat_id, user["id"], user["id"], user["id"]),
        ).fetchall()
        return self.json({"ok": True, "messages": [dict(row) for row in rows]})

    def has_chat_access(self, con, user_id, chat_id):
        return bool(con.execute(
            """SELECT 1 FROM chat_members cm JOIN chats c ON c.id = cm.chat_id
               WHERE cm.chat_id = ? AND cm.user_id = ?
                 AND NOT EXISTS(SELECT 1 FROM user_blocks ub WHERE ub.owner_id = c.owner_id AND ub.blocked_user_id = ?)
                 AND NOT (c.type = 'direct' AND EXISTS(SELECT 1 FROM chat_members other WHERE other.chat_id = c.id AND other.user_id != ? AND EXISTS(SELECT 1 FROM user_blocks ub WHERE (ub.owner_id = ? AND ub.blocked_user_id = other.user_id) OR (ub.owner_id = other.user_id AND ub.blocked_user_id = ?))))
                 AND (c.type != 'secret' OR EXISTS(SELECT 1 FROM secret_chat_unlocks scu WHERE scu.chat_id = c.id AND scu.user_id = ?))""",
            (chat_id, user_id, user_id, user_id, user_id, user_id, user_id),
        ).fetchone())

    def visible_chat_activities(self, con, chats, user_id):
        direct_chat_ids = {
            chat["id"] for chat in chats
            if chat["type"] == "direct" and self.has_chat_access(con, user_id, chat["id"])
        }
        now_monotonic = time.monotonic()
        activities = {}
        with chat_activities_lock:
            expired = [key for key, (_, expires_at) in chat_activities.items() if expires_at <= now_monotonic]
            for key in expired:
                chat_activities.pop(key, None)
            for (chat_id, sender_id), (activity, _) in chat_activities.items():
                if chat_id in direct_chat_ids and sender_id != user_id:
                    activities[chat_id] = activity
        return activities

    def chat_member_role(self, con, chat_id, user_id):
        row = con.execute(
            "SELECT role FROM chat_members WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id),
        ).fetchone()
        return row["role"] if row else None

    def can_manage_group_messages(self, con, user_id, chat_id):
        chat = con.execute("SELECT type FROM chats WHERE id = ?", (chat_id,)).fetchone()
        if not chat:
            return False
        role = self.chat_member_role(con, chat_id, user_id)
        if chat["type"] == "channel":
            return role in CHANNEL_MANAGER_ROLES
        return chat["type"] in {"group", "community"} and role in {"owner", "admin"}

    def effective_limits(self, con, user_id, level: dict) -> dict:
        limits = {**{key: 0 for key in LEVEL_LIMIT_KEYS}, **level.get("limits", {})}
        for row in con.execute("SELECT limits_json FROM personal_limit_rewards WHERE user_id = ?", (user_id,)).fetchall():
            reward_limits = loads(row["limits_json"], {})
            if not isinstance(reward_limits, dict):
                continue
            for key, value in reward_limits.items():
                if key not in LEVEL_LIMIT_KEYS:
                    continue
                personal_limit = int(value or 0)
                current_limit = int(limits.get(key, 0) or 0)
                if personal_limit and (not current_limit or personal_limit > current_limit):
                    limits[key] = personal_limit
        return limits

    def star_package_discount_percent(self, con, user_id) -> int:
        row = con.execute(
            "SELECT MAX(discount_percent) AS discount_percent FROM personal_star_package_discounts WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        return int(row["discount_percent"] or 0) if row else 0

    def apply_reward_benefits(self, con, user_id, source_type, source_id, title, reward):
        premium_days = int(reward.get("premiumDays", 0) or 0)
        if premium_days:
            user = con.execute("SELECT premium_until FROM users WHERE id = ?", (user_id,)).fetchone()
            premium_start = max(now(), int(user["premium_until"] or 0) if user else 0)
            con.execute("UPDATE users SET premium_until = ? WHERE id = ?", (premium_start + premium_days * 86400, user_id))
        limits = reward.get("limits", {}) if isinstance(reward, dict) else {}
        if limits:
            con.execute(
                "INSERT OR REPLACE INTO personal_limit_rewards(user_id,source_type,source_id,limits_json,created_at) VALUES (?,?,?,?,?)",
                (user_id, source_type, source_id, dumps(limits), now()),
            )
        discount_percent = int(reward.get("starPackageDiscountPercent", 0) or 0)
        if discount_percent:
            con.execute(
                "INSERT OR REPLACE INTO personal_star_package_discounts(user_id,source_type,source_id,discount_percent,created_at) VALUES (?,?,?,?,?)",
                (user_id, source_type, source_id, discount_percent, now()),
            )
        recurring_stars = int(reward.get("recurringStars", 0) or 0)
        if recurring_stars:
            interval_seconds = int(reward["recurringIntervalDays"]) * 86400
            ends_at = now() + int(reward["recurringDurationDays"]) * 86400
            con.execute(
                """INSERT OR REPLACE INTO recurring_star_rewards(user_id,source_type,source_id,title,stars,interval_seconds,ends_at,next_credit_at,created_at)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (user_id, source_type, source_id, title, recurring_stars, interval_seconds, ends_at, now() + interval_seconds, now()),
            )

    def process_recurring_star_rewards(self, con):
        current = now()
        rewards = con.execute("SELECT * FROM recurring_star_rewards WHERE next_credit_at <= ? ORDER BY next_credit_at LIMIT 100", (current,)).fetchall()
        for reward in rewards:
            if reward["next_credit_at"] > reward["ends_at"]:
                con.execute("DELETE FROM recurring_star_rewards WHERE user_id = ? AND source_type = ? AND source_id = ?", (reward["user_id"], reward["source_type"], reward["source_id"]))
                continue
            try:
                self.credit_stars(con, reward["user_id"], reward["stars"])
            except ValueError:
                pass
            else:
                self.record_star_transaction(con, reward["user_id"], reward["stars"], "recurring_reward", f"Периодическая награда «{reward['title']}»")
            next_credit_at = int(reward["next_credit_at"]) + int(reward["interval_seconds"])
            if next_credit_at > reward["ends_at"]:
                con.execute("DELETE FROM recurring_star_rewards WHERE user_id = ? AND source_type = ? AND source_id = ?", (reward["user_id"], reward["source_type"], reward["source_id"]))
            else:
                con.execute("UPDATE recurring_star_rewards SET next_credit_at = ? WHERE user_id = ? AND source_type = ? AND source_id = ?", (next_credit_at, reward["user_id"], reward["source_type"], reward["source_id"]))

    def enforce_autopost_source_limit(self, con, user_id, channel_id):
        limits = self.account_level_data(con, user_id).get("limits", {})
        total_limit = int(limits.get("autopostSourcesTotal", 0) or 0)
        channel_limit = int(limits.get("autopostSourcesPerChannel", 0) or 0)
        counts = con.execute(
            """SELECT
                   (SELECT count(*) FROM telegram_channel_links t JOIN chats c ON c.id = t.channel_id WHERE c.owner_id = ?) +
                   (SELECT count(*) FROM rss_channel_sources r JOIN chats c ON c.id = r.channel_id WHERE c.owner_id = ?) +
                   (SELECT count(*) FROM vk_channel_sources v JOIN chats c ON c.id = v.channel_id WHERE c.owner_id = ?) AS total,
                   (SELECT count(*) FROM telegram_channel_links WHERE channel_id = ?) +
                   (SELECT count(*) FROM rss_channel_sources WHERE channel_id = ?) +
                   (SELECT count(*) FROM vk_channel_sources WHERE channel_id = ?) AS channel_total""",
            (user_id, user_id, user_id, channel_id, channel_id, channel_id),
        ).fetchone()
        if total_limit and counts["total"] >= total_limit:
            raise ValueError(f"На вашем уровне доступно не более {total_limit} источников автопостинга.")
        if channel_limit and counts["channel_total"] >= channel_limit:
            raise ValueError(f"К одному каналу на вашем уровне можно подключить не более {channel_limit} источников автопостинга.")

    def credit_stars(self, con, user_id, amount):
        amount = nonnegative_int(amount, "amount")
        if not amount:
            return
        user = con.execute("SELECT stars FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            raise ValueError("Пользователь не найден.")
        maximum = int(self.account_level_data(con, user_id).get("limits", {}).get("maxStars", 0) or 0)
        if maximum and int(user["stars"]) + amount > maximum:
            raise ValueError(f"Баланс этого аккаунта ограничен {maximum} звёздами.")
        con.execute("UPDATE users SET stars = stars + ? WHERE id = ?", (amount, user_id))

    def enforce_join_limit(self, con, user_id, chat_type):
        limit_key = {"group": "groupsJoined", "community": "communitiesJoined", "channel": "channelsJoined"}[chat_type]
        limits = self.account_level_data(con, user_id).get("limits", {})
        maximum = int(limits.get(limit_key, 0) or 0)
        if not maximum:
            return
        joined = con.execute(
            """SELECT count(*) AS count FROM chat_members cm JOIN chats c ON c.id = cm.chat_id
               WHERE cm.user_id = ? AND c.type = ? AND c.owner_id != ?""",
            (user_id, chat_type, user_id),
        ).fetchone()["count"]
        if joined >= maximum:
            label = {"group": "групп", "community": "бесед", "channel": "каналов"}[chat_type]
            raise ValueError(f"На вашем уровне можно вступить не более чем в {maximum} {label}.")

    def enforce_message_limit(self, con, user_id):
        maximum = int(self.account_level_data(con, user_id).get("limits", {}).get("messagesPerDay", 0) or 0)
        if not maximum:
            return
        sent_today = con.execute(
            "SELECT count(*) AS count FROM messages WHERE sender_id = ? AND created_at >= ? AND forwarded_from IS NULL",
            (user_id, now() - 86400),
        ).fetchone()["count"]
        if sent_today >= maximum:
            raise ValueError(f"На вашем уровне можно отправлять до {maximum} сообщений в сутки.")

    def enforce_post_limit(self, con, user_id):
        maximum = int(self.account_level_data(con, user_id).get("limits", {}).get("postsPerDay", 0) or 0)
        if not maximum:
            return
        created_today = con.execute(
            """SELECT
                   (SELECT count(*) FROM profile_posts WHERE user_id = ? AND created_at >= ?) +
                   (SELECT count(*) FROM messages m JOIN chats c ON c.id = m.chat_id
                    WHERE m.sender_id = ? AND m.created_at >= ? AND c.type = 'channel' AND m.forwarded_from IS NULL) AS count""",
            (user_id, now() - 86400, user_id, now() - 86400),
        ).fetchone()["count"]
        if created_today >= maximum:
            raise ValueError(f"На вашем уровне можно публиковать до {maximum} постов в сутки.")

    def update_avatar(self, con, user, body):
        avatar = normalize_image_data(body.get("avatarData", ""), 1_800_000, "Аватар")
        previous = con.execute("SELECT avatar_data FROM users WHERE id = ?", (user["id"],)).fetchone()["avatar_data"]
        if previous and previous != avatar:
            con.execute("DELETE FROM avatar_history WHERE user_id = ? AND avatar_data = ?", (user["id"], previous))
            con.execute("INSERT INTO avatar_history(id,user_id,avatar_data,created_at) VALUES (?,?,?,?)", (uid("avatar"), user["id"], previous, now()))
            con.execute("""DELETE FROM avatar_history WHERE id IN (
                           SELECT id FROM avatar_history WHERE user_id = ?
                           ORDER BY created_at DESC, id DESC LIMIT -1 OFFSET 20
                         )""", (user["id"],))
        con.execute("UPDATE users SET avatar_data = ? WHERE id = ?", (avatar, user["id"]))
        return self.json({"ok": True})

    def update_profile_description(self, con, user, body):
        description = " ".join(str(body.get("description", "")).split())
        if len(description) > 1000:
            raise ValueError("Описание профиля не должно быть длиннее 1000 символов.")
        con.execute("UPDATE users SET profile_description = ? WHERE id = ?", (description, user["id"]))
        return self.json({"ok": True})

    def update_profile_channel_visibility(self, con, user, body):
        chat_id = str(body.get("chatId", "")).strip()
        hidden = body.get("hidden")
        if not isinstance(hidden, bool):
            raise ValueError("Некорректная настройка видимости канала.")
        chat = con.execute("SELECT settings_json FROM chats WHERE id = ? AND type = 'channel' AND owner_id = ?", (chat_id, user["id"])).fetchone()
        if not chat:
            raise ValueError("Канал не найден.")
        settings = loads(chat["settings_json"], {}) or {}
        settings["hideFromProfile"] = hidden
        con.execute("UPDATE chats SET settings_json = ?, updated_at = ? WHERE id = ?", (dumps(settings), now(), chat_id))
        return self.json({"ok": True})

    def set_user_block(self, con, user, body):
        target_id = str(body.get("userId", "")).strip()
        blocked = body.get("blocked")
        if target_id == user["id"] or not con.execute("SELECT 1 FROM users WHERE id = ?", (target_id,)).fetchone():
            raise ValueError("Пользователь не найден.")
        if not isinstance(blocked, bool):
            raise ValueError("Некорректная настройка блокировки.")
        if blocked:
            con.execute("INSERT OR IGNORE INTO user_blocks(owner_id,blocked_user_id,created_at) VALUES (?,?,?)", (user["id"], target_id, now()))
            con.execute("DELETE FROM chat_members WHERE user_id = ? AND chat_id IN (SELECT id FROM chats WHERE type = 'channel' AND owner_id = ?)", (target_id, user["id"]))
        else:
            con.execute("DELETE FROM user_blocks WHERE owner_id = ? AND blocked_user_id = ?", (user["id"], target_id))
        return self.json({"ok": True, "blocked": blocked})

    def create_profile_post(self, con, user, body):
        raise PermissionError("Публикации в профилях отключены.")
        text = str(body.get("text", "")).strip()
        media = str(body.get("mediaData", ""))
        if (not text and not media) or len(text) > 3000:
            raise ValueError("Пост должен содержать текст или фото, текст — до 3000 символов.")
        if media and (not media.startswith("data:image/") or len(media) > 3_500_000):
            raise ValueError("Фото поста должно быть изображением до 2,5 МБ.")
        self.enforce_post_limit(con, user["id"])
        con.execute("INSERT INTO profile_posts(id,user_id,text,media_data,created_at) VALUES (?,?,?,?,?)", (uid("post"), user["id"], text, media or None, now()))
        return self.json({"ok": True})

    def edit_profile_post(self, con, user, body):
        post_id = str(body.get("postId", "")).strip()
        text = str(body.get("text", "")).strip()
        if not post_id:
            raise ValueError("Публикация не найдена.")
        if len(text) > 3000:
            raise ValueError("Текст публикации — до 3000 символов.")
        post = con.execute("SELECT user_id, media_data FROM profile_posts WHERE id = ?", (post_id,)).fetchone()
        if not post:
            raise ValueError("Публикация не найдена.")
        if post["user_id"] != user["id"]:
            raise PermissionError("Можно редактировать только свои публикации.")
        if not text and not post["media_data"]:
            raise ValueError("Пост должен содержать текст или фото.")
        con.execute("UPDATE profile_posts SET text = ? WHERE id = ?", (text, post_id))
        return self.json({"ok": True})

    def delete_profile_post(self, con, user, body):
        post_id = str(body.get("postId", "")).strip()
        if not post_id:
            raise ValueError("Публикация не найдена.")
        post = con.execute("SELECT user_id FROM profile_posts WHERE id = ?", (post_id,)).fetchone()
        if not post:
            raise ValueError("Публикация не найдена.")
        if post["user_id"] != user["id"]:
            raise PermissionError("Можно удалять только свои публикации.")
        con.execute("DELETE FROM profile_posts WHERE id = ?", (post_id,))
        return self.json({"ok": True})

    def react_to_profile_post(self, con, user, body):
        post_id = str(body.get("postId", ""))
        emoji = str(body.get("emoji", ""))[:32]
        if not emoji:
            raise ValueError("Выберите реакцию.")
        post = con.execute("SELECT user_id, media_data FROM profile_posts WHERE id = ?", (post_id,)).fetchone()
        if not post:
            raise ValueError("Публикация не найдена.")
        author_id = post["user_id"]
        if author_id == user["id"]:
            raise ValueError("Нельзя отправить реакцию на свою публикацию.")
        if self.users_are_blocked(con, user["id"], author_id):
            raise PermissionError("Взаимодействие с заблокированным пользователем недоступно.")
        member_ids = sorted([user["id"], author_id])
        chat = con.execute(
            "SELECT c.id FROM chats c JOIN chat_members a ON a.chat_id = c.id JOIN chat_members b ON b.chat_id = c.id WHERE c.type = 'direct' AND a.user_id = ? AND b.user_id = ?",
            (member_ids[0], member_ids[1]),
        ).fetchone()
        if chat:
            chat_id = chat["id"]
        else:
            privacy_row = con.execute("SELECT direct_message_privacy FROM users WHERE id = ?", (author_id,)).fetchone()
            if privacy_row and privacy_row["direct_message_privacy"] != "everyone":
                raise PermissionError("Автор принимает новые сообщения только от людей из личных диалогов.")
            chat_id = uid("chat")
            con.execute("INSERT INTO chats(id,type,title,owner_id,created_at,updated_at) VALUES (?,?,?,?,?,?)", (chat_id, "direct", "Личный чат", user["id"], now(), now()))
            for member_id in member_ids:
                con.execute("INSERT INTO chat_members(chat_id,user_id,role,created_at) VALUES (?,?,?,?)", (chat_id, member_id, "member", now()))
        con.execute("DELETE FROM hidden_chats WHERE chat_id = ? AND user_id IN (?, ?)", (chat_id, user["id"], author_id))
        con.execute(
            "INSERT INTO messages(id,chat_id,sender_id,text,media_type,media_data,views,created_at) VALUES (?,?,?,?,?,?,?,?)",
            (uid("msg"), chat_id, user["id"], emoji, "photo" if post["media_data"] else None, post["media_data"], 1, now()),
        )
        con.execute("INSERT OR IGNORE INTO profile_post_reactions(post_id,user_id,emoji,created_at) VALUES (?,?,?,?)", (post_id, user["id"], emoji, now()))
        con.execute("UPDATE chats SET updated_at = ? WHERE id = ?", (now(), chat_id))
        return self.json({"ok": True, "chatId": chat_id})

    def create_story(self, con, user, body):
        raise PermissionError("Публикация историй отключена.")
        media = str(body.get("mediaData", ""))
        caption = str(body.get("caption", "")).strip()[:300]
        if not media.startswith("data:image/") or len(media) > 3_500_000:
            raise ValueError("Загрузите изображение истории до 2,5 МБ.")
        limits = self.account_level_data(con, user["id"]).get("limits", {})
        daily_limit = int(limits.get("storiesPerDay", 0) or 0)
        monthly_limit = int(limits.get("storiesPerMonth", 0) or 0)
        created_today = con.execute("SELECT count(*) AS count FROM stories WHERE user_id = ? AND created_at >= ?", (user["id"], now() - 86400)).fetchone()["count"]
        created_month = con.execute("SELECT count(*) AS count FROM stories WHERE user_id = ? AND created_at >= ?", (user["id"], now() - 30 * 86400)).fetchone()["count"]
        if daily_limit and created_today >= daily_limit:
            raise ValueError(f"На вашем уровне можно публиковать до {daily_limit} сторис в сутки.")
        if monthly_limit and created_month >= monthly_limit:
            raise ValueError(f"На вашем уровне можно публиковать до {monthly_limit} сторис за 30 дней.")
        con.execute("INSERT INTO stories(id,user_id,media_data,caption,created_at,expires_at,permanent) VALUES (?,?,?,?,?,?,0)", (uid("story"), user["id"], media, caption, now(), now() + 172800))
        return self.json({"ok": True})

    def story_to_dict(self, con, row, viewer_id):
        story = dict(row)
        own_story = story["user_id"] == viewer_id
        story["viewed"] = own_story or bool(con.execute("SELECT 1 FROM story_views WHERE story_id = ? AND user_id = ?", (story["id"], viewer_id)).fetchone())
        story["viewerCount"] = con.execute("SELECT count(*) AS count FROM story_views WHERE story_id = ?", (story["id"],)).fetchone()["count"] if own_story else None
        if own_story:
            story["viewers"] = []
            for viewer in con.execute(
                """SELECT u.*, sr.emoji AS story_reaction FROM story_views sv
                   JOIN users u ON u.id = sv.user_id
                   LEFT JOIN story_reactions sr ON sr.story_id = sv.story_id AND sr.user_id = sv.user_id
                   WHERE sv.story_id = ? ORDER BY sv.viewed_at DESC""", (story["id"],)
            ).fetchall():
                public = public_user(viewer)
                public["storyReaction"] = viewer["story_reaction"] or ""
                story["viewers"].append(public)
        else:
            story["viewers"] = []
        reaction = con.execute("SELECT emoji FROM story_reactions WHERE story_id = ? AND user_id = ?", (story["id"], viewer_id)).fetchone()
        story["myReaction"] = reaction["emoji"] if reaction else ""
        return story

    def view_story(self, con, user, body):
        story_id = body.get("storyId")
        story = con.execute(
            """SELECT * FROM stories
               WHERE id = ? AND (permanent = 1 OR expires_at > ?)
                 AND NOT EXISTS(SELECT 1 FROM hidden_story_authors hsa WHERE hsa.user_id = ? AND hsa.author_id = stories.user_id)
                 AND NOT EXISTS(SELECT 1 FROM story_privacy_blocks spb WHERE spb.owner_id = stories.user_id AND spb.blocked_user_id = ?)""",
            (story_id, now(), user["id"], user["id"]),
        ).fetchone()
        if not story:
            raise ValueError("Сторис больше недоступна.")
        if story["user_id"] != user["id"]:
            con.execute("INSERT OR IGNORE INTO story_views(story_id,user_id,viewed_at) VALUES (?,?,?)", (story_id, user["id"], now()))
        return self.json({"ok": True, "story": self.story_to_dict(con, story, user["id"])})

    def react_to_story(self, con, user, body):
        story_id = body.get("storyId")
        emoji = str(body.get("emoji", ""))[:32]
        story = con.execute("SELECT * FROM stories WHERE id = ? AND (permanent = 1 OR expires_at > ?)", (story_id, now())).fetchone()
        if not story or story["user_id"] == user["id"]:
            raise ValueError("Нельзя поставить реакцию на эту сторис.")
        if not emoji:
            con.execute("DELETE FROM story_reactions WHERE story_id = ? AND user_id = ?", (story_id, user["id"]))
        else:
            con.execute("INSERT OR REPLACE INTO story_reactions(story_id,user_id,emoji,created_at) VALUES (?,?,?,?)", (story_id, user["id"], emoji, now()))
        return self.json({"ok": True})

    def save_story_permanent(self, con, user, body):
        story_id = body.get("storyId")
        story = con.execute("SELECT * FROM stories WHERE id = ? AND user_id = ?", (story_id, user["id"])).fetchone()
        if not story:
            raise ValueError("История не найдена.")
        con.execute("UPDATE stories SET permanent = 1, expires_at = ? WHERE id = ?", (now() + 315360000, story_id))
        return self.json({"ok": True})

    def hide_story_author(self, con, user, body):
        author_id = str(body.get("authorId", ""))
        hidden = bool(body.get("hidden", True))
        if not author_id or author_id == user["id"]:
            raise ValueError("Нельзя скрыть эти сторис.")
        if hidden:
            con.execute("INSERT OR IGNORE INTO hidden_story_authors(user_id,author_id,created_at) VALUES (?,?,?)", (user["id"], author_id, now()))
        else:
            con.execute("DELETE FROM hidden_story_authors WHERE user_id = ? AND author_id = ?", (user["id"], author_id))
        return self.json({"ok": True})

    def update_story_privacy(self, con, user, body):
        target_id = str(body.get("userId", ""))
        hidden = bool(body.get("hidden", True))
        if not target_id or target_id == user["id"]:
            raise ValueError("Нельзя изменить видимость для этого пользователя.")
        if hidden:
            con.execute("INSERT OR IGNORE INTO story_privacy_blocks(owner_id,blocked_user_id,created_at) VALUES (?,?,?)", (user["id"], target_id, now()))
        else:
            con.execute("DELETE FROM story_privacy_blocks WHERE owner_id = ? AND blocked_user_id = ?", (user["id"], target_id))
        return self.json({"ok": True})

    def reply_to_story(self, con, user, body):
        story_id = body.get("storyId")
        text = str(body.get("text", "")).strip()[:1000]
        if not text:
            raise ValueError("Введите ответ на сторис.")
        story = con.execute(
            """SELECT * FROM stories
               WHERE id = ? AND user_id != ? AND (permanent = 1 OR expires_at > ?)
                 AND NOT EXISTS(SELECT 1 FROM story_privacy_blocks spb WHERE spb.owner_id = stories.user_id AND spb.blocked_user_id = ?)""",
            (story_id, user["id"], now(), user["id"]),
        ).fetchone()
        if not story:
            raise ValueError("Сторис больше недоступна.")
        owner = con.execute("SELECT name FROM users WHERE id = ?", (story["user_id"],)).fetchone()
        ids = sorted([user["id"], story["user_id"]])
        chat = con.execute(
            """SELECT c.* FROM chats c
               JOIN chat_members a ON a.chat_id = c.id
               JOIN chat_members b ON b.chat_id = c.id
               WHERE c.type = 'direct' AND a.user_id = ? AND b.user_id = ?""",
            (ids[0], ids[1]),
        ).fetchone()
        if not chat:
            chat_id = uid("chat")
            title = f"{user['name']} и {owner['name']}"
            con.execute(
                "INSERT INTO chats(id,type,title,description,owner_id,settings_json,subscriber_count,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (chat_id, "direct", title, "", user["id"], dumps({}), 2, now(), now()),
            )
            for member_id in ids:
                con.execute("INSERT INTO chat_members(chat_id,user_id,role,created_at) VALUES (?,?,?,?)", (chat_id, member_id, "member", now()))
        else:
            chat_id = chat["id"]
            con.execute("DELETE FROM hidden_chats WHERE chat_id = ? AND user_id IN (?, ?)", (chat_id, user["id"], story["user_id"]))
        message_text = f"Ответ на сторис #{story_id}\n{story['caption'] or 'Без подписи'}\n\n{text}"
        con.execute("INSERT INTO messages(id,chat_id,sender_id,text,media_type,media_data,views,created_at) VALUES (?,?,?,?,?,?,?,?)", (uid("msg"), chat_id, user["id"], message_text, "photo", story["media_data"], 1, now()))
        con.execute("UPDATE chats SET updated_at = ? WHERE id = ?", (now(), chat_id))
        return self.json({"ok": True, "chatId": chat_id})

    def share_story(self, con, user, body):
        story_id = str(body.get("storyId", ""))
        recipient_id = str(body.get("recipientId", ""))
        if not recipient_id or recipient_id == user["id"]:
            raise ValueError("Выберите другого пользователя.")
        story = con.execute("SELECT * FROM stories WHERE id = ? AND (permanent = 1 OR expires_at > ?)", (story_id, now())).fetchone()
        recipient = con.execute("SELECT * FROM users WHERE id = ?", (recipient_id,)).fetchone()
        if not story or not recipient:
            raise ValueError("Сторис или получатель не найдены.")
        ids = sorted([user["id"], recipient_id])
        chat = con.execute(
            """SELECT c.* FROM chats c
               JOIN chat_members a ON a.chat_id = c.id
               JOIN chat_members b ON b.chat_id = c.id
               WHERE c.type = 'direct' AND a.user_id = ? AND b.user_id = ?""",
            (ids[0], ids[1]),
        ).fetchone()
        if not chat:
            chat_id = uid("chat")
            con.execute("INSERT INTO chats(id,type,title,owner_id,created_at,updated_at) VALUES (?,?,?,?,?,?)", (chat_id, "direct", "Личный чат", user["id"], now(), now()))
            for member_id in ids:
                con.execute("INSERT INTO chat_members(chat_id,user_id,role,created_at) VALUES (?,?,?,?)", (chat_id, member_id, "member", now()))
        else:
            chat_id = chat["id"]
            con.execute("DELETE FROM hidden_chats WHERE chat_id = ? AND user_id IN (?, ?)", (chat_id, user["id"], recipient_id))
        owner = con.execute("SELECT name FROM users WHERE id = ?", (story["user_id"],)).fetchone()
        text = f"Сторис от {owner['name'] if owner else 'пользователя'}\n{story['caption'] or 'Без подписи'}"
        con.execute("INSERT INTO messages(id,chat_id,sender_id,text,media_type,media_data,views,created_at) VALUES (?,?,?,?,?,?,?,?)", (uid("msg"), chat_id, user["id"], text, "photo", story["media_data"], 1, now()))
        con.execute("UPDATE chats SET updated_at = ? WHERE id = ?", (now(), chat_id))
        return self.json({"ok": True, "chatId": chat_id})

    def create_chat(self, con, user, body):
        chat_type = body.get("type", "direct")
        if chat_type == "direct":
            other_id = body.get("userId")
            if not other_id or other_id == user["id"]:
                raise ValueError("Выберите другого пользователя.")
            if self.users_are_blocked(con, user["id"], other_id):
                raise PermissionError("Личный диалог недоступен: один из пользователей заблокировал другого.")
            ids = sorted([user["id"], other_id])
            existing = con.execute(
                "SELECT c.* FROM chats c JOIN chat_members a ON a.chat_id=c.id JOIN chat_members b ON b.chat_id=c.id WHERE c.type='direct' AND a.user_id=? AND b.user_id=?",
                (ids[0], ids[1]),
            ).fetchone()
            if existing:
                con.execute("DELETE FROM hidden_chats WHERE chat_id = ? AND user_id = ?", (existing["id"], user["id"]))
                return self.json({"ok": True, "chat": chat_to_dict(existing)})
            shared_channel = con.execute(
                """SELECT 1 FROM chat_members manager
                   JOIN chat_members subscriber ON subscriber.chat_id = manager.chat_id
                   JOIN chats channel ON channel.id = manager.chat_id
                   WHERE channel.type = 'channel'
                     AND manager.user_id = ? AND manager.role IN ('owner', 'admin', 'author')
                     AND subscriber.user_id = ? AND subscriber.role = 'member'
                   LIMIT 1""",
                (user["id"], other_id),
            ).fetchone()
            recipient = con.execute("SELECT direct_message_privacy FROM users WHERE id = ?", (other_id,)).fetchone()
            if not recipient:
                raise ValueError("Пользователь не найден.")
            privacy = recipient["direct_message_privacy"]
            allows_all_incoming = bool(con.execute(
                "SELECT 1 FROM ai_agent_tasks WHERE user_id = ? AND enabled = 1 AND scope = 'all_direct'",
                (other_id,),
            ).fetchone())
            if shared_channel and not allows_all_incoming:
                raise PermissionError("Администраторы канала не могут начинать личные диалоги с его подписчиками.")
            if privacy == "nobody" and not allows_all_incoming:
                raise PermissionError("Пользователь принимает новые сообщения только от тех, кому написал сам.")
            if privacy == "contacts" and not allows_all_incoming:
                raise PermissionError("Пользователь принимает новые сообщения только от людей из личных диалогов.")
            chat_id = uid("chat")
            con.execute("INSERT INTO chats(id,type,title,owner_id,created_at,updated_at) VALUES (?,?,?,?,?,?)", (chat_id, "direct", "Личный чат", user["id"], now(), now()))
            for member_id in ids:
                con.execute("INSERT INTO chat_members(chat_id,user_id,role,created_at) VALUES (?,?,?,?)", (chat_id, member_id, "member", now()))
            return self.json({"ok": True, "chat": chat_to_dict(con.execute("SELECT * FROM chats WHERE id=?", (chat_id,)).fetchone())})

        if chat_type == "secret":
            password = str(body.get("password", ""))
            if not re.fullmatch(r"\d{4}", password):
                raise ValueError("Пароль конфиденциального чата должен состоять из 4 цифр.")
            raw_member_ids = body.get("memberIds", [])
            if not isinstance(raw_member_ids, list):
                raise ValueError("Некорректный список участников.")
            member_ids = list(dict.fromkeys(str(member_id) for member_id in raw_member_ids if member_id and member_id != user["id"]))
            if not member_ids:
                raise ValueError("Добавьте хотя бы одного собеседника.")
            if len(member_ids) > 50:
                raise ValueError("В конфиденциальном чате может быть не более 50 приглашённых участников.")
            for member_id in member_ids:
                if not con.execute("SELECT 1 FROM users WHERE id = ?", (member_id,)).fetchone():
                    raise ValueError("Один из выбранных пользователей не найден.")
                is_direct_contact = con.execute(
                    """SELECT 1 FROM chats c
                       JOIN chat_members owner_member ON owner_member.chat_id = c.id
                       JOIN chat_members contact_member ON contact_member.chat_id = c.id
                       WHERE c.type = 'direct' AND owner_member.user_id = ? AND contact_member.user_id = ?
                       LIMIT 1""",
                    (user["id"], member_id),
                ).fetchone()
                if not is_direct_contact:
                    raise ValueError("Добавить можно только пользователя из ваших личных диалогов.")
            title = str(body.get("title", "")).strip() or "Скрытый чат"
            chat_id = uid("chat")
            con.execute(
                "INSERT INTO chats(id,type,title,description,owner_id,settings_json,subscriber_count,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (chat_id, "secret", title, "", user["id"], dumps({"showViews": True, "showSubscribers": False, "showReactions": True}), len(member_ids) + 1, now(), now()),
            )
            con.execute("INSERT INTO secret_chats(chat_id,password_hash,created_at) VALUES (?,?,?)", (chat_id, secret_password_hash(password), now()))
            for member_id in [user["id"], *member_ids]:
                con.execute("INSERT INTO chat_members(chat_id,user_id,role,created_at) VALUES (?,?,?,?)", (chat_id, member_id, "owner" if member_id == user["id"] else "member", now()))
            con.execute("INSERT INTO secret_chat_unlocks(chat_id,user_id,unlocked_at) VALUES (?,?,?)", (chat_id, user["id"], now()))
            secret_chat = con.execute("SELECT c.*, 0 AS pinned, 0 AS archived FROM chats c WHERE c.id = ?", (chat_id,)).fetchone()
            return self.json({"ok": True, "chat": chat_to_dict(secret_chat)})

        if chat_type not in ("community", "channel"):
            raise ValueError("Неизвестный тип чата.")
        limits = self.account_level_data(con, user["id"]).get("limits", {})
        limit_key = {"community": "communitiesCreated", "channel": "channelsCreated"}[chat_type]
        maximum = int(limits.get(limit_key, 0) or 0)
        if maximum:
            existing = con.execute("SELECT count(*) AS count FROM chats WHERE owner_id = ? AND type = ?", (user["id"], chat_type)).fetchone()["count"]
            if existing >= maximum:
                label = {"community": "бесед", "channel": "каналов"}[chat_type]
                raise ValueError(f"На вашем уровне доступно до {maximum} {label}.")
        if chat_type == "channel":
            title = str(body.get("title", "")).strip() or "Новый канал"
            settings = {"showViews": True, "showSubscribers": True, "showReactions": True, "commentsEnabled": True, "isPublic": True, "joinApprovalRequired": False, "protectContent": False}
            chat_id = uid("chat")
            con.execute(
                "INSERT INTO chats(id,type,title,description,invite_code,owner_id,settings_json,subscriber_count,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (chat_id, "channel", title, str(body.get("description", "")), secrets.token_urlsafe(12), user["id"], dumps(settings), 1, now(), now()),
            )
            con.execute("INSERT INTO chat_members(chat_id,user_id,role,created_at) VALUES (?,?,?,?)", (chat_id, user["id"], "owner", now()))
            default_package = con.execute("SELECT * FROM demo_activity_packages WHERE apply_to_new_channels = 1 LIMIT 1").fetchone()
            if default_package and account_level_available_for_user(con, user["id"], default_package["required_account_level_id"]):
                current = now()
                con.execute(
                    """INSERT INTO demo_activity_subscriptions(id,package_id,channel_id,starts_at,ends_at,auto_renew,created_at)
                       VALUES (?,?,?,?,?,?,?)""",
                    (uid("demosubscription"), default_package["id"], chat_id, current, current + max(1, default_package["duration_days"]) * 86400, 0, current),
                )
            return self.json({"ok": True, "chat": chat_to_dict(con.execute("SELECT * FROM chats WHERE id=?", (chat_id,)).fetchone())})
        title = str(body.get("title", "")).strip() or "Новый чат"
        settings = {"showViews": True, "showSubscribers": True, "showReactions": True, "inviteLinkEnabled": True}
        chat_id = uid("chat")
        con.execute(
            "INSERT INTO chats(id,type,title,description,invite_code,owner_id,settings_json,subscriber_count,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (chat_id, chat_type, title, str(body.get("description", "")), secrets.token_urlsafe(12), user["id"], dumps(settings), 1, now(), now()),
        )
        con.execute("INSERT INTO chat_members(chat_id,user_id,role,created_at) VALUES (?,?,?,?)", (chat_id, user["id"], "owner", now()))
        return self.json({"ok": True, "chat": chat_to_dict(con.execute("SELECT * FROM chats WHERE id=?", (chat_id,)).fetchone())})

    def unlock_secret_chats(self, con, user, password):
        password = str(password or "")
        if not re.fullmatch(r"\d{4}", password):
            raise ValueError("Введите пароль из 4 цифр.")
        rows = con.execute(
            """SELECT sc.chat_id FROM secret_chats sc
               JOIN chat_members cm ON cm.chat_id = sc.chat_id
               WHERE cm.user_id = ? AND sc.password_hash = ?""",
            (user["id"], secret_password_hash(password)),
        ).fetchall()
        if not rows:
            raise ValueError("Скрытых чатов с таким паролем не найдено.")
        for row in rows:
            con.execute("INSERT OR REPLACE INTO secret_chat_unlocks(chat_id,user_id,unlocked_at) VALUES (?,?,?)", (row["chat_id"], user["id"], now()))
        return self.json({"ok": True, "count": len(rows), "chatIds": [row["chat_id"] for row in rows]})

    def join_chat(self, con, user, chat_id):
        chat = con.execute("SELECT type, owner_id, settings_json FROM chats WHERE id = ?", (chat_id,)).fetchone()
        if not chat or chat["type"] not in {"group", "community", "channel"}:
            raise ValueError("Не выбран чат.")
        if chat["type"] == "channel" and self.users_are_blocked(con, user["id"], chat["owner_id"]):
            raise PermissionError("Этот канал недоступен.")
        already_joined = con.execute("SELECT 1 FROM chat_members WHERE chat_id = ? AND user_id = ?", (chat_id, user["id"])).fetchone()
        settings = loads(chat["settings_json"], {}) or {}
        if chat["type"] == "channel" and settings.get("joinApprovalRequired", False) and not already_joined and chat["owner_id"] != user["id"]:
            con.execute("""INSERT INTO channel_join_requests(channel_id,user_id,status,created_at,resolved_at,resolved_by) VALUES (?,?,'pending',?,NULL,NULL)
                ON CONFLICT(channel_id,user_id) DO UPDATE SET status='pending', created_at=excluded.created_at, resolved_at=NULL, resolved_by=NULL""", (chat_id, user["id"], now()))
            return self.json({"ok": True, "requested": True})
        if not already_joined and chat["owner_id"] != user["id"]:
            self.enforce_join_limit(con, user["id"], chat["type"])
        con.execute("INSERT OR IGNORE INTO chat_members(chat_id,user_id,role,created_at) VALUES (?,?,?,?)", (chat_id, user["id"], "member", now()))
        con.execute("DELETE FROM hidden_chats WHERE chat_id = ? AND user_id = ?", (chat_id, user["id"]))
        con.execute("UPDATE chats SET subscriber_count = (SELECT count(*) FROM chat_members WHERE chat_id = ?), updated_at = ? WHERE id = ?", (chat_id, now(), chat_id))
        return self.json({"ok": True, "chatId": chat_id})

    def join_chat_by_invite(self, con, user, code):
        chat = con.execute("SELECT id, type, settings_json FROM chats WHERE invite_code = ?", (str(code or ""),)).fetchone()
        if not chat or chat["type"] not in {"group", "community", "channel"}:
            raise ValueError("Ссылка-приглашение недействительна.")
        if chat["type"] in {"group", "community"} and not loads(chat["settings_json"], {}).get("inviteLinkEnabled", True):
            raise PermissionError("Владелец группы отключил публичную ссылку-приглашение.")
        return self.join_chat(con, user, chat["id"])

    def channel_join_requests(self, con, user):
        rows = con.execute("""SELECT r.channel_id, r.user_id, r.created_at, u.name AS user_name, u.username
            FROM channel_join_requests r JOIN users u ON u.id = r.user_id
            WHERE r.status = 'pending' AND EXISTS(SELECT 1 FROM chat_members cm WHERE cm.chat_id = r.channel_id AND cm.user_id = ? AND cm.role IN ('owner', 'admin', 'author'))
            ORDER BY r.created_at""", (user["id"],)).fetchall()
        return self.json({"ok": True, "requests": [{"channelId": row["channel_id"], "userId": row["user_id"], "userName": row["user_name"], "username": row["username"], "createdAt": row["created_at"]} for row in rows]})

    def resolve_channel_join_request(self, con, user, body):
        channel_id, user_id, decision = str(body.get("channelId", "")), str(body.get("userId", "")), str(body.get("decision", ""))
        if decision not in {"approve", "reject"}:
            raise ValueError("Выберите решение по заявке.")
        if self.chat_member_role(con, channel_id, user["id"]) not in CHANNEL_MANAGER_ROLES:
            raise PermissionError("Одобрять заявки могут только создатель и администраторы канала.")
        if decision == "approve":
            owner = con.execute("SELECT owner_id FROM chats WHERE id = ?", (channel_id,)).fetchone()
            if owner and self.users_are_blocked(con, owner["owner_id"], user_id):
                raise PermissionError("Пользователь заблокирован владельцем канала.")
            self.enforce_join_limit(con, user_id, "channel")
            con.execute("INSERT OR IGNORE INTO chat_members(chat_id,user_id,role,created_at) VALUES (?,?,?,?)", (channel_id, user_id, "member", now()))
            con.execute("DELETE FROM hidden_chats WHERE chat_id = ? AND user_id = ?", (channel_id, user_id))
            con.execute("UPDATE chats SET subscriber_count=(SELECT count(*) FROM chat_members WHERE chat_id=?), updated_at=? WHERE id=?", (channel_id, now(), channel_id))
        updated = con.execute("UPDATE channel_join_requests SET status=?, resolved_at=?, resolved_by=? WHERE channel_id=? AND user_id=? AND status='pending'", ("approved" if decision == "approve" else "rejected", now(), user["id"], channel_id, user_id)).rowcount
        if not updated:
            raise ValueError("Эта заявка уже обработана.")
        return self.json({"ok": True, "decision": decision})

    def add_chat_member(self, con, user, body):
        chat_id, user_id = body.get("chatId"), body.get("userId")
        chat = con.execute("SELECT type, owner_id FROM chats WHERE id = ?", (chat_id,)).fetchone()
        if not chat or chat["type"] not in {"group", "community", "secret", "channel"}:
            raise ValueError("Участников можно добавлять только в группу, беседу, канал или скрытый чат.")
        if chat["owner_id"] != user["id"]:
            raise PermissionError("Добавлять участников может только создатель чата.")
        if not con.execute("SELECT 1 FROM users WHERE id = ?", (user_id,)).fetchone():
            raise ValueError("Пользователь не найден.")
        invite_privacy = con.execute("SELECT group_invite_privacy FROM users WHERE id = ?", (user_id,)).fetchone()["group_invite_privacy"]
        if invite_privacy == "nobody":
            raise PermissionError("Пользователь запретил добавлять себя в группы.")
        is_direct_contact = con.execute(
            """SELECT 1 FROM chats c
               JOIN chat_members inviter ON inviter.chat_id = c.id
               JOIN chat_members candidate ON candidate.chat_id = c.id
               WHERE c.type = 'direct' AND inviter.user_id = ? AND candidate.user_id = ?
               LIMIT 1""",
            (user["id"], user_id),
        ).fetchone()
        if invite_privacy == "contacts" and not is_direct_contact:
            raise PermissionError("Пользователь разрешил добавление только контактам.")
        already_joined = con.execute("SELECT 1 FROM chat_members WHERE chat_id = ? AND user_id = ?", (chat_id, user_id)).fetchone()
        if not already_joined and chat["type"] in {"group", "community", "channel"} and chat["owner_id"] != user_id:
            self.enforce_join_limit(con, user_id, chat["type"])
        added = con.execute("INSERT OR IGNORE INTO chat_members(chat_id,user_id,role,created_at) VALUES (?,?,?,?)", (chat_id, user_id, "member", now())).rowcount
        if added:
            invited = con.execute("SELECT name FROM users WHERE id = ?", (user_id,)).fetchone()
            chat_label = "скрытый чат" if chat["type"] == "secret" else "канал" if chat["type"] == "channel" else "беседу"
            con.execute(
                "INSERT INTO messages(id,chat_id,sender_id,text,media_type,views,created_at) VALUES (?,?,?,?,?,?,?)",
                (uid("msg"), chat_id, user["id"], f"{user['name']} пригласил(а) {invited['name']} в {chat_label}", "system", 1, now()),
            )
        con.execute("UPDATE chats SET subscriber_count = (SELECT count(*) FROM chat_members WHERE chat_id = ?) WHERE id = ?", (chat_id, chat_id))
        return self.json({"ok": True})

    def update_group_chat(self, con, user, body):
        chat_id = body.get("chatId")
        chat = con.execute("SELECT type, owner_id, settings_json FROM chats WHERE id = ?", (chat_id,)).fetchone()
        if not chat or chat["type"] not in {"group", "community", "channel"}:
            raise ValueError("Изменить можно только группу, беседу или канал.")
        if chat["owner_id"] != user["id"]:
            raise PermissionError("Изменять профиль и настройки может только создатель.")
        title = str(body.get("title", "")).strip()
        description = str(body.get("description", "")).strip()
        avatar = str(body.get("avatarData", "") or "")
        if not title or len(title) > 120:
            raise ValueError("Название должно содержать от 1 до 120 символов.")
        if len(description) > 1000:
            raise ValueError("Описание должно быть не длиннее 1000 символов.")
        if avatar and (not avatar.startswith("data:image/") or len(avatar) > 2_500_000):
            raise ValueError("Загрузите изображение до 1,8 МБ в формате PNG, JPG или WebP.")
        settings = loads(chat["settings_json"], {})
        if chat["type"] == "channel":
            for key in ("showViews", "showSubscribers", "showReactions", "commentsEnabled", "isPublic", "joinApprovalRequired", "protectContent"):
                if key in body:
                    settings[key] = bool(body[key])
            if settings.get("joinApprovalRequired", False):
                settings["isPublic"] = False
            package_gifts = body.get("buyerGiftStarsByPackage", settings.get("buyerGiftStarsByPackage", {}))
            if not isinstance(package_gifts, dict):
                raise ValueError("Некорректные настройки подарков покупателю.")
            available_package_ids = {package["id"] for package in yookassa_star_packages(con)}
            settings["buyerGiftStarsByPackage"] = {
                package_id: nonnegative_int(gift, "buyerGiftStars", 100_000)
                for package_id, gift in package_gifts.items()
                if package_id in available_package_ids
            }
            buyer_message = str(body.get("buyerPurchaseMessage", settings.get("buyerPurchaseMessage", ""))).strip()
            if len(buyer_message) > 500:
                raise ValueError("Сообщение покупателю должно быть не длиннее 500 символов.")
            settings["buyerPurchaseMessage"] = buyer_message
        elif chat["type"] in {"group", "community"} and "inviteLinkEnabled" in body:
            settings["inviteLinkEnabled"] = bool(body["inviteLinkEnabled"])
        con.execute("UPDATE chats SET title = ?, description = ?, avatar_data = ?, settings_json = ?, updated_at = ? WHERE id = ?", (title, description, avatar or None, dumps(settings), now(), chat_id))
        return self.json({"ok": True})

    def update_chat_member_role(self, con, user, body):
        chat_id, user_id = body.get("chatId"), body.get("userId")
        role = str(body.get("role", ""))
        chat = con.execute("SELECT type, owner_id FROM chats WHERE id = ?", (chat_id,)).fetchone()
        if not chat or chat["type"] not in {"group", "community", "channel"}:
            raise ValueError("Роли доступны только в группе, беседе или канале.")
        if chat["owner_id"] != user["id"]:
            raise PermissionError("Назначать администраторов может только создатель беседы.")
        if user_id == chat["owner_id"]:
            raise ValueError("Нельзя изменить роль создателя беседы.")
        allowed_roles = {"member", "admin"}
        if role not in allowed_roles:
            raise ValueError("Выберите допустимую роль участника.")
        if not con.execute("SELECT 1 FROM chat_members WHERE chat_id = ? AND user_id = ?", (chat_id, user_id)).fetchone():
            raise ValueError("Пользователь не состоит в беседе.")
        con.execute("UPDATE chat_members SET role = ? WHERE chat_id = ? AND user_id = ?", (role, chat_id, user_id))
        return self.json({"ok": True})

    def remove_chat_member(self, con, user, body):
        chat_id, user_id = body.get("chatId"), body.get("userId")
        chat = con.execute("SELECT type, owner_id FROM chats WHERE id = ?", (chat_id,)).fetchone()
        if not chat or chat["type"] not in {"group", "community", "channel"}:
            raise ValueError("Удалять участников можно только из группы, беседы или канала.")
        actor_role = self.chat_member_role(con, chat_id, user["id"])
        target_role = self.chat_member_role(con, chat_id, user_id)
        if actor_role not in ({"owner", "admin", "author"} if chat["type"] == "channel" else {"owner", "admin"}):
            raise PermissionError("Удалять участников могут только создатель и администраторы.")
        if not target_role:
            raise ValueError("Пользователь не состоит в беседе.")
        if user_id == chat["owner_id"]:
            raise PermissionError("Нельзя удалить создателя беседы.")
        if actor_role in {"admin", "author"} and target_role != "member":
            raise PermissionError("Администратор может удалить только обычного участника.")
        con.execute("DELETE FROM chat_members WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
        con.execute("DELETE FROM pinned_chats WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
        con.execute("UPDATE chats SET subscriber_count = (SELECT count(*) FROM chat_members WHERE chat_id = ?), updated_at = ? WHERE id = ?", (chat_id, now(), chat_id))
        return self.json({"ok": True})

    def leave_chat(self, con, user, chat_id):
        chat = con.execute("SELECT id, type, owner_id FROM chats WHERE id = ?", (chat_id,)).fetchone()
        if not chat or chat["type"] not in {"group", "community", "channel"}:
            raise ValueError("Выйти можно только из группы, беседы или канала.")
        if not con.execute("SELECT 1 FROM chat_members WHERE chat_id = ? AND user_id = ?", (chat_id, user["id"])).fetchone():
            raise PermissionError("Вы не состоите в этой беседе.")
        con.execute("DELETE FROM chat_members WHERE chat_id = ? AND user_id = ?", (chat_id, user["id"]))
        if chat["owner_id"] == user["id"]:
            next_owner = con.execute(
                "SELECT user_id FROM chat_members WHERE chat_id = ? ORDER BY created_at, user_id LIMIT 1", (chat_id,)
            ).fetchone()
            if next_owner:
                con.execute("UPDATE chats SET owner_id = ? WHERE id = ?", (next_owner["user_id"], chat_id))
                con.execute("UPDATE chat_members SET role = 'owner' WHERE chat_id = ? AND user_id = ?", (chat_id, next_owner["user_id"]))
            else:
                con.execute("UPDATE chats SET owner_id = NULL WHERE id = ?", (chat_id,))
        con.execute("DELETE FROM pinned_chats WHERE chat_id = ? AND user_id = ?", (chat_id, user["id"]))
        con.execute("UPDATE chats SET subscriber_count = (SELECT count(*) FROM chat_members WHERE chat_id = ?), updated_at = ? WHERE id = ?", (chat_id, now(), chat_id))
        return self.json({"ok": True})

    def toggle_chat_pin(self, con, user, chat_id):
        if not chat_id or not self.has_chat_access(con, user["id"], chat_id):
            raise PermissionError()
        pinned = con.execute("SELECT 1 FROM pinned_chats WHERE chat_id = ? AND user_id = ?", (chat_id, user["id"])).fetchone()
        if pinned:
            con.execute("DELETE FROM pinned_chats WHERE chat_id = ? AND user_id = ?", (chat_id, user["id"]))
        else:
            con.execute("INSERT INTO pinned_chats(chat_id,user_id,pinned_at) VALUES (?,?,?)", (chat_id, user["id"], now()))
        return self.json({"ok": True, "pinned": not bool(pinned)})

    def toggle_chat_archive(self, con, user, chat_id, archived):
        if not chat_id or not self.has_chat_access(con, user["id"], chat_id):
            raise PermissionError()
        if archived:
            con.execute("INSERT OR REPLACE INTO archived_chats(chat_id,user_id,archived_at) VALUES (?,?,?)", (chat_id, user["id"], now()))
            con.execute("DELETE FROM pinned_chats WHERE chat_id = ? AND user_id = ?", (chat_id, user["id"]))
        else:
            con.execute("DELETE FROM archived_chats WHERE chat_id = ? AND user_id = ?", (chat_id, user["id"]))
        return self.json({"ok": True, "archived": bool(archived)})

    def delete_chat(self, con, user, chat_id, scope):
        chat = con.execute("SELECT id, owner_id FROM chats WHERE id = ?", (chat_id,)).fetchone()
        if not chat or not self.has_chat_access(con, user["id"], chat_id):
            raise PermissionError()
        if scope == "me":
            con.execute("INSERT OR IGNORE INTO hidden_chats(chat_id,user_id,created_at) VALUES (?,?,?)", (chat_id, user["id"], now()))
            con.execute("DELETE FROM archived_chats WHERE chat_id = ? AND user_id = ?", (chat_id, user["id"]))
            con.execute("DELETE FROM pinned_chats WHERE chat_id = ? AND user_id = ?", (chat_id, user["id"]))
            return self.json({"ok": True})
        if scope == "everyone":
            if chat["owner_id"] != user["id"]:
                raise PermissionError("Удалить диалог у всех может только его создатель.")
            con.execute("DELETE FROM chats WHERE id = ?", (chat_id,))
            return self.json({"ok": True})
        raise ValueError("Неизвестный вариант удаления.")

    def prepare_message_media_upload(self, con, user, body):
        if not s3_is_configured():
            raise ValueError("Загрузка больших файлов скоро будет доступна. Повторите попытку через несколько минут.")
        chat_id = str(body.get("chatId", "")).strip()
        media_type = str(body.get("mediaType", "")).strip()
        file_name = str(body.get("fileName", "")).strip()[:240]
        content_type = str(body.get("contentType", "")).strip().lower().split(";", 1)[0]
        try:
            size_bytes = int(body.get("sizeBytes", 0) or 0)
        except (TypeError, ValueError):
            size_bytes = 0
        allowed_content_types = {
            "photo": {"image/png", "image/jpeg", "image/webp"},
            "video": {"video/mp4", "video/webm", "video/quicktime"},
            "document": {
                "application/pdf", "text/plain", "application/msword",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            },
        }
        if media_type not in allowed_content_types or content_type not in allowed_content_types[media_type]:
            raise ValueError("Этот тип файла не поддерживается.")
        if not 0 < size_bytes <= 25_000_000:
            raise ValueError("Размер вложения не должен превышать 25 МБ.")
        if media_type == "document" and not file_name:
            raise ValueError("Не удалось определить имя документа.")
        if not self.has_chat_access(con, user["id"], chat_id):
            raise PermissionError()
        chat = con.execute("SELECT type FROM chats WHERE id = ?", (chat_id,)).fetchone()
        if not chat:
            raise ValueError("Чат не найден.")
        if chat["type"] == "channel" and self.chat_member_role(con, chat_id, user["id"]) not in CHANNEL_MANAGER_ROLES:
            raise PermissionError("Публиковать в канале могут только создатель и назначенные администраторы.")
        extension = mimetypes.guess_extension(content_type, strict=False) or ""
        if content_type == "video/quicktime":
            extension = ".mov"
        key = f"messages/{chat_id}/{uid('media')}{extension}"
        expires_at = now() + 900
        con.execute("DELETE FROM media_uploads WHERE expires_at < ?", (now(),))
        con.execute(
            "INSERT INTO media_uploads(key,user_id,chat_id,media_type,file_name,content_type,size_bytes,expires_at,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (key, user["id"], chat_id, media_type, file_name, content_type, size_bytes, expires_at, now()),
        )
        upload_url, upload_headers = s3_presigned_url("PUT", key, expires_in=900, content_type=content_type)
        return self.json({"ok": True, "mediaKey": key, "uploadUrl": upload_url, "uploadHeaders": upload_headers, "expiresAt": expires_at})

    def add_message(self, con, user, body):
        chat_id = body.get("chatId")
        text = str(body.get("text", "")).strip()
        media_type = str(body.get("mediaType", "")).strip() or None
        media_data = str(body.get("mediaData", "")) or None
        raw_circle_preview_data = body.get("circlePreviewData", "")
        media_key = str(body.get("mediaKey", "")).strip()
        raw_voice_waveform = body.get("voiceWaveform", [])
        profile_user_id = str(body.get("profileUserId", "")).strip() or None
        file_name = str(body.get("fileName", "")).strip()[:240]
        reply_to_id = str(body.get("replyToId", "")).strip() or None
        allowed_media = {None, "photo", "video", "voice", "circle", "document"}
        if media_type not in allowed_media:
            raise ValueError("Этот тип вложения не поддерживается.")
        if raw_circle_preview_data and media_type != "circle":
            raise ValueError("Кадр предпросмотра можно передать только для видеокружка.")
        circle_preview_data = normalize_image_data(raw_circle_preview_data, CIRCLE_PREVIEW_MAX_BYTES, "Кадр видеокружка") if raw_circle_preview_data else None
        if not isinstance(raw_voice_waveform, list):
            raise ValueError("Некорректные данные голосового сообщения.")
        voice_waveform = [max(0, min(100, int(value))) for value in raw_voice_waveform[:64] if isinstance(value, (int, float))] if media_type == "voice" else []
        if not text and not media_data and not media_key and not profile_user_id:
            raise ValueError("Введите сообщение или прикрепите файл.")
        if profile_user_id and not con.execute("SELECT 1 FROM users WHERE id = ?", (profile_user_id,)).fetchone():
            raise ValueError("Профиль для отправки не найден.")
        if media_data:
            expected = {"photo": "data:image/", "video": "data:video/", "voice": "data:audio/", "circle": "data:video/", "document": "data:"}.get(media_type)
            if not expected or not media_data.startswith(expected) or len(media_data) > 5_000_000:
                raise ValueError("Файл слишком большой или неподходящего типа.")
            if media_type == "document" and not file_name:
                raise ValueError("Не удалось определить имя документа.")
            if media_type == "document" and not media_data.startswith(("data:application/pdf;", "data:text/plain;", "data:application/msword;", "data:application/vnd.openxmlformats-officedocument.wordprocessingml.document;")):
                raise ValueError("Можно прикрепить PDF, TXT, DOC или DOCX.")
        if not self.has_chat_access(con, user["id"], chat_id):
            raise PermissionError()
        chat = con.execute("SELECT type, owner_id, settings_json FROM chats WHERE id = ?", (chat_id,)).fetchone()
        if chat and chat["type"] == "direct":
            counterpart = con.execute(
                "SELECT user_id FROM chat_members WHERE chat_id = ? AND user_id != ?", (chat_id, user["id"])
            ).fetchone()
            if counterpart and self.users_are_blocked(con, user["id"], counterpart["user_id"]):
                raise PermissionError("Нельзя отправить сообщение заблокированному пользователю.")
            protected_subscriber = counterpart and con.execute(
                """SELECT 1 FROM chat_members manager
                   JOIN chat_members subscriber ON subscriber.chat_id = manager.chat_id
                   JOIN chats channel ON channel.id = manager.chat_id
                   WHERE channel.type = 'channel'
                     AND manager.user_id = ? AND manager.role IN ('owner', 'admin', 'author')
                     AND subscriber.user_id = ? AND subscriber.role = 'member'
                   LIMIT 1""",
                (user["id"], counterpart["user_id"]),
            ).fetchone()
            allows_all_incoming = counterpart and bool(con.execute(
                "SELECT 1 FROM ai_agent_tasks WHERE user_id = ? AND enabled = 1 AND scope = 'all_direct'",
                (counterpart["user_id"],),
            ).fetchone())
            if protected_subscriber and not allows_all_incoming:
                raise PermissionError("Администраторы канала не могут писать его подписчикам в личных диалогах.")
        if chat and chat["type"] == "channel" and self.chat_member_role(con, chat_id, user["id"]) not in CHANNEL_MANAGER_ROLES:
            raise PermissionError("Публиковать в канале могут только создатель и назначенные администраторы.")
        if reply_to_id and not con.execute("SELECT 1 FROM messages WHERE id = ? AND chat_id = ?", (reply_to_id, chat_id)).fetchone():
            raise ValueError("Сообщение для ответа не найдено.")
        if chat and chat["type"] == "channel":
            enforce_channel_post_limit(con, chat_id)
        self.enforce_message_limit(con, user["id"])
        msg_id = uid("msg")
        if media_key:
            if media_data:
                raise ValueError("Передайте либо файл, либо ключ S3, но не оба сразу.")
            upload = con.execute(
                "SELECT * FROM media_uploads WHERE key = ? AND user_id = ? AND chat_id = ? AND expires_at >= ?",
                (media_key, user["id"], chat_id, now()),
            ).fetchone()
            if not upload or upload["media_type"] != media_type:
                raise ValueError("Ссылка на загрузку недействительна. Выберите файл ещё раз.")
            actual_size, actual_content_type = s3_object_metadata(media_key)
            if actual_size != upload["size_bytes"] or actual_content_type != upload["content_type"]:
                raise ValueError("Загруженный файл не прошёл проверку.")
            media_data = f"s3:{media_key}"
            file_name = upload["file_name"] or file_name
            con.execute("DELETE FROM media_uploads WHERE key = ?", (media_key,))
        stored_text = f"Документ: {file_name}" if media_type == "document" and not text else text
        con.execute("INSERT INTO messages(id,chat_id,sender_id,profile_user_id,text,media_type,media_data,circle_preview_data,voice_waveform_json,views,reply_to_id,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (msg_id, chat_id, user["id"], profile_user_id, stored_text, media_type, media_data, circle_preview_data, dumps(voice_waveform), 1, reply_to_id, now()))
        con.execute("UPDATE chats SET updated_at=? WHERE id=?", (now(), chat_id))
        if chat and chat["type"] == "channel":
            schedule_automated_comments(con, msg_id, chat_id)
        if chat and chat["type"] == "channel":
            link = con.execute("SELECT target_chat_id FROM channel_links WHERE channel_id = ?", (chat_id,)).fetchone()
            if link:
                con.execute("INSERT INTO messages(id,chat_id,sender_id,text,media_type,media_data,circle_preview_data,views,forwarded_from,created_at) VALUES (?,?,?,?,?,?,?,?,?,?)", (uid("msg"), link["target_chat_id"], user["id"], text, media_type, media_data, circle_preview_data, 1, chat["title"], now()))
                con.execute("UPDATE chats SET updated_at=? WHERE id=?", (now(), link["target_chat_id"]))
        with chat_activities_lock:
            chat_activities.pop((chat_id, user["id"]), None)
        return self.json({"ok": True, "messageId": msg_id})

    def ai_agent_conversation(self, con, user_id):
        rows = con.execute(
            "SELECT role, text, created_at FROM ai_agent_conversation_messages WHERE user_id = ? ORDER BY created_at DESC, id DESC LIMIT 300",
            (user_id,),
        ).fetchall()
        return [{"role": row["role"], "text": row["text"], "createdAt": row["created_at"]} for row in reversed(rows)]

    def add_ai_agent_conversation_message(self, con, user_id, role, text):
        message = " ".join(str(text or "").split())[:3_000]
        if not message or role not in {"user", "assistant"}:
            return
        con.execute(
            "INSERT INTO ai_agent_conversation_messages(id,user_id,role,text,created_at) VALUES (?,?,?,?,?)",
            (uid("ai_conversation"), user_id, role, message, now()),
        )

    def ai_agent_tasks(self, con, user_id):
        rows = con.execute(
            "SELECT * FROM ai_agent_tasks WHERE user_id = ? ORDER BY enabled DESC, updated_at DESC, id DESC",
            (user_id,),
        ).fetchall()
        return [{
            "id": row["id"],
            "title": row["title"],
            "instruction": row["instruction"],
            "scope": row["scope"],
            "chatIds": loads(row["chat_ids_json"], []),
            "enabled": bool(row["enabled"]),
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
        } for row in rows]

    def ai_agent_settings(self, con, user_id):
        row = con.execute("SELECT * FROM ai_agent_settings WHERE user_id = ?", (user_id,)).fetchone()
        channel_rule = con.execute("SELECT * FROM ai_agent_channel_rules WHERE user_id = ?", (user_id,)).fetchone()
        model_profiles = genapi_model_profiles()
        tasks = self.ai_agent_tasks(con, user_id)
        channel_data = {
            "enabled": bool(channel_rule["enabled"]) if channel_rule else False,
            "targetChannelId": channel_rule["target_channel_id"] if channel_rule else "",
            "sourceChannelIds": loads(channel_rule["source_channel_ids_json"], []) if channel_rule else [],
            "rewritePosts": bool(channel_rule["rewrite_posts"]) if channel_rule else False,
        }
        if not row:
            return {"instruction": "", "style": "friendly", "modelProfile": "default", "modelProfiles": model_profiles, "autopilotEnabled": any(task["enabled"] for task in tasks), "autopilotAllDirect": any(task["scope"] == "all_direct" and task["enabled"] for task in tasks), "allowedChatIds": [], "templateMessageIds": [], "agentName": "ИИ-администратор", "bookingConfig": self.normalize_ai_agent_booking_config({}), "tasks": tasks, "channelRule": channel_data, "globalInstructions": self.ai_agent_global_instructions(con) if self.is_ai_agent_global_manager(con.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()) else []}
        return {
            "instruction": row["instruction"],
            "style": row["style"],
            "modelProfile": normalize_genapi_model_profile(row["model_profile"]),
            "modelProfiles": model_profiles,
            "autopilotEnabled": any(task["enabled"] for task in tasks),
            "autopilotAllDirect": any(task["scope"] == "all_direct" and task["enabled"] for task in tasks),
            "allowedChatIds": [],
            "templateMessageIds": loads(row["template_message_ids_json"], []),
            "agentName": row["agent_name"] or "ИИ-администратор",
            "bookingConfig": self.normalize_ai_agent_booking_config(loads(row["booking_config_json"], {})),
            "tasks": tasks,
            "channelRule": channel_data,
            "globalInstructions": self.ai_agent_global_instructions(con) if self.is_ai_agent_global_manager(con.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()) else [],
        }

    def save_ai_agent_task(self, con, user, body):
        task_id = str(body.get("id", "")).strip()
        title = " ".join(str(body.get("title", "")).split())[:120]
        instruction = " ".join(str(body.get("instruction", "")).split())[:3_000]
        scope = str(body.get("scope", "all_direct")).strip()
        enabled = bool(body.get("enabled", True))
        chat_ids = body.get("chatIds", [])
        if not title:
            raise ValueError("Укажите название задачи.")
        if scope not in {"all_direct", "selected_direct"}:
            raise ValueError("Выберите область задачи.")
        if not isinstance(chat_ids, list):
            raise ValueError("Некорректный список диалогов.")
        chat_ids = list(dict.fromkeys(str(value) for value in chat_ids if isinstance(value, str)))[:50]
        if scope == "selected_direct" and not chat_ids:
            raise ValueError("Для задачи выберите хотя бы один личный диалог.")
        for chat_id in chat_ids:
            chat = con.execute("SELECT type FROM chats WHERE id = ?", (chat_id,)).fetchone()
            if not chat or chat["type"] != "direct" or not self.has_chat_access(con, user["id"], chat_id):
                raise ValueError("В задаче можно использовать только доступные личные диалоги.")
        timestamp = now()
        if task_id:
            if not con.execute(
                "UPDATE ai_agent_tasks SET title=?, instruction=?, scope=?, chat_ids_json=?, enabled=?, updated_at=? WHERE id=? AND user_id=?",
                (title, instruction, scope, dumps([] if scope == "all_direct" else chat_ids), int(enabled), timestamp, task_id, user["id"]),
            ).rowcount:
                raise ValueError("Задача не найдена.")
        else:
            task_id = uid("ai_task")
            con.execute(
                "INSERT INTO ai_agent_tasks(id,user_id,title,instruction,scope,chat_ids_json,enabled,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (task_id, user["id"], title, instruction, scope, dumps([] if scope == "all_direct" else chat_ids), int(enabled), timestamp, timestamp),
            )
        return self.json({"ok": True, "taskId": task_id, "message": "Задача сохранена."})

    def toggle_ai_agent_task(self, con, user, body):
        task_id = str(body.get("id", "")).strip()
        enabled = bool(body.get("enabled", False))
        if not task_id or not con.execute(
            "UPDATE ai_agent_tasks SET enabled=?, updated_at=? WHERE id=? AND user_id=?",
            (int(enabled), now(), task_id, user["id"]),
        ).rowcount:
            raise ValueError("Задача не найдена.")
        return self.json({"ok": True})

    def delete_ai_agent_task(self, con, user, body):
        task_id = str(body.get("id", "")).strip()
        if not task_id or not con.execute("DELETE FROM ai_agent_tasks WHERE id=? AND user_id=?", (task_id, user["id"])).rowcount:
            raise ValueError("Задача не найдена.")
        return self.json({"ok": True})

    def is_ai_agent_global_manager(self, user) -> bool:
        return bool(user) and str(user["username"] or "").casefold() == "andrei"

    def ai_agent_global_instructions(self, con):
        return [dict(row) for row in con.execute(
            "SELECT id, title, instruction, updated_at FROM ai_agent_global_instructions ORDER BY updated_at DESC, created_at DESC"
        ).fetchall()]

    def ai_agent_global_instruction_text(self, con) -> str:
        return "\n".join(f"- {item['title']}: {item['instruction']}" for item in self.ai_agent_global_instructions(con))

    def update_ai_agent_global_instruction(self, con, user, body):
        if not self.is_ai_agent_global_manager(user):
            raise PermissionError("Глобальные сценарии ИИ доступны только @andrei.")
        instruction_id = str(body.get("id", "")).strip()
        title = " ".join(str(body.get("title", "")).split())[:120]
        instruction = " ".join(str(body.get("instruction", "")).split())[:3_000]
        if not title or not instruction:
            raise ValueError("Укажите название и правило для ИИ.")
        timestamp = now()
        if instruction_id:
            updated = con.execute("UPDATE ai_agent_global_instructions SET title = ?, instruction = ?, updated_at = ? WHERE id = ?", (title, instruction, timestamp, instruction_id)).rowcount
            if not updated:
                raise ValueError("Глобальный сценарий не найден.")
            return self.json({"ok": True, "message": f"Глобальный сценарий «{title}» обновлён."})
        con.execute("INSERT INTO ai_agent_global_instructions(id,title,instruction,created_by,created_at,updated_at) VALUES (?,?,?,?,?,?)", (uid("ai_global"), title, instruction, user["id"], timestamp, timestamp))
        return self.json({"ok": True, "message": f"Глобальный сценарий «{title}» добавлен."})

    def delete_ai_agent_global_instruction(self, con, user, body):
        if not self.is_ai_agent_global_manager(user):
            raise PermissionError("Глобальные сценарии ИИ доступны только @andrei.")
        instruction_id = str(body.get("id", "")).strip()
        if not instruction_id or not con.execute("DELETE FROM ai_agent_global_instructions WHERE id = ?", (instruction_id,)).rowcount:
            raise ValueError("Глобальный сценарий не найден.")
        return self.json({"ok": True, "message": "Глобальный сценарий удалён."})

    def ai_agent_global_command(self, con, user, question):
        if not self.is_ai_agent_global_manager(user):
            return None
        structured = re.match(
            r"^(?P<action>добавь|создай|обнови)\s+(?:глобальную\s+)?(?:функцию|сценарий|правило)\s*:\s*(?P<title>[^:]{2,120})\s*:\s*(?P<instruction>.+)$",
            question,
            re.IGNORECASE,
        )
        if structured:
            action = structured.group("action").casefold()
            title = " ".join(structured.group("title").split())
            instruction = " ".join(structured.group("instruction").split())[:3_000]
        else:
            teaching = re.match(
                r"^(?:запомни|научи)(?:\s+(?:ии|агента|чат[ -]?про))?\s*(?::|,|—|-)\s*(?P<instruction>.{8,})$",
                question,
                re.IGNORECASE,
            )
            if teaching:
                action = "добавь"
                instruction = " ".join(teaching.group("instruction").split())[:3_000]
                title = f"Правило: {instruction[:80]}".rstrip(" .,:;-")
            else:
                teaching_question = re.search(r"(?:обуч|научи|запомни|глобальн(?:ое|ые)?\s+(?:правил|сценар|функц))", question, re.IGNORECASE)
                if teaching_question:
                    return "Да. В этом диалоге аккаунт @andrei может обучать ИИ общим правилам для Chat-Pro. Напишите, например: «запомни: при вопросах о доставке уточняй номер заказа и называй сроки». Я сохраню правило, подтвержу его и сообщу, что оно применяется к новым ответам ИИ. Правила меняют поведение ответов, но не дают доступ к чужим данным и не запускают код."
                return None
        if not instruction:
            return None
        timestamp = now()
        if action == "обнови":
            existing = con.execute(
                "SELECT id FROM ai_agent_global_instructions WHERE casefold(title) = casefold(?) ORDER BY updated_at DESC LIMIT 1",
                (title,),
            ).fetchone()
            if existing:
                con.execute(
                    "UPDATE ai_agent_global_instructions SET instruction = ?, updated_at = ? WHERE id = ?",
                    (instruction, timestamp, existing["id"]),
                )
                return f"Глобальный сценарий «{title}» обновлён. Новое правило применяется к следующим ответам ИИ у всех пользователей и не расширяет права доступа."
        con.execute(
            "INSERT INTO ai_agent_global_instructions(id,title,instruction,created_by,created_at,updated_at) VALUES (?,?,?,?,?,?)",
            (uid("ai_global"), title, instruction, user["id"], timestamp, timestamp),
        )
        return f"Глобальный сценарий «{title}» сохранён. Он применяется к новым запросам и ответам ИИ у всех пользователей, но не расширяет права доступа к чатам и каналам и не исполняет код."

    def require_pro_account_level(self, con, user_id):
        data = self.account_level_data(con, user_id)
        pro_index = next((index for index, level in enumerate(data["levels"]) if level["id"] == "pro"), None)
        current_index = next((index for index, level in enumerate(data["levels"]) if level["id"] == data["current"]["id"]), -1)
        if pro_index is None or current_index < pro_index:
            raise ValueError("Автопилот ИИ-агента доступен с уровня «Профи». Повысьте уровень аккаунта.")

    def normalize_ai_agent_booking_config(self, value):
        value = value if isinstance(value, dict) else {}
        resources = value.get("resources", [])
        if not isinstance(resources, list):
            resources = []
        resources = list(dict.fromkeys(" ".join(str(item).split())[:80] for item in resources if " ".join(str(item).split())))[:50]
        fields = value.get("fields", [])
        if not isinstance(fields, list):
            fields = []
        fields = list(dict.fromkeys(" ".join(str(item).split())[:80] for item in fields if " ".join(str(item).split())))[:12]
        try:
            duration = int(value.get("durationMinutes", 60))
        except (TypeError, ValueError):
            duration = 60
        working_hours = value.get("workingHours", {})
        working_hours = working_hours if isinstance(working_hours, dict) else {}
        start_time = str(working_hours.get("start", "")).strip()
        end_time = str(working_hours.get("end", "")).strip()
        time_pattern = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")
        if not time_pattern.fullmatch(start_time) or not time_pattern.fullmatch(end_time) or start_time >= end_time:
            start_time = ""
            end_time = ""
        return {
            "enabled": bool(value.get("enabled", False)),
            "serviceName": " ".join(str(value.get("serviceName", "")).split())[:100],
            "resources": resources,
            "durationMinutes": max(10, min(duration, 480)),
            "fields": fields,
            "workingHours": {"start": start_time, "end": end_time},
        }

    def ai_agent_booking_time_error(self, config, start_at, end_at):
        working_hours = config.get("workingHours", {})
        start_time = str(working_hours.get("start", ""))
        end_time = str(working_hours.get("end", ""))
        if not start_time or not end_time:
            return None
        booking_start = datetime.datetime.fromtimestamp(start_at)
        booking_end = datetime.datetime.fromtimestamp(end_at)
        start_hour, start_minute = (int(value) for value in start_time.split(":"))
        end_hour, end_minute = (int(value) for value in end_time.split(":"))
        work_start = booking_start.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
        work_end = booking_start.replace(hour=end_hour, minute=end_minute, second=0, microsecond=0)
        if booking_end.date() != booking_start.date() or booking_start < work_start or booking_end > work_end:
            return f"Брони принимаются с {start_time} до {end_time}. Выберите время, чтобы вся запись укладывалась в этот интервал."
        return None

    def ai_agent_bookings(self, con, user_id):
        rows = con.execute(
            """SELECT id, customer_name, contact, booking_type, resource_name, start_at, end_at, details_json, status, created_at
               FROM ai_agent_bookings WHERE owner_id = ? ORDER BY start_at DESC LIMIT 200""",
            (user_id,),
        ).fetchall()
        bookings = []
        for row in rows:
            item = dict(row)
            item["details"] = loads(item.pop("details_json"), {})
            bookings.append(item)
        return bookings

    def create_ai_agent_booking(self, con, user, body):
        settings = self.ai_agent_settings(con, user["id"])
        config = settings["bookingConfig"]
        if not config["enabled"]:
            raise ValueError("Сначала включите приём заявок в настройках ИИ-администратора.")
        customer_name = " ".join(str(body.get("customerName", "")).split())[:120]
        contact = " ".join(str(body.get("contact", "")).split())[:160]
        resource_name = " ".join(str(body.get("resourceName", "")).split())[:80]
        booking_type = " ".join(str(body.get("bookingType", "")).split())[:100] or config["serviceName"] or "Запись"
        try:
            start_at = int(body.get("startAt", 0))
        except (TypeError, ValueError):
            start_at = 0
        if not customer_name or not resource_name or not start_at:
            raise ValueError("Для записи укажите имя клиента, ресурс (например, столик или мастера) и дату со временем.")
        if config["resources"] and resource_name.casefold() not in {item.casefold() for item in config["resources"]}:
            raise ValueError(f"Ресурс «{resource_name}» не указан в настройках. Выберите один из списка: {', '.join(config['resources'])}.")
        if start_at < now() - 300:
            raise ValueError("Нельзя создать запись в прошлом. Укажите будущую дату и время.")
        end_at = start_at + config["durationMinutes"] * 60
        time_error = self.ai_agent_booking_time_error(config, start_at, end_at)
        if time_error:
            raise ValueError(time_error)
        details = body.get("details", {})
        if not isinstance(details, dict):
            raise ValueError("Дополнительные детали записи должны быть объектом.")
        details = {" ".join(str(key).split())[:80]: " ".join(str(value).split())[:300] for key, value in details.items() if " ".join(str(key).split()) and " ".join(str(value).split())}
        conflict = con.execute(
            """SELECT start_at, end_at FROM ai_agent_bookings
               WHERE owner_id = ? AND status != 'cancelled' AND casefold(resource_name) = casefold(?)
                 AND start_at < ? AND end_at > ? LIMIT 1""",
            (user["id"], resource_name, end_at, start_at),
        ).fetchone()
        if conflict:
            raise ValueError("Этот столик или специалист уже занят на выбранное время. Выберите другой ресурс либо время.")
        booking_id = uid("ai_booking")
        timestamp = now()
        con.execute(
            """INSERT INTO ai_agent_bookings(id,owner_id,customer_user_id,source_chat_id,customer_name,contact,booking_type,resource_name,start_at,end_at,details_json,status,created_at,updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (booking_id, user["id"], None, None, customer_name, contact, booking_type, resource_name, start_at, end_at, dumps(details), "confirmed", timestamp, timestamp),
        )
        return self.json({"ok": True, "message": f"Запись для {customer_name} подтверждена: {resource_name}, {time.strftime('%d.%m.%Y %H:%M', time.localtime(start_at))}.", "bookingId": booking_id})

    def ai_agent_booking_from_chat(self, con, owner_id, chat_id, customer, text):
        settings = self.ai_agent_settings(con, owner_id)
        config = settings["bookingConfig"]
        if not config["enabled"]:
            return None
        match = re.match(r"^\s*(?:запись|бронь|бронирование)\s*:\s*(?P<resource>[^;]+)\s*;\s*(?P<when>[^;]+)\s*;\s*(?P<name>[^;]+)(?:\s*;\s*(?P<contact>[^;]+))?(?:\s*;\s*(?P<details>.+))?\s*$", text, re.IGNORECASE)
        if not match:
            if re.search(r"\b(?:запис|брон|столик|мастер)\w*", text, re.IGNORECASE):
                return f"Чтобы оформить запись, пришлите одной строкой: «Запись: ресурс; ДД.ММ.ГГГГ ЧЧ:ММ; ваше имя; телефон; поле=значение». Доступные ресурсы: {', '.join(config['resources']) or 'уточните у администратора'}. Дополнительные поля: {', '.join(config['fields']) or 'нет'}."
            return None
        resource_name = " ".join(match.group("resource").split())[:80]
        customer_name = " ".join(match.group("name").split())[:120]
        contact = " ".join(str(match.group("contact") or "").split())[:160]
        if config["resources"] and resource_name.casefold() not in {item.casefold() for item in config["resources"]}:
            return f"Ресурс «{resource_name}» не найден. Выберите один из доступных: {', '.join(config['resources'])}."
        try:
            start_at = int(time.mktime(datetime.datetime.strptime(" ".join(match.group("when").split()), "%d.%m.%Y %H:%M").timetuple()))
        except ValueError:
            return "Не удалось прочитать дату. Используйте формат ДД.ММ.ГГГГ ЧЧ:ММ, например: 25.09.2026 18:30."
        if start_at < now() - 300:
            return "Нельзя оформить запись на прошедшее время. Укажите будущую дату и время."
        end_at = start_at + config["durationMinutes"] * 60
        time_error = self.ai_agent_booking_time_error(config, start_at, end_at)
        if time_error:
            return time_error
        conflict = con.execute(
            """SELECT 1 FROM ai_agent_bookings WHERE owner_id = ? AND status != 'cancelled'
               AND casefold(resource_name) = casefold(?) AND start_at < ? AND end_at > ? LIMIT 1""",
            (owner_id, resource_name, end_at, start_at),
        ).fetchone()
        if conflict:
            return f"{resource_name} уже занят на это время. Выберите другое время или ресурс."
        details_text = " ".join(str(match.group("details") or "").split())
        details = {}
        if details_text:
            for part in details_text.split(","):
                key, separator, value = part.partition("=")
                key = " ".join(key.split())[:80]
                value = " ".join(value.split())[:300]
                if separator and key and value:
                    details[key] = value
            if not details:
                details["Комментарий"] = details_text[:300]
        timestamp = now()
        con.execute(
            """INSERT INTO ai_agent_bookings(id,owner_id,customer_user_id,source_chat_id,customer_name,contact,booking_type,resource_name,start_at,end_at,details_json,status,created_at,updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (uid("ai_booking"), owner_id, customer["id"], chat_id, customer_name, contact, config["serviceName"] or "Запись", resource_name, start_at, end_at, dumps(details), "confirmed", timestamp, timestamp),
        )
        return f"Запись подтверждена: {resource_name}, {time.strftime('%d.%m.%Y %H:%M', time.localtime(start_at))}. Если планы изменятся, напишите администратору."

    def update_ai_agent_booking_status(self, con, user, body):
        booking_id = str(body.get("id", "")).strip()
        status = str(body.get("status", "")).strip()
        if status not in {"confirmed", "cancelled"}:
            raise ValueError("Можно подтвердить или отменить запись.")
        if not booking_id or not con.execute(
            "UPDATE ai_agent_bookings SET status = ?, updated_at = ? WHERE id = ? AND owner_id = ?",
            (status, now(), booking_id, user["id"]),
        ).rowcount:
            raise ValueError("Запись не найдена.")
        return self.json({"ok": True})

    def update_ai_agent_model_profile(self, con, user, body):
        model_profile = normalize_genapi_model_profile(body.get("modelProfile", "default"))
        con.execute(
            "INSERT INTO ai_agent_settings(user_id, model_profile, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET model_profile = excluded.model_profile, updated_at = excluded.updated_at",
            (user["id"], model_profile, now()),
        )
        return self.json({"ok": True, "modelProfile": model_profile})

    def update_ai_agent_settings(self, con, user, body):
        instruction = " ".join(str(body.get("instruction", "")).split())[:3_000]
        agent_name = " ".join(str(body.get("agentName", "ИИ-администратор")).split())[:60] or "ИИ-администратор"
        booking_config = self.normalize_ai_agent_booking_config(body.get("bookingConfig", {}))
        style = str(body.get("style", "friendly"))
        model_profile = normalize_genapi_model_profile(body.get("modelProfile", "default"))
        if style not in {"friendly", "business", "brief"}:
            raise ValueError("Неизвестный стиль ИИ-агента.")
        allowed_chat_ids = body.get("allowedChatIds", [])
        autopilot_all_direct = bool(body.get("autopilotAllDirect", False))
        template_message_ids = body.get("templateMessageIds", [])
        if not isinstance(allowed_chat_ids, list) or not isinstance(template_message_ids, list):
            raise ValueError("Некорректные настройки ИИ-агента.")
        allowed_chat_ids = list(dict.fromkeys(str(value) for value in allowed_chat_ids if isinstance(value, str)))[:50]
        template_message_ids = list(dict.fromkeys(str(value) for value in template_message_ids if isinstance(value, str)))[:30]
        for chat_id in allowed_chat_ids:
            chat = con.execute("SELECT type FROM chats WHERE id = ?", (chat_id,)).fetchone()
            if not chat or chat["type"] != "direct" or not self.has_chat_access(con, user["id"], chat_id):
                raise ValueError("В автопилоте можно использовать только доступные личные диалоги.")
        saved = con.execute("SELECT c.id FROM chats c JOIN chat_members m ON m.chat_id = c.id WHERE c.type = 'saved' AND m.user_id = ?", (user["id"],)).fetchone()
        if template_message_ids and not saved:
            raise ValueError("Не найден чат «Избранное».")
        for message_id in template_message_ids:
            template = con.execute("SELECT sender_id, chat_id, media_type FROM messages WHERE id = ?", (message_id,)).fetchone()
            if not template or template["sender_id"] != user["id"] or template["chat_id"] != saved["id"]:
                raise ValueError("Шаблоны можно выбирать только из собственных сообщений в «Избранном».")
        autopilot_enabled = bool(body.get("autopilotEnabled", False))
        if autopilot_enabled and not (autopilot_all_direct or allowed_chat_ids):
            raise ValueError("Для автопилота выберите личные диалоги или включите ответы на все входящие сообщения.")
        con.execute(
            """INSERT INTO ai_agent_settings(user_id,instruction,style,model_profile,autopilot_enabled,autopilot_all_direct,allowed_chat_ids_json,template_message_ids_json,agent_name,booking_config_json,updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(user_id) DO UPDATE SET instruction=excluded.instruction, style=excluded.style, model_profile=excluded.model_profile, autopilot_enabled=excluded.autopilot_enabled, autopilot_all_direct=excluded.autopilot_all_direct, allowed_chat_ids_json=excluded.allowed_chat_ids_json, template_message_ids_json=excluded.template_message_ids_json, agent_name=excluded.agent_name, booking_config_json=excluded.booking_config_json, updated_at=excluded.updated_at""",
            (user["id"], instruction, style, model_profile, int(autopilot_enabled), int(autopilot_all_direct), dumps(allowed_chat_ids), dumps(template_message_ids), agent_name, dumps(booking_config), now()),
        )
        return self.json({"ok": True})

    def ai_agent_private_search(self, con, user, query):
        text = " ".join((query.get("q", [""])[0] or "").split())
        if len(text) < 2:
            raise ValueError("Введите не менее двух символов для поиска.")
        if len(text) > 120:
            raise ValueError("Поисковый запрос не должен быть длиннее 120 символов.")
        rows = con.execute(
            """SELECT m.id, m.chat_id, m.text, m.media_type, m.created_at, c.title AS chat_title
               FROM messages m JOIN chats c ON c.id = m.chat_id
               WHERE c.type = 'direct' AND m.deleted_by_admin = 0
                 AND m.text IS NOT NULL AND trim(m.text) != '' AND casefold(m.text) LIKE ?
                 AND NOT EXISTS(SELECT 1 FROM hidden_messages hm WHERE hm.message_id = m.id AND hm.user_id = ?)
                 AND EXISTS(SELECT 1 FROM chat_members cm WHERE cm.chat_id = c.id AND cm.user_id = ?)
               ORDER BY m.created_at DESC LIMIT 50""",
            (f"%{text.casefold()}%", user["id"], user["id"]),
        ).fetchall()
        return self.json({"ok": True, "messages": [dict(row) for row in rows]})

    def update_ai_agent_channel_rule(self, con, user, body):
        target_channel_id = str(body.get("targetChannelId", "")).strip()
        source_channel_ids = body.get("sourceChannelIds", [])
        if not isinstance(source_channel_ids, list):
            raise ValueError("Некорректный список каналов-источников.")
        source_channel_ids = list(dict.fromkeys(str(value) for value in source_channel_ids if isinstance(value, str)))[:30]
        enabled = bool(body.get("enabled", False))
        if target_channel_id:
            target = con.execute("SELECT type FROM chats WHERE id = ?", (target_channel_id,)).fetchone()
            if not target or target["type"] != "channel" or self.chat_member_role(con, target_channel_id, user["id"]) not in CHANNEL_MANAGER_ROLES:
                raise ValueError("Выберите канал, в котором вы создатель, администратор или автор.")
        for channel_id in source_channel_ids:
            source = con.execute("SELECT type FROM chats WHERE id = ?", (channel_id,)).fetchone()
            if not source or source["type"] != "channel" or not self.has_chat_access(con, user["id"], channel_id):
                raise ValueError("Источниками могут быть только доступные вам каналы.")
            if channel_id == target_channel_id:
                raise ValueError("Свой канал нельзя выбрать источником.")
        if enabled and (not target_channel_id or not source_channel_ids):
            raise ValueError("Выберите свой канал и хотя бы один канал-источник.")
        con.execute(
            """INSERT INTO ai_agent_channel_rules(user_id,enabled,target_channel_id,source_channel_ids_json,created_at,updated_at)
               VALUES (?,?,?,?,?,?)
               ON CONFLICT(user_id) DO UPDATE SET enabled=excluded.enabled,target_channel_id=excluded.target_channel_id,source_channel_ids_json=excluded.source_channel_ids_json,updated_at=excluded.updated_at""",
            (user["id"], int(enabled), target_channel_id or None, dumps(source_channel_ids), now(), now()),
        )
        if source_channel_ids:
            placeholders = ",".join("?" for _ in source_channel_ids)
            con.execute(
                f"""INSERT OR IGNORE INTO ai_agent_channel_processed_posts(rule_user_id,message_id,processed_at)
                    SELECT ?, m.id, ? FROM messages m WHERE m.chat_id IN ({placeholders})""",
                (user["id"], now(), *source_channel_ids),
            )
        return self.json({"ok": True})

    def ai_agent_action_log(self, con, user_id, action, status, summary, payload=None, result_text=""):
        con.execute(
            "INSERT INTO ai_agent_action_log(id,user_id,action,status,summary,payload_json,result_text,created_at) VALUES (?,?,?,?,?,?,?,?)",
            (uid("ai_action"), user_id, action, status, summary[:500], dumps(payload or {}), str(result_text or "")[:2_000], now()),
        )

    def ai_agent_action_logs(self, con, user, query):
        try:
            limit = max(1, min(int((query.get("limit", [100]) or [100])[0]), 200))
        except (TypeError, ValueError):
            limit = 100
        rows = con.execute(
            "SELECT id, action, status, summary, payload_json, result_text, created_at FROM ai_agent_action_log WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user["id"], limit),
        ).fetchall()
        logs = []
        for row in rows:
            item = dict(row)
            item["payload"] = loads(item.pop("payload_json"), {})
            logs.append(item)
        return self.json({"ok": True, "logs": logs})

    def create_ai_agent_pending_action(self, con, user_id, action, payload, summary, ttl=300):
        action_id = uid("ai_pending")
        timestamp = now()
        con.execute(
            "INSERT INTO ai_agent_pending_actions(id,user_id,action,payload_json,summary,created_at,expires_at) VALUES (?,?,?,?,?,?,?)",
            (action_id, user_id, action, dumps(payload or {}), summary[:500], timestamp, timestamp + max(60, min(int(ttl), 1800))),
        )
        return {"id": action_id, "action": action, "summary": summary[:500], "expiresAt": timestamp + max(60, min(int(ttl), 1800))}

    def ai_agent_managed_chat_by_title(self, con, user_id, title):
        title_key = " ".join(str(title or "").split()).casefold()
        rows = con.execute(
            """SELECT c.id, c.title, c.type, c.owner_id
               FROM chats c JOIN chat_members cm ON cm.chat_id = c.id AND cm.user_id = ?
               WHERE c.type IN ('channel', 'group', 'community') AND casefold(c.title) = ?""",
            (user_id, title_key),
        ).fetchall()
        if not rows:
            raise ValueError(f"Не нашёл доступную управляемую беседу или канал «{title}».")
        if len(rows) > 1:
            raise ValueError(f"Нашёл несколько объектов «{title}». Укажите более точное название.")
        chat = rows[0]
        if not self.can_manage_group_messages(con, user_id, chat["id"]):
            raise PermissionError(f"У вас нет прав администратора в «{chat['title']}».")
        return chat

    def ai_agent_prepare_delete_messages(self, con, user, title, query, limit=50):
        chat = self.ai_agent_managed_chat_by_title(con, user["id"], title)
        phrase = " ".join(str(query or "").split())[:160]
        if len(phrase) < 2:
            raise ValueError("Укажите слово или фразу, по которой искать сообщения для удаления.")
        rows = con.execute(
            """SELECT id, text FROM messages
               WHERE chat_id = ? AND deleted_by_admin = 0 AND media_type != 'system' AND casefold(text) LIKE casefold(?)
               ORDER BY created_at DESC LIMIT ?""",
            (chat["id"], f"%{phrase}%", max(1, min(int(limit), 100))),
        ).fetchall()
        if not rows:
            return {"answer": f"В «{chat['title']}» не найдено сообщений с фрагментом «{phrase}»."}
        ids = [row["id"] for row in rows]
        summary = f"Скрыть {len(ids)} сообщений в «{chat['title']}» по запросу «{phrase}»?"
        pending = self.create_ai_agent_pending_action(
            con,
            user["id"],
            "delete_messages",
            {"chatId": chat["id"], "messageIds": ids, "query": phrase},
            summary,
        )
        self.ai_agent_action_log(con, user["id"], "delete_messages", "pending", summary, pending)
        return {"answer": f"Нашёл {len(ids)} сообщений в «{chat['title']}». Подтвердите удаление кнопкой или напишите «подтверждаю».", "pendingAction": pending, "messages": [{"id": row["id"], "text": row["text"][:220], "chat_title": chat["title"]} for row in rows]}

    def ai_agent_prepare_vk_publish(self, con, user, title, text):
        channel = self.ai_agent_managed_channel_by_title(con, user["id"], title)
        target = con.execute(
            "SELECT id, target_title FROM vk_channel_targets WHERE channel_id = ? AND publish_enabled = 1 ORDER BY created_at LIMIT 1",
            (channel["id"],),
        ).fetchone()
        if not target:
            raise ValueError(f"Для канала «{channel['title']}» не подключено сообщество VK с включённой отправкой публикаций.")
        message = " ".join(str(text or "").split())[:10_000]
        if not message:
            raise ValueError("Укажите текст публикации для VK.")
        summary = f"Опубликовать текст в сообществе VK «{target['target_title']}» от канала «{channel['title']}»?"
        pending = self.create_ai_agent_pending_action(
            con,
            user["id"],
            "publish_vk",
            {"targetId": target["id"], "channelId": channel["id"], "text": message},
            summary,
        )
        self.ai_agent_action_log(con, user["id"], "publish_vk", "pending", summary, pending)
        return {"answer": "Подготовил публикацию в VK. Нужны подтверждение и проверка текста.", "pendingAction": pending}

    def execute_ai_agent_pending_action(self, con, user, pending):
        action = pending["action"]
        payload = loads(pending["payload_json"], {})
        if not isinstance(payload, dict):
            raise ValueError("Повреждены данные ожидающего действия.")
        if action == "delete_messages":
            chat_id = str(payload.get("chatId", ""))
            message_ids = list(dict.fromkeys(str(item) for item in payload.get("messageIds", []) if item))[:100]
            if not chat_id or not message_ids or not self.can_manage_group_messages(con, user["id"], chat_id):
                raise PermissionError("У вас больше нет прав на удаление этих сообщений.")
            placeholders = ",".join("?" for _ in message_ids)
            rows = con.execute(
                f"SELECT id, text FROM messages WHERE chat_id = ? AND id IN ({placeholders}) AND deleted_by_admin = 0",
                [chat_id, *message_ids],
            ).fetchall()
            chat = con.execute("SELECT title FROM chats WHERE id = ?", (chat_id,)).fetchone()
            for row in rows:
                con.execute("UPDATE messages SET deleted_by_admin = 1 WHERE id = ?", (row["id"],))
                con.execute(
                    "INSERT INTO ai_agent_moderation_events(id,user_id,channel_id,target_type,target_id,source,text,decision,reason,confidence,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (uid("moderation"), user["id"], chat_id, "message", row["id"], "chat-pro", row["text"][:10_000], "delete", "Удалено после подтверждения ИИ-администратора", 1.0, now()),
                )
            summary = f"Удалено сообщений: {len(rows)} в «{chat['title'] if chat else chat_id}»."
            self.ai_agent_action_log(con, user["id"], action, "completed", summary, payload, summary)
            return {"answer": summary}
        if action == "publish_vk":
            target_id = str(payload.get("targetId", ""))
            target = con.execute(
                "SELECT * FROM vk_channel_targets WHERE id = ? AND channel_id IN (SELECT id FROM chats WHERE owner_id = ?)",
                (target_id, user["id"]),
            ).fetchone()
            if not target or not target["publish_enabled"]:
                raise PermissionError("Сообщество VK не найдено или публикация отключена.")
            result = vk_api(target["access_token"], "wall.post", {"owner_id": target["owner_id"], "message": str(payload.get("text", ""))[:10_000]})
            post_id = result.get("post_id") if isinstance(result, dict) else result
            summary = f"Публикация отправлена в сообщество VK «{target['target_title']}»" + (f" (ID {post_id})." if post_id else ".")
            self.ai_agent_action_log(con, user["id"], action, "completed", summary, payload, summary)
            return {"answer": summary}
        raise ValueError("Неизвестное ожидающее действие ИИ.")

    def confirm_ai_agent_action(self, con, user, body):
        action_id = str(body.get("actionId", "")).strip()
        pending = con.execute(
            "SELECT * FROM ai_agent_pending_actions WHERE id = ? AND user_id = ? AND expires_at >= ?",
            (action_id, user["id"], now()),
        ).fetchone()
        if not pending:
            raise ValueError("Действие не найдено или срок его подтверждения истёк.")
        result = self.execute_ai_agent_pending_action(con, user, pending)
        con.execute("DELETE FROM ai_agent_pending_actions WHERE id = ?", (action_id,))
        return self.json({"ok": True, **result})

    def ai_agent_moderation_rules(self, con, user):
        rows = con.execute(
            """SELECT r.*, c.title AS channel_title FROM ai_agent_comment_moderation_rules r
               JOIN chats c ON c.id = r.channel_id WHERE r.user_id = ? ORDER BY c.title COLLATE NOCASE""",
            (user["id"],),
        ).fetchall()
        rules = []
        for row in rows:
            rules.append({
                "channelId": row["channel_id"],
                "channelTitle": row["channel_title"],
                "blockedWords": loads(row["blocked_words_json"], []) or [],
                "semanticRules": loads(row["semantic_rules_json"], []) or [],
                "actionMode": row["action_mode"],
                "notifyOwner": bool(row["notify_owner"]),
                "targetScope": row["target_scope"],
                "aiEnabled": bool(row["ai_enabled"]),
                "updatedAt": row["updated_at"],
            })
        return self.json({"ok": True, "rules": rules})

    def update_ai_agent_moderation_rule(self, con, user, body):
        channel_id = str(body.get("channelId", "")).strip()
        chat = con.execute("SELECT id, type FROM chats WHERE id = ?", (channel_id,)).fetchone()
        if not chat or chat["type"] not in {"channel", "group", "community"} or not self.can_manage_group_messages(con, user["id"], channel_id):
            raise PermissionError("Настраивать модерацию может только создатель или администратор управляемой группы/канала.")

        def normalize_items(value, limit, item_limit):
            values = value if isinstance(value, list) else re.split(r"[,;\n]", str(value or ""))
            result = []
            for item in values:
                normalized = " ".join(str(item or "").split())[:item_limit]
                if normalized and normalized.casefold() not in {entry.casefold() for entry in result}:
                    result.append(normalized)
            if len(result) > limit:
                raise ValueError(f"Можно указать не более {limit} правил.")
            return result

        words = normalize_items(body.get("blockedWords"), 40, 80)
        semantic = normalize_items(body.get("semanticRules"), 5, 500)
        action_mode = str(body.get("actionMode", "review")).strip().casefold()
        target_scope = str(body.get("targetScope", "comments")).strip().casefold()
        if action_mode not in {"delete", "review"}:
            raise ValueError("Режим модерации должен быть delete или review.")
        if target_scope not in {"comments", "messages", "all"}:
            raise ValueError("Укажите область модерации: comments, messages или all.")
        if not words and not semantic:
            con.execute("DELETE FROM ai_agent_comment_moderation_rules WHERE user_id = ? AND channel_id = ?", (user["id"], channel_id))
            return self.json({"ok": True, "disabled": True, "message": "Модерация отключена."})
        ai_enabled = bool(body.get("aiEnabled")) and bool(semantic)
        notify_owner = 1 if body.get("notifyOwner", True) else 0
        timestamp = now()
        con.execute(
            """INSERT INTO ai_agent_comment_moderation_rules(user_id,channel_id,blocked_words_json,semantic_rules_json,action_mode,notify_owner,target_scope,ai_enabled,created_at,updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(user_id,channel_id) DO UPDATE SET blocked_words_json=excluded.blocked_words_json,semantic_rules_json=excluded.semantic_rules_json,action_mode=excluded.action_mode,notify_owner=excluded.notify_owner,target_scope=excluded.target_scope,ai_enabled=excluded.ai_enabled,updated_at=excluded.updated_at""",
            (user["id"], channel_id, dumps(words), dumps(semantic), action_mode, notify_owner, target_scope, int(ai_enabled), timestamp, timestamp),
        )
        return self.json({"ok": True, "message": "Правила модерации сохранены.", "channelId": channel_id})

    def resolve_ai_agent_moderation_event(self, con, user, body):
        event_id = str(body.get("eventId", "")).strip()
        requested = str(body.get("decision", "")).strip().casefold()
        if not event_id or requested not in {"allow", "delete"}:
            raise ValueError("Укажите событие и решение: approve или reject.")
        event = con.execute(
            "SELECT * FROM ai_agent_moderation_events WHERE id = ? AND decision = 'review'",
            (event_id,),
        ).fetchone()
        if not event or not self.can_manage_group_messages(con, user["id"], event["channel_id"]):
            raise PermissionError("У вас нет прав на это решение модерации или событие уже обработано.")
        target_type = event["target_type"]
        target_id = event["target_id"]
        if str(event["source"] or "").startswith("vk:"):
            source_parts = str(event["source"]).split(":", 2)
            if len(source_parts) != 3:
                raise ValueError("Повреждена ссылка на VK-комментарий.")
            source_id, post_id = source_parts[1], source_parts[2]
            source = con.execute(
                "SELECT * FROM vk_channel_sources WHERE id = ? AND channel_id = ?",
                (source_id, event["channel_id"]),
            ).fetchone()
            if not source:
                raise ValueError("VK-источник комментария не найден.")
            if requested == "delete":
                vk_api(source["access_token"], "wall.deleteComment", {"owner_id": source["owner_id"], "comment_id": int(target_id)})
            con.execute(
                "UPDATE vk_source_moderated_comments SET decision = ?, last_error = NULL WHERE source_id = ? AND post_id = ? AND comment_id = ?",
                (requested, source_id, int(post_id), int(target_id)),
            )
            target_type = "comment"
        elif str(event["source"] or "").startswith("vk-target:"):
            target_parts = str(event["source"]).split(":", 2)
            if len(target_parts) != 3:
                raise ValueError("Повреждена ссылка на VK-комментарий.")
            vk_target_id, post_id = target_parts[1], target_parts[2]
            vk_target = con.execute(
                "SELECT * FROM vk_channel_targets WHERE id = ? AND channel_id = ?",
                (vk_target_id, event["channel_id"]),
            ).fetchone()
            if not vk_target:
                raise ValueError("Сообщество VK для комментария не найдено.")
            if requested == "delete":
                vk_api(vk_target["access_token"], "wall.deleteComment", {"owner_id": vk_target["owner_id"], "comment_id": int(target_id)})
            con.execute(
                "UPDATE vk_target_moderated_comments SET decision = ?, last_error = NULL WHERE target_id = ? AND post_id = ? AND comment_id = ?",
                (requested, vk_target_id, int(post_id), int(target_id)),
            )
            target_type = "comment"
        elif target_type == "comment":
            target = con.execute(
                """SELECT cc.id FROM channel_comments cc JOIN messages m ON m.id = cc.message_id
                   WHERE cc.id = ? AND m.chat_id = ?""",
                (target_id, event["channel_id"]),
            ).fetchone()
            if not target:
                raise ValueError("Комментарий уже удалён или не найден.")
            if requested == "delete":
                con.execute("DELETE FROM channel_comments WHERE id = ?", (target_id,))
        elif target_type == "message":
            target = con.execute(
                "SELECT id FROM messages WHERE id = ? AND chat_id = ? AND deleted_by_admin = 0",
                (target_id, event["channel_id"]),
            ).fetchone()
            if not target:
                raise ValueError("Сообщение уже удалено или не найдено.")
            if requested == "delete":
                con.execute("UPDATE messages SET deleted_by_admin = 1 WHERE id = ? AND chat_id = ?", (target_id, event["channel_id"]))
        else:
            raise ValueError("Неизвестный тип объекта модерации.")
        final_reason = "Одобрено администратором" if requested == "allow" else "Отклонено администратором"
        con.execute(
            "UPDATE ai_agent_moderation_events SET decision = ?, reason = ?, resolved_at = ? WHERE id = ? AND decision = 'review'",
            (requested, final_reason, now(), event_id),
        )
        summary = f"Модерация: {'объект оставлен' if requested == 'allow' else 'объект удалён'}."
        self.ai_agent_action_log(
            con,
            user["id"],
            "moderation_review",
            "completed",
            summary,
            {"eventId": event_id, "decision": requested, "targetType": target_type, "targetId": target_id},
            summary,
        )
        return self.json({"ok": True, "answer": summary, "eventId": event_id, "decision": requested})

    def ai_agent_moderation_events(self, con, user, query):
        try:
            limit = max(1, min(int((query.get("limit", [50]) or [50])[0]), 200))
        except (TypeError, ValueError):
            limit = 50
        rows = self.ai_agent_moderation_event_rows(con, user["id"], limit)
        return self.json({"ok": True, "events": [dict(row) for row in rows]})

    def ai_agent_moderation_event_rows(self, con, user_id, limit):
        return con.execute(
            """SELECT e.*, c.title AS channel_title FROM ai_agent_moderation_events e
               JOIN chats c ON c.id = e.channel_id
               WHERE EXISTS (
                   SELECT 1 FROM chat_members cm
                   WHERE cm.chat_id = e.channel_id AND cm.user_id = ?
                     AND ((c.type = 'channel' AND cm.role IN ('owner', 'admin', 'author'))
                       OR (c.type IN ('group', 'community') AND cm.role IN ('owner', 'admin')))
               )
               ORDER BY e.created_at DESC LIMIT ?""",
            (user_id, limit),
        ).fetchall()

    def ai_agent_handle_command(self, con, user, question):
        normalized = " ".join(str(question or "").split())
        confirm_match = re.fullmatch(r"(?:подтверждаю|подтвердить|да,?\s*подтверждаю)", normalized, re.IGNORECASE)
        if confirm_match:
            pending = con.execute(
                "SELECT * FROM ai_agent_pending_actions WHERE user_id = ? AND expires_at >= ? ORDER BY created_at DESC LIMIT 1",
                (user["id"], now()),
            ).fetchone()
            if not pending:
                return None
            result = self.execute_ai_agent_pending_action(con, user, pending)
            con.execute("DELETE FROM ai_agent_pending_actions WHERE id = ?", (pending["id"],))
            return result
        delete_match = re.match(
            r"^(?:удали|удалить|удаляй)\s+(?:сообщения|публикации|посты)\s+(?:в|из)\s+(?:беседе|группе|канале)\s+[«\"]?(?P<title>[^«»\":]+)[»\"]?\s*:\s*(?P<query>.+)$",
            normalized,
            re.IGNORECASE,
        )
        if delete_match:
            return self.ai_agent_prepare_delete_messages(con, user, delete_match.group("title"), delete_match.group("query"))
        vk_match = re.match(
            r"^(?:опубликуй|опубликовать|размести|выложи)\s+в\s+VK\s+(?:в\s+)?(?:канал|канале)\s+[«\"]?(?P<title>[^«»\":]+)[»\"]?\s*:\s*(?P<text>.+)$",
            normalized,
            re.IGNORECASE,
        )
        if vk_match:
            return self.ai_agent_prepare_vk_publish(con, user, vk_match.group("title"), vk_match.group("text"))
        if re.search(r"(?:покажи|пришли|список).*(?:удал[её]н|модерац|сомнительн)", normalized, re.IGNORECASE):
            rows = self.ai_agent_moderation_event_rows(con, user["id"], 30)
            if not rows:
                return {"answer": "Журнал модерации пока пуст."}
            lines = [f"{row['channel_title']}: {row['decision']} — {row['text'][:120]}" for row in rows]
            return {"answer": "Последние объекты модерации:\n" + "\n".join(lines), "moderationEvents": [dict(row) for row in rows]}
        return None

    def ai_completion_json(self, system, prompt, max_tokens=180, admin=True, timeout=12, model_profile=None):
        profile_id = None if model_profile is None else normalize_genapi_model_profile(model_profile)
        api_key, base_url, model = genapi_configuration_for_profile(profile_id, admin=admin)
        if not api_key:
            raise ValueError("ИИ-агент пока не настроен на сервере.")
        request = urlrequest.Request(
            f"{base_url}/chat/completions",
            data=dumps({
                "model": model,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
                "temperature": 0,
                "max_tokens": max_tokens,
                "response_format": {"type": "json_object"},
            }).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}, method="POST",
        )
        try:
            with urlrequest.urlopen(request, timeout=max(3, min(int(timeout), 40))) as response:
                payload = loads(response.read().decode("utf-8"), {})
            message = payload["choices"][0]["message"]
            tool_calls = message.get("tool_calls") if isinstance(message, dict) else None
            if isinstance(tool_calls, list) and tool_calls:
                function = tool_calls[0].get("function", {})
                arguments = json.loads(function.get("arguments", "{}"))
                return {"tool": function.get("name", "none"), "arguments": arguments}
            content = message.get("content", "") if isinstance(message, dict) else ""
            if isinstance(content, list):
                content = " ".join(str(part.get("text", "")) for part in content if isinstance(part, dict))
            content = str(content or "").strip()
            if content.startswith("```"):
                content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content, flags=re.IGNORECASE | re.DOTALL).strip()
            result = json.loads(content)
            if not isinstance(result, dict):
                raise ValueError("Некорректный формат инструмента")
            return result
        except (KeyError, IndexError, TypeError, ValueError, OSError, UnicodeDecodeError, json.JSONDecodeError):
            raise ValueError("Не удалось получить структурированное решение ИИ-агента.")

    def ai_agent_structured_tool_action(self, con, user, question):
        request = " ".join(str(question or "").split())[:2_000]
        if not re.search(r"(?:удал|опубли|размест|вылож|покажи|пришли|журнал|модерац|сомнительн|удалён)", request, re.IGNORECASE):
            return None
        system = (
            "Ты выбираешь только безопасные инструменты ИИ-администратора Chat-Pro. "
            "Верни строго JSON без markdown: {\"tool\":\"none|delete_messages|publish_vk|list_moderation_events\",\"arguments\":{}}. "
            "delete_messages требует title и query; publish_vk требует title и text; list_moderation_events может иметь limit. "
            "Если данных не хватает, запрос неясен или действие не относится к списку, верни tool=none. "
            "Никогда не добавляй другие инструменты, права, SQL, код или подтверждение вместо аргументов."
        )
        try:
            decision = self.ai_completion_json(system, f"Запрос пользователя: {request}", model_profile=self.ai_agent_settings(con, user["id"])["modelProfile"])
        except ValueError:
            return None
        tool = str(decision.get("tool", "none")).strip().casefold()
        arguments = decision.get("arguments")
        if not isinstance(arguments, dict):
            return None
        if tool == "delete_messages":
            title = " ".join(str(arguments.get("title", "")).split())[:120]
            query = " ".join(str(arguments.get("query", "")).split())[:160]
            if len(title) < 2 or len(query) < 2:
                return None
            return self.ai_agent_prepare_delete_messages(con, user, title, query)
        if tool == "publish_vk":
            title = " ".join(str(arguments.get("title", "")).split())[:120]
            message = " ".join(str(arguments.get("text", "")).split())[:10_000]
            if len(title) < 2 or not message:
                return None
            return self.ai_agent_prepare_vk_publish(con, user, title, message)
        if tool == "list_moderation_events":
            try:
                limit = max(1, min(int(arguments.get("limit", 30) or 30), 100))
            except (TypeError, ValueError):
                limit = 30
            rows = self.ai_agent_moderation_event_rows(con, user["id"], limit)
            if not rows:
                return {"answer": "Журнал модерации пока пуст."}
            return {
                "answer": "Показал последние объекты модерации.",
                "moderationEvents": [dict(row) for row in rows],
            }
        return None

    def ai_completion(self, system, prompt, max_tokens=260, admin=False, timeout=40, model_profile=None):
        profile_id = None if model_profile is None else normalize_genapi_model_profile(model_profile)
        api_key, base_url, model = genapi_configuration_for_profile(profile_id, admin=admin)
        if not api_key:
            raise ValueError("ИИ-агент пока не настроен на сервере.")
        request = urlrequest.Request(
            f"{base_url}/chat/completions",
            data=dumps({"model": model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}], "temperature": 0.55, "max_tokens": max_tokens}).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}, method="POST",
        )
        try:
            with urlrequest.urlopen(request, timeout=max(3, min(int(timeout), 40))) as response:
                payload = loads(response.read().decode("utf-8"), {})
            text = payload["choices"][0]["message"]["content"]
            if isinstance(text, list):
                text = " ".join(str(part.get("text", "")) for part in text if isinstance(part, dict))
            answer = " ".join(str(text or "").strip().strip('«»"').split())[:1_500]
            if not answer or answer.casefold() == "none":
                raise ValueError("Пустой ответ модели")
            return answer
        except (KeyError, IndexError, OSError, UnicodeDecodeError, json.JSONDecodeError):
            raise ValueError("Не удалось получить ответ ИИ-агента. Повторите позже.")

    def ai_agent_fallback_answer(self, question):
        request = " ".join(str(question or "").split())
        if re.search(r"(?:кто тебя (?:сделал|создал|разработал)|кем ты создан)", request, re.IGNORECASE):
            return "Я ИИ-администратор Chat-Pro. Меня разработала команда Chat-Pro, чтобы помогать с сообщениями, каналами и рутинными задачами."
        if re.search(r"(?:что ты умеешь|что умеешь|твои возможности)", request, re.IGNORECASE):
            return "Я помогаю вести каналы: публикую и планирую посты, подключаю RSS и VK, настраиваю комментарии и реакции, модерирую комментарии, ищу сообщения в личных диалогах и готовлю ответы. Дайте задачу обычными словами — если для действия не хватает данных, уточню только необходимое."
        return f"Понял задачу: «{request[:220]}». Могу помочь с анализом, текстом публикации, настройкой канала или поиском по доступным личным диалогам; уточните желаемый результат, если он не указан."

    def ask_ai_agent(self, con, user, body):
        question = " ".join(str(body.get("question", "")).split())[:2_000]
        if not question:
            raise ValueError("Напишите вопрос ИИ-агенту.")
        self.add_ai_agent_conversation_message(con, user["id"], "user", question)
        if re.search(r"(?:кто тебя (?:сделал|создал|разработал)|кем ты создан)", question, re.IGNORECASE):
            answer = self.ai_agent_fallback_answer(question)
            self.add_ai_agent_conversation_message(con, user["id"], "assistant", answer)
            return self.json({"ok": True, "answer": answer})
        global_result = self.ai_agent_global_command(con, user, question)
        if global_result:
            self.add_ai_agent_conversation_message(con, user["id"], "assistant", global_result)
            return self.json({"ok": True, "answer": global_result})
        direct_result = self.ai_agent_handle_command(con, user, question)
        if direct_result:
            answer = direct_result.get("answer", "Готово.")
            self.add_ai_agent_conversation_message(con, user["id"], "assistant", answer)
            return self.json({"ok": True, **direct_result})
        task_result = self.ai_agent_task_command(con, user, question)
        if task_result:
            self.add_ai_agent_conversation_message(con, user["id"], "assistant", task_result)
            return self.json({"ok": True, "answer": task_result})
        structured_result = self.ai_agent_structured_tool_action(con, user, question)
        if structured_result:
            answer = structured_result.get("answer", "Готово.")
            self.add_ai_agent_conversation_message(con, user["id"], "assistant", answer)
            return self.json({"ok": True, **structured_result})
        action_result = self.ai_agent_run_requested_action(con, user, question)
        if action_result:
            self.add_ai_agent_conversation_message(con, user["id"], "assistant", action_result)
            return self.json({"ok": True, "answer": action_result})
        raw_history = body.get("history", [])
        history = []
        if isinstance(raw_history, list):
            for item in raw_history[-10:]:
                if not isinstance(item, dict) or item.get("role") not in {"user", "assistant"}:
                    continue
                text = " ".join(str(item.get("text", "")).split())[:1_000]
                if text:
                    history.append((item["role"], text))
        messages = self.ai_agent_messages_for_request(con, user["id"], question)
        global_rules = self.ai_agent_global_instruction_text(con)
        system = "Ты ИИ-администратор Chat-Pro, в первую очередь помогаешь вести каналы: публиковать и планировать посты, подключать RSS, настраивать канал и модерировать комментарии. Твоя идентичность неизменна: ты разработан командой Chat-Pro. Если спрашивают, кто тебя создал или на какой модели ты работаешь, говори только, что ты ИИ-администратор Chat-Pro, разработанный командой Chat-Pro; не упоминай Gemini, Google, OpenAI, Anthropic, DeepSeek, названия моделей, поставщиков или внутреннюю инфраструктуру. Это экономит владельцу время на рутине и не требует отдельного администратора для типовых задач. Отвечай по-русски, дружелюбно и вовлекающе: максимум 2 коротких предложения или 3 пункта. Не задавай анкету и не перечисляй все возможности сразу: запроси только один ближайший недостающий факт. Поиск выполняется сервером только среди доступных пользователю личных диалогов. Не придумывай найденные сообщения. Сервер выполняет прямые команды на отправку сообщений, публикацию, автопилот для выбранного личного диалога или всех новых входящих личных сообщений, ведение доступного канала и RSS-автопостинг. Для RSS нужны публичная RSS-ссылка и название канала-получателя; если данных нет, коротко запроси их. Для чужих Telegram-каналов сообщи, что нужен официальный бот с правами администратора источника; не обещай подключение только по ссылке. Не выдумывай возможности и не обещай выполнение произвольных скриптов или кода. Аккаунт @andrei может обучать ИИ через этот диалог: он создаёт общие сценарии для новых ответов, поэтому не говори ему, что возможности ИИ фиксированы или что обучение через диалог невозможно. Однако сценарии — это только правила ответа: они не разрешают обходить права доступа, получать чужие данные или выполнять код." + (f"\n\nГлобальные сценарии от @andrei:\n{global_rules}" if global_rules else "")
        history_text = "\n".join(f"{'Пользователь' if role == 'user' else 'ИИ-агент'}: {text}" for role, text in history)
        found_text = "\n".join(f"Диалог «{item['chat_title']}»: {item['text'][:500]}" for item in messages)
        prompt = f"Предыдущий разговор:\n{history_text or 'нет'}\n\nНовый запрос: {question}\n\nНайденные сервером сообщения:\n{found_text or 'нет'}\n\nОтветь на новый запрос."
        try:
            answer = self.ai_completion(system, prompt, 320, admin=True, model_profile=self.ai_agent_settings(con, user["id"])["modelProfile"])
        except ValueError:
            answer = self.ai_agent_fallback_answer(question)
        self.add_ai_agent_conversation_message(con, user["id"], "assistant", answer)
        return self.json({"ok": True, "answer": answer, "messages": messages})

    def ai_agent_run_requested_action(self, con, user, question):
        result = self.ai_agent_rename_requested(con, user, question)
        if result:
            return result
        result = self.ai_agent_channel_status(con, user, question)
        if result:
            return result
        result = self.ai_agent_configure_channel(con, user, question)
        if result:
            return result
        result = self.ai_agent_configure_comment_moderation(con, user, question)
        if result:
            return result
        result = self.ai_agent_configure_booking(con, user, question)
        if result:
            return result
        result = self.ai_agent_configure_rss_autoposting(con, user, question)
        if result:
            return result
        result = self.ai_agent_publish_latest_saved_circle(con, user, question)
        if result:
            return result
        result = self.ai_agent_publish_requested_message(con, user, question)
        if result:
            return result
        result = self.ai_agent_send_requested_message(con, user, question)
        if result:
            return result
        task_result = self.ai_agent_task_command(con, user, question)
        if task_result:
            return task_result
        channel_rule = re.match(r"^(?:веди|настрой\s+ведение|включи\s+ведение)\s+(?:(?:мой\s+)?канал|канал\s+(?P<target>[^:]+?))\s*(?:из|от)\s+канал(?:а|ов)?\s*:\s*(?P<sources>.+)$", question, re.IGNORECASE)
        if channel_rule:
            target = self.ai_agent_managed_channel_by_title(con, user["id"], channel_rule.group("target"))
            source_names = [item.strip() for item in channel_rule.group("sources").split(",") if item.strip()]
            if not source_names:
                raise ValueError("После двоеточия укажите хотя бы один канал-источник.")
            sources = [self.ai_agent_channel_by_title(con, user["id"], name) for name in source_names[:30]]
            source_ids = list(dict.fromkeys(item["id"] for item in sources))
            if target["id"] in source_ids:
                raise ValueError("Свой канал нельзя выбрать источником.")
            rewrite_posts = bool(re.search(r"\b(?:переписыв|перефразир|изменяй\s+текст|своими\s+словами)\w*", question, re.IGNORECASE))
            con.execute(
                """INSERT INTO ai_agent_channel_rules(user_id,enabled,target_channel_id,source_channel_ids_json,rewrite_posts,created_at,updated_at)
                   VALUES (?,?,?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET enabled=excluded.enabled,target_channel_id=excluded.target_channel_id,source_channel_ids_json=excluded.source_channel_ids_json,rewrite_posts=excluded.rewrite_posts,updated_at=excluded.updated_at""",
                (user["id"], 1, target["id"], dumps(source_ids), int(rewrite_posts), now(), now()),
            )
            wording = "с переформулированным текстом без изменения смысла" if rewrite_posts else "как репосты с указанием источника"
            return f"Ведение канала «{target['title']}» включено. Новые публикации из выбранных каналов будут выходить {wording}."
        result = self.ai_agent_channel_management_help(question)
        if result:
            return result
        return None

    def ai_agent_task_by_title(self, con, user_id, title):
        task_key = " ".join(str(title).split()).casefold()
        rows = con.execute(
            "SELECT * FROM ai_agent_tasks WHERE user_id = ? AND casefold(title) = ?",
            (user_id, task_key),
        ).fetchall()
        if not rows:
            raise ValueError(f"Не нашёл задачу «{title}».")
        if len(rows) > 1:
            raise ValueError(f"Нашёл несколько задач «{title}». Переименуйте одну из них.")
        return rows[0]

    def ai_agent_task_command(self, con, user, question):
        request = " ".join(str(question or "").split())
        if re.fullmatch(r"(?:(?:покажи|открой|выведи)\s+(?:мои\s+)?задачи|список\s+задач)", request, re.IGNORECASE):
            tasks = self.ai_agent_tasks(con, user["id"])
            if not tasks:
                return "Задач пока нет. Например: «создай задачу: Отвечать на все входящие; консультируй по колёсам BMW за 50 тыс.»"
            return "Ваши задачи:\n" + "\n".join(f"- {task['title']} — {'включена' if task['enabled'] else 'приостановлена'}" for task in tasks)
        task_match = re.match(r"^(?:создай|добавь|поставь)\s+задач[ау]\s*:\s*(?P<title>[^;:]{2,120})(?:\s*[;:]\s*(?P<instruction>.+))?$", request, re.IGNORECASE)
        legacy_match = re.search(r"\b(?:включи|запусти|сделай|активируй|подключи)\b.*\b(?:автопилот\w*|автоответ\w*)\b", request, re.IGNORECASE) and re.search(r"\b(?:все|всем|любые)\b", request, re.IGNORECASE) and re.search(r"\b(?:входящ\w*|личн\w*|пиш\w*)", request, re.IGNORECASE)
        if task_match or legacy_match:
            title = " ".join((task_match.group("title") if task_match else "Отвечать на все новые входящие").split())
            instruction = " ".join((task_match.group("instruction") if task_match and task_match.group("instruction") else self.ai_agent_settings(con, user["id"])["instruction"]).split())
            timestamp = now()
            con.execute(
                "INSERT INTO ai_agent_tasks(id,user_id,title,instruction,scope,chat_ids_json,enabled,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (uid("ai_task"), user["id"], title, instruction, "all_direct", "[]", 1, timestamp, timestamp),
            )
            return f"Создал задачу «{title}»: она отвечает на новые входящие личные сообщения. Отключить или изменить её можно в «Списке задач»."
        toggle = re.match(r"^(?P<action>включи|возобнови|отключи|приостанови|удали)\s+задач[ау]\s+[«\"]?(?P<title>.+?)[»\"]?$", request, re.IGNORECASE)
        if toggle:
            task = self.ai_agent_task_by_title(con, user["id"], toggle.group("title"))
            action = toggle.group("action").casefold()
            if action == "удали":
                con.execute("DELETE FROM ai_agent_tasks WHERE id = ? AND user_id = ?", (task["id"], user["id"]))
                return f"Задача «{task['title']}» удалена."
            enabled = action in {"включи", "возобнови"}
            con.execute("UPDATE ai_agent_tasks SET enabled = ?, updated_at = ? WHERE id = ?", (int(enabled), now(), task["id"]))
            return f"Задача «{task['title']}» {'включена' if enabled else 'приостановлена'}."
        edit = re.match(r"^(?P<action>измени|обнови|дополни)\s+задач[ау]\s+[«\"]?(?P<title>[^«»\":]+?)[»\"]?\s*:\s*(?P<instruction>.+)$", request, re.IGNORECASE)
        if edit:
            task = self.ai_agent_task_by_title(con, user["id"], edit.group("title"))
            addition = " ".join(edit.group("instruction").split())
            instruction = addition if edit.group("action").casefold() != "дополни" else " ".join(filter(None, [task["instruction"], addition]))
            con.execute("UPDATE ai_agent_tasks SET instruction = ?, updated_at = ? WHERE id = ?", (instruction[:3_000], now(), task["id"]))
            return f"Задача «{task['title']}» {'дополнена' if edit.group('action').casefold() == 'дополни' else 'обновлена'}."
        return None

    def ai_agent_rename_requested(self, con, user, question):
        match = re.match(
            r"^(?:переименуй(?:ся)?|назови(?:сь)?|смени\s+имя)\s+(?:на|в)\s+(?P<name>.{2,60})$",
            " ".join(question.split()),
            re.IGNORECASE,
        )
        if not match:
            return None
        agent_name = " ".join(match.group("name").strip("«»\"' ").split())[:60]
        if not agent_name:
            raise ValueError("Укажите новое имя администратора.")
        settings = self.ai_agent_settings(con, user["id"])
        con.execute(
            """INSERT INTO ai_agent_settings(user_id,instruction,style,autopilot_enabled,allowed_chat_ids_json,template_message_ids_json,agent_name,booking_config_json,updated_at)
               VALUES (?,?,?,?,?,?,?,?,?)
               ON CONFLICT(user_id) DO UPDATE SET agent_name=excluded.agent_name,updated_at=excluded.updated_at""",
            (user["id"], settings["instruction"], settings["style"], int(settings["autopilotEnabled"]), dumps(settings["allowedChatIds"]), dumps(settings["templateMessageIds"]), agent_name, dumps(settings["bookingConfig"]), now()),
        )
        return f"Готово, для вас я теперь «{agent_name}»."

    def ai_agent_channel_status(self, con, user, question):
        request = " ".join(question.split())
        if not re.search(r"\b(?:статус|обстановк|состояни|настройк).*\bканал|\bканал.*\b(?:статус|обстановк|состояни|настройк)", request, re.IGNORECASE):
            return None
        match = re.search(r"\bканал(?:а|е)?\s+[«\"]?(?P<title>[^«»\"?.!]+)[»\"]?", request, re.IGNORECASE)
        channel = self.ai_agent_managed_channel_by_title(con, user["id"], match.group("title").strip() if match else None)
        data = con.execute("SELECT settings_json, subscriber_count FROM chats WHERE id = ?", (channel["id"],)).fetchone()
        settings = loads(data["settings_json"], {}) or {}
        posts = con.execute("SELECT count(*) FROM messages WHERE chat_id = ? AND deleted_by_admin = 0", (channel["id"],)).fetchone()[0]
        comments = con.execute("SELECT count(*) FROM channel_comments cc JOIN messages m ON m.id = cc.message_id WHERE m.chat_id = ?", (channel["id"],)).fetchone()[0]
        moderation = con.execute("SELECT blocked_words_json FROM ai_agent_comment_moderation_rules WHERE user_id = ? AND channel_id = ?", (user["id"], channel["id"])).fetchone()
        words = loads(moderation["blocked_words_json"], []) if moderation else []
        return f"«{channel['title']}»: {data['subscriber_count']} подписчиков, {posts} публикаций, {comments} комментариев. Комментарии {'включены' if settings.get('commentsEnabled', True) else 'выключены'}; модерация: {', '.join(words) if words else 'не настроена'}."

    def ai_agent_configure_channel(self, con, user, question):
        request = " ".join(question.split())
        if not re.search(r"\b(?:настрой|измени|включи|выключи)\b.*\bканал|\bканал\b.*\b(?:настрой|измени|включи|выключи)", request, re.IGNORECASE):
            return None
        if not re.search(r"\b(?:комментар|реакци|подписчик|публичн)\w*", request, re.IGNORECASE):
            return None
        match = re.search(r"\bканал\s+[«\"]?(?P<title>[^«»\":]+?)[»\"]?\s*:\s*(?P<settings>.+)$", request, re.IGNORECASE)
        if not match:
            return "Напишите канал и изменение одной строкой: «Настрой канал Мой канал: выключи комментарии»."
        channel = self.ai_agent_managed_channel_by_title(con, user["id"], match.group("title").strip())
        value = match.group("settings").casefold()
        enabled = not bool(re.search(r"\b(?:выключ|отключ|скрой)\w*", value))
        field = None
        label = ""
        if re.search(r"комментар", value): field, label = "commentsEnabled", "комментарии"
        elif re.search(r"реакци", value): field, label = "showReactions", "реакции"
        elif re.search(r"подписчик", value): field, label = "showSubscribers", "счётчик подписчиков"
        elif re.search(r"публичн", value): field, label = "isPublic", "публичный доступ"
        if not field:
            return "Сейчас могу изменить комментарии, реакции, счётчик подписчиков или публичность канала."
        row = con.execute("SELECT settings_json FROM chats WHERE id = ?", (channel["id"],)).fetchone()
        settings = loads(row["settings_json"], {}) or {}
        settings[field] = enabled
        con.execute("UPDATE chats SET settings_json = ?, updated_at = ? WHERE id = ?", (dumps(settings), now(), channel["id"]))
        return f"Готово: в канале «{channel['title']}» {label} {'включены' if enabled else 'выключены'}."

    def ai_agent_configure_comment_moderation(self, con, user, question):
        request = " ".join(question.split())
        if not re.search(r"\b(?:модерир|удаляй|фильтр|проверя)\w*", request, re.IGNORECASE):
            return None
        match = re.search(r"\b(?:в\s+)?(?:канал(?:е)?|бесед(?:е|ы)|групп(?:е|ы))\s+[«\"]?(?P<title>[^«»\":]+?)[»\"]?\s*:\s*(?P<rules>.+)$", request, re.IGNORECASE)
        if not match:
            return "Напишите: «Модерируй комментарии в канале Мой канал: мат, спам» или «Проверяй сообщения в беседе Чат: реклама, мошенничество»."
        chat = self.ai_agent_managed_chat_by_title(con, user["id"], match.group("title").strip())
        rules_text = match.group("rules").strip()
        action_mode = "review" if re.search(r"(?:провер|сомн|на\s+рассмотр|не\s+удаляй)", rules_text, re.IGNORECASE) else "delete"
        semantic = []
        semantic_match = re.search(r"(?:смысл|если\s+по\s+смыслу|правило)\s*[:=]\s*(.+)$", rules_text, re.IGNORECASE)
        if semantic_match:
            semantic.append(" ".join(semantic_match.group(1).split())[:500])
            rules_text = rules_text[:semantic_match.start()].strip(" ,;")
        words = list(dict.fromkeys(" ".join(item.split()).casefold()[:80] for item in re.split(r"[,;]", rules_text) if " ".join(item.split())))[:40]
        if not words and not semantic:
            raise ValueError("После двоеточия перечислите слова, фразы или смысловое правило.")
        mentions_messages = bool(re.search(r"(?:сообщен|пост|публикац|бесед|групп)", request, re.IGNORECASE))
        mentions_comments = bool(re.search(r"комментар", request, re.IGNORECASE))
        if mentions_messages and mentions_comments:
            scope = "all"
        elif mentions_messages:
            scope = "messages"
        else:
            scope = "comments"
        ai_enabled = bool(semantic)
        con.execute(
            """INSERT INTO ai_agent_comment_moderation_rules(user_id,channel_id,blocked_words_json,semantic_rules_json,action_mode,notify_owner,target_scope,ai_enabled,created_at,updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(user_id,channel_id) DO UPDATE SET blocked_words_json=excluded.blocked_words_json,semantic_rules_json=excluded.semantic_rules_json,action_mode=excluded.action_mode,notify_owner=excluded.notify_owner,target_scope=excluded.target_scope,ai_enabled=excluded.ai_enabled,updated_at=excluded.updated_at""",
            (user["id"], chat["id"], dumps(words), dumps(semantic), action_mode, 1, scope, int(ai_enabled), now(), now()),
        )
        mode_label = "отправлять на проверку" if action_mode == "review" else "удалять автоматически"
        scope_label = "сообщения" if scope == "messages" else "комментарии"
        return f"Модерация «{chat['title']}» включена: {scope_label} будут {mode_label}. Слова: {', '.join(words) if words else 'нет'}{f'; смысловое правило: {semantic[0]}' if semantic else ''}."

    def ai_agent_configure_booking(self, con, user, question):
        request = " ".join(str(question or "").split())
        request_key = request.casefold()
        booking_words = r"(?:брон|брониров|заявк|столик|ресторан)"
        setup_words = r"(?:настр|включ|организ|сдела|добав|приним)"
        if not re.search(rf"\b{booking_words}\w*", request_key) or not re.search(rf"\b{setup_words}\w*", request_key):
            return None

        number_words = {
            "один": 1, "одна": 1, "одно": 1, "два": 2, "две": 2, "три": 3,
            "четыре": 4, "пять": 5, "шесть": 6, "семь": 7, "восемь": 8,
            "девять": 9, "десять": 10, "одиннадцать": 11, "двенадцать": 12,
            "тринадцать": 13, "четырнадцать": 14, "пятнадцать": 15,
            "шестнадцать": 16, "семнадцать": 17, "восемнадцать": 18,
            "девятнадцать": 19, "двадцать": 20,
        }
        count_pattern = r"(?P<count>\d{1,2}|" + "|".join(number_words) + r")"
        table_count = re.search(rf"(?:столик|стола|столов)\w*(?:\s+\w+){{0,2}}?\s+(?:всего\s+)?{count_pattern}", request_key)
        if not table_count:
            table_count = re.search(rf"{count_pattern}\s+(?:столик|стола|столов)\w*", request_key)
        count_value = table_count.group("count") if table_count else ""
        try:
            table_count_value = int(count_value)
        except ValueError:
            table_count_value = number_words.get(count_value, 0)
        if not 1 <= table_count_value <= 50:
            return "Для настройки бронирований укажите количество столиков или список ресурсов. Например: «настрой бронирование в ресторане: 5 столиков, с 12:00 до 17:00»."

        hours = re.search(r"\b(?:с|от)\s*(?P<start_hour>[01]?\d|2[0-3])(?:\s*[:.]?\s*(?P<start_minute>[0-5]\d))?\s*(?:до|[-–])\s*(?P<end_hour>[01]?\d|2[0-3])(?:\s*[:.]?\s*(?P<end_minute>[0-5]\d))?\b", request_key)
        working_hours = {"start": "", "end": ""}
        if hours:
            start_time = f"{int(hours.group('start_hour')):02d}:{int(hours.group('start_minute') or 0):02d}"
            end_time = f"{int(hours.group('end_hour')):02d}:{int(hours.group('end_minute') or 0):02d}"
            if start_time >= end_time:
                return "Время работы указано неверно: окончание должно быть позже начала."
            working_hours = {"start": start_time, "end": end_time}

        duration_match = re.search(r"\b(?:длительность|на)\s*(?P<duration>\d{1,3})\s*(?P<unit>мин\w*|час\w*)", request_key)
        duration = 60
        if duration_match:
            duration = int(duration_match.group("duration")) * (60 if duration_match.group("unit").startswith("час") else 1)
        settings = self.ai_agent_settings(con, user["id"])
        previous_config = settings["bookingConfig"]
        booking_config = self.normalize_ai_agent_booking_config({
            **previous_config,
            "enabled": True,
            "serviceName": "Ресторан" if re.search(r"\b(?:ресторан|столик)\w*", request_key) else previous_config["serviceName"] or "Запись",
            "resources": [f"Столик {index}" for index in range(1, table_count_value + 1)],
            "durationMinutes": duration,
            "workingHours": working_hours,
        })
        con.execute(
            """INSERT INTO ai_agent_settings(user_id,instruction,style,autopilot_enabled,allowed_chat_ids_json,template_message_ids_json,agent_name,booking_config_json,updated_at)
               VALUES (?,?,?,?,?,?,?,?,?)
               ON CONFLICT(user_id) DO UPDATE SET booking_config_json=excluded.booking_config_json,updated_at=excluded.updated_at""",
            (user["id"], settings["instruction"], settings["style"], int(settings["autopilotEnabled"]), dumps(settings["allowedChatIds"]), dumps(settings["templateMessageIds"]), settings["agentName"], dumps(booking_config), now()),
        )
        schedule = f" с {working_hours['start']} до {working_hours['end']}" if working_hours["start"] else ""
        return f"Готово: включил приём бронирований для ресторана — {table_count_value} столиков{schedule}. Одна подтверждённая бронь занимает свой столик на {booking_config['durationMinutes']} минут, поэтому его нельзя забронировать повторно на пересекающееся время. Для автоматических ответов клиентам отметьте нужный личный диалог и включите автопилот; длительность можно изменить в «Моих правилах общения»."

    def ai_agent_channel_management_help(self, question):
        normalized = " ".join(question.split())
        if not re.search(r"\b(?:канал|групп|репост|ведение|автопост)\w*\b", normalized, re.IGNORECASE):
            return None
        if not re.search(r"\b(?:вести|настро|репост|копир|постить|публиков)\w*\b", normalized, re.IGNORECASE):
            return None
        if re.search(r"https?://", normalized, re.IGNORECASE):
            return "По одной ссылке на чужой канал я не могу получить доступ к его публикациям. Сначала откройте или добавьте источник в Chat‑Pro, затем пришлите точные названия источника и канала-получателя. В канале-получателе у вас должна быть роль создателя, администратора или автора. Для сайта вместо страницы пришлите публичную RSS-ссылку — её я проверю и подключу."
        return "Чтобы настроить ведение канала, укажите источник и получатель: «Веди канал Мой канал из каналов: Канал-источник». Для переработки текста добавьте «перефразируй своими словами». Я проверю, что у вас есть доступ к источнику и право публиковать в канале-получателе."

    def ai_agent_configure_rss_autoposting(self, con, user, question):
        normalized = " ".join(question.split())
        request_key = normalized.casefold()
        mentions_site = re.search(r"\b(?:сайт|rss|лента|feed|новост)\w*\b", normalized, re.IGNORECASE)
        intent = re.search(r"\b(?:автопостинг|автопост|импорт\w*|rss|лента|feed)\b", normalized, re.IGNORECASE) or (
            mentions_site and re.search(r"\b(?:публик\w*|пост\w*|вести|сделай)\b", normalized, re.IGNORECASE)
        )
        suggestions_requested = bool(re.search(r"\b(?:пришли|дай|покажи|подскажи)\w*\s+(?:мне\s+)?(?:ссылк|источник|rss)|какие\s+(?:ссылк|источник|rss)", request_key))
        if suggestions_requested and not self.ai_agent_urls_from_text(normalized):
            return self.ai_agent_rss_source_suggestions(request_key)
        recent_context = con.execute(
            "SELECT role, text FROM ai_agent_conversation_messages WHERE user_id = ? ORDER BY created_at DESC, id DESC LIMIT 8",
            (user["id"],),
        ).fetchall()
        continuing_setup = any(
            row["role"] == "assistant" and re.search(r"(?:автопостинг|RSS-лент|ссылка.*автопостинг)", row["text"], re.IGNORECASE)
            for row in recent_context
        )
        has_setup_fact = bool(self.ai_agent_urls_from_text(normalized)) or bool(
            re.search(r"\b(?:в|на)\s+(?:мой\s+)?канал\b", normalized, re.IGNORECASE)
        )
        if not intent and not (continuing_setup and has_setup_fact):
            return None

        # Reuse facts supplied in the immediately preceding setup messages, so the
        # user can send the RSS URL and channel URL in separate turns.
        urls = self.ai_agent_urls_from_text(normalized)
        for row in recent_context:
            urls.extend(self.ai_agent_urls_from_text(row["text"]))
        urls = list(dict.fromkeys(urls))
        target = None
        site_urls = []
        for url in urls:
            channel = self.ai_agent_managed_channel_by_public_url(con, user["id"], url)
            if channel:
                if target and target["id"] != channel["id"]:
                    raise ValueError("Укажите только один канал-получатель для RSS-автопостинга.")
                target = channel
            else:
                site_urls.append(url)

        # A named channel remains supported, but a public Chat-Pro URL is preferred.
        target_match = re.search(r"\b(?:в|на)\s+(?:мой\s+)?канал\s+[«\"]?(?P<title>[^«»\"\n]+?)[»\"]?(?:\s*(?:[.,;]|$))", normalized, re.IGNORECASE)
        if not target and target_match:
            title = " ".join(target_match.group("title").split()).strip(" :")
            target = self.ai_agent_managed_channel_by_title(con, user["id"], title)

        if not site_urls:
            return "Пришлите ссылку с которой хотите сделать автопостинг. Нужна публичная RSS-лента сайта."
        if not target:
            return "Пришлите ссылку своего канала в который хотите осуществлять автопостинг. Я проверю, что у вас есть право публиковать в нём."

        site_url = site_urls[0]
        url_path = urlparse(site_url).path.casefold()
        if not re.search(r"(?:rss|feed|\.xml)(?:/|$)", url_path) and "rss" not in request_key and "feed" not in request_key:
            feed_url = discover_rss_feed(site_url)
        else:
            feed_url = validate_rss_url(site_url)
        feed_title, entries = fetch_rss_feed(feed_url)
        if not entries:
            raise ValueError("Сайт доступен, но в RSS-ленте пока нет публикаций. Пришлите другую RSS-ссылку или проверьте ленту на сайте.")
        existing = con.execute("SELECT 1 FROM rss_channel_sources WHERE channel_id = ? AND feed_url = ?", (target["id"], feed_url)).fetchone()
        if existing:
            return f"RSS-лента «{feed_title or feed_url}» уже подключена к каналу «{target['title']}»."
        self.enforce_autopost_source_limit(con, user["id"], target["id"])
        current = now()
        source_id = uid("rss")
        con.execute(
            """INSERT INTO rss_channel_sources(id,channel_id,feed_url,feed_title,next_poll_at,last_sync_at,last_error,created_by,created_at)
               VALUES (?,?,?,?,?,?,NULL,?,?)""",
            (source_id, target["id"], feed_url, feed_title, current + RSS_POLL_INTERVAL, current, user["id"], current),
        )
        con.executemany(
            "INSERT OR IGNORE INTO rss_source_imported_posts(source_id,entry_id,imported_at) VALUES (?,?,?)",
            [(source_id, entry["id"], current) for entry in entries],
        )
        return f"Подключил RSS-ленту «{feed_title or feed_url}» к каналу «{target['title']}». Новые публикации будут импортироваться автоматически."

    def ai_agent_rss_source_suggestions(self, request_key):
        topics = {
            "технолог": "технологии", "спорт": "спорт", "бизнес": "бизнес", "эконом": "экономика",
            "культур": "культура", "наук": "наука", "игр": "игры", "полит": "политика",
        }
        topic = next((label for key, label in topics.items() if key in request_key), "новости")
        return f"Могу сам найти RSS на сайте, который вы пришлёте. Для ленты на тему «{topic}» отправьте ссылку на подходящий сайт, а затем ссылку своего канала — я найду и проверю RSS перед подключением."

    def ai_agent_urls_from_text(self, text):
        # The host portion deliberately excludes Cyrillic characters. It keeps adjacent
        # prose (for example, "сайтаhttps://example.org") out of a preceding URL.
        pattern = r"https?://[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?(?::\d{1,5})?(?:/[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]*)?"
        return list(dict.fromkeys(match.group(0).rstrip(".,;:!?»»\"'»") for match in re.finditer(pattern, str(text or ""), re.IGNORECASE)))

    def ai_agent_managed_channel_by_public_url(self, con, user_id, value):
        parsed = urlparse(value)
        match = re.fullmatch(r"/channel/([A-Za-z0-9_-]+)", parsed.path.rstrip("/"))
        if not match:
            return None
        channel = con.execute(
            """SELECT c.id, c.title FROM chats c JOIN chat_members member ON member.chat_id = c.id AND member.user_id = ?
               WHERE c.type = 'channel' AND c.invite_code = ?""",
            (user_id, match.group(1)),
        ).fetchone()
        if not channel:
            raise ValueError("Не нашёл доступный вам канал по этой ссылке. Откройте канал в Chat-Pro или пришлите ссылку своего канала.")
        if self.chat_member_role(con, channel["id"], user_id) not in CHANNEL_MANAGER_ROLES:
            raise PermissionError(f"У вас нет права публиковать в канале «{channel['title']}». Нужна роль создателя, администратора или автора.")
        return channel

    def ai_agent_publish_latest_saved_circle(self, con, user, question):
        normalized = " ".join(question.casefold().replace("ё", "е").split())
        if not re.search(r"\b(опубликуй|опубликовать|размести|выложи|отправь|перешли|скопируй|сделай)\b", normalized):
            return None
        if not re.search(r"\b(?:видео)?круж\w*\b", normalized) or "избран" not in normalized:
            return None
        channel = self.ai_agent_owned_channel_from_request(con, user["id"], normalized)
        saved_circle = con.execute(
            """SELECT m.text, m.media_type, m.media_data, m.circle_preview_data, m.voice_waveform_json
               FROM messages m JOIN chats c ON c.id = m.chat_id
               JOIN chat_members member ON member.chat_id = c.id AND member.user_id = ?
               WHERE c.type = 'saved' AND m.sender_id = ? AND m.media_type = 'circle'
                 AND m.deleted_by_admin = 0 AND m.media_data IS NOT NULL
               ORDER BY m.created_at DESC LIMIT 1""",
            (user["id"], user["id"]),
        ).fetchone()
        if not saved_circle:
            raise ValueError("В «Избранном» не нашёл ни одного видеокружка для публикации.")
        enforce_channel_post_limit(con, channel["id"])
        self.enforce_message_limit(con, user["id"])
        message_id = uid("msg")
        con.execute(
            """INSERT INTO messages(id,chat_id,sender_id,text,media_type,media_data,circle_preview_data,voice_waveform_json,views,source_type,ai_agent,created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (message_id, channel["id"], user["id"], saved_circle["text"], "circle", saved_circle["media_data"], saved_circle["circle_preview_data"], saved_circle["voice_waveform_json"], 1, "ai_agent_saved_circle", 1, now()),
        )
        con.execute("UPDATE chats SET updated_at = ? WHERE id = ?", (now(), channel["id"]))
        schedule_automated_comments(con, message_id, channel["id"])
        return f"Опубликовал последний видеокружок из «Избранного» в канале «{channel['title']}»."

    def ai_agent_publish_requested_message(self, con, user, question):
        request = re.match(r"^(?:опубликуй|опубликовать|размести|выложи|отправь|напиши|сделай\s+пост)\s+(?:в\s+)?(?:(?:мой\s+)?канал|канал\s+(?P<target>[^:]+))\s*:\s*(?P<text>.+)$", question, re.IGNORECASE)
        if not request:
            return None
        channel = self.ai_agent_owned_channel(con, user["id"], request.group("target"))
        text = " ".join(request.group("text").split())[:2_000]
        if not text:
            raise ValueError("После двоеточия напишите текст публикации.")
        enforce_channel_post_limit(con, channel["id"])
        self.enforce_message_limit(con, user["id"])
        message_id = uid("msg")
        con.execute(
            "INSERT INTO messages(id,chat_id,sender_id,text,views,ai_agent,created_at) VALUES (?,?,?,?,?,?,?)",
            (message_id, channel["id"], user["id"], f"🤖 Помощник: {text}", 1, 1, now()),
        )
        con.execute("UPDATE chats SET updated_at = ? WHERE id = ?", (now(), channel["id"]))
        schedule_automated_comments(con, message_id, channel["id"])
        return f"Опубликовал в канале «{channel['title']}»."

    def ai_agent_owned_channel(self, con, user_id, title=None):
        normalized_title = " ".join(str(title or "").split())
        if normalized_title:
            return self.ai_agent_channel_by_title(con, user_id, normalized_title, own=True)
        rows = con.execute("SELECT id, title FROM chats WHERE type = 'channel' AND owner_id = ? ORDER BY updated_at DESC", (user_id,)).fetchall()
        if not rows:
            raise ValueError("У вас пока нет собственного канала для публикации.")
        if len(rows) > 1:
            raise ValueError("У вас несколько собственных каналов. Укажите название: «Опубликуй в канал Название: текст».")
        return rows[0]

    def ai_agent_owned_channel_from_request(self, con, user_id, request):
        rows = con.execute("SELECT id, title FROM chats WHERE type = 'channel' AND owner_id = ? ORDER BY updated_at DESC", (user_id,)).fetchall()
        if not rows:
            raise ValueError("У вас пока нет собственного канала для публикации.")
        request_key = str(request or "").casefold()
        matches = [row for row in rows if re.search(rf"(?<!\w){re.escape(row['title'].casefold())}(?!\w)", request_key)]
        if len(matches) == 1:
            return matches[0]
        if len(rows) == 1:
            return rows[0]
        names = ", ".join(f"«{row['title']}»" for row in rows[:5])
        raise ValueError(f"Не понял, в какой из ваших каналов отправить кружок. Укажите название канала в запросе: {names}.")

    def ai_agent_managed_channel_by_title(self, con, user_id, title):
        channel = self.ai_agent_channel_by_title(con, user_id, title)
        if self.chat_member_role(con, channel["id"], user_id) not in CHANNEL_MANAGER_ROLES:
            raise PermissionError(f"У вас нет права публиковать в канале «{channel['title']}». Нужна роль создателя, администратора или автора.")
        return channel

    def ai_agent_direct_chat_by_recipient(self, con, user_id, recipient):
        recipient_key = " ".join(str(recipient).replace("@", "").split()).casefold()
        chats = con.execute(
            """SELECT c.id, u.name, u.username FROM chats c JOIN chat_members mine ON mine.chat_id = c.id AND mine.user_id = ?
               JOIN chat_members peer ON peer.chat_id = c.id AND peer.user_id != ? JOIN users u ON u.id = peer.user_id
               WHERE c.type = 'direct' AND (casefold(u.name) = ? OR casefold(u.username) = ?) ORDER BY c.updated_at DESC""",
            (user_id, user_id, recipient_key, recipient_key),
        ).fetchall()
        unique_chats = {row["id"]: row for row in chats}
        if not unique_chats:
            raise ValueError(f"Не нашёл доступный личный диалог с «{recipient}». Укажите точное имя или @username.")
        if len(unique_chats) > 1:
            raise ValueError(f"Нашёл несколько личных диалогов с «{recipient}». Укажите точный @username.")
        return next(iter(unique_chats.values()))

    def ai_agent_channel_by_title(self, con, user_id, title, own=False):
        title_key = " ".join(str(title).split()).casefold()
        rows = con.execute(
            """SELECT c.id, c.title FROM chats c JOIN chat_members member ON member.chat_id = c.id AND member.user_id = ?
               WHERE c.type = 'channel' AND casefold(c.title) = ?""" + (" AND c.owner_id = ?" if own else ""),
            (user_id, title_key, user_id) if own else (user_id, title_key),
        ).fetchall()
        if not rows:
            raise ValueError(f"Не нашёл {'ваш' if own else 'доступный'} канал «{title}». Укажите точное название.")
        if len(rows) > 1:
            raise ValueError(f"Нашёл несколько каналов «{title}». Переименуйте один из них или используйте уникальное название.")
        return rows[0]

    def control_ai_agent(self, con, user, body):
        enabled = bool(body.get("enabled", False))
        settings = self.ai_agent_settings(con, user["id"])
        allowed_chat_ids = settings["allowedChatIds"]
        channel_rule = settings["channelRule"]
        autopilot_enabled = enabled and bool(settings["autopilotAllDirect"] or allowed_chat_ids)
        channel_enabled = enabled and bool(channel_rule["targetChannelId"] and channel_rule["sourceChannelIds"])
        con.execute(
            """INSERT INTO ai_agent_settings(user_id,instruction,style,autopilot_enabled,allowed_chat_ids_json,template_message_ids_json,updated_at)
               VALUES (?,?,?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET autopilot_enabled=excluded.autopilot_enabled,updated_at=excluded.updated_at""",
            (user["id"], settings["instruction"], settings["style"], int(autopilot_enabled), dumps(allowed_chat_ids), dumps(settings["templateMessageIds"]), now()),
        )
        if channel_rule["targetChannelId"] or channel_rule["sourceChannelIds"]:
            con.execute(
                """INSERT INTO ai_agent_channel_rules(user_id,enabled,target_channel_id,source_channel_ids_json,created_at,updated_at)
                   VALUES (?,?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET enabled=excluded.enabled,updated_at=excluded.updated_at""",
                (user["id"], int(channel_enabled), channel_rule["targetChannelId"] or None, dumps(channel_rule["sourceChannelIds"]), now(), now()),
            )
        if enabled and not autopilot_enabled and not channel_enabled:
            raise ValueError("Сначала выберите личные диалоги или включите ответы на все входящие сообщения; для каналов настройте ведение через запрос агенту.")
        return self.json({"ok": True, "running": bool(autopilot_enabled or channel_enabled)})

    def ai_agent_send_requested_message(self, con, user, question):
        request = re.match(r"^(?:напиши|отправь|передай)\s+(?:сообщение\s+)?(?P<recipient>[^:]{2,80})\s*:\s*(?P<text>.+)$", question, re.IGNORECASE)
        if not request:
            return None
        recipient = " ".join(request.group("recipient").replace("@", "").split())
        text = " ".join(request.group("text").split())[:2_000]
        if not text:
            raise ValueError("После двоеточия напишите текст сообщения.")
        recipient_key = recipient.casefold()
        chats = con.execute(
            """SELECT c.id, u.name, u.username FROM chats c
               JOIN chat_members mine ON mine.chat_id = c.id AND mine.user_id = ?
               JOIN chat_members peer ON peer.chat_id = c.id AND peer.user_id != ?
               JOIN users u ON u.id = peer.user_id
               WHERE c.type = 'direct' AND (casefold(u.name) = ? OR casefold(u.username) = ?)
               ORDER BY c.updated_at DESC""",
            (user["id"], user["id"], recipient_key, recipient_key),
        ).fetchall()
        unique_chats = {row["id"]: row for row in chats}
        if not unique_chats:
            raise ValueError(f"Не нашёл доступный личный диалог с «{recipient}». Укажите точное имя или @username после команды.")
        if len(unique_chats) > 1:
            raise ValueError(f"Нашёл несколько личных диалогов с «{recipient}». Укажите точный @username получателя.")
        self.enforce_message_limit(con, user["id"])
        chat = next(iter(unique_chats.values()))
        con.execute(
            "INSERT INTO messages(id,chat_id,sender_id,text,views,ai_agent,created_at) VALUES (?,?,?,?,?,?,?)",
            (uid("msg"), chat["id"], user["id"], f"🤖 Помощник: {text}", 1, 1, now()),
        )
        con.execute("UPDATE chats SET updated_at = ? WHERE id = ?", (now(), chat["id"]))
        return f"Отправил сообщение пользователю {chat['name']} от вашего имени."

    def ai_agent_messages_for_request(self, con, user_id, question):
        if not re.search(r"\b(найд|ищ|поиск|покаж|пришл|отправ|сообщени|диалог|переписк)\w*", question, re.IGNORECASE):
            return []
        ignored = {"найди", "найти", "покажи", "пришли", "отправь", "сообщение", "сообщения", "сообщений", "диалог", "диалоге", "переписке", "личных", "личной", "чат", "чате", "мне", "где", "которое", "которые", "про", "или", "что", "это", "вот", "было", "был", "была", "есть", "из", "для", "с", "по", "и", "а", "у"}
        terms = [word.casefold() for word in re.findall(r"[\wёЁ-]{3,}", question) if word.casefold() not in ignored][:6]
        if not terms:
            return []
        conditions = " AND ".join("(casefold(m.text) LIKE ? OR casefold(c.title) LIKE ?)" for _ in terms)
        params = [value for term in terms for value in (f"%{term}%", f"%{term}%")]
        rows = con.execute(
            f"""SELECT m.id, m.chat_id, m.text, m.created_at, c.title AS chat_title
                FROM messages m JOIN chats c ON c.id = m.chat_id
                WHERE c.type = 'direct' AND m.deleted_by_admin = 0 AND trim(m.text) != ''
                  AND NOT EXISTS(SELECT 1 FROM hidden_messages hm WHERE hm.message_id = m.id AND hm.user_id = ?)
                  AND EXISTS(SELECT 1 FROM chat_members cm WHERE cm.chat_id = c.id AND cm.user_id = ?)
                  AND {conditions}
                ORDER BY m.created_at DESC LIMIT 10""",
            (user_id, user_id, *params),
        ).fetchall()
        return [dict(row) for row in rows]

    def draft_ai_agent_reply(self, con, user, body):
        chat_id = str(body.get("chatId", ""))
        chat = con.execute("SELECT type FROM chats WHERE id = ?", (chat_id,)).fetchone()
        if not chat or chat["type"] != "direct" or not self.has_chat_access(con, user["id"], chat_id):
            raise PermissionError()
        settings = self.ai_agent_settings(con, user["id"])
        recent = con.execute("SELECT sender_id,text FROM messages WHERE chat_id = ? ORDER BY created_at DESC LIMIT 8", (chat_id,)).fetchall()
        if not recent:
            raise ValueError("В диалоге пока нет сообщений для подготовки ответа.")
        context = "\n".join(f"{'Пользователь' if item['sender_id'] == user['id'] else 'Собеседник'}: {item['text'][:500]}" for item in reversed(recent))
        system = "Ты создаёшь черновик ответа для владельца аккаунта в личном диалоге. Не рекламируй Chat-Pro, его уровни или подписки. Не утверждай, что являешься человеком. Не добавляй пометку об ИИ: её добавит интерфейс. Не обещай то, чего нет в инструкции."
        prompt = f"Глобальные сценарии: {self.ai_agent_global_instruction_text(con) or 'нет'}\nИнструкция владельца: {settings['instruction'] or 'Вежливо помогай собеседнику.'}\nСтиль: {settings['style']}\n\nДиалог:\n{context}\n\nВерни только один короткий ответ на последнее сообщение собеседника."
        return self.json({"ok": True, "draft": self.ai_completion(system, prompt, 220, model_profile=settings["modelProfile"])})

    def process_ai_agent_autopilots(self, con):
        rows = []
        for task in con.execute("SELECT * FROM ai_agent_tasks WHERE enabled = 1 ORDER BY updated_at DESC, id DESC").fetchall():
            chat_ids = loads(task["chat_ids_json"], [])
            if not isinstance(chat_ids, list):
                chat_ids = []
            chat_ids = [str(chat_id) for chat_id in chat_ids[:50] if isinstance(chat_id, str)]
            settings = self.ai_agent_settings(con, task["user_id"])
            common_params = (task["id"], task["title"], task["instruction"], task["user_id"], settings["instruction"], settings["style"], settings["modelProfile"], dumps(settings["templateMessageIds"]), task["updated_at"])
            if task["scope"] == "all_direct":
                rows.extend(con.execute(
                    """SELECT ? AS task_id, ? AS task_title, ? AS task_instruction, ? AS user_id, ? AS instruction, ? AS style, ? AS model_profile, ? AS template_message_ids_json,
                               m.id AS message_id, m.chat_id, m.sender_id, m.text, m.created_at
                        FROM messages m JOIN chats c ON c.id = m.chat_id
                        JOIN chat_members cm ON cm.chat_id = c.id AND cm.user_id = ?
                        WHERE c.type = 'direct' AND m.sender_id != ? AND m.ai_agent = 0 AND m.created_at >= ?
                          AND NOT EXISTS(SELECT 1 FROM ai_agent_processed_messages p WHERE p.message_id = m.id)
                        ORDER BY m.created_at ASC LIMIT 10""",
                    (*common_params[:8], task["user_id"], task["user_id"], common_params[8]),
                ).fetchall())
            elif task["scope"] == "selected_direct" and chat_ids:
                placeholders = ",".join("?" for _ in chat_ids)
                rows.extend(con.execute(
                    f"""SELECT ? AS task_id, ? AS task_title, ? AS task_instruction, ? AS user_id, ? AS instruction, ? AS style, ? AS model_profile, ? AS template_message_ids_json,
                               m.id AS message_id, m.chat_id, m.sender_id, m.text, m.created_at
                        FROM messages m JOIN chats c ON c.id = m.chat_id
                        WHERE m.chat_id IN ({placeholders}) AND c.type = 'direct' AND m.sender_id != ? AND m.ai_agent = 0 AND m.created_at >= ?
                          AND NOT EXISTS(SELECT 1 FROM ai_agent_processed_messages p WHERE p.message_id = m.id)
                        ORDER BY m.created_at ASC LIMIT 10""",
                    (*common_params[:8], *chat_ids, task["user_id"], common_params[8]),
                ).fetchall())
        rows.sort(key=lambda row: row["created_at"])
        handled_message_ids = set()
        for row in rows:
            if row["message_id"] in handled_message_ids:
                continue
            handled_message_ids.add(row["message_id"])
            con.execute("INSERT OR IGNORE INTO ai_agent_processed_messages(message_id,processed_at) VALUES (?,?)", (row["message_id"], now()))
            owner_id = row["user_id"]
            try:
                text = " ".join(str(row["text"] or "").split())
                if not text or re.search(r"\b(оператор|человек|стоп|не пишите|отключи)\b", text, re.IGNORECASE):
                    continue
                customer = con.execute("SELECT * FROM users WHERE id = ?", (row["sender_id"],)).fetchone()
                booking_reply = self.ai_agent_booking_from_chat(con, owner_id, row["chat_id"], customer, text) if customer else None
                if booking_reply:
                    con.execute("INSERT INTO messages(id,chat_id,sender_id,text,views,ai_agent,created_at) VALUES (?,?,?,?,?,?,?)", (uid("msg"), row["chat_id"], owner_id, f"🤖 {self.ai_agent_settings(con, owner_id)['agentName']}: {booking_reply}", 1, 1, now()))
                    con.execute("UPDATE chats SET updated_at = ? WHERE id = ?", (now(), row["chat_id"]))
                    continue
                sent_today = con.execute("SELECT COUNT(*) AS total FROM messages WHERE sender_id = ? AND ai_agent = 1 AND created_at >= ?", (owner_id, now() - 86400)).fetchone()["total"]
                if sent_today >= 40:
                    continue
                recent = con.execute("SELECT sender_id,text FROM messages WHERE chat_id = ? ORDER BY created_at DESC LIMIT 8", (row["chat_id"],)).fetchall()
                context = "\n".join(f"{'Владелец' if item['sender_id'] == owner_id else 'Собеседник'}: {item['text'][:500]}" for item in reversed(recent))
                template_ids = loads(row["template_message_ids_json"], [])
                templates = [item["text"] for item in con.execute(f"SELECT text FROM messages WHERE id IN ({','.join('?' for _ in template_ids)})", template_ids).fetchall()] if template_ids else []
                system = "Ты рабочий ИИ-помощник в личном диалоге. Создаёшь безопасный короткий ответ по инструкции владельца и активной задаче. Никогда не рекламируй Chat-Pro, его подписки, уровни или функции. Не выдавай себя за человека. Не обещай невозможное."
                booking_config = self.ai_agent_settings(con, owner_id)["bookingConfig"]
                booking_instruction = f"\nПриём заявок: {'включён' if booking_config['enabled'] else 'выключен'}. Если включён и клиент хочет записаться, попроси точную строку: «Запись: ресурс; ДД.ММ.ГГГГ ЧЧ:ММ; имя; телефон; поле=значение». Ресурсы: {', '.join(booking_config['resources']) or 'не указаны'}. Дополнительные поля: {', '.join(booking_config['fields']) or 'нет'}. Длительность: {booking_config['durationMinutes']} минут." if booking_config['enabled'] else ""
                prompt = f"Глобальные сценарии: {self.ai_agent_global_instruction_text(con) or 'нет'}\nЗадача: {row['task_title']}\nПравило задачи: {row['task_instruction'] or 'Вежливо ответь по теме.'}\nОбщие правила владельца: {row['instruction'] or 'нет'}\nСтиль: {row['style']}\nРазрешённые текстовые шаблоны: {' | '.join(templates[:5]) or 'нет'}{booking_instruction}\n\nДиалог:\n{context}\n\nВерни только один ответ на последнее сообщение собеседника."
                with chat_activities_lock:
                    chat_activities[(row["chat_id"], owner_id)] = ("typing", time.monotonic() + CHAT_ACTIVITY_TTL)
                reply = self.ai_completion(system, prompt, 220, model_profile=row["model_profile"])
                if len(reply) < 2:
                    continue
                con.execute("INSERT INTO messages(id,chat_id,sender_id,text,views,ai_agent,created_at) VALUES (?,?,?,?,?,?,?)", (uid("msg"), row["chat_id"], owner_id, f"🤖 {self.ai_agent_settings(con, owner_id)['agentName']}: {reply}", 1, 1, now()))
                con.execute("UPDATE chats SET updated_at = ? WHERE id = ?", (now(), row["chat_id"]))
            except Exception:
                continue
            finally:
                with chat_activities_lock:
                    chat_activities.pop((row["chat_id"], owner_id), None)

    def process_ai_agent_channel_rules(self, con):
        for rule in con.execute("SELECT * FROM ai_agent_channel_rules WHERE enabled = 1").fetchall():
            model_profile = self.ai_agent_settings(con, rule["user_id"])["modelProfile"]
            source_ids = loads(rule["source_channel_ids_json"], [])
            if not isinstance(source_ids, list) or not source_ids or not rule["target_channel_id"]:
                continue
            source_ids = [str(item) for item in source_ids[:30] if isinstance(item, str)]
            target = con.execute("SELECT type FROM chats WHERE id = ?", (rule["target_channel_id"],)).fetchone()
            if not target or target["type"] != "channel" or self.chat_member_role(con, rule["target_channel_id"], rule["user_id"]) not in CHANNEL_MANAGER_ROLES:
                continue
            placeholders = ",".join("?" for _ in source_ids)
            posts = con.execute(
                f"""SELECT m.*, c.title AS source_title FROM messages m JOIN chats c ON c.id = m.chat_id
                    WHERE m.chat_id IN ({placeholders}) AND c.type = 'channel' AND m.deleted_by_admin = 0
                      AND NOT EXISTS(SELECT 1 FROM ai_agent_channel_processed_posts p WHERE p.rule_user_id = ? AND p.message_id = m.id)
                    ORDER BY m.created_at ASC LIMIT 10""",
                (*source_ids, rule["user_id"]),
            ).fetchall()
            for post in posts:
                if channel_post_limit_reached(con, rule["target_channel_id"]):
                    break
                con.execute("INSERT OR IGNORE INTO ai_agent_channel_processed_posts(rule_user_id,message_id,processed_at) VALUES (?,?,?)", (rule["user_id"], post["id"], now()))
                if not self.has_chat_access(con, rule["user_id"], post["chat_id"]):
                    continue
                text = post["text"]
                forwarded_from = post["source_title"]
                source_type = "ai_agent_repost"
                if rule["rewrite_posts"] and text.strip():
                    try:
                        text = self.ai_completion(
                            "Ты редактор канала. Перефразируй публикацию своими словами без изменения фактов, смысла, имён, чисел, ссылок и призывов. Не добавляй ничего от себя. Верни только готовый текст публикации.",
                            text,
                            700,
                            model_profile=model_profile,
                        )
                        forwarded_from = None
                        source_type = "ai_agent_rewrite"
                    except ValueError:
                        continue
                con.execute(
                    "INSERT INTO messages(id,chat_id,sender_id,text,media_type,media_data,circle_preview_data,voice_waveform_json,views,forwarded_from,forwarded_from_user_id,source_type,source_id,ai_agent,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (uid("msg"), rule["target_channel_id"], rule["user_id"], text, post["media_type"], post["media_data"], post["circle_preview_data"], post["voice_waveform_json"], 1, forwarded_from, post["sender_id"], source_type, post["id"], 1, now()),
                )
                con.execute("UPDATE chats SET updated_at = ? WHERE id = ?", (now(), rule["target_channel_id"]))

    def ai_agent_semantic_moderation(self, text, rules, model_profile="default"):
        instruction = " ".join(str(item).split())[:500]
        if not instruction or not str(text or "").strip():
            return "allow", "", 0.0
        try:
            answer = self.ai_completion(
                "Ты модератор пользовательского контента. Верни строго одну строку в формате: DECISION=allow|delete|review; REASON=краткая причина. Не выдумывай факты.",
                f"Смысловое правило: {instruction}\nТекст: {str(text)[:4000]}",
                120,
                admin=True,
                timeout=8,
                model_profile=model_profile,
            )
        except ValueError:
            return "review", "ИИ-модерация временно недоступна", 0.0
        decision_match = re.search(r"DECISION\s*=\s*(allow|delete|review)", answer, re.IGNORECASE)
        reason_match = re.search(r"REASON\s*=\s*(.+)$", answer, re.IGNORECASE)
        decision = decision_match.group(1).casefold() if decision_match else "review"
        reason = reason_match.group(1).strip()[:500] if reason_match else answer[:500]
        return decision, reason, 0.75 if decision_match else 0.4

    def record_ai_moderation_event(self, con, rule, channel_id, target_type, target_id, text, decision, reason, confidence, source="chat-pro"):
        con.execute(
            "INSERT INTO ai_agent_moderation_events(id,user_id,channel_id,target_type,target_id,source,text,decision,reason,confidence,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (uid("moderation"), rule["user_id"], channel_id, target_type, target_id, source, str(text or "")[:10_000], decision, str(reason or "")[:500], confidence, now()),
        )
        self.ai_agent_action_log(
            con,
            rule["user_id"],
            "moderation",
            decision,
            f"Модерация: {decision} для {target_type} {target_id}",
            {"channelId": channel_id, "targetType": target_type, "targetId": target_id},
            str(reason or "")[:2_000],
        )
        if rule["notify_owner"]:
            channel = con.execute("SELECT title, owner_id FROM chats WHERE id = ?", (channel_id,)).fetchone()
            owner_id = channel["owner_id"] if channel else rule["user_id"]
            if owner_id:
                con.execute(
                    "INSERT INTO notifications(id,user_id,kind,text,target_id,created_at) VALUES (?,?,?,?,?,?)",
                    (uid("notice"), owner_id, "ai_moderation", f"ИИ-модерация: {decision} в «{channel['title'] if channel else channel_id}»: {str(reason or 'без причины')[:240]}", target_id, now()),
                )

    def process_ai_agent_comment_moderation(self, con):
        rules = con.execute("SELECT * FROM ai_agent_comment_moderation_rules").fetchall()
        semantic_budget = 5
        for rule in rules:
            if self.chat_member_role(con, rule["channel_id"], rule["user_id"]) not in CHANNEL_MANAGER_ROLES and not self.can_manage_group_messages(con, rule["user_id"], rule["channel_id"]):
                continue
            chat = con.execute("SELECT type FROM chats WHERE id = ?", (rule["channel_id"],)).fetchone()
            if not chat:
                continue
            words = [str(word).casefold() for word in loads(rule["blocked_words_json"], []) if str(word).strip()]
            semantic_rules = [str(item) for item in loads(rule["semantic_rules_json"], []) if str(item).strip()]
            model_profile = self.ai_agent_settings(con, rule["user_id"])["modelProfile"]
            requested_scope = str(rule["target_scope"] or "").casefold()
            scope = requested_scope if requested_scope in {"comments", "messages", "all"} else "comments"
            candidates = []
            if scope in {"comments", "all"}:
                candidates.extend(("comment", row["id"], row["text"]) for row in con.execute(
                    """SELECT cc.id, cc.text FROM channel_comments cc JOIN messages m ON m.id = cc.message_id
                       WHERE m.chat_id = ? AND NOT EXISTS(
                           SELECT 1 FROM ai_agent_moderated_comments amc
                           WHERE amc.comment_id = 'comment:' || cc.id
                       ) LIMIT 100""",
                    (rule["channel_id"],),
                ).fetchall())
            if scope in {"messages", "all"} and chat["type"] in {"channel", "group", "community"}:
                candidates.extend(("message", row["id"], row["text"]) for row in con.execute(
                    """SELECT m.id, m.text FROM messages m
                       WHERE m.chat_id = ? AND m.deleted_by_admin = 0 AND m.media_type != 'system'
                         AND NOT EXISTS(
                             SELECT 1 FROM ai_agent_moderated_comments amc
                             WHERE amc.comment_id = 'message:' || m.id
                         ) LIMIT 100""",
                    (rule["channel_id"],),
                ).fetchall())
            for target_type, target_id, target_text in candidates:
                marker = f"{target_type}:{target_id}"
                if con.execute("SELECT 1 FROM ai_agent_moderated_comments WHERE comment_id = ?", (marker,)).fetchone():
                    continue
                matched_word = next((word for word in words if word in str(target_text or "").casefold()), None)
                if matched_word:
                    decision = rule["action_mode"] if rule["action_mode"] in {"delete", "review"} else "delete"
                    reason = f"Совпадение с правилом: {matched_word}"
                    confidence = 1.0
                elif rule["ai_enabled"] and semantic_rules:
                    if semantic_budget <= 0:
                        continue
                    semantic_budget -= 1
                    decision, reason, confidence = self.ai_agent_semantic_moderation(target_text, semantic_rules, model_profile)
                    if decision == "allow":
                        con.execute("INSERT OR IGNORE INTO ai_agent_moderated_comments(comment_id,user_id,moderated_at) VALUES (?,?,?)", (marker, rule["user_id"], now()))
                        continue
                else:
                    con.execute("INSERT OR IGNORE INTO ai_agent_moderated_comments(comment_id,user_id,moderated_at) VALUES (?,?,?)", (marker, rule["user_id"], now()))
                    continue
                self.record_ai_moderation_event(con, rule, rule["channel_id"], target_type, target_id, target_text, decision, reason, confidence)
                if decision == "delete":
                    if target_type == "comment":
                        con.execute("DELETE FROM channel_comments WHERE id = ?", (target_id,))
                    else:
                        con.execute("UPDATE messages SET deleted_by_admin = 1 WHERE id = ?", (target_id,))
                con.execute("INSERT OR IGNORE INTO ai_agent_moderated_comments(comment_id,user_id,moderated_at) VALUES (?,?,?)", (marker, rule["user_id"], now()))

    def update_chat_activity(self, con, user, body):
        chat_id = str(body.get("chatId", "")).strip()
        activity = str(body.get("activity", "")).strip()
        if activity not in {"typing", "recording", "sending", ""}:
            raise ValueError("Неизвестный статус активности.")
        chat = con.execute("SELECT type FROM chats WHERE id = ?", (chat_id,)).fetchone()
        if not chat or chat["type"] != "direct" or not self.has_chat_access(con, user["id"], chat_id):
            raise PermissionError()
        key = (chat_id, user["id"])
        with chat_activities_lock:
            if activity:
                chat_activities[key] = (activity, time.monotonic() + CHAT_ACTIVITY_TTL)
            else:
                chat_activities.pop(key, None)
        return self.json({"ok": True})

    def schedule_channel_post(self, con, user, body):
        chat_id = str(body.get("chatId", ""))
        publish_at = int(body.get("publishAt", 0) or 0)
        text = str(body.get("text", "")).strip()
        media_type = str(body.get("mediaType", "")).strip() or None
        media_data = str(body.get("mediaData", "")) or None
        chat = con.execute("SELECT type FROM chats WHERE id = ?", (chat_id,)).fetchone()
        if not chat or chat["type"] != "channel" or self.chat_member_role(con, chat_id, user["id"]) not in CHANNEL_MANAGER_ROLES:
            raise PermissionError("Планировать публикации могут только создатель и администраторы канала.")
        if not text and not media_data:
            raise ValueError("Пост должен содержать текст или фото.")
        if publish_at <= now():
            raise ValueError("Укажите будущие дату и время публикации.")
        if media_data and (media_type != "photo" or not media_data.startswith("data:image/") or len(media_data) > 5_000_000):
            raise ValueError("Для отложенного поста доступно фото до 3,5 МБ.")
        con.execute("INSERT INTO scheduled_posts(id,chat_id,sender_id,text,media_type,media_data,publish_at,created_at) VALUES (?,?,?,?,?,?,?,?)", (uid("scheduled"), chat_id, user["id"], text, media_type, media_data, publish_at, now()))
        return self.json({"ok": True})

    def update_channel_link(self, con, user, body):
        channel_id = str(body.get("channelId", ""))
        target_chat_id = str(body.get("targetChatId", ""))
        channel = con.execute("SELECT type FROM chats WHERE id = ?", (channel_id,)).fetchone()
        target = con.execute("SELECT type FROM chats WHERE id = ?", (target_chat_id,)).fetchone() if target_chat_id else None
        if not channel or channel["type"] != "channel" or self.chat_member_role(con, channel_id, user["id"]) not in CHANNEL_MANAGER_ROLES:
            raise PermissionError("Привязать беседу может только создатель или администратор канала.")
        if not target_chat_id:
            con.execute("DELETE FROM channel_links WHERE channel_id = ?", (channel_id,))
            return self.json({"ok": True})
        if not target or target["type"] not in {"group", "community"} or self.chat_member_role(con, target_chat_id, user["id"]) not in {"owner", "admin"}:
            raise ValueError("Можно привязать только группу или беседу, которой вы управляете.")
        con.execute("INSERT OR REPLACE INTO channel_links(channel_id,target_chat_id,created_at) VALUES (?,?,?)", (channel_id, target_chat_id, now()))
        return self.json({"ok": True})

    def update_telegram_channel_link(self, con, user, body):
        channel_id = str(body.get("channelId", "")).strip()
        disconnect = bool(body.get("disconnect"))
        channel = con.execute("SELECT owner_id, type FROM chats WHERE id = ?", (channel_id,)).fetchone()
        if not channel or channel["type"] != "channel" or channel["owner_id"] != user["id"]:
            raise PermissionError("Подключить Telegram может только создатель канала.")
        if disconnect:
            con.execute("DELETE FROM telegram_channel_links WHERE channel_id = ?", (channel_id,))
            return self.json({"ok": True, "connected": False})
        if not con.execute("SELECT 1 FROM telegram_channel_links WHERE channel_id = ?", (channel_id,)).fetchone():
            self.enforce_autopost_source_limit(con, user["id"], channel_id)
        source_ref = str(body.get("sourceChat", "")).strip()
        bot_token = str(body.get("botToken", "")).strip()
        if not re.fullmatch(r"@[A-Za-z0-9_]{5,64}|-?\d{5,20}", source_ref):
            raise ValueError("Укажите @username исходного канала или его числовой ID.")
        if not re.fullmatch(r"\d{6,12}:[A-Za-z0-9_-]{20,80}", bot_token):
            raise ValueError("Введите корректный токен Telegram Bot API.")
        bot = telegram_api(bot_token, "getMe")
        source_chat = telegram_api(bot_token, "getChat", {"chat_id": source_ref})
        source_chat_id = str(source_chat.get("id", ""))
        bot_id = int(bot.get("id", 0) or 0)
        if not source_chat_id or not bot_id:
            raise ValueError("Telegram не вернул данные бота или исходного канала.")
        bot_membership = telegram_api(bot_token, "getChatMember", {"chat_id": source_chat_id, "user_id": bot_id})
        if str(bot_membership.get("status", "")) not in {"administrator", "creator"}:
            raise ValueError("Добавьте бота администратором исходного Telegram-канала и повторите попытку.")
        con.execute(
            """INSERT INTO telegram_channel_links(channel_id,source_chat_ref,source_chat_id,bot_token,last_update_id,next_poll_at,last_sync_at,last_error,created_by,created_at)
               VALUES (?,?,?,?,0,0,NULL,NULL,?,?)
               ON CONFLICT(channel_id) DO UPDATE SET source_chat_ref=excluded.source_chat_ref, source_chat_id=excluded.source_chat_id,
                   bot_token=excluded.bot_token, last_update_id=0, next_poll_at=0, last_sync_at=NULL, last_error=NULL,
                   created_by=excluded.created_by, created_at=excluded.created_at""",
            (channel_id, source_ref.lower() if source_ref.startswith("@") else source_ref, source_chat_id, bot_token, user["id"], now()),
        )
        return self.json({"ok": True, "connected": True})

    def update_rss_channel_link(self, con, user, body):
        channel_id = str(body.get("channelId", "")).strip()
        source_id = str(body.get("sourceId", "")).strip()
        channel = con.execute("SELECT owner_id, type FROM chats WHERE id = ?", (channel_id,)).fetchone()
        if not channel or channel["type"] != "channel" or channel["owner_id"] != user["id"]:
            raise PermissionError("Подключить RSS может только создатель канала.")
        if bool(body.get("disconnect")):
            if not source_id:
                raise ValueError("Не выбран RSS-источник для отключения.")
            deleted = con.execute("DELETE FROM rss_channel_sources WHERE id = ? AND channel_id = ?", (source_id, channel_id)).rowcount
            if not deleted:
                raise ValueError("RSS-источник не найден.")
            return self.json({"ok": True, "connected": False})
        self.enforce_autopost_source_limit(con, user["id"], channel_id)
        count = con.execute("SELECT count(*) FROM rss_channel_sources WHERE channel_id = ?", (channel_id,)).fetchone()[0]
        feed_url = validate_rss_url(body.get("feedUrl"))
        feed_title, entries = fetch_rss_feed(feed_url)
        current = now()
        existing = con.execute("SELECT id FROM rss_channel_sources WHERE channel_id = ? AND feed_url = ?", (channel_id, feed_url)).fetchone()
        if existing:
            raise ValueError("Этот RSS-источник уже подключён к каналу.")
        source_id = uid("rss")
        con.execute(
            """INSERT INTO rss_channel_sources(id,channel_id,feed_url,feed_title,next_poll_at,last_sync_at,last_error,created_by,created_at)
               VALUES (?,?,?,?,?,?,NULL,?,?)""",
            (source_id, channel_id, feed_url, feed_title, current + RSS_POLL_INTERVAL, current, user["id"], current),
        )
        con.executemany(
            "INSERT OR IGNORE INTO rss_source_imported_posts(source_id,entry_id,imported_at) VALUES (?,?,?)",
            [(source_id, entry["id"], current) for entry in entries],
        )
        return self.json({"ok": True, "connected": True, "sourceId": source_id, "feedTitle": feed_title})

    def vk_proposed_posts(self, con, user, method, query, body):
        if method == "GET":
            channel_id = str((query.get("channelId", [""]) or [""])[0]).strip()
            if not channel_id or not self.has_chat_access(con, user["id"], channel_id):
                raise PermissionError("Нет доступа к этому каналу.")
            manager = self.can_manage_group_messages(con, user["id"], channel_id)
            if manager:
                rows = con.execute(
                    """SELECT p.*, s.source_title, u.name AS proposer_name, u.username AS proposer_username
                       FROM vk_proposed_posts p
                       JOIN vk_channel_sources s ON s.id = p.source_id
                       JOIN users u ON u.id = p.proposer_id
                       WHERE p.channel_id = ? ORDER BY p.created_at DESC LIMIT 100""",
                    (channel_id,),
                ).fetchall()
            else:
                rows = con.execute(
                    """SELECT p.*, s.source_title, u.name AS proposer_name, u.username AS proposer_username
                       FROM vk_proposed_posts p
                       JOIN vk_channel_sources s ON s.id = p.source_id
                       JOIN users u ON u.id = p.proposer_id
                       WHERE p.channel_id = ? AND p.proposer_id = ?
                       ORDER BY p.created_at DESC LIMIT 50""",
                    (channel_id, user["id"]),
                ).fetchall()
            return self.json({"ok": True, "proposals": [dict(row) for row in rows], "canResolve": manager})
        source_id = str(body.get("sourceId", "")).strip()
        text = " ".join(str(body.get("text", "") or "").split())[:10_000]
        source = con.execute("SELECT * FROM vk_channel_sources WHERE id = ?", (source_id,)).fetchone()
        if not source or not self.has_chat_access(con, user["id"], source["channel_id"]):
            raise PermissionError("Нет доступа к выбранному VK-источнику.")
        if not source["publish_enabled"]:
            raise ValueError("Публикация в этом VK-источнике отключена администратором.")
        if not text:
            raise ValueError("Заявка должна содержать текст.")
        pending_count = con.execute(
            "SELECT count(*) FROM vk_proposed_posts WHERE source_id = ? AND proposer_id = ? AND status = 'pending'",
            (source_id, user["id"]),
        ).fetchone()[0]
        if pending_count >= 10:
            raise ValueError("У вас уже 10 заявок на проверке для этого VK-источника.")
        proposal_id = uid("vk_proposal")
        timestamp = now()
        con.execute(
            """INSERT INTO vk_proposed_posts(id,source_id,channel_id,proposer_id,text,status,created_at)
               VALUES (?,?,?,?,?,'pending',?)""",
            (proposal_id, source_id, source["channel_id"], user["id"], text, timestamp),
        )
        channel = con.execute("SELECT title, owner_id FROM chats WHERE id = ?", (source["channel_id"],)).fetchone()
        if channel and channel["owner_id"] and channel["owner_id"] != user["id"]:
            con.execute(
                "INSERT INTO notifications(id,user_id,kind,text,target_id,created_at) VALUES (?,?,?,?,?,?)",
                (uid("notice"), channel["owner_id"], "vk_proposal", f"Новая заявка на публикацию в VK для «{channel['title']}».", proposal_id, timestamp),
            )
        self.ai_agent_action_log(con, user["id"], "vk_proposed_post", "pending", "Заявка на публикацию в VK отправлена на проверку.", {"proposalId": proposal_id, "sourceId": source_id})
        return self.json({"ok": True, "proposalId": proposal_id, "message": "Заявка отправлена на проверку администратору VK-источника."})

    def resolve_vk_proposed_post(self, con, user, body):
        proposal_id = str(body.get("proposalId", "")).strip()
        decision = str(body.get("decision", "")).strip().casefold()
        if not proposal_id or decision not in {"approve", "reject"}:
            raise ValueError("Укажите заявку и решение approve или reject.")
        proposal = con.execute(
            "SELECT p.*, s.access_token, s.owner_id, s.source_title, s.publish_enabled FROM vk_proposed_posts p JOIN vk_channel_sources s ON s.id = p.source_id WHERE p.id = ? AND p.status = 'pending'",
            (proposal_id,),
        ).fetchone()
        if not proposal or not self.can_manage_group_messages(con, user["id"], proposal["channel_id"]):
            raise PermissionError("У вас нет права принять это решение или заявка уже обработана.")
        timestamp = now()
        if decision == "reject":
            rejected = con.execute(
                "UPDATE vk_proposed_posts SET status = 'rejected', decision_reason = ?, reviewed_by = ?, reviewed_at = ? WHERE id = ? AND status = 'pending'",
                ("Отклонено администратором", user["id"], timestamp, proposal_id),
            ).rowcount
            if not rejected:
                raise PermissionError("У вас нет права принять это решение или заявка уже обработана.")
            self.ai_agent_action_log(con, user["id"], "vk_proposed_post", "rejected", "Заявка на публикацию в VK отклонена.", {"proposalId": proposal_id})
            return self.json({"ok": True, "status": "rejected", "message": "Заявка отклонена."})
        if not proposal["publish_enabled"]:
            raise ValueError("Публикация в этом VK-источнике отключена.")
        claimed = con.execute(
            "UPDATE vk_proposed_posts SET status = 'publishing', decision_reason = ?, reviewed_by = ?, reviewed_at = ?, last_error = NULL WHERE id = ? AND status = 'pending'",
            ("Одобрено администратором, публикация выполняется", user["id"], timestamp, proposal_id),
        ).rowcount
        if not claimed:
            raise PermissionError("У вас нет права принять это решение или заявка уже обрабатывается.")
        con.commit()
        try:
            result = vk_api(proposal["access_token"], "wall.post", {"owner_id": proposal["owner_id"], "message": proposal["text"]})
            vk_post_id = int(result.get("post_id", 0) or 0) if isinstance(result, dict) else int(result or 0)
            if not vk_post_id:
                raise ValueError("VK не вернул ID опубликованного поста.")
        except (ValueError, TypeError) as error:
            con.execute(
                "UPDATE vk_proposed_posts SET status = 'failed', last_error = ?, reviewed_by = ?, reviewed_at = ? WHERE id = ? AND status = 'publishing'",
                (str(error)[:300], user["id"], timestamp, proposal_id),
            )
            self.ai_agent_action_log(con, user["id"], "vk_proposed_post", "failed", "Публикация заявки в VK не удалась.", {"proposalId": proposal_id}, str(error)[:500])
            return self.json({"ok": False, "status": "failed", "error": "VK не принял публикацию. Заявка отмечена как failed."}, HTTPStatus.BAD_GATEWAY)
        con.execute(
            "UPDATE vk_proposed_posts SET status = 'published', vk_post_id = ?, decision_reason = ?, reviewed_by = ?, reviewed_at = ?, published_at = ?, last_error = NULL WHERE id = ? AND status = 'publishing'",
            (vk_post_id, "Одобрено и опубликовано администратором", user["id"], timestamp, timestamp, proposal_id),
        )
        self.ai_agent_action_log(con, user["id"], "vk_proposed_post", "published", f"Заявка опубликована в VK-группе «{proposal['source_title']}».", {"proposalId": proposal_id, "vkPostId": vk_post_id})
        return self.json({"ok": True, "status": "published", "vkPostId": vk_post_id, "message": "Заявка одобрена и опубликована в VK."})

    def update_vk_channel_link(self, con, user, body):
        channel_id = str(body.get("channelId", "")).strip()
        source_id = str(body.get("sourceId", "")).strip()
        channel = con.execute("SELECT owner_id, type FROM chats WHERE id = ?", (channel_id,)).fetchone()
        if not channel or channel["type"] != "channel" or channel["owner_id"] != user["id"]:
            raise PermissionError("Подключить VK может только создатель канала.")
        if bool(body.get("settingsOnly")):
            if not source_id:
                raise ValueError("Не выбран VK-источник для настройки.")
            source = con.execute("SELECT id FROM vk_channel_sources WHERE id = ? AND channel_id = ?", (source_id, channel_id)).fetchone()
            if not source:
                raise ValueError("VK-источник не найден.")
            con.execute(
                "UPDATE vk_channel_sources SET publish_enabled = ?, moderation_enabled = ? WHERE id = ? AND channel_id = ?",
                (1 if body.get("publishEnabled", True) else 0, 1 if body.get("moderationEnabled", False) else 0, source_id, channel_id),
            )
            return self.json({"ok": True, "sourceId": source_id})
        if bool(body.get("disconnect")):
            if not source_id:
                raise ValueError("Не выбран VK-источник для отключения.")
            deleted = con.execute("DELETE FROM vk_channel_sources WHERE id = ? AND channel_id = ?", (source_id, channel_id)).rowcount
            if not deleted:
                raise ValueError("VK-источник не найден.")
            return self.json({"ok": True, "connected": False})
        self.enforce_autopost_source_limit(con, user["id"], channel_id)
        count = con.execute("SELECT count(*) FROM vk_channel_sources WHERE channel_id = ?", (channel_id,)).fetchone()[0]
        access_token = VK_ID_SERVICE_TOKEN
        if len(access_token) < 20 or len(access_token) > 512:
            raise ValueError("На сервере не настроен ключ VK для чтения публичных групп. Обратитесь к администратору.")
        source_url, source_ref = validate_vk_group_url(body.get("sourceUrl"))
        keywords = normalize_vk_keywords(body.get("keywords", ""))
        existing = con.execute("SELECT id FROM vk_channel_sources WHERE channel_id = ? AND source_url = ?", (channel_id, source_url)).fetchone()
        if existing:
            raise ValueError("Эта VK-группа уже подключена к каналу.")
        owner_id, source_title = vk_group_data(access_token, source_ref)
        wall = vk_api(access_token, "wall.get", {"owner_id": owner_id, "count": 30, "filter": "owner"})
        posts = wall.get("items", []) if isinstance(wall, dict) else []
        current = now()
        source_id = uid("vk")
        con.execute(
            """INSERT INTO vk_channel_sources(id,channel_id,source_url,source_ref,source_title,owner_id,access_token,keywords_json,next_poll_at,last_sync_at,last_error,created_by,created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,NULL,?,?)""",
            (source_id, channel_id, source_url, source_ref, source_title, owner_id, access_token, dumps(keywords), current + VK_POLL_INTERVAL, current, user["id"], current),
        )
        con.executemany(
            "INSERT OR IGNORE INTO vk_source_imported_posts(source_id,post_id,imported_at) VALUES (?,?,?)",
            [(source_id, int(post.get("id", 0)), current) for post in posts if isinstance(post, dict) and int(post.get("id", 0) or 0)],
        )
        return self.json({"ok": True, "connected": True, "sourceId": source_id, "sourceTitle": source_title})

    def update_vk_channel_target(self, con, user, body):
        channel_id = str(body.get("channelId", "")).strip()
        target_id = str(body.get("targetId", "")).strip()
        channel = con.execute("SELECT owner_id, type FROM chats WHERE id = ?", (channel_id,)).fetchone()
        if not channel or channel["type"] != "channel" or channel["owner_id"] != user["id"]:
            raise PermissionError("Подключать сообщество VK может только создатель канала.")
        if bool(body.get("settingsOnly")):
            if not target_id:
                raise ValueError("Не выбрано сообщество VK для настройки.")
            changed = con.execute(
                "UPDATE vk_channel_targets SET publish_enabled = ?, moderation_enabled = ? WHERE id = ? AND channel_id = ?",
                (1 if body.get("publishEnabled", True) else 0, 1 if body.get("moderationEnabled", False) else 0, target_id, channel_id),
            ).rowcount
            if not changed:
                raise ValueError("Сообщество VK не найдено.")
            return self.json({"ok": True, "targetId": target_id})
        if bool(body.get("disconnect")):
            if not target_id:
                raise ValueError("Не выбрано сообщество VK для отключения.")
            if not con.execute("DELETE FROM vk_channel_targets WHERE id = ? AND channel_id = ?", (target_id, channel_id)).rowcount:
                raise ValueError("Сообщество VK не найдено.")
            return self.json({"ok": True, "connected": False})
        access_token = str(body.get("accessToken", "")).strip()
        if len(access_token) < 20 or len(access_token) > 512:
            raise ValueError("Укажите ключ доступа сообщества VK.")
        target_url, target_ref = validate_vk_group_url(body.get("targetUrl"))
        if con.execute("SELECT 1 FROM vk_channel_targets WHERE channel_id = ? AND target_url = ?", (channel_id, target_url)).fetchone():
            raise ValueError("Это сообщество VK уже подключено к каналу.")
        owner_id, target_title = vk_group_data(access_token, target_ref)
        vk_api(access_token, "wall.get", {"owner_id": owner_id, "count": 1, "filter": "owner"})
        current = now()
        target_id = uid("vk_target")
        con.execute(
            """INSERT INTO vk_channel_targets(id,channel_id,target_url,target_ref,target_title,owner_id,access_token,publish_enabled,moderation_enabled,last_publish_at,last_moderation_sync_at,last_error,created_by,created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,NULL,?,?)""",
            (target_id, channel_id, target_url, target_ref, target_title, owner_id, access_token, 1 if body.get("publishEnabled", True) else 0, 1 if body.get("moderationEnabled", False) else 0, None, None, user["id"], current),
        )
        return self.json({"ok": True, "connected": True, "targetId": target_id, "targetTitle": target_title})

    def update_channel_appearance(self, con, user, body):
        channel_id = str(body.get("channelId", "")).strip()
        chat = con.execute("SELECT type, settings_json FROM chats WHERE id = ?", (channel_id,)).fetchone()
        if not chat or chat["type"] != "channel" or self.chat_member_role(con, channel_id, user["id"]) not in CHANNEL_MANAGER_ROLES:
            raise PermissionError("Оформление могут менять только создатель и администраторы канала.")
        settings = loads(chat["settings_json"], {}) or {}
        if bool(body.get("reset")):
            settings.pop("appearance", None)
            con.execute("UPDATE chats SET settings_json = ?, updated_at = ? WHERE id = ?", (dumps(settings), now(), channel_id))
            return self.json({"ok": True})
        appearance = body.get("appearance", {})
        if not isinstance(appearance, dict):
            raise ValueError("Оформление канала должно быть объектом.")
        wallpaper = str(appearance.get("wallpaper", "default"))
        allowed_wallpapers = {"default", "whatsapp", "mint", "aurora", "noir", "cyan", "mist", "sunset", "ocean", "lavender", "forest", "midnight", "ember", "iris", "custom"}
        if wallpaper not in allowed_wallpapers:
            raise ValueError("Выберите допустимый фон канала.")
        background_data = str(appearance.get("backgroundData", "")) or None
        if wallpaper == "custom":
            if not background_data.startswith("data:image/") or len(background_data) > 3_500_000:
                raise ValueError("Загрузите фоновое изображение до 2,5 МБ.")
        else:
            background_data = None
        colors = {key: str(appearance.get(key, "")) for key in ("ownBubble", "otherBubble", "panelColor") if appearance.get(key)}
        if any(not re.fullmatch(r"#[0-9a-fA-F]{6}", color) for color in colors.values()):
            raise ValueError("Цвета оформления должны быть в формате #RRGGBB.")
        font = str(appearance.get("font", ""))
        if font and font not in {"system", "business", "classic", "script", "rounded", "serif", "mono", "humanist", "condensed", "typewriter", "elegant"}:
            raise ValueError("Выберите допустимый шрифт канала.")
        settings["appearance"] = {"wallpaper": wallpaper, "backgroundData": background_data, **colors, **({"font": font} if font else {})}
        con.execute("UPDATE chats SET settings_json = ?, updated_at = ? WHERE id = ?", (dumps(settings), now(), channel_id))
        return self.json({"ok": True})

    def add_channel_comment(self, con, user, body):
        message_id = str(body.get("messageId", ""))
        text = str(body.get("text", "")).strip()
        media_data = str(body.get("mediaData", ""))
        message = con.execute(
            "SELECT m.chat_id, c.settings_json FROM messages m JOIN chats c ON c.id = m.chat_id WHERE m.id = ? AND c.type IN ('channel', 'group', 'community')",
            (message_id,),
        ).fetchone()
        if not message or not self.has_chat_access(con, user["id"], message["chat_id"]):
            raise PermissionError("Нет доступа к публикации.")
        if not loads(message["settings_json"], {}).get("commentsEnabled", True):
            raise PermissionError("Комментарии отключены автором чата.")
        if (not text and not media_data) or len(text) > 1000:
            raise ValueError("Комментарий должен содержать текст до 1000 символов или фото.")
        if media_data and (not media_data.startswith("data:image/") or len(media_data) > 2_500_000):
            raise ValueError("К комментарию можно прикрепить изображение PNG, JPG или WebP до 1,8 МБ.")
        con.execute("INSERT INTO channel_comments(id,message_id,user_id,text,media_data,created_at) VALUES (?,?,?,?,?,?)", (uid("comment"), message_id, user["id"], text, media_data or None, now()))
        return self.json({"ok": True})

    def delete_channel_comment(self, con, user, body):
        comment_id = str(body.get("commentId", "")).strip()
        comment = con.execute("SELECT cc.user_id, m.chat_id FROM channel_comments cc JOIN messages m ON m.id = cc.message_id WHERE cc.id = ?", (comment_id,)).fetchone()
        if not comment or not self.has_chat_access(con, user["id"], comment["chat_id"]):
            raise PermissionError("Комментарий не найден или недоступен.")
        if user["id"] != comment["user_id"] and self.chat_member_role(con, comment["chat_id"], user["id"]) not in {"owner", "admin"}:
            raise PermissionError("Удалить комментарий может его автор, создатель или администратор канала.")
        con.execute("DELETE FROM channel_comments WHERE id = ?", (comment_id,))
        return self.json({"ok": True})

    def create_automated_commenter(self, con, body):
        name = " ".join(str(body.get("name", "")).strip().split())[:80]
        if not name:
            raise ValueError("Введите имя автокомментатора.")
        username = normalize_username(body.get("username"))
        validate_username(username)
        if username_taken(con, username):
            raise ValueError("Этот логин уже занят. Выберите другой.")
        password = str(body.get("password", ""))
        if len(password) < 8:
            raise ValueError("Пароль должен содержать не менее 8 символов.")
        avatar_data = str(body.get("avatarData", "") or "")
        if avatar_data and (not avatar_data.startswith("data:image/") or len(avatar_data) > 2_500_000):
            raise ValueError("Аватар должен быть изображением PNG, JPG или WebP до 1,8 МБ.")
        user_id = uid("user")
        current = now()
        appearance = dialog_appearance_defaults(con)
        con.execute(
            """INSERT INTO users(id,name,username,password,stars,theme,dialog_color,other_dialog_color,dialog_panel_color,dialog_panel_style,dialog_bubble_style,dialog_font,text_scale,chat_background,chat_background_data,avatar_data,created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (user_id, name, username, hash_password(password), 0, *(appearance[field] for field in DIALOG_APPEARANCE_FIELDS), avatar_data or None, current),
        )
        commenter_id = uid("autocommenter")
        con.execute("INSERT INTO automated_commenters(id,user_id,created_at) VALUES (?,?,?)", (commenter_id, user_id, current))
        return self.json({"ok": True, "commenterId": commenter_id})

    def update_automated_commenter(self, con, body):
        commenter_id = str(body.get("commenterId", "")).strip()
        name = " ".join(str(body.get("name", "")).strip().split())[:80]
        avatar_data = str(body.get("avatarData", "") or "")
        commenter = con.execute("SELECT user_id FROM automated_commenters WHERE id = ?", (commenter_id,)).fetchone()
        if not commenter:
            raise ValueError("Автокомментатор не найден.")
        if not name:
            raise ValueError("Введите имя автокомментатора.")
        if avatar_data and (not avatar_data.startswith("data:image/") or len(avatar_data) > 2_500_000):
            raise ValueError("Аватар должен быть изображением PNG, JPG или WebP до 1,8 МБ.")
        con.execute("UPDATE users SET name = ?, avatar_data = ? WHERE id = ?", (name, avatar_data or None, commenter["user_id"]))
        return self.json({"ok": True})

    def create_automated_commenter_pool(self, con):
        existing = con.execute("SELECT count(*) AS count FROM automated_commenters").fetchone()["count"]
        to_create = max(0, 100 - int(existing))
        if not to_create:
            return self.json({"ok": True, "created": 0, "total": existing})
        current = now()
        names = [
            "Алекс", "Уля", "Арт", "Лера", "Даня", "Саша", "Мила", "Ник", "Соня", "Тим",
            "Вика", "Егор", "Алиса", "Кир", "Полина", "Марк", "Алина", "Глеб", "Настя", "Рома",
            "Яна", "Макс", "Ксю", "Даша", "Лина", "Женя", "Миша", "Тая", "Стас", "Влад",
            "Рина", "Лёша", "Ника", "Вера", "Оля", "Илья", "Ася", "Паша", "Адольф",
            "Алекс Морозов", "Уля Белова", "Арт Лисов", "Лера Соколова", "Даня Крылов", "Мила Рэй",
            "Ник Орлов", "Соня Лайт", "Тим Ковалёв", "Вика Мэй", "Егор Ветров", "Алиса Нова",
            "Кир Волков", "Полина Скай", "Марк Левин", "Алина Фокс", "Глеб Север", "Настя Роу",
            "Рома Дэн", "Яна Вэй",
            "Геркулес", "Джин", "Хорошая девочка", "Жан-Клод Ван Дамм", "Джеки Чан", "Люкс Авто МСК",
            "Sherlock Holmes", "Luna Lovegood", "Tony Stark", "Harley Quinn", "Neo", "Trinity", "Loki", "Thor",
            "Wonder Woman", "Batman", "Black Panther", "Spiderman", "Catwoman", "Sonic", "Zelda", "Mario",
            "Pikachu", "Wolverine", "Deadpool", "Iron Man", "Doctor Strange", "Obi-Wan Kenobi", "Princess Leia",
            "Indiana Jones", "Lara Croft", "Jack Sparrow", "Wednesday Addams", "Eleven", "The Joker",
            "Daenerys Stormborn", "Geralt of Rivia", "Yennefer", "Hermione Granger", "Mr Bean", "Maverick",
        ]
        for position in range(to_create):
            number = int(existing) + position + 1
            username = f"channel_reader_{number:03d}"
            while username_taken(con, username):
                number += 100
                username = f"channel_reader_{number:03d}"
            user_id = uid("user")
            appearance = dialog_appearance_defaults(con)
            con.execute(
                """INSERT INTO users(id,name,username,password,stars,theme,dialog_color,other_dialog_color,dialog_panel_color,dialog_panel_style,dialog_bubble_style,dialog_font,text_scale,chat_background,chat_background_data,created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (user_id, names[position % len(names)], username, hash_password(secrets.token_urlsafe(32)), 0,
                 *(appearance[field] for field in DIALOG_APPEARANCE_FIELDS), current),
            )
            con.execute("INSERT INTO automated_commenters(id,user_id,created_at) VALUES (?,?,?)", (uid("autocommenter"), user_id, current))
        return self.json({"ok": True, "created": to_create, "total": int(existing) + to_create})

    def reset_automated_commenter_password(self, con, body):
        commenter_id = str(body.get("commenterId", "")).strip()
        password = str(body.get("password", ""))
        if len(password) < 8:
            raise ValueError("Пароль должен содержать не менее 8 символов.")
        commenter = con.execute("SELECT user_id FROM automated_commenters WHERE id = ?", (commenter_id,)).fetchone()
        if not commenter:
            raise ValueError("Автокомментатор не найден.")
        con.execute("UPDATE users SET password = ? WHERE id = ?", (hash_password(password), commenter["user_id"]))
        return self.json({"ok": True})

    def create_automated_comment_rule(self, con, body):
        channel_id = str(body.get("channelId", ""))
        target_scope = str(body.get("targetScope", "future"))
        target_message_id = str(body.get("targetMessageId", "")).strip() or None
        channel = con.execute("SELECT id FROM chats WHERE id = ? AND type = 'channel'", (channel_id,)).fetchone()
        if not channel:
            raise ValueError("Выберите канал.")
        if target_scope not in {"selected", "existing", "future"}:
            raise ValueError("Выберите, к каким публикациям применять правило.")
        if target_scope == "selected" and not target_message_id:
            raise ValueError("Выберите публикацию.")
        if target_scope != "selected":
            target_message_id = None
        commenter_ids = list(dict.fromkeys(str(item) for item in body.get("commenterIds", []) if item))
        if not commenter_ids or len(commenter_ids) > 100:
            raise ValueError("Выберите от 1 до 100 автокомментаторов.")
        found_commenters = con.execute(
            f"SELECT id FROM automated_commenters WHERE id IN ({','.join('?' for _ in commenter_ids)})",
            commenter_ids,
        ).fetchall()
        if len(found_commenters) != len(commenter_ids):
            raise ValueError("Один из автокомментаторов не найден.")
        requested_mode = str(body.get("commentMode", "ai")).strip()
        if requested_mode not in {"ai", "circle_compliment"}:
            requested_mode = "ai"
        comment_mode = requested_mode
        texts = []
        categories = list(dict.fromkeys(str(category) for category in body.get("categories", []) if str(category) in AUTOMATED_COMMENT_CATEGORIES))
        if not categories:
            categories = ["support", "opinion", "question"]
        if comment_mode == "circle_compliment":
            if len(commenter_ids) != 1:
                raise ValueError("Для комплиментов к видеокружкам выберите одного автокомментатора.")
            if target_scope != "future":
                raise ValueError("Комплименты применяются только к новым видеокружкам.")
        minimum = nonnegative_int(body.get("minDelayMinutes", 5), "minDelayMinutes", 10_080) * 60
        maximum = nonnegative_int(body.get("maxDelayMinutes", 30), "maxDelayMinutes", 10_080) * 60
        if minimum > maximum:
            raise ValueError("Минимальная задержка не может быть больше максимальной.")
        distribution_hours = nonnegative_int(body.get("distributionHours", 12), "distributionHours", 24)
        if not distribution_hours:
            raise ValueError("Укажите окно публикации от 1 до 24 часов.")
        duration_days = nonnegative_int(body.get("durationDays", 2), "durationDays", 30)
        if not duration_days:
            raise ValueError("Укажите срок работы от 1 до 30 дней.")
        current = now()
        if target_message_id:
            target = con.execute(
                "SELECT id FROM messages WHERE id = ? AND chat_id = ? AND media_type != 'system'",
                (target_message_id, channel_id),
            ).fetchone()
            if not target:
                raise ValueError("Выберите публикацию указанного канала.")
        rule_id = uid("autocommentrule")
        con.execute(
            """INSERT INTO automated_comment_rules(id,channel_id,target_message_id,target_scope,commenter_ids_json,texts_json,comment_mode,categories_json,min_delay_seconds,max_delay_seconds,distribution_seconds,starts_at,ends_at,active,created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (rule_id, channel_id, target_message_id, target_scope, dumps(commenter_ids), dumps(texts), comment_mode, dumps(categories), minimum, maximum, distribution_hours * 3600, current, current + duration_days * 86400, 1, current),
        )
        if target_scope == "selected":
            schedule_automated_comments(con, target_message_id, channel_id, current)
        elif target_scope == "existing":
            posts = con.execute("SELECT id FROM messages WHERE chat_id = ? AND media_type != 'system' ORDER BY created_at", (channel_id,)).fetchall()
            for post in posts:
                schedule_automated_comments(con, post["id"], channel_id, current, include_existing=True)
        return self.json({"ok": True, "ruleId": rule_id})

    def edit_message(self, con, user, body):
        message_id = body.get("messageId")
        text = str(body.get("text", "")).strip()
        if not text:
            raise ValueError("Введите текст сообщения.")
        row = con.execute("SELECT id, chat_id, sender_id, media_type FROM messages WHERE id = ?", (message_id,)).fetchone()
        if not row or not self.has_chat_access(con, user["id"], row["chat_id"]):
            raise PermissionError()
        if row["sender_id"] != user["id"] or row["media_type"] == "system":
            raise PermissionError("Редактировать можно только свои сообщения.")
        con.execute("UPDATE messages SET text = ?, edited_at = ? WHERE id = ?", (text, now(), message_id))
        con.execute("UPDATE chats SET updated_at=? WHERE id=?", (now(), row["chat_id"]))
        return self.json({"ok": True})

    def mark_messages_read(self, con, user, chat_id):
        if not self.has_chat_access(con, user["id"], chat_id):
            raise PermissionError()
        latest = con.execute(
            "SELECT COALESCE(MAX(rowid), 0) AS rowid, COALESCE(MAX(created_at), 0) AS created_at FROM messages WHERE chat_id = ? AND sender_id != ?",
            (chat_id, user["id"]),
        ).fetchone()
        con.execute(
            """INSERT INTO chat_read_states(chat_id, user_id, read_at, read_rowid) VALUES (?,?,?,?)
               ON CONFLICT(chat_id, user_id) DO UPDATE SET read_at = excluded.read_at, read_rowid = excluded.read_rowid""",
            (chat_id, user["id"], latest["created_at"], latest["rowid"]),
        )
        return self.json({"ok": True})

    def send_message_media(self, con, user, message_id):
        row = con.execute(
            """SELECT m.media_data FROM messages m
               JOIN chats c ON c.id = m.chat_id
                WHERE m.id = ? AND (
                     EXISTS(SELECT 1 FROM chat_members cm WHERE cm.chat_id = m.chat_id AND cm.user_id = ?)
                     OR (c.type = 'channel' AND COALESCE(json_extract(c.settings_json, '$.isPublic'), 1) = 1)
                   )
                  AND (c.type != 'secret' OR EXISTS(
                    SELECT 1 FROM secret_chat_unlocks scu
                    WHERE scu.chat_id = c.id AND scu.user_id = ?
                 ))""",
            (message_id, user["id"], user["id"]),
        ).fetchone()
        if not row or not row["media_data"]:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        if str(row["media_data"]).startswith("s3:"):
            download_url, _ = s3_presigned_url("GET", str(row["media_data"])[3:], expires_in=300)
            self.send_response(HTTPStatus.FOUND)
            self.send_header("Location", download_url)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            return
        header, separator, encoded = row["media_data"].partition(";base64,")
        if not separator or not header.startswith("data:"):
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            data = base64.b64decode(encoded, validate=True)
        except (ValueError, base64.binascii.Error):
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        content_type = header[5:].split(";", 1)[0]
        start, end = 0, len(data) - 1
        range_header = self.headers.get("Range", "")
        if range_header.startswith("bytes="):
            requested_start, _, requested_end = range_header[6:].partition("-")
            try:
                start = int(requested_start) if requested_start else 0
                end = int(requested_end) if requested_end else end
            except ValueError:
                start, end = 0, len(data) - 1
            start = max(0, start)
            end = min(len(data) - 1, end)
        if start > end:
            self.send_error(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
            return
        partial = range_header.startswith("bytes=")
        self.send_response(HTTPStatus.PARTIAL_CONTENT if partial else HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        if content_type == "application/pdf" or content_type.startswith("text/"):
            self.send_header("Content-Disposition", "inline")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("Cache-Control", "private, max-age=86400")
        if partial:
            self.send_header("Content-Range", f"bytes {start}-{end}/{len(data)}")
        self.end_headers()
        if self.command == "HEAD":
            return
        try:
            self.wfile.write(data[start:end + 1])
        except ConnectionError:
            return

    def toggle_message_pin(self, con, user, message_id):
        message = con.execute("SELECT m.id, m.chat_id, m.pinned, c.type FROM messages m JOIN chats c ON c.id = m.chat_id WHERE m.id = ?", (message_id,)).fetchone()
        if not message:
            raise ValueError("Сообщение не найдено.")
        if not self.has_chat_access(con, user["id"], message["chat_id"]):
            raise PermissionError()
        if message["type"] == "channel" and self.chat_member_role(con, message["chat_id"], user["id"]) not in CHANNEL_MANAGER_ROLES:
            raise PermissionError("Закреплять публикации могут только создатель и администраторы канала.")
        pinned = not bool(message["pinned"])
        con.execute("UPDATE messages SET pinned = ? WHERE id = ?", (pinned, message_id))
        if not pinned:
            con.execute("DELETE FROM hidden_pinned_messages WHERE message_id = ?", (message_id,))
        return self.json({"ok": True, "pinned": pinned})

    def hide_pinned_message(self, con, user, message_id):
        message = con.execute("SELECT id, chat_id, pinned FROM messages WHERE id = ?", (message_id,)).fetchone()
        if not message:
            raise ValueError("Сообщение не найдено.")
        if not bool(message["pinned"]):
            raise ValueError("Это сообщение уже не закреплено.")
        if not self.has_chat_access(con, user["id"], message["chat_id"]):
            raise PermissionError()
        con.execute(
            "INSERT OR IGNORE INTO hidden_pinned_messages(message_id,user_id,created_at) VALUES (?,?,?)",
            (message_id, user["id"], now()),
        )
        return self.json({"ok": True})

    def delete_message(self, con, user, body):
        message_id = body.get("messageId")
        scope = body.get("scope")
        message = con.execute("SELECT id, chat_id, sender_id FROM messages WHERE id = ?", (message_id,)).fetchone()
        if not message:
            raise ValueError("Сообщение не найдено.")
        if not self.has_chat_access(con, user["id"], message["chat_id"]):
            raise PermissionError()
        if scope == "me":
            con.execute("INSERT OR IGNORE INTO hidden_messages(message_id,user_id,created_at) VALUES (?,?,?)", (message_id, user["id"], now()))
            return self.json({"ok": True})
        if scope == "everyone":
            if message["sender_id"] != user["id"] and not self.can_manage_group_messages(con, user["id"], message["chat_id"]):
                raise PermissionError("Удалить сообщение для всех может автор, создатель или администратор беседы.")
            con.execute("DELETE FROM messages WHERE id = ?", (message_id,))
            return self.json({"ok": True})
        raise ValueError("Неизвестный вариант удаления.")

    def bulk_messages(self, con, user, body):
        action = str(body.get("action", ""))
        raw_message_ids = body.get("messageIds", [])
        if not isinstance(raw_message_ids, list):
            raise ValueError("Некорректный список сообщений.")
        message_ids = list(dict.fromkeys(str(message_id) for message_id in raw_message_ids if message_id))
        if not message_ids:
            raise ValueError("Выберите хотя бы одно сообщение.")
        if len(message_ids) > 100:
            raise ValueError("За один раз можно обработать до 100 сообщений.")

        placeholders = ",".join("?" for _ in message_ids)
        messages = con.execute(
            f"""SELECT id, chat_id, sender_id, text, media_type, media_data, circle_preview_data, forwarded_from, forwarded_from_user_id, source_channel_id FROM messages
                WHERE id IN ({placeholders})
                  AND NOT EXISTS(SELECT 1 FROM hidden_messages hm WHERE hm.message_id = messages.id AND hm.user_id = ?)
                ORDER BY created_at, rowid""",
            [*message_ids, user["id"]],
        ).fetchall()
        if len(messages) != len(message_ids):
            raise ValueError("Одно или несколько сообщений не найдены.")
        if any(not self.has_chat_access(con, user["id"], message["chat_id"]) for message in messages):
            raise PermissionError()

        if action == "delete":
            scope = str(body.get("scope", "me"))
            if scope == "everyone":
                if any(
                    message["sender_id"] != user["id"]
                    and not self.can_manage_group_messages(con, user["id"], message["chat_id"])
                    for message in messages
                ):
                    raise PermissionError("Удалить у всех можно свои сообщения или сообщения в управляемой беседе.")
                con.execute(f"DELETE FROM messages WHERE id IN ({placeholders})", message_ids)
                return self.json({"ok": True, "count": len(messages), "scope": scope})
            if scope != "me":
                raise ValueError("Неизвестный вариант удаления.")
            for message in messages:
                con.execute(
                    "INSERT OR IGNORE INTO hidden_messages(message_id,user_id,created_at) VALUES (?,?,?)",
                    (message["id"], user["id"], now()),
                )
            return self.json({"ok": True, "count": len(messages)})

        if action == "forward":
            target_chat_id = str(body.get("targetChatId", ""))
            target = con.execute("SELECT id, type FROM chats WHERE id = ?", (target_chat_id,)).fetchone()
            if not target or target["type"] == "secret" or not self.has_chat_access(con, user["id"], target_chat_id):
                raise PermissionError("Выберите доступный обычный чат.")
            if any(message["chat_id"] == target_chat_id for message in messages):
                raise ValueError("Нельзя переслать сообщения в тот же чат.")
            self.copy_messages(con, user["id"], messages, target_chat_id)
            return self.json({"ok": True, "count": len(messages), "targetChatId": target_chat_id})

        if action == "forward_confidential":
            password = str(body.get("password", ""))
            if not re.fullmatch(r"\d{4}", password):
                raise ValueError("Введите код из 4 цифр.")
            targets = con.execute(
                """SELECT sc.chat_id FROM secret_chats sc
                   JOIN chat_members cm ON cm.chat_id = sc.chat_id
                   WHERE cm.user_id = ? AND sc.password_hash = ?""",
                (user["id"], secret_password_hash(password)),
            ).fetchall()
            if not targets:
                raise ValueError("По данному запросу чатов нет.")
            if len(targets) > 1:
                raise ValueError("По этому коду найдено несколько чатов. Выберите другой код.")
            target_chat_id = targets[0]["chat_id"]
            if any(message["chat_id"] == target_chat_id for message in messages):
                raise ValueError("Нельзя переслать сообщения в тот же чат.")
            con.execute("INSERT OR REPLACE INTO secret_chat_unlocks(chat_id,user_id,unlocked_at) VALUES (?,?,?)", (target_chat_id, user["id"], now()))
            self.copy_messages(con, user["id"], messages, target_chat_id)
            return self.json({"ok": True, "count": len(messages), "targetChatId": target_chat_id})

        if action == "move_confidential":
            password = str(body.get("password", ""))
            recipient_id = str(body.get("recipientUserId", ""))
            if not re.fullmatch(r"\d{4}", password):
                raise ValueError("Введите пароль из 4 цифр.")
            if not recipient_id or recipient_id == user["id"]:
                raise ValueError("Выберите собеседника.")
            is_direct_contact = con.execute(
                """SELECT 1 FROM chats c
                   JOIN chat_members own_member ON own_member.chat_id = c.id
                   JOIN chat_members contact_member ON contact_member.chat_id = c.id
                   WHERE c.type = 'direct' AND own_member.user_id = ? AND contact_member.user_id = ?
                   LIMIT 1""",
                (user["id"], recipient_id),
            ).fetchone()
            if not is_direct_contact:
                raise ValueError("Собеседник должен быть в ваших личных диалогах.")

            password_hash = secret_password_hash(password)
            target = con.execute(
                """SELECT c.id FROM chats c
                   JOIN secret_chats sc ON sc.chat_id = c.id
                   JOIN chat_members own_member ON own_member.chat_id = c.id AND own_member.user_id = ?
                   JOIN chat_members contact_member ON contact_member.chat_id = c.id AND contact_member.user_id = ?
                   WHERE c.type = 'secret' AND sc.password_hash = ?
                     AND (SELECT count(*) FROM chat_members WHERE chat_id = c.id) = 2
                   ORDER BY c.created_at DESC LIMIT 1""",
                (user["id"], recipient_id, password_hash),
            ).fetchone()
            created = False
            if target:
                target_chat_id = target["id"]
                con.execute(
                    "INSERT OR REPLACE INTO secret_chat_unlocks(chat_id,user_id,unlocked_at) VALUES (?,?,?)",
                    (target_chat_id, user["id"], now()),
                )
            else:
                target_chat_id = uid("chat")
                created = True
                con.execute(
                    "INSERT INTO chats(id,type,title,description,owner_id,settings_json,subscriber_count,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
                    (target_chat_id, "secret", "Скрытый чат", "", user["id"], dumps({"showViews": True, "showSubscribers": False, "showReactions": True}), 2, now(), now()),
                )
                con.execute("INSERT INTO secret_chats(chat_id,password_hash,created_at) VALUES (?,?,?)", (target_chat_id, password_hash, now()))
                for member_id in (user["id"], recipient_id):
                    con.execute(
                        "INSERT INTO chat_members(chat_id,user_id,role,created_at) VALUES (?,?,?,?)",
                        (target_chat_id, member_id, "owner" if member_id == user["id"] else "member", now()),
                    )
                con.execute(
                    "INSERT INTO secret_chat_unlocks(chat_id,user_id,unlocked_at) VALUES (?,?,?)",
                    (target_chat_id, user["id"], now()),
                )
            self.copy_messages(con, user["id"], messages, target_chat_id)
            for message in messages:
                con.execute(
                    "INSERT OR IGNORE INTO hidden_messages(message_id,user_id,created_at) VALUES (?,?,?)",
                    (message["id"], user["id"], now()),
                )
            return self.json({"ok": True, "count": len(messages), "targetChatId": target_chat_id, "created": created})

        raise ValueError("Неизвестное групповое действие.")

    def copy_messages(self, con, sender_id, messages, target_chat_id):
        target = con.execute("SELECT type FROM chats WHERE id = ?", (target_chat_id,)).fetchone()
        source_channel_ids = {message["source_channel_id"] or message["chat_id"] for message in messages}
        source_chats = con.execute(f"SELECT id, type, settings_json FROM chats WHERE id IN ({','.join('?' for _ in source_channel_ids)})", tuple(source_channel_ids)).fetchall()
        if any(row["type"] == "channel" and loads(row["settings_json"], {}).get("protectContent", False) for row in source_chats):
            raise PermissionError("Автор канала запретил пересылку этой публикации.")
        for message in messages:
            if target and target["type"] == "channel":
                enforce_channel_post_limit(con, target_chat_id)
            source_chat = con.execute("SELECT type, title FROM chats WHERE id = ?", (message["chat_id"],)).fetchone()
            source_channel_id = message["source_channel_id"] or (message["chat_id"] if source_chat and source_chat["type"] == "channel" else None)
            forwarded_from = message["forwarded_from"]
            forwarded_from_user_id = message["forwarded_from_user_id"]
            if not forwarded_from and source_chat and source_chat["type"] != "saved":
                original_sender = con.execute("SELECT name FROM users WHERE id = ?", (message["sender_id"],)).fetchone()
                forwarded_from = original_sender["name"] if original_sender else source_chat["title"]
                forwarded_from_user_id = message["sender_id"] if original_sender else None
            con.execute(
                "INSERT INTO messages(id,chat_id,sender_id,text,media_type,media_data,circle_preview_data,views,forwarded_from,forwarded_from_user_id,source_channel_id,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (uid("msg"), target_chat_id, sender_id, message["text"], message["media_type"], message["media_data"], message["circle_preview_data"], 1, forwarded_from, forwarded_from_user_id, source_channel_id, now()),
            )
        con.execute("UPDATE chats SET updated_at = ? WHERE id = ?", (now(), target_chat_id))

    def react(self, con, user, body):
        emoji = str(body.get("emoji", "👍"))[:32]
        if not emoji:
            raise ValueError("Выберите реакцию.")
        row = con.execute(
            "SELECT m.chat_id, c.type AS chat_type, c.settings_json FROM messages m JOIN chats c ON c.id = m.chat_id WHERE m.id=?",
            (body.get("messageId"),),
        ).fetchone()
        if not row:
            raise ValueError("Пост не найден.")
        if not self.has_chat_access(con, user["id"], row["chat_id"]):
            raise PermissionError()
        message_id = body.get("messageId")
        existing = con.execute(
            "SELECT 1 FROM message_reactions WHERE message_id = ? AND user_id = ? AND emoji = ?",
            (message_id, user["id"], emoji),
        ).fetchone()
        if row["chat_type"] == "channel":
            if not loads(row["settings_json"], {}).get("showReactions", True):
                raise PermissionError("Реакции отключены автором канала.")
            if not existing and emoji not in channel_reaction_emojis(con):
                raise ValueError("Эта реакция недоступна в каналах.")
        if existing:
            con.execute(
                "DELETE FROM message_reactions WHERE message_id = ? AND user_id = ? AND emoji = ?",
                (message_id, user["id"], emoji),
            )
        else:
            con.execute(
                "INSERT INTO message_reactions(message_id,user_id,emoji,created_at) VALUES (?,?,?,?)",
                (message_id, user["id"], emoji, now()),
            )
        reactions = {
            item["emoji"]: item["count"]
            for item in con.execute(
                "SELECT emoji, count(*) AS count FROM message_reactions WHERE message_id = ? GROUP BY emoji",
                (message_id,),
            ).fetchall()
        }
        con.execute("UPDATE messages SET reactions_json=? WHERE id=?", (dumps(reactions), message_id))
        return self.json({"ok": True, "active": not bool(existing)})

    def donate(self, con, user, body):
        amount = nonnegative_int(body.get("amount", 0), "amount")
        if amount <= 0:
            raise ValueError("Введите количество звёзд.")
        message = con.execute(
            """SELECT m.sender_id, m.chat_id, c.type, u.name
               FROM messages m
               JOIN chats c ON c.id = m.chat_id
               JOIN users u ON u.id = m.sender_id
               WHERE m.id = ? AND m.media_type IS NOT 'system'""",
            (body.get("messageId"),),
        ).fetchone()
        if not message or message["type"] != "channel":
            raise ValueError("Звёзды можно подарить только за публикацию в канале.")
        if not self.has_chat_access(con, user["id"], message["chat_id"]):
            raise PermissionError()
        target_user_id = message["sender_id"]
        if target_user_id == user["id"]:
            raise ValueError("Нельзя отправить звёзды самому себе.")
        debited = con.execute("UPDATE users SET stars = stars - ? WHERE id = ? AND stars >= ?", (amount, user["id"], amount)).rowcount
        if not debited:
            raise ValueError("Недостаточно звёзд.")
        self.credit_stars(con, target_user_id, amount)
        self.record_star_transaction(con, user["id"], -amount, "donation_sent", f"Донат за публикацию {message['name']}")
        self.record_star_transaction(con, target_user_id, amount, "donation_received", f"Донат за публикацию от {user['name']}")
        return self.json({"ok": True})

    def record_star_transaction(self, con, user_id, amount, kind, description):
        con.execute(
            "INSERT INTO star_transactions(id,user_id,amount,kind,description,created_at) VALUES (?,?,?,?,?,?)",
            (uid("stars"), user_id, amount, kind, description, now()),
        )

    def create_yookassa_payment(self, con, user, body):
        if not yookassa_configured():
            raise ValueError("Оплата ЮKassa пока не настроена. Попробуйте позже.")
        if body.get("purchaseTermsAccepted") is not True and str(body.get("purchaseTermsAccepted", "")).lower() != "true":
            raise ValueError("Для покупки необходимо принять условия покупки.")
        package_id = str(body.get("packageId", "")).strip().lower()
        package = next((item for item in yookassa_star_packages(con) if item["id"] == package_id), None)
        if not package:
            raise ValueError("Выбранный пакет звёзд недоступен.")
        discount_percent = self.star_package_discount_percent(con, user["id"])
        amount_value = discounted_price(package["price"], discount_percent)
        maximum = int(self.account_level_data(con, user["id"]).get("limits", {}).get("maxStars", 0) or 0)
        if maximum and int(user["stars"] or 0) + package["stars"] > maximum:
            raise ValueError(f"Этот пакет превышает лимит баланса: {maximum} звёзд.")
        channel_id = str(body.get("channelId", "")).strip() or None
        channel_bonus_type = None
        channel_bonus_amount = None
        if channel_id:
            channel = con.execute("SELECT id, type, owner_id, subscriber_count, subscriber_boost, settings_json FROM chats WHERE id = ?", (channel_id,)).fetchone()
            if not channel or channel["type"] not in MONETIZED_CHAT_TYPES or not channel["owner_id"]:
                raise ValueError("Канал или беседа для покупки не найдены.")
            if not self.has_chat_access(con, user["id"], channel_id):
                raise PermissionError("Вступите в канал или беседу, чтобы купить звёзды через неё.")
            settings = loads(channel["settings_json"], {}) or {}
            monetization = self.channel_monetization(con)
            bonus_percent = self.channel_commission_percent(monetization, self.monetized_chat_member_count(con, channel_id, channel["type"]))
            if not bonus_percent:
                raise ValueError("Для текущего числа участников объекта не настроена комиссия.")
            channel_bonus_type = "money"
            channel_bonus_amount = str((Decimal(str(package["stars"])) * Decimal(monetization["starRateRubles"]) * Decimal(bonus_percent) / Decimal(100)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
            package_gifts = settings.get("buyerGiftStarsByPackage", {}) if channel["type"] == "channel" else {}
            if not isinstance(package_gifts, dict):
                package_gifts = {}
            buyer_gift_stars = nonnegative_int(package_gifts.get(package["id"], settings.get("buyerGiftStars", 0)), "buyerGiftStars", 100_000)
        else:
            buyer_gift_stars = 0
        order_id = uid("yookassa")
        current = now()
        con.execute(
            """INSERT INTO yookassa_payments(id,user_id,package_id,stars,amount_value,channel_id,channel_bonus_type,channel_bonus_amount,buyer_gift_stars,status,terms_accepted_at,created_at,updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,'creating',?,?,?)""",
            (order_id, user["id"], package["id"], package["stars"], amount_value, channel_id, channel_bonus_type, channel_bonus_amount, buyer_gift_stars, current, current, current),
        )
        payment = yookassa_request(
            "/payments",
            "POST",
            {
                "amount": {"value": amount_value, "currency": "RUB"},
                "capture": True,
                "confirmation": {"type": "redirect", "return_url": f"{YOOKASSA_RETURN_URL}/payment-return?order={order_id}"},
                "description": f"Chat-Pro: {package['stars']} звёзд" + (f" со скидкой {discount_percent}%" if discount_percent else "") + (f" через {('канал' if channel['type'] == 'channel' else 'беседу')}" if channel_id else ""),
                "metadata": {"chat_pro_order_id": order_id},
            },
            idempotence_key=order_id,
        )
        payment_id = str(payment.get("id", ""))
        confirmation_url = str((payment.get("confirmation") or {}).get("confirmation_url", ""))
        if not payment_id or not confirmation_url:
            con.execute("UPDATE yookassa_payments SET status = 'failed', updated_at = ? WHERE id = ?", (now(), order_id))
            raise ValueError("ЮKassa не вернула ссылку для оплаты. Попробуйте ещё раз.")
        con.execute(
            "UPDATE yookassa_payments SET yookassa_payment_id = ?, status = ?, updated_at = ? WHERE id = ?",
            (payment_id, str(payment.get("status", "pending")), now(), order_id),
        )
        return self.json({"ok": True, "orderId": order_id, "confirmationUrl": confirmation_url})

    def check_yookassa_payment(self, con, user, body):
        order_id = str(body.get("orderId", "")).strip()
        payment_order = con.execute("SELECT * FROM yookassa_payments WHERE id = ? AND user_id = ?", (order_id, user["id"])).fetchone()
        if not payment_order:
            raise ValueError("Заказ на оплату не найден.")
        return self.json({"ok": True, **self.finalize_yookassa_payment(con, payment_order)})

    def handle_yookassa_webhook(self, con, body):
        if not isinstance(body, dict) or body.get("event") != "payment.succeeded":
            return self.json({"ok": True})
        payment_id = str((body.get("object") or {}).get("id", "")).strip()
        if not payment_id:
            return self.json({"ok": True})
        payment_order = con.execute("SELECT * FROM yookassa_payments WHERE yookassa_payment_id = ?", (payment_id,)).fetchone()
        if payment_order:
            self.finalize_yookassa_payment(con, payment_order)
        subscription_payment = con.execute("SELECT * FROM account_level_subscription_payments WHERE yookassa_payment_id = ?", (payment_id,)).fetchone()
        if subscription_payment:
            self.finalize_account_level_subscription_payment(con, subscription_payment)
        return self.json({"ok": True})

    def finalize_yookassa_payment(self, con, payment_order):
        if payment_order["credited_at"]:
            return {"status": "succeeded", "credited": True, "stars": payment_order["stars"]}
        if not payment_order["yookassa_payment_id"]:
            raise ValueError("Платёж ещё создаётся. Попробуйте обновить страницу.")
        payment = yookassa_request(f"/payments/{payment_order['yookassa_payment_id']}")
        status = str(payment.get("status", ""))
        con.execute("UPDATE yookassa_payments SET status = ?, updated_at = ? WHERE id = ?", (status or "unknown", now(), payment_order["id"]))
        if status != "succeeded" or payment.get("paid") is not True:
            return {"status": status or "pending", "credited": False}
        metadata = payment.get("metadata") or {}
        amount = payment.get("amount") or {}
        if (
            metadata.get("chat_pro_order_id") != payment_order["id"]
            or amount.get("currency") != "RUB"
            or amount.get("value") != payment_order["amount_value"]
        ):
            raise ValueError("Данные оплаченного заказа не прошли проверку.")
        claimed = con.execute(
            "UPDATE yookassa_payments SET credited_at = -1, status = 'succeeded', updated_at = ? WHERE id = ? AND credited_at IS NULL",
            (now(), payment_order["id"]),
        ).rowcount
        if not claimed:
            return {"status": "succeeded", "credited": True, "stars": payment_order["stars"]}
        self.credit_stars(con, payment_order["user_id"], payment_order["stars"])
        self.record_star_transaction(con, payment_order["user_id"], payment_order["stars"], "yookassa_purchase", f"Покупка {payment_order['stars']} звёзд через ЮKassa")
        if payment_order["channel_id"]:
            channel = con.execute("SELECT title, type, owner_id, subscriber_count, subscriber_boost, settings_json FROM chats WHERE id = ? AND type IN ('channel', 'group', 'community')", (payment_order["channel_id"],)).fetchone()
            if channel and payment_order["channel_bonus_type"] in {"stars", "money"} and payment_order["channel_bonus_amount"]:
                bonus_type = payment_order["channel_bonus_type"]
                bonus_amount = payment_order["channel_bonus_amount"]
                settings = loads(channel["settings_json"], {}) or {}
                requested_gift = nonnegative_int(payment_order["buyer_gift_stars"], "buyerGiftStars", 100_000)
                buyer_message = str(settings.get("buyerPurchaseMessage", "") if channel["type"] == "channel" else "").strip()[:500]
                owner = con.execute("SELECT stars FROM users WHERE id = ?", (channel["owner_id"],)).fetchone()
                gift_stars = requested_gift if owner and owner["stars"] >= requested_gift else 0
                buyer = con.execute("SELECT name, username FROM users WHERE id = ?", (payment_order["user_id"],)).fetchone()
                buyer_label = buyer["name"] if buyer else "Пользователь"
                chat_label = "канал" if channel["type"] == "channel" else "беседу"
                if bonus_type == "money":
                    bonus_label = f"{bonus_amount} ₽ к выплате"
                else:
                    bonus_label = f"★ {bonus_amount}"
                if gift_stars:
                    debited = con.execute("UPDATE users SET stars = stars - ? WHERE id = ? AND stars >= ?", (gift_stars, channel["owner_id"], gift_stars)).rowcount
                    if debited:
                        self.credit_stars(con, payment_order["user_id"], gift_stars)
                        self.record_star_transaction(con, channel["owner_id"], -gift_stars, "channel_buyer_gift_sent", f"Подарок покупателю через {chat_label} «{channel['title']}»")
                        self.record_star_transaction(con, payment_order["user_id"], gift_stars, "channel_buyer_gift_received", f"Подарок за покупку через {chat_label} «{channel['title']}»")
                    else:
                        gift_stars = 0
                purchase_id = uid("channel_purchase")
                con.execute(
                    """INSERT OR IGNORE INTO channel_star_purchases(id,payment_id,channel_id,buyer_user_id,stars,bonus_type,bonus_amount,buyer_gift_stars,buyer_message,created_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (purchase_id, payment_order["id"], payment_order["channel_id"], payment_order["user_id"], payment_order["stars"], bonus_type, bonus_amount, gift_stars, buyer_message, now()),
                )
                if bonus_type == "money":
                    monetization = self.channel_monetization(con)
                    con.execute(
                        """INSERT OR IGNORE INTO channel_payout_accruals(id,purchase_id,channel_id,owner_user_id,amount_value,commission_percent,star_rate_rubles,created_at)
                           VALUES (?,?,?,?,?,?,?,?)""",
                        (uid("payout_accrual"), purchase_id, payment_order["channel_id"], channel["owner_id"], bonus_amount, self.channel_commission_percent(monetization, self.monetized_chat_member_count(con, payment_order["channel_id"], channel["type"])), monetization["starRateRubles"], now()),
                    )
                if buyer_message:
                    direct = con.execute(
                        """SELECT c.id FROM chats c JOIN chat_members owner_member ON owner_member.chat_id = c.id
                           JOIN chat_members buyer_member ON buyer_member.chat_id = c.id
                           WHERE c.type = 'direct' AND owner_member.user_id = ? AND buyer_member.user_id = ? LIMIT 1""",
                        (channel["owner_id"], payment_order["user_id"]),
                    ).fetchone()
                    direct_id = direct["id"] if direct else uid("chat")
                    if not direct:
                        con.execute("INSERT INTO chats(id,type,title,owner_id,created_at,updated_at) VALUES (?,?,?,?,?,?)", (direct_id, "direct", "Личный чат", channel["owner_id"], now(), now()))
                        for member_id in (channel["owner_id"], payment_order["user_id"]):
                            con.execute("INSERT INTO chat_members(chat_id,user_id,role,created_at) VALUES (?,?,?,?)", (direct_id, member_id, "member", now()))
                    con.execute("INSERT INTO messages(id,chat_id,sender_id,text,media_type,views,created_at) VALUES (?,?,?,?,?,?,?)", (uid("msg"), direct_id, channel["owner_id"], buyer_message, "system", 1, now()))
                    con.execute("UPDATE chats SET updated_at = ? WHERE id = ?", (now(), direct_id))
                notice = f"{buyer_label} купил(а) {payment_order['stars']} звёзд через {chat_label} «{channel['title']}». Бонус: {bonus_label}."
                con.execute("INSERT INTO notifications(id,user_id,kind,text,target_id,created_at) VALUES (?,?,?,?,?,?)", (uid("notice"), channel["owner_id"], "channel_star_purchase", notice, payment_order["channel_id"], now()))
                con.execute("INSERT INTO messages(id,chat_id,sender_id,text,media_type,views,created_at) VALUES (?,?,?,?,?,?,?)", (uid("msg"), payment_order["channel_id"], channel["owner_id"], f"{buyer_label} купил(а) ★ {payment_order['stars']} через этот объект.", "system", 1, now()))
                con.execute("UPDATE chats SET updated_at = ? WHERE id = ?", (now(), payment_order["channel_id"]))
        con.execute("UPDATE yookassa_payments SET credited_at = ?, status = 'succeeded', updated_at = ? WHERE id = ?", (now(), now(), payment_order["id"]))
        return {"status": "succeeded", "credited": True, "stars": payment_order["stars"]}

    def channel_monetization(self, con) -> dict:
        row = con.execute("SELECT value FROM settings WHERE key = 'channel_monetization'").fetchone()
        try:
            return normalize_channel_monetization(loads(row["value"], {}) if row else DEFAULT_CHANNEL_MONETIZATION)
        except ValueError:
            return DEFAULT_CHANNEL_MONETIZATION

    def channel_commission_percent(self, monetization: dict, subscriber_count: int) -> int:
        for tier in monetization["tiers"]:
            maximum = tier["maxSubscribers"]
            if subscriber_count >= tier["minSubscribers"] and (maximum is None or subscriber_count < maximum):
                return tier["percent"]
        return 0

    def monetized_chat_member_count(self, con, chat_id, chat_type=None) -> int:
        if chat_type is None:
            chat = con.execute(
                "SELECT type, subscriber_count, subscriber_boost FROM chats WHERE id = ?",
                (chat_id,),
            ).fetchone()
        else:
            chat = con.execute(
                "SELECT type, subscriber_count, subscriber_boost FROM chats WHERE id = ? AND type = ?",
                (chat_id, chat_type),
            ).fetchone()
        if not chat or chat["type"] not in MONETIZED_CHAT_TYPES:
            return 0
        if chat["type"] == "channel":
            return max(0, int(chat["subscriber_count"] or 0) + int(chat["subscriber_boost"] or 0))
        return int(con.execute("SELECT count(*) AS count FROM chat_members WHERE chat_id = ?", (chat_id,)).fetchone()["count"] or 0)

    def channel_payout_summary(self, con, owner_user_id, channel_id) -> dict:
        earned = sum((Decimal(str(row["amount_value"])) for row in con.execute(
            "SELECT amount_value FROM channel_payout_accruals WHERE owner_user_id = ? AND channel_id = ?", (owner_user_id, channel_id)
        ).fetchall()), Decimal("0.00"))
        reserved = sum((Decimal(str(row["amount_value"])) for row in con.execute(
            "SELECT amount_value FROM channel_payout_requests WHERE owner_user_id = ? AND channel_id = ? AND status IN ('pending', 'paid')", (owner_user_id, channel_id)
        ).fetchall()), Decimal("0.00"))
        available = max(Decimal("0.00"), earned - reserved)
        return {"channelId": channel_id, "earned": str(earned.quantize(Decimal("0.01"))), "reserved": str(reserved.quantize(Decimal("0.01"))), "available": str(available.quantize(Decimal("0.01")))}

    def purchase_demo_activity_package(self, con, user, body):
        package_id = str(body.get("packageId", "")).strip()
        channel_id = str(body.get("channelId", "")).strip()
        package = con.execute("SELECT * FROM demo_activity_packages WHERE id = ?", (package_id,)).fetchone()
        channel = con.execute("SELECT id, title, type FROM chats WHERE id = ? AND type IN ('channel', 'group', 'community') AND owner_id = ?", (channel_id, user["id"])).fetchone()
        if not package or not channel:
            raise ValueError("Выберите доступный пакет и свою беседу или канал.")
        if package["required_account_level_id"]:
            raise ValueError("Этот пакет подключается автоматически каналам владельцев с требуемым уровнем аккаунта.")
        if (package["views_per_day"] or package["reactions_per_day"] or package["comments_per_day"]) and not demo_activity_post(con, channel_id):
            raise ValueError("Для этого пакета в объекте должна быть хотя бы одна публикация.")
        if not account_level_available_for_user(con, user["id"], package["required_account_level_id"]):
            raise ValueError("Ваш уровень аккаунта не соответствует требованию этого пакета.")
        if package["comments_per_day"] and not automated_commenter_pool(con):
            raise ValueError("Для комментариев сначала должны быть настроены служебные аккаунты.")
        price_stars = int(package["price_stars"] or 0)
        if price_stars:
            charged = con.execute("UPDATE users SET stars = stars - ? WHERE id = ? AND stars >= ?", (price_stars, user["id"], price_stars)).rowcount
            if not charged:
                raise ValueError("Недостаточно звёзд для этого пакета.")
            self.record_star_transaction(con, user["id"], -price_stars, "demo_activity_package", f"Демо-пакет «{package['title']}» для объекта «{channel['title']}»")
        current = now()
        con.execute(
            """INSERT INTO demo_activity_subscriptions(id,package_id,channel_id,starts_at,ends_at,auto_renew,created_at)
               VALUES (?,?,?,?,?,?,?)""",
            (uid("demosubscription"), package_id, channel_id, current, current + max(1, package["duration_days"]) * 86400, 0, current),
        )
        return self.json({"ok": True})

    def create_channel_payout_request(self, con, user, body):
        channel_id = str(body.get("channelId", "")).strip()
        channel = con.execute("SELECT id, title, type FROM chats WHERE id = ? AND type IN ('channel', 'group', 'community') AND owner_id = ?", (channel_id, user["id"])).fetchone()
        if not channel:
            raise PermissionError("Заявку может создать только владелец беседы или канала.")
        amount_value = normalize_money(body.get("amount"), "Сумма выплаты")
        summary = self.channel_payout_summary(con, user["id"], channel_id)
        if Decimal(amount_value) > Decimal(summary["available"]):
            raise ValueError("Сумма заявки превышает доступное начисление.")
        current = now()
        request_id = uid("payout_request")
        con.execute(
            "INSERT INTO channel_payout_requests(id,channel_id,owner_user_id,amount_value,status,created_at) VALUES (?,?,?,?,?,?)",
            (request_id, channel_id, user["id"], amount_value, "pending", current),
        )
        andrei = con.execute("SELECT id FROM users WHERE lower(username) = 'andrei' LIMIT 1").fetchone()
        if andrei:
            con.execute(
                "INSERT INTO notifications(id,user_id,kind,text,target_id,created_at) VALUES (?,?,?,?,?,?)",
                (uid("notice"), andrei["id"], "channel_payout_request", f"Новая заявка на выплату: {user['name']} · объект «{channel['title']}» · {amount_value} ₽.", request_id, current),
            )
        return self.json({"ok": True, "requestId": request_id, "summary": self.channel_payout_summary(con, user["id"], channel_id)})

    def add_review(self, con, user, body):
        url = normalize_review_source(body.get("url"))
        if not url:
            raise ValueError("Укажите ссылку, @username или название источника.")
        is_url = is_review_url(url)
        is_phone = is_review_phone(url)
        is_telegram = is_review_telegram(url)
        if len(url) > (2048 if is_url else 120):
            raise ValueError("Название или ссылка источника слишком длинные.")
        source_type = "website" if is_url else "phone" if is_phone else "telegram" if is_telegram else " ".join(str(body.get("sourceType", "")).strip().split())
        if not (is_url or is_phone or is_telegram) and not source_type:
            raise ValueError("Выберите площадку для источника без ссылки.")
        if len(source_type) > 80:
            raise ValueError("Название площадки не должно превышать 80 символов.")
        source_type = source_type.lower() if source_type in {"telegram", "instagram", "other"} else source_type
        rating = 1 if int(body.get("rating", 1)) >= 0 else -1
        comment = str(body.get("comment", "")).strip()
        if len(comment) > 3000:
            raise ValueError("Текст отзыва не должен превышать 3000 символов.")
        city = " ".join(str(body.get("city", "")).strip().split())
        if len(city) > 120:
            raise ValueError("Название города не должно превышать 120 символов.")
        links = list(dict.fromkeys(normalize_review_source(link) for link in str(body.get("links", "")).split("\n") if link.strip()))
        if len(links) > 20 or any(not link or len(link) > (2048 if is_review_url(link) else 120) for link in links):
            raise ValueError("Укажите до 20 связанных ссылок, номеров, @username или названий.")
        media_data = str(body.get("mediaData", "") or "")
        if media_data and (not media_data.startswith(("data:image/", "data:video/")) or len(media_data) > 5_000_000):
            raise ValueError("Прикрепите изображение или видео размером до 3,6 МБ.")
        con.execute(
            "INSERT INTO reviews(id,url,source_type,rating,comment,city,links_json,media_data,created_by,created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (uid("review"), url, source_type, rating, comment, city, dumps(links), media_data or None, user["id"], now()),
        )
        return self.json({"ok": True})

    def normalize_channel_share_url(self, value):
        raw = str(value or "").strip()
        parsed = urlparse(raw)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or len(raw) > 2048:
            raise ValueError("Укажите корректную ссылку на опубликованный пост или сторис.")
        return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path.rstrip("/") or "/", "", parsed.query, ""))

    def add_channel_share_submission(self, con, user, body):
        channel_id = str(body.get("channelId", "")).strip()
        platform = " ".join(str(body.get("platform", "")).split())[:80]
        external_url = self.normalize_channel_share_url(body.get("externalUrl"))
        description = str(body.get("description", "")).strip()
        screenshot_data = str(body.get("screenshotData", "")).strip()
        if not platform:
            raise ValueError("Укажите площадку публикации.")
        if len(description) > 2000:
            raise ValueError("Описание не должно превышать 2000 символов.")
        try:
            screenshot_data = normalize_image_data(screenshot_data, 2_500_000, "Скриншот")
        except ValueError:
            raise ValueError("Прикрепите скриншот PNG, JPG или WebP размером до 2,5 МБ.")
        channel = con.execute("SELECT id, title, subscriber_count FROM chats WHERE id = ? AND type = 'channel'", (channel_id,)).fetchone()
        if not channel or self.chat_member_role(con, channel_id, user["id"]) not in CHANNEL_MANAGER_ROLES:
            raise PermissionError("Подать заявку может только администратор этого канала.")
        current = now()
        if con.execute("SELECT 1 FROM channel_share_submissions WHERE external_url = ?", (external_url,)).fetchone():
            raise ValueError("За эту ссылку уже была подана заявка.")
        previous = con.execute("SELECT created_at FROM channel_share_submissions WHERE channel_id = ? ORDER BY created_at DESC LIMIT 1", (channel_id,)).fetchone()
        if previous and current - int(previous["created_at"]) < 30 * 86400:
            raise ValueError("Заявку на продвижение этого канала можно отправлять не чаще одного раза в 30 дней.")
        reward_stars = int(channel["subscriber_count"] or 0) // 3
        if reward_stars < 1:
            raise ValueError("Для награды у канала должно быть не менее 3 подписчиков.")
        submission_id = uid("channelshare")
        con.execute("""INSERT INTO channel_share_submissions(
            id,channel_id,submitter_id,platform,external_url,description,screenshot_data,reward_stars,status,eligible_at,created_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?)""", (submission_id, channel_id, user["id"], platform, external_url, description, screenshot_data, reward_stars, "pending", current + 600, current))
        return self.json({"ok": True, "submissionId": submission_id, "rewardStars": reward_stars, "eligibleAt": current + 600})

    def process_channel_share_submissions(self, con):
        current = now()
        rows = con.execute("SELECT * FROM channel_share_submissions WHERE status = 'pending' AND eligible_at <= ? ORDER BY eligible_at LIMIT 100", (current,)).fetchall()
        for submission in rows:
            claimed = con.execute("UPDATE channel_share_submissions SET status = 'credited', credited_at = ? WHERE id = ? AND status = 'pending'", (current, submission["id"])).rowcount
            if not claimed:
                continue
            try:
                self.credit_stars(con, submission["submitter_id"], submission["reward_stars"])
            except ValueError as error:
                con.execute("UPDATE channel_share_submissions SET status = 'pending', credited_at = NULL WHERE id = ?", (submission["id"],))
                print(f"Не удалось начислить награду за публикацию канала: {error}")
                continue
            self.record_star_transaction(con, submission["submitter_id"], submission["reward_stars"], "channel_share_reward", "Награда за публикацию канала")
            con.execute("INSERT INTO notifications(id,user_id,kind,text,target_id,created_at) VALUES (?,?,?,?,?,?)", (uid("notice"), submission["submitter_id"], "channel_share_reward", f"Начислено ★ {submission['reward_stars']} за публикацию канала.", submission["id"], current))

    def vk_review_reference(self, value):
        parsed = urlparse(str(value or "").strip())
        if parsed.scheme not in {"http", "https"} or parsed.hostname not in {"vk.com", "www.vk.com", "m.vk.com", "vk.ru", "www.vk.ru", "m.vk.ru"}:
            raise ValueError("Укажите ссылку VK на ролик или пост.")
        match = re.fullmatch(r"/(wall|video)(-?\d+)_([0-9]+)(?:_([A-Za-z0-9_-]+))?", parsed.path)
        if not match:
            raise ValueError("VK-ссылка должна вести на конкретный ролик или пост.")
        kind = "video" if match.group(1) == "video" else "post"
        return kind, int(match.group(2)), int(match.group(3)), match.group(4) or ""

    def add_vk_review_submission(self, con, user, body):
        submitted_url = self.normalize_channel_share_url(body.get("externalUrl"))
        kind, owner_id, item_id, access_key = self.vk_review_reference(submitted_url)
        external_url = f"https://vk.com/{'video' if kind == 'video' else 'wall'}{owner_id}_{item_id}{'_' + access_key if access_key else ''}"
        if con.execute("SELECT 1 FROM vk_review_submissions WHERE external_url = ?", (external_url,)).fetchone():
            raise ValueError("За этот ролик или пост VK награда уже запрашивалась.")
        access_token = VK_ID_SERVICE_TOKEN
        if len(access_token) < 20 or len(access_token) > 512:
            raise ValueError("На сервере не настроен ключ VK для проверки публичных публикаций. Обратитесь к администратору.")
        if kind == "post":
            result = vk_api(access_token, "wall.getById", {"posts": f"{owner_id}_{item_id}"})
            item = result[0] if isinstance(result, list) and result else None
            title = str(item.get("text", "") if isinstance(item, dict) else "")
        else:
            video_ref = f"{owner_id}_{item_id}" + (f"_{access_key}" if access_key else "")
            result = vk_api(access_token, "video.get", {"videos": video_ref})
            items = result.get("items", []) if isinstance(result, dict) else []
            item = items[0] if items else None
            title = str(item.get("title", "") if isinstance(item, dict) else "")
        if not isinstance(item, dict):
            raise ValueError("VK не нашёл открытую публикацию или видео по этой ссылке.")
        marker = re.compile(r"(?:чат[\s\-_‑–—]*про|chat[\s\-_‑–—]*pro)", re.IGNORECASE)
        if not marker.search(title):
            raise ValueError("В названии или тексте VK-публикации должно быть «Chat-Pro» или «Чат-Про».")
        likes = int((item.get("likes") or {}).get("count", 0) or 0)
        if likes < 1:
            raise ValueError("На момент проверки у публикации должен быть хотя бы один лайк.")
        current = now(); submission_id = uid("vkreview")
        con.execute("""INSERT INTO vk_review_submissions(id,channel_id,submitter_id,vk_target_id,external_url,vk_kind,vk_owner_id,vk_item_id,verified_title,likes_count,reward_stars,status,eligible_at,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (submission_id, None, user["id"], None, external_url, kind, owner_id, item_id, " ".join(title.split())[:2000], likes, likes, "pending", current + 600, current))
        return self.json({"ok": True, "submissionId": submission_id, "rewardStars": likes, "eligibleAt": current + 600})

    def process_vk_review_submissions(self, con):
        current = now()
        for submission in con.execute("SELECT * FROM vk_review_submissions WHERE status = 'pending' AND eligible_at <= ? ORDER BY eligible_at LIMIT 100", (current,)).fetchall():
            if not con.execute("UPDATE vk_review_submissions SET status = 'credited', credited_at = ? WHERE id = ? AND status = 'pending'", (current, submission["id"])).rowcount:
                continue
            try:
                self.credit_stars(con, submission["submitter_id"], submission["reward_stars"])
            except ValueError as error:
                con.execute("UPDATE vk_review_submissions SET status = 'pending', credited_at = NULL WHERE id = ?", (submission["id"],))
                print(f"Не удалось начислить награду за ролик или пост VK: {error}")
                continue
            self.record_star_transaction(con, submission["submitter_id"], submission["reward_stars"], "vk_chat_pro_review_reward", "Награда за ролик или пост о Chat-Pro в VK")
            con.execute("INSERT INTO notifications(id,user_id,kind,text,target_id,created_at) VALUES (?,?,?,?,?,?)", (uid("notice"), submission["submitter_id"], "vk_review_reward", f"Начислено ★ {submission['reward_stars']} за ролик или пост о Chat-Pro в VK.", submission["id"], current))

    def update_vk_review_submission(self, con, body):
        submission_id = str(body.get("submissionId", "")).strip()
        action = str(body.get("action", "")).strip()
        submission = con.execute("SELECT * FROM vk_review_submissions WHERE id = ?", (submission_id,)).fetchone()
        if not submission or action not in {"credit", "reject", "revoke"}:
            raise ValueError("Заявка или действие не найдены.")
        current = now()
        if action == "credit":
            if not con.execute("UPDATE vk_review_submissions SET status = 'credited', credited_at = ? WHERE id = ? AND status = 'pending'", (current, submission_id)).rowcount:
                raise ValueError("Заявка уже обработана.")
            self.credit_stars(con, submission["submitter_id"], submission["reward_stars"])
            self.record_star_transaction(con, submission["submitter_id"], submission["reward_stars"], "vk_chat_pro_review_reward", "Награда за ролик или пост о Chat-Pro в VK")
            text = f"Администрация одобрила ролик или пост VK: начислено ★ {submission['reward_stars']}."
        elif action == "reject":
            if not con.execute("UPDATE vk_review_submissions SET status = 'rejected', rejected_at = ? WHERE id = ? AND status = 'pending'", (current, submission_id)).rowcount:
                raise ValueError("Отклонить можно только ожидающую заявку.")
            text = "Администрация отклонила заявку на награду за ролик или пост VK."
        else:
            if submission["status"] != "credited":
                raise ValueError("Отозвать можно только начисленную награду.")
            user = con.execute("SELECT stars FROM users WHERE id = ?", (submission["submitter_id"],)).fetchone()
            if not user: raise ValueError("Пользователь не найден.")
            actual = min(int(submission["reward_stars"]), int(user["stars"]))
            con.execute("UPDATE users SET stars = stars - ? WHERE id = ?", (actual, submission["submitter_id"]))
            con.execute("UPDATE vk_review_submissions SET status = 'revoked', rejected_at = ? WHERE id = ?", (current, submission_id))
            if actual: self.record_star_transaction(con, submission["submitter_id"], -actual, "vk_chat_pro_review_reversal", "Отмена награды за ролик или пост о Chat-Pro в VK")
            text = "Администрация отменила награду за ролик или пост VK из-за нарушения правил или накрутки."
        con.execute("INSERT INTO notifications(id,user_id,kind,text,target_id,created_at) VALUES (?,?,?,?,?,?)", (uid("notice"), submission["submitter_id"], "vk_review_submission", text, submission_id, current))
        return self.json({"ok": True})

    def respond_to_appeal(self, con, body):
        appeal_type = str(body.get("appealType", "")).strip()
        appeal_id = str(body.get("appealId", "")).strip()
        response = str(body.get("response", "")).strip()
        if appeal_type not in {"report", "submission", "vk-review"} or not appeal_id or not response or len(response) > 2000:
            raise ValueError("Введите ответ длиной до 2000 символов.")
        table, user_column = {"report": ("reports", "created_by"), "submission": ("channel_share_submissions", "submitter_id"), "vk-review": ("vk_review_submissions", "submitter_id")}[appeal_type]
        row = con.execute(f"SELECT {user_column} AS user_id FROM {table} WHERE id = ?", (appeal_id,)).fetchone()
        if not row:
            raise ValueError("Обращение не найдено.")
        current = now()
        con.execute(f"UPDATE {table} SET admin_response = ?, responded_at = ?, responded_by = 'admin' WHERE id = ?", (response, current, appeal_id))
        if row["user_id"]:
            con.execute("INSERT INTO notifications(id,user_id,kind,text,target_id,created_at) VALUES (?,?,?,?,?,?)", (uid("notice"), row["user_id"], "admin_response", f"Ответ администрации: {response}", appeal_id, current))
        return self.json({"ok": True})

    def update_channel_share_submission(self, con, body):
        submission_id = str(body.get("submissionId", "")).strip()
        action = str(body.get("action", "")).strip()
        if action not in {"credit", "reject", "revoke"}:
            raise ValueError("Неизвестное действие.")
        submission = con.execute("SELECT * FROM channel_share_submissions WHERE id = ?", (submission_id,)).fetchone()
        if not submission:
            raise ValueError("Заявка не найдена.")
        current = now()
        if action == "credit":
            updated = con.execute("UPDATE channel_share_submissions SET status = 'credited', credited_at = ? WHERE id = ? AND status = 'pending'", (current, submission_id)).rowcount
            if not updated:
                raise ValueError("Заявка уже обработана.")
            self.credit_stars(con, submission["submitter_id"], submission["reward_stars"])
            self.record_star_transaction(con, submission["submitter_id"], submission["reward_stars"], "channel_share_reward", "Награда за публикацию канала")
            text = f"Администрация одобрила заявку: начислено ★ {submission['reward_stars']}."
        elif action == "reject":
            updated = con.execute("UPDATE channel_share_submissions SET status = 'rejected', rejected_at = ? WHERE id = ? AND status = 'pending'", (current, submission_id)).rowcount
            if not updated:
                raise ValueError("Отменить можно только ожидающую заявку.")
            text = "Администрация отклонила заявку на награду за публикацию канала."
        else:
            if submission["status"] != "credited":
                raise ValueError("Отозвать можно только уже начисленную награду.")
            user = con.execute("SELECT stars FROM users WHERE id = ?", (submission["submitter_id"],)).fetchone()
            if not user:
                raise ValueError("Пользователь не найден.")
            # The user may have spent some stars after the payout, so never create a negative balance.
            actual = min(int(submission["reward_stars"]), int(user["stars"]))
            con.execute("UPDATE users SET stars = stars - ? WHERE id = ?", (actual, submission["submitter_id"]))
            con.execute("UPDATE channel_share_submissions SET status = 'revoked', rejected_at = ? WHERE id = ?", (current, submission_id))
            if actual:
                self.record_star_transaction(con, submission["submitter_id"], -actual, "channel_share_reward_reversal", "Отмена награды за публикацию канала")
            text = "Администрация отменила ранее начисленную награду за публикацию канала."
        con.execute("INSERT INTO notifications(id,user_id,kind,text,target_id,created_at) VALUES (?,?,?,?,?,?)", (uid("notice"), submission["submitter_id"], "channel_share_submission", text, submission_id, current))
        return self.json({"ok": True})

    def add_report(self, con, user, body):
        target_type = str(body.get("targetType", "")).strip()[:40]
        target_id = str(body.get("targetId", "")).strip()[:2048]
        reason = str(body.get("reason", "")).strip()[:1000]
        if target_type not in {"profile", "profile-post", "review-page", "review", "story", "group-post", "channel", "channel-comment"} or not target_id:
            raise ValueError("Не удалось отправить жалобу.")
        if target_type == "profile-post":
            post = con.execute("SELECT id FROM profile_posts WHERE id = ?", (target_id,)).fetchone()
            if not post:
                raise ValueError("Публикация не найдена.")
        if target_type == "group-post":
            post = con.execute("SELECT m.id, c.owner_id, c.title FROM messages m JOIN chats c ON c.id = m.chat_id WHERE m.id = ? AND c.type = 'channel'", (target_id,)).fetchone()
            if not post:
                raise ValueError("Публикация не найдена.")
            if post["owner_id"] and post["owner_id"] != user["id"]:
                notice = "Поступила жалоба на пост «{}». Просим обратить внимание: за нарушение правил площадки и прав человека публикация удаляется.".format(post["title"])
                con.execute("INSERT INTO notifications(id,user_id,kind,text,target_id,created_at) VALUES (?,?,?,?,?,?)", (uid("notice"), post["owner_id"], "group_post_report", notice, target_id, now()))
        if target_type == "channel-comment":
            if not con.execute("SELECT 1 FROM channel_comments WHERE id = ?", (target_id,)).fetchone():
                raise ValueError("Комментарий не найден.")
        if target_type == "channel":
            channel = con.execute("SELECT owner_id, title FROM chats WHERE id = ? AND type = 'channel'", (target_id,)).fetchone()
            if not channel:
                raise ValueError("Канал не найден.")
            if channel["owner_id"] and channel["owner_id"] != user["id"]:
                con.execute(
                    "INSERT INTO notifications(id,user_id,kind,text,target_id,created_at) VALUES (?,?,?,?,?,?)",
                    (uid("notice"), channel["owner_id"], "channel_report", f"Поступила жалоба на канал «{channel['title']}».", target_id, now()),
                )
        con.execute(
            "INSERT INTO reports(id,target_type,target_id,reason,created_by,created_at) VALUES (?,?,?,?,?,?)",
            (uid("report"), target_type, target_id, reason, user["id"], now()),
        )
        return self.json({"ok": True})

    def share_content_to_group(self, con, user, body):
        target_chat_id = str(body.get("targetChatId", ""))
        source_type = str(body.get("sourceType", ""))
        source_id = str(body.get("sourceId", ""))
        comment = str(body.get("comment", "")).strip()
        if len(comment) > 1000:
            raise ValueError("Комментарий к репосту не должен быть длиннее 1000 символов.")
        target = con.execute("SELECT type FROM chats WHERE id = ?", (target_chat_id,)).fetchone()
        if not target or target["type"] not in {"direct", "group", "community", "channel"} or not self.has_chat_access(con, user["id"], target_chat_id):
            raise PermissionError("Нет доступа к выбранному диалогу.")
        if target["type"] == "channel" and self.chat_member_role(con, target_chat_id, user["id"]) not in CHANNEL_MANAGER_ROLES:
            raise PermissionError("Публиковать в этом канале могут только администраторы.")
        if source_type == "profile-post":
            source = con.execute("SELECT * FROM profile_posts WHERE id = ?", (source_id,)).fetchone()
            author_id = source["user_id"] if source else None
            text, media_type, media_data = (source["text"], "photo" if source["media_data"] else None, source["media_data"]) if source else (None, None, None)
        elif source_type == "story":
            source = con.execute("SELECT * FROM stories WHERE id = ?", (source_id,)).fetchone()
            author_id = source["user_id"] if source else None
            text, media_type, media_data = (source["caption"], "photo", source["media_data"]) if source else (None, None, None)
        else:
            raise ValueError("Неизвестный источник публикации.")
        if not source or not text and not media_data:
            raise ValueError("Исходная публикация не найдена.")
        author = con.execute("SELECT name, username FROM users WHERE id = ?", (author_id,)).fetchone()
        source_label = f"{author['name']} (@{author['username']})" if author else "удалённый автор"
        text = "\n\n".join(part for part in (comment, text) if part)
        if target["type"] == "channel":
            enforce_channel_post_limit(con, target_chat_id)
        message_id = uid("msg")
        con.execute("INSERT INTO messages(id,chat_id,sender_id,text,media_type,media_data,views,forwarded_from,source_type,source_id,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)", (message_id, target_chat_id, user["id"], text, media_type, media_data, 1, f"Источник: {source_label}", source_type, source_id, now()))
        if target["type"] == "channel":
            schedule_automated_comments(con, message_id, target_chat_id)
        con.execute("UPDATE chats SET updated_at = ? WHERE id = ?", (now(), target_chat_id))
        return self.json({"ok": True, "messageId": message_id})

    def delete_source_repost(self, con, user, message_id):
        message = con.execute("SELECT id, source_type, source_id FROM messages WHERE id = ?", (message_id,)).fetchone()
        if not message or not message["source_type"]:
            raise ValueError("Это не репост из источника.")
        owner_column = "user_id"
        table = "profile_posts" if message["source_type"] == "profile-post" else "stories" if message["source_type"] == "story" else ""
        if not table:
            raise ValueError("Неизвестный источник публикации.")
        owner = con.execute(f"SELECT {owner_column} FROM {table} WHERE id = ?", (message["source_id"],)).fetchone()
        if not owner or owner[owner_column] != user["id"]:
            raise PermissionError("Удалить этот репост может только автор исходного материала.")
        con.execute("DELETE FROM messages WHERE id = ?", (message_id,))
        return self.json({"ok": True})

    def moderate_message_admin(self, con, body):
        message_id = str(body.get("messageId", ""))
        restore = bool(body.get("restore"))
        message = con.execute(
            """SELECT m.id FROM messages m
               JOIN chats c ON c.id = m.chat_id
               WHERE m.id = ? AND c.type IN ('group', 'community', 'channel')""",
            (message_id,),
        ).fetchone()
        if not message:
            raise ValueError("Публикация не найдена.")
        con.execute("UPDATE messages SET deleted_by_admin = ? WHERE id = ?", (0 if restore else 1, message_id))
        return self.json({"ok": True})

    def claim_promotion(self, con, user, promotion_id):
        promo = con.execute("SELECT * FROM promotions WHERE id=? AND active=1", (promotion_id,)).fetchone()
        if not promo:
            raise ValueError("Акция не найдена.")
        claim = con.execute("SELECT * FROM promotion_claims WHERE promotion_id=? AND user_id=?", (promotion_id, user["id"])).fetchone()
        if claim and claim["count"] >= promo["daily_limit"]:
            raise ValueError("Лимит награды по акции уже получен.")
        self.credit_stars(con, user["id"], promo["reward_amount"])
        if promo["reward_amount"]:
            self.record_star_transaction(con, user["id"], promo["reward_amount"], "promotion", f"Награда за акцию «{promo['title']}»")
        if promo["premium_days"]:
            con.execute("UPDATE users SET premium_until = ? WHERE id=?", (now() + promo["premium_days"] * 86400, user["id"]))
        con.execute("INSERT OR REPLACE INTO promotion_claims(promotion_id,user_id,count,claimed_at) VALUES (?,?,COALESCE((SELECT count FROM promotion_claims WHERE promotion_id=? AND user_id=?),0)+1,?)", (promotion_id, user["id"], promotion_id, user["id"], now()))
        return self.json({"ok": True})

    def normalize_activity_criteria(self, criteria):
        if not isinstance(criteria, dict):
            return {}
        normalized = {}
        for key, value in criteria.items():
            if key not in ACTIVITY_METRIC_KEYS:
                continue
            try:
                target = max(0, int(value))
            except (TypeError, ValueError):
                continue
            if target:
                normalized[key] = target
        return normalized

    def activity_metrics(self, con, user_id):
        def count(query, params=()):
            return int(con.execute(query, params).fetchone()["count"] or 0)

        def audience(chat_type):
            row = con.execute(
                "SELECT MAX(subscriber_count + subscriber_boost) AS count FROM chats WHERE owner_id = ? AND type = ?",
                (user_id, chat_type),
            ).fetchone()
            return int(row["count"] or 0)

        user = con.execute("SELECT stars, login_streak FROM users WHERE id = ?", (user_id,)).fetchone()
        review_marker = re.compile(r"(?:чат[\s\-_‑–—]*про|chat[\s\-_‑–—]*pro)", re.IGNORECASE)
        review_video = any(
            review_marker.search(str(row["text"] or ""))
            for row in con.execute(
                """SELECT m.text FROM messages m JOIN chats c ON c.id = m.chat_id
                   WHERE c.owner_id = ? AND c.type = 'channel' AND m.sender_id = ?""",
                (user_id, user_id),
            ).fetchall()
        )
        return {
            "stars_balance": int(user["stars"] or 0) if user else 0,
            "direct_chats": count("SELECT count(*) AS count FROM chat_members cm JOIN chats c ON c.id = cm.chat_id WHERE cm.user_id = ? AND c.type = 'direct'", (user_id,)),
            "channels_joined": count("SELECT count(*) AS count FROM chat_members cm JOIN chats c ON c.id = cm.chat_id WHERE cm.user_id = ? AND c.type = 'channel' AND c.owner_id != ?", (user_id, user_id)),
            "channel_subscriptions": count("SELECT count(*) AS count FROM chat_members cm JOIN chats c ON c.id = cm.chat_id WHERE cm.user_id = ? AND c.type = 'channel' AND c.owner_id != ?", (user_id, user_id)),
            "communities_joined": count("SELECT count(*) AS count FROM chat_members cm JOIN chats c ON c.id = cm.chat_id WHERE cm.user_id = ? AND c.type = 'community'", (user_id,)),
            "groups_joined": count("SELECT count(*) AS count FROM chat_members cm JOIN chats c ON c.id = cm.chat_id WHERE cm.user_id = ? AND c.type = 'group'", (user_id,)),
            "channels_created": count("SELECT count(*) AS count FROM chats WHERE owner_id = ? AND type = 'channel'", (user_id,)),
            "communities_created": count("SELECT count(*) AS count FROM chats WHERE owner_id = ? AND type = 'community'", (user_id,)),
            "groups_created": count("SELECT count(*) AS count FROM chats WHERE owner_id = ? AND type = 'group'", (user_id,)),
            "channel_subscribers": audience("channel"),
            "community_subscribers": audience("community"),
            "group_subscribers": audience("group"),
            "messages": count("SELECT count(*) AS count FROM messages WHERE sender_id = ?", (user_id,)),
            "posts": count("SELECT count(*) AS count FROM profile_posts WHERE user_id = ?", (user_id,)),
            "channel_comments_written": count("SELECT count(*) AS count FROM channel_comments cc JOIN messages m ON m.id = cc.message_id JOIN chats c ON c.id = m.chat_id WHERE cc.user_id = ? AND cc.automated = 0 AND c.type = 'channel'", (user_id,)),
            "stories": count("SELECT count(*) AS count FROM stories WHERE user_id = ?", (user_id,)),
            "reviews": count("SELECT count(*) AS count FROM reviews WHERE created_by = ?", (user_id,)),
            "donations_sent": count("SELECT count(*) AS count FROM star_transactions WHERE user_id = ? AND kind = 'donation_sent'", (user_id,)),
            "stars_donated": count("SELECT COALESCE(SUM(ABS(amount)), 0) AS count FROM star_transactions WHERE user_id = ? AND kind = 'donation_sent' AND created_at >= ?", (user_id, int(datetime.datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0).timestamp()))),
            "donations_received": count("SELECT count(*) AS count FROM star_transactions WHERE user_id = ? AND kind = 'donation_received'", (user_id,)),
            "login_streak": int(user["login_streak"] or 0) if user else 0,
            "completed_calls": count("SELECT count(*) AS count FROM calls WHERE (caller_id = ? OR receiver_id = ?) AND answer_sdp IS NOT NULL", (user_id, user_id)),
            "call_partners": count("SELECT count(DISTINCT CASE WHEN caller_id = ? THEN receiver_id ELSE caller_id END) AS count FROM calls WHERE (caller_id = ? OR receiver_id = ?) AND answer_sdp IS NOT NULL", (user_id, user_id, user_id)),
            "chat_pro_review_video": int(review_video),
        }

    def activity_rewards_data(self, con, user_id):
        metrics = self.activity_metrics(con, user_id)
        account_level = self.account_level_data(con, user_id)
        level_indexes = {level["id"]: index for index, level in enumerate(account_level["levels"])}
        current_level_index = level_indexes.get(account_level["current"]["id"], -1)
        rewards = []
        for row in con.execute("SELECT * FROM activity_rewards WHERE active = 1 ORDER BY created_at DESC").fetchall():
            reward = dict(row)
            criteria = self.normalize_activity_criteria(loads(reward.pop("criteria_json"), {}))
            reward_data = loads(reward.get("reward_json"), {})
            try:
                reward["reward"] = normalize_level_reward(reward_data or {
                    "stars": reward["reward_stars"],
                    "premiumDays": reward["premium_days"],
                }, "reward")
            except ValueError:
                reward["reward"] = {"stars": reward["reward_stars"], "premiumDays": reward["premium_days"], "limits": {}, "recurringStars": 0, "recurringIntervalDays": 0, "recurringDurationDays": 0, "accountLevelId": "", "recommendOwnChannel": False}
            reward["criteria"] = criteria
            reward["progress"] = {key: min(metrics.get(key, 0), target) for key, target in criteria.items()}
            reward["claimed"] = bool(con.execute("SELECT 1 FROM activity_reward_claims WHERE reward_id = ? AND user_id = ?", (reward["id"], user_id)).fetchone())
            target_level_index = level_indexes.get(reward["reward"]["accountLevelId"], -1)
            reward["levelAvailable"] = not reward["reward"]["accountLevelId"] or target_level_index >= current_level_index
            reward["available"] = not reward["claimed"] and reward["levelAvailable"] and all(metrics.get(key, 0) >= target for key, target in criteria.items())
            rewards.append(reward)
        return rewards

    def claim_activity_reward(self, con, user, reward_id, channel_id=None):
        reward = con.execute("SELECT * FROM activity_rewards WHERE id = ? AND active = 1", (str(reward_id or ""),)).fetchone()
        if not reward:
            raise ValueError("Награда не найдена.")
        already_claimed = con.execute("SELECT 1 FROM activity_reward_claims WHERE reward_id = ? AND user_id = ?", (reward["id"], user["id"])).fetchone()
        if already_claimed:
            raise ValueError("Эта награда уже получена.")
        criteria = self.normalize_activity_criteria(loads(reward["criteria_json"], {}))
        metrics = self.activity_metrics(con, user["id"])
        unmet = [key for key, target in criteria.items() if metrics.get(key, 0) < target]
        if unmet:
            raise ValueError("Условия награды ещё не выполнены.")
        reward_data = loads(reward["reward_json"], {})
        reward_benefits = normalize_level_reward(reward_data or {
            "stars": reward["reward_stars"],
            "premiumDays": reward["premium_days"],
        }, "reward")
        account_level_id = reward_benefits["accountLevelId"]
        if account_level_id:
            account_level = self.account_level_data(con, user["id"])
            target_index = next((index for index, level in enumerate(account_level["levels"]) if level["id"] == account_level_id), None)
            current_index = next((index for index, level in enumerate(account_level["levels"]) if level["id"] == account_level["current"]["id"]), -1)
            if target_index is None:
                raise ValueError("Уровень этой награды больше не существует.")
            if target_index < current_index:
                raise ValueError("Нельзя получить уровень ниже текущего.")
        selected_channel_id = str(channel_id or "").strip()
        if reward_benefits["recommendOwnChannel"]:
            channel = con.execute(
                "SELECT id FROM chats WHERE id = ? AND type = 'channel' AND owner_id = ?",
                (selected_channel_id, user["id"]),
            ).fetchone()
            if not channel:
                raise ValueError("Выберите свой канал для добавления в рекомендации.")
            if con.execute("SELECT 1 FROM recommended_groups WHERE chat_id = ?", (selected_channel_id,)).fetchone():
                raise ValueError("Этот канал уже находится в рекомендациях.")
        con.execute("INSERT INTO activity_reward_claims(reward_id,user_id,claimed_at) VALUES (?,?,?)", (reward["id"], user["id"], now()))
        if account_level_id:
            con.execute(
                "INSERT INTO account_level_reward_grants(user_id,level_id,reward_id,granted_at) VALUES (?,?,?,?)",
                (user["id"], account_level_id, reward["id"], now()),
            )
        if reward_benefits["recommendOwnChannel"]:
            con.execute(
                "INSERT INTO recommended_groups(chat_id,position,created_at) VALUES (?,?,?)",
                (selected_channel_id, 100, now()),
            )
        if reward_benefits["stars"]:
            self.credit_stars(con, user["id"], reward_benefits["stars"])
            self.record_star_transaction(con, user["id"], reward_benefits["stars"], "activity_reward", f"Награда за активность «{reward['title']}»")
        self.apply_reward_benefits(con, user["id"], "activity_reward", reward["id"], reward["title"], reward_benefits)
        return self.json({"ok": True})

    def account_level_data(self, con, user_id, configured_levels=None):
        if configured_levels is None:
            row = con.execute("SELECT value FROM settings WHERE key='account_levels'").fetchone()
            configured_levels = loads(row["value"], []) if row else []
        try:
            levels = normalize_account_levels(configured_levels)
        except ValueError:
            levels = []
        activity = self.activity_metrics(con, user_id)
        activity.update({"communities": activity["communities_created"], "channels": activity["channels_created"]})
        current_time = now()
        legacy_purchased_ids = {row["level_id"] for row in con.execute(
            "SELECT level_id FROM account_level_purchases WHERE user_id = ?", (user_id,)
        ).fetchall()}
        granted_ids = {row["level_id"] for row in con.execute(
            "SELECT level_id FROM account_level_reward_grants WHERE user_id = ?", (user_id,)
        ).fetchall()}
        admin_grant = con.execute(
            "SELECT level_id FROM admin_account_level_grants WHERE user_id = ?", (user_id,)
        ).fetchone()
        if admin_grant:
            granted_ids.add(admin_grant["level_id"])
        subscription_rows = con.execute(
            """SELECT * FROM account_level_subscriptions
               WHERE user_id = ? AND status IN ('active', 'cancelled', 'payment_failed') AND active_until > ?""",
            (user_id, current_time),
        ).fetchall()
        subscribed_ids = {row["level_id"] for row in subscription_rows}
        subscription_by_level = {row["level_id"]: dict(row) for row in subscription_rows}

        earned_indexes = []
        for index, level in enumerate(levels):
            criteria = level.get("criteria", {}) or {}
            if index == 0 or all(activity.get(key, 0) >= value for key, value in criteria.items()):
                earned_indexes.append(index)
            else:
                break
        earned_index = earned_indexes[-1] if earned_indexes else -1
        achievement = con.execute("SELECT highest_level_index FROM account_level_achievements WHERE user_id = ?", (user_id,)).fetchone()
        highest_achievement_index = int(achievement["highest_level_index"]) if achievement else 0
        if earned_index > highest_achievement_index:
            con.execute(
                """INSERT INTO account_level_achievements(user_id, highest_level_index, updated_at) VALUES (?,?,?)
                   ON CONFLICT(user_id) DO UPDATE SET highest_level_index = excluded.highest_level_index, updated_at = excluded.updated_at""",
                (user_id, earned_index, current_time),
            )
            highest_achievement_index = earned_index
        achievement_lost = highest_achievement_index > earned_index

        level_states = []
        current_index = -1
        for index, level in enumerate(levels):
            criteria = level.get("criteria", {}) or {}
            earned = index <= earned_index
            legacy_purchased = level["id"] in legacy_purchased_ids
            granted = level["id"] in granted_ids
            subscribed = level["id"] in subscribed_ids
            paid_access = legacy_purchased or granted or subscribed
            unlocked = index == 0 or (not achievement_lost and index <= earned_index) or paid_access
            if unlocked:
                current_index = index
            claimed = bool(con.execute(
                "SELECT 1 FROM account_level_rewards WHERE user_id = ? AND level_id = ?", (user_id, level["id"])
            ).fetchone())
            level_states.append({
                **level, "earned": earned, "purchased": legacy_purchased, "granted": granted,
                "subscribed": subscribed, "subscription": subscription_by_level.get(level["id"]),
                "unlocked": unlocked, "rewardClaimed": claimed, "rewardAvailable": unlocked and not claimed,
            })
        current = level_states[current_index] if current_index >= 0 else {"id": "regular", "title": "Обычный", "description": "Стандартный аккаунт.", "limits": {}, "reward": {"stars": 0}}
        next_level = level_states[current_index + 1] if current_index + 1 < len(level_states) else None
        return {
            "current": current, "next": next_level, "levels": level_states, "activity": activity,
            "limits": self.effective_limits(con, user_id, current), "rewardClaimed": bool(current.get("rewardClaimed", False)),
            "achievementLost": achievement_lost,
        }

    def claim_account_level_reward(self, con, user, level_id):
        data = self.account_level_data(con, user["id"])
        level = next((item for item in data["levels"] if item["id"] == str(level_id or "")), None)
        if not level or not level["unlocked"]:
            raise ValueError("Награда доступна только за открытый уровень.")
        if level["rewardClaimed"]:
            raise ValueError("Награда за этот уровень уже получена.")
        reward = level.get("reward", {}) or {}
        stars = max(0, int(reward.get("stars", 0) or 0))
        con.execute("INSERT INTO account_level_rewards(user_id,level_id,claimed_at) VALUES (?,?,?)", (user["id"], level["id"], now()))
        if stars:
            self.credit_stars(con, user["id"], stars)
            self.record_star_transaction(con, user["id"], stars, "level_reward", f"Награда за уровень «{level['title']}»")
        self.apply_reward_benefits(con, user["id"], "account_level_reward", level["id"], level["title"], reward)
        return self.json({"ok": True})

    def create_account_level_subscription(self, con, user, body):
        if not yookassa_configured():
            raise ValueError("Оплата ЮKassa пока не настроена. Попробуйте позже.")
        if body.get("subscriptionTermsAccepted") is not True and str(body.get("subscriptionTermsAccepted", "")).lower() != "true":
            raise ValueError("Для подписки нужно принять условия регулярных списаний.")
        data = self.account_level_data(con, user["id"])
        level_id = str(body.get("levelId", "")).strip()
        next_level = data["next"]
        if not next_level or next_level["id"] != level_id:
            raise ValueError("Подписку можно оформить только на следующий уровень аккаунта.")
        monthly_price = normalize_money(next_level.get("monthlyPrice", "0"), "monthlyPrice")
        if Decimal(monthly_price) <= 0:
            raise ValueError("Для этого уровня не задана цена месячной подписки.")
        existing = con.execute("SELECT * FROM account_level_subscriptions WHERE user_id = ? AND level_id = ?", (user["id"], level_id)).fetchone()
        current_time = now()
        if existing and existing["active_until"] > current_time and existing["status"] in {"active", "cancelled", "payment_failed"}:
            raise ValueError("Подписка на этот уровень уже активна.")
        if existing and con.execute(
            """SELECT 1 FROM account_level_subscription_payments
               WHERE subscription_id = ? AND paid_at IS NULL AND status IN ('creating', 'pending', 'waiting_for_capture')""",
            (existing["id"],),
        ).fetchone():
            raise ValueError("Оплата подписки уже ожидает подтверждения. Завершите её или подождите отмены платежа.")
        subscription_id = existing["id"] if existing else uid("levelsub")
        if existing:
            con.execute("""UPDATE account_level_subscriptions
                           SET monthly_price = ?, payment_method_id = NULL, active_until = 0, next_charge_at = 0,
                               status = 'payment_failed', terms_accepted_at = ?, updated_at = ? WHERE id = ?""",
                        (monthly_price, current_time, current_time, subscription_id))
        else:
            con.execute("""INSERT INTO account_level_subscriptions(id,user_id,level_id,monthly_price,payment_method_id,active_until,next_charge_at,status,terms_accepted_at,created_at,updated_at)
                           VALUES (?,?,?,?,NULL,0,0,'payment_failed',?,?,?)""",
                        (subscription_id, user["id"], level_id, monthly_price, current_time, current_time, current_time))
        payment_id = uid("levelsubpay")
        con.execute("""INSERT INTO account_level_subscription_payments(id,subscription_id,amount_value,status,created_at,updated_at)
                       VALUES (?,?,?,'creating',?,?)""", (payment_id, subscription_id, monthly_price, current_time, current_time))
        payment = yookassa_request("/payments", "POST", {
            "amount": {"value": monthly_price, "currency": "RUB"}, "capture": True, "save_payment_method": True,
            "confirmation": {"type": "redirect", "return_url": f"{YOOKASSA_RETURN_URL}/payment-return?subscriptionOrder={payment_id}"},
            "description": f"Chat-Pro: подписка на уровень «{next_level['title']}» на 30 дней",
            "metadata": {"chat_pro_level_subscription_payment_id": payment_id},
        }, idempotence_key=payment_id)
        yookassa_payment_id = str(payment.get("id", ""))
        confirmation_url = str((payment.get("confirmation") or {}).get("confirmation_url", ""))
        if not yookassa_payment_id or not confirmation_url:
            con.execute("UPDATE account_level_subscription_payments SET status = 'failed', updated_at = ? WHERE id = ?", (now(), payment_id))
            raise ValueError("ЮKassa не вернула ссылку для оплаты. Попробуйте позже.")
        con.execute("UPDATE account_level_subscription_payments SET yookassa_payment_id = ?, status = ?, updated_at = ? WHERE id = ?",
                    (yookassa_payment_id, str(payment.get("status", "pending")), now(), payment_id))
        return self.json({"ok": True, "subscriptionOrderId": payment_id, "confirmationUrl": confirmation_url})

    def finalize_account_level_subscription_payment(self, con, payment_row):
        if payment_row["paid_at"]:
            return {"status": "succeeded", "activated": True}
        if not payment_row["yookassa_payment_id"]:
            raise ValueError("Платёж ещё создаётся.")
        payment = yookassa_request(f"/payments/{payment_row['yookassa_payment_id']}")
        status = str(payment.get("status", ""))
        con.execute("UPDATE account_level_subscription_payments SET status = ?, updated_at = ? WHERE id = ?", (status or "unknown", now(), payment_row["id"]))
        if status != "succeeded" or payment.get("paid") is not True:
            return {"status": status or "pending", "activated": False}
        subscription = con.execute("SELECT * FROM account_level_subscriptions WHERE id = ?", (payment_row["subscription_id"],)).fetchone()
        metadata = payment.get("metadata") or {}
        amount = payment.get("amount") or {}
        if not subscription or metadata.get("chat_pro_level_subscription_payment_id") != payment_row["id"] or amount.get("currency") != "RUB" or amount.get("value") != payment_row["amount_value"]:
            raise ValueError("Данные оплаты подписки не прошли проверку.")
        claimed = con.execute("UPDATE account_level_subscription_payments SET paid_at = -1, status = 'succeeded', updated_at = ? WHERE id = ? AND paid_at IS NULL", (now(), payment_row["id"])).rowcount
        if not claimed:
            return {"status": "succeeded", "activated": True}
        method = payment.get("payment_method") or {}
        payment_method_id = str(method.get("id", "")) if method.get("saved") is True else ""
        if not payment_method_id and not subscription["payment_method_id"]:
            con.execute("UPDATE account_level_subscription_payments SET paid_at = NULL, status = 'failed', updated_at = ? WHERE id = ?", (now(), payment_row["id"]))
            raise ValueError("ЮKassa не сохранила способ оплаты для продления подписки.")
        current_time = now()
        active_until = max(current_time, int(subscription["active_until"] or 0)) + 30 * 86400
        con.execute("""UPDATE account_level_subscriptions
                       SET payment_method_id = COALESCE(?, payment_method_id), active_until = ?, next_charge_at = ?,
                           status = 'active', updated_at = ? WHERE id = ?""",
                    (payment_method_id or None, active_until, active_until, current_time, subscription["id"]))
        con.execute("UPDATE account_level_subscription_payments SET paid_at = ?, updated_at = ? WHERE id = ?", (current_time, current_time, payment_row["id"]))
        return {"status": "succeeded", "activated": True, "activeUntil": active_until}

    def check_account_level_subscription_payment(self, con, user, body):
        payment_id = str(body.get("subscriptionOrderId", "")).strip()
        payment = con.execute("""SELECT payment.* FROM account_level_subscription_payments payment
                               JOIN account_level_subscriptions subscription ON subscription.id = payment.subscription_id
                               WHERE payment.id = ? AND subscription.user_id = ?""", (payment_id, user["id"])).fetchone()
        if not payment:
            raise ValueError("Заказ подписки не найден.")
        return self.json({"ok": True, **self.finalize_account_level_subscription_payment(con, payment)})

    def cancel_account_level_subscription(self, con, user, body):
        level_id = str(body.get("levelId", "")).strip()
        changed = con.execute("""UPDATE account_level_subscriptions SET status = 'cancelled', updated_at = ?
                               WHERE user_id = ? AND level_id = ? AND status = 'active' AND active_until > ?""",
                              (now(), user["id"], level_id, now())).rowcount
        if not changed:
            raise ValueError("Активная подписка на этот уровень не найдена.")
        return self.json({"ok": True})

    def process_account_level_subscriptions(self, con):
        current_time = now()
        pending = con.execute("SELECT * FROM account_level_subscription_payments WHERE paid_at IS NULL AND yookassa_payment_id IS NOT NULL AND status IN ('pending', 'waiting_for_capture') LIMIT 100").fetchall()
        for payment in pending:
            try:
                self.finalize_account_level_subscription_payment(con, payment)
            except ValueError:
                pass
        due = con.execute("""SELECT subscription.* FROM account_level_subscriptions subscription
                           WHERE subscription.status = 'active' AND subscription.next_charge_at <= ?
                             AND NOT EXISTS (SELECT 1 FROM account_level_subscription_payments payment
                                             WHERE payment.subscription_id = subscription.id AND payment.paid_at IS NULL
                                               AND payment.status IN ('creating', 'pending', 'waiting_for_capture'))
                           LIMIT 50""", (current_time,)).fetchall()
        for subscription in due:
            if not subscription["payment_method_id"]:
                con.execute("UPDATE account_level_subscriptions SET status = 'payment_failed', updated_at = ? WHERE id = ?", (current_time, subscription["id"]))
                continue
            payment_id = uid("levelsubpay")
            con.execute("UPDATE account_level_subscriptions SET next_charge_at = ?, updated_at = ? WHERE id = ?", (current_time + 300, current_time, subscription["id"]))
            con.execute("INSERT INTO account_level_subscription_payments(id,subscription_id,amount_value,status,created_at,updated_at) VALUES (?,?,?,'creating',?,?)", (payment_id, subscription["id"], subscription["monthly_price"], current_time, current_time))
            try:
                payment = yookassa_request("/payments", "POST", {
                    "amount": {"value": subscription["monthly_price"], "currency": "RUB"}, "capture": True,
                    "payment_method_id": subscription["payment_method_id"],
                    "description": f"Chat-Pro: продление подписки на уровень на 30 дней",
                    "metadata": {"chat_pro_level_subscription_payment_id": payment_id},
                }, idempotence_key=payment_id)
                yookassa_payment_id = str(payment.get("id", ""))
                if not yookassa_payment_id:
                    raise ValueError("ЮKassa не вернула идентификатор платежа.")
                con.execute("UPDATE account_level_subscription_payments SET yookassa_payment_id = ?, status = ?, updated_at = ? WHERE id = ?", (yookassa_payment_id, str(payment.get("status", "pending")), now(), payment_id))
                self.finalize_account_level_subscription_payment(con, con.execute("SELECT * FROM account_level_subscription_payments WHERE id = ?", (payment_id,)).fetchone())
            except ValueError:
                con.execute("UPDATE account_level_subscription_payments SET status = 'failed', updated_at = ? WHERE id = ?", (now(), payment_id))
                con.execute("UPDATE account_level_subscriptions SET status = 'payment_failed', updated_at = ? WHERE id = ?", (now(), subscription["id"]))

    def start_call(self, con, user, body):
        chat_id = body.get("chatId")
        call_type = body.get("callType")
        offer_sdp = body.get("offerSdp")
        if call_type not in ("audio", "video") or not isinstance(offer_sdp, dict):
            raise ValueError("Некорректные данные звонка.")
        chat = con.execute("SELECT * FROM chats WHERE id = ? AND type = 'direct'", (chat_id,)).fetchone()
        if not chat or not con.execute("SELECT 1 FROM chat_members WHERE chat_id = ? AND user_id = ?", (chat_id, user["id"])).fetchone():
            raise PermissionError()
        receiver = con.execute("SELECT user_id FROM chat_members WHERE chat_id = ? AND user_id != ?", (chat_id, user["id"])).fetchone()
        if not receiver:
            raise ValueError("Собеседник не найден.")
        con.execute("UPDATE calls SET status = 'ended', updated_at = ? WHERE chat_id = ? AND status IN ('ringing','accepted')", (now(), chat_id))
        call_id = uid("call")
        con.execute(
            """INSERT INTO calls(id,chat_id,caller_id,receiver_id,call_type,offer_sdp,status,created_at,updated_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (call_id, chat_id, user["id"], receiver["user_id"], call_type, dumps(offer_sdp), "ringing", now(), now()),
        )
        return self.json({"ok": True, "callId": call_id})

    def require_active_account_level(self, con, user_id):
        data = self.account_level_data(con, user_id)
        active_index = next((index for index, level in enumerate(data["levels"]) if level["id"] == "active"), None)
        current_index = next((index for index, level in enumerate(data["levels"]) if level["id"] == data["current"]["id"]), -1)
        if active_index is None or current_index < active_index:
            raise ValueError("Эта функция доступна с уровня «Активный». Повысьте уровень аккаунта.")

    def require_enhanced_account_level(self, con, user_id):
        data = self.account_level_data(con, user_id)
        current_index = next((index for index, level in enumerate(data["levels"]) if level["id"] == data["current"]["id"]), -1)
        if current_index <= 0:
            raise ValueError("Эта функция доступна на уровне выше «Обычного». Повысьте уровень аккаунта.")

    def poll_calls(self, con, user):
        rows = con.execute(
            """SELECT * FROM calls WHERE (caller_id = ? OR receiver_id = ?) AND status IN ('ringing','accepted')
               ORDER BY created_at DESC""",
            (user["id"], user["id"]),
        ).fetchall()
        calls = []
        for row in rows:
            caller = con.execute("SELECT name,username,call_ringtone,call_ringtone_data FROM users WHERE id=?", (row["caller_id"],)).fetchone()
            calls.append({
                "id": row["id"], "chatId": row["chat_id"], "callerId": row["caller_id"], "receiverId": row["receiver_id"],
                "callType": row["call_type"], "offerSdp": loads(row["offer_sdp"], {}), "answerSdp": loads(row["answer_sdp"], None),
                "status": row["status"], "callerName": caller["name"] if caller else "Пользователь", "callerRingtone": caller["call_ringtone"] if caller else "classic", "callerRingtoneData": caller["call_ringtone_data"] if caller and row["receiver_id"] == user["id"] and caller["call_ringtone"] == "custom" else None, "createdAt": row["created_at"],
            })
        return self.json({"ok": True, "calls": calls})

    def answer_call(self, con, user, body):
        call_id = body.get("callId")
        answer_sdp = body.get("answerSdp")
        row = con.execute("SELECT * FROM calls WHERE id = ?", (call_id,)).fetchone()
        if not row or row["receiver_id"] != user["id"] or row["status"] != "ringing":
            raise ValueError("Этот звонок больше недоступен.")
        con.execute("UPDATE calls SET answer_sdp = ?, status = 'accepted', updated_at = ? WHERE id = ?", (dumps(answer_sdp), now(), call_id))
        return self.json({"ok": True})

    def end_call(self, con, user, body):
        call_id = body.get("callId")
        row = con.execute("SELECT * FROM calls WHERE id = ?", (call_id,)).fetchone()
        if not row or user["id"] not in (row["caller_id"], row["receiver_id"]):
            raise PermissionError()
        con.execute("UPDATE calls SET status = 'ended', updated_at = ? WHERE id = ?", (now(), call_id))
        return self.json({"ok": True})

    def ensure_saved(self, con, user_id):
        existing = con.execute("SELECT 1 FROM chats c JOIN chat_members m ON m.chat_id=c.id WHERE c.type='saved' AND m.user_id=?", (user_id,)).fetchone()
        if existing:
            return
        chat_id = uid("chat")
        con.execute("INSERT INTO chats(id,type,title,owner_id,subscriber_count,created_at,updated_at) VALUES (?,?,?,?,?,?,?)", (chat_id, "saved", "Избранное", user_id, 1, now(), now()))
        con.execute("INSERT INTO chat_members(chat_id,user_id,role,created_at) VALUES (?,?,?,?)", (chat_id, user_id, "owner", now()))

    def evaluate_statuses(self, con, user_id):
        user = con.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        statuses = con.execute("SELECT * FROM statuses WHERE active=1").fetchall()
        for status in statuses:
            criteria = loads(status["criteria_json"], {}) or {}
            ok = True
            if criteria.get("minStars") and user["stars"] < int(criteria["minStars"]):
                ok = False
            if criteria.get("minReviews"):
                count = con.execute("SELECT count(*) c FROM reviews WHERE created_by=?", (user_id,)).fetchone()["c"]
                ok = ok and count >= int(criteria["minReviews"])
            if ok:
                con.execute("INSERT OR IGNORE INTO user_statuses(status_id,user_id,created_at) VALUES (?,?,?)", (status["id"], user_id, now()))

    def admin_bootstrap(self, con):
        settings = {r["key"]: loads(r["value"], {}) for r in con.execute("SELECT * FROM settings").fetchall()}
        users = []
        for row in con.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall():
            item = public_user(row)
            item["accountLevel"] = self.account_level_data(con, row["id"], settings.get("account_levels", []))["current"]
            users.append(item)
        chats = [chat_to_dict(r) for r in con.execute("SELECT * FROM chats ORDER BY updated_at DESC").fetchall()]
        members = [dict(r) for r in con.execute("SELECT * FROM chat_members").fetchall()]
        messages = []
        for row in con.execute("SELECT * FROM messages ORDER BY created_at DESC LIMIT 200").fetchall():
            item = message_to_dict(row)
            item["deletedByAdmin"] = bool(row["deleted_by_admin"])
            messages.append(item)
        promos = [dict(r) for r in con.execute("SELECT * FROM promotions ORDER BY created_at DESC").fetchall()]
        recommended = [dict(r) for r in con.execute("SELECT * FROM recommended_groups ORDER BY position, created_at").fetchall()]
        activity_rewards = []
        for row in con.execute("SELECT * FROM activity_rewards ORDER BY created_at DESC").fetchall():
            reward = dict(row)
            reward["criteria"] = self.normalize_activity_criteria(loads(reward.pop("criteria_json"), {}))
            reward_data = loads(reward.get("reward_json"), {})
            try:
                reward["reward"] = normalize_level_reward(reward_data or {
                    "stars": reward["reward_stars"],
                    "premiumDays": reward["premium_days"],
                }, "reward")
            except ValueError:
                reward["reward"] = {"stars": reward["reward_stars"], "premiumDays": reward["premium_days"], "limits": {}, "recurringStars": 0, "recurringIntervalDays": 0, "recurringDurationDays": 0}
            reward["claimsCount"] = con.execute("SELECT count(*) AS count FROM activity_reward_claims WHERE reward_id = ?", (reward["id"],)).fetchone()["count"]
            activity_rewards.append(reward)
        statuses = [dict(r) for r in con.execute("SELECT * FROM statuses ORDER BY created_at DESC").fetchall()]
        boosts = [dict(r) for r in con.execute("SELECT * FROM boost_jobs ORDER BY created_at DESC").fetchall()]
        demo_activity_packages = [dict(r) for r in con.execute("SELECT * FROM demo_activity_packages ORDER BY created_at DESC").fetchall()]
        demo_activity_subscriptions = [dict(r) for r in con.execute(
            """SELECT subscription.*, package.title AS package_title, chat.title AS channel_title
               FROM demo_activity_subscriptions subscription
               JOIN demo_activity_packages package ON package.id = subscription.package_id
               JOIN chats chat ON chat.id = subscription.channel_id
               ORDER BY subscription.created_at DESC LIMIT 50"""
        ).fetchall()]
        channel_growth_jobs = [dict(r) for r in con.execute(
            """SELECT job.*, chat.title AS channel_title FROM channel_growth_jobs job
               JOIN chats chat ON chat.id = job.channel_id ORDER BY job.created_at DESC LIMIT 50"""
        ).fetchall()]
        automated_commenters = [dict(r) for r in con.execute(
            """SELECT ac.id, ac.user_id, ac.created_at, u.name, u.username, u.avatar_data
               FROM automated_commenters ac JOIN users u ON u.id = ac.user_id
               ORDER BY ac.created_at DESC"""
        ).fetchall()]
        automated_comment_rules = [dict(r) for r in con.execute(
            """SELECT rule.*, c.title AS channel_title,
                      message.text AS target_message_text,
                      (SELECT count(*) FROM automated_comment_jobs job WHERE job.rule_id = rule.id) AS pending_count
               FROM automated_comment_rules rule
               JOIN chats c ON c.id = rule.channel_id
               LEFT JOIN messages message ON message.id = rule.target_message_id
               ORDER BY rule.created_at DESC"""
        ).fetchall()]
        payout_requests = [dict(r) for r in con.execute(
            """SELECT request.*, owner.name AS owner_name, owner.username AS owner_username,
                      chat.title AS channel_title, chat.type AS channel_type
               FROM channel_payout_requests request
               JOIN users owner ON owner.id = request.owner_user_id
               JOIN chats chat ON chat.id = request.channel_id
               ORDER BY request.created_at DESC LIMIT 100"""
        ).fetchall()]
        share_submissions = [dict(r) for r in con.execute(
            """SELECT submission.*, submitter.name AS submitter_name, submitter.username AS submitter_username,
                      chat.title AS channel_title
               FROM channel_share_submissions submission
               JOIN users submitter ON submitter.id = submission.submitter_id
               JOIN chats chat ON chat.id = submission.channel_id
               ORDER BY submission.created_at DESC LIMIT 200"""
        ).fetchall()]
        vk_review_submissions = [dict(r) for r in con.execute(
            """SELECT submission.*, submitter.name AS submitter_name, submitter.username AS submitter_username
               FROM vk_review_submissions submission
               JOIN users submitter ON submitter.id = submission.submitter_id
               ORDER BY submission.created_at DESC LIMIT 200"""
        ).fetchall()]
        reports = [dict(r) for r in con.execute(
            """SELECT r.*, u.name AS reporter_name, u.username AS reporter_username,
                      s.caption AS story_caption, s.media_data AS story_media_data,
                      m.text AS message_text, m.media_type AS message_media_type, m.deleted_by_admin AS message_deleted_by_admin,
                      c.title AS group_title, reported_channel.title AS channel_title
               FROM reports r
               LEFT JOIN users u ON u.id = r.created_by
               LEFT JOIN stories s ON r.target_type = 'story' AND s.id = r.target_id
               LEFT JOIN messages m ON r.target_type = 'group-post' AND m.id = r.target_id
               LEFT JOIN chats c ON c.id = m.chat_id
               LEFT JOIN chats reported_channel ON r.target_type = 'channel' AND reported_channel.id = r.target_id
               ORDER BY r.created_at DESC LIMIT 200"""
        ).fetchall()]
        return self.json({"ok": True, "settings": settings, "users": users, "chats": chats, "members": members, "messages": messages, "promotions": promos, "recommended": recommended, "activityRewards": activity_rewards, "statuses": statuses, "boosts": boosts, "channelGrowthJobs": channel_growth_jobs, "demoActivityPackages": demo_activity_packages, "demoActivitySubscriptions": demo_activity_subscriptions, "payoutRequests": payout_requests, "reports": reports, "shareSubmissions": share_submissions, "vkReviewSubmissions": vk_review_submissions, "automatedCommenters": automated_commenters, "automatedCommentRules": automated_comment_rules, "adminKeyHint": "По умолчанию: admin123"})

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def require_user(self, user):
        if not user:
            raise PermissionError()

    def require_admin(self):
        if self.headers.get("X-Admin-Key") != ADMIN_KEY:
            raise PermissionError()

    def json(self, payload, status=HTTPStatus.OK):
        data = dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_file(self, path: Path):
        if not path.resolve().is_relative_to(ROOT) or not path.exists() or path.is_dir():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        data = path.read_bytes()
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} - {fmt % args}")


def normalize_username(value) -> str:
    return str(value or "").strip().lower().removeprefix("@")


def is_review_url(value) -> bool:
    return str(value or "").strip().lower().startswith(("http://", "https://"))


def is_review_phone(value) -> bool:
    digits = re.sub(r"\D", "", str(value or ""))
    return 7 <= len(digits) <= 15 and bool(re.fullmatch(r"[+\d()\-\s.]+", str(value or "").strip()))


def is_review_telegram(value) -> bool:
    return bool(re.fullmatch(r"@?[A-Za-z0-9_]{3,64}", str(value or "").strip()))


def normalize_review_source(value) -> str:
    source = " ".join(str(value or "").strip().split())
    if is_review_url(source):
        return source
    if is_review_phone(source):
        return "+" + re.sub(r"\D", "", source)
    if is_review_telegram(source):
        return f"@{source.removeprefix('@').lower()}"
    return source.casefold()


def validate_username(username: str) -> None:
    if len(username) < 3 or len(username) > 20:
        raise ValueError("Username должен быть от 3 до 20 символов.")
    if not all(ch.isalnum() or ch == "_" for ch in username) or not username.isascii():
        raise ValueError("Username может содержать только латиницу, цифры и подчёркивание.")


def run_background_worker() -> None:
    reward_processor = object.__new__(Handler)
    while True:
        try:
            with connect() as con:
                cleanup_expired_deleted_accounts(con)
                tick_boosts(con)
                tick_channel_activity_regulator(con)
                tick_channel_growth(con)
                sync_account_level_activity_packages(con)
                tick_demo_activity(con)
                publish_scheduled_posts(con)
                poll_telegram_channels(con)
                poll_rss_channels(con)
                poll_vk_channels(con, reward_processor)
                publish_vk_channel_posts(con)
                publish_vk_channel_targets(con)
                moderate_vk_channel_targets(con, reward_processor)
                publish_automated_comments(con)
                publish_activity_comments(con)
                reward_processor.process_recurring_star_rewards(con)
                reward_processor.process_account_level_subscriptions(con)
                reward_processor.process_channel_share_submissions(con)
                reward_processor.process_vk_review_submissions(con)
                reward_processor.process_ai_agent_autopilots(con)
                reward_processor.process_ai_agent_channel_rules(con)
                reward_processor.process_ai_agent_comment_moderation(con)
        except sqlite3.Error as error:
            print(f"Ошибка фоновой обработки: {error}")
        time.sleep(5)


def main():
    init_db()
    threading.Thread(target=run_background_worker, name="background-worker", daemon=True).start()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Chat-Pro запущен: http://{HOST}:{PORT}")
    print(f"Админка: http://{HOST}:{PORT}/admin")
    server.serve_forever()


if __name__ == "__main__":
    main()
