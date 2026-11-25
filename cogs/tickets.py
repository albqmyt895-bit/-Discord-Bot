from datetime import datetime, timezone
import discord
from discord import app_commands
from discord.ext import commands

TICKET_PANEL_IMAGE_URL = "https://j.top4top.io/p_39816x5hr5.png"

STAFF_ROLE_IDS = [
    1552699892214792256,
    1552700483938947072,
]

TICKET_TYPES = {
    "member_report": {
        "label": "إبلاغ عن عضو",
        "needs_modal": True,
        "target_label": "يوزر العضو دسكورد",
        "target_placeholder": "مثال: username أو 123456789012345678",
        "reason_placeholder": "اكتب تفاصيل البلاغ ضد العضو...",
        "color": discord.Color.from_rgb(130, 35, 45),
        "welcome_msg": "تم فتح تكت **إبلاغ عن عضو**، اكتب أي تفاصيل إضافية أو أدلة هنا حتى يباشرها الإدارة.",
    },
    "staff_report": {
        "label": "إبلاغ عن إداري",
        "needs_modal": True,
        "target_label": "يوزر الإداري دسكورد",
        "target_placeholder": "مثال: admin_user أو 123456789012345678",
        "reason_placeholder": "اكتب تفاصيل البلاغ ضد الإداري...",
        "color": discord.Color.from_rgb(155, 85, 25),
        "welcome_msg": "تم فتح تكت **إبلاغ عن إداري**، سيتم التعامل مع البلاغ بسرية وموضوعية من قِبل الإدارة العليا.",
    },
    "inquiry": {
        "label": "إستفسار",
        "needs_modal": False,
        "color": discord.Color.from_rgb(45, 95, 155),
        "welcome_msg": "تم فتح تكت **إستفسار**، اطرح سؤالك أو استفسارك هنا ونجاوبك بإذن الله.",
    },
    "verification": {
        "label": "توثيق",
        "needs_modal": False,
        "color": discord.Color.from_rgb(185, 145, 45),
        "welcome_msg": "تم فتح تكت **توثيق**، أرسل البيانات أو المتطلبات المطلوبة للتوثيق هنا.",
    },
}


def is_staff(member: discord.abc.User | discord.Member | None) -> bool:
  if not isinstance(member, discord.Member):
    return False
  return any(role.id in STAFF_ROLE_IDS for role in member.roles)


def format_now_ar() -> str:
  now = datetime.now(timezone.utc).astimezone()
  return now.strftime("%Y-%m-%d | %I:%M:%S %p")


def build_ticket_log_text(
    ticket_number: int,
    ticket_type_label: str,
    opener_mention: str,
    claimed_by_mention: str,
    opened_at: str,
    closed_at: str,
    closed_by_mention: str,
    close_reason: str,
) -> str:
  return (
      "𓆩 HAVEN・سجل التكت 𓆪\n\n"
      "━━━━━━━━━━━━━━━━━━━━\n\n"
      "🎫 معلومات التكت\n\n"
      f"«رقم التكت: #{ticket_number:04d} ({ticket_type_label})\n"
      f"صاحب التكت: {opener_mention}\n"
      f"الإداري المستلم: {claimed_by_mention}»\n\n"
      "━━━━━━━━━━━━━━━━━━━━\n\n"
      "📅 سجل التوقيت\n\n"
      f"«وقت فتح التكت: {opened_at}\n"
      f"وقت إغلاق التكت: {closed_at}»\n\n"
      "━━━━━━━━━━━━━━━━━━━━\n\n"
      "🔒 معلومات الإغلاق\n\n"
      f"«الإداري الذي أغلق التكت: {closed_by_mention}\n"
      f"سبب إغلاق التكت: {close_reason}»\n\n"
      "━━━━━━━━━━━━━━━━━━━━\n\n"
      "𓆩 HAVEN・TICKET LOGS 𓆪"
  )


class CloseTicketReasonModal(discord.ui.Modal):

  def __init__(self, bot: commands.Bot, ticket_number: int):
    super().__init__(title=f"إغلاق التكت #{ticket_number:04d}")
    self.bot = bot
    self.ticket_number = ticket_number

    self.reason_input = discord.ui.TextInput(
        label="سبب إغلاق التكت",
        placeholder="مثال: تم حل المشكلة أو انتهاء الاستفسار...",
        required=True,
        max_length=400,
    )
    self.add_item(self.reason_input)

  async def on_submit(self, interaction: discord.Interaction):
    if not is_staff(interaction.user):
      await interaction.response.send_message(
          "⛔ الأمر مو مخول لك", ephemeral=True
      )
      return

    channel = interaction.channel
    if not isinstance(channel, discord.TextChannel):
      await interaction.response.send_message(
          "⚠️ لا يمكن إغلاق هذا الروم.", ephemeral=True
      )
      return

    reason = self.reason_input.value.strip()
    closed_at = format_now_ar()

    await interaction.response.send_message(
        f"🔒 جاري إغلاق التكت بواسطة {interaction.user.mention}...",
        ephemeral=False,
    )

    ticket_data = await get_ticket_record(self.bot, channel.id)
    if ticket_data:
      (
          t_num,
          t_type_label,
          opener_id,
          claimed_by_id,
          opened_at,
          _,
          _,
          _,
      ) = ticket_data
      opener_mention = f"<@{opener_id}>"
      claimed_mention = f"<@{claimed_by_id}>" if claimed_by_id else "لم يُستلم بعد"
      await update_ticket_closed_db(
          self.bot, channel.id, closed_at, interaction.user.id, reason
      )

      log_msg_id = ticket_data[7]
      if log_msg_id:
        try:
          log_msg = await channel.fetch_message(log_msg_id)
          updated_log = build_ticket_log_text(
              ticket_number=t_num,
              ticket_type_label=t_type_label,
              opener_mention=opener_mention,
              claimed_by_mention=claimed_mention,
              opened_at=opened_at,
              closed_at=closed_at,
              closed_by_mention=interaction.user.mention,
              close_reason=reason,
          )
          await log_msg.edit(content=updated_log)
        except Exception:
          pass

    # قفل صلاحيات الكتابة للعضو وحفظ الروم كـ مغلق
    if ticket_data:
      opener_member = interaction.guild.get_member(ticket_data[2]) if interaction.guild else None
      if opener_member:
        try:
          await channel.set_permissions(
              opener_member, view_channel=True, send_messages=False
          )
        except Exception:
          pass

    try:
      await channel.edit(
          name=f"closed-{self.ticket_number:04d}",
          reason=f"Closed by {interaction.user} | Reason: {reason}",
      )
    except Exception:
      pass

    close_embed = discord.Embed(
        title="🔒 تم إغلاق التكت",
        description=(
            f"**بواسطة:** {interaction.user.mention}\n"
            f"**السبب:** {reason}\n"
            f"**الوقت:** {closed_at}"
        ),
        color=discord.Color.from_rgb(90, 25, 30),
    )
    await channel.send(embed=close_embed)


class TicketControlView(discord.ui.View):

  def __init__(self, bot: commands.Bot):
    super().__init__(timeout=None)
    self.bot = bot

  @discord.ui.button(
      label="إغلاق التكت",
      style=discord.ButtonStyle.danger,
      emoji="🔒",
      custom_id="haven_ticket_close_btn",
  )
  async def close_ticket_button(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    if not is_staff(interaction.user):
      await interaction.response.send_message(
          "⛔ الأمر مو مخول لك", ephemeral=True
      )
      return

    ticket_number = 0
    if isinstance(interaction.channel, discord.TextChannel):
      record = await get_ticket_record(self.bot, interaction.channel.id)
      if record:
        ticket_number = record[0]
        if not record[3]:
          await set_ticket_claimed_db(
              self.bot, interaction.channel.id, interaction.user.id
          )

    await interaction.response.send_modal(
        CloseTicketReasonModal(self.bot, ticket_number)
    )

  @discord.ui.button(
      label="منشن الإدارة",
      style=discord.ButtonStyle.secondary,
      emoji="📣",
      custom_id="haven_ticket_ping_staff_btn",
  )
  async def ping_staff_button(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    staff_mentions = " ".join(f"<@&{role_id}>" for role_id in STAFF_ROLE_IDS)
    embed = discord.Embed(
        title="📣 نداء الإدارة — HAVEN",
        description=(
            "الحين تبشر امنشنهم لك\n\n"
            f"{staff_mentions}\n\n"
            f"**بواسطة:** {interaction.user.mention}"
        ),
        color=discord.Color.from_rgb(195, 155, 55),
    )
    embed.set_footer(text="HAVEN Support System")
    await interaction.response.send_message(embed=embed)


class ReportSurveyModal(discord.ui.Modal):

  def __init__(
      self, bot: commands.Bot, ticket_key: str, target_label: str, target_placeholder: str, reason_placeholder: str
  ):
    cfg = TICKET_TYPES[ticket_key]
    super().__init__(title=f"{cfg['label']} — تعبئة البيانات")
    self.bot = bot
    self.ticket_key = ticket_key

    self.target_input = discord.ui.TextInput(
        label=target_label,
        placeholder=target_placeholder,
        required=True,
        max_length=120,
    )
    self.add_item(self.target_input)

    self.reason_input = discord.ui.TextInput(
        label="السبب",
        placeholder=reason_placeholder,
        required=True,
        style=discord.TextStyle.paragraph,
        max_length=800,
    )
    self.add_item(self.reason_input)

  async def on_submit(self, interaction: discord.Interaction):
    await open_ticket_channel(
        interaction=interaction,
        bot=self.bot,
        ticket_key=self.ticket_key,
        reported_user=self.target_input.value.strip(),
        reason=self.reason_input.value.strip(),
    )


class TicketPanelView(discord.ui.View):

  def __init__(self, bot: commands.Bot):
    super().__init__(timeout=None)
    self.bot = bot

  @discord.ui.button(
      label="ＩＢＬＡＧＨ ・ إبلاغ عن عضو",
      style=discord.ButtonStyle.danger,
      emoji="⚔️",
      custom_id="haven_btn_member_report",
      row=0,
  )
  async def member_report_btn(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    cfg = TICKET_TYPES["member_report"]
    await interaction.response.send_modal(
        ReportSurveyModal(
            bot=self.bot,
            ticket_key="member_report",
            target_label=cfg["target_label"],
            target_placeholder=cfg["target_placeholder"],
            reason_placeholder=cfg["reason_placeholder"],
        )
    )

  @discord.ui.button(
      label="ＩＢＬＡＧＨ ・ إبلاغ عن إداري",
      style=discord.ButtonStyle.secondary,
      emoji="🛡️",
      custom_id="haven_btn_staff_report",
      row=0,
  )
  async def staff_report_btn(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    cfg = TICKET_TYPES["staff_report"]
    await interaction.response.send_modal(
        ReportSurveyModal(
            bot=self.bot,
            ticket_key="staff_report",
            target_label=cfg["target_label"],
            target_placeholder=cfg["target_placeholder"],
            reason_placeholder=cfg["reason_placeholder"],
        )
    )

  @discord.ui.button(
      label="✦ ＩＮＱＵＩＲＹ ・ إستفسار",
      style=discord.ButtonStyle.primary,
      emoji="💬",
      custom_id="haven_btn_inquiry",
      row=1,
  )
  async def inquiry_btn(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    await open_ticket_channel(
        interaction=interaction, bot=self.bot, ticket_key="inquiry"
    )

  @discord.ui.button(
      label="❖ ＶＥＲＩＦＩＣＡＴＩＯＮ ・ توثيق",
      style=discord.ButtonStyle.success,
      emoji="👑",
      custom_id="haven_btn_verification",
      row=1,
  )
  async def verification_btn(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    await open_ticket_channel(
        interaction=interaction, bot=self.bot, ticket_key="verification"
    )


async def ensure_ticket_tables(bot: commands.Bot):
  db = getattr(bot, "db", None)
  if not db or not getattr(db, "conn", None):
    return

  await db.conn.execute("""
      CREATE TABLE IF NOT EXISTS ticket_counter (
          id INTEGER PRIMARY KEY CHECK (id = 1),
          last_number INTEGER NOT NULL DEFAULT 0
      )
      """)
  await db.conn.execute("""
      INSERT OR IGNORE INTO ticket_counter (id, last_number) VALUES (1, 0)
      """)
  await db.conn.execute("""
      CREATE TABLE IF NOT EXISTS tickets (
          channel_id INTEGER PRIMARY KEY,
          ticket_number INTEGER NOT NULL,
          ticket_type TEXT NOT NULL,
          ticket_type_label TEXT NOT NULL,
          opener_id INTEGER NOT NULL,
          claimed_by_id INTEGER,
          opened_at TEXT NOT NULL,
          closed_at TEXT,
          closed_by_id INTEGER,
          close_reason TEXT,
          log_message_id INTEGER
      )
      """)
  await db.conn.commit()


async def next_ticket_number(bot: commands.Bot) -> int:
  db = getattr(bot, "db", None)
  if db and getattr(db, "conn", None):
    await db.conn.execute(
        "UPDATE ticket_counter SET last_number = last_number + 1 WHERE id = 1"
    )
    await db.conn.commit()
    async with db.conn.execute(
        "SELECT last_number FROM ticket_counter WHERE id = 1"
    ) as cursor:
      row = await cursor.fetchone()
      if row:
        return int(row[0])

  # احتياطي في حال عدم وجود قاعدة بيانات متصلة
  return int(datetime.now(timezone.utc).timestamp()) % 10000


async def save_ticket_record(
    bot: commands.Bot,
    channel_id: int,
    ticket_number: int,
    ticket_type: str,
    ticket_type_label: str,
    opener_id: int,
    opened_at: str,
    log_message_id: int,
):
  db = getattr(bot, "db", None)
  if not db or not getattr(db, "conn", None):
    return
  await db.conn.execute(
      """
      INSERT OR REPLACE INTO tickets (
          channel_id, ticket_number, ticket_type, ticket_type_label,
          opener_id, claimed_by_id, opened_at, closed_at, closed_by_id,
          close_reason, log_message_id
      ) VALUES (?, ?, ?, ?, ?, NULL, ?, NULL, NULL, NULL, ?)
      """,
      (
          channel_id,
          ticket_number,
          ticket_type,
          ticket_type_label,
          opener_id,
          opened_at,
          log_message_id,
      ),
  )
  await db.conn.commit()


async def get_ticket_record(bot: commands.Bot, channel_id: int):
  db = getattr(bot, "db", None)
  if not db or not getattr(db, "conn", None):
    return None
  async with db.conn.execute(
      """
      SELECT ticket_number, ticket_type_label, opener_id, claimed_by_id,
             opened_at, closed_at, close_reason, log_message_id
      FROM tickets WHERE channel_id = ?
      """,
      (channel_id,),
  ) as cursor:
    return await cursor.fetchone()


async def set_ticket_claimed_db(
    bot: commands.Bot, channel_id: int, staff_id: int
):
  db = getattr(bot, "db", None)
  if not db or not getattr(db, "conn", None):
    return
  await db.conn.execute(
      "UPDATE tickets SET claimed_by_id = ? WHERE channel_id = ? AND claimed_by_id IS NULL",
      (staff_id, channel_id),
  )
  await db.conn.commit()


async def update_ticket_closed_db(
    bot: commands.Bot,
    channel_id: int,
    closed_at: str,
    closed_by_id: int,
    close_reason: str,
):
  db = getattr(bot, "db", None)
  if not db or not getattr(db, "conn", None):
    return
  await db.conn.execute(
      """
      UPDATE tickets
      SET closed_at = ?, closed_by_id = ?, close_reason = ?
      WHERE channel_id = ?
      """,
      (closed_at, closed_by_id, close_reason, channel_id),
  )
  await db.conn.commit()


async def open_ticket_channel(
    interaction: discord.Interaction,
    bot: commands.Bot,
    ticket_key: str,
    reported_user: str | None = None,
    reason: str | None = None,
):
  guild = interaction.guild
  if not guild:
    await interaction.response.send_message(
        "⚠️ هذا الأمر يعمل داخل السيرفرات فقط.", ephemeral=True
    )
    return

  cfg = TICKET_TYPES[ticket_key]
  await ensure_ticket_tables(bot)
  ticket_number = await next_ticket_number(bot)
  opened_at = format_now_ar()

  overwrites: dict[discord.abc.Snowflake, discord.PermissionOverwrite] = {
      guild.default_role: discord.PermissionOverwrite(view_channel=False),
      interaction.user: discord.PermissionOverwrite(
          view_channel=True,
          send_messages=True,
          read_message_history=True,
          attach_files=True,
      ),
      guild.me: discord.PermissionOverwrite(
          view_channel=True,
          send_messages=True,
          manage_channels=True,
          manage_messages=True,
          read_message_history=True,
      ),
  }

  for role_id in STAFF_ROLE_IDS:
    role = guild.get_role(role_id)
    if role:
      overwrites[role] = discord.PermissionOverwrite(
          view_channel=True,
          send_messages=True,
          read_message_history=True,
          attach_files=True,
      )

  channel_name = f"ticket-{ticket_number:04d}-{interaction.user.name[:12]}".lower()

  try:
    ticket_channel = await guild.create_text_channel(
        name=channel_name,
        overwrites=overwrites,
        reason=f"Ticket #{ticket_number:04d} ({cfg['label']}) by {interaction.user}",
    )
  except discord.Forbidden:
    await interaction.response.send_message(
        "❌ البوت لا يملك صلاحية `Manage Channels` لفتح التكت.",
        ephemeral=True,
    )
    return

  log_text = build_ticket_log_text(
      ticket_number=ticket_number,
      ticket_type_label=cfg["label"],
      opener_mention=interaction.user.mention,
      claimed_by_mention="لم يُستلم بعد",
      opened_at=opened_at,
      closed_at="لم يُغلق بعد",
      closed_by_mention="لم يُغلق بعد",
      close_reason="لم يُغلق بعد",
  )

  log_msg = await ticket_channel.send(log_text)

  info_embed = discord.Embed(
      title=f"✦ {cfg['label']} — تكت #{ticket_number:04d}",
      description=cfg["welcome_msg"],
      color=cfg["color"],
  )
  info_embed.add_field(
      name="صاحب التكت", value=interaction.user.mention, inline=True
  )
  info_embed.add_field(name="النوع", value=cfg["label"], inline=True)

  if reported_user and reason:
    info_embed.add_field(
        name=cfg["target_label"], value=f"`{reported_user}`", inline=False
    )
    info_embed.add_field(name="السبب", value=reason, inline=False)

  info_embed.set_footer(text="HAVEN Ticket System")

  await ticket_channel.send(
      content=f"{interaction.user.mention}",
      embed=info_embed,
      view=TicketControlView(bot),
  )

  await save_ticket_record(
      bot=bot,
      channel_id=ticket_channel.id,
      ticket_number=ticket_number,
      ticket_type=ticket_key,
      ticket_type_label=cfg["label"],
      opener_id=interaction.user.id,
      opened_at=opened_at,
      log_message_id=log_msg.id,
  )

  await interaction.response.send_message(
      f"✅ تم فتح التكت الخاص بك بنجاح: {ticket_channel.mention}",
      ephemeral=True,
  )


class TicketsCog(commands.Cog):

  def __init__(self, bot: commands.Bot):
    self.bot = bot

  async def cog_load(self):
    self.bot.add_view(TicketPanelView(self.bot))
    self.bot.add_view(TicketControlView(self.bot))
    await ensure_ticket_tables(self.bot)

  @app_commands.command(
      name="ticket", description="إرسال لوحة فتح التذاكر في السيرفر"
  )
  async def ticket(self, interaction: discord.Interaction):
    if not interaction.channel:
      await interaction.response.send_message(
          "⚠️ لا يمكن إرسال اللوحة هنا.", ephemeral=True
      )
      return

    embed = discord.Embed(
        title="🎫 نظام التذاكر — HAVEN",
        description="افتح تكت حسب مشكلتك وبنحلها لك بإذن الله",
        color=discord.Color.from_rgb(24, 24, 30),
    )
    embed.set_image(url=TICKET_PANEL_IMAGE_URL)
    embed.set_footer(text="اختر نوع التكت المناسب من الأزرار بالأسفل")

    await interaction.response.send_message(
        "✅ تم إرسال لوحة التذاكر.", ephemeral=True
    )
    await interaction.channel.send(embed=embed, view=TicketPanelView(self.bot))


async def setup(bot: commands.Bot):
  await bot.add_cog(TicketsCog(bot))
