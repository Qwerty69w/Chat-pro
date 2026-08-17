const TOKEN_KEY = "minigram_token_v2";
const BASE_NIGHT_APPEARANCE = { outlineColor: "#65ddf8", glowColor: "#21d5f0", glowIntensity: 35 };
const SAVED_ACCOUNTS_KEY = "minigram_saved_accounts_v2";
const RECENT_EMOJI_LIMIT = 24;
let EMOJI_SET = `
🏧 🚮 🚰 ♿ 🚹 🚺 🚻 🚼 🚾 🛂 🛃 🛄 🛅 🗣️ 👤 👥 🫂 👣 🫆 ⚠️ 🚸 ⛔ 🚫 🚳 🚭 🚯 🚱 🚷 📵 🔞 ☢️ ☣️
⬆️ ↗️ ➡️ ↘️ ⬇️ ↙️ ⬅️ ↖️ ↕️ ↔️ ↩️ ↪️ ⤴️ ⤵️ 🔃 🔄 🔙 🔚 🔛 🔜 🔝 🛐 ⚛️ 🕉️ ✡️ ☸️ ☯️ ✝️ ☦️ ☪️ ☮️ 🕎 🔯 🪯
♈ ♉ ♊ ♋ ♌ ♍ ♎ ♏ ♐ ♑ ♒ ♓ ⛎ 🔀 🔁 🔂 ▶️ ⏩ ⏭️ ⏯️ ◀️ ⏪ ⏮️ 🔼 ⏫ 🔽 ⏬ ⏸️ ⏹️ ⏺️ ⏏️ 🎦 🔅 🔆 📶 🛜 📳 📴
♀️ ♂️ ⚧️ ✖️ ➕ ➖ ➗ 🟰 ♾️ ‼️ ⁉️ ❓ ❔ ❕ ❗ 〰️ 💱 💲 ⚕️ ♻️ ⚜️ 🔱 📛 🔰 ⭕ ✅ ☑️ ✔️ ❌ ❎ ➰ ➿ 〽️ ✳️ ✴️ ❇️ ©️ ®️ ™️ 🫟 #️⃣ *️⃣
0️⃣ 1️⃣ 2️⃣ 3️⃣ 4️⃣ 5️⃣ 6️⃣ 7️⃣ 8️⃣ 9️⃣ 🔟 🔠 🔡 🔢 🔣 🔤 🅰️ 🆎 🅱️ 🆑 🆒 🆓 ℹ️ 🆔 Ⓜ️ 🆕 🆖 🅾️ 🆗 🅿️ 🆘 🆙 🆚 🈁 🈂️ 🈷️ 🈶 🈯 🉐 🈹 🈚 🈲 🉑 🈸 🈴 🈳 ㊗️ ㊙️ 🈺 🈵
🔴 🟠 🟡 🟢 🔵 🟣 🟤 ⚫ ⚪ 🟥 🟧 🟨 🟩 🟦 🟪 🟫 ⬛ ⬜ ◼️ ◻️ ◾ ◽ ▪️ ▫️ 🔶 🔷 🔸 🔹 🔺 🔻 💠 🔘 🔳 🔲 💬 👁️‍🗨️ 🗨️ 🗯️ 💭
👨‍👩‍👦 👨‍👩‍👧 👨‍👩‍👧‍👦 👨‍👩‍👦‍👦 👨‍👩‍👧‍👧 👨‍👦 👨‍👦‍👦 👨‍👧 👨‍👧‍👦 👨‍👧‍👧 👩‍👦 👩‍👦‍👦 👩‍👧 👩‍👧‍👦 👩‍👧‍👧 👪 🧑‍🧑‍🧒 🧑‍🧑‍🧒‍🧒 🧑‍🧒 🧑‍🧒‍🧒
🏁 🚩 🎌 🏴 🏳️
🇦🇨 🇦🇩 🇦🇪 🇦🇫 🇦🇬 🇦🇮 🇦🇱 🇦🇲 🇦🇴 🇦🇶 🇦🇷 🇦🇸 🇦🇹 🇦🇺 🇦🇼 🇦🇽 🇦🇿 🇧🇦 🇧🇧 🇧🇩 🇧🇪 🇧🇫 🇧🇬 🇧🇭 🇧🇮 🇧🇯 🇧🇱 🇧🇲 🇧🇳 🇧🇴 🇧🇶 🇧🇷 🇧🇸 🇧🇹 🇧🇻 🇧🇼 🇧🇾 🇧🇿
🇨🇦 🇨🇨 🇨🇩 🇨🇫 🇨🇬 🇨🇭 🇨🇮 🇨🇰 🇨🇱 🇨🇲 🇨🇳 🇨🇴 🇨🇵 🇨🇶 🇨🇷 🇨🇺 🇨🇻 🇨🇼 🇨🇽 🇨🇾 🇨🇿 🇩🇪 🇩🇬 🇩🇯 🇩🇰 🇩🇲 🇩🇴 🇩🇿
🇪🇦 🇪🇨 🇪🇪 🇪🇬 🇪🇭 🇪🇷 🇪🇸 🇪🇹 🇪🇺 🇫🇮 🇫🇯 🇫🇰 🇫🇲 🇫🇴 🇫🇷 🇬🇦 🇬🇧 🇬🇩 🇬🇪 🇬🇫 🇬🇬 🇬🇭 🇬🇮 🇬🇱 🇬🇲 🇬🇳 🇬🇵 🇬🇶 🇬🇷 🇬🇸 🇬🇹 🇬🇺 🇬🇼 🇬🇾
🇭🇰 🇭🇲 🇭🇳 🇭🇷 🇭🇹 🇭🇺 🇮🇨 🇮🇩 🇮🇪 🇮🇱 🇮🇲 🇮🇳 🇮🇴 🇮🇶 🇮🇷 🇮🇸 🇮🇹 🇯🇪 🇯🇲 🇯🇴 🇯🇵 🇰🇪 🇰🇬 🇰🇭 🇰🇮 🇰🇲 🇰🇳 🇰🇵 🇰🇷 🇰🇼 🇰🇾 🇰🇿
🇱🇦 🇱🇧 🇱🇨 🇱🇮 🇱🇰 🇱🇷 🇱🇸 🇱🇹 🇱🇺 🇱🇻 🇱🇾 🇲🇦 🇲🇨 🇲🇩 🇲🇪 🇲🇫 🇲🇬 🇲🇭 🇲🇰 🇲🇱 🇲🇲 🇲🇳 🇲🇴 🇲🇵 🇲🇶 🇲🇷 🇲🇸 🇲🇹 🇲🇺 🇲🇻 🇲🇼 🇲🇽 🇲🇾 🇲🇿
🇳🇦 🇳🇨 🇳🇪 🇳🇫 🇳🇬 🇳🇮 🇳🇱 🇳🇴 🇳🇵 🇳🇷 🇳🇺 🇳🇿 🇴🇲 🇵🇦 🇵🇪 🇵🇫 🇵🇬 🇵🇭 🇵🇰 🇵🇱 🇵🇲 🇵🇳 🇵🇷 🇵🇸 🇵🇹 🇵🇼 🇵🇾 🇶🇦 🇷🇪 🇷🇴 🇷🇸 🇷🇺 🇷🇼
🇸🇦 🇸🇧 🇸🇨 🇸🇩 🇸🇪 🇸🇬 🇸🇭 🇸🇮 🇸🇯 🇸🇰 🇸🇱 🇸🇲 🇸🇳 🇸🇴 🇸🇷 🇸🇸 🇸🇹 🇸🇻 🇸🇽 🇸🇾 🇸🇿 🇹🇦 🇹🇨 🇹🇩 🇹🇫 🇹🇬 🇹🇭 🇹🇯 🇹🇰 🇹🇱 🇹🇲 🇹🇳 🇹🇴 🇹🇷 🇹🇹 🇹🇻 🇹🇼 🇹🇿
🇺🇦 🇺🇬 🇺🇲 🇺🇳 🇺🇸 🇺🇾 🇺🇿 🇻🇦 🇻🇨 🇻🇪 🇻🇬 🇻🇮 🇻🇳 🇻🇺 🇼🇫 🇼🇸 🇽🇰 🇾🇪 🇾🇹 🇿🇦 🇿🇲 🇿🇼 🏴󠁧󠁢󠁥󠁮󠁧󠁿 🏴󠁧󠁢󠁳󠁣󠁴󠁿 🏴󠁧󠁢󠁷󠁬󠁳󠁿
☺︎ ☹︎ ☠︎ ❣︎ ❤︎ ☘︎ ⛸︎ ♠︎ ♥︎ ♦︎ ♣︎ ♟︎ ⛷︎ ⛰︎ ⛩︎ ♨︎ ⛴︎ ✈︎ ☀︎ ⏱︎ ⏲︎ ☁︎ ⛈︎ ☂︎ ⛱︎ ❄︎ ☃︎ ☄︎ ⛑︎ ☎︎ ⌨︎ ✏︎ ✒︎ ✉︎ ✂︎ ⛏︎ ⚒︎ ⚔︎ ⚙︎ ⚖︎ ⛓︎ ⚗︎ ⚰︎ ⚱︎
😀 😃 😄 😁 😆 😅 🤣 😂 🙂 🙃 🫠 😉 😊 😇 🥰 😍 🤩 😘 😗 ☺️ 😚 😙 🥲 😋 😛 😜 🤪 😝 🤑 🤗 🤭 🫢 🫣 🤫 🤔 🫡 🤐 🤨 😐 😑 😶 🫥 😶‍🌫️ 😏 😒 🙄 😬 😮‍💨 🤥 🫨 🙂‍↔️ 🙂‍↕️ 😌 😔 😪 🤤 😴 🫩 😷 🤒 🤕 🤢 🤮 🤧 🥵 🥶 🥴 😵 😵‍💫 🤯 🤠 🥳 🥸 😎 🤓 🧐 😕 🫤 😟 🙁 ☹️ 😮 😯 😲 😳 🥺 🥹 😦 😧 😨 😰 😥 😢 😭 😱 😖 😣 😞 😓 😩 😫 🥱 😤 😡 😠 🤬 😈 👿 💀 ☠️ 💩 🤡 👹 👺 👻 👽 👾 🤖 😺 😸 😹 😻 😼 😽 🙀 😿 😾 🙈 🙉 🙊 💋 💯 💢 💥 💫 💦 💨 🕳️ 💤
👋 🤚 🖐️ ✋ 🖖 🫱 🫲 🫳 🫴 🫷 🫸 👌 🤌 🤏 ✌️ 🤞 🫰 🤟 🤘 🤙 👈 👉 👆 🖕 👇 ☝️ 🫵 👍 👎 ✊ 👊 🤛 🤜 👏 🙌 🫶 👐 🤲 🤝 🙏 ✍️ 💅 🤳 💪 🦾 🦿 🦵 🦶 👂 🦻 👃 🧠 🫀 🫁 🦷 🦴 👀 👁️ 👅 👄 🫦
👶 🧒 👦 👧 🧑 👱 👨 🧔 👨‍🦰 👨‍🦱 👨‍🦳 👨‍🦲 👩 👩‍🦰 🧑‍🦰 👩‍🦱 🧑‍🦱 👩‍🦳 🧑‍🦳 👩‍🦲 🧑‍🦲 👱‍♀️ 👱‍♂️ 🧓 👴 👵 🙍 🙍‍♂️ 🙍‍♀️ 🙎 🙎‍♂️ 🙎‍♀️ 🙅 🙅‍♂️ 🙅‍♀️ 🙆 🙆‍♂️ 🙆‍♀️ 💁 💁‍♂️ 💁‍♀️ 🙋 🙋‍♂️ 🙋‍♀️ 🧏 🧏‍♂️ 🧏‍♀️ 🙇 🙇‍♂️ 🙇‍♀️ 🤦 🤦‍♂️ 🤦‍♀️ 🤷 🤷‍♂️ 🤷‍♀️ 🫅 🤴 👸 👳 👲 🧕 🤵 👰 🤰 🤱 👩‍🍼 👨‍🍼 🧑‍🍼 💃 🕺 🛀 🛌 👫 💏 👩‍❤️‍💋‍👨 💑 👩‍❤️‍👨 💌 💘 💝 💖 💗 💓 💞 💕 💟 ❣️ 💔 ❤️‍🔥 ❤️‍🩹 ❤️ 🩷 🧡 💛 💚 💙 🩵 💜 🤎 🖤 🩶 🤍
🐵 🐒 🦍 🦧 🐶 🐕 🦮 🐕‍🦺 🐩 🐺 🦊 🦝 🐱 🐈 🐈‍⬛ 🦁 🐯 🐅 🐆 🐴 🫎 🫏 🐎 🦄 🦓 🦌 🦬 🐮 🐂 🐃 🐄 🐷 🐖 🐗 🐽 🐏 🐑 🐐 🐪 🐫 🦙 🦒 🐘 🦣 🦏 🦛 🐭 🐁 🐀 🐹 🐰 🐇 🐿️ 🦫 🦔 🦇 🐻 🐻‍❄️ 🐨 🐼 🦥 🦦 🦨 🦘 🦡 🐾 🦃 🐔 🐓 🐣 🐤 🐥 🐦 🐧 🕊️ 🦅 🦆 🦢 🦉 🦤 🪶 🦩 🦚 🦜 🪽 🐦‍⬛ 🪿 🐦‍🔥 🐸 🐊 🐢 🦎 🐍 🐲 🐉 🦕 🦖 🐳 🐋 🐬 🦭 🐟 🐠 🐡 🦈 🐙 🐚 🪸 🪼 🦀 🦞 🦐 🦑 🦪 🐌 🦋 🐛 🐜 🐝 🪲 🐞 🦗 🪳 🕷️ 🕸️ 🦂 🦟 🪰 🪱 🦠 💐 🌸 💮 🪷 🏵️ 🌹 🥀 🌺 🌻 🌼 🌷 🪻 🌱 🪴 🌲 🌳 🌴 🌵 🌾 🌿 ☘️ 🍀 🍁 🍂 🍃 🪹 🪺 🍄 🪾
🍇 🍈 🍉 🍊 🍋 🍋‍🟩 🍌 🍍 🥭 🍎 🍏 🍐 🍑 🍒 🍓 🫐 🥝 🍅 🫒 🥥 🥑 🍆 🥔 🥕 🌽 🌶️ 🫑 🥒 🥬 🥦 🧄 🧅 🥜 🫘 🌰 🫚 🫛 🍄‍🟫 🫜 🍞 🥐 🥖 🫓 🥨 🥯 🥞 🧇 🧀 🍖 🍗 🥩 🥓 🍔 🍟 🍕 🌭 🥪 🌮 🌯 🫔 🥙 🧆 🥚 🍳 🥘 🍲 🫕 🥣 🥗 🍿 🧈 🧂 🥫 🍱 🍘 🍙 🍚 🍛 🍜 🍝 🍠 🍢 🍣 🍤 🍥 🥮 🍡 🥟 🥠 🥡 🍦 🍧 🍨 🍩 🍪 🎂 🍰 🧁 🥧 🍫 🍬 🍭 🍮 🍯 🍼 🥛 ☕ 🫖 🍵 🍶 🍾 🍷 🍸 🍹 🍺 🍻 🥂 🥃 🫗 🥤 🧋 🧃 🧉 🧊 🥢 🍽️ 🍴 🥄 🔪 🫙 🏺
🎃 🎄 🎆 🎇 🧨 ✨ 🎈 🎉 🎊 🎋 🎍 🎎 🎏 🎐 🎑 🧧 🎀 🎁 🎗️ 🎟️ 🎫 🎖️ 🏆 🏅 🥇 🥈 🥉 ⚽ ⚾ 🥎 🏀 🏐 🏈 🏉 🎾 🥏 🎳 🏏 🏑 🏒 🥍 🏓 🏸 🥊 🥋 🥅 ⛳ ⛸️ 🎣 🤿 🎽 🎿 🛷 🥌 🎯 🪀 🪁 🔫 🎱 🔮 🪄 🎮 🕹️ 🎰 🎲 🧩 🧸 🪅 🪩 🪆 ♠️ ♥️ ♦️ ♣️ ♟️ 🃏 🀄 🎴 🎭 🖼️ 🎨 🧵 🪡 🧶 🪢
🧑‍⚕️ 👨‍⚕️ 👩‍⚕️ 🧑‍🎓 👨‍🎓 👩‍🎓 🧑‍🏫 👨‍🏫 👩‍🏫 🧑‍⚖️ 👨‍⚖️ 👩‍⚖️ 🧑‍🌾 👨‍🌾 👩‍🌾 🧑‍🍳 👨‍🍳 👩‍🍳 🧑‍🔧 👨‍🔧 👩‍🔧 🧑‍🏭 👨‍🏭 👩‍🏭 🧑‍💼 👨‍💼 👩‍💼 🧑‍🔬 👨‍🔬 👩‍🔬 🧑‍💻 👨‍💻 👩‍💻 🧑‍🎤 👨‍🎤 👩‍🎤 🧑‍🎨 👨‍🎨 👩‍🎨 🧑‍✈️ 👨‍✈️ 👩‍✈️ 🧑‍🚀 👨‍🚀 👩‍🚀 🧑‍🚒 👨‍🚒 👩‍🚒 👮 👮‍♂️ 👮‍♀️ 🕵️ 🕵️‍♂️ 🕵️‍♀️ 💂 💂‍♂️ 💂‍♀️ 🥷 👷 👷‍♂️ 👷‍♀️ 👼 🎅 🤶 🧑‍🎄 🦸 🦸‍♂️ 🦸‍♀️ 🦹 🦹‍♂️ 🦹‍♀️ 🧙 🧙‍♂️ 🧙‍♀️ 🧚 🧚‍♂️ 🧚‍♀️ 🧛 🧛‍♂️ 🧛‍♀️ 🧜 🧜‍♂️ 🧜‍♀️ 🧝 🧝‍♂️ 🧝‍♀️ 🧞 🧞‍♂️ 🧞‍♀️ 🧟 🧟‍♂️ 🧟‍♀️ 🧌
🚶 🚶‍♂️ 🚶‍♀️ 🚶‍➡️ 🚶‍♀️‍➡️ 🚶‍♂️‍➡️ 🧍 🧍‍♂️ 🧍‍♀️ 🧎 🧎‍♂️ 🧎‍♀️ 🧎‍➡️ 🧎‍♀️‍➡️ 🧎‍♂️‍➡️ 🧑‍🦯 🧑‍🦯‍➡️ 👨‍🦯 👨‍🦯‍➡️ 👩‍🦯 👩‍🦯‍➡️ 🧑‍🦼 🧑‍🦼‍➡️ 👨‍🦼 👨‍🦼‍➡️ 👩‍🦼 👩‍🦼‍➡️ 🧑‍🦽 🧑‍🦽‍➡️ 👨‍🦽 👨‍🦽‍➡️ 👩‍🦽 👩‍🦽‍➡️ 🏃 🏃‍♂️ 🏃‍♀️ 🏃‍➡️ 🏃‍♀️‍➡️ 🏃‍♂️‍➡️ 💇 💇‍♂️ 💇‍♀️ 🕴️ 👯 👯‍♂️ 👯‍♀️ 🧖 🧖‍♂️ 🧖‍♀️ 🧗 🧗‍♂️ 🧗‍♀️ 🤺 🏇 ⛷️ 🏂 🏌️ 🏌️‍♂️ 🏌️‍♀️ 🏄 🏄‍♂️ 🏄‍♀️ 🚣 🚣‍♂️ 🚣‍♀️ 🏊 🏊‍♂️ 🏊‍♀️ ⛹️ ⛹️‍♂️ ⛹️‍♀️ 🏋️ 🏋️‍♂️ 🏋️‍♀️ 🚴 🚴‍♂️ 🚴‍♀️ 🚵 🚵‍♂️ 🚵‍♀️ 🤸 🤸‍♂️ 🤸‍♀️ 🤼 🤼‍♂️ 🤼‍♀️ 🤽 🤽‍♂️ 🤽‍♀️ 🤾 🤾‍♂️ 🤾‍♀️ 🤹 🤹‍♂️ 🤹‍♀️ 🧘 🧘‍♂️ 🧘‍♀️
🌍 🌎 🌏 🌐 🗺️ 🗾 🧭 🏔️ ⛰️ 🌋 🗻 🏕️ 🏖️ 🏜️ 🏝️ 🏞️ 🏟️ 🏛️ 🏗️ 🧱 🪨 🪵 🛖 🏘️ 🏚️ 🏠 🏡 🏢 🏣 🏤 🏥 🏦 🏨 🏩 🏪 🏫 🏬 🏭 🏯 🏰 💒 🗼 🗽 ⛪ 🕌 🛕 🕍 ⛩️ 🕋 ⛲ ⛺ 🌁 🌃 🏙️ 🌄 🌅 🌆 🌇 🌉 ♨️ 🎠 🛝 🎡 🎢 💈 🎪
🚂 🚃 🚄 🚅 🚆 🚇 🚈 🚉 🚊 🚝 🚞 🚋 🚌 🚍 🚎 🚐 🚑 🚒 🚓 🚔 🚕 🚖 🚗 🚘 🚙 🛻 🚚 🚛 🚜 🏎️ 🏍️ 🛵 🦽 🦼 🛺 🚲 🛴 🛹 🛼 🚏 🛣️ 🛤️ 🛢️ ⛽ 🛞 🚨 🚥 🚦 🛑 🚧 ⚓ 🛟 ⛵ 🛶 🚤 🛳️ ⛴️ 🛥️ 🚢 ✈️ 🛩️ 🛫 🛬 🪂 💺 🚁 🚟 🚠 🚡 🛰️ 🚀 🛸 🛎️ 🧳 ⌛ ⏳ ⌚ ⏰ ⏱️ ⏲️ 🕰️ 🕛 🕧 🕐 🕜 🕑 🕝 🕒 🕞 🕓 🕟 🕔 🕠 🕕 🕡 🕖 🕢 🕗 🕣 🕘 🕤 🕙 🕥 🕚 🕦
🌑 🌒 🌓 🌔 🌕 🌖 🌗 🌘 🌙 🌚 🌛 🌜 🌡️ ☀️ 🌝 🌞 🪐 ⭐ 🌟 🌠 🌌 ☁️ ⛅ ⛈️ 🌤️ 🌥️ 🌦️ 🌧️ 🌨️ 🌩️ 🌪️ 🌫️ 🌬️ 🌀 🌈 🌂 ☂️ ☔ ⛱️ ⚡ ❄️ ☃️ ⛄ ☄️ 🔥 💧 🌊
👓 🕶️ 🥽 🥼 🦺 👔 👕 👖 🧣 🧤 🧥 🧦 👗 👘 🥻 🩱 🩲 🩳 👙 👚 🪭 👛 👜 👝 🛍️ 🎒 🩴 👞 👟 🥾 🥿 👠 👡 🩰 👢 🪮 👑 👒 🎩 🎓 🧢 🪖 ⛑️ 📿 💄 💍 💎
🔇 🔈 🔉 🔊 📢 📣 📯 🔔 🔕 🎼 🎵 🎶 🎙️ 🎚️ 🎛️ 🎤 🎧 📻 🎷 🪗 🎸 🎹 🎺 🎻 🪕 🥁 🪘 🪇 🪈 🪉 📱 📲 ☎️ 📞 📟 📠 🔋 🪫 🔌 💻 🖥️ 🖨️ ⌨️ 🖱️ 🖲️ 💽 💾 💿 📀 🧮 🎥 🎞️ 📽️ 🎬 📺 📷 📸 📹 📼 🔍 🔎 🕯️ 💡 🔦 🏮 🪔
📔 📕 📖 📗 📘 📙 📚 📓 📒 📃 📜 📄 📰 🗞️ 📑 🔖 🏷️ 💰 🪙 💴 💵 💶 💷 💸 💳 🧾 💹 ✉️ 📧 📨 📩 📤 📥 📦 📫 📪 📬 📭 📮 🗳️ ✏️ ✒️ 🖋️ 🖊️ 🖌️ 🖍️ 📝 💼 📁 📂 🗂️ 📅 📆 🗒️ 🗓️ 📇 📈 📉 📊 📋 📌 📍 📎 🖇️ 📏 📐 ✂️ 🗃️ 🗄️ 🗑️
🔒 🔓 🔏 🔐 🔑 🗝️ 🔨 🪓 ⛏️ ⚒️ 🛠️ 🗡️ ⚔️ 💣 🪃 🏹 🛡️ 🪚 🔧 🪛 🔩 ⚙️ 🗜️ ⚖️ 🦯 🔗 ⛓️‍💥 ⛓️ 🪝 🧰 🧲 🪜 🪏 ⚗️ 🧪 🧫 🧬 🔬 🔭 📡 💉 🩸 💊 🩹 🩼 🩺 🩻 🚪 🛗 🪞 🪟 🛏️ 🛋️ 🪑 🚽 🪠 🚿 🛁 🪤 🪒 🧴 🧷 🧹 🧺 🧻 🪣 🧼 🫧 🪥 🧽 🧯 🛒 🚬 ⚰️ 🪦 ⚱️ 🧿 🪬 🗿 🪧 🪪
`.trim().split(/\s+/);
const FIRST_FACE_EMOJI = EMOJI_SET.indexOf("😀");
if (FIRST_FACE_EMOJI > 0) EMOJI_SET = [...EMOJI_SET.slice(FIRST_FACE_EMOJI), ...EMOJI_SET.slice(0, FIRST_FACE_EMOJI)];

const app = document.querySelector("#app");
let token = localStorage.getItem(TOKEN_KEY) || "";
let state = null;
let activeSection = "chats";
let settingsSection = "general";
let menuOpen = false;
let chatFilter = "all";
let storiesCollapsed = false;
let activeChatId = null;
let openedProfileId = null;
let profileReturnSection = "chats";
let activeCall = null;
let callPollTimer = null;
let messagePollTimer = null;
let ringTone = null;
let callVoiceActivity = [];
let scrollChatToLatest = false;
let selectedMessageIds = new Set();
let expandedRssPostIds = new Set();
let pinnedMessageIndex = 0;
let reviewPageUrl = "";
const pendingOutgoingMessages = new Map();

function pinIcon(className = "") {
  return `<svg${className ? ` class="${className}"` : ""} viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 4h12M8 4v5l-3 4h14l-3-4V4M12 13v7"/></svg>`;
}

function actionIcon(name, className = "") {
  const paths = {
    more: '<circle cx="12" cy="5" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="12" cy="19" r="1"/>',
    reaction: '<circle cx="12" cy="12" r="8.25"/><path d="M8.2 14c1 1.35 2.25 2 3.8 2s2.8-.65 3.8-2M9 10h.01M15 10h.01"/>',
    select: '<rect x="4" y="4" width="16" height="16" rx="3"/><path d="m8 12 2.5 2.5L16.5 8.5"/>',
    profile: '<circle cx="12" cy="8" r="3"/><path d="M5.5 20v-1a5.5 5.5 0 0 1 11 0v1"/>',
    forward: '<path d="M14 5.5 20.5 12 14 18.5M20 12H9a5 5 0 0 0-5 5v1"/>',
    confidential: '<rect x="5" y="10" width="14" height="10" rx="2.5"/><path d="M8.5 10V7.5a3.5 3.5 0 0 1 7 0V10"/>',
    donate: '<path d="m12 3 2.15 5.1 5.5.45-4.18 3.62 1.27 5.33L12 14.3 7.26 17.5l1.27-5.33L4.35 8.55l5.5-.45L12 3Z"/>',
    download: '<path d="M12 3v11M8 10l4 4 4-4M5 20h14"/>',
    report: '<path d="M6 21V4m0 1h11l-1.7 3.5L17 12H6"/>',
    delete: '<path d="M4 7h16M10 11v6M14 11v6M9 7l1-3h4l1 3M6.5 7l.7 13h9.6l.7-13"/>',
    cancel: '<path d="M7 7h9a5 5 0 1 1-4.5 7.2"/><path d="M7 7v5M7 7h5"/>',
  };
  return `<svg${className ? ` class="${className}"` : ""} viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name] || ""}</svg>`;
}

function callControlIcon(name) {
  const paths = {
    accept: '<path d="M7.2 3.8 4.6 6.4c-.8.8-.9 2-.3 2.9 2.9 4.7 6.8 8.6 11.5 11.5.9.6 2.1.5 2.9-.3l2.6-2.6c.7-.7.7-1.9 0-2.6l-2.1-2.1c-.7-.7-1.8-.7-2.5-.1l-1.4 1.1a13.6 13.6 0 0 1-5.5-5.5l1.1-1.4c.6-.7.6-1.8-.1-2.5L9.8 3.8c-.7-.7-1.9-.7-2.6 0Z"/>',
    decline: '<path d="M7 15.6c3.2-2.1 6.8-2.1 10 0l1.7 1.1c.7.5.8 1.5.2 2.1l-1.2 1.2c-.4.4-1 .5-1.5.3a10.2 10.2 0 0 0-8.4 0c-.5.2-1.1.1-1.5-.3l-1.2-1.2c-.6-.6-.5-1.6.2-2.1L7 15.6Z"/><path d="M5.5 8.5c4.1-2.7 8.9-2.7 13 0"/>',
    microphone: '<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M6.5 11a5.5 5.5 0 0 0 11 0M12 16.5V21M9 21h6"/>',
    microphoneOff: '<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M6.5 11a5.5 5.5 0 0 0 11 0M12 16.5V21M9 21h6M4 4l16 16"/>',
    pause: '<path d="M8 5v14M16 5v14"/>',
    play: '<path d="m9 5 10 7-10 7V5Z"/>',
    camera: '<rect x="3.5" y="6.5" width="11.5" height="11" rx="2.5"/><path d="m15 10 5-3v10l-5-3"/>',
    cameraOff: '<rect x="3.5" y="6.5" width="11.5" height="11" rx="2.5"/><path d="m15 10 5-3v10l-5-3M4 4l16 16"/>',
    end: '<path d="M7 15.6c3.2-2.1 6.8-2.1 10 0l1.7 1.1c.7.5.8 1.5.2 2.1l-1.2 1.2c-.4.4-1 .5-1.5.3a10.2 10.2 0 0 0-8.4 0c-.5.2-1.1.1-1.5-.3l-1.2-1.2c-.6-.6-.5-1.6.2-2.1L7 15.6Z"/><path d="M5.5 8.5c4.1-2.7 8.9-2.7 13 0"/>',
    expand: '<rect x="5" y="5" width="14" height="14" rx="3"/><path d="M9 9h6v6"/>',
    shrink: '<rect x="5" y="5" width="14" height="14" rx="3"/><path d="M15 9H9v6"/>',
    minimize: '<path d="M5 12h14"/>',
  };
  return `<svg class="call-control__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name] || ""}</svg>`;
}

const CHAT_WALLPAPERS = [
  { id: "default", title: "Чистый", description: "Нейтральный фон" },
  { id: "whatsapp", title: "WhatsApp", description: "Светлый зелёный узор" },
  { id: "mint", title: "Мятный свет", description: "По вашему зелёному референсу" },
  { id: "aurora", title: "Неоновая аура", description: "Розовый, синий и индиго" },
  { id: "noir", title: "Ночной бархат", description: "Глубокий сине-чёрный" },
  { id: "cyan", title: "Бирюзовая волна", description: "Яркий циан и синий" },
  { id: "mist", title: "Северный туман", description: "Холодный с мягким цветом" },
  { id: "sunset", title: "Тёплый закат", description: "Персиковый и лиловый" },
  { id: "ocean", title: "Океан", description: "Светлая глубина" },
  { id: "lavender", title: "Лаванда", description: "Нежный фиолетовый" },
  { id: "forest", title: "Лес", description: "Спокойный зелёный" },
  { id: "midnight", title: "Полночь", description: "Сдержанный синий" },
  { id: "ember", title: "Янтарный огонь", description: "Авторский тёплый вариант" },
  { id: "iris", title: "Ирис", description: "Авторский фиолетовый вариант" },
  { id: "prism", title: "Живая призма", description: "8 редких градиентных переливов" },
  { id: "live", title: "Живые диалоги", description: "Плавно меняющийся цветной фон" },
];

const DIALOG_PANEL_STYLES = [
  { id: "custom", title: "Свой цвет", description: "Выберите цвет вручную" },
  { id: "pearl", title: "Жемчужный", description: "Светлый голубой" },
  { id: "sky", title: "Небесный", description: "Светлый синий" },
  { id: "mint", title: "Мятный", description: "Свежий зелёный" },
  { id: "sunset", title: "Закат", description: "Персиковый и лиловый" },
  { id: "lavender", title: "Лаванда", description: "Нежный фиолетовый" },
  { id: "midnight", title: "Полночь", description: "Глубокий синий" },
  { id: "noir", title: "Ночной бархат", description: "Сине-чёрный" },
  { id: "aurora", title: "Аура", description: "Индиго и циан" },
  { id: "live", title: "Живой градиент", description: "Медленно переливается" },
  { id: "interactive", title: "Интерактивный космос", description: "Перелив по нажатию" },
  { id: "interactive-light", title: "Интерактивный свет", description: "Светлый перелив по нажатию" },
  { id: "ember", title: "Янтарный огонь", description: "Тёплый тёмный" },
];

const DIALOG_FONTS = [
  { id: "business", title: "Деловой" },
  { id: "system", title: "Системный" },
  { id: "classic", title: "Классический" },
  { id: "script", title: "Прописной" },
  { id: "rounded", title: "Мягкий" },
  { id: "serif", title: "С засечками" },
  { id: "mono", title: "Моноширинный" },
  { id: "humanist", title: "Гуманистический" },
  { id: "condensed", title: "Компактный" },
  { id: "typewriter", title: "Печатная машинка" },
  { id: "elegant", title: "Элегантный" },
];

function dialogMessageFont(font) {
  return {
    business: 'Avenir Next, Avenir, "Helvetica Neue", Arial, sans-serif',
    classic: 'Palatino, "Palatino Linotype", Book Antiqua, Georgia, serif',
    script: 'Snell Roundhand, "Segoe Script", "Bradley Hand", cursive',
    rounded: 'ui-rounded, "Arial Rounded MT Bold", Arial, sans-serif',
    serif: 'Georgia, "Times New Roman", serif',
    mono: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
    humanist: 'Optima, Candara, "Segoe UI", sans-serif',
    condensed: 'Arial Narrow, "Roboto Condensed", "Helvetica Neue", sans-serif',
    typewriter: 'Courier New, Courier, ui-monospace, monospace',
    elegant: 'Baskerville, "Times New Roman", Georgia, serif',
  }[font] || 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif';
}

function dialogBubbleTextColor(color = "#ffffff") {
  const hex = String(color).replace("#", "");
  if (!/^[\da-f]{6}$/i.test(hex)) return "#17212b";
  const [red, green, blue] = [0, 2, 4].map((index) => Number.parseInt(hex.slice(index, index + 2), 16));
  return (red * 299 + green * 587 + blue * 114) / 1000 < 150 ? "#ffffff" : "#17212b";
}

function recentEmojiKey() {
  return `minigram_recent_emoji_${state?.me?.id || "guest"}`;
}

function recentEmojis() {
  try {
    const emojis = JSON.parse(localStorage.getItem(recentEmojiKey()) || "[]");
    return Array.isArray(emojis) ? emojis.filter((emoji) => typeof emoji === "string").slice(0, RECENT_EMOJI_LIMIT) : [];
  } catch {
    return [];
  }
}

function rememberRecentEmoji(emoji) {
  const emojis = [emoji, ...recentEmojis().filter((item) => item !== emoji)].slice(0, RECENT_EMOJI_LIMIT);
  localStorage.setItem(recentEmojiKey(), JSON.stringify(emojis));
}

start();

async function start() {
  if (!token) {
    renderAuth();
    hidePageLoader();
    return;
  }
  try {
    activeSection = "chats";
    settingsSection = "general";
    activeChatId = null;
    menuOpen = false;
    await loadState();
    trimSavedAccountsToLimit();
    const inviteCode = window.location.pathname.match(/^\/invite\/([^/]+)$/)?.[1];
    if (inviteCode) {
      window.history.replaceState({}, "", "/");
      try {
        const result = await api("/api/invites/join", { method: "POST", body: { code: inviteCode } });
        activeChatId = result.chatId || null;
        await loadState();
        toast("Вы вступили в группу по ссылке.");
      } catch (error) { toast(error.message, true); }
    }
    renderApp();
    beginCallPolling();
    beginMessagePolling();
  } catch {
    token = "";
    localStorage.removeItem(TOKEN_KEY);
    renderAuth();
  }
  hidePageLoader();
}

function hidePageLoader() {
  document.querySelector("#pageLoader")?.classList.add("page-loader--hidden");
}

async function api(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(path, { ...options, headers, body: options.body ? JSON.stringify(options.body) : undefined });
  const data = await response.json();
  if (!response.ok || data.ok === false) throw new Error(data.error || "Ошибка запроса");
  return data;
}

async function loadState() {
  state = await api("/api/bootstrap");
  state.posts ||= [];
  state.stories ||= [];
  state.scheduledPosts ||= [];
  state.channelLinks ||= [];
  state.telegramChannelLinks ||= [];
  state.rssChannelLinks ||= [];
  state.channelComments ||= [];
  state.notifications ||= [];
  document.body.classList.toggle("theme-dark", state.me.theme === "dark");
  document.documentElement.style.setProperty("--primary", state.me.siteColor || "#2aabee");
  document.documentElement.style.setProperty("--primary-dark", colorShade(state.me.siteColor || "#2aabee", -20));
  document.documentElement.style.setProperty("--primary-rgb", colorToRgb(state.me.siteColor || "#2aabee"));
  document.documentElement.style.setProperty("--own-bubble", state.me.dialogColor || "#ffffff");
  document.documentElement.style.setProperty("--own-bubble-background", state.me.dialogColor || "#ffffff");
  document.documentElement.style.setProperty("--own-bubble-text", dialogBubbleTextColor(state.me.dialogColor || "#ffffff"));
  document.documentElement.style.setProperty("--other-bubble", state.me.otherDialogColor || "#ffffff");
  document.documentElement.style.setProperty("--other-bubble-text", dialogBubbleTextColor(state.me.otherDialogColor || "#ffffff"));
  document.documentElement.style.setProperty("--message-font", dialogMessageFont(state.me.dialogFont || "business"));
  const nightAppearance = effectiveNightAppearance();
  document.body.classList.toggle("night-appearance-customized", Boolean(state.me.nightAppearanceCustom) || !sameNightAppearance(defaultNightAppearance(), BASE_NIGHT_APPEARANCE));
  document.documentElement.style.setProperty("--night-outline", nightAppearance.outlineColor);
  document.documentElement.style.setProperty("--night-outline-rgb", colorToRgb(nightAppearance.outlineColor));
  document.documentElement.style.setProperty("--night-glow-rgb", colorToRgb(nightAppearance.glowColor));
  document.documentElement.style.setProperty("--night-glow-low", String(nightAppearance.glowIntensity / 670));
  document.documentElement.style.setProperty("--night-glow-medium", String(nightAppearance.glowIntensity / 330));
  document.documentElement.style.setProperty("--night-glow-strong", String(nightAppearance.glowIntensity / 220));
  document.documentElement.style.setProperty("--night-glow-composer", String(nightAppearance.glowIntensity / 620));
  document.body.className = document.body.className.replace(/site-background-\S+/g, "").trim();
  document.body.classList.add(`site-background-${state.me.siteBackground || "default"}`);
  document.body.className = document.body.className.replace(/chat-theme-\S+/g, "").trim();
  document.body.classList.add(`chat-theme-${state.me.chatBackground || "default"}`);
  document.body.style.setProperty("--site-background-image", state.me.siteBackground === "custom" && state.me.siteBackgroundData ? `url('${state.me.siteBackgroundData.replace(/'/g, "%27")}')` : "none");
  document.documentElement.style.setProperty("--dialog-panel-wallpaper", state.me.chatBackground === "custom" && state.me.chatBackgroundData ? `url('${state.me.chatBackgroundData.replace(/'/g, "%27")}')` : "none");
  if (activeChatId && !state.chats.some((chat) => chat.id === activeChatId)) activeChatId = null;
}

function renderAuth() {
  document.body.classList.remove("theme-dark");
  app.innerHTML = `
    <main class="auth-shell">
      <section class="auth-card">
        <div class="brand">
          <div class="logo">CP</div>
          <div><h1 class="auth-brand-title" aria-label="Chat-Pro"><span aria-hidden="true" style="--letter-delay: 0ms">C</span><span aria-hidden="true" style="--letter-delay: 65ms">h</span><span aria-hidden="true" style="--letter-delay: 130ms">a</span><span aria-hidden="true" style="--letter-delay: 195ms">t</span><span aria-hidden="true" style="--letter-delay: 260ms">-</span><span aria-hidden="true" style="--letter-delay: 325ms">P</span><span aria-hidden="true" style="--letter-delay: 390ms">r</span><span aria-hidden="true" style="--letter-delay: 455ms">o</span></h1><p>Мессенджер, группы, отзывы, звёзды и акции</p></div>
        </div>
        <div class="tabs"><button class="tab active" data-tab="login">Вход</button><button class="tab" data-tab="register">Регистрация</button></div>
        <form class="form" data-form="login">
          <label>Username<input name="username" required placeholder="andrei"></label>
          <label>Пароль<span class="password-field"><input name="password" type="password" required><button class="button small" type="button" data-toggle-password>Показать</button></span></label>
          <button class="button primary">Войти</button>
          <button class="auth-link" type="button" data-open-password-reset>Забыли пароль?</button>
        </form>
        <form class="form hidden" data-form="register">
          <label>Имя<input name="name" required placeholder="Ваше имя"></label>
          <label>Username<input name="username" required placeholder="latin_123"></label>
          <label>Способ регистрации<select name="contactType" data-registration-contact-type><option value="email">E-mail</option><option value="phone">Номер телефона</option></select></label>
          <label data-registration-email>E-mail<input name="email" type="email" autocomplete="email" required placeholder="you@example.com"></label>
          <label class="hidden" data-registration-phone>Номер телефона<input name="phone" type="tel" inputmode="tel" autocomplete="tel" placeholder="+79991234567"></label>
          <label>Пароль<span class="password-field"><input name="password" type="password" minlength="8" autocomplete="new-password" required><button class="button small" type="button" data-toggle-password>Показать</button></span></label>
          <small class="muted">Код подтверждения придёт на выбранный контакт.</small>
          <button class="button primary">Создать аккаунт</button>
        </form>
        <div class="card"><b>Сохранённые аккаунты</b><div id="savedAccounts" class="grid" style="margin-top:10px"></div></div>
      </section>
    </main>`;

  app.querySelectorAll("[data-tab]").forEach((tab) => tab.addEventListener("click", () => {
    app.querySelectorAll("[data-tab]").forEach((x) => x.classList.toggle("active", x === tab));
    app.querySelectorAll("[data-form]").forEach((form) => form.classList.toggle("hidden", form.dataset.form !== tab.dataset.tab));
  }));
  app.querySelector('[data-form="login"]').addEventListener("submit", (event) => submitAuth(event, "/api/login"));
  app.querySelector('[data-form="register"]').addEventListener("submit", submitRegistration);
  const contactType = app.querySelector("[data-registration-contact-type]");
  contactType.addEventListener("change", () => {
    const isEmail = contactType.value === "email";
    const email = app.querySelector("[data-registration-email]");
    const phone = app.querySelector("[data-registration-phone]");
    email.classList.toggle("hidden", !isEmail);
    phone.classList.toggle("hidden", isEmail);
    email.querySelector("input").required = isEmail;
    phone.querySelector("input").required = !isEmail;
  });
  app.querySelector("[data-open-password-reset]").addEventListener("click", openPasswordReset);
  app.querySelectorAll("[data-toggle-password]").forEach((button) => button.addEventListener("click", togglePasswordVisibility));
  renderSavedAccounts();
}

async function submitRegistration(event) {
  event.preventDefault();
  try {
    const data = await api("/api/register", { method: "POST", body: Object.fromEntries(new FormData(event.currentTarget)) });
    openContactVerification(data.challengeId, "registration");
  } catch (error) { toast(error.message, true); }
}

function openContactVerification(challengeId, purpose) {
  const overlay = document.createElement("div");
  overlay.className = "member-manager-overlay";
  const apiPurpose = purpose === "registration" ? "register" : "password_reset";
  overlay.innerHTML = `<section class="member-manager auth-verification" role="dialog" aria-modal="true" aria-label="Подтверждение контактов"><header><div><b>${purpose === "registration" ? "Подтвердите контакт" : "Восстановление пароля"}</b><small>Введите шестизначный код из выбранного e-mail или SMS. Он действует 10 минут.</small></div><button class="member-manager__close" type="button" aria-label="Закрыть">×</button></header><form class="form" data-contact-verification><label>Код подтверждения<input name="code" inputmode="numeric" pattern="\\d{6}" maxlength="6" autocomplete="one-time-code" required placeholder="000000"></label>${purpose === "reset" ? '<label>Новый пароль<span class="password-field"><input name="password" type="password" minlength="8" autocomplete="new-password" required><button class="button small" type="button" data-toggle-password>Показать</button></span></label>' : ""}<button class="button primary">${purpose === "registration" ? "Подтвердить и войти" : "Изменить пароль"}</button><button class="auth-link" type="button" data-resend-auth-code>Отправить код повторно</button><small class="muted" data-resend-auth-status></small></form></section>`;
  document.body.append(overlay);
  const close = () => overlay.remove();
  overlay.querySelector(".member-manager__close").addEventListener("click", close);
  overlay.addEventListener("click", (event) => { if (event.target === overlay) close(); });
  overlay.querySelectorAll("[data-toggle-password]").forEach((button) => button.addEventListener("click", togglePasswordVisibility));
  const resendButton = overlay.querySelector("[data-resend-auth-code]");
  const resendStatus = overlay.querySelector("[data-resend-auth-status]");
  let resendTimer;
  const setResendCooldown = (seconds) => {
    window.clearInterval(resendTimer);
    let remaining = seconds;
    const update = () => {
      resendButton.disabled = remaining > 0;
      resendStatus.textContent = remaining > 0 ? `Повторная отправка будет доступна через ${remaining} с.` : "";
    };
    update();
    resendTimer = window.setInterval(() => {
      remaining -= 1;
      update();
      if (remaining <= 0) window.clearInterval(resendTimer);
    }, 1000);
  };
  setResendCooldown(60);
  resendButton.addEventListener("click", async () => {
    try {
      const data = await api("/api/auth-challenges/resend", { method: "POST", body: { challengeId, purpose: apiPurpose } });
      toast(data.message);
      setResendCooldown(60);
    } catch (error) { toast(error.message, true); }
  });
  overlay.querySelector("[data-contact-verification]").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const body = { challengeId, ...Object.fromEntries(new FormData(event.currentTarget)) };
      const data = await api(purpose === "registration" ? "/api/register/verify" : "/api/password-reset/confirm", { method: "POST", body });
      if (purpose === "registration") {
        token = data.token;
        localStorage.setItem(TOKEN_KEY, token);
        activeSection = "chats";
        activeChatId = null;
        menuOpen = false;
        await loadState();
        rememberAccount(state.me, token);
        close();
        render();
      } else {
        close();
        toast(data.message);
      }
    } catch (error) { toast(error.message, true); }
  });
}

function openPasswordReset() {
  const overlay = document.createElement("div");
  overlay.className = "member-manager-overlay";
  overlay.innerHTML = `<section class="member-manager auth-verification" role="dialog" aria-modal="true" aria-label="Восстановление пароля"><header><div><b>Восстановление пароля</b><small>Введите e-mail или номер телефона, привязанный к аккаунту.</small></div><button class="member-manager__close" type="button" aria-label="Закрыть">×</button></header><form class="form" data-password-reset-request><label>E-mail или номер телефона<input name="contact" required autocomplete="username" placeholder="you@example.com или +79991234567"></label><button class="button primary">Получить коды</button></form></section>`;
  document.body.append(overlay);
  const close = () => overlay.remove();
  overlay.querySelector(".member-manager__close").addEventListener("click", close);
  overlay.addEventListener("click", (event) => { if (event.target === overlay) close(); });
  overlay.querySelector("[data-password-reset-request]").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const data = await api("/api/password-reset/request", { method: "POST", body: Object.fromEntries(new FormData(event.currentTarget)) });
      close();
      if (data.challengeId) openContactVerification(data.challengeId, "reset");
      else toast(data.message);
    } catch (error) { toast(error.message, true); }
  });
}

function togglePasswordVisibility(event) {
  const button = event.currentTarget;
  const input = button.closest(".password-field").querySelector("input");
  const shouldShow = input.type === "password";
  input.type = shouldShow ? "text" : "password";
  button.textContent = shouldShow ? "Скрыть" : "Показать";
}

function renderSavedAccounts() {
  const box = app.querySelector("#savedAccounts");
  const accounts = getSavedAccounts();
  box.innerHTML = accounts.length ? "" : '<span class="muted">Пока нет сохранённых входов.</span>';
  accounts.forEach((account) => {
    const item = document.createElement("div");
    item.className = "saved-account";
    item.innerHTML = `<button class="row saved-account__login" type="button">${avatarHtml(account)}<div class="row__body"><div class="row__title">${esc(account.name)}</div><div class="row__sub">@${esc(account.username)}</div></div></button><button class="saved-account__remove" type="button" aria-label="Убрать ${esc(account.name)} из сохранённых аккаунтов" title="Убрать из сохранённых">×</button>`;
    item.querySelector(".saved-account__login").addEventListener("click", async () => {
      token = account.token;
      localStorage.setItem(TOKEN_KEY, token);
      await start();
    });
    item.querySelector(".saved-account__remove").addEventListener("click", () => {
      if (!window.confirm(`Вы уверены, что хотите убрать аккаунт «${account.name}» из сохранённых?`)) return;
      removeSavedAccount(account.id);
      renderSavedAccounts();
    });
    box.append(item);
  });
}

async function submitAuth(event, path) {
  event.preventDefault();
  const body = Object.fromEntries(new FormData(event.currentTarget));
  try {
    const data = await api(path, { method: "POST", body });
    token = data.token;
    localStorage.setItem(TOKEN_KEY, token);
    activeSection = "chats";
    activeChatId = null;
    menuOpen = false;
    await loadState();
    rememberAccount(state.me, token);
    renderApp();
  } catch (error) {
    toast(error.message, true);
  }
}

function renderApp() {
  if (activeSection === "profile") return renderProfileScreen();
  app.innerHTML = `
    <main class="app-shell without-rightbar${activeChatId ? " chat-is-open" : ""}">
      <aside class="sidebar ${chatBackgroundClass(state.me)}"${state.me.chatBackground === "custom" && state.me.chatBackgroundData ? ` style="--sidebar-chat-wallpaper: url('${esc(state.me.chatBackgroundData)}');"` : ""}>
        <header class="profile">
          <button class="profile-trigger" data-menu-toggle aria-expanded="${menuOpen}">
            ${avatarHtml(state.me)}
            <div class="profile__body">
              <strong>${esc(state.me.name)} ${premiumBadge(state.me)}</strong>
              <span>@${esc(state.me.username)}</span>
            </div>
            <span class="profile-menu-arrow" aria-hidden="true">⌄</span>
          </button>
          <nav class="nav menu-drawer${menuOpen ? " open" : ""}" aria-hidden="${!menuOpen}">
            ${navButton("chats", "Чаты", "💬")}${navButton("profile", "Профиль", "◉")}${navButton("channels", "Создать канал", "")}${navButton("community", "Создать беседу", "👥")}${navButton("secret-chat", "Скрытый чат", "")}${navButton("stars", "Звёзды", "★")}${navButton("account-level", "Уровень аккаунта", "✦")}${navButton("reviews", "Отзывы о действиях людей", "★")}${navButton("activity-rewards", "Награды за активность", "✧")}${navButton("settings", "Настройки", "⚙")}
          </nav>
        </header>
        <div class="list" id="leftList"></div>
      </aside>
      <section class="chat-panel" id="chatPanel"></section>

    </main>`;

  app.querySelectorAll(".menu-drawer [data-section]").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      openMenuSection(button.dataset.section);
    });
  });
  app.querySelector("[data-menu-toggle]").addEventListener("click", (event) => {
    menuOpen = !menuOpen;
    event.currentTarget.setAttribute("aria-expanded", String(menuOpen));
    const menu = app.querySelector(".menu-drawer");
    menu.classList.toggle("open", menuOpen);
    menu.setAttribute("aria-hidden", String(!menuOpen));
  });
  renderLeft();
  renderChat();
}

function openMenuSection(section) {
  profileReturnSection = activeSection;
  activeSection = section;
  if (activeSection === "secret-chat") {
    activeSection = "chats";
    menuOpen = false;
    renderApp();
    openSecretChatCreator();
    return;
  }
  if (activeSection === "settings") settingsSection = "general";
  if (activeSection === "profile") openedProfileId = state.me.id;
  menuOpen = false;
  renderApp();
}

function openMobileChatMenu() {
  const overlay = document.createElement("div");
  overlay.className = "mobile-chat-menu-overlay";
  overlay.innerHTML = `<section class="mobile-chat-menu" role="dialog" aria-modal="true" aria-label="Меню чата"><header><div><b>Меню</b><small>Навигация по Chat-Pro</small></div><button type="button" data-close-mobile-chat-menu aria-label="Закрыть меню">×</button></header><div class="mobile-chat-menu__actions"><button class="mobile-chat-menu__chats" type="button" data-mobile-chat-list>${navIcon("chats")}<span>Все чаты</span></button>${["profile", "channels", "community", "secret-chat", "stars", "account-level", "reviews", "activity-rewards", "settings"].map((section) => navButton(section, ({ profile: "Профиль", channels: "Создать канал", community: "Создать беседу", "secret-chat": "Скрытый чат", stars: "Звёзды", "account-level": "Уровень аккаунта", reviews: "Отзывы о действиях людей", "activity-rewards": "Награды за активность", settings: "Настройки" })[section], "")).join("")}</div></section>`;
  document.body.append(overlay);
  const close = () => overlay.remove();
  overlay.querySelector("[data-close-mobile-chat-menu]").addEventListener("click", close);
  overlay.querySelector("[data-mobile-chat-list]").addEventListener("click", () => {
    activeChatId = null;
    close();
    renderApp();
  });
  overlay.querySelectorAll("[data-section]").forEach((button) => button.addEventListener("click", () => {
    activeChatId = null;
    close();
    openMenuSection(button.dataset.section);
  }));
  overlay.addEventListener("click", (event) => { if (event.target === overlay) close(); });
}

function navIcon(id) {
  const icons = {
    chats: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M7.3 14.8h-.9A3.9 3.9 0 0 1 2.5 11V8.1a3.9 3.9 0 0 1 3.9-3.9h5.4a3.9 3.9 0 0 1 3.9 3.9v.6"/><path d="M5.9 14.6v3.1l3.5-2.5"/><path d="M8.6 13a4.5 4.5 0 0 1 4.5-4.5h4.1a4.3 4.3 0 0 1 4.3 4.3v1.8a4.3 4.3 0 0 1-4.3 4.3h-3.8L9.5 21v-2.5a4.5 4.5 0 0 1-.9-2.7V13Z"/></svg>',
    search: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="10.5" cy="10.5" r="4.7"/><path d="m14.2 14.2 4.3 4.3"/></svg>',
    community: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="7.5" r="3.25"/><path d="M5 20v-1.25A4.75 4.75 0 0 1 9.75 14h4.5A4.75 4.75 0 0 1 19 18.75V20"/><path d="M5.25 6.25a2.75 2.75 0 0 0 0 5.5M18.75 6.25a2.75 2.75 0 0 1 0 5.5M2.25 19v-.5a3.5 3.5 0 0 1 2.5-3.35M21.75 19v-.5a3.5 3.5 0 0 0-2.5-3.35"/></svg>',
    channels: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M4 12.5 20 5l-4.6 14-4.15-5.05L4 12.5Z"/><path d="m11.25 13.95 2.55-2.55"/></svg>',
    "secret-chat": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><rect x="5.5" y="10" width="13" height="10" rx="2.5"/><path d="M8.5 10V7.5a3.5 3.5 0 0 1 7 0V10"/><path d="M12 14v2"/></svg>',
    profile: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="8.25"/><circle cx="12" cy="12" r="4.7"/></svg>',
    stars: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="m12 2.8 2.7 5.55 6.12.88-4.43 4.31 1.05 6.1L12 16.77l-5.44 2.86 1.05-6.1-4.43-4.31 6.12-.88L12 2.8Z"/></svg>',
    "account-level": '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 3.2 14.2 9.8 20.8 12l-6.6 2.2L12 20.8l-2.2-6.6L3.2 12l6.6-2.2L12 3.2Z"/></svg>',
    reviews: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><rect x="3.5" y="3" width="17" height="18" rx="3"/><path d="m12 7 1.05 2.13 2.35.34-1.7 1.65.4 2.33L12 12.35l-2.1 1.1.4-2.33-1.7-1.65 2.35-.34L12 7Z"/><path d="M7.5 17h9"/></svg>',
    "activity-rewards": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3.5 14.05 9.95 20.5 12l-6.45 2.05L12 20.5l-2.05-6.45L3.5 12l6.45-2.05L12 3.5Z"/></svg>',
    settings: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M10.35 3h3.3l.52 2.15c.42.16.82.33 1.19.54l1.93-1.15 2.33 2.33-1.15 1.93c.21.37.39.77.54 1.19l2.15.52v3.3l-2.15.52c-.15.42-.33.82-.54 1.19l1.15 1.93-2.33 2.33-1.93-1.15c-.37.21-.77.39-1.19.54L13.65 21h-3.3l-.52-2.15c-.42-.15-.82-.33-1.19-.54l-1.93 1.15-2.33-2.33 1.15-1.93c-.21-.37-.39-.77-.54-1.19L2.84 13.5v-3.3l2.15-.52c.15-.42.33-.82.54-1.19L4.38 6.56l2.33-2.33 1.93 1.15c.37-.21.77-.39 1.19-.54L10.35 3Zm1.65 6a3 3 0 1 0 0 6 3 3 0 0 0 0-6Z"/></svg>',
  };
  return icons[id] || "";
}

function navButton(id, label, icon) { return `<button class="nav-button${activeSection === id ? " active" : ""}" data-section="${id}"><span class="nav-button__icon" aria-hidden="true">${navIcon(id) || icon}</span><span class="nav-button__label">${label}</span></button>`; }

function renderLeft() {
  const box = app.querySelector("#leftList");
  box.dataset.section = activeSection;
  if (activeSection === "chats") return renderChatsList(box);
  if (activeSection === "archive") return renderArchiveList(box);
  if (activeSection === "groups") return renderGroupsList(box, "group");
  if (activeSection === "community") return renderGroupsList(box, "community");
  if (activeSection === "channels") return renderGroupsList(box, "channel");
  if (activeSection === "stars") return renderStarsPanel(box);
  if (activeSection === "account-level") return renderAccountLevelPanel(box);
  if (activeSection === "reviews") return renderReviewsPanel(box);
  if (activeSection === "activity-rewards") return renderActivityRewardsPanel(box);
  renderSettingsPanel(box, settingsSection);
}

function renderChatsList(box) {
  const filters = [["all", "Все"], ["direct", "Диалоги"], ["community", "Беседы"], ["channel", "Каналы"]];
  const chats = visibleChats(false).filter((chat) => chatFilter === "all" || chat.type === chatFilter);
  const recommendedChannels = chatFilter === "channel"
    ? (state.recommended || []).map((rec) => state.chats.find((chat) => chat.id === rec.chat_id && chat.type === "channel" && !isMember(chat.id))).filter(Boolean)
    : [];
  const storyStrip = directStoryStripHtml();
  box.dataset.dialogFilter = chatFilter;
  const channelsHtml = chats.map(chatRow).join("") || '<p class="muted">Вы пока не подписаны ни на один канал.</p>';
  const recommendationsHtml = recommendedChannels.length ? `<section class="recommended-channels"><div class="recommended-channels__title"><b>Рекомендованные каналы</b><span>Подборка для вас</span></div>${recommendedChannels.map(recommendedChannelRow).join("")}</section>` : "";
  box.innerHTML = `<div class="chat-filters">${filters.map(([id, label]) => `<button class="chip${chatFilter === id ? " active" : ""}" data-chat-filter="${id}">${label}</button>`).join("")}</div>${storyStrip}<label class="chat-search" aria-label="Поиск людей"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="10.8" cy="10.8" r="5.8"></circle><path d="m15.2 15.2 4.3 4.3"></path></svg><input id="userSearch" placeholder="username"></label><div id="searchResults"></div>${channelsHtml}${recommendationsHtml}`;
  box.querySelectorAll("[data-chat-filter]").forEach((button) => button.addEventListener("click", () => { chatFilter = button.dataset.chatFilter; renderChatsList(box); }));
  bindChatRows(box);
  bindStoriesStrip(box);
  box.querySelector("#userSearch").addEventListener("input", searchUsers);
  box.querySelectorAll("[data-open-recommended-channel]").forEach((button) => button.addEventListener("click", () => {
    activeChatId = button.dataset.openRecommendedChannel;
    scrollChatToLatest = true;
    renderApp();
  }));
  box.querySelectorAll("[data-join-recommended-channel]").forEach((button) => button.addEventListener("click", async (event) => {
    try { await api("/api/chats/join", { method: "POST", body: { chatId: event.currentTarget.dataset.joinRecommendedChannel } }); toast("Вы подписались на канал."); await refresh(); }
    catch (error) { toast(error.message, true); }
  }));
}

function renderArchiveList(box) {
  const chats = visibleChats(true);
  box.innerHTML = `<div class="panel-title"><b>Архив</b><span class="muted">${chats.length}</span></div><p class="muted">Здесь находятся чаты, которые вы убрали из общего списка.</p>${chats.map(chatRow).join("") || '<p class="muted">Архив пока пуст.</p>'}`;
  bindChatRows(box);
}

function bindChatRows(box) {
  box.querySelectorAll("[data-chat]").forEach((row) => row.addEventListener("click", () => {
    activeChatId = row.dataset.chat;
    scrollChatToLatest = true;
    renderApp();
    markChatRead(row.dataset.chat);
  }));
  box.querySelectorAll("[data-chat-menu]").forEach((button) => button.addEventListener("click", () => openChatMenu(button.dataset.chatMenu)));
}

async function searchUsers(event) {
  const q = event.target.value.trim();
  const target = app.querySelector("#searchResults");
  if (!q) { target.innerHTML = ""; return; }
  try {
    const data = await api(`/api/users?q=${encodeURIComponent(q)}`);
    target.innerHTML = data.users.map((u) => `<button class="row" data-open-profile="${u.id}">${avatarHtml(u)}<div class="row__body"><div class="row__title">${esc(u.name)}</div><div class="row__sub">@${esc(u.username)}</div></div><span class="badge">Профиль</span></button>`).join("") || '<p class="muted">Никого не нашли.</p>';
    target.querySelectorAll("[data-open-profile]").forEach((btn) => btn.addEventListener("click", () => openProfile(btn.dataset.openProfile)));
  } catch (error) { toast(error.message, true); }
}


function renderProfileScreen() {
  const profileUser = userById(openedProfileId) || state.me;
  const ownProfile = profileUser.id === state.me.id;
  const posts = (state.posts || []).filter((post) => post.user_id === profileUser.id);
  const stories = (state.stories || []).filter((story) => story.user_id === profileUser.id);
  app.innerHTML = `<main class="profile-screen"><header class="profile-screen__head"><button class="back-button" data-close-profile aria-label="Вернуться">←</button><b>${ownProfile ? "Мой профиль" : "Профиль"}</b><button class="profile-more" type="button" data-profile-menu="${profileUser.id}" aria-label="Действия с профилем">⋯</button></header><section class="profile-screen__content"><div class="profile-hero"><button class="profile-avatar-button" data-open-media="${esc(profileUser.avatarData || "")}" ${profileUser.avatarData ? "" : "disabled"}>${avatarHtml(profileUser, "avatar profile-avatar")}</button><div><h1>${esc(profileUser.name)} ${premiumBadge(profileUser)}</h1><p class="muted">@${esc(profileUser.username)}</p>${!ownProfile ? `<button class="button primary small" data-message-user="${profileUser.id}">Написать</button>` : ""}</div></div>
    ${ownProfile ? `<section class="profile-actions"><div class="profile-action-grid"><button class="profile-action-button" type="button" data-profile-action="avatar"><span class="profile-action-button__icon">◉</span><span><b>Аватар</b><small>Фото профиля</small></span></button><button class="profile-action-button" type="button" data-profile-action="post"><span class="profile-action-button__icon">▤</span><span><b>Публикация</b><small>Текст или фото</small></span></button><button class="profile-action-button" type="button" data-profile-action="story"><span class="profile-action-button__icon">◌</span><span><b>История</b><small>На 48 часов</small></span></button></div><form class="card form profile-edit-card" id="avatarForm" data-profile-action-panel="avatar" hidden><div class="profile-edit-card__head"><span class="profile-action-button__icon">◉</span><div><b>Фото профиля</b><p class="muted">Обновите аватар, который видят друзья.</p></div></div><label>Аватар<input name="avatar" type="file" accept="image/png,image/jpeg,image/webp" data-image-preview-input="avatar-preview"></label><img class="profile-upload-preview profile-upload-preview--avatar" data-image-preview="avatar-preview" alt="Предпросмотр нового аватара" hidden><button class="button primary">Загрузить аватар</button></form><form class="card form profile-edit-card" id="postForm" data-profile-action-panel="post" hidden><div class="profile-edit-card__head"><span class="profile-action-button__icon">▤</span><div><b>Новая публикация</b><p class="muted">Добавьте текст или фото в профиль.</p></div></div><label>Подпись<textarea name="text" placeholder="Что у вас нового?"></textarea></label><label>Фото<input name="photo" type="file" accept="image/png,image/jpeg,image/webp" data-image-preview-input="post-preview"></label><img class="profile-upload-preview" data-image-preview="post-preview" alt="Предпросмотр фото для публикации" hidden><button class="button primary">Опубликовать пост</button></form><form class="card form profile-edit-card" id="storyForm" data-profile-action-panel="story" hidden><div class="profile-edit-card__head"><span class="profile-action-button__icon">◌</span><div><b>История на 48 часов</b><p class="muted">После выбора фото откроется редактор с текстом и вторым изображением.</p></div></div><label>Основное фото<input name="media" type="file" accept="image/png,image/jpeg,image/webp" required data-image-preview-input="story-preview"></label><img class="profile-upload-preview profile-upload-preview--story" data-image-preview="story-preview" alt="Предпросмотр истории" hidden><label>Подпись<input name="caption" placeholder="Можно оставить пустым"></label><button class="button primary">Открыть редактор</button></form></section>${state.notifications.length ? `<section class="card owner-notifications"><b>Уведомления владельца</b>${state.notifications.map((notice) => `<p>${esc(notice.text)}</p>`).join("")}</section>` : ""}` : ""}<div class="profile-publications"><section class="card"><b>Сторис</b><div class="stories-row">${stories.map(storyHtml).join("") || '<p class="muted">Сторис пока нет.</p>'}</div></section>${posts.some((post) => post.media_data) ? `<section class="card"><b>Фотографии</b><div class="post-gallery">${posts.filter((post) => post.media_data).map(galleryPostHtml).join("")}</div></section>` : ""}${posts.some((post) => post.text) ? `<section class="card"><b>Публикации</b>${posts.filter((post) => post.text).map(postHtml).join("")}</section>` : ""}${posts.length ? "" : '<section class="card"><p class="muted">Постов пока нет.</p></section>'}</div></section></main>`;
  app.querySelector("#avatarForm")?.addEventListener("submit", submitAvatar);
  app.querySelector("#postForm")?.addEventListener("submit", submitProfilePost);
  app.querySelector("#storyForm")?.addEventListener("submit", submitStory);
  app.querySelectorAll("[data-profile-action]").forEach((button) => button.addEventListener("click", () => {
    const action = button.dataset.profileAction;
    app.querySelectorAll("[data-profile-action]").forEach((item) => item.classList.toggle("active", item === button));
    app.querySelectorAll("[data-profile-action-panel]").forEach((panel) => { panel.hidden = panel.dataset.profileActionPanel !== action; });
  }));
  app.querySelectorAll("[data-image-preview-input]").forEach((input) => input.addEventListener("change", () => {
    const preview = app.querySelector(`[data-image-preview="${input.dataset.imagePreviewInput}"]`);
    const file = input.files?.[0];
    if (!preview || !file) return;
    const reader = new FileReader();
    reader.onload = () => { preview.src = reader.result; preview.hidden = false; };
    reader.readAsDataURL(file);
  }));
  app.querySelector("[data-close-profile]").addEventListener("click", closeProfile);
  app.querySelector("[data-message-user]")?.addEventListener("click", async (event) => { await openDirectChat(event.currentTarget.dataset.messageUser); });
  app.querySelector("[data-profile-menu]")?.addEventListener("click", (event) => openSimpleActions(event.currentTarget, profileMenuActions(profileUser)));
  app.querySelectorAll("[data-open-media]").forEach((item) => item.addEventListener("click", () => openMedia(item.dataset.openMedia)));
  app.querySelectorAll("[data-open-profile-post]").forEach((item) => item.addEventListener("click", () => openProfilePost(item.dataset.openProfilePost)));
  app.querySelectorAll("[data-open-story]").forEach((item) => item.addEventListener("click", () => openStory(item.dataset.openStory)));
  app.querySelectorAll("[data-share-profile-post]").forEach((item) => item.addEventListener("click", () => openGroupContentShare("profile-post", item.dataset.shareProfilePost)));
  app.querySelectorAll("[data-post-menu]").forEach((item) => item.addEventListener("click", (event) => {
    const post = state.posts.find((entry) => entry.id === event.currentTarget.dataset.postMenu);
    if (!post) return;
    const actions = [
      { label: "Открыть публикацию", action: () => openProfilePost(post.id) },
      { label: "Поделиться", action: () => openGroupContentShare("profile-post", post.id) },
    ];
    if (post.user_id !== state.me.id) actions.push({ label: "Пожаловаться", action: () => reportTarget("profile-post", post.id) });
    openSimpleActions(event.currentTarget, actions);
  }));
}

async function submitAvatar(event) {
  event.preventDefault();
  const file = new FormData(event.currentTarget).get("avatar");
  if (!file?.size) return toast("Выберите фото.", true);
  const avatarData = await fileToDataUrl(file, 1_800_000);
  await api("/api/profile/avatar", { method: "POST", body: { avatarData } });
  toast("Аватар обновлён.");
  await refresh();
}

async function submitProfilePost(event) {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const photo = form.get("photo");
  const mediaData = photo?.size ? await fileToDataUrl(photo, 2_500_000) : "";
  await api("/api/profile/posts", { method: "POST", body: { text: form.get("text"), mediaData } });
  toast("Пост опубликован.");
  await refresh();
}

async function submitStory(event) {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const file = form.get("media");
  if (!file?.size) return toast("Выберите основное фото.", true);
  openStoryEditor(file, String(form.get("caption") || ""));
}

function openStoryEditor(primaryFile, initialCaption) {
  const overlay = document.createElement("div");
  overlay.className = "story-editor-overlay";
  overlay.innerHTML = `<section class="story-editor" role="dialog" aria-modal="true" aria-label="Редактор сторис"><header><div><b>Редактор сторис</b><small>Перетаскивайте фото и текст прямо на макете</small></div><button type="button" class="member-manager__close" data-close-story-editor aria-label="Закрыть">×</button></header><div class="story-editor__canvas" data-story-editor-canvas><img data-story-primary alt="Основное фото"><img class="story-editor__sticker hidden" data-story-secondary alt="Дополнительное фото"><div class="story-editor__text" data-story-editor-text></div></div><form class="form story-editor__controls" data-story-editor-form><label>Дополнительное фото<input name="secondary" type="file" accept="image/png,image/jpeg,image/webp"></label><label>Размер фото<input name="secondarySize" type="range" min="18" max="70" value="34"></label><label>Текст на сторис<textarea name="text" maxlength="300" placeholder="Напишите что-нибудь">${esc(initialCaption)}</textarea></label><label>Размер текста<input name="textSize" type="range" min="18" max="64" value="36"></label><label>Шрифт<select name="font"><option value="system">Современный</option><option value="serif">С засечками</option><option value="mono">Моно</option><option value="script">Рукописный</option></select></label><label>Цвет текста<input name="color" type="color" value="#ffffff"></label><button class="button primary" type="submit">Опубликовать сторис</button></form></section>`;
  document.body.append(overlay);
  const primaryData = URL.createObjectURL(primaryFile);
  const primary = overlay.querySelector("[data-story-primary]");
  const secondary = overlay.querySelector("[data-story-secondary]");
  const canvas = overlay.querySelector("[data-story-editor-canvas]");
  const text = overlay.querySelector("[data-story-editor-text]");
  const form = overlay.querySelector("[data-story-editor-form]");
  let secondaryData = "";
  let secondaryPosition = { x: 50, y: 50 };
  let textPosition = { x: 50, y: 88 };
  let drag = null;
  primary.src = primaryData;
  const close = () => { URL.revokeObjectURL(primaryData); overlay.remove(); };
  overlay.querySelector("[data-close-story-editor]").addEventListener("click", close);
  overlay.addEventListener("click", (event) => { if (event.target === overlay) close(); });
  const renderText = () => {
    const values = new FormData(form);
    text.textContent = String(values.get("text") || "");
    text.dataset.font = String(values.get("font") || "system");
    text.style.color = String(values.get("color") || "#ffffff");
    text.style.fontSize = `${values.get("textSize") || 36}px`;
    text.style.left = `${textPosition.x}%`;
    text.style.top = `${textPosition.y}%`;
  };
  const renderSecondaryPosition = () => {
    secondary.style.left = `${secondaryPosition.x}%`;
    secondary.style.top = `${secondaryPosition.y}%`;
    secondary.style.width = `${form.elements.secondarySize.value}%`;
  };
  form.elements.secondary.addEventListener("change", async (event) => {
    const file = event.currentTarget.files[0];
    if (!file) return;
    try {
      secondaryData = await fileToDataUrl(file, 2_500_000);
      secondary.src = secondaryData;
      secondary.classList.remove("hidden");
      secondaryPosition = { x: 50, y: 50 };
      renderSecondaryPosition();
    } catch (error) { toast(error.message, true); }
  });
  form.elements.text.addEventListener("input", renderText);
  form.elements.textSize.addEventListener("input", renderText);
  form.elements.font.addEventListener("change", renderText);
  form.elements.color.addEventListener("input", renderText);
  form.elements.secondarySize.addEventListener("input", renderSecondaryPosition);
  secondary.addEventListener("pointerdown", (event) => {
    if (!secondaryData) return;
    event.preventDefault();
    secondary.setPointerCapture(event.pointerId);
    drag = { pointerId: event.pointerId, target: "secondary", startX: event.clientX, startY: event.clientY, x: secondaryPosition.x, y: secondaryPosition.y };
  });
  secondary.addEventListener("pointermove", (event) => {
    if (!drag || drag.pointerId !== event.pointerId) return;
    const rect = canvas.getBoundingClientRect();
    secondaryPosition.x = Math.max(12, Math.min(88, drag.x + (event.clientX - drag.startX) / rect.width * 100));
    secondaryPosition.y = Math.max(12, Math.min(88, drag.y + (event.clientY - drag.startY) / rect.height * 100));
    renderSecondaryPosition();
  });
  secondary.addEventListener("pointerup", () => { drag = null; });
  text.addEventListener("pointerdown", (event) => {
    if (!text.textContent) return;
    event.preventDefault();
    text.setPointerCapture(event.pointerId);
    drag = { pointerId: event.pointerId, target: "text", startX: event.clientX, startY: event.clientY, x: textPosition.x, y: textPosition.y };
  });
  text.addEventListener("pointermove", (event) => {
    if (!drag || drag.target !== "text" || drag.pointerId !== event.pointerId) return;
    const rect = canvas.getBoundingClientRect();
    textPosition.x = Math.max(10, Math.min(90, drag.x + (event.clientX - drag.startX) / rect.width * 100));
    textPosition.y = Math.max(8, Math.min(92, drag.y + (event.clientY - drag.startY) / rect.height * 100));
    renderText();
  });
  text.addEventListener("pointerup", () => { drag = null; });
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const values = new FormData(form);
    try {
      const mediaData = await composeStoryImage(primaryFile, secondaryData, secondaryPosition, Number(values.get("secondarySize") || 34), String(values.get("text") || ""), textPosition, Number(values.get("textSize") || 36), String(values.get("font") || "system"), String(values.get("color") || "#ffffff"));
      await api("/api/profile/stories", { method: "POST", body: { mediaData, caption: values.get("text") } });
      close();
      toast("Сторис опубликована.");
      await refresh();
    } catch (error) { toast(error.message, true); }
  });
  renderText();
}

function loadEditorImage(source) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error("Не удалось обработать изображение."));
    image.src = source;
  });
}

async function composeStoryImage(primaryFile, secondaryData, position, secondarySize, text, textPosition, textSize, font, color) {
  const primarySource = URL.createObjectURL(primaryFile);
  try {
    const primary = await loadEditorImage(primarySource);
    const scale = Math.min(1, 1080 / Math.max(primary.naturalWidth, primary.naturalHeight));
    const width = Math.max(1, Math.round(primary.naturalWidth * scale));
    const height = Math.max(1, Math.round(primary.naturalHeight * scale));
    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    const context = canvas.getContext("2d");
    context.drawImage(primary, 0, 0, width, height);
    if (secondaryData) {
      const secondary = await loadEditorImage(secondaryData);
      const stickerWidth = Math.round(width * secondarySize / 100);
      const stickerHeight = Math.round(stickerWidth * secondary.naturalHeight / secondary.naturalWidth);
      const x = Math.round(width * position.x / 100 - stickerWidth / 2);
      const y = Math.round(height * position.y / 100 - stickerHeight / 2);
      context.save();
      context.shadowColor = "rgba(0,0,0,.3)";
      context.shadowBlur = Math.max(8, width * .02);
      context.fillStyle = "#fff";
      context.fillRect(x - 4, y - 4, stickerWidth + 8, stickerHeight + 8);
      context.drawImage(secondary, x, y, stickerWidth, stickerHeight);
      context.restore();
    }
    if (text.trim()) {
      const fonts = { system: "Arial, sans-serif", serif: "Georgia, serif", mono: "Menlo, monospace", script: "cursive" };
      context.save();
      const fontSize = Math.max(18, Math.round(width * textSize / 510));
      context.font = `700 ${fontSize}px ${fonts[font] || fonts.system}`;
      context.textAlign = "center";
      context.textBaseline = "bottom";
      context.lineWidth = Math.max(3, Math.round(width * .008));
      context.strokeStyle = "rgba(0,0,0,.42)";
      context.fillStyle = color;
      const words = text.trim().split(/\s+/);
      const lines = [];
      let line = "";
      const maxWidth = width * .86;
      words.forEach((word) => { const next = line ? `${line} ${word}` : word; if (context.measureText(next).width > maxWidth && line) { lines.push(line); line = word; } else line = next; });
      if (line) lines.push(line);
      lines.slice(-4).reverse().forEach((lineText, index) => { const y = height * textPosition.y / 100 - index * fontSize * 1.2; context.strokeText(lineText, width * textPosition.x / 100, y); context.fillText(lineText, width * textPosition.x / 100, y); });
      context.restore();
    }
    return canvas.toDataURL("image/jpeg", .86);
  } finally { URL.revokeObjectURL(primarySource); }
}

function renderGroupsList(box, type) {
  const title = type === "group" ? "Группы" : type === "channel" ? "Каналы" : "Комьюнити / беседы";
  const mine = state.chats.filter((chat) => chat.type === type && isMember(chat.id));
  box.innerHTML = `
    <div class="panel-title"><b>${title}</b></div>
    <form class="card form" id="createGroup">
      <label>Название<input name="title" required></label>
      <label>Описание<textarea name="description" placeholder="${type === "channel" ? "О чём этот канал" : ""}"></textarea></label>
      ${type === "channel" ? '<p class="muted">Публиковать смогут только вы и выбранные авторы.</p>' : ""}
      <button class="button primary">Создать${type === "channel" ? " канал" : ""}</button>
    </form>
    ${mine.map(chatRow).join("") || '<p class="muted">Пока нет.</p>'}`;
  box.querySelector("#createGroup").addEventListener("submit", async (event) => {
    event.preventDefault();
    const body = Object.fromEntries(new FormData(event.currentTarget));
    body.type = type;
    const data = await api("/api/chats", { method: "POST", body });
    activeChatId = data.chat.id;
    await refresh();
  });
  box.querySelectorAll("[data-chat]").forEach((row) => row.addEventListener("click", () => { activeChatId = row.dataset.chat; renderApp(); }));
}

function renderReviewsPanel(box) {
  const sources = reviewStats();
  const activeUrl = normalizeReviewIdentifier(reviewPageUrl);
  const page = activeUrl ? sources[activeUrl] : null;
  const reviews = activeUrl ? state.reviews.filter((review) => normalizeReviewIdentifier(review.url) === activeUrl) : [];
  const relatedUrls = activeUrl ? reviewRelatedUrls(activeUrl) : [];
  const relatedReviews = !page ? state.reviews.filter((review) => relatedUrls.includes(normalizeReviewIdentifier(review.url))) : [];
  const searchForm = `<form class="review-search" data-review-search><input name="url" type="text" required placeholder="Ссылка, телефон, @username или название" value="${esc(activeUrl)}"><button class="button primary small">Найти</button></form>`;
  if (!activeUrl) {
    box.innerHTML = `<div class="panel-title"><b>Отзывы об источниках</b></div><p class="muted">Найдите ссылку, телефон, @username или название и оставьте первый отзыв.</p>${searchForm}<p class="review-suggestions-title">Возможные знакомые люди и компании</p><div class="review-source-list">${Object.values(sources).map(reviewSourceHtml).join("") || '<p class="muted">Пока нет отзывов. Укажите ссылку, телефон, @username или название выше, чтобы стать первым автором.</p>'}</div>`;
    return bindReviewSearch(box);
  }
  const positive = page?.positive || 0;
  const negative = page?.negative || 0;
  const sourceType = page?.sourceType || reviews[0]?.sourceType || (isReviewUrl(activeUrl) ? "website" : "");
  const relatedSection = relatedUrls.length ? `<section class="review-related"><b>${page ? "Связанные источники" : "Связанные источники и отзывы"}</b><div>${relatedUrls.map((url) => `<button type="button" data-open-review-page="${esc(url)}">${esc(url)}</button>`).join("")}</div></section>` : "";
  const feed = page ? `<section class="review-feed"><h3>Отзывы</h3>${reviews.map(reviewItemHtml).join("")}</section>` : `<section class="card review-empty"><b>На этот источник ещё не оставляли отзывов.</b><p class="muted">${relatedReviews.length ? "Ниже показаны отзывы со связанных источников." : "Вы можете стать первым."}</p></section>${relatedReviews.length ? `<section class="review-feed"><h3>Отзывы со связанных источников</h3>${relatedReviews.map(reviewItemHtml).join("")}</section>` : ""}`;
  box.innerHTML = `<div class="panel-title"><button class="back-button" type="button" data-close-review-page aria-label="Назад">←</button><b>Страница отзывов</b><button class="review-more" type="button" data-review-page-menu="${esc(activeUrl)}" aria-label="Действия со страницей">⋯</button></div>${searchForm}<section class="review-page card"><div class="review-page__url">${esc(activeUrl)}${sourceType ? sourceTypeBadge(sourceType) : ""}</div><div class="review-summary"><div><b>${page?.count || 0}</b><span>всего отзывов</span></div><div class="positive"><b>${positive}</b><span>положительных</span></div><div class="negative"><b>${negative}</b><span>отрицательных</span></div></div>${relatedSection}</section>${feed}${reviewFormHtml(activeUrl)}`;
  bindReviewSearch(box);
  box.querySelector("[data-close-review-page]").addEventListener("click", () => { reviewPageUrl = ""; renderReviewsPanel(box); });
  box.querySelectorAll("[data-open-review-page]").forEach((button) => button.addEventListener("click", () => { reviewPageUrl = button.dataset.openReviewPage; renderReviewsPanel(box); }));
  box.querySelectorAll("[data-open-media]").forEach((button) => button.addEventListener("click", () => openMedia(button.dataset.openMedia)));
  box.querySelector("[data-review-page-menu]")?.addEventListener("click", (event) => openSimpleActions(event.currentTarget, [{ label: "Пожаловаться на страницу", action: () => reportTarget("review-page", event.currentTarget.dataset.reviewPageMenu) }, { label: "Поделиться страницей", action: () => shareText(event.currentTarget.dataset.reviewPageMenu) }]));
  box.querySelectorAll("[data-review-menu]").forEach((button) => button.addEventListener("click", (event) => openSimpleActions(event.currentTarget, [{ label: "Пожаловаться на отзыв", action: () => reportTarget("review", event.currentTarget.dataset.reviewMenu) }, { label: "Поделиться отзывом", action: () => shareText(`Отзыв: ${event.currentTarget.dataset.reviewMenu}`) }])));
  bindReviewForm(box);
}

function bindReviewSearch(box) {
  box.querySelector("[data-review-search]").addEventListener("submit", (event) => {
    event.preventDefault();
    reviewPageUrl = normalizeReviewIdentifier(new FormData(event.currentTarget).get("url"));
    renderReviewsPanel(box);
  });
  box.querySelectorAll("[data-open-review-page]").forEach((button) => button.addEventListener("click", () => { reviewPageUrl = button.dataset.openReviewPage; renderReviewsPanel(box); }));
}

function reviewFormHtml(url) {
  const sourceType = isReviewUrl(url) || isReviewPhone(url) || isReviewTelegram(url) ? "" : `<label>Площадка этого источника<select name="sourceType" required><option value="" selected disabled>Выберите площадку</option><option value="telegram">Telegram</option><option value="instagram">Instagram</option><option value="other">Другая</option><option value="custom">Указать вручную</option></select></label><label class="review-custom-source hidden" data-custom-source>Название площадки<input name="customSourceType" maxlength="80" placeholder="Например, VK, Яндекс Карты"></label>`;
  return `<form class="card form review-form" data-review-form><h3>Оставить отзыв</h3><label>Ссылка, телефон, @username или название<input name="url" required readonly value="${esc(url)}"></label>${sourceType}<label>Город<input name="city" maxlength="120" placeholder="Например, Москва"></label><label>Оценка<select name="rating"><option value="1">Положительный</option><option value="-1">Отрицательный</option></select></label><label>Комментарий<textarea name="comment" maxlength="3000" placeholder="Расскажите о своём опыте"></textarea></label><label>Фото или видео<input name="media" type="file" accept="image/png,image/jpeg,image/webp,video/mp4,video/webm"></label><label>Связанные контакты и источники<textarea name="links" placeholder="По одному телефону, ссылке, @username или названию в строке"></textarea></label><p class="review-form__hint">Свяжите карточку с другими номерами, Telegram-именами и ссылками. По ним можно будет открыть общую страницу отзывов.</p><button class="button primary">Опубликовать отзыв</button></form>`;
}

function bindReviewForm(box) {
  const reviewForm = box.querySelector("[data-review-form]");
  const sourceType = reviewForm?.elements.sourceType;
  const customSource = reviewForm?.querySelector("[data-custom-source]");
  const syncCustomSource = () => {
    const isCustom = sourceType?.value === "custom";
    customSource?.classList.toggle("hidden", !isCustom);
    customSource?.querySelector("input").toggleAttribute("required", isCustom);
  };
  sourceType?.addEventListener("change", syncCustomSource);
  box.querySelector("[data-review-form]")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const form = new FormData(event.currentTarget);
      const media = form.get("media");
      const body = Object.fromEntries(form);
      if (body.sourceType === "custom") body.sourceType = body.customSourceType;
      delete body.customSourceType;
      delete body.media;
      if (media?.size) body.mediaData = await fileToDataUrl(media, 3_600_000);
      await api("/api/reviews", { method: "POST", body });
      toast("Отзыв опубликован.");
      await refresh();
    } catch (error) { toast(error.message, true); }
  });
}

function reviewSourceHtml(item) {
  return `<button type="button" class="card review-source" data-open-review-page="${esc(item.url)}"><div><b>${esc(item.url)}${sourceTypeBadge(item.sourceType)}</b><small>${item.count} ${reviewWord(item.count)}</small></div><div class="review-source__counts"><span class="positive">+${item.positive}</span><span class="negative">−${item.negative}</span></div></button>`;
}

function reviewItemHtml(review) {
  const media = review.mediaData || review.media_data;
  const mediaHtml = media?.startsWith("data:image/") ? `<button type="button" class="review-media" data-open-media="${esc(media)}"><img src="${esc(media)}" alt="Фото к отзыву"></button>` : media?.startsWith("data:video/") ? `<video class="review-video" controls preload="metadata" src="${esc(media)}"></video>` : "";
  return `<article class="card review-item"><div class="review-item__head"><span class="review-item__rating ${review.rating > 0 ? "positive" : "negative"}">${review.rating > 0 ? "Положительный" : "Отрицательный"}</span><button class="review-more" type="button" data-review-menu="${esc(review.id)}" aria-label="Действия с отзывом">⋯</button></div><div class="review-item__source">${esc(normalizeReviewIdentifier(review.url))}${sourceTypeBadge(review.sourceType)}</div>${review.city ? `<small class="review-item__city">${esc(review.city)}</small>` : ""}${review.comment ? `<p>${esc(review.comment)}</p>` : ""}${mediaHtml}${review.links?.length ? `<div class="review-item__links">${review.links.map((link) => `<button type="button" data-open-review-page="${esc(link)}">${esc(link)}</button>`).join("")}</div>` : ""}</article>`;
}

const ACTIVITY_CRITERIA_LABELS = {
  stars_balance: "звёзд на балансе", direct_chats: "личных диалогов", channels_joined: "подписок на каналы",
  communities_joined: "бесед", groups_joined: "групп", channels_created: "созданных каналов",
  communities_created: "созданных бесед", groups_created: "созданных групп", channel_subscribers: "подписчиков в одном канале",
  community_subscribers: "участников в одной беседе", group_subscribers: "участников в одной группе", messages: "сообщений",
  posts: "публикаций", stories: "сторис", reviews: "отзывов", donations_sent: "отправленных донатов",
  stars_donated: "отправленных звёзд", donations_received: "полученных донатов", login_streak: "дней подряд в приложении",
};

function activityCriteriaHtml(criteria = {}, progress = {}) {
  return `<ul class="activity-reward__criteria">${Object.entries(criteria).map(([key, target]) => `<li><span>${esc(ACTIVITY_CRITERIA_LABELS[key] || key)}</span><b>${Math.min(Number(progress[key]) || 0, Number(target))} / ${target}</b></li>`).join("")}</ul>`;
}

function renderActivityRewardsPanel(box) {
  const rewards = state.activityRewards || [];
  const activeRewards = rewards.filter((reward) => !reward.claimed);
  const completedRewards = rewards.filter((reward) => reward.claimed);
  const rewardCard = (reward) => `<article class="card activity-reward${reward.available ? " activity-reward--available" : ""}${reward.claimed ? " activity-reward--claimed" : ""}"><div class="activity-reward__head"><div><h3>${esc(reward.title)}</h3>${reward.description ? `<p class="muted">${esc(reward.description)}</p>` : ""}</div><span class="badge">${reward.reward_stars ? `★ ${reward.reward_stars}` : ""}${reward.reward_stars && reward.premium_days ? " · " : ""}${reward.premium_days ? `Premium ${reward.premium_days} дн.` : ""}</span></div><b class="activity-reward__label">${reward.claimed ? "Условия выполнены" : "Нужно выполнить"}</b>${activityCriteriaHtml(reward.criteria, reward.progress)}<button class="button primary small" data-claim-activity-reward="${esc(reward.id)}" ${reward.claimed || !reward.available ? "disabled" : ""}>${reward.claimed ? "Награда получена" : reward.available ? "Получить" : "Условия не выполнены"}</button></article>`;
  box.innerHTML = `<div class="panel-title"><div><b>Актуальные акции</b><small>Условия проверяются сервером, каждую награду можно получить только один раз.</small></div></div>${activeRewards.map(rewardCard).join("") || '<div class="card"><p class="muted">Актуальных наград пока нет.</p></div>'}${completedRewards.length ? `<div class="activity-rewards-completed-title"><b>Полученные награды</b><span>${completedRewards.length}</span></div>${completedRewards.map(rewardCard).join("")}` : ""}`;
  box.querySelectorAll("[data-claim-activity-reward]").forEach((button) => button.addEventListener("click", async (event) => {
    try { await api("/api/activity-rewards/claim", { method: "POST", body: { rewardId: event.currentTarget.dataset.claimActivityReward } }); toast("Награда начислена."); await refresh(); }
    catch (error) { toast(error.message, true); }
  }));
}

function renderStarsPanel(box) {
  const transactions = state.starTransactions || [];
  const transactionHtml = transactions.map((item) => {
    const amount = Number(item.amount) || 0;
    const sign = amount > 0 ? "+" : "−";
    return `<div class="star-transaction ${amount > 0 ? "income" : "expense"}"><div><b>${esc(item.description)}</b><span>${starDateFmt(item.created_at)}</span></div><strong><span>${sign} ★</span><span>${Math.abs(amount)}</span></strong></div>`;
  }).join("") || '<p class="muted">Операций пока нет. Здесь появятся полученные и отправленные звёзды, награды и покупки.</p>';
  box.innerHTML = `<div class="panel-title"><b>Звёзды</b></div><div class="card stars-balance"><i class="stars-balance__spark stars-balance__spark--left" aria-hidden="true">✦</i><i class="stars-balance__spark stars-balance__spark--right" aria-hidden="true">★</i><div class="stars-balance__copy"><span>Ваш баланс</span><strong><i aria-hidden="true">★</i>${state.me.stars}</strong><p>Получайте звёзды за активность и награды, отправляйте их другим пользователям и тратьте на премиум.</p></div></div><div class="card"><b>История операций</b><div class="star-transactions">${transactionHtml}</div></div>`;
}

function renderAccountLevelPanel(box) {
  const level = state.accountLevel || { current: { title: "Обычный", description: "Стандартный аккаунт.", limits: {} }, activity: {} };
  const current = level.current;
  const next = level.next;
  const names = { messages: "сообщений", posts: "постов", stories: "сторис", reviews: "отзывов", groups: "групп", communities: "бесед", channels: "каналов" };
  const requirement = (criteria = {}) => Object.entries(criteria).map(([key, value]) => `<li>${Math.min(level.activity[key] || 0, value)} / ${value} ${names[key] || key}</li>`).join("") || "<li>Все условия выполнены</li>";
  const rewardHtml = (reward = {}) => {
    const parts = [];
    if (Number(reward.stars)) parts.push(`★ ${Number(reward.stars)}`);
    if (Number(reward.premiumDays)) parts.push(`Premium ${Number(reward.premiumDays)} дн.`);
    return parts.join(" · ") || "Награда не предусмотрена";
  };
  const limitsHtml = (limits = {}) => `<ul class="level-limits__list">${Object.entries(limits).map(([key, value]) => `<li>${esc(limitLabel(key))}: <b>${esc(value)}</b></li>`).join("") || "<li>Без дополнительных ограничений</li>"}</ul>`;
  const limitsButton = (limits, label) => `<button class="button small level-limits__toggle" type="button" data-toggle-level-limits aria-expanded="false">${label}</button><div class="level-limits" hidden>${limitsHtml(limits)}</div>`;
  const limits = level.limits || current.limits || {};
  const levelCards = (level.levels || [current]).map((item) => {
    const reward = item.reward || {};
    const isNext = item.id === next?.id;
    const purchase = item.starsPrice > 0 && !item.unlocked ? `<button class="button small" data-buy-level="${esc(item.id)}" ${item.id !== next?.id ? "disabled" : ""}>Купить за ★ ${item.starsPrice}</button>` : "";
    const claim = (Number(reward.stars) || Number(reward.premiumDays)) && item.unlocked ? `<button class="button primary small" data-claim-level="${esc(item.id)}" ${item.rewardClaimed ? "disabled" : ""}>${item.rewardClaimed ? "Награда получена" : `Забрать: ★ ${reward.stars || 0}${reward.premiumDays ? ` + Premium ${reward.premiumDays} дн.` : ""}`}</button>` : "";
    return `<article class="card level-card${item.id === current.id ? " level-card--current" : ""}"><span class="badge">${item.id === current.id ? "Текущий" : item.unlocked ? "Открыт" : "Следующий уровень"}</span><h2>${esc(item.title)}</h2><p class="muted">${esc(item.description || "")}</p>${isNext ? `<div class="level-next-reward"><b>Награда за следующий уровень</b><span>${rewardHtml(reward)}</span></div>` : ""}${!item.unlocked ? `<b>Нужно выполнить</b><ul>${requirement(item.criteria)}</ul>` : ""}${isNext ? limitsButton(item.limits, "Показать лимиты уровня") : ""}${purchase}${claim}</article>`;
  }).join("");
  box.innerHTML = `<div class="panel-title"><b>Уровень аккаунта</b></div><div class="card level-current-limits"><span class="badge">Действующие лимиты</span><p class="muted">Ограничения, доступные вам сейчас.</p>${limitsButton(limits, "Показать действующие лимиты")}</div>${levelCards}`;
  box.querySelectorAll("[data-claim-level]").forEach((button) => button.addEventListener("click", async (event) => { try { await api("/api/account-level/claim", { method: "POST", body: { levelId: event.currentTarget.dataset.claimLevel } }); toast("Награда за уровень получена."); await refresh(); } catch (error) { toast(error.message, true); } }));
  box.querySelectorAll("[data-buy-level]").forEach((button) => button.addEventListener("click", async (event) => { try { await api("/api/account-level/buy", { method: "POST", body: { levelId: event.currentTarget.dataset.buyLevel } }); toast("Уровень куплен."); await refresh(); } catch (error) { toast(error.message, true); } }));
  box.querySelectorAll("[data-toggle-level-limits]").forEach((button) => button.addEventListener("click", () => {
    const details = button.nextElementSibling;
    const expanded = button.getAttribute("aria-expanded") === "true";
    button.setAttribute("aria-expanded", String(!expanded));
    button.textContent = expanded ? button.textContent.replace("Скрыть", "Показать") : button.textContent.replace("Показать", "Скрыть");
    details.hidden = expanded;
  }));
}

function renderSettingsPanel(box, section = "general") {
  if (section === "wallpapers") return renderWallpaperSettings(box);
  const hidden = new Set(state.me.hiddenStatusIds || []);
  const hiddenStoryAuthors = new Set(state.me.hiddenStoryAuthorIds || []);
  const storyHiddenFrom = new Set(state.me.storyHiddenFromIds || []);
  const hiddenStoryAuthorUsers = state.users.filter((user) => hiddenStoryAuthors.has(user.id));
  const storyHiddenFromUsers = state.users.filter((user) => storyHiddenFrom.has(user.id));
  box.innerHTML = `
    <div class="panel-title"><b>Настройки</b></div>
    <form class="card form" id="accountSettingsForm"><label>Username<input name="username" value="${esc(state.me.username)}" maxlength="20" autocomplete="username"></label><p class="muted">Используйте от 3 до 20 латинских символов, цифр или подчёркиваний.</p><button class="button primary">Сохранить username</button><button class="button danger" type="button" data-logout>Выйти из аккаунта</button></form>
    <form class="card form" id="privacySettingsForm"><b>Приватность</b><label>Кто может добавлять меня в группы<select name="groupInvitePrivacy"><option value="everyone" ${state.me.groupInvitePrivacy === "everyone" ? "selected" : ""}>Все</option><option value="contacts" ${state.me.groupInvitePrivacy !== "everyone" && state.me.groupInvitePrivacy !== "nobody" ? "selected" : ""}>Только те, с кем есть личный диалог</option><option value="nobody" ${state.me.groupInvitePrivacy === "nobody" ? "selected" : ""}>Никто</option></select></label><button class="button small" type="submit">Сохранить приватность</button></form>
    <section class="settings-cards" aria-label="Разделы настроек">
      <button class="settings-card settings-card--dialogs" type="button" data-settings-section="wallpapers"><span class="settings-card__art" aria-hidden="true"><i></i><i></i><i></i></span><span><b>Оформление диалогов</b><small>Тема, панели, сообщения и фоны</small></span><em>›</em></button>
      <button class="settings-card settings-card--archive" type="button" data-open-archive><span class="settings-card__art" aria-hidden="true"><i></i><i></i></span><span><b>Архив чатов</b><small>В архиве: ${visibleChats(true).length}</small></span><em>›</em></button>
    </section>
    <form class="card form" id="statusSettingsForm"><b>Мои статусы</b>${myStatuses().map((status) => `<label><input type="checkbox" data-hide-status="${status.id}" ${hidden.has(status.id) ? "checked" : ""}> Скрыть ${esc(status.icon)} ${esc(status.title)}</label>`).join("") || '<p class="muted">Статусов пока нет.</p>'}<button class="button small" type="submit">Сохранить видимость статусов</button></form>
    <section class="card story-privacy-card">
      <b>Приватность сторис</b>
      <p class="muted">Скрывайте чужие сторис из ленты или запретите выбранным людям смотреть ваши истории.</p>
      <label>Найти пользователя<input data-story-privacy-search placeholder="Имя или username"></label>
      <div class="story-privacy-results" data-story-privacy-results></div>
      <div class="story-privacy-lists">
        <div><b>Вы скрыли сторис</b>${hiddenStoryAuthorUsers.map((user) => `<button class="row" type="button" data-unhide-story-author="${user.id}">${avatarHtml(user)}<span>${esc(user.name)}<small>@${esc(user.username)}</small></span><em>Вернуть</em></button>`).join("") || '<p class="muted">Список пуст.</p>'}</div>
        <div><b>Ваши сторис скрыты от</b>${storyHiddenFromUsers.map((user) => `<button class="row" type="button" data-unhide-story-from="${user.id}">${avatarHtml(user)}<span>${esc(user.name)}<small>@${esc(user.username)}</small></span><em>Разрешить</em></button>`).join("") || '<p class="muted">Список пуст.</p>'}</div>
      </div>
    </section>
    <div class="card"><b>Премиум</b><p class="muted">Цена: ★ ${state.settings.premium?.starsPrice || 250} или ${state.settings.premium?.moneyPriceLabel || "оплата"}</p><button class="button primary small" data-buy-premium="stars">Купить за звёзды</button> <button class="button small" data-buy-premium="money">Купить за деньги (демо)</button></div>`;
  box.querySelector("#accountSettingsForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await api("/api/username", { method: "POST", body: { username: form.get("username") } });
    toast("Username изменён.");
    await refresh();
  });
  box.querySelector("[data-logout]").addEventListener("click", logout);
  box.querySelectorAll("[data-settings-section]").forEach((button) => button.addEventListener("click", (event) => { settingsSection = event.currentTarget.dataset.settingsSection; renderSettingsPanel(box, settingsSection); }));
  box.querySelector("[data-open-archive]").addEventListener("click", () => { activeSection = "archive"; renderApp(); });
  box.querySelector("#privacySettingsForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await api("/api/preferences", { method: "POST", body: preferencePayload({ groupInvitePrivacy: form.get("groupInvitePrivacy") }) });
    toast("Приватность сохранена.");
    await refresh();
  });
  box.querySelector("#statusSettingsForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const hiddenStatusIds = [...box.querySelectorAll("[data-hide-status]:checked")].map((input) => input.dataset.hideStatus);
    await api("/api/preferences", { method: "POST", body: preferencePayload({ hiddenStatusIds }) });
    toast("Видимость статусов сохранена.");
    await refresh();
  });
  const renderStoryPrivacyResults = () => {
    const query = (box.querySelector("[data-story-privacy-search]")?.value || "").trim().toLowerCase().replace("@", "");
    const results = query.length < 2 ? [] : state.users.filter((user) => user.id !== state.me.id && (`${user.name} ${user.username}`).toLowerCase().includes(query)).slice(0, 8);
    box.querySelector("[data-story-privacy-results]").innerHTML = results.map((user) => `<div class="story-privacy-result">${avatarHtml(user)}<span><b>${esc(user.name)}</b><small>@${esc(user.username)}</small></span><button class="button small" type="button" data-hide-story-author="${user.id}">${hiddenStoryAuthors.has(user.id) ? "Скрыто" : "Не видеть"}</button><button class="button small" type="button" data-hide-story-from="${user.id}">${storyHiddenFrom.has(user.id) ? "Уже скрыт" : "Скрыть мои"}</button></div>`).join("") || (query.length >= 2 ? '<p class="muted">Пользователь не найден.</p>' : '<p class="muted">Введите минимум 2 символа.</p>');
    box.querySelectorAll("[data-hide-story-author]").forEach((btn) => btn.addEventListener("click", () => setStoryAuthorHidden(btn.dataset.hideStoryAuthor, true)));
    box.querySelectorAll("[data-hide-story-from]").forEach((btn) => btn.addEventListener("click", () => setStoryPrivacyHidden(btn.dataset.hideStoryFrom, true)));
  };
  box.querySelector("[data-story-privacy-search]").addEventListener("input", renderStoryPrivacyResults);
  renderStoryPrivacyResults();
  box.querySelectorAll("[data-unhide-story-author]").forEach((btn) => btn.addEventListener("click", () => setStoryAuthorHidden(btn.dataset.unhideStoryAuthor, false)));
  box.querySelectorAll("[data-unhide-story-from]").forEach((btn) => btn.addEventListener("click", () => setStoryPrivacyHidden(btn.dataset.unhideStoryFrom, false)));
  box.querySelectorAll("[data-buy-premium]").forEach((btn) => btn.addEventListener("click", async () => {
    try { await api("/api/buy-premium", { method: "POST", body: { method: btn.dataset.buyPremium } }); toast("Премиум активирован."); await refresh(); }
    catch (error) { toast(error.message, true); }
  }));
}

function preferencePayload(overrides = {}) {
  return {
    theme: state.me.theme || "light",
    siteColor: state.me.siteColor || "#2aabee",
    siteBackground: state.me.siteBackground || "default",
    siteBackgroundData: state.me.siteBackgroundData || "",
    dialogColor: state.me.dialogColor || "#ffffff",
    otherDialogColor: state.me.otherDialogColor || "#ffffff",
    dialogPanelColor: state.me.dialogPanelColor || "#f4f8fc",
    dialogPanelStyle: state.me.dialogPanelStyle || "custom",
    dialogBubbleStyle: "custom",
    dialogFont: state.me.dialogFont || "business",
    chatBackground: state.me.chatBackground || "default",
    chatBackgroundData: state.me.chatBackgroundData || "",
    sidebarBackgroundData: state.me.sidebarBackgroundData || "",
    nightAppearanceCustom: Boolean(state.me.nightAppearanceCustom),
    nightOutlineColor: state.me.nightOutlineColor || defaultNightAppearance().outlineColor,
    nightGlowColor: state.me.nightGlowColor || defaultNightAppearance().glowColor,
    nightGlowIntensity: state.me.nightGlowIntensity ?? defaultNightAppearance().glowIntensity,
    hiddenStatusIds: state.me.hiddenStatusIds || [],
    groupInvitePrivacy: state.me.groupInvitePrivacy || "contacts",
    ...overrides,
  };
}

function renderWallpaperSettings(box) {
  const currentWallpaper = state.me.chatBackground || "default";
  const currentFont = state.me.dialogFont || "business";
  const bubbleColor = state.me.dialogColor || "#ffffff";
  const otherBubbleColor = state.me.otherDialogColor || "#ffffff";
  const bubbleText = dialogBubbleTextColor(bubbleColor);
  const otherBubbleText = dialogBubbleTextColor(otherBubbleColor);
  const adminNightAppearance = defaultNightAppearance();
  const personalNightAppearance = effectiveNightAppearance();
  const usesPersonalNightAppearance = Boolean(state.me.nightAppearanceCustom);
  box.innerHTML = `<div class="panel-title"><b>Оформление диалогов</b></div><form class="card form" id="wallpaperSettingsForm"><div class="dialog-color-controls"><label class="dialog-color-control">Цвет моих сообщений<input name="dialogColor" type="color" value="${esc(bubbleColor)}"><button class="dialog-color-control__button" type="button" data-open-dialog-color aria-label="Выбрать цвет моих сообщений"><span class="dialog-color-control__dot" data-dialog-color-dot style="--dialog-color: ${esc(bubbleColor)}"></span><span>Выбрать цвет</span></button></label><label class="dialog-color-control">Цвет сообщений собеседника<input name="otherDialogColor" type="color" value="${esc(otherBubbleColor)}"><button class="dialog-color-control__button" type="button" data-open-other-dialog-color aria-label="Выбрать цвет сообщений собеседника"><span class="dialog-color-control__dot" data-other-dialog-color-dot style="--dialog-color: ${esc(otherBubbleColor)}"></span><span>Выбрать цвет</span></button></label></div><label>Шрифт сообщений<select name="dialogFont">${DIALOG_FONTS.map((font) => `<option value="${font.id}" ${currentFont === font.id ? "selected" : ""}>${font.title}</option>`).join("")}</select></label><fieldset class="wallpaper-picker"><legend>Обои диалога</legend><p class="muted">Все варианты совпадают с палитрой оформления сайта. Нажмите на вариант — демо изменится сразу.</p><section class="wallpaper-chat-preview ${currentWallpaper === "custom" ? "chat-background-custom" : `chat-background-${currentWallpaper}`}" data-wallpaper-chat-preview style="--preview-own-bubble: ${bubbleColor}; --preview-own-text: ${bubbleText}; --preview-other-bubble: ${otherBubbleColor}; --preview-other-text: ${otherBubbleText}${currentWallpaper === "custom" && state.me.chatBackgroundData ? `; background-image: linear-gradient(rgba(255,255,255,.12), rgba(255,255,255,.12)), url('${esc(state.me.chatBackgroundData)}')` : ""}"><header><span class="wallpaper-preview-avatar">А</span><span><b>Алексей</b><small>в сети</small></span></header><div class="wallpaper-preview-messages"><p class="wallpaper-preview-message">Привет! Как тебе новые обои?</p><p class="wallpaper-preview-message own" data-dialog-font-preview style="font-family: ${dialogMessageFont(currentFont)}">Очень красиво, выбираю этот вариант ✨</p><p class="wallpaper-preview-message">Так будет выглядеть ваш диалог.</p></div></section><div class="wallpaper-grid">${CHAT_WALLPAPERS.map((wallpaper) => `<label class="wallpaper-option${currentWallpaper === wallpaper.id ? " selected" : ""}"><input type="radio" name="chatBackground" value="${wallpaper.id}" ${currentWallpaper === wallpaper.id ? "checked" : ""}><span class="wallpaper-preview chat-background-${wallpaper.id}" aria-hidden="true"></span><span><b>${esc(wallpaper.title)}</b><small>${esc(wallpaper.description)}</small></span></label>`).join("")}</div></fieldset><label>Своя картинка<input name="chatBackgroundImage" type="file" accept="image/png,image/jpeg,image/webp"></label><p class="muted">Загруженная картинка заменит выбранный вариант. Для чёткости на большом экране выбирайте изображение от 1920 px по ширине.</p><button class="button primary">Сохранить оформление</button></form>`;
  const form = box.querySelector("#wallpaperSettingsForm");
  box.querySelector(".panel-title").insertAdjacentHTML("afterbegin", '<button class="settings-back" type="button" data-settings-back aria-label="Вернуться к настройкам">‹</button>');
  box.querySelector("[data-settings-back]").addEventListener("click", () => { settingsSection = "general"; renderSettingsPanel(box, settingsSection); });
  form.insertAdjacentHTML("afterbegin", `<fieldset class="dialog-theme-picker"><legend>Режим</legend><div class="theme-mode-options"><label><input type="radio" name="theme" value="light" ${state.me.theme !== "dark" ? "checked" : ""}><span class="theme-mode-option theme-mode-option--light"><i>☀</i><b>Дневной</b><small>Светлый интерфейс</small></span></label><label><input type="radio" name="theme" value="dark" ${state.me.theme === "dark" ? "checked" : ""}><span class="theme-mode-option theme-mode-option--dark"><i>☾</i><b>Ночной</b><small>Мягкий тёмный интерфейс</small></span></label></div></fieldset>`);
  const dialogColorControls = form.querySelector(".dialog-color-controls");
  form.querySelector(".dialog-theme-picker").insertAdjacentHTML("afterend", `<fieldset class="night-appearance-picker"><legend>Подсветка ночного режима</legend><p class="muted">Цвет обводок и мягкого свечения для кнопок, полей и меню. В дневном режиме не применяется.</p><label class="night-appearance-toggle"><input name="nightAppearanceCustom" type="checkbox" ${usesPersonalNightAppearance ? "checked" : ""}> Использовать мои цвета вместо настроек администратора</label><div class="dialog-color-controls"><label class="dialog-color-control">Цвет обводок<input name="nightOutlineColor" type="color" value="${esc(personalNightAppearance.outlineColor)}"><button class="dialog-color-control__button" type="button" data-open-night-outline-color aria-label="Выбрать цвет обводок"><span class="dialog-color-control__dot" data-night-outline-color-dot style="--dialog-color: ${esc(personalNightAppearance.outlineColor)}"></span><span>Выбрать цвет</span></button></label><label class="dialog-color-control">Цвет свечения<input name="nightGlowColor" type="color" value="${esc(personalNightAppearance.glowColor)}"><button class="dialog-color-control__button" type="button" data-open-night-glow-color aria-label="Выбрать цвет свечения"><span class="dialog-color-control__dot" data-night-glow-color-dot style="--dialog-color: ${esc(personalNightAppearance.glowColor)}"></span><span>Выбрать цвет</span></button></label></div><label class="night-glow-intensity">Яркость свечения <output data-night-glow-intensity-output>${personalNightAppearance.glowIntensity}%</output><input name="nightGlowIntensity" type="range" min="0" max="100" step="1" value="${personalNightAppearance.glowIntensity}"></label><small class="muted" data-night-appearance-defaults>По умолчанию администратора: обводки ${esc(adminNightAppearance.outlineColor)}, свечение ${esc(adminNightAppearance.glowColor)}, ${adminNightAppearance.glowIntensity}%.</small></fieldset>`);
  const wallpaperPreview = box.querySelector("[data-wallpaper-chat-preview]");
  const colorDot = box.querySelector("[data-dialog-color-dot]");
  const otherColorDot = box.querySelector("[data-other-dialog-color-dot]");
  const nightOutlineDot = box.querySelector("[data-night-outline-color-dot]");
  const nightGlowDot = box.querySelector("[data-night-glow-color-dot]");
  const nightGlowIntensityOutput = box.querySelector("[data-night-glow-intensity-output]");
  const fontPreview = box.querySelector("[data-dialog-font-preview]");
  const previewWallpaper = (background, image = "") => {
    if (!wallpaperPreview) return;
    wallpaperPreview.className = `wallpaper-chat-preview ${background === "custom" ? "chat-background-custom" : `chat-background-${background}`}`;
    wallpaperPreview.style.backgroundImage = image ? `linear-gradient(rgba(255,255,255,.12), rgba(255,255,255,.12)), url('${image}')` : "";
    wallpaperPreview.classList.remove("is-wallpaper-preview-animating");
    void wallpaperPreview.offsetWidth;
    wallpaperPreview.classList.add("is-wallpaper-preview-animating");
  };
  form.querySelectorAll('[name="chatBackground"]').forEach((input) => input.addEventListener("change", () => {
    form.querySelectorAll(".wallpaper-option").forEach((option) => option.classList.toggle("selected", option.querySelector("input").checked));
    previewWallpaper(input.value);
  }));
  const updateBubblePreview = () => {
    if (!wallpaperPreview) return;
    wallpaperPreview.style.setProperty("--preview-own-bubble", form.elements.dialogColor.value);
    wallpaperPreview.style.setProperty("--preview-own-text", dialogBubbleTextColor(form.elements.dialogColor.value));
    wallpaperPreview.style.setProperty("--preview-other-bubble", form.elements.otherDialogColor.value);
    wallpaperPreview.style.setProperty("--preview-other-text", dialogBubbleTextColor(form.elements.otherDialogColor.value));
    colorDot?.style.setProperty("--dialog-color", form.elements.dialogColor.value);
    otherColorDot?.style.setProperty("--dialog-color", form.elements.otherDialogColor.value);
  };
  form.elements.dialogColor.addEventListener("input", updateBubblePreview);
  form.elements.otherDialogColor.addEventListener("input", updateBubblePreview);
  box.querySelector("[data-open-dialog-color]")?.addEventListener("click", () => form.elements.dialogColor.click());
  box.querySelector("[data-open-other-dialog-color]")?.addEventListener("click", () => form.elements.otherDialogColor.click());
  const updateNightAppearancePreview = () => {
    nightOutlineDot?.style.setProperty("--dialog-color", form.elements.nightOutlineColor.value);
    nightGlowDot?.style.setProperty("--dialog-color", form.elements.nightGlowColor.value);
    if (nightGlowIntensityOutput) nightGlowIntensityOutput.value = `${form.elements.nightGlowIntensity.value}%`;
  };
  const syncNightAppearanceControls = () => {
    const disabled = !form.elements.nightAppearanceCustom.checked;
    form.querySelectorAll("[data-open-night-outline-color], [data-open-night-glow-color]").forEach((button) => { button.disabled = disabled; });
    form.elements.nightGlowIntensity.disabled = disabled;
    form.querySelector(".night-appearance-picker").classList.toggle("uses-admin-defaults", disabled);
  };
  box.querySelector("[data-open-night-outline-color]")?.addEventListener("click", () => form.elements.nightOutlineColor.click());
  box.querySelector("[data-open-night-glow-color]")?.addEventListener("click", () => form.elements.nightGlowColor.click());
  form.elements.nightOutlineColor.addEventListener("input", updateNightAppearancePreview);
  form.elements.nightGlowColor.addEventListener("input", updateNightAppearancePreview);
  form.elements.nightGlowIntensity.addEventListener("input", updateNightAppearancePreview);
  form.elements.nightAppearanceCustom.addEventListener("change", syncNightAppearanceControls);
  updateNightAppearancePreview();
  syncNightAppearanceControls();
  form.elements.dialogFont?.addEventListener("change", () => { if (fontPreview) fontPreview.style.fontFamily = dialogMessageFont(form.elements.dialogFont.value); });
  form.elements.chatBackgroundImage.addEventListener("change", (event) => {
    const image = event.currentTarget.files?.[0];
    if (!image) return;
    const reader = new FileReader();
    reader.onload = () => previewWallpaper("custom", reader.result);
    reader.readAsDataURL(image);
  });
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const values = new FormData(form);
    const theme = values.get("theme") === "dark" ? "dark" : "light";
    const image = values.get("chatBackgroundImage");
    const chatBackground = image?.size ? "custom" : values.get("chatBackground") || "default";
    const chatBackgroundData = image?.size ? await fileToDataUrl(image, 2_500_000) : chatBackground === "custom" ? state.me.chatBackgroundData || "" : "";
    await api("/api/preferences", { method: "POST", body: preferencePayload({ theme, dialogColor: values.get("dialogColor"), otherDialogColor: values.get("otherDialogColor"), dialogBubbleStyle: "custom", dialogFont: values.get("dialogFont"), chatBackground, chatBackgroundData, nightAppearanceCustom: values.get("nightAppearanceCustom") === "on", nightOutlineColor: values.get("nightOutlineColor"), nightGlowColor: values.get("nightGlowColor"), nightGlowIntensity: Number(values.get("nightGlowIntensity")) }) });
    state.me.theme = theme;
    document.body.classList.toggle("theme-dark", theme === "dark");
    toast("Оформление диалогов сохранено.");
    await refresh();
  });
}

function logout() {
  if (!window.confirm("Выйти из аккаунта? Он останется в списке сохранённых аккаунтов.")) return;
  finishCall();
  token = "";
  localStorage.removeItem(TOKEN_KEY);
  clearInterval(callPollTimer);
  renderAuth();
}

function colorToRgb(hex) {
  const value = String(hex || "#2aabee").replace("#", "");
  const number = Number.parseInt(value, 16);
  return `${(number >> 16) & 255}, ${(number >> 8) & 255}, ${number & 255}`;
}

function defaultNightAppearance() {
  const configured = state?.settings?.ui_appearance || {};
  const validColor = (value, fallback) => /^#[0-9a-f]{6}$/i.test(String(value || "")) ? value : fallback;
  const intensity = Number(configured.glowIntensity);
  return {
    outlineColor: validColor(configured.outlineColor, "#65ddf8"),
    glowColor: validColor(configured.glowColor, "#21d5f0"),
    glowIntensity: Number.isFinite(intensity) ? Math.max(0, Math.min(100, Math.round(intensity))) : 35,
  };
}

function effectiveNightAppearance() {
  const defaults = defaultNightAppearance();
  if (!state?.me?.nightAppearanceCustom) return defaults;
  const validColor = (value, fallback) => /^#[0-9a-f]{6}$/i.test(String(value || "")) ? value : fallback;
  const intensity = Number(state.me.nightGlowIntensity);
  return {
    outlineColor: validColor(state.me.nightOutlineColor, defaults.outlineColor),
    glowColor: validColor(state.me.nightGlowColor, defaults.glowColor),
    glowIntensity: Number.isFinite(intensity) ? Math.max(0, Math.min(100, Math.round(intensity))) : defaults.glowIntensity,
  };
}

function sameNightAppearance(first, second) {
  return first.outlineColor.toLowerCase() === second.outlineColor
    && first.glowColor.toLowerCase() === second.glowColor
    && first.glowIntensity === second.glowIntensity;
}

function colorShade(hex, amount) {
  const value = String(hex || "#2aabee").replace("#", "");
  const channels = [0, 2, 4].map((offset) => Math.max(0, Math.min(255, Number.parseInt(value.slice(offset, offset + 2), 16) + amount)));
  return `#${channels.map((channel) => channel.toString(16).padStart(2, "0")).join("")}`;
}

function renderChat() {
  const panel = app.querySelector("#chatPanel");
  const previousMessages = panel.querySelector("#messages");
  const previousScrollTop = previousMessages?.scrollTop || 0;
  const previousDistanceToBottom = previousMessages
    ? previousMessages.scrollHeight - previousMessages.scrollTop - previousMessages.clientHeight
    : 0;
  const shouldScrollToLatest = scrollChatToLatest || !previousMessages || previousDistanceToBottom < 160;
  scrollChatToLatest = false;
  const chat = state.chats.find((item) => item.id === activeChatId);
  if (!chat) {
    const welcomeBrandLetters = ["C", "h", "a", "t", "‑", "P", "r", "o"].map((letter, index) => `<span aria-hidden="true" style="--letter-delay: ${index * 65}ms">${letter}</span>`).join("");
    panel.innerHTML = `<div class="empty"><section class="empty__card"><span class="empty__icon empty__icon--welcome" aria-hidden="true"><svg viewBox="0 0 96 96" fill="none"><path d="M18 23.5c0-5.25 4.25-9.5 9.5-9.5h41C73.75 14 78 18.25 78 23.5v26C78 54.75 73.75 59 68.5 59H46L30 75V59h-2.5C22.25 59 18 54.75 18 49.5v-26Z" fill="currentColor" fill-opacity=".16" stroke="currentColor" stroke-width="5" stroke-linejoin="round"/><path d="M34 37h28M34 48h17" stroke="white" stroke-width="5" stroke-linecap="round"/><circle cx="72" cy="72" r="12" fill="#A9F1D6"/><path d="m72 64 2.25 5.75L80 72l-5.75 2.25L72 80l-2.25-5.75L64 72l5.75-2.25L72 64Z" fill="#167FAE"/></svg></span><div class="empty__content"><span class="empty__eyebrow welcome-brand-letters" aria-label="Chat-Pro">${welcomeBrandLetters}</span><h2 class="empty__title-gradient">Добро пожаловать в Чат‑Про</h2><p>Найдите пользователя или откройте каналы.</p><p class="empty__motivation">Проявляйте активность и получайте звёзды!</p><div class="empty__tips"><span>Каналы</span><span>Отзывы</span><span>Звёзды</span></div><p class="empty__campaign">Приглашайте друзей и получайте награды, создавайте беседы, рассказывайте о звёздах приложения в своём канале и получайте бонусы за активность.</p></div></section></div>`;
    return;
  }
  const channelAppearance = chat.type === "channel" ? chat.settings?.appearance : null;
  const appearanceStyle = channelAppearance ? channelAppearanceStyle(channelAppearance) : "";
  panel.className = `chat-panel${channelAppearance ? ` ${chatBackgroundClass({ chatBackground: channelAppearance.wallpaper })} chat-panel--channel-themed` : ""}`;
  panel.style.cssText = appearanceStyle;
  const messages = state.messages.filter((msg) => msg.chatId === chat.id);
  const pendingMessages = [...pendingOutgoingMessages.values()].filter((msg) => msg.chatId === chat.id);
  messages.push(...pendingMessages);
  messages.sort((first, second) => first.createdAt - second.createdAt);
  const firstUnreadMessageId = messages.find((msg) => msg.unread)?.id;
  selectedMessageIds = new Set([...selectedMessageIds].filter((id) => messages.some((message) => message.id === id)));
  const pinnedMessages = messages.filter((msg) => msg.pinned && !msg.pinHidden);
  pinnedMessageIndex = pinnedMessages.length ? pinnedMessageIndex % pinnedMessages.length : 0;
  const activePinnedMessage = pinnedMessages[pinnedMessageIndex];
  const meta = chatMeta(chat);
  const emptyChatNotice = chat.type === "saved"
    ? '<section class="empty-chat-notice"><span class="empty-chat-notice__icon">★</span><div><b>Избранное готово</b><p>Сохраняйте здесь важные заметки, ссылки и файлы — всё останется под рукой.</p></div></section>'
    : `<section class="empty-chat-notice"><span class="empty-chat-notice__icon">✉</span><div><b>Начните диалог</b><p>Пока здесь нет сообщений. Напишите первое сообщение для ${esc(meta.title)}.</p></div></section>`;
  const mediaButton = '<button class="call-button" data-open-chat-media title="Вложения" aria-label="Вложения">▦</button>';
  const callButtons = `${mediaButton}${chat.type === "secret" && chat.ownerId === state.me.id ? '<button class="call-button" data-add-secret-member title="Пригласить участника" aria-label="Пригласить участника">+</button>' : ""}${chat.type === "direct" ? '<button class="call-button" data-call="audio" title="Аудиозвонок" aria-label="Аудиозвонок"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5.1 3.8 8.2 3l1.7 4.2-2 1.8a15.2 15.2 0 0 0 7.1 7.1l1.8-2 4.2 1.7-.8 3.1c-.2.8-1 1.3-1.8 1.2C10.5 19.1 4.9 13.5 3.9 5.6 3.8 4.8 4.3 4 5.1 3.8Z"/></svg></button><button class="call-button" data-call="video" title="Видеозвонок" aria-label="Видеозвонок"><svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="6" width="13" height="12" rx="3"/><path d="m16 10 5-3v10l-5-3Z"/></svg></button>' : ""}`;
  const chatIdentity = chat.type === "direct" && meta.user
    ? `<div class="chat-identity"><button class="chat-profile-avatar" data-open-profile="${meta.user.id}" title="Открыть профиль ${esc(meta.title)}" aria-label="Открыть профиль ${esc(meta.title)}">${avatarHtml(meta.user)}</button><button class="chat-profile-name" data-open-profile="${meta.user.id}" title="Открыть профиль ${esc(meta.title)}"><div class="chat-head__body"><strong>${esc(meta.title)}</strong><span>${esc(meta.subtitle)}</span></div></button></div>`
    : `${meta.user ? avatarHtml(meta.user) : chatAvatarHtml(chat)}<div class="chat-head__body"><strong>${esc(meta.title)}</strong><span>${esc(meta.subtitle)}</span></div>`;
  const canPublish = chat.type !== "channel" || isChannelManagerRole(chatMemberRole(chat.id));
  const showComposer = chat.type !== "channel" || canPublish;
  const channelJoinButton = chat.type === "channel" && !isMember(chat.id) ? '<button class="button small" type="button" data-join-open-channel>Подписаться</button>' : "";
  panel.innerHTML = `
    <header class="chat-head${["group", "community", "channel"].includes(chat.type) ? " chat-head--group" : ""}${chat.type === "channel" ? " chat-head--channel" : ""}${activePinnedMessage && !selectedMessageIds.size ? " chat-head--with-pinned" : ""}"${["group", "community", "channel"].includes(chat.type) ? ` data-open-group-profile="${chat.id}"` : ""}><button class="chat-back-button chat-head-action" type="button" data-back-to-chats title="Вернуться к списку чатов" aria-label="Вернуться к списку чатов">←</button><button class="chat-mobile-menu-button chat-head-action" type="button" data-open-mobile-chat-menu title="Открыть меню" aria-label="Открыть меню"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"/></svg></button>${chatIdentity}${callButtons}${channelJoinButton}${chat.type === "channel" && chat.ownerId !== state.me.id ? `<button class="call-button" type="button" data-report-channel="${chat.id}" aria-label="Пожаловаться на канал">${actionIcon("report")}</button>` : ""}</header>
    ${selectedMessageIds.size ? `<div class="message-selection-toolbar"><b class="message-selection-toolbar__count">Выбрано: ${selectedMessageIds.size}</b><div class="message-selection-toolbar__actions"><button type="button" data-bulk-forward>${actionIcon("forward")}<span>Переслать</span></button><button type="button" data-bulk-confidential>${actionIcon("confidential")}<span>В скрытый чат</span></button><button type="button" data-bulk-delete>${actionIcon("delete")}<span>Удалить</span></button><button type="button" data-bulk-clear>${actionIcon("cancel")}<span>Отмена</span></button></div></div>` : ""}
    <div class="chat-body${activePinnedMessage && !selectedMessageIds.size ? " chat-body--with-pinned" : ""}">
      ${activePinnedMessage && !selectedMessageIds.size ? `<div class="pinned-messages"><button class="pinned-messages__content" type="button" data-scroll-pinned-message="${activePinnedMessage.id}" title="Перейти к закреплённому сообщению"><span class="pinned-messages__label">${pinIcon("pinned-messages__pin-icon")}<span>Закреплённое сообщение${pinnedMessages.length > 1 ? ` · ${pinnedMessageIndex + 1} из ${pinnedMessages.length}` : ""}</span></span><span class="pinned-messages__text">${esc(pinnedMessagePreview(activePinnedMessage))}</span></button>${pinnedMessages.length > 1 ? '<button type="button" class="pinned-messages__next" data-next-pinned-message title="Следующее закреплённое сообщение" aria-label="Следующее закреплённое сообщение">⌄</button>' : ""}<button type="button" class="pinned-messages__menu" data-toggle-pinned-actions title="Действия с закрепом" aria-label="Действия с закрепом">${actionIcon("more")}</button></div>` : ""}
      <div class="scroll-date-bubble hidden" data-scroll-date></div><div class="messages ${channelAppearance ? "" : chatBackgroundClass(state.me)}" id="messages"${channelAppearance ? "" : chatBackgroundStyle(state.me)}>${messages.map((message) => `${message.id === firstUnreadMessageId ? '<div class="unread-divider"><span>Новые сообщения</span></div>' : ""}${messageHtml(message)}`).join("") || emptyChatNotice}</div>
      <button class="jump-to-latest hidden" type="button" data-jump-to-latest title="К последним сообщениям" aria-label="К последним сообщениям">↓</button>
    </div>
    ${showComposer ? `<form class="composer" id="composer">
      <label class="composer-icon attach-button" title="Прикрепить фото, видео или документ"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20.5 11.2 12 19.7a5.3 5.3 0 0 1-7.5-7.5l9-9a3.7 3.7 0 1 1 5.2 5.3l-9.1 9.1a2 2 0 0 1-2.8-2.8l8-8"/></svg><input name="attachment" type="file" accept="image/png,image/jpeg,image/webp,video/mp4,video/webm,video/quicktime,application/pdf,text/plain,.doc,.docx" hidden></label>
      <div class="composer-input"><textarea name="text" placeholder="${chat.type === "channel" ? "Новая публикация" : "Сообщение"}"></textarea><button class="composer-icon composer-icon--emoji" type="button" data-emoji-toggle title="Эмодзи" aria-label="Открыть эмодзи"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3.75a8.25 8.25 0 1 0 8.25 8.25"/><path d="M7.8 13.65c1.12 1.44 2.5 2.1 4.2 2.1s3.08-.66 4.2-2.1M8.75 9.75h.01M14.5 9.75h.01"/><path d="m18.6 3.25.48 1.32 1.32.48-1.32.48-.48 1.32-.48-1.32-1.32-.48 1.32-.48.48-1.32Z"/></svg></button></div>
      <div class="composer-tools">
        <button class="composer-icon" type="button" data-record="circle" title="Записать видеокружок"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="4"/></svg></button>
        <button class="composer-icon" type="button" data-record="voice" title="Записать голосовое сообщение"><svg viewBox="0 0 24 24" aria-hidden="true"><rect x="9" y="3" width="6" height="11" rx="3"/><path d="M6.5 11.5a5.5 5.5 0 0 0 11 0M12 17v4M9 21h6"/></svg></button>
        <button class="composer-icon composer-send" type="submit" title="Отправить" aria-label="Отправить сообщение"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m3.6 10.2 16.3-6.5c.7-.3 1.4.4 1.1 1.1l-6.5 16.3c-.3.8-1.4.8-1.8 0l-2.4-6-6-2.4c-.8-.4-.8-1.5 0-1.8Z"/><path d="m10.3 13.7 4.5-4.5"/></svg></button>
      </div>
      <div class="composer-attachment hidden" data-composer-attachment><span>📎</span><b data-composer-attachment-name></b><button type="button" data-clear-composer-attachment aria-label="Убрать вложение">×</button></div>
      <div class="emoji-panel hidden" data-emoji-panel><div class="emoji-panel__tabs"><button class="emoji-panel__tab active" type="button" data-emoji-tab="recent">Недавние</button><button class="emoji-panel__tab" type="button" data-emoji-tab="all">Все</button></div><div class="emoji-panel__content" data-emoji-content></div></div>
    </form>` : ""}`;
  if (!channelAppearance) panel.style.background = getComputedStyle(panel.querySelector("#messages")).background;
  const chatHead = panel.querySelector(".chat-head");
  if (chatHead) {
    const updateChatHeadSpace = () => panel.style.setProperty("--chat-head-height", `${chatHead.offsetHeight}px`);
    updateChatHeadSpace();
    new ResizeObserver(updateChatHeadSpace).observe(chatHead);
  }
  const composer = panel.querySelector("#composer");
  if (composer) {
  const updateComposerSpace = () => panel.style.setProperty("--composer-height", `${composer.offsetHeight}px`);
  updateComposerSpace();
  new ResizeObserver(updateComposerSpace).observe(composer);
  composer.addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const attachment = form.get("attachment");
    const body = { chatId: chat.id, text: form.get("text") };
    const temporaryId = `pending-${crypto.randomUUID()}`;
    try {
      if (attachment?.size) {
        body.mediaType = attachment.type.startsWith("image/") ? "photo" : attachment.type.startsWith("video/") ? "video" : "document";
        body.mediaData = await fileToDataUrl(attachment, 2_500_000);
        body.fileName = attachment.name;
      }
      const pendingStartedAt = Date.now();
      pendingOutgoingMessages.set(temporaryId, {
        id: temporaryId,
        chatId: chat.id,
        senderId: state.me.id,
        text: body.text,
        mediaType: body.mediaType || null,
        mediaData: body.mediaData || null,
        createdAt: Math.floor(pendingStartedAt / 1000),
        deliveryState: "sending",
      });
      event.currentTarget.reset();
      attachmentNotice.classList.add("hidden");
      updateComposerSpace();
      scrollChatToLatest = true;
      renderChat();
      const response = await api("/api/messages", { method: "POST", body });
      const remainingAnimation = 360 - (Date.now() - pendingStartedAt);
      if (remainingAnimation > 0) await new Promise((resolve) => window.setTimeout(resolve, remainingAnimation));
      pendingOutgoingMessages.delete(temporaryId);
      await refresh(false);
      renderLeft();
      requestAnimationFrame(() => {
        const latestMessages = app.querySelector("#messages");
        latestMessages?.scrollTo({ top: latestMessages.scrollHeight, behavior: "auto" });
      });
      app.querySelector("#composer textarea")?.focus();
      return response;
    } catch (error) {
      const failed = pendingOutgoingMessages.get(temporaryId);
      if (failed) {
        failed.deliveryState = "failed";
        pendingOutgoingMessages.set(temporaryId, failed);
        renderChat();
      }
      toast(error.message, true);
    }
  });
  const attachmentInput = composer.querySelector('input[name="attachment"]');
  const attachmentNotice = composer.querySelector("[data-composer-attachment]");
  const attachmentName = composer.querySelector("[data-composer-attachment-name]");
  attachmentInput.addEventListener("change", () => {
    const file = attachmentInput.files?.[0];
    attachmentNotice.classList.toggle("hidden", !file);
    attachmentName.textContent = file ? `${file.name} · ${Math.ceil(file.size / 1024)} КБ` : "";
    updateComposerSpace();
  });
  composer.querySelector("[data-clear-composer-attachment]").addEventListener("click", () => { attachmentInput.value = ""; attachmentInput.dispatchEvent(new Event("change")); });
  composer.querySelector("textarea").addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); composer.requestSubmit(); }
  });
  panel.querySelector("[data-add-secret-member]")?.addEventListener("click", () => openMemberManager(chat));
  const emojiPanel = panel.querySelector("[data-emoji-panel]");
  const renderEmojiPanel = (tab = "recent") => {
    const emojis = tab === "recent" ? recentEmojis() : EMOJI_SET;
    emojiPanel.querySelectorAll("[data-emoji-tab]").forEach((button) => button.classList.toggle("active", button.dataset.emojiTab === tab));
    emojiPanel.querySelector("[data-emoji-content]").innerHTML = emojis.length
      ? emojis.map((emoji) => `<button type="button" data-insert-emoji="${emoji}">${emoji}</button>`).join("")
      : '<p class="emoji-panel__empty">Здесь появятся эмодзи, которые вы используете.</p>';
    emojiPanel.querySelectorAll("[data-insert-emoji]").forEach((button) => button.addEventListener("click", () => {
      rememberRecentEmoji(button.dataset.insertEmoji);
      insertIntoComposer(button.dataset.insertEmoji);
      if (tab === "recent") renderEmojiPanel("recent");
    }));
  };
  panel.querySelector("[data-emoji-toggle]").addEventListener("click", () => {
    emojiPanel.classList.toggle("hidden");
    if (!emojiPanel.classList.contains("hidden")) renderEmojiPanel("recent");
  });
  emojiPanel.querySelectorAll("[data-emoji-tab]").forEach((button) => button.addEventListener("click", () => renderEmojiPanel(button.dataset.emojiTab)));
  }
  panel.querySelector("[data-join-open-channel]")?.addEventListener("click", async (event) => {
    event.stopPropagation();
    try {
      await api("/api/chats/join", { method: "POST", body: { chatId: chat.id } });
      toast("Вы подписались на канал.");
      await refresh();
    } catch (error) { toast(error.message, true); }
  });
  panel.querySelector("[data-report-channel]")?.addEventListener("click", async (event) => {
    event.stopPropagation();
    try { await reportTarget("channel", event.currentTarget.dataset.reportChannel); } catch (error) { toast(error.message, true); }
  });
  panel.querySelectorAll("[data-open-reacts]").forEach((btn) => btn.addEventListener("click", () => toggleReactionPicker(btn.dataset.openReacts)));
  panel.querySelectorAll("[data-close-reactions]").forEach((btn) => btn.addEventListener("click", () => closeReactionPickers()));
  panel.querySelectorAll("[data-react]").forEach((btn) => btn.addEventListener("click", async () => {
    showMessageReactionBurst(btn.dataset.emoji, btn);
    await api("/api/react", { method: "POST", body: { messageId: btn.dataset.react, emoji: btn.dataset.emoji } });
    await refresh(false);
  }));
  panel.querySelectorAll("[data-open-channel-comments]").forEach((button) => button.addEventListener("click", () => openChannelComments(button.dataset.openChannelComments)));
  panel.querySelectorAll("[data-toggle-rss-post]").forEach((button) => button.addEventListener("click", () => {
    const description = button.previousElementSibling;
    if (!description?.classList.contains("message__rss-description")) return;
    const collapsed = description.classList.toggle("is-collapsed");
    if (collapsed) expandedRssPostIds.delete(button.dataset.toggleRssPost);
    else expandedRssPostIds.add(button.dataset.toggleRssPost);
    button.textContent = collapsed ? "Читать дальше" : "Свернуть";
  }));
  panel.querySelectorAll("[data-delete-source-repost]").forEach((button) => button.addEventListener("click", async () => {
    if (!window.confirm("Удалить этот репост из группы?")) return;
    try { await api("/api/messages/source-delete", { method: "POST", body: { messageId: button.dataset.deleteSourceRepost } }); await refresh(false); }
    catch (error) { toast(error.message, true); }
  }));
  panel.querySelectorAll("[data-pin-message]").forEach((btn) => btn.addEventListener("click", async () => {
    if (btn.dataset.pinned === "true" && !window.confirm("Открепить сообщение для всех участников?")) return;
    try { await api("/api/messages/pin", { method: "POST", body: { messageId: btn.dataset.pinMessage } }); await refresh(false); }
    catch (error) { toast(error.message, true); }
  }));
  panel.querySelectorAll("[data-hide-pinned-message]").forEach((btn) => btn.addEventListener("click", async () => {
    if (!window.confirm("Убрать этот закреп только у вас? Само сообщение останется в переписке.")) return;
    try {
      await api("/api/messages/pin/hide", { method: "POST", body: { messageId: btn.dataset.hidePinnedMessage } });
      toast("Закреп убран у вас.");
      await refresh(false);
    } catch (error) { toast(error.message, true); }
  }));
  panel.querySelectorAll("[data-unpin-pinned-message]").forEach((btn) => btn.addEventListener("click", async () => {
    if (!window.confirm("Открепить это сообщение у всех участников?")) return;
    try {
      await api("/api/messages/pin", { method: "POST", body: { messageId: btn.dataset.unpinPinnedMessage } });
      toast("Сообщение откреплено у всех.");
      await refresh(false);
    } catch (error) { toast(error.message, true); }
  }));
  panel.querySelector("[data-toggle-pinned-actions]")?.addEventListener("click", () => openPinnedActions(activePinnedMessage));
  panel.querySelectorAll("[data-delete-message]").forEach((btn) => btn.addEventListener("click", async () => {
    const scope = btn.dataset.deleteScope;
    const label = scope === "everyone" ? "Удалить сообщение у всех?" : "Скрыть сообщение только у вас?";
    if (!window.confirm(label)) return;
    try {
      await api("/api/messages/delete", { method: "POST", body: { messageId: btn.dataset.deleteMessage, scope } });
      toast(scope === "everyone" ? "Сообщение удалено у всех." : "Сообщение скрыто у вас.");
      await refresh(false);
    } catch (error) { toast(error.message, true); }
  }));
  panel.querySelector("[data-bulk-forward]")?.addEventListener("click", () => openForwardPicker([...selectedMessageIds]));
  panel.querySelector("[data-bulk-confidential]")?.addEventListener("click", () => openConfidentialForwardDialog([...selectedMessageIds]));
  panel.querySelector("[data-bulk-delete]")?.addEventListener("click", () => openSelectedDeleteDialog([...selectedMessageIds]));
  panel.querySelector("[data-bulk-clear]")?.addEventListener("click", () => {
    selectedMessageIds.clear();
    renderChat();
  });
  panel.querySelector("[data-scroll-pinned-message]")?.addEventListener("click", (event) => {
    const pinnedButton = event.currentTarget;
    const message = panel.querySelector(`#message-${pinnedButton.dataset.scrollPinnedMessage}`);
    if (!message) return;
    message.scrollIntoView({ behavior: "smooth", block: "center" });
    message.classList.add("pinned-message-focus");
    window.setTimeout(() => message.classList.remove("pinned-message-focus"), 1200);
    if (pinnedMessages.length > 1) {
      pinnedMessageIndex = (pinnedMessageIndex + 1) % pinnedMessages.length;
      const nextPinnedMessage = pinnedMessages[pinnedMessageIndex];
      pinnedButton.dataset.scrollPinnedMessage = nextPinnedMessage.id;
      pinnedButton.querySelector(".pinned-messages__label span").textContent = `Закреплённое сообщение · ${pinnedMessageIndex + 1} из ${pinnedMessages.length}`;
      pinnedButton.querySelector(".pinned-messages__text").textContent = pinnedMessagePreview(nextPinnedMessage);
      panel.querySelectorAll("[data-hide-pinned-message]").forEach((button) => { button.dataset.hidePinnedMessage = nextPinnedMessage.id; });
      panel.querySelectorAll("[data-unpin-pinned-message]").forEach((button) => { button.dataset.unpinPinnedMessage = nextPinnedMessage.id; });
    }
  });
  panel.querySelector("[data-next-pinned-message]")?.addEventListener("click", () => {
    pinnedMessageIndex = (pinnedMessageIndex + 1) % pinnedMessages.length;
    renderChat();
  });
  panel.querySelectorAll("[data-open-profile]").forEach((btn) => btn.addEventListener("click", () => openProfile(btn.dataset.openProfile)));
  panel.querySelectorAll("[data-open-message-media]").forEach((button) => button.addEventListener("click", () => {
    const source = button.dataset.openMessageMediaSource;
    if (source) {
      openMedia(source, button.dataset.mediaType || "photo");
      return;
    }
    const message = messages.find((item) => item.id === button.dataset.openMessageMedia);
    if (message) openMedia(messageMediaUrl(message), message.mediaType);
  }));
  panel.querySelectorAll("[data-open-circle]").forEach((btn) => btn.addEventListener("click", () => openCircle(btn.dataset.openCircle)));
  const toggleCirclePlayback = (video) => {
    if (!video) return;
    if (video.paused) video.play().catch(() => toast("Не удалось запустить видеокружок.", true));
    else video.pause();
  };
  panel.querySelectorAll("[data-circle-playback]").forEach((btn) => btn.addEventListener("click", () => {
    toggleCirclePlayback(btn.closest(".circle-message")?.querySelector(".message-circle"));
  }));
  const setCircleProgress = (input, value) => {
    const progress = Math.min(100, Math.max(0, Number(value) || 0));
    input.value = String(progress);
    input.style.setProperty("--circle-progress", `${progress}%`);
  };
  panel.querySelectorAll("[data-circle-progress]").forEach((input) => input.addEventListener("input", () => {
    const video = input.closest(".circle-message")?.querySelector(".message-circle");
    setCircleProgress(input, input.value);
    if (video?.duration) video.currentTime = (Number(input.value) / 100) * video.duration;
  }));
  panel.querySelectorAll(".message-circle").forEach((video) => {
    const circle = video.closest(".circle-message");
    const playButton = circle.querySelector("[data-circle-playback]");
    const progress = circle.querySelector("[data-circle-progress]");
    const updatePlayback = () => {
      playButton.textContent = video.paused ? "▶" : "Ⅱ";
      circle.classList.toggle("is-playing", !video.paused);
    };
    video.addEventListener("play", updatePlayback);
    video.addEventListener("pause", updatePlayback);
    video.addEventListener("loadeddata", async () => {
      if (video.dataset.previewReady || !video.paused) return;
      video.dataset.previewReady = "true";
      video.muted = true;
      try {
        await video.play();
        window.setTimeout(() => {
          video.pause();
          video.currentTime = Math.min(.08, Number.isFinite(video.duration) ? video.duration : .08);
          video.muted = false;
        }, 80);
      } catch (_) { video.muted = false; }
    }, { once: true });
    video.addEventListener("click", () => toggleCirclePlayback(video));
    video.addEventListener("timeupdate", () => { if (video.duration) setCircleProgress(progress, (video.currentTime / video.duration) * 100); });
    video.addEventListener("ended", () => { setCircleProgress(progress, 0); updatePlayback(); });
    video.addEventListener("touchstart", () => {
      circle.classList.add("is-touched");
      window.setTimeout(() => circle.classList.remove("is-touched"), 1800);
    }, { passive: true });
  });
  panel.querySelectorAll("[data-voice-playback]").forEach((button) => button.addEventListener("click", async () => {
    const voice = button.closest(".message-voice");
    const audio = voice?.querySelector(".message-audio");
    if (!audio) return;
    if (!audio.paused) {
      audio.pause();
      return;
    }
    audio.muted = false;
    audio.volume = 1;
    try {
      await audio.play();
    } catch (_) {
      audio.load();
      audio.addEventListener("canplay", () => audio.play().catch(() => toast("Не удалось запустить голосовое сообщение. Возможно, старый формат не поддерживается браузером.", true)), { once: true });
    }
  }));
  panel.querySelectorAll(".message-voice").forEach((voice) => {
    const audio = voice.querySelector(".message-audio");
    const button = voice.querySelector("[data-voice-playback]");
    const duration = voice.querySelector("[data-voice-duration]");
    const format = (seconds) => `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, "0")}`;
    const update = () => {
      button.classList.toggle("is-playing", !audio.paused);
      button.setAttribute("aria-label", audio.paused ? "Воспроизвести голосовое" : "Приостановить голосовое");
      voice.classList.toggle("is-playing", !audio.paused);
    };
    audio.addEventListener("loadedmetadata", () => { if (Number.isFinite(audio.duration)) duration.textContent = format(audio.duration); });
    audio.addEventListener("play", update);
    audio.addEventListener("pause", update);
    audio.addEventListener("ended", () => { audio.currentTime = 0; update(); });
    audio.addEventListener("error", () => toast("Не удалось воспроизвести это голосовое. Возможно, его формат не поддерживается браузером.", true));
  });
  panel.querySelectorAll("[data-record]").forEach((btn) => btn.addEventListener("click", () => recordMediaMessage(chat.id, btn.dataset.record)));
  panel.querySelectorAll(".message").forEach((message) => message.addEventListener("click", (event) => {
    if (event.target.closest("button, audio, video, input, label")) return;
    const selectedMessage = messages.find((item) => item.id === message.id.replace("message-", ""));
    if (!selectedMessage || selectedMessage.mediaType === "system") return;
    if (selectedMessageIds.size) {
      if (selectedMessageIds.has(selectedMessage.id)) selectedMessageIds.delete(selectedMessage.id);
      else selectedMessageIds.add(selectedMessage.id);
      renderChat();
      return;
    }
    openMessageMenu(selectedMessage);
  }));
  panel.querySelectorAll("[data-call]").forEach((btn) => btn.addEventListener("click", () => startCall(chat, btn.dataset.call)));
  panel.querySelector("[data-open-chat-media]")?.addEventListener("click", () => openChatMedia(chat));
  panel.querySelector("[data-open-group-profile]")?.addEventListener("click", (event) => {
    if (!event.target.closest("button, input, label")) openGroupProfile(chat);
  });
  panel.querySelectorAll("[data-media-message]").forEach((media) => media.addEventListener("error", () => {
    const message = media.closest(".message");
    if (!message || message.querySelector(".media-error")) return;
    const label = media.dataset.mediaMessage === "voice" ? "Голосовое сообщение" : "Видеокружок";
    const code = media.error?.code;
    const isLegacyWebmVoice = media.dataset.mediaMessage === "voice" && media.dataset.mediaFormat?.includes("webm");
    const details = isLegacyWebmVoice
      ? "Эта старая запись сделана в WebM/Opus, который текущий браузер не поддерживает. Откройте её в Chrome или Firefox."
      : code === 2
        ? "Не удалось получить файл с сервера. Обновите страницу и попробуйте ещё раз."
        : code === 4
          ? "Браузер не смог декодировать запись. Попробуйте открыть её в актуальном Chrome, Safari или Firefox."
          : "Не удалось воспроизвести файл. Обновите страницу и попробуйте ещё раз.";
    message.insertAdjacentHTML("afterbegin", `<p class="media-error">${esc(label)}: ${esc(details)}</p>`);
  }, { once: true }));
  const closeChat = (event) => { event?.stopPropagation(); activeChatId = null; renderApp(); };
  panel.querySelector("[data-close-chat]")?.addEventListener("click", closeChat);
  panel.querySelector("[data-back-to-chats]").addEventListener("click", closeChat);
  panel.querySelector("[data-open-mobile-chat-menu]").addEventListener("click", (event) => {
    event.stopPropagation();
    openMobileChatMenu();
  });
  const messagesBox = panel.querySelector("#messages");
  const jumpToLatest = panel.querySelector("[data-jump-to-latest]");
  const dateBubble = panel.querySelector("[data-scroll-date]");
  const scrollToLatest = () => messagesBox.scrollTo({ top: messagesBox.scrollHeight, behavior: "auto" });
  const updateJumpButton = () => jumpToLatest.classList.toggle("hidden", messagesBox.scrollHeight - messagesBox.scrollTop - messagesBox.clientHeight < 160);
  const updateScrollDate = () => {
    const visible = [...messagesBox.querySelectorAll(".message")].find((message) => message.offsetTop + message.offsetHeight >= messagesBox.scrollTop + 12);
    const item = visible ? messages.find((message) => message.id === visible.id.replace("message-", "")) : messages[0];
    if (!item || !dateBubble) return;
    dateBubble.textContent = dateFmt(item.createdAt || item.created_at);
    dateBubble.classList.remove("hidden");
    clearTimeout(dateBubble._hideTimer);
    dateBubble._hideTimer = setTimeout(() => dateBubble.classList.add("hidden"), 1200);
  };
  messagesBox.addEventListener("scroll", () => { updateJumpButton(); updateScrollDate(); }, { passive: true });
  jumpToLatest.addEventListener("click", (event) => { event.preventDefault(); scrollToLatest(); jumpToLatest.blur(); updateJumpButton(); });
  if (shouldScrollToLatest) {
    scrollToLatest();
    requestAnimationFrame(scrollToLatest);
  }
  else messagesBox.scrollTop = previousScrollTop;
  updateJumpButton();
}

function renderRight() {
  const box = app.querySelector("#rightContent");
  if (!box) return;
  const recommended = state.recommended.map((rec) => state.chats.find((chat) => chat.id === rec.chat_id)).filter(Boolean);
  box.innerHTML = recommended.length
    ? `<div class="card"><b>Рекомендованные группы</b>${recommended.map((chat) => `<button class="row" data-join="${chat.id}"><div class="avatar">${esc(chatIcon(chat))}</div><div class="row__body"><div class="row__title">${esc(chat.title)}</div><div class="row__sub">${chat.subscriberCount} подписчиков</div></div><span class="badge">Вступить</span></button>`).join("")}</div>`
    : "";
  box.querySelectorAll("[data-join]").forEach((btn) => btn.addEventListener("click", async () => { await api("/api/chats/join", { method: "POST", body: { chatId: btn.dataset.join } }); activeChatId = btn.dataset.join; await refresh(); }));
  box.querySelectorAll("[data-open-profile]").forEach((btn) => btn.addEventListener("click", () => openProfile(btn.dataset.openProfile)));
}

function chatRow(chat) {
  const meta = chatMeta(chat);
  const active = chat.id === activeChatId ? " active" : "";
  const unread = Number(chat.unreadCount) || 0;
  const latestMessage = latestChatMessage(chat.id);
  const timestamp = latestMessage ? chatRowTimestamp(latestMessage.createdAt) : "";
  return `<div class="chat-row${active}${unread ? " has-unread" : ""}"><button class="row chat-row__main" data-chat="${chat.id}">${meta.user ? avatarHtml(meta.user) : chatAvatarHtml(chat)}<div class="row__body"><div class="row__title">${chat.pinned ? pinIcon("chat-row__pin-icon") : ""}${esc(meta.title)}</div><div class="row__sub">${esc(chatRowPreview(chat, meta))}</div></div><span class="chat-row__aside">${timestamp ? `<time class="chat-row__time" datetime="${new Date(latestMessage.createdAt * 1000).toISOString()}">${esc(timestamp)}</time>` : ""}${unread ? `<span class="unread-badge" aria-label="${unread} новых сообщений">${unread > 99 ? "99+" : unread}</span>` : ""}</span></button><button class="chat-menu-button" data-chat-menu="${chat.id}" title="Действия с диалогом" aria-label="Действия с диалогом">⋮</button></div>`;
}

function latestChatMessage(chatId) {
  return state.messages.reduce((latest, message) => {
    if (message.chatId !== chatId) return latest;
    return !latest || message.createdAt >= latest.createdAt ? message : latest;
  }, null);
}

function chatRowPreview(chat, meta) {
  const message = latestChatMessage(chat.id);
  if (!message) return meta.subtitle;
  const preview = pinnedMessagePreview(message);
  if (chat.type === "channel" || chat.type === "saved" || message.mediaType === "system") return preview;
  if (chat.type === "direct") return message.senderId === state.me.id ? `Вы: ${preview}` : preview;
  const sender = message.senderId === state.me.id ? "Вы" : userById(message.senderId)?.name || "Участник";
  return `${sender}: ${preview}`;
}

function chatRowTimestamp(timestamp) {
  const date = new Date(timestamp * 1000);
  const today = new Date();
  const dayStart = (value) => new Date(value.getFullYear(), value.getMonth(), value.getDate()).getTime();
  const dayDifference = Math.round((dayStart(today) - dayStart(date)) / 86_400_000);
  if (dayDifference === 0) return timeFmt(timestamp);
  if (dayDifference === 1) return "Вчера";
  if (date.getFullYear() === today.getFullYear()) return new Intl.DateTimeFormat("ru-RU", { day: "2-digit", month: "2-digit" }).format(date);
  return new Intl.DateTimeFormat("ru-RU", { day: "2-digit", month: "2-digit", year: "2-digit" }).format(date);
}

function recommendedChannelRow(chat) {
  return `<article class="recommended-channel"><button class="recommended-channel__info" type="button" data-open-recommended-channel="${esc(chat.id)}">${chatAvatarHtml(chat)}<span><b>${esc(chat.title)}</b><small>${chat.subscriberCount} подписчиков${chat.description ? ` · ${esc(chat.description)}` : ""}</small></span></button><button class="button primary small" type="button" data-join-recommended-channel="${esc(chat.id)}">Подписаться</button></article>`;
}

function secretChatRow(chat) {
  const meta = chatMeta(chat);
  return `<button class="row" data-chat="${chat.id}"><div class="avatar">🔒</div><div class="row__body"><div class="row__title">${esc(meta.title)}</div><div class="row__sub">Скрытый чат</div></div><span class="badge">Открыть</span></button>`;
}

function openSecretChatCreator() {
  const contactIds = new Set(
    state.chats
      .filter((chat) => chat.type === "direct" && isMember(chat.id))
      .flatMap((chat) => state.members.filter((member) => member.chat_id === chat.id && member.user_id !== state.me.id).map((member) => member.user_id)),
  );
  const contacts = state.users.filter((user) => contactIds.has(user.id));
  const overlay = document.createElement("div");
  overlay.className = "member-manager-overlay";
  overlay.innerHTML = `<section class="member-manager secret-chat-creator" role="dialog" aria-modal="true" aria-label="Создание скрытого чата"><header><div><b>Скрытый чат</b><small>Он не появится в общем списке или поиске.</small></div><button class="member-manager__close" type="button" aria-label="Закрыть">×</button></header><form class="form" data-secret-chat-form><label>Название<input name="title" maxlength="80" placeholder="Скрытый чат"></label><label>Пароль из 4 цифр<input name="password" inputmode="numeric" pattern="\\d{4}" minlength="4" maxlength="4" autocomplete="off" required placeholder="0000"></label><fieldset class="secret-chat-members"><legend>Участники</legend><div>${contacts.map((user) => `<label class="secret-chat-member"><input type="checkbox" name="memberIds" value="${user.id}">${avatarHtml(user)}<span><b>${esc(user.name)}</b><small>@${esc(user.username)}</small></span><i aria-hidden="true"></i></label>`).join("") || '<p class="muted">Сначала создайте личный диалог хотя бы с одним пользователем.</p>'}</div></fieldset><button class="button primary" ${contacts.length ? "" : "disabled"}>Создать скрытый чат</button></form></section>`;
  document.body.append(overlay);
  overlay.querySelector(".secret-chat-creator")?.setAttribute("aria-label", "Создание скрытого чата");
  overlay.querySelector(".secret-chat-creator header b").textContent = "Скрытый чат";
  overlay.querySelector(".secret-chat-creator header small").textContent = "Чтобы найти чат по коду, используйте поле ниже.";
  overlay.querySelector('input[name="title"]').placeholder = "Скрытый чат";
  overlay.querySelector('[data-secret-chat-form] .button.primary').textContent = "Создать скрытый чат";
  const searchForm = document.createElement("form");
  searchForm.className = "form secret-chat-search-form";
  searchForm.innerHTML = '<label>Найти чат по коду<input name="password" inputmode="numeric" pattern="\\d{4}" minlength="4" maxlength="4" autocomplete="off" required placeholder="0000"></label><button class="button" type="submit">Найти</button>';
  const searchResults = document.createElement("div");
  searchResults.className = "secret-chat-search-results";
  const divider = document.createElement("div");
  divider.className = "secret-chat-divider";
  divider.innerHTML = "<span>или создайте новый</span>";
  const createForm = overlay.querySelector("[data-secret-chat-form]");
  createForm.before(searchForm, searchResults, divider);
  const close = () => overlay.remove();
  overlay.querySelector(".member-manager__close").addEventListener("click", close);
  overlay.addEventListener("click", (event) => { if (event.target === overlay) close(); });
  searchForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const password = String(new FormData(searchForm).get("password") || "");
    if (!/^\d{4}$/.test(password)) { searchResults.innerHTML = '<p class="muted">Введите код из 4 цифр.</p>'; return; }
    try {
      const data = await api("/api/secret-chats/unlock", { method: "POST", body: { password } });
      await loadState();
      const chats = state.chats.filter((chat) => chat.type === "secret" && data.chatIds.includes(chat.id));
      if (chats.length === 1) {
        activeChatId = chats[0].id;
        scrollChatToLatest = true;
        close();
        renderApp();
        return;
      }
      searchResults.innerHTML = chats.map(secretChatRow).join("");
      bindChatRows(searchResults);
    } catch (error) {
      searchResults.innerHTML = `<p class="muted">${esc(error.message === "Скрытых чатов с таким паролем не найдено." ? "По данному запросу чатов нет." : error.message)}</p>`;
    }
  });
  overlay.querySelector("[data-secret-chat-form]").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const password = String(form.get("password") || "");
    const memberIds = form.getAll("memberIds");
    if (!/^\d{4}$/.test(password)) return toast("Пароль должен состоять ровно из 4 цифр.", true);
    if (!memberIds.length) return toast("Выберите хотя бы одного собеседника.", true);
    try {
      await api("/api/chats", { method: "POST", body: { type: "secret", title: form.get("title"), password, memberIds } });
      close();
      toast("Скрытый чат создан. Найти его можно здесь же, по коду из 4 цифр.");
      await refresh();
    } catch (error) { toast(error.message, true); }
  });
  searchForm.elements.password.focus();
}

function directContacts() {
  const contactIds = new Set(
    state.chats
      .filter((chat) => chat.type === "direct" && isMember(chat.id))
      .flatMap((chat) => state.members.filter((member) => member.chat_id === chat.id && member.user_id !== state.me.id).map((member) => member.user_id)),
  );
  return state.users.filter((user) => contactIds.has(user.id));
}

function userStories(userId) { return (state?.stories || []).filter((story) => story.user_id === userId); }
function hasUnseenStory(userId) { return userId !== state?.me?.id && userStories(userId).some((story) => !story.viewed); }
function firstUserStory(userId) { return userStories(userId)[0]; }
function directStoryStripHtml(className = "direct-stories") {
  const contacts = directContacts().filter((user) => userStories(user.id).length);
  if (!contacts.length) return "";
  return `<section class="stories-strip ${className}${storiesCollapsed ? " is-collapsed" : ""}" aria-label="Истории контактов"><button type="button" class="stories-strip__toggle" data-toggle-stories aria-expanded="${!storiesCollapsed}" aria-label="${storiesCollapsed ? "Показать истории" : "Скрыть истории"}" title="${storiesCollapsed ? "Показать истории" : "Скрыть истории"}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m7 14 5-5 5 5"/></svg></button><div class="stories-strip__items">${contacts.map((user) => { const story = firstUserStory(user.id); return `<button type="button" class="story-avatar${hasUnseenStory(user.id) ? " has-story" : ""}" data-open-story="${story.id}">${avatarHtml(user)}<span>${esc(user.name)}</span></button>`; }).join("")}</div></section>`;
}

function bindStoriesStrip(root) {
  root.querySelector("[data-toggle-stories]")?.addEventListener("click", () => {
    storiesCollapsed = !storiesCollapsed;
    renderChatsList(root);
  });
  root.querySelectorAll("[data-open-story]").forEach((button) => button.addEventListener("click", () => openStory(button.dataset.openStory)));
}

function openSimpleActions(anchor, actions) {
  document.querySelector(".simple-actions-overlay")?.remove();
  const overlay = document.createElement("div");
  overlay.className = "simple-actions-overlay";
  overlay.innerHTML = `<section class="simple-actions">${actions.map((item, index) => `<button type="button" data-action-index="${index}">${esc(item.label)}</button>`).join("")}</section>`;
  document.body.append(overlay);
  const rect = anchor.getBoundingClientRect();
  const menu = overlay.querySelector(".simple-actions");
  menu.style.top = `${Math.min(window.innerHeight - 120, rect.bottom + 8)}px`;
  menu.style.left = `${Math.max(12, Math.min(window.innerWidth - 230, rect.left - 170))}px`;
  const close = () => overlay.remove();
  overlay.addEventListener("click", (event) => { if (event.target === overlay) close(); });
  overlay.querySelectorAll("[data-action-index]").forEach((button) => button.addEventListener("click", async () => {
    close();
    try { await actions[Number(button.dataset.actionIndex)]?.action(); }
    catch (error) { toast(error.message, true); }
  }));
}

async function reportTarget(targetType, targetId) {
  const reason = window.prompt("Опишите причину жалобы", "");
  if (reason === null) return;
  await api("/api/reports", { method: "POST", body: { targetType, targetId, reason } });
  toast("Отправлено на рассмотрение.");
}

function profileMenuActions(profileUser) {
  const actions = [];
  if (profileUser.id !== state.me.id) actions.push({ label: "Пожаловаться на страницу", action: () => reportTarget("profile", profileUser.id) });
  actions.push(
    { label: "Скопировать username", action: () => copyText(`@${profileUser.username}`, "Username скопирован.") },
    { label: "Отправить профиль в чат", action: () => openProfileShareDialog(profileUser) },
  );
  return actions;
}

async function copyText(text, successMessage = "Текст скопирован.") {
  try {
    if (!navigator.clipboard?.writeText) throw new Error("Clipboard API недоступен");
    await navigator.clipboard.writeText(text);
  } catch {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.setAttribute("readonly", "");
    textarea.style.cssText = "position:fixed;opacity:0;pointer-events:none";
    document.body.append(textarea);
    textarea.select();
    const copied = document.execCommand("copy");
    textarea.remove();
    if (!copied) throw new Error("Не удалось скопировать username.");
  }
  toast(successMessage);
}

function openProfileShareDialog(profileUser) {
  const targets = visibleChats(false).filter((chat) => chat.type !== "secret" && (chat.type !== "channel" || isChannelManagerRole(chatMemberRole(chat.id))));
  const overlay = document.createElement("div");
  overlay.className = "member-manager-overlay";
  overlay.innerHTML = `<section class="member-manager" role="dialog" aria-modal="true" aria-label="Отправка профиля"><header><div><b>Отправить профиль</b><small>Выберите чат, в который будет отправлен @${esc(profileUser.username)}</small></div><button class="member-manager__close" type="button" aria-label="Закрыть">×</button></header><div class="member-manager__list">${targets.map((chat) => { const meta = chatMeta(chat); return `<button class="member-manager__user" type="button" data-share-profile-to="${chat.id}">${meta.user ? avatarHtml(meta.user) : `<div class="avatar">${esc(meta.icon)}</div>`}<span><b>${esc(meta.title)}</b><small>${esc(meta.subtitle)}</small></span><em>Отправить</em></button>`; }).join("") || '<p class="muted">Нет доступных чатов для отправки профиля.</p>'}</div></section>`;
  document.body.append(overlay);
  const close = () => overlay.remove();
  overlay.querySelector(".member-manager__close").addEventListener("click", close);
  overlay.addEventListener("click", (event) => { if (event.target === overlay) close(); });
  overlay.querySelectorAll("[data-share-profile-to]").forEach((button) => button.addEventListener("click", async () => {
    try {
      const chatId = button.dataset.shareProfileTo;
      await api("/api/messages", { method: "POST", body: { chatId, profileUserId: profileUser.id } });
      activeSection = "chats";
      activeChatId = chatId;
      scrollChatToLatest = true;
      close();
      await refresh();
      toast("Профиль отправлен.");
    } catch (error) { toast(error.message, true); }
  }));
}

async function shareText(text) {
  if (navigator.share) {
    try { await navigator.share({ text }); return; } catch {}
  }
  await navigator.clipboard?.writeText(text);
  toast("Ссылка/текст скопированы.");
}

async function setStoryAuthorHidden(authorId, hidden) {
  await api("/api/stories/hide-author", { method: "POST", body: { authorId, hidden } });
  toast(hidden ? "Сторис пользователя скрыты." : "Сторис снова будут показываться.");
  await refresh(false);
}

async function setStoryPrivacyHidden(userId, hidden) {
  await api("/api/stories/privacy", { method: "POST", body: { userId, hidden } });
  toast(hidden ? "Пользователь больше не увидит ваши сторис." : "Пользователь снова увидит ваши сторис.");
  await refresh(false);
}

function openChatMedia(chat) {
  const media = state.messages.filter((message) => message.chatId === chat.id && ["photo", "voice", "circle", "document"].includes(message.mediaType));
  const photos = media.filter((message) => message.mediaType === "photo");
  const voices = media.filter((message) => message.mediaType === "voice");
  const circles = media.filter((message) => message.mediaType === "circle");
  const documents = media.filter((message) => message.mediaType === "document");
  const overlay = document.createElement("div");
  overlay.className = "group-card-overlay";
  overlay.innerHTML = `<section class="group-card chat-media-card" role="dialog" aria-modal="true" aria-label="Вложения диалога"><header class="group-card__header"><div><b>Вложения</b><small>Фото, документы, голосовые и кружки</small></div><button type="button" data-close-chat-media aria-label="Закрыть">×</button></header><section class="group-card__section">${photos.length ? `<div class="group-card__photos">${photos.map((message) => `<button type="button" data-chat-photo="${message.id}"><img src="${esc(messageMediaUrl(message))}" alt="Фото"></button>`).join("")}</div>` : ""}${documents.length ? `<div class="group-card__media-list"><b>Документы · ${documents.length}</b>${documents.map((message) => `<a class="document-link" href="${esc(messageMediaUrl(message))}" target="_blank" rel="noopener">📄 ${esc(message.text?.replace(/^Документ:\s*/, "") || "Документ")}</a>`).join("")}</div>` : ""}${voices.length ? `<div class="group-card__media-list"><b>Голосовые · ${voices.length}</b>${voices.map((message) => `<audio controls preload="metadata" src="${esc(messageMediaUrl(message))}"></audio>`).join("")}</div>` : ""}${circles.length ? `<div class="group-card__circles"><b>Кружки · ${circles.length}</b><div>${circles.map((message) => `<button type="button" data-chat-circle="${message.id}"><video muted preload="metadata" src="${esc(messageMediaUrl(message))}"></video><span>▶</span></button>`).join("")}</div></div>` : ""}${!media.length ? '<p class="muted">В этом диалоге пока нет вложений.</p>' : ""}</section></section>`;
  document.body.append(overlay);
  const close = () => overlay.remove();
  overlay.querySelector("[data-close-chat-media]").addEventListener("click", close);
  overlay.addEventListener("click", (event) => { if (event.target === overlay) close(); });
  overlay.querySelectorAll("[data-chat-photo]").forEach((button) => button.addEventListener("click", () => openMedia(messageMediaUrl(state.messages.find((message) => message.id === button.dataset.chatPhoto)))));
  overlay.querySelectorAll("[data-chat-circle]").forEach((button) => button.addEventListener("click", () => { close(); openCircle(button.dataset.chatCircle); }));
}

function openForwardPicker(messageIds) {
  const targets = visibleChats(false).filter((chat) => chat.type !== "secret" && chat.id !== activeChatId);
  const overlay = document.createElement("div");
  overlay.className = "member-manager-overlay";
  overlay.innerHTML = `<section class="member-manager" role="dialog" aria-modal="true" aria-label="Пересылка сообщений"><header><div><b>Переслать сообщения</b><small>Выберите диалог, группу или беседу</small></div><button class="member-manager__close" type="button" aria-label="Закрыть">×</button></header><div class="member-manager__list">${targets.map((chat) => { const meta = chatMeta(chat); return `<button class="member-manager__user" type="button" data-forward-target="${chat.id}">${meta.user ? avatarHtml(meta.user) : `<div class="avatar">${esc(meta.icon)}</div>`}<span><b>${esc(meta.title)}</b><small>${esc(meta.subtitle)}</small></span><em>Переслать</em></button>`; }).join("") || '<p class="muted">Нет другого доступного чата для пересылки.</p>'}</div></section>`;
  document.body.append(overlay);
  const close = () => overlay.remove();
  overlay.querySelector(".member-manager__close").addEventListener("click", close);
  overlay.addEventListener("click", (event) => { if (event.target === overlay) close(); });
  overlay.querySelectorAll("[data-forward-target]").forEach((button) => button.addEventListener("click", async () => {
    const result = await runBulkMessageAction({ action: "forward", messageIds, targetChatId: button.dataset.forwardTarget }, "Сообщения пересланы.");
    if (result) close();
  }));
}

function openConfidentialForwardDialog(messageIds) {
  const overlay = document.createElement("div");
  overlay.className = "member-manager-overlay";
  overlay.innerHTML = `<section class="member-manager secret-chat-creator" role="dialog" aria-modal="true" aria-label="Пересылка в скрытый чат"><header><div><b>В скрытый чат</b><small>Введите код существующего чата. Исходные сообщения останутся в этом диалоге.</small></div><button class="member-manager__close" type="button" aria-label="Закрыть">×</button></header><form class="form" data-confidential-forward-form><label>Код чата<input name="password" inputmode="numeric" pattern="\\d{4}" minlength="4" maxlength="4" autocomplete="off" required placeholder="0000"></label><button class="button primary">Переслать</button></form></section>`;
  document.body.append(overlay);
  const close = () => overlay.remove();
  overlay.querySelector(".member-manager__close").addEventListener("click", close);
  overlay.addEventListener("click", (event) => { if (event.target === overlay) close(); });
  overlay.querySelector("[data-confidential-forward-form]").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const password = String(form.get("password") || "");
    if (!/^\d{4}$/.test(password)) return toast("Пароль должен состоять ровно из 4 цифр.", true);
    const result = await runBulkMessageAction({ action: "forward_confidential", messageIds, password }, "Сообщения пересланы в скрытый чат.");
    if (result) {
      close();
      activeChatId = result.targetChatId;
      scrollChatToLatest = true;
      renderApp();
    }
  });
  overlay.querySelector("input[name=password]").focus();
}

async function runBulkMessageAction(body, successMessage) {
  try {
    const result = await api("/api/messages/bulk", { method: "POST", body });
    selectedMessageIds.clear();
    toast(successMessage);
    await refresh(false);
    return result;
  } catch (error) {
    toast(error.message, true);
    return null;
  }
}

function openPinnedActions(msg) {
  if (!msg) return;
  const canPinForEveryone = canPinMessageForEveryone(msg);
  const overlay = document.createElement("div");
  overlay.className = "message-menu-overlay";
  overlay.innerHTML = `<section class="message-menu message-menu--compact" role="dialog" aria-modal="true" aria-label="Действия с закрепом"><header><div><b>Закреплённое сообщение</b></div><button type="button" data-close-menu aria-label="Закрыть">×</button></header><div class="message-menu__actions"><button type="button" data-pinned-action="hide">${actionIcon("cancel", "message-menu__icon")}<span>Открепить у себя</span></button>${canPinForEveryone ? `<button type="button" class="danger" data-pinned-action="unpin">${pinIcon("message-menu__icon")}<span>Открепить у всех</span></button>` : ""}</div></section>`;
  document.body.append(overlay);
  const close = () => overlay.remove();
  overlay.querySelector("[data-close-menu]").addEventListener("click", close);
  overlay.addEventListener("click", (event) => { if (event.target === overlay) close(); });
  overlay.querySelectorAll("[data-pinned-action]").forEach((button) => button.addEventListener("click", async () => {
    try {
      if (button.dataset.pinnedAction === "hide") {
        if (!window.confirm("Убрать этот закреп только у вас? Само сообщение останется в переписке.")) return;
        await api("/api/messages/pin/hide", { method: "POST", body: { messageId: msg.id } });
        toast("Закреп убран у вас.");
      } else if (canPinForEveryone) {
        if (!window.confirm("Открепить это сообщение у всех участников?")) return;
        await api("/api/messages/pin", { method: "POST", body: { messageId: msg.id } });
        toast("Сообщение откреплено у всех.");
      }
      close();
      await refresh(false);
    } catch (error) { toast(error.message, true); }
  }));
}

function openSelectedDeleteDialog(messageIds) {
  const selected = state.messages.filter((msg) => messageIds.includes(msg.id));
  const ownOnly = selected.length > 0 && selected.every((msg) => canDeleteMessageForEveryone(msg));
  const overlay = document.createElement("div");
  overlay.className = "message-menu-overlay";
  overlay.innerHTML = `<section class="message-menu message-menu--compact" role="dialog" aria-modal="true" aria-label="Удаление выбранных сообщений"><header><div><b>Удалить сообщения</b><small>Выбрано: ${selected.length}</small></div><button type="button" data-close-menu aria-label="Закрыть">×</button></header><div class="message-menu__actions"><button type="button" data-selected-delete="me">${actionIcon("delete", "message-menu__icon")}<span>Удалить у себя</span></button>${ownOnly ? `<button type="button" class="danger" data-selected-delete="everyone">${actionIcon("delete", "message-menu__icon")}<span>Удалить у всех</span></button>` : ""}</div></section>`;
  document.body.append(overlay);
  const close = () => overlay.remove();
  overlay.querySelector("[data-close-menu]").addEventListener("click", close);
  overlay.addEventListener("click", (event) => { if (event.target === overlay) close(); });
  overlay.querySelectorAll("[data-selected-delete]").forEach((button) => button.addEventListener("click", async () => {
    const scope = button.dataset.selectedDelete;
    const label = scope === "everyone" ? "Удалить выбранные сообщения у всех?" : "Скрыть выбранные сообщения только у вас?";
    if (!window.confirm(label)) return;
    const result = await runBulkMessageAction({ action: "delete", messageIds, scope }, scope === "everyone" ? "Сообщения удалены у всех." : "Сообщения скрыты у вас.");
    if (result) close();
  }));
}

function openChatMenu(chatId) {
  const chat = state.chats.find((item) => item.id === chatId);
  if (!chat) return;
  const meta = chatMeta(chat);
  const overlay = document.createElement("div");
  overlay.className = "chat-menu-overlay";
  overlay.innerHTML = `<section class="chat-menu" role="dialog" aria-modal="true" aria-label="Действия с диалогом"><header><div><b>${esc(meta.title)}</b><small>Управление диалогом</small></div><button type="button" data-close-chat-menu aria-label="Закрыть">×</button></header><div class="chat-menu__actions"><button type="button" data-chat-action="pin">${chat.pinned ? "Открепить" : "Закрепить"}</button><button type="button" data-chat-action="archive">${chat.archived ? "Вернуть из архива" : "Архивировать"}</button><button type="button" data-chat-action="delete-me">Удалить у себя</button>${chat.ownerId === state.me.id ? '<button type="button" class="danger" data-chat-action="delete-everyone">Удалить у всех</button>' : ""}</div></section>`;
  document.body.append(overlay);
  const close = () => overlay.remove();
  overlay.querySelector("[data-close-chat-menu]").addEventListener("click", close);
  overlay.addEventListener("click", (event) => { if (event.target === overlay) close(); });
  overlay.querySelectorAll("[data-chat-action]").forEach((button) => button.addEventListener("click", async () => {
    const action = button.dataset.chatAction;
    try {
      if (action === "pin") await api("/api/chats/pin", { method: "POST", body: { chatId } });
      if (action === "archive") await api("/api/chats/archive", { method: "POST", body: { chatId, archived: !chat.archived } });
      if (action === "delete-me") {
        if (!window.confirm(`Удалить «${meta.title}» только у вас?`)) return;
        await api("/api/chats/delete", { method: "POST", body: { chatId, scope: "me" } });
      }
      if (action === "delete-everyone") {
        if (!window.confirm(`Удалить «${meta.title}» у всех участников без возможности восстановления?`)) return;
        await api("/api/chats/delete", { method: "POST", body: { chatId, scope: "everyone" } });
      }
      if (["archive", "delete-me", "delete-everyone"].includes(action) && activeChatId === chatId) activeChatId = null;
      close();
      await refresh();
    } catch (error) { toast(error.message, true); }
  }));
}

function messageHtml(msg) {
  const chat = state.chats.find((item) => item.id === msg.chatId);
  const settings = chat.settings || {};
  if (msg.mediaType === "system") return `<div class="message message--system" id="message-${msg.id}"><span>${esc(msg.text)}</span></div>`;
  const reactions = Object.entries(msg.reactions || {}).filter(([, count]) => Number(count) > 0);
  const reactionHtml = reactions.length ? `<div class="reacts visible-reacts">${reactions.map(([emoji, count]) => `<button data-react="${msg.id}" data-emoji="${esc(emoji)}">${esc(emoji)} ${count}</button>`).join("")}</div>` : "";
  const isCircle = msg.mediaType === "circle";
  const isVoice = msg.mediaType === "voice";
  const isGroup = ["group", "community", "channel"].includes(chat?.type);
  const author = userById(msg.senderId);
  const sharedProfile = msg.profileUserId ? userById(msg.profileUserId) : null;
  const sourceItem = msg.sourceType === "profile-post"
    ? state.posts.find((post) => post.id === msg.sourceId)
    : msg.sourceType === "story"
      ? state.stories.find((story) => story.id === msg.sourceId)
      : null;
  const sourceAuthorId = sourceItem?.user_id;
  const showAuthor = isGroup && msg.senderId !== state.me.id;
  const showInlineDelivery = !msg.mediaType
    && !msg.forwardedFrom
    && !sharedProfile
    && !msg.profileUserId
    && !String(msg.text || "").includes("\n")
    && String(msg.text || "").length <= 52;
  const canDeleteRssPost = msg.sourceType === "rss" && chat?.type === "channel" && isChannelManagerRole(chatMemberRole(msg.chatId));
  const sourcePostActions = canDeleteRssPost
    ? `<div class="group-post-actions"><button type="button" data-delete-message="${msg.id}" data-delete-scope="everyone">Удалить публикацию</button></div>`
    : msg.sourceType && !["telegram", "rss"].includes(msg.sourceType)
      ? `<div class="group-post-actions"><button type="button" data-delete-source-repost="${msg.id}">Удалить репост</button></div>`
      : "";
  const comments = chat?.type === "channel" ? state.channelComments.filter((comment) => comment.message_id === msg.id) : [];
  const commentsHtml = chat?.type === "channel" && settings.commentsEnabled !== false ? `<div class="channel-comments"><button type="button" data-open-channel-comments="${msg.id}" aria-label="Комментарии${comments.length ? `: ${comments.length}` : ""}" title="Комментарии"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5.5 5.5h13a2.5 2.5 0 0 1 2.5 2.5v7a2.5 2.5 0 0 1-2.5 2.5H12l-4.6 3v-3H5.5A2.5 2.5 0 0 1 3 15V8a2.5 2.5 0 0 1 2.5-2.5Z"/><path d="M8 11.5h.01M12 11.5h.01M16 11.5h.01"/></svg>${comments.length ? `<span>${comments.length}</span>` : ""}</button></div>` : "";
  return `<div class="message ${msg.senderId === state.me.id ? "own" : ""}${showAuthor ? " message--with-author" : ""}${msg.pinned ? " pinned" : ""}${isCircle ? " message--circle" : ""}${isVoice ? " message--audio" : ""}${String(msg.id).startsWith("pending-") ? " message--pending" : ""}${msg.deliveryState === "failed" ? " message--failed" : ""}${selectedMessageIds.has(msg.id) ? " selected" : ""}" id="message-${msg.id}">
    ${showAuthor ? `<button class="message__author" type="button" data-open-profile="${msg.senderId}" title="Открыть профиль ${esc(author?.name || "участника")}">${avatarHtml(author, "message__author-avatar")}</button>` : ""}
    <div class="message__content">
      <div class="message__bubble${showInlineDelivery ? " message__bubble--inline-meta" : " message__bubble--with-meta"}">
        ${msg.forwardedFrom ? sourceAuthorId ? `<button type="button" class="message__forwarded message__forwarded--link" data-open-profile="${sourceAuthorId}" title="Открыть профиль автора источника">↪ ${esc(msg.forwardedFrom)}</button>` : `<div class="message__forwarded">↪ ${esc(msg.forwardedFrom)}</div>` : ""}
        ${messageMediaHtml(msg)}
        ${sharedProfile ? `<button type="button" class="shared-profile-card" data-open-profile="${sharedProfile.id}" title="Открыть профиль ${esc(sharedProfile.name)}">${avatarHtml(sharedProfile, "shared-profile-card__avatar")}<span><b>${esc(sharedProfile.name)}</b><small>@${esc(sharedProfile.username)}</small></span><em>Профиль</em></button>` : msg.profileUserId ? '<div class="shared-profile-card shared-profile-card--missing"><span><b>Профиль недоступен</b><small>Пользователь больше не найден</small></span></div>' : ""}
        ${msg.text ? (msg.sourceType === "rss" ? rssPostHtml(msg) : `<div class="message__text">${esc(msg.text)}</div>`) : ""}
        ${selectedMessageIds.has(msg.id) ? `<span class="message__selected-marker" aria-label="Сообщение выбрано">${actionIcon("select")}</span>` : ""}
        ${messageDeliveryHtml(msg, showInlineDelivery ? "inline" : "inside")}
      </div>
      ${settings.showReactions !== false ? reactionHtml : ""}
      ${commentsHtml}
      ${sourcePostActions}
    </div>
  </div>`;
}

function messageDeliveryHtml(msg, placement = "inside") {
  if (msg.mediaType === "system") return "";
  const dateTime = `${dateFmt(msg.createdAt)} · ${timeFmt(msg.createdAt)}`;
  if (msg.senderId !== state.me.id) {
    return `<span class="message__meta${placement === "side" ? " message__meta--side" : ""}" title="${esc(dateTime)}"><time datetime="${new Date(msg.createdAt * 1000).toISOString()}">${timeFmt(msg.createdAt)}</time></span>`;
  }
  const delivery = msg.deliveryState || (msg.readByRecipient ? "read" : "sent");
  const labels = {
    sending: "Отправляется",
    failed: "Не отправлено",
    sent: "Отправлено",
    read: "Прочитано",
  };
  const icons = {
    sending: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="7.5"/><path d="M12 4.5v3"/></svg>',
    failed: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="8"/><path d="m9 9 6 6m0-6-6 6"/></svg>',
    sent: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m5 12.5 4.1 4L19 7"/></svg>',
    read: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m3 12.5 4.1 4L15 8.5M9 12.5l4.1 4L21 7"/></svg>',
  };
  const deliveryLabel = labels[delivery] || labels.sent;
  return `<span class="message__meta${placement === "side" ? " message__meta--side" : ""} message__delivery message__delivery--${delivery}" title="${esc(`${dateTime} · ${deliveryLabel}`)}" aria-label="${deliveryLabel}"><time datetime="${new Date(msg.createdAt * 1000).toISOString()}">${timeFmt(msg.createdAt)}</time><span class="message__delivery-icon">${icons[delivery] || icons.sent}</span></span>`;
}

function externalHttpUrl(value) {
  try {
    const url = new URL(String(value || ""));
    return ["http:", "https:"].includes(url.protocol) ? url.href : "";
  } catch {
    return "";
  }
}

function rssPostHtml(msg) {
  const parts = String(msg.text || "").split(/\n\s*\n/);
  const trailingUrl = externalHttpUrl(parts[parts.length - 1]);
  if (trailingUrl) parts.pop();
  const title = (parts.shift() || "").trim();
  const description = parts.join("\n\n").trim();
  const articleUrl = externalHttpUrl(msg.sourceId) || trailingUrl;
  const sourceName = articleUrl ? new URL(articleUrl).hostname.replace(/^www\./, "") : "";
  const canCollapse = description.length > 380;
  const collapsed = canCollapse && !expandedRssPostIds.has(msg.id);
  return `<div class="message__text message__rss-text">${title ? `<b class="message__rss-title">${esc(title)}</b>` : ""}${description ? `<div class="message__rss-description${collapsed ? " is-collapsed" : ""}">${esc(description)}</div>${canCollapse ? `<button type="button" class="message__rss-toggle" data-toggle-rss-post="${msg.id}">${collapsed ? "Читать дальше" : "Свернуть"}</button>` : ""}` : ""}${articleUrl ? `<a class="message__rss-link" href="${esc(articleUrl)}" target="_blank" rel="noopener noreferrer">Источник: ${esc(sourceName)}</a>` : ""}</div>`;
}

function openMessageMenu(msg) {
  const chat = state.chats.find((item) => item.id === msg.chatId);
  const user = userById(msg.senderId);
  const settings = chat?.settings || {};
  const canDeleteForEveryone = canDeleteMessageForEveryone(msg);
  const canPinForEveryone = canPinMessageForEveryone(msg);
  const reactions = ["❤️", ...EMOJI_SET.filter((emoji) => emoji !== "❤️")];
  const downloadLabel = msg.mediaType === "voice" ? "Скачать голосовое" : msg.mediaType === "circle" ? "Скачать видеокружок" : "";
  const overlay = document.createElement("div");
  overlay.className = "message-menu-overlay";
  overlay.innerHTML = `<section class="message-menu" role="dialog" aria-modal="true" aria-label="Действия с сообщением"><header><div><b>Сообщение</b><small>${esc(user?.name || "Пользователь")} · ${esc(dateFmt(msg.createdAt))} · ${timeFmt(msg.createdAt)}</small></div><button type="button" data-close-message-menu aria-label="Закрыть">×</button></header><p class="message-menu__preview">${esc(pinnedMessagePreview(msg))}</p><div class="message-menu__actions">${settings.showReactions !== false ? `<button type="button" data-toggle-message-reactions>${actionIcon("reaction", "message-menu__icon")}<span>Реакция</span></button><div class="message-menu__reactions hidden" data-message-reactions>${reactions.map((emoji) => `<button type="button" data-message-menu-react="${esc(emoji)}">${esc(emoji)}</button>`).join("")}</div>` : ""}<button type="button" data-message-menu-action="select">${actionIcon("select", "message-menu__icon")}<span>${selectedMessageIds.has(msg.id) ? "Убрать из выбора" : "Выбрать"}</span></button><button type="button" data-message-menu-action="profile">${actionIcon("profile", "message-menu__icon")}<span>Открыть профиль</span></button>${chat?.type === "channel" && msg.mediaType !== "system" ? `<button type="button" data-message-menu-action="report">${actionIcon("report", "message-menu__icon")}<span>Пожаловаться</span></button><button type="button" data-message-menu-action="donate">${actionIcon("donate", "message-menu__icon")}<span>Подарить звёзды</span></button>` : ""}${downloadLabel ? `<button type="button" data-message-menu-action="download-media">${actionIcon("download", "message-menu__icon")}<span>${downloadLabel}</span></button>` : ""}${canPinForEveryone ? `<button type="button" data-message-menu-action="pin">${pinIcon("message-menu__icon")}<span>${msg.pinned ? "Открепить у всех" : "Закрепить у всех"}</span></button>` : ""}<button type="button" data-toggle-message-delete>${actionIcon("delete", "message-menu__icon")}<span>Удалить</span></button><div class="message-menu__nested hidden" data-message-delete-options><button type="button" data-message-menu-action="delete-me">Удалить у себя</button>${canDeleteForEveryone ? '<button type="button" class="danger" data-message-menu-action="delete-everyone">Удалить у всех</button>' : ""}</div></div></section>`;
  document.body.append(overlay);
  const close = () => overlay.remove();
  overlay.querySelector("[data-close-message-menu]").addEventListener("click", close);
  overlay.addEventListener("click", (event) => { if (event.target === overlay) close(); });
  overlay.querySelector("[data-toggle-message-reactions]")?.addEventListener("click", () => overlay.querySelector("[data-message-reactions]").classList.toggle("hidden"));
  overlay.querySelector("[data-toggle-message-delete]").addEventListener("click", () => overlay.querySelector("[data-message-delete-options]").classList.toggle("hidden"));
  overlay.querySelectorAll("[data-message-menu-react]").forEach((button) => button.addEventListener("click", async () => {
    try {
      showMessageReactionBurst(button.dataset.messageMenuReact, button);
      await api("/api/react", { method: "POST", body: { messageId: msg.id, emoji: button.dataset.messageMenuReact } });
      close();
      await refresh(false);
    } catch (error) { toast(error.message, true); }
  }));
  overlay.querySelectorAll("[data-message-menu-action]").forEach((button) => button.addEventListener("click", async () => {
    const action = button.dataset.messageMenuAction;
    try {
      if (action === "select") {
        if (selectedMessageIds.has(msg.id)) selectedMessageIds.delete(msg.id);
        else selectedMessageIds.add(msg.id);
        close();
        renderChat();
        return;
      }
      if (action === "profile") { close(); openProfile(msg.senderId); return; }
      if (action === "report") { close(); await reportTarget("group-post", msg.id); return; }
      if (action === "download-media") { close(); await downloadMessageMedia(msg); return; }
      if (action === "pin" && canPinForEveryone) {
        if (msg.pinned && !window.confirm("Открепить сообщение у всех участников?")) return;
        await api("/api/messages/pin", { method: "POST", body: { messageId: msg.id } });
      }
      if (action === "donate") { close(); await donateToChannelMessage(msg); return; }
      if (action === "delete-me") {
        if (!window.confirm("Скрыть сообщение только у вас?")) return;
        await api("/api/messages/delete", { method: "POST", body: { messageId: msg.id, scope: "me" } });
      }
      if (action === "delete-everyone") {
        if (!window.confirm("Удалить сообщение у всех?")) return;
        await api("/api/messages/delete", { method: "POST", body: { messageId: msg.id, scope: "everyone" } });
      }
      close();
      await refresh(false);
    } catch (error) { toast(error.message, true); }
  }));
}

function pinnedMessagePreview(msg) {
  if (msg.text) return msg.text;
  if (msg.mediaType === "photo") return "Фото";
  if (msg.mediaType === "voice") return "Голосовое сообщение";
  if (msg.mediaType === "circle") return "Видеокружок";
  return "Сообщение";
}

function openMemberManager(chat) {
  const memberIds = new Set(state.members.filter((member) => member.chat_id === chat.id).map((member) => member.user_id));
  const directContactIds = new Set(
    state.chats
      .filter((item) => item.type === "direct" && isMember(item.id))
      .flatMap((item) => state.members.filter((member) => member.chat_id === item.id && member.user_id !== state.me.id).map((member) => member.user_id)),
  );
  const candidates = state.users.filter((user) => directContactIds.has(user.id) && !memberIds.has(user.id));
  const overlay = document.createElement("div");
  overlay.className = "member-manager-overlay";
  overlay.innerHTML = `<section class="member-manager" role="dialog" aria-modal="true" aria-label="Добавление участников"><header><div><b>Добавить участников</b><small>${esc(chat.title)}</small></div><button class="member-manager__close" type="button" aria-label="Закрыть">×</button></header><label>Поиск<input type="search" placeholder="Имя или username" data-member-search></label><div class="member-manager__list" data-member-list></div></section>`;
  document.body.append(overlay);
  const list = overlay.querySelector("[data-member-list]");
  const renderCandidates = (query = "") => {
    const normalized = query.trim().toLowerCase().replace("@", "");
    const filtered = candidates.filter((user) => `${user.name} ${user.username}`.toLowerCase().includes(normalized));
    list.innerHTML = filtered.length ? filtered.map((user) => `<button class="member-manager__user" type="button" data-add-user="${user.id}">${avatarHtml(user)}<span><b>${esc(user.name)}</b><small>@${esc(user.username)}</small></span><em>Добавить</em></button>`).join("") : '<p class="muted">Можно добавить только пользователей из ваших личных диалогов.</p>';
    list.querySelectorAll("[data-add-user]").forEach((button) => button.addEventListener("click", async () => {
      try {
        await api("/api/chats/members", { method: "POST", body: { chatId: chat.id, userId: button.dataset.addUser } });
        toast("Участник добавлен.");
        overlay.remove();
        await refresh();
      } catch (error) { toast(error.message, true); }
    }));
  };
  overlay.querySelector("[data-member-search]").addEventListener("input", (event) => renderCandidates(event.currentTarget.value));
  overlay.querySelector(".member-manager__close").addEventListener("click", () => overlay.remove());
  overlay.addEventListener("click", (event) => { if (event.target === overlay) overlay.remove(); });
  renderCandidates();
  overlay.querySelector("[data-member-search]").focus();
}

function openGroupProfile(chat) {
  const roleOrder = { owner: 0, admin: 1, author: 1, member: 2 };
  const members = state.members
    .filter((member) => member.chat_id === chat.id)
    .map((member) => ({ ...member, user: userById(member.user_id) }))
    .sort((a, b) => (roleOrder[a.role] ?? 99) - (roleOrder[b.role] ?? 99) || (a.user?.name || "").localeCompare(b.user?.name || "", "ru"));
  const myRole = chatMemberRole(chat.id);
  const isChannel = chat.type === "channel";
  const canManageChannel = isChannel && isChannelManagerRole(myRole);
  const canModerate = isChannel ? canManageChannel : ["owner", "admin"].includes(myRole);
  const canEditProfile = myRole === "owner";
  const canAuthorChannel = canManageChannel;
  const subscriberCount = Number(chat.subscriberCount) || 0;
  const media = state.messages.filter((message) => message.chatId === chat.id && ["photo", "voice", "circle", "document"].includes(message.mediaType));
  const photos = media.filter((message) => message.mediaType === "photo");
  const audio = media.filter((message) => message.mediaType === "voice");
  const circles = media.filter((message) => message.mediaType === "circle");
  const inviteLink = `${window.location.origin}/invite/${encodeURIComponent(chat.inviteCode || "")}`;
  const inviteEnabled = chat.settings?.inviteLinkEnabled !== false;
  const roleLabel = { owner: "Создатель", admin: "Администратор", author: "Администратор", member: "Подписчик" };
  const memberHtml = members.map((member) => {
    const isCreator = member.user_id === chat.ownerId;
    const canRemove = canModerate && !isCreator && (myRole === "owner" || member.role === "member");
    const canChangeRole = myRole === "owner" && !isCreator;
    const privilegedRole = "admin";
    const isPrivileged = ["admin", "author"].includes(member.role);
    return `<article class="group-card__member">${avatarHtml(member.user, "group-card__member-avatar")}<button type="button" class="group-card__member-info" data-group-member-profile="${member.user_id}"><b>${esc(member.user?.name || "Участник")}</b><small>@${esc(member.user?.username || "")}</small></button><span class="group-card__role group-card__role--${esc(member.role)}">${roleLabel[member.role] || "Участник"}</span>${canChangeRole ? `<button class="group-card__member-action" type="button" data-member-role="${member.user_id}" data-next-role="${isPrivileged ? "member" : privilegedRole}">${isPrivileged ? "Снять права" : "Сделать админом"}</button>` : ""}${canRemove ? `<button class="group-card__member-action danger" type="button" data-remove-member="${member.user_id}">Удалить</button>` : ""}</article>`;
  }).join("");
  const overlay = document.createElement("div");
  overlay.className = `group-card-overlay${isChannel ? " group-card-overlay--channel" : ""}`;
  const channelSettings = isChannel && canEditProfile ? `<section class="group-card__section"><div class="group-card__section-head"><div><b>Настройки канала</b><small>Видимость и взаимодействия</small></div></div><div class="channel-settings">${[["showSubscribers", "Подписчики", "Показывать число подписчиков"], ["showReactions", "Реакции", "Показывать реакции под публикациями"], ["commentsEnabled", "Комментарии", "Разрешить комментарии к постам"], ["isPublic", "Публичный канал", "Показывать канал в общем поиске"]].map(([key, title, hint]) => `<label class="channel-setting"><span><b>${title}</b><small>${hint}</small></span><input type="checkbox" name="${key}" ${chat.settings?.[key] !== false ? "checked" : ""}></label>`).join("")}<div class="channel-settings__actions"><button class="button small" type="button" data-link-telegram>Импорт из Telegram</button><button class="button small" type="button" data-link-rss>Автопостинг из RSS</button></div></div></section>` : "";
  const channelAdminTools = canAuthorChannel ? `<section class="group-card__section group-card__section--tools"><div class="group-card__section-head"><div><b>Инструменты администратора</b><small>Публикации, оформление и связь с группой</small></div></div><div class="channel-settings__actions"><button class="button small" type="button" data-schedule-channel-post>Запланировать пост</button><button class="button small" type="button" data-link-channel>Привязать группу / беседу</button><button class="button small" type="button" data-channel-appearance>Оформление канала</button></div></section>` : "";
  const channelMedia = isChannel ? `<section class="group-card__section group-card__section--media"><div class="group-card__section-head"><div><b>Вложения</b><small>${media.length ? `${media.length} ${media.length === 1 ? "файл" : "файлов"}` : "Фото, документы, голосовые и кружки"}</small></div><button class="button small" type="button" data-open-group-media>Открыть</button></div></section>` : "";
  const groupTools = !isChannel ? `<section class="group-card__section"><div class="group-card__section-head"><div><b>Вложения</b><small>${media.length ? `${media.length} ${media.length === 1 ? "файл" : "файлов"}` : "Пока нет файлов"}</small></div><button class="button small" type="button" data-open-group-media>Открыть</button></div></section><section class="group-card__section"><div class="group-card__section-head"><div><b>Ссылка-приглашение</b><small>${inviteEnabled ? "Доступна всем, у кого есть ссылка" : "Выдавать ссылку могут только администраторы"}</small></div></div>${canModerate ? `<div class="invite-link"><code>${esc(inviteLink)}</code><button class="button small" type="button" data-copy-invite-link>Копировать</button></div><label class="channel-setting"><span><b>Публичная ссылка</b><small>Разрешить вступление по ссылке без приглашения администратора</small></span><input type="checkbox" name="inviteLinkEnabled" ${inviteEnabled ? "checked" : ""}></label>` : '<p class="muted">Ссылка доступна у владельца и администраторов группы.</p>'}</section>` : "";
  const profileEditor = canEditProfile
    ? `<form class="group-card__form" data-group-profile-form><label>Название<input name="title" maxlength="120" required value="${esc(chat.title)}"></label><label>Описание<textarea name="description" maxlength="1000" placeholder="Расскажите о ${isChannel ? "канале" : "беседе"}">${esc(chat.description || "")}</textarea></label><label>Аватар<input name="avatar" type="file" accept="image/png,image/jpeg,image/webp"></label><div class="group-card__form-actions"><button class="button small" type="submit">Сохранить профиль</button>${chat.avatarData ? '<button class="button small" type="button" data-clear-group-avatar>Убрать аватар</button>' : ""}</div></form>`
    : `<section class="group-card__section"><b>О канале</b><p class="muted">Название, описание и аватар меняет только создатель.</p></section>`;
  const memberSection = isChannel && !canManageChannel
    ? `<section class="group-card__section group-card__section--subscriber-count"><div class="group-card__section-head"><div><b>Подписчики</b><small>Список подписчиков скрыт создателем канала</small></div><strong>${subscriberCount}</strong></div></section>`
    : `<section class="group-card__section"><div class="group-card__section-head"><div><b>${isChannel ? "Подписчики и администраторы" : "Участники"}</b><small>${isChannel ? `${subscriberCount} ${subscriberWord(subscriberCount)}` : `${members.length} ${memberWord(members.length)}`}</small></div>${myRole === "owner" ? '<button class="button small" type="button" data-add-group-member>Добавить</button>' : ""}</div><div class="group-card__members">${memberHtml}</div></section>`;
  const profileCount = isChannel ? subscriberCount : members.length;
  overlay.innerHTML = `<section class="group-card${isChannel ? " group-card--channel" : ""}" role="dialog" aria-modal="true" aria-label="Профиль ${isChannel ? "канала" : "группы"}"><header class="group-card__header"><div class="group-card__identity">${chatAvatarHtml(chat, "group-card__avatar")}<div><b>${esc(chat.title)}</b><small>${profileCount} ${isChannel ? subscriberWord(profileCount) : memberWord(profileCount)} · ${isChannel ? "канал" : chat.type === "group" ? "группа" : "комьюнити"}</small></div></div><button type="button" data-close-group-card aria-label="Закрыть">×</button></header>${profileEditor}${channelSettings}${channelAdminTools}${channelMedia}${groupTools}${memberSection}<footer class="group-card__footer${isChannel ? " group-card__footer--channel" : ""}">${isChannel ? '<button class="button primary group-card__buy-stars" type="button" data-buy-stars-through-channel><span aria-hidden="true">★</span> Купить звёзды</button>' : ""}${isChannel && chat.ownerId !== state.me.id ? `<button class="button small" type="button" data-report-channel-profile="${chat.id}">Пожаловаться на канал</button>` : ""}<button class="button danger" type="button" data-group-leave>Выйти из ${isChannel ? "канала" : "беседы"}</button></footer></section>`;
  document.body.append(overlay);
  const close = () => overlay.remove();
  overlay.querySelector("[data-close-group-card]").addEventListener("click", close);
  overlay.addEventListener("click", (event) => { if (event.target === overlay) close(); });
  overlay.querySelector("[data-group-profile-form]")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const form = new FormData(event.currentTarget);
      const avatar = form.get("avatar");
      const avatarData = avatar?.size ? await fileToDataUrl(avatar, 1_800_000) : (chat.avatarData || "");
      const body = { chatId: chat.id, title: form.get("title"), description: form.get("description"), avatarData };
      if (isChannel) ["showSubscribers", "showReactions", "commentsEnabled", "isPublic"].forEach((key) => { body[key] = overlay.querySelector(`[name="${key}"]`)?.checked; });
      if (!isChannel && canModerate) body.inviteLinkEnabled = overlay.querySelector('[name="inviteLinkEnabled"]')?.checked;
      await api("/api/chats/update", { method: "POST", body });
      await refresh();
      close();
      openGroupProfile(state.chats.find((item) => item.id === chat.id));
    } catch (error) { toast(error.message, true); }
  });
  overlay.querySelector("[data-clear-group-avatar]")?.addEventListener("click", async () => {
    try {
      await api("/api/chats/update", { method: "POST", body: { chatId: chat.id, title: chat.title, description: chat.description, avatarData: "" } });
      await refresh(); close(); openGroupProfile(state.chats.find((item) => item.id === chat.id));
    } catch (error) { toast(error.message, true); }
  });
  overlay.querySelector("[data-add-group-member]")?.addEventListener("click", () => { close(); openMemberManager(chat); });
  overlay.querySelector("[data-open-group-media]")?.addEventListener("click", () => openChatMedia(chat));
  overlay.querySelector("[data-copy-invite-link]")?.addEventListener("click", async () => {
    try { await navigator.clipboard.writeText(inviteLink); toast("Ссылка-приглашение скопирована."); }
    catch { window.prompt("Скопируйте ссылку:", inviteLink); }
  });
  overlay.querySelector("[data-schedule-channel-post]")?.addEventListener("click", () => openChannelScheduleDialog(chat, () => { close(); openGroupProfile(state.chats.find((item) => item.id === chat.id)); }));
  overlay.querySelector("[data-link-channel]")?.addEventListener("click", () => openChannelLinkDialog(chat, () => { close(); openGroupProfile(state.chats.find((item) => item.id === chat.id)); }));
  overlay.querySelector("[data-link-telegram]")?.addEventListener("click", () => openChannelTelegramDialog(chat, () => { close(); openGroupProfile(state.chats.find((item) => item.id === chat.id)); }));
  overlay.querySelector("[data-link-rss]")?.addEventListener("click", () => openChannelRssDialog(chat, () => { close(); openGroupProfile(state.chats.find((item) => item.id === chat.id)); }));
  overlay.querySelector("[data-channel-appearance]")?.addEventListener("click", () => openChannelAppearanceDialog(chat, () => { close(); openGroupProfile(state.chats.find((item) => item.id === chat.id)); }));
  overlay.querySelector("[data-buy-stars-through-channel]")?.addEventListener("click", () => {
    toast("Покупка звёзд через канал будет доступна после подключения платёжного провайдера.");
  });
  overlay.querySelector("[data-report-channel-profile]")?.addEventListener("click", async (event) => {
    try { await reportTarget("channel", event.currentTarget.dataset.reportChannelProfile); } catch (error) { toast(error.message, true); }
  });
  overlay.querySelectorAll("[data-group-member-profile]").forEach((button) => button.addEventListener("click", () => { close(); openProfile(button.dataset.groupMemberProfile); }));
  overlay.querySelectorAll("[data-member-role]").forEach((button) => button.addEventListener("click", async () => {
    try { await api("/api/chats/members/role", { method: "POST", body: { chatId: chat.id, userId: button.dataset.memberRole, role: button.dataset.nextRole } }); await refresh(); close(); openGroupProfile(state.chats.find((item) => item.id === chat.id)); }
    catch (error) { toast(error.message, true); }
  }));
  overlay.querySelectorAll("[data-remove-member]").forEach((button) => button.addEventListener("click", async () => {
    const member = members.find((item) => item.user_id === button.dataset.removeMember);
    if (!window.confirm(`Удалить ${member?.user?.name || "участника"} из беседы?`)) return;
    try { await api("/api/chats/members/remove", { method: "POST", body: { chatId: chat.id, userId: button.dataset.removeMember } }); await refresh(); close(); openGroupProfile(state.chats.find((item) => item.id === chat.id)); }
    catch (error) { toast(error.message, true); }
  }));
  overlay.querySelectorAll("[data-group-photo]").forEach((button) => button.addEventListener("click", () => openMedia(messageMediaUrl(state.messages.find((message) => message.id === button.dataset.groupPhoto)))));
  overlay.querySelectorAll("[data-group-circle]").forEach((button) => button.addEventListener("click", () => { close(); openCircle(button.dataset.groupCircle); }));
  overlay.querySelector("[data-group-leave]").addEventListener("click", async () => {
    if (!window.confirm(`Выйти из «${chat.title}»?`)) return;
    try { await api("/api/chats/leave", { method: "POST", body: { chatId: chat.id } }); activeChatId = null; close(); toast("Вы вышли из беседы."); await refresh(); }
    catch (error) { toast(error.message, true); }
  });
}

function openChannelScheduleDialog(chat, afterSave) {
  const overlay = document.createElement("div");
  overlay.className = "member-manager-overlay";
  overlay.innerHTML = `<section class="member-manager" role="dialog" aria-modal="true" aria-label="Отложенная публикация"><header><div><b>Запланировать пост</b><small>${esc(chat.title)}</small></div><button class="member-manager__close" type="button" aria-label="Закрыть">×</button></header><form class="form" data-channel-schedule-form><label>Текст публикации<textarea name="text" maxlength="3000" placeholder="Что нового?"></textarea></label><label>Фото<input name="photo" type="file" accept="image/png,image/jpeg,image/webp"></label><label>Дата и время<input name="publishAt" type="datetime-local" required></label><button class="button primary">Запланировать</button></form></section>`;
  document.body.append(overlay);
  const close = () => overlay.remove();
  overlay.querySelector(".member-manager__close").addEventListener("click", close);
  overlay.addEventListener("click", (event) => { if (event.target === overlay) close(); });
  overlay.querySelector("[data-channel-schedule-form]").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const form = new FormData(event.currentTarget);
      const photo = form.get("photo");
      const body = { chatId: chat.id, text: form.get("text"), publishAt: Math.floor(new Date(form.get("publishAt")).getTime() / 1000) };
      if (photo?.size) { body.mediaType = "photo"; body.mediaData = await fileToDataUrl(photo, 2_500_000); }
      await api("/api/channels/schedule", { method: "POST", body });
      await refresh(false);
      close();
      toast("Пост запланирован.");
      afterSave?.();
    } catch (error) { toast(error.message, true); }
  });
}

function openChannelLinkDialog(chat, afterSave) {
  const targets = state.chats.filter((item) => ["group", "community"].includes(item.type) && ["owner", "admin"].includes(chatMemberRole(item.id)));
  const currentLink = state.channelLinks.find((link) => link.channel_id === chat.id)?.target_chat_id || "";
  const overlay = document.createElement("div");
  overlay.className = "member-manager-overlay";
  overlay.innerHTML = `<section class="member-manager" role="dialog" aria-modal="true" aria-label="Связанная группа"><header><div><b>Связать с группой</b><small>Новые посты будут автоматически дублироваться в выбранную беседу.</small></div><button class="member-manager__close" type="button" aria-label="Закрыть">×</button></header><form class="form" data-channel-link-form><label>Группа или беседа<select name="targetChatId"><option value="">Не привязывать</option>${targets.map((target) => `<option value="${target.id}" ${target.id === currentLink ? "selected" : ""}>${esc(target.title)}</option>`).join("")}</select></label>${targets.length ? "" : '<p class="muted">Сначала создайте свою группу или беседу.</p>'}<button class="button primary">Сохранить связь</button></form></section>`;
  document.body.append(overlay);
  const close = () => overlay.remove();
  overlay.querySelector(".member-manager__close").addEventListener("click", close);
  overlay.addEventListener("click", (event) => { if (event.target === overlay) close(); });
  overlay.querySelector("[data-channel-link-form]").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const targetChatId = new FormData(event.currentTarget).get("targetChatId");
      await api("/api/channels/link", { method: "POST", body: { channelId: chat.id, targetChatId } });
      await refresh(false);
      close();
      toast(targetChatId ? "Группа связана с каналом." : "Связь с группой удалена.");
      afterSave?.();
    } catch (error) { toast(error.message, true); }
  });
}

function openChannelTelegramDialog(chat, afterSave) {
  const link = state.telegramChannelLinks.find((item) => item.channel_id === chat.id);
  const overlay = document.createElement("div");
  overlay.className = "member-manager-overlay";
  const syncStatus = !link
    ? "Импорт ещё не подключён."
    : link.last_error
      ? `Последняя ошибка: ${link.last_error}`
      : link.last_sync_at
        ? `Последняя проверка: ${dateFmt(link.last_sync_at)} ${timeFmt(link.last_sync_at)}`
        : "Источник подключён, ожидается первая проверка.";
  overlay.innerHTML = `<section class="member-manager" role="dialog" aria-modal="true" aria-label="Импорт из Telegram"><header><div><b>Импорт публикаций из Telegram</b><small>Новые посты из внешнего канала будут появляться в «${esc(chat.title)}».</small></div><button class="member-manager__close" type="button" aria-label="Закрыть">×</button></header><form class="form" data-telegram-link-form><label>Исходный канал<input name="sourceChat" required placeholder="@channel_name или -100..." value="${esc(link?.source_chat_ref || "")}" autocomplete="off"></label><label>Токен Telegram Bot API<input name="botToken" required type="password" placeholder="123456:ABC..." autocomplete="new-password"></label><p class="muted">Добавьте бота администратором исходного канала. Импортируются только новые <code>channel_post</code>; история не загружается. Для <code>getUpdates</code> у бота не должен быть включён webhook. Токен хранится только локально на сервере и не показывается после сохранения.</p><p class="telegram-link-status">${esc(syncStatus)}</p><div class="group-card__form-actions"><button class="button primary">${link ? "Обновить подключение" : "Подключить Telegram"}</button>${link ? '<button class="button danger" type="button" data-disconnect-telegram>Отключить</button>' : ""}</div></form></section>`;
  document.body.append(overlay);
  const close = () => overlay.remove();
  overlay.querySelector(".member-manager__close").addEventListener("click", close);
  overlay.addEventListener("click", (event) => { if (event.target === overlay) close(); });
  overlay.querySelector("[data-telegram-link-form]").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const form = new FormData(event.currentTarget);
      await api("/api/channels/telegram", { method: "POST", body: { channelId: chat.id, sourceChat: form.get("sourceChat"), botToken: form.get("botToken") } });
      await refresh(false);
      close();
      toast("Telegram подключён. Ожидаются новые публикации.");
      afterSave?.();
    } catch (error) { toast(error.message, true); }
  });
  overlay.querySelector("[data-disconnect-telegram]")?.addEventListener("click", async () => {
    if (!window.confirm("Отключить импорт из Telegram? Уже импортированные публикации останутся в канале.")) return;
    try {
      await api("/api/channels/telegram", { method: "POST", body: { channelId: chat.id, disconnect: true } });
      await refresh(false);
      close();
      toast("Импорт из Telegram отключён.");
      afterSave?.();
    } catch (error) { toast(error.message, true); }
  });
}

function openChannelRssDialog(chat, afterSave) {
  const sources = state.rssChannelLinks.filter((item) => item.channel_id === chat.id);
  const overlay = document.createElement("div");
  overlay.className = "member-manager-overlay";
  const sourceList = sources.length
    ? `<div class="rss-source-list">${sources.map((source) => {
      const status = source.last_error
        ? `Ошибка: ${source.last_error}`
        : source.last_sync_at
          ? `Проверено: ${dateFmt(source.last_sync_at)} ${timeFmt(source.last_sync_at)}`
          : "Ожидается первая проверка";
      return `<article class="rss-source"><div><b>${esc(source.feed_title || "RSS-источник")}</b><small title="${esc(source.feed_url)}">${esc(source.feed_url)}</small><em class="${source.last_error ? "rss-source__error" : ""}">${esc(status)}</em></div><button class="button small danger" type="button" data-disconnect-rss="${source.id}">Отключить</button></article>`;
    }).join("")}</div>`
    : '<p class="telegram-link-status">Источники ещё не подключены.</p>';
  overlay.innerHTML = `<section class="member-manager" role="dialog" aria-modal="true" aria-label="Автопостинг из RSS"><header><div><b>Автопостинг из RSS</b><small>Новые публикации из лент будут появляться в «${esc(chat.title)}».</small></div><button class="member-manager__close" type="button" aria-label="Закрыть">×</button></header><form class="form" data-rss-link-form><label>Добавить URL RSS-ленты<input name="feedUrl" required type="url" placeholder="https://example.com/feed.xml" autocomplete="url"></label><p class="muted">Можно подключить до 10 публичных RSS или Atom-лент. Каждая проверяется примерно раз в 5 минут. Текущие публикации при подключении не переносятся: в канал попадут только новые записи.</p><div class="group-card__form-actions"><button class="button primary">Добавить источник</button></div></form><section class="rss-sources"><div class="panel-title"><div><b>Подключённые источники</b><small>${sources.length} из 10</small></div></div>${sourceList}</section></section>`;
  document.body.append(overlay);
  const close = () => overlay.remove();
  overlay.querySelector(".member-manager__close").addEventListener("click", close);
  overlay.addEventListener("click", (event) => { if (event.target === overlay) close(); });
  overlay.querySelector("[data-rss-link-form]").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const form = new FormData(event.currentTarget);
      const result = await api("/api/channels/rss", { method: "POST", body: { channelId: chat.id, feedUrl: form.get("feedUrl") } });
      await refresh(false);
      close();
      toast(`RSS «${result.feedTitle}» подключён. Ожидаются новые публикации.`);
      afterSave?.();
    } catch (error) { toast(error.message, true); }
  });
  overlay.querySelectorAll("[data-disconnect-rss]").forEach((button) => button.addEventListener("click", async () => {
    if (!window.confirm("Отключить автопостинг RSS? Уже импортированные публикации останутся в канале.")) return;
    try {
      await api("/api/channels/rss", { method: "POST", body: { channelId: chat.id, sourceId: button.dataset.disconnectRss, disconnect: true } });
      await refresh(false);
      close();
      toast("RSS-источник отключён.");
      afterSave?.();
    } catch (error) { toast(error.message, true); }
  }));
}

function openChannelAppearanceDialog(chat, afterSave) {
  const current = chat.settings?.appearance || {};
  const wallpaper = CHAT_WALLPAPERS.some((item) => item.id === current.wallpaper) || current.wallpaper === "custom" ? current.wallpaper : "default";
  const ownBubble = /^#[\da-f]{6}$/i.test(current.ownBubble || "") ? current.ownBubble : state.me.dialogColor || "#ffffff";
  const otherBubble = /^#[\da-f]{6}$/i.test(current.otherBubble || "") ? current.otherBubble : state.me.otherDialogColor || "#ffffff";
  const panelColor = /^#[\da-f]{6}$/i.test(current.panelColor || "") ? current.panelColor : state.me.dialogPanelColor || "#f4f8fc";
  const font = DIALOG_FONTS.some((item) => item.id === current.font) ? current.font : state.me.dialogFont || "business";
  let backgroundData = current.backgroundData || "";
  const overlay = document.createElement("div");
  overlay.className = "member-manager-overlay";
  overlay.innerHTML = `<section class="member-manager channel-appearance-dialog" role="dialog" aria-modal="true" aria-label="Оформление канала"><header><div><b>Оформление канала</b><small>Его увидят все подписчики. Если сбросить настройку, останется личная тема каждого пользователя.</small></div><button class="member-manager__close" type="button" aria-label="Закрыть">×</button></header><form class="form" data-channel-appearance-form><fieldset class="wallpaper-picker"><legend>Фон</legend><div class="wallpaper-grid">${CHAT_WALLPAPERS.map((item) => `<label class="wallpaper-option${wallpaper === item.id ? " selected" : ""}"><input type="radio" name="wallpaper" value="${item.id}" ${wallpaper === item.id ? "checked" : ""}><span class="wallpaper-preview chat-background-${item.id}" aria-hidden="true"></span><span><b>${esc(item.title)}</b><small>${esc(item.description)}</small></span></label>`).join("")}<label class="wallpaper-option${wallpaper === "custom" ? " selected" : ""}"><input type="radio" name="wallpaper" value="custom" ${wallpaper === "custom" ? "checked" : ""}><span class="wallpaper-preview chat-background-custom" data-channel-custom-preview aria-hidden="true"></span><span><b>Своя картинка</b><small>PNG, JPG или WebP</small></span></label></div></fieldset><label>Изображение фона<input name="background" type="file" accept="image/png,image/jpeg,image/webp"></label><div class="dialog-color-controls"><label class="dialog-color-control">Мои публикации<input name="ownBubble" type="color" value="${esc(ownBubble)}"></label><label class="dialog-color-control">Публикации других<input name="otherBubble" type="color" value="${esc(otherBubble)}"></label><label class="dialog-color-control">Панели канала<input name="panelColor" type="color" value="${esc(panelColor)}"></label></div><label>Шрифт публикаций<select name="font">${DIALOG_FONTS.map((item) => `<option value="${item.id}" ${font === item.id ? "selected" : ""}>${esc(item.title)}</option>`).join("")}</select></label><div class="group-card__form-actions"><button class="button primary">Сохранить оформление</button>${chat.settings?.appearance ? '<button class="button danger" type="button" data-reset-channel-appearance>Сбросить оформление</button>' : ""}</div></form></section>`;
  document.body.append(overlay);
  const close = () => overlay.remove();
  const form = overlay.querySelector("[data-channel-appearance-form]");
  const customPreview = overlay.querySelector("[data-channel-custom-preview]");
  const setCustomPreview = () => {
    customPreview.style.backgroundImage = backgroundData ? `url("${backgroundData}")` : "";
  };
  setCustomPreview();
  overlay.querySelector(".member-manager__close").addEventListener("click", close);
  overlay.addEventListener("click", (event) => { if (event.target === overlay) close(); });
  form.querySelectorAll('[name="wallpaper"]').forEach((input) => input.addEventListener("change", () => {
    form.querySelectorAll(".wallpaper-option").forEach((item) => item.classList.toggle("selected", item.querySelector("input").checked));
  }));
  form.elements.background.addEventListener("change", async (event) => {
    try {
      const file = event.currentTarget.files?.[0];
      if (!file) return;
      backgroundData = await fileToDataUrl(file, 2_500_000);
      form.elements.wallpaper.value = "custom";
      form.querySelectorAll(".wallpaper-option").forEach((item) => item.classList.toggle("selected", item.querySelector("input").checked));
      setCustomPreview();
    } catch (error) { toast(error.message, true); event.currentTarget.value = ""; }
  });
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const data = new FormData(form);
      await api("/api/channels/appearance", { method: "POST", body: { channelId: chat.id, appearance: { wallpaper: data.get("wallpaper"), backgroundData, ownBubble: data.get("ownBubble"), otherBubble: data.get("otherBubble"), panelColor: data.get("panelColor"), font: data.get("font") } } });
      await refresh(false);
      close();
      toast("Оформление канала сохранено.");
      afterSave?.();
    } catch (error) { toast(error.message, true); }
  });
  overlay.querySelector("[data-reset-channel-appearance]")?.addEventListener("click", async () => {
    if (!window.confirm("Сбросить единое оформление? Подписчики снова увидят свою личную тему.")) return;
    try {
      await api("/api/channels/appearance", { method: "POST", body: { channelId: chat.id, reset: true } });
      await refresh(false);
      close();
      toast("Единое оформление канала сброшено.");
      afterSave?.();
    } catch (error) { toast(error.message, true); }
  });
}

function openChannelComments(messageId) {
  const message = state.messages.find((item) => item.id === messageId);
  if (!message) return;
  const channel = state.chats.find((chat) => chat.id === message.chatId);
  const canComment = isMember(message.chatId);
  const comments = state.channelComments.filter((comment) => comment.message_id === messageId);
  const overlay = document.createElement("div");
  overlay.className = "member-manager-overlay";
  const commentForm = canComment
    ? `<form class="form" data-channel-comment-form><label>Ваш комментарий<textarea name="text" maxlength="1000" placeholder="Напишите комментарий"></textarea></label><label>Фото<input name="photo" type="file" accept="image/png,image/jpeg,image/webp"></label><button class="button primary">Отправить</button></form>`
    : `<section class="channel-comment-join"><p class="muted">Подпишитесь на канал, чтобы оставить комментарий.</p>${channel?.type === "channel" ? '<button class="button primary small" type="button" data-join-comment-channel>Подписаться</button>' : ""}</section>`;
  overlay.innerHTML = `<section class="member-manager" role="dialog" aria-modal="true" aria-label="Комментарии"><header><div><b>Комментарии</b><small>${esc(pinnedMessagePreview(message))}</small></div><button class="member-manager__close" type="button" aria-label="Закрыть">×</button></header><div class="channel-comment-list">${comments.map((comment) => { const author = userById(comment.user_id); return `<article><div class="channel-comment__author">${avatarHtml(author, "channel-comment__avatar")}<b>${esc(author?.name || "Пользователь")}</b>${comment.automated ? '<span class="channel-comment__automated">Автокомментарий</span>' : ""}</div>${comment.media_data ? `<button class="channel-comment-photo" type="button" data-open-comment-media="${esc(comment.media_data)}"><img src="${esc(comment.media_data)}" alt="Фото в комментарии"></button>` : ""}${comment.text ? `<p>${esc(comment.text)}</p>` : ""}<small>${timeFmt(comment.created_at)}</small></article>`; }).join("") || '<p class="muted">Комментариев пока нет.</p>'}</div>${commentForm}</section>`;
  document.body.append(overlay);
  const close = () => overlay.remove();
  overlay.querySelector(".member-manager__close").addEventListener("click", close);
  overlay.addEventListener("click", (event) => { if (event.target === overlay) close(); });
  overlay.querySelectorAll("[data-open-comment-media]").forEach((button) => button.addEventListener("click", () => openMedia(button.dataset.openCommentMedia)));
  overlay.querySelector("[data-join-comment-channel]")?.addEventListener("click", async () => {
    try {
      await api("/api/chats/join", { method: "POST", body: { chatId: message.chatId } });
      close();
      await refresh(false);
      openChannelComments(messageId);
    } catch (error) { toast(error.message, true); }
  });
  overlay.querySelector("[data-channel-comment-form]")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const form = new FormData(event.currentTarget);
      const photo = form.get("photo");
      const mediaData = photo?.size ? await fileToDataUrl(photo, 1_800_000) : "";
      await api("/api/channels/comments", { method: "POST", body: { messageId, text: form.get("text"), mediaData } });
      await refresh(false);
      close();
      openChannelComments(messageId);
    } catch (error) { toast(error.message, true); }
  });
}

function openGroupContentShare(sourceType, sourceId) {
  const targets = state.chats.filter((chat) => ["direct", "group", "community", "channel"].includes(chat.type) && isMember(chat.id) && (chat.type !== "channel" || isChannelManagerRole(chatMemberRole(chat.id))));
  const overlay = document.createElement("div");
  overlay.className = "member-manager-overlay";
  overlay.innerHTML = `<section class="member-manager" role="dialog" aria-modal="true" aria-label="Поделиться публикацией"><header><div><b>Поделиться публикацией</b><small>Автор и исходный материал будут указаны в сообщении.</small></div><button class="member-manager__close" type="button" aria-label="Закрыть">×</button></header><label class="share-comment">Сообщение к репосту <span class="muted">(необязательно)</span><textarea data-share-comment maxlength="1000" placeholder="Добавьте комментарий"></textarea></label><div class="member-manager__list">${targets.map((chat) => `<button class="member-manager__user" type="button" data-share-to-group="${chat.id}">${chatAvatarHtml(chat)}<span><b>${esc(chatMeta(chat).title)}</b><small>${chat.type === "direct" ? "Диалог" : chat.type === "channel" ? "Канал" : "Группа"}</small></span><em>Поделиться</em></button>`).join("") || '<p class="muted">Нет диалогов, групп или каналов, в которые можно поделиться публикацией.</p>'}</div></section>`;
  document.body.append(overlay);
  const close = () => overlay.remove();
  overlay.querySelector(".member-manager__close").addEventListener("click", close);
  overlay.addEventListener("click", (event) => { if (event.target === overlay) close(); });
  overlay.querySelectorAll("[data-share-to-group]").forEach((button) => button.addEventListener("click", async () => {
    try {
      const comment = overlay.querySelector("[data-share-comment]")?.value || "";
      const result = await api("/api/group-content/share", { method: "POST", body: { targetChatId: button.dataset.shareToGroup, sourceType, sourceId, comment } });
      activeSection = "chats";
      activeChatId = result.messageId ? button.dataset.shareToGroup : activeChatId;
      close();
      await refresh();
      toast("Публикация отправлена.");
    } catch (error) { toast(error.message, true); }
  }));
}

function messageMediaHtml(msg) {
  if (!msg.mediaType) return "";
  if (msg.mediaType === "photo") {
    const source = messageMediaUrl(msg);
    return `<button class="message-photo-button${msg.sourceType === "rss" ? " message-photo-button--rss" : ""}" type="button" data-open-message-media="${msg.id}" data-open-message-media-source="${esc(source)}" data-media-type="photo" title="Открыть фото на весь экран" aria-label="Открыть фото на весь экран"><img class="message-photo" src="${esc(source)}" alt="Фото"></button>`;
  }
  if (msg.mediaType === "document") return `<a class="message-document" href="${esc(messageMediaUrl(msg))}" target="_blank" rel="noopener"><span>📄</span><b>${esc(msg.text?.replace(/^Документ:\s*/, "") || "Документ")}</b><small>Открыть документ</small></a>`;
  const source = messageMediaUrl(msg);
  if (msg.mediaType === "video") return `<div class="message-video"><video controls playsinline preload="metadata" src="${esc(source)}"></video><button type="button" data-open-message-media="${msg.id}" title="Открыть видео на весь экран" aria-label="Открыть видео на весь экран">⤢</button></div>`;
  if (msg.mediaType === "voice") {
    const waveform = Array.isArray(msg.voiceWaveform) && msg.voiceWaveform.length ? msg.voiceWaveform : voiceWaveformFallback(msg.id);
    return `<div class="message-voice"><audio class="message-audio" preload="metadata" data-media-message="voice" src="${esc(source)}"></audio><button class="message-voice__play" type="button" data-voice-playback aria-label="Воспроизвести голосовое"></button><div class="message-voice__wave" data-voice-wave>${waveform.map((value) => `<i style="--voice-level:${Math.max(8, Number(value) || 8)}%"></i>`).join("")}</div><span class="message-voice__duration" data-voice-duration>0:00</span></div>`;
  }
  if (msg.mediaType === "circle") return `<div class="circle-message"><div class="circle-message__mask"><video class="message-circle" playsinline preload="auto" data-media-message="circle" src="${esc(source)}"></video></div><button class="circle-expand" type="button" data-open-circle="${msg.id}" title="Открыть видеокружок" aria-label="Открыть видеокружок">⤢</button><div class="circle-player" aria-label="Управление видеокружком"><button type="button" data-circle-playback aria-label="Воспроизвести видеокружок">▶</button><input type="range" min="0" max="100" value="0" step="0.1" data-circle-progress aria-label="Прогресс видеокружка"></div></div>`;
  return "";
}

function messageMediaUrl(msg) {
  return msg.mediaData || `/media/messages/${encodeURIComponent(msg.id)}?token=${encodeURIComponent(token)}`;
}

function voiceWaveformFallback(messageId) {
  let seed = [...String(messageId)].reduce((total, char) => (total * 31 + char.charCodeAt(0)) >>> 0, 17);
  return Array.from({ length: 40 }, () => {
    seed = (seed * 1664525 + 1013904223) >>> 0;
    return 18 + (seed % 68);
  });
}

function mediaDownloadExtension(mimeType, mediaType) {
  const extensions = {
    "audio/mp4": "m4a",
    "video/mp4": "mp4",
    "audio/webm": "webm",
    "video/webm": "webm",
    "audio/ogg": "ogg",
    "audio/wav": "wav",
    "video/quicktime": "mov",
  };
  return extensions[mimeType.split(";", 1)[0].toLowerCase()] || (mediaType === "voice" ? "m4a" : "mp4");
}

async function downloadMessageMedia(msg) {
  if (!["voice", "circle"].includes(msg.mediaType)) return;
  const response = await fetch(messageMediaUrl(msg));
  if (!response.ok) throw new Error("Не удалось скачать медиафайл.");
  const blob = await response.blob();
  if (!blob.size) throw new Error("Медиафайл пуст.");
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  const prefix = msg.mediaType === "voice" ? "голосовое" : "видеокружок";
  link.href = url;
  link.download = `${prefix}-${msg.id}.${mediaDownloadExtension(blob.type, msg.mediaType)}`;
  link.style.display = "none";
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  toast("Скачивание началось.");
}

function insertIntoComposer(value) {
  const input = app.querySelector("#composer textarea");
  if (!input) return;
  const start = input.selectionStart || input.value.length;
  input.value = `${input.value.slice(0, start)}${value}${input.value.slice(input.selectionEnd || start)}`;
  input.focus();
  input.selectionStart = input.selectionEnd = start + value.length;
}

function toggleReactionPicker(messageId) {
  const picker = app.querySelector(`[data-reaction-picker="${messageId}"]`);
  const shouldOpen = picker?.classList.contains("hidden");
  closeReactionPickers();
  if (shouldOpen) picker.classList.remove("hidden");
}

function closeReactionPickers() { app.querySelectorAll("[data-reaction-picker]").forEach((box) => box.classList.add("hidden")); }

function showMessageReactionBurst(emoji, source) {
  const rect = source.getBoundingClientRect();
  const burst = document.createElement("span");
  burst.className = "message-reaction-burst";
  burst.textContent = emoji;
  burst.style.left = `${rect.left + rect.width / 2}px`;
  burst.style.top = `${rect.top + rect.height / 2}px`;
  document.body.append(burst);
  burst.addEventListener("animationend", () => burst.remove());
}

function showStoryReactionBurst(emoji, source) {
  const rect = source.getBoundingClientRect();
  const burst = document.createElement("span");
  burst.className = "story-reaction-burst";
  burst.textContent = emoji;
  burst.style.left = `${rect.left + rect.width / 2}px`;
  burst.style.top = `${rect.top - 12}px`;
  document.body.append(burst);
  burst.addEventListener("animationend", () => burst.remove());
}

function openStoryShareDialog(story, closeStory) {
  const recipients = state.users.filter((user) => user.id !== state.me.id);
  const overlay = document.createElement("div");
  overlay.className = "member-manager-overlay story-share-overlay";
  overlay.innerHTML = `<section class="member-manager story-share-dialog" role="dialog" aria-modal="true" aria-label="Отправка сторис"><header><div><b>Поделиться сторис</b><small>Выберите получателя</small></div><button class="member-manager__close" type="button" aria-label="Закрыть">×</button></header><div class="member-manager__list">${recipients.map((user) => `<button class="member-manager__user" type="button" data-share-story-to="${user.id}">${avatarHtml(user)}<span><b>${esc(user.name)}</b><small>@${esc(user.username)}</small></span><em>Отправить</em></button>`).join("") || '<p class="muted">Нет доступных получателей.</p>'}</div></section>`;
  document.body.append(overlay);
  const close = () => overlay.remove();
  overlay.querySelector(".member-manager__close").addEventListener("click", close);
  overlay.addEventListener("click", (event) => { if (event.target === overlay) close(); });
  overlay.querySelectorAll("[data-share-story-to]").forEach((button) => button.addEventListener("click", async () => {
    try {
      const result = await api("/api/stories/share", { method: "POST", body: { storyId: story.id, recipientId: button.dataset.shareStoryTo } });
      activeChatId = result.chatId;
      activeSection = "chats";
      close();
      closeStory();
      await refresh();
      toast("Сторис отправлена.");
    } catch (error) { toast(error.message, true); }
  }));
}

function openProfile(userId) {
  profileReturnSection = activeSection === "profile" ? "chats" : activeSection;
  openedProfileId = userId;
  activeSection = "profile";
  renderApp();
}

function closeProfile() { openedProfileId = null; activeSection = profileReturnSection || "chats"; renderApp(); }

async function openDirectChat(userId) {
  const data = await api("/api/chats", { method: "POST", body: { type: "direct", userId } });
  activeChatId = data.chat.id;
  scrollChatToLatest = true;
  activeSection = "chats";
  await refresh();
}

function pickRecordingMimeType(type) {
  const isSafari = /^((?!chrome|android).)*safari/i.test(navigator.userAgent);
  const candidates = type === "voice"
    ? (isSafari ? ["audio/mp4;codecs=mp4a.40.2", "audio/mp4", "audio/webm;codecs=opus", "audio/webm"] : ["audio/webm;codecs=opus", "audio/webm", "audio/mp4;codecs=mp4a.40.2", "audio/mp4"])
    : ["video/mp4;codecs=avc1.42E01E,mp4a.40.2", "video/mp4", "video/webm;codecs=vp8,opus", "video/webm"];
  const supported = candidates.filter((mimeType) => MediaRecorder.isTypeSupported(mimeType));
  return supported[0] || "";
}

async function recordMediaMessage(chatId, type) {
  if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) return toast("Браузер не поддерживает запись.", true);
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: type === "circle" });
    const mimeType = pickRecordingMimeType(type);
    const recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
    const chunks = [];
    const recordingUi = showRecordingOverlay(type, stream);
    let cancelled = false;
    recorder.ondataavailable = (event) => { if (event.data.size) chunks.push(event.data); };
    recorder.onerror = () => {
      cancelled = true;
      stream.getTracks().forEach((track) => track.stop());
      recordingUi.close();
      toast("Не удалось записать медиа. Проверьте разрешения камеры и микрофона.", true);
    };
    recorder.onstop = async () => {
      stream.getTracks().forEach((track) => track.stop());
      recordingUi.close();
      if (cancelled) return;
      try {
        const recordedMimeType = recorder.mimeType || chunks.find((chunk) => chunk.type)?.type || mimeType;
        if (!chunks.length || !recordedMimeType.startsWith(type === "voice" ? "audio/" : "video/")) return toast("Запись не была создана. Попробуйте ещё раз.", true);
        const blob = new Blob(chunks, { type: recordedMimeType });
        if (blob.size > 3_600_000) return toast("Запись получилась слишком большой. Запишите более короткое сообщение.", true);
        const mediaData = await blobToDataUrl(blob);
        if (mediaData.length > 5_000_000) return toast("Запись получилась слишком большой. Запишите более короткое сообщение.", true);
        const temporaryId = `pending-${crypto.randomUUID()}`;
        const pendingStartedAt = Date.now();
        pendingOutgoingMessages.set(temporaryId, {
          id: temporaryId,
          chatId,
          senderId: state.me.id,
          text: "",
          mediaType: type,
          mediaData,
          createdAt: Math.floor(pendingStartedAt / 1000),
          deliveryState: "sending",
        });
        scrollChatToLatest = true;
        renderChat();
        await api("/api/messages", { method: "POST", body: { chatId, text: "", mediaType: type, mediaData, voiceWaveform: type === "voice" ? recordingUi.waveform() : [] } });
        const remainingAnimation = 360 - (Date.now() - pendingStartedAt);
        if (remainingAnimation > 0) await new Promise((resolve) => window.setTimeout(resolve, remainingAnimation));
        pendingOutgoingMessages.delete(temporaryId);
        await refresh(false);
      } catch (error) {
        const pending = [...pendingOutgoingMessages.entries()].find(([, message]) => message.chatId === chatId && message.mediaType === type && message.deliveryState === "sending");
        if (pending) {
          pending[1].deliveryState = "failed";
          pendingOutgoingMessages.set(pending[0], pending[1]);
          renderChat();
        }
        toast(error.message || "Не удалось подготовить запись к отправке.", true);
      }
    };
    recordingUi.onCancel(() => { cancelled = true; if (recorder.state !== "inactive") recorder.stop(); });
    recordingUi.onStop(() => { if (recorder.state !== "inactive") recorder.stop(); });
    recorder.start(250);
  } catch (error) {
    toast(error.name === "NotAllowedError" ? "Разрешите доступ к микрофону/камере." : error.message, true);
  }
}

function showRecordingOverlay(type, stream) {
  const overlay = document.createElement("div");
  overlay.className = "recording-overlay";
  overlay.innerHTML = type === "circle"
    ? `<div class="recording-card recording-circle-card"><video autoplay muted playsinline></video><div class="recording-status"><span class="recording-dot"></span> Запись кружка <b data-record-time>0:00</b></div><div class="recording-actions"><button class="button" data-cancel>Отмена</button><button class="button danger" data-stop>Остановить и отправить</button></div></div>`
    : `<div class="recording-card"><div class="recording-status"><span class="recording-dot"></span> Голосовое сообщение <b data-record-time>0:00</b></div><div class="voice-wave" data-wave>${Array.from({ length: 34 }, () => '<i></i>').join("")}</div><p class="muted">Говорите — дорожка показывает уровень звука</p><div class="recording-actions"><button class="button" data-cancel>Отмена</button><button class="button danger" data-stop>Остановить и отправить</button></div></div>`;
  document.body.append(overlay);
  const video = overlay.querySelector("video");
  if (video) video.srcObject = stream;
  const startedAt = Date.now();
  const timer = setInterval(() => {
    const seconds = Math.floor((Date.now() - startedAt) / 1000);
    overlay.querySelector("[data-record-time]").textContent = `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
  }, 250);
  let analyser;
  let audioContext;
  let animation;
  const waveform = [];
  if (type === "voice") {
    audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const source = audioContext.createMediaStreamSource(stream);
    analyser = audioContext.createAnalyser();
    analyser.fftSize = 64;
    source.connect(analyser);
    const data = new Uint8Array(analyser.frequencyBinCount);
    const bars = [...overlay.querySelectorAll("[data-wave] i")];
    const animate = () => {
      analyser.getByteFrequencyData(data);
      const level = Math.round(data.reduce((sum, value) => sum + value, 0) / data.length / 255 * 100);
      if (waveform.length < 48) waveform.push(level);
      else waveform[Math.floor((Date.now() - startedAt) / 120) % waveform.length] = level;
      bars.forEach((bar, index) => { bar.style.height = `${5 + (data[index % data.length] / 255) * 38}px`; });
      animation = requestAnimationFrame(animate);
    };
    animate();
  }
  const close = () => {
    clearInterval(timer);
    if (animation) cancelAnimationFrame(animation);
    audioContext?.close?.();
    overlay.remove();
  };
  return {
    close,
    waveform() { return waveform.length ? waveform : Array.from({ length: 40 }, () => 12); },
    onCancel(handler) { overlay.querySelector("[data-cancel]").addEventListener("click", handler); },
    onStop(handler) { overlay.querySelector("[data-stop]").addEventListener("click", handler); },
  };
}

async function donateToChannelMessage(message) {
  const recipient = userById(message.senderId);
  if (!recipient || recipient.id === state.me.id) {
    toast(recipient ? "Нельзя отправить звёзды самому себе." : "Получатель не найден.", true);
    return;
  }
  const overlay = document.createElement("div");
  overlay.className = "member-manager-overlay";
  overlay.innerHTML = `<section class="member-manager" role="dialog" aria-modal="true" aria-label="Подарить звёзды"><header><div><b>Подарить звёзды</b><small>За публикацию ${esc(recipient.name)} · доступно ★ ${state.me.stars || 0}</small></div><button class="member-manager__close" type="button" aria-label="Закрыть">×</button></header><form class="form" data-donation-form><label>Количество звёзд<input name="amount" type="number" min="1" max="${Math.max(1, Number(state.me.stars) || 0)}" step="1" required autofocus value="5"></label><p class="muted">Звёзды будут сразу зачислены автору публикации.</p><button class="button primary" ${state.me.stars > 0 ? "" : "disabled"}>Отправить</button></form></section>`;
  document.body.append(overlay);
  const close = () => overlay.remove();
  overlay.querySelector(".member-manager__close").addEventListener("click", close);
  overlay.addEventListener("click", (event) => { if (event.target === overlay) close(); });
  overlay.querySelector("[data-donation-form]").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const amount = Number(new FormData(event.currentTarget).get("amount"));
      await api("/api/donate", { method: "POST", body: { messageId: message.id, amount } });
      close();
      await refresh();
      toast("Звёзды отправлены.");
    } catch (error) { toast(error.message, true); }
  });
}

async function editUsername() {
  const username = prompt("Новый username", state.me.username);
  if (!username) return;
  try { await api("/api/username", { method: "POST", body: { username } }); toast("Username изменён."); await refresh(); }
  catch (error) { toast(error.message, true); }
}

async function refresh(full = true) { await loadState(); full ? renderApp() : (renderChat(), renderRight()); }

async function markChatRead(chatId) {
  const chat = state.chats.find((item) => item.id === chatId);
  if (!chat?.unreadCount) return;
  try {
    await api("/api/messages/read", { method: "POST", body: { chatId } });
    chat.unreadCount = 0;
    state.messages.filter((message) => message.chatId === chatId).forEach((message) => { message.unread = false; });
    app.querySelector(`.chat-row [data-chat="${chatId}"] .unread-badge`)?.remove();
    app.querySelector(`.chat-row [data-chat="${chatId}"]`)?.closest(".chat-row")?.classList.remove("has-unread");
  } catch { /* A subsequent polling cycle will retry the read status. */ }
}

function beginMessagePolling() {
  clearInterval(messagePollTimer);
  messagePollTimer = setInterval(async () => {
    if (!token || !state) return;
    const knownMessageIds = new Set(state.messages.map((message) => message.id));
    const previousListSignature = chatListSignature();
    const previousStoriesSignature = state.stories.map((story) => `${story.id}:${Number(story.viewed)}`).join("|");
    try {
      await loadState();
      const hasNewActiveMessage = activeChatId && state.messages.some((message) => message.chatId === activeChatId && !knownMessageIds.has(message.id));
      const shouldUpdateLeft = previousListSignature !== chatListSignature() || previousStoriesSignature !== state.stories.map((story) => `${story.id}:${Number(story.viewed)}`).join("|");
      if (shouldUpdateLeft && activeSection !== "settings" && document.activeElement?.id !== "userSearch") renderLeft();
      const composer = app.querySelector("#composer textarea");
      if (hasNewActiveMessage && !composer?.value) renderChat();
    } catch { /* The next cycle will retry after a temporary connection error. */ }
  }, 3000);
}

function beginCallPolling() {
  clearInterval(callPollTimer);
  callPollTimer = setInterval(pollCalls, 1500);
  pollCalls();
}

async function startCall(chat, callType) {
  if (!navigator.mediaDevices?.getUserMedia || !window.RTCPeerConnection) {
    toast("Этот браузер не поддерживает звонки.", true);
    return;
  }
  if (activeCall) { toast("Сначала завершите текущий звонок.", true); return; }
  let stream = null;
  let peer = null;
  const pendingCall = { callType, role: "caller", chatId: chat.id, pending: true, peer: null, stream: null, remoteStream: null };
  try {
    activeCall = pendingCall;
    showCallOverlay(`Звоним: ${chatMeta(chat).title}`, callType, null);
    updateCallOverlay("Подготавливаем звонок…");
    stream = await navigator.mediaDevices.getUserMedia(callMediaConstraints(callType));
    if (activeCall !== pendingCall) {
      stream.getTracks().forEach((track) => track.stop());
      return;
    }
    peer = createPeer(stream);
    Object.assign(pendingCall, { peer, stream, remoteStream: peer.remoteStream || null });
    const localVideo = document.querySelector("[data-local-video]");
    if (localVideo) {
      localVideo.srcObject = stream;
      localVideo.play().catch(() => {});
    }
    const offer = await peer.createOffer();
    await peer.setLocalDescription(offer);
    await waitForIce(peer);
    const response = await api("/api/calls/start", { method: "POST", body: { chatId: chat.id, callType, offerSdp: peer.localDescription } });
    if (activeCall !== pendingCall) {
      await api("/api/calls/end", { method: "POST", body: { callId: response.callId } });
      return;
    }
    Object.assign(pendingCall, { id: response.callId, pending: false });
    updateCallOverlay("Ожидаем ответа…");
    startRingTone();
  } catch (error) {
    peer?.close();
    stream?.getTracks().forEach((track) => track.stop());
    if (activeCall === pendingCall) activeCall = null;
    document.querySelector(".call-overlay")?.remove();
    toast(error.name === "NotAllowedError" ? "Разрешите доступ к микрофону и камере." : error.message, true);
  }
}

async function pollCalls() {
  if (!token) return;
  try {
    const data = await api("/api/calls/poll");
    const incoming = data.calls.find((call) => call.receiverId === state.me.id && call.status === "ringing");
    if (incoming && (!activeCall || activeCall.id !== incoming.id)) showIncomingCall(incoming);
    if (activeCall?.role === "caller" && activeCall.id) {
      const remote = data.calls.find((call) => call.id === activeCall.id);
      if (remote?.answerSdp && !activeCall.answerApplied) {
        await activeCall.peer.setRemoteDescription(new RTCSessionDescription(remote.answerSdp));
        activeCall.answerApplied = true;
        updateCallOverlay("Звонок подключён");
        stopRingTone();
      }
      if (!remote) finishCall(false);
    }
    if (activeCall?.role === "receiver" && !data.calls.some((call) => call.id === activeCall.id)) finishCall(false);
  } catch { /* Server may be restarting; the next poll will retry. */ }
}

function showIncomingCall(call) {
  document.querySelector(".incoming-call")?.remove();
  const box = document.createElement("div");
  box.className = "incoming-call";
  box.innerHTML = `<div><b>${esc(call.callerName)} звонит</b><p>${call.callType === "video" ? "Видеозвонок" : "Аудиозвонок"}</p><div class="incoming-call__actions"><button class="button call-action--accept" data-accept>${callControlIcon("accept")}<span>Принять</span></button><button class="button danger" data-decline>${callControlIcon("decline")}<span>Отклонить</span></button></div></div>`;
  document.body.append(box);
  startRingTone();
  box.querySelector("[data-accept]").addEventListener("click", () => acceptCall(call));
  box.querySelector("[data-decline]").addEventListener("click", async () => { stopRingTone(); await api("/api/calls/end", { method: "POST", body: { callId: call.id } }); box.remove(); });
}

async function acceptCall(call) {
  document.querySelector(".incoming-call")?.remove();
  stopRingTone();
  if (activeCall) return;
  let stream = null;
  let peer = null;
  try {
    stream = await navigator.mediaDevices.getUserMedia(callMediaConstraints(call.callType));
    peer = createPeer(stream);
    await peer.setRemoteDescription(new RTCSessionDescription(call.offerSdp));
    const answer = await peer.createAnswer();
    await peer.setLocalDescription(answer);
    await waitForIce(peer);
    await api("/api/calls/answer", { method: "POST", body: { callId: call.id, answerSdp: peer.localDescription } });
    activeCall = { id: call.id, peer, stream, remoteStream: peer.remoteStream || null, callType: call.callType, role: "receiver", chatId: call.chatId };
    showCallOverlay(`Звонок: ${call.callerName}`, call.callType, stream, null);
    updateCallOverlay("Звонок подключён");
  } catch (error) {
    peer?.close();
    stream?.getTracks().forEach((track) => track.stop());
    await api("/api/calls/end", { method: "POST", body: { callId: call.id } });
    toast(error.name === "NotAllowedError" ? "Разрешите доступ к микрофону и камере." : error.message, true);
  }
}

function callMediaConstraints(callType) {
  return {
    audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
    video: callType === "video"
      ? { facingMode: "user", width: { ideal: 1280 }, height: { ideal: 720 }, frameRate: { ideal: 30, max: 30 } }
      : false,
  };
}

function attachRemoteStream(stream) {
  const remote = document.querySelector("[data-remote-video]");
  if (!stream || !remote || remote.srcObject === stream) return;
  remote.srcObject = stream;
  remote.play().catch(() => {});
  startCallVoiceActivity("remote", stream);
}

function startCallVoiceActivity(side, stream) {
  if (!stream?.getAudioTracks?.().length) return;
  stopCallVoiceActivity(side);
  const AudioContext = window.AudioContext || window.webkitAudioContext;
  if (!AudioContext) return;
  const context = new AudioContext();
  const analyser = context.createAnalyser();
  analyser.fftSize = 512;
  analyser.smoothingTimeConstant = 0.74;
  const source = context.createMediaStreamSource(stream);
  source.connect(analyser);
  const data = new Uint8Array(analyser.fftSize);
  const selector = side === "local" ? "[data-local-video]" : "[data-remote-video]";
  const className = side === "local" ? "is-speaking-local" : "is-speaking-remote";
  let speaking = false;
  const tick = () => {
    if (!activeCall) return;
    analyser.getByteTimeDomainData(data);
    let sum = 0;
    for (const value of data) {
      const normalized = (value - 128) / 128;
      sum += normalized * normalized;
    }
    const level = Math.sqrt(sum / data.length);
    const nextSpeaking = speaking ? level > 0.055 : level > 0.075;
    if (nextSpeaking !== speaking) {
      speaking = nextSpeaking;
      document.querySelector(selector)?.classList.toggle(className, speaking);
    }
    const item = callVoiceActivity.find((entry) => entry.side === side);
    if (item) item.frame = requestAnimationFrame(tick);
  };
  const item = { side, context, source, frame: requestAnimationFrame(tick) };
  callVoiceActivity.push(item);
}

function stopCallVoiceActivity(side) {
  const keep = [];
  callVoiceActivity.forEach((item) => {
    if (side && item.side !== side) {
      keep.push(item);
      return;
    }
    cancelAnimationFrame(item.frame);
    try { item.source.disconnect(); } catch {}
    item.context.close?.();
    const selector = item.side === "local" ? "[data-local-video]" : "[data-remote-video]";
    const className = item.side === "local" ? "is-speaking-local" : "is-speaking-remote";
    document.querySelector(selector)?.classList.remove(className);
  });
  callVoiceActivity = keep;
}

function createPeer(stream) {
  const peer = new RTCPeerConnection({
    iceServers: [
      { urls: "stun:stun.l.google.com:19302" },
      { urls: "stun:stun1.l.google.com:19302" },
    ],
  });
  stream.getTracks().forEach((track) => peer.addTrack(track, stream));
  peer.ontrack = (event) => {
    const remoteStream = event.streams[0] || peer.remoteStream || new MediaStream();
    if (!event.streams[0] && !remoteStream.getTracks().includes(event.track)) remoteStream.addTrack(event.track);
    peer.remoteStream = remoteStream;
    if (activeCall?.peer === peer) activeCall.remoteStream = remoteStream;
    attachRemoteStream(remoteStream);
  };
  let disconnectTimer = null;
  peer.onconnectionstatechange = () => {
    if (peer.connectionState === "connected") {
      clearTimeout(disconnectTimer);
      return;
    }
    if (peer.connectionState === "disconnected") {
      clearTimeout(disconnectTimer);
      disconnectTimer = setTimeout(() => {
        if (peer.connectionState === "disconnected" && activeCall?.peer === peer) finishCall(false);
      }, 8000);
      return;
    }
    if (["failed", "closed"].includes(peer.connectionState) && activeCall?.peer === peer) finishCall(false);
  };
  return peer;
}

function waitForIce(peer) {
  if (peer.iceGatheringState === "complete") return Promise.resolve();
  return new Promise((resolve) => {
    const timeout = setTimeout(resolve, 8000);
    peer.addEventListener("icegatheringstatechange", () => {
      if (peer.iceGatheringState === "complete") { clearTimeout(timeout); resolve(); }
    });
  });
}

function showCallOverlay(title, callType, stream) {
  document.querySelector(".call-overlay")?.remove();
  const box = document.createElement("div");
  box.className = `call-overlay ${chatBackgroundClass(state.me)}`;
  if (state.me.chatBackground === "custom" && state.me.chatBackgroundData) {
    box.style.setProperty("--call-chat-wallpaper", `url('${state.me.chatBackgroundData.replace(/'/g, "\\'")}')`);
  }
  const cameraControl = callType === "video" ? `<button class="button call-control" data-toggle-camera>${callControlIcon("camera")}<span data-camera-label>Камера вкл.</span></button>` : "";
  box.innerHTML = `<div class="call-window"><div class="call-window__head"><div><h2>${esc(title)}</h2><p data-call-status>Подключение…</p></div><div class="call-window__view-actions"><button class="button call-control" data-toggle-call-fullscreen aria-label="На весь экран" title="На весь экран">${callControlIcon("expand")}<span data-fullscreen-label>На весь экран</span></button><button class="button call-control" data-toggle-call-minimized aria-label="Свернуть звонок" title="Свернуть звонок">${callControlIcon("minimize")}<span data-minimize-label>Свернуть</span></button></div></div><div class="call-videos ${callType === "audio" ? "audio-only" : ""}"><video class="call-videos__remote" data-remote-video autoplay playsinline></video><video class="call-videos__local" data-local-video autoplay muted playsinline></video></div><div class="call-actions"><button class="button call-control" data-toggle-mic>${callControlIcon("microphone")}<span data-mic-label>Микрофон вкл.</span></button>${cameraControl}<button class="button call-control" data-toggle-pause>${callControlIcon("pause")}<span data-pause-label>Пауза</span></button><button class="button danger call-control" data-end-call>${callControlIcon("end")}<span>Завершить звонок</span></button></div></div>`;
  document.body.append(box);
  const localVideo = box.querySelector("[data-local-video]");
  if (stream) {
    localVideo.srcObject = stream;
    localVideo.play().catch(() => {});
    startCallVoiceActivity("local", stream);
  }
  attachRemoteStream(activeCall?.remoteStream);
  box.querySelector("[data-end-call]").addEventListener("click", () => finishCall());
  box.querySelector("[data-toggle-mic]").addEventListener("click", toggleMicrophone);
  box.querySelector("[data-toggle-camera]")?.addEventListener("click", toggleCamera);
  box.querySelector("[data-toggle-pause]").addEventListener("click", toggleCallPause);
  box.querySelector("[data-toggle-call-fullscreen]").addEventListener("click", toggleCallFullscreen);
  box.querySelector("[data-toggle-call-minimized]").addEventListener("click", toggleCallMinimized);
}

function updateCallOverlay(message) { const status = document.querySelector("[data-call-status]"); if (status) status.textContent = message; }
function toggleCallFullscreen() {
  const overlay = document.querySelector(".call-overlay");
  if (!overlay) return;
  const fullScreen = !overlay.classList.contains("is-fullscreen");
  overlay.classList.toggle("is-fullscreen", fullScreen);
  overlay.classList.remove("is-minimized");
  if (fullScreen) overlay.requestFullscreen?.().catch(() => {});
  else if (document.fullscreenElement === overlay) document.exitFullscreen?.().catch(() => {});
  const label = overlay.querySelector("[data-fullscreen-label]");
  const button = overlay.querySelector("[data-toggle-call-fullscreen]");
  if (label) label.textContent = fullScreen ? "Обычный размер" : "На весь экран";
  if (button) {
    button.setAttribute("aria-label", fullScreen ? "Выйти из полноэкранного режима" : "На весь экран");
    button.setAttribute("title", fullScreen ? "Выйти из полноэкранного режима" : "На весь экран");
    button.innerHTML = `${callControlIcon(fullScreen ? "shrink" : "expand")}<span data-fullscreen-label>${fullScreen ? "Обычный размер" : "На весь экран"}</span>`;
  }
}
function toggleCallMinimized() {
  const overlay = document.querySelector(".call-overlay");
  if (!overlay) return;
  const minimized = overlay.classList.toggle("is-minimized");
  if (document.fullscreenElement === overlay) document.exitFullscreen?.().catch(() => {});
  overlay.classList.remove("is-fullscreen");
  const label = overlay.querySelector("[data-minimize-label]");
  const button = overlay.querySelector("[data-toggle-call-minimized]");
  if (label) label.textContent = minimized ? "Открыть" : "Свернуть";
  if (button) {
    button.setAttribute("aria-label", minimized ? "Открыть звонок" : "Свернуть звонок");
    button.setAttribute("title", minimized ? "Открыть звонок" : "Свернуть звонок");
    button.innerHTML = `${callControlIcon(minimized ? "expand" : "minimize")}<span data-minimize-label>${minimized ? "Открыть" : "Свернуть"}</span>`;
  }
}
function toggleMicrophone(event) {
  const audioTrack = activeCall?.stream?.getAudioTracks()[0];
  if (!audioTrack) return;
  audioTrack.enabled = !audioTrack.enabled;
  event.currentTarget.innerHTML = `${callControlIcon(audioTrack.enabled ? "microphone" : "microphoneOff")}<span data-mic-label>${audioTrack.enabled ? "Микрофон вкл." : "Микрофон выкл."}</span>`;
}
function toggleCamera(event) {
  const videoTrack = activeCall?.stream?.getVideoTracks()[0];
  if (!videoTrack) return;
  videoTrack.enabled = !videoTrack.enabled;
  event.currentTarget.innerHTML = `${callControlIcon(videoTrack.enabled ? "camera" : "cameraOff")}<span data-camera-label>${videoTrack.enabled ? "Камера вкл." : "Камера выкл."}</span>`;
}
function toggleCallPause(event) {
  if (!activeCall?.stream) return;
  activeCall.paused = !activeCall.paused;
  activeCall.stream.getTracks().forEach((track) => { track.enabled = !activeCall.paused; });
  event.currentTarget.innerHTML = `${callControlIcon(activeCall.paused ? "play" : "pause")}<span data-pause-label>${activeCall.paused ? "Продолжить" : "Пауза"}</span>`;
  updateCallOverlay(activeCall.paused ? "Звонок на паузе" : "Звонок подключён");
}
function startRingTone() {
  stopRingTone();
  const AudioContext = window.AudioContext || window.webkitAudioContext;
  if (!AudioContext) return;
  const context = new AudioContext();
  const gain = context.createGain();
  gain.gain.value = 0.04;
  gain.connect(context.destination);
  const playBeep = () => {
    const oscillator = context.createOscillator();
    oscillator.type = "sine";
    oscillator.frequency.value = 440;
    oscillator.connect(gain);
    oscillator.start();
    oscillator.stop(context.currentTime + 0.18);
  };
  playBeep();
  ringTone = { context, timer: setInterval(playBeep, 1400) };
}
function stopRingTone() {
  if (!ringTone) return;
  clearInterval(ringTone.timer);
  ringTone.context.close?.();
  ringTone = null;
}
async function finishCall(notify = true) {
  const call = activeCall;
  activeCall = null;
  stopRingTone();
  stopCallVoiceActivity();
  document.querySelector(".call-overlay")?.remove();
  document.querySelector(".incoming-call")?.remove();
  if (!call) return;
  call.stream?.getTracks().forEach((track) => track.stop());
  call.peer?.close();
  if (notify && call.id) { try { await api("/api/calls/end", { method: "POST", body: { callId: call.id } }); } catch {} }
}
function hasChatMessages(chatId) { return state.messages.some((message) => message.chatId === chatId); }
function shouldShowChatInList(chat) { return chat.type !== "direct" || hasChatMessages(chat.id); }
function visibleChats(archived = false) { return state.chats.filter((chat) => chat.type !== "secret" && isMember(chat.id) && shouldShowChatInList(chat) && Boolean(chat.archived) === archived).sort((a, b) => Number(b.pinned) - Number(a.pinned) || b.updatedAt - a.updatedAt); }
function chatListSignature() {
  return visibleChats(false)
    .map((chat) => `${chat.id}:${chat.updatedAt}:${latestChatMessage(chat.id)?.id || ""}:${chat.unreadCount || 0}:${Number(chat.pinned)}:${Number(chat.archived)}`)
    .join("|");
}
function isMember(chatId) { return state.members.some((m) => m.chat_id === chatId && m.user_id === state.me.id); }
function chatMemberRole(chatId, userId = state.me.id) { return state.members.find((member) => member.chat_id === chatId && member.user_id === userId)?.role || null; }
function isChannelManagerRole(role) { return ["owner", "admin", "author"].includes(role); }
function canPinMessageForEveryone(message) {
  const chat = state.chats.find((item) => item.id === message.chatId);
  return chat?.type !== "channel" || isChannelManagerRole(chatMemberRole(message.chatId));
}
function canDeleteMessageForEveryone(message) { return message.senderId === state.me.id || (["group", "community", "channel"].includes(state.chats.find((chat) => chat.id === message.chatId)?.type) && ["owner", "admin"].includes(chatMemberRole(message.chatId))); }
function userById(id) { return state.users.find((user) => user.id === id); }
function chatIcon(chat) { return chat.type === "saved" ? "★" : chat.type === "group" ? "G" : chat.type === "community" ? "C" : chat.type === "channel" ? "К" : initials(chat.title); }
function chatAvatarHtml(chat, className = "avatar") { return chat.avatarData ? `<img class="${className}" src="${esc(chat.avatarData)}" alt="">` : `<div class="${className}">${esc(chatIcon(chat))}</div>`; }
function memberWord(count) { return count % 10 === 1 && count % 100 !== 11 ? "участник" : count % 10 >= 2 && count % 10 <= 4 && (count % 100 < 10 || count % 100 >= 20) ? "участника" : "участников"; }
function subscriberWord(count) { return count % 10 === 1 && count % 100 !== 11 ? "подписчик" : count % 10 >= 2 && count % 10 <= 4 && (count % 100 < 10 || count % 100 >= 20) ? "подписчика" : "подписчиков"; }
function chatMeta(chat) {
  if (chat.type === "saved") return { icon: "★", title: "Избранное", subtitle: "Пишите самому себе" };
  if (chat.type === "direct") {
    const member = state.members.find((m) => m.chat_id === chat.id && m.user_id !== state.me.id);
    const user = userById(member?.user_id);
    return { icon: initials(user?.name || "?"), title: user?.name || "Пользователь", subtitle: user ? `@${user.username}` : "", user };
  }
  const parts = [];
  if ((chat.settings || {}).showSubscribers !== false) parts.push(`${chat.subscriberCount} подписчиков`);
  parts.push(chat.type === "group" ? "группа" : chat.type === "channel" ? "канал" : "комьюнити");
  return { icon: chatIcon(chat), title: chat.title, subtitle: parts.join(" · ") };
}
function reviewStats() {
  return state.reviews.reduce((acc, review) => {
    const url = normalizeReviewIdentifier(review.url);
    acc[url] ||= { url, sourceType: review.sourceType || (isReviewUrl(url) ? "website" : "other"), score: 0, count: 0, positive: 0, negative: 0, links: [] };
    acc[url].score += review.rating;
    acc[url].count += 1;
    if (review.rating > 0) acc[url].positive += 1;
    else acc[url].negative += 1;
    acc[url].links.push(...(review.links || []).map(normalizeReviewIdentifier));
    return acc;
  }, {});
}
function reviewRelatedUrls(url) {
  const normalizedUrl = normalizeReviewIdentifier(url);
  const linked = state.reviews.filter((review) => normalizeReviewIdentifier(review.url) === normalizedUrl).flatMap((review) => (review.links || []).map(normalizeReviewIdentifier));
  const reciprocal = state.reviews.filter((review) => (review.links || []).map(normalizeReviewIdentifier).includes(normalizedUrl)).map((review) => normalizeReviewIdentifier(review.url));
  return [...new Set([...linked, ...reciprocal])].filter((item) => item !== normalizedUrl);
}
function isReviewUrl(value) { return /^https?:\/\//i.test(String(value || "").trim()); }
function isReviewPhone(value) { const source = String(value || "").trim(); const digits = source.replace(/\D/g, ""); return /^[+\d()\-\s.]+$/.test(source) && digits.length >= 7 && digits.length <= 15; }
function isReviewTelegram(value) { return /^@?[A-Za-z0-9_]{3,64}$/.test(String(value || "").trim()); }
function normalizeReviewIdentifier(value) { const source = String(value || "").trim().replace(/\s+/g, " "); return isReviewUrl(source) ? source : isReviewPhone(source) ? `+${source.replace(/\D/g, "")}` : isReviewTelegram(source) ? `@${source.replace(/^@/, "").toLowerCase()}` : source.toLowerCase(); }
function sourceTypeBadge(sourceType) { const labels = { telegram: "Telegram", instagram: "Instagram", other: "Другая", website: "Сайт", phone: "Телефон" }; const title = labels[sourceType] || String(sourceType || "").trim(); return title ? `<span class="review-source-type">${esc(title)}</span>` : ""; }
function reviewWord(count) { return count % 10 === 1 && count % 100 !== 11 ? "отзыв" : count % 10 >= 2 && count % 10 <= 4 && (count % 100 < 10 || count % 100 >= 20) ? "отзыва" : "отзывов"; }
function myStatuses() { return state.userStatuses.filter((us) => us.user_id === state.me.id).map((us) => state.statuses.find((s) => s.id === us.status_id)).filter(Boolean); }
function visibleStatusesFor(userId) { const hidden = new Set(userById(userId)?.hiddenStatusIds || []); return state.userStatuses.filter((us) => us.user_id === userId && !hidden.has(us.status_id)).map((us) => state.statuses.find((s) => s.id === us.status_id)).filter(Boolean); }
function currentLimits() { return state.accountLevel?.limits || state.accountLevel?.current?.limits || state.settings.limits?.[isPremium(state.me) ? "premium" : "regular"] || {}; }
function isPremium(user) { return user.premiumUntil && user.premiumUntil > Math.floor(Date.now() / 1000); }
function premiumBadge(user) { return isPremium(user) ? '<span class="badge">PREMIUM</span>' : ""; }
function avatarHtml(user, className = "avatar") { const storyClass = user?.id && hasUnseenStory(user.id) && !className.includes("message__author-avatar") ? " has-story" : ""; return user?.avatarData ? `<img class="${className}${storyClass}" src="${esc(user.avatarData)}" alt="">` : `<div class="${className}${storyClass}">${esc(initials(user?.name || "U"))}</div>`; }
function storyHtml(story) { const user = userById(story.user_id); const own = story.user_id === state.me.id; return `<button class="story${story.viewed ? "" : " has-story"}" data-open-story="${story.id}"><img src="${esc(story.media_data)}" alt="Сторис"><b>${esc(user?.name || "Пользователь")}</b><span>${own ? `👁 ${story.viewerCount || 0}${story.permanent ? " · постоянная" : ""}` : esc(story.caption || "")}</span></button>`; }
function postHtml(post) {
  const user = userById(post.user_id);
  const reactions = Object.entries(post.reactions || {}).filter(([, count]) => Number(count) > 0);
  return `<article class="post">${avatarHtml(user)}<div class="post__body"><div class="post__author"><b>${esc(user?.name || "Пользователь")}</b><button class="post__menu" type="button" data-post-menu="${post.id}" aria-label="Действия с публикацией" title="Действия с публикацией">☰</button></div>${post.media_data ? `<button class="media-button" type="button" data-open-profile-post="${post.id}" aria-label="Открыть публикацию"><img class="post-photo" src="${esc(post.media_data)}" alt="Фото публикации"></button>` : ""}${post.text ? `<p>${esc(post.text)}</p>` : ""}${reactions.length ? `<div class="post-reactions">${reactions.map(([emoji, count]) => `<span>${esc(emoji)} ${count}</span>`).join("")}</div>` : ""}<span class="muted">${timeFmt(post.created_at)}</span></div></article>`;
}
function openProfilePost(postId) {
  const post = state.posts.find((item) => item.id === postId);
  if (!post) return;
  const author = userById(post.user_id);
  const reactions = Object.entries(post.reactions || {}).filter(([, count]) => Number(count) > 0);
  const emojis = ["❤️", "👍", "🔥", "😂", "😮", "👏"];
  const overlay = document.createElement("div");
  overlay.className = "profile-post-overlay";
  overlay.innerHTML = `<article class="profile-post-viewer" role="dialog" aria-modal="true" aria-label="Публикация"><header><div><b>${esc(author?.name || "Пользователь")}</b><span>${timeFmt(post.created_at)}</span></div><button type="button" data-close-profile-post aria-label="Закрыть">×</button></header>${post.media_data ? `<button type="button" class="profile-post-viewer__media" data-open-media="${esc(post.media_data)}" aria-label="Открыть фото на весь экран"><img src="${esc(post.media_data)}" alt="Фото публикации"></button>` : ""}${post.text ? `<p>${esc(post.text)}</p>` : ""}<footer>${reactions.length ? `<div class="profile-post-viewer__reactions">${reactions.map(([emoji, count]) => `<span>${esc(emoji)} ${count}</span>`).join("")}</div>` : ""}<div class="profile-post-viewer__actions"><div class="profile-post-viewer__emoji-actions">${emojis.map((emoji) => `<button type="button" data-react-profile-post="${post.id}" data-emoji="${esc(emoji)}" aria-label="Выбрать реакцию ${esc(emoji)}">${esc(emoji)}</button>`).join("")}</div><button type="button" class="profile-post-viewer__send-reaction" data-send-profile-post-reaction disabled aria-label="Отправить выбранную реакцию" title="Отправить реакцию">✈</button><button type="button" class="button small" data-share-profile-post="${post.id}">Поделиться</button></div></footer></article>`;
  document.body.append(overlay);
  const close = () => overlay.remove();
  overlay.querySelector("[data-close-profile-post]").addEventListener("click", close);
  overlay.addEventListener("click", (event) => { if (event.target === overlay) close(); });
  overlay.querySelector("[data-open-media]")?.addEventListener("click", (event) => openMedia(event.currentTarget.dataset.openMedia));
  overlay.querySelector("[data-share-profile-post]").addEventListener("click", () => { close(); openGroupContentShare("profile-post", post.id); });
  let selectedReaction = "";
  const sendReaction = overlay.querySelector("[data-send-profile-post-reaction]");
  const updateReactionSelection = () => {
    overlay.querySelectorAll("[data-react-profile-post]").forEach((button) => button.classList.toggle("active", button.dataset.emoji === selectedReaction));
    sendReaction.disabled = !selectedReaction;
  };
  overlay.querySelectorAll("[data-react-profile-post]").forEach((button) => button.addEventListener("click", () => {
    selectedReaction = button.dataset.emoji;
    updateReactionSelection();
  }));
  sendReaction.addEventListener("click", async () => {
    if (!selectedReaction) return;
    try {
      await api("/api/profile/posts/react", { method: "POST", body: { postId: post.id, emoji: selectedReaction } });
      toast("Реакция отправлена автору в личные сообщения.");
      selectedReaction = "";
      updateReactionSelection();
    } catch (error) { toast(error.message, true); }
  });
}
function galleryPostHtml(post) { return `<button class="gallery-photo" data-open-profile-post="${post.id}"><img src="${esc(post.media_data)}" alt="Фото поста"></button>`; }
function limitLabel(key) { return ({ maxStars: "Звёзд на балансе", postsPerDay: "Постов в сутки", storiesPerDay: "Сторис в сутки", storiesPerMonth: "Сторис за 30 дней", groupsJoined: "Подписок на группы", groupsCreated: "Созданных групп", communitiesJoined: "Вступлений в беседы", communitiesCreated: "Созданных бесед", channelsJoined: "Подписок на каналы", channelsCreated: "Созданных каналов", savedAccounts: "Сохранённых входов" })[key] || key; }
function openMedia(source, mediaType = "photo") {
  if (!source) return;
  const isVideo = mediaType === "video";
  const overlay = document.createElement("div");
  overlay.className = "media-overlay";
  overlay.innerHTML = `<button class="media-overlay__close" aria-label="Закрыть">×</button>${isVideo ? `<video controls autoplay playsinline src="${esc(source)}">Ваш браузер не поддерживает видео.</video>` : `<img src="${esc(source)}" alt="Просмотр изображения">`}`;
  document.body.append(overlay);
  const close = () => {
    overlay.querySelector("video")?.pause();
    overlay.remove();
    document.removeEventListener("keydown", onKeyDown);
  };
  const onKeyDown = (event) => { if (event.key === "Escape") close(); };
  overlay.addEventListener("click", (event) => { if (event.target === overlay) close(); });
  overlay.querySelector("button").addEventListener("click", close);
  document.addEventListener("keydown", onKeyDown);
}
function openCircle(messageId) {
  const message = state.messages.find((item) => item.id === messageId && item.mediaType === "circle");
  if (!message) return;
  const overlay = document.createElement("div");
  overlay.className = "circle-overlay";
  overlay.innerHTML = `<section class="circle-viewer"><header><button class="circle-back" type="button" data-close-circle>← <span>Назад к диалогу</span></button><span>Видеокружок</span></header><video autoplay playsinline src="${esc(messageMediaUrl(message))}"></video><div class="circle-viewer__player" aria-label="Управление видеокружком"><button type="button" data-circle-viewer-playback aria-label="Пауза">Ⅱ</button><input type="range" min="0" max="100" value="0" step="0.1" data-circle-viewer-progress aria-label="Прогресс видеокружка"></div></section>`;
  document.body.append(overlay);
  const video = overlay.querySelector("video");
  const playButton = overlay.querySelector("[data-circle-viewer-playback]");
  const progress = overlay.querySelector("[data-circle-viewer-progress]");
  const setProgress = (value) => {
    const normalized = Math.min(100, Math.max(0, Number(value) || 0));
    progress.value = String(normalized);
    progress.style.setProperty("--circle-progress", `${normalized}%`);
  };
  const updatePlayback = () => {
    playButton.textContent = video.paused ? "▶" : "Ⅱ";
    playButton.setAttribute("aria-label", video.paused ? "Воспроизвести" : "Пауза");
  };
  playButton.addEventListener("click", () => { if (video.paused) video.play(); else video.pause(); });
  progress.addEventListener("input", () => { if (video.duration) video.currentTime = (Number(progress.value) / 100) * video.duration; setProgress(progress.value); });
  video.addEventListener("play", updatePlayback);
  video.addEventListener("pause", updatePlayback);
  video.addEventListener("timeupdate", () => { if (video.duration) setProgress((video.currentTime / video.duration) * 100); });
  video.addEventListener("ended", () => { setProgress(0); updatePlayback(); });
  const onKeyDown = (event) => { if (event.key === "Escape") close(); };
  const close = () => { video.pause(); overlay.remove(); document.removeEventListener("keydown", onKeyDown); };
  overlay.querySelector("[data-close-circle]").addEventListener("click", close);
  overlay.addEventListener("click", (event) => { if (event.target === overlay) close(); });
  document.addEventListener("keydown", onKeyDown);
}
async function openStory(storyId) {
  try {
    const data = await api("/api/stories/view", { method: "POST", body: { storyId } });
    await refresh();
    const story = data.story;
    const own = story.user_id === state.me.id;
    const reactions = ["❤️", "🔥", "😍", "😂", "😮", "👏"];
    const overlay = document.createElement("div");
    overlay.className = "story-overlay";
    overlay.innerHTML = `<div class="story-viewer"><button class="media-overlay__close" data-close-story aria-label="Закрыть">×</button><img src="${esc(story.media_data)}" alt="Сторис">${story.caption ? `<p>${esc(story.caption)}</p>` : ""}${own ? `<button class="button small" type="button" data-save-story-permanent ${story.permanent ? "disabled" : ""}>${story.permanent ? "В постоянных" : "Сохранить в постоянные"}</button><section class="story-insights"><b>Просмотры: ${story.viewerCount || 0}</b>${story.viewers?.map((viewer) => `<div class="story-viewer-row"><button class="row" type="button" data-story-viewer="${viewer.id}">${avatarHtml(viewer)}<span>${esc(viewer.name)} ${viewer.storyReaction ? `<b>${esc(viewer.storyReaction)}</b>` : ""}<small>@${esc(viewer.username)}</small></span></button><button class="button danger small" type="button" data-hide-story-from-viewer="${viewer.id}">Скрыть от него</button></div>`).join("") || '<p class="muted">Пока никто не посмотрел.</p>'}</section>` : `<section class="story-reaction-panel"><div class="story-reactions">${reactions.map((emoji) => `<button class="${story.myReaction === emoji ? "active" : ""}" data-story-react="${emoji}" aria-label="Выбрать реакцию ${emoji}">${emoji}</button>`).join("")}</div><button class="story-send-reaction" type="button" data-send-story-reaction disabled><span data-selected-story-reaction>Выберите реакцию</span><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m21 3-7.4 18-3.7-7.3L3 10.1 21 3Z"/><path d="m10 14 4.2-4.2"/></svg></button></section><form class="story-reply" data-story-reply><input name="text" maxlength="1000" placeholder="Ответить на сторис"><button class="button small" type="submit">Ответить</button></form><div class="story-actions"><button class="button small" type="button" data-share-story>Поделиться</button><button class="button small" type="button" data-share-story-to-group>В группу</button><button class="button small" type="button" data-report-story>Пожаловаться</button></div><button class="story-hide-author" type="button" data-hide-current-story-author title="Скрыть сторис пользователя" aria-label="Скрыть сторис пользователя">◉</button>`}</div>`;
    document.body.append(overlay);
    const close = () => overlay.remove();
    overlay.querySelector("[data-close-story]").addEventListener("click", close);
    overlay.addEventListener("click", (event) => { if (event.target === overlay) close(); });
    overlay.querySelectorAll("[data-story-viewer]").forEach((button) => button.addEventListener("click", () => { close(); openProfile(button.dataset.storyViewer); }));
    overlay.querySelectorAll("[data-hide-story-from-viewer]").forEach((button) => button.addEventListener("click", async () => { await setStoryPrivacyHidden(button.dataset.hideStoryFromViewer, true); close(); }));
    overlay.querySelector("[data-hide-current-story-author]")?.addEventListener("click", async () => { await setStoryAuthorHidden(story.user_id, true); close(); });
    overlay.querySelector("[data-save-story-permanent]")?.addEventListener("click", async () => { await api("/api/stories/permanent", { method: "POST", body: { storyId } }); toast("История сохранена в постоянные."); await refresh(false); close(); });
    overlay.querySelector("[data-share-story]")?.addEventListener("click", () => openStoryShareDialog(story, close));
    overlay.querySelector("[data-share-story-to-group]")?.addEventListener("click", () => { close(); openGroupContentShare("story", story.id); });
    overlay.querySelector("[data-report-story]")?.addEventListener("click", async () => { try { await reportTarget("story", storyId); } catch (error) { toast(error.message, true); } });
    overlay.querySelector("[data-story-reply]")?.addEventListener("submit", async (event) => {
      event.preventDefault();
      try {
        const data = await api("/api/stories/reply", { method: "POST", body: { storyId, text: new FormData(event.currentTarget).get("text") } });
        activeChatId = data.chatId;
        activeSection = "chats";
        close();
        await refresh();
      } catch (error) { toast(error.message, true); }
    });
    let selectedReaction = story.myReaction || "";
    const sendReaction = overlay.querySelector("[data-send-story-reaction]");
    const selectedReactionLabel = overlay.querySelector("[data-selected-story-reaction]");
    const updateReactionSelection = () => {
      overlay.querySelectorAll("[data-story-react]").forEach((item) => item.classList.toggle("active", item.dataset.storyReact === selectedReaction));
      if (sendReaction) sendReaction.disabled = !selectedReaction;
      if (selectedReactionLabel) selectedReactionLabel.textContent = selectedReaction ? `Отправить реакцию ${selectedReaction}` : "Выберите реакцию";
    };
    overlay.querySelectorAll("[data-story-react]").forEach((button) => button.addEventListener("click", () => { selectedReaction = button.dataset.storyReact; updateReactionSelection(); }));
    sendReaction?.addEventListener("click", async () => {
      try {
        await api("/api/stories/react", { method: "POST", body: { storyId, emoji: selectedReaction } });
        showStoryReactionBurst(selectedReaction, sendReaction);
        toast("Реакция отправлена.");
      } catch (error) { toast(error.message, true); }
    });
    updateReactionSelection();
  } catch (error) { toast(error.message, true); }
}
function getSavedAccounts() {
  const keys = [SAVED_ACCOUNTS_KEY, "chatpro_saved_accounts_v1"];
  for (const key of keys) {
    try { const value = JSON.parse(localStorage.getItem(key) || "[]"); if (value.length) return value; } catch {}
  }
  return [];
}
function rememberAccount(user, accountToken) {
  const accounts = getSavedAccounts().filter((x) => x.id !== user.id);
  accounts.unshift({ id: user.id, name: user.name, username: user.username, avatarData: user.avatarData, token: accountToken });
  saveAccounts(limitSavedAccounts(accounts));
}
function limitSavedAccounts(accounts) { const configuredLimit = Number(state?.accountLevel?.limits?.savedAccounts) || 0; return configuredLimit > 0 ? accounts.slice(0, configuredLimit) : accounts; }
function trimSavedAccountsToLimit() { saveAccounts(limitSavedAccounts(getSavedAccounts())); }
function removeSavedAccount(userId) {
  saveAccounts(getSavedAccounts().filter((account) => account.id !== userId));
}
function saveAccounts(accounts) {
  const saved = JSON.stringify(accounts);
  localStorage.setItem(SAVED_ACCOUNTS_KEY, saved);
  localStorage.setItem("chatpro_saved_accounts_v1", saved);
}
function fileToDataUrl(file, maxBytes) {
  if (!file || !file.size) return Promise.reject(new Error("Выберите файл."));
  if (file.size > maxBytes) return Promise.reject(new Error("Файл слишком большой."));
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(new Error("Не удалось прочитать файл."));
    reader.readAsDataURL(file);
  });
}
function blobToDataUrl(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(new Error("Не удалось прочитать запись."));
    reader.readAsDataURL(blob);
  });
}
function channelAppearanceStyle(appearance) {
  const allowedWallpapers = new Set([...CHAT_WALLPAPERS.map(({ id }) => id), "custom"]);
  const allowedFonts = new Set(DIALOG_FONTS.map(({ id }) => id));
  const validColor = (value) => /^#[\da-f]{6}$/i.test(String(value || ""));
  const wallpaper = allowedWallpapers.has(appearance?.wallpaper) ? appearance.wallpaper : "default";
  const ownBubble = validColor(appearance?.ownBubble) ? appearance.ownBubble : "";
  const otherBubble = validColor(appearance?.otherBubble) ? appearance.otherBubble : "";
  const panelColor = validColor(appearance?.panelColor) ? appearance.panelColor : "";
  const font = allowedFonts.has(appearance?.font) ? appearance.font : "";
  const styles = [];
  if (ownBubble) styles.push(`--own-bubble-background:${ownBubble}`, `--own-bubble-text:${dialogBubbleTextColor(ownBubble)}`);
  if (otherBubble) styles.push(`--other-bubble:${otherBubble}`, `--other-bubble-text:${dialogBubbleTextColor(otherBubble)}`);
  if (panelColor) styles.push(`--channel-panel-color:${panelColor}`, `--channel-panel-text:${dialogBubbleTextColor(panelColor)}`);
  if (font) styles.push(`--message-font:${dialogMessageFont(font)}`);
  const backgroundData = String(appearance?.backgroundData || "");
  if (wallpaper === "custom" && /^data:image\/(?:png|jpeg|webp);base64,[a-z\d+/=\s]+$/i.test(backgroundData)) {
    styles.push(`--channel-background-image:url("${backgroundData.replace(/\s/g, "")}")`);
  }
  return styles.join(";");
}
function chatBackgroundClass(user) { return `chat-background-${user?.chatBackground || "default"}`; }
function chatBackgroundStyle(user) { return user?.chatBackground === "custom" && user.chatBackgroundData ? ` style="background-image: linear-gradient(rgba(255,255,255,.15), rgba(255,255,255,.15)), url('${esc(user.chatBackgroundData)}')"` : ""; }
function initials(name) { return String(name || "U").trim().split(/\s+/).slice(0,2).map((x) => x[0]?.toUpperCase() || "").join("") || "U"; }
function timeFmt(ts) { return new Intl.DateTimeFormat("ru-RU", { hour: "2-digit", minute: "2-digit" }).format(ts * 1000); }
function dateFmt(ts) { return new Intl.DateTimeFormat("ru-RU", { day: "numeric", month: "long", year: "numeric" }).format(ts * 1000); }
function starDateFmt(ts) { return new Intl.DateTimeFormat("ru-RU", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }).format(ts * 1000); }
function esc(value) { return String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;"); }
function toast(message, error = false) { document.querySelector(".toast")?.remove(); const el = document.createElement("div"); el.className = `toast${error ? " error" : ""}`; el.textContent = message; document.body.append(el); setTimeout(() => el.remove(), 3200); }
