from keep_alive import keep_alive
keep_alive()
import discord
import asyncio
import os
from dotenv import load_dotenv
import logging
import random

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

class VoiceBot(discord.Client):
    def __init__(self, token, voice_channel_id=None):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        super().__init__(intents=intents)
        self.token = token
        self.target_voice_channel_id = voice_channel_id
        self.voice_client = None
        self.reconnect_task = None
        self.is_reconnecting = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        
    async def on_ready(self):
        logger.info(f'تم تسجيل الدخول كـ {self.user} (ID: {self.user.id})')
        
        # إذا تم تحديد قناة صوتية، قم بالاتصال بها
        if self.target_voice_channel_id:
            logger.info(f'البوت {self.user} سيتصل بالقناة الصوتية المحددة له (ID: {self.target_voice_channel_id})')
            await self.connect_to_voice_channel(self.target_voice_channel_id)
        else:
            # إذا لم يتم تحديد قناة، ابحث عن قنوات صوتية في الفئة المحددة
            logger.info(f'البوت {self.user} سيبحث عن قناة صوتية متاحة في الفئة المحددة')
            await self.find_and_connect_to_voice_channel()
    
    async def find_and_connect_to_voice_channel(self):
        # إذا كان هناك قناة صوتية محددة للبوت، استخدمها
        if self.target_voice_channel_id:
            await self.connect_to_voice_channel(self.target_voice_channel_id)
            return
            
        # إذا لم يكن هناك قناة محددة، ابحث عن قناة متاحة
        for guild in self.guilds:
            category = guild.get_channel(CATEGORY_ID)
            if category:
                for channel in category.channels:
                    if isinstance(channel, discord.VoiceChannel):
                        # تحقق مما إذا كان البوت متصل بالفعل بهذه القناة
                        if not any(vc.channel.id == channel.id for vc in self.voice_clients):
                            await self.connect_to_voice_channel(channel.id)
                            return
    
    async def connect_to_voice_channel(self, channel_id):
        if self.is_reconnecting:
            logger.info(f'البوت {self.user} في حالة إعادة اتصال، تم تجاهل طلب الاتصال الجديد')
            return
            
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
                    
                    # تحقق مما إذا كان البوت متصل بالفعل بقناة أخرى
                    if self.voice_client and self.voice_client.is_connected():
                        logger.info(f'البوت {self.user} متصل بالفعل بقناة {self.voice_client.channel.name}، سيتم قطع الاتصال والانتقال إلى القناة الجديدة')
                        try:
                            await self.voice_client.disconnect(force=True)
                        except:
                            pass
                        await asyncio.sleep(2)  # انتظار قبل الاتصال بالقناة الجديدة
                    
                    self.voice_client = await channel.connect(reconnect=False, timeout=30.0)
                    logger.info(f'البوت {self.user} تم اتصاله بالقناة الصوتية: {channel.name} (ID: {channel.id})')
                    self.reconnect_attempts = 0  # إعادة تعيين عداد المحاولات عند نجاح الاتصال
                    
                except discord.errors.ClientException as e:
                    if "Already connected to a voice channel" in str(e):
                        logger.error(f'خطأ في اتصال البوت {self.user} بالقناة الصوتية {channel.name}: {e}')
                        # محاولة قطع الاتصال الحالي أولاً
                        if self.voice_client:
                            try:
                                await self.voice_client.disconnect(force=True)
                                await asyncio.sleep(3)  # انتظار أطول
                                self.voice_client = await channel.connect(reconnect=False, timeout=30.0)
                                logger.info(f'البوت {self.user} تم اتصاله بالقناة الصوتية: {channel.name} (ID: {channel.id}) بعد قطع الاتصال السابق')
                                self.reconnect_attempts = 0
                            except Exception as retry_error:
                                logger.error(f'فشل في إعادة الاتصال بعد قطع الاتصال: {retry_error}')
                    else:
                        logger.error(f'خطأ في اتصال البوت {self.user} بالقناة الصوتية {channel.name}: {e}')
                except Exception as e:
                    logger.error(f'خطأ في اتصال البوت {self.user} بالقناة الصوتية {channel.name}: {e}')
    
    async def schedule_reconnect(self, delay=None):
        """جدولة إعادة الاتصال مع تأخير متزايد"""
        if self.is_reconnecting:
            return
            
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error(f'البوت {self.user} وصل إلى الحد الأقصى من محاولات إعادة الاتصال ({self.max_reconnect_attempts})')
            return
        
        self.is_reconnecting = True
        
        if delay is None:
            # تأخير متزايد: 5, 10, 20, 40, 80 ثانية
            delay = min(5 * (2 ** self.reconnect_attempts), 80)
            # إضافة عشوائية لتجنب التصادم
            delay += random.uniform(1, 5)
        
        logger.info(f'البوت {self.user} سيحاول إعادة الاتصال خلال {delay:.1f} ثانية (المحاولة {self.reconnect_attempts + 1})')
        
        await asyncio.sleep(delay)
        
        try:
            self.reconnect_attempts += 1
            
            if self.target_voice_channel_id:
                logger.info(f'البوت {self.user} يحاول إعادة الاتصال بالقناة المخصصة له (ID: {self.target_voice_channel_id})')
                await self.connect_to_voice_channel(self.target_voice_channel_id)
            else:
                logger.info(f'البوت {self.user} يحاول البحث عن قناة صوتية متاحة في الفئة المحددة')
                await self.find_and_connect_to_voice_channel()
                
        except Exception as e:
            logger.error(f'خطأ أثناء محاولة إعادة الاتصال للبوت {self.user}: {e}')
        finally:
            self.is_reconnecting = False
    
    async def on_voice_state_update(self, member, before, after):
        # إذا تم فصل البوت من القناة، حاول إعادة الاتصال
        if (member.id == self.user.id and 
            before.channel and 
            not after.channel and 
            not self.is_reconnecting):
            
            logger.info(f'البوت {self.user} تم فصله من القناة الصوتية {before.channel.name}, جدولة إعادة الاتصال...')
            
            # إلغاء مهمة إعادة الاتصال السابقة إذا كانت موجودة
            if self.reconnect_task and not self.reconnect_task.done():
                self.reconnect_task.cancel()
            
            # جدولة إعادة اتصال جديدة
            self.reconnect_task = asyncio.create_task(self.schedule_reconnect())
    
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
            # الأمر: !join <channel_id>
            try:
                channel_id = int(message.content.split()[1])
                logger.info(f'المستخدم {message.author} طلب من البوت {self.user} الانضمام إلى القناة الصوتية بمعرف: {channel_id}')
                
                # تحديث القناة المخصصة للبوت
                self.target_voice_channel_id = channel_id
                
                # إلغاء أي مهمة إعادة اتصال جارية
                if self.reconnect_task and not self.reconnect_task.done():
                    self.reconnect_task.cancel()
                
                self.is_reconnecting = False
                self.reconnect_attempts = 0
                
                await self.connect_to_voice_channel(channel_id)
                await message.channel.send(f'تم اتصال البوت {self.user.name} بالقناة الصوتية بمعرف: {channel_id}')
            except (IndexError, ValueError):
                await message.channel.send('الرجاء تحديد معرف قناة صوتية صالح. مثال: !join 123456789012345678')
        
        elif message.content == '!leave':
            # الأمر: !leave
            if self.voice_client and self.voice_client.is_connected():
                channel_name = self.voice_client.channel.name
                logger.info(f'المستخدم {message.author} طلب من البوت {self.user} مغادرة القناة الصوتية: {channel_name}')
                
                # إلغاء أي مهمة إعادة اتصال جارية
                if self.reconnect_task and not self.reconnect_task.done():
                    self.reconnect_task.cancel()
                
                self.is_reconnecting = False
                self.target_voice_channel_id = None  # إزالة القناة المخصصة
                
                await self.voice_client.disconnect(force=True)
                await message.channel.send(f'تم قطع اتصال البوت {self.user.name} من القناة الصوتية {channel_name}')
            else:
                await message.channel.send(f'البوت {self.user.name} غير متصل بأي قناة صوتية')
        
        elif message.content == '!status':
            # الأمر: !status
            if self.voice_client and self.voice_client.is_connected():
                channel_name = self.voice_client.channel.name
                channel_id = self.voice_client.channel.id
                logger.info(f'المستخدم {message.author} طلب حالة البوت {self.user}')
                status_text = f'البوت {self.user.name} متصل بالقناة الصوتية: {channel_name} (ID: {channel_id})'
                if self.is_reconnecting:
                    status_text += f'\n🔄 في حالة إعادة اتصال (المحاولة {self.reconnect_attempts}/{self.max_reconnect_attempts})'
                await message.channel.send(status_text)
            else:
                status_text = f'البوت {self.user.name} غير متصل بأي قناة صوتية'
                if self.is_reconnecting:
                    status_text += f'\n🔄 في حالة إعادة اتصال (المحاولة {self.reconnect_attempts}/{self.max_reconnect_attempts})'
                await message.channel.send(status_text)
        
        elif message.content == '!reconnect':
            # الأمر: !reconnect - إعادة اتصال فورية
            logger.info(f'المستخدم {message.author} طلب من البوت {self.user} إعادة الاتصال')
            
            # إلغاء أي مهمة إعادة اتصال جارية
            if self.reconnect_task and not self.reconnect_task.done():
                self.reconnect_task.cancel()
            
            self.is_reconnecting = False
            self.reconnect_attempts = 0
            
            if self.target_voice_channel_id:
                await self.connect_to_voice_channel(self.target_voice_channel_id)
                await message.channel.send(f'تم إعادة اتصال البوت {self.user.name}')
            else:
                await message.channel.send(f'لم يتم تحديد قناة صوتية للبوت {self.user.name}')
        
        elif message.content == '!help':
            # الأمر: !help - إضافة أمر جديد للمساعدة
            help_text = """**أوامر التحكم بالبوت:**
!join <channel_id> - للانضمام إلى قناة صوتية محددة
!leave - لمغادرة القناة الصوتية الحالية
!status - لعرض حالة اتصال البوت
!reconnect - لإعادة الاتصال فوراً
!help - لعرض هذه المساعدة"""
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
        for guild in temp_client.guilds:
            category = guild.get_channel(CATEGORY_ID)
            if category:
                voice_channels = [channel for channel in category.channels if isinstance(channel, discord.VoiceChannel)]
                logger.info(f'تم العثور على {len(voice_channels)} قناة صوتية في الفئة المحددة')
                await temp_client.close()
    
    # تشغيل العميل المؤقت للحصول على القنوات الصوتية
    try:
        # استخدام أول توكن للحصول على القنوات
        first_token = BOT_TOKENS[0].strip()
        if first_token:
            await temp_client.start(first_token)
    except Exception as e:
        logger.error(f'خطأ في الحصول على القنوات الصوتية: {e}')
    
    # إنشاء بوت لكل توكن وتخصيص قناة صوتية له
    for i, token in enumerate(BOT_TOKENS):
        if token.strip():
            # تخصيص قناة صوتية للبوت إذا كانت متوفرة
            voice_channel_id = None
            if voice_channels and i < len(voice_channels):
                voice_channel_id = voice_channels[i].id
                logger.info(f'تخصيص القناة الصوتية {voice_channels[i].name} للبوت رقم {i+1}')
            
            bot = VoiceBot(token.strip(), voice_channel_id)
            bots.append(bot)
    
    # تشغيل جميع البوتات
    await asyncio.gather(*(bot.start(bot.token) for bot in bots))

if __name__ == '__main__':
    # تشغيل البرنامج الرئيسي
    asyncio.run(main())
