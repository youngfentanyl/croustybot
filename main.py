import os
import discord
import asyncio
from discord import app_commands
from discord.ext import commands
import re
import datetime

WELCOME_CHANNEL_ID = 1384615171154116691
AUTO_ROLE_ID = 1384194331941933126
STATUS_CHANNEL_ID = 1384625428576342147
TOURNAMENT_ROLE_ID = 1384552887312711821

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="/", intents=intents)
tree = bot.tree

def parse_duration(duration_str):
    match = re.match(r"(\d+)\s*([mhdw])", duration_str.lower())
    if not match:
        raise ValueError("Invalid time format. Use formats like 30m, 2h, 1d, or 1w")
    value, unit = int(match.group(1)), match.group(2)
    multipliers = {'m': 60, 'h': 3600, 'd': 86400, 'w': 604800}
    return value * multipliers[unit]

class TournamentModal(discord.ui.Modal, title="Create a Tournament"):
            def __init__(self, mode, registration_seconds):
                super().__init__()
                self.mode = mode
                self.registration_seconds = registration_seconds

                self.add_item(discord.ui.TextInput(label="Tournament Title", max_length=256, required=True))
                self.add_item(discord.ui.TextInput(label="Description", style=discord.TextStyle.paragraph, max_length=2048, required=True))
                self.add_item(discord.ui.TextInput(label="Color (hex, e.g. #ff0000 or ff0000)", required=True, max_length=7))
                self.add_item(discord.ui.TextInput(label="Banner image URL", required=True))

                if self.mode == "1v1":
                    label = "Number of players"
                else:
                    label = "Number of teams"
                self.add_item(discord.ui.TextInput(label=label, required=True))

            async def on_submit(self, interaction: discord.Interaction):
                inputs = {item.label: item.value for item in self.children}
                color_str = inputs["Color (hex, e.g. #ff0000 or ff0000)"].strip().lstrip("#")

                try:
                    color = discord.Color(int(color_str, 16))
                except Exception:
                    await interaction.response.send_message("❌ Invalid hex color! (e.g. #ff0000)", ephemeral=True)
                    return

                end_timestamp = int((discord.utils.utcnow().timestamp()) + self.registration_seconds)

                embed = discord.Embed(
                    title=f"__{inputs['Tournament Title']}__",
                    description=inputs["Description"],
                    color=color
                )

                embed.add_field(name="Mode", value=f"{self.mode} : {inputs.get('Number of players', inputs.get('Number of teams'))}", inline=True)
                embed.set_image(url=inputs["Banner image URL"])
                embed.set_footer(text=f"Tournament organized by {interaction.user.display_name}")
                embed.add_field(name="\u200b", value=f"⏰ Inscriptions : jusqu'au <t:{end_timestamp}:F>", inline=False)

                role_mention = f"<@&{TOURNAMENT_ROLE_ID}>"
                await interaction.response.send_message(content=role_mention, embed=embed)
                msg = await interaction.original_response()

                async def update_timer(message, end_ts):
                    while True:
                        remaining = int(end_ts - discord.utils.utcnow().timestamp())
                        if remaining <= 0:
                            break
                        await asyncio.sleep(min(remaining, 60))
                        embed.set_field_at(
                            len(embed.fields) - 1,
                            name="\u200b",
                            value=f"⏰ Inscriptions : jusqu'au <t:{end_ts}:F>",
                            inline=False
                        )
                        try:
                            await message.edit(embed=embed)
                        except Exception:
                            break
                    embed.set_field_at(
                        len(embed.fields) - 1,
                        name="\u200b",
                        value="⏰ Inscriptions : terminées !",
                        inline=False
                    )
                    try:
                        await message.edit(embed=embed)
                    except Exception:
                        pass

                bot.loop.create_task(update_timer(msg, end_timestamp))

@tree.command(name="create_tournament", description="Create a tournament embed (admin only)")
@app_commands.describe(
    mode="Mode du tournoi (1v1, 2v2, 3v3, 4v4, 5v5)",
    registration_time="Temps avant la fin des inscriptions (ex: 30m, 2h, 1d)"
)
@app_commands.choices(
    mode=[
        app_commands.Choice(name="1v1", value="1v1"),
        app_commands.Choice(name="2v2", value="2v2"),
        app_commands.Choice(name="3v3", value="3v3"),
        app_commands.Choice(name="4v4", value="4v4"),
        app_commands.Choice(name="5v5", value="5v5"),
    ]
)
async def create_tournament(interaction: discord.Interaction, mode: app_commands.Choice[str], registration_time: str):
    member = interaction.user
    if not isinstance(member, discord.Member):
        await interaction.response.send_message("❌ Command can only be used in a server.", ephemeral=True)
        return

    has_permission = member.guild_permissions.administrator
    has_role = any(role.id == TOURNAMENT_ROLE_ID for role in member.roles)

    if not (has_permission or has_role):
        await interaction.response.send_message("❌ You must be an administrator or have the tournament role to use this command.", ephemeral=True)
        return

    try:
        registration_seconds = parse_duration(registration_time)
    except ValueError as e:
        await interaction.response.send_message(f"❌ {e}", ephemeral=True)
        return

    await interaction.response.send_modal(TournamentModal(mode.value, registration_seconds))

@bot.event
async def on_ready():
    activity = discord.Streaming(
        name="Coding The BOT",
        url="https://www.twitch.tv/croustybad"
    )
    await bot.change_presence(status=discord.Status.online, activity=activity)
    print(f"Connected as {bot.user} with status Streaming : Coding The BOT")
    await tree.sync()
    print(f'Logged in as {bot.user.name}')
    print(f'Bot ID: {bot.user.id}')
    print('Slash commands synced.')

    for guild in bot.guilds:
        status_channel = guild.get_channel(STATUS_CHANNEL_ID)
        if status_channel:
            try:
                await status_channel.edit(name="🟢┃online")
                print(f"Status channel renamed to 'online' in {guild.name}")
            except Exception as e:
                print(f"Failed to rename status channel: {e}")
        else:
            print(f"Status channel with ID {STATUS_CHANNEL_ID} not found in guild {guild.name}")

@bot.event
async def on_disconnect():
    for guild in bot.guilds:
        status_channel = guild.get_channel(STATUS_CHANNEL_ID)
        if status_channel:
            try:
                bot.loop.create_task(status_channel.edit(name="🔴┃offline"))
                print(f"Status channel renamed to 'offline' in {guild.name}")
            except Exception as e:
                print(f"Failed to rename status channel: {e}")
        else:
            print(f"Status channel with ID {STATUS_CHANNEL_ID} not found in guild {guild.name}")

@bot.event
async def on_member_join(member: discord.Member):
    try:
        role_to_assign = member.guild.get_role(AUTO_ROLE_ID)
        if role_to_assign:
            await member.add_roles(role_to_assign)
            print(f"Role '{role_to_assign.name}' assigned to {member.name}.")
        else:
            print(f"Error: Role with ID {AUTO_ROLE_ID} not found.")
    except discord.Forbidden:
        print(f"Error: Bot does not have permissions to assign role {AUTO_ROLE_ID} to {member.name}.")
    except Exception as e:
        print(f"An error occurred while assigning the role: {e}")

    welcome_channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
    if welcome_channel:
        embed = discord.Embed(
            title=f"__HEY__",
            description=f"<a:pepe_Flip:1384618044852277411>  Greetings! I am thrilled to have you here. **Don't forget that this server needs to remain private since it's a secret project**!",
            color=0x90EE90
        )

        try:
            await welcome_channel.send(content=f"{member.mention}", embed=embed)
            print(f"Welcome message sent for {member.name} in #{welcome_channel.name}.")
        except discord.Forbidden:
            print(f"Error: Bot does not have permissions to send a message in #{welcome_channel.name}.")
        except Exception as e:
            print(f"An error occurred while sending the welcome message: {e}")
    else:
        print(f"Error: Welcome channel with ID {WELCOME_CHANNEL_ID} not found.")


def load_token(path="bot-token.txt"):
    with open(path, "r") as file:
        for line in file:
            if line.startswith("TOKEN="):
                return line.strip().split("TOKEN=")[1]
    raise ValueError("No valid TOKEN found in bot-token.txt")


bot.run(load_token())
