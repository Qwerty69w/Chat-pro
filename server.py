#!/usr/bin/env python3
"""Chat-Pro local backend with admin panel.

Run: python3 server.py
Open: http://localhost:8000
Admin: http://localhost:8000/admin

This is a local demo backend. Counters, boosts and reviews work only inside this
application and do not affect real Telegram/VK/web pages.
"""

from __future__ import annotations

import base64
import hashlib
import ipaddress
import json
import mimetypes
import os
import re
import secrets
import socket
import sqlite3
import smtplib
import threading
import time
from email.message import EmailMessage
from html import unescape
from http import HTTPStatus
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib import error as urlerror
from urllib.parse import parse_qs, urlencode, urljoin, urlparse
from urllib import request as urlrequest
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "minigram.sqlite3"
ADMIN_KEY = os.environ.get("MINIGRAM_ADMIN_KEY", "admin123")
TELEGRAM_POLL_INTERVAL = 15
TELEGRAM_MEDIA_MAX_BYTES = 2_500_000
RSS_POLL_INTERVAL = 300
RSS_MAX_BYTES = 512_000
RSS_MAX_ENTRIES = 100
RSS_IMAGE_MAX_BYTES = 2_500_000
AUTH_CODE_TTL = 600
AUTH_CODE_MAX_ATTEMPTS = 5
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM = os.environ.get("SMTP_FROM", SMTP_USERNAME)
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM_NUMBER = os.environ.get("TWILIO_FROM_NUMBER", "")
CHANNEL_MANAGER_ROLES = {"owner", "admin", "author"}
LEVEL_LIMIT_KEYS = {
    "maxStars", "storiesPerDay", "storiesPerMonth", "postsPerDay",
    "groupsJoined", "groupsCreated", "communitiesJoined", "communitiesCreated",
    "channelsJoined", "channelsCreated", "savedAccounts",
}
LEVEL_CRITERIA_KEYS = {"messages", "posts", "stories", "reviews", "groups", "communities", "channels"}
DEFAULT_UI_APPEARANCE = {"outlineColor": "#65ddf8", "glowColor": "#21d5f0", "glowIntensity": 35}


def nonnegative_int(value, field_name: str, maximum: int = 1_000_000) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"Поле «{field_name}» должно быть целым числом.") from None
    if parsed < 0 or parsed > maximum:
        raise ValueError(f"Поле «{field_name}» должно быть от 0 до {maximum}.")
    return parsed


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


def normalize_level_reward(value, field_name: str) -> dict:
    if value in (None, ""):
        value = {}
    if not isinstance(value, dict):
        raise ValueError(f"Поле «{field_name}» должно быть объектом.")
    unknown = set(value) - {"stars", "premiumDays"}
    if unknown:
        raise ValueError("В награде допустимы только stars и premiumDays.")
    return {
        "stars": nonnegative_int(value.get("stars", 0), "stars"),
        "premiumDays": nonnegative_int(value.get("premiumDays", 0), "premiumDays", 3650),
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
        unknown_criteria = set(criteria) - LEVEL_CRITERIA_KEYS
        unknown_limits = set(limits) - LEVEL_LIMIT_KEYS
        if unknown_criteria or unknown_limits:
            raise ValueError("В уровне есть неподдерживаемые критерии или лимиты.")
        normalized_criteria = {
            key: nonnegative_int(criteria[key], key)
            for key in criteria if nonnegative_int(criteria[key], key)
        }
        normalized_limits = {key: nonnegative_int(limits[key], key) for key in limits}
        levels.append({
            "id": level_id,
            "title": title,
            "description": description,
            "criteria": normalized_criteria,
            "limits": normalized_limits,
            "reward": normalize_level_reward(raw_level.get("reward", {}), "reward"),
            "starsPrice": nonnegative_int(raw_level.get("starsPrice", 0), "starsPrice"),
            "purchaseReward": normalize_level_reward(raw_level.get("purchaseReward", {}), "purchaseReward"),
        })
    return levels


def now() -> int:
    return int(time.time())


def connect() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH, timeout=10)
    con.row_factory = sqlite3.Row
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


def normalize_phone(value) -> str:
    raw = str(value or "").strip()
    digits = re.sub(r"\D", "", raw)
    if not raw.startswith("+") or not 8 <= len(digits) <= 15:
        raise ValueError("Введите номер в международном формате, например +79991234567.")
    return f"+{digits}"


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
        print(f"[DEV] Код e-mail для {email}: {code}")
        return
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as client:
        client.starttls()
        client.login(SMTP_USERNAME, SMTP_PASSWORD)
        client.send_message(message)


def deliver_sms_code(phone: str, code: str, purpose: str) -> None:
    if not all((TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER)):
        print(f"[DEV] Код SMS для {phone}: {code}")
        return
    encoded = urlencode({"To": phone, "From": TWILIO_FROM_NUMBER, "Body": f"Chat-Pro: {purpose}. Код: {code}. Действует 10 минут."}).encode("utf-8")
    credentials = base64.b64encode(f"{TWILIO_ACCOUNT_SID}:{TWILIO_AUTH_TOKEN}".encode("utf-8")).decode("ascii")
    request = urlrequest.Request(
        f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json",
        data=encoded,
        headers={"Authorization": f"Basic {credentials}", "Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urlrequest.urlopen(request, timeout=15) as response:
            if response.status not in {200, 201}:
                raise ValueError("SMS-провайдер не принял сообщение.")
    except urlerror.URLError as error:
        raise ValueError("Не удалось отправить SMS-код. Попробуйте позже.") from error


def public_user(row: sqlite3.Row | dict | None) -> dict | None:
    if not row:
        return None
    return {
        "id": row["id"],
        "name": row["name"],
        "username": row["username"],
        "stars": row["stars"],
        "premiumUntil": row["premium_until"],
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
        "chatBackground": row["chat_background"],
        "chatBackgroundData": row["chat_background_data"],
        "sidebarBackgroundData": row["sidebar_background_data"],
        "nightAppearanceCustom": bool(row["night_appearance_custom"]) if "night_appearance_custom" in row.keys() else False,
        "nightOutlineColor": row["night_outline_color"] if "night_outline_color" in row.keys() else None,
        "nightGlowColor": row["night_glow_color"] if "night_glow_color" in row.keys() else None,
        "nightGlowIntensity": row["night_glow_intensity"] if "night_glow_intensity" in row.keys() else None,
        "hiddenStatusIds": loads(row["hidden_status_ids"], []),
        "groupInvitePrivacy": row["group_invite_privacy"] if "group_invite_privacy" in row.keys() else "contacts",
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
        "voiceWaveform": loads(row["voice_waveform_json"], []) if "voice_waveform_json" in row.keys() else [],
        "views": int(row["views"] or 0) + int(row["views_boost"] or 0) if "views" in row.keys() else 0,
        "reactions": reactions,
        "reactionTotal": sum(int(v) for v in reactions.values()),
        "pinned": bool(row["pinned"]),
        "pinHidden": bool(row["pin_hidden"]) if "pin_hidden" in row.keys() else False,
        "forwardedFrom": row["forwarded_from"] if "forwarded_from" in row.keys() else None,
        "sourceType": row["source_type"] if "source_type" in row.keys() else None,
        "sourceId": row["source_id"] if "source_id" in row.keys() else None,
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
              dialog_color TEXT NOT NULL DEFAULT '#ffffff',
              other_dialog_color TEXT NOT NULL DEFAULT '#ffffff',
              dialog_panel_color TEXT NOT NULL DEFAULT '#f4f8fc',
              dialog_panel_style TEXT NOT NULL DEFAULT 'interactive-light',
              dialog_bubble_style TEXT NOT NULL DEFAULT 'custom',
              dialog_font TEXT NOT NULL DEFAULT 'business',
              chat_background TEXT NOT NULL DEFAULT 'cyan',
              chat_background_data TEXT,
              sidebar_background_data TEXT,
              night_appearance_custom INTEGER NOT NULL DEFAULT 0,
              night_outline_color TEXT,
              night_glow_color TEXT,
              night_glow_intensity INTEGER,
              hidden_status_ids TEXT NOT NULL DEFAULT '[]',
              group_invite_privacy TEXT NOT NULL DEFAULT 'contacts',
              avatar_data TEXT,
              last_login_day TEXT,
              login_streak INTEGER NOT NULL DEFAULT 0,
              created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
              token TEXT PRIMARY KEY,
              user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
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
              voice_waveform_json TEXT,
              profile_user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
              views INTEGER NOT NULL DEFAULT 0,
              views_boost INTEGER NOT NULL DEFAULT 0,
              reactions_json TEXT NOT NULL DEFAULT '{}',
              pinned INTEGER NOT NULL DEFAULT 0,
              forwarded_from TEXT,
              reply_to_id TEXT REFERENCES messages(id) ON DELETE SET NULL,
              edited_at INTEGER,
              created_at INTEGER NOT NULL
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

            CREATE TABLE IF NOT EXISTS automated_commenters (
              id TEXT PRIMARY KEY,
              user_id TEXT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
              created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS automated_comment_rules (
              id TEXT PRIMARY KEY,
              channel_id TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
              target_message_id TEXT REFERENCES messages(id) ON DELETE CASCADE,
              commenter_ids_json TEXT NOT NULL DEFAULT '[]',
              texts_json TEXT NOT NULL DEFAULT '[]',
              min_delay_seconds INTEGER NOT NULL DEFAULT 300,
              max_delay_seconds INTEGER NOT NULL DEFAULT 1800,
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
              created_at INTEGER NOT NULL
            );

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

            CREATE TABLE IF NOT EXISTS star_transactions (
              id TEXT PRIMARY KEY,
              user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              amount INTEGER NOT NULL,
              kind TEXT NOT NULL,
              description TEXT NOT NULL,
              created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS activity_rewards (
              id TEXT PRIMARY KEY,
              title TEXT NOT NULL,
              description TEXT NOT NULL DEFAULT '',
              criteria_json TEXT NOT NULL DEFAULT '{}',
              reward_stars INTEGER NOT NULL DEFAULT 0,
              premium_days INTEGER NOT NULL DEFAULT 0,
              active INTEGER NOT NULL DEFAULT 1,
              created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS activity_reward_claims (
              reward_id TEXT NOT NULL REFERENCES activity_rewards(id) ON DELETE CASCADE,
              user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              claimed_at INTEGER NOT NULL,
              PRIMARY KEY (reward_id, user_id)
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
        if "chat_background" not in columns:
            con.execute("ALTER TABLE users ADD COLUMN chat_background TEXT NOT NULL DEFAULT 'cyan'")
        if "dialog_bubble_style" not in columns:
            con.execute("ALTER TABLE users ADD COLUMN dialog_bubble_style TEXT NOT NULL DEFAULT 'custom'")
        if "dialog_font" not in columns:
            con.execute("ALTER TABLE users ADD COLUMN dialog_font TEXT NOT NULL DEFAULT 'system'")
        if "other_dialog_color" not in columns:
            con.execute("ALTER TABLE users ADD COLUMN other_dialog_color TEXT NOT NULL DEFAULT '#ffffff'")
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
        if "night_appearance_custom" not in columns:
            con.execute("ALTER TABLE users ADD COLUMN night_appearance_custom INTEGER NOT NULL DEFAULT 0")
        if "night_outline_color" not in columns:
            con.execute("ALTER TABLE users ADD COLUMN night_outline_color TEXT")
        if "night_glow_color" not in columns:
            con.execute("ALTER TABLE users ADD COLUMN night_glow_color TEXT")
        if "night_glow_intensity" not in columns:
            con.execute("ALTER TABLE users ADD COLUMN night_glow_intensity INTEGER")
        chat_columns = {row["name"] for row in con.execute("PRAGMA table_info(chats)").fetchall()}
        if "invite_code" not in chat_columns:
            con.execute("ALTER TABLE chats ADD COLUMN invite_code TEXT")
        for chat in con.execute("SELECT id FROM chats WHERE invite_code IS NULL OR invite_code = ''").fetchall():
            con.execute("UPDATE chats SET invite_code = ? WHERE id = ?", (secrets.token_urlsafe(12), chat["id"]))
        if "avatar_data" not in chat_columns:
            con.execute("ALTER TABLE chats ADD COLUMN avatar_data TEXT")
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
        if "profile_user_id" not in message_columns:
            con.execute("ALTER TABLE messages ADD COLUMN profile_user_id TEXT REFERENCES users(id) ON DELETE SET NULL")
        if "pinned" not in message_columns:
            con.execute("ALTER TABLE messages ADD COLUMN pinned INTEGER NOT NULL DEFAULT 0")
        if "forwarded_from" not in message_columns:
            con.execute("ALTER TABLE messages ADD COLUMN forwarded_from TEXT")
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
        review_columns = {row["name"] for row in con.execute("PRAGMA table_info(reviews)").fetchall()}
        if "media_data" not in review_columns:
            con.execute("ALTER TABLE reviews ADD COLUMN media_data TEXT")
        if "source_type" not in review_columns:
            con.execute("ALTER TABLE reviews ADD COLUMN source_type TEXT NOT NULL DEFAULT 'website'")
        if "city" not in review_columns:
            con.execute("ALTER TABLE reviews ADD COLUMN city TEXT NOT NULL DEFAULT ''")
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
            "limits": {
                "regular": {
                    "maxStars": 1000,
                    "storiesPerDay": 3,
                    "storiesPerMonth": 30,
                    "postsPerDay": 10,
                    "groupsJoined": 25,
                    "groupsCreated": 3,
                    "communitiesJoined": 25,
                    "communitiesCreated": 3,
                    "channelsJoined": 25,
                    "channelsCreated": 3,
                    "savedAccounts": 3,
                },
                "premium": {
                    "maxStars": 100000,
                    "storiesPerDay": 20,
                    "storiesPerMonth": 300,
                    "postsPerDay": 100,
                    "groupsJoined": 500,
                    "groupsCreated": 50,
                    "communitiesJoined": 500,
                    "communitiesCreated": 50,
                    "channelsJoined": 500,
                    "channelsCreated": 50,
                    "savedAccounts": 20,
                },
            },
            "premium": {"starsPrice": 250, "days": 30, "moneyPriceLabel": "299 ₽"},
            "account_levels": [
                {"id": "starter", "title": "Начальный", "description": "Первый уровень после регистрации.", "criteria": {"messages": 0}, "limits": {"postsPerDay": 3, "storiesPerDay": 2, "groupsCreated": 1, "communitiesCreated": 1, "channelsCreated": 1, "groupsJoined": 10, "communitiesJoined": 10, "channelsJoined": 10}, "reward": {"stars": 0, "premiumDays": 0}, "starsPrice": 0, "purchaseReward": {"stars": 0, "premiumDays": 0}},
                {"id": "active", "title": "Активный", "description": "Общайтесь и наполняйте свой профиль.", "criteria": {"messages": 20, "posts": 2, "stories": 1}, "limits": {"postsPerDay": 10, "storiesPerDay": 8, "groupsCreated": 3, "communitiesCreated": 3, "channelsCreated": 3, "groupsJoined": 50, "communitiesJoined": 50, "channelsJoined": 50}, "reward": {"stars": 50, "premiumDays": 0}, "starsPrice": 120, "purchaseReward": {"stars": 0, "premiumDays": 0}},
                {"id": "pro", "title": "Профи", "description": "Для постоянных участников сообщества.", "criteria": {"messages": 100, "posts": 10, "reviews": 2}, "limits": {"postsPerDay": 30, "storiesPerDay": 20, "groupsCreated": 10, "communitiesCreated": 10, "channelsCreated": 10, "groupsJoined": 200, "communitiesJoined": 200, "channelsJoined": 200}, "reward": {"stars": 200, "premiumDays": 7}, "starsPrice": 300, "purchaseReward": {"stars": 0, "premiumDays": 0}},
            ],
            "features": {
                "regular": {"groups": True, "communities": True, "reviews": True, "donations": True},
                "premium": {"groups": True, "communities": True, "reviews": True, "donations": True},
            },
            "ui_appearance": DEFAULT_UI_APPEARANCE,
        }
        for key, value in defaults.items():
            con.execute("INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)", (key, dumps(value)))
        existing_limits_row = con.execute("SELECT value FROM settings WHERE key = 'limits'").fetchone()
        existing_limits = loads(existing_limits_row["value"], {}) if existing_limits_row else {}
        if isinstance(existing_limits, dict):
            limits_changed = False
            for tier, tier_defaults in defaults["limits"].items():
                current_tier = existing_limits.setdefault(tier, {})
                if not isinstance(current_tier, dict):
                    current_tier = existing_limits[tier] = {}
                for limit_key, limit_value in tier_defaults.items():
                    if limit_key not in current_tier:
                        current_tier[limit_key] = limit_value
                        limits_changed = True
            if limits_changed:
                con.execute("UPDATE settings SET value = ? WHERE key = 'limits'", (dumps(existing_limits),))
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
                100,
                0,
            )


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


def add_activity_reward(con, title, description, criteria, reward_stars, premium_days):
    con.execute(
        """INSERT INTO activity_rewards(id,title,description,criteria_json,reward_stars,premium_days,active,created_at)
           VALUES (?,?,?,?,?,?,1,?)""",
        (uid("activity_reward"), title, description, dumps(criteria), reward_stars, premium_days, now()),
    )


def get_user_by_token(con: sqlite3.Connection, headers) -> sqlite3.Row | None:
    auth = headers.get("Authorization", "")
    token = auth.replace("Bearer ", "", 1).strip() if auth.startswith("Bearer ") else ""
    if not token:
        return None
    return con.execute(
        "SELECT users.* FROM users JOIN sessions ON sessions.user_id = users.id WHERE sessions.token = ?",
        (token,),
    ).fetchone()


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


def publish_scheduled_posts(con: sqlite3.Connection) -> None:
    due_posts = con.execute("SELECT * FROM scheduled_posts WHERE publish_at <= ? ORDER BY publish_at, created_at", (now(),)).fetchall()
    for post in due_posts:
        con.execute(
            "INSERT INTO messages(id,chat_id,sender_id,text,media_type,media_data,views,created_at) VALUES (?,?,?,?,?,?,?,?)",
            (uid("msg"), post["chat_id"], post["sender_id"], post["text"], post["media_type"], post["media_data"], 1, post["publish_at"]),
        )
        con.execute("UPDATE chats SET updated_at = ? WHERE id = ?", (post["publish_at"], post["chat_id"]))
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


def schedule_automated_comments(con: sqlite3.Connection, message_id: str, channel_id: str, current: int | None = None) -> None:
    current = current or now()
    rules = con.execute(
        """SELECT * FROM automated_comment_rules
           WHERE channel_id = ? AND active = 1 AND starts_at <= ? AND ends_at >= ?
             AND (target_message_id IS NULL OR target_message_id = ?)""",
        (channel_id, current, current, message_id),
    ).fetchall()
    for rule in rules:
        commenter_ids = loads(rule["commenter_ids_json"], [])
        texts = [str(text).strip()[:1000] for text in loads(rule["texts_json"], []) if str(text).strip()]
        if not isinstance(commenter_ids, list) or not texts:
            continue
        minimum = max(0, int(rule["min_delay_seconds"]))
        maximum = max(minimum, int(rule["max_delay_seconds"]))
        publish_at = current
        for position, commenter_id in enumerate(commenter_ids):
            commenter = con.execute("SELECT id FROM automated_commenters WHERE id = ?", (str(commenter_id),)).fetchone()
            if not commenter:
                continue
            publish_at += minimum + secrets.randbelow(maximum - minimum + 1)
            if publish_at > int(rule["ends_at"]):
                break
            con.execute(
                """INSERT OR IGNORE INTO automated_comment_jobs(id,rule_id,message_id,commenter_id,text,publish_at,created_at)
                   VALUES (?,?,?,?,?,?,?)""",
                (uid("autocomment"), rule["id"], message_id, commenter["id"], texts[position % len(texts)], publish_at, current),
            )


def publish_automated_comments(con: sqlite3.Connection) -> None:
    current = now()
    con.execute("DELETE FROM automated_comment_jobs WHERE rule_id IN (SELECT id FROM automated_comment_rules WHERE active = 0 OR ends_at < ?)", (current,))
    jobs = con.execute(
        """SELECT job.*, commenter.user_id
           FROM automated_comment_jobs job
           JOIN automated_comment_rules rule ON rule.id = job.rule_id
           JOIN automated_commenters commenter ON commenter.id = job.commenter_id
           JOIN messages message ON message.id = job.message_id
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
        con.execute(
            "INSERT INTO channel_comments(id,message_id,user_id,text,media_data,automated,created_at) VALUES (?,?,?,?,?,?,?)",
            (uid("comment"), job["message_id"], job["user_id"], job["text"], None, 1, current),
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
                con.execute(
                    """INSERT INTO messages(id,chat_id,sender_id,text,media_type,media_data,views,forwarded_from,source_type,source_id,created_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (uid("msg"), link["channel_id"], sender["id"], text, "photo" if media_data else None,
                     media_data, 1, f"Telegram · {source_title}", "telegram", str(telegram_message_id), int(post.get("date", current) or current)),
                )
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
                    tick_boosts(con)
                    publish_scheduled_posts(con)
                    poll_telegram_channels(con)
                    poll_rss_channels(con)
                    publish_automated_comments(con)
                    return self.handle_api(con, method, path, parse_qs(parsed.query))
            if method in {"GET", "HEAD"} and path.startswith("/media/messages/"):
                with connect() as con:
                    media_user = get_user_by_token(con, self.headers)
                    media_token = parse_qs(parsed.query).get("token", [""])[0]
                    if not media_user and media_token:
                        media_user = con.execute(
                            "SELECT users.* FROM users JOIN sessions ON sessions.user_id = users.id WHERE sessions.token = ?",
                            (media_token,),
                        ).fetchone()
                    self.require_user(media_user)
                    message_id = path.removeprefix("/media/messages/").removesuffix(".m4a").removesuffix(".mp4")
                    return self.send_message_media(con, media_user, message_id)
            if path == "/admin":
                return self.send_file(ROOT / "admin.html")
            if path == "/" or path.startswith("/invite/"):
                return self.send_file(ROOT / "index.html")
            return self.send_file(ROOT / path.lstrip("/"))
        except ConnectionError:
            return
        except ValueError as error:
            return self.json({"ok": False, "error": str(error)}, HTTPStatus.BAD_REQUEST)
        except PermissionError:
            return self.json({"ok": False, "error": "Нет доступа."}, HTTPStatus.FORBIDDEN)
        except Exception as error:  # Keep local demo debuggable.
            return self.json({"ok": False, "error": f"Ошибка сервера: {error}"}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def handle_api(self, con: sqlite3.Connection, method: str, path: str, query):
        body = self.read_json() if method == "POST" else {}
        user = get_user_by_token(con, self.headers)

        if path == "/api/register" and method == "POST":
            return self.register(con, body)
        if path == "/api/register/verify" and method == "POST":
            return self.verify_registration(con, body)
        if path == "/api/auth-challenges/resend" and method == "POST":
            return self.resend_auth_challenge(con, body)
        if path == "/api/login" and method == "POST":
            return self.login(con, body)
        if path == "/api/password-reset/request" and method == "POST":
            return self.request_password_reset(con, body)
        if path == "/api/password-reset/confirm" and method == "POST":
            return self.confirm_password_reset(con, body)
        if path == "/api/bootstrap" and method == "GET":
            self.require_user(user)
            return self.bootstrap(con, user)
        if path == "/api/users" and method == "GET":
            self.require_user(user)
            q = (query.get("q", [""])[0] or "").lower().replace("@", "")
            rows = con.execute(
                "SELECT * FROM users WHERE id != ? AND (username LIKE ? OR lower(name) LIKE ?) ORDER BY username LIMIT 12",
                (user["id"], f"%{q}%", f"%{q}%"),
            ).fetchall()
            return self.json({"ok": True, "users": [public_user(r) for r in rows]})
        if path == "/api/username" and method == "POST":
            self.require_user(user)
            username = normalize_username(body.get("username"))
            validate_username(username)
            if username_taken(con, username, user["id"]):
                raise ValueError("Этот username уже занят. Выберите другой.")
            con.execute("UPDATE users SET username = ? WHERE id = ?", (username, user["id"]))
            return self.json({"ok": True})
        if path == "/api/preferences" and method == "POST":
            self.require_user(user)
            theme = str(body.get("theme", "light"))
            if theme not in {"light", "dark"}:
                raise ValueError("Неизвестный режим оформления.")
            background = str(body.get("chatBackground", "default"))
            allowed_backgrounds = {"default", "whatsapp", "mint", "aurora", "noir", "cyan", "mist", "sunset", "ocean", "lavender", "forest", "midnight", "ember", "iris", "prism", "live", "custom"}
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
            dialog_color = str(body.get("dialogColor", "#ffffff"))
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
                "UPDATE users SET theme = ?, site_color = ?, site_background = ?, site_background_data = ?, dialog_color = ?, other_dialog_color = ?, dialog_panel_color = ?, dialog_panel_style = ?, dialog_bubble_style = ?, dialog_font = ?, chat_background = ?, chat_background_data = ?, sidebar_background_data = ?, hidden_status_ids = ?, group_invite_privacy = ?, night_appearance_custom = ?, night_outline_color = ?, night_glow_color = ?, night_glow_intensity = ? WHERE id = ?",
                (theme, site_color, site_background, site_background_data, dialog_color, other_dialog_color, dialog_panel_color, dialog_panel_style, dialog_bubble_style, dialog_font, background, background_data, sidebar_background_data, dumps(body.get("hiddenStatusIds", [])), group_invite_privacy, int(night_appearance_custom), night_appearance["outlineColor"] if night_appearance else None, night_appearance["glowColor"] if night_appearance else None, night_appearance["glowIntensity"] if night_appearance else None, user["id"]),
            )
            return self.json({"ok": True})
        if path == "/api/profile/avatar" and method == "POST":
            self.require_user(user)
            return self.update_avatar(con, user, body)
        if path == "/api/profile/posts" and method == "POST":
            self.require_user(user)
            return self.create_profile_post(con, user, body)
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
        if path == "/api/channels/appearance" and method == "POST":
            self.require_user(user)
            return self.update_channel_appearance(con, user, body)
        if path == "/api/channels/comments" and method == "POST":
            self.require_user(user)
            return self.add_channel_comment(con, user, body)
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
        if path == "/api/buy-premium" and method == "POST":
            self.require_user(user)
            return self.buy_premium(con, user, body)
        if path == "/api/reviews" and method == "POST":
            self.require_user(user)
            return self.add_review(con, user, body)
        if path == "/api/reports" and method == "POST":
            self.require_user(user)
            return self.add_report(con, user, body)
        if path == "/api/promotions/claim" and method == "POST":
            self.require_user(user)
            return self.claim_promotion(con, user, body.get("promotionId"))
        if path == "/api/activity-rewards/claim" and method == "POST":
            self.require_user(user)
            return self.claim_activity_reward(con, user, body.get("rewardId"))
        if path == "/api/account-level/claim" and method == "POST":
            self.require_user(user)
            return self.claim_account_level_reward(con, user, body.get("levelId"))
        if path == "/api/account-level/buy" and method == "POST":
            self.require_user(user)
            return self.buy_account_level(con, user, body.get("levelId"))
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
            elif key == "limits":
                requested = body.get("value")
                if not isinstance(requested, dict):
                    raise ValueError("Лимиты должны быть объектом.")
                current_row = con.execute("SELECT value FROM settings WHERE key = 'limits'").fetchone()
                current = loads(current_row["value"], {}) if current_row else {}
                if not isinstance(current, dict):
                    current = {}
                merged = {}
                for tier in ("regular", "premium"):
                    requested_tier = requested.get(tier, {})
                    if not isinstance(requested_tier, dict):
                        raise ValueError(f"Лимиты {tier} должны быть объектом.")
                    current_tier = current.get(tier, {})
                    merged[tier] = {**(current_tier if isinstance(current_tier, dict) else {}), **requested_tier}
                value = self.normalize_tier_limits(merged)
            elif key == "premium":
                value = self.normalize_premium_settings(body.get("value"))
            elif key == "features":
                value = body.get("value")
                if not isinstance(value, dict):
                    raise ValueError("Настройки функций должны быть объектом.")
            elif key == "ui_appearance":
                value = normalize_ui_appearance(body.get("value"))
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
        if path == "/api/admin/users/premium" and method == "POST":
            until = now() + int(body.get("days", 30)) * 86400
            con.execute("UPDATE users SET premium_until = ? WHERE id = ?", (until, body.get("userId")))
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
            reward_stars = max(0, int(body.get("rewardStars", 0) or 0))
            premium_days = max(0, int(body.get("premiumDays", 0) or 0))
            if not reward_stars and not premium_days:
                raise ValueError("Укажите количество звёзд или дней премиума.")
            add_activity_reward(con, title[:120], str(body.get("description", "")).strip()[:1000], criteria, reward_stars, premium_days)
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
        if path == "/api/admin/automated-commenters" and method == "POST":
            return self.create_automated_commenter(con, body)
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
        contact_type = str(body.get("contactType", ""))
        if contact_type not in {"email", "phone"}:
            raise ValueError("Выберите e-mail или номер телефона.")
        email = normalize_email(body.get("email")) if contact_type == "email" else None
        phone = normalize_phone(body.get("phone")) if contact_type == "phone" else None
        if not name:
            raise ValueError("Введите имя.")
        if len(password) < 8:
            raise ValueError("Пароль должен быть не короче 8 символов.")
        if con.execute("SELECT 1 FROM users WHERE email = ? COLLATE NOCASE OR phone = ?", (email, phone)).fetchone():
            raise ValueError("Этот e-mail или номер уже используется.")
        challenge_id = self.create_auth_challenge(
            con, "register", email, phone, None,
            {"name": name[:80], "username": username, "password": hash_password(password), "contactType": contact_type},
            "Подтверждение регистрации",
        )
        return self.json({"ok": True, "challengeId": challenge_id, "message": "Код подтверждения отправлен."})

    def verify_registration(self, con, body):
        challenge = self.verify_auth_challenge(con, body, "register")
        payload = loads(challenge["payload_json"], {})
        username = str(payload.get("username", ""))
        if not username or username_taken(con, username):
            raise ValueError("Username уже занят. Начните регистрацию заново.")
        if con.execute("SELECT 1 FROM users WHERE email = ? COLLATE NOCASE OR phone = ?", (challenge["email"], challenge["phone"])).fetchone():
            raise ValueError("Этот e-mail или номер уже используется.")
        user_id = uid("user")
        con.execute(
            """INSERT INTO users(id,name,username,password,email,phone,email_verified,phone_verified,stars,dialog_color,other_dialog_color,dialog_panel_color,dialog_panel_style,dialog_bubble_style,dialog_font,chat_background,created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (user_id, payload["name"], username, payload["password"], challenge["email"], challenge["phone"], int(payload["contactType"] == "email"), int(payload["contactType"] == "phone"), 50, "#ffffff", "#ffffff", "#f4f8fc", "interactive-light", "custom", "business", "cyan", now()),
        )
        con.execute("DELETE FROM auth_challenges WHERE id = ?", (challenge["id"],))
        self.ensure_saved(con, user_id)
        return self.issue_token(con, user_id)

    def login(self, con, body):
        username = normalize_username(body.get("username"))
        user = con.execute("SELECT * FROM users WHERE username = ? COLLATE NOCASE", (username,)).fetchone()
        if not user or not password_matches(user["password"], str(body.get("password", ""))):
            raise ValueError("Неверный username или пароль.")
        if not user["password"].startswith("pbkdf2_sha256$"):
            con.execute("UPDATE users SET password = ? WHERE id = ?", (hash_password(str(body.get("password", ""))), user["id"]))
        self.update_login_streak(con, user["id"])
        self.ensure_saved(con, user["id"])
        return self.issue_token(con, user["id"])

    def create_auth_challenge(self, con, purpose, email, phone, user_id, payload, message) -> str:
        current = now()
        con.execute("DELETE FROM auth_challenges WHERE expires_at < ? OR (purpose = ? AND email = ? AND phone = ?)", (current, purpose, email, phone))
        contact_type = payload.get("contactType") if purpose == "register" else payload.get("recoveryContact")
        email_code = generate_auth_code() if contact_type == "email" else None
        phone_code = generate_auth_code() if contact_type == "phone" else None
        challenge_id = uid("auth")
        con.execute(
            """INSERT INTO auth_challenges(id,purpose,email,phone,user_id,payload_json,email_code_hash,phone_code_hash,expires_at,created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (challenge_id, purpose, email, phone, user_id, dumps(payload), hash_password(email_code) if email_code else None, hash_password(phone_code) if phone_code else None, current + AUTH_CODE_TTL, current),
        )
        if email_code:
            deliver_email_code(email, email_code, message)
        if phone_code:
            deliver_sms_code(phone, phone_code, message)
        return challenge_id

    def verify_auth_challenge(self, con, body, purpose):
        challenge_id = str(body.get("challengeId", ""))
        challenge = con.execute("SELECT * FROM auth_challenges WHERE id = ? AND purpose = ?", (challenge_id, purpose)).fetchone()
        if not challenge or challenge["expires_at"] < now():
            raise ValueError("Код истёк. Запросите новые коды.")
        if challenge["attempts"] >= AUTH_CODE_MAX_ATTEMPTS:
            raise ValueError("Слишком много неверных попыток. Запросите новые коды.")
        code = str(body.get("code", ""))
        contact_type = loads(challenge["payload_json"], {}).get("contactType" if purpose == "register" else "recoveryContact")
        code_hash = challenge["email_code_hash"] if contact_type == "email" else challenge["phone_code_hash"]
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
        payload = loads(challenge["payload_json"], {})
        contact_type = payload.get("contactType" if purpose == "register" else "recoveryContact")
        if contact_type not in {"email", "phone"}:
            raise ValueError("Контакт для подтверждения не найден.")
        code = generate_auth_code()
        column = "email_code_hash" if contact_type == "email" else "phone_code_hash"
        message = "Подтверждение регистрации" if purpose == "register" else "Восстановление пароля"
        con.execute(
            f"UPDATE auth_challenges SET {column} = ?, attempts = 0, expires_at = ?, created_at = ? WHERE id = ?",
            (hash_password(code), now() + AUTH_CODE_TTL, now(), challenge_id),
        )
        if contact_type == "email":
            deliver_email_code(challenge["email"], code, message)
        else:
            deliver_sms_code(challenge["phone"], code, message)
        return self.json({"ok": True, "message": "Новый код отправлен на тот же контакт."})

    def request_password_reset(self, con, body):
        contact = str(body.get("contact", "")).strip()
        is_email = "@" in contact
        try:
            normalized_contact = normalize_email(contact) if is_email else normalize_phone(contact)
        except ValueError:
            return self.json({"ok": True, "message": "Если контакт найден, инструкции по восстановлению отправлены."})
        user = con.execute("SELECT * FROM users WHERE email = ? COLLATE NOCASE OR phone = ?", (normalized_contact, normalized_contact)).fetchone()
        if user:
            contact_type = "email" if is_email else "phone"
            challenge_id = self.create_auth_challenge(con, "password_reset", user["email"], user["phone"], user["id"], {"recoveryContact": contact_type}, "Восстановление пароля")
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

    def issue_token(self, con, user_id):
        token = secrets.token_urlsafe(24)
        con.execute("INSERT INTO sessions(token,user_id,created_at) VALUES (?,?,?)", (token, user_id, now()))
        user = con.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return self.json({"ok": True, "token": token, "user": public_user(user)})

    def update_login_streak(self, con, user_id):
        today = time.strftime("%Y-%m-%d")
        user = con.execute("SELECT last_login_day, login_streak FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user or user["last_login_day"] == today:
            return
        con.execute("UPDATE users SET last_login_day = ?, login_streak = login_streak + 1 WHERE id = ?", (today, user_id))

    def bootstrap(self, con, user):
        self.ensure_saved(con, user["id"])
        self.evaluate_statuses(con, user["id"])
        users = [public_user(r) for r in con.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()]
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
                 AND (c.type != 'secret' OR EXISTS(SELECT 1 FROM secret_chat_unlocks scu WHERE scu.chat_id = c.id AND scu.user_id = ?))
               ORDER BY updated_at DESC""",
            (user["id"], user["id"], user["id"], user["id"], user["id"], user["id"], user["id"]),
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
                       OR EXISTS(
                           SELECT 1 FROM chat_members viewer
                           WHERE viewer.chat_id = c.id
                             AND viewer.user_id = ?
                             AND viewer.role IN ('owner', 'admin', 'author')
                       )
                 )""",
            (user["id"], user["id"], user["id"]),
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
        channel_comments = [dict(r) for r in con.execute(
            "SELECT cc.* FROM channel_comments cc JOIN messages m ON m.id = cc.message_id JOIN chats c ON c.id = m.chat_id WHERE c.type = 'channel' ORDER BY cc.created_at"
        ).fetchall()]
        notifications = [dict(r) for r in con.execute("SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT 30", (user["id"],)).fetchall()]
        messages = [message_to_dict(r) for r in con.execute(
            """SELECT m.id, m.chat_id, m.sender_id, m.profile_user_id, m.text, m.media_type, m.voice_waveform_json, m.views, m.views_boost, m.reactions_json, m.pinned, m.forwarded_from, m.source_type, m.source_id, m.reply_to_id, m.edited_at, m.created_at,
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
                 AND (c.type != 'secret' OR EXISTS(SELECT 1 FROM secret_chat_unlocks scu WHERE scu.chat_id = c.id AND scu.user_id = ?))
               ORDER BY m.created_at""",
            (user["id"], user["id"], user["id"], user["id"], user["id"]),
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
        me["hiddenStoryAuthorIds"] = [r["author_id"] for r in con.execute("SELECT author_id FROM hidden_story_authors WHERE user_id = ? ORDER BY created_at DESC", (user["id"],)).fetchall()]
        me["storyHiddenFromIds"] = [r["blocked_user_id"] for r in con.execute("SELECT blocked_user_id FROM story_privacy_blocks WHERE owner_id = ? ORDER BY created_at DESC", (user["id"],)).fetchall()]
        return self.json({"ok": True, "me": me, "users": users, "chats": chats, "members": members, "messages": messages, "scheduledPosts": scheduled_posts, "channelLinks": channel_links, "telegramChannelLinks": telegram_channel_links, "rssChannelLinks": rss_channel_links, "channelComments": channel_comments, "notifications": notifications, "posts": posts, "stories": stories, "reviews": reviews, "settings": settings, "accountLevel": account_level, "promotions": promotions, "activityRewards": activity_rewards, "statuses": statuses, "userStatuses": user_statuses, "recommended": recommended, "starTransactions": star_transactions})

    def has_chat_access(self, con, user_id, chat_id):
        return bool(con.execute(
            """SELECT 1 FROM chat_members cm
               JOIN chats c ON c.id = cm.chat_id
               WHERE cm.chat_id = ? AND cm.user_id = ?
                 AND (c.type != 'secret' OR EXISTS(
                   SELECT 1 FROM secret_chat_unlocks scu
                   WHERE scu.chat_id = c.id AND scu.user_id = ?
                 ))""",
            (chat_id, user_id, user_id),
        ).fetchone())

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

    def normalize_tier_limits(self, value):
        if not isinstance(value, dict):
            raise ValueError("Лимиты должны быть объектом.")
        normalized = {}
        for tier in ("regular", "premium"):
            raw_tier = value.get(tier, {})
            if not isinstance(raw_tier, dict):
                raise ValueError(f"Лимиты {tier} должны быть объектом.")
            unknown = set(raw_tier) - LEVEL_LIMIT_KEYS
            if unknown:
                raise ValueError("В лимитах есть неподдерживаемые поля.")
            normalized[tier] = {key: nonnegative_int(raw_tier.get(key, 0), key) for key in LEVEL_LIMIT_KEYS}
        return normalized

    def normalize_premium_settings(self, value):
        if not isinstance(value, dict):
            raise ValueError("Настройки премиума должны быть объектом.")
        return {
            "starsPrice": nonnegative_int(value.get("starsPrice", 250), "starsPrice"),
            "days": nonnegative_int(value.get("days", 30), "days", 3650),
            "moneyPriceLabel": str(value.get("moneyPriceLabel", "")).strip()[:80],
        }

    def effective_limits(self, con, user_id, level: dict) -> dict:
        limits_row = con.execute("SELECT value FROM settings WHERE key = 'limits'").fetchone()
        tier_limits = loads(limits_row["value"], {}) if limits_row else {}
        user = con.execute("SELECT premium_until FROM users WHERE id = ?", (user_id,)).fetchone()
        tier = "premium" if user and int(user["premium_until"] or 0) > now() else "regular"
        base_limits = tier_limits.get(tier, {}) if isinstance(tier_limits, dict) else {}
        return {**{key: int(base_limits.get(key, 0) or 0) for key in LEVEL_LIMIT_KEYS}, **level.get("limits", {})}

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

    def update_avatar(self, con, user, body):
        avatar = str(body.get("avatarData", ""))
        if not avatar.startswith("data:image/") or len(avatar) > 2_500_000:
            raise ValueError("Загрузите изображение до 1,8 МБ в формате PNG, JPG или WebP.")
        con.execute("UPDATE users SET avatar_data = ? WHERE id = ?", (avatar, user["id"]))
        return self.json({"ok": True})

    def create_profile_post(self, con, user, body):
        text = str(body.get("text", "")).strip()
        media = str(body.get("mediaData", ""))
        if (not text and not media) or len(text) > 3000:
            raise ValueError("Пост должен содержать текст или фото, текст — до 3000 символов.")
        if media and (not media.startswith("data:image/") or len(media) > 3_500_000):
            raise ValueError("Фото поста должно быть изображением до 2,5 МБ.")
        maximum = int(self.account_level_data(con, user["id"]).get("limits", {}).get("postsPerDay", 0) or 0)
        if maximum:
            created_today = con.execute(
                "SELECT count(*) AS count FROM profile_posts WHERE user_id = ? AND created_at >= ?",
                (user["id"], now() - 86400),
            ).fetchone()["count"]
            if created_today >= maximum:
                raise ValueError(f"На вашем уровне можно публиковать до {maximum} постов в сутки.")
        con.execute("INSERT INTO profile_posts(id,user_id,text,media_data,created_at) VALUES (?,?,?,?,?)", (uid("post"), user["id"], text, media or None, now()))
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
        member_ids = sorted([user["id"], author_id])
        chat = con.execute(
            "SELECT c.id FROM chats c JOIN chat_members a ON a.chat_id = c.id JOIN chat_members b ON b.chat_id = c.id WHERE c.type = 'direct' AND a.user_id = ? AND b.user_id = ?",
            (member_ids[0], member_ids[1]),
        ).fetchone()
        if chat:
            chat_id = chat["id"]
        else:
            chat_id = uid("chat")
            con.execute("INSERT INTO chats(id,type,title,owner_id,created_at,updated_at) VALUES (?,?,?,?,?,?)", (chat_id, "direct", "Личный чат", user["id"], now(), now()))
            for member_id in member_ids:
                con.execute("INSERT INTO chat_members(chat_id,user_id,role,created_at) VALUES (?,?,?,?)", (chat_id, member_id, "member", now()))
        con.execute("DELETE FROM hidden_chats WHERE chat_id = ? AND user_id IN (?, ?)", (chat_id, user["id"], author_id))
        con.execute(
            "INSERT INTO messages(id,chat_id,sender_id,text,media_type,media_data,views,created_at) VALUES (?,?,?,?,?,?,?,?)",
            (uid("msg"), chat_id, user["id"], emoji, "photo" if post["media_data"] else None, post["media_data"], 1, now()),
        )
        con.execute("UPDATE chats SET updated_at = ? WHERE id = ?", (now(), chat_id))
        return self.json({"ok": True, "chatId": chat_id})

    def create_story(self, con, user, body):
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
            ids = sorted([user["id"], other_id])
            existing = con.execute(
                "SELECT c.* FROM chats c JOIN chat_members a ON a.chat_id=c.id JOIN chat_members b ON b.chat_id=c.id WHERE c.type='direct' AND a.user_id=? AND b.user_id=?",
                (ids[0], ids[1]),
            ).fetchone()
            if existing:
                con.execute("DELETE FROM hidden_chats WHERE chat_id = ? AND user_id = ?", (existing["id"], user["id"]))
                return self.json({"ok": True, "chat": chat_to_dict(existing)})
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

        if chat_type not in ("group", "community", "channel"):
            raise ValueError("Неизвестный тип чата.")
        limits = self.account_level_data(con, user["id"]).get("limits", {})
        limit_key = {"group": "groupsCreated", "community": "communitiesCreated", "channel": "channelsCreated"}[chat_type]
        maximum = int(limits.get(limit_key, 0) or 0)
        if maximum:
            existing = con.execute("SELECT count(*) AS count FROM chats WHERE owner_id = ? AND type = ?", (user["id"], chat_type)).fetchone()["count"]
            if existing >= maximum:
                label = {"group": "групп", "community": "бесед", "channel": "каналов"}[chat_type]
                raise ValueError(f"На вашем уровне доступно до {maximum} {label}.")
        if chat_type == "channel":
            title = str(body.get("title", "")).strip() or "Новый канал"
            settings = {"showViews": True, "showSubscribers": True, "showReactions": True, "commentsEnabled": True, "isPublic": True}
            chat_id = uid("chat")
            con.execute(
                "INSERT INTO chats(id,type,title,description,invite_code,owner_id,settings_json,subscriber_count,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (chat_id, "channel", title, str(body.get("description", "")), secrets.token_urlsafe(12), user["id"], dumps(settings), 1, now(), now()),
            )
            con.execute("INSERT INTO chat_members(chat_id,user_id,role,created_at) VALUES (?,?,?,?)", (chat_id, user["id"], "owner", now()))
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
        chat = con.execute("SELECT type, owner_id FROM chats WHERE id = ?", (chat_id,)).fetchone()
        if not chat or chat["type"] not in {"group", "community", "channel"}:
            raise ValueError("Не выбран чат.")
        already_joined = con.execute("SELECT 1 FROM chat_members WHERE chat_id = ? AND user_id = ?", (chat_id, user["id"])).fetchone()
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
            for key in ("showViews", "showSubscribers", "showReactions", "commentsEnabled", "isPublic"):
                if key in body:
                    settings[key] = bool(body[key])
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

    def add_message(self, con, user, body):
        chat_id = body.get("chatId")
        text = str(body.get("text", "")).strip()
        media_type = str(body.get("mediaType", "")).strip() or None
        media_data = str(body.get("mediaData", "")) or None
        raw_voice_waveform = body.get("voiceWaveform", [])
        profile_user_id = str(body.get("profileUserId", "")).strip() or None
        file_name = str(body.get("fileName", "")).strip()[:240]
        reply_to_id = str(body.get("replyToId", "")).strip() or None
        allowed_media = {None, "photo", "video", "voice", "circle", "document"}
        if media_type not in allowed_media:
            raise ValueError("Этот тип вложения не поддерживается.")
        if not isinstance(raw_voice_waveform, list):
            raise ValueError("Некорректные данные голосового сообщения.")
        voice_waveform = [max(0, min(100, int(value))) for value in raw_voice_waveform[:64] if isinstance(value, (int, float))] if media_type == "voice" else []
        if not text and not media_data and not profile_user_id:
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
        if chat and chat["type"] == "channel" and self.chat_member_role(con, chat_id, user["id"]) not in CHANNEL_MANAGER_ROLES:
            raise PermissionError("Публиковать в канале могут только создатель и назначенные администраторы.")
        if reply_to_id and not con.execute("SELECT 1 FROM messages WHERE id = ? AND chat_id = ?", (reply_to_id, chat_id)).fetchone():
            raise ValueError("Сообщение для ответа не найдено.")
        msg_id = uid("msg")
        stored_text = f"Документ: {file_name}" if media_type == "document" and not text else text
        con.execute("INSERT INTO messages(id,chat_id,sender_id,profile_user_id,text,media_type,media_data,voice_waveform_json,views,reply_to_id,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)", (msg_id, chat_id, user["id"], profile_user_id, stored_text, media_type, media_data, dumps(voice_waveform), 1, reply_to_id, now()))
        con.execute("UPDATE chats SET updated_at=? WHERE id=?", (now(), chat_id))
        if chat and chat["type"] == "channel":
            link = con.execute("SELECT target_chat_id FROM channel_links WHERE channel_id = ?", (chat_id,)).fetchone()
            if link:
                con.execute("INSERT INTO messages(id,chat_id,sender_id,text,media_type,media_data,views,forwarded_from,created_at) VALUES (?,?,?,?,?,?,?,?,?)", (uid("msg"), link["target_chat_id"], user["id"], text, media_type, media_data, 1, chat["title"], now()))
                con.execute("UPDATE chats SET updated_at=? WHERE id=?", (now(), link["target_chat_id"]))
        return self.json({"ok": True, "messageId": msg_id})

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
        count = con.execute("SELECT count(*) FROM rss_channel_sources WHERE channel_id = ?", (channel_id,)).fetchone()[0]
        if count >= 10:
            raise ValueError("К одному каналу можно подключить до 10 RSS-источников.")
        feed_url = validate_rss_url(body.get("feedUrl"))
        feed_title, entries = fetch_rss_feed(feed_url)
        current = now()
        existing = con.execute("SELECT id FROM rss_channel_sources WHERE channel_id = ? AND feed_url = ?", (channel_id, feed_url)).fetchone()
        if existing:
            raise ValueError("Этот RSS-источник уже подключён к каналу.")
        source_id = uid("rss")
        con.executemany(
            "INSERT OR IGNORE INTO rss_source_imported_posts(source_id,entry_id,imported_at) VALUES (?,?,?)",
            [(source_id, entry["id"], current) for entry in entries],
        )
        con.execute(
            """INSERT INTO rss_channel_sources(id,channel_id,feed_url,feed_title,next_poll_at,last_sync_at,last_error,created_by,created_at)
               VALUES (?,?,?,?,?,?,NULL,?,?)""",
            (source_id, channel_id, feed_url, feed_title, current + RSS_POLL_INTERVAL, current, user["id"], current),
        )
        return self.json({"ok": True, "connected": True, "sourceId": source_id, "feedTitle": feed_title})

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
        message = con.execute("SELECT m.chat_id, c.settings_json FROM messages m JOIN chats c ON c.id = m.chat_id WHERE m.id = ? AND c.type = 'channel'", (message_id,)).fetchone()
        if not message or not self.has_chat_access(con, user["id"], message["chat_id"]):
            raise PermissionError("Нет доступа к публикации.")
        if not loads(message["settings_json"], {}).get("commentsEnabled", True):
            raise PermissionError("Комментарии отключены автором канала.")
        if (not text and not media_data) or len(text) > 1000:
            raise ValueError("Комментарий должен содержать текст до 1000 символов или фото.")
        if media_data and (not media_data.startswith("data:image/") or len(media_data) > 2_500_000):
            raise ValueError("К комментарию можно прикрепить изображение PNG, JPG или WebP до 1,8 МБ.")
        con.execute("INSERT INTO channel_comments(id,message_id,user_id,text,media_data,created_at) VALUES (?,?,?,?,?,?)", (uid("comment"), message_id, user["id"], text, media_data or None, now()))
        return self.json({"ok": True})

    def create_automated_commenter(self, con, body):
        name = " ".join(str(body.get("name", "")).strip().split())[:80]
        if not name:
            raise ValueError("Введите имя автокомментатора.")
        avatar_data = str(body.get("avatarData", "") or "")
        if avatar_data and (not avatar_data.startswith("data:image/") or len(avatar_data) > 2_500_000):
            raise ValueError("Аватар должен быть изображением PNG, JPG или WebP до 1,8 МБ.")
        username = f"autocomment_{secrets.token_hex(5)}"
        user_id = uid("user")
        current = now()
        con.execute(
            """INSERT INTO users(id,name,username,password,stars,dialog_color,other_dialog_color,dialog_panel_color,dialog_panel_style,dialog_bubble_style,dialog_font,chat_background,avatar_data,created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (user_id, name, username, secrets.token_urlsafe(24), 0, "#ffffff", "#ffffff", "#f4f8fc", "interactive-light", "custom", "business", "cyan", avatar_data or None, current),
        )
        commenter_id = uid("autocommenter")
        con.execute("INSERT INTO automated_commenters(id,user_id,created_at) VALUES (?,?,?)", (commenter_id, user_id, current))
        return self.json({"ok": True, "commenterId": commenter_id})

    def create_automated_comment_rule(self, con, body):
        channel_id = str(body.get("channelId", ""))
        target_message_id = str(body.get("targetMessageId", "")).strip() or None
        channel = con.execute("SELECT id FROM chats WHERE id = ? AND type = 'channel'", (channel_id,)).fetchone()
        if not channel:
            raise ValueError("Выберите канал.")
        commenter_ids = list(dict.fromkeys(str(item) for item in body.get("commenterIds", []) if item))
        if not commenter_ids or len(commenter_ids) > 20:
            raise ValueError("Выберите от 1 до 20 автокомментаторов.")
        found_commenters = con.execute(
            f"SELECT id FROM automated_commenters WHERE id IN ({','.join('?' for _ in commenter_ids)})",
            commenter_ids,
        ).fetchall()
        if len(found_commenters) != len(commenter_ids):
            raise ValueError("Один из автокомментаторов не найден.")
        texts = [" ".join(str(text).strip().split())[:1000] for text in body.get("texts", []) if str(text).strip()]
        if not texts or len(texts) > 30:
            raise ValueError("Добавьте от 1 до 30 текстов комментариев.")
        minimum = nonnegative_int(body.get("minDelayMinutes", 5), "minDelayMinutes", 10_080) * 60
        maximum = nonnegative_int(body.get("maxDelayMinutes", 30), "maxDelayMinutes", 10_080) * 60
        if minimum > maximum:
            raise ValueError("Минимальная задержка не может быть больше максимальной.")
        duration_days = nonnegative_int(body.get("durationDays", 2), "durationDays", 30)
        if not duration_days:
            raise ValueError("Укажите срок работы от 1 до 30 дней.")
        current = now()
        if target_message_id:
            target = con.execute(
                "SELECT id FROM messages WHERE id = ? AND chat_id = ? AND source_type = 'rss'",
                (target_message_id, channel_id),
            ).fetchone()
            if not target:
                raise ValueError("Выберите RSS-публикацию указанного канала.")
        rule_id = uid("autocommentrule")
        con.execute(
            """INSERT INTO automated_comment_rules(id,channel_id,target_message_id,commenter_ids_json,texts_json,min_delay_seconds,max_delay_seconds,starts_at,ends_at,active,created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (rule_id, channel_id, target_message_id, dumps(commenter_ids), dumps(texts), minimum, maximum, current, current + duration_days * 86400, 1, current),
        )
        if target_message_id:
            schedule_automated_comments(con, target_message_id, channel_id, current)
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
                     OR (c.type = 'channel' AND (
                         EXISTS(SELECT 1 FROM recommended_groups rg WHERE rg.chat_id = c.id)
                         OR COALESCE(json_extract(c.settings_json, '$.isPublic'), 1) = 1
                     ))
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
            f"""SELECT id, chat_id, sender_id, text, media_type, media_data FROM messages
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
        for message in messages:
            source_chat = con.execute("SELECT type, title FROM chats WHERE id = ?", (message["chat_id"],)).fetchone()
            forwarded_from = None
            if source_chat and source_chat["type"] != "saved":
                original_sender = con.execute("SELECT name FROM users WHERE id = ?", (message["sender_id"],)).fetchone()
                forwarded_from = original_sender["name"] if original_sender else source_chat["title"]
            con.execute(
                "INSERT INTO messages(id,chat_id,sender_id,text,media_type,media_data,views,forwarded_from,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (uid("msg"), target_chat_id, sender_id, message["text"], message["media_type"], message["media_data"], 1, forwarded_from, now()),
            )
        con.execute("UPDATE chats SET updated_at = ? WHERE id = ?", (now(), target_chat_id))

    def react(self, con, user, body):
        emoji = str(body.get("emoji", "👍"))[:32]
        if not emoji:
            raise ValueError("Выберите реакцию.")
        row = con.execute("SELECT chat_id, reactions_json FROM messages WHERE id=?", (body.get("messageId"),)).fetchone()
        if not row:
            raise ValueError("Пост не найден.")
        if not self.has_chat_access(con, user["id"], row["chat_id"]):
            raise PermissionError()
        message_id = body.get("messageId")
        existing = con.execute(
            "SELECT 1 FROM message_reactions WHERE message_id = ? AND user_id = ? AND emoji = ?",
            (message_id, user["id"], emoji),
        ).fetchone()
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

    def buy_premium(self, con, user, body):
        settings = loads(con.execute("SELECT value FROM settings WHERE key='premium'").fetchone()["value"], {})
        days = nonnegative_int(settings.get("days", 30), "days", 3650)
        if body.get("method") == "stars":
            price = nonnegative_int(settings.get("starsPrice", 250), "starsPrice")
            if price <= 0:
                raise ValueError("Покупка премиума за звёзды сейчас недоступна.")
            debited = con.execute("UPDATE users SET stars = stars - ? WHERE id = ? AND stars >= ?", (price, user["id"], price)).rowcount
            if not debited:
                raise ValueError("Недостаточно звёзд для премиума.")
            self.record_star_transaction(con, user["id"], -price, "premium", f"Премиум на {days} дн.")
        con.execute("UPDATE users SET premium_until = ? WHERE id = ?", (now() + days * 86400, user["id"]))
        return self.json({"ok": True})

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

    def add_report(self, con, user, body):
        target_type = str(body.get("targetType", "")).strip()[:40]
        target_id = str(body.get("targetId", "")).strip()[:2048]
        reason = str(body.get("reason", "")).strip()[:1000]
        if target_type not in {"profile", "profile-post", "review-page", "review", "story", "group-post", "channel"} or not target_id:
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
        message_id = uid("msg")
        con.execute("INSERT INTO messages(id,chat_id,sender_id,text,media_type,media_data,views,forwarded_from,source_type,source_id,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)", (message_id, target_chat_id, user["id"], text, media_type, media_data, 1, f"Источник: {source_label}", source_type, source_id, now()))
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
        allowed = {
            "stars_balance", "direct_chats", "channels_joined", "communities_joined", "groups_joined",
            "channels_created", "communities_created", "groups_created", "channel_subscribers",
            "community_subscribers", "group_subscribers", "messages", "posts", "stories", "reviews",
            "donations_sent", "stars_donated", "donations_received", "login_streak",
        }
        if not isinstance(criteria, dict):
            return {}
        normalized = {}
        for key, value in criteria.items():
            if key not in allowed:
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
        return {
            "stars_balance": int(user["stars"] or 0) if user else 0,
            "direct_chats": count("SELECT count(*) AS count FROM chat_members cm JOIN chats c ON c.id = cm.chat_id WHERE cm.user_id = ? AND c.type = 'direct'", (user_id,)),
            "channels_joined": count("SELECT count(*) AS count FROM chat_members cm JOIN chats c ON c.id = cm.chat_id WHERE cm.user_id = ? AND c.type = 'channel' AND c.owner_id != ?", (user_id, user_id)),
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
            "stories": count("SELECT count(*) AS count FROM stories WHERE user_id = ?", (user_id,)),
            "reviews": count("SELECT count(*) AS count FROM reviews WHERE created_by = ?", (user_id,)),
            "donations_sent": count("SELECT count(*) AS count FROM star_transactions WHERE user_id = ? AND kind = 'donation_sent'", (user_id,)),
            "stars_donated": count("SELECT COALESCE(SUM(ABS(amount)), 0) AS count FROM star_transactions WHERE user_id = ? AND kind = 'donation_sent'", (user_id,)),
            "donations_received": count("SELECT count(*) AS count FROM star_transactions WHERE user_id = ? AND kind = 'donation_received'", (user_id,)),
            "login_streak": int(user["login_streak"] or 0) if user else 0,
        }

    def activity_rewards_data(self, con, user_id):
        metrics = self.activity_metrics(con, user_id)
        rewards = []
        for row in con.execute("SELECT * FROM activity_rewards WHERE active = 1 ORDER BY created_at DESC").fetchall():
            reward = dict(row)
            criteria = self.normalize_activity_criteria(loads(reward.pop("criteria_json"), {}))
            reward["criteria"] = criteria
            reward["progress"] = {key: min(metrics.get(key, 0), target) for key, target in criteria.items()}
            reward["claimed"] = bool(con.execute("SELECT 1 FROM activity_reward_claims WHERE reward_id = ? AND user_id = ?", (reward["id"], user_id)).fetchone())
            reward["available"] = not reward["claimed"] and all(metrics.get(key, 0) >= target for key, target in criteria.items())
            rewards.append(reward)
        return rewards

    def claim_activity_reward(self, con, user, reward_id):
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
        con.execute("INSERT INTO activity_reward_claims(reward_id,user_id,claimed_at) VALUES (?,?,?)", (reward["id"], user["id"], now()))
        if reward["reward_stars"]:
            self.credit_stars(con, user["id"], reward["reward_stars"])
            self.record_star_transaction(con, user["id"], reward["reward_stars"], "activity_reward", f"Награда за активность «{reward['title']}»")
        if reward["premium_days"]:
            con.execute("UPDATE users SET premium_until = MAX(COALESCE(premium_until, 0), ?) + ? WHERE id = ?", (now(), reward["premium_days"] * 86400, user["id"]))
        return self.json({"ok": True})

    def account_level_data(self, con, user_id, configured_levels=None):
        if configured_levels is None:
            row = con.execute("SELECT value FROM settings WHERE key='account_levels'").fetchone()
            configured_levels = loads(row["value"], []) if row else []
        try:
            levels = normalize_account_levels(configured_levels)
        except ValueError:
            levels = []
        activity = {
            "messages": con.execute("SELECT count(*) AS count FROM messages WHERE sender_id = ?", (user_id,)).fetchone()["count"],
            "posts": con.execute("SELECT count(*) AS count FROM profile_posts WHERE user_id = ?", (user_id,)).fetchone()["count"],
            "stories": con.execute("SELECT count(*) AS count FROM stories WHERE user_id = ?", (user_id,)).fetchone()["count"],
            "reviews": con.execute("SELECT count(*) AS count FROM reviews WHERE created_by = ?", (user_id,)).fetchone()["count"],
            "groups": con.execute("SELECT count(*) AS count FROM chats WHERE owner_id = ? AND type = 'group'", (user_id,)).fetchone()["count"],
            "communities": con.execute("SELECT count(*) AS count FROM chats WHERE owner_id = ? AND type = 'community'", (user_id,)).fetchone()["count"],
            "channels": con.execute("SELECT count(*) AS count FROM chats WHERE owner_id = ? AND type = 'channel'", (user_id,)).fetchone()["count"],
        }
        purchased_ids = {
            row["level_id"] for row in con.execute("SELECT level_id FROM account_level_purchases WHERE user_id = ?", (user_id,)).fetchall()
        }
        current_index = -1
        level_states = []
        for index, level in enumerate(levels):
            criteria = level.get("criteria", {}) or {}
            earned = all(activity.get(key, 0) >= value for key, value in criteria.items())
            purchased = level["id"] in purchased_ids
            unlocked = index == 0 or (current_index == index - 1 and (earned or purchased))
            if unlocked:
                current_index = index
            claimed = bool(con.execute("SELECT 1 FROM account_level_rewards WHERE user_id = ? AND level_id = ?", (user_id, level["id"])).fetchone())
            level_states.append({**level, "earned": earned, "purchased": purchased, "unlocked": unlocked, "rewardClaimed": claimed, "rewardAvailable": unlocked and not claimed})
        current = level_states[current_index] if current_index >= 0 else {"id": "regular", "title": "Обычный", "description": "Стандартный аккаунт.", "limits": {}, "reward": {"stars": 0, "premiumDays": 0}}
        next_level = level_states[current_index + 1] if current_index + 1 < len(level_states) else None
        return {
            "current": current,
            "next": next_level,
            "levels": level_states,
            "activity": activity,
            "limits": self.effective_limits(con, user_id, current),
            "rewardClaimed": bool(current.get("rewardClaimed", False)),
        }

    def claim_account_level_reward(self, con, user, level_id):
        data = self.account_level_data(con, user["id"])
        level = next((item for item in data["levels"] if item["id"] == str(level_id or "")), None)
        if not level or not level["unlocked"]:
            raise ValueError("Награда доступна только за открытый уровень.")
        if level["rewardClaimed"]:
            raise ValueError("Награда за этот уровень уже получена.")
        reward = level.get("reward", {}) or {}
        stars, premium_days = max(0, int(reward.get("stars", 0) or 0)), max(0, int(reward.get("premiumDays", 0) or 0))
        con.execute("INSERT INTO account_level_rewards(user_id,level_id,claimed_at) VALUES (?,?,?)", (user["id"], level["id"], now()))
        if stars:
            self.credit_stars(con, user["id"], stars)
            self.record_star_transaction(con, user["id"], stars, "level_reward", f"Награда за уровень «{level['title']}»")
        if premium_days:
            con.execute("UPDATE users SET premium_until = MAX(COALESCE(premium_until, 0), ?) + ? WHERE id = ?", (now(), premium_days * 86400, user["id"]))
        return self.json({"ok": True})

    def buy_account_level(self, con, user, level_id):
        data = self.account_level_data(con, user["id"])
        next_level = data["next"]
        if not next_level or next_level["id"] != str(level_id or ""):
            raise ValueError("Купить можно только следующий уровень аккаунта.")
        price = int(next_level.get("starsPrice", 0) or 0)
        if price <= 0:
            raise ValueError("Этот уровень нельзя купить за звёзды.")
        debited = con.execute("UPDATE users SET stars = stars - ? WHERE id = ? AND stars >= ?", (price, user["id"], price)).rowcount
        if not debited:
            raise ValueError("Недостаточно звёзд для покупки уровня.")
        con.execute("INSERT INTO account_level_purchases(user_id,level_id,purchased_at) VALUES (?,?,?)", (user["id"], next_level["id"], now()))
        self.record_star_transaction(con, user["id"], -price, "account_level_purchase", f"Покупка уровня «{next_level['title']}»")
        reward = next_level.get("purchaseReward", {})
        stars = int(reward.get("stars", 0) or 0)
        premium_days = int(reward.get("premiumDays", 0) or 0)
        if stars:
            self.credit_stars(con, user["id"], stars)
            self.record_star_transaction(con, user["id"], stars, "account_level_purchase_reward", f"Награда за покупку уровня «{next_level['title']}»")
        if premium_days:
            con.execute("UPDATE users SET premium_until = MAX(COALESCE(premium_until, 0), ?) + ? WHERE id = ?", (now(), premium_days * 86400, user["id"]))
        return self.json({"ok": True})

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

    def poll_calls(self, con, user):
        rows = con.execute(
            """SELECT * FROM calls WHERE (caller_id = ? OR receiver_id = ?) AND status IN ('ringing','accepted')
               ORDER BY created_at DESC""",
            (user["id"], user["id"]),
        ).fetchall()
        calls = []
        for row in rows:
            caller = con.execute("SELECT name,username FROM users WHERE id=?", (row["caller_id"],)).fetchone()
            calls.append({
                "id": row["id"], "chatId": row["chat_id"], "callerId": row["caller_id"], "receiverId": row["receiver_id"],
                "callType": row["call_type"], "offerSdp": loads(row["offer_sdp"], {}), "answerSdp": loads(row["answer_sdp"], None),
                "status": row["status"], "callerName": caller["name"] if caller else "Пользователь", "createdAt": row["created_at"],
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
        users = [public_user(r) for r in con.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()]
        chats = [chat_to_dict(r) for r in con.execute("SELECT * FROM chats ORDER BY updated_at DESC").fetchall()]
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
            reward["claimsCount"] = con.execute("SELECT count(*) AS count FROM activity_reward_claims WHERE reward_id = ?", (reward["id"],)).fetchone()["count"]
            activity_rewards.append(reward)
        statuses = [dict(r) for r in con.execute("SELECT * FROM statuses ORDER BY created_at DESC").fetchall()]
        boosts = [dict(r) for r in con.execute("SELECT * FROM boost_jobs ORDER BY created_at DESC").fetchall()]
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
        return self.json({"ok": True, "settings": settings, "users": users, "chats": chats, "messages": messages, "promotions": promos, "recommended": recommended, "activityRewards": activity_rewards, "statuses": statuses, "boosts": boosts, "reports": reports, "automatedCommenters": automated_commenters, "automatedCommentRules": automated_comment_rules, "adminKeyHint": "По умолчанию: admin123"})

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


def run_automated_comment_worker() -> None:
    while True:
        try:
            with connect() as con:
                publish_automated_comments(con)
        except sqlite3.Error as error:
            print(f"Не удалось опубликовать автокомментарии: {error}")
        time.sleep(5)


def main():
    init_db()
    threading.Thread(target=run_automated_comment_worker, name="automated-comment-worker", daemon=True).start()
    server = ThreadingHTTPServer(("0.0.0.0", 8000), Handler)
    print("Chat-Pro запущен: http://localhost:8000")
    print("Админка: http://localhost:8000/admin, ключ по умолчанию: admin123")
    server.serve_forever()


if __name__ == "__main__":
    main()
