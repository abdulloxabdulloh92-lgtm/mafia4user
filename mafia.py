import os
import asyncio
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from urllib.parse import urlparse, parse_qs

# ═══════════════════════════════════════
# ENVIRONMENT VARIABLES
# ═══════════════════════════════════════
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")

SESSIONS = [
    os.environ.get("SESSION_1"),
    os.environ.get("SESSION_2"),
    os.environ.get("SESSION_3"),
    os.environ.get("SESSION_4"),
]

TARGET_GROUP = int(os.environ.get("TARGET_GROUP"))
MAFIA_BOT = "MafiaBakuBlack1Bot"
# ═══════════════════════════════════════

clients = []
don_index = None
joined_set = set()
joined_lock = asyncio.Lock()
start_task = None
restarting = False


async def reset_state():
    global don_index, joined_set, start_task, restarting
    don_index = None
    joined_set = set()
    restarting = False
    if start_task and not start_task.done():
        start_task.cancel()
    start_task = None
    print("[🔄] Holat tiklandi")


async def delayed_start():
    try:
        print("[⏳] 5 sekund kutilmoqda...")
        await asyncio.sleep(5)
        await clients[0].send_message(TARGET_GROUP, "/start")
        print("[▶️] /start yuborildi!")
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"[❌] /start xato: {e}")


async def restart_game():
    global restarting
    restarting = True
    await reset_state()
    await asyncio.sleep(5)
    try:
        await clients[0].send_message(TARGET_GROUP, "/game")
        print("[🎮] /game yuborildi")
    except Exception as e:
        print(f"[❌] /game xato: {e}")


async def setup_client(session_string, index):
    client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
    await client.start()
    me = await client.get_me()
    print(f"[✅] {index+1}-akkaunt ulandi: {me.first_name}")
    clients.append(client)

    @client.on(events.NewMessage(chats=TARGET_GROUP))
    async def group_handler(event):
        global don_index, joined_set, start_task, restarting
        text = event.raw_text or ""

        # Ro'yxatdan o'tish
        if "yxatdan o'tish" in text:
            if event.buttons:
                for row in event.buttons:
                    for btn in row:
                        if getattr(btn, "url", None):
                            try:
                                parsed = urlparse(btn.url)
                                params = parse_qs(parsed.query)
                                if "start" in params:
                                    start_param = params["start"][0]
                                    await client.send_message(MAFIA_BOT, f"/start {start_param}")
                                    print(f"[📝] {index+1}-akkaunt ro'yxatdan o'tdi")
                                    async with joined_lock:
                                        joined_set.add(index)
                                        print(f"[✅] {index+1}-akkaunt qo'shildi ({len(joined_set)}/4)")
                                        if len(joined_set) == 4 and start_task is None:
                                            print("[🚀] 4 ta qo'shildi → 5 sekunddan keyin /start!")
                                            start_task = asyncio.create_task(delayed_start())
                            except Exception as e:
                                print(f"[❌] {index+1}-ak ro'yxat xato: {e}")

        # Aybdorlar vaqti — leave logikasi
        if "Aybdorlarni aniqlash va jazolash vaqti keldi" in text:
            if don_index == 0:
                # 1-akkaunt Don → faqat 2,3,4 leave qiladi
                if index != 0:
                    try:
                        await asyncio.sleep(1)
                        await client.send_message(TARGET_GROUP, "/leave")
                        print(f"[👋] {index+1}-akkaunt leave qildi (1-ak Don)")
                    except Exception as e:
                        print(f"[❌] /leave xato: {e}")
            else:
                # Boshqa akkaunt Don → faqat shu Don leave qiladi
                if don_index == index:
                    try:
                        await asyncio.sleep(1)
                        await client.send_message(TARGET_GROUP, "/leave")
                        print(f"[👋] {index+1}-akkaunt (Don) leave qildi")
                    except Exception as e:
                        print(f"[❌] /leave xato: {e}")

        # O'yin tugadi
        if index == 0 and ("O'yin tugadi" in text or "G'oliblar:" in text):
            if restarting:
                return
            print("[🏁] O'yin tugadi! Qayta boshlanmoqda...")
            await restart_game()

    @client.on(events.NewMessage(from_users=MAFIA_BOT, func=lambda e: e.is_private))
    async def private_handler(event):
        global don_index
        text = event.raw_text or ""
        if "Don siz" in text or "🤵🏻 Don" in text:
            don_index = index
            if index == 0:
                print(f"[🎩] 1-akkaunt DON bo'ldi! Qolganlar leave qiladi.")
            else:
                print(f"[🎩] {index+1}-akkaunt DON bo'ldi! U leave qiladi, 1-akkaunt qoladi.")

    return client


async def main():
    print("[*] Mafia Auto Bot ishga tushmoqda...")
    for i, session in enumerate(SESSIONS):
        await setup_client(session, i)
        await asyncio.sleep(1)
    print("[✅] Hammasi tayyor! O'yin boshlanmoqda...")
    await asyncio.sleep(2)
    await clients[0].send_message(TARGET_GROUP, "/game")
    print("[🎮] /game yuborildi")
    await asyncio.gather(*(c.run_until_disconnected() for c in clients))


asyncio.run(main())
