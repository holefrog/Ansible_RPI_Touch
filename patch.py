import re

with open('/home/david/Coding/Ansible_RPI_Touch/ansible/roles/wyoming/files/satellite.py', 'r') as f:
    content = f.read()

# Add is_deaf_mode to __init__
if 'self.is_deaf_mode = False' not in content:
    content = content.replace('self.is_running = True', 'self.is_running = True\n        self.is_deaf_mode = False')

# Modify event_from_mic to zero out audio if deaf
deaf_logic = """    async def event_from_mic(self, event: Event, audio_bytes: Optional[bytes] = None) -> None:
        if self.is_deaf_mode and audio_bytes is not None:
            # Replace audio bytes with pure silence (zeros)
            audio_bytes = bytes(len(audio_bytes))
            event = AudioChunk(rate=event.data.get("rate", 16000), width=event.data.get("width", 2), channels=event.data.get("channels", 1), audio=audio_bytes).event()
"""
if 'def event_from_mic' in content:
    content = re.sub(r'    async def event_from_mic\(self, event: Event, audio_bytes: Optional\[bytes\] = None\) -> None:.*?(?=    async def event_from_snd)', deaf_logic + '\n        await self.event_to_server(event)\n        await self.forward_event(event)\n\n', content, flags=re.DOTALL)

# Add trigger to make deaf mode active after wake word
deaf_trigger = """                    # Temporarily deafen mic to avoid capturing wake prompt
                    self.is_deaf_mode = True
                    async def undeafen():
                        await asyncio.sleep(1.2)
                        self.is_deaf_mode = False
                    asyncio.create_task(undeafen())"""
if 'self.is_deaf_mode = True' not in content:
    content = content.replace('_LOGGER.debug("Wake word detected: %s", wake_word.name)', '_LOGGER.debug("Wake word detected: %s", wake_word.name)\n' + deaf_trigger)

with open('/home/david/Coding/Ansible_RPI_Touch/ansible/roles/wyoming/files/satellite.py', 'w') as f:
    f.write(content)
