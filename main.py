import discord
import json
import re
from dotenv import dotenv_values

config = dotenv_values(".env")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = discord.Client(intents=intents)

PREFIX = 'b!'

def load_settings(guild):
    try:
        with open(f'.settings/{guild.id}.json') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_settings(guild, settings):
    with open(f'.settings/{guild.id}.json', 'w') as f:
        return json.dump(settings, f)

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith(f'{PREFIX}hello'):
        await message.channel.send('Hello!')

    if message.content.startswith(f'{PREFIX}verifyrole'):
        target = re.search(r'\d+', message.content).group(0)
        targetrole = message.guild.get_role(int(target))
        set_verifyrole(targetrole)

    if message.content.startswith(f'{PREFIX}welcomechannel'):
        target = re.search(r'\d+', message.content).group(0)
        targetchan = message.guild.get_channel(int(target))
        set_welcomechannel(targetchan)

    if message.content.startswith(f'{PREFIX}fakejoin'):
        target = re.search(r'\d+', message.content).group(0)
        await on_member_join(message.guild.get_member(int(target)))

def set_verifyrole(role):
    guild = role.guild
    settings = load_settings(guild)
    settings['VERIFY_ROLE'] = role.id
    save_settings(guild, settings)
    print(f'Set verifyrole to {role.id} for guild {guild.id}')

def set_welcomechannel(channel):
    guild = channel.guild
    settings = load_settings(guild)
    settings['WELCOME_CHANNEL'] = channel.id
    save_settings(guild, settings)
    print(f'Set welcomechannel to {channel.id} for {guild.id}')

@client.event
async def on_member_join(member):
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

@client.event
async def on_raw_reaction_add(payload):
    reaction = payload.emoji
    user = payload.member
    guild = payload.member.guild
    channel = client.get_channel(payload.channel_id)
    message = await channel.fetch_message(payload.message_id)

    # load settings for the guild
    settings = load_settings(guild)
    verify_role = guild.get_role(settings['VERIFY_ROLE'])

    # who did it?
    verifier = user

    # ignore it if it was us
    if user == client.user:
        return

    # if it's not one of ours we don't care
    if message.author != client.user:
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

client.run(config['DISCORD_TOKEN'])
