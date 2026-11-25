import discord
from discord import app_commands
from discord.ext import commands

RULES_IMAGE_URL = "https://l.top4top.io/p_39801059m0.png"

SAUDI_RULES_TEXT = (
    "**1. الاحترام أولاً وآخراً:** خلك رجال محترم ولا تغلط على أحد، لا"
    " بضحك ولا بجد، حدودك معروفة.\n"
    "**2. لا تسب ولا تقذف:** أي سب أو قذف أو طعن في الأعراض أو القبائل"
    " أو الأديان على طول بدون مقدمات، الباب يوسّع جمل.\n"
    "**3. ممنوع السبام والإزعاج:** لا ترسل ورا بعض ولا تكرر الكلام ولا"
    " تزعج الناس بالمنشنات، خذ راحتك بس بعقل.\n"
    "**4. لا تنشر روابط أو إعلانات:** ممنوع تسوّق لسيرفرات أو حسابات أو"
    " تحط روابط مشبوهة إلا بإذن الإدارة.\n"
    "**5. خلك في مكانك الصح:** كل شات وله شغله؛ السوالف في الشات العام،"
    " والأوامر والميمز في روماتها، لا تحوس الدنيا.\n"
    "**6. المحتوى المخل والمقرف مرفوض:** لا صور ولا مقاطع ولا كلام خادش"
    " أو مقرف، السيرفر نظيف ويبقى نظيف.\n"
    "**7. لا تقلبها دراما أو مشاكل:** عندك خلاف مع أحد حله برواق أو تواصل"
    " مع الإدارة بهدوء، لا تشبّونها في العام.\n"
    "**8. لا تسوّي مشاكل في الفويس:** لا تصارخ، ولا تشغّل أصوات مزعجة"
    " أو ساوند بورد يصدّع بالروس، احترم الموجودين.\n"
    "**9. لا تتدخل في شغل الإدارة:** قرارات الإدارة والستاف تُحترم، وإذا"
    " عندك ملاحظة أو ظلم افتح تكت وتكلم بأسلوب زين.\n"
    "**10. استغل حسابك صح:** ممنوع الحسابات الوهمية المزعجة أو انتحال"
    " الشخصيات أو محاولة استغلال الثغرات، خل لعبك نظيف."
)


class ReadRulesView(discord.ui.View):

  def __init__(self):
    super().__init__(timeout=None)

  @discord.ui.button(
      label="قراءة القوانين",
      style=discord.ButtonStyle.secondary,
      emoji="📜",
      custom_id="haven_read_rules_persistent_btn",
  )
  async def read_rules_button(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    guild_name = interaction.guild.name if interaction.guild else "HAVEN"

    embed = discord.Embed(
        title=f"📜 قوانين {guild_name}",
        description=SAUDI_RULES_TEXT,
        color=discord.Color.from_rgb(28, 28, 32),
    )
    if interaction.guild and interaction.guild.icon:
      embed.set_thumbnail(url=interaction.guild.icon.url)
    embed.set_footer(text="التزامك بالقوانين يجمّلك ويحفظ مكانك • HAVEN")

    await interaction.response.send_message(embed=embed, ephemeral=True)


class RulesCog(commands.Cog):

  def __init__(self, bot: commands.Bot):
    self.bot = bot
    self.bot.add_view(ReadRulesView())

  @app_commands.command(
      name="rules", description="إرسال لوحة القوانين مع زر قراءة القوانين"
  )
  async def rules(self, interaction: discord.Interaction):
    if not interaction.channel:
      await interaction.response.send_message(
          "⚠️ ما أقدر أرسل اللوحة هنا.", ephemeral=True
      )
      return

    guild_name = interaction.guild.name if interaction.guild else "HAVEN"
    panel_embed = discord.Embed(
        title=f"⚔️ بوابة قوانين {guild_name}",
        description=(
            "حيّاك الله في **HAVEN**.\n"
            "قبل لا تبدأ وتاخذ راحتك، اضغط زر **قراءة القوانين** تحت عشان"
            " تعرف وش لك ووش عليك."
        ),
        color=discord.Color.from_rgb(20, 20, 24),
    )
    panel_embed.set_image(url=RULES_IMAGE_URL)
    panel_embed.set_footer(text="اضغط الزر بالأسفل لعرض القوانين كاملة")

    await interaction.response.send_message(
        "✅ تم إرسال لوحة القوانين.", ephemeral=True
    )
    await interaction.channel.send(embed=panel_embed, view=ReadRulesView())


async def setup(bot: commands.Bot):
  await bot.add_cog(RulesCog(bot))
