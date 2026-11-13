
import json
import logging
from datetime import datetime, timezone

import discord
from discord.ext import commands


logger = logging.getLogger("Bot.Backup")


class Backup(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    # =========================
    # DATABASE
    # =========================

    async def prepare_database(self):
        await self.bot.db.execute("""
            CREATE TABLE IF NOT EXISTS server_backups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                owner_id INTEGER NOT NULL,
                backup_data TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

    async def get_backup(self, guild_id, backup_id):
        return await self.bot.db.fetchone(
            """
            SELECT * FROM server_backups
            WHERE guild_id = ? AND id = ?
            """,
            (guild_id, backup_id)
        )

    # =========================
    # CHANNEL SNAPSHOT
    # =========================

    def get_overwrites(self, channel):
        result = []

        for target, overwrite in channel.overwrites.items():

            if isinstance(target, discord.Role):
                target_type = "role"

            elif isinstance(target, discord.Member):
                target_type = "member"

            else:
                continue

            allow, deny = overwrite.pair()

            result.append({
                "type": target_type,
                "id": target.id,
                "name": target.name,
                "allow": allow.value,
                "deny": deny.value
            })

        return result

    def snapshot_channel(self, channel):

        channel_type = getattr(
            channel.type,
            "name",
            str(channel.type)
        )

        data = {
            "id": channel.id,
            "name": channel.name,
            "type": channel_type,
            "position": channel.position,
            "category_id": (
                channel.category.id
                if channel.category else None
            ),
            "category_name": (
                channel.category.name
                if channel.category else None
            ),
            "overwrites": self.get_overwrites(channel)
        }

        if isinstance(channel, discord.TextChannel):

            data.update({
                "topic": channel.topic,
                "nsfw": channel.nsfw,
                "slowmode": channel.slowmode_delay,
                "default_auto_archive_duration":
                    channel.default_auto_archive_duration
            })

        elif isinstance(channel, discord.VoiceChannel):

            data.update({
                "bitrate": channel.bitrate,
                "user_limit": channel.user_limit,
                "rtc_region": (
                    str(channel.rtc_region)
                    if channel.rtc_region else None
                )
            })

        return data

    # =========================
    # PERMISSION RESTORATION
    # =========================

    async def resolve_overwrites(self, guild, saved):

        overwrites = {}

        for item in saved:

            target = None

            if item["type"] == "role":

                target = guild.get_role(item["id"])

                if target is None:

                    matches = [
                        role for role in guild.roles
                        if role.name == item["name"]
                    ]

                    if len(matches) == 1:
                        target = matches[0]

            elif item["type"] == "member":

                target = guild.get_member(item["id"])

            if target is None:
                continue

            allow = discord.Permissions(item["allow"])
            deny = discord.Permissions(item["deny"])

            overwrites[target] = (
                discord.PermissionOverwrite.from_pair(
                    allow,
                    deny
                )
            )

        return overwrites

    # =========================
    # CREATE BACKUP
    # =========================

    @commands.command(name="حفظ")
    @commands.guild_only()
    @commands.has_guild_permissions(administrator=True)
    @commands.bot_has_guild_permissions(manage_channels=True)
    async def backup(self, ctx):

        await self.prepare_database()

        guild = ctx.guild

        channels = [
            self.snapshot_channel(channel)
            for channel in guild.channels
        ]

        data = {
            "version": 1,
            "guild_id": guild.id,
            "guild_name": guild.name,
            "created_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "channels": channels
        }

        await self.bot.db.execute(
            """
            INSERT INTO server_backups
            (guild_id, owner_id, backup_data, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                guild.id,
                ctx.author.id,
                json.dumps(data, ensure_ascii=False),
                data["created_at"]
            )
        )

        row = await self.bot.db.fetchone(
            """
            SELECT MAX(id) AS backup_id
            FROM server_backups
            WHERE guild_id = ?
            """,
            (guild.id,)
        )

        embed = discord.Embed(
            title="تم حفظ السيرفر",
            description=(
                "تم إنشاء النسخة الاحتياطية بنجاح.\n"
                f"رقم النسخة: `{row['backup_id']}`\n"
                f"عدد الرومات والتصنيفات: `{len(channels)}`"
            ),
            color=discord.Color.gold()
        )

        await ctx.reply(embed=embed)

    # =========================
    # LIST BACKUPS
    # =========================

    @commands.command(name="النسخ")
    @commands.guild_only()
    @commands.has_guild_permissions(administrator=True)
    async def backups(self, ctx):

        await self.prepare_database()

        rows = await self.bot.db.fetchall(
            """
            SELECT id, created_at, backup_data
            FROM server_backups
            WHERE guild_id = ?
            ORDER BY id DESC
            LIMIT 15
            """,
            (ctx.guild.id,)
        )

        if not rows:
            return await ctx.reply(
                "لا توجد نسخ احتياطية."
            )

        embed = discord.Embed(
            title="النسخ الاحتياطية",
            color=discord.Color.gold()
        )

        for row in rows:

            data = json.loads(row["backup_data"])

            embed.add_field(
                name=f"النسخة رقم {row['id']}",
                value=(
                    f"السيرفر: {data['guild_name']}\n"
                    f"العناصر: {len(data['channels'])}\n"
                    f"التاريخ: {row['created_at']}"
                ),
                inline=False
            )

        await ctx.reply(embed=embed)

    # =========================
    # BACKUP INFORMATION
    # =========================

    @commands.command(name="معلومات")
    @commands.guild_only()
    @commands.has_guild_permissions(administrator=True)
    async def backup_info(self, ctx, backup_id: int):

        await self.prepare_database()

        row = await self.get_backup(
            ctx.guild.id,
            backup_id
        )

        if not row:
            return await ctx.reply(
                "النسخة غير موجودة."
            )

        data = json.loads(row["backup_data"])

        embed = discord.Embed(
            title=f"معلومات النسخة رقم {backup_id}",
            color=discord.Color.gold()
        )

        embed.add_field(
            name="السيرفر",
            value=data["guild_name"],
            inline=True
        )

        embed.add_field(
            name="عدد الرومات والتصنيفات",
            value=str(len(data["channels"])),
            inline=True
        )

        embed.add_field(
            name="تاريخ الحفظ",
            value=row["created_at"],
            inline=False
        )

        await ctx.reply(embed=embed)

    # =========================
    # RESTORE BACKUP
    # =========================

    @commands.command(name="استعادة")
    @commands.guild_only()
    @commands.has_guild_permissions(administrator=True)
    @commands.bot_has_guild_permissions(manage_channels=True)
    async def restore(self, ctx, backup_id: int):

        await self.prepare_database()

        row = await self.get_backup(
            ctx.guild.id,
            backup_id
        )

        if not row:
            return await ctx.reply(
                "النسخة غير موجودة."
            )

        data = json.loads(row["backup_data"])

        if data.get("version") != 1:
            return await ctx.reply(
                "إصدار النسخة غير مدعوم."
            )

        await ctx.reply(
            f"سيتم استعادة العناصر الناقصة من النسخة "
            f"`{backup_id}`.\n"
            "لن يتم حذف الرومات الموجودة أو تعديلها.\n"
            "اكتب `تأكيد` خلال 30 ثانية للمتابعة."
        )

        def check(message):
            return (
                message.author.id == ctx.author.id
                and message.channel.id == ctx.channel.id
                and message.content == "تأكيد"
            )

        try:

            await self.bot.wait_for(
                "message",
                timeout=30,
                check=check
            )

        except TimeoutError:

            return await ctx.reply(
                "انتهت مهلة التأكيد."
            )

        guild = ctx.guild
        saved_channels = data["channels"]

        restored = 0
        skipped = 0
        failed = 0

        category_map = {}

        # Restore categories first

        categories = [
            item for item in saved_channels
            if item["type"] == "category"
        ]

        for item in sorted(
            categories,
            key=lambda x: x["position"]
        ):

            existing = discord.utils.get(
                guild.categories,
                name=item["name"]
            )

            if existing:

                category_map[item["id"]] = existing
                skipped += 1
                continue

            try:

                overwrites = await self.resolve_overwrites(
                    guild,
                    item["overwrites"]
                )

                category = await guild.create_category(
                    name=item["name"],
                    overwrites=overwrites,
                    reason="Server backup restoration"
                )

                await category.edit(
                    position=item["position"]
                )

                category_map[item["id"]] = category
                restored += 1

            except (discord.HTTPException, TypeError, ValueError):

                logger.exception(
                    "Could not restore category %s",
                    item["name"]
                )

                failed += 1

        # Restore text and voice channels

        supported_types = {
            "text": discord.ChannelType.text,
            "news": discord.ChannelType.news,
            "voice": discord.ChannelType.voice
        }

        for item in sorted(
            saved_channels,
            key=lambda x: x["position"]
        ):

            channel_type = item["type"]

            if channel_type == "category":
                continue

            expected_type = supported_types.get(
                channel_type
            )

            if expected_type is None:

                skipped += 1
                continue

            category = category_map.get(
                item.get("category_id")
            )

            if category is None and item.get("category_name"):

                category = discord.utils.get(
                    guild.categories,
                    name=item["category_name"]
                )

            # Check whether the channel already exists

            existing = None

            for channel in guild.channels:

                current_type = getattr(
                    channel.type,
                    "name",
                    str(channel.type)
                )

                if channel.name != item["name"]:
                    continue

                if channel.type != expected_type:
                    continue

                existing_category = (
                    channel.category.name
                    if channel.category else None
                )

                if existing_category == item.get(
                    "category_name"
                ):

                    existing = channel
                    break

            if existing:

                skipped += 1
                continue

            try:

                overwrites = await self.resolve_overwrites(
                    guild,
                    item["overwrites"]
                )

                common = {
                    "name": item["name"],
                    "category": category,
                    "overwrites": overwrites,
                    "reason": "Server backup restoration"
                }

                if channel_type in ("text", "news"):

                    channel = await guild.create_text_channel(
                        **common,
                        topic=item.get("topic"),
                        nsfw=item.get("nsfw", False),
                        slowmode_delay=item.get("slowmode", 0),
                        news=(channel_type == "news"),
                        default_auto_archive_duration=item.get(
                            "default_auto_archive_duration", 1440
                        )
                    )

                elif channel_type == "voice":

                    channel = await guild.create_voice_channel(
                        **common,
                        bitrate=item.get("bitrate", 64000),
                        user_limit=item.get("user_limit", 0)
                    )

                await channel.edit(
                    position=item["position"]
                )

                restored += 1

            except (discord.HTTPException, TypeError, ValueError):

                logger.exception(
                    "Could not restore channel %s",
                    item["name"]
                )

                failed += 1

        # Restoration report

        embed = discord.Embed(
            title="تقرير الاستعادة",
            color=discord.Color.gold()
        )

        embed.add_field(
            name="تمت استعادته",
            value=str(restored),
            inline=True
        )

        embed.add_field(
            name="تم تجاوزه",
            value=str(skipped),
            inline=True
        )

        embed.add_field(
            name="تعذر استعادته",
            value=str(failed),
            inline=True
        )

        await ctx.reply(embed=embed)

    # =========================
    # DELETE BACKUP
    # =========================

    @commands.command(name="حذف_نسخة")
    @commands.guild_only()
    @commands.has_guild_permissions(administrator=True)
    async def delete_backup(self, ctx, backup_id: int):

        await self.prepare_database()

        row = await self.get_backup(
            ctx.guild.id,
            backup_id
        )

        if not row:
            return await ctx.reply(
                "النسخة غير موجودة."
            )

        await self.bot.db.execute(
            """
            DELETE FROM server_backups
            WHERE guild_id = ? AND id = ?
            """,
            (ctx.guild.id, backup_id)
        )

        await ctx.reply(
            f"تم حذف النسخة رقم `{backup_id}`."
        )

    # =========================
    # ERROR HANDLING
    # =========================

    @backup.error
    @backups.error
    @backup_info.error
    @restore.error
    @delete_backup.error
    async def command_error(self, ctx, error):

        if isinstance(error, commands.MissingPermissions):

            await ctx.reply(
                "هذا الأمر مخصص لمسؤولي السيرفر."
            )

        elif isinstance(error, commands.BotMissingPermissions):

            await ctx.reply(
                "البوت لا يمتلك الصلاحيات المطلوبة."
            )

        elif isinstance(error, commands.MissingRequiredArgument):

            await ctx.reply(
                "يرجى كتابة رقم النسخة المطلوبة."
            )

        elif isinstance(error, commands.BadArgument):

            await ctx.reply(
                "رقم النسخة غير صحيح."
            )

        else:

            logger.error(
                "Backup command error",
                exc_info=(
                    type(error),
                    error,
                    error.__traceback__
                )
            )

            await ctx.reply(
                "حدث خطأ أثناء تنفيذ الأمر."
            )


async def setup(bot):
    await bot.add_cog(Backup(bot))
