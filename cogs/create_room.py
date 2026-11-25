import discord
from discord import app_commands
from discord.ext import commands

OWNER_ID = 1495450684731162664


def is_authorized(user_id: int) -> bool:
  return user_id == OWNER_ID


# --- الخطوة 2: نافذة إدخال الاسم والوصف ---
class RoomNameModal(discord.ui.Modal):

  def __init__(self, room_type: str, is_private: bool):
    super().__init__(title="إعدادات الروم الجديد")
    self.room_type = room_type
    self.is_private = is_private

    self.name_input = discord.ui.TextInput(
        label="اسم الروم / الكاتجوري",
        placeholder="مثال: غرفة-العمليات أو الدردشة العامة",
        required=True,
        max_length=100,
    )
    self.add_item(self.name_input)

    if room_type == "text":
      self.topic_input = discord.ui.TextInput(
          label="وصف الروم (اختياري)",
          placeholder="اكتب وصفاً مختصراً للشات...",
          required=False,
          max_length=500,
      )
      self.add_item(self.topic_input)
    else:
      self.topic_input = None

  async def on_submit(self, interaction: discord.Interaction):
    if not is_authorized(interaction.user.id):
      await interaction.response.send_message(
          "⛔ هذا الأمر مخصص للمالك فقط.", ephemeral=True
      )
      return

    room_name = self.name_input.value.strip()
    topic = self.topic_input.value.strip() if self.topic_input else None

    if self.room_type == "category":
      overwrites = {}
      if self.is_private:
        overwrites[interaction.guild.default_role] = (
            discord.PermissionOverwrite(view_channel=False)
        )
        overwrites[interaction.user] = discord.PermissionOverwrite(
            view_channel=True, manage_channels=True
        )

      category = await interaction.guild.create_category(
          name=room_name, overwrites=overwrites
      )
      embed = discord.Embed(
          title="✅ تم إنشاء الكاتجوري بنجاح",
          description=f"**الاسم:** {category.name}\n**الآيدي:** `{category.id}`",
          color=discord.Color.gold(),
      )
      await interaction.response.edit_message(
          content=None, embed=embed, view=None
      )
      return

    categories = list(interaction.guild.categories)[:24]
    options = [
        discord.SelectOption(
            label="بدون كاتجوري (في أعلى السيرفر)",
            value="none",
            emoji="📌",
            description="إنشاء الروم خارج أي كاتجوري",
        )
    ]
    for cat in categories:
      options.append(
          discord.SelectOption(
              label=cat.name[:100],
              value=str(cat.id),
              emoji="📁",
              description=f"عدد الرومات: {len(cat.channels)}",
          )
      )

    select_view = CategorySelectView(
        room_type=self.room_type,
        room_name=room_name,
        topic=topic,
        is_private=self.is_private,
        options=options,
    )
    await interaction.response.edit_message(
        content=f"اختر الكاتجوري المناسب لإنشاء **{room_name}** داخله:",
        embed=None,
        view=select_view,
    )


# --- الخطوة 3: قائمة اختيار الكاتجوري ---
class CategorySelect(discord.ui.Select):

  def __init__(
      self,
      room_type: str,
      room_name: str,
      topic: str | None,
      is_private: bool,
      options: list[discord.SelectOption],
  ):
    super().__init__(
        placeholder="اختر الكاتجوري من القائمة...",
        min_values=1,
        max_values=1,
        options=options,
    )
    self.room_type = room_type
    self.room_name = room_name
    self.topic = topic
    self.is_private = is_private

  async def callback(self, interaction: discord.Interaction):
    if not is_authorized(interaction.user.id):
      await interaction.response.send_message(
          "⛔ غير مسموح لك بإتمام هذا الإجراء.", ephemeral=True
      )
      return

    chosen_value = self.values[0]
    target_category = None
    if chosen_value != "none":
      target_category = interaction.guild.get_channel(int(chosen_value))

    overwrites = {}
    if self.is_private:
      overwrites[interaction.guild.default_role] = discord.PermissionOverwrite(
          view_channel=False
      )
      overwrites[interaction.user] = discord.PermissionOverwrite(
          view_channel=True, manage_channels=True, connect=True, speak=True
      )

    guild = interaction.guild
    if self.room_type == "text":
      created = await guild.create_text_channel(
          name=self.room_name,
          category=target_category,
          topic=self.topic,
          overwrites=overwrites,
      )
    else:
      created = await guild.create_voice_channel(
          name=self.room_name,
          category=target_category,
          overwrites=overwrites,
      )

    if target_category and not self.is_private:
      await created.edit(sync_permissions=True)

    embed = discord.Embed(
        title="✅ تم إنشاء الروم بنجاح",
        color=discord.Color.green(),
    )
    embed.add_field(name="الروم", value=created.mention, inline=True)
    embed.add_field(
        name="النوع",
        value="💬 شات كتابي" if self.room_type == "text" else "🔊 روم صوتي",
        inline=True,
    )
    embed.add_field(
        name="الكاتجوري",
        value=target_category.name if target_category else "بدون كاتجوري",
        inline=False,
    )
    embed.add_field(
        name="الخصوصية",
        value="🔒 خاص (مخفي)" if self.is_private else "🌐 عام",
        inline=True,
    )

    await interaction.response.edit_message(content=None, embed=embed, view=None)


class CategorySelectView(discord.ui.View):

  def __init__(
      self,
      room_type: str,
      room_name: str,
      topic: str | None,
      is_private: bool,
      options: list[discord.SelectOption],
  ):
    super().__init__(timeout=120)
    self.add_item(
        CategorySelect(room_type, room_name, topic, is_private, options)
    )


# --- الخطوة 1: أزرار اختيار النوع + زر الخصوصية ---
class RoomSetupView(discord.ui.View):

  def __init__(self):
    super().__init__(timeout=120)
    self.is_private = False

  async def interaction_check(self, interaction: discord.Interaction) -> bool:
    if not is_authorized(interaction.user.id):
      await interaction.response.send_message(
          "⛔ هذا الأمر مخصص لصاحب الآيدي المحدد فقط، ولا يحق لك استخدامه.",
          ephemeral=True,
      )
      return False
    return True

  @discord.ui.button(
      label="كاتجوري (Category)", style=discord.ButtonStyle.primary, emoji="📁"
  )
  async def create_category_btn(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    await interaction.response.send_modal(
        RoomNameModal(room_type="category", is_private=self.is_private)
    )

  @discord.ui.button(
      label="روم شات (Text)", style=discord.ButtonStyle.success, emoji="💬"
  )
  async def create_text_btn(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    await interaction.response.send_modal(
        RoomNameModal(room_type="text", is_private=self.is_private)
    )

  @discord.ui.button(
      label="روم صوتي (Voice)", style=discord.ButtonStyle.success, emoji="🔊"
  )
  async def create_voice_btn(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    await interaction.response.send_modal(
        RoomNameModal(room_type="voice", is_private=self.is_private)
    )

  @discord.ui.button(
      label="الوضع: عام", style=discord.ButtonStyle.secondary, emoji="🌐"
  )
  async def toggle_private_btn(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    self.is_private = not self.is_private
    if self.is_private:
      button.label = "الوضع: خاص (مخفي)"
      button.style = discord.ButtonStyle.danger
      button.emoji = "🔒"
    else:
      button.label = "الوضع: عام"
      button.style = discord.ButtonStyle.secondary
      button.emoji = "🌐"
    await interaction.response.edit_message(view=self)


class CreateRoomCog(commands.Cog):

  def __init__(self, bot: commands.Bot):
    self.bot = bot

  @app_commands.command(
      name="create_room",
      description="إنشاء كاتجوري أو روم كتابي أو صوتي بخطوات تفاعلية",
  )
  async def create_room(self, interaction: discord.Interaction):
    if not is_authorized(interaction.user.id):
      await interaction.response.send_message(
          "⛔ عذراً، هذا الأمر محصور على المستخدم المصرح له فقط.",
          ephemeral=True,
      )
      return

    embed = discord.Embed(
        title="🛠️ لوحة إنشاء الرومات",
        description=(
            "اختر نوع العنصر الذي تريد إنشاءه من الأزرار بالأسفل.\n"
            "يمكنك أيضاً تبديل زر **الوضع** قبل الضغط على النوع إذا أردت الروم"
            " مخفياً."
        ),
        color=discord.Color.blurple(),
    )
    await interaction.response.send_message(
        embed=embed, view=RoomSetupView(), ephemeral=True
    )


async def setup(bot: commands.Bot):
  await bot.add_cog(CreateRoomCog(bot))
