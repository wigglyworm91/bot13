import discord
from discord.ext import commands
import json
import re
from dotenv import dotenv_values

config = dotenv_values(".env")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

PREFIX = 'b!'

bot = commands.Bot(command_prefix=PREFIX, intents=intents)


def load_settings(guild):
    try:
        with open(f'.settings/{guild.id}.json') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_settings(guild, settings):
    with open(f'.settings/{guild.id}.json', 'w') as f:
        return json.dump(settings, f)

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')

@bot.command()
async def hello(ctx):
    await ctx.reply(f'Hello {ctx.author.name}!')

@bot.hybrid_command()
async def verifyrole(ctx, role: discord.Role):
    guild = role.guild
    settings = load_settings(guild)
    settings['VERIFY_ROLE'] = role.id
    save_settings(guild, settings)
    await ctx.reply(f'Set verifyrole to <&{role}>')

@bot.hybrid_command()
async def welcomechannel(ctx, channel: discord.TextChannel):
    guild = channel.guild
    settings = load_settings(guild)
    settings['WELCOME_CHANNEL'] = channel.id
    save_settings(guild, settings)
    await ctx.reply(f'Set welcomechannel to <#{channel}>')

@bot.hybrid_command()
async def fakejoin(ctx, target: discord.Member):
    await send_join_message(target)
    await ctx.reply('k')

@bot.command()
async def sync(ctx):
    if ctx.author.id == 246857845285453824: # me!
        print('Syncing as requested...')
        async with ctx.typing():
            await bot.tree.sync()
        await ctx.reply('Synced')
    else:
        await ctx.reply("You're not my supervisor!")

@bot.event
async def on_member_join(member):
    await send_join_message(member)

async def send_join_message(member):
    # load settings for the guild
    guild = member.guild
    settings = load_settings(guild)

    print(f'New user {member.id} joined guild {guild.id}')

    # figure out what invite link they used
    # figure out who made that invite link
    # add message in #general saying welcome
    welcch = guild.get_channel(int(settings['WELCOME_CHANNEL']))
    msg = await welcch.send(f'{member.name}#{member.discriminator} (<@{member.id}>) just joined and is waiting to be verified! Please click the check mark below if you can vouch for this user! ||ID: {member.id}||')
    print(f'sent welcome message id {msg.id}')

    # react to that message with :white_check_mark:
    await msg.add_reaction('✅')

@bot.event
async def on_raw_reaction_add(payload):
    reaction = payload.emoji
    user = payload.member
    guild = payload.member.guild
    channel = bot.get_channel(payload.channel_id)
    message = await channel.fetch_message(payload.message_id)

    # load settings for the guild
    settings = load_settings(guild)
    verify_role = guild.get_role(settings['VERIFY_ROLE'])

    # who did it?
    verifier = user

    # ignore it if it was us
    if user == bot.user:
        return

    # if it's not one of ours we don't care
    if message.author != bot.user:
        return

    # if it's one of ours, was it a join message?
    if 'just joined and is waiting to be verified' not in message.content:
        print('reacted to a non-join message')
        return

    # figure out who the join message is talking about
    print(f'{message.content=!r}')
    match = re.search(r'ID: (\d+)', message.content)
    verifee_id = int(match.group(1))
    verifee = guild.get_member(verifee_id)

    # and verify them
    if verify_role in verifee.roles:
        # already verified
        pass
    else:
        await verifee.add_roles(verify_role, reason=f'Verified by {verifier.name}#{verifier.discriminator} <@{verifier.id}>')
        new_content = re.sub(r'just joined and is waiting to be verified.*', f'has been verified by <@{verifier.id}>; welcome to the server!', message.content)
        await message.edit(content=new_content)

bot.run(config['DISCORD_TOKEN'])
