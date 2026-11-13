import discord
from discord.ext import commands

class DeleteServerChannels(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="حذف")
    @commands.has_permissions(administrator=True) # شرط أن يكون المستخدم مسولاً
    async def delete_all_channels(self, ctx):
        # رسالة تأكيد للبدء
        confirm_msg = await ctx.send("⚠️ **هل أنت متأكد من رغبتك في حذف جميع الرومات والفئات في السيرفر؟** اكتب `نعم` خلال 15 ثانية للتأكيد.")

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content == "نعم"

        try:
            # انتظار رد المستخدم للتأكيد (حماية ضد الاستخدام الخاطئ)
            await self.bot.wait_for('message', check=check, timeout=15.0)
        except asyncio.TimeoutError:
            return await ctx.send("❌ تم إلغاء عملية الحذف لعدم الاستجابة في الوقت المحدد.")

        await ctx.send("🧹 جاري حذف جميع الرومات والفئات والصوتيات...")

        # حذف جميع الفئات والرومات (كتابية وصوتية) الموجودة في السيرفر
        for channel in ctx.guild.channels:
            try:
                await channel.delete()
            except Exception as e:
                print(f"فشل في حذف الروم {channel.name}: {e}")

async def setup(bot):
    await bot.add_cog(DeleteServerChannels(bot))
