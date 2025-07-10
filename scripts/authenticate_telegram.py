#!/usr/bin/env python3
"""
Script to authenticate Telegram userbot for first-time setup.
This creates a session file that the userbot will use.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

from src.common.config import settings


async def authenticate():
    """Authenticate with Telegram and create session file."""
    # Ensure sessions directory exists
    session_path = settings.data_dir / "sessions"
    session_path.mkdir(parents=True, exist_ok=True)
    
    session_file = session_path / f"{settings.telegram_session_name}.session"
    
    print(f"Creating Telegram session at: {session_file}")
    print(f"Using API ID: {settings.telegram_api_id}")
    
    # Create client
    client = TelegramClient(
        str(session_file),
        settings.telegram_api_id,
        settings.telegram_api_hash
    )
    
    try:
        await client.start()
        
        # Check if already authorized
        if await client.is_user_authorized():
            me = await client.get_me()
            print(f"\n✅ Already authenticated as: @{me.username} ({me.first_name})")
        else:
            print("\n❌ Not authenticated. Starting authentication process...")
            
            # Request phone number
            phone = input("Enter your phone number (with country code, e.g., +1234567890): ")
            
            await client.send_code_request(phone)
            
            # Request verification code
            code = input("Enter the verification code sent to your phone: ")
            
            try:
                await client.sign_in(phone, code)
            except SessionPasswordNeededError:
                # 2FA is enabled
                password = input("Two-factor authentication is enabled. Enter your password: ")
                await client.sign_in(password=password)
            
            me = await client.get_me()
            print(f"\n✅ Successfully authenticated as: @{me.username} ({me.first_name})")
        
        print(f"\nSession file created at: {session_file}")
        print("You can now run the userbot!")
        
    except Exception as e:
        print(f"\n❌ Authentication failed: {e}")
        sys.exit(1)
    finally:
        await client.disconnect()


if __name__ == "__main__":
    print("🤖 Telegram Userbot Authentication")
    print("=" * 40)
    asyncio.run(authenticate())