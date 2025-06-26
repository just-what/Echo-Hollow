from keep_alive import keep_alive
keep_alive()
asyncio.run(main())
import discord
import asyncio
import os
from dotenv import load_dotenv
import logging
import time

# إعداد التسجيل
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('DiscordVoiceBots')

# تحميل المتغيرات البيئية
load_dotenv()

# معرف الفئة (Category ID) الذي تحتوي على القنوات الصوتية
CATEGORY_ID = 1386381378844623128

# معرف الرتبة التي يمكنها التحكم بالبوتات
ADMIN_ROLE_ID = int(os.getenv('ADMIN_ROLE_ID', '0'))

# قائمة توكنات البوتات
BOT_TOKENS = os.getenv('BOT_TOKENS', '').split(',')

# متغيرات للتحكم في إعادة الاتصال
MAX_RECONNECT_ATTEMPTS = 3
RECONNECT_DELAY = 10  # ثوانٍ
CONNECTION_CHECK_INTERVAL = 30  # ثوانٍ

class VoiceBot(discord.Client):
    def __init__(self, token, voice_channel_id=None, bot_index=0):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        super().__init__(intents=intents)
        self.token = token
        self.target_voice_channel_id = voice_channel_id
        self.voice_client = None
        self.bot_index = bot_index
        self.is_connecting = False
        self.last_connection_attempt = 0
        self.reconnect_attempts = 0
        self.should_stay_connected = True
        
    async def on_ready(self):
        logger.info(f'تم تسجيل الدخول كـ {self.user} (ID: {self.user.id}) - البوت رقم {self.bot_index + 1}')
        
        # انتظار قصير لتجنب التضارب
        await asyncio.sleep(self.bot_index * 2)
        
        # إذا تم تحديد قناة صوتية، قم بالاتصال بها
        if self.target_voice_channel_id:
            logger.info(f'البوت {self.user} سيتصل بالقناة الصوتية المحددة له (ID: {self.target_voice_channel_id})')
            await self.connect_to_voice_channel_safe(self.target_voice_channel_id)
        else:
            # إذا لم يتم تحديد قناة، ابحث عن قنوات صوتية في الفئة المحددة
            logger.info(f'البوت {self.user} سيبحث عن قناة صوتية متاحة في الفئة المحددة')
            await self.find_and_connect_to_voice_channel()
    
    async def connect_to_voice_channel_safe(self, channel_id):
        """اتصال آمن بالقناة الصوتية مع فحص التضارب"""
        current_time = time.time()
        
        # تجنب المحاولات السريعة المتتالية
        if current_time - self.last_connection_attempt < RECONNECT_DELAY:
            logger.info(f'البوت {self.user} ينتظر قبل محاولة الاتصال مرة أخرى...')
            return
        
        if self.is_connecting:
            logger.info(f'البوت {self.user} يحاول الاتصال بالفعل، تجاهل المحاولة الجديدة')
            return
            
        self.is_connecting = True
        self.last_connection_attempt = current_time
        
        try:
            await self.connect_to_voice_channel(channel_id)
        finally:
            self.is_connecting = False
    
    async def find_and_connect_to_voice_channel(self):
        # إذا كان هناك قناة صوتية محددة للبوت، استخدمها
        if self.target_voice_channel_id:
            await self.connect_to_voice_channel_safe(self.target_voice_channel_id)
            return
            
        # إذا لم يكن هناك قناة محددة، ابحث عن قناة متاحة
        for guild in self.guilds:
            category = guild.get_channel(CATEGORY_ID)
            if category:
                for channel in category.channels:
                    if isinstance(channel, discord.VoiceChannel):
                        # تحقق مما إذا كان أي بوت متصل بالفعل بهذه القناة
                        bots_in_channel = [member for member in channel.members if member.bot]
                        if len(bots_in_channel) == 0:  # القناة فارغة من البوتات
                            await self.connect_to_voice_channel_safe(channel.id)
                            return
    
    async def connect_to_voice_channel(self, channel_id):
        for guild in self.guilds:
            channel = guild.get_channel(channel_id)
            if channel and isinstance(channel, discord.VoiceChannel):
                try:
                    # تحقق مما إذا كان البوت متصل بالفعل بنفس القناة
                    if (self.voice_client and 
                        self.voice_client.is_connected() and 
                        self.voice_client.channel.id == channel_id):
                        logger.info(f'البوت {self.user} متصل بالفعل بالقناة {channel.name}')
                        return
                    
                    # تحقق مما إذا كان البوت متصل بقناة أخرى
                    if self.voice_client and self.voice_client.is_connected():
                        logger.info(f'البوت {self.user} متصل بقناة أخرى، سيتم قطع الاتصال أولاً')
                        await self.voice_client.disconnect()
                        await asyncio.sleep(2)  # انتظار قصير
                    
                    # تحقق من عدد البوتات في القناة المستهدفة
                    bots_in_target_channel = [member for member in channel.members if member.bot]
                    if len(bots_in_target_channel) >= 1 and channel_id != self.target_voice_channel_id:
                        logger.info(f'القناة {channel.name} تحتوي على بوت آخر بالفعل، البحث عن قناة أخرى...')
                        return
                    
                    self.voice_client = await channel.connect(reconnect=False, timeout=30.0)
                    logger.info(f'البوت {self.user} تم اتصاله بالقناة الصوتية: {channel.name} (ID: {channel.id})')
                    
                    self.reconnect_attempts = 0  # إعادة تعيين عداد المحاولات عند النجاح
                    
                    # بدء مراقبة الاتصال
                    asyncio.create_task(self.monitor_connection())
                    
                except discord.errors.ClientException as e:
                    if "already connected" in str(e).lower():
                        logger.info(f'البوت {self.user} متصل بالفعل بقناة صوتية')
                    else:
                        logger.error(f'خطأ في اتصال البوت {self.user} بالقناة الصوتية {channel.name}: {e}')
                except asyncio.TimeoutError:
                    logger.error(f'انتهت مهلة اتصال البوت {self.user} بالقناة {channel.name}')
                except Exception as e:
                    logger.error(f'خطأ غير متوقع في اتصال البوت {self.user} بالقناة الصوتية {channel.name}: {e}')
    
    async def monitor_connection(self):
        """مراقبة الاتصال والتأكد من بقاء البوت متصلاً"""
        while self.should_stay_connected:
            await asyncio.sleep(CONNECTION_CHECK_INTERVAL)
            
            # تحقق من حالة الاتصال
            if (not self.voice_client or 
                not self.voice_client.is_connected() or
                self.voice_client.channel is None):
                
                if self.reconnect_attempts < MAX_RECONNECT_ATTEMPTS:
                    logger.info(f'البوت {self.user} فقد الاتصال، محاولة إعادة الاتصال ({self.reconnect_attempts + 1}/{MAX_RECONNECT_ATTEMPTS})')
                    self.reconnect_attempts += 1
                    
                    if self.target_voice_channel_id:
                        await self.connect_to_voice_channel_safe(self.target_voice_channel_id)
                    else:
                        await self.find_and_connect_to_voice_channel()
                else:
                    logger.error(f'البوت {self.user} فشل في إعادة الاتصال بعد {MAX_RECONNECT_ATTEMPTS} محاولات')
                    break
            else:
                # إعادة تعيين عداد المحاولات عند التأكد من الاتصال
                self.reconnect_attempts = 0
    
    async def on_voice_state_update(self, member, before, after):
        # التعامل مع تغييرات حالة الصوت للبوت نفسه فقط
        if member.id != self.user.id:
            return
            
        # إذا تم فصل البوت من القناة
        if before.channel and not after.channel:
            logger.info(f'البوت {self.user} تم فصله من القناة الصوتية {before.channel.name}')
            
            # لا نحاول إعادة الاتصال فوراً هنا لتجنب التضارب
            # المراقب سيتولى إعادة الاتصال
            
        # إذا انتقل البوت إلى قناة جديدة
        elif before.channel != after.channel and after.channel:
            logger.info(f'البوت {self.user} انتقل إلى القناة الصوتية {after.channel.name}')
    
    async def on_message(self, message):
        # تجاهل الرسائل من البوتات
        if message.author.bot:
            return
        
        # تحقق مما إذا كان المستخدم لديه الرتبة المطلوبة للتحكم بالبوت
        has_permission = False
        if message.guild:
            admin_role = discord.utils.get(message.guild.roles, id=ADMIN_ROLE_ID)
            if admin_role and admin_role in message.author.roles:
                has_permission = True
        
        if not has_permission:
            return
        
        # أوامر التحكم بالبوت
        if message.content.startswith('!join'):
            # الأمر: !join <channel_id> [bot_index]
            parts = message.content.split()
            if len(parts) < 2:
                await message.channel.send('الرجاء تحديد معرف قناة صوتية صالح. مثال: !join 123456789012345678')
                return
                
            try:
                channel_id = int(parts[1])
                target_bot_index = None
                
                # إذا تم تحديد رقم البوت
                if len(parts) > 2:
                    target_bot_index = int(parts[2]) - 1  # تحويل إلى فهرس (البوت 1 = فهرس 0)
                    if target_bot_index != self.bot_index:
                        return  # هذا الأمر ليس لهذا البوت
                
                logger.info(f'المستخدم {message.author} طلب من البوت {self.user} الانضمام إلى القناة الصوتية بمعرف: {channel_id}')
                
                # تحديث القناة المخصصة للبوت
                self.target_voice_channel_id = channel_id
                
                await self.connect_to_voice_channel_safe(channel_id)
                await message.channel.send(f'تم طلب اتصال البوت {self.user.name} بالقناة الصوتية بمعرف: {channel_id}')
                
            except (IndexError, ValueError):
                await message.channel.send('الرجاء تحديد معرف قناة صوتية صالح. مثال: !join 123456789012345678 [رقم_البوت]')
        
        elif message.content.startswith('!leave'):
            # الأمر: !leave [bot_index]
            parts = message.content.split()
            target_bot_index = None
            
            # إذا تم تحديد رقم البوت
            if len(parts) > 1:
                try:
                    target_bot_index = int(parts[1]) - 1
                    if target_bot_index != self.bot_index:
                        return  # هذا الأمر ليس لهذا البوت
                except ValueError:
                    pass
            
            if self.voice_client and self.voice_client.is_connected():
                channel_name = self.voice_client.channel.name
                logger.info(f'المستخدم {message.author} طلب من البوت {self.user} مغادرة القناة الصوتية: {channel_name}')
                
                self.should_stay_connected = False  # إيقاف المراقبة
                await self.voice_client.disconnect()
                await message.channel.send(f'تم قطع اتصال البوت {self.user.name} من القناة الصوتية {channel_name}')
            else:
                await message.channel.send(f'البوت {self.user.name} غير متصل بأي قناة صوتية')
        
        elif message.content == '!status':
            # الأمر: !status - إظهار حالة جميع البوتات
            if self.voice_client and self.voice_client.is_connected():
                channel_name = self.voice_client.channel.name
                channel_id = self.voice_client.channel.id
                await message.channel.send(f'البوت {self.user.name} (#{self.bot_index + 1}) متصل بالقناة الصوتية: {channel_name} (ID: {channel_id})')
            else:
                await message.channel.send(f'البوت {self.user.name} (#{self.bot_index + 1}) غير متصل بأي قناة صوتية')
        
        elif message.content == '!help':
            # الأمر: !help - إضافة أمر جديد للمساعدة
            help_text = """**أوامر التحكم بالبوتات:**
`!join <channel_id> [bot_number]` - للانضمام إلى قناة صوتية محددة
`!leave [bot_number]` - لمغادرة القناة الصوتية الحالية
`!status` - لعرض حالة اتصال جميع البوتات
`!help` - لعرض هذه المساعدة

**ملاحظات:**
- إذا لم تحدد رقم البوت، سيتم تطبيق الأمر على جميع البوتات
- أرقام البوتات تبدأ من 1"""
            await message.channel.send(help_text)

async def main():
    # إنشاء قائمة من البوتات
    bots = []
    
    # تحقق من وجود توكنات
    if not BOT_TOKENS or BOT_TOKENS[0] == '':
        logger.error('لم يتم تحديد أي توكنات للبوتات. الرجاء إضافة توكنات في ملف .env')
        return
    
    # الحصول على قائمة القنوات الصوتية في الفئة المحددة
    voice_channels = []
    
    # إنشاء عميل مؤقت للحصول على القنوات الصوتية
    temp_client = discord.Client(intents=discord.Intents.default())
    
    @temp_client.event
    async def on_ready():
        nonlocal voice_channels
        try:
            for guild in temp_client.guilds:
                category = guild.get_channel(CATEGORY_ID)
                if category:
                    voice_channels = [channel for channel in category.channels if isinstance(channel, discord.VoiceChannel)]
                    logger.info(f'تم العثور على {len(voice_channels)} قناة صوتية في الفئة المحددة')
                    break
        except Exception as e:
            logger.error(f'خطأ في الحصول على القنوات: {e}')
        finally:
            await temp_client.close()
    
    # تشغيل العميل المؤقت للحصول على القنوات الصوتية
    try:
        first_token = BOT_TOKENS[0].strip()
        if first_token:
            await temp_client.start(first_token)
    except Exception as e:
        logger.error(f'خطأ في الحصول على القنوات الصوتية: {e}')
    
    # إنشاء بوت لكل توكن وتخصيص قناة صوتية له
    tasks = []
    for i, token in enumerate(BOT_TOKENS):
        if token.strip():
            # تخصيص قناة صوتية للبوت إذا كانت متوفرة
            voice_channel_id = None
            if voice_channels and i < len(voice_channels):
                voice_channel_id = voice_channels[i].id
                logger.info(f'تخصيص القناة الصوتية {voice_channels[i].name} للبوت رقم {i+1}')
            
            bot = VoiceBot(token.strip(), voice_channel_id, i)
            bots.append(bot)
            tasks.append(bot.start(bot.token))
    
    # تشغيل جميع البوتات
    if tasks:
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            logger.info('تم إيقاف البرنامج بواسطة المستخدم')
            # إيقاف جميع البوتات بشكل صحيح
            for bot in bots:
                bot.should_stay_connected = False
                if bot.voice_client and bot.voice_client.is_connected():
                    await bot.voice_client.disconnect()
                await bot.close()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info('تم إنهاء البرنامج')
    except Exception as e:
        logger.error(f'خطأ في تشغيل البرنامج: {e}')
async def main():
    # تشغيل كل البوتات من 
