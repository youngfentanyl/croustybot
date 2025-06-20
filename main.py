import discord
from discord.ext import commands
import random

BOT_PREFIX = "pjt!"
intents = discord.Intents.default()
intents.message_content = True
RULESET_CHANNEL_ID = 1384999264031084565
CATEGORY_ID = 1384154642166059088

bot = commands.Bot(command_prefix=BOT_PREFIX, intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Bot connecté en tant que {bot.user.name}")
    await bot.change_presence(activity=discord.Game(name="Préparation des tournois..."))

@bot.command(name="ping")
async def ping(ctx):
    ping_value = random.randint(20, 100)
    embed = discord.Embed(
        title="CroustyBot Ping",
        description=f"Here's my ping:\n`{ping_value} ms`",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

TICKET_MESSAGE = {
    "title": "🎟️ Tournament Registration",
    "description": (
        "Please provide the following information:\n\n"
        "1. **Team Name**\n"
        "2. **Team Tag**\n"
        "3. **Competitive Roster** (list all players using Discord tags, e.g. `User#0001`)"
    ),
    "color": discord.Color.dark_gray()
}

class JoinButton(discord.ui.View):
    def __init__(self, author: discord.Member):
        super().__init__(timeout=None)
        self.author = author

    @discord.ui.button(label="Join Tournament", style=discord.ButtonStyle.secondary)
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            await interaction.response.send_message("❌ Only the command author can use this button.", ephemeral=True)
            return

        guild = interaction.guild
        category = guild.get_channel(CATEGORY_ID)
        if not category or not isinstance(category, discord.CategoryChannel):
            await interaction.response.send_message("❌ Ticket category not found.", ephemeral=True)
            return

        channel = await guild.create_text_channel(
            name=f"ticket-{interaction.user.name}",
            category=category,
            overwrites={
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
        )

        embed = discord.Embed(
            title=TICKET_MESSAGE["title"],
            description=TICKET_MESSAGE["description"],
            color=TICKET_MESSAGE["color"]
        )

        await channel.send(content=f"{interaction.user.mention}", embed=embed)
        await interaction.response.send_message(f"✅ Ticket created: {channel.mention}", ephemeral=True)

@bot.command(name="newtournament")
async def new_tournament(ctx, *, args: str):
    try:
        parts = [part.strip() for part in args.split("/")]

        if len(parts) != 6:
            await ctx.send("❌ Invalid format. Use: `pjt!newtournament Name/Description/Format/MaxTeams/AdditionalMessage/DD,MM,YYYY,HH:MM`")
            return

        title, description, format_, max_teams, extra_msg, raw_schedule = parts
        valid_formats = ["1v1", "2v2", "3v3", "4v4", "5v5"]

        if format_ not in valid_formats:
            await ctx.send("❌ Invalid format. Choose from: 1v1, 2v2, 3v3, 4v4, 5v5.")
            return

        if not max_teams.isdigit():
            await ctx.send("❌ Max teams must be an integer.")
            return

        # Parse date & time
        try:
            day, month, year, hour_minute = raw_schedule.split(",")
            hour, minute = map(int, hour_minute.split(":"))
            from datetime import datetime, timezone, timedelta
            uk_offset = timedelta(hours=1)  # UK time = UTC+1 in July (BST)
            dt = datetime(int(year), int(month), int(day), hour, minute, tzinfo=timezone.utc) - uk_offset
            timestamp = int(dt.timestamp())
            schedule_value = f"<t:{timestamp}:F>"
        except Exception:
            await ctx.send("❌ Invalid date format. Use: `DD,MM,YYYY,HH:MM` (e.g. 06,07,2025,22:30)")
            return

        embed = discord.Embed(
            title=f"Tournament: {title}",
            description=f"> {description}",
            color=discord.Color.teal()
        )
        embed.add_field(name="🧩 Format", value=format_, inline=True)
        embed.add_field(name="👥 Max Teams", value=max_teams, inline=True)
        embed.add_field(name="📜 Ruleset", value=f"<#{RULESET_CHANNEL_ID}>", inline=True)
        embed.add_field(name="📅 Schedule", value=schedule_value, inline=True)
        embed.add_field(name="\u200b", value=extra_msg, inline=False)
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/1055/1055646.png")
        embed.set_footer(text=f"Organized by {ctx.author.display_name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)

        view = JoinButton(ctx.author)
        await ctx.send(embed=embed, view=view)

    except Exception as e:
        await ctx.send(f"❌ An error occurred: {e}")

def load_token(path="bot-token.txt"):
    with open(path, "r") as file:
        for line in file:
            if line.startswith("TOKEN="):
                return line.strip().split("TOKEN=")[1]
    raise ValueError("TOKEN non trouvé dans bot-token.txt")

bot.run(load_token())
