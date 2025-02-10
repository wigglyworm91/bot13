import discord
from discord.ext import commands
import json
import re
from dotenv import dotenv_values
import datetime as dt

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
    print(f'Logged in as {bot.user}')

@bot.command()
async def hello(ctx):
    await ctx.reply(f'Hello {ctx.author.name}!')

@bot.hybrid_command()
async def verifyrole(ctx, role: discord.Role):
    guild = role.guild
    settings = load_settings(guild)
    settings['VERIFY_ROLE'] = role.id
    save_settings(guild, settings)
    await ctx.reply(f'Set verifyrole to <@&{role}>')

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

@bot.hybrid_command()
async def modrole(ctx, role: discord.Role):
    guild = role.guild
    settings = load_settings(guild)
    settings['MOD_ROLE'] = role.id
    save_settings(guild, settings)
    await ctx.reply(f'Set modrole to <@&{role}>')

@bot.hybrid_command()
async def lsync(ctx):
    if ctx.author.id == 246857845285453824:  # Your user ID
        if ctx.guild is None:
            await ctx.reply("This command can only be used in a server.")
            return

        print(f'Syncing commands for guild: {ctx.guild.id}...')
        await bot.tree.sync(guild=discord.Object(id=ctx.guild.id))
        await ctx.reply(f"Commands synced for `{ctx.guild.name}`!")
    else:
        await ctx.reply("You're not my supervisor!")

@bot.hybrid_command()
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

    # if it wasn't a green check reaction then we don't care
    if reaction.name != '✅':
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

@bot.hybrid_command(name="purge", description='Purge old messages over N hours (up to 14 days)')
#@discord.app_commands.describe(
#    hours='Will purge messages older than this many hours'
#)
async def purge_old_messages(
    ctx,
    hours: int,
):
    user = ctx.author

    # load settings
    settings = load_settings(ctx.guild)
    mod_role = settings.get('MOD_ROLE', None)
    if mod_role is None:
        await ctx.reply('modrole must be configured first by an admin', ephemeral=True)
        return

    # check permission
    if not any(role.id == mod_role for role in user.roles):
        await ctx.reply(f'You need the <@&{mod_role}> role to use this command.', ephemeral=True)
        return

    # check data
    if hours < 24:
        await ctx.reply('Please enter a value of at least 24 hours.', ephemeral=True)
        return
    if hours > 14*24:
        await ctx.reply('Note that we are not capable of deleting messages over 2 weeks old', ephemeral=True)
        return

    # make sure threshold_time is UTC timezone aware
    now_time = dt.datetime.utcnow().replace(tzinfo=discord.utils.utcnow().tzinfo)
    threshold_time = now_time - dt.timedelta(hours=hours)
    def is_older_than_72h(msg):
        # make sure we don't delete the message we're responding to
        if msg == ctx.message:
            return False
        return msg.created_at < threshold_time

    async with ctx.typing():
        deleted = await ctx.channel.purge(limit=5000, check=is_older_than_72h)
        await ctx.reply(f'Deleted {len(deleted)} {"message" if len(deleted)==1 else "messages"} older than {hours} hours.', ephemeral=True)

bot.run(config['DISCORD_TOKEN'])
