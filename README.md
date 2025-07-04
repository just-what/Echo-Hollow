# بوتات ديسكورد للقنوات الصوتية

هذا المشروع يقوم بإنشاء بوتات ديسكورد تبقى متصلة بالقنوات الصوتية ولا تخرج منها مهما حدث. يمكن التحكم بالبوتات من خلال رتبة محددة فقط. البوتات تتعامل تلقائياً مع مشاكل الاتصال وتحاول إعادة الاتصال في حالة الانقطاع. كما أن البوتات تتوزع على قنوات صوتية مختلفة بحيث لا يتواجد أكثر من بوت في نفس القناة.

## المتطلبات

- Python 3.8 أو أحدث
- مكتبات Python المطلوبة (موجودة في ملف requirements.txt)

## الإعداد

1. قم بتثبيت المكتبات المطلوبة:

```bash
pip install -r requirements.txt
```

2. قم بتعديل ملف `.env` وإضافة توكنات البوتات ومعرف الرتبة:

```
# توكنات البوتات (مفصولة بفواصل)
BOT_TOKENS=token1,token2,token3,token4,token5

# معرف الرتبة التي يمكنها التحكم بالبوتات
ADMIN_ROLE_ID=123456789012345678
```

3. قم بتعديل معرف الفئة (Category ID) في ملف `discord_voice_bots.py`:

```python
# معرف الفئة (Category ID) الذي تحتوي على القنوات الصوتية
CATEGORY_ID = 1384230814560030720  # قم بتغيير هذا الرقم إلى معرف الفئة الخاصة بك
```

## التشغيل

```bash
python discord_voice_bots.py
```

## الأوامر

يمكن للمستخدمين الذين لديهم الرتبة المحددة استخدام الأمر الموحد `!bot` مع الإجراءات التالية:

- `!bot join <channel_id>`: يجعل البوت ينضم إلى قناة صوتية محددة
- `!bot leave`: يجعل البوت يغادر القناة الصوتية الحالية
- `!bot status`: يعرض حالة البوت والقناة الصوتية المتصل بها مع معلومات إضافية
- `!bot restart`: يعيد تشغيل اتصال البوت بالقناة الصوتية
- `!bot`: يعرض قائمة المساعدة مع جميع الأوامر المتاحة

### ميزات الواجهة الجديدة

- واجهة مستخدم محسنة باستخدام Embeds
- ألوان مختلفة للحالات المختلفة (نجاح، فشل، معلومات)
- عرض معلومات مفصلة عن حالة الاتصال
- التعامل التلقائي مع مشاكل الاتصال
- توزيع البوتات على قنوات صوتية مختلفة
- منع تواجد أكثر من بوت في نفس القناة الصوتية

## كيفية الحصول على معرفات ديسكورد

### للحصول على معرف الفئة (Category ID):

1. افتح إعدادات ديسكورد
2. انتقل إلى "مظهر" > "وضع المطور" وقم بتفعيله
3. انقر بزر الماوس الأيمن على الفئة واختر "نسخ المعرف"

### للحصول على معرف الرتبة (Role ID):

1. افتح إعدادات السيرفر
2. انتقل إلى "الرتب"
3. انقر بزر الماوس الأيمن على الرتبة واختر "نسخ المعرف"

## ملاحظات

- يجب أن يكون لكل بوت توكن مختلف، حيث لا يمكن لبوت واحد الاتصال بأكثر من قناة صوتية في نفس السيرفر
- تأكد من أن البوتات لديها الصلاحيات الكافية للانضمام إلى القنوات الصوتية
- يمكنك إنشاء توكنات البوتات من [بوابة مطوري ديسكورد](https://discord.com/developers/applications)